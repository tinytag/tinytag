#!/usr/bin/python
# -*- coding: utf-8 -*-

# tests can be extended using other bigger files that are not going to be
# checked into git, by placing them into the custom_samples folder
#
# see custom_samples/instructions.txt
#

from __future__ import unicode_literals
import pytest
import os
import re
from tinytag import TinyTagException, TinyTag, ID3, Ogg, Wave, Flac
from collections import OrderedDict  # not needed for Python >= 3.5
try:
    from pathlib import Path
except ImportError:
    Path = None  # type: ignore
xfail = pytest.mark.xfail


testfiles = OrderedDict([
    # MP3
    ('samples/vbri.mp3', {'channels': 2, 'samplerate': 44100, 'track_total': None, 'duration': 0.47020408163265304, 'album': 'I Can Walk On Water I Can Fly', 'year': '2007',
                          'title': 'I Can Walk On Water I Can Fly', 'artist': 'Basshunter', 'track': '01', 'filesize': 8192, 'audio_offset': 1007, 'genre': '(3)Dance', 'comment': '\uff00þ\uff00勾椀瀀瀀攀搀\u2000戀礀\u2000吀䠀匀䰀䤀嘀䔀'}),
    ('samples/cbr.mp3', {'channels': 2, 'samplerate': 44100, 'track_total': None, 'duration': 0.49, 'album': 'I Can Walk On Water I Can Fly', 'year': '2007',
                         'title': 'I Can Walk On Water I Can Fly', 'artist': 'Basshunter', 'track': '01', 'filesize': 8186, 'audio_offset': 246, 'bitrate': 128.0, 'genre': 'Dance', 'comment': 'XXX'}),
    # the output of the lame encoder was 185.4 bitrate, but this is good enough for now
    ('samples/vbr_xing_header.mp3', {'bitrate': 186.04383278145696, 'channels': 1,
                                     'samplerate': 44100, 'duration': 3.944489795918367, 'filesize': 91731, 'audio_offset': 441}),
    ('samples/id3v22-test.mp3', {'channels': 2, 'samplerate': 44100, 'track_total': '11', 'duration': 0.138, 'album': 'Hymns for the Exiled', 'year': '2004',
                                 'title': 'cosmic american', 'artist': 'Anais Mitchell', 'track': '3', 'filesize': 5120, 'audio_offset': 2225, 'bitrate': 160.0, 'comment': 'TunNORM'}),
    ('samples/silence-44-s-v1.mp3', {'channels': 2, 'samplerate': 44100, 'genre': 'Darkwave', 'track_total': None, 'duration': 3.7355102040816326,
                                     'album': 'Quod Libet Test Data', 'year': '2004', 'title': 'Silence', 'artist': 'piman', 'track': '2', 'filesize': 15070, 'audio_offset': 0, 'bitrate': 32.0, 'comment': ''}),
    ('samples/id3v1-latin1.mp3', {'channels': 2, 'samplerate': None, 'genre': 'Rock', 'album': 'The Young Americans',
                                  'title': 'Play Dead', 'filesize': 256, 'track': '12', 'artist': 'Björk', 'track_total': None, 'year': '1993', 'comment': '                            '}),
    ('samples/UTF16.mp3', {'channels': None, 'samplerate': None, 'track_total': '11', 'track': '07', 'artist': 'The National',
                           'year': '2010', 'album': 'High Violet', 'title': 'Lemonworld', 'filesize': 20480, 'genre': 'Indie', 'comment': ''}),
    ('samples/utf-8-id3v2.mp3', {'channels': 2, 'samplerate': None, 'genre': 'Acustico', 'track_total': '21', 'track': '01', 'filesize': 2119,
                                 'title': 'Gran día', 'artist': 'Paso a paso', 'album': 'S/T', 'year': None, 'disc': '', 'disc_total': '0'}),
    ('samples/empty_file.mp3', {'channels': None, 'samplerate': None, 'track_total': None,
                                'album': None, 'year': None, 'title': None, 'track': None, 'artist': None, 'filesize': 0}),
    ('samples/silence-44khz-56k-mono-1s.mp3', {'channels': 1, 'samplerate': 44100,
                                               'duration': 1.018, 'samplerate': 44100, 'filesize': 7280, 'audio_offset': 0, 'bitrate': 56.0}),
    ('samples/silence-22khz-mono-1s.mp3', {'channels': 1, 'samplerate': 22050,
                                           'filesize': 4284, 'audio_offset': 0, 'bitrate': 32.0, 'duration': 1.0438932496075353}),
    ('samples/id3v24-long-title.mp3', {'track': '1', 'disc_total': '1', 'album': 'The Double EP: A Sea of Split Peas', 'filesize': 10000, 'channels': None, 'track_total': '12', 'genre': 'AlternRock',
                                       'title': 'Out of the Woodwork', 'artist': 'Courtney Barnett', 'albumartist': 'Courtney Barnett', 'samplerate': None, 'year': None, 'disc': '1', 'comment': 'Amazon.com Song ID: 240853806'}),
    ('samples/utf16be.mp3', {'title': '52-girls', 'filesize': 2048, 'track': '6', 'album': 'party mix',
                             'artist': 'The B52s', 'genre': '(17)', 'albumartist': None, 'disc': None, 'channels': 2}),
    ('samples/id3v22_image.mp3', {'title': 'Kids (MGMT Cover) ', 'filesize': 35924,
                                  'album': 'winniecooper.net ', 'artist': 'The Kooks', 'year': '2008', 'channels': 2}),

    # OGG
    ('samples/empty.ogg', {'track_total': None, 'duration': 3.684716553287982, 'album': None, '_max_samplenum': 162496, 'year': None, 'title': None,
                           'artist': None, 'track': None, '_tags_parsed': False, 'filesize': 4328, 'audio_offset': 0, 'bitrate': 109.375, 'samplerate': 44100}),
    ('samples/multipagecomment.ogg', {'track_total': None, 'duration': 3.684716553287982, 'album': None, '_max_samplenum': 162496, 'year': None,
                                      'title': None, 'artist': None, 'track': None, '_tags_parsed': False, 'filesize': 135694, 'audio_offset': 0, 'bitrate': 109.375, 'samplerate': 44100}),
    ('samples/multipage-setup.ogg', {'genre': 'JRock', 'track_total': None, 'duration': 4.128798185941043, 'album': 'Timeless', 'year': '2006', 'title': 'Burst',
                                     'artist': 'UVERworld', 'track': '7', '_tags_parsed': False, 'filesize': 76983, 'audio_offset': 0, 'bitrate': 156.25, 'samplerate': 44100}),
    ('samples/test.ogg', {'track_total': None, 'duration': 1.0, 'album': 'the boss', 'year': '2006', 'title': 'the boss', 'artist': 'james brown',
                          'track': '1', '_tags_parsed': False, 'filesize': 7467, 'audio_offset': 0, 'bitrate': 156.25, 'samplerate': 44100, 'comment': 'hello!'}),
    ('samples/corrupt_metadata.ogg', {'filesize': 18648, 'audio_offset': 0,
                                      'bitrate': 78.125, 'duration': 2.132358276643991, 'samplerate': 44100}),

    # OPUS
    ('samples/test.opus', {'albumartist': 'Alstroemeria Records', 'samplerate': 48000, 'channels': 2, 'track': '1', 'disc': '1', 'title': 'Bad Apple!!', 'duration': 2.0,
                           'year': '2008.05.25', 'filesize': 10000, 'artist': 'nomico', 'album': 'Exserens - A selection of Alstroemeria Records', 'comment': 'ARCD0018 - Lovelight'}),

    # WAV
    ('samples/test.wav', {'duration': 1.0, 'filesize': 176444, 'bitrate': 1378.125, 'samplerate': 44100, 'audio_offest': 36}),
    ('samples/test3sMono.wav', {'duration': 3.0, 'filesize': 264644, 'bitrate': 689.0625, 'duration': 3.0, 'samplerate': 44100, 'audio_offest': 36}),
    ('samples/test-tagged.wav', {'duration': 1.0, 'filesize': 176688, 'album': 'thealbum', 'artist': 'theartisst', 'bitrate': 1378.125, 'genre': 'Acid', 'samplerate': 44100, 'title': 'thetitle', 'track': '66', 'audio_offest': 36, 'comment': 'hello', 'year': '2014'}),
    ('samples/test-riff-tags.wav', {'duration': 1.0, 'filesize': 176540, 'album': None, 'artist': 'theartisst', 'bitrate': 1378.125, 'genre': 'Acid', 'samplerate': 44100, 'title': 'thetitle', 'track': None, 'audio_offest': 36, 'comment': 'hello', 'year': '2014'}),
    ('samples/silence-22khz-mono-1s.wav', {'duration': 1.0, 'filesize': 48160, 'bitrate': 344.53125, 'samplerate': 22050, 'audio_offest': 4088}),

    # FLAC
    ('samples/flac1sMono.flac', {'genre': 'Avantgarde', 'track_total': None, 'album': 'alb', 'year': '2014', 'duration': 1.0,
                                 'title': 'track', 'track': '23', 'artist': 'art', 'channels': 1, 'filesize': 26632, 'bitrate': 208.0625, 'samplerate': 44100}),
    ('samples/flac453sStereo.flac', {'channels': 2, 'track_total': None, 'album': None, 'year': None, 'duration': 453.51473922902494,
                                     'title': None, 'track': None, 'artist': None, 'filesize': 84236, 'bitrate': 1.45109671875, 'samplerate': 44100}),
    ('samples/flac1.5sStereo.flac', {'channels': 2, 'track_total': None, 'album': 'alb', 'year': '2014', 'duration': 1.4995238095238095,
                                     'title': 'track', 'track': '23', 'artist': 'art', 'filesize': 59868, 'bitrate': 311.9115195300095, 'genre': 'Avantgarde', 'samplerate': 44100}),
    ('samples/flac_application.flac', {'channels': 2, 'track_total': '11', 'album': 'Belle and Sebastian Write About Love', 'year': '2010-10-11', 'duration': 273.64,
                                       'title': 'I Want the World to Stop', 'track': '4', 'artist': 'Belle and Sebastian', 'filesize': 13000, 'bitrate': 0.37115370559859673, 'samplerate': 44100}),
    ('samples/no-tags.flac', {'channels': 2, 'track_total': None, 'album': None, 'year': None, 'duration': 3.684716553287982,
                              'title': None, 'track': None, 'artist': None, 'filesize': 4692, 'bitrate': 9.94818718614612, 'samplerate': 44100}),
    ('samples/variable-block.flac', {'channels': 2, 'track_total': None, 'album': 'Appleseed Original Soundtrack', 'year': '2004', 'duration': 261.68, 'title': 'DIVE FOR YOU',
                                     'track': '01', 'artist': 'Boom Boom Satellites', 'filesize': 10240, 'bitrate': 0.3057169061449098, 'disc': '1', 'genre': 'Anime Soundtrack', 'samplerate': 44100}),
    ('samples/106-invalid-streaminfo.flac', {'filesize': 4692}),
    ('samples/106-short-picture-block-size.flac', {'filesize': 4692,
                                                   'bitrate': 9.94818718614612, 'channels': 2, 'duration': 3.68, 'samplerate': 44100}),
    ('samples/with_id3_header.flac', {'filesize': 49805, 'album': '   ',
                                      'artist': '群星', 'disc': '0', 'title': 'A 梦 哆啦 机器猫 短信铃声', 'track': '0'}),

    # WMA
    ('samples/test2.wma', {'samplerate': 44100, 'album': 'The Colour and the Shape', 'title': 'Doll', 'bitrate': 64.04, 'filesize': 5800, 'track': 1,
                           'albumartist': 'Foo Fighters', 'artist': 'Foo Fighters', 'duration': 86.406, 'track_total': None, 'year': '1997', 'genre': 'Alternative', 'comment': ''}),

    # M4A/MP4
    ('samples/test.m4a', {'samplerate': 44100, 'duration': 314.97, 'bitrate': 256.0, 'channels': 2, 'genre': 'Pop', 'year': '2011',
                          'title': 'Nothing', 'album': 'Only Our Hearts To Lose', 'track_total': 11, 'track': 11, 'artist': 'Marian', 'filesize': 61432}),
    ('samples/test2.m4a', {'bitrate': 256.0, 'track': 1, 'albumartist': "Millie Jackson - Get It Out 'cha System - 1978", 'duration': 167.78739229024944, 'filesize': 223365, 'channels': 2, 'year': '1978', 'artist': 'Millie Jackson',
                           'track_total': 9, 'disc_total': 1, 'genre': 'R&B/Soul', 'album': "Get It Out 'cha System", 'samplerate': 44100, 'disc': 1, 'title': 'Go Out and Get Some', 'comment': "Millie Jackson - Get It Out 'cha System - 1978"}),
    ('samples/iso8859_with_image.m4a', {'artist': 'Major Lazer', 'filesize': 57017, 'title': 'Cold Water (feat. Justin Bieber & M�)', 'album': 'Cold Water (feat. Justin Bieber & M�) - Single',
                                        'year': '2016', 'samplerate': 44100, 'duration': 188.545, 'genre': 'Electronic;Music', 'albumartist': 'Major Lazer', 'channels': 2, 'bitrate': 303040.001, 'comment': '? 2016 Mad Decent'}),

])

