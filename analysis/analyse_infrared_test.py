# input file structure of an experiment
#
# ./cmd.sh
# ./infrared-test_layout-SHORT_DESCRIPTION.config

# output file structure of an experiment
#
# ./background.avi
# ./data_infrared-test/
# ./data_infrared-test/bee-arena/
# ./data_infrared-test/bee-arena/casu-NNN/
# ./data_infrared-test/bee-arena/casu-NNN/YYYY-MM-DD-HH-MM-SS-casu-NNN.csv
# ./infrared-test.arena
# ./infrared-test.assisi
# ./infrared-test_assisi-run.log
# ./infrared-test.darc.config
# ./infrared-test.dep
# ./infrared-test-manager.log
# ./infrared-test.nbg
# ./infrared-test_sandbox/...
# ./video.avi

import argparse
import csv
import cv2
import math
import matplotlib
import numpy
import os.path
import shutil
import subprocess
import tempfile
import yaml

matplotlib.use ('Agg')

import casu_log
import domset_binary.prologue.infrared_test_manager
import util.math
import util.video

def main ():
    args = process_arguments ()
    frames_folder = tempfile.mkdtemp (prefix = 'infrared-test_')
    for config_filename in args.config:
        experiment_folder = os.path.dirname (config_filename)
        with open (config_filename, 'r') as fd:
            config_data = yaml.safe_load (fd)
        if args.split_background_video:
            split_background_video (
                config_data = config_data,
                experiment_folder = experiment_folder,
                working_folder = frames_folder,
            )
        if args.process_bees_video:
            create_average_background_image (
                 config_data = config_data,
                 experiment_folder = experiment_folder,
                 working_folder = frames_folder,
            )
            split_bees_video (
                config_data = config_data,
                experiment_folder = experiment_folder,
                bees_frames_folder = frames_folder,
            )
            prepare_masks (
                config_data = config_data,
                experiment_folder = experiment_folder,
                working_folder = frames_folder)
            for df in args.delta_frame:
                for sct in args.same_colour_threshold:
                    for dv in args.delta_velocity:
                        compute_bees_data (
                            config_data = config_data,
                            experiment_folder = experiment_folder,
                            working_folder = frames_folder,
                            delta_frame = df,
                            same_colour_threshold = sct,
                            delta_velocity = dv,
                            debug = True
                            )
        if args.plot_video_casu_log_data:
            plot_video_casu_log_data (
                config_data = config_data,
                experiment_folder = experiment_folder,
                list_same_colour_threshold = args.same_colour_threshold,
                list_delta_frame = args.delta_frame)
        shutil.rmtree (frames_folder)
        os.mkdir (frames_folder)

def split_background_video (config_data, experiment_folder, working_folder):
    print ('Splitting background video of experiment {}...'.format (experiment_folder))
    background_frames_folder = os.path.join (experiment_folder, 'background.frames')
    os.mkdir (background_frames_folder)
    number_frames = domset_binary.prologue.infrared_test_manager.BACKGROUND_VIDEO_LENGTH * config_data ['video']['frames_per_second']
    util.video.split_video (
        video_filename = os.path.join (experiment_folder, 'background.avi'),
        number_frames = number_frames,
        frames_per_second = config_data ['video']['frames_per_second'],
        output_template = os.path.join (
            background_frames_folder,
            'background-%0{:d}d.png'.format (1 + int (math.ceil (math.log (number_frames, 10))))
        ),
        debug = False
    )

def create_average_background_image (config_data, experiment_folder, working_folder):
    number_frames = domset_binary.prologue.infrared_test_manager.BACKGROUND_VIDEO_LENGTH * config_data ['video']['frames_per_second']
    size = (
        util.video.CAMERA_RESOLUTION_Y - config_data ['video']['crop_bottom'] - config_data ['video']['crop_top'],
        util.video.CAMERA_RESOLUTION_X - config_data ['video']['crop_left'] - config_data ['video']['crop_right'],
        3)
    background_image = numpy.zeros (size, dtype = numpy.uint16)
    for index in range (1, 1 + number_frames):
        current_image = cv2.imread (os.path.join (
            os.path.join (experiment_folder, 'background.frames'),
            #working_folder,
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
            os.path.join (experiment_folder, 'background.frames'),
            'avg-background.png'),
        background_image)
    cv2.imwrite (
        os.path.join (
            working_folder,
            'background.png'),
        background_image)

