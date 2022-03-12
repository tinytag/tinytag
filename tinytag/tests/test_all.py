#!/usr/bin/python
# -*- coding: utf-8 -*-

# tests can be extended using other bigger files that are not going to be
# checked into git, by placing them into the custom_samples folder
#
# see custom_samples/instructions.txt
#


from __future__ import unicode_literals

import io
import os
import re
import shutil
import sys

import pytest
from pytest import raises

from tinytag.tinytag import TinyTag, TinyTagException, ID3, Ogg, Wave, Flac, Wma, MP4, Aiff

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict  # python 2.6 and 3.2 compat


testfiles = OrderedDict([
    # MP3
    ('samples/vbri.mp3',
        {'extra': {'url': ''}, 'channels': 2, 'samplerate': 44100, 'track_total': None,
         'duration': 0.47020408163265304, 'album': 'I Can Walk On Water I Can Fly', 'year': '2007',
         'title': 'I Can Walk On Water I Can Fly', 'artist': 'Basshunter', 'track': '01',
         'filesize': 8192, 'audio_offset': 1007, 'genre': '(3)Dance',
         'comment': 'Ripped by THSLIVE', 'composer': '', 'bitrate': 125.33333333333333}),
    ('samples/cbr.mp3',
        {'extra': {}, 'channels': 2, 'samplerate': 44100, 'track_total': None, 'duration': 0.49,
         'album': 'I Can Walk On Water I Can Fly', 'year': '2007',
         'title': 'I Can Walk On Water I Can Fly', 'artist': 'Basshunter', 'track': '01',
         'filesize': 8186, 'audio_offset': 246, 'bitrate': 128.0, 'genre': 'Dance',
         'comment': 'Ripped by THSLIVE'}),
    # the output of the lame encoder was 185.4 bitrate, but this is good enough for now
    ('samples/vbr_xing_header.mp3',
        {'extra': {}, 'bitrate': 186.04383278145696, 'channels': 1, 'samplerate': 44100,
         'duration': 3.944489795918367, 'filesize': 91731, 'audio_offset': 441}),
    ('samples/vbr_xing_header_2channel.mp3',
        {'extra': {}, 'filesize': 2000, 'album': "The Harpers' Masque",
         'artist': 'Knodel and Valencia', 'audio_offset': 694, 'bitrate': 46.276128290848305,
         'channels': 2, 'duration': 250.04408163265308, 'samplerate': 22050,
         'title': 'Lochaber No More', 'year': '1992'}),
    ('samples/id3v22-test.mp3',
        {'extra': {}, 'channels': 2, 'samplerate': 44100, 'track_total': '11', 'duration': 0.138,
         'album': 'Hymns for the Exiled', 'year': '2004', 'title': 'cosmic american',
         'artist': 'Anais Mitchell', 'track': '3', 'filesize': 5120, 'audio_offset': 2225,
         'bitrate': 160.0, 'comment': 'Waterbug Records, www.anaismitchell.com'}),
    ('samples/silence-44-s-v1.mp3',
        {'extra': {}, 'channels': 2, 'samplerate': 44100, 'genre': 'Darkwave', 'track_total': None,
         'duration': 3.7355102040816326, 'album': 'Quod Libet Test Data', 'year': '2004',
         'title': 'Silence', 'artist': 'piman', 'track': '2', 'filesize': 15070, 'audio_offset': 0,
         'bitrate': 32.0, 'comment': ''}),
    ('samples/id3v1-latin1.mp3',
        {'extra': {}, 'channels': None, 'samplerate': None, 'genre': 'Rock',
         'album': 'The Young Americans', 'title': 'Play Dead', 'filesize': 256, 'track': '12',
         'artist': 'Björk', 'track_total': None, 'year': '1993',
         'comment': '                            '}),
    ('samples/UTF16.mp3',
        {'extra': {'text': 'MusicBrainz Artist Id664c3e0e-42d8-48c1-b209-1efca19c0325',
         'url': 'WIKIPEDIA_RELEASEhttp://en.wikipedia.org/wiki/High_Violet'}, 'channels': None,
         'samplerate': None, 'track_total': '11', 'track': '07', 'artist': 'The National',
         'year': '2010', 'album': 'High Violet', 'title': 'Lemonworld', 'filesize': 20480,
         'genre': 'Indie', 'comment': 'Track 7'}),
    ('samples/utf-8-id3v2.mp3',
        {'extra': {}, 'channels': None, 'samplerate': None, 'genre': 'Acustico',
         'track_total': '21', 'track': '01', 'filesize': 2119, 'title': 'Gran día',
         'artist': 'Paso a paso', 'album': 'S/T', 'year': None, 'disc': '', 'disc_total': '0'}),
    ('samples/empty_file.mp3',
        {'extra': {}, 'channels': None, 'samplerate': None, 'track_total': None, 'album': None,
         'year': None, 'title': None, 'track': None, 'artist': None, 'filesize': 0}),
    ('samples/silence-44khz-56k-mono-1s.mp3',
        {'extra': {}, 'channels': 1, 'samplerate': 44100, 'duration': 1.018, 'filesize': 7280,
         'audio_offset': 0, 'bitrate': 56.0}),
    ('samples/silence-22khz-mono-1s.mp3',
        {'extra': {}, 'channels': 1, 'samplerate': 22050, 'filesize': 4284, 'audio_offset': 0,
         'bitrate': 32.0, 'duration': 1.0438932496075353}),
    ('samples/id3v24-long-title.mp3',
        {'extra': {}, 'track': '1', 'disc_total': '1',
         'album': 'The Double EP: A Sea of Split Peas', 'filesize': 10000,
         'channels': None, 'track_total': '12', 'genre': 'AlternRock',
         'title': 'Out of the Woodwork', 'artist': 'Courtney Barnett',
         'albumartist': 'Courtney Barnett', 'samplerate': None, 'year': None, 'disc': '1',
         'comment': 'Amazon.com Song ID: 240853806', 'composer': 'Courtney Barnett'}),
    ('samples/utf16be.mp3',
        {'extra': {}, 'title': '52-girls', 'filesize': 2048, 'track': '6', 'album': 'party mix',
         'artist': 'The B52s', 'genre': 'Rock', 'albumartist': None, 'disc': None,
         'channels': None}),
    ('samples/id3v22_image.mp3',
        {'extra': {}, 'title': 'Kids (MGMT Cover) ', 'filesize': 35924,
         'album': 'winniecooper.net ', 'artist': 'The Kooks', 'year': '2008',
         'channels': None, 'genre': '.'}),
    ('samples/id3v22.TCO.genre.mp3',
        {'extra': {}, 'filesize': 500, 'album': 'ARTPOP', 'artist': 'Lady GaGa',
         'comment': 'engiTunPGAP0', 'genre': 'Pop', 'title': 'Applause'}),
    ('samples/id3_comment_utf_16_with_bom.mp3',
        {'extra': {'isrc': 'USTC40852229'}, 'filesize': 19980, 'album': 'Ghosts I-IV',
         'albumartist': 'Nine Inch Nails', 'artist': 'Nine Inch Nails', 'disc': '1',
         'disc_total': '2', 'title': '1 Ghosts I', 'track': '1', 'track_total': '36',
         'year': '2008', 'comment': '3/4 time'}),
    ('samples/id3_comment_utf_16_double_bom.mp3',
        {'extra': {'text': 'LABEL\ufeffUnclear'}, 'filesize': 512, 'album': 'The Embrace',
         'artist': 'Johannes Heil & D.Diggler', 'comment': 'Unclear',
         'title': 'The Embrace (Romano Alfieri Remix)',
         'track': '04-johannes_heil_and_d.diggler-the_embrace_(romano_alfieri_remix)',
         'year': '2012'}),
    ('samples/id3_genre_id_out_of_bounds.mp3',
        {'extra': {}, 'filesize': 512, 'album': 'MECHANICAL ANIMALS', 'artist': 'Manson',
         'comment': '', 'genre': '(255)', 'title': '01 GREAT BIG WHITE WORLD', 'track': 'Marilyn',
         'year': '0'}),
    ('samples/image-text-encoding.mp3',
        {'extra': {}, 'channels': 1, 'samplerate': 22050, 'filesize': 11104,
         'title': 'image-encoding', 'audio_offset': 6820, 'bitrate': 32.0,
         'duration': 1.0438932496075353}),
    ('samples/id3v1_does_not_overwrite_id3v2.mp3',
        {'filesize': 1130, 'album': 'Somewhere Far Beyond', 'albumartist': 'Blind Guardian',
         'artist': 'Blind Guardian', 'comment': '', 'extra': {'text': 'LOVE RATINGL'},
         'genre': 'Power Metal', 'title': 'Time What Is Time', 'track': '01', 'year': '1992'}),
    ('samples/nicotinetestdata.mp3',
        {'extra': {}, 'filesize': 80919, 'audio_offset': 45, 'channels': 2,
         'duration': 5.067755102040817, 'samplerate': 44100, 'bitrate': 127.6701030927835}),
    ('samples/chinese_id3.mp3',
        {'extra': {}, 'filesize': 1000, 'album': '½ÇÂäÖ®¸è', 'albumartist': 'ËÕÔÆ',
         'artist': 'ËÕÔÆ', 'audio_offset': 512, 'bitrate': 128.0, 'channels': 2,
         'duration': 0.052244897959183675, 'genre': 'ÐÝÏÐÒôÀÖ', 'samplerate': 44100,
         'title': '½ÇÂäÖ®¸è', 'track': '1'}),
    ('samples/cut_off_titles.mp3',
        {'extra': {}, 'filesize': 1000, 'album': 'ERB', 'artist': 'Epic Rap Battles Of History',
         'audio_offset': 194, 'bitrate': 192.0, 'channels': 2, 'duration': 0.052244897959183675,
         'samplerate': 44100, 'title': 'Tony Hawk VS Wayne Gretzky'}),
    ('samples/id3_xxx_lang.mp3',
        {'extra': {'isrc': 'USVI20400513', 'lyrics': "Don't fret, precious",
                   'text': 'SCRIPT\ufeffLatn'},
         'filesize': 6943, 'album': 'eMOTIVe', 'albumartist': 'A Perfect Circle',
         'artist': 'A Perfect Circle', 'audio_offset': 3647, 'bitrate': 192.0, 'channels': 2,
         'duration': 0.13198711063372717, 'genre': 'Rock',
         'samplerate': 44100, 'title': 'Counting Bodies Like Sheep to the Rhythm of the War Drums',
         'track': '10', 'comment': '                            ',
         'composer': 'Billy Howerdel/Maynard James Keenan', 'disc': '1', 'disc_total': '1',
         'track_total': '12', 'year': '2004'}),
    ('samples/mp3/vbr/vbr8.mp3',
     {'filesize': 9504, 'audio_offset': 433, 'bitrate': 8.25, 'channels': 1, 'duration': 9.2,
      'extra': {}, 'samplerate': 8000}),
    ('samples/mp3/vbr/vbr8stereo.mp3',
     {'filesize': 9504, 'audio_offset': 441, 'bitrate': 8.25, 'channels': 2, 'duration': 9.216,
      'extra': {}, 'samplerate': 8000}),
    ('samples/mp3/vbr/vbr11.mp3',
     {'filesize': 9360, 'audio_offset': 433, 'bitrate': 8.143465909090908, 'channels': 1,
      'duration': 9.2, 'extra': {}, 'samplerate': 11025}),
    ('samples/mp3/vbr/vbr11stereo.mp3',
     {'filesize': 9360, 'audio_offset': 441, 'bitrate': 8.143465909090908, 'channels': 2,
      'duration': 9.195102040816327, 'extra': {}, 'samplerate': 11025}),
    ('samples/mp3/vbr/vbr16.mp3',
     {'filesize': 9432, 'audio_offset': 433, 'bitrate': 8.251968503937007, 'channels': 1,
      'duration': 9.2, 'extra': {}, 'samplerate': 16000}),
    ('samples/mp3/vbr/vbr16stereo.mp3',
     {'filesize': 9432, 'audio_offset': 441, 'bitrate': 8.251968503937007, 'channels': 2,
      'duration': 9.144, 'extra': {}, 'samplerate': 16000}),
    ('samples/mp3/vbr/vbr22.mp3',
     {'filesize': 9282, 'audio_offset': 433, 'bitrate': 8.145021489971347, 'channels': 1,
      'duration': 9.2, 'extra': {}, 'samplerate': 22050}),
    ('samples/mp3/vbr/vbr22stereo.mp3',
     {'filesize': 9282, 'audio_offset': 441, 'bitrate': 8.145021489971347, 'channels': 2,
      'duration': 9.11673469387755, 'extra': {}, 'samplerate': 22050}),
    ('samples/mp3/vbr/vbr32.mp3',
     {'filesize': 37008, 'audio_offset': 441, 'bitrate': 32.50592885375494, 'channels': 1,
      'duration': 9.108, 'extra': {}, 'samplerate': 32000}),
    ('samples/mp3/vbr/vbr32stereo.mp3',
     {'filesize': 37008, 'audio_offset': 456, 'bitrate': 32.50592885375494, 'channels': 2,
      'duration': 9.108, 'extra': {}, 'samplerate': 32000}),
    ('samples/mp3/vbr/vbr44.mp3',
     {'filesize': 36609, 'audio_offset': 441, 'bitrate': 32.21697198275862, 'channels': 1,
      'duration': 9.09061224489796, 'extra': {}, 'samplerate': 44100}),
    ('samples/mp3/vbr/vbr44stereo.mp3',
     {'filesize': 36609, 'audio_offset': 456, 'bitrate': 32.21697198275862, 'channels': 2,
      'duration': 9.0, 'extra': {}, 'samplerate': 44100}),
    ('samples/mp3/vbr/vbr48.mp3',
     {'filesize': 36672, 'audio_offset': 441, 'bitrate': 32.33862433862434, 'channels': 1,
      'duration': 9.072, 'extra': {}, 'samplerate': 48000}),
    ('samples/mp3/vbr/vbr48stereo.mp3',
     {'filesize': 36672, 'audio_offset': 456, 'bitrate': 32.33862433862434, 'channels': 2,
      'duration': 9.072, 'extra': {}, 'samplerate': 48000}),

    # OGG
    ('samples/empty.ogg',
        {'extra': {}, 'track_total': None, 'duration': 3.684716553287982, 'album': None,
         '_max_samplenum': 162496, 'year': None, 'title': None, 'artist': None, 'track': None,
         '_tags_parsed': False, 'filesize': 4328, 'audio_offset': 0, 'bitrate': 112.0,
         'samplerate': 44100}),
    ('samples/multipagecomment.ogg',
        {'extra': {}, 'track_total': None, 'duration': 3.684716553287982, 'album': None,
         '_max_samplenum': 162496, 'year': None, 'title': None, 'artist': None, 'track': None,
         '_tags_parsed': False, 'filesize': 135694, 'audio_offset': 0, 'bitrate': 112,
         'samplerate': 44100}),
    ('samples/multipage-setup.ogg',
        {'extra': {}, 'genre': 'JRock', 'track_total': None, 'duration': 4.128798185941043,
         'album': 'Timeless', 'year': '2006', 'title': 'Burst', 'artist': 'UVERworld', 'track': '7',
         '_tags_parsed': False, 'filesize': 76983, 'audio_offset': 0, 'bitrate': 160.0,
         'samplerate': 44100}),
    ('samples/test.ogg',
        {'extra': {}, 'track_total': None, 'duration': 1.0, 'album': 'the boss', 'year': '2006',
         'title': 'the boss', 'artist': 'james brown', 'track': '1', '_tags_parsed': False,
         'filesize': 7467, 'audio_offset': 0, 'bitrate': 160.0, 'samplerate': 44100,
         'comment': 'hello!'}),
    ('samples/corrupt_metadata.ogg',
        {'extra': {}, 'filesize': 18648, 'audio_offset': 0, 'bitrate': 80.0,
         'duration': 2.132358276643991, 'samplerate': 44100}),
    ('samples/composer.ogg',
        {'extra': {}, 'filesize': 4480, 'album': 'An Album', 'artist': 'An Artist',
         'audio_offset': 0, 'bitrate': 112.0, 'duration': 3.684716553287982,
         'genre': 'Some Genre', 'samplerate': 44100, 'title': 'A Title', 'track': '2',
         'year': '2007', 'composer': 'some composer'}),

    # OPUS
    ('samples/test.opus',
        {'extra': {}, 'albumartist': 'Alstroemeria Records', 'samplerate': 48000, 'channels': 2,
         'track': '1', 'disc': '1', 'title': 'Bad Apple!!', 'duration': 2.0, 'year': '2008.05.25',
         'filesize': 10000, 'artist': 'nomico',
         'album': 'Exserens - A selection of Alstroemeria Records',
         'comment': 'ARCD0018 - Lovelight'}),
    ('samples/8khz_5s.opus',
        {'extra': {}, 'filesize': 7251, 'channels': 1, 'samplerate': 48000, 'duration': 5.0}),

    # WAV
    ('samples/test.wav',
        {'extra': {}, 'channels': 2, 'duration': 1.0, 'filesize': 176444, 'bitrate': 1411.2,
         'samplerate': 44100, 'audio_offset': 36}),
    ('samples/test3sMono.wav',
        {'extra': {}, 'channels': 1, 'duration': 3.0, 'filesize': 264644, 'bitrate': 705.6,
         'samplerate': 44100, 'audio_offset': 36}),
    ('samples/test-tagged.wav',
        {'extra': {}, 'channels': 2, 'duration': 1.0, 'filesize': 176688, 'album': 'thealbum',
         'artist': 'theartisst', 'bitrate': 1411.2, 'genre': 'Acid', 'samplerate': 44100,
         'title': 'thetitle', 'track': '66', 'audio_offset': 36, 'comment': 'hello',
         'year': '2014'}),
    ('samples/test-riff-tags.wav',
        {'extra': {}, 'channels': 2, 'duration': 1.0, 'filesize': 176540, 'album': None,
         'artist': 'theartisst', 'bitrate': 1411.2, 'genre': 'Acid', 'samplerate': 44100,
         'title': 'thetitle', 'track': None, 'audio_offset': 36, 'comment': 'hello',
         'year': '2014'}),
    ('samples/silence-22khz-mono-1s.wav',
        {'extra': {}, 'channels': 1, 'duration': 1.0, 'filesize': 48160, 'bitrate': 352.8,
         'samplerate': 22050, 'audio_offset': 4088}),
    ('samples/id3_header_with_a_zero_byte.wav',
        {'extra': {}, 'channels': 1, 'duration': 1.0, 'filesize': 44280, 'bitrate': 352.8,
         'samplerate': 22050, 'audio_offset': 122, 'artist': 'Purpley', 'title': 'Test000',
         'track': '17'}),
    ('samples/adpcm.wav',
        {'extra': {}, 'channels': 1, 'duration': 12.167256235827665, 'filesize': 268686,
         'bitrate': 176.4, 'samplerate': 44100, 'audio_offset': 82, 'artist': 'test artist',
         'title': 'test title', 'track': '1', 'album': 'test album', 'comment': 'test comment',
         'genre': 'test genre', 'year': '1990'}),

    # FLAC
    ('samples/flac1sMono.flac',
        {'extra': {}, 'genre': 'Avantgarde', 'track_total': None, 'album': 'alb', 'year': '2014',
         'duration': 1.0, 'title': 'track', 'track': '23', 'artist': 'art', 'channels': 1,
         'filesize': 26632, 'bitrate': 213.056, 'samplerate': 44100}),
    ('samples/flac453sStereo.flac',
        {'extra': {}, 'channels': 2, 'track_total': None, 'album': None, 'year': None,
         'duration': 453.51473922902494, 'title': None, 'track': None, 'artist': None,
         'filesize': 84236, 'bitrate': 1.4859230399999999, 'samplerate': 44100}),
    ('samples/flac1.5sStereo.flac',
        {'extra': {}, 'channels': 2, 'track_total': None, 'album': 'alb', 'year': '2014',
         'duration': 1.4995238095238095, 'title': 'track', 'track': '23', 'artist': 'art',
         'filesize': 59868, 'bitrate': 319.39739599872973, 'genre': 'Avantgarde',
         'samplerate': 44100}),
    ('samples/flac_application.flac',
        {'extra': {}, 'channels': 2, 'track_total': '11',
         'album': 'Belle and Sebastian Write About Love', 'year': '2010-10-11', 'duration': 273.64,
         'title': 'I Want the World to Stop', 'track': '4', 'artist': 'Belle and Sebastian',
         'filesize': 13000, 'bitrate': 0.38006139453296306, 'samplerate': 44100}),
    ('samples/no-tags.flac',
        {'extra': {}, 'channels': 2, 'track_total': None, 'album': None, 'year': None,
         'duration': 3.684716553287982, 'title': None, 'track': None, 'artist': None,
         'filesize': 4692, 'bitrate': 10.186943678613627, 'samplerate': 44100}),
    ('samples/variable-block.flac',
        {'extra': {}, 'channels': 2, 'album': 'Appleseed Original Soundtrack', 'year': '2004',
         'duration': 261.68, 'title': 'DIVE FOR YOU', 'track': '01', 'track_total': '11',
         'artist': 'Boom Boom Satellites', 'filesize': 10240, 'bitrate': 0.31305411189238763,
         'disc': '1', 'genre': 'Anime Soundtrack', 'samplerate': 44100,
         'composer': 'Boom Boom Satellites (Lyrics)', 'disc_total': '2'}),
    ('samples/106-invalid-streaminfo.flac',
        {'extra': {}, 'filesize': 4692}),
    ('samples/106-short-picture-block-size.flac',
        {'extra': {}, 'filesize': 4692, 'bitrate': 10.186943678613627, 'channels': 2,
         'duration': 3.68, 'samplerate': 44100}),
    ('samples/with_id3_header.flac',
        {'extra': {}, 'filesize': 64837, 'album': '   ', 'artist': '群星', 'disc': '0',
         'title': 'A 梦 哆啦 机器猫 短信铃声', 'track': '0', 'bitrate': 1143.72468, 'channels': 1,
         'duration': 0.45351473922902497, 'genre': 'genre', 'samplerate': 44100, 'year': '2018'}),
    ('samples/with_padded_id3_header.flac',
        {'extra': {}, 'filesize': 16070, 'album': 'album', 'albumartist': None, 'artist': 'artist',
         'audio_offset': None, 'bitrate': 283.4748, 'channels': 1, 'comment': None, 'disc': None,
         'disc_total': None, 'duration': 0.45351473922902497, 'genre': 'genre', 'samplerate': 44100,
         'title': 'title', 'track': '1', 'track_total': None, 'year': '2018'}),
    ('samples/with_padded_id3_header2.flac',
        {'extra': {}, 'filesize': 19522, 'album': 'Unbekannter Titel', 'albumartist': None,
         'artist': 'Unbekannter Künstler', 'audio_offset': None, 'bitrate': 344.36807999999996,
         'channels': 1, 'comment': None, 'disc': '1', 'disc_total': '1',
         'duration': 0.45351473922902497, 'genre': 'genre', 'samplerate': 44100, 'title': 'Track01',
         'track': '01', 'track_total': '05', 'year': '2018'}),
    ('samples/flac_with_image.flac',
        {'extra': {}, 'filesize': 80000, 'album': 'smilin´ in circles', 'artist': 'Andreas Kümmert',
         'bitrate': 7.6591670655816175, 'channels': 2, 'disc': '1', 'disc_total': '1',
         'duration': 83.56, 'genre': 'Blues', 'samplerate': 44100, 'title': 'intro', 'track': '01',
         'track_total': '8'}),

    # WMA
    ('samples/test2.wma',
        {'extra': {}, 'samplerate': 44100, 'album': 'The Colour and the Shape', 'title': 'Doll',
         'bitrate': 64.04, 'filesize': 5800, 'track': '1', 'albumartist': 'Foo Fighters',
         'artist': 'Foo Fighters', 'duration': 83.406, 'track_total': None, 'year': '1997',
         'genre': 'Alternative', 'comment': '', 'composer': 'Foo Fighters'}),

    # ALAC/M4A/MP4
    ('samples/test.m4a',
        {'extra': {}, 'samplerate': 44100, 'duration': 314.97, 'bitrate': 256.0, 'channels': 2,
         'genre': 'Pop', 'year': '2011', 'title': 'Nothing', 'album': 'Only Our Hearts To Lose',
         'track_total': '11', 'track': '11', 'artist': 'Marian', 'filesize': 61432}),
    ('samples/test2.m4a',
        {'extra': {}, 'bitrate': 256.0, 'track': '1',
         'albumartist': "Millie Jackson - Get It Out 'cha System - 1978",
         'duration': 167.78739229024944, 'filesize': 223365, 'channels': 2, 'year': '1978',
         'artist': 'Millie Jackson', 'track_total': '9', 'disc_total': '1', 'genre': 'R&B/Soul',
         'album': "Get It Out 'cha System", 'samplerate': 44100, 'disc': '1',
         'title': 'Go Out and Get Some',
         'comment': "Millie Jackson - Get It Out 'cha System - 1978",
         'composer': "Millie Jackson - Get It Out 'cha System - 1978"}),
    ('samples/iso8859_with_image.m4a',
        {'extra': {}, 'artist': 'Major Lazer', 'filesize': 57017,
         'title': 'Cold Water (feat. Justin Bieber & M�)',
         'album': 'Cold Water (feat. Justin Bieber & M�) - Single', 'year': '2016',
         'samplerate': 44100, 'duration': 188.545, 'genre': 'Electronic;Music',
         'albumartist': 'Major Lazer', 'channels': 2, 'bitrate': 125.584,
         'comment': '? 2016 Mad Decent'}),
    ('samples/alac_file.m4a',
        {'extra': {}, 'artist': 'Howard Shelley', 'composer': 'Clementi, Muzio (1752-1832)',
         'filesize': 20000,
         'title': 'Clementi: Piano Sonata in D major, Op 25 No 6 - Movement 2: Un poco andante',
         'album': 'Clementi: The Complete Piano Sonatas, Vol. 4', 'year': '2009', 'track': '14',
         'track_total': '27', 'disc': '1', 'disc_total': '1', 'samplerate': 44100,
         'duration': 166.62639455782312, 'genre': 'Classical', 'albumartist': 'Howard Shelley',
         'channels': 2, 'bitrate': 436.743}),

    # AIFF
    ('samples/test-tagged.aiff',
        {'extra': {}, 'channels': 2, 'duration': 1.0, 'filesize': 177620, 'artist': 'theartist',
         'bitrate': 1411.2, 'genre': 'Acid', 'samplerate': 44100, 'track': '1', 'title': 'thetitle',
         'album': 'thealbum', 'audio_offset': 76, 'comment': 'hello', 'year': '2014'}),
    ('samples/test.aiff',
        {'extra': {'copyright': '℗ 1992 Ace Records'}, 'channels': 2, 'duration': 0.0,
         'filesize': 164, 'artist': None, 'bitrate': 1411.2, 'genre': None, 'samplerate': 44100,
         'track': None, 'title': 'Go Out and Get Some', 'album': None, 'audio_offset': 156,
         'comment': 'Millie Jackson - Get It Out \'cha System - 1978'}),
    ('samples/pluck-pcm8.aiff',
        {'extra': {}, 'channels': 2, 'duration': 0.2999546485260771, 'filesize': 6892,
         'artist': 'Serhiy Storchaka', 'title': 'Pluck', 'album': 'Python Test Suite',
         'bitrate': 176.4, 'samplerate': 11025, 'audio_offset': 116,
         'comment': 'Audacity Pluck + Wahwah'}),
    ('samples/M1F1-mulawC-AFsp.afc',
        {'extra': {}, 'channels': 2, 'duration': 2.936625, 'filesize': 47148, 'artist': None,
         'title': None, 'album': None, 'bitrate': 256.0, 'samplerate': 8000, 'audio_offset': 154,
         'comment': 'AFspdate: 2003-01-30 03:28:34 UTCuser: kabal@CAPELLAprogram: CopyAudio'}),

])

