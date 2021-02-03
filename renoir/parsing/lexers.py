# -*- coding: utf-8 -*-
"""
    renoir.parsing.lexers
    ---------------------

    Provides lexers for templates parsing.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""

from typing import Optional

from .stack import Context


class Lexer:
    evaluate: bool = False
    remove_line: bool = False

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __call__(self, ctx: Context, value: Optional[str] = None):
        if self.evaluate and value is not None:
            value = eval(value, ctx.scope)
        self.process(ctx, value)

    def process(self, ctx: Context, value: Optional[str]):
        raise NotImplementedError


class VariableLexer(Lexer):
    def process(self, ctx, value):
        #: insert a variable in the template
        ctx.variable(value)


class BlockLexer(Lexer):
    remove_line = True

    def process(self, ctx, value):
        #: create a new stack element with name
        with ctx(value):
            ctx.parse()


class EndLexer(Lexer):
    remove_line = True

    def process(self, ctx, value):
        #: we are done with this node, move up in the stack
        ctx.end_current_step()


class SuperLexer(Lexer):
    remove_line = True

    def process(self, ctx, value):
        #: create a node for later injection by super block
        target_block = value if value else ctx.name
        node = ctx.node_group()
        ctx.state.injections[ctx.state.extend_src_id][target_block] = node


class IncludeLexer(Lexer):
    def process(self, ctx, value):
        #: if we have a value, just add the new content
        if value:
            with ctx.load(value):
                ctx.parse()
                included_id = ctx.state._id
        #: otherwise, inject in the extended node
        else:
            extend_src = ctx.state.extend_map[ctx.state.source]
            extend_src.swap_block_type()
            with ctx(
                f"__include__{extend_src._id}",
                extend_src.elements,
                in_python_block=extend_src.in_python_block,
                source=extend_src.source,
                line_start=extend_src.lines.end,
                blocks=extend_src.blocks,
                extend_src_id=extend_src._id
            ):
                ctx.parse()
                ctx.state.blocks_map[extend_src._id].update(ctx.state.blocks)
                extend_src.update_lines_count(
                    ctx.state.lines.end - ctx.state.lines.start
                )
                included_id = ctx.state._id
            ctx.state.implicit_extenders.pop(extend_src._id)
        ctx.nodes_map[included_id].increment_children_indent(ctx.state.indent)


class ExtendLexer(Lexer):
    remove_line = True

    def process(self, ctx, value):
        #: extend the proper template
        with ctx.load(
            value,
            blocks_map=ctx.state.blocks_map or {},
            extend_map=ctx.state.extend_map or {},
            implicit_extenders=ctx.state.implicit_extenders or {},
            injections=ctx.state.injections or {}
        ):
            ctx.state.blocks_map[ctx.state.parent._id] = {}
            ctx.state.extend_map[ctx.state.source] = ctx.state.parent
            ctx.state.implicit_extenders[ctx.state.parent._id] = True
            ctx.state.injections[ctx.state.parent._id] = {}
            ctx.parse()
            if ctx.state.implicit_extenders.pop(ctx.state.parent._id, None):
                self._parse_implicit_extender(ctx)
            self.inject_content_in_children(
                ctx, ctx.state.injections[ctx.state.parent._id]
            )
            self.replace_extended_blocks(
                ctx, ctx.state.blocks_map[ctx.state.parent._id]
            )
            ctx.state.injections.pop(ctx.state.parent._id)

    def _parse_implicit_extender(self, ctx):
        extend_src = ctx.state.extend_map[ctx.state.source]
        extend_src.swap_block_type()
        with ctx(
            f"__impl__{extend_src._id}",
            extend_src.elements,
            in_python_block=extend_src.in_python_block,
            source=extend_src.source,
            line_start=extend_src.lines.end,
            blocks=extend_src.blocks,
            extend_src_id=extend_src._id
        ):
            ctx.parse()
            ctx.state.blocks_map[extend_src._id].update(ctx.state.blocks)
            ctx.content.evict()
            extend_src.update_lines_count(
                ctx.state.lines.end - ctx.state.lines.start
            )

    def inject_content_in_children(self, ctx, injections):
        for key, node in injections.items():
            #: get the content to inject
            src = ctx.nodes_map[ctx.state.blocks[key]]
            original_indent = src.indent
            #: align src indent with the destination
            src.change_indent(node.indent)
            node.value = list(src.value)
            #: restore the original indent on the block
            src.indent = original_indent

    def replace_extended_blocks(self, ctx, blocks_map):
        for key in set(ctx.state.blocks.keys()) & set(blocks_map.keys()):
            #: get destination and source blocks
            dst = ctx.state.blocks[key]
            src = blocks_map[key]
            #: update the source indent with the destination one
            ctx.nodes_map[src].change_indent(ctx.nodes_map[dst].indent)
            ctx.nodes_map[dst].value = list(ctx.nodes_map[src].value)
            #: cleanup
            ctx.nodes_map[src].evict()
            ctx.nodes_map[src] = ctx.nodes_map[dst]


class IgnoreLexer(Lexer):
    remove_line = True

    def process(self, ctx, value):
        with ctx('__ignore__'):
            ctx.ignore()


default_lexers = {
    '=': VariableLexer(),
    'block': BlockLexer(),
    'end': EndLexer(),
    'super': SuperLexer(),
    'include': IncludeLexer(),
    'extend': ExtendLexer(),
    'raw': IgnoreLexer()
}