def split_bees_video (config_data, experiment_folder, bees_frames_folder):
    print ('Splitting video with bees of experiment {}...'.format (experiment_folder))
    number_frames = 60 * config_data ['parameters']['experiment_duration'] * config_data ['video']['frames_per_second']
    util.video.split_video (
        video_filename = os.path.join (experiment_folder, 'video.avi'),
        number_frames = number_frames,
        frames_per_second = config_data ['video']['frames_per_second'],
        output_template = os.path.join (
            bees_frames_folder,
            'frames-%04d.png',
            #'frames-%0{:d}d.png'.format (1 + int (math.ceil (math.log (number_frames, 10))))
        ),
        debug = False
    )

def prepare_masks (config_data, experiment_folder, working_folder):
    number_ROIs = 2 * len (config_data ['arenas'])
    list_casus = [
        a_casu
        for an_arena in config_data ['arenas']
        for a_casu in an_arena.itervalues ()]
    list_casus.sort ()
    for index, a_casu in enumerate (list_casus):
        os.symlink (
            os.path.join (
                os.path.join (
                    os.getcwd (),
                    experiment_folder),
                'background.frames/Ring-Mask-{}.png'.format (a_casu)),
            os.path.join (
                working_folder,
                'Mask-{}.png'.format (index + 1)))

