#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This script reads a graphviz file representing a graph and an arena file containing the physical location of
# available CASUs and generates the configuration files needed by the inter-species DOMSET tools.

import argparse
import copy
import inspyred
import pygraphviz
import random
import yaml

BEE_ARENA = 'beearena'
INTER_CASU_DISTANCE = 9

CAMERA_SCALE = 189
CAMERA_MARGIN_LEFT = 100
CAMERA_MARGIN_RIGHT = 100
CAMERA_MARGIN_TOP = 100
CAMERA_MARGIN_BOTTOM = 100

class AbstractGenerator:
    def __init__ (self, _graph_filename, _arena_filename, _project_name, _number_copies):
        self.project_name = _project_name
        self.number_copies = _number_copies
        self.graph = pygraphviz.AGraph (_graph_filename)
        with open (_arena_filename, 'r') as fd:
            self.arena = yaml.safe_load (fd)
        self.node_CASUs = {
            AbstractGenerator.graph_node_str (graph_index, node.name) : []
            for node in self.graph.nodes ()
            for graph_index in range (1, self.number_copies + 1)
        }
        self.available_CASUs = {key : True for key in self.arena [BEE_ARENA].keys ()}
        self.available_arena_locations = {}
        for casu_key in self.arena [BEE_ARENA].keys ():
            ns = self.__nearby_CASUs (casu_key)
            if len (ns) > 0:
                self.available_arena_locations [casu_key] = ns
        self.solution = {}

    def print_available_arena_locations (self):
        for k, v in self.available_arena_locations.iteritems():
            print (k, v)

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

    def can_place_arena (self, casu_1_key, casu_2_key):
        x1 = self.arena [BEE_ARENA][casu_1_key]['pose']['x']
        y1 = self.arena [BEE_ARENA][casu_1_key]['pose']['y']
        x2 = self.arena [BEE_ARENA][casu_2_key]['pose']['x']
        y2 = self.arena [BEE_ARENA][casu_2_key]['pose']['y']
        return (abs (x1 - x2) == INTER_CASU_DISTANCE and y1 == y2) or (x1 == x2 and abs (y1 - y2) == INTER_CASU_DISTANCE)

    def casu_distance (self, casu_1_key, casu_2_key):
        x1 = self.arena [BEE_ARENA][casu_1_key]['pose']['x']
        y1 = self.arena [BEE_ARENA][casu_1_key]['pose']['y']
        x2 = self.arena [BEE_ARENA][casu_2_key]['pose']['x']
        y2 = self.arena [BEE_ARENA][casu_2_key]['pose']['y']
        return (abs (x1 - x2) + abs (y1 - y2)) / INTER_CASU_DISTANCE

    def assign_CASUs_to_nodes (self):
        """
        Go through the solution attribute and assign CASUs to the nodes in the logical graph.
        :return:
        """
        print (self.solution)
        for k, v in self.solution.iteritems ():
            key = AbstractGenerator.graph_node_str (k [0], k[1][0])
            self.node_CASUs [key].append (v [0])
            key = AbstractGenerator.graph_node_str (k [0], k[1][1])
            self.node_CASUs [key].append (v [1])
        print ('CASUs assigned to logical nodes')
        for k, v in self.node_CASUs.iteritems ():
            print ('{}: {}'.format (k, v))

    def create_CASU_config_file (self):
        """
        Create the configuration file used by the CASU controllers manager.
        This file contains which CASUs are used, the CASU neighbourhood message network, the cropping video parameters.
        :return:
        """
        video = self.__compute_video_cropping ()
        video ['frames_per_second'] = 10
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
                'edges': [
                    [AbstractGenerator.graph_node_str (graph_index, n.name) for n in e]
#                    [str (e[0].name), str (e[1].name)]
                    for e in self.graph.edges ()
                    for graph_index in range (1, self.number_copies + 1)
                ],
                'node_CASUs': {
                    k: [int (c [-3:]) for c in v]
                    for k, v in self.node_CASUs.iteritems ()
                }
            },
            'experiment_duration': 25,
            'video': video
        }
        fn = '{}.config'.format (self.project_name)
        with open (fn, 'w') as fd:
            yaml.dump (contents, fd, default_flow_style = False)
            fd.close ()

    def create_ISI_nodemasters_file (self):
        contents = {
            'master_casus': {
                k: min ([int (c [-3:]) for c in v])
                for k, v in self.node_CASUs.iteritems ()
            }
        }
        fn = '{}.nodemasters'.format (self.project_name)
        with open (fn, 'w') as fd:
            yaml.dump (contents, fd, default_flow_style = False)
            fd.close ()

    def create_arena_location_file (self):
        fn = '{}.html'.format (self.project_name)
        with open (fn, 'w') as fd:
            fd.write ('<html><body><p>Place an arena between CASUs<ul>')
            arenas = self.solution.values ()
            arenas.sort ()
            for v in arenas:
                casu1 = int (v [0][-3:])
                casu2 = int (v [1][-3:])
                fd.write ('<li>{} and {}</li>'.format (casu1, casu2))
            fd.write ('</ul></p></body></html>')
            fd.close ()

    @staticmethod
    def graph_node_str (graph_index, graph_node):
        # type: (int, object) -> str
        return 'G{}_{}'.format (graph_index, str (graph_node))



    def __used_casus (self):
        result = []
        for v in self.node_CASUs.values ():
            result.extend ([int (c [-3:]) for c in v])
        return result

    def __compute_video_cropping (self):
        used_casus = self.__used_casus ()
        xs = [self.arena [BEE_ARENA]['casu-{:03d}'.format (_c)]['pose']['x'] for _c in used_casus]
        ys = [self.arena [BEE_ARENA]['casu-{:03d}'.format (_c)]['pose']['y'] for _c in used_casus]
        result = {
            'crop_left': CAMERA_SCALE * (min (xs) + 36)/ INTER_CASU_DISTANCE + CAMERA_MARGIN_LEFT,
            'crop_right': 250,
            'crop_bottom': 150,
            'crop_top': CAMERA_SCALE * (min (ys) + 36)/ INTER_CASU_DISTANCE + CAMERA_MARGIN_TOP
        }
        return result

    def cmp_casu_keys (self, key1, key2):
        """
        Compare two CASUs based on their physical location in the bee
        arena.  This takes into account stadium arena placement: either
        to the right (increasing x coordinate) or to the bottom
        (decreasing y coordinate) of a selected CASU.  When searching
        for CASUs to place stadium arenas, we go from CASUs in the top
        left corner of the bee arena.
        """
        x1 = self.arena [BEE_ARENA][key1]['pose']['x']
        y1 = self.arena [BEE_ARENA][key1]['pose']['y']
        x2 = self.arena [BEE_ARENA][key2]['pose']['x']
        y2 = self.arena [BEE_ARENA][key2]['pose']['y']
        if x1 == x2 and y1 == y2:
            return 0
        elif y1 > y2 or (y1 == y2 and x1 < x2):
            return -1
        else:
            return 1

