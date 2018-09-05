#!/usr/bin/python

# file structure of an inter-species experiment

# run-RRR/video.avi
# run-RRR/background.avi
# run-RRR/cfgs/GRAPH.conf
# run-RRR/cfgs/GRAPH.config
# run-RRR/cfgs/GRAPH_graph.yml
# run-RRR/cfgs/GRAPH.nodemasters
# run-RRR/cfgs/GRAPH.workers
# run-RRR/casu-NNN/YYYY-MM-DD-HH-MM-SS-casu-NNN.csv
# run-RRR/casu-NNN/YYYY-MM-DD-HH-MM-SS-casu-NNN-domset.csv
# run-RRR/data_workers/fish-tank/cats/*.csv
# run-RRR/ISIlog/data_beeArena_to_ISI.log
# run-RRR/ISIlog/ISI_log.log

import argparse
import csv
import cv2
import numpy
import os.path
import shutil
import subprocess
import tempfile
import yaml

import casu_domset_log
import casu_log
import util.video

BACKGROUND_VIDEO_FILENAME = 'background-video.avi'

def main ():
    args = process_arguments ()
    working_folder = tempfile.mkdtemp (prefix = 'interspecies-experiment_')
    for run_number in args.run:
        process_experiment (
            graph_name = args.graph,
            run_number = run_number,
            base_path = args.base_path,
            working_folder = working_folder,
            delta_frame = args.delta_frame,
            same_colour_threshold = args.same_colour_threshold)
    print ('Press ENTER to remove working folder [{}]'.format (working_folder))
    raw_input ('> ')
    shutil.rmtree (working_folder)

def process_experiment (graph_name, run_number, working_folder, delta_frame, same_colour_threshold, base_path = '.'):
    experiment_path = os.path.join (base_path, 'run-{:03d}'.format (run_number))
    frames_path = os.path.join (experiment_path, 'frames')
    if not os.path.exists (frames_path):
        os.makedirs (frames_path)
    args = process_arguments ()
    config_filename = os.path.join (
        experiment_path,
        'cfgs/{}.config'.format (graph_name)
        )
    with open (config_filename, 'r') as fd:
        config_data = yaml.safe_load (fd)
    with open (os.path.join (experiment_path, 'cfgs/arenas.config'), 'r') as fdr:
        arena_data = yaml.safe_load (fdr)
    # background video
    if False:
        split_background_video (config_data, experiment_path)
        create_average_background_image (config_data, experiment_path, working_folder)
    # bee video
    if False:
        prepare_masks (arena_data, experiment_path, working_folder)
        split_bees_video (config_data, experiment_path, working_folder)
        compute_bees_data (
            arena_data = arena_data,
            config_data = config_data,
            experiment_folder = experiment_path,
            working_folder = working_folder,
            delta_frame = delta_frame,
            same_colour_threshold = same_colour_threshold,
            debug = True
            )
    # read data for plots
    dict_casu_logs = read_casu_logs (config_data, experiment_path)
    dict_casu_domset_logs = read_casu_domset_logs (config_data, experiment_path)
    video_data = read_video_data (experiment_path, same_colour_threshold, delta_frame)

def split_background_video (config_data, experiment_path):
    number_frames = config_data ['video']['frames_per_second'] * 2
    code = util.video.split_video (
        os.path.join (experiment_path, BACKGROUND_VIDEO_FILENAME),
        number_frames,
        config_data ['video']['frames_per_second'],
        os.path.join (experiment_path, 'frames/background-%3d.png'),
        debug = True
    )
    if code != 0:
        print ('[E] There was a problem splitting the background video!')
        sys.exit (code)

