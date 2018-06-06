#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import stat
import time
import yaml
import zmq

import assisipy.deploy
import assisipy.assisirun
import assisipy.collect_data

import util

class WorkerSettings:
    """
    Worker settings used by the master program to deploy the workers.
    These settings specify the CASU that the worker will control,
    the ZMQ address where the worker will listen for commands from the manager,
    and the parameters of the RTC file.
    """
    def __init__ (self, dictionary):
        self.casu_number = dictionary ['casu_number']
        self.wrk_addr    = dictionary ['wrk_addr']
        self.pub_addr    = dictionary ['pub_addr']
        self.sub_addr    = dictionary ['sub_addr']
        self.msg_addr    = dictionary ['msg_addr']

    def key (self):
        return 'casu-%03d' % (self.casu_number)

    def to_dep (self, controller, extra):
        return (
            self.key () ,
            {
                'controller' : controller
              , 'extra'      : extra
              , 'args'       : [str (self.casu_number), 'tcp://*:%s' % (self.wrk_addr.split (':') [2])]
              , 'hostname'   : self.wrk_addr.split (':') [1][2:]
              , 'user'       : 'assisi'
              , 'prefix'     : 'pedro/domset'
              , 'results'    : []
            })

    def to_arena (self):
        return (
            self.key () ,
            {
                'pub_addr' : self.pub_addr
              , 'sub_addr' : self.sub_addr
              , 'msg_addr' : self.msg_addr
            })

    def connect_to_worker (self):
        """
        Connect to the worker and return the socket.
        """
        context = zmq.Context ()
        print ("Connecting to worker at %s responsible for casu #%d..." % (self.wrk_addr, self.casu_number))
        socket = context.socket (zmq.REQ)
        socket.connect (self.wrk_addr)
        return socket

    def __str__ (self):
        return 'casu_number : %d , wrk_addr : %s , pub_addr : %s , sub_addr : %s , msg_addr : %s' % (
            self.casu_number, self.wrk_addr, self.pub_addr, self.sub_addr, self.msg_addr)

def load_worker_settings (filename):
    """
    Return a list with the worker settings loaded from a file with the given name.
    """
    print ("\n* ** Loading worker settings...")
    file_object = open (filename, 'r')
    dictionary = yaml.load (file_object)
    file_object.close ()
    list_worker_settings = [
        WorkerSettings (element)
        for element in dictionary ['workers']]
    print ("     Loaded worker settings.")
    return list_worker_settings

BASE_PATH = 'tmp'
ASSISI_FILE_NAME = os.path.join (BASE_PATH, 'workers.assisi')

def deploy_and_run_workers (list_worker_settings, controller, extra, workers_graph):
    # type: (list, object, object, graph.Graph) -> object
    """

    :param list_worker_settings:
    :param controller:
    :param extra:
    :param workers_graph:
    """
    print ('\n\n* ** Worker Apps Launch')
    # create assisi file
    fp_assisi = open (ASSISI_FILE_NAME, 'w')
    yaml.dump ({'arena' : 'workers.arena'}, fp_assisi, default_flow_style = False)
    yaml.dump ({'dep' : 'workers.dep'}, fp_assisi, default_flow_style = False)
    yaml.dump ({'nbg' : 'workers.nbg'}, fp_assisi, default_flow_style = False)
    fp_assisi.close ()
    print ("Created assisi file")
    # create arena file
    fp_arena = open ('tmp/workers.arena', 'w')
    yaml.dump ({
        util.BEE_LAYER : dict ([ws.to_arena () for ws in list_worker_settings]),
        # Not sure if this is needed
        util.MANAGER_LAYER : {
            'cats' : {
                'sub_addr' : 'tcp://control-workstation:5555' ,
                'pub_addr' : 'tcp://control-workstation:5556' ,
            #    'sub_addr' : 'tcp://control-workstation:35555' ,
            #    'pub_addr' : 'tcp://control-workstation:35556' ,
                'msg_addr' : 'tcp://control-workstation:49876'
                }
            }
        }, fp_arena, default_flow_style = False)
    fp_arena.close ()
    print ("Created arena file")
    # create dep file
    fp_dep = open ('tmp/workers.dep', 'w')
    yaml.dump ({
        util.BEE_LAYER : dict ([ws.to_dep (controller, extra) for ws in list_worker_settings]),
        # Not sure if this is needed
        util.MANAGER_LAYER : {
            'cats' : {
                'hostname': 'localhost' ,
                'user': 'assisi' ,
                'prefix': 'pedro/domset' ,
                'controller' : os.path.join (os.path.dirname (os.path.dirname (os.path.abspath (__file__))), 'controllers/dummy.py')
                }
            }
        }, fp_dep, default_flow_style = False)
    fp_dep.close ()
    print ("Created dep file")
    # create neighbourhood file
    workers_graph.create_neighbourhood_dot ().write ('tmp/workers.nbg')
    # deploy the workers
    d = assisipy.deploy.Deploy (ASSISI_FILE_NAME)
    d.prepare ()
    d.deploy ()
    ar = assisipy.assisirun.AssisiRun (ASSISI_FILE_NAME)
    ar.run ()
    print ("Workers have finished")

def collect_data_from_workers (list_worker_settings, destination):
    dc = assisipy.collect_data.DataCollector (ASSISI_FILE_NAME, logpath = destination)
    dc.collect ()
    time.sleep (1)
    for ws in list_worker_settings:
        try:
            os.makedirs (os.path.join (destination, ws.key ()))
        except:
            pass
        try:
            source = os.path.join (destination, os.path.join ('data_workers', os.path.join (util.BEE_LAYER, ws.key ())))
            for filename in os.listdir (source):
                new = os.path.join (os.path.join (destination, ws.key ()), filename)
                os.rename (os.path.join (source, filename), new)
                os.chmod (new, stat.S_IREAD)
            os.rmdir (source)
        except:
            print ('[W] problems moving files for CASU {}'.format (ws.key ()))
    os.rmdir (os.path.join (destination, os.path.join ('data_workers', util.BEE_LAYER)))
    try:
        os.rmdir (os.path.join (destination, 'data_workers'))
    except Exception as e:
        print (e)
