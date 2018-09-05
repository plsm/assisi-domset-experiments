#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Read the configuration file of an inter-species DOMSET experiment and process the background video to create the masks

from __future__ import print_function

import argparse
import os.path
import sys
import yaml

import util.video

BACKGROUND_VIDEO_FILENAME = 'background-video.avi'
BACKGROUND_VIDEO_NUMBER_FRAMES = 10

def main ():
    if not os.path.exists ('frames'):
        os.makedirs ('frames')
    args = process_arguments ()
    with open (args.config, 'r') as fd:
        config = yaml.safe_load (fd)
    split_background_video (config, args.base_path)

def process_arguments ():
    parser = argparse.ArgumentParser (
        'Process background video'
    )
    parser.add_argument (
        '--config', '-c',
        metavar = 'FILENAME',
        type = str,
        required = True,
        help = 'configuration file name'
    )
    parser.add_argument (
        '--base-path',
        metavar = 'PATH',
        type = str,
        default = '.',
        help = 'path where the experiment data files are stored'
    )
    return parser.parse_args ()

def split_background_video (config, base_path = '.'):
    code = util.video.split_video (
        os.path.join (base_path, BACKGROUND_VIDEO_FILENAME),
        BACKGROUND_VIDEO_NUMBER_FRAMES,
        config ['video']['frames_per_second'],
        'frames/background-%4d.png',
        debug = True
    )
    if code != 0:
        print ('[E] There was a problem splitting the background video!')
        sys.exit (code)

if __name__ == '__main__':
    main ()
