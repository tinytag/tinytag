# tests can be extended using other bigger files that are not going to be
# checked into git, by placing them into the custom_samples folder
#
# see custom_samples/instructions.txt
#

# pylint: disable=missing-function-docstring,missing-module-docstring,protected-access


from __future__ import annotations
from typing import Any

import io
import os
import pathlib
import re
import shutil
import sys

import pytest

from tinytag.tinytag import TinyTag, TinyTagException, _ID3, _Ogg, _Wave, _Flac, _Wma, _MP4, _Aiff


testfiles = dict([
    # MP3
    ('samples/vbri.mp3',
        {'extra': {}, 'channels': 2, 'samplerate': 44100,
         'duration': 0.47020408163265304, 'album': 'I Can Walk On Water I Can Fly', 'year': '2007',
         'title': 'I Can Walk On Water I Can Fly', 'artist': 'Basshunter', 'track': 1,
         'filesize': 8192, 'genre': 'Dance',
         'comment': 'Ripped by THSLIVE', 'bitrate': 125.33333333333333}),
    ('samples/cbr.mp3',
        {'extra': {}, 'channels': 2, 'samplerate': 44100, 'duration': 0.48866995073891617,
         'album': 'I Can Walk On Water I Can Fly', 'year': '2007',
         'title': 'I Can Walk On Water I Can Fly', 'artist': 'Basshunter', 'track': 1,
         'filesize': 8186, 'bitrate': 128.0, 'genre': 'Dance',
         'comment': 'Ripped by THSLIVE'}),
    # the output of the lame encoder was 185.4 bitrate, but this is good enough for now
    ('samples/vbr_xing_header.mp3',
        {'extra': {}, 'bitrate': 186.04383278145696, 'channels': 1, 'samplerate': 44100,
         'duration': 3.944489795918367, 'filesize': 91731}),
    ('samples/vbr_xing_header_2channel.mp3',
        {'extra': {'tsse': 'LAME 32bits version 3.99.5 (http://lame.sf.net)', 'tlen': '249976'},
         'filesize': 2000, 'album': "The Harpers' Masque",
         'artist': 'Knodel and Valencia', 'bitrate': 46.276128290848305,
         'channels': 2, 'duration': 250.04408163265308, 'samplerate': 22050,
         'title': 'Lochaber No More', 'year': '1992'}),
    ('samples/id3v22-test.mp3',
        {'extra': {'ten': 'iTunes v4.6',
                   'itunnorm': (' 0000044E 00000061 00009B67 000044C3 00022478 00022182 '
                                '00007FCC 00007E5C 0002245E 0002214E'),
                   'itunes_cddb_1': ('9D09130B+174405+11+150+14097+27391+43983+65786+84877+'
                                     '99399+113226+132452+146426+163829'),
                   'itunes_cddb_tracknumber': '3'},
         'channels': 2, 'samplerate': 44100, 'track_total': 11, 'duration': 0.13836297152858082,
         'album': 'Hymns for the Exiled', 'year': '2004', 'title': 'cosmic american',
         'artist': 'Anais Mitchell', 'track': 3, 'filesize': 5120,
         'bitrate': 160.0, 'comment': 'Waterbug Records, www.anaismitchell.com'}),
    ('samples/silence-44-s-v1.mp3',
        {'extra': {}, 'channels': 2, 'samplerate': 44100, 'genre': 'Darkwave',
         'duration': 3.738712956446946, 'album': 'Quod Libet Test Data', 'year': '2004',
         'title': 'Silence', 'artist': 'piman', 'track': 2, 'filesize': 15070,
         'bitrate': 32.0}),
    ('samples/id3v1-latin1.mp3',
        {'extra': {}, 'genre': 'Rock',
         'album': 'The Young Americans', 'title': 'Play Dead', 'filesize': 256, 'track': 12,
         'artist': 'Björk', 'year': '1993', 'comment': '                            '}),
    ('samples/UTF16.mp3',
        {'extra': {'musicbrainz artist id': '664c3e0e-42d8-48c1-b209-1efca19c0325',
                   'musicbrainz album id': '25322466-a29b-417b-b560-399687b91ddd',
                   'musicbrainz album artist id': '664c3e0e-42d8-48c1-b209-1efca19c0325',
                   'musicbrainz disc id': 'p.5xoyYRtCVFe2gt0mfTfsXrO9U-',
                   'musicip puid': '6ff97581-1c73-fc05-b4e4-a4ccee12ec84', 'asin': 'B003KVNV4S',
                   'musicbrainz album status': 'Official', 'musicbrainz album type': 'Album',
                   'musicbrainz album release country': 'United States',
                   'ufid': 'http://musicbrainz.org\x00cf639964-eabb-4c40-9673-c2117e456ea5',
                   'publisher': '4AD', 'tdat': '1105',
                   'wxxx': 'WIKIPEDIA_RELEASE\x00http://en.wikipedia.org/wiki/High_Violet',
                   'tmed': 'Digital', 'tlen': '203733',
                   'tsse': 'LAME 32bits version 3.98.4 (http://www.mp3dev.org/)'},
         'track_total': 11, 'track': 7, 'artist': 'The National',
         'year': '2010', 'album': 'High Violet', 'title': 'Lemonworld', 'filesize': 20480,
         'genre': 'Indie', 'comment': 'Track 7'}),
    ('samples/utf-8-id3v2.mp3',
        {'extra': {}, 'genre': 'Acustico',
         'track_total': 21, 'track': 1, 'filesize': 2119, 'title': 'Gran día',
         'artist': 'Paso a paso', 'album': 'S/T', 'disc_total': 0, 'year': '2003'}),
    ('samples/empty_file.mp3',
        {'extra': {}, 'filesize': 0}),
    ('samples/silence-44khz-56k-mono-1s.mp3',
        {'extra': {}, 'channels': 1, 'samplerate': 44100, 'duration': 1.0265261269342902,
         'filesize': 7280, 'bitrate': 56.0}),
    ('samples/silence-22khz-mono-1s.mp3',
        {'extra': {}, 'channels': 1, 'samplerate': 22050, 'filesize': 4284,
         'bitrate': 32.0, 'duration': 1.0438932496075353}),
    ('samples/id3v24-long-title.mp3',
        {'extra':
         {'copyright': '2013 Marathon Artists under exclsuive license from Courtney Barnett',
          'composer': 'Courtney Barnett'},
         'track': 1, 'disc_total': 1,
         'album': 'The Double EP: A Sea of Split Peas', 'filesize': 10000,
         'track_total': 12, 'genre': 'AlternRock',
         'title': 'Out of the Woodwork', 'artist': 'Courtney Barnett',
         'albumartist': 'Courtney Barnett', 'disc': 1,
         'comment': 'Amazon.com Song ID: 240853806', 'year': '2013'}),
    ('samples/utf16be.mp3',
        {'extra': {}, 'title': '52-girls', 'filesize': 2048, 'track': 6, 'album': 'party mix',
         'artist': 'The B52s', 'genre': 'Rock', 'year': '1981'}),
    ('samples/id3v22_image.mp3',
        {'extra': {'rva': '\x10', 'tbp': '131'}, 'title': 'Kids (MGMT Cover) ', 'filesize': 35924,
         'album': 'winniecooper.net ', 'artist': 'The Kooks', 'year': '2008',
         'genre': '.'}),
    ('samples/id3v22.TCO.genre.mp3',
        {'extra': {'ten': 'iTunes 11.0.4',
                   'itunnorm': (' 000019F0 00001E2A 00009F9A 0000C689 000312A1 00030C1A 0000902E '
                                '00008D36 00020882 000321D6'),
                   'itunsmpb': (' 00000000 00000210 000007B9 00000000008FB737 00000000 008242F1 '
                                '00000000 00000000 00000000 00000000 00000000 00000000'),
                   'itunpgap': '0'},
         'filesize': 500, 'album': 'ARTPOP', 'artist': 'Lady GaGa',
         'genre': 'Pop', 'title': 'Applause'}),
    ('samples/id3_comment_utf_16_with_bom.mp3',
        {'extra': {'copyright': '(c) 2008 nin', 'isrc': 'USTC40852229', 'bpm': '60',
                   'url': 'www.nin.com', 'tenc': 'LAME 3.97'},
         'filesize': 19980,
         'album': 'Ghosts I-IV', 'albumartist': 'Nine Inch Nails', 'artist': 'Nine Inch Nails',
         'disc': 1, 'disc_total': 2, 'title': '1 Ghosts I', 'track': 1, 'track_total': 36,
         'year': '2008', 'comment': '3/4 time'}),
    ('samples/id3_comment_utf_16_double_bom.mp3',
        {'extra': {'label': 'Unclear'}, 'filesize': 512, 'album': 'The Embrace',
         'artist': 'Johannes Heil & D.Diggler', 'comment': 'Unclear',
         'title': 'The Embrace (Romano Alfieri Remix)',
         'year': '2012'}),
    ('samples/id3_genre_id_out_of_bounds.mp3',
        {'extra': {}, 'filesize': 512, 'album': 'MECHANICAL ANIMALS', 'artist': 'Manson',
         'genre': '(255)', 'title': '01 GREAT BIG WHITE WORLD',
         'year': '0'}),
    ('samples/image-text-encoding.mp3',
        {'extra': {}, 'channels': 1, 'samplerate': 22050, 'filesize': 11104,
         'title': 'image-encoding', 'bitrate': 32.0,
         'duration': 1.0438932496075353}),
    ('samples/id3v1_does_not_overwrite_id3v2.mp3',
        {'filesize': 1130, 'album': 'Somewhere Far Beyond', 'albumartist': 'Blind Guardian',
         'artist': 'Blind Guardian',
         'extra': {'love rating': 'L', 'publisher': 'Century Media', 'popm': 'MusicBee\x00Ä'},
         'genre': 'Power Metal', 'title': 'Time What Is Time', 'track': 1,
         'year': '1992'}),
    ('samples/nicotinetestdata.mp3',
        {'extra': {'tsse': 'Lavf58.20.100'}, 'filesize': 80919, 'channels': 2,
         'duration': 5.067755102040817, 'samplerate': 44100, 'bitrate': 127.6701030927835}),
    ('samples/chinese_id3.mp3',
        {'extra': {}, 'filesize': 1000, 'album': '½ÇÂäÖ®¸è', 'albumartist': 'ËÕÔÆ',
         'artist': 'ËÕÔÆ', 'bitrate': 128.0, 'channels': 2,
         'duration': 0.052244897959183675, 'genre': 'ÐÝÏÐÒôÀÖ', 'samplerate': 44100,
         'title': '½ÇÂäÖ®¸è', 'track': 1}),
    ('samples/cut_off_titles.mp3',
        {'extra': {'tsse': 'Lavf54.29.104'}, 'filesize': 1000, 'album': 'ERB',
         'artist': 'Epic Rap Battles Of History',
         'bitrate': 192.0, 'channels': 2, 'duration': 0.052244897959183675,
         'samplerate': 44100, 'title': 'Tony Hawk VS Wayne Gretzky'}),
    ('samples/id3_xxx_lang.mp3',
        {'extra': {'script': 'Latn', 'originalyear': '2004',
                   'acoustid id': '2dc0b571-a633-45b0-aa5e-f3d25e4e0020',
                   'musicbrainz album type': 'album',
                   'musicbrainz album artist id': '078a9376-3c04-4280-b7d7-b20e158f345d',
                   'musicbrainz artist id': '078a9376-3c04-4280-b7d7-b20e158f345d',
                   'barcode': '724386668721',
                   'musicbrainz album id': '38b555fe-24c7-37b3-ad1b-f6dea9f1aafa',
                   'artists': 'A Perfect Circle',
                   'musicbrainz release track id': '7f7c31a5-0905-39ba-ba72-68db91d3b9da',
                   'catalognumber': '7243 8 66687 2 1',
                   'musicbrainz release group id': '0f21095a-e629-389c-981a-d9569e9673c9',
                   'musicbrainz album status': 'official',
                   'asin': 'B000641ZIQ', 'musicbrainz album release country': 'US',
                   'isrc': 'USVI20400513', 'lyrics': 'Don\'t fret, precious',
                   'replaygain_track_gain': '-3.95 dB', 'replaygain_track_peak': '0.999969',
                   'replaygain_album_gain': '-8.26 dB', 'publisher': 'Virgin Records America',
                   'composer': 'Billy Howerdel/Maynard James Keenan', 'tmed': 'CD',
                   'tso2': 'Perfect Circle, A',
                   'ufid': 'http://musicbrainz.org\x00d2b8f0e6-735a-42ee-adf0-7eca4e65cd72',
                   'tsop': 'Perfect Circle, A', 'tory': '2004', 'tdat': '0211',
                   'ipls': ('producer\x00Billy Howerdel\x00producer\x00Maynard James Keenan'
                            '\x00engineer\x00Billy Howerdel\x00engineer\x00Critter')},
         'filesize': 6943, 'album': 'eMOTIVe', 'albumartist': 'A Perfect Circle',
         'artist': 'A Perfect Circle', 'bitrate': 192.0, 'channels': 2,
         'duration': 0.13198711063372717, 'genre': 'Rock',
         'samplerate': 44100, 'title': 'Counting Bodies Like Sheep to the Rhythm of the War Drums',
         'track': 10, 'comment': '                            ', 'disc': 1, 'disc_total': 1,
         'track_total': 12, 'year': '2004'}),
    ('samples/mp3/vbr/vbr8.mp3',
        {'filesize': 9504, 'bitrate': 8.25, 'channels': 1, 'duration': 9.216,
         'extra': {}, 'samplerate': 8000}),
    ('samples/mp3/vbr/vbr8stereo.mp3',
        {'filesize': 9504, 'bitrate': 8.25, 'channels': 2, 'duration': 9.216,
         'extra': {}, 'samplerate': 8000}),
    ('samples/mp3/vbr/vbr11.mp3',
        {'filesize': 9360, 'bitrate': 8.143465909090908, 'channels': 1,
         'duration': 9.195102040816327, 'extra': {}, 'samplerate': 11025}),
    ('samples/mp3/vbr/vbr11stereo.mp3',
        {'filesize': 9360, 'bitrate': 8.143465909090908, 'channels': 2,
         'duration': 9.195102040816327, 'extra': {}, 'samplerate': 11025}),
    ('samples/mp3/vbr/vbr16.mp3',
        {'filesize': 9432, 'bitrate': 8.251968503937007, 'channels': 1,
         'duration': 9.144, 'extra': {}, 'samplerate': 16000}),
    ('samples/mp3/vbr/vbr16stereo.mp3',
        {'filesize': 9432, 'bitrate': 8.251968503937007, 'channels': 2,
         'duration': 9.144, 'extra': {}, 'samplerate': 16000}),
    ('samples/mp3/vbr/vbr22.mp3',
        {'filesize': 9282, 'bitrate': 8.145021489971347, 'channels': 1,
         'duration': 9.11673469387755, 'extra': {}, 'samplerate': 22050}),
    ('samples/mp3/vbr/vbr22stereo.mp3',
        {'filesize': 9282, 'bitrate': 8.145021489971347, 'channels': 2,
         'duration': 9.11673469387755, 'extra': {}, 'samplerate': 22050}),
    ('samples/mp3/vbr/vbr32.mp3',
        {'filesize': 37008, 'bitrate': 32.50592885375494, 'channels': 1,
         'duration': 9.108, 'extra': {}, 'samplerate': 32000}),
    ('samples/mp3/vbr/vbr32stereo.mp3',
        {'filesize': 37008, 'bitrate': 32.50592885375494, 'channels': 2,
         'duration': 9.108, 'extra': {}, 'samplerate': 32000}),
    ('samples/mp3/vbr/vbr44.mp3',
        {'filesize': 36609, 'bitrate': 32.21697198275862, 'channels': 1,
         'duration': 9.09061224489796, 'extra': {}, 'samplerate': 44100}),
    ('samples/mp3/vbr/vbr44stereo.mp3',
        {'filesize': 36609, 'bitrate': 32.21697198275862, 'channels': 2,
         'duration': 9.09061224489796, 'extra': {}, 'samplerate': 44100}),
    ('samples/mp3/vbr/vbr48.mp3',
        {'filesize': 36672, 'bitrate': 32.33862433862434, 'channels': 1,
         'duration': 9.072, 'extra': {}, 'samplerate': 48000}),
    ('samples/mp3/vbr/vbr48stereo.mp3',
        {'filesize': 36672, 'bitrate': 32.33862433862434, 'channels': 2,
         'duration': 9.072, 'extra': {}, 'samplerate': 48000}),
    ('samples/id3v24_genre_null_byte.mp3',
        {'extra': {}, 'filesize': 256, 'album': '\u79d8\u5bc6', 'albumartist': 'aiko',
         'artist': 'aiko', 'disc': 1, 'genre': 'Pop',
         'title': '\u661f\u306e\u306a\u3044\u4e16\u754c', 'track': 10, 'year': '2008'}),
    ('samples/vbr_xing_header_short.mp3',
        {'filesize': 432, 'bitrate': 24.0, 'channels': 1, 'duration': 0.144,
         'extra': {}, 'samplerate': 8000}),

    # OGG
    ('samples/empty.ogg',
        {'extra': {}, 'duration': 3.684716553287982,
         'filesize': 4328, 'bitrate': 112.0, 'samplerate': 44100, 'channels': 2}),
    ('samples/multipage-setup.ogg',
        {'extra': {'transcoded': 'mp3;241', 'replaygain_album_gain': '-10.29 dB',
                   'replaygain_album_peak': '1.50579047', 'replaygain_track_peak': '1.17979193',
                   'replaygain_track_gain': '-10.02 dB'},
         'genre': 'JRock', 'duration': 4.128798185941043,
         'album': 'Timeless', 'year': '2006', 'title': 'Burst', 'artist': 'UVERworld', 'track': 7,
         'filesize': 76983, 'bitrate': 160.0,
         'samplerate': 44100, 'comment': 'SRCL-6240', 'channels': 2}),
    ('samples/test.ogg',
        {'extra': {}, 'duration': 1.0, 'album': 'the boss', 'year': '2006',
         'title': 'the boss', 'artist': 'james brown', 'track': 1,
         'filesize': 7467, 'bitrate': 160.0, 'samplerate': 44100, 'channels': 2,
         'comment': 'hello!'}),
    ('samples/corrupt_metadata.ogg',
        {'extra': {}, 'filesize': 18648, 'bitrate': 80.0,
         'duration': 2.132358276643991, 'samplerate': 44100, 'channels': 1}),
    ('samples/composer.ogg',
        {'extra': {'composer': 'some composer'}, 'filesize': 4480,
         'album': 'An Album', 'artist': 'An Artist',
         'bitrate': 112.0, 'duration': 3.684716553287982, 'channels': 2,
         'genre': 'Some Genre', 'samplerate': 44100, 'title': 'A Title', 'track': 2,
         'year': '2007', 'comment': 'A Comment'}),
    ('samples/test.opus',
        {'extra': {'encoder': 'Lavc57.24.102 libopus', 'arrange': '\u6771\u65b9',
                   'catalogid': 'ARCD0024', 'discid': 'A212230D', 'event': '\u4f8b\u5927\u796d5',
                   'lyricist': 'Haruka', 'mastering': 'Hedonist',
                   'origin': '\u6771\u65b9\u5e7b\u60f3\u90f7', 'originaltitle': 'Bad Apple!!',
                   'performer': 'Masayoshi Minoshima', 'vocal': 'nomico'},
         'albumartist': 'Alstroemeria Records', 'samplerate': 48000, 'channels': 2,
         'track': 1, 'disc': 1, 'title': 'Bad Apple!!', 'duration': 2.0, 'year': '2008.05.25',
         'filesize': 10000, 'artist': 'nomico',
         'album': 'Exserens - A selection of Alstroemeria Records',
         'comment': 'ARCD0018 - Lovelight', 'disc_total': 1, 'track_total': 13}),
    ('samples/8khz_5s.opus',
        {'extra': {'encoder': 'opusenc from opus-tools 0.2'}, 'filesize': 7251, 'channels': 1,
         'samplerate': 48000, 'duration': 5.0065}),
    ('samples/test_flac.oga',
        {'extra': {'copyright': 'test3', 'isrc': 'test4', 'lyrics': 'test7'},
         'filesize': 9273, 'album': 'test2', 'artist': 'test6', 'comment': 'test5',
         'bitrate': 20.022488249118684, 'duration': 3.705034013605442, 'channels': 2,
         'genre': 'Acoustic', 'samplerate': 44100, 'bitdepth': 16, 'title': 'test1', 'track': 5,
         'year': '2023'}),
    ('samples/test.spx',
        {'extra': {}, 'filesize': 7921, 'channels': 1, 'samplerate': 16000, 'bitrate': -1,
         'duration': 2.1445625, 'artist': 'test1', 'title': 'test2',
         'comment': 'Encoded with Speex 1.2.0'}),

    # WAV
    ('samples/test.wav',
        {'extra': {}, 'channels': 2, 'duration': 1.0, 'filesize': 176444, 'bitrate': 1411.2,
         'samplerate': 44100, 'bitdepth': 16}),
    ('samples/test3sMono.wav',
        {'extra': {}, 'channels': 1, 'duration': 3.0, 'filesize': 264644, 'bitrate': 705.6,
         'samplerate': 44100, 'bitdepth': 16}),
    ('samples/test-tagged.wav',
        {'extra': {}, 'channels': 2, 'duration': 1.0, 'filesize': 176688, 'album': 'thealbum',
         'artist': 'theartisst', 'bitrate': 1411.2, 'genre': 'Acid', 'samplerate': 44100,
         'bitdepth': 16, 'title': 'thetitle', 'track': 66, 'comment': 'hello',
         'year': '2014'}),
    ('samples/test-riff-tags.wav',
        {'extra': {}, 'channels': 2, 'duration': 1.0, 'filesize': 176540,
         'artist': 'theartisst', 'bitrate': 1411.2, 'genre': 'Acid', 'samplerate': 44100,
         'bitdepth': 16, 'title': 'thetitle', 'comment': 'hello',
         'year': '2014'}),
    ('samples/silence-22khz-mono-1s.wav',
        {'extra': {}, 'channels': 1, 'duration': 0.9991836734693877, 'filesize': 48160,
         'bitrate': 352.8, 'samplerate': 22050, 'bitdepth': 16}),
    ('samples/id3_header_with_a_zero_byte.wav',
        {'extra': {}, 'channels': 1, 'duration': 1.0, 'filesize': 44280, 'bitrate': 352.8,
         'samplerate': 22050, 'bitdepth': 16, 'artist': 'Purpley',
         'title': 'Test000\x00Stacked', 'track': 17,
         'album': 'prototypes'}),
    ('samples/adpcm.wav',
        {'extra': {}, 'channels': 1, 'duration': 12.167256235827665, 'filesize': 268686,
         'bitrate': 176.4, 'samplerate': 44100, 'bitdepth': 4,
         'artist': 'test artist', 'title': 'test title', 'track': 1, 'album': 'test album',
         'comment': 'test comment', 'genre': 'test genre', 'year': '1990'}),
    ('samples/riff_extra_zero.wav',
        {'extra': {}, 'channels': 2, 'duration': 0.11609977324263039, 'filesize': 20670,
         'bitrate': 1411.2, 'samplerate': 44100, 'bitdepth': 16,
         'artist': 'B.O.S.E.', 'title': 'Mission Bass', 'album': '808 Bass Express',
         'genre': 'Hip-Hop/Rap', 'year': '1996', 'track': 3}),
    ('samples/riff_extra_zero_2.wav',
        {'extra': {}, 'channels': 2, 'duration': 0.11609977324263039, 'filesize': 20682,
         'bitrate': 1411.2, 'samplerate': 44100, 'bitdepth': 16,
         'artist': 'The Jimmy Castor Bunch', 'title': 'It\'s Just Begun',
         'album': 'The Perfect Beats, Vol. 4', 'genre': 'Pop Electronica', 'track': 7}),
    ('samples/wav_invalid_track_number.wav',
        {'extra': {}, 'filesize': 8908, 'bitrate': 705.6,
         'duration': 0.1, 'samplerate': 44100, 'channels': 1,
         'bitdepth': 16}),
    ('samples/gsm_6_10.wav',
        {'extra': {}, 'bitdepth': 1, 'bitrate': 44.1, 'channels': 1,
         'duration': 0.16507936507936508, 'filesize': 1246, 'samplerate': 44100,
         'album': 'album', 'artist': 'artist', 'title': 'track', 'track': 99,
         'year': '2010', 'comment': 'some comment here', 'genre': 'Bass'}),

    # FLAC
    ('samples/flac1sMono.flac',
        {'extra': {}, 'genre': 'Avantgarde', 'album': 'alb', 'year': '2014',
         'duration': 1.0, 'title': 'track', 'track': 23, 'artist': 'art', 'channels': 1,
         'filesize': 26632, 'bitrate': 213.056, 'samplerate': 44100, 'bitdepth': 16,
         'comment': 'hello'}),
    ('samples/flac453sStereo.flac',
        {'extra': {}, 'channels': 2, 'duration': 453.51473922902494, 'filesize': 84236,
         'bitrate': 1.4859230399999999, 'samplerate': 44100, 'bitdepth': 16}),
    ('samples/flac1.5sStereo.flac',
        {'extra': {}, 'channels': 2, 'album': 'alb', 'year': '2014',
         'duration': 1.4995238095238095, 'title': 'track', 'track': 23, 'artist': 'art',
         'filesize': 59868, 'bitrate': 319.39739599872973, 'genre': 'Avantgarde',
         'samplerate': 44100, 'bitdepth': 16, 'comment': 'hello'}),
    ('samples/flac_application.flac',
        {'extra': {'replaygain_track_peak': '0.9976',
                   'musicbrainz_albumartistid': 'e5c7b94f-e264-473c-bb0f-37c85d4d5c70',
                   'musicbrainz_trackid': 'e65fb332-0c1e-4172-85e0-59cd37e5669e',
                   'replaygain_album_gain': '-8.14 dB', 'labelid': 'RTRADLP480',
                   'musicbrainz_albumid': '359a91e9-3bb3-4b60-a823-8aaa4bad1e36',
                   'artistsort': 'Belle and Sebastian', 'replaygain_track_gain': '-8.08 dB',
                   'replaygain_album_peak': '1.0000'},
         'channels': 2, 'track_total': 11,
         'album': 'Belle and Sebastian Write About Love', 'year': '2010-10-11', 'duration': 273.64,
         'title': 'I Want the World to Stop', 'track': 4, 'artist': 'Belle and Sebastian',
         'filesize': 13000, 'bitrate': 0.38006139453296306, 'samplerate': 44100, 'bitdepth': 16}),
    ('samples/no-tags.flac',
        {'extra': {}, 'channels': 2, 'duration': 3.684716553287982, 'filesize': 4692,
         'bitrate': 10.186943678613627, 'samplerate': 44100, 'bitdepth': 16}),
    ('samples/variable-block.flac',
        {'extra': {'discid': 'AA0B360B',
                   'japanese title': ('\u30a2\u30c3\u30d7\u30eb\u30b7\u30fc\u30c9 '
                                      '\u30aa\u30ea\u30b8\u30ca\u30eb\u30fb\u30b5\u30a6'
                                      '\u30f3\u30c9\u30c8\u30e9\u30c3\u30af'),
                   'organization': 'Sony Music Records (SRCP-371)',
                   'ripper': 'Exact Audio Copy 0.99pb5',
                   'replaygain_album_gain': '-8.68 dB', 'replaygain_album_peak': '1.000000',
                   'replaygain_track_gain': '-9.61 dB', 'replaygain_track_peak': '1.000000',
                   'composer': 'Boom Boom Satellites (Lyrics)'},
         'channels': 2, 'album': 'Appleseed Original Soundtrack', 'year': '2004',
         'duration': 261.68, 'title': 'DIVE FOR YOU', 'track': 1, 'track_total': 11,
         'artist': 'Boom Boom Satellites', 'filesize': 10240, 'bitrate': 0.31305411189238763,
         'disc': 1, 'genre': 'Anime Soundtrack', 'samplerate': 44100, 'bitdepth': 16,
         'disc_total': 2, 'comment': 'Original Soundtrack'}),
    ('samples/106-invalid-streaminfo.flac',
        {'extra': {}, 'filesize': 4692}),
    ('samples/106-short-picture-block-size.flac',
        {'extra': {}, 'filesize': 4692, 'bitrate': 10.186943678613627, 'channels': 2,
         'duration': 3.684716553287982, 'samplerate': 44100, 'bitdepth': 16}),
    ('samples/with_id3_header.flac',
        {'extra': {'id': '8591671910'}, 'filesize': 64837, 'album': 'album\x00   ',
         'artist': 'artist\x00群星',
         'title': 'title\x00A 梦 哆啦 机器猫 短信铃声', 'track': 1, 'bitrate': 1143.72468, 'channels': 1,
         'duration': 0.45351473922902497, 'genre': 'genre', 'samplerate': 44100, 'bitdepth': 16,
         'year': '2018', 'comment': 'comment'}),
    ('samples/with_padded_id3_header.flac',
        {'extra': {}, 'filesize': 16070, 'album': 'album', 'artist': 'artist',
         'bitrate': 283.4748, 'channels': 1,
         'duration': 0.45351473922902497, 'genre': 'genre', 'samplerate': 44100, 'bitdepth': 16,
         'title': 'title', 'track': 1, 'year': '2018', 'comment': 'comment'}),
    ('samples/with_padded_id3_header2.flac',
        {'extra': {'mcdi': ('2\x01\x05\x00\x10\x01\x00\x00\x00\x00\x00\x00\x10\x02\x00\x00\x00W5'
                            '\x00\x10\x03\x00\x00\x00\x90\x0c\x00\x10\x04\x00\x00\x00ä7\x00\x10'
                            '\x05\x00\x00\x013«\x00\x10ª\x00\x00\x01\x8c\xa0'),
                   'tlen': '297666', 'tenc': 'Exact Audio Copy   (Sicherer Modus)',
                   'tsse': ('flac.exe -T "artist=Unbekannter Künstler" -T "title=Track01" -T '
                            '"album=Unbekannter Titel" -T "date=" -T "tracknumber=01" -T '
                            '"genre=" -5')},
         'filesize': 19522, 'album': 'album\x00Unbekannter Titel',
         'artist': 'artist\x00Unbekannter Künstler', 'bitrate': 344.36807999999996,
         'channels': 1, 'disc': 1, 'disc_total': 1,
         'duration': 0.45351473922902497, 'genre': 'genre', 'samplerate': 44100, 'bitdepth': 16,
         'title': 'title\x00Track01', 'track': 1, 'track_total': 5, 'year': '2018',
         'comment': 'comment'}),
    ('samples/flac_with_image.flac',
        {'extra': {}, 'filesize': 80000, 'album': 'smilin´ in circles',
         'artist': 'Andreas Kümmert',
         'bitrate': 7.6591670655816175, 'channels': 2, 'disc': 1, 'disc_total': 1,
         'duration': 83.56, 'genre': 'Blues', 'samplerate': 44100, 'bitdepth': 16, 'title': 'intro',
         'track': 1, 'track_total': 8}),
    ('samples/flac_invalid_track_number.flac',
        {'extra': {}, 'filesize': 235, 'bitrate': 18.8, 'channels': 1,
         'duration': 0.1, 'samplerate': 44100, 'bitdepth': 16}),
    ('samples/flac_multiple_fields.flac',
        {'extra': {}, 'filesize': 235, 'album': 'album 1\x00album 2',
         'artist': 'artist 1\x00artist 2\x00artist 3',
         'bitrate': 18.8, 'channels': 1, 'duration': 0.1, 'genre': 'genre 1\x00genre 2',
         'samplerate': 44100, 'bitdepth': 16}),

    # WMA
    ('samples/test2.wma',
        {'extra': {'track': 0,
                   'mediaprimaryclassid': '{D1607DBC-E323-4BE2-86A1-48A42A28441E}',
                   'encodingtime': 128861118183900000, 'wmfsdkversion': '11.0.5721.5145',
                   'wmfsdkneeded': '0.0.0.0000', 'isvbr': 1, 'peakvalue': 30369,
                   'averagelevel': 7291, 'composer': 'Foo Fighters'},
         'samplerate': 44100, 'album': 'The Colour and the Shape', 'title': 'Doll',
         'bitrate': 64.04, 'filesize': 5800, 'track': 1, 'albumartist': 'Foo Fighters',
         'artist': 'Foo Fighters', 'duration': 83.406, 'year': '1997',
         'genre': 'Alternative', 'channels': 2}),
    ('samples/lossless.wma',
        {'extra': {}, 'samplerate': 44100, 'bitrate': 667.296, 'filesize': 2500, 'bitdepth': 16,
         'duration': 43.133, 'channels': 2}),
    ('samples/wma_invalid_track_number.wma',
        {'extra': {'encodingsettings': 'Lavf60.16.100'}, 'filesize': 3940, 'bitrate': 128.0,
         'duration': 2.1409999999999996, 'samplerate': 44100, 'channels': 1}),

    # ALAC/M4A/MP4
    ('samples/test.m4a',
        {'extra': {'itunsmpb': (' 00000000 00000840 000001DC 0000000000D3E9E4 00000000 00000000 '
                                '00000000 00000000 00000000 00000000 00000000 00000000'),
                   'itunnorm': (' 00000358 0000032E 000020AE 000020D9 0003A228 00032A28 00007E20 '
                                '00007E90 00007BFD 00009293'),
                   'itunes_cddb_ids': '11++', 'ufidhttp://www.cddb.com/id3/taginfo1.html':
                   '3CD3N48Q241232290U3387DD249F72E6B082B283425ADB9B0F324P1', 'bpm': 0},
         'samplerate': 44100, 'duration': 314.97868480725623, 'bitrate': 256.0, 'channels': 2,
         'genre': 'Pop', 'year': '2011', 'title': 'Nothing', 'album': 'Only Our Hearts To Lose',
         'track_total': 11, 'track': 11, 'artist': 'Marian', 'filesize': 61432}),
    ('samples/test2.m4a',
        {'extra': {'copyright': '℗ 1992 Ace Records',
                   'itunnorm': (' 00000371 00000481 00002E90 00002EA6 00000099 00000058 000073F3 '
                                '0000768E 00000092 00000092'),
                   'itunsmpb': (' 00000000 00000840 00000110 000000000070DEB0 00000000 00000000 '
                                '00000000 00000000 00000000 00000000 00000000 00000000'),
                   'itunmovi': ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC '
                                '"-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs'
                                '/PropertyList-1.0.dtd">\n<plist version="1.0">\n<dict>\n\t<key>'
                                'asset-info</key>\n\t<dict>\n\t\t<key>flavor</key>\n\t\t<string>'
                                '2:256</string>\n\t</dict>\n</dict>\n</plist>\n'),
                   'tool': 144255989988720642,
                   'composer': "Millie Jackson - Get It Out 'cha System - 1978"},
         'bitrate': 256.0, 'track': 1,
         'albumartist': "Millie Jackson - Get It Out 'cha System - 1978",
         'duration': 167.78739229024944, 'filesize': 223365, 'channels': 2, 'year': '1978',
         'artist': 'Millie Jackson', 'track_total': 9, 'disc_total': 1, 'genre': 'R&B/Soul',
         'album': "Get It Out 'cha System", 'samplerate': 44100, 'disc': 1,
         'title': 'Go Out and Get Some',
         'comment': "Millie Jackson - Get It Out 'cha System - 1978"}),
    ('samples/iso8859_with_image.m4a',
        {'extra': {}, 'artist': 'Major Lazer', 'filesize': 57017,
         'title': 'Cold Water (feat. Justin Bieber & M\uFFFD)',
         'album': 'Cold Water (feat. Justin Bieber & M\uFFFD) - Single', 'year': '2016',
         'samplerate': 44100, 'duration': 188.545, 'genre': 'Electronic;Music',
         'albumartist': 'Major Lazer', 'channels': 2, 'bitrate': 125.584,
         'comment': '? 2016 Mad Decent'}),
    ('samples/alac_file.m4a',
        {'extra': {'copyright': '© Hyperion Records Ltd, London', 'lyrics': 'Album notes:',
         'upc': '0034571177380', 'composer': 'Clementi, Muzio (1752-1832)'},
         'artist': 'Howard Shelley', 'filesize': 20000,
         'title': 'Clementi: Piano Sonata in D major, Op 25 No 6 - Movement 2: Un poco andante',
         'album': 'Clementi: The Complete Piano Sonatas, Vol. 4', 'year': '2009', 'track': 14,
         'track_total': 27, 'disc': 1, 'disc_total': 1, 'samplerate': 44100,
         'duration': 166.62639455782312, 'genre': 'Classical', 'albumartist': 'Howard Shelley',
         'channels': 2, 'bitrate': 436.743, 'bitdepth': 16}),
    ('samples/mpeg4_desc_cmt.m4a', {
        'filesize': 32006,
        'bitrate': 101.038,
        'channels': 2,
        'comment': 'test comment',
        'duration': 2.36,
        'extra': {'description': 'test description'},
        'samplerate': 44100}),
    ('samples/mpeg4_xa9des.m4a', {
        'filesize': 2639,
        'comment': 'test comment',
        'duration': 727.1066666666667,
        'extra': {'description': 'test description'}}),
    ('samples/test3.m4a',
        {'extra': {'publisher': 'test7', 'bpm': 99999, 'composer': 'test8'}, 'artist': 'test1',
         'filesize': 6260, 'samplerate': 8000, 'duration': 1.294, 'channels': 1,
         'bitrate': 27.887}),

    # AIFF
    ('samples/test-tagged.aiff',
        {'extra': {}, 'channels': 2, 'duration': 1.0, 'filesize': 177620, 'artist': 'theartist',
         'bitrate': 1411.2, 'genre': 'Acid', 'samplerate': 44100, 'bitdepth': 16, 'track': 1,
         'title': 'thetitle', 'album': 'thealbum', 'comment': 'hello',
         'year': '2014'}),
    ('samples/test.aiff',
        {'extra': {'copyright': '℗ 1992 Ace Records'}, 'channels': 2, 'duration': 0.0,
         'filesize': 164, 'bitrate': 1411.2, 'samplerate': 44100, 'bitdepth': 16,
         'title': 'Go Out and Get Some',
         'comment': 'Millie Jackson - Get It Out \'cha System - 1978'}),
    ('samples/pluck-pcm8.aiff',
        {'extra': {}, 'channels': 2, 'duration': 0.2999546485260771, 'filesize': 6892,
         'artist': 'Serhiy Storchaka', 'title': 'Pluck', 'album': 'Python Test Suite',
         'bitrate': 176.4, 'samplerate': 11025, 'bitdepth': 8,
         'comment': 'Audacity Pluck + Wahwah', 'year': '2013'}),
    ('samples/M1F1-mulawC-AFsp.afc',
        {'extra': {}, 'channels': 2, 'duration': 2.936625, 'filesize': 47148,
         'bitrate': 256.0, 'samplerate': 8000, 'bitdepth': 16,
         'comment':
         'AFspdate: 2003-01-30 03:28:34 UTC\x00user: kabal@CAPELLA\x00program: CopyAudio'}),
    ('samples/invalid_sample_rate.aiff',
        {'extra': {}, 'channels': 1, 'filesize': 4096, 'bitdepth': 16}),
    ('samples/aiff_extra_tags.aiff',
        {'extra': {'copyright': 'test', 'isrc': 'CC-XXX-YY-NNNNN'}, 'channels': 1,
         'duration': 2.176, 'filesize': 18532, 'bitrate': 64.0, 'samplerate': 8000, 'bitdepth': 8,
         'title': 'song title', 'artist': 'artist 1;artist 2'}),

])

