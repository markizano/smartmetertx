#!/usr/bin/env python3

import os, io
import sys
from glob import glob
from pprint import pprint
from setuptools import setup

try:
    VERSION = f"{io.open('VERSION').read().strip()}.{io.open('.build-id').read().strip()}"
except Exception:
    try:
        import yaml
        pkginfo = yaml.safe_load(io.open('PKG-INFO').read())
        VERSION = pkginfo['Version']
    except ModuleNotFoundError:
        with io.open('PKG-INFO') as fd:
            for line in fd:
                if 'Version' in line:
                    VERSION = line.split(': ')[1].strip()
                    break

try:
    requirements = io.open('requirements.txt').read().strip().split('\n')
except Exception:
    try:
        requirements = io.open('smartmetertx2mongo.egg-info/requires.txt').read().strip().split('\n')
    except Exception:
        requirements = '''dateparser
kizano
pymongo
requests
cherrypy
PyYAML
python-gnupg
jinja2'''.split()

setup_opts = {
    'name'                : 'smartmetertx2mongo',
    # We change this default each time we tag a release.
    'version'             : VERSION,
    'description'         : 'Implementation of smartmetertx to save records to mongodb with config driven via YAML.',
    'author'              : 'Markizano Draconus',
    'author_email'        : 'markizano@markizano.net',
    'url'                 : 'https://markizano.net/',
    'license'             : 'GNU',
    'tests_require'       : ['nose', 'mock', 'coverage'],
    'setup_requires'      : ['PyYAML>=6.0.1', 'boto3>=1.34.155'],
    'install_requires'    : requirements,
    'package_dir'         : { 'smartmetertx': 'lib/smartmetertx' },
    'package_data'        : { '': ['VERSION', 'requirements.txt'] },
    'include_package_data': True,
    'packages'            : [
      'smartmetertx',
    ],
    'scripts'             : glob('bin/*'),
    'test_suite'          : 'tests',
    'data_files'          : [
        ('share/smartmetertx', glob('lib/ui/*')),
    ]
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

if 'sdist' in sys.argv:
    import gnupg, hashlib
    gpg = gnupg.GPG()
    for artifact in glob('dist/*.tar.gz'):
        # Detach sign the artifact in dist/ folder.
        fd = open(artifact, 'rb')
        checksums = open('dist/CHECKSUMS.txt', 'w+b')
        status = gpg.sign_file(fd, detach=True, output=f'{artifact}.asc')
        print(f'Signed {artifact} with {status.fingerprint}')

        # create a MD5, SHA1 and SHA256 hash of the artifact.
        for hashname in ['md5', 'sha1', 'sha256']:
            hasher = getattr(hashlib, hashname)()
            fd.seek(0,0)
            hasher.update(fd.read())
            digest = hasher.hexdigest()
            checksums.write(f'''{hashname.upper()}:
{digest} {artifact}

'''.encode('utf-8'))
            print(f'Got {artifact}.{hashname} as {digest}')
        checksums.seek(0, 0)
        chk_status = gpg.sign_file(checksums, detach=True, output=f'dist/CHECKSUMS.txt.asc')
        checksums.close()
        fd.close()
        print(f'Signed CHECKSUMS.txt with {chk_status.fingerprint}')

