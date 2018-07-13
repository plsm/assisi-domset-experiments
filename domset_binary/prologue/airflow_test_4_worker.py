#!/usr/bin/env python
# -*- coding: utf-8 -*-

from assisipy import casu

import sys
import time
from threading import Thread, Event
from datetime import datetime
from copy import deepcopy
import json
from json import encoder
import zmq

import csv
from math import exp

START_LEAF = 1
START_CORE = 2
INITIALIZE = 3
OK = 1001

DELTA = 5

class DomsetController:

    MAX_TEMPERATURE = 36
    MIN_TEMPERATURE = 26
    START_TEMPERATURE = 28

    def __init__(self, rtc_file, log=False):

        self.turn_off_LED = False
        self.casu = casu.Casu(rtc_file,log=True)
        # Parse rtc file name to get CASU id
        # assumes casu-xxx.rtc file name format
        self.casu_id = int(rtc_file[-7:-4])
        nbg_ids = []
        for name in self.casu._Casu__neighbors:
            if not ('cats' in name):
                nbg_ids.append(int(name[-3:]))
        #nbg_ids = [int(name[-3:]) for name in self.casu._Casu__neighbors]
        self.nbg_data_buffer = {}
        self._is_master = 1 # master in CASU group calculates new temp ref
        self.group_size = 1 # only counts the neighbours; have to add myself

        for nb in nbg_ids:
            self.group_size += 1
            self.nbg_data_buffer[nb] = []
            if nb < self.casu_id:
                self._is_master = 0

        self.spoof_group_size = self.group_size

        print("CASU: " + str(self.casu_id) + ", group size: " + str(self.group_size))

        self.fish_info = []

        if self._is_master == 0:
            master_id = self.casu_id
            master = self.casu
            for nbg in self.casu._Casu__neighbors:
                if "cats" in nbg:
                    pass
                else:
                    nbg_id = int(nbg[-3:])
                    if nbg_id < master_id:
                        master = nbg
                        master_id = nbg_id
            self.group_master = master
            self.group_master_id = master_id

        self._Td = 0.1 # Sample time for sensor readings is 0.1 second
        Ttemp = 5.0 # discretisation period
        self._temp_control_freq = 1.0 / Ttemp # Sample frequency for temperature control in seconds is once in 5 seconds
        self.time_start = time.time()
        self.time_start_cool = time.time()
        self.time_start_heat = time.time()
        self._time_length = 1800.0 #1500.0 - longer experiment run for the fish influence
        self._time_length_cool = 750.0
        self._time_length_heat = 500.0
        self.t_prev = time.time()
        self.stop_flag = Event()
        self.temp_ref = float (DomsetController.START_TEMPERATURE)
        self.temp_ref_old = float (DomsetController.START_TEMPERATURE)
        self.blow = 0.0
        self.blow_prev = 0.0

        # sensor activity variables - denote bee presence
        self.activeSensors = [0]
        self._sensors_buf_len = 10 * Ttemp # last 2 sec? should be Ttemp/Td
        self.ir_thresholds = [25000, 25000, 25000, 25000, 25000, 25000]
        self.integrate_activity = 0.0
        self.average_activity = 0.0
        self.maximum_activity = 0.0
        self.minimum_activity = 1.0
        self.temp_ctrl = 0
        self.initial_heating = 0
        self.heat_float = 0.0
        self.cool_float = 0.0

        # constants for temperature control
        self._integration_limit = 100.0
        self._integrate_limit_lower = 10.0 / Ttemp
        self._integrate_limit_upper = 20.0 / Ttemp
        self._stop_initial_heating = 10
        self._inflection_heat = 0.17
        self._inflection_cool = 0.85
        self._start_heat = 0.1
        self._stop_heat = 0.7
        self._start_cool = 0.2
        self._stop_cool = 0.5
        self._rho = 0.85
        self._step_heat = 0.05
        self._step_cool = 0.03
        self._epsilon = 0.3

        self.integrate_minimum_activity = 0.0

        self._blow_allowed_start = 5 * 60.0 # no blow first 5 min
        self._blow_allowed_stop = 1500.0 - 10 * 60.0 # no blowing in last n minutes
        self._scaling_blow = 0.2 # 1 sensor active (0.16.) is not enough to stay in the domset
        self._integrate_min_windup = 100
        self._blow_start_condition = 12 # n x Td seconds minimum activity below threshold before we start blowing
        self._default_blow_duration = 60.0


        # Set up zeta logging
        now_str = datetime.now().__str__().split('.')[0]
        now_str = now_str.replace(' ','-').replace(':','-')
        self.logfile = open(now_str + '-' + self.casu.name() + '-domset.csv','wb')
        self.logger = csv.writer(self.logfile, delimiter=';')

        self.i = 0

    def reset (self):
        self.integrate_activity = 0.0
        self.average_activity = 0.0
        self.maximum_activity = 0.0
        self.minimum_activity = 1.0
        self.temp_ctrl = 0
        self.initial_heating = 0
        self.heat_float = 0.0
        self.cool_float = 0.0
        self.time_start_cool = time.time ()
        self.time_start_heat = time.time ()

    def calibrate_ir_thresholds(self, margin = 500, duration = 10):
        self.casu.set_diagnostic_led_rgb(r=1)

        t_start = time.time()
        ir_raw_buffers = [[0],[0],[0],[0],[0],[0]]
        while time.time() - t_start < duration:
            ir_raw = self.casu.get_ir_raw_value(casu.ARRAY)
            for (val, buff) in zip(ir_raw, ir_raw_buffers):
                buff.append(val)
            time.sleep(0.1)

        self.ir_thresholds = [max(buff)+margin for buff in ir_raw_buffers]
        print(self.casu.name(), self.ir_thresholds)
        self.logger.writerow (['IRT', time.time ()] + self.ir_thresholds)

        self.casu.diagnostic_led_standby()

    def initial_wait(self, duration = 60):
        self.casu.set_diagnostic_led_rgb(r = 1, g = 1, b = 1)

        t_start = time.time()

        while time.time() - t_start < duration:
            time.sleep(0.1)

        self.casu.diagnostic_led_standby()

    def initialize_temperature(self):

        self.casu.set_temp(self.temp_ref)

    def update(self):

        t_old = self.t_prev
        self.t_prev = time.time()
        # calculate local ir sensor activity over time
        self.calculate_self_average_activity()
        if self.group_size == 1:
            msg = self.casu.read_message()
            if msg:
                if 'iface' in msg['sender']:
                    self.fish_info.append(msg['data'])
                    print("[I] casu-{:03d} rx from iface".format(self.casu_id), msg['data'])
        if self._is_master:
            if self.group_size > 1:
                # receive group ir readings
                updated_all = False
                while not updated_all:
                    msg = self.casu.read_message()
                    if msg:
                        if 'iface' in msg['sender']:
                            self.fish_info.append(msg['data'])
                            print("[I] casu-{:03d} rx from iface".format(self.casu_id), msg['data'])
                            #print("CASU " + str(self.casu_id) + " got DATA: " + msg['data'])
                        else:
                            nbg_id = int(msg['sender'][-3:])
                            self.nbg_data_buffer[nbg_id].append(msg['data'])
                            #print(self.nbg_data_buffer[nbg_id])
                        # Check if we now have at least one message from each neighbor
                        updated_all = True
                        for nbg in self.nbg_data_buffer:
                            if not self.nbg_data_buffer[nbg]:
                                #print(str(casu_id) + ' +++ missing ir readings +++ ' + str(nbg))
                                updated_all = False
                        #else:
                            #self.nbg_data_buffer[nbg_id].pop(0)
            # calculate cumulative sensor activity of a group --> temperature control
            if (self.reset_threshold == 1.0):
                self.time_start_cool = time.time()
                self.time_start_heat = time.time()
                self.reset_threshold = 0.0
            self.calculate_sensor_activity()
            self.calculate_temp_ref()
            if (self.reset_temp == 1.0):
                self.temp_ref = 28.0
                self.reset_temp = 0.0
            if (self.group_size > 1):
                for nbg in self.casu._Casu__neighbors:
                    if not ("cats" in nbg):
                        success = self.casu.send_message(nbg,json.dumps({
                        't_ref':self.temp_ref,
                        'blow':self.blow}))
                        if 0: print success


        else:
            # send self ir readings to group master
            '''
            master_id = casu_id
            master = self.casu
            for nbg in self.casu._Casu__neighbors:
                if "cats" in nbg:
                    pass
                else:
                    nbg_id = int(nbg[-3:])
                    if nbg_id < master_id:
                        master = nbg
                        master_id = nbg_id
            '''
            self.casu.send_message(self.group_master,json.dumps(self.average_activity))
            # wait for new temp reference from group master
            updated_temp_ref = False
            while not updated_temp_ref:
                msg = self.casu.read_message()
                if msg:
                    nbg_id = int(msg['sender'][-3:])
                    self.nbg_data_buffer[nbg_id].append(msg['data'])
                    updated_temp_ref = True
            data = self.nbg_data_buffer[nbg_id].pop()
            tmp = json.loads(data)
            self.blow = float(tmp['blow'])

            t_ref = float(tmp['t_ref'])
            self.temp_ref_old = self.temp_ref
            self.temp_ref = t_ref

        # Set temperature reference
        if not (self.temp_ref_old == self.temp_ref):
            self.logger.writerow (["CT", time.time (), self.temp_ref])
            self.casu.set_temp(self.temp_ref)

    def communicate(self):

        if self._is_master:
            # construct payload, with max precision 3dp
            pl = json.dumps({
                'max':"{:.3f}".format(self.maximum_activity),
                'avg':"{:.3f}".format(self.average_activity),
                'min':"{:.3f}".format(self.minimum_activity),
                'tref':"{:.3f}".format(self.temp_ref),
                'thres_max' : "{:.3f}".format(self.thres_cool),
                'thres_avg' : "{:.3f}".format(self.thres_heat),
                'thres_min' : "{:.3f}".format(self.thres_blow),
            })
            self.casu.send_message("cats", pl)
            #print("[I]{}: emitted to ISI, payload:\n\t{}".format(self.casu_id, pl))

            #self.casu.send_message("cats", json.dumps({
            #'max' : self.maximum_activity,
            #'avg' : self.average_activity,
            #'min' : self.minimum_activity,
            #'tref':self.temp_ref,
            #'thres_max' : self.thres_cool,
            #'thres_avg' : self.thres_heat,
            #'thres_min' : self.thres_blow}))

    def respond_to_fish(self):
        if self.fish_info:
            msg = self.fish_info.pop()
            decompose = msg.split("blow:")
            decompose = decompose[1].split(';')
            duration = float(decompose[0])
            self.blow = duration

            decompose = msg.split("reset_temp:")
            decompose = decompose[1].split(';')
            self.reset_temp = float(decompose[0])

            decompose = msg.split("delta_temp_ref:")
            decompose = decompose[1].split(';')
            self.delta_temp_ref = float(decompose[0])

            decompose = msg.split("reset_threshold:")
            decompose = decompose[1].split(';')
            self.reset_threshold = float(decompose[0])




            # here i should set the self.blow to received blow duration
            print("CASU-" + str(self.casu_id) + ": " + msg)
            self.casu.set_diagnostic_led_rgb (r = 1, b = 0, g = 1)
            self.turn_off_LED = True
        else:
            pass

    def airflow_control(self):
        if self.blow > 0.0:
            if self.blow_prev == 0.0:
                self.start_blow = time.time()
                self.logger.writerow (["CAF", time.time (), 1])
                self.casu.set_airflow_intensity(1)
                if self.casu_id == 20:
                    print("Actually starts blowing")
            else:
                time_now = time.time()
                if (time_now - self.start_blow) > self.blow:
                    self.logger.writerow (["CAF", time.time (), 0])
                    self.casu.airflow_standby()
                    self.blow = 0.0
                    self.integrate_minimum_activity = 0
                    if self.casu_id == 20:
                        print("Stop blowing, timeout!")
        else:
            if not (self.blow_prev == 0.0):
                self.logger.writerow (["CAF", time.time (), 0])
                self.casu.airflow_standby()
                self.integrate_minimum_activity = 0
        self.blow_prev = self.blow


    def run(self, time_adjustment):
        # Just call update every Td
        self.time_start = time.time()
        self.time_start_cool = time.time() - time_adjustment
        self.time_start_heat = time.time() - time_adjustment
        self.i = 0
        self.time_index = 1
        while (time.time() - self.time_start < self._time_length) and not (self.stop_flag.wait(self._Td)):
            if (time.time() - self.time_start > self.time_index * 100) and (time.time() - self.time_start < self.time_index * 100 + 1):
                print("[casu-{:03}] {}s elapsed".format(self.casu_id, self.time_index * 100))
                self.time_index += 1
            self.update_activeSensors_estimate()
            self.i += 1
            if (self.i >= 1 / (self._Td * float(self._temp_control_freq))):
                #print(str(self.casu_id) + ' ' + str(self.t_prev - self.time_start))
                self.update()
                if self.turn_off_LED:
                    self.casu.set_diagnostic_led_rgb (0,0,0)
                self.airflow_control()
                self.respond_to_fish()
                self.communicate()
                self.i = 0
        self.casu.airflow_standby()

    def end (self):
        self.logfile.close ()
        print("Done")

    def update_activeSensors_estimate(self):
        """
        Bee density estimator.
        """
        activeSensors_current = [x>t for (x,t) in zip(self.casu.get_ir_raw_value(casu.ARRAY), self.ir_thresholds) if x < 65535]
        if len(activeSensors_current) > 0:
            activeSensors_current_percentage = sum(activeSensors_current) / float(len(activeSensors_current))
            self.activeSensors.append(activeSensors_current_percentage)
        else:
            self.activeSensors.append(-1)
        if len(self.activeSensors) > self._sensors_buf_len:
            self.activeSensors.pop(0)
        self.logger.writerow (["CAS", time.time ()] + activeSensors_current)

    def calculate_self_average_activity(self):
        activeSensors = [x for x in self.activeSensors if x >= 0]
        try:
            if len(activeSensors) > 0:
                self.average_activity = sum(activeSensors) / float(len(activeSensors))
                self.maximum_activity = self.average_activity
                self.minimum_activity = self.average_activity
            else:
                self.average_activity = -1
                self.maximum_activity = 0
                self.minimum_activity = 1
        except:
            self.average_activity = -1
            self.maximum_activity = 0
            self.minimum_activity = 1
        self.logger.writerow (["CAC", time.time (), self.average_activity])

    def calculate_sensor_activity(self):
        group_functional = self.group_size

        if self.average_activity == -1:
            self.average_activity = 0
            self.maximum_activity = 0
            self.minimum_activity = 1
            group_functional -= 1

