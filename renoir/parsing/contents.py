# -*- coding: utf-8 -*-
"""
renoir.parsing.contents
-----------------------

Provides structures for templating system.

:copyright: 2014 Giovanni Barillari
:license: BSD-3-Clause
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import List, Optional

from .._shortcuts import to_unicode
from ..helpers import adict


class Element:
    __slots__ = [
        "ctx",
        "idx",
        "text",
        "is_python_block",
        "linesn",
        "linesd",
        "strippable_head",
        "strippable_tail",
        "stripped_head",
        "stripped_tail",
        "reindent_skip",
    ]

    def __init__(self, ctx: "Elements", idx: int, text: str, is_python_block: bool = False):
        self.ctx = ctx
        self.idx = idx
        self.text = text
        self.is_python_block = is_python_block
        self.linesn = text.count("\n")
        self.linesd = self.linesn + 1
        self.strippable_head = False
        self.strippable_tail = False
        self.stripped_head = False
        self.stripped_tail = False
        self.reindent_skip = False
        if not text:
            self.strippable_head = False
            self.strippable_tail = False
        else:
            lsplit = text.split("\n", 1)
            rsplit = text.rsplit("\n", 1)
            if not lsplit[0].strip(" "):
                self.strippable_head = True
            if not rsplit[-1].strip(" "):
                self.strippable_tail = True

    def prev(self, positions: int = 1) -> Optional["Element"]:
        idx = self.idx - positions
        if idx < 0:
            return None
        try:
            return self.ctx[idx]
        except IndexError:
            return None

    def next(self, positions: int = 1) -> Optional["Element"]:
        try:
            return self.ctx[self.idx + positions]
        except IndexError:
            return None

    def strip(self, force_reindent_skip: bool = False):
        prev_element, next_element = self.prev(), self.next()
        if prev_element is None and next_element is not None:
            next_element.strip_head()
            next_element.reindent_skip = force_reindent_skip
            return
        if next_element is None:
            return
        if prev_element.strippable_tail and next_element.strippable_head:
            prev_element.strip_tail()
            next_element.strip_head()
            next_element.reindent_skip = force_reindent_skip

    def strip_head(self):
        if not self.strippable_head:
            return
        self.stripped_head = True

    def strip_tail(self):
        if not self.strippable_tail:
            return
        self.stripped_tail = True

    def split(self) -> ElementSplitted:
        return ElementSplitted(self)

    def __str__(self) -> str:
        rv = self.text
        if self.stripped_tail:
            rv = rv.rsplit("\n", 1)[0] + "\n"
        if self.stripped_head:
            rv = rv.split("\n", 1)[-1]
        return rv

    def __bool__(self) -> bool:
        return bool(self.text)

    @property
    def can_arbitrate_reindent(self) -> bool:
        return not bool(str(self))


class ElementSplitted:
    __slots__ = ["parent", "lines"]

    def __init__(self, parent: Element):
        self.parent = parent
        self.lines = [
            adict(text=line, indent=0, original_indent=0, ignore_reindent=False, offset=idx)
            for idx, line in enumerate(self.parent.text.split("\n"))
        ]

    @property
    def linesn(self) -> int:
        return self.parent.linesn

    @property
    def linesd(self) -> int:
        return self.parent.linesd

    def increment_indent(self, increment: int):
        for line in self.lines:
            line.indent += increment

    def change_indent(self, indent: int):
        for line in self.lines:
            line.indent = indent

    def _has_reindent_arbiter(self):
        if self.parent.reindent_skip:
            return False
        if self.parent.stripped_head and self.parent.idx == self.parent.ctx.strip_arbiter.idx:
            return True
        rv, prev = False, self.parent.prev(2)
        while prev is not None:
            if prev.stripped_head and not prev.reindent_skip:
                if prev.idx != self.parent.ctx.strip_arbiter.idx:
                    prev = prev.prev(2)
                else:
                    rv = prev.can_arbitrate_reindent
                    break
            else:
                break
        return rv

    def __str__(self) -> str:
        lines = []
        offsets = (1 if self.parent.stripped_head else None, -1 if self.parent.stripped_tail else None)
        if not self.parent.strippable_head and self.lines:
            self.lines[0].ignore_reindent = True
        if self.parent.stripped_head and self._has_reindent_arbiter():
            self.lines[offsets[0] or 0].ignore_reindent = True
        for line in self.lines[offsets[0] : offsets[1]]:
            lines.append(
                "{pre}{text}".format(
                    pre=(" " * line.original_indent if line.ignore_reindent else " " * line.indent), text=line.text
                )
            )
        if self.parent.stripped_tail:
            lines.append("")
        return "\n".join(lines)

    def __bool__(self) -> bool:
        return bool(str(self))


class Elements(Sequence):
    __slots__ = ["data"]

    def __init__(self, elements: List[str]):
        self.data = []
        in_python_block = False
        offsets = [None, None]
        if len(elements) > 1:
            if not elements[0]:
                offsets[0] = 1
                in_python_block = True
            if not elements[-1]:
                offsets[1] = -1
        for idx, element in enumerate(elements[offsets[0] : offsets[1]]):
            self.data.append(Element(self, idx, element, in_python_block))
            in_python_block = not in_python_block

    @property
    def strip_arbiter(self):
        if not self.data:
            return None
        if not self.data[0].is_python_block:
            return self.data[0]
        if len(self.data) > 1:
            return self.data[1]

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, key: int) -> Element:
        return self.data[key]

    def to_list(self) -> List[Element]:
        return list(self.data)


class Content:
    __slots__ = ["_contents", "_evicted"]

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
        return "" if self._evicted else "".join(element.__render__(parser) for element in self._contents)

    def reference(self):
        rv = []
        for element in self._contents:
            rv.extend(element.__reference__())
        return rv


class Node:
    __slots__ = ["value", "indent", "source", "lines"]

    def __init__(self, value=None, indent=0, source=None, lines=None):
        self.value = value
        self.indent = indent
        self.source = source
        self.lines = lines or (None, None)

    def increment_indent(self, increment):
        self.indent += increment

    def change_indent(self, indent):
        self.indent = indent

    def __render__(self, parser):
        return "\n" + to_unicode(self.value)

    def __reference__(self):
        return [(self.source, self.lines)]

    def _rendered_lines(self):
        return self.__render__(adict(writer="w")).split("\n")[1:]


class NodeGroup(Node):
    __slots__ = ["value", "indent", "source", "lines", "_evicted"]

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
        return "" if self._evicted else "".join(element.__render__(parser) for element in self.value)

    def __reference__(self):
        rv = []
        stack = self.value if not self._evicted else []
        for element in stack:
            rv.extend(element.__reference__())
        return rv


class WriterNode(Node):
    __slots__ = ["value", "indent", "source", "lines"]
    _writer_method = "write"

    def render_value(self):
        return str(self.value)

    def __render__(self, parser):
        v = to_unicode(self.render_value())
        return f"\n{parser.writer}.{self._writer_method}({v})" if v else ""

    def __reference__(self):
        if not to_unicode(self.render_value()):
            return []
        return super().__reference__()


class PlainNode(WriterNode):
    __slots__ = ["value", "indent", "source", "lines"]

    def render_value(self):
        v = str(self.value)
        return repr(v) if v else None


class WrappedNode(PlainNode):
    __slots__ = ["value", "indent", "source", "lines"]

    def increment_indent(self, increment):
        self.value.increment_indent(increment)
        self.indent += increment

    def change_indent(self, indent):
        diff = indent - self.indent
        self.value.increment_indent(diff)
        self.indent = indent


class HTMLEscapeNode(WriterNode):
    __slots__ = ["value", "indent", "source", "lines"]
    _writer_method = "escape"
