import matplotlib
if __name__ == '__main__':
    matplotlib.use ('Agg')

import argparse
import csv
import matplotlib.pyplot
import numpy
import os.path
import re
import sys

import assisipy.casu

import plot_common

CT = 'CT'
CAF = 'CAF'
CAC = 'CAC'
NAC = 'NAC'
CAS = 'CAS'
NT = 'NT'
ZT = 'ZT'
IRT = 'IRT'
TH_HEAT = 'TH_HEAT'
TH_COOL = 'TH_COOL'
TH_MIN = 'TH_MIN'
TH = 'TH'

class CASU_DOMSET_Log:
    def __init__ (self, number, base_path = '.'):
        def convert_row (a_row):
            def convert_field (value):
                if value == 'True':
                    return 1
                elif value == 'False':
                    return 0
                else:
                    try:
                        return int (value)
                    except ValueError:
                        try:
                            return float (value)
                        except ValueError:
                            return value
            return [convert_field (f) for f in a_row]
        self.number = number
        self.casu_temperature = []
        self.casu_airflow_set_point = []
        self.casu_average_activity = []
        self.node_average_activity = []
        self.casu_active_sensors = []
        self.node_temperature_reference = []
        self.zero_time = []
        self.infrared_thresholds = []
        _temperature_threshold_heat = []
        _temperature_threshold_cool = []
        _temperature_threshold_min = []
        self.__data_dicts = {
            CT: self.casu_temperature,
            CAF: self.casu_airflow_set_point,
            CAC: self.casu_average_activity,
            NAC: self.node_average_activity,
            CAS: self.casu_active_sensors,
            NT: self.node_temperature_reference,
            ZT: self.zero_time,
            IRT: self.infrared_thresholds,
            TH_HEAT: _temperature_threshold_heat,
            TH_COOL: _temperature_threshold_cool,
            TH_MIN: _temperature_threshold_min,
        }
        with open (filename (number, base_path)) as fd:
            reader = csv.reader (fd, delimiter=';')
            for row in reader:
                try:
                    self.__data_dicts [row [0]].append (convert_row (row [1:]))
                except KeyError:
                    print ('[E] Unknown CASU DOMSET log data: {}'.format (row))
                    sys.exit (1)
        self.temperature_threshold_heat = numpy.array (_temperature_threshold_heat)
        self.temperature_threshold_cool = numpy.array (_temperature_threshold_cool)
        self.temperature_threshold_min = numpy.array (_temperature_threshold_min)
        self.__data_dicts [TH_HEAT] = self.temperature_threshold_heat
        self.__data_dicts [TH_COOL] = self.temperature_threshold_cool
        self.__data_dicts [TH_MIN] = self.temperature_threshold_min

    def plot (self, index, dict_axes, **args):
        '''
        Plot CASU DOMSET log data in the provided axes.

        Parameter `index` is a number starting from zero used to compute a colour for the plot.

        Parameter `dict_axes` is a dictionary of integers to a list of axes.
        For each CASU DOMSET log data there is a unique integer.

        To plot casu temperature use the value `CT`.

        To plot casu airflow set point use the value 'CAF`.

        To plot casu average activity use the value `CAC`.

        To plot node average activity use the value `NAC`.

        To plot casu active sensors use the value `CAS`.
        If the argument `avg_active_sensor` is True, then the average is displayed.
        If the argument `list_active_sensors` is provided and contains any of the constants `assisipy.casu.IR_xxx` constants, then the corresponding active sensor value is displayed.

        To plot node temperature use the value `NT`.

        To plot casu thresholds use the value `TH`.

        Usage examples:

        `
        cdl = casu_domset_log.CASU_DOMSET_Log (1)
        cdl.plot (
            index = 0,
            dict_axes = {
               casu_domset_log.TH : [axes],
            }
        )
        `
        '''
        if CT in dict_axes:
            self.__plot_casu_temperature (index, dict_axes [CT])
        if CAF in dict_axes:
            self.__plot_casu_airflow_set_point (index, dict_axes [CAF])
        if CAC in dict_axes:
            self.__plot_casu_average_activity (index, dict_axes [CAC])
        if NAC in dict_axes:
            self.__plot_node_average_activity (index, dict_axes [NAC])
        if CAS in dict_axes:
            self.__plot_casu_active_sensors (index, dict_axes [CAS], **args)
        if NT in dict_axes:
            self.__plot_node_temperature (index, dict_axes [NT])
        if TH in dict_axes:
            self.__plot_temperature_thresholds (index, dict_axes [TH])

    def __plot_casu_temperature (self, index, list_axes):
        self.__print_info (list_axes, self.casu_temperature, 'casu temperature')
        xs = [r [0] for r in self.casu_temperature]
        ys = [r [1] for r in self.casu_temperature]
        for axa in list_axes:
            axa.plot (
                xs,
                ys,
                '--',
                label = 'CT{:3d}'.format (self.number),
                color = plot_common.COLOURS [index]
            )

    def __plot_casu_airflow_set_point (self, index, list_axes):
        self.__print_info (list_axes, self.casu_airflow_set_point, 'casu airflow set point')
        xs = [r [0] for r in self.casu_airflow_set_point]
        ys = [r [1] for r in self.casu_airflow_set_point]
        for axa in list_axes:
            axa.scatter (
                xs,
                ys,
                s = 0.1,
            )

    def __plot_casu_average_activity (self, index, list_axes):
        self.__print_info (list_axes, self.casu_average_activity, 'casu average activity')
        xs = [r [0] for r in self.casu_average_activity]
        ys = [r [1] for r in self.casu_average_activity]
        for axa in list_axes:
            axa.plot (
                xs,
                ys,
                '--',
                label = 'CAC{:3d}'.format (self.number),
                color = plot_common.COLOURS [index]
            )

    def __plot_node_average_activity (self, index, list_axes):
        self.__print_info (list_axes, self.node_average_activity, 'node average activity')
        xs = [r [0] for r in self.node_average_activity]
        ys = [r [1] for r in self.node_average_activity]
        for axa in list_axes:
            axa.scatter (
                xs,
                ys,
                label = 'NAC{:3d}'.format (self.number),
                c = plot_common.COLOURS [index]
            )

    def __plot_casu_active_sensors (self, index, list_axes, **args):
        avg_active_sensors = args.get ('avg_active_sensors', True)
        list_active_sensors = args.get ('list_active_sensors', [])
        if avg_active_sensors or len (list_active_sensors) > 0:
            self.__print_info (list_axes, self.casu_active_sensors, 'casu active sensors')
        if avg_active_sensors:
            xs = [r [0] for r in self.casu_active_sensors]
            ys = [sum (r [1:]) / float (len (r) - 1) for r in self.casu_active_sensors]
            for axa in list_axes:
                axa.plot (
                    xs,
                    ys,
                    ':',
                    label = 'CAS{:3d}'.format (self.number),
                    color = plot_common.COLOURS [index]
                )
        for infrared_field in [assisipy.casu.IR_B, assisipy.casu.IR_BL, assisipy.casu.IR_BR, assisipy.casu.IR_F, assisipy.casu.IR_FL, assisipy.casu.IR_FR]:
            if infrared_field in list_active_sensors:
                xs = [r [0] for r in self.casu_active_sensors]
                ys = [r [1 + assisipy.casu.IR_F - infrared_field] for r in self.casu_active_sensors]
                for axa in list_axes:
                    axa.scatter (
                        xs,
                        ys,
                        c = plot_common.COLOURS [index]
                    )

    def __plot_node_temperature (self, index, list_axes):
        self.__print_info (list_axes, self.node_temperature_reference, 'node temperature reference')
        xs = [r [0] for r in self.node_temperature_reference]
        ys = [r [1] for r in self.node_temperature_reference]
        for axa in list_axes:
            axa.plot (
                xs,
                ys,
                ':',
                label = 'NT{:3d}'.format (self.number),
                color = plot_common.COLOURS [index]
            )

    def __plot_temperature_thresholds (self, index, list_axes):
        for th, st, lb in zip (
                [self.temperature_threshold_cool, self.temperature_threshold_heat, self.temperature_threshold_min],
                [':', '--', '-.'],
                ['C', 'H', 'M']):
            xs = th [:, 0]
            ys = th [:, 1]
            for axa in list_axes:
                axa.plot (
                    xs,
                    ys,
                    st,
                    label = 'TH{}{:3d}'.format (lb, self.number),
                    color = plot_common.COLOURS [index]
                )

    def min_time (self):
        return min ([
            min ([
                row [0]
                for row in data
            ])
            for data in self.__data_dicts.values ()
            if len (data) > 0
        ])

    def max_time (self):
        return min ([
            max ([
                row [0]
                for row in data
            ])
            for data in self.__data_dicts.values ()
            if len (data) > 0
        ])

    def __print_info (self, list_axes, data, description):
        if len (list_axes) > 0 and len (data) == 0:
            print ('[W] No {} data to plot for casu {}!'.format (description, self.number))

