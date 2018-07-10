import matplotlib
if __name__ == '__main__':
    matplotlib.use ('Agg')

import argparse
import csv
import matplotlib.patches
import matplotlib.pyplot
import numpy
import os.path
import re
import sys

import assisipy.casu

import plot_common
import util.math

IR_RAW = 'ir_raw'
TEMP = 'temp'
PELTIER = 'Peltier'
AIRFLOW = 'Airflow'
LED = 'DiagnosticLed'
ACTIVITY = 'activity'

class CASU_Log:
    
    def __init__ (self, number, base_path = '.'):
        def convert_row (a_row):
            def convert_field (value):
                try:
                    return int (value)
                except ValueError:
                    try:
                        return float (value)
                    except ValueError:
                        return value
            return [convert_field (f) for f in a_row]
        # initialise fields
        self.number = number
        self.infrared_raw = []
        self.temperature = []
        self.peltier = []
        self.airflow = []
        self.led = []
        self.activity = None
        self.hits = None
        self.moving_average_hits = None
        self.__data_dicts = {
            IR_RAW : self.infrared_raw,
            TEMP : self.temperature,
            PELTIER : self.peltier,
            AIRFLOW : self.airflow,
            LED : self.led,
        }
        # read CASU log
        skipped = {}
        with open (filename (number, base_path)) as fd:
            reader = csv.reader (fd, delimiter = ';', quoting = csv.QUOTE_NONE)
            for row in reader:
                try:
                    self.__data_dicts [row [0]].append (convert_row (row [1:]))
                except KeyError:
                    skipped [row [0]] = True
        if len (skipped.keys ()) > 0:
            print ('[I] skipped data {}'.format (skipped.keys ()))
        # convert to numpy arrays
        self.infrared_raw = numpy.array (self.infrared_raw)
        self.__data_dicts [IR_RAW] = self.infrared_raw

    def plot (self, index, dict_axes, **args):
        if IR_RAW in dict_axes:
            self.__plot_sensor_infrared_raw (index, dict_axes [IR_RAW], **args)
        if TEMP in dict_axes:
            self.__plot_sensor_temperature (index, dict_axes [TEMP], **args)
        if PELTIER in dict_axes:
            self.__plot_setpoint_peltier (index, dict_axes [PELTIER], **args)
        if AIRFLOW in dict_axes:
            self.__plot_setpoint_airflow (index, dict_axes [AIRFLOW], **args)
        if LED in dict_axes:
            self.__plot_setpoint_led (index, dict_axes [LED], **args)
        if ACTIVITY in dict_axes:
            self.__plot_moving_average_hits (index, dict_axes [ACTIVITY])

    def __plot_sensor_infrared_raw (self, index, list_axes, **args):
        if args.get ('ir_raw_avg', True):
            self.__print_info (list_axes, self.infrared_raw, 'infrared raw')
        if args.get ('ir_raw_avg', True):
            xs = self.infrared_raw [:,0]
            ys = self.infrared_raw [:,1:].mean (axis = 1)
            for axa in list_axes:
                axa.plot (
                    xs,
                    ys,
                    '-',
                    label = 'IR{:3d}'.format (self.number),
                    color = plot_common.COLOURS [index]
                )

    def __plot_sensor_temperature (self, index, list_axes, **args):
        if args.get ('avg_temp', True) or len (args.get ('temp_field', [])) > 0:
            self.__print_info (list_axes, self.temperature, 'temperature')
        if args.get ('avg_temp', True):
            xs = [r [0] for r in self.temperature]
            ys = [sum (r [1:]) / float (len (r) - 1) for r in self.temperature]
            for axa in list_axes:
                axa.scatter (
                    xs,
                    ys,
                    c = plot_common.COLOURS [index]
                )
        for temperature_field in [assisipy.casu.TEMP_F, assisipy.casu.TEMP_L, assisipy.casu.TEMP_B, assisipy.casu.TEMP_R, assisipy.casu.TEMP_TOP, assisipy.casu.TEMP_PCB, assisipy.casu.TEMP_RING, assisipy.casu.TEMP_WAX]:
            if temperature_field in args.get ('temp_field', []):
                xs = [r [0] for r in self.temperature]
                ys = [r [1 + assisipy.casu.TEMP_F - temperature_field] for r in self.temperature]
                for axa in list_axes:
                    axa.scatter (
                        xs,
                        ys,
                        c = plot_common.COLOURS [index]
                    )
                    
    def __plot_setpoint_peltier (self, index, list_axes, **args):
        self.__print_info (list_axes, self.peltier, 'peltier')
        if args.get ('peltier', True):
            xs = [r [0] for r in self.peltier]
            ys = [r [1] * r [2] for r in self.peltier]
            for axa in list_axes:
                axa.plot (
                    xs,
                    ys,
                    '-',
                    label = 'peltier{:3d}'.format (self.number),
                    color = plot_common.COLOURS [index]
                )

    def __plot_setpoint_airflow (self, index, list_axes, **args):
        self.__print_info (list_axes, self.airflow, 'airflow')
        ith = 0
        last_time_airflow_on = None
        while ith < len (self.airflow):
            row = self.airflow [ith]
            if row [1] == 0:
                if last_time_airflow_on is not None:
                    for axa in list_axes:
                        ylim = axa.get_ylim ()
                        rect = matplotlib.patches.Rectangle (
                            xy = [last_time_airflow_on, ylim [0]],
                            width = row [0] - last_time_airflow_on,
                            height = ylim [1] - ylim [0],
                            color = '#{:02X}DDFF7F'.format (index)
                        )
                        axa.add_patch (rect)
                last_time_airflow_on = None
            elif row [1] == 1 and last_time_airflow_on is None:
                last_time_airflow_on = row [0]
            ith += 1

    def __plot_setpoint_led (self, index, list_axes, **args):
        def __draw ():
            for axa in list_axes:
                ylim = axa.get_ylim ()
                rect = matplotlib.patches.Rectangle (
                    xy = [last_time_led_on, ylim [1] - (index + 1) * (ylim [1] - ylim [0]) / 10],
                    width = row [0] - last_time_led_on,
                    height = (ylim [1] - ylim [0]) / 10,
                    color = '#{:02X}{:02X}{:02X}7F'.format (int (255 * last_led_color [0]), int (255 * last_led_color [2]), int (255 * last_led_color [2]))
                )
                axa.add_patch (rect)
        self.__print_info (list_axes, self.led, "led")
        ith = 0
        last_time_led_on = None
        last_led_color = None
        while ith < len (self.led):
            row = self.led [ith]
            if row [1] == 1 and last_time_led_on is not None and any ([now != then for now, then in zip (row [2:5], last_led_color)]):
                __draw ()
                last_time_led_on = row [0]
                last_led_color = row [2:5]
            elif row [1] == 0 or (row [2] == 0 and row [3] == 0 and row [4] == 0):
                if last_time_led_on is not None:
                    __draw ()
                last_time_led_on = None
            elif row [1] == 1 and last_time_led_on is None:
                last_time_led_on = row [0]
                last_led_color = row [2:5]
            ith += 1

    def __plot_moving_average_hits (self, index, list_axes):
        xs = self.infrared_raw [:, 0]
        ys = self.moving_average_hits [:]
        for axa in list_axes:
            axa.plot (
                xs,
                ys,
                '-',
                label = 'mah{:3d}'.format (self.number),
                color = plot_common.COLOURS [index]
            )

    def min_time (self):
        return min ([
            min ([
                row [0]
                for row in data
            ])
            for data in self.__data_dicts.values ()
        ])

    def max_time (self):
        return min ([
            max ([
                row [0]
                for row in data
            ])
            for data in self.__data_dicts.values ()
        ])

    def compute_activity (self, start_index, end_index, offset, moving_average_length):
        """
        Compute the infrared sensor activity.  This assumes that during the period start_time to end_time there are no bees.
        :param offset:
        :param moving_average_length:
        :param start_index:
        :param end_index:
        :return:
        """
        thresholds = self.infrared_raw [start_index:end_index, 1:].max (axis = 0)
        thresholds = thresholds + offset
        number_sensors = self.infrared_raw.shape [1] - 1
        self.activity =  self.infrared_raw [:, 1:] > thresholds
        self.hits = self.activity.sum (axis = 1)
        self.moving_average_hits = util.math.moving_average (self.hits, moving_average_length) / float (number_sensors)

    def __print_info (self, list_axes, data, description):
        if len (list_axes) > 0 and len (data) == 0:
            print ('[W] No {} in log data to plot for casu {}!'.format (description, self.number))

