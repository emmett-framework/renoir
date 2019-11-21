# -*- coding: utf-8 -*-
"""
    renoir.helpers
    --------------

    Provides helpers.

    :copyright: (c) 2014-2019 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

import traceback


class TemplateReference:
    def __init__(self, parser_ctx, exc_type, exc_value, tb):
        self.parser_ctx = parser_ctx
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.tb = tb
        if hasattr(exc_value, 'lineno'):
            writer_lineno = exc_value.lineno
        else:
            template_frame = traceback.extract_tb(tb, 2)[-1]
            writer_lineno = template_frame[1]
        self.lines = parser_ctx.content.reference()
        self.file_path, self.lineno = self.match_template(writer_lineno)

    def match_template(self, writer_lineno):
        element = self.lines[writer_lineno - 1]
        try:
            reference = (element[0], element[1])
        except Exception:
            reference = (self.parser_ctx.name, ('<unknown>', 'unknown'))
        return reference[0], reference[1][0]


class ParserCtx:
    __slots__ = ('name', 'content')

    def __init__(self, name, content):
        self.name = name
        self.content = content


class adict(dict):
    __setattr__ = dict.__setitem__
    __getattr__ = dict.__getitem__


class cachedprop:
    __slots__ = ('fget', '__doc__', '__name__')

    def __init__(self, fget, doc=None, name=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = name or fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return self
        rv = self.fget(obj)
        setattr(obj, self.__name__, rv)
        return rv