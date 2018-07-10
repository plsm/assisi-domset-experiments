# defines several constants that contain the full path name to external applications

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
FFMPEG = find_app ('ffmpeg')
AVCONV = find_app ('avconv')
