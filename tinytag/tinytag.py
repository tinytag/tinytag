# tinytag - an audio meta info reader
# Copyright (c) 2014-2023 Tom Wallroth
# Copyright (c) 2021-2024 Mat (mathiascode)
#
# Sources on GitHub:
# http://github.com/devsnd/tinytag/

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

# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
# pylint: disable=invalid-name,protected-access
# pylint: disable=too-many-lines,too-many-arguments,too-many-boolean-expressions
# pylint: disable=too-many-branches,too-many-instance-attributes,too-many-locals
# pylint: disable=too-many-nested-blocks,too-many-statements,too-few-public-methods


from functools import reduce
from sys import stderr
import base64
import io
import os
import re
import struct

DEBUG = bool(os.environ.get('DEBUG'))  # some of the parsers can print debug info


class TinyTagException(Exception):
    pass


class TinyTag:
    SUPPORTED_FILE_EXTENSIONS = [
        '.mp1', '.mp2', '.mp3',
        '.oga', '.ogg', '.opus', '.spx',
        '.wav', '.flac', '.wma',
        '.m4b', '.m4a', '.m4r', '.m4v', '.mp4', '.aax', '.aaxc',
        '.aiff', '.aifc', '.aif', '.afc'
    ]
    _file_extension_mapping = None
    _magic_bytes_mapping = None

    def __init__(self, filehandler, filesize, ignore_errors=False):
        if isinstance(filehandler, str):
            raise TinyTagException('Use `TinyTag.get(filepath)` instead of `TinyTag(filepath)`')
        self._filehandler = filehandler
        self._filename = None  # for debugging purposes
        self._default_encoding = None  # allow override for some file formats
        self.filesize = filesize
        self.album = None
        self.albumartist = None
        self.artist = None
        self.bitrate = None
        self.channels = None
        self.comment = None
        self.disc = None
        self.disc_total = None
        self.duration = None
        self.extra = {}
        self.genre = None
        self.samplerate = None
        self.bitdepth = None
        self.title = None
        self.track = None
        self.track_total = None
        self.year = None
        self._parse_tags = True
        self._parse_duration = True
        self._load_image = False
        self._image_data = None
        self._ignore_errors = ignore_errors
        self._tags_parsed = False

    @classmethod
    def get(cls, filename=None, tags=True, duration=True, image=False,
            ignore_errors=False, encoding=None, file_obj=None):
        should_open_file = file_obj is None
        if should_open_file:
            file_obj = open(filename, 'rb')  # pylint: disable=consider-using-with
        elif isinstance(file_obj, io.BytesIO):
            file_obj = io.BufferedReader(file_obj)  # buffered reader to support peeking
        try:
            file_obj.seek(0, os.SEEK_END)
            filesize = file_obj.tell()
            file_obj.seek(0)
            if filesize <= 0:
                return TinyTag(None, filesize)
            parser_class = cls._get_parser_class(filename, file_obj)
            tag = parser_class(file_obj, filesize, ignore_errors=ignore_errors)
            tag._filename = filename
            tag._default_encoding = encoding
            try:
                tag._load(tags=tags, duration=duration, image=image)
            except Exception as exc:
                raise TinyTagException(f'Failed to parse file: {exc}') from exc
            return tag
        finally:
            if should_open_file:
                file_obj.close()

    def get_image(self):
        return self._image_data

    @classmethod
    def is_supported(cls, filename):
        return cls._get_parser_for_filename(filename) is not None

    def __repr__(self):
        return str(self._as_dict())

    def _as_dict(self):
        return {k: v for k, v in sorted(self.__dict__.items()) if not k.startswith('_')}

    @classmethod
    def _get_parser_for_filename(cls, filename):
        if cls._file_extension_mapping is None:
            cls._file_extension_mapping = {
                (b'.mp1', b'.mp2', b'.mp3'): _ID3,
                (b'.oga', b'.ogg', b'.opus', b'.spx'): _Ogg,
                (b'.wav',): _Wave,
                (b'.flac',): _Flac,
                (b'.wma',): _Wma,
                (b'.m4b', b'.m4a', b'.m4r', b'.m4v', b'.mp4', b'.aax', b'.aaxc'): _MP4,
                (b'.aiff', b'.aifc', b'.aif', b'.afc'): _Aiff,
            }
        if not isinstance(filename, bytes):  # convert filename to binary
            try:
                filename = filename.encode('ASCII', errors='ignore')
            except AttributeError:
                filename = bytes(filename)  # pathlib
        filename = filename.lower()
        for ext, tagclass in cls._file_extension_mapping.items():
            if filename.endswith(ext):
                return tagclass
        return None

    @classmethod
    def _get_parser_for_file_handle(cls, fh):
        # https://en.wikipedia.org/wiki/List_of_file_signatures
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
        header = fh.peek(max(len(sig) for sig in cls._magic_bytes_mapping))
        for magic, parser in cls._magic_bytes_mapping.items():
            if re.match(magic, header):
                return parser
        return None

    @classmethod
    def _get_parser_class(cls, filename=None, filehandle=None):
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
        raise TinyTagException('No tag reader found to support filetype')

    def _load(self, tags, duration, image=False):
        self._parse_tags = tags
        self._parse_duration = duration
        self._load_image = image
        if tags:
            self._parse_tag(self._filehandler)
        if duration:
            if tags:  # rewind file if the tags were already parsed
                self._filehandler.seek(0)
            self._determine_duration(self._filehandler)

    def _set_field(self, fieldname, value):
        """convenience function to set fields of the tinytag by name"""
        write_dest = self.__dict__  # write into the TinyTag by default
        is_str = isinstance(value, str)
        if is_str and not value:
            # don't set empty value
            return
        if fieldname.startswith('extra.'):
            fieldname = fieldname[6:]
            write_dest = self.extra  # write into the extra field instead
        old_value = write_dest.get(fieldname)
        if is_str and old_value and old_value != value:
            # Combine same field with a null character
            value = old_value + '\x00' + value
        if DEBUG:
            print(f'Setting field "{fieldname}" to "{value}"')
        write_dest[fieldname] = value

    def _determine_duration(self, fh):
        raise NotImplementedError()

    def _parse_tag(self, fh):
        raise NotImplementedError()

    def _update(self, other):
        # update the values of this tag with the values from another tag
        for key in ('track', 'track_total', 'title', 'artist',
                    'album', 'albumartist', 'year', 'duration',
                    'genre', 'disc', 'disc_total', 'comment',
                    'bitdepth', 'bitrate', 'channels', 'samplerate',
                    '_image_data'):
            new_value = getattr(other, key)
            if new_value:
                self._set_field(key, new_value)
        for key, value in other.extra.items():
            self._set_field("extra." + key, value)

    @staticmethod
    def _bytes_to_int_le(b):
        fmt = {1: '<B', 2: '<H', 4: '<I', 8: '<Q'}.get(len(b))
        return struct.unpack(fmt, b)[0] if fmt is not None else 0

    @staticmethod
    def _bytes_to_int(b):
        return reduce(lambda accu, elem: (accu << 8) + elem, b, 0)

    @staticmethod
    def _unpad(s):
        # strings in mp3 and asf *may* be terminated with a zero byte at the end
        return s.strip('\x00')


