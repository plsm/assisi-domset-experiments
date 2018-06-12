#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This script reads a graphviz file representing a graph and an arena file containing the physical location of
# available CASUs and generates the configuration files needed by the inter-species DOMSET tools.

import argparse
import copy
import pygraphviz
import yaml

BEE_ARENA = 'beearena'
INTER_CASU_DISTANCE = 9

class AbstractGenerator:
    def __init__ (self, _graph_filename, _arena_filename):
        self.graph = pygraphviz.AGraph (_graph_filename)
        with open (_arena_filename, 'r') as fd:
            self.arena = yaml.safe_load (fd)
        self.node_CASUs = {str (node.name) : [] for node in self.graph.nodes ()}
        #print (self.node_CASUs)
        self.available_CASUs = {key : True for key in self.arena [BEE_ARENA].keys ()}
        #print (self.available_CASUs)
        self.available_arena_locations = {}
        for casu_key in self.arena [BEE_ARENA].keys ():
            ns = self.__nearby_CASUs (casu_key)
            if len (ns) > 0:
                self.available_arena_locations [casu_key] = ns
        for k, v in self.available_arena_locations.iteritems():
            print (k, v)
        self.solution = {}

    def __nearby_CASUs (self, casuc_key):
        result = []
        xc = self.arena [BEE_ARENA][casuc_key]['pose']['x']
        yc = self.arena [BEE_ARENA][casuc_key]['pose']['y']
        for casup_key, casu_data in self.arena [BEE_ARENA].iteritems ():
            xp = casu_data ['pose']['x']
            yp = casu_data ['pose']['y']
            if (xc + INTER_CASU_DISTANCE == xp and yc == yp) or (xc == xp and yc == yp + INTER_CASU_DISTANCE):
                result.append (casup_key)
        return result

    def assign_CASUs_to_nodes (self):
        '''
        Go through the solution attribute and assign CASUs to the nodes in the logical graph.
        :return:
        '''
        for k, v in self.solution.iteritems ():
            self.node_CASUs [k [0]].append (v [0])
            self.node_CASUs [k [1]].append (v [1])
        print ('CASUs assigned to logical nodes')
        for k, v in self.node_CASUs.iteritems ():
            print ('{}: {}'.format (k, v))

    def create_CASU_config_file (self):
        '''
        Create the configuration file used by the CASU controllers manager.
        This file contains which CASUs are used, the CASU neighbourhood message network, the cropping video parameters.
        :return:
        '''
        contents = {
            'controllers': {
                'domset': {
                    'args': [],
                    'casus': self.__used_casus (),
                    'extra': [
                        '/home/assisi/assisi/pedro/assisi-domset-experiments/controllers/domset_interspecies.py',
                        '/home/assisi/assisi/pedro/assisi-domset-experiments/manager/zmq_sock_utils.py'
                        ],
                    'main': '/home/assisi/assisi/pedro/assisi-domset-experiments/manager/workers.py',
                    'results': []
                }
            },
            'deploy': {
                'args': {
                    'add_casu_number': True,
                    'add_worker_address': True
                },
                'prefix': 'assisi/domset',
                'user': 'pedro'
            },
            'graph': {
                'edges': [[str (e[0].name), str (e[1].name)] for e in self.graph.edges ()],
                'node_CASUs': {
                    k: [int (c [-3:]) for c in v]
                    for k, v in self.node_CASUs.iteritems ()
                }
            },
            'experiment_duration': 25
        }
        with open ('project.config', 'w') as fd:
            yaml.dump (contents, fd, default_flow_style = False)
            fd.close ()
        print ([[e[0].name, e[1].name] for e in self.graph.edges ()])

    def __used_casus (self):
        result = []
        for v in self.node_CASUs.values ():
            result.extend ([int (c [-3:]) for c in v])
        return result

# Exhaustive
class ExhaustiveSearch (AbstractGenerator):
    def __init__ (self, _graph_filename, _arena_filename):
        AbstractGenerator.__init__ (self, _graph_filename, _arena_filename)

    def run (self):
        list_edges = self.graph.edges ()
        if self.__main_loop (list_edges, self.available_arena_locations):
            print ('Found a solution')
            self.assign_CASUs_to_nodes ()
            self.create_CASU_config_file ()
            #for k, v in self.solution.iteritems ():
            #    print (k, v)

    def __main_loop (self, list_edges, available_arena_locations):
        if len (list_edges) > 0 and len (available_arena_locations) == 0:
            return False
        elif len (list_edges) == 0:
            return True
        new_list_edges = list_edges [1:]
        this_edge = list_edges [0]
        list_keys = available_arena_locations.keys ()
        list_keys.sort ()
        for casu1_key in list_keys:
            casus_data = available_arena_locations [casu1_key]
        #for casu1_key, casus_data in available_arena_locations.iteritems ():
            for casu2_key in casus_data:
                print ('Trying placing edge {} in CASUs {} {}'.format (this_edge, casu1_key, casu2_key))
                new_available_arena_locations = copy.copy (available_arena_locations)
                del new_available_arena_locations [casu1_key]
                if casu2_key in new_available_arena_locations:
                    del new_available_arena_locations [casu2_key]
                if self.__main_loop (new_list_edges, new_available_arena_locations):
                    self.solution [this_edge] = (casu1_key, casu2_key)
                    return True
        return False

def main ():
    args = parse_arguments ()
    ag = ExhaustiveSearch (args.graph, args.arena)
    ag.run ()

def parse_arguments ():
    parser = argparse.ArgumentParser (
        description = 'Read a graphviz file representing a graph and an arena file containing the physical location '
                      'of available CASUs and generates the configuration files needed by the inter-species DOMSET '
                      'tools.',
        argument_default = None
    )
    parser.add_argument (
        '--graph', '-g',
        type = str,
        metavar = 'FILENAME',
        required = True,
        help = 'Graphviz file containing the logical graph to be used.'
    )
    parser.add_argument (
        '--arena', '-a',
        metavar = 'FILENAME',
        type = str,
        required = True,
        help = 'Filename containing the description of available physical CASUs and their sockets'
    )
    return parser.parse_args ()

if __name__ == '__main__':
    main ()
