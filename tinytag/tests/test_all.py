# SPDX-FileCopyrightText: 2019-2025 tinytag Contributors
# SPDX-License-Identifier: MIT

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=missing-module-docstring

from __future__ import annotations

import os.path

from io import BytesIO, TextIOWrapper
from math import isclose
from pathlib import Path
from platform import python_implementation, system
from sys import stdout
from unittest import skipIf, TestCase

from tinytag import ParseError, TinyTagException, UnsupportedFormatError
from tinytag import Images, OtherFields, TinyTag
from tinytag.tinytag import _ID3, _Ogg, _Wave, _Flac, _Wma, _MP4, _Aiff

TYPE_CHECKING = False

# Lazy imports for type checking
if TYPE_CHECKING:
    from typing import BinaryIO, Mapping, Union
    ExpectedTag = Mapping[str, Union[str, float, OtherFields]]
else:
    ExpectedTag = dict

TEST_FILES: dict[str, ExpectedTag] = dict([
    ('vbri.mp3', {
        'other': OtherFields(),
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.47020408163265304,
        'album': 'I Can Walk On Water I Can Fly',
        'year': '2007',
        'title': 'I Can Walk On Water I Can Fly',
        'artist': 'Basshunter',
        'track': 1,
        'filesize': 8192,
        'genre': 'Dance',
        'comment': 'Ripped by THSLIVE',
        'bitrate': 125.33333333333333,
    }),
    ('cbr.mp3', {
        'other': OtherFields(),
        'channels': 2,
        'samplerate': 44100,
        'duration': 0.48866995073891617,
        'album': 'I Can Walk On Water I Can Fly',
        'year': '2007',
        'title': 'I Can Walk On Water I Can Fly',
        'artist': 'Basshunter',
        'track': 1,
        'filesize': 8186,
        'bitrate': 128.0,
        'genre': 'Dance',
        'comment': 'Ripped by THSLIVE',
    }),
    ('vbr_xing_header.mp3', {
        'other': OtherFields(),
        'bitrate': 186.04383278145696,
        'channels': 1,
        'samplerate': 44100,
        'duration': 3.944489795918367,
        'filesize': 91731,
    }),
    ('vbr_xing_header_2channel.mp3', {
        'other': OtherFields({
            'encoder_settings': [
                'LAME 32bits version 3.99.5 (http://lame.sf.net)'
            ],
            'tlen': ['249976']
        }),
        'filesize': 2000,
        'album': "The Harpers' Masque",
        'artist': 'Knodel and Valencia',
        'bitrate': 46.276128290848305,
        'channels': 2,
        'duration': 250.04408163265308,
        'samplerate': 22050,
        'title': 'Lochaber No More',
        'year': '1992',
    }),
    ('id3v22-test.mp3', {
        'other': OtherFields({
            'encoded_by': ['iTunes v4.6'],
            'itunnorm': [
                ' 0000044E 00000061 00009B67 000044C3 00022478 00022182'
                ' 00007FCC 00007E5C 0002245E 0002214E'
            ],
            'itunes_cddb_1': [
                '9D09130B+174405+11+150+14097+27391+43983+65786+84877+99399+'
                '113226+132452+146426+163829'
            ],
            'itunes_cddb_tracknumber': ['3'],
        }),
        'channels': 2,
        'samplerate': 44100,
        'track_total': 11,
        'duration': 0.13836297152858082,
        'album': 'Hymns for the Exiled',
        'year': '2004',
        'title': 'cosmic american',
        'artist': 'Anais Mitchell',
        'track': 3,
        'filesize': 5120,
        'bitrate': 160.0,
        'comment': 'Waterbug Records, www.anaismitchell.com',
    }),
    ('silence-44-s-v1.mp3', {
        'other': OtherFields(),
        'channels': 2,
        'samplerate': 44100,
        'genre': 'Darkwave',
        'duration': 3.738712956446946,
        'album': 'Quod Libet Test Data',
        'year': '2004',
        'title': 'Silence',
        'artist': 'piman',
        'track': 2,
        'filesize': 15070,
        'bitrate': 32.0,
    }),
    ('id3v1-latin1.mp3', {
        'other': OtherFields(),
        'genre': 'Rock',
        'album': 'The Young Americans',
        'title': 'Play Dead',
        'filesize': 256,
        'track': 12,
        'artist': 'Björk',
        'year': '1993',
        'comment': '                            ',
    }),
    ('UTF16.mp3', {
        'other': OtherFields({
            'musicbrainz artist id': ['664c3e0e-42d8-48c1-b209-1efca19c0325'],
            'musicbrainz album id': ['25322466-a29b-417b-b560-399687b91ddd'],
            'musicbrainz album artist id': [
                '664c3e0e-42d8-48c1-b209-1efca19c0325'
            ],
            'musicbrainz disc id': ['p.5xoyYRtCVFe2gt0mfTfsXrO9U-'],
            'musicip puid': ['6ff97581-1c73-fc05-b4e4-a4ccee12ec84'],
            'asin': ['B003KVNV4S'],
            'musicbrainz album status': ['Official'],
            'musicbrainz album type': ['Album'],
            'musicbrainz album release country': ['United States'],
            'ufid': [
                ('http://musicbrainz.org\x00'
                 'cf639964-eabb-4c40-9673-c2117e456ea5')
            ],
            'publisher': ['4AD'],
            'tdat': ['1105'],
            'wxxx': [
                'WIKIPEDIA_RELEASE\x00http://en.wikipedia.org/wiki/High_Violet'
            ],
            'media': ['Digital'],
            'tlen': ['203733'],
            'encoder_settings': [
                'LAME 32bits version 3.98.4 (http://www.mp3dev.org/)'
            ],
        }),
        'track_total': 11,
        'track': 7,
        'artist': 'The National',
        'year': '2010',
        'album': 'High Violet',
        'title': 'Lemonworld',
        'filesize': 20480,
        'genre': 'Indie',
        'comment': 'Track 7',
    }),
    ('utf-8-id3v2.mp3', {
        'other': OtherFields(),
        'genre': 'Acustico',
        'track_total': 21,
        'track': 1,
        'filesize': 2119,
        'title': 'Gran día',
        'artist': 'Paso a paso',
        'album': 'S/T',
        'disc_total': 0,
        'year': '2003',
    }),
    ('empty_file.mp3', {
        'other': OtherFields(),
        'filesize': 0
    }),
    ('incomplete.mp3', {
        'other': OtherFields(),
        'filesize': 3
    }),
    ('silence-44khz-56k-mono-1s.mp3', {
        'other': OtherFields(),
        'channels': 1,
        'samplerate': 44100,
        'duration': 1.0265261269342902,
        'filesize': 7280,
        'bitrate': 56.0,
    }),
    ('silence-22khz-mono-1s.mp3', {
        'other': OtherFields(),
        'channels': 1,
        'samplerate': 22050,
        'filesize': 4284,
        'bitrate': 32.0,
        'duration': 1.0438932496075353,
    }),
    ('id3v24-long-title.mp3', {
        'other': OtherFields({
            'copyright': [
                '2013 Marathon Artists under exclsuive license from '
                'Courtney Barnett'
            ]
        }),
        'track': 1,
        'disc_total': 1,
        'composer': 'Courtney Barnett',
        'album': 'The Double EP: A Sea of Split Peas',
        'filesize': 10000,
        'track_total': 12,
        'genre': 'AlternRock',
        'title': 'Out of the Woodwork',
        'artist': 'Courtney Barnett',
        'albumartist': 'Courtney Barnett',
        'disc': 1,
        'comment': 'Amazon.com Song ID: 240853806',
        'year': '2013',
    }),
    ('utf16be.mp3', {
        'other': OtherFields(),
        'title': '52-girls',
        'filesize': 2048,
        'track': 6,
        'album': 'party mix',
        'artist': 'The B52s',
        'genre': 'Rock',
        'year': '1981',
    }),
    ('id3v22.TCO.genre.mp3', {
        'other': OtherFields({
            'encoded_by': ['iTunes 11.0.4'],
            'itunnorm': [
                ' 000019F0 00001E2A 00009F9A 0000C689 000312A1 00030C1A'
                ' 0000902E 00008D36 00020882 000321D6'
            ],
            'itunsmpb': [
                ' 00000000 00000210 000007B9 00000000008FB737 00000000'
                ' 008242F1 00000000 00000000 00000000 00000000 00000000'
                ' 00000000'
            ],
            'itunpgap': ['0'],
        }),
        'filesize': 500,
        'album': 'ARTPOP',
        'artist': 'Lady GaGa',
        'genre': 'Pop',
        'title': 'Applause',
    }),
    ('id3_comment_utf_16_with_bom.mp3', {
        'other': OtherFields({
            'copyright': ['(c) 2008 nin'],
            'isrc': ['USTC40852229'],
            'bpm': ['60'],
            'url': ['www.nin.com'],
            'encoded_by': ['LAME 3.97'],
        }),
        'filesize': 19980,
        'album': 'Ghosts I-IV',
        'albumartist': 'Nine Inch Nails',
        'artist': 'Nine Inch Nails',
        'disc': 1,
        'disc_total': 2,
        'title': '1 Ghosts I',
        'track': 1,
        'track_total': 36,
        'year': '2008',
        'comment': '3/4 time',
    }),
    ('id3_comment_utf_16_double_bom.mp3', {
        'other': OtherFields({
            'label': ['Unclear']
        }),
        'filesize': 512,
        'album': 'The Embrace',
        'artist': 'Johannes Heil & D.Diggler',
        'comment': 'Unclear',
        'title': 'The Embrace (Romano Alfieri Remix)',
        'year': '2012',
    }),
    ('id3_genre_id_out_of_bounds.mp3', {
        'other': OtherFields(),
        'filesize': 512,
        'album': 'MECHANICAL ANIMALS',
        'artist': 'Manson',
        'genre': '(255)',
        'title': '01 GREAT BIG WHITE WORLD',
        'year': '0',
    }),
    ('image-text-encoding.mp3', {
        'other': OtherFields(),
        'channels': 1,
        'samplerate': 22050,
        'filesize': 11104,
        'title': 'image-encoding',
        'bitrate': 32.0,
        'duration': 1.0438932496075353,
    }),
    ('id3v1_does_not_overwrite_id3v2.mp3', {
        'other': OtherFields({
            'love rating': ['L'],
            'publisher': ['Century Media']
        }),
        'filesize': 1130,
        'album': 'Somewhere Far Beyond',
        'albumartist': 'Blind Guardian',
        'artist': 'Blind Guardian',
        'genre': 'Power Metal',
        'title': 'Time What Is Time',
        'track': 1,
        'year': '1992',
    }),
    ('non_ascii_filename_äää.mp3', {
        'other': OtherFields({
            'encoder_settings': ['Lavf58.20.100']
        }),
        'filesize': 80919,
        'channels': 2,
        'duration': 5.067755102040817,
        'samplerate': 44100,
        'bitrate': 127.6701030927835,
    }),
    ('chinese_id3.mp3', {
        'other': OtherFields(),
        'filesize': 1000,
        'album': '½ÇÂäÖ®¸è',
        'albumartist': 'ËÕÔÆ',
        'artist': 'ËÕÔÆ',
        'bitrate': 128.0,
        'channels': 2,
        'duration': 0.052244897959183675,
        'genre': 'ÐÝÏÐÒôÀÖ',
        'samplerate': 44100,
        'title': '½ÇÂäÖ®¸è',
        'track': 1,
    }),
    ('cut_off_titles.mp3', {
        'other': OtherFields({
            'encoder_settings': ['Lavf54.29.104']
        }),
        'filesize': 1000,
        'album': 'ERB',
        'artist': 'Epic Rap Battles Of History',
        'bitrate': 192.0,
        'channels': 2,
        'duration': 0.052244897959183675,
        'samplerate': 44100,
        'title': 'Tony Hawk VS Wayne Gretzky',
    }),
    ('id3_xxx_lang.mp3', {
        'other': OtherFields({
            'script': ['Latn'],
            'acoustid id': ['2dc0b571-a633-45b0-aa5e-f3d25e4e0020'],
            'musicbrainz album type': ['album'],
            'musicbrainz album artist id': [
                '078a9376-3c04-4280-b7d7-b20e158f345d'
            ],
            'musicbrainz artist id': ['078a9376-3c04-4280-b7d7-b20e158f345d'],
            'barcode': ['724386668721'],
            'musicbrainz album id': ['38b555fe-24c7-37b3-ad1b-f6dea9f1aafa'],
            'musicbrainz release track id': [
                '7f7c31a5-0905-39ba-ba72-68db91d3b9da'
            ],
            'catalog_number': ['7243 8 66687 2 1'],
            'musicbrainz release group id': [
                '0f21095a-e629-389c-981a-d9569e9673c9'
            ],
            'musicbrainz album status': ['official'],
            'asin': ['B000641ZIQ'],
            'musicbrainz album release country': ['US'],
            'isrc': ['USVI20400513'],
            'lyrics': ['Don\'t fret, precious'],
            'replaygain_track_gain': ['-3.95 dB'],
            'replaygain_track_peak': ['0.999969'],
            'replaygain_album_gain': ['-8.26 dB'],
            'publisher': ['Virgin Records America'],
            'media': ['CD'],
            'tso2': ['Perfect Circle, A'],
            'ufid': [
                ('http://musicbrainz.org\x00'
                 'd2b8f0e6-735a-42ee-adf0-7eca4e65cd72')
            ],
            'tsop': ['Perfect Circle, A'],
            'tory': ['2004'],
            'originalyear': ['2004'],
            'tdat': ['0211'],
            'ipls': [
                ('producer\x00Billy Howerdel\x00'
                 'producer\x00Maynard James Keenan\x00'
                 'engineer\x00Billy Howerdel\x00engineer\x00Critter')
            ],
        }),
        'filesize': 6943,
        'album': 'eMOTIVe',
        'albumartist': 'A Perfect Circle',
        'artist': 'A Perfect Circle',
        'composer': 'Billy Howerdel/Maynard James Keenan',
        'bitrate': 192.0,
        'channels': 2,
        'duration': 0.13198711063372717,
        'genre': 'Rock',
        'samplerate': 44100,
        'title': 'Counting Bodies Like Sheep to the Rhythm of the War Drums',
        'track': 10,
        'comment': '                            ',
        'disc': 1,
        'disc_total': 1,
        'track_total': 12,
        'year': '2004',
    }),
    ('vbr8.mp3', {
        'filesize': 9504,
        'bitrate': 8.25,
        'channels': 1,
        'duration': 9.216,
        'other': OtherFields(),
        'samplerate': 8000,
    }),
    ('vbr8stereo.mp3', {
        'filesize': 9504,
        'bitrate': 8.25,
        'channels': 2,
        'duration': 9.216,
        'other': OtherFields(),
        'samplerate': 8000,
    }),
    ('vbr11.mp3', {
        'filesize': 9360,
        'bitrate': 8.143465909090908,
        'channels': 1,
        'duration': 9.195102040816327,
        'other': OtherFields(),
        'samplerate': 11025,
    }),
    ('vbr11stereo.mp3', {
        'filesize': 9360,
        'bitrate': 8.143465909090908,
        'channels': 2,
        'duration': 9.195102040816327,
        'other': OtherFields(),
        'samplerate': 11025,
    }),
    ('vbr16.mp3', {
        'filesize': 9432,
        'bitrate': 8.251968503937007,
        'channels': 1,
        'duration': 9.144,
        'other': OtherFields(),
        'samplerate': 16000,
    }),
    ('vbr16stereo.mp3', {
        'filesize': 9432,
        'bitrate': 8.251968503937007,
        'channels': 2,
        'duration': 9.144,
        'other': OtherFields(),
        'samplerate': 16000,
    }),
    ('vbr22.mp3', {
        'filesize': 9282,
        'bitrate': 8.145021489971347,
        'channels': 1,
        'duration': 9.11673469387755,
        'other': OtherFields(),
        'samplerate': 22050,
    }),
    ('vbr22stereo.mp3', {
        'filesize': 9282,
        'bitrate': 8.145021489971347,
        'channels': 2,
        'duration': 9.11673469387755,
        'other': OtherFields(),
        'samplerate': 22050,
    }),
    ('vbr32.mp3', {
        'filesize': 37008,
        'bitrate': 32.50592885375494,
        'channels': 1,
        'duration': 9.108,
        'other': OtherFields(),
        'samplerate': 32000,
    }),
    ('vbr32stereo.mp3', {
        'filesize': 37008,
        'bitrate': 32.50592885375494,
        'channels': 2,
        'duration': 9.108,
        'other': OtherFields(),
        'samplerate': 32000,
    }),
    ('vbr44.mp3', {
        'filesize': 36609,
        'bitrate': 32.21697198275862,
        'channels': 1,
        'duration': 9.09061224489796,
        'other': OtherFields(),
        'samplerate': 44100,
    }),
    ('vbr44stereo.mp3', {
        'filesize': 36609,
        'bitrate': 32.21697198275862,
        'channels': 2,
        'duration': 9.09061224489796,
        'other': OtherFields(),
        'samplerate': 44100,
    }),
    ('vbr48.mp3', {
        'filesize': 36672,
        'bitrate': 32.33862433862434,
        'channels': 1,
        'duration': 9.072,
        'other': OtherFields(),
        'samplerate': 48000,
    }),
    ('vbr48stereo.mp3', {
        'filesize': 36672,
        'bitrate': 32.33862433862434,
        'channels': 2,
        'duration': 9.072,
        'other': OtherFields(),
        'samplerate': 48000,
    }),
    ('id3v24_genre_null_byte.mp3', {
        'other': OtherFields(),
        'filesize': 256,
        'album': '\u79d8\u5bc6',
        'albumartist': 'aiko',
        'artist': 'aiko',
        'disc': 1,
        'genre': 'Pop',
        'title': '\u661f\u306e\u306a\u3044\u4e16\u754c',
        'track': 10,
        'year': '2008',
    }),
    ('vbr_xing_header_short.mp3', {
        'filesize': 432,
        'bitrate': 24.0,
        'channels': 1,
        'duration': 0.144,
        'other': OtherFields(),
        'samplerate': 8000,
    }),
    ('id3_multiple_artists.mp3', {
        'other': OtherFields({
            'artist': [
                'artist2',
                'artist3',
                'artist4',
                'artist5',
                'artist6',
                'artist7',
            ]
        }),
        'filesize': 2007,
        'bitrate': 57.39124999999999,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
        'artist': 'artist1',
        'genre': 'something 1',
    }),
    ('id3_frames.mp3', {
        'filesize': 27576,
        'bitrate': 50.03636363636364,
        'channels': 1,
        'duration': 3.96,
        'samplerate': 16000,
        'other': OtherFields(),
    }),
    ('id3v22_with_image.mp3', {
        'other': OtherFields(),
        'filesize': 2311,
        'title': 'image',
    }),
    ('utf16_no_bom.mp3', {
        'other': OtherFields(),
        'filesize': 1069,
        'title': 'no bom test ë',
        'artist': 'no bom test 2 ë',
    }),
    ('title_after_image.mp3', {
        'other': OtherFields(),
        'filesize': 2311,
        'title': 'title after image',
        'track': 1,
    }),
    ('grouping.mp3', {
        'other': OtherFields({
            'grouping': ['some grouping'],
        }),
        'filesize': 2007,
        'bitrate': 57.39124999999999,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
        'year': '2025',
        'track': 1,
        'track_total': 2,
    }),
    ('classical.mp3', {
        'other': OtherFields({
            'grouping': ['some grouping'],
            'work': ['some work'],
            'movement_name': ['some movement'],
            'movement': ['1'],
            'movement_total': ['2'],
            'show_movement': ['1']
        }),
        'filesize': 2007,
        'bitrate': 57.39124999999999,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
        'composer': 'some composer',
        'genre': 'Classical',
        'year': '2025',
        'track': 1,
        'track_total': 2,
    }),
    ('empty_frame.mp3', {
        'other': OtherFields(),
        'filesize': 2005,
        'bitrate': 57.39124999999999,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
        'album': 'some album',
        'artist': 'some artist',
    }),
    ('synced_lyrics_milliseconds.mp3', {
        'other': OtherFields({
            'lyrics': ['[00:00.00]\n[00:01.00]first line\n[00:01.55]second '
                       'line\n[00:05.99]third line'],
        }),
        'filesize': 2007,
        'bitrate': 57.39124999999999,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
    }),
    ('synced_lyrics_invalid.mp3', {
        'other': OtherFields({
            'lyrics': ['\nfirst line\nsecond line\nthird line'],
        }),
        'filesize': 2007,
        'bitrate': 57.39124999999999,
        'channels': 1,
        'duration': 0.1306122448979592,
        'samplerate': 44100,
    }),
    ('empty.ogg', {
        'other': OtherFields(),
        'duration': 3.684716553287982,
        'filesize': 4328,
        'bitrate': 112.0,
        'samplerate': 44100,
        'channels': 2,
    }),
    ('multipage-setup.ogg', {
        'other': OtherFields({
            'transcoded': ['mp3;241'],
            'replaygain_album_gain': ['-10.29 dB'],
            'replaygain_album_peak': ['1.50579047'],
            'replaygain_track_peak': ['1.17979193'],
            'replaygain_track_gain': ['-10.02 dB'],
        }),
        'genre': 'JRock',
        'duration': 4.128798185941043,
        'album': 'Timeless',
        'year': '2006',
        'title': 'Burst',
        'artist': 'UVERworld',
        'track': 7,
        'filesize': 76983,
        'bitrate': 160.0,
        'samplerate': 44100,
        'comment': 'SRCL-6240',
        'channels': 2,
    }),
    ('test.ogg', {
        'other': OtherFields(),
        'duration': 1.0,
        'album': 'the boss',
        'year': '2006',
        'title': 'the boss',
        'artist': 'james brown',
        'track': 1,
        'filesize': 7467,
        'bitrate': 160.0,
        'samplerate': 44100,
        'channels': 2,
        'comment': 'hello!',
    }),
    ('corrupt_metadata.ogg', {
        'other': OtherFields(),
        'filesize': 18648,
        'bitrate': 80.0,
        'duration': 2.132358276643991,
        'samplerate': 44100,
        'channels': 1,
    }),
    ('composer.ogg', {
        'other': OtherFields(),
        'filesize': 4480,
        'album': 'An Album',
        'artist': 'An Artist',
        'composer': 'some composer',
        'bitrate': 112.0,
        'duration': 3.684716553287982,
        'channels': 2,
        'genre': 'Some Genre',
        'samplerate': 44100,
        'title': 'A Title',
        'track': 2,
        'year': '2007',
        'comment': 'A Comment',
    }),
    ('ogg_with_image.ogg', {
        'other': OtherFields(),
        'channels': 1,
        'duration': 0.1,
        'filesize': 5759,
        'bitrate': 96.0,
        'samplerate': 44100,
        'artist': 'Sample Artist',
        'title': 'Sample Title',
    }),
    ('classical.ogg', {
        'other': OtherFields({
            'grouping': ['some grouping', 'some content group'],
            'work': ['some work'],
            'movement_name': ['some movement'],
            'movement': ['1'],
            'movement_total': ['2'],
            'show_movement': ['1']
        }),
        'channels': 1,
        'duration': 0.1,
        'filesize': 4279,
        'bitrate': 96.0,
        'samplerate': 44100,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
        'composer': 'some composer',
        'genre': 'Classical',
        'year': '2025',
        'track': 1,
        'track_total': 2
    }),
    ('data_after_eos.ogg', {
        'other': OtherFields(),
        'duration': 3.684716553287982,
        'filesize': 4424,
        'bitrate': 112.0,
        'samplerate': 44100,
        'channels': 2,
    }),
    ('test.opus', {
        'other': OtherFields({
            'encoder': ['Lavc57.24.102 libopus'],
            'arrange': ['\u6771\u65b9'],
            'catalogid': ['ARCD0024'],
            'discid': ['A212230D'],
            'event': ['\u4f8b\u5927\u796d5'],
            'lyricist': ['Haruka'],
            'mastering': ['Hedonist'],
            'origin': ['\u6771\u65b9\u5e7b\u60f3\u90f7'],
            'originaltitle': ['Bad Apple!!'],
            'performer': ['Masayoshi Minoshima'],
            'vocal': ['nomico'],
        }),
        'albumartist': 'Alstroemeria Records',
        'samplerate': 48000,
        'channels': 2,
        'track': 1,
        'disc': 1,
        'title': 'Bad Apple!!',
        'duration': 0.9935,
        'bitrate': 51.5832913940614,
        'year': '2008.05.25',
        'filesize': 10000,
        'artist': 'nomico',
        'album': 'Exserens - A selection of Alstroemeria Records',
        'comment': 'ARCD0018 - Lovelight',
        'disc_total': 1,
        'track_total': 13,
    }),
    ('8khz_5s.opus', {
        'other': OtherFields({
            'encoder': ['opusenc from opus-tools 0.2']
        }),
        'filesize': 7251,
        'channels': 1,
        'samplerate': 48000,
        'duration': 5.0,
        'bitrate': 9.5952
    }),
    ('test_flac.oga', {
        'other': OtherFields({
            'copyright': ['test3'],
            'isrc': ['test4'],
            'lyrics': ['test7']
        }),
        'filesize': 9273,
        'album': 'test2',
        'artist': 'test6',
        'comment': 'test5',
        'bitrate': 20.022488249118684,
        'duration': 3.705034013605442,
        'channels': 2,
        'genre': 'Acoustic',
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'test1',
        'track': 5,
        'year': '2023',
    }),
    ('test.spx', {
        'other': OtherFields(),
        'filesize': 7921,
        'channels': 1,
        'samplerate': 16000,
        'bitrate': -1,
        'duration': 2.1445625,
        'artist': 'test1',
        'title': 'test2',
        'comment': 'Encoded with Speex 1.2.0',
    }),
    ('test.wav', {
        'other': OtherFields(),
        'channels': 2,
        'duration': 1.0,
        'filesize': 176444,
        'bitrate': 1411.2,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('test3sMono.wav', {
        'other': OtherFields(),
        'channels': 1,
        'duration': 3.0,
        'filesize': 264644,
        'bitrate': 705.6,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('test-tagged.wav', {
        'other': OtherFields(),
        'channels': 2,
        'duration': 1.0,
        'filesize': 176688,
        'album': 'thealbum',
        'artist': 'theartisst',
        'bitrate': 1411.2,
        'genre': 'Acid',
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'thetitle',
        'track': 66,
        'comment': 'hello',
        'year': '2014',
    }),
    ('test-riff-tags.wav', {
        'other': OtherFields(),
        'channels': 2,
        'duration': 1.0,
        'filesize': 176540,
        'artist': 'theartisst',
        'bitrate': 1411.2,
        'genre': 'Acid',
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'thetitle',
        'comment': 'hello',
        'year': '2014',
    }),
    ('silence-22khz-mono-1s.wav', {
        'other': OtherFields(),
        'channels': 1,
        'duration': 0.9991836734693877,
        'filesize': 48160,
        'bitrate': 352.8,
        'samplerate': 22050,
        'bitdepth': 16,
    }),
    ('id3_header_with_a_zero_byte.wav', {
        'other': OtherFields({
            'title': ['Stacked']
        }),
        'channels': 1,
        'duration': 1.0,
        'filesize': 44280,
        'bitrate': 352.8,
        'samplerate': 22050,
        'bitdepth': 16,
        'artist': 'Purpley',
        'title': 'Test000',
        'track': 17,
        'album': 'prototypes',
    }),
    ('adpcm.wav', {
        'other': OtherFields(),
        'channels': 1,
        'duration': 12.167256235827665,
        'filesize': 268686,
        'bitrate': 176.4,
        'samplerate': 44100,
        'bitdepth': 4,
        'artist': 'test artist',
        'title': 'test title',
        'track': 1,
        'album': 'test album',
        'comment': 'test comment',
        'genre': 'test genre',
        'year': '1990',
    }),
    ('riff_extra_zero.wav', {
        'other': OtherFields(),
        'channels': 2,
        'duration': 0.11609977324263039,
        'filesize': 20670,
        'bitrate': 1411.2,
        'samplerate': 44100,
        'bitdepth': 16,
        'artist': 'B.O.S.E.',
        'title': 'Mission Bass',
        'album': '808 Bass Express',
        'genre': 'Hip-Hop/Rap',
        'year': '1996',
        'track': 3,
    }),
    ('riff_extra_zero_2.wav', {
        'other': OtherFields(),
        'channels': 2,
        'duration': 0.11609977324263039,
        'filesize': 20682,
        'bitrate': 1411.2,
        'samplerate': 44100,
        'bitdepth': 16,
        'artist': 'The Jimmy Castor Bunch',
        'title': 'It\'s Just Begun',
        'album': 'The Perfect Beats, Vol. 4',
        'genre': 'Pop Electronica',
        'track': 7,
    }),
    ('wav_invalid_track_number.wav', {
        'other': OtherFields(),
        'filesize': 8908,
        'bitrate': 705.6,
        'duration': 0.1,
        'samplerate': 44100,
        'channels': 1,
        'bitdepth': 16,
    }),
    ('gsm_6_10.wav', {
        'other': OtherFields(),
        'bitdepth': 1,
        'bitrate': 44.1,
        'channels': 1,
        'duration': 0.16507936507936508,
        'filesize': 1246,
        'samplerate': 44100,
        'album': 'album',
        'artist': 'artist',
        'title': 'track',
        'track': 99,
        'year': '2010',
        'comment': 'some comment here',
        'genre': 'Bass',
    }),
    ('wav_with_image.wav', {
        'other': OtherFields(),
        'channels': 1,
        'duration': 2.14475,
        'filesize': 22902,
        'bitrate': 64.0,
        'samplerate': 8000,
        'bitdepth': 8,
    }),
    ('flac1sMono.flac', {
        'other': OtherFields(),
        'genre': 'Avantgarde',
        'album': 'alb',
        'year': '2014',
        'duration': 1.0,
        'title': 'track',
        'track': 23,
        'artist': 'art',
        'channels': 1,
        'filesize': 26632,
        'bitrate': 213.056,
        'samplerate': 44100,
        'bitdepth': 16,
        'comment': 'hello',
    }),
    ('flac453sStereo.flac', {
        'other': OtherFields(),
        'channels': 2,
        'duration': 453.51473922902494,
        'filesize': 84236,
        'bitrate': 1.4859230399999999,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('flac1.5sStereo.flac', {
        'other': OtherFields(),
        'channels': 2,
        'album': 'alb',
        'year': '2014',
        'duration': 1.4995238095238095,
        'title': 'track',
        'track': 23,
        'artist': 'art',
        'filesize': 59868,
        'bitrate': 319.39739599872973,
        'genre': 'Avantgarde',
        'samplerate': 44100,
        'bitdepth': 16,
        'comment': 'hello',
    }),
    ('flac_application.flac', {
        'other': OtherFields({
            'replaygain_track_peak': ['0.9976'],
            'musicbrainz_albumartistid': [
                'e5c7b94f-e264-473c-bb0f-37c85d4d5c70'
            ],
            'musicbrainz_trackid': ['e65fb332-0c1e-4172-85e0-59cd37e5669e'],
            'replaygain_album_gain': ['-8.14 dB'],
            'labelid': ['RTRADLP480'],
            'musicbrainz_albumid': ['359a91e9-3bb3-4b60-a823-8aaa4bad1e36'],
            'artistsort': ['Belle and Sebastian'],
            'replaygain_track_gain': ['-8.08 dB'],
            'replaygain_album_peak': ['1.0000'],
        }),
        'channels': 2,
        'track_total': 11,
        'album': 'Belle and Sebastian Write About Love',
        'year': '2010-10-11',
        'duration': 273.64,
        'title': 'I Want the World to Stop',
        'track': 4,
        'artist': 'Belle and Sebastian',
        'filesize': 13000,
        'bitrate': 0.38006139453296306,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('no-tags.flac', {
        'other': OtherFields(),
        'channels': 2,
        'duration': 3.684716553287982,
        'filesize': 4692,
        'bitrate': 10.186943678613627,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('variable-block.flac', {
        'other': OtherFields({
            'discid': ['AA0B360B'],
            'japanese title': ['アップルシード オリジナル・サウンドトラック'],
            'organization': ['Sony Music Records (SRCP-371)'],
            'ripper': ['Exact Audio Copy 0.99pb5'],
            'replaygain_album_gain': ['-8.68 dB'],
            'replaygain_album_peak': ['1.000000'],
            'replaygain_track_gain': ['-9.61 dB'],
            'replaygain_track_peak': ['1.000000'],
        }),
        'channels': 2,
        'album': 'Appleseed Original Soundtrack',
        'year': '2004',
        'duration': 261.68,
        'title': 'DIVE FOR YOU',
        'track': 1,
        'track_total': 11,
        'artist': 'Boom Boom Satellites',
        'filesize': 10240,
        'bitrate': 0.31305411189238763,
        'disc': 1,
        'genre': 'Anime Soundtrack',
        'samplerate': 44100,
        'bitdepth': 16,
        'disc_total': 2,
        'comment': 'Original Soundtrack',
        'composer': 'Boom Boom Satellites (Lyrics)',
    }),
    ('106-invalid-streaminfo.flac', {
        'other': OtherFields(),
        'filesize': 4692
    }),
    ('106-short-picture-block-size.flac', {
        'other': OtherFields(),
        'filesize': 4692,
        'bitrate': 10.186943678613627,
        'channels': 2,
        'duration': 3.684716553287982,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('with_padded_id3_header.flac', {
        'other': OtherFields(),
        'filesize': 16070,
        'album': 'album',
        'artist': 'artist',
        'bitrate': 283.4748,
        'channels': 1,
        'duration': 0.45351473922902497,
        'genre': 'genre',
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'title',
        'track': 1,
        'year': '2018',
        'comment': 'comment',
    }),
    ('with_padded_id3_header2.flac', {
        'other': OtherFields({
            'tlen': ['297666'],
            'encoded_by': ['Exact Audio Copy   (Sicherer Modus)'],
            'encoder_settings': [
                'flac.exe -T "artist=Unbekannter Künstler" '
                '-T "title=Track01" -T "album=Unbekannter Titel" '
                '-T "date=" -T "tracknumber=01" -T "genre=" -5'
            ],
            'artist': ['Unbekannter Künstler'],
            'album': ['Unbekannter Titel'],
            'title': ['Track01'],
        }),
        'filesize': 19522,
        'album': 'album',
        'artist': 'artist',
        'bitrate': 344.36807999999996,
        'channels': 1,
        'disc': 1,
        'disc_total': 1,
        'duration': 0.45351473922902497,
        'genre': 'genre',
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'title',
        'track': 1,
        'track_total': 5,
        'year': '2018',
        'comment': 'comment',
    }),
    ('flac_invalid_track_number.flac', {
        'other': OtherFields(),
        'filesize': 235,
        'bitrate': 18.8,
        'channels': 1,
        'duration': 0.1,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('flac_with_image.flac', {
        'other': OtherFields({
            'artist': ['artist 2', 'artist 3'],
            'genre': ['genre 2'],
            'album': ['album 2'],
            'url': ['https://example.com'],
        }),
        'filesize': 2824,
        'album': 'album 1',
        'artist': 'artist 1',
        'bitrate': 225.92,
        'channels': 1,
        'duration': 0.1,
        'genre': 'genre 1',
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('unsynced_lyrics.flac', {
        'other': OtherFields({
            'lyrics': ['some lyrics here\nnew line']
        }),
        'channels': 2,
        'duration': 3.684716553287982,
        'filesize': 4777,
        'bitrate': 10.371489759747933,
        'samplerate': 44100,
        'bitdepth': 16,
    }),
    ('test2.wma', {
        'other': OtherFields({
            '_track': ['0'],
            'mediaprimaryclassid': ['{D1607DBC-E323-4BE2-86A1-48A42A28441E}'],
            'encodingtime': ['128861118183900000'],
            'wmfsdkversion': ['11.0.5721.5145'],
            'wmfsdkneeded': ['0.0.0.0000'],
            'isvbr': ['1'],
            'peakvalue': ['30369'],
            'averagelevel': ['7291'],
        }),
        'samplerate': 44100,
        'album': 'The Colour and the Shape',
        'title': 'Doll',
        'bitrate': 64.04,
        'filesize': 5800,
        'track': 1,
        'albumartist': 'Foo Fighters',
        'artist': 'Foo Fighters',
        'duration': 83.406,
        'year': '1997',
        'genre': 'Alternative',
        'composer': 'Foo Fighters',
        'channels': 2,
    }),
    ('lossless.wma', {
        'other': OtherFields(),
        'samplerate': 44100,
        'bitrate': 667.296,
        'filesize': 2500,
        'bitdepth': 16,
        'duration': 43.133,
        'channels': 2,
    }),
    ('wma_invalid_track_number.wma', {
        'other': OtherFields({
            'encoder_settings': ['Lavf60.16.100']
        }),
        'filesize': 3940,
        'bitrate': 128.0,
        'duration': 2.1409999999999996,
        'samplerate': 44100,
        'channels': 1,
    }),
    ('grouping.wma', {
        'other': OtherFields({
            'grouping': ['some grouping'],
            'work': ['some work'],
        }),
        'filesize': 4070,
        'bitrate': 128.0,
        'duration': 2.1409999999999996,
        'samplerate': 44100,
        'channels': 1,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
        'year': '2025',
    }),
    ('test.m4a', {
        'other': OtherFields({
            'itunsmpb': [
                ' 00000000 00000840 000001DC 0000000000D3E9E4 00000000'
                ' 00000000 00000000 00000000 00000000 00000000 00000000'
                ' 00000000'
            ],
            'itunnorm': [
                ' 00000358 0000032E 000020AE 000020D9 0003A228 00032A28'
                ' 00007E20 00007E90 00007BFD 00009293'
            ],
            'itunes_cddb_ids': ['11++'],
            'ufidhttp://www.cddb.com/id3/taginfo1.html': [
                '3CD3N48Q241232290U3387DD249F72E6B082B283425ADB9B0F324P1'
            ],
            'bpm': ['0'],
            'encoded_by': ['iTunes 10.5'],
            'cpil': ['0'],
            'pgap': ['0'],
        }),
        'samplerate': 44100,
        'duration': 314.97868480725623,
        'bitrate': 256.0,
        'channels': 2,
        'genre': 'Pop',
        'year': '2011',
        'title': 'Nothing',
        'album': 'Only Our Hearts To Lose',
        'track_total': 11,
        'track': 11,
        'artist': 'Marian',
        'filesize': 61432,
    }),
    ('mpeg4_with_image.m4a', {
        'other': OtherFields({
            'publisher': ['test7'],
            'bpm': ['1'],
            'encoded_by': ['Lavf60.3.100']
        }),
        'artist': 'test1',
        'composer': 'test8',
        'filesize': 7371,
        'samplerate': 8000,
        'duration': 1.294,
        'channels': 1,
        'bitrate': 27.887,
    }),
    ('alac_file.m4a', {
        'other': OtherFields({
            'copyright': ['© Hyperion Records Ltd, London'],
            'lyrics': ['Album notes:'],
            'upc': ['0034571177380']
        }),
        'artist': 'Howard Shelley',
        'filesize': 20000,
        'composer': 'Clementi, Muzio (1752-1832)',
        'title': 'Clementi: Piano Sonata in D major, Op 25 No 6 - Movement 2: '
                 'Un poco andante',
        'album': 'Clementi: The Complete Piano Sonatas, Vol. 4',
        'year': '2009',
        'track': 14,
        'track_total': 27,
        'disc': 1,
        'disc_total': 1,
        'samplerate': 44100,
        'duration': 166.62639455782312,
        'genre': 'Classical',
        'albumartist': 'Howard Shelley',
        'channels': 2,
        'bitrate': 436.743,
        'bitdepth': 16,
    }),
    ('mpeg4_desc_cmt.m4a', {
        'other': OtherFields({
            'description': ['test description'],
            'encoded_by': ['Lavf59.27.100']
        }),
        'filesize': 32006,
        'bitrate': 101.038,
        'channels': 2,
        'comment': 'test comment',
        'duration': 2.36,
        'samplerate': 44100,
    }),
    ('mpeg4_xa9des.m4a', {
        'other': OtherFields({
            'description': ['test description']
        }),
        'filesize': 2639,
        'comment': 'test comment',
        'duration': 727.1066666666667,
    }),
    ('test2.m4a', {
        'other': OtherFields({
            'publisher': ['test7'],
            'bpm': ['99999'],
            'encoded_by': ['Lavf60.3.100']
        }),
        'artist': 'test1',
        'composer': 'test8',
        'filesize': 6260,
        'samplerate': 8000,
        'duration': 1.294,
        'channels': 1,
        'bitrate': 27.887,
    }),
    ('mvhd_version_1.m4a', {
        'other': OtherFields(),
        'title': '64-bit test',
        'filesize': 2048,
        'samplerate': 44100,
        'duration': 123251.6585941043,
        'channels': 2,
        'bitrate': 0.0,
    }),
    ('multi_value.m4a', {
        'other': OtherFields({
            'artist': ['another artist', 'yet another artist'],
            'composer': [
                'another composer', 'yet another composer', 'last composer'
            ],
            'custom': ['value1', 'value2', 'value3'],
            'encoded_by': ['Lavf61.7.100'],
            'grouping': ['grouping', 'second grouping']
        }),
        'artist': 'some artist',
        'title': 'some title',
        'album': 'some album',
        'composer': 'some composer',
        'filesize': 1995,
        'samplerate': 44100,
        'duration': 0.524,
        'channels': 1,
        'bitrate': 1.666,
    }),
    ('mixed_case_atoms.m4a', {
        'other': OtherFields({
            'plid': ['1'],
            'atid': ['2'],
            'cnid': ['3'],
            'pgap': ['1'],
        }),
        'filesize': 1995,
        'samplerate': 44100,
        'duration': 0.524,
        'channels': 1,
        'bitrate': 1.666,
    }),
    ('classical.m4a', {
        'other': OtherFields({
            'grouping': ['some grouping'],
            'work': ['some work'],
            'movement_name': ['some movement'],
            'movement': ['1'],
            'movement_total': ['2'],
            'show_movement': ['1'],
        }),
        'filesize': 1995,
        'samplerate': 44100,
        'duration': 0.524,
        'channels': 1,
        'bitrate': 1.666,
        'title': 'some title',
        'album': 'some album',
        'artist': 'some artist',
        'composer': 'some composer',
        'genre': 'Classical',
        'year': '2025',
        'track': 1,
        'track_total': 2,
    }),
    ('mp4_extended_size.m4a', {
        'other': OtherFields({
            'description': ['test description'],
            'encoded_by': ['Lavf59.27.100']
        }),
        'comment': 'test comment',
        'filesize': 32014,
        'samplerate': 44100,
        'duration': 2.36,
        'channels': 2,
        'bitrate': 101.038,
    }),
    ('mp4_extended_size_truncated.m4a', {
        'other': OtherFields(),
        'filesize': 39
    }),
    ('mp4_size_zero.m4a', {
        'other': OtherFields(),
        'filesize': 152,
        'duration': 2.0
    }),
    ('test-tagged.aiff', {
        'other': OtherFields(),
        'channels': 2,
        'duration': 1.0,
        'filesize': 177620,
        'artist': 'theartist',
        'bitrate': 1411.2,
        'genre': 'Acid',
        'samplerate': 44100,
        'bitdepth': 16,
        'track': 1,
        'title': 'thetitle',
        'album': 'thealbum',
        'comment': 'hello',
        'year': '2014',
    }),
    ('test.aiff', {
        'other': OtherFields({
            'copyright': ['℗ 1992 Ace Records']
        }),
        'channels': 2,
        'duration': 0.0,
        'filesize': 164,
        'bitrate': 1411.2,
        'samplerate': 44100,
        'bitdepth': 16,
        'title': 'Go Out and Get Some',
        'comment': 'Millie Jackson - Get It Out \'cha System - 1978',
    }),
    ('pluck-pcm8.aiff', {
        'other': OtherFields(),
        'channels': 2,
        'duration': 0.2999546485260771,
        'filesize': 6892,
        'artist': 'Serhiy Storchaka',
        'title': 'Pluck',
        'album': 'Python Test Suite',
        'bitrate': 176.4,
        'samplerate': 11025,
        'bitdepth': 8,
        'comment': 'Audacity Pluck + Wahwah',
        'year': '2013',
    }),
    ('M1F1-mulawC-AFsp.afc', {
        'other': OtherFields({
            'comment': ['user: kabal@CAPELLA', 'program: CopyAudio']
        }),
        'channels': 2,
        'duration': 2.936625,
        'filesize': 47148,
        'bitrate': 256.0,
        'samplerate': 8000,
        'bitdepth': 16,
        'comment': 'AFspdate: 2003-01-30 03:28:34 UTC',
    }),
    ('invalid_sample_rate.aiff', {
        'other': OtherFields(),
        'channels': 1,
        'filesize': 4096,
        'bitdepth': 16,
    }),
    ('aiff_extra_tags.aiff', {
        'other': OtherFields({
            'copyright': ['test'],
            'isrc': ['CC-XXX-YY-NNNNN']
        }),
        'channels': 1,
        'duration': 2.176,
        'filesize': 18532,
        'bitrate': 64.0,
        'samplerate': 8000,
        'bitdepth': 8,
        'title': 'song title',
        'artist': 'artist 1;artist 2',
    }),
    ('aiff_with_image.aiff', {
        'other': OtherFields(),
        'channels': 1,
        'duration': 2.176,
        'filesize': 21044,
        'bitrate': 64.0,
        'samplerate': 8000,
        'bitdepth': 8,
        'title': 'image',
    }),
])

SAMPLE_FOLDER = os.path.join(os.path.dirname(__file__), 'samples')


class TestAll(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # Use utf-8 encoding for debug print()
        if isinstance(stdout, TextIOWrapper):
            stdout.reconfigure(encoding='utf-8')

    def compare_tag(self,
                    results: ExpectedTag,
                    expected: ExpectedTag,
                    file: str) -> None:
        def error_fmt(value: str | float | list[str]) -> str:
            return f'{repr(value)} ({type(value)})'

        def assert_complete_data(results: ExpectedTag | OtherFields,
                                 expected: ExpectedTag | OtherFields) -> None:
            missing_result_fields = set(expected) - set(results)
            missing_expected_fields = set(results) - set(expected)
            self.assertFalse(
                missing_result_fields,
                f'Missing fields in tag \n{missing_result_fields}')
            self.assertFalse(
                missing_expected_fields,
                f'Missing fields in test case \n{missing_expected_fields}')

        def assert_values_match(path: str,
                                result_val: str | float | list[str],
                                expected_val: str | float | list[str]) -> None:
            fmt_string = 'field "%s": got %s expected %s in %s!'
            fmt_values = (
                path, error_fmt(result_val), error_fmt(expected_val), file)
            values_match = False
            # lets not copy *all* the lyrics inside the fixture
            if (path == 'other.lyrics'
                    and isinstance(expected_val, list)
                    and isinstance(result_val, list)):
                values_match = result_val[0].startswith(expected_val[0])
            elif (isinstance(result_val, float)
                    and isinstance(expected_val, float)):
                values_match = isclose(result_val, expected_val)
            else:
                values_match = result_val == expected_val
            self.assertTrue(values_match, fmt_string % fmt_values)

        assert_complete_data(results, expected)

        for path, result_val in results.items():
            expected_val = expected[path]
            if (isinstance(result_val, OtherFields)
                    and isinstance(expected_val, OtherFields)):
                assert_complete_data(result_val, expected_val)

                for other_key, other_result_val in result_val.items():
                    other_path = f"{path}.{other_key}"
                    assert_values_match(
                        other_path, other_result_val,
                        expected_val[other_key]
                    )
            elif (not isinstance(result_val, OtherFields)
                    and not isinstance(expected_val, OtherFields)):
                assert_values_match(path, result_val, expected_val)

    def test_file_reading_all(self) -> None:
        for testfile, expected in TEST_FILES.items():
            with self.subTest(testfile=testfile, expected=expected):
                filename = os.path.join(SAMPLE_FOLDER, testfile)
                tag = TinyTag.get(
                    filename, tags=True, duration=True, image=True)
                results = {
                    key: val for key, val in tag.__dict__.items()
                    if not key.startswith('_') and key != 'filename'
                    and val is not None and not isinstance(val, Images)
                }
                self.compare_tag(results, expected, filename)

    def test_file_reading_tags(self) -> None:
        for testfile, expected in TEST_FILES.items():
            with self.subTest(testfile=testfile, expected=expected):
                filename = os.path.join(SAMPLE_FOLDER, testfile)
                excluded_attrs = {
                    'bitdepth', 'bitrate', 'channels', 'duration', 'samplerate'
                }
                tag = TinyTag.get(filename, tags=True, duration=False)
                results = {
                    key: val for key, val in tag.__dict__.items()
                    if not key.startswith('_') and key != 'filename'
                    and val is not None and not isinstance(val, Images)
                }
                filtered_expected = {
                    key: val for key, val in expected.items()
                    if key not in excluded_attrs
                }
                self.compare_tag(results, filtered_expected, filename)
                assert tag.images.any is None

    def test_file_reading_duration(self) -> None:
        for testfile, expected in TEST_FILES.items():
            with self.subTest(testfile=testfile, expected=expected):
                filename = os.path.join(SAMPLE_FOLDER, testfile)
                allowed_attrs = {
                    'bitdepth', 'bitrate', 'channels', 'duration',
                    'filesize', 'samplerate'}
                tag = TinyTag.get(filename, tags=False, duration=True)
                results = {
                    key: val for key, val in tag.__dict__.items()
                    if not key.startswith('_') and key != 'filename'
                    and val is not None and not isinstance(val, Images)
                    and not isinstance(val, OtherFields)
                }
                filtered_expected = {
                    key: val for key, val in expected.items()
                    if key in allowed_attrs
                }
                self.compare_tag(results, filtered_expected, filename)
                assert tag.images.any is None

    def test_pathlib_compatibility(self) -> None:
        testfile = next(iter(TEST_FILES.keys()))
        filename = Path(SAMPLE_FOLDER) / testfile
        TinyTag.get(filename)
        self.assertTrue(TinyTag.is_supported(filename))

    def test_file_obj_compatibility(self) -> None:
        testfile = next(iter(TEST_FILES.keys()))
        filename = os.path.join(SAMPLE_FOLDER, testfile)
        with open(filename, 'rb') as file_handle:
            tag = TinyTag.get(file_obj=file_handle)
            file_handle.seek(0)
            tag_bytesio = TinyTag.get(file_obj=BytesIO(file_handle.read()))
            self.assertEqual(tag.filesize, tag_bytesio.filesize)

    @skipIf(
        system() == 'Windows' and python_implementation() == 'PyPy',
        reason='PyPy on Windows not supported'
    )
    def test_binary_path_compatibility(self) -> None:
        binary_file_path = os.path.join(
            SAMPLE_FOLDER, 'non_ascii_filename_äää.mp3').encode('utf-8')
        tag = TinyTag.get(binary_file_path)
        self.assertEqual(tag.samplerate, 44100)
        self.assertEqual(tag.other['encoder_settings'], ['Lavf58.20.100'])

    def test_unsupported_extension(self) -> None:
        bogus_file = os.path.join(SAMPLE_FOLDER, 'there_is_no_such_ext.bogus')
        with self.assertRaises(UnsupportedFormatError) as context:
            TinyTag.get(bogus_file)
        self.assertIsInstance(context.exception, TinyTagException)

    def test_override_encoding(self) -> None:
        chinese_id3 = os.path.join(SAMPLE_FOLDER, 'chinese_id3.mp3')
        tag = TinyTag.get(chinese_id3, encoding='gbk')
        self.assertEqual(tag.artist, '苏云')
        self.assertEqual(tag.album, '角落之歌')

    def test_invalid_file(self) -> None:
        for path, cls in (
            ('silence-44-s-v1.mp3', _Flac),
            ('flac1.5sStereo.flac', _Ogg),
            ('flac1.5sStereo.flac', _Wave),
            ('flac1.5sStereo.flac', _Wma),
            ('ilbm.aiff', _Aiff),
        ):
            with self.subTest(path=path, cls=cls):
                with self.assertRaises(ParseError) as context:
                    cls.get(os.path.join(SAMPLE_FOLDER, path))
                self.assertIsInstance(context.exception, TinyTagException)

    def test_image_loading(self) -> None:
        for path, expected_size, desc in (
            ('image-text-encoding.mp3', 5708, 'cover'),
            ('id3v22_with_image.mp3', 1220, 'some image ë'),
            ('id3v22_with_image_stray_null.mp3', 1220, 'some image ë'),
            ('mpeg4_with_image.m4a', 1220, None),
            ('flac_with_image.flac', 1220, 'some image ë'),
            ('wav_with_image.wav', 4627, 'some image ë'),
            ('aiff_with_image.aiff', 1220, 'some image ë'),
        ):
            with self.subTest(path=path, expected_size=expected_size,
                              desc=desc):
                tag = TinyTag.get(
                    os.path.join(SAMPLE_FOLDER, path), image=True)
                image = tag.images.any
                manual_image = tag.images.front_cover
                if manual_image is None:
                    manual_image = tag.images.other['generic'][0]
                assert image is not None
                assert manual_image is not None
                self.assertIn(image.name, {'front_cover', 'generic'})
                assert image.data is not None
                self.assertEqual(image.data, manual_image.data)
                with self.assertWarns(DeprecationWarning):
                    self.assertEqual(image.data, tag.get_image())
                image_size = len(image.data)
                self.assertEqual(
                    image_size, expected_size,
                    (f'Image is {image_size} bytes but should be '
                     f'{expected_size} bytes')
                )
                self.assertTrue(
                    image.data.startswith(b'\xff\xd8\xff\xe0'),
                    'The image data must start with a jpeg header'
                )
                self.assertEqual(image.mime_type, 'image/jpeg')
                self.assertEqual(image.description, desc)

    def test_image_loading_other(self) -> None:
        tag = TinyTag.get(
            os.path.join(SAMPLE_FOLDER, 'ogg_with_image.ogg'), image=True)
        image = tag.images.other['bright_colored_fish'][0]
        assert image.data is not None
        assert tag.images.any is not None
        self.assertEqual(tag.images.any.data, image.data)
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(image.data, tag.get_image())
        self.assertEqual(image.mime_type, 'image/jpeg')
        self.assertEqual(image.name, 'bright_colored_fish')
        self.assertEqual(image.description, 'some image ë')
        self.assertEqual(len(image.data), 1220)
        self.assertEqual(
            str(image),
            "Image(name='bright_colored_fish', data=b'\\xff\\xd8\\xff\\xe0"
            "\\x00\\x10JFIF\\x00\\x01\\x01\\x01\\x00H\\x00H\\x00\\x00\\xff"
            "\\xe2\\x02\\xb0ICC_PROFILE\\x00\\x01\\x01\\x00\\x00\\x02"
            "\\xa0lcm..', mime_type='image/jpeg', description='some image ë')"
        )

    def test_mp3_utf_8_invalid_string(self) -> None:
        tag = TinyTag.get(
            os.path.join(SAMPLE_FOLDER, 'utf-8-id3v2-invalid-string.mp3'))
        # the title used to be Gran dia, but I replaced the first byte with
        # 0xFF, which should be ignored here
        self.assertEqual(tag.title, '�ran día')

    def test_detect_magic_headers(self) -> None:
        for testfile, expected in (
            ('detect_mp3_id3.x', _ID3),
            ('detect_mp3_fffb.x', _ID3),
            ('detect_ogg_flac.x', _Ogg),
            ('detect_ogg_opus.x', _Ogg),
            ('detect_ogg_vorbis.x', _Ogg),
            ('detect_wav.x', _Wave),
            ('detect_flac.x', _Flac),
            ('detect_wma.x', _Wma),
            ('detect_mp4_m4a.x', _MP4),
            ('detect_aiff.x', _Aiff),
        ):
            with self.subTest(testfile=testfile, expected=expected):
                filename = os.path.join(SAMPLE_FOLDER, testfile)
                tag = TinyTag.get(filename)
                self.assertIsInstance(tag, expected)

    def test_show_hint_for_wrong_usage(self) -> None:
        with self.assertRaises(ValueError) as context:
            TinyTag.get()
        self.assertIsInstance(context.exception, ValueError)
        self.assertEqual(
            str(context.exception),
            'Either filename or file_obj argument is required'
        )

    def test_unimplemented_load(self) -> None:
        class IncompleteTag(TinyTag):  # pylint: disable=abstract-method
            def load(self,
                     file_handle: BinaryIO | None,
                     tags: bool,
                     duration: bool) -> None:
                self._filehandler = file_handle
                self._load(tags=tags, duration=duration)
        tag = IncompleteTag()
        with self.assertRaises(ValueError):
            tag.load(file_handle=None, tags=True, duration=True)
        with self.assertRaises(NotImplementedError):
            tag.load(file_handle=BytesIO(), tags=True, duration=False)
        with self.assertRaises(NotImplementedError):
            tag.load(file_handle=BytesIO(), tags=False, duration=True)

    def test_deprecations(self) -> None:
        file_path = os.path.join(SAMPLE_FOLDER, 'flac_with_image.flac')
        with self.assertWarns(DeprecationWarning):
            tag = TinyTag.get(
                filename=file_path, image=True, ignore_errors=True)
        with self.assertWarns(DeprecationWarning):
            tag = TinyTag.get(
                filename=file_path, image=True, ignore_errors=False)
        with self.assertWarns(DeprecationWarning):
            assert tag.audio_offset is None
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(str(tag.extra), "{'url': 'https://example.com'}")
        with self.assertWarns(DeprecationWarning):
            assert tag.images.any is not None
            self.assertEqual(tag.get_image(), tag.images.any.data)

    def test_str_vars(self) -> None:
        tag = TinyTag.get(
            os.path.join(SAMPLE_FOLDER, 'flac_with_image.flac'), image=True)
        vars_str = str(vars(tag))
        self.assertIn(
            "flac_with_image.flac', 'filesize': 2824, 'duration': 0.1, "
            "'channels': 1, 'bitrate': 225.92, "
            "'bitdepth': 16, 'samplerate': 44100, 'artist': 'artist 1', "
            "'albumartist': None, 'composer': None, 'album': 'album 1', "
            "'disc': None, 'disc_total': None, 'title': None, 'track': None, "
            "'track_total': None, 'genre': 'genre 1', 'year': None, "
            "'comment': None, 'images': <tinytag.tinytag.Images "
            "object at ",
            vars_str
        )
        self.assertIn(
            "'other': {'artist': ['artist 2', 'artist 3'], "
            "'album': ['album 2'], 'genre': ['genre 2'], "
            "'url': ['https://example.com']}",
            vars_str
        )
        self.assertEqual(
            str(vars(tag.images)),
            "{'front_cover': Image(name='front_cover', data=b'\\xff\\xd8\\xff"
            "\\xe0\\x00\\x10JFIF\\x00\\x01\\x01\\x01\\x00H\\x00H\\x00\\x00"
            "\\xff\\xe2\\x02\\xb0ICC_PROFILE\\x00\\x01\\x01\\x00\\x00\\x02"
            "\\xa0lcm..', mime_type='image/jpeg', description='some image ë'),"
            " 'back_cover': None, 'media': None, 'other': "
            "{'bright_colored_fish': [Image(name='bright_colored_fish', data="
            "b'\\xff\\xd8\\xff\\xe0\\x00\\x10JFIF\\x00\\x01\\x01\\x01\\x00H"
            "\\x00H\\x00\\x00\\xff\\xe2\\x02\\xb0ICC_PROFILE\\x00\\x01\\x01"
            "\\x00\\x00\\x02\\xa0lcm..', mime_type='image/jpeg', description="
            "'some image ë')]}}"
        )

    def test_str_flat_dict(self) -> None:
        tag = TinyTag.get(
            os.path.join(SAMPLE_FOLDER, 'flac_with_image.flac'), image=True)
        self.assertTrue(str(tag.as_dict()).endswith(
            "flac_with_image.flac', 'filesize': 2824, 'duration': 0.1, "
            "'channels': 1, 'bitrate': 225.92, "
            "'bitdepth': 16, 'samplerate': 44100, 'artist': ['artist 1', "
            "'artist 2', 'artist 3'], 'album': ['album 1', 'album 2'], "
            "'genre': ['genre 1', 'genre 2'], 'url': ['https://example.com']}"
        ))
        self.assertEqual(
            str(tag.images.as_dict()),
            "{'front_cover': [Image(name='front_cover', data=b'\\xff\\xd8\\xff"
            "\\xe0\\x00\\x10JFIF\\x00\\x01\\x01\\x01\\x00H\\x00H\\x00\\x00"
            "\\xff\\xe2\\x02\\xb0ICC_PROFILE\\x00\\x01\\x01\\x00\\x00\\x02"
            "\\xa0lcm..', mime_type='image/jpeg', description='some image ë')]"
            ", 'bright_colored_fish': [Image(name='bright_colored_fish', "
            "data=b'\\xff\\xd8\\xff\\xe0\\x00\\x10JFIF\\x00\\x01\\x01\\x01"
            "\\x00H\\x00H\\x00\\x00\\xff\\xe2\\x02\\xb0ICC_PROFILE\\x00\\x01"
            "\\x01\\x00\\x00\\x02\\xa0lcm..', mime_type='image/jpeg', "
            "description='some image ë')]}"
        )
