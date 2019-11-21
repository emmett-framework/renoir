# -*- coding: utf-8 -*-
"""
    renoir._internal
    ----------------

    Provides internally used helpers and objects.

    :copyright: (c) 2014-2019 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""


def reraise(tp, value, tb=None):
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value
