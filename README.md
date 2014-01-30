tinytag 
=======

tinytag is a library for reading music meta data of MP3 and OGG files with python

[![Build Status](https://travis-ci.org/devsnd/tinytag.png?branch=master)](https://travis-ci.org/devsnd/tinytag)

Features:
  * Read tags and length of music files
  * supports MP3 (ID3 v1, v1.1, v2.2, v2.3+) and OGG
  * pure python
  * supports python 2 and 3
  * is tested 
  * Under 300 lines of code (just include it in your project!) 

tinytag only provides the minimum needed for _reading_ MP3 and OGG meta-data.
It can determine track number, total tracks, title, artist, album, year and length in seconds.

    from tinytag import TinyTag
    info = TinyTag.get('/some/music.mp3')
    print('This track is by %s.' % info.artist)
    print('It is %f seconds long.' % info.length)

supported python versions:

 * 2.6
 * 2.7
 * 3.2
 * 3.3
 * pypy

and possibly more.
