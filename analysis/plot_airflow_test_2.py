#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import matplotlib
matplotlib.use ('Agg')

import argparse
import datetime
import matplotlib.lines
import matplotlib.pyplot
import os.path
import yaml

import assisipy.casu

import casu_log
import casu_domset_log
import plot_common

def main ():
    args = process_arguments ()
    with open (args.config) as fd:
        config = yaml.safe_load (fd)
    for an_arena in config ['arenas']:
        plot_arena (args.run, an_arena ['core'], an_arena ['leaf'], args.base_path)

def plot_arena (run_number, core_casu_number, leaf_casu_number, base_path):
    print ('[I] Creating plot for arena with core casu {} and leaf casu'.format (core_casu_number, leaf_casu_number))
    casu_numbers = [core_casu_number, leaf_casu_number]
    casu_labels = ['core', 'leaf']
    # read logs
    casu_logs = [
        casu_log.CASU_Log (a_casu_number, os.path.join (base_path, 'data_airflow-test/beearena/'))
        for a_casu_number in casu_numbers
    ]
    core_casu_log, leaf_casu_log = casu_logs
    casu_domset_logs = [
        casu_domset_log.CASU_DOMSET_Log (a_casu_number, os.path.join (base_path, 'data_airflow-test/beearena/'))
        for a_casu_number in casu_numbers
    ]
    all_logs = casu_logs + casu_domset_logs
    number_axes = 3
    # create the figure
    margin_left, margin_right, margin_top, margin_bottom = 0.7, 0.1, 0.5, 0.4
    inter_axes_distance = 0.2
    axes_width, axes_height = 6, 1.8
    figure_width = margin_left + axes_width + margin_right
    figure_height = margin_top + number_axes * axes_height + (number_axes - 1) * inter_axes_distance + margin_bottom
    figure = matplotlib.pyplot.figure (figsize = (figure_width, figure_height))
    # create the axes
    list_axes = [
        figure.add_axes ([
            margin_left / figure_width,
            (margin_bottom + index * (axes_height + inter_axes_distance)) / figure_height,
            axes_width / figure_width,
            axes_height / figure_height])
        for index in range (number_axes)]
    axes_temperature, axes_ir_raw, axes_activity = list_axes
    # setup axes
    axes_temperature.set_ylim (26, 38)
    axes_ir_raw.set_ylim (0, 30000)
    axes_activity.set_ylim (0, 1)
    min_time = min ([a_casu_log.min_time () for a_casu_log in all_logs])
    max_time = min ([a_casu_log.max_time () for a_casu_log in all_logs])
    axes_temperature.set_xlabel ('time (m:ss)', fontsize = 7)
    axes_temperature.set_ylabel (u'temperature (℃)', fontsize = 7)
    axes_ir_raw.set_ylabel ('infrared (a.u.)', fontsize = 7)
    axes_activity.set_ylabel ('sensor activity (a.u.)', fontsize = 7)
    for axa in list_axes:
        axa.set_xlim (min_time, max_time)
        ts = [t for t in range (int (min_time), int (max_time), 60)]
        axa.set_xticks (ts)
        axa.set_xticklabels ([datetime.datetime.fromtimestamp (t - ts [0]).strftime ('%M:%S') for t in ts])
        for ata in [axa.xaxis, axa.yaxis]:
            for tick in ata.get_major_ticks ():
                tick.label.set_fontsize (7)
    # figure properties
    figure.suptitle ('airflow test 2\nrun #{} core casu {} leaf casu {}'.format (run_number, core_casu_number, leaf_casu_number))
    figure.legend (
        handles = [
            matplotlib.lines.Line2D (
                xdata = [0, 1],
                ydata = [1, 0],
                linestyle = 'solid',
                color = c)
            for c in plot_common.COLOURS
        ],
        labels = ['{}{}'.format (l, n) for l, n in zip (casu_labels, casu_numbers)],
        loc = 'upper right',
        fontsize = 7
    )
    # plot
    casu_log_axes_dict = {
        casu_log.IR_RAW : [axes_ir_raw],
        casu_log.TEMP : [axes_temperature],
        casu_log.AIRFLOW : [axes_ir_raw, axes_temperature],
        casu_log.LED : [axes_ir_raw],
    }
    for index, a_casu_log in enumerate (casu_logs):
        a_casu_log.plot (
            index,
            casu_log_axes_dict,
            ir_raw_avg = True,
            avg_temp = False,
            temp_field = [assisipy.casu.TEMP_WAX]
        )
    casu_domset_log_axes_dict = {
        casu_domset_log.CAS : [axes_activity],
        casu_domset_log.CAC : [axes_activity],
        casu_domset_log.NAC : [axes_activity],
        casu_domset_log.CT : [axes_temperature],
        casu_domset_log.NT : [axes_temperature],
        casu_domset_log.CAF : [axes_activity],
    }
    for index, a_casu_domset_log in enumerate (casu_domset_logs):
        a_casu_domset_log.plot (
            index,
            casu_domset_log_axes_dict,
            avg_active_sensors = True
        )
    # final properties
    for axa in list_axes:
        axa.legend (
            fontsize = 5
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
    return parser.parse_args ()

if __name__ == '__main__':
    main ()
