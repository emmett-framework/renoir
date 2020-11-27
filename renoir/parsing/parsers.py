# -*- coding: utf-8 -*-
"""
    renoir.parsing.parser
    ---------------------

    Provides the templating parser.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

import os
import re

from pathlib import Path

from ..errors import TemplateError
from .contents import (
    WriterNode, PlainNode, WrappedNode, HTMLEscapeNode
)
from .lexers import default_lexers
from .stack import Context, HTMLContext


class TemplateParser:
    _nodes_cls = {
        'writer': WriterNode,
        'plain': PlainNode
    }

    re_multiline = re.compile(r'(""".*?""")|(\'\'\'.*?\'\'\')', re.DOTALL)

    #: re-indentation rules
    re_auto_dedent = re.compile(
        r'^(elif |else:|except:|except |finally:).*$',
        re.DOTALL
    )
    re_dedent = re.compile(
        r'^(return|continue|break|raise)( .*)?$',
        re.DOTALL
    )
    re_pass = re.compile(r'^pass( .*)?$', re.DOTALL)

    def __init__(
        self, templater, text, name="ParserContainer", scope={},
        writer='__writer__', lexers={}, delimiters=('{{', '}}')
    ):
        self.templater = templater
        self.name = name
        self.text = text
        self.writer = writer
        self.scope = scope
        #: lexers to use
        self.lexers = dict(default_lexers)
        self.lexers.update(lexers)
        #: configure delimiters
        self.delimiters = delimiters
        escaped_delimiters = (
            re.escape(delimiters[0]), re.escape(delimiters[1]))
        self.r_tag = re.compile(
            r'((?<!%s)%s.*?%s(?!%s))' % (
                escaped_delimiters[0][0:2], escaped_delimiters[0],
                escaped_delimiters[1], escaped_delimiters[1][-2:]), re.DOTALL)
        self.delimiters_len = (
            len(self.delimiters[0]), len(self.delimiters[1]))
        #: build content
        self.parse(text)

    def _tag_split_text(self, text):
        return self.r_tag.split(text.replace('\t', '    '))

    def _get_file_text(self, ctx, filename, ctxpath=None):
        #: remove quotation from filename string
        try:
            filename = eval(filename, self.scope)
        except Exception:
            raise TemplateError(
                'Invalid template filename', ctx.state.source, ctx.state.lines)
        #: resolve paths
        preload_params = {}
        if any(filename.startswith(relpath) for relpath in ["./", "../"]):
            full_path = (ctxpath / Path(filename)).resolve()
            preload_params["path"] = full_path.parent
            filename = full_path.name
        #: get the file contents
        path, file_name = self.templater.preload(filename, **preload_params)
        file_path = os.path.join(path, file_name)
        try:
            text = self.templater.load(file_path)
        except Exception:
            raise TemplateError(
                'Unable to open included view file',
                ctx.state.source, ctx.state.lines)
        text = self.templater.prerender(text, file_path)
        return filename, file_path, text

    def parse_plain_block(self, ctx, element):
        ctx.update_lines_count(element.linesn)
        ctx.plain(element)

    #: get rid of delimiters
    def _get_python_block_text(self, element):
        return element.text[
            self.delimiters_len[0]:-self.delimiters_len[1]
        ].strip()

    #: escape new lines on python comment blocks
    def _escape_python_multiline_newlines(self, text):
        return re.sub(self.re_multiline, _escape_newlines, text)

    def _parse_python_line(self, ctx, element, line):
        #: get line components for lexers
        if line.startswith('='):
            lex, value = '=', line[1:].strip()
        else:
            v = line.split(' ', 1)
            if len(v) == 1:
                lex = v[0]
                value = ''
            else:
                lex = v[0]
                value = v[1]
        #: use appropriate lexer if available for current lex
        lexer = self.lexers.get(lex)
        if lexer and not value.startswith('='):
            if lexer.remove_line:
                element.strip()
            lexer(ctx, value=value)
            return
        #: otherwise add as a python node
        element.strip()
        ctx.python_node(line)

    def parse_python_block(self, ctx, element):
        text = self._get_python_block_text(element)
        if not text:
            return
        ctx.update_lines_count(element.linesn)
        for line in self._escape_python_multiline_newlines(text).split('\n'):
            self._parse_python_line(ctx, element, line.strip())

    def _parse_raw_contents(self, ctx, element, parsed):
        #: use appropriate lexer
        if parsed == 'end':
            lexer = self.lexers[parsed]
            if lexer.remove_line:
                element.strip()
            lexer(ctx, value=None)
            return
        #: otherwise add as a plain node
        ctx.plain(element)

    def parse_raw_block(self, ctx, element):
        text = self._get_python_block_text(element)
        if not text:
            return
        ctx.update_lines_count(element.linesn)
        self._parse_raw_contents(ctx, element, text.strip())

    def _build_ctx(self, text):
        return Context(
            self, self.name, text, self.scope,
            writer_node_cls=self._nodes_cls['writer'],
            plain_node_cls=self._nodes_cls['plain']
        )

    def parse(self, text):
        ctx = self._build_ctx(text)
        ctx.parse()
        self.content = ctx.content
        self.dependencies = list(set(ctx.state.dependencies))

    def reindent(self, text):
        lines = text.split('\n')
        new_lines = []
        indent = 0
        dedented = 0
        #: parse lines
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            #: apply auto dedenting
            if TemplateParser.re_auto_dedent.match(line):
                indent = indent + dedented - 1
            dedented = 0
            #: apply indentation
            indent = max(indent, 0)
            new_lines.append(' ' * (4 * indent) + line)
            #: dedenting on `pass`
            if TemplateParser.re_pass.match(line):
                indent -= 1
            #: implicit dedent on specific commands
            if TemplateParser.re_dedent.match(line):
                dedented = 1
                indent -= 1
            #: indenting on lines ending with `:`
            if line.endswith(':') and not line.startswith('#'):
                indent += 1
        #: handle indentation errors
        if indent > 0:
            raise TemplateError(
                'missing "pass" in view', self.name, 1)
        elif indent < 0:
            raise TemplateError(
                'too many "pass" in view', self.name, 1)
        #: rebuild text
        return '\n'.join(new_lines)

    def render(self):
        rv = self.reindent(self.content.render(self))
        return rv


class IndentTemplateParser(TemplateParser):
    re_wspace = re.compile("^( *)")

    def parse_plain_block(self, ctx, element):
        lines_element = element.split()
        ctx.update_lines_count(lines_element.linesn)
        for line in lines_element.lines:
            indent = len(self.re_wspace.search(line.text).group(0))
            ctx.state.indent = indent
            line.text = line.text[indent:]
            line.indent = ctx.state.indent
        ctx._plain(WrappedNode, lines_element)


class HTMLTemplateParser(TemplateParser):
    _nodes_cls = {
        'writer': WriterNode,
        'plain': PlainNode,
        'escape': HTMLEscapeNode
    }

    def _build_ctx(self, text):
        return HTMLContext(
            self, self.name, text, self.scope,
            writer_node_cls=self._nodes_cls['writer'],
            plain_node_cls=self._nodes_cls['plain'],
            escape_node_cls=self._nodes_cls['escape']
        )


class HTMLIndentTemplateParser(HTMLTemplateParser, IndentTemplateParser):
    @staticmethod
    def _html_pre_limiters(ctx, line):
        if not ctx.state.in_html_pre and '<pre' in line and '</pre>' not in line:
            return True, False
        if ctx.state.in_html_pre and '</pre>' in line:
            return False, True
        return False, False

    @staticmethod
    def _start_html_pre(ctx, start):
        if start:
            ctx.state.settings['in_html_pre'] = True

    @staticmethod
    def _end_html_pre(ctx, end):
        if end:
            ctx.state.settings['in_html_pre'] = False

    def parse_plain_block(self, ctx, element):
        lines_element = element.split()
        ctx.update_lines_count(lines_element.linesn)
        for line in lines_element.lines:
            indent = len(self.re_wspace.search(line.text).group(0))
            ctx.state.indent = indent
            start_pre, end_pre = self._html_pre_limiters(ctx, line.text)
            self._end_html_pre(ctx, end_pre)
            line.text = line.text[indent:]
            line.indent = ctx.state.indent
            line.ignore_reindent = (
                ctx.state.in_html_pre if not line.ignore_reindent else
                line.ignore_reindent
            )
            self._start_html_pre(ctx, start_pre)
        ctx._plain(WrappedNode, lines_element)


def _escape_newlines(re_val):
    #: take the entire match and replace newlines with escaped newlines
    return re_val.group(0).replace('\n', '\\n')