def filename (number, base_path = '.'):
        filename_pattern = '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-casu-' + '{:03d}'.format (number) + '[.]csv$'
        filename_regular_expression = re.compile (filename_pattern)
        fsf = os.path.join (base_path, 'casu-{:03d}'.format (number))
        print ('[II] Searching files in folder {}'.format (fsf))
        result = None
        for af in os.listdir (fsf):
            if filename_regular_expression.match (af):
                if result is None:
                    result = af
                else:
                    print ('[E] There are multiple CASU logs in folder {}'.format (fsf))
                    sys.exit (1)
        if result is None:
            print ('[E] There is no CASU log in folder {}'.format (fsf))
            sys.exit (1)
        return os.path.join (fsf, result)

def main ():
    parser = argparse.ArgumentParser (
        description = 'Test CASU logs'
        )
    parser.add_argument (
        '--number', '-n',
        metavar = 'N',
        required = True,
        type = int,
        help = 'CASU number to plot'
    )
    parser.add_argument (
        '--base-path',
        metavar = 'PATH',
        type = str,
        default = '.',
        help = 'Path where the CASU logs are stored'
    )
    parser.add_argument (
        '--plot-peltier',
        action = 'store_true',
        help = 'Plot peltier setpoint'
    )
    parser.add_argument (
        '--plot-temp-wax',
        action = 'store_true',
        help = 'plot estimated wax temperature'
    )
    args = parser.parse_args ()
    cl = CASU_Log (args.number, args.base_path)
    plot_args = {}
    plot_args ['peltier'] = args.plot_peltier
    plot_args ['temp_field'] = []
    if args.plot_temp_wax: plot_args ['temp_field'].append (assisipy.casu.TEMP_WAX)
    figure = matplotlib.pyplot.figure ()
    number_axes = 3
    axes_list = [figure.add_axes ([0.05, i / float (number_axes) + 0.05, 0.9, (1.0 / number_axes - 0.05)]) for i in range (number_axes)]
    axes_dict = {
        IR_RAW : [axes_list [0]],
        TEMP : [axes_list [1]],
        PELTIER : [axes_list [2]]}
    cl.plot (0, axes_dict, **plot_args)
    figure.savefig ('plot-casu-{:03d}.png'.format (args.number))
    cl.compute_activity (0, 50, 500)

if __name__ == '__main__':
    main ()
