# -*- coding: utf-8 -*-
"""
    renoir._internal
    ----------------

    Provides internally used helpers and objects.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""


def reraise(tp, value, tb=None):
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value