class _MP4(TinyTag):
    # https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/Metadata/Metadata.html
    # https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/QTFFChap2/qtff2.html

    @classmethod
    def _unpack_integer(cls, value, signed=True):
        value_length = len(value)
        if value_length == 1:
            return struct.unpack('>b' if signed else '>B', value)[0]
        if value_length == 2:
            return struct.unpack('>h' if signed else '>H', value)[0]
        if value_length == 4:
            return struct.unpack('>i' if signed else '>I', value)[0]
        if value_length == 8:
            return struct.unpack('>q' if signed else '>Q', value)[0]
        return None

    class _Parser:
        # https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/Metadata/Metadata.html#//apple_ref/doc/uid/TP40000939-CH1-SW34
        ATOM_DECODER_BY_TYPE = {
            # 0: 'reserved'
            1: lambda x: x.decode('utf-8', 'replace'),   # UTF-8
            2: lambda x: x.decode('utf-16', 'replace'),  # UTF-16
            3: lambda x: x.decode('s/jis', 'replace'),   # S/JIS
            # 16: duration in millis
            13: lambda x: x,  # JPEG
            14: lambda x: x,  # PNG
            # pylint: disable=unnecessary-lambda
            21: lambda x: _MP4._unpack_integer(x),                # BE Signed int
            22: lambda x: _MP4._unpack_integer(x, signed=False),  # BE Unsigned int
            23: lambda x: struct.unpack('>f', x)[0],  # BE Float32
            24: lambda x: struct.unpack('>d', x)[0],  # BE Float64
            # 27: lambda x: x,  # BMP
            # 28: lambda x: x,  # QuickTime Metadata atom
            65: lambda x: struct.unpack('b', x)[0],   # 8-bit Signed int
            66: lambda x: struct.unpack('>h', x)[0],  # BE 16-bit Signed int
            67: lambda x: struct.unpack('>i', x)[0],  # BE 32-bit Signed int
            74: lambda x: struct.unpack('>q', x)[0],  # BE 64-bit Signed int
            75: lambda x: struct.unpack('B', x)[0],   # 8-bit Unsigned int
            76: lambda x: struct.unpack('>H', x)[0],  # BE 16-bit Unsigned int
            77: lambda x: struct.unpack('>I', x)[0],  # BE 32-bit Unsigned int
            78: lambda x: struct.unpack('>Q', x)[0],  # BE 64-bit Unsigned int
        }

        @classmethod
        def _make_data_atom_parser(cls, fieldname):
            def _parse_data_atom(data_atom):
                data_type = struct.unpack('>I', data_atom[:4])[0]
                conversion = cls.ATOM_DECODER_BY_TYPE.get(data_type)
                if conversion is None:
                    if DEBUG:
                        print(f'Cannot convert data type: {data_type}', file=stderr)
                    return {}  # don't know how to convert data atom
                # skip header & null-bytes, convert rest
                return {fieldname: conversion(data_atom[8:])}
            return _parse_data_atom

        @classmethod
        def _make_number_parser(cls, fieldname1, fieldname2):
            def _(data_atom):
                number_data = data_atom[8:14]
                numbers = struct.unpack('>HHH', number_data)
                # for some reason the first number is always irrelevant.
                return {fieldname1: numbers[1], fieldname2: numbers[2]}
            return _

        @classmethod
        def _parse_id3v1_genre(cls, data_atom):
            # dunno why the genre is offset by -1 but that's how mutagen does it
            idx = struct.unpack('>H', data_atom[8:])[0] - 1
            if idx < len(_ID3.ID3V1_GENRES):
                return {'genre': _ID3.ID3V1_GENRES[idx]}
            return {'genre': None}

        @classmethod
        def _read_extended_descriptor(cls, esds_atom):
            for _i in range(4):
                if esds_atom.read(1) != b'\x80':
                    break

        @classmethod
        def _parse_custom_field(cls, data):
            fh = io.BytesIO(data)
            header_size = 8
            field_name = None
            data_atom = b''
            atom_header = fh.read(header_size)
            while len(atom_header) == header_size:
                atom_size = struct.unpack('>I', atom_header[:4])[0] - header_size
                atom_type = atom_header[4:]
                if atom_type == b'name':
                    atom_value = fh.read(atom_size)[4:].lower()
                    field_name = 'extra.' + atom_value.decode('utf-8', 'replace')
                elif atom_type == b'data':
                    data_atom = fh.read(atom_size)
                else:
                    fh.seek(atom_size, os.SEEK_CUR)
                atom_header = fh.read(header_size)  # read next atom
            if len(data_atom) < 8:
                return {}
            parser = cls._make_data_atom_parser(field_name)
            return parser(data_atom)

        @classmethod
        def _parse_audio_sample_entry_mp4a(cls, data):
            # this atom also contains the esds atom:
            # https://ffmpeg.org/doxygen/0.6/mov_8c-source.html
            # http://xhelmboyx.tripod.com/formats/mp4-layout.txt
            # http://sasperger.tistory.com/103
            datafh = io.BytesIO(data)
            datafh.seek(16, os.SEEK_CUR)  # jump over version and flags
            channels = struct.unpack('>H', datafh.read(2))[0]
            datafh.seek(2, os.SEEK_CUR)   # jump over bit_depth
            datafh.seek(2, os.SEEK_CUR)   # jump over QT compr id & pkt size
            sr = struct.unpack('>I', datafh.read(4))[0]

            # ES Description Atom
            esds_atom_size = struct.unpack('>I', data[28:32])[0]
            esds_atom = io.BytesIO(data[36:36 + esds_atom_size])
            esds_atom.seek(5, os.SEEK_CUR)   # jump over version, flags and tag

            # ES Descriptor
            cls._read_extended_descriptor(esds_atom)
            esds_atom.seek(4, os.SEEK_CUR)   # jump over ES id, flags and tag

            # Decoder Config Descriptor
            cls._read_extended_descriptor(esds_atom)
            esds_atom.seek(9, os.SEEK_CUR)
            avg_br = struct.unpack('>I', esds_atom.read(4))[0] / 1000  # kbit/s
            return {'channels': channels, 'samplerate': sr, 'bitrate': avg_br}

        @classmethod
        def _parse_audio_sample_entry_alac(cls, data):
            # https://github.com/macosforge/alac/blob/master/ALACMagicCookieDescription.txt
            alac_atom_size = struct.unpack('>I', data[28:32])[0]
            alac_atom = io.BytesIO(data[36:36 + alac_atom_size])
            alac_atom.seek(9, os.SEEK_CUR)
            bitdepth = struct.unpack('b', alac_atom.read(1))[0]
            alac_atom.seek(3, os.SEEK_CUR)
            channels = struct.unpack('b', alac_atom.read(1))[0]
            alac_atom.seek(6, os.SEEK_CUR)
            avg_br = struct.unpack('>I', alac_atom.read(4))[0] / 1000  # kbit/s
            sr = struct.unpack('>I', alac_atom.read(4))[0]
            return {'channels': channels, 'samplerate': sr, 'bitrate': avg_br, 'bitdepth': bitdepth}

        @classmethod
        def _parse_mvhd(cls, data):
            # http://stackoverflow.com/a/3639993/1191373
            walker = io.BytesIO(data)
            version = struct.unpack('b', walker.read(1))[0]
            walker.seek(3, os.SEEK_CUR)  # jump over flags
            if version == 0:  # uses 32 bit integers for timestamps
                walker.seek(8, os.SEEK_CUR)  # jump over create & mod times
                time_scale = struct.unpack('>I', walker.read(4))[0]
                duration = struct.unpack('>I', walker.read(4))[0]
            else:  # version == 1:  # uses 64 bit integers for timestamps
                walker.seek(16, os.SEEK_CUR)  # jump over create & mod times
                time_scale = struct.unpack('>I', walker.read(4))[0]
                duration = struct.unpack('>q', walker.read(8))[0]
            return {'duration': duration / time_scale}

        @classmethod
        def _debug_atom(cls, data):
            print(data)  # use this function to inspect atoms in an atom tree
            return {}

    # The parser tree: Each key is an atom name which is traversed if existing.
    # Leaves of the parser tree are callables which receive the atom data.
    # callables return {fieldname: value} which is updates the TinyTag.
    META_DATA_TREE = {b'moov': {b'udta': {b'meta': {b'ilst': {
        # see: http://atomicparsley.sourceforge.net/mpeg-4files.html
        # and: https://metacpan.org/dist/Image-ExifTool/source/lib/Image/ExifTool/QuickTime.pm#L3093
        b'\xa9ART': {b'data': _Parser._make_data_atom_parser('artist')},
        b'\xa9alb': {b'data': _Parser._make_data_atom_parser('album')},
        b'\xa9cmt': {b'data': _Parser._make_data_atom_parser('comment')},
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
        b'\xa9wrt': {b'data': _Parser._make_data_atom_parser('extra.composer')},
        b'aART': {b'data': _Parser._make_data_atom_parser('albumartist')},
        b'cprt': {b'data': _Parser._make_data_atom_parser('extra.copyright')},
        b'desc': {b'data': _Parser._make_data_atom_parser('extra.description')},
        b'disk': {b'data': _Parser._make_number_parser('disc', 'disc_total')},
        b'gnre': {b'data': _Parser._parse_id3v1_genre},
        b'trkn': {b'data': _Parser._make_number_parser('track', 'track_total')},
        b'tmpo': {b'data': _Parser._make_data_atom_parser('extra.bpm')},
        b'covr': {b'data': _Parser._make_data_atom_parser('_image_data')},
        b'----': _Parser._parse_custom_field,
    }}}}}

    # see: https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/QTFFChap3/qtff3.html
    AUDIO_DATA_TREE = {
        b'moov': {
            b'mvhd': _Parser._parse_mvhd,
            b'trak': {b'mdia': {b"minf": {b"stbl": {b"stsd": {
                b'mp4a': _Parser._parse_audio_sample_entry_mp4a,
                b'alac': _Parser._parse_audio_sample_entry_alac
            }}}}}
        }
    }

    VERSIONED_ATOMS = {b'meta', b'stsd'}  # those have an extra 4 byte header
    FLAGGED_ATOMS = {b'stsd'}  # these also have an extra 4 byte header

    def _determine_duration(self, fh):
        self._traverse_atoms(fh, path=self.AUDIO_DATA_TREE)

    def _parse_tag(self, fh):
        self._traverse_atoms(fh, path=self.META_DATA_TREE)

    def _traverse_atoms(self, fh, path, stop_pos=None, curr_path=None):
        header_size = 8
        atom_header = fh.read(header_size)
        while len(atom_header) == header_size:
            atom_size = struct.unpack('>I', atom_header[:4])[0] - header_size
            atom_type = atom_header[4:]
            if curr_path is None:  # keep track how we traversed in the tree
                curr_path = [atom_type]
            if atom_size <= 0:  # empty atom, jump to next one
                atom_header = fh.read(header_size)
                continue
            if DEBUG:
                print((f'{" " * 4 * len(curr_path)} pos: {fh.tell() - header_size} '
                       f'atom: {atom_type} len: {atom_size + header_size}'))
            if atom_type in self.VERSIONED_ATOMS:  # jump atom version for now
                fh.seek(4, os.SEEK_CUR)
            if atom_type in self.FLAGGED_ATOMS:  # jump atom flags for now
                fh.seek(4, os.SEEK_CUR)
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
                    if fieldname == '_image_data' and not self._load_image:
                        continue
                    if fieldname:
                        self._set_field(fieldname, value)
            # if no action was specified using dict or callable, jump over atom
            else:
                fh.seek(atom_size, os.SEEK_CUR)
            # check if we have reached the end of this branch:
            if stop_pos and fh.tell() >= stop_pos:
                return  # return to parent (next parent node in tree)
            atom_header = fh.read(header_size)  # read next atom