# Exhaustive
class ExhaustiveSearch (AbstractGenerator):
    def __init__ (self, _graph_filename, _arena_filename, _project_name, _number_copies):
        AbstractGenerator.__init__ (self, _graph_filename, _arena_filename, _project_name, _number_copies)

    def run (self):
        list_edges = self.graph.edges ()
        if self.__main_loop (list_edges, self.available_arena_locations, 1):
            print ('Found a solution')
            self.assign_CASUs_to_nodes ()
            self.create_CASU_config_file ()
            self.create_ISI_nodemasters_file ()
            self.create_arena_location_file ()

    def __main_loop (self, list_edges, available_arena_locations, graph_index):
        if len (list_edges) > 0 and len (available_arena_locations) == 0:
            return False
        elif len (list_edges) == 0:
            if graph_index == self.number_copies:
                return True
            else:
                return self.__main_loop (self.graph.edges (), available_arena_locations, graph_index + 1)
        new_list_edges = list_edges [1:]
        this_edge = list_edges [0]
        list_keys = available_arena_locations.keys ()
        list_keys.sort (cmp = self.cmp_casu_keys)
        for casu1_key in list_keys:
            casus_data = available_arena_locations [casu1_key]
            for casu2_key in casus_data:
                print ('Trying placing edge {} in CASUs {} {}'.format (this_edge, casu1_key, casu2_key))
                new_available_arena_locations = copy.copy (available_arena_locations)
                del new_available_arena_locations [casu1_key]
                if casu2_key in new_available_arena_locations:
                    del new_available_arena_locations [casu2_key]
                if self.__main_loop (new_list_edges, new_available_arena_locations, graph_index):
                    self.solution [(graph_index, this_edge)] = (casu1_key, casu2_key)
                    return True
        return False

