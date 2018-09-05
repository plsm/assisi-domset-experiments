#!/usr/bin/env python
# -*- coding: utf-8 -*-

# analyse bee visitation for different graph layouts.

# We use stadium arenas that have two CASUs inside.  For each pair of CASUs we
# take the infrared reading for both CASUs.  We create a CSV file with the
# following data:
#
# - lowest casu number
# - highest casu number
# - time
# - bee activity around casu with lowest number
# - bee activity around casu with highest number
# - raw infrared readings of CASU with lowest number
# - raw infrared readings of CASU with lowest number

import matplotlib
matplotlib.use ("Agg")

import argparse
import csv
import datetime
import numpy
import os
import os.path
import yaml

import assisipy.casu

import casu_log
import util.math

def main ():
    args = process_arguments ()
    if not args.update_bee_visitation_plot:
        with open ('bee-visitation.csv', 'w') as fdw:
            bee_visitation_writer = csv.writer (
                fdw,
                delimiter = ';', quoting = csv.QUOTE_NONNUMERIC)
            header_row = [
                'casu_A',
                'casu_B',
                'time',
                'bee_activity_A',
                'bee_activity_B',
                ]
            bee_visitation_writer.writerow (header_row)
            for config_filename in args.config:
                process_run (
                    base_path = args.base_path,
                    output_path = args.output,
                    config_filename = config_filename,
                    bee_visitation_writer = bee_visitation_writer,
                )
    plot_bee_visitation (
        output_path = args.output,
    )

def process_run (base_path, output_path, config_filename, bee_visitation_writer):
    fn = os.path.join (base_path, config_filename)
    with open (fn) as fd:
        config_data = yaml.safe_load (fd)
    for an_arena in config_data ['arenas']:
        process_arena (
            output_path = output_path,
            config_filename = config_filename,
            bee_visitation_writer = bee_visitation_writer,
            experiment_duration = config_data ['parameters']['experiment_duration'],
            casu_A_number = an_arena ['A'],
            casu_B_number = an_arena ['B'],
        )

def process_arena (output_path, config_filename, bee_visitation_writer, experiment_duration, casu_A_number, casu_B_number):
    casu_numbers = [min (casu_A_number, casu_B_number), max (casu_A_number, casu_B_number)]
    base_path = os.path.dirname (config_filename)
    # read logs
    casu_logs = {
        a_casu_number : casu_log.CASU_Log (
            a_casu_number,
            os.path.join (base_path, 'data_infrared-test/beearena/')
        )
        for a_casu_number in casu_numbers
    }
    zero_time = numpy.mean ([
        a_casu_log.led_actuator [0, 0]
        for a_casu_log in casu_logs.values ()
    ])
    # compute infrared data
    build_bee_visitation_CSV_file (
        bee_visitation_writer = bee_visitation_writer,
        experiment_duration = experiment_duration,
        casu_numbers = casu_numbers,
        casu_logs = casu_logs,
        zero_time = zero_time,
    )
    # create plot
    plot_arena (
        output_path = output_path,
        config_filename = config_filename,
        experiment_duration = experiment_duration,
        casu_numbers = casu_numbers,
        casu_logs = casu_logs,
        zero_time = zero_time,
        )

def plot_arena (output_path, config_filename, experiment_duration, casu_numbers, casu_logs, zero_time):
    print ('[I] Creating plot for arena with casus {} and {}'.format (casu_numbers [0], casu_numbers [1]))
    figure_width, figure_height = 14, 9
    figure = matplotlib.pyplot.figure (figsize = (figure_width, figure_height))
    margin_left, margin_right  = 0.75, 0.1
    margin_bottom, margin_top = 0.6, 0.75
    axes = figure.subplots (
        nrows = 3,
        ncols = 2,
        gridspec_kw = {
            'width_ratios' : [2, 2],
            'right' : 1 - margin_right / figure_width,
            'left' : margin_left / figure_width,
            'top' : 1 - margin_top / figure_height,
            'bottom' : margin_bottom / figure_height,
            'wspace' : 0.05
        },
        sharex = True,
        sharey = 'row',
    )
    axes [0, 0].set_ylim (0, 40000)
    axes [0, 0].set_ylabel ('infrared raw (a.u.)', fontsize = 7)
    axes [1, 0].set_ylim (-0.03, 1.03)
    axes [1, 0].set_ylabel ('computed\nbee activity (a.u.)', fontsize = 7)
    axes [2, 0].set_ylim (25.87, 36.13)
    axes [2, 0].set_ylabel (u'temperature (℃)', fontsize = 7)
    for index, a_casu_number in enumerate (casu_numbers):
        axes_dict = {
            casu_log.IR_RAW : [axes [0, index]],
            casu_log.ACTIVITY : [axes [1, index]],
            casu_log.LED : axes [:, index],
            casu_log.TEMP : [axes [2, index]],
        }
        casu_logs [a_casu_number].plot (
            index,
            axes_dict,
            ir_raw_avg = True,
            avg_temp = False,
            temp_field = [assisipy.casu.TEMP_WAX],
        )
    # setup axes
    ts = [t + zero_time for t in range (0, experiment_duration * 60, 45)]
    for axa in [axes [2, 0], axes [2, 1]]:
        axa.set_xlabel ('time (mm:ss)', fontsize = 7)
        axa.set_xticks (ts)
        axa.set_xticklabels ([datetime.datetime.fromtimestamp (t - ts [0]).strftime ('%M:%S') for t in ts])
        for ata in [axa.xaxis, axa.yaxis]:
            for tick in ata.get_major_ticks ():
                tick.label.set_fontsize (7)
    for axa in [axes [i, j] for i in range (2) for j in range (2)]:
        axa.legend (fontsize = 7)
        for ata in [axa.xaxis, axa.yaxis]:
            for tick in ata.get_major_ticks ():
                tick.label.set_fontsize (7)
    label = config_filename.replace ('/', '_')
    figure.suptitle ('infrared test\nrun {} casus {} and {}'.format (label, casu_numbers [0], casu_numbers [1]), fontsize = 9)
    figure.savefig (
        os.path.join (
            output_path,
            'casu-log_L{}-C{}-C{}.png'.format (label, casu_numbers [0], casu_numbers [1])))
    matplotlib.pyplot.close (figure)

