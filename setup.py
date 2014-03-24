from os.path import join
from setuptools import setup, find_packages


def get_version():
    with open(join('tinytag', '__init__.py')) as f:
        for line in f:
            if line.startswith('__version__ ='):
                return line.split('=')[1].strip().strip('"\'')


setup(
    name='tinytag',
    version=get_version(),
    description='Read music meta data and length of MP3, OGG, FLAC and Wave files',
    long_description=(open('README.md').read()),
    author='Tom Wallroth',
    author_email='tomwallroth@gmail.com',
    url='https://github.com/devsnd/tinytag/',
    license='GPLv3',
    packages=find_packages(),
    install_requires=[],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Multimedia',
        'Topic :: Multimedia :: Sound/Audio',
    ],
    zip_safe=False,
    tests_require=["nose"],
)