testfolder = os.path.join(os.path.dirname(__file__))

# load custom samples
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
        expected_values['__do_not_require_all_values'] = True
        testfiles[os.path.join('custom_samples', filename)] = expected_values
    else:
        # if there are no expected values, just try parsing the file
        testfiles[os.path.join('custom_samples', filename)] = {}


@pytest.mark.parametrize("testfile,expected", [
    pytest.param(testfile, expected) for testfile, expected in testfiles.items()
])
def test_file_reading(testfile, expected):
    filename = os.path.join(testfolder, testfile)
    tag = TinyTag.get(filename)

    for key, expected_val in expected.items():
        if key.startswith('__'):
            continue
        result = getattr(tag, key)
        fmt_string = 'field "%s": got %s (%s) expected %s (%s)!'
        fmt_values = (key, repr(result), type(result), repr(expected_val), type(expected_val))
        if key == 'duration' and result is not None and expected_val is not None:
            # allow duration to be off by 100 ms and a maximum of 1%
            if abs(result - expected_val) < 0.100:
                if expected_val and min(result, expected_val) / max(result, expected_val) > 0.99:
                    continue
        assert result == expected_val, fmt_string % fmt_values
    # for custom samples, allow not specifying all values
    if expected.get('_do_not_require_all_values'):
        return
    undefined_in_fixture = {}
    for key, val in tag.__dict__.items():
        if key.startswith('_') or val is None:
            continue
        if key not in expected:
            undefined_in_fixture[key] = val
    assert not undefined_in_fixture, 'Missing data in fixture \n%s' % str(undefined_in_fixture)
