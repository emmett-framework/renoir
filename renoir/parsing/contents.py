# -*- coding: utf-8 -*-
"""
    renoir.parsing.contents
    -----------------------

    Provides structures for templating system.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

from .._shortcuts import to_unicode
from ..helpers import adict


class Node:
    __slots__ = ('value', 'indent', 'new_line', 'source', 'lines')

    def __init__(
        self, value=None, indent=0, new_line=False, source=None, lines=None
    ):
        self.value = value
        self.indent = indent
        self.new_line = new_line
        self.source = source
        self.lines = lines or (None, None)

    def increment_indent(self, increment):
        self.indent += increment

    def change_indent(self, indent):
        self.indent = indent

    def __render__(self, parser):
        return '\n' + to_unicode(self.value)

    def __reference__(self):
        return [(self.source, self.lines)]

    def _rendered_lines(self):
        return self.__render__(adict(writer='w')).split('\n')[1:]


class NodeGroup(Node):
    __slots__ = ('value', 'indent', 'new_line', 'source', 'lines')

    def __init__(self, value=None, **kwargs):
        value = value or []
        super().__init__(value, **kwargs)

    def increment_children_indent(self, increment):
        for element in self.value:
            element.increment_indent(increment)

    def increment_indent(self, increment):
        self.increment_children_indent(increment)
        self.indent += increment

    def change_indent(self, indent):
        diff = indent - self.indent
        self.increment_children_indent(diff)
        self.indent = indent

    def __render__(self, parser):
        return ''.join(element.__render__(parser) for element in self.value)

    def __reference__(self):
        rv = []
        for element in self.value:
            rv.extend(element.__reference__())
        return rv


class WriterNode(Node):
    __slots__ = ('value', 'indent', 'new_line', 'source', 'lines')

    _writer_method = 'write'
    _newline_val = {True: ', ' + repr('\n'), False: ''}

    def render_value(self):
        return self.value

    def __render__(self, parser):
        return ''.join([
            '\n', parser.writer, '.', self._writer_method, '(',
            to_unicode(self.render_value()), ')'])


class EscapeNode(WriterNode):
    __slots__ = ('value', 'indent', 'new_line', 'source', 'lines')

    _writer_method = 'escape'


class HTMLNode(WriterNode):
    __slots__ = ('value', 'indent', 'new_line', 'source', 'lines')

    def render_value(self):
        return repr(self.value)


class PrettyMixin:
    def __render__(self, parser):
        return ''.join([
            '\n', parser.writer, '.', self._writer_method, '(',
            to_unicode(self.render_value()), ', ',
            to_unicode(self.new_line and self.indent or 0),
            self._newline_val[self.new_line], ')'])


class PrettyWriterNode(PrettyMixin, WriterNode):
    __slots__ = ('value', 'indent', 'new_line', 'source', 'lines')


class PrettyEscapeNode(PrettyMixin, EscapeNode):
    __slots__ = ('value', 'indent', 'new_line', 'source', 'lines')


class PrettyHTMLNode(PrettyMixin, HTMLNode):
    __slots__ = ('value', 'indent', 'new_line', 'source', 'lines')


class PrettyHTMLPreNode(PrettyHTMLNode):
    __slots__ = ('value', 'indent', 'new_line', 'source', 'lines')

    def increment_indent(self, increment):
        return

    def change_indent(self, indent):
        return