class MinimizeNodeCASUsDistance_EvolutionaryAlgorithm (AbstractGenerator):
    def __init__ (self, _graph_filename, _arena_filename, _project_name, _number_copies):
        AbstractGenerator.__init__ (self, _graph_filename, _arena_filename, _project_name, _number_copies)
        self.chromosome_size = self.number_copies * len (self.graph.edges ())
        self.possible_shifts = {}
        for casu_key_1 in self.arena [BEE_ARENA].keys ():
            ps = []
            for casu_key_2 in self.arena [BEE_ARENA].keys ():
                if self.can_place_arena (casu_key_1, casu_key_2) and casu_key_2 in self.available_arena_locations:
                    ps.append (casu_key_2)
            if len (ps) > 0:
                self.possible_shifts [casu_key_1] = ps

    def run (self):
        rng = random.Random ()
        import logging
        logger = logging.getLogger ('inspyred.ec')
        logger.setLevel (logging.DEBUG)
        file_handler = logging.FileHandler ('inspyred.log', mode='w')
        file_handler.setLevel (logging.DEBUG)
        formatter = logging.Formatter ('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter (formatter)
        logger.addHandler (file_handler)

        ea = inspyred.ec.EvolutionaryComputation (rng)
        ea.selector = inspyred.ec.selectors.tournament_selection
        ea.variator = [
        #    inspyred.ec.variators.n_point_crossover,
            self.mutator_shift__,
        ]
        ea.replacer = inspyred.ec.replacers.generational_replacement
        ea.terminator = inspyred.ec.terminators.generation_termination
        ea.logger = logger
        final_pop = ea.evolve (
            generator = self.generator,
            evaluator = self.evaluate____,
            maximize = False,
            pop_size = 100,
            max_generations = 50,
            tournament_size = 5,
            num_selected = 100,
            num_elites = 1
        )
        for c in final_pop:
            print (c)

    def _random_neighbour (self, casu_key, random):
        index = random.randint (0, len (self.available_arena_locations [casu_key]) - 1)
        return self.available_arena_locations [casu_key][index]

    def generator (self, random, args):
        result = self.available_arena_locations.keys ()
        random.shuffle (result)
        result = result [:self.chromosome_size]
        result = [(c, self._random_neighbour (c, random)) for c in result]
        return result

    def mutator_shift__ (self, random, candidates, args):
        result = []
        for c in candidates:
            result.append (self.mutator_shift (random, c, args))
        return result

    def mutator_shift (self, random, candidate, args):
        index = random.randint (0, self.chromosome_size - 1)
        old_casu = candidate [index][0]
        new_casu = self.possible_shifts [old_casu][random.randint (0, len (self.possible_shifts [old_casu]) - 1)]
        new_direction = self._random_neighbour (new_casu, random)
        result = copy.copy (candidate)
        result [index] = (new_casu, new_direction)
        return result

    CASU_COLLISION_PENALTY = 1000

    def evaluate____ (self, candidates, args):
        result = []
        for c in candidates:
            result.append (self.evaluate (c))
        return result

    def evaluate (self, candidate):
        result = 0
        used_CASUs = {key : False for key in self.arena [BEE_ARENA].keys ()}
        node_CASUs = copy.deepcopy (self.node_CASUs)
        index = 0
        for edge in self.graph.edges ():
            for graph_index in range (1, self.number_copies + 1):
                casu_key_1, casu_key_2 = candidate [index]
                for a_casu_key in [casu_key_1, casu_key_2]:
                    if used_CASUs [a_casu_key]:
                        result += MinimizeNodeCASUsDistance_EvolutionaryAlgorithm.CASU_COLLISION_PENALTY
                    used_CASUs [a_casu_key] = True
                for a_node, a_casu_key in zip ([AbstractGenerator.graph_node_str (graph_index, n) for n in edge], [casu_key_1, casu_key_2]):
                    for b_casu_key in node_CASUs [a_node]:
                        result += self.casu_distance (a_casu_key, b_casu_key)
                    node_CASUs [a_node].append (a_casu_key)
                index += 1
        return result

ALGORITHMS = {
    ExhaustiveSearch.__name__ : ExhaustiveSearch,
    MinimizeNodeCASUsDistance_EvolutionaryAlgorithm.__name__ : MinimizeNodeCASUsDistance_EvolutionaryAlgorithm,
}

def main ():
    args = parse_arguments ()
    if args.project is None:
        project_name = args.graph
        if project_name.lower ().endswith ('.gv'):
            project_name = project_name [:-3]
        elif project_name.lower ().endswith ('.dot'):
            project_name = project_name [:-4]
    else:
        project_name = args.project
    if args.algorithm == ExhaustiveSearch.__name__:
        ag = ExhaustiveSearch (args.graph, args.arena, project_name, args.copy)
    elif args.algorithm == MinimizeNodeCASUsDistance_EvolutionaryAlgorithm.__name__:
        ag = MinimizeNodeCASUsDistance_EvolutionaryAlgorithm (args.graph, args.arena, project_name, args.copy)
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
    parser.add_argument (
        '--project', '-p',
        metavar = 'NAME',
        type = str,
        help = 'Name to be used in the config and nodemasters files.  By default is the name of the Graphviz file.'
    )
    parser.add_argument (
        '--copy', '-c',
        metavar = 'N',
        type = int,
        default = 1,
        help = 'How many copies of the graph should be physically created.'
    )
    parser.add_argument (
        '--algorithm',
        choices = ALGORITHMS.keys (),
        default = 'ExhaustiveSearch',
        help = 'Which algorithm to use'
    )
    return parser.parse_args ()

if __name__ == '__main__':
    main ()
