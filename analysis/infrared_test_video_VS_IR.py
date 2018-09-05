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
import math
import matplotlib
import numpy
import os.path
import yaml
matplotlib.use ('Agg')

import casu_log
import util

class Experiment:
    def __init__ (self, csv_row, same_colour_threshold, delta_frame):
        config_filename = csv_row [0]
        experiment_folder = os.path.dirname (config_filename)
        self.graph_name = csv_row [1]
        self.graph_layout = csv_row [2]
        self.run_number = int (csv_row [3])
        with open (config_filename, 'r') as fd:
            self.config_data = yaml.safe_load (fd)
        self.list_casu_numbers = [
            a_casu
            for an_arena in self.config_data ['arenas']
            for a_casu in an_arena.itervalues ()]
        self.list_casu_numbers.sort ()
        self.casu_video_data_column = dict ([
            (a_casu, index)
            for index, a_casu in enumerate (self.list_casu_numbers)])
#        self.video_data = None
#        self.casu_logs = None

 #   def load_data (self, same_colour_threshold, delta_frame):
        # initialise video data features
        self.video_data = read_video_data (experiment_folder, same_colour_threshold = same_colour_threshold, delta_frame = delta_frame)
        # initialise casu log
        self.casu_logs = {
            a_casu_number : casu_log.CASU_Log (
                a_casu_number,
                os.path.join (
                    experiment_folder,
                    'data_infrared-test/beearena/'
                )
            )
            for a_casu_number in self.list_casu_numbers
        }
        for a_casu_log in self.casu_logs.values ():
            a_casu_log.compute_activity (
                start_index = 0,
                end_index = 50,
                offset = 500,
                moving_average_length = 61,
                )

    def __str__ (self):
        return '{} {} {} {} {}'.format (self.graph_name, self.graph_layout, self.run_number, self.list_casu_numbers, self.config_data ['arenas'])

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

