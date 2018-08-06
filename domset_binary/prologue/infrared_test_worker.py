#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import sys
import zmq

from assisipy import casu

START = 1
INITIALIZE = 3
OK = 1001

DELTA = 5

def main (rtc_file_name, casu_number, worker_address):
    import zmq_sock_utils
    print ('[I] Main function for CASU {}'.format (casu_number))
    # open ZMQ server socket
    context = zmq.Context ()
    socket = context.socket (zmq.REP)
    print ('[I] Binding to {}'.format (worker_address))
    socket.bind (worker_address)
    # Initialize domset algorithm
    a_casu = casu.Casu (rtc_file_name, log = True)
    # main thread loop
    go = True
    print ('[I] Entering main loop for CASU {}'.format (casu_number))
    while go:
        message = zmq_sock_utils.recv (socket)
        if message [0] == INITIALIZE:
            print ('[I] Initialize message for CASU {}'.format (casu_number))
            zmq_sock_utils.send (socket, [OK])
        elif message [0] == START:
            print ('[I] Start message for CASU {}'.format (casu_number))
            infrared_hit (
                casu = a_casu,
                temperature_reference = message ['temperature_reference'],
                experiment_duration = message ['experiment_duration'],
            )
            go = False
            zmq_sock_utils.send (socket, [OK])
        else:
            print ('Unknown message {}'.format (message))
    a_casu.stop ()
    print ('[I] End of worker for CASU {}'.format (casu_number))

LED_DURATION = 1

def flash_led (casu):
    casu.set_diagnostic_led_rgb (r = 1, g = 0, b = 0)
    time.sleep (LED_DURATION)
    casu.set_diagnostic_led_rgb (0, 0, 0)

def infrared_hit (casu, temperature_reference, experiment_duration):
    temperature_reference = initial_temperature
    flash_led (casu)
    casu.set_temp (temperature_reference)
    time.sleep (experiment_duration)
    flash_led (casu)

if __name__ == '__main__':
    main (rtc_file_name = sys.argv [1], casu_number = int (sys.argv [2]), worker_address = sys.argv [3])