testfolder = os.path.join(os.path.dirname(__file__))


def load_custom_samples() -> dict[str, dict[str, Any]]:
    retval = {}
    custom_samples_folder = os.path.join(testfolder, 'custom_samples')
    pattern_field_name_type = [
        (r'sr=(\d+)', 'samplerate', int),
        (r'dn=(\d+)', 'disc', str),
        (r'dt=(\d+)', 'disc_total', str),
        (r'd=(\d+.?\d*)', 'duration', float),
        (r'b=(\d+)', 'bitrate', int),
        (r'c=(\d)', 'channels', int),
        (r'genre="([^"]+)"', 'genre', str),
    ]
    for filename in os.listdir(custom_samples_folder):
        if filename == 'instructions.txt':
            continue
        if os.path.isdir(os.path.join(custom_samples_folder, filename)):
            continue
        expected_values = {}
        for pattern, fieldname, _type in pattern_field_name_type:
            match = re.findall(pattern, filename)
            if match:
                expected_values[fieldname] = _type(match[0])
        if expected_values:
            expected_values['_do_not_require_all_values'] = True
            retval[os.path.join('custom_samples', filename)] = expected_values
        else:
            # if there are no expected values, just try parsing the file
            retval[os.path.join('custom_samples', filename)] = {}
    return retval


