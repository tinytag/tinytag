from __future__ import unicode_literals
from os import path
import nose

from tinytag import *

def test_id3_v1():    
    testfiles = ['vbri.mp3', 'cbr.mp3', 'id3v22-test.mp3']
    folder = path.join(path.dirname(__file__), 'samples')
    for testfile in testfiles:
        TinyTag.open(path.join(folder, testfile))


if __name__ == '__main__':
    nose.runmodule()