#        print('self.group_size ' + str(self.group_size))
#        print('group_functional ' + str(group_functional))
        for nbg in self.nbg_data_buffer:
            try:
                data = self.nbg_data_buffer[nbg].pop().split(';')
            except IndexError:
                print('casu ' + str(self.casu_id) + ' EMPTY LIST')
                data = [-1]
            tmp = json.loads(data[0])
            if not (tmp == -1):
                self.average_activity += tmp
                if self.maximum_activity < tmp:
                    self.maximum_activity = tmp
                if self.minimum_activity > tmp:
                    self.minimum_activity = tmp
            else:
                group_functional -= 1

        if self.integrate_activity < self._integration_limit:
            self.integrate_activity += self.average_activity
        if group_functional > 0:
            self.average_activity /= group_functional
        #print('average ' + str(self.average_activity))
        #print(self.maximum_activity)
        #print('integrate ' + str(self.integrate_activity))
        self.logger.writerow (["NAC", time.time (), self.average_activity])

    def calculate_temp_ref(self):
        """
        Dominating set temperature control based on sensor activity of CASU group
        """
        # directly from matlab. Should rewrite clearer
        if (self.integrate_activity > self._integrate_limit_lower) and (self.temp_ctrl < self._stop_initial_heating):
            self.temp_ctrl += 1
        self.initial_heating = 1
        if (self.integrate_activity < self._integrate_limit_lower) or (self.integrate_activity > self._integrate_limit_upper) or (self.temp_ctrl >= self._stop_initial_heating) :
            self.initial_heating = 0

        #i_n = (self.t_prev - self.time_start) / self._time_length;
        i_n_cool = ((self.t_prev - self.time_start_cool) / self._time_length_cool)
        i_n_heat = ((self.t_prev - self.time_start_heat) / self._time_length_heat)
        if i_n_cool >= 1:
            i_n_cool = 0.99
        if i_n_heat >= 1:
            i_n_heat = 0.99
        progress = 1.0 - 1.0 / (1.0 - i_n_heat)
        progress_heat = 1 - exp(self._inflection_heat * progress)
        progress = 1.0 - 1.0 / (1.0 - i_n_cool)
        progress_cool = 1 - exp(self._inflection_cool * progress)
        scaling_heat = (1.0 - progress_heat) * self._start_heat + progress_heat * self._stop_heat
        scaling_cool = (1.0 - progress_cool) * self._start_cool + progress_cool * self._stop_cool

        self.cool_float = (1.0 - self._rho) * self.cool_float
        #if ((self.maximum_activity < scaling_cool) or (self.minimum_activity == 0.0)) and (self.temp_ctrl > 0):
        if (self.maximum_activity < scaling_cool) and (self.temp_ctrl > 0):
            self.cool_float += self._rho * 1.0
        if (self.cool_float > 0.5):
            cool = 1.0
        else:
            cool = 0.0

        self.heat_float = (1 - self._rho) * self.heat_float
        if (self.average_activity > scaling_heat) and (self.temp_ctrl > 0) and (cool == 0.0):
             self.heat_float += self._rho * 1.0
        if (self.heat_float > 0.5) and (cool == 0.0):
            heat = 1.0
        else:
            heat = 0.0

        if int(self.casu_id) == -1:
            print(" maximum_activity " + str(self.maximum_activity)+ " scaling_cool " + str(scaling_cool))
            print("minimum activity " + str(self.minimum_activity))
            print("cool_float " + str(self.cool_float) + " cool " + str(cool))
            print("heat_float " + str(self.heat_float) + " heat " + str(heat))
            print("temp_ctrl " + str(self.temp_ctrl))

        d_t_ref = 0.0
        if (heat == 1.0):
            d_t_ref = self._step_heat * self.group_size
        if (cool == 1.0):
            d_t_ref = - self._step_cool
        if d_t_ref > 0.5:
            d_t_ref = 0.5

        self.temp_ref_old = self.temp_ref
        self.temp_ref = self.temp_ref + d_t_ref
        if self.temp_ref > DomsetController.MAX_TEMPERATURE:
            self.temp_ref = DomsetController.MAX_TEMPERATURE
        if self.temp_ref < DomsetController.MIN_TEMPERATURE:
            self.temp_ref = DomsetController.MIN_TEMPERATURE
        #if not (self.temp_ref_old == self.temp_ref):
            #print('new temperature reference ')
        self.logger.writerow (["NT", time.time (), self.temp_ref])

        # save thresholds for fish side
        self.thres_cool = scaling_cool
        self.thres_heat = scaling_heat
        time_now = time.time()
        if (time_now - self.time_start > self._blow_allowed_start) and (time_now - self.time_start < self._blow_allowed_stop):
            self.thres_blow = self._scaling_blow
        else:
            self.thres_blow = 0.0

        self.logger.writerow (["TH_HEAT", time.time (), self.thres_heat])
        self.logger.writerow (["TH_COOL", time.time (), self.thres_cool])
        self.logger.writerow (["TH_MIN",  time.time (), self.thres_blow])

    def calculate_blow_ref(self):
        time_now = time.time()
        if (time_now - self.time_start > self._blow_allowed_start) and (time_now - self.time_start < self._blow_allowed_stop):
            if (self.blow == 0.0):
                if (self.integrate_minimum_activity < self._integrate_min_windup):
                    if (self.minimum_activity < self._scaling_blow):
                        self.integrate_minimum_activity += 1
                        if (self.casu_id == 20):
                            print("Integrating activity " + str(self.integrate_minimum_activity))
                    else:
                        self.integrate_minimum_activity = 0
                if (self.integrate_minimum_activity >= self._blow_start_condition):
                    self.blow = self._default_blow_duration
                    if (self.casu_id == 20):
                        print("Integration over, setpoint blowing " + str(self.integrate_minimum_activity))