testfiles.update(load_custom_samples())


def compare_tag(results: dict[str, dict[str, Any]], expected: dict[str, dict[str, Any]],
                file: str, prev_path: str | None = None) -> None:
    def compare_values(path: str, result_val: int | float | str | dict[str, Any],
                       expected_val: int | float | str | dict[str, Any]) -> bool:
        # lets not copy *all* the lyrics inside the fixture
        if (path == 'extra.lyrics'
                and isinstance(expected_val, str) and isinstance(result_val, str)):
            return result_val.startswith(expected_val)
        if isinstance(expected_val, float):
            return result_val == pytest.approx(expected_val)
        return result_val == expected_val

    def error_fmt(value: int | float | str | dict[str, Any]) -> str:
        return f'{repr(value)} ({type(value)})'

    assert isinstance(results, dict)
    missing_keys = set(expected.keys()) - set(results)
    assert not missing_keys, f'Missing data in fixture \n{missing_keys}'

    for key, result_val in results.items():
        path = prev_path + '.' + key if prev_path else key
        expected_val = expected[key]
        # recurse if the result and expected values are a dict:
        if isinstance(result_val, dict) and isinstance(expected_val, dict):
            compare_tag(result_val, expected_val, file, prev_path=key)
        else:
            fmt_string = 'field "%s": got %s expected %s in %s!'
            fmt_values = (key, error_fmt(result_val), error_fmt(expected_val), file)
            assert compare_values(path, result_val, expected_val), fmt_string % fmt_values


