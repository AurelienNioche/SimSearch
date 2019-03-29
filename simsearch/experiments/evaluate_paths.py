#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  evaluate_paths.py
#  simsearch
# 
#  Created by Lars Yencken on 03-09-2010.
#  Copyright 2010 Lars Yencken. All rights reserved.
#
#  Revised by Aurélien Nioche on 23-03-2019

"""
A script to generate statistics on a set of query traces (i.e. walks through
the kanji graph generated by simulated search).
"""

import os
import sys
import optparse

import numpy as np

from simsearch.experiments.simulate_search import TraceFile


def evaluate_paths(input_file, limit=5):
    print(f'Evaluating paths from "{os.path.basename(input_file)}"')
    traces = TraceFile.load(input_file)

    path_lengths = []
    successes = []
    for (query, target, path) in traces:
        if path and path[-1] == target:
            successes.append(path)
            path_lengths.append(len(path) - 1)
        else:
            path_lengths.append(limit)

    print(f'Success rate: {len(successes)}/{len(traces)} ({100.0 * len(successes) / len(traces):.2f})')

    print(f'Mean path length: {np.mean(path_lengths):.2f} (σ = {np.std(path_lengths):.2f})')

# ---------------------------------------------------------------------------- #


def _create_option_parser():
    usage = \
        """%prog [options] input_file
        
        Generates evaluation statistics on a collection of traces."""

    parser = optparse.OptionParser(usage)

    return parser


def main(argv):
    parser = _create_option_parser()
    (options, args) = parser.parse_args(argv)

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)

    input_file, = args
    evaluate_paths(input_file)

# ---------------------------------------------------------------------------- #


if __name__ == '__main__':
    main(sys.argv[1:])