def main (rtc_file_name, casu_number, worker_address):
    import zmq_sock_utils
    print ('[I] Main function for CASU {}'.format (casu_number))
    # open ZMQ server socket
    context = zmq.Context ()
    socket = context.socket (zmq.REP)
    print ('[I] Binding to {}'.format (worker_address))
    socket.bind (worker_address)
    # Initialize domset algorithm
    ctrl = DomsetController (rtc_file_name, log = True)
    ctrl.calibrate_ir_thresholds (500, 1)
    ctrl.initialize_temperature ()
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
                controller = ctrl,
                first_period_length = message ['first_period_length'],
                airflow_duration = message ['airflow_duration'],
                third_period_length = message ['third_period_length'],
                time_adjustment = message ['time_adjustment'],
            )
            go = False
            zmq_sock_utils.send (socket, [OK])
        elif message [0] == START_CORE:
            print ('[I] Start core message for CASU {}'.format (casu_number))
            temperature_profile_core (
                controller = ctrl,
                first_period_length = message ['first_period_length'],
                rate_temperature_increase = message ['rate_temperature_increase_core'],
                node_size = message ['core_node_size'],
                airflow_duration = message ['airflow_duration'],
                third_period_length = message ['third_period_length']
            )
            zmq_sock_utils.send (socket, [OK])
            go = False
        else:
            print ('Unknown message {}'.format (message))
    ctrl.casu.stop ()
    print ('[I] End of worker for CASU {}'.format (casu_number))

