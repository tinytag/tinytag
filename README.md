tinytag 
=======

tinytag is a library for reading music meta data of most common audio files in pure python

[![Build Status](https://travis-ci.org/devsnd/tinytag.png?branch=master)](https://travis-ci.org/devsnd/tinytag)
[![Build status](https://ci.appveyor.com/api/projects/status/w9y2kg97869g1edj?svg=true)](https://ci.appveyor.com/project/devsnd/tinytag)
[![Coverage Status](https://coveralls.io/repos/devsnd/tinytag/badge.svg)](https://coveralls.io/r/devsnd/tinytag)
[![PyPI version](https://badge.fury.io/py/tinytag.svg)](https://pypi.org/project/tinytag/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/tinytag.svg)](https://pypistats.org/packages/tinytag)

Install
-------

```pip install tinytag```


Features:
---------

  * Read tags, length and cover images of audio files
  * supported formats
    * MP3/MP2/MP1 (ID3 v1, v1.1, v2.2, v2.3+)
    * Wave/RIFF
    * OGG
    * OPUS
    * FLAC
    * WMA
    * MP4/M4A/M4B/M4R/ALAC
    * AIFF/AIFF-C
  * pure python, no dependencies
  * supports python 2.7 and 3.4 or higher
  * high test coverage
  * Just a few hundred lines of code (just include it in your project!) 

tinytag only provides the minimum needed for _reading_ meta-data.
It can determine track number, total tracks, title, artist, album, year, duration and any more.

    from tinytag import TinyTag
    tag = TinyTag.get('/some/music.mp3')
    print('This track is by %s.' % tag.artist)
    print('It is %f seconds long.' % tag.duration)
    
Alternatively you can use tinytag directly on the command line:

    $ python -m tinytag --format csv /some/music.mp3
    > {"filename": "/some/music.mp3", "filesize": 30212227, "album": "Album", "albumartist": "Artist", "artist": "Artist", "audio_offset": null, "bitrate": 256, "channels": 2, "comment": null, "composer": null, "disc": "1", "disc_total": null, "duration": 10, "genre": null, "samplerate": 44100, "title": "Title", "track": "5", "track_total": null, "year": "2012"}

Check `python -m tinytag --help` for all CLI options, for example other output formats

List of possible attributes you can get with TinyTag:

    tag.album         # album as string
    tag.albumartist   # album artist as string
    tag.artist        # artist name as string
    tag.audio_offset  # number of bytes before audio data begins
    tag.bitrate       # bitrate in kBits/s
    tag.comment       # file comment as string
    tag.composer      # composer as string 
    tag.disc          # disc number
    tag.disc_total    # the total number of discs
    tag.duration      # duration of the song in seconds
    tag.filesize      # file size in bytes
    tag.genre         # genre as string
    tag.samplerate    # samples per second
    tag.title         # title of the song
    tag.track         # track number as string
    tag.track_total   # total number of tracks as string
    tag.year          # year or data as string

For non-common fields and fields specific to single file formats use extra

    tag.extra         # a dict of additional data

The `extra` dict currently *may* contain the following data:
   `url`, `isrc`, `text`, `initial_key`, `lyrics`, `copyright`

Aditionally you can also get cover images from ID3 tags:

    tag = TinyTag.get('/some/music.mp3', image=True)
    image_data = tag.get_image()

To open files using a specific encoding, you can use the `encoding` parameter.
This parameter is however only used for formats where the encoding isn't explicitly
specified.

    TinyTag.get('a_file_with_gbk_encoding.mp3', encoding='gbk')

Changelog:
 * 1.8.1  (2022-03-12) [still mathiascode-edition]
   - MP3 ID3: Set correct file position if tag reading is disabled #119 (thanks to mathiascode)
   - MP3: Fix incorrect calculation of duration for VBR encoded MP3s #128 (thanks to mathiascode)
 * 1.8.0  (2022-03-05) [mathiascode-edition]
   - Add support for ALAC audio files #130 (thanks to mathiascode)
   - AIFF: Fixed bitrate calculation for certain files #129 (thanks to mathiascode)
   - MP3: Do not round MP3 bitrates #131 (thanks to mathiascode)
   - MP3 ID3: Support any language in COMM and USLT frames #135 (thanks to mathiascode)
   - Performance: Don't use regex when parsing genre #136 (thanks to mathiascode)
   - Disable tag parsing for all formats when requested #137 (thanks to mathiascode)
   - M4A: Fix invalid bitrates in certain files #132 (thanks to mathiascode)
   - WAV: Fix metadata parsing for certain files #133 (thanks to mathiascode)
 * 1.7.0. (2021-12-14)
   - fixed rare occasion of ID3v2 tags missing their first character, #106
   - allow overriding the default encoding of ID3 tags (e.g. `TinyTag.get(..., encoding='gbk'))`)
   - fixed calculation of bitrate for very short mp3 files, #99
   - utf-8 support for AIFF files, #123
   - fixed image parsing for id3v2 with images containing utf-16LE descriptions, #117
   - fixed ID3v1 tags overwriting ID3v2 tags, #121
   - Set correct file position if tag reading is disabled for ID3 (thanks to mathiascode)
 * 1.6.0  (2021-08-28) [aw-edition]:
   - fixed handling of non-latin encoding types for images (thanks to aw-was-here)
   - added support for ISRC data, available in `extra['isrc']` field (thanks to aw-was-here)
   - added support for AIFF/AIFF-C (thanks to aw-was-here)
   - fixed import deprecation warnings (thanks to idotobi)
   - fixed exception for TinyTag misuse being different in different python versions (thanks to idotobi)
   - added support for ID3 initial key tonality hint, available in `extra['initial_key']`
   - added support for ID3 unsynchronized lyrics, available in `extra['lyrics']`
   - added `extra` field, which may contain additional metadata not available in all file formats
 * 1.5.0  (2020-11-05):
   - fixed data type to always return str for disc, disc_total, track, track_total #97 (thanks to kostalski)
   - fixed package install being reported as UNKNOWN for some python/pip variations #90 (thanks to russpoutine)
   - Added automatic detection for certain MP4 file headers
 * 1.4.0  (2020-04-23):
   - detecting file types based on their magic header bytes, #85
   - fixed opus duration being wrong for files with lower sample rate #81
   - implemented support for binary paths #72
   - always cast mp3 bitrates to int, so that CBR and VBR output behaves the sam
   - made __str__ deterministic and use json as output format
 * 1.3.0  (2020-03-09):
   - added option to ignore encoding errors `ignore_errors` #73
   - Improved text decoding for many malformed files
 * 1.2.2  (2019-04-13):
   - Improved stability when reading corrupted mp3 files
 * 1.2.1  (2019-04-13):
   - fixed wav files not correctly reporting the number of channels #61
 * 1.2.0  (2019-04-13):
   - using setup.cfg instead of setup.py (thanks to scivision)
   - added support for calling TinyTag.get with pathlib.Path (thanks to scivision)
   - added appveyor windows test CI (thanks to scivision)
   - using pytest instead of nosetest (thanks to scivision)
 * 1.1.0  (2019-04-13):
   - added new field "composer" (Thanks to Phil Borman)
 * 1.0.1  (2019-04-13):
   - fixed ID3 loading for files with corrupt header (thanks to Ian Homer)
   - fixed parsing of duration in wav file (thanks to Ian Homer)
 * 1.0.0  (2018-12-12):
   - added comment field
   - added wav-riff format support
   - use MP4 parser for m4b files
   - added simple cli tool
   - fix parsing of FLAC files with ID3 header (thanks to minus7)
   - added method `TinyTag.is_supported(filename)`
 * 0.19.0 (2018-02-11):
   - fixed corrupted images for some mp3s (#45)
 * 0.18.0 (2017-04-29):
   - fixed wrong bitrate and crash when parsing xing header
 * 0.17.0 (2016-10-02):
   - supporting ID3v2.2 images
 * 0.16.0 (2016-08-06):
   - MP4 cover image support
 * 0.15.2 (2016-08-06):
   - fixed crash for malformed MP4 files (#34)
 * 0.15.0 (2016-08-06):
   - fixed decoding of UTF-16LE ID3v2 Tags, improved overall stability
 * 0.14.0 (2016-06-05):
   - MP4/M4A and Opus support
