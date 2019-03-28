#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  simulate_search.py
#  simsearch
# 
#  Created by Lars Yencken on 03-09-2010.
#  Copyright 2010 Lars Yencken. All rights reserved.
#
#  Revised by Aurélien Nioche on 23-03-2019

"""
A script to simulate how users might search with the system. Query paths
generated by this script can be analysed as a form of intrinsic evaluation.
"""

import os
import sys
import optparse
import codecs
import random

import consoleLog

from simsearch import settings, stroke, models


def simulate_search(output_file, strategy='greedy',
        k=settings.N_NEIGHBOURS_RECALLED, error_rate=0.0):
    """
    Simulate user searches on every query/target pair from the flashcard
    dataset, using one of the available strategies. The resulting query paths
    are dumped to the specified file.
    """
    if strategy == 'greedy':
        search_fn = _greedy_search
    elif strategy == 'shortest':
        search_fn = _breadth_first_search
    elif strategy == 'random':
        random.seed(123456789)
        search_fn = _random_stumble
    else:
        raise ValueError(strategy)

    traces = []
    for query, target in consoleLog.withProgress(_load_search_examples()):
        path = search_fn(query, target, k=k, error_rate=error_rate)
        traces.append((query, target, path))

    TraceFile.save(traces, output_file)
    print 'Paths dumped to %s' % output_file


class TraceFile(object):
    """A basic human-readable query path file format."""
    @staticmethod
    def save(traces, filename):
        with codecs.open(filename, 'w', 'utf8') as ostream:
            print >> ostream, u"#query\ttarget\tvia"
            for query, target, path in traces:
                if path:
                    assert path[0] == query
                    # have at least a partial search
                    if path[-1] == target:
                        # success
                        print >> ostream, u'%s\t%s\t[%s]' % (query, target, ''.join(path[1:-1]))

                    else:
                        # failure with partial path
                        print >> ostream, u'%s\t(%s)\t[%s]' % (query, target, ''.join(path[1:]))
                
                else:
                    # failure without partial path
                    print >> ostream, u'%s\t(%s)\tNone' % (query, target)

    @staticmethod
    def load(filename):
        traces = []
        with codecs.open(filename, 'r', 'utf8') as istream:
            header = istream.next()
            assert header.startswith('#')
            for line in istream:
                query, target, path = line.rstrip().split('\t')
                if len(target) != 1:
                    target = target.strip('()')
                    was_success = False
                    assert len(target) == 1
                else:
                    was_success = True

                if path == 'None':
                    path = None
                else:
                    path = [query] + list(path.strip('[]'))
                    if was_success:
                        path.append(target)

                traces.append((query, target, path))

        return traces


def _load_search_examples():
    flashcard_file = os.path.join(settings.DATA_DIR, 'similarity', 'flashcard')
    results = []
    with codecs.open(flashcard_file, 'r', 'utf8') as istream:
        for line in istream:
            _id, query, targets = line.split()
            for target in targets:
                results.append((query, target))

    return results


def _greedy_search(query, target, limit=5, k=settings.N_NEIGHBOURS_RECALLED, error_rate=0.0):
    """
    Simulate a search between the query and target where the user always
    chooses the next kanji which looks closest to the target.
    """
    assert query != target
    if query not in sed or target not in sed:
        # we can't simulate this search type without using a distance
        # heuristic
        return

    path = [query]
    while path[-1] != target and len(path) <= limit:
        assert path[0] == query

        new_query = path[-1]
        neighbours = _get_neighbours(new_query, k=k)

        if target in neighbours:
            if error_rate == 0.0 or random.random() < (1 - error_rate)**k:
                # Success!
                path.append(target)
                return path

            # Recognition error =(
            neighbours.remove(target)

        # Our options are neighbours we haven't tried yet
        options = neighbours.difference(path)

        if not options:
            # Search exhausted =(
            break

        # Choose the one visually most similar to the target
        _d, neighbour = min((sed(n, target), n) for n in options)
        path.append(neighbour)

    assert path[0] == query and path[-1] != target

    return path


def _breadth_first_search(query, target, limit=5,
        k=settings.N_NEIGHBOURS_RECALLED, error_rate=0.0):
    """
    Perform breadth first search to a fixed depth limit, returning the
    shortest path from the query to the target (within the limit).
    """
    paths = [[query]]
    shortest = {query}  # has a shortest path been checked
    while paths:
        current = paths.pop(0)
        current_query = current[-1]
        neighbours = _get_neighbours(current_query, k=k)

        if target in neighbours:
            current.append(target)
            assert current[0] == query
            return current

        if len(current) < limit:
            # visit in similarity order if possible
            try:
                neighbours = sorted(neighbours, key=lambda n: sed(n, target))
            except KeyError:
                pass
            neighbours = [n for n in neighbours if n not in shortest]
            shortest.update(neighbours)
            paths.extend((current + [n]) for n in neighbours)


def _random_stumble(query, target, limit=5, k=settings.N_NEIGHBOURS_RECALLED, error_rate=0.0):
    """
    A worst-case simulation of user search, completely unguided by the
    target kanji (except for the initial query).
    """
    path = [query]
    while len(path) <= limit:
        neighbours = _get_neighbours(path[-1], k=k)
        if target in neighbours:
            if error_rate == 0.0 or random.random() < (1 - error_rate)**k:
                return path + [target]

            neighbours.remove(target)

        path.append(random.choice(list(neighbours)))

    return path


class Cache(object):
    """
    A simple cache wrapper whose contents never expire. Useful for reducing
    expensive calls on small datasets.
    """
    def __init__(self, f):
        self.f = f
        self._cached = {}

    def __call__(self, *args, **kwargs):
        key = args + tuple(kwargs.items())
        if key not in self._cached:
            self._cached[key] = self.f(*args, **kwargs)

        return self._cached[key]

    def __contains__(self, key):
        # workaround for StrokeEditDistance also acting like a container
        return self.f.__contains__(key)


@Cache
def _get_neighbours(query, k=settings.N_NEIGHBOURS_RECALLED):
    neighbours = set(n.kanji for n in models.Node.objects.get(
            pivot=query).neighbours[:k])
    return neighbours


sed = Cache(stroke.StrokeEditDistance())

# ---------------------------------------------------------------------------- #


def _create_option_parser():
    usage = \
        """%prog [options] output_file
        
        Simulate queries through the search graph, dumping the traces to the given
        file."""

    parser = optparse.OptionParser(usage)

    parser.add_option(
        '--strategy', action='store', type='choice',
        choices=['greedy', 'shortest', 'random'], dest='strategy',
        default='greedy',
        help='The search strategy to use ([greedy]/shortest/random)')
    
    parser.add_option(
        '-k', action='store', type='int',
        default=settings.N_NEIGHBOURS_RECALLED, dest='k',
        help='The number of neighbours displayed each query [%d]' % \
        settings.N_NEIGHBOURS_RECALLED)

    parser.add_option(
        '-e', action='store', type='float',
        default=0.0, dest='error_rate',
        help='Factor in an estimated recognition error rate [0.0]')

    return parser


def main(argv):
    parser = _create_option_parser()
    (options, args) = parser.parse_args(argv)

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)

    simulate_search(args[0], strategy=options.strategy, k=options.k, error_rate=options.error_rate)

# ---------------------------------------------------------------------------- #


if __name__ == '__main__':
    main(sys.argv[1:])
