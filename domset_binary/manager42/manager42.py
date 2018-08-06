#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os.path
import subprocess
import time
import yaml
import zmq

import assisipy_utils.darc.manager

import domset_binary.controllers.domset_fish_airflow
import domset_binary.util.video_sync
import domset_binary.util.zmq_sock_utils
import util.app
import util.video

TEST_DURATION = 5 # duration of a test run in minutes

class InterSpecies_DOMSET_Manager (assisipy_utils.darc.manager.DARC_Manager):
    def __init__ (self, isdm_config_filename, arena_filename, ISI_config_filename, ISI_path, test_run):
        """

        :type isdm_config_filename: str
        """
        with open (isdm_config_filename) as fd:
            self.isdm_config = yaml.safe_load (fd)
        self.experiment_folder = calculate_experiment_folder_for_new_run ()
        index = isdm_config_filename.find ('.')
        if index != -1:
            project_name = '{}_darc'.format (isdm_config_filename [:index])
        else:
            project_name = '{}_darc'.format (isdm_config_filename)
        assisipy_utils.darc.manager.DARC_Manager.__init__ (
            self,
            _project = project_name,
            arena_file_name = arena_filename,
            config_file_name = create_DARC_config_file (
                experiment_folder = self.experiment_folder,
                project_name = project_name,
                list_casus = self.isdm_config ['controllers']['domset']['casus'],
                node_CASUs = self.isdm_config ['graph']['node_CASUs'],
                flash_casu =  self.isdm_config ['controllers']['flash']['casu']
            )
        )
        self.sockets_domset_casus = {}
        self.socket_flash_casu = None
        self.ISI_config_filename = ISI_config_filename
        self.ISI_path = ISI_path
        self.process_ISI = None
        self.test_run = test_run

    def monitor (self):
        self.open_worker_connections ()
        self.send_initialise_message ()
        self.create_background_video ()
        self.IR_calibration_step ()
        self.run_inter_species_domset ()
        self.terminate_processes ()

    def open_worker_connections (self):
        def __create_socket (casu_number):
            socket = context.socket (zmq.REQ)
            socket.connect (self.worker_address_client_side (casu_number))
            return socket
        context = zmq.Context ()
        for a_casu in self.isdm_config ['controllers']['domset']['casus']:
            self.sockets_domset_casus [a_casu] = __create_socket (a_casu)
        self.socket_flash_casu = __create_socket (self.isdm_config ['controllers']['flash']['casu'])

    def send_initialise_message (self):
        print ('\n* ** Initialisation step ** *')
        message = [domset_binary.controllers.domset_fish_airflow.INITIALIZE]
        for casu_number, worker_socket in self.sockets_domset_casus.iteritems ():
            print ('Sending initialize DOMSET command to worker responsible for casu #{}...'.format (casu_number))
            answer = domset_binary.util.zmq_sock_utils.send_recv (worker_socket, message)
            print ('Worker responded with: {}'.format (str (answer)))
        print ('All the CASU workers are up and running')

    def create_background_video (self):
        print ('\n* ** Background video step ** *')
        print ('Close the lab door, close the curtains and turn off the lights...')
        print ('and press ENTER to record a background video')
        raw_input ('> ')
        number_frames = self.isdm_config ['video'] ['frames_per_second'] * 2
        util.video.record_video_gstreamer (
            os.path.join (self.experiment_folder, 'background-video.avi'),
            number_frames,
            self.isdm_config ['video'] ['frames_per_second'],
            self.isdm_config ['video'] ['crop_left'],
            self.isdm_config ['video'] ['crop_right'],
            self.isdm_config ['video'] ['crop_top'],
            self.isdm_config ['video'] ['crop_bottom'])

    def IR_calibration_step (self):
        """
        Sends a command to the code running in the beagle bones that starts the DOMSET thread.

        """
        print ('\n* ** Infrared calibration step ** *')
        self._send_message_domset_casus (
            message = [domset_binary.controllers.domset_fish_airflow.IR_CALIBRATION],
            text = 'infrared calibration command'
        )
        self._recv_message_domset_casus ()
        print ('Infrared calibration finished.')
        print ('Go and put the bees.')
        print ('Press ENTER when you are done')
        raw_input ('> ')

    def run_inter_species_domset (self):
        print ('\n* ** DOMSET algorithm and video recording step ** *')
        print ('In experiments with bee fish, this step has to be coordinated with Paris')
        print ('Press ENTER to start DOMSET and start video recording')
        raw_input ('> ')
        if self.test_run:
            experiment_duration = TEST_DURATION
        else:
            experiment_duration = self.isdm_config ['experiment_duration'] + domset_binary.util.video_sync.LENGTH
        self.process_ISI = self.run_ISI ()
        self._send_message_domset_casus (
            message = [domset_binary.controllers.domset_fish_airflow.START],
            text = 'start command'
        )
        print ('[I] recording a {} minutes video'.format (experiment_duration))
        number_frames = self.isdm_config ['video']['frames_per_second'] * experiment_duration * 60
        util.video.record_video_gstreamer (
            os.path.join (self.experiment_folder, 'video.avi'),
            number_frames,
            self.isdm_config ['video'] ['frames_per_second'],
            self.isdm_config ['video'] ['crop_left'],
            self.isdm_config ['video'] ['crop_right'],
            self.isdm_config ['video'] ['crop_top'],
            self.isdm_config ['video'] ['crop_bottom']
        )
        self._recv_message_domset_casus ()

    def run_ISI (self, debug = False):
        if self.ISI_config_filename is None or self.ISI_path is None:
            print ('[I] there is no ISI configuration file, so there will no ISI process')
            return None
        ISI_log_folder = os.path.join (self.experiment_folder, 'ISIlog')
        os.makedirs (ISI_log_folder)
        command = [
            util.app.XTERM,
            '-geometry', '80x20+0+400',
            '-bg', 'rgb:0/0/1F',
            '-title', 'ISI',
            '-e',
            'stdbuf -ol python /home/assisi/assisi/inter-domset/inter_domset/ISI/ISI.py --pth {} --proj_conf {} --logpath {} | tee {} ; echo Press ENTER to finish ; read DUMMY'.format (
                self.ISI_path,
                self.ISI_config_filename,
                ISI_log_folder,
                os.path.join (ISI_log_folder, 'ISIstdbuf')
            )
        ]
        if debug:
            print ('Full ISI command is:')
            print (' '.join (command))
            print ()
        return subprocess.Popen (command)

    def terminate_processes (self):
        print ('\n* ** Termination step ** *')
        self._send_message_domset_casus (
            message = [domset_binary.controllers.domset_fish_airflow.TERMINATE],
            text = 'terminate command'
        )
        self._recv_message_domset_casus ()
        print ('In the window with dark red background and titled «deploy», press ENTER.')
        if self.process_ISI is not None:
            print ('In the window with dark green background and title «ISI», press CONTROL-C.')
            self.process_ISI.wait ()

    def _send_message_domset_casus (self, message, text):
        for casu_number, worker_socket in self.sockets_domset_casus.iteritems ():
            print ('Sending {} to worker responsible for casu #{}...'.format (text, casu_number))
            domset_binary.util.zmq_sock_utils.send (worker_socket, message)

    def _recv_message_domset_casus (self):
        for casu_number, worker_socket in self.sockets_domset_casus.iteritems ():
            answer = domset_binary.util.zmq_sock_utils.recv (worker_socket)
            print ('Worker responsible for casu #{} responded with: {}'.format (casu_number, answer))
        

