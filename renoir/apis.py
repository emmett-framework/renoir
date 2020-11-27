# -*- coding: utf-8 -*-
"""
    renoir.apis
    -----------

    Provides the main apis for the templating system.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

import os
import sys

from functools import reduce
from typing import Any, Dict, List, Optional, Type

from .cache import TemplaterCache
from .constants import MODES, ESCAPES, NOFILEPATH
from .debug import make_traceback
from .errors import TemplateError, TemplateMissingError, TemplateSyntaxError
from .extensions import Extension
from .helpers import TemplateReference, ParserCtx, adict
from .parsing import (
    Lexer,
    TemplateParser,
    IndentTemplateParser,
    HTMLTemplateParser,
    HTMLIndentTemplateParser
)
from .typing import LoaderType, RenderType, ContextType
from .writers import (
    Writer,
    EscapeAllWriter
)


class Renoir:
    _writers = {ESCAPES.common: Writer, ESCAPES.all: EscapeAllWriter}

    def __init__(
        self,
        path: Optional[str] = None,
        loaders: Optional[Dict[str, List[LoaderType]]] = None,
        renderers: Optional[List[RenderType]] = None,
        contexts: Optional[List[ContextType]] = None,
        lexers: Optional[Dict[str, Lexer]] = None,
        encoding: str = 'utf8',
        mode: str = MODES.html,
        escape: str = ESCAPES.common,
        adjust_indent: bool = False,
        reload: bool = False,
        debug: bool = False
    ):
        self.path = path or os.getcwd()
        self.loaders = loaders or {}
        self.renderers = renderers or []
        self.contexts = contexts or []
        self.lexers = lexers or {}
        self.encoding = encoding
        self.mode = mode
        self.escape = escape
        self.indent = adjust_indent
        self.cache = TemplaterCache(self, reload=reload or debug)
        self._extensions = []
        self._extensions_env = {}
        self._configure()

    def _configure(self):
        self.writer_cls = self._writers.get(
            self.escape, self._writers[ESCAPES.common]
        )
        if not self.indent:
            self.parser_cls = (
                HTMLTemplateParser if self.mode == MODES.html else
                TemplateParser
            )
        else:
            self.parser_cls = (
                HTMLIndentTemplateParser if self.mode == MODES.html else
                IndentTemplateParser
            )
        self.preload = self._preload if self.loaders else self._no_preload

    def __init_extension(self, ext_cls):
        namespace = ext_cls.namespace or ext_cls.__name__
        if namespace not in self._extensions_env:
            self._extensions_env[namespace] = adict()
        return namespace, self._extensions_env[namespace]

    def use_extension(self, ext_cls: Type[Extension], **config) -> Extension:
        if not issubclass(ext_cls, Extension):
            raise RuntimeError(
                f'{ext_cls.__name__} is an invalid Renoir extension'
            )
        namespace, env = self.__init_extension(ext_cls)
        ext = ext_cls(self, namespace, env, config)
        if ext.file_extension:
            self.loaders[ext.file_extension] = (
                self.loaders.get(ext.file_extension) or []
            )
            self.loaders[ext.file_extension].append(ext.load)
        if ext._ext_render_:
            self.renderers.append(ext.render)
        if ext._ext_context_:
            self.contexts.append(ext.context)
        for name, lexer in ext.lexers.items():
            self.lexers[name] = lexer(ext=ext)
        self._extensions.append(ext)
        ext.on_load()
        self._configure()
        return ext

    def _preload(self, file_name, path=None):
        path = path or self.path
        file_extension = os.path.splitext(file_name)[1]
        return reduce(
            lambda args, loader: loader(args[0], args[1]),
            self.loaders.get(file_extension, []),
            (path, file_name)
        )

    def _no_preload(self, file_name, path=None):
        return (path or self.path, file_name)

    def _load(self, file_path):
        with open(file_path, 'r', encoding=self.encoding) as file_obj:
            source = file_obj.read()
        return source

    def load(self, file_path):
        rv = self.cache.load.get(file_path)
        if not rv:
            try:
                rv = self._load(file_path)
            except Exception:
                raise TemplateMissingError(file_path)
            self.cache.load.set(file_path, rv)
        return rv

    def _prerender(self, source, name):
        return reduce(
            lambda source, renderer: renderer(source, name),
            self.renderers,
            source
        )

    def prerender(self, source, name):
        rv = self.cache.prerender.get(name, source)
        if not rv:
            rv = self._prerender(source, name)
            self.cache.prerender.set(name, source)
        return rv

    def parse(self, file_path, source, context):
        code, content = self.cache.parse.get(file_path, source)
        if not code:
            parser = self.parser_cls(
                self,
                source,
                name=file_path,
                scope=context,
                lexers=self.lexers
            )
            try:
                code = compile(
                    parser.render(),
                    os.path.split(file_path)[-1],
                    'exec'
                )
            except SyntaxError:
                parser_ctx = ParserCtx(file_path, parser.content)
                raise TemplateSyntaxError(parser_ctx, *sys.exc_info())
            content = parser.content
            self.cache.parse.set(
                file_path, source, code, content, parser.dependencies
            )
        return code, content

    def inject(self, context):
        for injector in self.contexts:
            injector(context)

    def _render(self, source='', file_path=NOFILEPATH, context=None):
        context = context or {}
        context['__writer__'] = self.writer_cls()
        try:
            code, content = self.parse(file_path, source, context)
        except (TemplateError, TemplateSyntaxError):
            make_traceback(sys.exc_info())
        self.inject(context)
        try:
            exec(code, context)
        except Exception:
            exc_info = sys.exc_info()
            try:
                parser_ctx = ParserCtx(file_path, content)
                template_ref = TemplateReference(parser_ctx, *exc_info)
            except Exception:
                template_ref = None
            context['__renoir_template__'] = template_ref
            make_traceback(exc_info)
        return context['__writer__'].body.getvalue()

    def render(
        self,
        template_file_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        file_path = os.path.join(*self.preload(template_file_name))
        source = self.prerender(self.load(file_path), file_path)
        return self._render(source, file_path, context)
