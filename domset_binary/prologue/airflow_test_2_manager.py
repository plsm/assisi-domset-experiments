
import argparse
import os.path
import yaml
import zmq

import assisipy_utils.darc.manager

import airflow_test_1_worker
from domset_binary.util import zmq_sock_utils
import domset_binary.manager.util


class Airflow_Test_Manager (assisipy_utils.darc.manager.DARC_Manager):
    def __init__ (self, airflow_test_config_filename, arena_filename):
        with open (airflow_test_config_filename, 'r') as fd:
            self.atm_config = yaml.safe_load (fd)
        assisipy_utils.darc.manager.DARC_Manager.__init__ (
            self,
            _project = 'airflow-test',
            arena_file_name = arena_filename,
            config_file_name = create_DARC_config_file (
                compute_used_casus (self.atm_config)
            )
        )

    def monitor (self):
        experiment_folder = '.'
        # open connections
        context = zmq.Context ()
        for a in self.atm_config ['arenas']:
            socket = context.socket (zmq.REQ)
            socket.connect (self.worker_address_client_side (a ['core']))
            a ['socket_core'] = socket
            socket = context.socket (zmq.REQ)
            socket.connect (self.worker_address_client_side (a ['leaf']))
            a ['socket_leaf'] = socket
        # wait for all them to initialize
        for a in self.atm_config ['arenas']:
            for sn in ['socket_core', 'socket_leaf']:
                zmq_sock_utils.send_recv (a [sn], [airflow_test_1_worker.INITIALIZE])
        # tell the user to put bees
        print ('Put bees in the arena and press ENTER')
        raw_input ('> ')
        # record video
        number_frames = self.atm_config ['video']['frames_per_second'] * (self.atm_config ['parameters']['first_period_length'] + self.atm_config ['parameters']['airflow_duration'] + self.atm_config ['parameters']['third_period_length'])
        process_recording = domset_binary.manager.util.record_video_gstreamer (
            os.path.join (experiment_folder, 'video.avi'),
            number_frames,
            self.atm_config ['video']['frames_per_second'],
            self.atm_config ['video']['crop_left'],
            self.atm_config ['video']['crop_right'],
            self.atm_config ['video']['crop_top'],
            self.atm_config ['video']['crop_bottom'])
        # tell each arena to do the temperature profile
        for a in self.atm_config ['arenas']:
            print ('Starting temperature profile for arena with CASUs {} and {}'.format (a ['core'], a ['leaf']))
            self.atm_config['parameters'][0] = airflow_test_1_worker.START_CORE
            zmq_sock_utils.send (a ['socket_core'], self.atm_config ['parameters'])
            self.atm_config['parameters'][0] = airflow_test_1_worker.START_LEAF
            zmq_sock_utils.send (a ['socket_leaf'], self.atm_config ['parameters'])
        for a in self.atm_config ['arenas']:
            print ('Waiting for temperature profile in arena with CASUs {} and {} to finish'.format (a ['core'], a ['leaf']))
            zmq_sock_utils.recv (a ['socket_core'])
            zmq_sock_utils.recv (a ['socket_leaf'])
        # finish
        process_recording.wait ()
        print ('Close the window titled "{} deploy"'.format (self.project))

def compute_used_casus (config):
    result = []
    for a in config ['arenas']:
        result.append (a ['core'])
        result.append (a ['leaf'])
    return result

def check_file (filename):
    if filename [-2:] == 'py':
        return filename
    elif filename [-3:] == 'pyc':
        return filename [:-1]
    else:
        print ('Don t know what to do with {}'.format (filename))
        return None

def create_DARC_config_file (list_casus):
    contents = {
        'controllers': {
            'domset': {
                'main': check_file (airflow_test_1_worker.__file__),
                'extra': [
                    check_file (zmq_sock_utils.__file__)
                ],
                'args': [],
                'results': [],
                'casus': list_casus
            }
        },
        'deploy': {
            'user': 'assisi',
            'prefix': 'domset/airflow_test',
            'args': {
                'add_casu_number': True,
                'add_worker_address': True
            }
        },
        'graph': {
            'node_CASUs': {
            },
        }
    }
    filename = 'airflow-test.darc.config'
    with open (filename, 'w') as fd:
        yaml.dump (contents, fd, default_flow_style = False)
        fd.close ()
    return filename

def main ():
    args = process_arguments ()
    aftm = Airflow_Test_Manager (args.config, args.arena)
    if args.debug == 'create-files':
        aftm.create_files ()
    elif args.debug == 'monitor':
        aftm.monitor ()
    else:
        aftm.create_files ()
        aftm.run ('.')

def process_arguments ():
    parser = argparse.ArgumentParser (
        description = 'Test the effect of airflow and decreasing temperature on a leaf and core CASUs',
        argument_default = None
    )
    parser.add_argument (
        '--config', '-c',
        metavar = 'FILENAME',
        type = str,
        help = 'configuration file to use'
    )
    parser.add_argument (
        '--arena', '-a',
        metavar = 'FILENAME',
        type = str,
        required = True,
        help = 'Filename containing the description of available CASUs and their sockets'
    )
    parser.add_argument (
        '--debug',
        choices = ['create-files', 'monitor'],
        help = 'Debug part of the program'
    )
    return parser.parse_args ()

if __name__ == '__main__':
    main ()
