#!/usr/bin/python
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import os
import codecs
import tinytag

here = os.path.abspath(os.path.dirname(__file__))

def module(foldername):
    ret = [foldername]
    for i in os.listdir(foldername):
        if i == '__pycache__':
            continue
        if i == 'test':
            continue
        subfolder = os.path.join(foldername, i)
        if os.path.isdir(subfolder) and _ispackage(subfolder):
            ret += module(subfolder)
            ret += [subfolder.replace(os.sep,'.')]
    return ret

def _ispackage(foldername):
    containsinit = '__init__.py' in os.listdir(foldername)
    return containsinit and not istest

def read(*parts):
    return codecs.open(os.path.join(here, *parts), 'r').read()

long_description = "\n" + "\n".join([read('README.md')])

setup_options = {
    'name': 'TinyTag',
    'version': tinytag.__version__,
    'description': 'TinyTag reads music meta-data of MP3, OGG, FLAC and Wave files',
    'long_description': long_description,
    'author': 'Tom Wallroth',
    'author_email': 'tomwallroth@gmail.com',
    'url': 'https://github.com/devsnd/tinytag',
    'license': 'GPLv3',
    'install_requires': [],
    'packages': module('tinytag'),
    'package_data': {
    },
    #startup script
    'scripts': [],
    'classifiers': [
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Natural Language :: English',
        'Topic :: Multimedia :: Sound/Audio :: Analysis',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],
}

setup(**setup_options)
