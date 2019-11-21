# -*- coding: utf-8 -*-
"""
    renoir.extensions
    -----------------

    Provides base classes to create extensions.

    :copyright: (c) 2014-2019 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""


class Extension:
    namespace = None
    file_extension = None
    lexers = {}

    def __init__(self, templater, namespace, env, config=None):
        self.templater = templater
        self.namespace = namespace
        self.env = env
        self.config = config or {}
        if (
            isinstance(self.file_extension, str) and
            not self.file_extension.startswith('.')
        ):
            self.file_extension = '.' + self.file_extension

    def load(self, path, file_name):
        return path, file_name

    def render(self, source, name):
        return source

    def inject(self, context):
        pass