def create_DARC_config_file (experiment_folder, project_name, list_casus, node_CASUs, flash_casu):
    contents = {
        'controllers': {
            'domset': {
                'main': check_file (domset_binary.controllers.domset_fish_airflow.__file__),
                'extra': [
                    check_file (domset_binary.util.zmq_sock_utils.__file__)
                ],
                'args': [],
                'results': [],
                'casus': list_casus
            },
            'flash': {
                'main': check_file (domset_binary.util.video_sync),
                'extra': [],
                'results': [],
                'casus': [flash_casu]
            }
        },
        'deploy': {
            'user': 'assisi',
            'prefix': 'domset/interspecies',
            'args': {
                'add_casu_number': True,
                'add_worker_address': True
            }
        },
        'graph': {
            'node_CASUs': node_CASUs,
        }
    }
    filename = os.path.join (experiment_folder, '{}.config'.format (project_name))
    with open (filename, 'w') as fd:
        yaml.dump (contents, fd, default_flow_style = False)
        fd.close ()
    return filename

def check_file (filename):
    if filename [-2:] == 'py':
        return filename
    elif filename [-3:] == 'pyc':
        return filename [:-1]
    else:
        print ('Don t know what to do with {}'.format (filename))
        return None

def calculate_experiment_folder_for_new_run (starting_number = 1):
    """
    Compute the experiment folder for a new experimental run.
    This folder is where all the files generated by an experimental run are stored.
    """
    run_number = starting_number
    while True:
        result = 'run-{:03d}'.format (run_number)
        if not os.path.exists (result):
            os.makedirs (result)
            return result
        run_number += 1