class Plot:
    def __init__ (self, casu_A, casu_B, _experiments):
        self.experiments = []
        self.casu_A = casu_A
        self.casu_B = casu_B
        key1 = {
            'A': casu_A,
            'B': casu_B}
        key2 = {
            'B': casu_A,
            'A': casu_B}
        print ('Starting plot for CASUS {} and {}'.format (casu_A, casu_B))
        for an_experiment in _experiments:
            if key1 in an_experiment.config_data ['arenas'] or key2 in an_experiment.config_data ['arenas']:
                print ('Adding {}'.format (an_experiment))
                self.experiments.append (an_experiment)

    def initialise (self,
                        figure_width = 14, figure_height = 9,
                        margin_left  = 0.75, margin_right = 0.1,
                        margin_bottom = 0.6, margin_top = 0.75):
        number_graphs = 2 * len (self.experiments)
        self.number_rows = int (math.ceil (math.sqrt (number_graphs * figure_height / figure_width)))
        self.number_rows += self.number_rows % 2
        self.number_cols = int (math.ceil (self.number_rows * figure_width / figure_width))
        print ('[III] Computed {} X {} axes'.format (self.number_rows, self.number_cols))
        if figure_width > figure_height:
            if self.number_cols * self.number_rows < number_graphs:
                print ('[III] Fixing number of rows')
                while self.number_cols * self.number_rows < number_graphs:
                    self.number_cols += 2
            elif self.number_cols * (self.number_rows - 1) >= number_graphs:
                print ('[III] Adjusting number of rows')
                while self.number_cols * (self.number_rows - 1) >= number_graphs:
                    self.number_rows += -1
        else:
            if self.number_cols * self.number_rows < number_graphs:
                print ('[III] Fixing number of columns')
                while self.number_cols * self.number_rows < number_graphs:
                    self.number_rows += 2
            elif (self.number_cols - 2) * self.number_rows >= number_graphs:
                print ('[III] Adjusting number of columns')
                while (self.number_cols - 2) * self.number_rows >= number_graphs:
                    self.number_cols += -2
        self.figure = matplotlib.pyplot.figure (figsize = (figure_width, figure_height))
        self.axes = self.figure.subplots (
            nrows = self.number_rows,
            ncols = self.number_cols,
            gridspec_kw = {
                'right' : 1 - margin_right / figure_width,
                'left' : margin_left / figure_width,
                'top' : 1 - margin_top / figure_height,
                'bottom' : margin_bottom / figure_height,
                'wspace' : 0.05
            },
            sharex = 'col',
            sharey = 'row',
            squeeze = False,
        )
        print ('[II] initialise a plot with {} rows by {} columns axes'.format (self.number_rows, self.number_cols))
        print (self.axes.size)

    def plot (self):
        index_x, index_y = 0, 0
        for an_experiment in self.experiments:
            self.__plot_casu (index_x, index_y, an_experiment, self.casu_A)
            index_x += 1
            self.__plot_casu (index_x, index_y, an_experiment, self.casu_B)
            index_x += 1
            if index_x == self.number_cols:
                index_x = 0
                index_y += 1

    def finalise (self, same_colour_threshold, delta_frame, output_path = '.'):
        self.figure.suptitle ('bee activity versus bee pixels\ncasus {} and {}'.format (self.casu_A, self.casu_B))
        self.figure.savefig (
            os.path.join (
                output_path,
                'bee-pixels-VS-activity_SCT{}-DF{}-C{}-C{}.png'.format (
                    same_colour_threshold,
                    delta_frame,
                    self.casu_A,
                    self.casu_B)))
        matplotlib.pyplot.close (self.figure)

    def __plot_casu (self, index_x, index_y, an_experiment, casu_number):
        an_axes = self.axes [index_y, index_x]
        experiment_duration = 60 * an_experiment.config_data ['parameters']['experiment_duration']
        a_casu_log = an_experiment.casu_logs [casu_number]
        zero_time = a_casu_log.led_actuator [0, 0]
        times_xs = [
            zero_time + second
            for second in range (experiment_duration)]
        indexes = [
            util.math.find_nearest_index (a_casu_log.infrared_raw [:, 0], a_time)
            for a_time in times_xs]
        xs = a_casu_log.moving_average_hits [indexes]
        ys = an_experiment.video_data [0::int (an_experiment.config_data ['video']['frames_per_second']), 2 * an_experiment.casu_video_data_column [casu_number]]
        an_axes.scatter (
            xs, ys
            )
        MAX_Y = 9000
        max_ys = max (ys)
        if max_ys > MAX_Y:
            print ('[W] Maximum bee pixel in this case is {}'.format (max_ys))
        if index_y == self.number_rows - 1:
            an_axes.set_xlabel ('bee activity')
            an_axes.set_xlim (-0.03, 1.03)
        if index_x == 0:
            an_axes.set_ylabel ('bee pixels')
            an_axes.set_ylim (-7, MAX_Y + 7)
        an_axes.set_title ('graph {} {} run {} casu {}'.format (
            an_experiment.graph_name,
            an_experiment.graph_layout,
            an_experiment.run_number,
            casu_number))

def main ():
    args = process_arguments ()
    with open (args.csv_file, 'r') as fdr:
        reader = csv.reader (
            fdr,
            delimiter = ',',
            quoting = csv.QUOTE_NONNUMERIC)
        reader.next ()
        experiments = [
            Experiment (row, args.same_colour_threshold, args.delta_frame)
            for row in reader]
    list_arenas = [
        (min (an_arena ['A'], an_arena ['B']), max (an_arena ['A'], an_arena ['B']))
        for an_experiment in experiments
        for an_arena in an_experiment.config_data ['arenas']]
    list_arenas.sort ()
    set_arenas = set (list_arenas)
    all_arenas = list (set_arenas)
    all_arenas.sort ()
    print (all_arenas)
    for an_arena in all_arenas:
        plot = Plot (an_arena [0], an_arena [1], experiments)
        plot.initialise ()
        plot.plot ()
        plot.finalise (args.same_colour_threshold, args.delta_frame, output_path = args.output)
        

def process_arguments ():
    parser = argparse.ArgumentParser (
        description = 'Analyse the results of infra red test'
        )
    parser.add_argument (
        '--csv-file', '-c',
        metavar = 'FILENAME',
        type = str,
        required = True,
        help = 'configuration file name'
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
    parser.add_argument (
        '--output',
        metavar = 'PATH',
        default = '.',
        help = 'Output where plot files are saved.  Default is current directory.'
    )
    return parser.parse_args ()

if __name__ == '__main__':
    main ()