def build_bee_visitation_CSV_file (bee_visitation_writer, experiment_duration, casu_logs, casu_numbers, zero_time):
    zero_time = numpy.mean ([
        a_casu_log.led_actuator [2, 0]
        for a_casu_log in casu_logs.values ()
    ])
    sampling_times = [
        zero_time + t
        for t in range (0, experiment_duration * 60)
    ]
    indexes = {}
    for a_casu_number, a_casu_log in casu_logs.iteritems ():
        a_casu_log.compute_activity (
            start_index = 0,
            end_index = 50,
            offset = 500,
            moving_average_length = 61,
        )
        indexes [a_casu_number] = [
            util.math.find_nearest_index (
                a_casu_log.infrared_raw [:, 0],
                a_time)
            for a_time in sampling_times
        ]
    for a_time, index_A, index_B in zip (
        sampling_times,
        indexes [casu_numbers [0]], indexes [casu_numbers [1]]):
        row = [
            casu_numbers [0],
            casu_numbers [1],
            a_time,
            casu_logs [casu_numbers [0]].moving_average_hits [index_A],
            casu_logs [casu_numbers [1]].moving_average_hits [index_B],
            ]
        bee_visitation_writer.writerow (row)

def plot_bee_visitation (output_path):
    # initialise plot
    figure_width, figure_height = 14, 9
    figure = matplotlib.pyplot.figure (figsize = (figure_width, figure_height))
    margin_left, margin_right  = 0.75, 0.1
    margin_bottom, margin_top = 0.6, 0.75
    axes = figure.subplots (
        nrows = 1,
        ncols = 1,
        gridspec_kw = {
            'right' : 1 - margin_right / figure_width,
            'left' : margin_left / figure_width,
            'top' : 1 - margin_top / figure_height,
            'bottom' : margin_bottom / figure_height,
        },
    )
    # read data
    fdr = open ('bee-visitation.csv', 'r')
    reader = csv.reader (
        fdr,
        delimiter = ';',
        quoting = csv.QUOTE_NONNUMERIC)
    reader.next ()
    data = numpy.array ([row for row in reader])
    print (data)
    casu_pairs = numpy.unique (
        data [:, 0:2],
        axis = 0)
    print (casu_pairs)
    # create box plot
    data_to_plot = []
    for a_casu_pair in casu_pairs:
        condition = data [:, 0:2] == a_casu_pair
        condition = condition [:, 0]
        for index in [3, 4]:
            data_to_analyse = numpy.extract (condition, data [:, index])
            print (data_to_analyse)
            data_to_plot.append (data_to_analyse)
    axes.boxplot (
        x = data_to_plot,
        positions = [
            ith + (0.2 if ith % 2 == 0 else -0.2)
            for ith in range (2 * len (casu_pairs))],
        labels = [
            int (cn)
            for a_casu_pair in casu_pairs
            for cn in a_casu_pair]
        )
    axes.set_xlabel ('arena casus', fontsize = 7)
    axes.set_ylim (-0.03, 1.03)
    axes.set_ylabel ('computed\nbee activity (a.u.)', fontsize = 7)
    figure.suptitle ('infrared test\nbee visitation', fontsize = 9)
    figure.savefig (
        os.path.join (
            output_path,
            'bee-visitation.png'))
    matplotlib.pyplot.close (figure)

def process_arguments ():
    parser = argparse.ArgumentParser (
        description = 'Analyse the results of infra red test'
        )
    parser.add_argument (
        '--base-path',
        metavar = 'PATH',
        type = str,
        default = '.',
        help = 'path where the experiment data files are stored'
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
        '--update-bee-visitation-plot',
        action = 'store_true',
        help = 'only update the bee visitation plot'
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
