#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  simulate_search.py
#  simsearch
# 
#  Created by Lars Yencken on 03-09-2010.
#  Copyright 2010 Lars Yencken. All rights reserved.
#

"""
A script to simulate how users might search with the system. Query paths
generated by this script can be analysed as a form of intrinsic evaluation.
"""

import os
import sys
import optparse
import codecs

from django.conf import settings
from consoleLog import withProgress

from simsearch.search import stroke, models

def simulate_search(output_file, strategy='greedy'):
    """
    Simulate user searches on every query/target pair from the flashcard
    dataset, using one of the available strategies. The resulting query paths
    are dumped to the specified file.
    """
    if strategy == 'greedy':
        search_fn = _greedy_search
    elif strategy == 'shortest':
        search_fn = _breadth_first_search
    else:
        raise ValueError(strategy)

    traces = []
    for query, target in withProgress(_load_search_examples()):
        path = search_fn(query, target)
        traces.append((query, target, path))

    TraceFile.dump(traces, output_file)
    print 'Paths dumped to %s' % output_file

class TraceFile(object):
    "A basic human-readable query path file format."
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
                        print >> ostream, u'%s\t%s\t[%s]' % (query, target,
                                ''.join(path[1:-1]))
                    else:
                        # failure with partial path
                        print >> ostream, u'%s\t(%s)\t[%s]' % (query, target,
                                ''.join(path[1:]))
                
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

def _greedy_search(query, target, limit=5):
    """
    Simulate a search between the query and target where the user always
    chooses the next kanji which looks closest to the target.
    """
    if query not in sed or target not in sed:
        # we can't simulate this search type without using a distance
        # heuristic
        return

    path = [query]
    while path[-1] != target and len(path) <= limit:
        assert path[0] == query

        new_query = path[-1]
        neighbours = _get_neighbours(new_query)

        if target in neighbours:
            # Success!
            path.append(target)
        else:
            # Our options are neighbours we haven't tried yet
            options = neighbours.difference(path)

            if not options:
                # Search exhausted =(
                break

            # Choose the one visually most similar to the target
            _d, neighbour = min((sed(n, target), n) for n in options)
            path.append(neighbour)

    assert path[0] == query

    return path

def _breadth_first_search(query, target, limit=5):
    """
    Perform breadth first search to a fixed depth limit, returning the
    shortest path from the query to the target (within the limit).
    """
    paths = [[query]]
    shortest = set([query]) # has a shortest path been checked
    while paths:
        current = paths.pop(0)
        current_query = current[-1]
        neighbours = _get_neighbours(current_query)

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

class cache(object):
    """
    A simple cache wrapper whose contents never expire. Useful for reducing
    expensive calls on small datasets.
    """
    def __init__(self, f):
        self.f = f
        self._cached = {}

    def __call__(self, *args):
        if args not in self._cached:
            self._cached[args] = self.f(*args)

        return self._cached[args]

    def __contains__(self, key):
        # workaround for StrokeEditDistance also acting like a container
        return self.f.__contains__(key)

@cache
def _get_neighbours(k):
    neighbours = set(n.kanji for n in models.Node.objects.get(
            pivot=k).neighbours[:settings.N_NEIGHBOURS_RECALLED])
    return neighbours

sed = cache(stroke.StrokeEditDistance())

#----------------------------------------------------------------------------#

def _create_option_parser():
    usage = \
"""%prog [options] output_file

Simulate queries through the search graph, dumping the traces to the given
file."""

    parser = optparse.OptionParser(usage)

    parser.add_option('--strategy', action='store', type='choice',
            choices=['greedy', 'shortest'], dest='strategy',
            default='greedy',
            help='The search strategy to use ([greedy]/shortest)')

    return parser

def main(argv):
    parser = _create_option_parser()
    (options, args) = parser.parse_args(argv)

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)

    simulate_search(args[0], strategy=options.strategy)

#----------------------------------------------------------------------------#

if __name__ == '__main__':
    main(sys.argv[1:])

# vim: ts=4 sw=4 sts=4 et tw=78:
