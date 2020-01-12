# -*- coding: utf-8 -*-
"""
    renoir.errors
    -------------

    Provides errors.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

from .helpers import TemplateReference


class TemplateMissingError(Exception):
    def __init__(self, file_path):
        self.path = file_path
        self.message = f'Template {self.path} not found'
        super().__init__(self.message)


class TemplateError(Exception):
    def __init__(self, message, file_path, lineno):
        super().__init__(message)
        self.message = message
        self.file_path = file_path
        if isinstance(lineno, tuple):
            lineno = lineno[0]
        self.lineno = lineno


class TemplateSyntaxError(Exception):
    def __init__(self, parser_ctx, exc_type, exc_value, tb):
        super().__init__('invalid syntax')
        self._reference = TemplateReference(
            parser_ctx, exc_type, exc_value, tb)

    @property
    def file_path(self):
        return self._reference.file_path

    @property
    def lineno(self):
        return self._reference.lineno

    @property
    def message(self):
        location = f'File "{self.file_path}", line {self.lineno}'
        lines = [self.args[0], '  ' + location]
        return '\n'.join(lines)
