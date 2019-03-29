# -*- coding: utf-8 -*-
#
#  setup.py
#  simsearch
#
#  Created by Lars Yencken on 2011-10-26.
#  Copyright 2011 Lars Yencken. All rights reserved.
#
#  Revised by Aurélien Nioche on 23-03-2019

"""
Package information for simsearch.
"""

from setuptools import setup
from setuptools.extension import Extension

setup(
    name='simsearch',
    version='1.0.0',
    license='BSD',
    install_requires=[
        'cjktools>=1.5.0',
        'mongoengine>=0.3',
        'nltk',
        'flask',
        'simplejson',
        'cython',
        # 'simplestats>=0.2.0',  # Only for experiments
        # 'consoleLog>=0.2.4',   # Only for experiments
        # # Not necessary?
        # 'cjktools-data>=0.2.1-2010-07-29',
        # 'simplestats>=0.2.0',
        # 'pymongo',
        # 'pyyaml',
    ],
    packages=['simsearch'],
    ext_modules=[Extension(
            'simsearch.stroke',
            sources=['simsearch/stroke.pyx'],
        )],
    scripts=['simsearch.py'],
    zip_safe=False,
)

