import matplotlib
if __name__ == '__main__':
    matplotlib.use ('Agg')

import argparse
import csv
import matplotlib.pyplot
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
        self.__data_dicts = {
            CT: self.casu_temperature,
            CAF: self.casu_airflow_set_point,
            CAC: self.casu_average_activity,
            NAC: self.node_average_activity,
            CAS: self.casu_active_sensors,
            NT: self.node_temperature_reference
        }
        with open (filename (number, base_path)) as fd:
            reader = csv.reader (fd, delimiter=';')
            for row in reader:
                try:
                    self.__data_dicts [row [0]].append (convert_row (row [1:]))
                except KeyError:
                    print ('[E] Unknown CASU DOMSET log data: {}'.format (row))
                    sys.exit (1)

    def plot (self, index, dict_axes, **args):
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
                ys
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
        temp_field = args.get ('temp_field', [])
        if avg_active_sensors or len (temp_field) > 0:
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
            if infrared_field in temp_field:
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
