#!/usr/bin/env python
# -*- coding: utf-8 -*-

import matplotlib
matplotlib.use ("Agg")

import argparse
import csv
import datetime
import matplotlib.pyplot
import numpy
import os.path
import yaml

import assisipy.casu

import bee_where_abouts
import casu_log
import casu_domset_log
import util.math

def main ():
    args = process_arguments ()
    filename = 'bee-where-about_L={}_D={}.csv'.format (args.sampling_length, args.sampling_delta)
    if not args.update_bee_where_abouts_plot or not os.path.exists (filename):
        fdw = open (filename, 'w')
        bee_where_about_writer = csv.writer (fdw, delimiter = ';', quoting = csv.QUOTE_NONNUMERIC)
        for run_number in args.run:
            process_run (
                run_number = run_number,
                base_path = os.path.join (args.base_path, args.run_folder_template.format (run_number)),
                config_filename = args.config,
                moving_average_length = args.moving_average_length,
                sampling_length = args.sampling_length,
                sampling_delta = args.sampling_delta,
                bee_where_about_writer = bee_where_about_writer,
            )
        fdw.close ()
    bee_where_abouts.plot (
        filename,
        sampling_length = args.sampling_length,
        sampling_delta = args.sampling_delta,
    )

def process_run (run_number, base_path, config_filename,
        moving_average_length,
        sampling_length, sampling_delta, bee_where_about_writer):
    fn = os.path.join (base_path, config_filename)
    with open (fn) as fd:
        config_data = yaml.safe_load (fd)
    for an_arena in config_data ['arenas']:
        process_arena (
            run_number = run_number,
            core_casu_number = an_arena ['core'],
            leaf_casu_number = an_arena ['leaf'],
            base_path = base_path,
            first_period_length = config_data ['parameters'] ['first_period_length'],
            airflow_period_length = config_data ['parameters'] ['airflow_duration'],
            third_period_length = config_data ['parameters'] ['third_period_length'],
            moving_average_length = moving_average_length,
            sampling_length = sampling_length,
            sampling_delta = sampling_delta,
            bee_where_about_writer = bee_where_about_writer,
        )

def process_arena (
        run_number, base_path,
        core_casu_number, leaf_casu_number,
        first_period_length, airflow_period_length, third_period_length,
        moving_average_length,
        sampling_length, sampling_delta, bee_where_about_writer):
    # read logs
    casu_logs = {
        a_casu_number : casu_log.CASU_Log (a_casu_number, os.path.join (base_path, 'data_airflow-test/beearena/'))
        for a_casu_number in [core_casu_number, leaf_casu_number]
    }
    casu_domset_logs = {
        a_casu_number : casu_domset_log.CASU_DOMSET_Log (a_casu_number, os.path.join (base_path, 'data_airflow-test/beearena/'))
        for a_casu_number in [core_casu_number, leaf_casu_number]
    }
    # compute activity (needed by bee where about)
    for a_casu_log in casu_logs.values ():
        a_casu_log.compute_activity (
            start_index = 0,
            end_index = 50,
            offset = 500,
            moving_average_length = moving_average_length
        )
    # create plot
    plot_arena (
        run_number, core_casu_number, leaf_casu_number,
        first_period_length, airflow_period_length, third_period_length,
        casu_logs, casu_domset_logs
    )
    #
    compute_bee_where_about (
        run_number,
        casu_logs,
        first_period_length,
        airflow_period_length,
        third_period_length,
        sampling_length = sampling_length,
        sampling_delta = sampling_delta,
        writer = bee_where_about_writer)

