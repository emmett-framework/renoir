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

from ..errors import TemplateError
from .contents import (
    WriterNode, EscapeNode, HTMLNode,
    PrettyWriterNode, PrettyEscapeNode, PrettyHTMLNode, PrettyHTMLPreNode
)
from .lexers import default_lexers
from .stack import Context


class TemplateParser:
    _nodes_cls = {
        'writer': WriterNode,
        'escape': EscapeNode,
        'html': HTMLNode,
        'htmlpre': HTMLNode
    }

    r_multiline = re.compile(r'(""".*?""")|(\'\'\'.*?\'\'\')', re.DOTALL)

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

    def _get_file_text(self, ctx, filename):
        #: remove quotation from filename string
        try:
            filename = eval(filename, self.scope)
        except Exception:
            raise TemplateError(
                'Invalid template filename', ctx.state.source, ctx.state.lines)
        #: get the file contents
        path, file_name = self.templater.preload(filename)
        file_path = os.path.join(path, file_name)
        try:
            text = self.templater.load(file_path)
        except Exception:
            raise TemplateError(
                'Unable to open included view file',
                ctx.state.source, ctx.state.lines)
        text = self.templater.prerender(text, file_path)
        return filename, file_path, text

    def parse_html_block(self, ctx, element):
        lines = element.split("\n")
        ctx.update_lines_count(len(lines) - 1)
        new_lines = [line for line in lines if line]
        if new_lines:
            ctx.html('\n'.join(new_lines))

    def _get_python_block_text(self, element):
        return element[self.delimiters_len[0]:-self.delimiters_len[1]].strip()

    def _parse_python_line(self, ctx, line):
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
            lexer(ctx, value=value)
            return
        #: otherwise add as a python node
        ctx.python_node(line)

    def parse_python_block(self, ctx, element):
        #: get rid of delimiters
        text = self._get_python_block_text(element)
        if not text:
            return
        ctx.update_lines_count(len(text.split('\n')) - 1)
        #: escape new lines on comment blocks
        text = re.sub(self.r_multiline, _escape_newlines, text)
        #: parse block lines
        lines = text.split('\n')
        for line in lines:
            self._parse_python_line(ctx, line.strip())

    def _parse_plain_contents(self, ctx, stripped, original):
        if stripped == 'end':
            #: use appropriate lexer if available for current lex
            lexer = self.lexers.get(stripped)
            lexer(ctx, value=None)
            return
        #: otherwise add as a plain node
        ctx.html(original)

    def ignore_block(self, ctx, element):
        #: get rid of delimiters
        text = self._get_python_block_text(element)
        if not text:
            return
        ctx.update_lines_count(len(text.split('\n')) - 1)
        #: parse block lines
        self._parse_plain_contents(ctx, text.strip(), element)

    def _build_ctx(self, text):
        return Context(
            self, self.name, text, self.scope, self._nodes_cls['writer'],
            self._nodes_cls['escape'], self._nodes_cls['html'],
            self._nodes_cls['htmlpre']
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
        return self.reindent(self.content.render(self))


class PrettyTemplateParser(TemplateParser):
    _nodes_cls = {
        'writer': PrettyWriterNode,
        'escape': PrettyEscapeNode,
        'html': PrettyHTMLNode,
        'htmlpre': PrettyHTMLPreNode
    }

    r_wspace = re.compile("^( *)")

    @staticmethod
    def _check_html_pre(ctx, line):
        if not ctx._in_html_pre and '<pre' in line and '</pre>' not in line:
            return True, False
        if ctx._in_html_pre and '</pre>' in line:
            return False, True
        return False, False

    @staticmethod
    def _start_html_pre(ctx, start):
        if start:
            ctx._in_html_pre = True

    @staticmethod
    def _end_html_pre(ctx, end):
        if end:
            ctx._in_html_pre = False

    def parse_html_block(self, ctx, element):
        lines = element.split("\n")
        ctx.update_lines_count(len(lines) - 1)
        #: remove empty lines if needed
        removed_last_line = False
        if not lines[0]:
            lines.pop(0)
            ctx.state.new_line = True
        if lines and not lines[-1]:
            lines.pop()
            removed_last_line = True
        #: process lines
        line = None
        for line in lines:
            empty_line = not line
            indent = len(self.r_wspace.search(line).group(0))
            start_pre, end_pre = self._check_html_pre(ctx, line)
            self._end_html_pre(ctx, end_pre)
            line = line[indent:]
            ctx.state.indent = indent
            if line or empty_line:
                ctx.html(line)
            self._start_html_pre(ctx, start_pre)
            ctx.state.new_line = True
        #: set correct `new_line` state depending on last line
        if line and not removed_last_line:
            ctx.state.new_line = False
        else:
            ctx.state.new_line = True


def _escape_newlines(re_val):
    #: take the entire match and replace newlines with escaped newlines
    return re_val.group(0).replace('\n', '\\n')
