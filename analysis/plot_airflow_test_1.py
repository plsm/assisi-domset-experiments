#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import csv
import datetime
import matplotlib.pyplot
import numpy
import os.path
import yaml

import assisipy.casu

import casu_log
import util.math

def main ():
    args = process_arguments ()
    filename = 'bee-where-about_L={}_D={}.csv'.format (args.sampling_length, args.sampling_delta)
    if not args.update_bee_where_abouts_plot:
        fdw = open (filename, 'w')
        bee_where_about_writer = csv.writer (fdw, delimiter = ';', quoting = csv.QUOTE_NONNUMERIC)
        for run_number in args.run:
            process_run (
                run_number = run_number,
                base_path = os.path.join (args.base_path, args.run_folder_template.format (run_number)),
                config_filename = args.config,
                bee_where_about_writer = bee_where_about_writer,
                moving_average_length = args.moving_average_length,
                sampling_length = args.sampling_length,
                sampling_delta = args.sampling_delta,
            )
        fdw.close ()
    plot_bee_where_abouts (
        filename,
        sampling_length = args.sampling_length,
        sampling_delta = args.sampling_delta,
    )

def process_run (run_number, base_path, config_filename, bee_where_about_writer, moving_average_length, sampling_length, sampling_delta):
    fn = os.path.join (base_path, config_filename)
    with open (fn) as fd:
        config_data = yaml.safe_load (fd)
    for an_arena in config_data ['arenas']:
        process_arena (
            run_number = run_number,
            core_casu_number = an_arena ['core'],
            leaf_casu_number = an_arena ['leaf'],
            base_path = base_path,
            moving_average_length = moving_average_length,
            first_period_length = config_data ['parameters'] ['first_period_length'],
            third_period_length = config_data ['parameters'] ['third_period_length'],
            sampling_length = sampling_length,
            sampling_delta = sampling_delta,
            bee_where_about_writer = bee_where_about_writer
        )

def process_arena (run_number, core_casu_number, leaf_casu_number, base_path, moving_average_length, first_period_length, third_period_length, sampling_length, sampling_delta, bee_where_about_writer):
    # read logs
    casu_logs = [
        casu_log.CASU_Log (a_casu_number, os.path.join (base_path, 'data_airflow-test/beearena/'))
        for a_casu_number in [core_casu_number, leaf_casu_number]]
    for a_casu_log in casu_logs:
        a_casu_log.compute_activity (
            start_index = 0,
            end_index = 50,
            offset = 500,
            moving_average_length = moving_average_length
        )
    plot_arena (run_number, core_casu_number, leaf_casu_number, casu_logs)
    core_casu_log, leaf_casu_log = casu_logs
    compute_bee_where_about (run_number, casu_logs, core_casu_log, first_period_length, third_period_length, sampling_length, sampling_delta, bee_where_about_writer)

def plot_arena (run_number, core_casu_number, leaf_casu_number, casu_logs):
    print ('[I] Creating plot for arena with core casu {} and leaf casu'.format (core_casu_number, leaf_casu_number))
    number_axes = 3
    # create the figure
    margin_left, margin_right, margin_top, margin_bottom = 0.7, 0.1, 0.5, 0.4
    inter_axes_distance = 0.2
    axes_width, axes_height = 6, 1.8
    figure_width = margin_left + axes_width + margin_right
    figure_height = margin_top + number_axes * axes_height + (number_axes - 1) * inter_axes_distance + margin_bottom
    figure = matplotlib.pyplot.figure (figsize = (figure_width, figure_height))
    # create the axes
    axes_activity, axes_temperature, axes_ir_raw = [
        figure.add_axes ([
            margin_left / figure_width,
            (margin_bottom + index * (axes_height + inter_axes_distance)) / figure_height,
            axes_width / figure_width,
            axes_height / figure_height])
        for index in range (number_axes)]
    # setup axes
    axes_temperature.set_ylim (26, 38)
    axes_ir_raw.set_ylim (0, 30000)
    min_time = min ([a_casu_log.min_time () for a_casu_log in casu_logs])
    max_time = min ([a_casu_log.max_time () for a_casu_log in casu_logs])
    axes_temperature.set_xlim (min_time, max_time)
    axes_ir_raw.set_xlim (min_time, max_time)
    axes_temperature.set_xlabel ('time (m:ss)', fontsize = 7)
    axes_temperature.set_ylabel (u'temperature (℃)', fontsize = 7)
    axes_ir_raw.set_ylabel ('infrared (a.u.)', fontsize = 7)
    axes_activity.set_ylim (-0.035, 1.035)
    axes_activity.set_ylabel ('sensor activity (a.u.)', fontsize = 7)
    for axa in [axes_temperature, axes_ir_raw, axes_activity]:
        axa.set_xlim (min_time, max_time)
        ts = [t for t in range (int (min_time), int (max_time), 60)]
        axa.set_xticks (ts)
        axa.set_xticklabels ([datetime.datetime.fromtimestamp (t - ts [0]).strftime ('%M:%S') for t in ts])
        for ata in [axa.xaxis, axa.yaxis]:
            for tick in ata.get_major_ticks ():
                tick.label.set_fontsize (7)
    # figure properties
    figure.suptitle ('airflow test 1\nrun #{} core casu {} leaf casu {}'.format (run_number, core_casu_number, leaf_casu_number))
    # plot
    axes_dict = {
        casu_log.IR_RAW : [axes_ir_raw],
        casu_log.TEMP : [axes_temperature],
        casu_log.AIRFLOW : [axes_ir_raw, axes_temperature, axes_activity],
        casu_log.LED : [axes_ir_raw],
        casu_log.ACTIVITY : [axes_activity],
    }
    for index, a_casu_log in enumerate (casu_logs):
        a_casu_log.plot (
            index,
            axes_dict,
            ir_raw_avg = True,
            avg_temp = False,
            temp_field = [assisipy.casu.TEMP_WAX]
        )
    # save figure
    figure.savefig ('casu-log_R{}-C{}-L{}.png'.format (run_number, core_casu_number, leaf_casu_number))
    matplotlib.pyplot.close (figure)

