#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  simulate_accessibility.py
#  simsearch
# 
#  Created by Lars Yencken on 05-09-2010.
#  Copyright 2010 Lars Yencken. All rights reserved.
#
#  Revised by Aurélien Nioche on 23-03-2019

"""
A basic simulation of accessibility improvements estimated from use of visual
similarity search.
"""

import os
import sys
import optparse
import random
import bz2
import gzip
import codecs

import numpy as np
from math import log

from simsearch import settings
from simsearch import models


DEFAULT_THRESHOLD = 0.95

SYMBOL_SEP = ' '           # The separator we use in our file format
SPACE_REPLACEMENT = '_^_'  # The replacement string for dumps


def sopen(filename, mode='rb', encoding='utf8'):
    """
    Transparently uses compression on the given file based on file
    extension.
    @param filename: The filename to use for the file handle.
    @param mode: The mode to open the file in, e.g. 'r' for read, 'w' for
        write, 'a' for append.
    @param encoding: The encoding to use. Can be set to None to avoid
        using unicode at all.
    """
    read_mode = 'r' in mode
    if read_mode and 'w' in mode:
        raise Exception("Must be either read mode or write, but not both")

    if filename.endswith('.bz2'):
        stream = bz2.BZ2File(filename, mode)
    elif filename.endswith('.gz'):
        stream = gzip.GzipFile(filename, mode)
    elif filename == '-':
        if read_mode:
            stream = sys.stdin
        else:
            stream = sys.stdout
    else:
        stream = open(filename, mode)

    if encoding not in (None, 'byte'):
        if read_mode:
            return codecs.getreader(encoding)(stream)
        else:
            return codecs.getwriter(encoding)(stream)

    return stream


def _escape_spaces(value):
    """
    Esacapes any spaces in the given string with a special value.
    >>> _escape_spaces('dog eats cat')
    'dog_^_eats_^_cat'
    >>> _escape_spaces('cow')
    'cow'
    """
    return value.replace(SYMBOL_SEP, SPACE_REPLACEMENT)


def _unescape_spaces(value):
    """
    Unescapes any escaped spaces in the string.
    >>> _unescape_spaces('dog_^_eats_^_cat')
    'dog eats cat'
    >>> _unescape_spaces('cow')
    'cow'
    """
    return value.replace(SPACE_REPLACEMENT, SYMBOL_SEP)


def _contains_escape(value):
    """
    Checks the string for the special replacement sequence.
    >>> _contains_escape('cow')
    False
    >>> _contains_escape('dog_^_eats_^_cat')
    True
    """
    return SPACE_REPLACEMENT in value


class FreqDist(dict):
    """
    A simple frequency distribution, and some methods to access MLE
    probability estimations based on this distribution.
        >>> x = FreqDist()
        >>> x.prob('unknown')
        0.0
        >>> x.inc('a', 3)
        >>> x.inc('b')
        >>> x.prob('a')
        0.75
        >>> x.prob('b')
        0.25
        >>> x.prob('unknown')
        0.0
    """
    def __init__(self, pairSeq=None):
        """
        Can optionally be given a sequence of (sample, count) pairs to load
        counts from.
        """

        super().__init__()
        self._total = 0

        if pairSeq is not None:
            for sample, count in pairSeq:
                self[sample] = count
                self._total += count

    def inc(self, sample, n=1):
        self.__setitem__(sample, self.get(sample, 0) + n)
        self._total += n

    def decrement(self, sample, n=1):
        count = self[sample]

        if count < n:
            raise ValueError("can't reduce a count below zero")
        elif count == n:
            # If we reduce a count to zero, delete it.
            self._total -= n
            del self[sample]
        else:
            # Reduce it by the given amount only.
            self._total -= n
            self[sample] -= n

        return

    # ------------------------------------------------------------------------ #

    def remove_sample(self, sample):
        """
        Removes the sample and its count from the distribution. Returns
        the count of the sample.
        """
        count = self[sample]
        del self[sample]
        self._total -= count

        return count

    # ------------------------------------------------------------------------ #

    def count(self, sample):
        """Return the frequency count of the sample."""
        return self.get(sample, 0)

    def prob(self, sample):
        """Returns the MLE probability of this sample."""
        c = self.get(sample, 0)
        if c > 0:
            return c / float(self._total)
        else:
            return 0.0

    def log_prob(self, sample):
        """Returns the log MLE probability of this sample."""
        return log(self.get(sample, 0) / float(self._total))

    def candidates(self):
        """
        Returns a list of (sample, log_prob) pairs, using the log MLE
        probability of each sample.
        """
        return [
            (k, log(v / float(self._total)))
            for (k, v) in self.items()
        ]

    def dump(self, filename):
        """
        Dump the current counts to the given filename. Note that symbols
        are coerced to strings, so arbitrary objects may not be
        reconstructed identically.
        """
        o_stream = sopen(filename, 'w')
        for key, count in sorted(self.items(), key=lambda x: x[1],
                                 reverse=True):
            key = _escape_spaces(key)
            print(f"{key} {count}", file=o_stream)
        o_stream.close()
        return

    # ------------------------------------------------------------------------ #

    def load(self, filename):
        """
        Loads counts from the given filename. Can be done for more than
        one file.
        """
        i_stream = sopen(filename, 'r')
        for line in i_stream:
            key, count = line.rstrip().split(SYMBOL_SEP)
            key = _unescape_spaces(key)
            count = int(count)
            self.inc(key, count)
        i_stream.close()

        return

    # ------------------------------------------------------------------------ #

    @staticmethod
    def from_file(filename):
        """
        An alternative constructor which builds the distribution from a file.
        """
        dist = FreqDist()
        dist.load(filename)
        return dist

    # ------------------------------------------------------------------------ #

    def merge(self, rhs_dist):
        for sample, count in rhs_dist.iteritems():
            self.inc(sample, count)


