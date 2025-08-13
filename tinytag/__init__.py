# SPDX-FileCopyrightText: 2014-2024 tinytag Contributors
# SPDX-License-Identifier: MIT

"""Audio file metadata reader."""

__version__ = '2.1.2'

from .tinytag import (
    TinyTag, Image, Images, OtherFields, OtherImages,
    TinyTagException, ParseError, UnsupportedFormatError
)
__all__ = (
    "TinyTag", "Image", "Images", "OtherFields", "OtherImages",
    "TinyTagException", "ParseError", "UnsupportedFormatError"
)