def create_average_background_image (config_data, experiment_path, working_folder):
    number_frames = config_data ['video']['frames_per_second'] * 2
    size = (
        util.video.CAMERA_RESOLUTION_Y - config_data ['video']['crop_bottom'] - config_data ['video']['crop_top'],
        util.video.CAMERA_RESOLUTION_X - config_data ['video']['crop_left'] - config_data ['video']['crop_right'],
        3)
    background_image = numpy.zeros (size, dtype = numpy.uint16)
    for index in range (1, 1 + number_frames):
        current_image = cv2.imread (os.path.join (
            os.path.join (experiment_path, 'frames'),
            'background-{:03d}.png'.format (index)))
        background_image = cv2.add (
            background_image,
            current_image,
            dtype = cv2.CV_32F,
            )
    background_image = cv2.addWeighted (
        src1 = background_image,
        alpha = 1.0 / number_frames,
        src2 = numpy.zeros (size, dtype = numpy.uint8),
        beta = 0,
        gamma = 0,
        dtype = cv2.CV_8U)
    cv2.imwrite (
        os.path.join (
            experiment_path,
            'avg-background.png'),
        background_image)
    cv2.imwrite (
        os.path.join (
            working_folder,
            'background.png'),
        background_image)

def prepare_masks (arena_data, experiment_folder, working_folder):
    number_ROIs = 2 * len (arena_data ['arenas'])
    list_arenas = []
    for an_arena in arena_data ['arenas']:
        casus = [a_casu for a_casu in an_arena.itervalues ()]
        casus.sort ()
        list_arenas.append (casus)
    list_arenas.sort ()
    print (list_arenas)
    for index_arena, casus in enumerate (list_arenas):
        for index_casu, a_casu in enumerate (casus):
            os.symlink (
                os.path.join (
                    os.path.join (
                        os.getcwd (),
                        experiment_folder),
                    'masks/Stadium-Ring-{}-{}.png'.format (index_arena + 1, a_casu)),
                os.path.join (
                    working_folder,
                    'Mask-{}.png'.format (2 * index_arena + index_casu + 1)))

def split_bees_video (config_data, experiment_folder, working_folder):
    print ('Splitting video with bees of experiment {}...'.format (experiment_folder))
    number_frames = 60 * config_data ['experiment_duration'] * config_data ['video']['frames_per_second']
    util.video.split_video (
        video_filename = os.path.join (experiment_folder, 'video.avi'),
        number_frames = number_frames,
        frames_per_second = config_data ['video']['frames_per_second'],
        output_template = os.path.join (
            working_folder,
            'frames-%04d.png',
        ),
        debug = False
    )

def compute_bees_data (arena_data, config_data, experiment_folder, working_folder, delta_frame, same_colour_threshold, delta_velocity = 2, debug = False):
    # create the CSV file read by assisi-batch-video-processing that contains the video to process
    csv_filename = os.path.join (working_folder, 'data.csv')
    with open (csv_filename, 'w') as fdw:
        writer = csv.writer (
            fdw,
            delimiter = ',',
            quoting = csv.QUOTE_NONNUMERIC,
            lineterminator = '\n')
        writer.writerow ([
            'folder',
            'x1',
            'y1',
            'x2',
            'y2',
            'use',
            ])
        writer.writerow ([
            working_folder,
            0, 0, 0, 0,
            1,
            ])
        fdw.close ()
    number_frames = 60 * config_data ['experiment_duration'] * config_data ['video']['frames_per_second']
    command = [
        '/home/pedro/cloud/Dropbox/xSearch/ASSISIbf/software/build-assisi-batch-video-processing-Desktop-Debug/assisi-batch-video-processing',
        '--number-frames', '{:d}'.format (number_frames),
        '--csv-file', csv_filename,
        '--number-ROIs', '{:d}'.format (2 * len (arena_data ['arenas'])),
        '--delta-frame', '{:d}'.format (delta_frame),
        '--same-colour-threshold', '{:d}'.format (same_colour_threshold),
        '--delta-velocity', '{:d}'.format (delta_velocity),
        '--frame-file-type', 'png',
        '--check-ROIs',
        '--features-number-bees-AND-bee-speed',
    ]
    if debug:
        print ('Full command is:')
        print (' '.join (command))
        print
    process = subprocess.Popen (command)
    process.wait ()
    # move the CSV files to the experiment folder
    for csv_file in [
            'features-pixel-count-difference_SCT={}_DF={}_histogram-equalization.csv'.format (same_colour_threshold, delta_frame),
            'histograms-frames_masked-ROIs_bee-speed_histogram-equalisation-normal_DF={}.csv'.format (delta_frame),
            'histograms-frames_masked-ROIs_number-bees_histogram-equalisation-normal.csv'
            ]:
        print ('Moving file {} form {} to {}...'.format (csv_file, working_folder, experiment_folder))
        os.rename (
            os.path.join (
                working_folder,
                csv_file),
            os.path.join (
                experiment_folder,
                csv_file))

