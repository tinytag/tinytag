"""Audio file metadata reader"""

from .tinytag import (
    ParseError, TinyTag, TagImage, TagImages, TinyTagException, UnsupportedFormatError
)
__all__ = (
    "ParseError", "TinyTag", "TagImage", "TagImages", "TinyTagException", "UnsupportedFormatError"
)
