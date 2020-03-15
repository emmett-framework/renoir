# -*- coding: utf-8 -*-
"""
    renoir.parsing.stack
    --------------------

    Provides stack helpers for templates parsing.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

import uuid

from collections import namedtuple

from .contents import Node, NodeGroup


ParsedLines = namedtuple('ParsedLines', ('start', 'end'))


class Content:
    __slots__ = ('_contents')

    def __init__(self):
        self._contents = []

    def append(self, element):
        self._contents.append(element)

    def extend(self, *elements):
        for element in elements:
            self.append(element)

    def render(self, parser):
        return ''.join(
            element.__render__(parser) for element in self._contents)

    def reference(self):
        rv = []
        for element in self._contents:
            rv.extend(element.__reference__())
        return rv


class State:
    __slots__ = (
        '_id', 'name', 'source', 'elements', 'blocks', 'lines',
        'in_python_block', 'content', 'parent', 'settings', 'dependencies',
        'indent', 'new_line'
    )

    def __init__(
        self, name, elements, in_python_block=False, parent=None, source=None,
        line_start=1, **settings
    ):
        self._id = uuid.uuid4().hex
        self.name = name
        self.elements = elements
        self.in_python_block = in_python_block
        self.parent = parent
        self.source = source
        self.lines = ParsedLines(line_start, line_start)
        self.settings = settings
        self.content = Content()
        self.blocks = {}
        self.dependencies = []
        self.indent = 0
        self.new_line = True

    def __call__(
        self, name=None, elements=None, in_python_block=None, parent=None,
        source=None, line_start=None, **kwargs
    ):
        name = name or self.name
        elements = self.elements if elements is None else elements
        parent = parent or self
        source = source or parent.source
        settings = dict(**self.settings)
        if in_python_block is None:
            self.swap_block_type()
            in_python_block = parent.in_python_block
            line_start = parent.lines.end if line_start is None else line_start
            settings['isolated_pyblockstate'] = False
        else:
            line_start = 1 if line_start is None else line_start
            settings['isolated_pyblockstate'] = True
        if kwargs:
            settings.update(kwargs)
        return self.__class__(
            name, elements, in_python_block, parent, source, line_start,
            **settings)

    def swap_block_type(self):
        self.in_python_block = not self.in_python_block

    def update_lines_count(self, additional_lines, offset=None):
        start = self.lines.end if offset is None else offset
        self.lines = self.lines._replace(
            start=start, end=start + additional_lines)

    def __getattr__(self, name):
        return self.settings.get(name)


class Context:
    def __init__(
        self, parser, name, text, scope, writer_node_cls, escape_node_cls,
        html_node_cls, htmlpre_node_cls
    ):
        self.parser = parser
        self.stack = []
        self.scope = scope
        self.state = State(
            name,
            self.parser._tag_split_text(text),
            source=name,
            isolated_pyblockstate=True
        )
        self.contents_map = {}
        self.blocks_tree = {}
        self._writer_node_cls = writer_node_cls
        self._escape_node_cls = escape_node_cls
        self._html_node_cls = html_node_cls
        self._htmlpre_node_cls = htmlpre_node_cls
        self._in_html_pre = False

    @property
    def name(self):
        return self.state.name

    @property
    def content(self):
        return self.state.content

    @property
    def elements(self):
        return self.state.elements

    def swap_block_type(self):
        return self.state.swap_block_type()

    def update_lines_count(self, *args, **kwargs):
        return self.state.update_lines_count(*args, **kwargs)

    def __call__(
        self, name=None, elements=None, in_python_block=None, **kwargs
    ):
        self.stack.append(self.state)
        self.state = self.state(
            name=name, elements=elements, in_python_block=in_python_block,
            **kwargs)
        return self

    def load(self, name, **kwargs):
        name, file_path, text = self.parser._get_file_text(self, name)
        self.state.dependencies.append(name)
        kwargs['source'] = file_path
        kwargs['in_python_block'] = False
        return self(
            name=name, elements=self.parser._tag_split_text(text), **kwargs)

    def end_current_step(self):
        self.state.elements = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            raise
        self.swap_block_type()
        deps = list(self.state.dependencies)
        blocks = self.state.blocks
        contents = list(self.content._contents)
        name = self.name
        lines = self.state.lines
        in_python_block = self.state.in_python_block
        isolated_pyblockstate = self.state.isolated_pyblockstate
        state_id = self.state._id
        self.state = self.stack.pop()
        node = self.node_group(contents)
        if not isolated_pyblockstate:
            self.state.in_python_block = in_python_block
            self.update_lines_count(
                lines.end - lines.start, offset=lines.end)
        self.blocks_tree.update(blocks)
        self.state.blocks[name] = state_id
        self.state.dependencies.extend(deps)
        self.contents_map[state_id] = node

    def python_node(self, value=None):
        node = Node(value, source=self.state.source, lines=self.state.lines)
        self.content.append(node)
        return node

    def variable(self, value=None, escape=True):
        node_cls = self._escape_node_cls if escape else self._writer_node_cls
        node = node_cls(
            value, indent=self.state.indent, new_line=self.state.new_line,
            source=self.state.source, lines=self.state.lines)
        self.content.append(node)
        return node

    def node_group(self, value=None):
        node = NodeGroup(value, indent=self.state.indent)
        self.content.append(node)
        return node

    def html(self, value):
        node_cls = (
            self._html_node_cls if not self._in_html_pre else
            self._htmlpre_node_cls)
        self.content.append(
            node_cls(
                value, indent=self.state.indent, new_line=self.state.new_line,
                source=self.state.source, lines=self.state.lines))

    def parse(self):
        while self.elements:
            element = self.elements.pop(0)
            if self.state.in_python_block:
                self.parser.parse_python_block(self, element)
            else:
                self.parser.parse_html_block(self, element)
            self.swap_block_type()

    def ignore(self):
        while self.elements:
            element = self.elements.pop(0)
            if self.state.in_python_block:
                self.parser.ignore_block(self, element)
            else:
                self.parser.parse_html_block(self, element)
            self.swap_block_type()