# -*- coding: utf-8 -*-
"""
    renoir.constants
    ----------------

    Provides constants for the templating system.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

from enum import Enum

NOFILEPATH = "<string>"


class MODES(str, Enum):
    html = "html"
    plain = "plain"


class ESCAPES(str, Enum):
    all = "all"
    common = "common"
