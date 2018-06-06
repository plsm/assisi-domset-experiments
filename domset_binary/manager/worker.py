#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import zmq

import zmq_sock_utils

TERMINATE = 1
START = 2
INITIALIZE = 3
OK = 1001


def main (rtc_file_name, casu_number, worker_address):
    import domset_interspecies
    print ('[I] Main function for CASU {}'.format (casu_number))
    # open ZMQ server socket
    context = zmq.Context ()
    socket = context.socket (zmq.REP)
    socket.bind (worker_address)
    # Initialize domset algorithm
    ctrl = domset_interspecies.DomsetController (rtc_file_name, log=True)
    # main thread loop
    go = True
    print ('[I] Entering main loop for CASU {}'.format (casu_number))
    while go:
        message = zmq_sock_utils.recv (socket)
        if message [0] == INITIALIZE:
            print ('Initialize message')
            zmq_sock_utils.send (socket, [OK])
        elif message [0] == START:
            ctrl.calibrate_ir_thresholds ()
            ctrl.initialize_temperature ()
            ctrl.initial_wait (duration = 60)
            ctrl.start ()
            zmq_sock_utils.send (socket, [OK])
        elif message [0] == TERMINATE:
            go = False
            ctrl.stop = True
            zmq_sock_utils.send (socket, [OK])
        else:
            print ('Unknown message {}'.format (message))
    ctrl.join ()
    ctrl.casu.stop ()
    print ('End of worker for CASU {}'.format (casu_number))

if __name__ == '__main__':
    main (rtc_file_name = sys.argv [1], casu_number = int (sys.argv [2]), worker_address = sys.argv [3])
