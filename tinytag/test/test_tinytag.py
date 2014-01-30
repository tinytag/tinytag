from __future__ import unicode_literals
from os import path
import nose

from tinytag import *

testfiles = {'vbri.mp3': {'track_total': None, 'length': 0.5224489795918368, 'album': 'I Can Walk On Water I Can Fly', 'year': '2007', 'title': 'I Can Walk On Water I Can Fly', 'artist': 'Basshunter', 'track': '01'},
             'cbr.mp3': {'track_total': None, 'length': 0.4963265306122449, 'album': None, 'year': None, 'title': None, 'artist': None, 'track': None},
             'id3v22-test.mp3': {'track_total': '11', 'length': 0.156734693877551, 'album': 'Hymns for the Exiled', 'year': '2004', 'title': 'cosmic american', 'artist': 'Anais Mitchell', 'track': '3'},
             'silence-44-s-v1.mp3': {'track_total': None, 'length': 3.7355102040816326, 'album': 'Quod Libet Test Data', 'year': '2004', 'title': 'Silence', 'artist': 'piman', 'track': '2'},
             'empty.ogg': {'track_total': None, 'length': 3.684716553287982, 'album': None, '_max_samplenum': 162496, 'year': None, 'title': None, 'artist': None, 'track': None, '_tags_parsed': False},
             'multipagecomment.ogg': {'track_total': None, 'length': 3.684716553287982, 'album': None, '_max_samplenum': 162496, 'year': None, 'title': None, 'artist': None, 'track': None, '_tags_parsed': False},
             'multipage-setup.ogg': {'track_total': None, 'length': 4.128798185941043, 'album': 'Timeless', '_max_samplenum': 182080, 'year': '2006', 'title': 'Burst', 'artist': None, 'track': '7', '_tags_parsed': False},
             'test.ogg': {'track_total': None, 'length': 1.0, 'album': 'the boss', '_max_samplenum': 44100, 'year': '2006', 'title': 'the boss', 'artist': None, 'track': '1', '_tags_parsed': False},
            }

def get_info(testfile, expected):
    folder = path.join(path.dirname(__file__), 'samples')
    filename = path.join(folder, testfile)
    print(filename)
    tag = TinyTag.get(filename)
    for key, value in expected.items():
        assert getattr(tag, key) == value
    print(tag)
    print('')

def test_generator():
    for testfile, expected in testfiles.items():
        yield get_info, testfile, expected


if __name__ == '__main__':
    nose.runmodule()