LED_DURATION = 1

def flash_led (casu):
    casu.set_diagnostic_led_rgb (r = 1, g = 0, b = 0)
    time.sleep (LED_DURATION)
    casu.set_diagnostic_led_rgb (0, 0, 0)

def temperature_profile_leaf (controller, first_period_length, airflow_duration, third_period_length, time_adjustment = 300):
    controller._time_length = first_period_length - LED_DURATION
    flash_led (controller.casu)
    controller.run (0)
    controller._time_length = airflow_duration + third_period_length - LED_DURATION
    flash_led (controller.casu)
    controller.reset ()
    controller.run (time_adjustment)
    # stop cleanly
    controller.end ()

def temperature_profile_core (controller, first_period_length, rate_temperature_increase, node_size, airflow_duration, third_period_length):
    temperature_reference = DomsetController.MIN_TEMPERATURE
    # first period
    flash_led (controller.casu)
    start = time.time ()
    stop = start + first_period_length - LED_DURATION
    while time.time () < stop:
        temperature_reference = min (
            DomsetController.MAX_TEMPERATURE,
            temperature_reference + rate_temperature_increase * DELTA)
        controller.casu.set_temp (temperature_reference)
        time.sleep (DELTA)
    # second period
    flash_led (controller.casu)
    controller.casu.set_airflow_intensity(1)
    start = time.time ()
    stop = start + airflow_duration - LED_DURATION
    while time.time () < stop:
        temperature_reference = max (
            DomsetController.MIN_TEMPERATURE,
            temperature_reference - rate_temperature_increase * DELTA)
        controller.casu.set_temp (temperature_reference)
        time.sleep (DELTA)
    controller.casu.airflow_standby ()
    # third period
    controller._time_length = third_period_length
    controller.spoof_group_size = node_size
    controller.run (0)
    # stop cleanly
    controller.end ()

if __name__ == '__main__':
    main (rtc_file_name = sys.argv [1], casu_number = int (sys.argv [2]), worker_address = sys.argv [3])
