#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import sys
import zmq

from assisipy import casu

START_LEAF = 1
START_CORE = 2
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
        elif message [0] == START_LEAF:
            print ('[I] Start leaf message for CASU {}'.format (casu_number))
            temperature_profile_leaf (
                casu = a_casu,
                initial_temperature= message ['temperature_reference'],
                first_period_length = message ['first_period_length'],
                rate_temperature_increase = message ['rate_temperature_increase_leaf'],
                target_temperature = message ['target_temperature'],
                airflow_duration = message ['airflow_duration'],
                third_period_length = message ['third_period_length']
            )
            go = False
            zmq_sock_utils.send (socket, [OK])
        elif message [0] == START_CORE:
            print ('[I] Start core message for CASU {}'.format (casu_number))
            temperature_profile_core (
                casu = a_casu,
                initial_temperature= message ['temperature_reference'],
                first_period_length = message ['first_period_length'],
                rate_temperature_increase = message ['rate_temperature_increase_core'],
                target_temperature = message ['target_temperature'],
                airflow_duration = message ['airflow_duration'],
                third_period_length = message ['third_period_length']
            )
            zmq_sock_utils.send (socket, [OK])
            go = False
        else:
            print ('Unknown message {}'.format (message))
    a_casu.stop ()
    print ('[I] End of worker for CASU {}'.format (casu_number))

LED_DURATION = 1

def flash_led (casu):
    casu.set_diagnostic_led_rgb (r = 1, g = 0, b = 0)
    time.sleep (LED_DURATION)
    casu.set_diagnostic_led_rgb (0, 0, 0)

def temperature_profile_leaf (casu, initial_temperature, first_period_length, rate_temperature_increase, target_temperature, airflow_duration, third_period_length):
    temperature_reference = initial_temperature
    # first period
    flash_led (casu)
    casu.set_temp (temperature_reference)
    time.sleep (first_period_length - LED_DURATION)
    # second third period
    flash_led (casu)
    start = time.time ()
    stop = start + airflow_duration + third_period_length - LED_DURATION
    while time.time () < stop:
        temperature_reference = min (
            target_temperature,
            temperature_reference + rate_temperature_increase * DELTA)
        casu.set_temp (temperature_reference)
        time.sleep (DELTA)

def temperature_profile_core (casu, initial_temperature, first_period_length, rate_temperature_increase, target_temperature, airflow_duration, third_period_length):
    temperature_reference = initial_temperature
    # first period
    flash_led (casu)
    start = time.time ()
    stop = start + first_period_length - LED_DURATION
    while time.time () < stop:
        temperature_reference = min (
            target_temperature,
            temperature_reference + rate_temperature_increase * DELTA)
        casu.set_temp (temperature_reference)
        time.sleep (DELTA)
    # second period
    flash_led (casu)
    start = time.time ()
    stop = start + airflow_duration - LED_DURATION
    casu.set_temp (initial_temperature)
    casu.set_airflow_intensity(1)
    time.sleep (airflow_duration)
    casu.airflow_standby ()
    # third period
    flash_led (casu)
    start = time.time ()
    time.sleep (third_period_length)


if __name__ == '__main__':
    main (rtc_file_name = sys.argv [1], casu_number = int (sys.argv [2]), worker_address = sys.argv [3])
