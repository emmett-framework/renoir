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
    return Renoir(debug=True)


@pytest.fixture(scope='function')
def templater_pretty():
    return Renoir(escape='all', prettify=True, debug=True)


def test_variable(templater, templater_pretty):
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
    assert templater_pretty._render(
        source='{{=a}}',
        context={'a': 'nuvolosità variabile'.encode('utf8')}
    ) == 'nuvolosit&#224; variabile'
    assert templater_pretty._render(
        source='{{=a}}',
        context={'a': 'nuvolosità variabile'}
    ) == 'nuvolosit&#224; variabile'
    assert templater._render(
        source='{{=a}}',
        context={'a': [i for i in range(0, 5)]}
    ) == "[0, 1, 2, 3, 4]"


def test_pycode(templater, templater_pretty):
    #: test if block
    s = (
        "{{if a == 1:}}\nfoo\n{{elif a == 2:}}\nbar"
        "\n{{else:}}\nfoobar\n{{pass}}"
    )
    r = templater._render(source=s, context={'a': 1})
    assert r == "foo"
    r = templater._render(source=s, context={'a': 2})
    assert r == "bar"
    r = templater._render(source=s, context={'a': 25})
    assert r == "foobar"
    #: test for block
    s = "{{for i in range(0, 5):}}\n{{=i}}\n{{pass}}"
    r = templater._render(source=s)
    assert r == "01234"
    r = templater_pretty._render(source=s)
    assert r == "0\n1\n2\n3\n4"


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
