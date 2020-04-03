# -*- coding: utf-8 -*-
"""
    tests.parser
    ------------

    Tests parser module.
"""

import pytest
import traceback

from renoir import Renoir


@pytest.fixture(scope='function')
def templater():
    return Renoir(mode='plain', debug=True)


@pytest.fixture(scope='function')
def templater_indent():
    return Renoir(mode='plain', adjust_indent=True, debug=True)


@pytest.fixture(scope='function')
def templater_escape():
    return Renoir(escape='all', debug=True)


def test_variable(templater, templater_escape):
    assert templater._render(
        source='{{=1}}'
    ) == '1'
    assert templater._render(
        source='{{=a}}',
        context={'a': 'nuvolosità variabile'.encode('utf8')}
    ) == 'nuvolosità variabile'
    assert templater._render(
        source='{{=a}}',
        context={'a': 'nuvolosità variabile'}
    ) == 'nuvolosità variabile'
    assert templater_escape._render(
        source='{{=a}}',
        context={'a': 'nuvolosità variabile'.encode('utf8')}
    ) == 'nuvolosit&#224; variabile'
    assert templater_escape._render(
        source='{{=a}}',
        context={'a': 'nuvolosità variabile'}
    ) == 'nuvolosit&#224; variabile'
    assert templater._render(
        source='{{=a}}',
        context={'a': [i for i in range(0, 5)]}
    ) == "[0, 1, 2, 3, 4]"


def test_raw(templater, templater_indent):
    s = '{{=1}}{{raw}}{{=1}}{{end}}'
    assert templater._render(
        source=s
    ) == '1{{=1}}'
    assert templater_indent._render(
        source=s
    ) == '1{{=1}}'


def test_pycode(templater, templater_indent):
    #: test if block
    s = (
        "{{if a == 1:}}\nfoo\n{{elif a == 2:}}\nbar"
        "\n{{else:}}\nfoobar\n{{pass}}"
    )
    r = templater._render(source=s, context={'a': 1})
    assert r == "foo\n"
    r = templater._render(source=s, context={'a': 2})
    assert r == "bar\n"
    r = templater._render(source=s, context={'a': 25})
    assert r == "foobar\n"
    #: test for block
    s = "{{for i in range(0, 5):}}\n{{=i}}\n{{pass}}"
    r = templater._render(source=s)
    assert r == "\n".join([str(i) for i in range(0, 5)]) + "\n"
    r = templater_indent._render(source=s)
    assert r == "\n".join([str(i) for i in range(0, 5)]) + "\n"


def test_python_errors(templater):
    with pytest.raises(ZeroDivisionError) as exc:
        templater._render('foo\n{{=1/0}}\nbar')

    tbs = ''.join(traceback.format_exception(exc.type, exc.value, exc.tb))
    frame = exc.traceback[-1]

    frames = []
    tb = exc.tb
    while tb:
        frames.append(tb)
        tb = tb.tb_next
    tb_frame = frames[-1]

    assert frame.name == 'template'
    assert str(frame.path) == '<string>'
    assert tb_frame.tb_lineno == 2

    assert '<string>", line 2, in template' in tbs