class _ID3(TinyTag):
    FRAME_ID_TO_FIELD = {
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
        'TCOM': 'extra.composer', 'TCM': 'extra.composer',
        'WOAR': 'extra.url', 'WAR': 'extra.url',
        'TSRC': 'extra.isrc',
        'TCOP': 'extra.copyright', 'TCR': 'extra.copyright',
        'TBPM': 'extra.bpm',
        'TKEY': 'extra.initial_key',
        'TLAN': 'extra.language', 'TLA': 'extra.language',
        'TPUB': 'extra.publisher', 'TPB': 'extra.publisher',
        'USLT': 'extra.lyrics', 'ULT': 'extra.lyrics',
    }
    IMAGE_FRAME_IDS = {'APIC', 'PIC'}
    CUSTOM_FRAME_IDS = {'TXXX', 'TXX'}
    DISALLOWED_FRAME_IDS = {'PRIV', 'RGAD', 'GEOB', 'GEO', 'ÿû°d'}
    _MAX_ESTIMATION_SEC = 30
    _CBR_DETECTION_FRAME_COUNT = 5
    _USE_XING_HEADER = True  # much faster, but can be deactivated for testing

    ID3V1_GENRES = [
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
        'Big Band', 'Chorus', 'Easy Listening', 'Acoustic', 'Humour', 'Speech',
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
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # save position after the ID3 tag for duration measurement speedup
        self._bytepos_after_id3v2 = None

    # see this page for the magic values used in mp3:
    # http://www.mpgedit.org/mpgedit/mpeg_format/mpeghdr.htm
    samplerates = [
        [11025, 12000, 8000],   # MPEG 2.5
        [],                     # reserved
        [22050, 24000, 16000],  # MPEG 2
        [44100, 48000, 32000],  # MPEG 1
    ]
    v1l1 = [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 0]
    v1l2 = [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 0]
    v1l3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
    v2l1 = [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 0]
    v2l2 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
    v2l3 = v2l2
    bitrate_by_version_by_layer = [
        [None, v2l3, v2l2, v2l1],  # MPEG Version 2.5  # note that the layers go
        None,                      # reserved          # from 3 to 1 by design.
        [None, v2l3, v2l2, v2l1],  # MPEG Version 2    # the first layer id is
        [None, v1l3, v1l2, v1l1],  # MPEG Version 1    # reserved
    ]
    samples_per_frame = 1152  # the default frame size for mp3
    channels_per_channel_mode = [
        2,  # 00 Stereo
        2,  # 01 Joint stereo (Stereo)
        2,  # 10 Dual channel (2 mono channels)
        1,  # 11 Single channel (Mono)
    ]

    @staticmethod
    def _parse_xing_header(fh):
        # see: http://www.mp3-tech.org/programmer/sources/vbrheadersdk.zip
        fh.seek(4, os.SEEK_CUR)  # read over Xing header
        header_flags = struct.unpack('>i', fh.read(4))[0]
        frames = byte_count = toc = vbr_scale = None
        if header_flags & 1:  # FRAMES FLAG
            frames = struct.unpack('>i', fh.read(4))[0]
        if header_flags & 2:  # BYTES FLAG
            byte_count = struct.unpack('>i', fh.read(4))[0]
        if header_flags & 4:  # TOC FLAG
            toc = [struct.unpack('>i', fh.read(4))[0] for _ in range(25)]  # 100 bytes
        if header_flags & 8:  # VBR SCALE FLAG
            vbr_scale = struct.unpack('>i', fh.read(4))[0]
        return frames, byte_count, toc, vbr_scale

    def _determine_duration(self, fh):
        # if tag reading was disabled, find start position of audio data
        if self._bytepos_after_id3v2 is None:
            self._parse_id3v2_header(fh)

        max_estimation_frames = (_ID3._MAX_ESTIMATION_SEC * 44100) // _ID3.samples_per_frame
        frame_size_accu = 0
        header_bytes = 4
        frames = 0  # count frames for determining mp3 duration
        bitrate_accu = 0    # add up bitrates to find average bitrate to detect
        last_bitrates = []  # CBR mp3s (multiple frames with same bitrates)
        # seek to first position after id3 tag (speedup for large header)
        fh.seek(self._bytepos_after_id3v2)
        while True:
            # reading through garbage until 11 '1' sync-bits are found
            b = fh.peek(4)
            if len(b) < 4:
                if frames:
                    self.bitrate = bitrate_accu / frames
                break  # EOF
            _sync, conf, bitrate_freq, rest = struct.unpack('BBBB', b[0:4])
            br_id = (bitrate_freq >> 4) & 0x0F  # biterate id
            sr_id = (bitrate_freq >> 2) & 0x03  # sample rate id
            padding = 1 if bitrate_freq & 0x02 > 0 else 0
            mpeg_id = (conf >> 3) & 0x03
            layer_id = (conf >> 1) & 0x03
            channel_mode = (rest >> 6) & 0x03
            # check for eleven 1s, validate bitrate and sample rate
            if (not b[:2] > b'\xFF\xE0' or br_id > 14 or br_id == 0 or sr_id == 3
                    or layer_id == 0 or mpeg_id == 1):  # noqa
                idx = b.find(b'\xFF', 1)  # invalid frame, find next sync header
                if idx == -1:
                    idx = len(b)  # not found: jump over the current peek buffer
                fh.seek(max(idx, 1), os.SEEK_CUR)
                continue
            self.channels = self.channels_per_channel_mode[channel_mode]
            frame_bitrate = self.bitrate_by_version_by_layer[mpeg_id][layer_id][br_id]
            self.samplerate = self.samplerates[mpeg_id][sr_id]
            # There might be a xing header in the first frame that contains
            # all the info we need, otherwise parse multiple frames to find the
            # accurate average bitrate
            if frames == 0 and self._USE_XING_HEADER:
                xing_header_offset = b.find(b'Xing')
                if xing_header_offset != -1:
                    fh.seek(xing_header_offset, os.SEEK_CUR)
                    xframes, byte_count, _toc, _vbr_scale = self._parse_xing_header(fh)
                    if xframes and xframes != 0 and byte_count:
                        # MPEG-2 Audio Layer III uses 576 samples per frame
                        samples_per_frame = 576 if mpeg_id <= 2 else self.samples_per_frame
                        self.duration = xframes * samples_per_frame / self.samplerate
                        # self.duration = (xframes * self.samples_per_frame / self.samplerate
                        #                  / self.channels)  # noqa
                        self.bitrate = byte_count * 8 / self.duration / 1000
                        return
                    continue

            frames += 1  # it's most probably an mp3 frame
            bitrate_accu += frame_bitrate
            if frames == 1:
                audio_offset = fh.tell()
            if frames <= self._CBR_DETECTION_FRAME_COUNT:
                last_bitrates.append(frame_bitrate)
            fh.seek(4, os.SEEK_CUR)  # jump over peeked bytes

            frame_length = (144000 * frame_bitrate) // self.samplerate + padding
            frame_size_accu += frame_length
            # if bitrate does not change over time its probably CBR
            is_cbr = (frames == self._CBR_DETECTION_FRAME_COUNT and len(set(last_bitrates)) == 1)
            if frames == max_estimation_frames or is_cbr:
                # try to estimate duration
                fh.seek(-128, 2)  # jump to last byte (leaving out id3v1 tag)
                audio_stream_size = fh.tell() - audio_offset
                est_frame_count = audio_stream_size / (frame_size_accu / frames)
                samples = est_frame_count * self.samples_per_frame
                self.duration = samples / self.samplerate
                self.bitrate = bitrate_accu / frames
                return

            if frame_length > 1:  # jump over current frame body
                fh.seek(frame_length - header_bytes, os.SEEK_CUR)
        if self.samplerate:
            self.duration = frames * self.samples_per_frame / self.samplerate

    def _parse_tag(self, fh):
        self._parse_id3v2(fh)
        if self.filesize > 128:
            fh.seek(-128, os.SEEK_END)  # try parsing id3v1 in last 128 bytes
            self._parse_id3v1(fh)

    def _parse_id3v2_header(self, fh):
        size, extended, major = 0, None, None
        # for info on the specs, see: http://id3.org/Developer%20Information
        header = struct.unpack('3sBBB4B', fh.read(10))
        tag = header[0].decode('ISO-8859-1')
        # check if there is an ID3v2 tag at the beginning of the file
        if tag == 'ID3':
            major, _rev = header[1:3]
            if DEBUG:
                print(f'Found id3 v2.{major}')
            # unsync = (header[3] & 0x80) > 0
            extended = (header[3] & 0x40) > 0
            # experimental = (header[3] & 0x20) > 0
            # footer = (header[3] & 0x10) > 0
            size = self._calc_size(header[4:8], 7)
        self._bytepos_after_id3v2 = size
        return size, extended, major

    def _parse_id3v2(self, fh):
        size, extended, major = self._parse_id3v2_header(fh)
        if size:
            end_pos = fh.tell() + size
            parsed_size = 0
            if extended:  # just read over the extended header.
                size_bytes = struct.unpack('4B', fh.read(6)[0:4])
                extd_size = self._calc_size(size_bytes, 7)
                fh.seek(extd_size - 6, os.SEEK_CUR)  # jump over extended_header
            while parsed_size < size:
                frame_size = self._parse_frame(fh, id3version=major)
                if frame_size == 0:
                    break
                parsed_size += frame_size
            fh.seek(end_pos, os.SEEK_SET)

    def _parse_id3v1(self, fh):
        if fh.read(3) != b'TAG':  # check if this is an ID3 v1 tag
            return
        def asciidecode(x):
            return self._unpad(x.decode(self._default_encoding or 'latin1'))
        # Only set fields that were not set by ID3v2 tags, as ID3v1
        # tags are more likely to be outdated or have encoding issues
        fields = fh.read(30 + 30 + 30 + 4 + 30 + 1)
        if not self.title:
            self._set_field('title', asciidecode(fields[:30]))
        if not self.artist:
            self._set_field('artist', asciidecode(fields[30:60]))
        if not self.album:
            self._set_field('album', asciidecode(fields[60:90]))
        if not self.year:
            self._set_field('year', asciidecode(fields[90:94]))
        comment = fields[94:124]
        if b'\x00\x00' < comment[-2:] < b'\x01\x00':
            if self.track is None:
                self._set_field('track', ord(comment[-1:]))
            comment = comment[:-2]
        if not self.comment:
            self._set_field('comment', asciidecode(comment))
        if not self.genre:
            genre_id = ord(fields[124:125])
            if genre_id < len(self.ID3V1_GENRES):
                self._set_field('genre', self.ID3V1_GENRES[genre_id])

    def __parse_custom_field(self, content):
        custom_field_name, separator, value = content.partition('\x00')
        if custom_field_name and separator:
            self._set_field('extra.' + custom_field_name.lower(), value.lstrip('\ufeff'))
            return True
        return False

    @staticmethod
    def _index_utf16(s, search):
        for i in range(0, len(s), len(search)):
            if s[i:i + len(search)] == search:
                return i
        return -1

    def _parse_frame(self, fh, id3version=False):
        # ID3v2.2 especially ugly. see: http://id3.org/id3v2-00
        frame_header_size = 6 if id3version == 2 else 10
        frame_size_bytes = 3 if id3version == 2 else 4
        binformat = '3s3B' if id3version == 2 else '4s4B2B'
        bits_per_byte = 7 if id3version == 4 else 8  # only id3v2.4 is synchsafe
        frame_header_data = fh.read(frame_header_size)
        if len(frame_header_data) != frame_header_size:
            return 0
        frame = struct.unpack(binformat, frame_header_data)
        frame_id = self._decode_string(frame[0])
        frame_size = self._calc_size(frame[1:1 + frame_size_bytes], bits_per_byte)
        if DEBUG:
            print((f'Found id3 Frame {frame_id} at {fh.tell()}-{fh.tell() + frame_size} '
                   f'of {self.filesize}'))
        if frame_size > 0:
            # flags = frame[1+frame_size_bytes:] # dont care about flags.
            content = fh.read(frame_size)
            fieldname = self.FRAME_ID_TO_FIELD.get(frame_id)
            should_set_field = True
            if fieldname:
                if not self._parse_tags:
                    return frame_size
                language = fieldname in {'comment', 'extra.lyrics'}
                value = self._decode_string(content, language)
                try:
                    if fieldname == "comment":
                        # check if comment is a key-value pair (used by iTunes)
                        should_set_field = not self.__parse_custom_field(value)
                    elif fieldname in {'track', 'disc'}:
                        if '/' in value:
                            value, total = value.split('/')[:2]
                            self._set_field(f'{fieldname}_total', int(total))
                        value = int(value)
                    elif fieldname == 'genre':
                        genre_id = 255
                        # funky: id3v1 genre hidden in a id3v2 field
                        if value.isdigit():
                            genre_id = int(value)
                        # funkier: the TCO may contain genres in parens, e.g. '(13)'
                        elif value[:1] == '(' and value[-1:] == ')' and value[1:-1].isdigit():
                            genre_id = int(value[1:-1])
                        if 0 <= genre_id < len(_ID3.ID3V1_GENRES):
                            value = _ID3.ID3V1_GENRES[genre_id]
                except ValueError as exc:
                    if DEBUG:
                        print(f'Failed to read {fieldname}: {exc}', file=stderr)
                else:
                    if should_set_field:
                        self._set_field(fieldname, value)
            elif frame_id in self.CUSTOM_FRAME_IDS:
                # custom fields
                if self._parse_tags:
                    self.__parse_custom_field(self._decode_string(content))
            elif frame_id in self.IMAGE_FRAME_IDS:
                if self._load_image:
                    # See section 4.14: http://id3.org/id3v2.4.0-frames
                    encoding = content[0:1]
                    if frame_id == 'PIC':  # ID3 v2.2:
                        desc_start_pos = 1 + 3 + 1  # skip encoding (1), imgformat (3), pictype(1)
                    else:  # ID3 v2.3+
                        desc_start_pos = content.index(b'\x00', 1) + 1 + 1  # skip mtype, pictype(1)
                    # latin1 and utf-8 are 1 byte
                    termination = b'\x00' if encoding in {b'\x00', b'\x03'} else b'\x00\x00'
                    desc_length = self._index_utf16(content[desc_start_pos:], termination)
                    desc_end_pos = desc_start_pos + desc_length + len(termination)
                    self._image_data = content[desc_end_pos:]
            elif frame_id not in self.DISALLOWED_FRAME_IDS:
                # unknown, try to add to extra dict
                if self._parse_tags:
                    self._set_field('extra.' + frame_id.lower(), self._decode_string(content))
            return frame_size
        return 0

    def _decode_string(self, bytestr, language=False):
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
            encoding = 'UTF-16be' if bytestr[0:2] == b'\xfe\xff' else 'UTF-16le'
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
        errors = 'ignore' if self._ignore_errors else 'strict'
        return self._unpad(bytestr.decode(encoding, errors))

    @staticmethod
    def _calc_size(bytestr, bits_per_byte):
        # length of some mp3 header fields is described by 7 or 8-bit-bytes
        return reduce(lambda accu, elem: (accu << bits_per_byte) + elem, bytestr, 0)


class _Ogg(TinyTag):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_samplenum = 0  # maximum sample position ever read

    def _determine_duration(self, fh):
        max_page_size = 65536  # https://xiph.org/ogg/doc/libogg/ogg_page.html
        if not self._tags_parsed:
            self._parse_tag(fh)  # determine sample rate
            fh.seek(0)           # and rewind to start
        if self.duration is not None or not self.samplerate:
            return  # either ogg flac or invalid file
        if self.filesize > max_page_size:
            fh.seek(-max_page_size, 2)  # go to last possible page position
        while True:
            b = fh.peek(4)
            if len(b) == 0:
                return  # EOF
            if b[:4] == b'OggS':  # look for an ogg header
                for _ in self._parse_pages(fh):
                    pass  # parse all remaining pages
                self.duration = self._max_samplenum / self.samplerate
            else:
                idx = b.find(b'OggS')  # try to find header in peeked data
                seekpos = idx if idx != -1 else len(b) - 3
                fh.seek(max(seekpos, 1), os.SEEK_CUR)

    def _parse_tag(self, fh):
        check_flac_second_packet = False
        check_speex_second_packet = False
        for packet in self._parse_pages(fh):
            walker = io.BytesIO(packet)
            if packet[0:7] == b"\x01vorbis":
                if self._parse_duration:
                    (_channels, self.samplerate, _max_bitrate, bitrate,
                     _min_bitrate) = struct.unpack("<B4i", packet[11:28])
                    self.bitrate = bitrate / 1000
            elif packet[0:7] == b"\x03vorbis":
                if self._parse_tags:
                    walker.seek(7, os.SEEK_CUR)  # jump over header name
                    self._parse_vorbis_comment(walker)
            elif packet[0:8] == b'OpusHead':
                if self._parse_duration:  # parse opus header
                    # https://www.videolan.org/developers/vlc/modules/codec/opus_header.c
                    # https://mf4.xiph.org/jenkins/view/opus/job/opusfile-unix/ws/doc/html/structOpusHead.html
                    walker.seek(8, os.SEEK_CUR)  # jump over header name
                    (version, ch, _, _sr, _, _) = struct.unpack("<BBHIHB", walker.read(11))
                    if (version & 0xF0) == 0:  # only major version 0 supported
                        self.channels = ch
                        self.samplerate = 48000  # internally opus always uses 48khz
            elif packet[0:8] == b'OpusTags':
                if self._parse_tags:  # parse opus metadata:
                    walker.seek(8, os.SEEK_CUR)  # jump over header name
                    self._parse_vorbis_comment(walker)
            elif packet[0:5] == b'\x7fFLAC':
                # https://xiph.org/flac/ogg_mapping.html
                walker.seek(9, os.SEEK_CUR)  # jump over header name, version and number of headers
                flactag = _Flac(io.BufferedReader(walker), self.filesize)
                flactag._load(tags=self._parse_tags, duration=self._parse_duration,
                              image=self._load_image)
                self._update(flactag)
                check_flac_second_packet = True
            elif check_flac_second_packet:
                # second packet contains FLAC metadata block
                if self._parse_tags:
                    meta_header = struct.unpack('B3B', walker.read(4))
                    block_type = meta_header[0] & 0x7f
                    if block_type == _Flac.METADATA_VORBIS_COMMENT:
                        self._parse_vorbis_comment(walker)
                check_flac_second_packet = False
            elif packet[0:8] == b'Speex   ':
                # https://speex.org/docs/manual/speex-manual/node8.html
                if self._parse_duration:
                    walker.seek(36, os.SEEK_CUR)  # jump over header name and irrelevant fields
                    (self.samplerate, _, _, self.channels,
                     self.bitrate) = struct.unpack("<5i", walker.read(20))
                check_speex_second_packet = True
            elif check_speex_second_packet:
                if self._parse_tags:
                    length = struct.unpack('I', walker.read(4))[0]  # starts with a comment string
                    comment = walker.read(length).decode('UTF-8')
                    self._set_field('comment', comment)
                    self._parse_vorbis_comment(walker, contains_vendor=False)  # other tags
                check_speex_second_packet = False
            else:
                if DEBUG:
                    print('Unsupported Ogg page type: ', packet[:16], file=stderr)
                break
        self._tags_parsed = True

    def _parse_vorbis_comment(self, fh, contains_vendor=True):
        # for the spec, see: http://xiph.org/vorbis/doc/v-comment.html
        # discnumber tag based on: https://en.wikipedia.org/wiki/Vorbis_comment
        # https://sno.phy.queensu.ca/~phil/exiftool/TagNames/Vorbis.html
        comment_type_to_attr_mapping = {
            'album': 'album',
            'albumartist': 'albumartist',
            'title': 'title',
            'artist': 'artist',
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
            'composer': 'extra.composer',
            'bpm': 'extra.bpm',
            'copyright': 'extra.copyright',
            'isrc': 'extra.isrc',
            'lyrics': 'extra.lyrics',
            'publisher': 'extra.publisher',
            'language': 'extra.language',
            'director': 'extra.director',
            'website': 'extra.url',
        }
        if contains_vendor:
            vendor_length = struct.unpack('I', fh.read(4))[0]
            fh.seek(vendor_length, os.SEEK_CUR)  # jump over vendor
        elements = struct.unpack('I', fh.read(4))[0]
        for _i in range(elements):
            length = struct.unpack('I', fh.read(4))[0]
            try:
                keyvalpair = fh.read(length).decode('UTF-8')
            except UnicodeDecodeError:
                continue
            if '=' in keyvalpair:
                key, value = keyvalpair.split('=', 1)
                key_lowercase = key.lower()

                if key_lowercase == "metadata_block_picture" and self._load_image:
                    if DEBUG:
                        print('Found Vorbis Image', key, value[:64])
                    self._image_data = _Flac._parse_image(io.BytesIO(base64.b64decode(value)))
                else:
                    if DEBUG:
                        print('Found Vorbis Comment', key, value[:64])
                    fieldname = comment_type_to_attr_mapping.get(
                        key_lowercase, 'extra.' + key_lowercase)  # custom fields go in 'extra'
                    try:
                        if fieldname in {'track', 'disc'}:
                            if '/' in value:
                                value, total = value.split('/')[:2]
                                self._set_field(f'{fieldname}_total', int(total))
                            value = int(value)
                        elif fieldname in {'track_total', 'disc_total'}:
                            value = int(value)
                    except ValueError as exc:
                        if DEBUG:
                            print(f'Failed to read {fieldname}: {exc}', file=stderr)
                    else:
                        self._set_field(fieldname, value)

    def _parse_pages(self, fh):
        # for the spec, see: https://wiki.xiph.org/Ogg
        previous_page = b''  # contains data from previous (continuing) pages
        header_data = fh.read(27)  # read ogg page header
        while len(header_data) == 27:
            header = struct.unpack('<4sBBqIIiB', header_data)
            # https://xiph.org/ogg/doc/framing.html
            oggs, version, _flags, pos, _serial, _pageseq, _crc, segments = header
            self._max_samplenum = max(self._max_samplenum, pos)
            if oggs != b'OggS' or version != 0:
                raise TinyTagException('Invalid OGG file')
            segsizes = struct.unpack('B' * segments, fh.read(segments))
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
    riff_mapping = {
        b'INAM': 'title',
        b'TITL': 'title',
        b'IPRD': 'album',
        b'IART': 'artist',
        b'IBPM': 'extra.bpm',
        b'ICMT': 'comment',
        b'IMUS': 'extra.composer',
        b'ICOP': 'extra.copyright',
        b'ICRD': 'year',
        b'IGNR': 'genre',
        b'ILNG': 'extra.language',
        b'ISRC': 'extra.isrc',
        b'IPUB': 'extra.publisher',
        b'IPRT': 'track',
        b'ITRK': 'track',
        b'TRCK': 'track',
        b'PRT1': 'track',
        b'PRT2': 'track_number',
        b'IBSU': 'extra.url',
        b'YEAR': 'year',
    }

    def _determine_duration(self, fh):
        if not self._tags_parsed:
            self._parse_tag(fh)

    def _parse_tag(self, fh):
        # see: http://www-mmsp.ece.mcgill.ca/Documents/AudioFormats/WAVE/WAVE.html
        # and: https://en.wikipedia.org/wiki/WAV
        riff, _size, fformat = struct.unpack('4sI4s', fh.read(12))
        if riff != b'RIFF' or fformat != b'WAVE':
            raise TinyTagException('Invalid WAV file')
        self.bitdepth = 16  # assume 16bit depth (CD quality)
        chunk_header = fh.read(8)
        while len(chunk_header) == 8:
            subchunkid, subchunksize = struct.unpack('4sI', chunk_header)
            subchunksize += subchunksize % 2  # IFF chunks are padded to an even number of bytes
            if subchunkid == b'fmt ':
                _, self.channels, self.samplerate = struct.unpack('HHI', fh.read(8))
                _, _, self.bitdepth = struct.unpack('<IHH', fh.read(8))
                if self.bitdepth == 0:
                    # Certain codecs (e.g. GSM 6.10) give us a bit depth of zero.
                    # Avoid division by zero when calculating duration.
                    self.bitdepth = 1
                self.bitrate = self.samplerate * self.channels * self.bitdepth / 1000
                remaining_size = subchunksize - 16
                if remaining_size > 0:
                    fh.seek(remaining_size, 1)  # skip remaining data in chunk
            elif subchunkid == b'data':
                self.duration = subchunksize / self.channels / self.samplerate / (self.bitdepth / 8)
                fh.seek(subchunksize, 1)
            elif subchunkid == b'LIST' and self._parse_tags:
                is_info = fh.read(4)  # check INFO header
                if is_info != b'INFO':  # jump over non-INFO sections
                    fh.seek(subchunksize - 4, os.SEEK_CUR)
                else:
                    sub_fh = io.BytesIO(fh.read(subchunksize - 4))
                    field = sub_fh.read(4)
                    while len(field) == 4:
                        data_length = struct.unpack('I', sub_fh.read(4))[0]
                        data_length += data_length % 2  # IFF chunks are padded to an even size
                        data = sub_fh.read(data_length).split(b'\x00', 1)[0]  # strip zero-byte
                        fieldname = self.riff_mapping.get(field)
                        if fieldname:
                            value = data.decode('utf-8')
                            try:
                                if fieldname == 'track':
                                    value = int(value)
                            except ValueError as exc:
                                if DEBUG:
                                    print(f'Failed to read {fieldname}: {exc}', file=stderr)
                            else:
                                self._set_field(fieldname, value)
                        field = sub_fh.read(4)
            elif subchunkid in {b'id3 ', b'ID3 '} and self._parse_tags:
                id3 = _ID3(fh, 0)
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

    def _determine_duration(self, fh):
        if not self._tags_parsed:
            self._parse_tag(fh)

    def _parse_tag(self, fh):
        id3 = None
        header = fh.peek(4)
        if header[:3] == b'ID3':  # parse ID3 header if it exists
            id3 = _ID3(fh, 0)
            id3._parse_tags = self._parse_tags
            id3._load_image = self._load_image
            id3._parse_id3v2(fh)
            header = fh.peek(4)  # after ID3 should be fLaC
        if header[:4] != b'fLaC':
            raise TinyTagException('Invalid FLAC file')
        fh.seek(4, os.SEEK_CUR)
        # for spec, see https://xiph.org/flac/ogg_mapping.html
        header_data = fh.read(4)
        while len(header_data) == 4:
            meta_header = struct.unpack('B3B', header_data)
            block_type = meta_header[0] & 0x7f
            is_last_block = meta_header[0] & 0x80
            size = self._bytes_to_int(meta_header[1:4])
            # http://xiph.org/flac/format.html#metadata_block_streaminfo
            if block_type == self.METADATA_STREAMINFO and self._parse_duration:
                stream_info_header = fh.read(size)
                if len(stream_info_header) < 34:  # invalid streaminfo
                    break
                header = struct.unpack('HH3s3s8B16s', stream_info_header)
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
                # min_blk, max_blk, min_frm, max_frm = header[0:4]
                # min_frm = self._bytes_to_int(struct.unpack('3B', min_frm))
                # max_frm = self._bytes_to_int(struct.unpack('3B', max_frm))
                #                 channels--.  bits      total samples
                # |----- samplerate -----| |-||----| |---------~   ~----|
                # 0000 0000 0000 0000 0000 0000 0000 0000 0000      0000
                # #---4---# #---5---# #---6---# #---7---# #--8-~   ~-12-#
                self.samplerate = self._bytes_to_int(header[4:7]) >> 4
                self.channels = ((header[6] >> 1) & 0x07) + 1
                self.bitdepth = ((header[6] & 1) << 4) + ((header[7] & 0xF0) >> 4) + 1
                total_sample_bytes = [(header[7] & 0x0F)] + list(header[8:12])
                total_samples = self._bytes_to_int(total_sample_bytes)
                self.duration = total_samples / self.samplerate
                if self.duration > 0:
                    self.bitrate = self.filesize / self.duration * 8 / 1000
            elif block_type == self.METADATA_VORBIS_COMMENT and self._parse_tags:
                oggtag = _Ogg(fh, 0)
                oggtag._parse_vorbis_comment(fh)
                self._update(oggtag)
            elif block_type == self.METADATA_PICTURE and self._load_image:
                self._image_data = self._parse_image(fh)
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

    @staticmethod
    def _parse_image(fh):
        # https://xiph.org/flac/format.html#metadata_block_picture
        _pic_type, mime_len = struct.unpack('>2I', fh.read(8))
        fh.read(mime_len)
        description_len = struct.unpack('>I', fh.read(4))[0]
        fh.read(description_len)
        _width, _height, _depth, _colors, pic_len = struct.unpack('>5I', fh.read(20))
        return fh.read(pic_len)


class _Wma(TinyTag):
    ASF_CONTENT_DESCRIPTION_OBJECT = b'3&\xb2u\x8ef\xcf\x11\xa6\xd9\x00\xaa\x00b\xcel'
    ASF_EXTENDED_CONTENT_DESCRIPTION_OBJECT = (b'@\xa4\xd0\xd2\x07\xe3\xd2\x11\x97\xf0\x00'
                                               b'\xa0\xc9^\xa8P')
    STREAM_BITRATE_PROPERTIES_OBJECT = b'\xceu\xf8{\x8dF\xd1\x11\x8d\x82\x00`\x97\xc9\xa2\xb2'
    ASF_FILE_PROPERTY_OBJECT = b'\xa1\xdc\xab\x8cG\xa9\xcf\x11\x8e\xe4\x00\xc0\x0c Se'
    ASF_STREAM_PROPERTIES_OBJECT = b'\x91\x07\xdc\xb7\xb7\xa9\xcf\x11\x8e\xe6\x00\xc0\x0c Se'
    STREAM_TYPE_ASF_AUDIO_MEDIA = b'@\x9ei\xf8M[\xcf\x11\xa8\xfd\x00\x80_\\D+'
    # see:
    # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx
    # and (japanese, but none the less helpful)
    # http://uguisu.skr.jp/Windows/format_asf.html

    def _determine_duration(self, fh):
        if not self._tags_parsed:
            self._parse_tag(fh)

    def _read_blocks(self, fh, blocks):
        # blocks are a list(tuple('fieldname', byte_count, cast_int), ...)
        decoded = {}
        for block in blocks:
            val = fh.read(block[1])
            if block[2]:
                val = self._bytes_to_int_le(val)
            decoded[block[0]] = val
        return decoded

    def _decode_string(self, bytestring):
        return self._unpad(bytestring.decode('utf-16'))

    def _decode_ext_desc(self, value_type, value):
        """ decode ASF_EXTENDED_CONTENT_DESCRIPTION_OBJECT values"""
        if value_type == 0:  # Unicode string
            return self._decode_string(value)
        if value_type == 1:  # BYTE array
            return value
        if 1 < value_type < 6:  # DWORD / QWORD / WORD
            return self._bytes_to_int_le(value)
        return None

    def _parse_tag(self, fh):
        self._tags_parsed = True
        guid = fh.read(16)  # 128 bit GUID
        if guid != b'0&\xb2u\x8ef\xcf\x11\xa6\xd9\x00\xaa\x00b\xcel':
            # not a valid ASF container! see: http://www.garykessler.net/library/file_sigs.html
            return
        fh.read(12)  # size and obj_count
        if fh.read(2) != b'\x01\x02':
            # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx#_Toc521913958
            return  # not a valid asf header!
        while True:
            object_id = fh.read(16)
            object_size = self._bytes_to_int_le(fh.read(8))
            if object_size == 0 or object_size > self.filesize:
                break  # invalid object, stop parsing.
            if object_id == self.ASF_CONTENT_DESCRIPTION_OBJECT and self._parse_tags:
                len_blocks = self._read_blocks(fh, [
                    ('title_length', 2, True),
                    ('author_length', 2, True),
                    ('copyright_length', 2, True),
                    ('description_length', 2, True),
                    ('rating_length', 2, True),
                ])
                data_blocks = self._read_blocks(fh, [
                    ('title', len_blocks['title_length'], False),
                    ('artist', len_blocks['author_length'], False),
                    ('', len_blocks['copyright_length'], True),
                    ('comment', len_blocks['description_length'], False),
                    ('', len_blocks['rating_length'], True),
                ])
                for field_name, bytestring in data_blocks.items():
                    if field_name:
                        self._set_field(field_name, self._decode_string(bytestring))
            elif object_id == self.ASF_EXTENDED_CONTENT_DESCRIPTION_OBJECT and self._parse_tags:
                mapping = {
                    'WM/TrackNumber': 'track',
                    'WM/PartOfSet': 'disc',
                    'WM/Year': 'year',
                    'WM/AlbumArtist': 'albumartist',
                    'WM/Genre': 'genre',
                    'WM/AlbumTitle': 'album',
                    'WM/Composer': 'extra.composer',
                    'WM/Publisher': 'extra.publisher',
                    'WM/BeatsPerMinute': 'extra.bpm',
                    'WM/InitialKey': 'extra.initial_key',
                    'WM/Lyrics': 'extra.lyrics',
                    'WM/Language': 'extra.language',
                    'WM/AuthorURL': 'extra.url',
                }
                # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx#_Toc509555195
                descriptor_count = self._bytes_to_int_le(fh.read(2))
                for _ in range(descriptor_count):
                    name_len = self._bytes_to_int_le(fh.read(2))
                    name = self._decode_string(fh.read(name_len))
                    value_type = self._bytes_to_int_le(fh.read(2))
                    value_len = self._bytes_to_int_le(fh.read(2))
                    if value_type == 1:
                        fh.seek(value_len, os.SEEK_CUR)  # skip byte values
                        continue
                    field_name = mapping.get(name)  # try to get normalized field name
                    if field_name is None:  # custom field
                        if name.startswith('WM/'):
                            name = name[3:]
                        field_name = 'extra.' + name.lower()
                    field_value = self._decode_ext_desc(value_type, fh.read(value_len))
                    try:
                        if field_name in {'track', 'disc'}:
                            field_value = int(field_value)
                    except ValueError as exc:
                        if DEBUG:
                            print(f'Failed to read {field_name}: {exc}', file=stderr)
                    else:
                        self._set_field(field_name, field_value)
            elif object_id == self.ASF_FILE_PROPERTY_OBJECT:
                blocks = self._read_blocks(fh, [
                    ('file_id', 16, False),
                    ('file_size', 8, False),
                    ('creation_date', 8, True),
                    ('data_packets_count', 8, True),
                    ('play_duration', 8, True),
                    ('send_duration', 8, True),
                    ('preroll', 8, True),
                    ('flags', 4, False),
                    ('minimum_data_packet_size', 4, True),
                    ('maximum_data_packet_size', 4, True),
                    ('maximum_bitrate', 4, False),
                ])
                # According to the specification, we need to subtract the preroll from play_duration
                # to get the actual duration of the file
                preroll = blocks.get('preroll') / 1000
                self.duration = max(blocks.get('play_duration') / 10000000 - preroll, 0.0)
            elif object_id == self.ASF_STREAM_PROPERTIES_OBJECT:
                blocks = self._read_blocks(fh, [
                    ('stream_type', 16, False),
                    ('error_correction_type', 16, False),
                    ('time_offset', 8, True),
                    ('type_specific_data_length', 4, True),
                    ('error_correction_data_length', 4, True),
                    ('flags', 2, True),
                    ('reserved', 4, False)
                ])
                already_read = 0
                if blocks['stream_type'] == self.STREAM_TYPE_ASF_AUDIO_MEDIA:
                    stream_info = self._read_blocks(fh, [
                        ('codec_id_format_tag', 2, True),
                        ('number_of_channels', 2, True),
                        ('samples_per_second', 4, True),
                        ('avg_bytes_per_second', 4, True),
                        ('block_alignment', 2, True),
                        ('bits_per_sample', 2, True),
                    ])
                    self.samplerate = stream_info['samples_per_second']
                    self.bitrate = stream_info['avg_bytes_per_second'] * 8 / 1000
                    if stream_info['codec_id_format_tag'] == 355:  # lossless
                        self.bitdepth = stream_info['bits_per_sample']
                    already_read = 16
                fh.seek(blocks['type_specific_data_length'] - already_read, os.SEEK_CUR)
                fh.seek(blocks['error_correction_data_length'], os.SEEK_CUR)
            else:
                fh.seek(object_size - 24, os.SEEK_CUR)  # read over onknown object ids


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

    aiff_mapping = {
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

    def _parse_tag(self, fh):
        chunk_id, _size, form = struct.unpack('>4sI4s', fh.read(12))
        if chunk_id != b'FORM' or form not in (b'AIFC', b'AIFF'):
            raise TinyTagException('Invalid AIFF file')
        chunk_header = fh.read(8)
        while len(chunk_header) == 8:
            sub_chunk_id, sub_chunk_size = struct.unpack('>4sI', chunk_header)
            sub_chunk_size += sub_chunk_size % 2  # IFF chunks are padded to an even number of bytes
            if sub_chunk_id in self.aiff_mapping and self._parse_tags:
                value = self._unpad(fh.read(sub_chunk_size).decode('utf-8'))
                self._set_field(self.aiff_mapping[sub_chunk_id], value)
            elif sub_chunk_id == b'COMM':
                self.channels, num_frames, self.bitdepth = struct.unpack('>hLh', fh.read(8))
                try:
                    exponent, mantissa = struct.unpack('>HQ', fh.read(10))   # Extended precision
                    self.samplerate = int(mantissa * (2 ** (exponent - 0x3FFF - 63)))
                    self.duration = num_frames / self.samplerate
                    self.bitrate = self.samplerate * self.channels * self.bitdepth / 1000
                except OverflowError:
                    self.samplerate = self.duration = self.bitrate = None  # invalid sample rate
                fh.seek(sub_chunk_size - 18, 1)  # skip remaining data in chunk
            elif sub_chunk_id in {b'id3 ', b'ID3 '} and self._parse_tags:
                id3 = _ID3(fh, 0)
                id3._load(tags=True, duration=False, image=self._load_image)
                self._update(id3)
            elif sub_chunk_id == b'SSND':
                fh.seek(sub_chunk_size, 1)
            else:  # some other chunk, just skip the data
                fh.seek(sub_chunk_size, 1)
            chunk_header = fh.read(8)
        self._tags_parsed = True

    def _determine_duration(self, fh):
        if not self._tags_parsed:
            self._parse_tag(fh)