def create_background_video (cfg, run_folder):
    print ('\n* ** Background video step ** *')
    print ('Close the lab door, close the curtains and turn off the lights...')
    print ('and press ENTER to record a background video')
    raw_input ('> ')
    number_frames = cfg ['video']['frames_per_second'] * 2
    util.video.record_video_gstreamer (
        os.path.join (run_folder, 'background-video.avi'),
        number_frames,
        cfg ['video']['frames_per_second'],
        cfg ['video']['crop_left'],
        cfg ['video']['crop_right'],
        cfg ['video']['crop_top'],
        cfg ['video']['crop_bottom'])

def process_arguments ():
    parser = argparse.ArgumentParser (
        description = 'Inter-Species DOMSET bee and ISI manager.',
        argument_default = None
    )
    parser.add_argument (
        '--isdm-config',
        default = 'config',
        metavar = 'FILENAME',
        type = str,
        help = 'configuration file specifying graph and CASUs to use'
    )
    parser.add_argument (
        '--arena',
        default = 'arena',
        metavar = 'FILENAME',
        type = str,
        help = 'arena file with CASU attributes'
    )
    parser.add_argument (
        '--check-video',
        action = 'store_true',
        help = 'check video cropping parameters'
    )
    parser.add_argument (
        '--test-run',
        action = 'store_true',
        help = 'do a test run with a length of {} minutes'.format (TEST_DURATION)
    )
    parser.add_argument (
        '--ISI-config',
        type = str,
        metavar = 'FILENAME',
        help = 'Configuration file for ISI.  If not specified a control experiment is run.'
    )
    parser.add_argument (
        '--ISI-path',
        type = str,
        metavar = 'PATH',
        default = '.',
        help = 'path to ISI files'
    )
    return parser.parse_args ()

def check_video (isdm_config_filename):
    with open (isdm_config_filename) as fd:
        isdm_config = yaml.safe_load (fd)
    number_frames = isdm_config ['video']['frames_per_second'] * 10
    util.video.record_video_gstreamer (
        'check-video-cropping.avi',
        number_frames,
        isdm_config ['video'] ['frames_per_second'],
        isdm_config ['video'] ['crop_left'],
        isdm_config ['video'] ['crop_right'],
        isdm_config ['video'] ['crop_top'],
        isdm_config ['video'] ['crop_bottom']
    )
    print ('Done checking video cropping')


def main ():
    args = process_arguments ()
    if args.check_video:
        check_video (args.isdm_config)
    else:
        m = InterSpecies_DOMSET_Manager (
            isdm_config_filename = args.isdm_config,
            arena_filename = args.arena,
            ISI_config_filename = args.ISI_config,
            ISI_path = args.ISI_path,
            test_run = args.test_run
        )
        m.run (m.experiment_folder)
