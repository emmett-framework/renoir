# -*- coding: utf-8 -*-
"""
tests.parser
------------

Tests parser module.
"""

import sys
import traceback

import pytest

from renoir import Renoir


@pytest.fixture(scope="function")
def templater_plain():
    return Renoir(mode="plain", debug=True)


@pytest.fixture(scope="function")
def templater_escape():
    return Renoir(escape="all", debug=True)


@pytest.fixture(scope="function", params=[False, True], ids=["basic", "auto-indent"])
def ptemplater_plain(request):
    return Renoir(mode="plain", adjust_indent=request.param, debug=True)


def test_variable(templater_plain):
    assert templater_plain._render(source="{{=1}}") == "1"
    assert templater_plain._render(source="{{=a}}", context={"a": list(range(0, 5))}) == "[0, 1, 2, 3, 4]"


def test_variable_encoding(templater_plain):
    assert (
        templater_plain._render(source="{{=a}}", context={"a": "nuvolosità variabile".encode("utf8")})
        == "nuvolosità variabile"
    )
    assert templater_plain._render(source="{{=a}}", context={"a": "nuvolosità variabile"}) == "nuvolosità variabile"


def test_variable_escaping(templater_escape):
    assert (
        templater_escape._render(source="{{=a}}", context={"a": "nuvolosità variabile".encode("utf8")})
        == "nuvolosit&#224; variabile"
    )
    assert (
        templater_escape._render(source="{{=a}}", context={"a": "nuvolosità variabile"}) == "nuvolosit&#224; variabile"
    )


def test_raw(ptemplater_plain):
    s = "{{=1}}{{raw}}{{=1}}{{end}}"
    assert ptemplater_plain._render(source=s) == "1{{=1}}"


def test_pycode_if(ptemplater_plain):
    s = "{{if a == 1:}}\nfoo\n{{elif a == 2:}}\nbar" "\n{{else:}}\nfoobar\n{{pass}}"
    r = ptemplater_plain._render(source=s, context={"a": 1})
    assert r == "foo\n"
    r = ptemplater_plain._render(source=s, context={"a": 2})
    assert r == "bar\n"
    r = ptemplater_plain._render(source=s, context={"a": 25})
    assert r == "foobar\n"


def test_pycode_for(ptemplater_plain):
    s = "{{for i in range(0, 5):}}\n{{=i}}\n{{pass}}"
    r = ptemplater_plain._render(source=s)
    assert r == "\n".join([str(i) for i in range(0, 5)]) + "\n"


@pytest.mark.skipif(sys.version_info < (3, 10), reason="match requires py >= 3.10")
def test_pycode_match(ptemplater_plain):
    s = (
        "{{match a:}}\n"
        "{{case 1:}}\na cat\n"
        "{{case a if a < 5:}}\nfew cats\n"
        "{{case _:}}\nseveral cats\n"
        "{{pass}}showed up again"
    )
    r = ptemplater_plain._render(source=s, context={"a": 1})
    assert r == "a cat\nshowed up again"
    r = ptemplater_plain._render(source=s, context={"a": 3})
    assert r == "few cats\nshowed up again"
    r = ptemplater_plain._render(source=s, context={"a": 25})
    assert r == "several cats\nshowed up again"


def test_python_errors(templater_plain):
    with pytest.raises(ZeroDivisionError) as exc:
        templater_plain._render("foo\n{{=1/0}}\nbar")

    tbs = "".join(traceback.format_exception(exc.type, exc.value, exc.tb))
    frame = exc.traceback[-1]

    frames = []
    tb = exc.tb
    while tb:
        frames.append(tb)
        tb = tb.tb_next
    tb_frame = frames[-1]

    assert frame.name == "template"
    assert str(frame.path) == "<string>"
    assert tb_frame.tb_lineno == 2

    assert '<string>", line 2, in template' in tbs