def plot_arena (run_number, core_casu_number, leaf_casu_number,
        first_period_length, airflow_period_length, third_period_length, casu_logs, casu_domset_logs):
    casu_numbers = [core_casu_number, leaf_casu_number]
    print ('[I] Creating plot for arena with core casu {} and leaf casu'.format (core_casu_number, leaf_casu_number))
    figure_width, figure_height = 12, 6
    figure = matplotlib.pyplot.figure (figsize = (figure_width, figure_height))
    axes = figure.subplots (
        nrows = 3,
        ncols = 2,
        gridspec_kw = {
            'width_ratios' : [2, 2],
            'left' : 0.05,
            'right' : 0.99,
#            'wspace' : 0.1
        },
        sharex = 'col',
        sharey = 'row',
    )
    for axa in axes [0,:]:
        axa.set_ylim (25.15, 37.15)
        axa.set_ylabel (u'temperature (℃)', fontsize = 7)
    for axa in axes [1,:]:
        axa.set_ylim (-0.03, 1.03)
        axa.set_ylabel ('node activity (a.u.)', fontsize = 7)
    for axa in axes [2,:]:
        axa.set_ylim (-0.03, 1.03)
        axa.set_ylabel ('thresholds (a.u.)', fontsize = 7)
    for index, a_casu_number in enumerate (casu_numbers):
        axes_dict = {
            casu_log.TEMP : [axes [0,index]],
            casu_log.AIRFLOW : axes [:,index],
            casu_log.LED : axes [:,index],
        }
        casu_logs [a_casu_number].plot (
            index,
            axes_dict,
            ir_raw_avg = True,
            avg_temp = False,
            temp_field = [assisipy.casu.TEMP_WAX]
        )
        axes_dict = {
            casu_domset_log.CAC : [axes [1,index]],
            casu_domset_log.TH : [axes [2,index]],
        }
        casu_domset_logs [a_casu_number].plot (
            index,
            axes_dict,
        )
    # setup axes
    zero_time = numpy.mean ([a_casu_log.led_actuator [2,0] for a_casu_log in casu_logs.values ()])
    ts = [t + zero_time for t in range (0, first_period_length + airflow_period_length + third_period_length, 60)]
    for axa in [axes [2,0], axes [2,1]]:
        axa.set_xlabel ('time (mm:ss)', fontsize = 7)
        axa.set_xticks (ts)
        axa.set_xticklabels ([datetime.datetime.fromtimestamp (t - ts [0]).strftime ('%M:%S') for t in ts])
        for ata in [axa.xaxis, axa.yaxis]:
            for tick in ata.get_major_ticks ():
                tick.label.set_fontsize (7)
    for axa in [axes [i,j] for i in range (3) for j in range (2)]:
        axa.legend (fontsize = 7)
        for ata in [axa.xaxis, axa.yaxis]:
            for tick in ata.get_major_ticks ():
                tick.label.set_fontsize (7)
    figure.suptitle ('airflow test 4\nrun #{} core casu {} leaf casu {}'.format (run_number, core_casu_number, leaf_casu_number), fontsize = 9)
    figure.savefig ('casu-log_R{}-C{}-L{}.png'.format (run_number, core_casu_number, leaf_casu_number))
    matplotlib.pyplot.close (figure)

