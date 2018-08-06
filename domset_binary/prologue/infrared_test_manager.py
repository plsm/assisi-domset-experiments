
import argparse
import os.path
import yaml
import zmq

import assisipy_utils.darc.manager

import infrared_test_worker
from domset_binary.util import zmq_sock_utils
import util.video

BACKGROUND_VIDEO_LENGTH = 2

class Infrared_Test_Manager (assisipy_utils.darc.manager.DARC_Manager):
    def __init__ (self, infrared_test_config_filename, arena_filename):
        with open (infrared_test_config_filename, 'r') as fd:
            self.atm_config = yaml.safe_load (fd)
        assisipy_utils.darc.manager.DARC_Manager.__init__ (
            self,
            _project = 'infrared-test',
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
            for k in ['A', 'B']:
                socket = context.socket (zmq.REQ)
                socket.connect (self.worker_address_client_side (a [k]))
                a ['s' + k] = socket
        # wait for all them to initialize
        for a in self.atm_config ['arenas']:
            for sn in ['sA', 'sB']:
                zmq_sock_utils.send_recv (a [sn], [infrared_test_worker.INITIALIZE])
        # record background video
        print ('Press ENTER to record a background video')
        raw_input ('> ')
        number_frames = self.atm_config ['video']['frames_per_second'] * BACKGROUND_VIDEO_LENGTH
        util.video.record_video_gstreamer (
            os.path.join (experiment_folder, 'background.avi'),
            number_frames,
            self.atm_config ['video']['frames_per_second'],
            self.atm_config ['video']['crop_left'],
            self.atm_config ['video']['crop_right'],
            self.atm_config ['video']['crop_top'],
            self.atm_config ['video']['crop_bottom'])
        # tell the user to put bees
        print ('Put bees in the arena and press ENTER')
        raw_input ('> ')
        # record video
        number_frames = self.atm_config ['video']['frames_per_second'] * self.atm_config ['parameters']['experiment_duration'] * 60
        process_recording = util.video.record_video_gstreamer (
            os.path.join (experiment_folder, 'video.avi'),
            number_frames,
            self.atm_config ['video']['frames_per_second'],
            self.atm_config ['video']['crop_left'],
            self.atm_config ['video']['crop_right'],
            self.atm_config ['video']['crop_top'],
            self.atm_config ['video']['crop_bottom'],
            async = True)
        # tell each arena to do the temperature profile
        self.atm_config ['parameters'][0] = infrared_test_worker.START
        for a in self.atm_config ['arenas']:
            print ('Starting infrared hit test for arena with CASUs {} and {}'.format (a ['A'], a ['B']))
            for sn in ['sA', 'sB']:
                zmq_sock_utils.send (a [sn], self.atm_config ['parameters'])
        for a in self.atm_config ['arenas']:
            print ('Waiting for infrared hit test in arena with CASUs {} and {} to finish'.format (a ['A'], a ['B']))
            zmq_sock_utils.recv (a ['sA'])
            zmq_sock_utils.recv (a ['sB'])
        # finish
        process_recording.wait ()
        print ('Close the window titled "{} deploy"'.format (self.project))

def compute_used_casus (config):
    result = []
    for a in config ['arenas']:
        result.append (a ['A'])
        result.append (a ['B'])
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
                'main': check_file (infrared_test_worker.__file__),
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
            'prefix': 'domset/infrared_test',
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
    filename = 'infrared-test.darc.config'
    with open (filename, 'w') as fd:
        yaml.dump (contents, fd, default_flow_style = False)
        fd.close ()
    return filename

def main ():
    args = process_arguments ()
    aftm = Infrared_Test_Manager (args.config, args.arena)
    if args.debug == 'create-files':
        aftm.create_files ()
    elif args.debug == 'monitor':
        aftm.monitor ()
    else:
        aftm.create_files ()
        aftm.run ('.')

def process_arguments ():
    parser = argparse.ArgumentParser (
        description = 'Test the infrared hits in a set of arenas',
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