#
# def test_generator():
#     for testfile, expected in testfiles.items():
#         yield get_info, testfile, expected


def test_pathlib_compatibility():
    try:
        import pathlib
    except ImportError:
        return
    testfile = next(iter(testfiles.keys()))
    filename = pathlib.Path(testfolder) / testfile
    TinyTag.get(filename)


@pytest.mark.skipif(sys.platform == "win32", reason='Windows does not support binary paths')
def test_binary_path_compatibility():
    binary_file_path = os.path.join(os.path.dirname(__file__).encode('utf-8'), b'\x01.mp3')
    testfile = os.path.join(testfolder, next(iter(testfiles.keys())))
    shutil.copy(testfile, binary_file_path)
    assert os.path.exists(binary_file_path)
    TinyTag.get(binary_file_path)
    os.unlink(binary_file_path)
    assert not os.path.exists(binary_file_path)


@pytest.mark.xfail(raises=TinyTagException)
def test_unsupported_extension():
    bogus_file = os.path.join(testfolder, 'samples/there_is_no_such_ext.bogus')
    TinyTag.get(bogus_file)


def test_override_encoding():
    chinese_id3 = os.path.join(testfolder, 'samples/chinese_id3.mp3')
    tag = TinyTag.get(chinese_id3, encoding='gbk')
    assert tag.artist == '苏云'
    assert tag.album == '角落之歌'


