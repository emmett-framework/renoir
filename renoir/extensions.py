# -*- coding: utf-8 -*-
"""
    renoir.extensions
    -----------------

    Provides base classes to create extensions.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

from typing import Any, Dict, Optional, Tuple, Type

from .parsing.lexers import Lexer


class MetaExtension(type):
    _ext_methods_ = {'load', 'render', 'context'}

    def __new__(cls, name, bases, attrs):
        new_class = type.__new__(cls, name, bases, attrs)
        if not bases:
            return new_class
        declared_methods = cls._ext_methods_ & set(attrs.keys())
        new_class._ext_declared_methods_ = declared_methods
        all_methods = set()
        for base in reversed(new_class.__mro__[:-2]):
            if hasattr(base, '_ext_declared_methods_'):
                all_methods = all_methods | base._ext_declared_methods_
        all_methods = all_methods | declared_methods
        new_class._ext_all_methods_ = all_methods
        new_class._ext_render_ = 'render' in all_methods
        new_class._ext_context_ = 'context' in all_methods
        return new_class


class Extension(metaclass=MetaExtension):
    namespace: Optional[str] = None
    file_extension: Optional[str] = None
    lexers: Dict[str, Type[Lexer]] = {}
    default_config: Dict[str, Any] = {}

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
        self.__load_config()

    def __load_config(self):
        for key, default_val in self.default_config.items():
            self.config[key] = self.config.get(key, default_val)

    def on_load(self):
        pass

    def load(self, path: str, file_name: str) -> Tuple[str, str]:
        return path, file_name

    def render(self, source: str, name: str) -> str:
        return source

    def context(self, context: Dict[str, Any]):
        pass
