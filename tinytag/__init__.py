"""Audio file metadata reader"""

from .tinytag import (
    TinyTag, Extra, Image, Images, ImagesExtra,
    TinyTagException, ParseError, UnsupportedFormatError
)
__all__ = (
    "TinyTag", "Extra", "Image", "Images", "ImagesExtra",
    "TinyTagException", "ParseError", "UnsupportedFormatError"
)
