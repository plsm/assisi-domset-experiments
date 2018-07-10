#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import datetime
import matplotlib.pyplot
import os.path
import yaml

import assisipy.casu

import casu_log

def main ():
    args = process_arguments ()
    with open (args.config) as fd:
        config = yaml.safe_load (fd)
    for an_arena in config ['arenas']:
        plot_arena (args.run, an_arena ['core'], an_arena ['leaf'], args.base_path, args.moving_average_length)

def plot_arena (run_number, core_casu_number, leaf_casu_number, base_path, moving_average_length):
    print ('[I] Creating plot for arena with core casu {} and leaf casu'.format (core_casu_number, leaf_casu_number))
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
    core_casu_log, leaf_casu_log = casu_logs
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
        type = int,
        required = True,
        help = 'run number'
    )
    parser.add_argument (
        '--moving-average-length',
        metavar = 'L',
        type = int,
        default = 61,
        help = 'Moving average length used when computing the moving average of infrared sensor hits'
    )
    return parser.parse_args ()

if __name__ == '__main__':
    main ()