def filename (number, base_path = '.'):
        filename_pattern = '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-casu-' + '{:03d}'.format (number) + '-domset[.]csv$'
        filename_regular_expression = re.compile (filename_pattern)
        fsf = os.path.join (base_path, 'casu-{:03d}'.format (number))
        print ('[II] Searching files in folder {}'.format (fsf))
        result = None
        for af in os.listdir (fsf):
            if filename_regular_expression.match (af):
                if result is None:
                    result = af
                else:
                    print ('[E] There are multiple CASU DOMSET logs in folder {}'.format (fsf))
                    sys.exit (1)
        if result is None:
            print ('[E] There is no CASU DOMSET log in folder {}'.format (fsf))
            sys.exit (1)
        return os.path.join (fsf, result)

def main ():
    parser = argparse.ArgumentParser (
        description = 'Test CASU DOMSET logs'
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
    args = parser.parse_args ()
    cl = CASU_DOMSET_Log (args.number, args.base_path)
    figure = matplotlib.pyplot.figure ()
    number_axes = 3
    axes = [figure.add_axes ([0.05, i / float (number_axes) + 0.05, 0.9, (1.0 / number_axes - 0.05)]) for i in range (number_axes)]
    dict_axes = {
        CT : [axes [0]],
        CAF : [axes [1]],
        CAC : [axes [2]],
        NAC : [axes [2]],
        CAS : [axes [2]],
        NT : [axes [0]],
    }
    cl.plot (0, dict_axes, avg_active_sensors = True)
    figure.savefig ('plot-casu-{:03d}.png'.format (args.number))

if __name__ == '__main__':
    main ()
