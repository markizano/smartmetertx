#!/usr/bin/env python3

import os
import sys
from glob import glob
from pprint import pprint
from setuptools import setup

sys.path.insert(0, os.path.abspath('.'))

setup_opts = {
    'name'                : 'smartmetertx2mongo',
    # We change this default each time we tag a release.
    'version'             : '1.0.0',
    'description'         : 'Implementation of smartmetertx to save records to mongodb with config driven via YAML.',
    'author'              : 'Markizano Draconus',
    'author_email'        : 'markizano@markizano.net',
    'url'                 : 'https://markizano.net/',
    'license'             : 'GNU',

    'tests_require'       : ['nose', 'mock', 'coverage'],
    'install_requires'    : [
        'kizano',
        'pymongo',
        'requests',
        'cherrypy',
        'jinja2',
    ],
    'package_dir'         : { 'smartmetertx': 'smartmetertx' },
    'packages'            : [
      'smartmetertx',
    ],
    'scripts'             : glob('bin/*'),
    'test_suite'          : 'tests',
}

try:
    import argparse
    HAS_ARGPARSE = True
except:
    HAS_ARGPARSE = False

if not HAS_ARGPARSE: setup_opts['install_requires'].append('argparse')

# I botch this too many times.
if sys.argv[1] == 'test':
    sys.argv[1] = 'nosetests'

if 'DEBUG' in os.environ: pprint(setup_opts)

setup(**setup_opts)
