"""Audio file metadata reader"""

from .tinytag import (
    ParseError, TinyTag, TagExtra, TagImage, TagImages, TagImagesExtra,
    TinyTagException, UnsupportedFormatError
)
__all__ = (
    "ParseError", "TinyTag", "TagExtra", "TagImage", "TagImages", "TagImagesExtra",
    "TinyTagException", "UnsupportedFormatError"
)
