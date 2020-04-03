# -*- coding: utf-8 -*-
"""
    renoir.writers
    --------------

    Provides the writers for the templating system.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

from io import StringIO

from ._shortcuts import to_bytes, to_unicode, htmlescape


class Writer:
    def __init__(self):
        self.body = StringIO()

    @staticmethod
    def _to_html(data):
        return htmlescape(data)

    @staticmethod
    def _to_unicode(data):
        if isinstance(data, str):
            return data
        return to_unicode(data)

    def write(self, data):
        self.body.write(self._to_unicode(data))

    def _escape_data(self, data):
        body = None
        if hasattr(data, '__html__'):
            try:
                body = data.__html__()
            except Exception:
                pass
        if body is None:
            body = self._to_html(self._to_unicode(data))
        return body

    def escape(self, data):
        self.write(self._escape_data(data))


class EscapeAll:
    @staticmethod
    def _to_html(data):
        return to_bytes(
            Writer._to_html(data), 'ascii', 'xmlcharrefreplace')


class EscapeAllWriter(EscapeAll, Writer):
    pass
