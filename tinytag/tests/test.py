#!/usr/bin/python
# -*- coding: utf-8 -*-

# tests can be extended using other bigger files that are not going to be
# checked into git, by placing them into the custom_samples folder
#
# see custom_samples/instructions.txt
#


from __future__ import unicode_literals
import timeit

import os
import re
from nose.tools import *
from tinytag import TinyTagException, TinyTag, ID3, Ogg, Wave, Flac

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict  # python 2.6 and 3.2 compat


testfiles = OrderedDict([
    # MP3
    ('samples/vbri.mp3', {'channels': 2, 'samplerate': 44100, 'track_total': None, 'duration': 0.47020408163265304, 'album': 'I Can Walk On Water I Can Fly', 'year': '2007', 'title': 'I Can Walk On Water I Can Fly', 'artist': 'Basshunter', 'track': '01'}),
    ('samples/cbr.mp3', {'channels': 2, 'samplerate': 44100, 'track_total': None, 'duration': 0.49, 'album': 'I Can Walk On Water I Can Fly', 'year': '2007', 'title': 'I Can Walk On Water I Can Fly', 'artist': 'Basshunter', 'track': '01'}),
    ('samples/id3v22-test.mp3', {'channels': 2, 'samplerate': 44100, 'track_total': '11', 'duration': 0.138, 'album': 'Hymns for the Exiled', 'year': '2004', 'title': 'cosmic american', 'artist': 'Anais Mitchell', 'track': '3'}),
    ('samples/silence-44-s-v1.mp3', {'channels': 2, 'samplerate': 44100, 'genre': 'Darkwave', 'track_total': None, 'duration': 3.7355102040816326, 'album': 'Quod Libet Test Data', 'year': '2004', 'title': 'Silence', 'artist': 'piman', 'track': '2'}),
    ('samples/id3v1-latin1.mp3', {'channels': 2, 'samplerate': 44100, 'genre': 'Rock', 'samplerate': None, 'album': 'The Young Americans', 'title': 'Play Dead', 'bitrate': 0.0, 'filesize': 256, 'audio_offset': 0, 'track': '12', 'artist': 'Björk', 'duration': 0, 'track_total': None, 'year': '1993'}),
    ('samples/UTF16.mp3', {'channels': None, 'samplerate': None, 'duration': 0, 'track_total': '11', 'track': '07', 'artist': 'The National', 'year': '2010', 'album': 'High Violet', 'title': 'Lemonworld'}),
    ('samples/utf-8-id3v2.mp3', {'channels': 2, 'samplerate': 44100, 'genre': 'Acustico', 'duration': 0, 'track_total': '21', 'track': '01', 'filesize': 2119, 'title': 'Gran día', 'artist': 'Paso a paso', 'album': 'S/T', 'bitrate': 0.0, 'year': None, 'audio_offset': 0, 'samplerate': None}),
    ('samples/empty_file.mp3', {'channels': None, 'samplerate': None, 'track_total': None, 'album': None, 'year': None, 'duration': 0.0, 'title': None, 'track': None, 'artist': None}),
    ('samples/silence-44khz-56k-mono-1s.mp3', {'channels': 1, 'samplerate': 44100, 'duration': 1.018, 'samplerate': 44100}),
    ('samples/silence-22khz-mono-1s.mp3', {'channels': 1, 'samplerate': 22050}),
    ('samples/id3v24-long-title.mp3', {'track': '1', 'audio_offset': 0, 'disc_total': '1', 'album': 'The Double EP: A Sea of Split Peas', 'filesize': 10000, 'duration': 0, 'channels': None, 'track_total': '12', 'genre': 'AlternRock', 'title': 'Out of the Woodwork', 'artist': 'Courtney Barnett', 'bitrate': 0.0, 'samplerate': None, 'year': None, 'disc': '1'}),
    ('samples/utf16be.mp3', {'title': '52-girls', 'filesize': 2048, 'track': '6', 'album': 'party mix', 'artist': 'The B52s', 'genre': '(17)', 'albumartist': None, 'disc': None}),

    # OGG
    ('samples/empty.ogg', {'track_total': None, 'duration': 3.684716553287982, 'album': None, '_max_samplenum': 162496, 'year': None, 'title': None, 'artist': None, 'track': None, '_tags_parsed': False}),
    ('samples/multipagecomment.ogg', {'track_total': None, 'duration': 3.684716553287982, 'album': None, '_max_samplenum': 162496, 'year': None, 'title': None, 'artist': None, 'track': None, '_tags_parsed': False}),
    ('samples/multipage-setup.ogg', {'genre': 'JRock', 'track_total': None, 'duration': 4.128798185941043, 'album': 'Timeless', 'year': '2006', 'title': 'Burst', 'artist': 'UVERworld', 'track': '7', '_tags_parsed': False}),
    ('samples/test.ogg', {'track_total': None, 'duration': 1.0, 'album': 'the boss', 'year': '2006', 'title': 'the boss', 'artist': 'james brown', 'track': '1', '_tags_parsed': False}),

    # OPUS
    ('samples/test.opus', {'albumartist': 'Alstroemeria Records', 'samplerate': 48000, 'channels': 2, 'track': '1', 'disc': '1', 'title': 'Bad Apple!!', 'duration': 2.0, 'year': '2008.05.25', 'filesize': 10000, 'artist': 'nomico', 'album': 'Exserens - A selection of Alstroemeria Records'}),

    # WAV
    ('samples/test.wav', {'duration': 1.0}),
    ('samples/test3sMono.wav', {'duration': 3.0}),
    ('samples/test-tagged.wav', {'duration': 1.0}),
    ('samples/silence-22khz-mono-1s.wav', {'duration': 1.0}),

    # FLAC
    ('samples/flac1sMono.flac', {'genre': 'Avantgarde', 'track_total': None, 'album': 'alb', 'year': '2014', 'duration': 1.0, 'title': 'track', 'track': '23', 'artist': 'art'}),
    ('samples/flac453sStereo.flac', {'track_total': None, 'album': None, 'year': None, 'duration': 453.51473922902494, 'title': None, 'track': None, 'artist': None}),
    ('samples/flac1.5sStereo.flac', {'track_total': None, 'album': 'alb', 'year': '2014', 'duration': 1.4995238095238095, 'title': 'track', 'track': '23', 'artist': 'art'}),
    ('samples/flac_application.flac', {'track_total': '11', 'album': 'Belle and Sebastian Write About Love', 'year': '2010-10-11', 'duration': 273.64, 'title': 'I Want the World to Stop', 'track': '4', 'artist': 'Belle and Sebastian'}),
    ('samples/no-tags.flac', {'track_total': None, 'album': None, 'year': None, 'duration': 3.684716553287982, 'title': None, 'track': None, 'artist': None}),
    ('samples/variable-block.flac', {'track_total': None, 'album': 'Appleseed Original Soundtrack', 'year': '2004', 'duration': 261.68, 'title': 'DIVE FOR YOU', 'track': '01', 'artist': 'Boom Boom Satellites'}),
    ('samples/106-invalid-streaminfo.flac', {}),
    ('samples/106-short-picture-block-size.flac', {}),

    # WMA
    ('samples/test2.wma', {'samplerate': 44100, 'album': 'The Colour and the Shape', 'title': 'Doll', 'bitrate': 64.04, 'filesize': 5800, 'audio_offset': 0, 'track': '1', 'artist': 'Foo Fighters', 'duration': 86.406, 'track_total': None, 'year': '1997', 'genre': 'Alternative'}),

    # M4A/MP4
    ('samples/test.m4a', {'samplerate': 44100, 'duration': 314.97,  'bitrate': 256.0, 'channels': 2, 'genre': 'Pop', 'year': '2011', 'title': 'Nothing', 'album': 'Only Our Hearts To Lose', 'track_total': 11, 'track': 11, 'artist': 'Marian', 'filesize': 61432}),
    ('samples/test2.m4a', {'bitrate': 256.0, 'track': 1, 'albumartist': "Millie Jackson - Get It Out 'cha System - 1978", 'duration': 167.78739229024944, 'filesize': 223365, 'channels': 2, 'year': '1978', 'artist': 'Millie Jackson', 'track_total': 9, 'disc_total': 1, 'genre': 'R&B/Soul', 'album': "Get It Out 'cha System", 'samplerate': 44100, 'disc': 1, 'title': 'Go Out and Get Some'}),

])