@pytest.mark.parametrize("testfile,expected", testfiles.items())
def test_file_reading_tags_duration(testfile: str, expected: dict[str, dict[str, Any]]) -> None:
    filename = os.path.join(testfolder, testfile)
    tag = TinyTag.get(filename, tags=True, duration=True)
    results = {
        key: val for key, val in tag._as_dict().items() if val is not None and key != 'images'
    }
    compare_tag(results, expected, filename)
    assert tag.images.front_cover.data is None


@pytest.mark.parametrize("testfile,expected", testfiles.items())
def test_file_reading_tags(testfile: str, expected: dict[str, dict[str, Any]]) -> None:
    filename = os.path.join(testfolder, testfile)
    excluded_attrs = {"bitdepth", "bitrate", "channels", "duration", "samplerate"}
    tag = TinyTag.get(filename, tags=True, duration=False)
    results = {
        key: val for key, val in tag._as_dict().items() if val is not None and key != 'images'
    }
    expected = {
        key: val for key, val in expected.items() if key not in excluded_attrs
    }
    compare_tag(results, expected, filename)
    assert tag.images.front_cover.data is None


@pytest.mark.parametrize("testfile,expected", testfiles.items())
def test_file_reading_duration(testfile: str, expected: dict[str, dict[str, Any]]) -> None:
    filename = os.path.join(testfolder, testfile)
    allowed_attrs = {"bitdepth", "bitrate", "channels", "duration", "filesize", "samplerate"}
    tag = TinyTag.get(filename, tags=False, duration=True)
    results = {
        key: val for key, val in tag._as_dict().items() if val is not None and key != 'images'
    }
    expected = {
        key: val for key, val in expected.items() if key in allowed_attrs
    }
    expected["extra"] = {}
    compare_tag(results, expected, filename)
    assert tag.images.front_cover.data is None