testfolder = os.path.join(os.path.dirname(__file__))

# load custom samples
custom_samples_folder = os.path.join(testfolder, 'custom_samples')
pattern_field_name_type = [
    ('sr=(\\d+)', 'samplerate', int),
    ('dn=(\\d+)', 'disc', str),
    ('dt=(\\d+)', 'disc_total', str),
    ('d=(\\d+.?\\d*)', 'duration', float),
    ('b=(\\d+)', 'bitrate', int),
    ('c=(\\d)', 'channels', int),
]
for filename in os.listdir(custom_samples_folder):
    if filename == 'instructions.txt':
        continue
    expected_values = {}
    for pattern, fieldname, _type in pattern_field_name_type:
        match = re.findall(pattern, filename)
        if match:
            expected_values[fieldname] = _type(match[0])
    if expected_values:
        testfiles[os.path.join('custom_samples', filename)] = expected_values
    else:
        # if there are no expected values, just try parsing the file
        testfiles[os.path.join('custom_samples', filename)] = {}


def get_info(testfile, expected):
    filename = os.path.join(testfolder, testfile)
    # print(filename)
    tag = TinyTag.get(filename)

    for key, expected_val in expected.items():
        result = getattr(tag, key)
        fmt_string = 'field "%s": got %s (%s) expected %s (%s)!'
        fmt_values = (key, repr(result), type(result), repr(expected_val), type(expected_val))
        if key == 'duration' and result is not None and expected_val is not None:
            # allow duration to be off by 100 ms and a maximum of 1%
            if abs(result - expected_val) < 0.100:
                if expected_val and min(result, expected_val) / max(result, expected_val) > 0.99:
                    continue
        assert result == expected_val, fmt_string % fmt_values
    undefined_in_fixture = {}
    for key, val in tag.__dict__.items():
        if key.startswith('_') or val is None:
            continue
        if key not in expected:
            undefined_in_fixture[key] = val

    assert not undefined_in_fixture, 'Missing data in fixture \n%s' % str(undefined_in_fixture)

