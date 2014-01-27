tinytag
=======

Read ID3 tags and length of MP3 files with python 2 or 3
------------------

tinytag only provides the minimum needed for _reading_ MP3 meta-data in 
pure python 2 or 3.

    from tinytag import TinyTag
    info = TinyTag.get('/some/music.mp3')
    print('This track is by %s.' % info.artist)
    print('It is %d milliseconds long.' % info.length)