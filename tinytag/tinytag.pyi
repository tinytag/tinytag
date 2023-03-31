from _typeshed import Incomplete, ReadableBuffer
import io
from pathlib import Path
from collections.abc import Callable
from typing import Any

DEBUG: str | bool #really just bool, but os.environ.get returns str

class TinyTagException(LookupError): ...

def stderr(*args) -> None: ...

class TinyTag:
    filesize: int | None
    album: str | None
    albumartist: str | None
    artist: str | None
    audio_offset: int | None
    bitrate: float | None
    channels: int | None
    comment: str | None
    composer: str | None
    disc: str | None
    disc_total: str | None
    duration: float | None
    extra: dict[str, Any]
    genre: str | None
    samplerate: int | None
    bitdepth: int | None
    title: str | None
    track: str | None
    track_total: str | None
    year: str | None
    def __init__(self, filehandler: io.BufferedReader, filesize: int | None, ignore_errors: bool = ...) -> None: ...
    def as_dict(self) -> dict[str, Any]: ...
    @classmethod
    def is_supported(cls, filename: str | bytes) -> bool: ...
    def get_image(self) -> bytes: ...
    @classmethod
    def get_parser_class(cls, filename: str | bytes, filehandle: io.BufferedReader) -> type[TinyTag]: ...
    @classmethod
    def get(cls, filename: str | bytes | Path, tags: bool = ..., duration: bool = ..., image: bool = ..., ignore_errors: bool = ..., encoding: str | None = ...) -> TinyTag: ...
    def load(self, tags: bool, duration: bool, image: bool = ...) -> None: ...
    def update(self, other: TinyTag) -> None: ...

class MP4(TinyTag):
    class Parser:
        ATOM_DECODER_BY_TYPE: dict[int, Callable[[bytes], Incomplete]]
        @classmethod
        def make_data_atom_parser(cls, fieldname: str) -> Callable[[bytes], dict[str, Incomplete]]: ...
        @classmethod
        def make_number_parser(cls, fieldname1: str, fieldname2: str) -> Callable[[bytes], dict[str, int]]: ...
        @classmethod
        def parse_id3v1_genre(cls, data_atom: bytes) -> dict[str, str | None]: ...
        @classmethod
        def read_extended_descriptor(cls, esds_atom: io.BytesIO) -> None: ...
        @classmethod
        def parse_audio_sample_entry_mp4a(cls, data: ReadableBuffer) -> dict[str, int | float]: ...
        @classmethod
        def parse_audio_sample_entry_alac(cls, data: ReadableBuffer) -> dict[str, int | float]: ...
        @classmethod
        def parse_mvhd(cls, data: ReadableBuffer) -> dict[str, float]: ...
        @classmethod
        def debug_atom(cls, data): ...
    META_DATA_TREE: Incomplete
    AUDIO_DATA_TREE: Incomplete
    IMAGE_DATA_TREE: Incomplete
    VERSIONED_ATOMS: set[bytes]
    FLAGGED_ATOMS: set[bytes]

class ID3(TinyTag):
    FRAME_ID_TO_FIELD: dict[str, str]
    IMAGE_FRAME_IDS: set[str]
    PARSABLE_FRAME_IDS: set[str]
    ID3V1_GENRES: list[str]
    def __init__(self, filehandler: io.BufferedReader, filesize: int | None, *args, **kwargs) -> None: ...
    @classmethod
    def set_estimation_precision(cls, estimation_in_seconds: int) -> None: ...
    samplerates: list[list[int]]
    v1l1: list[int]
    v1l2: list[int]
    v1l3: list[int]
    v2l1: list[int]
    v2l2: list[int]
    v2l3 = v2l2
    bitrate_by_version_by_layer: list[list[None | list[int]] | None]
    samples_per_frame: int
    channels_per_channel_mode: list[int]
    @staticmethod
    def index_utf16(s: bytes, search: bytes) -> int: ...

class Ogg(TinyTag):
    def __init__(self, filehandler: io.BufferedReader, filesize: int | None, *args, **kwargs) -> None: ...

class Wave(TinyTag):
    riff_mapping: dict[bytes, str]
    def __init__(self, filehandler: io.BufferedReader, filesize: int | None, *args, **kwargs) -> None: ...

class Flac(TinyTag):
    METADATA_STREAMINFO: int
    METADATA_PADDING: int
    METADATA_APPLICATION: int
    METADATA_SEEKTABLE: int
    METADATA_VORBIS_COMMENT: int
    METADATA_CUESHEET: int
    METADATA_PICTURE: int
    def load(self, tags: bool, duration: bool, image: bool = ...) -> None: ...

class Wma(TinyTag):
    ASF_CONTENT_DESCRIPTION_OBJECT: bytes
    ASF_EXTENDED_CONTENT_DESCRIPTION_OBJECT: bytes
    STREAM_BITRATE_PROPERTIES_OBJECT: bytes
    ASF_FILE_PROPERTY_OBJECT: bytes
    ASF_STREAM_PROPERTIES_OBJECT: bytes
    STREAM_TYPE_ASF_AUDIO_MEDIA: bytes
    def __init__(self, filehandler: io.BufferedReader, filesize: int | None, *args, **kwargs) -> None: ...
    def read_blocks(self, fh: io.BufferedReader, blocks: list[tuple[str, int, bool]]): ...

class Aiff(ID3):
    aiff_mapping: dict[bytes, str]
    def __init__(self, filehandler: io.BufferedReader, filesize: int | None, *args, **kwargs) -> None: ...