def test_pathlib_compatibility() -> None:
    testfile = next(iter(testfiles.keys()))
    filename = pathlib.Path(testfolder) / testfile
    TinyTag.get(filename)
    assert TinyTag.is_supported(filename)


def test_file_obj_compatibility() -> None:
    testfile = next(iter(testfiles.keys()))
    filename = os.path.join(testfolder, testfile)
    with open(filename, 'rb') as file_handle:
        tag = TinyTag.get(file_obj=file_handle)
        file_handle.seek(0)
        tag_bytesio = TinyTag.get(file_obj=io.BytesIO(file_handle.read()))
        assert tag.filesize == tag_bytesio.filesize


@pytest.mark.skipif(sys.platform == "win32", reason='Windows does not support binary paths')
def test_binary_path_compatibility() -> None:
    binary_file_path = os.path.join(os.path.dirname(__file__).encode('utf-8'), b'\x01.mp3')
    testfile = os.path.join(testfolder, next(iter(testfiles.keys()))).encode('utf-8')
    shutil.copy(testfile, binary_file_path)
    assert os.path.exists(binary_file_path)
    TinyTag.get(binary_file_path)
    os.unlink(binary_file_path)
    assert not os.path.exists(binary_file_path)


@pytest.mark.xfail(raises=TinyTagException)
def test_unsupported_extension() -> None:
    bogus_file = os.path.join(testfolder, 'samples/there_is_no_such_ext.bogus')
    TinyTag.get(bogus_file)