@pytest.mark.parametrize("testfile, expected", testfiles.items())
def test_generator(testfile, expected):
    get_info(testfile, expected)


@xfail(raises=TinyTagException, strict=True)
def test_unsupported_extension():
    bogus_file = os.path.join(testfolder, 'samples/there_is_no_such_ext.bogus')
    TinyTag.get(bogus_file)


@xfail(raises=NotImplementedError, strict=True)
def test_unsubclassed_tinytag_duration():
    tag = TinyTag(None, 0)
    tag._determine_duration(None)


@xfail(raises=NotImplementedError, strict=True)
def test_unsubclassed_tinytag_parse_tag():
    tag = TinyTag(None, 0)
    tag._parse_tag(None)


def test_mp3_length_estimation():
    ID3.set_estimation_precision(0.7)
    tag = TinyTag.get(os.path.join(testfolder, 'samples/silence-44-s-v1.mp3'))
    assert 3.5 < tag.duration < 4.0


@xfail(raises=TinyTagException, strict=True)
def test_unexpected_eof():
    ID3.get(os.path.join(testfolder, 'samples/incomplete.mp3'))


@xfail(raises=TinyTagException, strict=True)
def test_invalid_flac_file():
    Flac.get(os.path.join(testfolder, 'samples/silence-44-s-v1.mp3'))