def compute_bee_where_about (run_number, casu_logs, first_period_length, airflow_period_length, third_period_length, sampling_length, sampling_delta, writer):
    """
    Compute where the majority of bees are based on sensor activity
    :param sampling_delta:
    :type casu_logs: list(casu_log.CASU_Log)
    """
    first_period_start_time = numpy.mean ([a_casu_log.led_actuator [2, 0] for a_casu_log in casu_logs.values ()])
    second_period_start_time = numpy.mean ([a_casu_log.led_actuator [4, 0] for a_casu_log in casu_logs.values ()])
    third_period_start_time = second_period_start_time + airflow_period_length

    sums_activity = {}
    for a_start_time, a_length in zip ([first_period_start_time, third_period_start_time], [first_period_length, third_period_length]):
        sampling_times = [a_start_time + a_length - sampling_delta * ith for ith in range (int (sampling_length / sampling_delta) + 1)]
        sums_activity [a_start_time] = {}
        for index, a_casu_log in enumerate (casu_logs.values ()):
            indexes = [util.math.find_nearest_index (a_casu_log.infrared_raw [:,0], a_time) for a_time in sampling_times]
            print ('[I] Computing for run {} casus {} and {} bee where about between relative timestamps {:.2f}% and {:.2f}% or indexes {} and {}'.format (
                run_number,
                casu_logs.values () [0].number,
                casu_logs.values () [1].number,
                100 * (min (sampling_times) - a_casu_log.infrared_raw [:, 0].min ()) / (
                    a_casu_log.infrared_raw [:, 0].max () - a_casu_log.infrared_raw [:, 0].min ()),
                100 * (max (sampling_times) - a_casu_log.infrared_raw [:, 0].min ()) / (
                            a_casu_log.infrared_raw [:, 0].max () - a_casu_log.infrared_raw [:, 0].min ()),
                min (indexes),
                max (indexes)
            ))
            data = [a_casu_log.moving_average_hits [ith] for ith in indexes]
            sums_activity [a_start_time][index] = sum (data) / len (data)
    row = [run_number]
    row.extend ([a_casu_log.number for a_casu_log in casu_logs.values ()])
    row.extend ([
        sums_activity [at][ai]
        for at in sums_activity.keys ()
        for ai in sums_activity [at].keys ()])
    row.extend ([
        sums_activity [at][1] - sums_activity [at][0]
        for at in sums_activity.keys ()
    ])
    writer.writerow (row)

def process_arguments ():
    parser = argparse.ArgumentParser (
        description = 'Plot the results of airflow test number 4.'
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
        type = str,
        required = True,
        help = 'configuration file name'
    )
    parser.add_argument (
        '--run', '-r',
        metavar = 'N',
        action = 'append',
        type = int,
        required = True,
        help = 'run number'
    )
    DEFAULT_RUN_FOLDER_TEMPLATE = 'run-{}'
    parser.add_argument (
        '--run-folder-template',
        metavar = 'STRING',
        type = str,
        default = DEFAULT_RUN_FOLDER_TEMPLATE,
        help = 'Template of the run folder.  This is joined to the base path.  Default value is «{}».'.format (DEFAULT_RUN_FOLDER_TEMPLATE)
    )
    DEFAULT_MOVING_AVERAGE_LENGTH = 61
    parser.add_argument (
        '--moving-average-length',
        metavar = 'L',
        type = int,
        default = DEFAULT_MOVING_AVERAGE_LENGTH,
        help = 'Moving average length used when computing the moving average of infrared sensor hits.  Default value is {} seconds.'.format (DEFAULT_MOVING_AVERAGE_LENGTH)
    )
    DEFAULT_SAMPLING_LENGTH = 60
    parser.add_argument (
        '--sampling-length',
        metavar = 'L',
        type = int,
        default = DEFAULT_SAMPLING_LENGTH,
        help = 'Duration of the sampling data used when computing bee where abouts in first and third period.  The data are taken in the last L seconds of the first period and third period.  Default value is {} seconds,'.format (DEFAULT_SAMPLING_LENGTH)
    )
    DEFAULT_SAMPLING_DELTA = 1
    parser.add_argument (
        '--sampling-delta',
        metavar = 'D',
        type = int,
        default = 1,
        help = 'Sampling delta used when computing bee where abouts in first and third period.  Default value is sample every {} second{}'.format (
            DEFAULT_SAMPLING_DELTA,
            '' if DEFAULT_SAMPLING_DELTA == 1 else 's'
        )
    )
    parser.add_argument (
        '--update-bee-where-abouts-plot',
        action = 'store_true',
        help = 'only update the bee where abouts plot'
    )
    parser.add_argument (
        '--output',
        metavar = 'PATH',
        default = '.',
        help = 'Output where plots and csv files are saved.  Default is current directory.'
    )
    return parser.parse_args ()

if __name__ == '__main__':
    main ()