def compute_bees_data (config_data, experiment_folder, working_folder, delta_frame, same_colour_threshold, delta_velocity, debug = False):
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
    number_frames = 60 * config_data ['parameters']['experiment_duration'] * config_data ['video']['frames_per_second']
    command = [
        '/home/pedro/cloud/Dropbox/xSearch/ASSISIbf/software/build-assisi-batch-video-processing-Desktop-Debug/assisi-batch-video-processing',
        '--number-frames', '{:d}'.format (number_frames),
        '--csv-file', csv_filename,
        '--number-ROIs', '{:d}'.format (2 * len (config_data ['arenas'])),
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

def plot_video_casu_log_data (config_data, experiment_folder, list_same_colour_threshold, list_delta_frame):
    casu_logs = read_casu_logs (config_data, experiment_folder)
    for a_casu_log in casu_logs.values ():
        a_casu_log.compute_activity (
            start_index = 0,
            end_index = 50,
            offset = 500,
            moving_average_length = 61,
            )
    casu_numbers = casu_logs.keys ()
    casu_numbers.sort ()
    for same_colour_threshold in list_same_colour_threshold:
        for delta_frame in list_delta_frame:
            process_video_data_FOR_video_casu_log_data_plot (config_data, experiment_folder, casu_logs, casu_numbers, same_colour_threshold, delta_frame)

def process_video_data_FOR_video_casu_log_data_plot (config_data, experiment_folder, casu_logs, casu_numbers, same_colour_threshold, delta_frame):
    video_data = read_video_data (experiment_folder, same_colour_threshold = same_colour_threshold, delta_frame = delta_frame)
    video_data_column = dict ([
        (a_casu, index)
        for index, a_casu in enumerate (casu_numbers)])
    for an_arena in config_data ['arenas']:
        casu_A = an_arena ['A']
        casu_B = an_arena ['B']
        create_plot_video_casu_log_data (
            config_data = config_data,
            experiment_folder = experiment_folder,
            same_colour_threshold = same_colour_threshold,
            delta_frame = delta_frame,
            casu_A = casu_A,
            casu_B = casu_B,
            casu_log_A = casu_logs [casu_A],
            casu_log_B = casu_logs [casu_B],
            video_data_A = video_data [:, 2 * video_data_column [casu_A]],
            video_data_B = video_data [:, 2 * video_data_column [casu_B]],
            )

def read_casu_logs (config_data, experiment_folder):
    list_casu_numbers = [
        a_casu_number
        for an_arena in config_data ['arenas']
        for a_casu_number in an_arena.itervalues ()
    ]
    result = {
        a_casu_number : casu_log.CASU_Log (
            a_casu_number,
            os.path.join (
                experiment_folder,
                'data_infrared-test/beearena/'
            )
        )
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

def create_plot_video_casu_log_data (config_data, experiment_folder, same_colour_threshold, delta_frame, casu_A, casu_B, casu_log_A, casu_log_B, video_data_A, video_data_B, output_path = '.'):
    print ('Creating plots for data in folder {}, parameters SCT={} DF={}, and CASUs {} and {}'.format (experiment_folder, same_colour_threshold, delta_frame, casu_A, casu_B))
    zero_time = numpy.mean ([
        a_casu_log.led_actuator [0, 0]
        for a_casu_log in [casu_log_A, casu_log_B]
    ])
    experiment_duration = 60 * config_data ['parameters']['experiment_duration']
    # initialise plot
    figure_width, figure_height = 14, 9
    figure = matplotlib.pyplot.figure (figsize = (figure_width, figure_height))
    margin_left, margin_right  = 0.75, 0.1
    margin_bottom, margin_top = 0.6, 0.75
    axes = figure.subplots (
        nrows = 1,
        ncols = 2,
        gridspec_kw = {
            'width_ratios' : [2, 2],
            'right' : 1 - margin_right / figure_width,
            'left' : margin_left / figure_width,
            'top' : 1 - margin_top / figure_height,
            'bottom' : margin_bottom / figure_height,
            'wspace' : 0.05
        },
        sharey = 'row',
    )
    for index, (a_casu_log, a_video_data) in enumerate (zip ([casu_log_A, casu_log_B], [video_data_A, video_data_B])):
        times_xs = [
            zero_time + second
            for second in range (experiment_duration)]
        indexes = [
            util.math.find_nearest_index (a_casu_log.infrared_raw [:, 0], a_time)
            for a_time in times_xs]
        xs = a_casu_log.moving_average_hits [indexes]
        ys = a_video_data [0::int (config_data ['video']['frames_per_second'])]
        axes [index].scatter (
            xs, ys
            )
        MAX_Y = 8000
        axes [index].set_xlabel ('bee activity')
        axes [index].set_xlim (-0.03, 1.03)
        axes [index].set_ylabel ('bee pixels')
        axes [index].set_ylim (-7, MAX_Y + 7)
        max_ys = max (ys)
        if max_ys > MAX_Y:
            print ('Maximum bee pixel in this case is {}'.format (max_ys))
    figure.suptitle ('infrared test\nrun {} SCT={} DF={} casus {} and {}'.format (
        experiment_folder,
        same_colour_threshold,
        delta_frame,
        casu_A, casu_B), fontsize = 9)
    figure.savefig (
        os.path.join (
            output_path,
            'bee-pixels-VS-activity_L{}-SCT{}-DF{}-C{}-C{}.png'.format (
                experiment_folder,
                same_colour_threshold,
                delta_frame,
                casu_A, casu_B)))

def process_arguments ():
    parser = argparse.ArgumentParser (
        description = 'Analyse the results of infra red test'
        )
    parser.add_argument (
        '--config', '-c',
        metavar = 'FILENAME',
        action = 'append',
        type = str,
        required = True,
        help = 'configuration file name'
    )
    parser.add_argument (
        '--output',
        metavar = 'PATH',
        default = '.',
        help = 'Output where plot files are saved.  Default is current directory.'
    )
    parser.add_argument (
        '--split-background-video',
        action = 'store_true',
        help = 'split background video'
    )
    parser.add_argument (
        '--process-bees-video',
        action = 'store_true',
        help = 'process videos with bees'
    )
    parser.add_argument (
        '--plot-video-casu-log-data',
        action = 'store_true',
        help = 'process videos with bees'
    )
    parser.add_argument (
        '--delta-frame',
        metavar = 'N',
        action = 'append',
        type = int,
        required = True,
        help = 'Delta frame used when computing bee velocity'
    )
    parser.add_argument (
        '--same-colour-threshold',
        metavar = 'N',
        action = 'append',
        type = int,
        required = True,
        help = 'Threshold used when comparing two images for differences'
    )
    parser.add_argument (
        '--delta-velocity',
        metavar = 'N',
        action = 'append',
        type = int,
        help = 'Delta velocity used when computing bee acceleration'
    )
    return parser.parse_args ()

if __name__ == '__main__':
    main ()