@pytest.mark.xfail(raises=NotImplementedError)
def test_unsubclassed_tinytag_duration():
    tag = TinyTag(None, 0)
    tag._determine_duration(None)


@pytest.mark.xfail(raises=NotImplementedError)
def test_unsubclassed_tinytag_parse_tag():
    tag = TinyTag(None, 0)
    tag._parse_tag(None)


def test_mp3_length_estimation():
    ID3.set_estimation_precision(0.7)
    tag = TinyTag.get(os.path.join(testfolder, 'samples/silence-44-s-v1.mp3'))
    assert 3.5 < tag.duration < 4.0


@pytest.mark.xfail(raises=TinyTagException)
def test_unexpected_eof():
    ID3.get(os.path.join(testfolder, 'samples/incomplete.mp3'))


@pytest.mark.xfail(raises=TinyTagException)
def test_invalid_flac_file():
    Flac.get(os.path.join(testfolder, 'samples/silence-44-s-v1.mp3'))


@pytest.mark.xfail(raises=TinyTagException)
def test_invalid_mp3_file():
    ID3.get(os.path.join(testfolder, 'samples/flac1.5sStereo.flac'))


@pytest.mark.xfail(raises=TinyTagException)
def test_invalid_ogg_file():
    Ogg.get(os.path.join(testfolder, 'samples/flac1.5sStereo.flac'))


