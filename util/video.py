import subprocess

import app

CAMERA_RESOLUTION_X = 2048
CAMERA_RESOLUTION_Y = 2048

def split_video (video_filename, number_frames, frames_per_second, output_template, debug = False):
    # type: (str, int, float, str) -> int
    """
    Split a video in its frames.  The filename of the frames is given by parameter output_template.

    :param video_filename: filename of the video to split
    :param number_frames: number of frames in the video
    :param frames_per_second: frame rate of the video
    :param output_template: a string representing the frame filename. Should contain
    :return: The return code of the ffmpeg process
    """
    command = [
        app.FFMPEG,
        '-i', video_filename,
        '-r', '{:f}'.format (frames_per_second),
        '-loglevel', 'error',
        '-frames', '{:d}'.format (number_frames),
        '-f', 'image2',
        output_template
    ]
    if debug:
        print ('Full command is:')
        print (' '.join (command))
        print
    process = subprocess.Popen (command)
    process.wait ()
    return process.returncode

def record_video_gstreamer (video_filename, number_frames, frames_per_second, crop_left, crop_right, crop_top, crop_bottom, debug = True):
    """

    :rtype: int
    """
    command =  [
        app.GST_LAUNCH,
        '--gst-plugin-path=/usr/local/lib/gstreamer-0.10/',
        '--gst-plugin-load=libgstaravis-0.4.so',
        #'--verbose',
        #'--quiet',
        'aravissrc', 'num-buffers=%d' % (number_frames), '!',
        'video/x-raw-yuv,', 'width=2048,', 'height=2048,', 'framerate=%d/1' % (frames_per_second), '!',
        'videocrop', 'left=%d' % (crop_left), 'right=%d' % (crop_right), 'top=%d' % (crop_top), 'bottom=%d' % (crop_bottom), '!',
        'jpegenc', '!',
        'avimux', 'name=mux', '!',
        'filesink', 'location=%s' % (video_filename)
        ]
    if debug:
        print
        print ('Recording a video with %d frames at %d frames per second.' % (number_frames, frames_per_second))
        print ('Frame resolution is %dx%d.' % (CAMERA_RESOLUTION_X - crop_right - crop_left, CAMERA_RESOLUTION_Y - crop_top - crop_bottom))
        print ('Full command is:')
        print (' '.join (command))
        print
    process = subprocess.Popen (command)
    process.wait ()
    return process.returncode