@xfail(raises=TinyTagException, strict=True)
def test_invalid_mp3_file():
    ID3.get(os.path.join(testfolder, 'samples/flac1.5sStereo.flac'))


@xfail(raises=TinyTagException, strict=True)
def test_invalid_ogg_file():
    Ogg.get(os.path.join(testfolder, 'samples/flac1.5sStereo.flac'))


@xfail(raises=TinyTagException, strict=True)
def test_invalid_wave_file():
    Wave.get(os.path.join(testfolder, 'samples/flac1.5sStereo.flac'))


def test_mp3_image_loading():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/cover_img.mp3'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 140000 < len(image_data) < 150000, 'Image is %d bytes but should be around 145kb' % len(image_data)
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), 'The image data must start with a jpeg header'


def test_mp3_id3v22_image_loading():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/id3v22_image.mp3'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 18000 < len(image_data) < 19000, 'Image is %d bytes but should be around 18.1kb' % len(image_data)
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), 'The image data must start with a jpeg header'


def test_mp3_image_loading_without_description():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/id3image_without_description.mp3'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 28600 < len(image_data) < 28700, 'Image is %d bytes but should be around 28.6kb' % len(image_data)
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), 'The image data must start with a jpeg header'


def test_mp4_image_loading():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/iso8859_with_image.m4a'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 20000 < len(image_data) < 25000, 'Image is %d bytes but should be around 22kb' % len(image_data)


def test_to_str():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/empty.ogg'))
    assert str(tag)  # since the dict is not ordered we cannot == 'somestring'
    assert repr(tag)  # since the dict is not ordered we cannot == 'somestring'


@pytest.mark.skipif(Path is None, reason='requires pathlib.Path')
def test_pathlib():
    tag = TinyTag.get(Path(testfolder) / 'samples' / 'empty.ogg')
    assert str(tag)
    assert repr(tag)


if __name__ == '__main__':
    pytest.main(['-xrsv', __file__])