@pytest.mark.xfail(raises=TinyTagException)
def test_invalid_wave_file():
    Wave.get(os.path.join(testfolder, 'samples/flac1.5sStereo.flac'))


@pytest.mark.xfail(raises=TinyTagException)
def test_invalid_aiff_file():
    Aiff.get(os.path.join(testfolder, 'samples/ilbm.aiff'))


def test_unpad():
    # make sure that unpad only removes trailing 0-bytes
    assert TinyTag._unpad('foo\x00') == 'foo'
    assert TinyTag._unpad('foo\x00bar\x00') == 'foobar'


def test_mp3_image_loading():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/cover_img.mp3'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 140000 < len(image_data) < 150000, ('Image is %d bytes but should be around 145kb' %
                                               len(image_data))
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), ('The image data must start with a jpeg '
                                                        'header')


def test_mp3_id3v22_image_loading():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/id3v22_image.mp3'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 18000 < len(image_data) < 19000, ('Image is %d bytes but should be around 18.1kb' %
                                             len(image_data))
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), ('The image data must start with a jpeg '
                                                        'header')


def test_mp3_image_loading_without_description():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/id3image_without_description.mp3'),
                      image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 28600 < len(image_data) < 28700, ('Image is %d bytes but should be around 28.6kb' %
                                             len(image_data))
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), ('The image data must start with a jpeg '
                                                        'header')


