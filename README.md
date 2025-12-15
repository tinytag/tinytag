<!--
  SPDX-FileCopyrightText: 2014-2024 tinytag Contributors
  SPDX-License-Identifier: MIT
-->

# tinytag 

tinytag is a Python library for reading audio file metadata

[![Build Status](https://img.shields.io/github/actions/workflow/status/tinytag/tinytag/tests.yml
)](https://github.com/tinytag/tinytag/actions?query=workflow:%22Tests%22)
[![PyPI Version](https://img.shields.io/pypi/v/tinytag
)](https://pypi.org/project/tinytag/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/tinytag
)](https://pypistats.org/packages/tinytag)


## Install

```
python3 -m pip install tinytag
```


## Features

  * Read tags, images and properties of audio files
  * Supported formats:
    * MP3 / MP2 / MP1 (ID3 v1, v1.1, v2.2, v2.3+)
    * M4A (AAC / ALAC)
    * WAVE / WAV
    * OGG (FLAC / Opus / Speex / Vorbis)
    * FLAC
    * WMA
    * AIFF / AIFF-C
  * Same API for all formats
  * Small, portable library
  * High code coverage
  * Pure Python, no dependencies
  * Supports Python 3.7 or higher

> [!IMPORTANT]  
> Support for changing/writing metadata will not be added. Use another library
> such as [Mutagen](https://mutagen.readthedocs.io/) for this.


## Usage

tinytag only provides the minimum needed for _reading_ metadata, and presents
it in a simple format. It can determine track number, total tracks, title,
artist, album, year, duration and more.

```python
from tinytag import TinyTag
tag: TinyTag = TinyTag.get('/some/music.mp3')

print(f'This track is by {tag.artist}.')
print(f'It is {tag.duration:.2f} seconds long.')
```

> [!WARNING]  
> The `ignore_errors` parameter of `TinyTag.get()` is obsolete as of tinytag
> 2.0.0, and will be removed in the future.

Alternatively you can use tinytag directly on the command line:

    $ python3 -m tinytag /some/music.mp3
    {
      "filename": "/some/music.mp3",
      "filesize": 3243226,
      "duration": 173.52,
      "channels": 2,
      "bitrate": 128,
      "samplerate": 44100,
      "artist": [
        "artist name"
      ],
      "album": [
        "album name"
      ],
      "title": [
        "track name"
      ],
      "track": 4,
      "genre": [
        "Jazz"
      ],
      "year": [
        "2010"
      ],
      "comment": [
        "Some comment here"
      ]
    }

Check `python3 -m tinytag --help` for all CLI options, for example other
output formats.

### Supported Files

To receive a tuple of file extensions tinytag supports, use the
`SUPPORTED_FILE_EXTENSIONS` constant:

```python
TinyTag.SUPPORTED_FILE_EXTENSIONS
```

Alternatively, check if a file is supported by providing its path:

```python
is_supported = TinyTag.is_supported('/some/music.mp3')
```

### Common Metadata

tinytag provides some common attributes, which always contain a single value.
These are helpful when you need quick access to common metadata.

#### File/Audio Properties

    tag.bitdepth      # bit depth as integer (for lossless audio)
    tag.bitrate       # bitrate in kBits/s as float
    tag.duration      # audio duration in seconds as float
    tag.filename      # filename as string
    tag.filesize      # file size in bytes as integer
    tag.samplerate    # samples per second as integer

> [!WARNING]  
> The `tag.audio_offset` attribute is obsolete as of tinytag 2.0.0, and will
> be removed in the future.

#### Metadata Fields

    tag.album         # album as string
    tag.albumartist   # album artist as string
    tag.artist        # artist name as string
    tag.comment       # file comment as string
    tag.composer      # composer as string
    tag.disc          # disc number as integer
    tag.disc_total    # total number of discs as integer
    tag.genre         # genre as string
    tag.title         # title of the song as string
    tag.track         # track number as integer
    tag.track_total   # total number of tracks as integer
    tag.year          # year or date as string

### Additional Metadata

For additional values of the same field type, uncommon metadata fields, or
metadata specific to certain file formats, use `other`:

    tag.other         # a dictionary of additional fields

> [!WARNING]  
> The `other` dictionary has replaced the `extra` dictionary in tinytag 2.0.0.
> The latter will be removed in a future release.

The following `other` field names are standardized in tinytag, and optionally
present when files provide such metadata:

    barcode
    bpm
    catalog_number
    conductor
    copyright
    director
    encoded_by
    encoder_settings
    grouping
    initial_key
    isrc
    language
    license
    lyricist
    lyrics
    media
    movement
    movement_name
    movement_total
    publisher
    set_subtitle
    show_movement
    url
    work

Additional `other` field names not documented above may be present, but are
format-specific and may change or disappear in future tinytag releases. If
tinytag does not expose metadata you need, or you wish to standardize more
field names, open a feature request on GitHub for discussion.

`other` values are always provided as strings, and are not guaranteed to be
valid. Should e.g. the `bpm` value in the file contain non-numeric characters,
tinytag will provide the string as-is. It is your responsibility to handle
possible exceptions, e.g. when converting the value to an integer.

Multiple values of the same field type are provided if a file contains them.
Values are always provided as a list, even when only a single value exists.

Example:

```python
from tinytag import OtherFields, TinyTag

tag: TinyTag = TinyTag.get('/some/music.mp3')
other_fields: OtherFields = tag.other
catalog_numbers: list[str] | None = other_fields.get('catalog_number')

if catalog_numbers:
    catalog_number: str = catalog_numbers[0]
    print(catalog_number)

print(catalog_numbers)
```

Output:

    > 10
    > ['10']

When a file contains multiple values for a [common metadata field](#common-metadata)
(e.g. `artist`), the primary value is accessed through the common attribute
(`tag.artist`), and any additional values through the `other` dictionary
(`tag.other['artist']`).

Example:

```python
from tinytag import TinyTag

tag: TinyTag = TinyTag.get('/some/music.mp3')
artist: str | None = tag.artist
additional_artists: list[str] | None = tag.other.get('artist')

print(artist)
print(additional_artists)
```

Output:

    > main artist
    > ['another artist', 'yet another artist']

### All Metadata

If you need to receive all available metadata as key-value pairs in a flat
dictionary, use the `as_dict()` method. This combines the common attributes
and `other` dictionary, which can be more convenient in some cases.

    from tinytag import TinyTag

    tag: TinyTag = TinyTag.get('/some/music.mp3')
    metadata: dict = tag.as_dict()

### Images

Additionally, you can also read embedded images by passing a `image=True`
keyword argument to `TinyTag.get()`.

If you need to receive an image of a specific kind, including its description,
use `images`:

    tag.images        # available embedded images

The following common image attributes are available, providing the first
located image of each kind:

    tag.images.front_cover  # front cover as 'Image' object
    tag.images.back_cover   # back cover as 'Image' object
    tag.images.media        # media (e.g. CD label) as 'Image' object

When present, any additional images are available in an `images.other`
dictionary, using the following standardized key names:

    generic
    icon
    alt_icon
    front_cover
    back_cover
    media
    leaflet
    lead_artist
    artist
    conductor
    band
    composer
    lyricist
    recording_location
    during_recording
    during_performance
    screen_capture
    bright_colored_fish
    illustration
    band_logo
    publisher_logo
    unknown

Provided values are always lists containing at least one `Image` object.

The `Image` object provides the following attributes:

    data           # image data as bytes
    name           # image name/kind as string
    mime_type      # image MIME type as string
    description    # image description as string

To receive any available image, prioritizing the front cover, use `images.any`:

```python
from tinytag import Image, TinyTag

tag: TinyTag = TinyTag.get('/some/music.ogg', image=True)
image: Image | None = tag.images.any

if image is not None:
    data: bytes = image.data
    name: str = image.name
    mime_type: str = image.mime_type
    description: str = image.description

    print(len(data))
    print(name)
    print(mime_type)
    print(description)
```

Output:

    > 74452
    > front_cover
    > image/jpeg
    > some image description

> [!WARNING]  
> `tag.images.any` has replaced `tag.get_image()` in tinytag 2.0.0.
> `tag.get_image()` will be removed in the future.

To receive a common image, e.g. `front_cover`:

```python
from tinytag import Image, Images, TinyTag

tag: TinyTag = TinyTag.get('/some/music.ogg', image=True)
images: Images = tag.images
cover_image: Image = images.front_cover

if cover_image is not None:
    data: bytes = cover_image.data
    description: str = cover_image.description
```

To receive an additional image, e.g. `bright_colored_fish`:

```python
from tinytag import Image, OtherImages, TinyTag

tag: TinyTag = TinyTag.get('/some/music.ogg', image=True)
other_images: OtherImages = tag.images.other
fish_images: list[Image] | None = other_images.get('bright_colored_fish')

if fish_images:
    image = fish_images[0]  # Use first image
    data = image.data
    description = image.description
```

### Encoding

To open files using a specific encoding, you can use the `encoding` parameter.
This parameter is however only used for formats where the encoding is not
explicitly specified.

```python
TinyTag.get('a_file_with_gbk_encoding.mp3', encoding='gbk')
```

### File-like Objects

To use a file-like object (e.g. BytesIO) instead of a file path, pass a
`file_obj` keyword argument:

```python
TinyTag.get(file_obj=your_file_obj)
```

### Exceptions

    TinyTagException        # Base class for exceptions
    ParseError              # Parsing an audio file failed
    UnsupportedFormatError  # File format is not supported


## Changelog

### 2.2.0  (2025-12-15)

- Add support for movement, work and grouping fields
- ID3: Make synced lyrics available in 'other.lyrics' (LRC format)
- ID3: Continue reading after encountering empty frame
- ID3: Fix frame reading when image parsing is disabled
- ID3: Exclude more frames containing binary data
- ID3: Avoid unnecessary string decoding
- M4A: Support extended atom sizes
- M4A: Ensure all field names are lowercase
- OGG: Stop reading after reaching EOS page
- Vorbis: Map UNSYNCEDLYRICS field to other.lyrics

### 2.1.2  (2025-08-14)

- M4A: Add a few missing additional metadata fields
- M4A: Support '©com' composer atom
- M4A: Fix reading of multi-value custom fields
- M4A: Use correct encoding when reading data names
- ID3: Don't read entire file to determine duration
- ID3: Skip stray null byte before image data
- Add missing `__version__` attribute
- Avoid some unnecessary work in hot code paths
- Improve a few incomplete type hints

### 2.1.1  (2025-04-23)

- ID3: Stop removing 'b' character from strings
- Port unit tests from pytest to built-in unittest module

### 2.1.0  (2025-02-23)

- Opus: Calculate audio bitrate
- Opus: Take pre-skip into account when calculating the duration

### 2.0.0  (2024-11-03)

- **BREAKING:** Store 'disc', 'disc_total', 'track' and 'track_total' values as int instead of str
- **BREAKING:** 'as_dict()' method (previously undocumented) returns tag field values in list form
- **BREAKING:** TinyTagException no longer inherits LookupError
- **BREAKING:** TinyTag subclasses are now private
- **BREAKING:** Remove function to use custom audio file samples in tests
- **BREAKING:** Remove support for Python 2
- **DEPRECATION:** Mark 'ignore_errors' parameter for TinyTag.get() as obsolete
- **DEPRECATION:** Mark 'audio_offset' attribute as obsolete
- **DEPRECATION:** Deprecate 'extra' dict in favor of 'other' dict with values in list form
- **DEPRECATION:** Deprecate 'get_image()' method in favor of 'images.any' property
- Add type hints to codebase
- Provide access to custom metadata fields through the 'other' dict
- Provide access to all available images
- Add more standard 'other' fields
- Use Flit as Python build backend instead of Setuptools
- ID3: Fix invalid sample rate/duration in some cases
- ID3: Fix reading of UTF-16 strings without BOM
- FLAC: Apply ID3 tags after Vorbis
- OGG/WMA: Set missing 'channels' field
- WMA: Set missing 'other.copyright' field
- WMA: Raise exception if file is invalid
- Various optimizations

### 1.10.1  (2023-10-26)

- Update 'extra' fields with data from other tags #188
- ID3: Add missing 'extra.copyright' field

### 1.10.0  (2023-10-18)

- Add support for OGG FLAC format #182
- Add support for OGG Speex format #181
- Wave: support image loading
- Add support for file-like objects (BytesIO) #178
- Add list of supported file extensions #177
- Fix deprecations related to setuptools #176
- Fix pathlib support in TinyTag.is_supported()
- Only remove zero bytes at the end of strings
- Stricter conditions in while loops
- OGG: Add stricter magic byte matching for OGG files
- Compatibility with Python 3.4 and 3.5 is no longer tested

### 1.9.0  (2023-04-23)

- Add bitdepth attribute for lossless audio #157
- Add recognition of Audible formats #163 (thanks to snowskeleton)
- Add .m4v to list of supported file extensions #142
- Aiff: Implement replacement for Python's aifc module #164
- ID3: Only check for language in COMM and USLT frames #147
- ID3: Read the correct number of bytes from Xing header #154
- ID3: Add support for ID3v2.4 TDRC frame #156 (thanks to Uninen)
- M4A: Add description fields #168 (thanks to snowskeleton)
- RIFF: Handle tags containing extra zero-byte #141
- Vorbis: Parse OGG cover art #144 (thanks to Pseurae)
- Vorbis: Support standard disctotal/tracktotal comments #171
- Wave: Add proper support for padded IFF chunks

### 1.8.1  (2022-03-12) [still mathiascode-edition]

- MP3 ID3: Set correct file position if tag reading is disabled #119 (thanks to mathiascode)
- MP3: Fix incorrect calculation of duration for VBR encoded MP3s #128 (thanks to mathiascode)

### 1.8.0  (2022-03-05) [mathiascode-edition]

- Add support for ALAC audio files #130 (thanks to mathiascode)
- AIFF: Fixed bitrate calculation for certain files #129 (thanks to mathiascode)
- MP3: Do not round MP3 bitrates #131 (thanks to mathiascode)
- MP3 ID3: Support any language in COMM and USLT frames #135 (thanks to mathiascode)
- Performance: Don't use regex when parsing genre #136 (thanks to mathiascode)
- Disable tag parsing for all formats when requested #137 (thanks to mathiascode)
- M4A: Fix invalid bitrates in certain files #132 (thanks to mathiascode)
- WAV: Fix metadata parsing for certain files #133 (thanks to mathiascode)

### 1.7.0. (2021-12-14)

- fixed rare occasion of ID3v2 tags missing their first character, #106
- allow overriding the default encoding of ID3 tags (e.g. `TinyTag.get(..., encoding='gbk'))`)
- fixed calculation of bitrate for very short mp3 files, #99
- utf-8 support for AIFF files, #123
- fixed image parsing for id3v2 with images containing utf-16LE descriptions, #117
- fixed ID3v1 tags overwriting ID3v2 tags, #121
- Set correct file position if tag reading is disabled for ID3 (thanks to mathiascode)

### 1.6.0  (2021-08-28) [aw-edition]

- fixed handling of non-latin encoding types for images (thanks to aw-was-here)
- added support for ISRC data, available in `extra['isrc']` field (thanks to aw-was-here)
- added support for AIFF/AIFF-C (thanks to aw-was-here)
- fixed import deprecation warnings (thanks to idotobi)
- fixed exception for TinyTag misuse being different in different python versions (thanks to idotobi)
- added support for ID3 initial key tonality hint, available in `extra['initial_key']`
- added support for ID3 unsynchronized lyrics, available in `extra['lyrics']`
- added `extra` field, which may contain additional metadata not available in all file formats

### 1.5.0  (2020-11-05)

- fixed data type to always return str for disc, disc_total, track, track_total #97 (thanks to kostalski)
- fixed package install being reported as UNKNOWN for some python/pip variations #90 (thanks to russpoutine)
- Added automatic detection for certain MP4 file headers

### 1.4.0  (2020-04-23)

- detecting file types based on their magic header bytes, #85
- fixed opus duration being wrong for files with lower sample rate #81
- implemented support for binary paths #72
- always cast mp3 bitrates to int, so that CBR and VBR output behaves the sam
- made __str__ deterministic and use json as output format

### 1.3.0  (2020-03-09)

- added option to ignore encoding errors `ignore_errors` #73
- Improved text decoding for many malformed files

### 1.2.2  (2019-04-13)

- Improved stability when reading corrupted mp3 files

### 1.2.1  (2019-04-13)

- fixed wav files not correctly reporting the number of channels #61

### 1.2.0  (2019-04-13)

- using setup.cfg instead of setup.py (thanks to scivision)
- added support for calling TinyTag.get with pathlib.Path (thanks to scivision)
- added appveyor windows test CI (thanks to scivision)
- using pytest instead of nosetest (thanks to scivision)

### 1.1.0  (2019-04-13)

- added new field "composer" (Thanks to Phil Borman)

### 1.0.1  (2019-04-13)

- fixed ID3 loading for files with corrupt header (thanks to Ian Homer)
- fixed parsing of duration in wav file (thanks to Ian Homer)

### 1.0.0  (2018-12-12)

- added comment field
- added wav-riff format support
- use MP4 parser for m4b files
- added simple cli tool
- fix parsing of FLAC files with ID3 header (thanks to minus7)
- added method `TinyTag.is_supported(filename)`

### 0.19.0 (2018-02-11)

- fixed corrupted images for some mp3s (#45)

### 0.18.0 (2017-04-29)

- fixed wrong bitrate and crash when parsing xing header

### 0.17.0 (2016-10-02)

- supporting ID3v2.2 images

### 0.16.0 (2016-08-06)

- MP4 cover image support

### 0.15.2 (2016-08-06)

- fixed crash for malformed MP4 files (#34)

### 0.15.0 (2016-08-06)

- fixed decoding of UTF-16LE ID3v2 Tags, improved overall stability

### 0.14.0 (2016-06-05):

- MP4/M4A and Opus support