def simulate_accessibility(output_file):
    print('Loading frequency distribution')
    dist = FreqDist.from_file(settings.FREQ_SOURCE)

    print('Loading kanji')
    kanji_set = list(models._get_kanji())
    random.seed(123456789)
    random.shuffle(kanji_set)

    kanji_in_order = sorted(kanji_set, key=lambda k: dist.prob(k))

    print('Loading graph')
    graph = RestrictedGraph()

    print(f'Dumping frequencies to {os.path.basename(output_file)}')
    n_neighbours = []
    with codecs.open(output_file, 'w', 'utf8') as ostream:
        print(u'#n_known,n_accessible', file=ostream)
        print(f'{0},{0}', file=ostream)
        known_set = set()
        accessible_set = set()
        for i, kanji in enumerate(kanji_in_order):
            known_set.add(kanji)
            accessible_set.add(kanji)

            neighbours = graph[kanji]
            accessible_set.update(neighbours)
            n_neighbours.append(len(neighbours))

            if (i + 1) % 50 == 0:
                print(f'{len(known_set)},{len(accessible_set)}', file=ostream)
        print(f'{len(known_set)},{len(accessible_set)}', file=ostream)

    print(f'Average neighbourhood size: {np.mean(n_neighbours):.3f} (σ = {n_neighbours:.3f})')


class RestrictedGraph(object):
    def __init__(self, threshold=DEFAULT_THRESHOLD):
        self._graph = models.Similarity.load()
        self._threshold = threshold

    def __getitem__(self, kanji):
        neighbour_heap = self._graph[kanji]
        ordered_neighbourhood = sorted(neighbour_heap.get_contents(), reverse=True)

        first_sim, first_neighbour = ordered_neighbourhood[0]
        cutoff_neighbours = set(n for (s, n) in ordered_neighbourhood if s >= self._threshold * first_sim)

        return cutoff_neighbours

# ---------------------------------------------------------------------------- #


def _create_option_parser():
    usage = \
        """%prog [options] output_file.csv
        
        Simulates how many kanji are accessible as kanji are learned, assuming they
        are studied in frequency order."""

    parser = optparse.OptionParser(usage)

    parser.add_option(
        '-t', action='store', dest='threshold',
        default=DEFAULT_THRESHOLD, type='float',
        help='The neighbourhood cutoff threshold [%.02f]' % DEFAULT_THRESHOLD)

    return parser


def main(argv):
    parser = _create_option_parser()
    (options, args) = parser.parse_args(argv)

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)

    simulate_accessibility(args[0], threshold=options.threshold)

# --------------------------------------------------------------------------- #


if __name__ == '__main__':
    main(sys.argv[1:])
