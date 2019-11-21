# -*- coding: utf-8 -*-
"""
    renoir.lexers
    -------------

    Provides lexers for templates parsing.

    :copyright: (c) 2014-2019 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""


class Lexer:
    evaluate = False

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __call__(self, ctx, value=None):
        if self.evaluate and value is not None:
            value = eval(value, ctx.scope)
        self.process(ctx, value)

    def process(self, ctx, value):
        raise NotImplementedError


class VariableLexer(Lexer):
    def process(self, ctx, value):
        #: insert a variable in the template
        ctx.variable(value)


class BlockLexer(Lexer):
    def process(self, ctx, value):
        #: create a new stack element with name
        with ctx(value):
            ctx.parse()


class EndLexer(Lexer):
    def process(self, ctx, value):
        #: we are done with this node, move up in the stack
        ctx.end_current_step()


class SuperLexer(Lexer):
    def process(self, ctx, value):
        #: create a node for later injection by super block
        target_block = value if value else ctx.name
        node = ctx.node_group()
        ctx.state.injections[target_block] = node


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
                '__include__' + extend_src._id,
                extend_src.elements,
                in_python_block=extend_src.in_python_block,
                source=extend_src.source,
                line_start=extend_src.lines.end
            ):
                ctx.parse()
                extend_src.update_lines_count(
                    ctx.state.lines.end - ctx.state.lines.start)
                included_id = ctx.state._id
        ctx.contents_map[included_id].increment_children_indent(
            ctx.state.indent)


class ExtendLexer(Lexer):
    def process(self, ctx, value):
        #: extend the proper template
        with ctx.load(
            value, extend_map=ctx.state.extend_map or {}, injections={}
        ):
            ctx.state.extend_map[ctx.state.source] = ctx.state.parent
            ctx.parse()
            self.inject_content_in_children(ctx)
            self.replace_extended_blocks(ctx)

    def inject_content_in_children(self, ctx):
        for key, node in ctx.state.injections.items():
            #: get the content to inject
            src = ctx.contents_map[ctx.state.blocks[key]]
            original_indent = src.indent
            #: align src indent with the destination
            src.change_indent(node.indent)
            node.value = list(src.value)
            #: restore the original indent on the block
            src.indent = original_indent

    def replace_extended_blocks(self, ctx):
        for key in set(ctx.state.blocks.keys()) & set(ctx.blocks_tree.keys()):
            #: get destination and source blocks
            dst = ctx.state.blocks[key]
            src = ctx.blocks_tree[key]
            #: update the source indent with the destination one
            ctx.contents_map[src].change_indent(ctx.contents_map[dst].indent)
            ctx.contents_map[dst].value = list(ctx.contents_map[src].value)
            #: cleanup
            ctx.contents_map[src].value = []
            del ctx.contents_map[src]
            del ctx.blocks_tree[key]


class IgnoreLexer(Lexer):
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
    'asis': IgnoreLexer()
}
