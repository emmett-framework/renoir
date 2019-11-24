# -*- coding: utf-8 -*-
"""
    renoir.apis
    -----------

    Provides the main apis for the templating system.

    :copyright: (c) 2014-2019 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

import os
import sys

from functools import reduce

from .cache import TemplaterCache
from .debug import make_traceback
from .errors import TemplateError, TemplateMissingError, TemplateSyntaxError
from .extensions import Extension
from .helpers import TemplateReference, ParserCtx, adict
from .parser import TemplateParser, PrettyTemplateParser
from .writers import (
    Writer, EscapeAllWriter,
    IndentWriter, EscapeAllIndentWriter)


class Renoir:
    _writers = {
        'basic': {'common': Writer, 'all': EscapeAllWriter},
        'pretty': {'common': IndentWriter, 'all': EscapeAllIndentWriter}
    }

    def __init__(
        self, path=None,
        loaders=None, renderers=None, contexts=None, lexers=None,
        encoding='utf8', escape='common', prettify=False,
        reload=False, debug=False
    ):
        self.path = path or os.getcwd()
        self.loaders = loaders or {}
        self.renderers = renderers or []
        self.contexts = contexts or []
        self.lexers = lexers or {}
        self.encoding = encoding
        self.escape = escape
        self.prettify = prettify
        self.cache = TemplaterCache(self, reload=reload or debug)
        self._extensions = []
        self._extensions_env = {}
        self._configure()

    def _configure(self):
        writer_group_key = 'pretty' if self.prettify else 'basic'
        writer_group = self._writers[writer_group_key]
        self.writer_cls = writer_group.get(
            self.escape, writer_group['common'])
        self.parser_cls = (
            PrettyTemplateParser if self.prettify else TemplateParser)
        self.preload = self._preload if self.loaders else self._no_preload

    def __init_extension(self, ext_cls):
        namespace = ext_cls.namespace or ext_cls.__name__
        if namespace not in self._extensions_env:
            self._extensions_env[namespace] = adict()
        return namespace, self._extensions_env[namespace]

    def use_extension(self, ext_cls, **config):
        if not issubclass(ext_cls, Extension):
            raise RuntimeError(
                f'{ext_cls.__name__} is an invalid Renoir extension'
            )
        namespace, env = self.__init_extension(ext_cls)
        ext = ext_cls(self, env, config)
        if ext.file_extension:
            self.loaders[ext.file_extension] = (
                self.loaders.get(ext.file_extension) or [])
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

    def _preload(self, file_name):
        file_extension = os.path.splitext(file_name)[1]
        return reduce(
            lambda args, loader: loader(args[0], args[1]),
            self.loaders.get(file_extension, []),
            (self.path, file_name)
        )

    def _no_preload(self, file_name):
        return self.path, file_name

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
                self, source, name=file_path, scope=context,
                lexers=self.lexers)
            try:
                code = compile(
                    parser.render(),
                    os.path.split(file_path)[-1],
                    'exec')
            except SyntaxError:
                parser_ctx = ParserCtx(file_path, parser.content)
                raise TemplateSyntaxError(parser_ctx, *sys.exc_info())
            content = parser.content
            self.cache.parse.set(
                file_path, source, code, content, parser.dependencies)
        return code, content

    def inject(self, context):
        for injector in self.contexts:
            injector(context)

    def _render(self, source='', file_path='<string>', context=None):
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

    def render(self, template_file_name, context=None):
        file_path = os.path.join(*self.preload(template_file_name))
        source = self.prerender(self.load(file_path), file_path)
        return self._render(source, file_path, context)
