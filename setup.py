from os.path import join
from setuptools import setup, find_packages
import sys
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def get_version():
    with open(join('tinytag', '__init__.py')) as f:
        for line in f:
            if line.startswith('__version__ ='):
                return line.split('=')[1].strip().strip('"\'')

long_description = read('README.md')

tests_require = ["pytest", "nose", "coveralls"]

setup(
    name='tinytag',
    version=get_version(),
    description='Read music meta data and length of MP3, OGG, OPUS, MP4, M4A, FLAC, WMA and Wave files',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Tom Wallroth',
    author_email='tomwallroth@gmail.com',
    url='https://github.com/devsnd/tinytag/',
    license='GPLv3',
    packages=find_packages(),
    install_requires=[],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Multimedia',
        'Topic :: Multimedia :: Sound/Audio',
        'Topic :: Multimedia :: Sound/Audio :: Analysis',
    ],
    python_requires='>=2.7',
    zip_safe=False,
    tests_require=tests_require,
    extras_require={'tests': tests_require},
)
