#!/usr/bin/env python3

import os, io
import sys
import yaml
from glob import glob
from pprint import pprint
from setuptools import setup

sys.path.insert(0, os.path.abspath('.'))

try:
    PATCH = io.open('.build-id').read().strip()
except:
    try:
        pkginfo = yaml.safe_load(io.open('PKG-INFO').read())
        PATCH = pkginfo['Version'].split('.').pop()
    except Exception as e:
        PATCH = '0'

setup_opts = {
    'name'                : 'smartmetertx2mongo',
    # We change this default each time we tag a release.
    'version'             : f'1.0.{PATCH}',
    'summary'             : 'SmartMeterTX Web Viewer Applet',
    'description'         : 'Implementation of smartmetertx to save records to mongodb with config driven via YAML.',
    'author'              : 'Markizano Draconus',
    'author_email'        : 'markizano@markizano.net',
    'url'                 : 'https://markizano.net/',
    'license'             : 'GNU',
    'platform'            : 'linux',

    'tests_require'       : ['nose', 'mock', 'coverage'],
    'install_requires'    : [
        'kizano',
        'pymongo',
        'requests',
        'cherrypy',
        'jinja2',
    ],
    'package_dir'         : { 'smartmetertx': 'lib/smartmetertx' },
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

