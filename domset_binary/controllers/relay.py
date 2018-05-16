#!/usr/bin/env python
# -*- coding: utf-8 -*-


import zmq

import threading
import time

import json

class Relay:

    def __init__(self):
        ''' Create and connect sockets '''
        self.context = zmq.Context(1)

        self.sub_internet = self.context.socket(zmq.SUB)
        # Bind the address to listen to CATS
        self.sub_internet.bind('tcp://*:5556')
        self.sub_internet.setsockopt(zmq.SUBSCRIBE,'casu-')
        #self.sub_internet.setsockopt(zmq.SUBSCRIBE,'casu-007')
        print('Internet subscriber bound!')

        self.pub_internet = self.context.socket(zmq.PUB)
        # Bind the address to publish to CATS
        self.pub_internet.bind('tcp://*:5555')
        print('Internet publisher bound!')

        self.pub_local = self.context.socket(zmq.PUB)
        self.pub_local.bind('tcp://*:10105')
        print('Local publisher bound!')

        self.sub_local = self.context.socket(zmq.SUB)

        #cfg1 - circ5
        self.sub_local.connect('tcp://bbg-007:50701')
        self.sub_local.connect('tcp://bbg-005:50503')
        self.sub_local.connect('tcp://bbg-005:50504')
        self.sub_local.connect('tcp://bbg-006:50604')
        self.sub_local.connect('tcp://bbg-008:50803')
        self.sub_local.connect('tcp://bbg-018:51804')
        self.sub_local.connect('tcp://bbg-007:50704')
        self.sub_local.connect('tcp://bbg-010:51001')
        self.sub_local.connect('tcp://bbg-018:51803')
        self.sub_local.connect('tcp://bbg-006:50603')
        '''#cfg1
        self.sub_local.connect('tcp://bbg-007:50701')
        self.sub_local.connect('tcp://bbg-005:50503')
        self.sub_local.connect('tcp://bbg-005:50504')
        self.sub_local.connect('tcp://bbg-006:50604')
        self.sub_local.connect('tcp://bbg-008:50803')
        self.sub_local.connect('tcp://bbg-008:50801')
        self.sub_local.connect('tcp://bbg-007:50704')
        self.sub_local.connect('tcp://bbg-010:51001')
        self.sub_local.connect('tcp://bbg-018:51803')
        self.sub_local.connect('tcp://bbg-006:50603')
        #cfg2
        self.sub_local.connect('tcp://bbg-016:51601')
        self.sub_local.connect('tcp://bbg-012:51201')
        self.sub_local.connect('tcp://bbg-014:51404')
        self.sub_local.connect('tcp://bbg-014:51401')
        self.sub_local.connect('tcp://bbg-015:51503')
        self.sub_local.connect('tcp://bbg-016:51603')
        self.sub_local.connect('tcp://bbg-016:51604')
        self.sub_local.connect('tcp://bbg-017:51701')
        self.sub_local.connect('tcp://bbg-017:51703')
        self.sub_local.connect('tcp://bbg-017:51704')
        '''
        self.sub_local.setsockopt(zmq.SUBSCRIBE,'cats')
        print('Local subscribers bound!')

        self.incoming_thread = threading.Thread(target = self.recieve_from_internet)
        self.outgoing_thread = threading.Thread(target = self.recieve_from_local)

        self.stop = False

        self.incoming_thread.start()
        self.outgoing_thread.start()

    def recieve_from_internet(self):
        while not self.stop:
            [name, msg, sender, data] = self.sub_internet.recv_multipart()
            print('Received from cats: ' + name + ';' + msg + ';' + sender + ';' + data)
            self.pub_local.send_multipart([name,msg,sender,data])

    def recieve_from_local(self):
        while not self.stop:
            [name, msg, sender, data] = self.sub_local.recv_multipart()
            #print('Received from arena: ' + name + ';' + msg + ';' + sender + ';' + "{0:.2f}".format(float(data)))
            print('Received from arena: ' + name + ';' + msg + ';' + sender + ';' + data)
            self.pub_local.send_multipart([sender,msg,name,data])

if __name__ == '__main__':

    relay = Relay()

    cmd = 'a'
    while cmd != 'q':
        cmd = raw_input('To stop the program press q<Enter>')

    relay.stop = True
