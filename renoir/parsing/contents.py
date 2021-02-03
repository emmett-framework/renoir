# -*- coding: utf-8 -*-
"""
    renoir.parsing.contents
    -----------------------

    Provides structures for templating system.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

from collections.abc import Sequence
from typing import List, Optional

from .._shortcuts import to_unicode
from ..helpers import adict


class Element:
    __slots__ = [
        'ctx', 'idx', 'text',
        'linesn', 'linesd',
        'nlb', 'nle', 'striplb', 'striple'
    ]

    def __init__(self, ctx: 'Elements', idx: int, text: str):
        self.ctx = ctx
        self.idx = idx
        self.text = text
        self.nlb = False
        self.nle = False
        self.striplb = False
        self.striple = False
        self.linesn = text.count('\n')
        self.linesd = self.linesn + 1
        lsplit = text.split('\n', 1)
        if len(lsplit) > 1 and not lsplit[0].strip(' '):
            self.nlb = True
        rsplit = text.rsplit('\n', 1)
        if len(rsplit) > 1 and not rsplit[-1].rstrip(' '):
            self.nle = True
        if self.prev() is None:
            self.nle = True

    def prev(self) -> Optional['Element']:
        try:
            return self.ctx[self.idx - 1]
        except IndexError:
            return None

    def next(self) -> Optional['Element']:
        try:
            return self.ctx[self.idx + 1]
        except IndexError:
            return None

    def strip_prev(self):
        element = self.prev()
        if element:
            element.striple = True

    def strip_next(self):
        element = self.next()
        if element:
            element.striplb = True

    def strip(self):
        prev_element, next_element = self.prev(), self.next()
        if prev_element is None and next_element is not None:
            if next_element.nlb:
                next_element.striplb = True
            return
        if prev_element.nle and next_element.nlb:
            prev_element.striple = True
            next_element.striplb = True

    def split(self) -> 'ElementSplitted':
        return ElementSplitted(self)

    def __str__(self) -> str:
        rv = self.text
        if self.striple and self.nle:
            rv = rv.rsplit('\n', 1)[0] + '\n'
        if self.striplb and self.nlb:
            rv = rv.split('\n', 1)[-1]
        return rv

    def __bool__(self) -> bool:
        return bool(self.text)


class ElementSplitted:
    __slots__ = ['parent', 'lines']

    def __init__(self, parent: Element):
        self.parent = parent
        self.lines = [
            adict(text=line, indent=0, ignore_reindent=False)
            for line in self.parent.text.split('\n')
        ]
        if not self.nlb:
            self.lines[0].ignore_reindent = True

    @property
    def linesn(self) -> int:
        return self.parent.linesn

    @property
    def linesd(self) -> int:
        return self.parent.linesd

    @property
    def nlb(self) -> bool:
        return self.parent.nlb

    @property
    def nle(self) -> bool:
        return self.parent.nle

    @property
    def striplb(self) -> bool:
        return self.parent.striplb

    @striplb.setter
    def striplb(self, val: bool):
        self.parent.striplb = val

    @property
    def striple(self) -> bool:
        return self.parent.striple

    @striple.setter
    def striple(self, val: bool):
        self.parent.striple = val

    def increment_indent(self, increment: int):
        for line in self.lines:
            if line.ignore_reindent:
                continue
            line.indent += increment

    def change_indent(self, indent: int):
        for line in self.lines:
            if line.ignore_reindent:
                continue
            line.indent = indent

    def __str__(self) -> str:
        lines = []
        for line in self.lines:
            lines.append(
                "{pre}{text}".format(
                    pre=" " * line.indent,
                    text=line.text
                )
            )
        if self.striple and self.nle:
            lines.pop()
            lines.append("")
        if self.striplb and self.nlb:
            lines.pop(0)
        return "\n".join(lines)


class Elements(Sequence):
    __slots__ = ['data']

    def __init__(self, elements: List[str]):
        self.data = []
        for element in elements:
            self.data.append(Element(self, len(self.data), element))

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key: int) -> Element:
        return self.data[key]

    def to_list(self) -> List[Element]:
        return list(self.data)


class Content:
    __slots__ = ['_contents', '_evicted']

    def __init__(self):
        self._contents = []
        self._evicted = False

    def append(self, element):
        self._contents.append(element)

    def extend(self, *elements):
        for element in elements:
            self.append(element)

    def evict(self):
        self._evicted = True

    @property
    def contents(self):
        return [] if self._evicted else list(self._contents)

    def render(self, parser):
        return '' if self._evicted else ''.join(
            element.__render__(parser) for element in self._contents
        )

    def reference(self):
        rv = []
        for element in self._contents:
            rv.extend(element.__reference__())
        return rv


class Node:
    __slots__ = ['value', 'indent', 'source', 'lines']

    def __init__(
        self, value=None, indent=0, source=None, lines=None
    ):
        self.value = value
        self.indent = indent
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
    __slots__ = ['value', 'indent', 'source', 'lines', '_evicted']

    def __init__(self, value=None, **kwargs):
        super().__init__(value or [], **kwargs)
        self._evicted = False

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

    def evict(self):
        self._evicted = True

    def __render__(self, parser):
        return '' if self._evicted else ''.join(
            element.__render__(parser) for element in self.value
        )

    def __reference__(self):
        rv = []
        for element in self.value:
            rv.extend(element.__reference__())
        return rv


class WriterNode(Node):
    __slots__ = ['value', 'indent', 'source', 'lines']
    _writer_method = 'write'

    def render_value(self):
        return str(self.value)

    def __render__(self, parser):
        return ''.join([
            '\n', parser.writer, '.', self._writer_method, '(',
            to_unicode(self.render_value()), ')'])


class PlainNode(WriterNode):
    __slots__ = ['value', 'indent', 'source', 'lines']

    def render_value(self):
        return repr(str(self.value))


class WrappedNode(PlainNode):
    __slots__ = ['value', 'indent', 'source', 'lines']

    def increment_indent(self, increment):
        self.value.increment_indent(increment)
        self.indent += increment

    def change_indent(self, indent):
        diff = indent - self.indent
        self.value.increment_indent(diff)
        self.indent = indent


class HTMLEscapeNode(WriterNode):
    __slots__ = ['value', 'indent', 'source', 'lines']
    _writer_method = 'escape'