def create_plot (config_data, experiment_folder, same_colour_threshold, delta_frame):
    dict_casu_logs = read_casu_logs (config_data, experiment_folder)
    dict_casu_domset_logs = read_casu_domset_logs (config_data, experiment_folder)
    video_data = read_video_data (experiment_folder, same_colour_threshold, delta_frame)
    number_nodes = len (config_data ['graph']['node_CASUs'])
    # initialise plot
    figure, axes = create_figure (
        figure_width = 14, figure_height = 9,
        number_rows = number_nodes, number_cols = 2,
        margin_left = 0.5, margin_right = 0.1,
        margin_top = 0.5, margin_bottom = 0.2
        )
    for index_axes in range (2):
        axes [number_nodes - 1, index_axes].set_xlabel ('time (m:ss)')
        axes [number_nodes - 1, index_axes].set_xlim (
    for index_node in range (number_nodes):

def create_figure (figure_width, figure_height, number_rows, number_cols,
                       margin_left, margin_right, margin_top, margin_bottom):
    figure = matplotlib.pyplot.figure (figsize = (figure_width, figure_height))
    axes = figure.subplots (
        nrows = number_rows,
        ncols = number_cols,
#            'width_ratios' : [2, 2],
            'right' : 1 - margin_right / figure_width,
            'left' : margin_left / figure_width,
            'top' : 1 - margin_top / figure_height,
            'bottom' : margin_bottom / figure_height,
            'wspace' : 0.05
        },
        sharex = True,
        )
    return figure, axes

def read_casu_logs (config_data, experiment_folder):
    list_casu_numbers = config_data ['controllers']['domset']['casus']
    result = {
        a_casu_number : casu_log.CASU_Log (a_casu_number, experiment_folder)
        for a_casu_number in list_casu_numbers
    }
    return result

def read_casu_domset_logs (config_data, experiment_folder):
    list_casu_numbers = config_data ['controllers']['domset']['casus']
    result = {
        a_casu_number : casu_domset_log.CASU_DOMSET_Log (a_casu_number, experiment_folder)
        for a_casu_number in list_casu_numbers
    }
    return result

def read_video_data (experiment_folder, same_colour_threshold, delta_frame):
    _filename = os.path.join (
        experiment_folder,
        'features-pixel-count-difference_SCT={}_DF={}_histogram-equalization.csv'.format (
            same_colour_threshold,
            delta_frame
    ))
    with open (_filename, 'rb') as fdr:
        reader = csv.reader (
            fdr, 
            delimiter = ',',
            quoting = csv.QUOTE_NONE)
        csv_contents = [[int (x) for x in row] for row in reader]
    result = numpy.array (csv_contents)
    return result

def process_arguments ():
    parser = argparse.ArgumentParser (
        'Process interspecies experiment data.\nThe data produced by an experiment is stored in a folder named run-XXX.  Inside this folder, there is a folder cfgs with configuration files, folders casu-NNN with casu log, ...\n\n'
    )
    parser.add_argument (
        '--graph', '-g',
        metavar = 'LABEL',
        type = str,
        required = True,
        help = 'graph name used in the file name of all configuration files'
    )
    parser.add_argument (
        '--run', '-r',
        metavar = 'N',
        action = 'append',
        type = int,
        required = True,
        help = 'run number to process'
    )
    parser.add_argument (
        '--base-path',
        metavar = 'PATH',
        type = str,
        default = '.',
        help = 'path where the experiment data files are stored'
    )
    parser.add_argument (
        '--delta-frame',
        metavar = 'N',
        type = int,
        required = True,
        help = 'Delta frame used when computing bee velocity'
    )
    parser.add_argument (
        '--same-colour-threshold',
        metavar = 'N',
        type = int,
        required = True,
        help = 'Threshold used when comparing two images for differences'
    )
    return parser.parse_args ()

if __name__ == '__main__':
    main ()