testfolder = os.path.join(os.path.dirname(__file__))

# load custom samples
custom_samples_folder = os.path.join(testfolder, 'custom_samples')
pattern_field_name_type = [
    ('sr(\d+)', 'samplerate', int),
    ('dn(\d+)', 'disc', str),
    ('dt(\d+)', 'disc_total', str),
    ('d(\d+.?\d*)', 'duration', float),
    ('b(\d+)', 'bitrate', int),
    ('c(\d)', 'channels', int),
]
for filename in os.listdir(custom_samples_folder):
    expected_values = {}
    for pattern, fieldname, _type in pattern_field_name_type:
        match = re.findall(pattern, filename)
        if match:
            expected_values[fieldname] = _type(match[0])
    if expected_values:
        testfiles[os.path.join('custom_samples', filename)] = expected_values


def get_info(testfile, expected):
    filename = os.path.join(testfolder, testfile)
    print(filename)
    tag = TinyTag.get(filename)

    for key, expected_val in expected.items():
        result = getattr(tag, key)
        if key == 'duration':
            # allow duration to be off by 100 ms and a maximum of 1%
            if abs(result - expected_val) < 0.100:
                if expected_val and min(result, expected_val) / max(result, expected_val) > 0.99:
                    continue
        fmt_string = 'field "%s": got %s (%s) expected %s (%s)!'
        fmt_values = (key, repr(result), type(result), repr(expected_val), type(expected_val))
        assert result == expected_val, fmt_string % fmt_values

def test_generator():
    for testfile, expected in testfiles.items():
        yield get_info, testfile, expected

@raises(LookupError)
def test_unsupported_extension():
    bogus_file = os.path.join(testfolder, 'samples/there_is_no_such_ext.bogus')
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
    tag = TinyTag.get(os.path.join(testfolder, 'samples/silence-44-s-v1.mp3'))
    print(tag.duration)
    assert 3.5 < tag.duration < 4.0 

@raises(TinyTagException)
def test_invalid_flac_file():
    tag = Flac.get(os.path.join(testfolder, 'samples/silence-44-s-v1.mp3'))

@raises(TinyTagException)
def test_invalid_mp3_file():
    tag = ID3.get(os.path.join(testfolder, 'samples/flac1.5sStereo.flac'))

@raises(TinyTagException)
def test_invalid_ogg_file():
    tag = Ogg.get(os.path.join(testfolder, 'samples/flac1.5sStereo.flac'))

@raises(TinyTagException)
def test_invalid_wave_file():
    tag = Wave.get(os.path.join(testfolder, 'samples/flac1.5sStereo.flac'))

def test_mp3_image_loading():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/cover_img.mp3'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 140000 < len(image_data) < 150000, 'Image is %d bytes but should be around 145kb' % len(image_data)

def test_to_str():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/empty.ogg'))
    assert str(tag)  # since the dict is not ordered we cannot == 'somestring'
    assert repr(tag)  # since the dict is not ordered we cannot == 'somestring'