def test_override_encoding() -> None:
    chinese_id3 = os.path.join(testfolder, 'samples/chinese_id3.mp3')
    tag = TinyTag.get(chinese_id3, encoding='gbk')
    assert tag.artist == '苏云'
    assert tag.album == '角落之歌'


@pytest.mark.xfail(raises=TinyTagException)
def test_unsubclassed_tinytag_load() -> None:
    tag = TinyTag()
    tag._load(tags=True, duration=True)


@pytest.mark.xfail(raises=NotImplementedError)
def test_unsubclassed_tinytag_duration() -> None:
    tag = TinyTag()
    tag._determine_duration(None)  # type: ignore


@pytest.mark.xfail(raises=NotImplementedError)
def test_unsubclassed_tinytag_parse_tag() -> None:
    tag = TinyTag()
    tag._parse_tag(None)  # type: ignore


def test_mp3_length_estimation() -> None:
    _ID3._MAX_ESTIMATION_SEC = 0.7
    tag = TinyTag.get(os.path.join(testfolder, 'samples/silence-44-s-v1.mp3'))
    assert tag.duration is not None
    assert 3.5 < tag.duration < 4.0


@pytest.mark.parametrize("path,cls", [
    ('samples/silence-44-s-v1.mp3', _Flac),
    ('samples/incomplete.mp3', _ID3),
    ('samples/flac1.5sStereo.flac', _Ogg),
    ('samples/flac1.5sStereo.flac', _Wave),
    ('samples/flac1.5sStereo.flac', _Wma),
    ('samples/ilbm.aiff', _Aiff),
])
@pytest.mark.xfail(raises=TinyTagException)
def test_invalid_file(path: str, cls: type[TinyTag]) -> None:
    cls.get(os.path.join(testfolder, path))