def test_mp3_image_loading_with_utf8_description():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/image-text-encoding.mp3'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 5700 < len(image_data) < 6000, ('Image is %d bytes but should be around 6kb' %
                                           len(image_data))
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), ('The image data must start with a jpeg '
                                                        'header')


def test_mp3_image_loading2():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/12oz.mp3'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 2000 < len(image_data) < 2500, ('Image is %d bytes but should be around 145kb' %
                                           len(image_data))
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), ('The image data must start with a jpeg '
                                                        'header')


def test_mp3_utf_8_invalid_string_raises_exception():
    with raises(TinyTagException):
        TinyTag.get(os.path.join(testfolder, 'samples/utf-8-id3v2-invalid-string.mp3'))


def test_mp3_utf_8_invalid_string_can_be_ignored():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/utf-8-id3v2-invalid-string.mp3'),
                      ignore_errors=True)
    # the title used to be Gran dia, but I replaced the first byte with 0xFF,
    # which should be ignored here
    assert tag.title == 'ran día'


def test_mp4_image_loading():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/iso8859_with_image.m4a'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 20000 < len(image_data) < 25000, ('Image is %d bytes but should be around 22kb' %
                                             len(image_data))
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), ('The image data must start with a jpeg '
                                                        'header')


def test_flac_image_loading():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/flac_with_image.flac'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 70000 < len(image_data) < 80000, ('Image is %d bytes but should be around 75kb' %
                                             len(image_data))
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), ('The image data must start with a jpeg '
                                                        'header')


