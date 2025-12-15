# SPDX-FileCopyrightText: 2014-2024 tinytag Contributors
# SPDX-License-Identifier: MIT

"""Audio file metadata reader."""

__version__ = '2.2.0'

from .tinytag import (
    TinyTag, Image, Images, OtherFields, OtherImages,
    TinyTagException, ParseError, UnsupportedFormatError
)
__all__ = (
    "TinyTag", "Image", "Images", "OtherFields", "OtherImages",
    "TinyTagException", "ParseError", "UnsupportedFormatError"
)
