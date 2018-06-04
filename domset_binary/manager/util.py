import subprocess

def find_app (app):
    command = "which " + app
    process = subprocess.Popen (command, stdout = subprocess.PIPE, shell = True)
    out, _ = process.communicate ()
    if process.returncode != 0:
        print ('This computer does not have application', app)
        return '/bin/true'
    else:
        return out [:-1]

GST_LAUNCH = find_app ('gst-launch-0.10')
XTERM = find_app ('xterm')

CAMERA_RESOLUTION_X = 2048
CAMERA_RESOLUTION_Y = 2048

def record_video_gstreamer (video_filename, number_frames, frames_per_second, crop_left, crop_right, crop_top, crop_bottom, debug = False):
    command =  [
        GST_LAUNCH,
        '--gst-plugin-path=/usr/local/lib/gstreamer-0.10/',
        '--gst-plugin-load=libgstaravis-0.4.so',
        #'--verbose',                                                                                                                                                                                                                          
        '--quiet',
        'aravissrc', 'num-buffers=%d' % (number_frames), '!',
        'video/x-raw-yuv,width=2048,height=2048,framerate=%d/1' % (frames_per_second), '!',
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
    return subprocess.Popen (command)


BEE_LAYER = 'bee-arena'
MANAGER_LAYER = 'fish-tank'
MANAGER_NODE = '{}/cats'.format (MANAGER_LAYER)