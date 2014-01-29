from __future__ import unicode_literals
from os import path
import nose

from tinytag import *

testfiles = ['vbri.mp3', 
             'cbr.mp3',
             'id3v22-test.mp3',
             'empty.ogg',
             'multipagecomment.ogg',
             'multipage-setup.ogg',
             'test.ogg',
            ]

def get_info(testfile):
    folder = path.join(path.dirname(__file__), 'samples')
    TinyTag.get(path.join(folder, testfile))

def test_generator():
    for testfile in testfiles:
        yield get_info, testfile


if __name__ == '__main__':
    nose.runmodule()