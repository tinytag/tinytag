#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from nose.tools import *
from tinytag import TinyTag, ID3, Ogg, Wave, Flac


testfiles = {'vbri.mp3': {'track_total': None, 'duration': 0.47020408163265304, 'album': 'I Can Walk On Water I Can Fly', 'year': '2007', 'title': 'I Can Walk On Water I Can Fly', 'artist': 'Basshunter', 'track': '01'},
             'cbr.mp3': {'track_total': None, 'duration': 0.4963265306122449, 'album': 'I Can Walk On Water I Can Fly', 'year': '2007', 'title': 'I Can Walk On Water I Can Fly', 'artist': 'Basshunter', 'track': '01'},
             'id3v22-test.mp3': {'track_total': '11', 'duration': 0.156734693877551, 'album': 'Hymns for the Exiled', 'year': '2004', 'title': 'cosmic american', 'artist': 'Anais Mitchell', 'track': '3'},
             'silence-44-s-v1.mp3': {'track_total': None, 'duration': 3.7355102040816326, 'album': 'Quod Libet Test Data', 'year': '2004', 'title': 'Silence', 'artist': 'piman', 'track': '2'},
             'UTF16.mp3': {'duration': 0, 'track_total': '11', 'track': '07', 'artist': 'The National', 'year': '2010', 'album': 'High Violet', 'title': 'Lemonworld'},
             'empty.ogg': {'track_total': None, 'duration': 3.684716553287982, 'album': None, '_max_samplenum': 162496, 'year': None, 'title': None, 'artist': None, 'track': None, '_tags_parsed': False},
             'multipagecomment.ogg': {'track_total': None, 'duration': 3.684716553287982, 'album': None, '_max_samplenum': 162496, 'year': None, 'title': None, 'artist': None, 'track': None, '_tags_parsed': False},
             'multipage-setup.ogg': {'track_total': None, 'duration': 4.128798185941043, 'album': 'Timeless', 'year': '2006', 'title': 'Burst', 'artist': 'UVERworld', 'track': '7', '_tags_parsed': False},
             'test.ogg': {'track_total': None, 'duration': 1.0, 'album': 'the boss', 'year': '2006', 'title': 'the boss', 'artist': 'james brown', 'track': '1', '_tags_parsed': False},
             'test.wav': {'duration': 1.0},
             'test3sMono.wav': {'duration': 3.0},
             'test-tagged.wav': {'duration': 1.0},

             'flac1sMono.flac': {'track_total': None, 'album': None, 'year': None, 'duration': 1.0, 'title': None, 'track': None, 'artist': None},
             'flac453sStereo.flac': {'track_total': None, 'album': None, 'year': None, 'duration': 453.51473922902494, 'title': None, 'track': None, 'artist': None},
             'flac1.5sStereo.flac': {'track_total': None, 'album': None, 'year': None, 'duration': 1.4995238095238095, 'title': None, 'track': None, 'artist': None},
             'flac_application.flac': {'track_total': None, 'album': 'Belle and Sebastian Write About Love', 'year': '2010-10-11', 'duration': 273.64, 'title': 'I Want the World to Stop', 'track': '4/11', 'artist': 'Belle and Sebastian'},
             'no-tags.flac': {'track_total': None, 'album': None, 'year': None, 'duration': 3.684716553287982, 'title': None, 'track': None, 'artist': None},
             'variable-block.flac': {'track_total': None, 'album': 'Appleseed Original Soundtrack', 'year': '2004', 'duration': 261.68, 'title': 'DIVE FOR YOU', 'track': '01', 'artist': 'Boom Boom Satellites'},
             '106-invalid-streaminfo.flac': {},
             '106-short-picture-block-size.flac': {},
             'empty_file.mp3': {'track_total': None, 'album': None, 'year': None, 'duration': 0.0, 'title': None, 'track': None, 'artist': None},
             'id3v1-latin1.mp3': {'samplerate': 0, 'album': 'The Young Americans', 'title': 'Play Dead', 'bitrate': 0.0, 'filesize': 256, 'audio_offset': 0, 'track': '12', 'artist': 'Björk', 'duration': 0, 'track_total': None, 'year': '1993'}
,
             }
samplefolder = os.path.join(os.path.dirname(__file__), 'samples')

def get_info(testfile, expected):
    filename = os.path.join(samplefolder, testfile)
    print(filename)
    tag = TinyTag.get(filename)
    for key, value in expected.items():
        result = getattr(tag, key)
        fmt_string = 'field "%s": got %s (%s) expected %s (%s)!'
        fmt_values = (key, repr(result), type(result), repr(value), type(value))
        assert result == value, fmt_string % fmt_values
    print(tag)
    print(tag.__repr__())


def test_generator():
    for testfile, expected in testfiles.items():
        yield get_info, testfile, expected

@raises(LookupError)
def test_unsupported_extension():
    bogus_file = os.path.join(samplefolder, 'there_is_no_such_ext.bogus')
    TinyTag.get(bogus_file)

@raises(NotImplementedError)
def test_unsubclassed_tinytag_duration():
    tag = TinyTag(None, 0)
    tag._determine_duration(None)

@raises(NotImplementedError)
def test_unsubclassed_tinytag_parse_tag():
    tag = TinyTag(None, 0)
    tag._parse_tag(None)

def test_mp3_length_estimation():
    ID3.set_estimation_precision(0.7)
    tag = TinyTag.get(os.path.join(samplefolder, 'silence-44-s-v1.mp3'))
    print(tag.duration)
    assert 3.5 < tag.duration < 4.0 

def test_invalid_flac_file():
    tag = Flac.get(os.path.join(samplefolder, 'silence-44-s-v1.mp3'))

def test_invalid_mp3_file():
    tag = ID3.get(os.path.join(samplefolder, 'flac1.5sStereo.flac'))

def test_invalid_ogg_file():
    tag = Ogg.get(os.path.join(samplefolder, 'flac1.5sStereo.flac'))

def test_invalid_wave_file():
    tag = Wave.get(os.path.join(samplefolder, 'flac1.5sStereo.flac'))