def test_aiff_image_loading():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/test_with_image.aiff'), image=True)
    image_data = tag.get_image()
    assert image_data is not None
    assert 15000 < len(image_data) < 25000, ('Image is %d bytes but should be around 20kb' %
                                             len(image_data))
    assert image_data.startswith(b'\xff\xd8\xff\xe0'), ('The image data must start with a jpeg '
                                                        'header')


@pytest.mark.parametrize("testfile,expected", [
    pytest.param(testfile, expected) for testfile, expected in [
        ('samples/detect_mp3_id3.x', ID3),
        ('samples/detect_mp3_fffb.x', ID3),
        ('samples/detect_ogg.x', Ogg),
        ('samples/detect_wav.x', Wave),
        ('samples/detect_flac.x', Flac),
        ('samples/detect_wma.x', Wma),
        ('samples/detect_mp4_m4a.x', MP4),
        ('samples/detect_aiff.x', Aiff),
    ]
])
def test_detect_magic_headers(testfile, expected):
    filename = os.path.join(testfolder, testfile)
    with io.open(filename, 'rb') as fh:
        parser = TinyTag.get_parser_class(filename, fh)
    assert parser == expected


def test_show_hint_for_wrong_usage():
    with pytest.raises(Exception) as exc_info:
        TinyTag('filename.mp3', 0)
    assert exc_info.type == Exception
    assert exc_info.value.args[0] == 'Use `TinyTag.get(filepath)` instead of `TinyTag(filepath)`'


def test_to_str():
    tag = TinyTag.get(os.path.join(testfolder, 'samples/id3v22-test.mp3'))
    assert str(tag)  # since the dict is not ordered we cannot == 'somestring'
    assert repr(tag)  # since the dict is not ordered we cannot == 'somestring'
    assert str(tag) == (
        '{"album": "Hymns for the Exiled", "albumartist": null, "artist": "Anais Mitchell", '
        '"audio_offset": 2225, "bitrate": 160.0, "channels": 2, "comment": "Waterbug Records, '
        'www.anaismitchell.com", "composer": null, "disc": null, "disc_total": null, '
        '"duration": 0.13836297152858082, "extra": {}, "filesize": 5120, "genre": null, '
        '"samplerate": 44100, "title": "cosmic american", "track": "3", "track_total": "11", '
        '"year": "2004"}')