def plot_bee_where_abouts (filename, sampling_length, sampling_delta):
    with open (filename, 'r') as fd:
        reader = csv.reader (fd, delimiter = ';', quoting = csv.QUOTE_NONNUMERIC)
        data = numpy.array ([row for row in reader])
    print (data)
    figure_width, figure_height = 8, 4
    figure = matplotlib.pyplot.figure (figsize = (figure_width, figure_height))
    axes = figure.subplots (
        nrows = 1,
        ncols = 2,
        gridspec_kw = {
            'width_ratios' : [2, 1],
            'wspace' : 0.5
        }
    )
    axes [0].boxplot (
        data [:, 3:7],
        labels = ['core\n1st period', 'leaf\n1st period', 'core\n3rd period', 'leaf\n3rd period']
    )
    axes [0].set_ylim (-0.03, 1.03)
    axes [0].set_ylabel ('absolute\nsensor activity (a.u.)')
    axes [1].boxplot (
        data [:, 7:9],
        labels = ['gain\n1st period', 'gain\n3rd period']
    )
    axes [1].set_ylim (-1.03, 1.03)
    axes [1].set_ylabel ('leaf-core\nsensor activity (a.u.)')
    figure.suptitle ('Sensor activity\nlast {}s of first and third period'.format (sampling_length))
    figure.savefig ('bee-where-about_L={}_D={}.png'.format (sampling_length, sampling_delta))

def compute_bee_where_about (run_number, casu_logs, core_casu_log, first_period_length, third_period_length, sampling_length, sampling_delta, writer):
    """
    Compute where the majority of bees are based on sensor activity
    :param sampling_delta:
    :type core_casu_log: casu_log.CASU_Log
    :type casu_logs: list(casu_log.CASU_Log)
    """
    def search_led_on (ith):
        while True:
            if core_casu_log.led [ith, 1] == 1:
                timestamp = core_casu_log.led [ith, 0]
                while core_casu_log.led [ith, 1] == 1:
                    ith += 1
                return timestamp, ith
            ith += 1
    index = 0
    first_period_start_time, index = search_led_on (index)
    _second_period_start_time, index = search_led_on (index)
    third_period_start_time, _index = search_led_on (index)
    sums_activity = {}
    for a_start_time, a_length in zip ([first_period_start_time, third_period_start_time], [first_period_length, third_period_length]):
        sampling_times = [a_start_time + a_length - sampling_delta * ith for ith in range (int (sampling_length / sampling_delta) + 1)]
        sums_activity [a_start_time] = {}
        for index, a_casu_log in enumerate (casu_logs):
            indexes = [util.math.find_nearest_index (a_casu_log.infrared_raw [:,0], a_time) for a_time in sampling_times]
            print ('[I] Computing for run {} casus {} and {} bee where about between relative timestamps {:.2f}% and {:.2f}% or indexes {} and {}'.format (
                run_number,
                casu_logs [0].number,
                casu_logs [1].number,
                100 * (min (sampling_times) - a_casu_log.infrared_raw [:,0].min ()) / (a_casu_log.infrared_raw [:,0].max () - a_casu_log.infrared_raw [:,0].min ()),
                100 * (max (sampling_times) - a_casu_log.infrared_raw [:, 0].min ()) / (
                            a_casu_log.infrared_raw [:, 0].max () - a_casu_log.infrared_raw [:, 0].min ()),
                min (indexes),
                max (indexes)
            ))
            data = [a_casu_log.moving_average_hits [ith] for ith in indexes]
            sums_activity [a_start_time][index] = sum (data) / len (data)
    row = [run_number]
    row.extend ([a_casu_log.number for a_casu_log in casu_logs])
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
        description = 'Test CASU logs'
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
    parser.add_argument (
        '--run-folder-template',
        metavar = 'STRING',
        type = str,
        default = 'run-{}',
        help = 'Template of the run folder.  This is joined to the base path.'
    )
    parser.add_argument (
        '--moving-average-length',
        metavar = 'L',
        type = int,
        default = 61,
        help = 'Moving average length used when computing the moving average of infrared sensor hits'
    )
    parser.add_argument (
        '--sampling-length',
        metavar = 'L',
        type = int,
        default = 60,
        help = 'Duration of the sampling data used when computing bee where abouts in first and third period.  The data are taken in the last L seconds of the first period and third period.'
    )
    parser.add_argument (
        '--sampling-delta',
        metavar = 'D',
        type = int,
        default = 1,
        help = 'Sampling delta used when computing bee where abouts in first and third period'
    )
    parser.add_argument (
        '--update-bee-where-abouts-plot',
        action = 'store_true',
        help = 'only update the bee where abouts plot'
    )
    return parser.parse_args ()

if __name__ == '__main__':
    main ()
