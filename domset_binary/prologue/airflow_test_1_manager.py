
import argparse
import yaml
import zmq

import assisipy_utils.darc.manager

import airflow_test_1_worker
from domset_binary.util import zmq_sock_utils


class Airflow_Test_Manager (assisipy_utils.darc.manager.DARC_Manager):
    def __init__ (self, airflow_test_config_filename, arena_filename):
        with open (airflow_test_config_filename, 'r') as fd:
            self.config = yaml.safe_load (fd)
        assisipy_utils.darc.manager.DARC_Manager.__init__ (
            self,
            _project = 'airflow-test',
            arena_file_name = arena_filename,
            config_file_name = create_DARC_config_file (
                compute_used_casus (self.config)
            )
        )

    def monitor (self):
        # open connections
        context = zmq.Context ()
        for a in self.config ['arenas']:
            socket = context.socket (zmq.REQ)
            socket.connect (self.worker_address_client_side (a ['core']))
            a ['socket_core'] = socket
            socket = context.socket (zmq.REQ)
            socket.connect (self.worker_address_client_side (a ['leaf']))
            a ['socket_leaf'] = socket
        # wait for all them to initialize
        for a in self.config ['arenas']:
            for sn in ['socket_core', 'socket_leaf']:
                zmq_sock_utils.send_recv (a [sn], airflow_test_1_worker.INITIALIZE)
        # tell the use to put bees
        print ('Put bees in the arena and press ENTER')
        raw_input ('> ')
        # tell each arena to do the temperature profile
        for a in self.config ['arenas']:
            print ('Starting temperature profile for arena with CASUs {} and {}'.format (a ['core'], a ['leaf']))
            self.config['parameters'][0] = airflow_test_1_worker.START_CORE
            zmq_sock_utils.send (a ['socket_core'], self.config ['parameters'])
            self.config['parameters'][0] = airflow_test_1_worker.START_LEAF
            zmq_sock_utils.send (a ['socket_leaf'], self.config ['parameters'])
        for a in self.config ['arenas']:
            print ('Waiting for temperature profile in arena with CASUs {} and {} to finish'.format (a ['core'], a ['leaf']))
            zmq_sock_utils.recv (a ['socket_core'])
            zmq_sock_utils.recv (a ['socket_leaf'])

def compute_used_casus (config):
    result = []
    for a in config ['arenas']:
        result.append (a ['core'])
        result.append (a ['leaf'])
    return result


def create_DARC_config_file (list_casus):
    contents = {
        'controllers': {
            'domset': {
                'main': airflow_test_1_worker.__file__,
                'extra': [
                    zmq_sock_utils.__file__
                ],
                'args': [],
                'results': [],
                'casus': list_casus
            }
        },
        'deploy': {
            'user': 'pedro',
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
    return parser.parse_args ()
