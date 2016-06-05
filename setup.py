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

long_description = None
if 'upload' in sys.argv or 'register' in sys.argv:
    readmemd = "\n" + "\n".join([read('README.md')])
    print("converting markdown to reStucturedText for upload to pypi.")
    from urllib.request import urlopen
    from urllib.parse import quote
    import json
    import codecs
    url = 'http://johnmacfarlane.net/cgi-bin/trypandoc?text=%s&from=markdown&to=rst'
    urlhandler = urlopen(url % quote(readmemd))
    result = json.loads(codecs.decode(urlhandler.read(), 'utf-8'))
    long_description = result['result']
else:
    long_description = "\n" + "\n".join([read('README.md')])

setup(
    name='tinytag',
    version=get_version(),
    description='Read music meta data and length of MP3, OGG, OPUS, MP4, M4A, FLAC, WMA and Wave files',
    long_description=long_description,
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
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
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