@pytest.mark.parametrize('path,expected_size', [
    ('samples/cover_img.mp3', 146676),
    ('samples/id3v22_image.mp3', 18092),
    ('samples/id3image_without_description.mp3', 28680),
    ('samples/image-text-encoding.mp3', 5708),
    ('samples/12oz.mp3', 2210),
    ('samples/iso8859_with_image.m4a', 21963),
    ('samples/flac_with_image.flac', 73246),
    ('samples/ogg_with_image.ogg', 1220),
    ('samples/wav_with_image.wav', 4627),
    ('samples/aiff_with_image.aiff', 21963),
])
def test_image_loading(path: str, expected_size: int) -> None:
    tag = TinyTag.get(os.path.join(testfolder, path), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    image_size = len(image_data)
    assert image_size == expected_size, \
           f'Image is {image_size} bytes but should be {expected_size} bytes'
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), \
           'The image data must start with a jpeg header'


@pytest.mark.xfail(raises=TinyTagException)
def test_mp3_utf_8_invalid_string_raises_exception() -> None:
    TinyTag.get(os.path.join(testfolder, 'samples/utf-8-id3v2-invalid-string.mp3'))


def test_mp3_utf_8_invalid_string_can_be_ignored() -> None:
    tag = TinyTag.get(os.path.join(testfolder, 'samples/utf-8-id3v2-invalid-string.mp3'),
                      ignore_errors=True)
    # the title used to be Gran dia, but I replaced the first byte with 0xFF,
    # which should be ignored here
    assert tag.title == 'ran día'


