# tinytag - an audio file metadata reader
# Copyright (c) 2014-2023 Tom Wallroth
# Copyright (c) 2021-2024 Mat (mathiascode)
#
# Sources on GitHub:
# http://github.com/tinytag/tinytag

# MIT License

# Copyright (c) 2014-2024 Tom Wallroth, Mat (mathiascode)

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Audio file metadata reader"""


from __future__ import annotations
from binascii import a2b_base64
from io import BytesIO
from os import PathLike, SEEK_CUR, SEEK_END, SEEK_SET, environ, fsdecode
from struct import unpack
from sys import stderr

# Lazy imports for type checking
if False:  # pylint: disable=using-constant-test
    from collections.abc import Callable, Iterator
    from typing import Any, BinaryIO, Dict, List

    _Extra = Dict[str, List[str]]
    _ImagesExtra = Dict[str, List["Image"]]
else:
    _Extra = _ImagesExtra = dict


DEBUG = bool(environ.get('TINYTAG_DEBUG'))  # some of the parsers can print debug info


class TinyTagException(Exception):
    """Base class for exceptions."""


class ParseError(TinyTagException):
    """Parsing an audio file failed."""


class UnsupportedFormatError(TinyTagException):
    """File format is not supported."""


class TinyTag:
    """A class containing audio file metadata."""

    SUPPORTED_FILE_EXTENSIONS = (
        '.mp1', '.mp2', '.mp3',
        '.oga', '.ogg', '.opus', '.spx',
        '.wav', '.flac', '.wma',
        '.m4b', '.m4a', '.m4r', '.m4v', '.mp4', '.aax', '.aaxc',
        '.aiff', '.aifc', '.aif', '.afc'
    )
    _EXTRA_PREFIX = 'extra.'
    _file_extension_mapping: dict[tuple[str, ...], type[TinyTag]] | None = None
    _magic_bytes_mapping: dict[bytes, type[TinyTag]] | None = None

    def __init__(self) -> None:
        self.filename: bytes | str | PathLike[Any] | None = None
        self.filesize = 0
        self.duration: float | None = None
        self.channels: int | None = None
        self.bitrate: float | None = None
        self.bitdepth: int | None = None
        self.samplerate: int | None = None
        self.artist: str | None = None
        self.albumartist: str | None = None
        self.composer: str | None = None
        self.album: str | None = None
        self.disc: int | None = None
        self.disc_total: int | None = None
        self.title: str | None = None
        self.track: int | None = None
        self.track_total: int | None = None
        self.genre: str | None = None
        self.year: str | None = None
        self.comment: str | None = None
        self.extra = Extra()
        self.images = Images()
        self._filehandler: BinaryIO | None = None
        self._default_encoding: str | None = None  # allow override for some file formats
        self._parse_duration = True
        self._parse_tags = True
        self._load_image = False
        self._tags_parsed = False
        self.__dict__: dict[str, str | int | float | Extra | Images]

    def __repr__(self) -> str:
        return str({key: value for key, value in self.__dict__.items() if not key.startswith('_')})

    @classmethod
    def get(cls,
            filename: bytes | str | PathLike[Any] | None = None,
            tags: bool = True,
            duration: bool = True,
            image: bool = False,
            encoding: str | None = None,
            file_obj: BinaryIO | None = None,
            **kwargs: Any) -> TinyTag:
        """Return a tag object for an audio file."""
        should_close_file = file_obj is None
        if filename and should_close_file:
            file_obj = open(filename, 'rb')  # pylint: disable=consider-using-with
        if file_obj is None:
            raise ValueError('Either filename or file_obj argument is required')
        if 'ignore_errors' in kwargs:
            from warnings import warn  # pylint: disable=import-outside-toplevel
            warn('ignore_errors argument is obsolete, and will be removed in a future '
                 '2.x release', DeprecationWarning, stacklevel=2)
        try:
            file_obj.seek(0, SEEK_END)
            filesize = file_obj.tell()
            file_obj.seek(0)
            parser_class = cls._get_parser_class(filename, file_obj)
            tag = parser_class()
            tag._filehandler = file_obj
            tag._default_encoding = encoding
            tag.filename = filename
            tag.filesize = filesize
            if filesize > 0:
                try:
                    tag._load(tags=tags, duration=duration, image=image)
                except Exception as exc:
                    raise ParseError(exc) from exc
            return tag
        finally:
            if should_close_file:
                file_obj.close()

    @classmethod
    def is_supported(cls, filename: bytes | str | PathLike[Any]) -> bool:
        """Check if a specific file is supported based on its file extension."""
        return cls._get_parser_for_filename(filename) is not None

    def as_dict(self) -> dict[str, str | int | float | list[str] | dict[str, list[Image]]]:
        """Return a flat dictionary representation of available metadata."""
        fields: dict[str, str | int | float | list[str] | dict[str, list[Image]]] = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, Images):
                fields[key] = value.as_dict()
                continue
            if not isinstance(value, Extra):
                if value is None:
                    continue
                if key != 'filename' and isinstance(value, str):
                    fields[key] = [value]
                else:
                    fields[key] = value
                continue
            for extra_key, extra_values in value.items():
                extra_fields = fields.get(extra_key)
                if not isinstance(extra_fields, list):
                    extra_fields = fields[extra_key] = []
                extra_fields += extra_values
        return fields

    @classmethod
    def _get_parser_for_filename(
            cls, filename: bytes | str | PathLike[Any]) -> type[TinyTag] | None:
        if cls._file_extension_mapping is None:
            cls._file_extension_mapping = {
                ('.mp1', '.mp2', '.mp3'): _ID3,
                ('.oga', '.ogg', '.opus', '.spx'): _Ogg,
                ('.wav',): _Wave,
                ('.flac',): _Flac,
                ('.wma',): _Wma,
                ('.m4b', '.m4a', '.m4r', '.m4v', '.mp4', '.aax', '.aaxc'): _MP4,
                ('.aiff', '.aifc', '.aif', '.afc'): _Aiff,
            }
        filename = fsdecode(filename).lower()
        for ext, tagclass in cls._file_extension_mapping.items():
            if filename.endswith(ext):
                return tagclass
        return None

    @classmethod
    def _get_parser_for_file_handle(cls, fh: BinaryIO) -> type[TinyTag] | None:
        # https://en.wikipedia.org/wiki/List_of_file_signatures
        from re import match  # pylint: disable=import-outside-toplevel
        if cls._magic_bytes_mapping is None:
            cls._magic_bytes_mapping = {
                b'^ID3': _ID3,
                b'^\xff\xfb': _ID3,
                b'^OggS.........................FLAC': _Ogg,
                b'^OggS........................Opus': _Ogg,
                b'^OggS........................Speex': _Ogg,
                b'^OggS.........................vorbis': _Ogg,
                b'^RIFF....WAVE': _Wave,
                b'^fLaC': _Flac,
                b'^\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C': _Wma,
                b'....ftypM4A': _MP4,  # https://www.file-recovery.com/m4a-signature-format.htm
                b'....ftypaax': _MP4,  # Audible proprietary M4A container
                b'....ftypaaxc': _MP4,  # Audible proprietary M4A container
                b'\xff\xf1': _MP4,  # https://www.garykessler.net/library/file_sigs.html
                b'^FORM....AIFF': _Aiff,
                b'^FORM....AIFC': _Aiff,
            }
        header = fh.read(max(len(sig) for sig in cls._magic_bytes_mapping))
        fh.seek(0)
        for magic, parser in cls._magic_bytes_mapping.items():
            if match(magic, header):
                return parser
        return None

    @classmethod
    def _get_parser_class(cls, filename: bytes | str | PathLike[Any] | None = None,
                          filehandle: BinaryIO | None = None) -> type[TinyTag]:
        if cls != TinyTag:  # if `get` is invoked on TinyTag, find parser by ext
            return cls  # otherwise use the class on which `get` was invoked
        if filename:
            parser_class = cls._get_parser_for_filename(filename)
            if parser_class is not None:
                return parser_class
        # try determining the file type by magic byte header
        if filehandle:
            parser_class = cls._get_parser_for_file_handle(filehandle)
            if parser_class is not None:
                return parser_class
        raise UnsupportedFormatError('No tag reader found to support file type')

    def _load(self, tags: bool, duration: bool, image: bool = False) -> None:
        self._parse_tags = tags
        self._parse_duration = duration
        self._load_image = image
        if self._filehandler is None:
            return
        if tags:
            self._parse_tag(self._filehandler)
        if duration:
            if tags:  # rewind file if the tags were already parsed
                self._filehandler.seek(0)
            self._determine_duration(self._filehandler)

    def _set_field(self, fieldname: str, value: str | int | float,
                   check_conflict: bool = True) -> None:
        if fieldname.startswith(self._EXTRA_PREFIX):
            fieldname = fieldname[len(self._EXTRA_PREFIX):]
            if check_conflict and fieldname in self.__dict__:
                fieldname = '_' + fieldname
            extra_values = self.extra.get(fieldname, [])
            if not isinstance(value, str) or value in extra_values:
                return
            extra_values.append(value)
            if DEBUG:
                print(f'Setting extra field "{fieldname}" to "{extra_values!r}"')
            self.extra[fieldname] = extra_values
            return
        old_value = self.__dict__.get(fieldname)
        new_value = value
        if isinstance(new_value, str):
            # First value goes in tag, others in tag.extra
            values = new_value.split('\x00')
            for index, i_value in enumerate(values):
                if index or old_value and i_value != old_value:
                    self._set_field(self._EXTRA_PREFIX + fieldname, i_value, check_conflict=False)
                    continue
                new_value = i_value
            if old_value:
                return
        elif not new_value and old_value:
            # Prioritize non-zero integer values
            return
        if DEBUG:
            print(f'Setting field "{fieldname}" to "{new_value!r}"')
        self.__dict__[fieldname] = new_value

    def _determine_duration(self, fh: BinaryIO) -> None:
        raise NotImplementedError

    def _parse_tag(self, fh: BinaryIO) -> None:
        raise NotImplementedError

    def _update(self, other: TinyTag) -> None:
        # update the values of this tag with the values from another tag
        for key, value in other.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, Extra):
                for extra_key, extra_values in other.extra.items():
                    for extra_value in extra_values:
                        self._set_field(
                            self._EXTRA_PREFIX + extra_key, extra_value, check_conflict=False)
            elif isinstance(value, Images):
                self.images._update(value)
            elif value is not None:
                self._set_field(key, value)

    @staticmethod
    def _unpad(s: str) -> str:
        # strings in mp3 and asf *may* be terminated with a zero byte at the end
        return s.strip('\x00')

    def get_image(self) -> bytes | None:
        """Deprecated, use images.any instead."""
        from warnings import warn  # pylint: disable=import-outside-toplevel
        warn('get_image() is deprecated, and will be removed in a future 2.x release. '
             'Use images.any instead.', DeprecationWarning, stacklevel=2)
        image = self.images.any
        return image.data if image is not None else None

    @property
    def audio_offset(self) -> None:
        """Obsolete."""
        from warnings import warn  # pylint: disable=import-outside-toplevel
        warn('audio_offset attribute is obsolete, and will be '
             'removed in a future 2.x release', DeprecationWarning, stacklevel=2)


class Extra(_Extra):
    """A dictionary containing additional fields of an audio file."""


class Images:
    """A class containing images embedded in an audio file."""
    _EXTRA_PREFIX = 'extra.'

    def __init__(self) -> None:
        self.front_cover: list[Image] = []
        self.back_cover: list[Image] = []
        self.leaflet: list[Image] = []
        self.media: list[Image] = []
        self.other: list[Image] = []
        self.extra = ImagesExtra()
        self.__dict__: dict[str, list[Image] | ImagesExtra]

    def __repr__(self) -> str:
        return str({key: value for key, value in self.__dict__.items() if not key.startswith('_')})

    @property
    def any(self) -> Image | None:
        """Return a cover image.
        If not present, fall back to any other available image.
        """
        for value in self.__dict__.values():
            if isinstance(value, ImagesExtra):
                for extra_images in value.values():
                    for image in extra_images:
                        return image
                continue
            for image in value:
                return image
        return None

    def as_dict(self) -> dict[str, list[Image]]:
        """Return a flat dictionary representation of available images."""
        images: dict[str, list[Image]] = {}
        for key, value in self.__dict__.items():
            if not isinstance(value, ImagesExtra):
                if value:
                    images[key] = value
                continue
            for extra_key, extra_values in value.items():
                extra_images = images.get(extra_key)
                if not isinstance(extra_images, list):
                    extra_images = images[extra_key] = []
                extra_images += extra_values
        return images

    def _set_field(self, fieldname: str, value: Image) -> None:
        if fieldname.startswith(self._EXTRA_PREFIX):
            fieldname = fieldname[len(self._EXTRA_PREFIX):]
            extra_values = self.extra.get(fieldname, [])
            extra_values.append(value)
            if DEBUG:
                print(f'Setting extra image field "{fieldname}"')
            self.extra[fieldname] = extra_values
            return
        values = self.__dict__.get(fieldname, [])
        if isinstance(values, list):
            values.append(value)
            if DEBUG:
                print(f'Setting image field "{fieldname}"')
            self.__dict__[fieldname] = values

    def _update(self, other: Images) -> None:
        for key, value in other.__dict__.items():
            if isinstance(value, ImagesExtra):
                for extra_key, extra_values in value.items():
                    for image_extra in extra_values:
                        self._set_field(self._EXTRA_PREFIX + extra_key, image_extra)
                continue
            for image in value:
                self._set_field(key, image)


class ImagesExtra(_ImagesExtra):
    """A dictionary containing additional images embedded in an audio file."""


class Image:
    """A class representing an image embedded in an audio file."""
    def __init__(self, name: str, data: bytes, mime_type: str | None = None) -> None:
        self.name = name
        self.data = data
        self.mime_type = mime_type
        self.description: str | None = None

    def __repr__(self) -> str:
        variables = vars(self).copy()
        data = variables.get("data")
        if data is not None:
            variables["data"] = (data[:45] + b'..') if len(data) > 45 else data
        return str(variables)


class _MP4(TinyTag):
    # https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/Metadata/Metadata.html
    # https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/QTFFChap2/qtff2.html

    class _Parser:
        atom_decoder_by_type: dict[
            int, Callable[[bytes], int | str | bytes | Image]] | None = None
        _CUSTOM_FIELD_NAME_MAPPING = {
            'artists': 'artist',
            'conductor': 'extra.conductor',
            'discsubtitle': 'extra.set_subtitle',
            'initialkey': 'extra.initial_key',
            'isrc': 'extra.isrc',
            'language': 'extra.language',
            'lyricist': 'extra.lyricist',
            'media': 'extra.media',
            'website': 'extra.url',
            'originaldate': 'extra.original_date',
            'originalyear': 'extra.original_year',
            'license': 'extra.license',
            'barcode': 'extra.barcode',
            'catalognumber': 'extra.catalog_number',
        }

        @classmethod
        def _unpack_integer(cls, value: bytes, signed: bool = True) -> str:
            value_length = len(value)
            result = -1
            if value_length == 1:
                result = unpack('>b' if signed else '>B', value)[0]
            elif value_length == 2:
                result = unpack('>h' if signed else '>H', value)[0]
            elif value_length == 4:
                result = unpack('>i' if signed else '>I', value)[0]
            elif value_length == 8:
                result = unpack('>q' if signed else '>Q', value)[0]
            return str(result)

        @classmethod
        def _unpack_integer_unsigned(cls, value: bytes) -> str:
            return cls._unpack_integer(value, signed=False)

        @classmethod
        def _make_data_atom_parser(
                cls, fieldname: str) -> Callable[[bytes], dict[str, int | str | bytes | Image]]:
            def _parse_data_atom(data_atom: bytes) -> dict[str, int | str | bytes | Image]:
                data_type = unpack('>I', data_atom[:4])[0]
                if cls.atom_decoder_by_type is None:
                    # https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/Metadata/Metadata.html#//apple_ref/doc/uid/TP40000939-CH1-SW34
                    cls.atom_decoder_by_type = {
                        # 0: 'reserved'
                        1: lambda x: x.decode('utf-8', 'replace'),   # UTF-8
                        2: lambda x: x.decode('utf-16', 'replace'),  # UTF-16
                        3: lambda x: x.decode('s/jis', 'replace'),   # S/JIS
                        # 16: duration in millis
                        13: lambda x: Image('front_cover', x, 'image/jpeg'),  # JPEG
                        14: lambda x: Image('front_cover', x, 'image/png'),   # PNG
                        21: cls._unpack_integer,                    # BE Signed int
                        22: cls._unpack_integer_unsigned,           # BE Unsigned int
                        # 23: lambda x: unpack('>f', x)[0],  # BE Float32
                        # 24: lambda x: unpack('>d', x)[0],  # BE Float64
                        # 27: lambda x: x,                          # BMP
                        # 28: lambda x: x,                          # QuickTime Metadata atom
                        65: cls._unpack_integer,                    # 8-bit Signed int
                        66: cls._unpack_integer,                    # BE 16-bit Signed int
                        67: cls._unpack_integer,                    # BE 32-bit Signed int
                        74: cls._unpack_integer,                    # BE 64-bit Signed int
                        75: cls._unpack_integer_unsigned,           # 8-bit Unsigned int
                        76: cls._unpack_integer_unsigned,           # BE 16-bit Unsigned int
                        77: cls._unpack_integer_unsigned,           # BE 32-bit Unsigned int
                        78: cls._unpack_integer_unsigned,           # BE 64-bit Unsigned int
                    }
                conversion = cls.atom_decoder_by_type.get(data_type)
                if conversion is None:
                    if DEBUG:
                        print(f'Cannot convert data type: {data_type}', file=stderr)
                    return {}  # don't know how to convert data atom
                # skip header & null-bytes, convert rest
                return {fieldname: conversion(data_atom[8:])}
            return _parse_data_atom

        @classmethod
        def _make_number_parser(
                cls, fieldname1: str, fieldname2: str) -> Callable[[bytes], dict[str, int]]:
            def _(data_atom: bytes) -> dict[str, int]:
                number_data = data_atom[8:14]
                numbers = unpack('>3H', number_data)
                # for some reason the first number is always irrelevant.
                return {fieldname1: numbers[1], fieldname2: numbers[2]}
            return _

        @classmethod
        def _parse_id3v1_genre(cls, data_atom: bytes) -> dict[str, str]:
            # dunno why the genre is offset by -1 but that's how mutagen does it
            idx = unpack('>H', data_atom[8:])[0] - 1
            result = {}
            if idx < len(_ID3._ID3V1_GENRES):
                result['genre'] = _ID3._ID3V1_GENRES[idx]
            return result

        @classmethod
        def _read_extended_descriptor(cls, esds_atom: BinaryIO) -> None:
            for _i in range(4):
                if esds_atom.read(1) != b'\x80':
                    break

        @classmethod
        def _parse_custom_field(cls, data: bytes) -> dict[str, int | str | bytes | Image]:
            fh = BytesIO(data)
            header_size = 8
            field_name = None
            data_atom = b''
            atom_header = fh.read(header_size)
            while len(atom_header) == header_size:
                atom_size = unpack('>I', atom_header[:4])[0] - header_size
                atom_type = atom_header[4:]
                if atom_type == b'name':
                    atom_value = fh.read(atom_size)[4:].lower()
                    field_name = atom_value.decode('utf-8', 'replace')
                    field_name = cls._CUSTOM_FIELD_NAME_MAPPING.get(
                        field_name, TinyTag._EXTRA_PREFIX + field_name)
                elif atom_type == b'data':
                    data_atom = fh.read(atom_size)
                else:
                    fh.seek(atom_size, SEEK_CUR)
                atom_header = fh.read(header_size)  # read next atom
            if len(data_atom) < 8 or field_name is None:
                return {}
            parser = cls._make_data_atom_parser(field_name)
            return parser(data_atom)

        @classmethod
        def _parse_audio_sample_entry_mp4a(cls, data: bytes) -> dict[str, int]:
            # this atom also contains the esds atom:
            # https://ffmpeg.org/doxygen/0.6/mov_8c-source.html
            # http://xhelmboyx.tripod.com/formats/mp4-layout.txt
            # http://sasperger.tistory.com/103
            datafh = BytesIO(data)
            datafh.seek(16, SEEK_CUR)  # jump over version and flags
            channels = unpack('>H', datafh.read(2))[0]
            datafh.seek(4, SEEK_CUR)   # jump over bit_depth, QT compr id & pkt size
            sr = unpack('>I', datafh.read(4))[0]

            # ES Description Atom
            esds_atom_size = unpack('>I', data[28:32])[0]
            esds_atom = BytesIO(data[36:36 + esds_atom_size])
            esds_atom.seek(5, SEEK_CUR)   # jump over version, flags and tag

            # ES Descriptor
            cls._read_extended_descriptor(esds_atom)
            esds_atom.seek(4, SEEK_CUR)   # jump over ES id, flags and tag

            # Decoder Config Descriptor
            cls._read_extended_descriptor(esds_atom)
            esds_atom.seek(9, SEEK_CUR)
            avg_br = unpack('>I', esds_atom.read(4))[0] / 1000  # kbit/s
            return {'channels': channels, 'samplerate': sr, 'bitrate': avg_br}

        @classmethod
        def _parse_audio_sample_entry_alac(cls, data: bytes) -> dict[str, int]:
            # https://github.com/macosforge/alac/blob/master/ALACMagicCookieDescription.txt
            alac_atom_size = unpack('>I', data[28:32])[0]
            alac_atom = BytesIO(data[36:36 + alac_atom_size])
            alac_atom.seek(9, SEEK_CUR)
            bitdepth = unpack('b', alac_atom.read(1))[0]
            alac_atom.seek(3, SEEK_CUR)
            channels = unpack('b', alac_atom.read(1))[0]
            alac_atom.seek(6, SEEK_CUR)
            avg_br = unpack('>I', alac_atom.read(4))[0] / 1000  # kbit/s
            sr = unpack('>I', alac_atom.read(4))[0]
            return {'channels': channels, 'samplerate': sr, 'bitrate': avg_br, 'bitdepth': bitdepth}

        @classmethod
        def _parse_mvhd(cls, data: bytes) -> dict[str, float]:
            # http://stackoverflow.com/a/3639993/1191373
            walker = BytesIO(data)
            version = unpack('b', walker.read(1))[0]
            walker.seek(3, SEEK_CUR)  # jump over flags
            if version == 0:  # uses 32 bit integers for timestamps
                walker.seek(8, SEEK_CUR)  # jump over create & mod times
                time_scale = unpack('>I', walker.read(4))[0]
                duration = unpack('>I', walker.read(4))[0]
            else:  # version == 1:  # uses 64 bit integers for timestamps
                walker.seek(16, SEEK_CUR)  # jump over create & mod times
                time_scale = unpack('>I', walker.read(4))[0]
                duration = unpack('>q', walker.read(8))[0]
            return {'duration': duration / time_scale}

    # The parser tree: Each key is an atom name which is traversed if existing.
    # Leaves of the parser tree are callables which receive the atom data.
    # callables return {fieldname: value} which is updates the TinyTag.
    _META_DATA_TREE = {b'moov': {b'udta': {b'meta': {b'ilst': {
        # see: http://atomicparsley.sourceforge.net/mpeg-4files.html
        # and: https://metacpan.org/dist/Image-ExifTool/source/lib/Image/ExifTool/QuickTime.pm#L3093
        b'\xa9ART': {b'data': _Parser._make_data_atom_parser('artist')},
        b'\xa9alb': {b'data': _Parser._make_data_atom_parser('album')},
        b'\xa9cmt': {b'data': _Parser._make_data_atom_parser('comment')},
        b'\xa9con': {b'data': _Parser._make_data_atom_parser('extra.conductor')},
        # need test-data for this
        # b'cpil':   {b'data': _Parser._make_data_atom_parser('extra.compilation')},
        b'\xa9day': {b'data': _Parser._make_data_atom_parser('year')},
        b'\xa9des': {b'data': _Parser._make_data_atom_parser('extra.description')},
        b'\xa9dir': {b'data': _Parser._make_data_atom_parser('extra.director')},
        b'\xa9gen': {b'data': _Parser._make_data_atom_parser('genre')},
        b'\xa9lyr': {b'data': _Parser._make_data_atom_parser('extra.lyrics')},
        b'\xa9mvn': {b'data': _Parser._make_data_atom_parser('movement')},
        b'\xa9nam': {b'data': _Parser._make_data_atom_parser('title')},
        b'\xa9pub': {b'data': _Parser._make_data_atom_parser('extra.publisher')},
        b'\xa9too': {b'data': _Parser._make_data_atom_parser('extra.encoded_by')},
        b'\xa9wrt': {b'data': _Parser._make_data_atom_parser('composer')},
        b'aART': {b'data': _Parser._make_data_atom_parser('albumartist')},
        b'cprt': {b'data': _Parser._make_data_atom_parser('extra.copyright')},
        b'desc': {b'data': _Parser._make_data_atom_parser('extra.description')},
        b'disk': {b'data': _Parser._make_number_parser('disc', 'disc_total')},
        b'gnre': {b'data': _Parser._parse_id3v1_genre},
        b'trkn': {b'data': _Parser._make_number_parser('track', 'track_total')},
        b'tmpo': {b'data': _Parser._make_data_atom_parser('extra.bpm')},
        b'covr': {b'data': _Parser._make_data_atom_parser('images.front_cover')},
        b'----': _Parser._parse_custom_field,
    }}}}}

    # see: https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/QTFFChap3/qtff3.html
    _AUDIO_DATA_TREE = {
        b'moov': {
            b'mvhd': _Parser._parse_mvhd,
            b'trak': {b'mdia': {b"minf": {b"stbl": {b"stsd": {
                b'mp4a': _Parser._parse_audio_sample_entry_mp4a,
                b'alac': _Parser._parse_audio_sample_entry_alac
            }}}}}
        }
    }

    _VERSIONED_ATOMS = {b'meta', b'stsd'}  # those have an extra 4 byte header
    _FLAGGED_ATOMS = {b'stsd'}  # these also have an extra 4 byte header

    def _determine_duration(self, fh: BinaryIO) -> None:
        self._traverse_atoms(fh, path=self._AUDIO_DATA_TREE)

    def _parse_tag(self, fh: BinaryIO) -> None:
        self._traverse_atoms(fh, path=self._META_DATA_TREE)

    def _traverse_atoms(self, fh: BinaryIO, path: dict[bytes, Any],
                        stop_pos: int | None = None,
                        curr_path: list[bytes] | None = None) -> None:
        header_size = 8
        atom_header = fh.read(header_size)
        while len(atom_header) == header_size:
            atom_size = unpack('>I', atom_header[:4])[0] - header_size
            atom_type = atom_header[4:]
            if curr_path is None:  # keep track how we traversed in the tree
                curr_path = [atom_type]
            if atom_size <= 0:  # empty atom, jump to next one
                atom_header = fh.read(header_size)
                continue
            if DEBUG:
                print(f'{" " * 4 * len(curr_path)} pos: {fh.tell() - header_size} '
                      f'atom: {atom_type!r} len: {atom_size + header_size}')
            if atom_type in self._VERSIONED_ATOMS:  # jump atom version for now
                fh.seek(4, SEEK_CUR)
            if atom_type in self._FLAGGED_ATOMS:  # jump atom flags for now
                fh.seek(4, SEEK_CUR)
            sub_path = path.get(atom_type, None)
            # if the path leaf is a dict, traverse deeper into the tree:
            if isinstance(sub_path, dict):
                atom_end_pos = fh.tell() + atom_size
                self._traverse_atoms(fh, path=sub_path, stop_pos=atom_end_pos,
                                     curr_path=curr_path + [atom_type])
            # if the path-leaf is a callable, call it on the atom data
            elif callable(sub_path):
                for fieldname, value in sub_path(fh.read(atom_size)).items():
                    if DEBUG:
                        print(' ' * 4 * len(curr_path), 'FIELD: ', fieldname)
                    if fieldname.startswith('images.'):
                        if self._load_image:
                            self.images._set_field(fieldname[len('images.'):], value)
                    elif fieldname:
                        self._set_field(fieldname, value)
            # if no action was specified using dict or callable, jump over atom
            else:
                fh.seek(atom_size, SEEK_CUR)
            # check if we have reached the end of this branch:
            if stop_pos and fh.tell() >= stop_pos:
                return  # return to parent (next parent node in tree)
            atom_header = fh.read(header_size)  # read next atom


class _ID3(TinyTag):
    _ID3_MAPPING = {
        # Mapping from Frame ID to a field of the TinyTag
        # https://exiftool.org/TagNames/ID3.html
        'COMM': 'comment', 'COM': 'comment',
        'TRCK': 'track', 'TRK': 'track',
        'TYER': 'year', 'TYE': 'year', 'TDRC': 'year',
        'TALB': 'album', 'TAL': 'album',
        'TPE1': 'artist', 'TP1': 'artist',
        'TIT2': 'title', 'TT2': 'title',
        'TCON': 'genre', 'TCO': 'genre',
        'TPOS': 'disc', 'TPA': 'disc',
        'TPE2': 'albumartist', 'TP2': 'albumartist',
        'TCOM': 'composer', 'TCM': 'composer',
        'WOAR': 'extra.url', 'WAR': 'extra.url',
        'TSRC': 'extra.isrc', 'TRC': 'extra.isrc',
        'TCOP': 'extra.copyright', 'TCR': 'extra.copyright',
        'TBPM': 'extra.bpm', 'TBP': 'extra.bpm',
        'TKEY': 'extra.initial_key', 'TKE': 'extra.initial_key',
        'TLAN': 'extra.language', 'TLA': 'extra.language',
        'TPUB': 'extra.publisher', 'TPB': 'extra.publisher',
        'USLT': 'extra.lyrics', 'ULT': 'extra.lyrics',
        'TPE3': 'extra.conductor', 'TP3': 'extra.conductor',
        'TEXT': 'extra.lyricist', 'TXT': 'extra.lyricist',
        'TSST': 'extra.set_subtitle',
        'TENC': 'extra.encoded_by', 'TEN': 'extra.encoded_by',
        'TSSE': 'extra.encoder_settings', 'TSS': 'extra.encoder_settings',
        'TMED': 'extra.media', 'TMT': 'extra.media',
        'TDOR': 'extra.original_date',
        'TORY': 'extra.original_year', 'TOR': 'extra.original_year',
        'WCOP': 'extra.license',
    }
    _ID3_MAPPING_CUSTOM = {
        'artists': 'artist',
        'director': 'extra.director',
        'license': 'extra.license',
        'originalyear': 'extra.original_year',
        'barcode': 'extra.barcode',
        'catalognumber': 'extra.catalog_number',
    }
    _IMAGE_FRAME_IDS = {'APIC', 'PIC'}
    _CUSTOM_FRAME_IDS = {'TXXX', 'TXX'}
    _DISALLOWED_FRAME_IDS = {'PRIV', 'RGAD', 'GEOB', 'GEO', 'ÿû°d'}
    _MAX_ESTIMATION_SEC = 30.0
    _CBR_DETECTION_FRAME_COUNT = 5
    _USE_XING_HEADER = True  # much faster, but can be deactivated for testing

    _ID3V1_GENRES = (
        'Blues', 'Classic Rock', 'Country', 'Dance', 'Disco',
        'Funk', 'Grunge', 'Hip-Hop', 'Jazz', 'Metal', 'New Age', 'Oldies',
        'Other', 'Pop', 'R&B', 'Rap', 'Reggae', 'Rock', 'Techno', 'Industrial',
        'Alternative', 'Ska', 'Death Metal', 'Pranks', 'Soundtrack',
        'Euro-Techno', 'Ambient', 'Trip-Hop', 'Vocal', 'Jazz+Funk', 'Fusion',
        'Trance', 'Classical', 'Instrumental', 'Acid', 'House', 'Game',
        'Sound Clip', 'Gospel', 'Noise', 'AlternRock', 'Bass', 'Soul', 'Punk',
        'Space', 'Meditative', 'Instrumental Pop', 'Instrumental Rock',
        'Ethnic', 'Gothic', 'Darkwave', 'Techno-Industrial', 'Electronic',
        'Pop-Folk', 'Eurodance', 'Dream', 'Southern Rock', 'Comedy', 'Cult',
        'Gangsta', 'Top 40', 'Christian Rap', 'Pop/Funk', 'Jungle',
        'Native American', 'Cabaret', 'New Wave', 'Psychadelic', 'Rave',
        'Showtunes', 'Trailer', 'Lo-Fi', 'Tribal', 'Acid Punk', 'Acid Jazz',
        'Polka', 'Retro', 'Musical', 'Rock & Roll', 'Hard Rock',

        # Wimamp Extended Genres
        'Folk', 'Folk-Rock', 'National Folk', 'Swing', 'Fast Fusion', 'Bebob',
        'Latin', 'Revival', 'Celtic', 'Bluegrass', 'Avantgarde', 'Gothic Rock',
        'Progressive Rock', 'Psychedelic Rock', 'Symphonic Rock', 'Slow Rock',
        'Big Band', 'Chorus', 'Easy listening', 'Acoustic', 'Humour', 'Speech',
        'Chanson', 'Opera', 'Chamber Music', 'Sonata', 'Symphony', 'Booty Bass',
        'Primus', 'Porn Groove', 'Satire', 'Slow Jam', 'Club', 'Tango', 'Samba',
        'Folklore', 'Ballad', 'Power Ballad', 'Rhythmic Soul', 'Freestyle',
        'Duet', 'Punk Rock', 'Drum Solo', 'A capella', 'Euro-House',
        'Dance Hall', 'Goa', 'Drum & Bass',

        # according to https://de.wikipedia.org/wiki/Liste_der_ID3v1-Genres:
        'Club-House', 'Hardcore Techno', 'Terror', 'Indie', 'BritPop',
        '',  # don't use ethnic slur ("Negerpunk", WTF!)
        'Polsk Punk', 'Beat', 'Christian Gangsta Rap', 'Heavy Metal',
        'Black Metal', 'Contemporary Christian', 'Christian Rock',
        # WinAmp 1.91
        'Merengue', 'Salsa', 'Thrash Metal', 'Anime', 'Jpop', 'Synthpop',
        # WinAmp 5.6
        'Abstract', 'Art Rock', 'Baroque', 'Bhangra', 'Big Beat', 'Breakbeat',
        'Chillout', 'Downtempo', 'Dub', 'EBM', 'Eclectic', 'Electro',
        'Electroclash', 'Emo', 'Experimental', 'Garage', 'Illbient',
        'Industro-Goth', 'Jam Band', 'Krautrock', 'Leftfield', 'Lounge',
        'Math Rock', 'New Romantic', 'Nu-Breakz', 'Post-Punk', 'Post-Rock',
        'Psytrance', 'Shoegaze', 'Space Rock', 'Trop Rock', 'World Music',
        'Neoclassical', 'Audiobook', 'Audio Theatre', 'Neue Deutsche Welle',
        'Podcast', 'Indie Rock', 'G-Funk', 'Dubstep', 'Garage Rock', 'Psybient',
    )
    _ID3V2_2_IMAGE_FORMATS = {
        'bmp': 'image/bmp',
        'jpg': 'image/jpeg',
        'png': 'image/png',
    }
    _IMAGE_TYPES = (
        'other',
        'extra.icon',
        'extra.other_icon',
        'front_cover',
        'back_cover',
        'leaflet',
        'media',
        'extra.lead_artist',
        'extra.artist',
        'extra.conductor',
        'extra.band',
        'extra.composer',
        'extra.lyricist',
        'extra.recording_location',
        'extra.during_recording',
        'extra.during_performance',
        'extra.video',
        'extra.bright_colored_fish',
        'extra.illustration',
        'extra.band_logo',
        'extra.publisher_logo',
    )
    _UNKNOWN_IMAGE_TYPE = 'extra.unknown'

    # see this page for the magic values used in mp3:
    # http://www.mpgedit.org/mpgedit/mpeg_format/mpeghdr.htm
    _SAMPLE_RATES = (
        (11025, 12000, 8000),   # MPEG 2.5
        (0, 0, 0),              # reserved
        (22050, 24000, 16000),  # MPEG 2
        (44100, 48000, 32000),  # MPEG 1
    )
    _V1L1 = (0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 0)
    _V1L2 = (0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 0)
    _V1L3 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0)
    _V2L1 = (0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 0)
    _V2L2 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0)
    _V2L3 = _V2L2
    _NONE = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    _BITRATE_BY_VERSION_BY_LAYER = (
        (_NONE, _V2L3, _V2L2, _V2L1),  # MPEG Version 2.5  # note that the layers go
        (_NONE, _NONE, _NONE, _NONE),  # reserved          # from 3 to 1 by design.
        (_NONE, _V2L3, _V2L2, _V2L1),  # MPEG Version 2    # the first layer id is
        (_NONE, _V1L3, _V1L2, _V1L1),  # MPEG Version 1    # reserved
    )
    _SAMPLES_PER_FRAME = 1152  # the default frame size for mp3
    _CHANNELS_PER_CHANNEL_MODE = (
        2,  # 00 Stereo
        2,  # 01 Joint stereo (Stereo)
        2,  # 10 Dual channel (2 mono channels)
        1,  # 11 Single channel (Mono)
    )

    def __init__(self) -> None:
        super().__init__()
        # save position after the ID3 tag for duration measurement speedup
        self._bytepos_after_id3v2 = -1

    @staticmethod
    def _parse_xing_header(fh: BinaryIO) -> tuple[int, int]:
        # see: http://www.mp3-tech.org/programmer/sources/vbrheadersdk.zip
        fh.seek(4, SEEK_CUR)  # read over Xing header
        header_flags = unpack('>i', fh.read(4))[0]
        frames = byte_count = 0
        if header_flags & 1:  # FRAMES FLAG
            frames = unpack('>i', fh.read(4))[0]
        if header_flags & 2:  # BYTES FLAG
            byte_count = unpack('>i', fh.read(4))[0]
        if header_flags & 4:  # TOC FLAG
            fh.seek(100, SEEK_CUR)
        if header_flags & 8:  # VBR SCALE FLAG
            fh.seek(4, SEEK_CUR)
        return frames, byte_count

    def _determine_duration(self, fh: BinaryIO) -> None:
        # if tag reading was disabled, find start position of audio data
        if self._bytepos_after_id3v2 == -1:
            self._parse_id3v2_header(fh)

        max_estimation_frames = (_ID3._MAX_ESTIMATION_SEC * 44100) // _ID3._SAMPLES_PER_FRAME
        frame_size_accu = 0
        audio_offset = 0
        frames = 0  # count frames for determining mp3 duration
        bitrate_accu = 0    # add up bitrates to find average bitrate to detect
        last_bitrates = set()  # CBR mp3s (multiple frames with same bitrates)
        # seek to first position after id3 tag (speedup for large header)
        first_mpeg_id = None
        fh.seek(self._bytepos_after_id3v2)
        file_offset = fh.tell()
        walker = BytesIO(fh.read())
        while True:
            # reading through garbage until 11 '1' sync-bits are found
            header = walker.read(4)
            header_len = len(header)
            walker.seek(-header_len, SEEK_CUR)
            if header_len < 4:
                if frames:
                    self.bitrate = bitrate_accu / frames
                break  # EOF
            _sync, conf, bitrate_freq, rest = unpack('BBBB', header)
            br_id = (bitrate_freq >> 4) & 0x0F  # biterate id
            sr_id = (bitrate_freq >> 2) & 0x03  # sample rate id
            padding = 1 if bitrate_freq & 0x02 > 0 else 0
            mpeg_id = (conf >> 3) & 0x03
            layer_id = (conf >> 1) & 0x03
            channel_mode = (rest >> 6) & 0x03
            # check for eleven 1s, validate bitrate and sample rate
            if (not header[:2] > b'\xFF\xE0'
                    or (first_mpeg_id is not None and first_mpeg_id != mpeg_id)
                    or br_id > 14 or br_id == 0 or sr_id == 3 or layer_id == 0 or mpeg_id == 1):
                idx = header.find(b'\xFF', 1)  # invalid frame, find next sync header
                if idx == -1:
                    idx = header_len  # not found: jump over the current peek buffer
                walker.seek(max(idx, 1), SEEK_CUR)
                continue
            if first_mpeg_id is None:
                first_mpeg_id = mpeg_id
            self.channels = self._CHANNELS_PER_CHANNEL_MODE[channel_mode]
            frame_bitrate = self._BITRATE_BY_VERSION_BY_LAYER[mpeg_id][layer_id][br_id]
            self.samplerate = samplerate = self._SAMPLE_RATES[mpeg_id][sr_id]
            frame_length = (144000 * frame_bitrate) // samplerate + padding
            # There might be a xing header in the first frame that contains
            # all the info we need, otherwise parse multiple frames to find the
            # accurate average bitrate
            if frames == 0 and self._USE_XING_HEADER:
                walker_offset = walker.tell()
                frame_content = walker.read(frame_length)
                xing_header_offset = frame_content.find(b'Xing')
                if xing_header_offset != -1:
                    walker.seek(walker_offset + xing_header_offset)
                    xframes, byte_count = self._parse_xing_header(walker)
                    if xframes > 0 and byte_count > 0:
                        # MPEG-2 Audio Layer III uses 576 samples per frame
                        samples_per_frame = 576 if mpeg_id <= 2 else self._SAMPLES_PER_FRAME
                        self.duration = duration = xframes * samples_per_frame / samplerate
                        self.bitrate = byte_count * 8 / duration / 1000
                        return
                walker.seek(walker_offset)

            frames += 1  # it's most probably an mp3 frame
            bitrate_accu += frame_bitrate
            if frames == 1:
                audio_offset = file_offset + walker.tell()
            if frames <= self._CBR_DETECTION_FRAME_COUNT:
                last_bitrates.add(frame_bitrate)

            frame_size_accu += frame_length
            # if bitrate does not change over time its probably CBR
            is_cbr = (frames == self._CBR_DETECTION_FRAME_COUNT and len(last_bitrates) == 1)
            if frames == max_estimation_frames or is_cbr:
                # try to estimate duration
                fh.seek(-128, 2)  # jump to last byte (leaving out id3v1 tag)
                audio_stream_size = fh.tell() - audio_offset
                est_frame_count = audio_stream_size / (frame_size_accu / frames)
                samples = est_frame_count * self._SAMPLES_PER_FRAME
                self.duration = samples / samplerate
                self.bitrate = bitrate_accu / frames
                return

            if frame_length > 1:  # jump over current frame body
                walker.seek(frame_length, SEEK_CUR)
        if self.samplerate:
            self.duration = frames * self._SAMPLES_PER_FRAME / self.samplerate

    def _parse_tag(self, fh: BinaryIO) -> None:
        self._parse_id3v2(fh)
        if self.filesize > 128:
            fh.seek(-128, SEEK_END)  # try parsing id3v1 in last 128 bytes
            self._parse_id3v1(fh)

    def _parse_id3v2_header(self, fh: BinaryIO) -> tuple[int, bool, int]:
        size = major = 0
        extended = False
        # for info on the specs, see: http://id3.org/Developer%20Information
        header = unpack('3sBBB4B', fh.read(10))
        tag = header[0].decode('ISO-8859-1', 'replace')
        # check if there is an ID3v2 tag at the beginning of the file
        if tag == 'ID3':
            major, _rev = header[1:3]
            if DEBUG:
                print(f'Found id3 v2.{major}')
            # unsync = (header[3] & 0x80) > 0
            extended = (header[3] & 0x40) > 0
            # experimental = (header[3] & 0x20) > 0
            # footer = (header[3] & 0x10) > 0
            size = self._unsynchsafe(header[4:8])
        self._bytepos_after_id3v2 = size
        return size, extended, major

    def _parse_id3v2(self, fh: BinaryIO) -> None:
        size, extended, major = self._parse_id3v2_header(fh)
        if size:
            end_pos = fh.tell() + size
            parsed_size = 0
            if extended:  # just read over the extended header.
                extd_size = self._unsynchsafe(unpack('4B', fh.read(6)[:4]))
                fh.seek(extd_size - 6, SEEK_CUR)  # jump over extended_header
            while parsed_size < size:
                frame_size = self._parse_frame(fh, id3version=major)
                if frame_size == 0:
                    break
                parsed_size += frame_size
            fh.seek(end_pos, SEEK_SET)

    def _parse_id3v1(self, fh: BinaryIO) -> None:
        if fh.read(3) != b'TAG':  # check if this is an ID3 v1 tag
            return

        def asciidecode(x: bytes) -> str:
            return self._unpad(x.decode(self._default_encoding or 'latin1', 'replace'))
        # Only set fields that were not set by ID3v2 tags, as ID3v1
        # tags are more likely to be outdated or have encoding issues
        fields = fh.read(30 + 30 + 30 + 4 + 30 + 1)
        if not self.title:
            value = asciidecode(fields[:30])
            if value:
                self._set_field('title', value)
        if not self.artist:
            value = asciidecode(fields[30:60])
            if value:
                self._set_field('artist', value)
        if not self.album:
            value = asciidecode(fields[60:90])
            if value:
                self._set_field('album', value)
        if not self.year:
            value = asciidecode(fields[90:94])
            if value:
                self._set_field('year', value)
        comment = fields[94:124]
        if b'\x00\x00' < comment[-2:] < b'\x01\x00':
            if self.track is None:
                self._set_field('track', ord(comment[-1:]))
            comment = comment[:-2]
        if not self.comment:
            value = asciidecode(comment)
            if value:
                self._set_field('comment', value)
        if not self.genre:
            genre_id = ord(fields[124:125])
            if genre_id < len(self._ID3V1_GENRES):
                self._set_field('genre', self._ID3V1_GENRES[genre_id])

    def __parse_custom_field(self, content: str) -> bool:
        custom_field_name, separator, value = content.partition('\x00')
        custom_field_name_lower = custom_field_name.lower()
        value = value.lstrip('\ufeff')
        if custom_field_name_lower and separator and value:
            field_name = self._ID3_MAPPING_CUSTOM.get(
                custom_field_name_lower, self._EXTRA_PREFIX + custom_field_name_lower)
            self._set_field(field_name, value)
            return True
        return False

    @classmethod
    def _create_tag_image(cls, data: bytes, pic_type: int, mime_type: str | None = None,
                          description: str | None = None) -> tuple[str, Image]:
        field_name = cls._UNKNOWN_IMAGE_TYPE
        if 0 <= pic_type <= len(cls._IMAGE_TYPES):
            field_name = cls._IMAGE_TYPES[pic_type]
        name = field_name
        if field_name.startswith(cls._EXTRA_PREFIX):
            name = field_name[len(cls._EXTRA_PREFIX):]
        image = Image(name, data)
        if mime_type:
            image.mime_type = mime_type
        if description:
            image.description = description
        return field_name, image

    @staticmethod
    def _index_utf16(s: bytes, search: bytes) -> int:
        for i in range(0, len(s), len(search)):
            if s[i:i + len(search)] == search:
                return i
        return -1

    def _parse_frame(self, fh: BinaryIO, id3version: int | None = None) -> int:
        # ID3v2.2 especially ugly. see: http://id3.org/id3v2-00
        frame_header_size = 6 if id3version == 2 else 10
        frame_size_bytes = 3 if id3version == 2 else 4
        is_synchsafe_int = id3version == 4
        frame_header_data = fh.read(frame_header_size)
        if len(frame_header_data) != frame_header_size:
            return 0
        frame_id = self._decode_string(frame_header_data[:frame_size_bytes])
        frame_size: int
        if frame_size_bytes == 3:
            frame_size = unpack('>I', b'\x00' + frame_header_data[3:6])[0]
        elif is_synchsafe_int:
            frame_size = self._unsynchsafe(unpack('4B', frame_header_data[4:8]))
        else:
            frame_size = unpack('>I', frame_header_data[4:8])[0]
        if DEBUG:
            print(f'Found id3 Frame {frame_id} at {fh.tell()}-{fh.tell() + frame_size} '
                  f'of {self.filesize}')
        if frame_size > 0:
            # flags = frame[1+frame_size_bytes:] # dont care about flags.
            content = fh.read(frame_size)
            fieldname = self._ID3_MAPPING.get(frame_id)
            should_set_field = True
            if fieldname:
                if not self._parse_tags:
                    return frame_size
                language = fieldname in {'comment', 'extra.lyrics'}
                value = self._decode_string(content, language)
                if not value:
                    return frame_size
                if fieldname == "comment":
                    # check if comment is a key-value pair (used by iTunes)
                    should_set_field = not self.__parse_custom_field(value)
                elif fieldname in {'track', 'disc'}:
                    if '/' in value:
                        value, total = value.split('/')[:2]
                        if total.isdecimal():
                            self._set_field(f'{fieldname}_total', int(total))
                    if value.isdecimal():
                        self._set_field(fieldname, int(value))
                    should_set_field = False
                elif fieldname == 'genre':
                    genre_id = 255
                    # funky: id3v1 genre hidden in a id3v2 field
                    if value.isdecimal():
                        genre_id = int(value)
                    # funkier: the TCO may contain genres in parens, e.g. '(13)'
                    elif value[:1] == '(':
                        end_pos = value.find(')')
                        parens_text = value[1:end_pos]
                        if end_pos > 0 and parens_text.isdecimal():
                            genre_id = int(parens_text)
                    if 0 <= genre_id < len(_ID3._ID3V1_GENRES):
                        value = _ID3._ID3V1_GENRES[genre_id]
                if should_set_field:
                    self._set_field(fieldname, value)
            elif frame_id in self._CUSTOM_FRAME_IDS:
                # custom fields
                if self._parse_tags:
                    value = self._decode_string(content)
                    if value:
                        self.__parse_custom_field(value)
            elif frame_id in self._IMAGE_FRAME_IDS:
                if self._load_image:
                    # See section 4.14: http://id3.org/id3v2.4.0-frames
                    encoding = content[:1]
                    if frame_id == 'PIC':  # ID3 v2.2:
                        imgformat = self._decode_string(content[1:4]).lower()
                        mime_type = self._ID3V2_2_IMAGE_FORMATS.get(imgformat)
                        desc_start_pos = 1 + 3 + 1  # skip encoding (1), imgformat (3), pictype(1)
                    else:  # ID3 v2.3+
                        mime_type_end_pos = content.index(b'\x00', 1)
                        mime_type = self._decode_string(content[1:mime_type_end_pos]).lower()
                        if mime_type in self._ID3V2_2_IMAGE_FORMATS:  # ID3 v2.2 format in v2.3...
                            mime_type = self._ID3V2_2_IMAGE_FORMATS[mime_type]
                        desc_start_pos = mime_type_end_pos + 1 + 1  # skip mtype, pictype(1)
                    pic_type = content[desc_start_pos - 1]
                    # latin1 and utf-8 are 1 byte
                    termination = b'\x00' if encoding in {b'\x00', b'\x03'} else b'\x00\x00'
                    desc_length = self._index_utf16(content[desc_start_pos:], termination)
                    desc_end_pos = desc_start_pos + desc_length + len(termination)
                    description = self._decode_string(content[desc_start_pos:desc_end_pos])
                    field_name, image = self._create_tag_image(
                        content[desc_end_pos:], pic_type, mime_type, description)
                    self.images._set_field(field_name, image)
            elif frame_id not in self._DISALLOWED_FRAME_IDS:
                # unknown, try to add to extra dict
                if self._parse_tags:
                    value = self._decode_string(content)
                    if value:
                        self._set_field(self._EXTRA_PREFIX + frame_id.lower(), value)
            return frame_size
        return 0

    def _decode_string(self, bytestr: bytes, language: bool = False) -> str:
        default_encoding = 'ISO-8859-1'
        if self._default_encoding:
            default_encoding = self._default_encoding
        # it's not my fault, this is the spec.
        first_byte = bytestr[:1]
        if first_byte == b'\x00':  # ISO-8859-1
            bytestr = bytestr[1:]
            encoding = default_encoding
        elif first_byte == b'\x01':  # UTF-16 with BOM
            bytestr = bytestr[1:]
            # remove language (but leave BOM)
            if language:
                if bytestr[3:5] in {b'\xfe\xff', b'\xff\xfe'}:
                    bytestr = bytestr[3:]
                if bytestr[:3].isalpha():
                    bytestr = bytestr[3:]  # remove language
                bytestr = bytestr.lstrip(b'\x00')  # strip optional additional null bytes
            # read byte order mark to determine endianness
            encoding = 'UTF-16be' if bytestr[:2] == b'\xfe\xff' else 'UTF-16le'
            # strip the bom if it exists
            if bytestr[:2] in {b'\xfe\xff', b'\xff\xfe'}:
                bytestr = bytestr[2:] if len(bytestr) % 2 == 0 else bytestr[2:-1]
            # remove ADDITIONAL EXTRA BOM :facepalm:
            if bytestr[:4] == b'\x00\x00\xff\xfe':
                bytestr = bytestr[4:]
        elif first_byte == b'\x02':  # UTF-16LE
            # strip optional null byte, if byte count uneven
            bytestr = bytestr[1:-1] if len(bytestr) % 2 == 0 else bytestr[1:]
            encoding = 'UTF-16le'
        elif first_byte == b'\x03':  # UTF-8
            bytestr = bytestr[1:]
            encoding = 'UTF-8'
        else:
            encoding = default_encoding  # wild guess
        if language and bytestr[:3].isalpha():
            bytestr = bytestr[3:]  # remove language
        return self._unpad(bytestr.decode(encoding, 'replace'))

    @staticmethod
    def _unsynchsafe(intarr: tuple[int, ...]) -> int:
        return (intarr[0] << 21) + (intarr[1] << 14) + (intarr[2] << 7) + intarr[3]


class _Ogg(TinyTag):
    _VORBIS_MAPPING = {
        'album': 'album',
        'albumartist': 'albumartist',
        'title': 'title',
        'artist': 'artist',
        'artists': 'artist',
        'author': 'artist',
        'date': 'year',
        'tracknumber': 'track',
        'tracktotal': 'track_total',
        'totaltracks': 'track_total',
        'discnumber': 'disc',
        'disctotal': 'disc_total',
        'totaldiscs': 'disc_total',
        'genre': 'genre',
        'description': 'comment',
        'comment': 'comment',
        'comments': 'comment',
        'composer': 'composer',
        'bpm': 'extra.bpm',
        'copyright': 'extra.copyright',
        'isrc': 'extra.isrc',
        'lyrics': 'extra.lyrics',
        'publisher': 'extra.publisher',
        'language': 'extra.language',
        'director': 'extra.director',
        'website': 'extra.url',
        'conductor': 'extra.conductor',
        'lyricist': 'extra.lyricist',
        'discsubtitle': 'extra.set_subtitle',
        'setsubtitle': 'extra.set_subtitle',
        'initialkey': 'extra.initial_key',
        'key': 'extra.initial_key',
        'encodedby': 'extra.encoded_by',
        'encodersettings': 'extra.encoder_settings',
        'media': 'extra.media',
        'originaldate': 'extra.original_date',
        'originalyear': 'extra.original_year',
        'license': 'extra.license',
        'barcode': 'extra.barcode',
        'catalognumber': 'extra.catalog_number',
    }

    def __init__(self) -> None:
        super().__init__()
        self._max_samplenum = 0  # maximum sample position ever read

    def _determine_duration(self, fh: BinaryIO) -> None:
        max_page_size = 65536  # https://xiph.org/ogg/doc/libogg/ogg_page.html
        if not self._tags_parsed:
            self._parse_tag(fh)  # determine sample rate
            fh.seek(0)           # and rewind to start
        if self.duration is not None or not self.samplerate:
            return  # either ogg flac or invalid file
        if self.filesize > max_page_size:
            fh.seek(-max_page_size, 2)  # go to last possible page position
        while True:
            file_offset = fh.tell()
            b = fh.read()
            if len(b) < 4:
                return  # EOF
            if b[:4] == b'OggS':  # look for an ogg header
                fh.seek(file_offset)
                for _ in self._parse_pages(fh):
                    pass  # parse all remaining pages
                self.duration = self._max_samplenum / self.samplerate
                break
            idx = b.find(b'OggS')  # try to find header in peeked data
            if idx != -1:
                fh.seek(file_offset + idx)

    def _parse_tag(self, fh: BinaryIO) -> None:
        check_flac_second_packet = False
        check_speex_second_packet = False
        for packet in self._parse_pages(fh):
            walker = BytesIO(packet)
            if packet[:7] == b"\x01vorbis":
                if self._parse_duration:
                    (self.channels, self.samplerate, _max_bitrate, bitrate,
                     _min_bitrate) = unpack("<B4i", packet[11:28])
                    self.bitrate = bitrate / 1000
            elif packet[:7] == b"\x03vorbis":
                if self._parse_tags:
                    walker.seek(7, SEEK_CUR)  # jump over header name
                    self._parse_vorbis_comment(walker)
            elif packet[:8] == b'OpusHead':
                if self._parse_duration:  # parse opus header
                    # https://www.videolan.org/developers/vlc/modules/codec/opus_header.c
                    # https://mf4.xiph.org/jenkins/view/opus/job/opusfile-unix/ws/doc/html/structOpusHead.html
                    walker.seek(8, SEEK_CUR)  # jump over header name
                    version, ch = unpack("BB", walker.read(2))
                    walker.seek(9, SEEK_CUR)
                    if (version & 0xF0) == 0:  # only major version 0 supported
                        self.channels = ch
                        self.samplerate = 48000  # internally opus always uses 48khz
            elif packet[:8] == b'OpusTags':
                if self._parse_tags:  # parse opus metadata:
                    walker.seek(8, SEEK_CUR)  # jump over header name
                    self._parse_vorbis_comment(walker)
            elif packet[:5] == b'\x7fFLAC':
                # https://xiph.org/flac/ogg_mapping.html
                walker.seek(9, SEEK_CUR)  # jump over header name, version and number of headers
                flactag = _Flac()
                flactag._filehandler = walker
                flactag.filesize = self.filesize
                flactag._load(tags=self._parse_tags, duration=self._parse_duration,
                              image=self._load_image)
                self._update(flactag)
                check_flac_second_packet = True
            elif check_flac_second_packet:
                # second packet contains FLAC metadata block
                if self._parse_tags:
                    meta_header = unpack('B3B', walker.read(4))
                    block_type = meta_header[0] & 0x7f
                    if block_type == _Flac.METADATA_VORBIS_COMMENT:
                        self._parse_vorbis_comment(walker)
                check_flac_second_packet = False
            elif packet[:8] == b'Speex   ':
                # https://speex.org/docs/manual/speex-manual/node8.html
                if self._parse_duration:
                    walker.seek(36, SEEK_CUR)  # jump over header name and irrelevant fields
                    self.samplerate = unpack("<i", walker.read(4))[0]
                    walker.seek(8, SEEK_CUR)
                    self.channels, self.bitrate = unpack("<ii", walker.read(8))
                check_speex_second_packet = True
            elif check_speex_second_packet:
                if self._parse_tags:
                    length = unpack('I', walker.read(4))[0]  # starts with a comment string
                    comment = walker.read(length).decode('utf-8', 'replace')
                    self._set_field('comment', comment)
                    self._parse_vorbis_comment(walker, contains_vendor=False)  # other tags
                check_speex_second_packet = False
            else:
                if DEBUG:
                    print('Unsupported Ogg page type: ', packet[:16], file=stderr)
                break
        self._tags_parsed = True

    def _parse_vorbis_comment(self, fh: BinaryIO, contains_vendor: bool = True) -> None:
        # for the spec, see: http://xiph.org/vorbis/doc/v-comment.html
        # discnumber tag based on: https://en.wikipedia.org/wiki/Vorbis_comment
        # https://sno.phy.queensu.ca/~phil/exiftool/TagNames/Vorbis.html
        if contains_vendor:
            vendor_length = unpack('I', fh.read(4))[0]
            fh.seek(vendor_length, SEEK_CUR)  # jump over vendor
        elements = unpack('I', fh.read(4))[0]
        for _i in range(elements):
            length = unpack('I', fh.read(4))[0]
            keyvalpair = fh.read(length).decode('utf-8', 'replace')
            if '=' in keyvalpair:
                key, value = keyvalpair.split('=', 1)
                key_lowercase = key.lower()

                if key_lowercase == "metadata_block_picture" and self._load_image:
                    if DEBUG:
                        print('Found Vorbis Image', key, value[:64])
                    fieldname, fieldvalue = _Flac._parse_image(BytesIO(a2b_base64(value)))
                    self.images._set_field(fieldname, fieldvalue)
                else:
                    if DEBUG:
                        print('Found Vorbis Comment', key, value[:64])
                    fieldname = self._VORBIS_MAPPING.get(
                        key_lowercase, self._EXTRA_PREFIX + key_lowercase)  # custom field
                    if fieldname in {'track', 'disc', 'track_total', 'disc_total'}:
                        if fieldname in {'track', 'disc'} and '/' in value:
                            value, total = value.split('/')[:2]
                            if total.isdecimal():
                                self._set_field(f'{fieldname}_total', int(total))
                        if value.isdecimal():
                            self._set_field(fieldname, int(value))
                    elif value:
                        self._set_field(fieldname, value)

    def _parse_pages(self, fh: BinaryIO) -> Iterator[bytes]:
        # for the spec, see: https://wiki.xiph.org/Ogg
        previous_page = b''  # contains data from previous (continuing) pages
        header_data = fh.read(27)  # read ogg page header
        while len(header_data) == 27:
            header = unpack('<4sBBqIIiB', header_data)
            # https://xiph.org/ogg/doc/framing.html
            oggs, version, _flags, pos, _serial, _pageseq, _crc, segments = header
            self._max_samplenum = max(self._max_samplenum, pos)
            if oggs != b'OggS' or version != 0:
                raise ParseError('Invalid OGG header')
            segsizes = unpack('B' * segments, fh.read(segments))
            total = 0
            for segsize in segsizes:  # read all segments
                total += segsize
                if total < 255:  # less than 255 bytes means end of page
                    yield previous_page + fh.read(total)
                    previous_page = b''
                    total = 0
            if total != 0:
                if total % 255 == 0:
                    previous_page += fh.read(total)
                else:
                    yield previous_page + fh.read(total)
                    previous_page = b''
            header_data = fh.read(27)


class _Wave(TinyTag):
    # https://sno.phy.queensu.ca/~phil/exiftool/TagNames/RIFF.html
    _RIFF_MAPPING = {
        b'INAM': 'title',
        b'TITL': 'title',
        b'IPRD': 'album',
        b'IART': 'artist',
        b'IBPM': 'extra.bpm',
        b'ICMT': 'comment',
        b'IMUS': 'composer',
        b'ICOP': 'extra.copyright',
        b'ICRD': 'year',
        b'IGNR': 'genre',
        b'ILNG': 'extra.language',
        b'ISRC': 'extra.isrc',
        b'IPUB': 'extra.publisher',
        b'IPRT': 'track',
        b'ITRK': 'track',
        b'TRCK': 'track',
        b'IBSU': 'extra.url',
        b'YEAR': 'year',
        b'IWRI': 'extra.lyricist',
        b'IENC': 'extra.encoded_by',
        b'IMED': 'extra.media',
    }

    def _determine_duration(self, fh: BinaryIO) -> None:
        if not self._tags_parsed:
            self._parse_tag(fh)

    def _parse_tag(self, fh: BinaryIO) -> None:
        # see: http://www-mmsp.ece.mcgill.ca/Documents/AudioFormats/WAVE/WAVE.html
        # and: https://en.wikipedia.org/wiki/WAV
        riff, _size, fformat = unpack('4sI4s', fh.read(12))
        if riff != b'RIFF' or fformat != b'WAVE':
            raise ParseError('Invalid WAV header')
        if self._parse_duration:
            self.bitdepth = 16  # assume 16bit depth (CD quality)
        chunk_header = fh.read(8)
        while len(chunk_header) == 8:
            subchunkid, subchunksize = unpack('4sI', chunk_header)
            subchunksize += subchunksize % 2  # IFF chunks are padded to an even number of bytes
            if subchunkid == b'fmt ' and self._parse_duration:
                _, channels, samplerate = unpack('HHI', fh.read(8))
                _, _, bitdepth = unpack('<IHH', fh.read(8))
                if bitdepth == 0:
                    # Certain codecs (e.g. GSM 6.10) give us a bit depth of zero.
                    # Avoid division by zero when calculating duration.
                    bitdepth = 1
                self.bitrate = samplerate * channels * bitdepth / 1000
                self.channels, self.samplerate, self.bitdepth = channels, samplerate, bitdepth
                remaining_size = subchunksize - 16
                if remaining_size > 0:
                    fh.seek(remaining_size, 1)  # skip remaining data in chunk
            elif subchunkid == b'data' and self._parse_duration:
                if (self.channels is not None and self.samplerate is not None
                        and self.bitdepth is not None):
                    self.duration = (
                        subchunksize / self.channels / self.samplerate / (self.bitdepth / 8))
                fh.seek(subchunksize, 1)
            elif subchunkid == b'LIST' and self._parse_tags:
                is_info = fh.read(4)  # check INFO header
                if is_info != b'INFO':  # jump over non-INFO sections
                    fh.seek(subchunksize - 4, SEEK_CUR)
                else:
                    sub_fh = BytesIO(fh.read(subchunksize - 4))
                    field = sub_fh.read(4)
                    while len(field) == 4:
                        data_length = unpack('I', sub_fh.read(4))[0]
                        data_length += data_length % 2  # IFF chunks are padded to an even size
                        data = sub_fh.read(data_length).split(b'\x00', 1)[0]  # strip zero-byte
                        fieldname = self._RIFF_MAPPING.get(field)
                        if fieldname:
                            value = data.decode('utf-8', 'replace')
                            if fieldname == 'track':
                                if value.isdecimal():
                                    self._set_field(fieldname, int(value))
                            else:
                                self._set_field(fieldname, value)
                        field = sub_fh.read(4)
            elif subchunkid in {b'id3 ', b'ID3 '} and self._parse_tags:
                id3 = _ID3()
                id3._filehandler = fh
                id3._load(tags=True, duration=False, image=self._load_image)
                self._update(id3)
            else:  # some other chunk, just skip the data
                fh.seek(subchunksize, 1)
            chunk_header = fh.read(8)
        self._tags_parsed = True


class _Flac(TinyTag):
    METADATA_STREAMINFO = 0
    METADATA_PADDING = 1
    METADATA_APPLICATION = 2
    METADATA_SEEKTABLE = 3
    METADATA_VORBIS_COMMENT = 4
    METADATA_CUESHEET = 5
    METADATA_PICTURE = 6

    def _determine_duration(self, fh: BinaryIO) -> None:
        if not self._tags_parsed:
            self._parse_tag(fh)

    def _parse_tag(self, fh: BinaryIO) -> None:
        id3 = None
        header = fh.read(4)
        if header[:3] == b'ID3':  # parse ID3 header if it exists
            fh.seek(-4, SEEK_CUR)
            id3 = _ID3()
            id3._filehandler = fh
            id3._parse_tags = self._parse_tags
            id3._load_image = self._load_image
            id3._parse_id3v2(fh)
            header = fh.read(4)  # after ID3 should be fLaC
        if header[:4] != b'fLaC':
            raise ParseError('Invalid FLAC header')
        # for spec, see https://xiph.org/flac/ogg_mapping.html
        header_data = fh.read(4)
        while len(header_data) == 4:
            block_type = header_data[0] & 0x7f
            is_last_block = header_data[0] & 0x80
            size = unpack('>I', b'\x00' + header_data[1:4])[0]
            # http://xiph.org/flac/format.html#metadata_block_streaminfo
            if block_type == self.METADATA_STREAMINFO and self._parse_duration:
                info_header = fh.read(size)
                if len(info_header) < 34:  # invalid streaminfo
                    break
                # From the xiph documentation:
                # py | <bits>
                # ----------------------------------------------
                # H  | <16>  The minimum block size (in samples)
                # H  | <16>  The maximum block size (in samples)
                # 3s | <24>  The minimum frame size (in bytes)
                # 3s | <24>  The maximum frame size (in bytes)
                # 8B | <20>  Sample rate in Hz.
                #    | <3>   (number of channels)-1.
                #    | <5>   (bits per sample)-1.
                #    | <36>  Total samples in stream.
                # 16s| <128> MD5 signature
                #                 channels--.  bits      total samples
                # |----- samplerate -----| |-||----| |---------~   ~----|
                # 0000 0000 0000 0000 0000 0000 0000 0000 0000      0000
                # #---4---# #---5---# #---6---# #---7---# #--8-~   ~-12-#
                self.samplerate = samplerate = unpack('>I', b'\x00' + info_header[10:13])[0] >> 4
                self.channels = ((info_header[12] >> 1) & 0x07) + 1
                self.bitdepth = (
                    ((info_header[12] & 1) << 4) + ((info_header[13] & 0xF0) >> 4) + 1)
                total_sample_bytes = bytes([info_header[13] & 0x0F]) + info_header[14:18]
                total_samples = unpack('>Q', b'\x00\x00\x00' + total_sample_bytes)[0]
                self.duration = duration = total_samples / samplerate
                if duration > 0:
                    self.bitrate = self.filesize / duration * 8 / 1000
            elif block_type == self.METADATA_VORBIS_COMMENT and self._parse_tags:
                oggtag = _Ogg()
                oggtag._filehandler = fh
                oggtag._parse_vorbis_comment(fh)
                self._update(oggtag)
            elif block_type == self.METADATA_PICTURE and self._load_image:
                fieldname, value = self._parse_image(fh)
                self.images._set_field(fieldname, value)
            elif block_type >= 127:
                break  # invalid block type
            else:
                if DEBUG:
                    print('Unknown FLAC block type', block_type)
                fh.seek(size, 1)  # seek over this block

            if is_last_block:
                break
            header_data = fh.read(4)
        if id3 is not None:  # apply ID3 tags after vorbis
            self._update(id3)
        self._tags_parsed = True

    @classmethod
    def _parse_image(cls, fh: BinaryIO) -> tuple[str, Image]:
        # https://xiph.org/flac/format.html#metadata_block_picture
        pic_type, mime_type_len = unpack('>II', fh.read(8))
        mime_type = fh.read(mime_type_len).decode('utf-8', 'replace')
        description_len = unpack('>I', fh.read(4))[0]
        description = fh.read(description_len).decode('utf-8', 'replace')
        _width, _height, _depth, _colors, pic_len = unpack('>5I', fh.read(20))
        return _ID3._create_tag_image(fh.read(pic_len), pic_type, mime_type, description)


class _Wma(TinyTag):
    # see:
    # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx
    # and (japanese, but none the less helpful)
    # http://uguisu.skr.jp/Windows/format_asf.html
    _ASF_MAPPING = {
        'WM/ARTISTS': 'artist',
        'WM/TrackNumber': 'track',
        'WM/PartOfSet': 'disc',
        'WM/Year': 'year',
        'WM/AlbumArtist': 'albumartist',
        'WM/Genre': 'genre',
        'WM/AlbumTitle': 'album',
        'WM/Composer': 'composer',
        'WM/Publisher': 'extra.publisher',
        'WM/BeatsPerMinute': 'extra.bpm',
        'WM/InitialKey': 'extra.initial_key',
        'WM/Lyrics': 'extra.lyrics',
        'WM/Language': 'extra.language',
        'WM/Director': 'extra.director',
        'WM/AuthorURL': 'extra.url',
        'WM/ISRC': 'extra.isrc',
        'WM/Conductor': 'extra.conductor',
        'WM/Writer': 'extra.lyricist',
        'WM/SetSubTitle': 'extra.set_subtitle',
        'WM/EncodedBy': 'extra.encoded_by',
        'WM/EncodingSettings': 'extra.encoder_settings',
        'WM/Media': 'extra.media',
        'WM/OriginalReleaseTime': 'extra.original_date',
        'WM/OriginalReleaseYear': 'extra.original_year',
        'WM/Barcode': 'extra.barcode',
        'WM/CatalogNo': 'extra.catalog_number',
    }
    _ASF_CONTENT_DESCRIPTION_OBJECT = b'3&\xb2u\x8ef\xcf\x11\xa6\xd9\x00\xaa\x00b\xcel'
    _ASF_EXTENDED_CONTENT_DESCRIPTION_OBJECT = (b'@\xa4\xd0\xd2\x07\xe3\xd2\x11\x97\xf0\x00'
                                                b'\xa0\xc9^\xa8P')
    _STREAM_BITRATE_PROPERTIES_OBJECT = b'\xceu\xf8{\x8dF\xd1\x11\x8d\x82\x00`\x97\xc9\xa2\xb2'
    _ASF_FILE_PROPERTY_OBJECT = b'\xa1\xdc\xab\x8cG\xa9\xcf\x11\x8e\xe4\x00\xc0\x0c Se'
    _ASF_STREAM_PROPERTIES_OBJECT = b'\x91\x07\xdc\xb7\xb7\xa9\xcf\x11\x8e\xe6\x00\xc0\x0c Se'
    _STREAM_TYPE_ASF_AUDIO_MEDIA = b'@\x9ei\xf8M[\xcf\x11\xa8\xfd\x00\x80_\\D+'

    def _determine_duration(self, fh: BinaryIO) -> None:
        if not self._tags_parsed:
            self._parse_tag(fh)

    def _decode_string(self, bytestring: bytes) -> str:
        return self._unpad(bytestring.decode('utf-16', 'replace'))

    def _decode_ext_desc(self, value_type: int, value: bytes) -> str | None:
        """ decode _ASF_EXTENDED_CONTENT_DESCRIPTION_OBJECT values"""
        if value_type == 0:  # Unicode string
            return self._decode_string(value)
        fmt = None
        if 1 < value_type < 6:  # DWORD / QWORD / WORD
            if len(value) == 1:
                fmt = '<B'
            elif len(value) == 2:
                fmt = '<H'
            elif len(value) == 4:
                fmt = '<I'
            elif len(value) == 8:
                fmt = '<Q'
        if fmt:
            return str(unpack(fmt, value)[0])
        return None

    def _parse_tag(self, fh: BinaryIO) -> None:
        header = fh.read(30)
        # http://www.garykessler.net/library/file_sigs.html
        # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx#_Toc521913958
        if (header[:16] != b'0&\xb2u\x8ef\xcf\x11\xa6\xd9\x00\xaa\x00b\xcel'  # 128 bit GUID
                or header[-1:] != b'\x02'):
            raise ParseError('Invalid WMA header')
        while True:
            object_id = fh.read(16)
            object_size_data = fh.read(8)
            if not object_size_data:
                break
            object_size = unpack('<Q', object_size_data)[0]
            if object_size == 0 or object_size > self.filesize:
                break  # invalid object, stop parsing.
            if object_id == self._ASF_CONTENT_DESCRIPTION_OBJECT and self._parse_tags:
                (title_length, author_length, copyright_length, description_length,
                 rating_length) = unpack('<5H', fh.read(10))
                data_blocks = {
                    'title': title_length,
                    'artist': author_length,
                    'extra.copyright': copyright_length,
                    'comment': description_length,
                    '_rating': rating_length,
                }
                for i_field_name, length in data_blocks.items():
                    bytestring = fh.read(length)
                    value = self._decode_string(bytestring)
                    if not i_field_name.startswith('_') and value:
                        self._set_field(i_field_name, value)
            elif object_id == self._ASF_EXTENDED_CONTENT_DESCRIPTION_OBJECT and self._parse_tags:
                # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx#_Toc509555195
                descriptor_count = unpack('<H', fh.read(2))[0]
                for _ in range(descriptor_count):
                    name_len = unpack('<H', fh.read(2))[0]
                    name = self._decode_string(fh.read(name_len))
                    value_type, value_len = unpack('<HH', fh.read(4))
                    if value_type == 1:
                        fh.seek(value_len, SEEK_CUR)  # skip byte values
                        continue
                    field_name = self._ASF_MAPPING.get(name)  # try to get normalized field name
                    if field_name is None:  # custom field
                        if name.startswith('WM/'):
                            name = name[3:]
                        field_name = self._EXTRA_PREFIX + name.lower()
                    field_value = self._decode_ext_desc(value_type, fh.read(value_len))
                    if field_value is not None:
                        if field_name in {'track', 'disc'}:
                            if isinstance(field_value, int) or field_value.isdecimal():
                                self._set_field(field_name, int(field_value))
                        elif field_value:
                            self._set_field(field_name, field_value)
            elif object_id == self._ASF_FILE_PROPERTY_OBJECT and self._parse_duration:
                fh.seek(40, SEEK_CUR)
                play_duration = unpack('<Q', fh.read(8))[0] / 10000000
                fh.seek(8, SEEK_CUR)
                preroll = unpack('<Q', fh.read(8))[0] / 1000
                fh.seek(16, SEEK_CUR)
                # According to the specification, we need to subtract the preroll from play_duration
                # to get the actual duration of the file
                self.duration = max(play_duration - preroll, 0.0)
            elif object_id == self._ASF_STREAM_PROPERTIES_OBJECT and self._parse_duration:
                stream_type = fh.read(16)
                fh.seek(24, SEEK_CUR)  # skip irrelevant fields
                type_specific_data_length, error_correction_data_length = unpack('<II', fh.read(8))
                fh.seek(6, SEEK_CUR)   # skip irrelevant fields
                already_read = 0
                if stream_type == self._STREAM_TYPE_ASF_AUDIO_MEDIA:
                    (codec_id_format_tag, self.channels, self.samplerate,
                     avg_bytes_per_second) = unpack('<HHII', fh.read(12))
                    self.bitrate = avg_bytes_per_second * 8 / 1000
                    fh.seek(2, SEEK_CUR)  # skip irrelevant field
                    bits_per_sample = unpack('<H', fh.read(2))[0]
                    if codec_id_format_tag == 355:  # lossless
                        self.bitdepth = bits_per_sample
                    already_read = 16
                fh.seek(type_specific_data_length - already_read, SEEK_CUR)
                fh.seek(error_correction_data_length, SEEK_CUR)
            else:
                fh.seek(object_size - 24, SEEK_CUR)  # read over onknown object ids
        self._tags_parsed = True


class _Aiff(TinyTag):
    #
    # AIFF is part of the IFF family of file formats.
    #
    # https://en.wikipedia.org/wiki/Audio_Interchange_File_Format#Data_format
    # https://web.archive.org/web/20171118222232/http://www-mmsp.ece.mcgill.ca/documents/audioformats/aiff/aiff.html
    # https://web.archive.org/web/20071219035740/http://www.cnpbagwell.com/aiff-c.txt
    #
    # A few things about the spec:
    #
    # * IFF strings are not supposed to be null terminated.  They sometimes are.
    # * Some tools might throw more metadata into the ANNO chunk but it is
    #   wildly unreliable to count on it. In fact, the official spec recommends against
    #   using it. That said... this code throws the ANNO field into comment and hopes
    #   for the best.
    #
    # The key thing here is that AIFF metadata is usually in a handful of fields
    # and the rest is an ID3 or XMP field.  XMP is too complicated and only Adobe-related
    # products support it. The vast majority use ID3. As such, this code inherits from
    # ID3 rather than TinyTag since it does everything that needs to be done here.
    #

    _AIFF_MAPPING = {
        #
        # "Name Chunk text contains the name of the sampled sound."
        #
        # "Author Chunk text contains one or more author names.  An author in
        # this case is the creator of a sampled sound."
        #
        # "Annotation Chunk text contains a comment.  Use of this chunk is
        # discouraged within FORM AIFC." Some tools: "hold my beer"
        #
        # "The Copyright Chunk contains a copyright notice for the sound.  text
        #  contains a date followed by the copyright owner.  The chunk ID '[c] '
        # serves as the copyright character. " Some tools: "hold my beer"
        #
        b'NAME': 'title',
        b'AUTH': 'artist',
        b'ANNO': 'comment',
        b'(c) ': 'extra.copyright',
    }

    def _parse_tag(self, fh: BinaryIO) -> None:
        chunk_id, _size, form = unpack('>4sI4s', fh.read(12))
        if chunk_id != b'FORM' or form not in (b'AIFC', b'AIFF'):
            raise ParseError('Invalid AIFF header')
        chunk_header = fh.read(8)
        while len(chunk_header) == 8:
            sub_chunk_id, sub_chunk_size = unpack('>4sI', chunk_header)
            sub_chunk_size += sub_chunk_size % 2  # IFF chunks are padded to an even number of bytes
            if sub_chunk_id in self._AIFF_MAPPING and self._parse_tags:
                value = self._unpad(fh.read(sub_chunk_size).decode('utf-8', 'replace'))
                self._set_field(self._AIFF_MAPPING[sub_chunk_id], value)
            elif sub_chunk_id == b'COMM' and self._parse_duration:
                channels, num_frames, bitdepth = unpack('>hLh', fh.read(8))
                self.channels, self.bitdepth = channels, bitdepth
                try:
                    exponent, mantissa = unpack('>HQ', fh.read(10))   # Extended precision
                    samplerate = int(mantissa * (2 ** (exponent - 0x3FFF - 63)))
                    duration = num_frames / samplerate
                    bitrate = samplerate * channels * bitdepth / 1000
                    self.samplerate, self.duration, self.bitrate = samplerate, duration, bitrate
                except OverflowError:
                    pass
                fh.seek(sub_chunk_size - 18, 1)  # skip remaining data in chunk
            elif sub_chunk_id in {b'id3 ', b'ID3 '} and self._parse_tags:
                id3 = _ID3()
                id3._filehandler = fh
                id3._load(tags=True, duration=False, image=self._load_image)
                self._update(id3)
            else:  # some other chunk, just skip the data
                fh.seek(sub_chunk_size, 1)
            chunk_header = fh.read(8)
        self._tags_parsed = True

    def _determine_duration(self, fh: BinaryIO) -> None:
        if not self._tags_parsed:
            self._parse_tag(fh)
