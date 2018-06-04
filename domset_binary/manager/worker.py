#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import zmq

import zmq_sock_utils

TERMINATE = 1
START = 2
OK = 1001


def main (rtc_file_name, casu_number, worker_address):
    import domset_interspecies
    # open ZMQ server socket
    context = zmq.Context ()
    socket = context.socket (zmq.REP)
    socket.bind (worker_address)
    # Initialize domset algorithm
    ctrl = domset_interspecies.DomsetController (rtc_file_name, log=True)
    ctrl.calibrate_ir_thresholds ()
    ctrl.initialize_temperature ()
    ctrl.initial_wait ()
    # main thread loop
    go = True
    while go:
        message = zmq_sock_utils.recv (socket)
        if message [0] == START:
            ctrl.start ()
            zmq_sock_utils.send (socket, [OK])
        elif message [0] == TERMINATE:
            go = False
            ctrl.stop = True
            zmq_sock_utils.send (socket, [OK])
        else:
            print ('Unknown message {}'.format (message))
    ctrl.join ()
    print ('End of worker for CASU {}'.format (casu_number))

if __name__ == '__main__':
    main (rtc_file_name = sys.argv [1], casu_number = int (sys.argv [2]), worker_address = sys.argv [3])
