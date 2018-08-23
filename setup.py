from os.path import join
from setuptools import setup


def get_version():
    with open(join('tinytag', '__init__.py')) as f:
        for line in f:
            if line.startswith('__version__ ='):
                return line.split('=')[1].strip().strip('"\'')


setup(version=get_version())