@pytest.mark.parametrize("testfile,expected", [
    ('samples/detect_mp3_id3.x', _ID3),
    ('samples/detect_mp3_fffb.x', _ID3),
    ('samples/detect_ogg_flac.x', _Ogg),
    ('samples/detect_ogg_opus.x', _Ogg),
    ('samples/detect_ogg_vorbis.x', _Ogg),
    ('samples/detect_wav.x', _Wave),
    ('samples/detect_flac.x', _Flac),
    ('samples/detect_wma.x', _Wma),
    ('samples/detect_mp4_m4a.x', _MP4),
    ('samples/detect_aiff.x', _Aiff),
])
def test_detect_magic_headers(testfile: str, expected: type[TinyTag]) -> None:
    filename = os.path.join(testfolder, testfile)
    with open(filename, 'rb') as file_handle:
        parser = TinyTag._get_parser_class(filename, file_handle)
    assert parser == expected


def test_show_hint_for_wrong_usage() -> None:
    with pytest.raises(TinyTagException) as exc_info:
        TinyTag.get()
    assert exc_info.type == TinyTagException
    assert exc_info.value.args[0] == 'Either filename or file_obj argument is required'


def test_to_str() -> None:
    tag = TinyTag.get(os.path.join(testfolder, 'samples/id3v22-test.mp3'))
    assert str(tag) == (
        "{'album': 'Hymns for the Exiled', 'albumartist': None, 'artist': 'Anais Mitchell', "
        "'bitdepth': None, 'bitrate': 160.0, 'channels': 2, "
        "'comment': 'Waterbug Records, www.anaismitchell.com', 'disc': None, "
        "'disc_total': None, 'duration': 0.13836297152858082, 'extra': {'ten': 'iTunes v4.6', "
        "'itunnorm': ' 0000044E 00000061 00009B67 000044C3 00022478 00022182 00007FCC "
        "00007E5C 0002245E 0002214E', 'itunes_cddb_1': '9D09130B+174405+11+150+14097+27391+43983+"
        "65786+84877+99399+113226+132452+146426+163829', 'itunes_cddb_tracknumber': '3'}, "
        "'filesize': 5120, "
        "'genre': None, 'samplerate': 44100, 'title': 'cosmic american', 'track': 3, "
        "'track_total': 11, 'year': '2004'}")
