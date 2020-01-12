# -*- coding: utf-8 -*-
"""
    tests.extensions
    ----------------

    Tests extensions module.
"""

import pytest

from renoir import Renoir, Extension, Lexer


class FooLexer(Lexer):
    def process(self, ctx, value):
        ctx.html(value * 2)


class FooExtension(Extension):
    namespace = 'foo'
    lexers = {'foo': FooLexer}

    def render(self, source, name):
        return source + 'foo'


class BarExtension(Extension):
    namespace = 'bar'
    file_extension = 'test'

    def load(self, path, file_name):
        return path, file_name + '.bar'

    def context(self, context):
        context['bar'] = True


@pytest.fixture(scope='function')
def templater():
    rv = Renoir()
    rv.use_extension(FooExtension)
    rv.use_extension(BarExtension)
    return rv


def test_config(templater):
    assert set(templater.loaders.keys()) == {'.test'}
    assert len(templater.loaders['.test']) == 1
    assert templater.loaders['.test'][0].__self__.__class__ == BarExtension

    assert len(templater.renderers) == 1
    assert templater.renderers[0].__self__.__class__ == FooExtension

    assert len(templater.contexts) == 1
    assert templater.contexts[0].__self__.__class__ == BarExtension

    assert set(templater.lexers.keys()) == {'foo'}
    assert isinstance(templater.lexers['foo'], FooLexer)


def test_load(templater):
    path, name = templater.preload('test.html.test')
    assert name == 'test.html.test.bar'


def test_render(templater):
    source = templater.prerender('test', '<string>')
    assert source == 'testfoo'


def test_context(templater):
    ctx = {'foo': False}
    templater.inject(ctx)
    assert ctx['foo'] is False
    assert ctx['bar'] is True


def test_lexers(templater):
    r = templater._render(source='{{foo asd}}')
    assert r == 'asdasd'
