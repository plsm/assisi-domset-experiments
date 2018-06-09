#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import os.path
import subprocess
import yaml

import graph
import util
import worker_settings
import worker_stub

def main ():
    try:
        os.makedirs ("tmp")
    except OSError:
        pass
    args = process_arguments ()
    with open (args.config, 'r') as fd:
        cfg = yaml.load (fd)
    print ('Configuration file')
    print (cfg)
    lwsg = worker_settings.load_worker_settings (args.workers)
    g = graph.Graph (cfg)

    if args.check_video:
        check_video (cfg)
    elif args.deploy:
        deploy (lwsg, g)
    else:
        main_operations (cfg, lwsg)

def check_video (cfg):
    number_frames = cfg ['video']['frames_per_second'] * 10
    process_recording = util.record_video_gstreamer (
        'check-video-cropping.avi',
        number_frames,
        cfg ['video']['frames_per_second'],
        cfg ['video']['crop_left'],
        cfg ['video']['crop_right'],
        cfg ['video']['crop_top'],
        cfg ['video']['crop_bottom'])
    try:
        process_recording.wait ()
    except KeyboardInterrupt:
        print ('Terminate processes')
    print ('Done checking video cropping')

def deploy (lwsg, g):
    worker_settings.deploy_and_run_workers (
        lwsg,
        os.path.join (os.path.dirname (os.path.abspath (__file__)), 'worker.py'),
        [
            os.path.join (os.path.dirname (os.path.dirname (os.path.abspath (__file__))), 'controllers/domset_interspecies.py'),
            os.path.join (os.path.dirname (os.path.abspath (__file__)), 'zmq_sock_utils.py'),
        ],
        g)

def main_operations (cfg, lws):
    dws = worker_stub.connect_workers (lwsg)
    experiment_folder = calculate_experiment_folder_for_new_run ()
    process_deploy = run_command_deploy (args.config, args.workers)
    print ('Sending initialize message to all workers')
    for ws in dws.values ():
        ws.initialize ()
    print ('Press ENTER to start DOMSET and start video recording')
    raw_input ('> ')
    send_start_command_to_workers (dws)
    print ('[I] recording a {} minutes video'.format (cfg ['experiment_duration']))
    number_frames = cfg ['video']['frames_per_second'] * cfg ['experiment_duration'] * 60
    process_recording = util.record_video_gstreamer (
        os.path.join (experiment_folder, 'video.avi'),
        number_frames,
        cfg ['video']['frames_per_second'],
        cfg ['video']['crop_left'],
        cfg ['video']['crop_right'],
        cfg ['video']['crop_top'],
        cfg ['video']['crop_bottom'])
    try:
        process_recording.wait ()
    except KeyboardInterrupt:
        print ('Terminate processes')
    send_terminate_command_to_workers (dws)
    process_deploy.wait ()
    worker_settings.collect_data_from_workers (lwsg, experiment_folder)

def process_arguments ():
    parser = argparse.ArgumentParser (
        description = 'EvoVibe system - this application evolves vibration patterns generated by CASUs using bees as fitness providers. This program is part of the ASSISI PatVibe Software Suite.',
        argument_default = None
    )
    parser.add_argument (
        '--config',
        default = 'config',
        metavar = 'FILENAME',
        type = str,
        help = 'configuration file to use')
    parser.add_argument (
        '--workers',
        default = 'workers',
        metavar = 'FILENAME',
        type = str,
        help = 'worker settings file to load')
    parser.add_argument (
        '--deploy',
        action = 'store_true',
        help = 'deploy controllers to the beaglebones. Should be only used while debugging')
    parser.add_argument (
        '--check-video',
        action = 'store_true',
        help = 'check video cropping parameters')
    return parser.parse_args ()

def calculate_experiment_folder_for_new_run ():
    """
    Compute the experiment folder for a new experimental run.
    This folder is where all the files generated by an experimental run are stored.
    """
    run_number = 1
    while True:
        result = 'run-%03d/' % (run_number)
        if not os.path.isdir (result) and not os.path.exists (result):
            os.makedirs (result)
            return result
        run_number += 1

def run_command_deploy (config, workers):
    """
    Create a new process that is going to deploy code to the beagle bones.

    :param config:
    :param workers:
    :return:
    """
    command = [
        util.XTERM,
        '-geometry', '80x20+600+0',
        '-bg', 'rgb:5F/1F/0',
        '-title', 'deploy',
        '-e', 'python "%s" --deploy --config %s --workers "%s" ; echo Press ENTER to finish ; read DUMMY' % (__file__, config, workers)
        ]
    pdeploy = subprocess.Popen (command)
    return pdeploy

def send_start_command_to_workers (dict_worker_stubs):
    """
    Sends a command to the code running in the beagle bones that starts the DOMSET thread.

    :param dict_worker_stubs:
    """
    for ws in dict_worker_stubs.values ():
        ws.start_domset_send ()
    for ws in dict_worker_stubs.values ():
        ws.start_domset_recv ()

def send_terminate_command_to_workers (dict_worker_stubs):
    """
    Sends a command to the processes running in the beagle bones so that they finish the DOMSET thread.

    :param dict_worker_stubs:
    """
    for ws in dict_worker_stubs.values ():
        ws.terminate_session ()

if __name__ == '__main__':
    main ()
