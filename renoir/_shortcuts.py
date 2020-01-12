# -*- coding: utf-8 -*-
"""
    renoir._shortcuts
    -----------------

    Some shortcuts

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

import hashlib
import html

hashlib_sha1 = lambda s: hashlib.sha1(bytes(s, 'utf8'))


def to_bytes(obj, charset='utf8', errors='strict'):
    if obj is None:
        return None
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return bytes(obj)
    if isinstance(obj, str):
        return obj.encode(charset, errors)
    raise TypeError('Expected bytes')


def to_unicode(obj, charset='utf8', errors='strict'):
    if obj is None:
        return None
    if not isinstance(obj, bytes):
        return str(obj)
    return obj.decode(charset, errors)


def to_str(obj):
    if not isinstance(obj, str):
        return str(obj)
    return obj


def htmlescape(obj):
    if hasattr(obj, '__html__'):
        return obj.__html__()
    return html.escape(to_str(obj), True).replace("'", "&#39;")
