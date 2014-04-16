tinytag 
=======

tinytag is a library for reading music meta data of MP3, OGG, FLAC and Wave files with python

[![Build Status](https://travis-ci.org/devsnd/tinytag.png?branch=master)](https://travis-ci.org/devsnd/tinytag)
[![Coverage Status](https://coveralls.io/repos/devsnd/tinytag/badge.png)](https://coveralls.io/r/devsnd/tinytag)

Features:
  * Read tags and length of music files
  * supported formats
    * MP3 (ID3 v1, v1.1, v2.2, v2.3+)
    * Wave
    * OGG
    * FLAC
  * pure python
  * supports python 2 and 3 (without 2to3)
  * is tested 
  * Just a few hundred lines of code (just include it in your project!) 

tinytag only provides the minimum needed for _reading_ MP3, OGG, FLAC and Wave meta-data.
It can determine track number, total tracks, title, artist, album, year, duration and more.

    from tinytag import TinyTag
    tag = TinyTag.get('/some/music.mp3')
    print('This track is by %s.' % tag.artist)
    print('It is %f seconds long.' % tag.duration)

List of possible attributes you can get with TinyTag:

    tag.album         # album as string
    tag.artist        # artist name as string
    tag.audio_offset  # number of bytes before audio data begins
    tag.bitrate       # bitrate in kBits/s
    tag.duration      # duration of the song in seconds
    tag.filesize      # file size in bytes
    tag.samplerate    # samples per second
    tag.title         # title of the song
    tag.track         # track number as string
    tag.track_total   # total number of tracks as string
    tag.year          # year or data as string

supported python versions:

 * 2.6
 * 2.7
 * 3.2
 * 3.3
 * pypy

and possibly more.
