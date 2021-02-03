# -*- coding: utf-8 -*-
"""
    tests.templater
    ---------------

    Tests templater module.
"""

import os
import pytest
import traceback
import yaml

from renoir import Renoir


@pytest.fixture(scope='function')
def templater():
    return Renoir(
        mode='plain', debug=True, path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'yaml'
        )
    )


@pytest.fixture(scope='function')
def templater_indent():
    return Renoir(
        mode='plain', adjust_indent=True, debug=True, path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'yaml'
        )
    )


@pytest.fixture(scope='function')
def templater_html():
    return Renoir(
        debug=True, path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'html'
        )
    )


@pytest.fixture(scope='function')
def templater_html_indent():
    return Renoir(
        escape='all', adjust_indent=True, debug=True,
        path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'html'
        )
    )


yaml_rendered = """
str: str
int: 1
float: 1.2
sfloat: "1.2"
obj:
  nested:
    key: str
    array:
      - foo
      - bar
  array:
    - foo
    - foo: bar
      array:
        - str
        - foo
        - 1
        - 1.2
"""


def test_plain(templater):
    r = templater.render('basic.yaml', {})
    assert r == yaml_rendered[1:]
    data = yaml.load(r, Loader=yaml.SafeLoader)
    assert data['obj']['nested']['array'][1] == "bar"
    assert data['obj']['array'][1]['array'][-1] == 1.2


yaml_indent_rendered = """
str: str
int: 1
float: 1.2
sfloat: "1.2"
obj:
  nested:
    key: str
    array:
      - foo
      - bar
  array:
    - foo
    - foo: bar
      array: []
added:
  indent:
    foo:
      bar:
        - baz
  ints:
    - 2
    - 4
    - 6
    - 8
"""


def test_plain_indent(templater_indent):
    r = templater_indent.render('nested.yaml', {
        'indent': lambda v, i: (
            "\n".join([
                v.split("\n")[0],
                "\n".join([
                    f"{' '*i}{el}" for el in v.split("\n")[1:]
                ])
            ])
        ),
        'additional': "foo:\n  bar:\n    - baz"
    })
    assert "\n".join([l.rstrip() for l in r.splitlines()]) == \
        yaml_indent_rendered[1:]
    data = yaml.load(r, Loader=yaml.SafeLoader)
    assert data['obj']['nested']['array'][1] == "bar"
    assert not data['obj']['array'][1]['array']
    assert data['added']['indent']['foo']['bar'][0] == "baz"
    assert data['added']['ints'][-1] == 8


html_rendered = """
<!DOCTYPE html>
<html>
    <head>
        <title>Test</title>

    </head>
    <body>
        <div>header1</div>

<div>header2</div>
        <div class="page">
            <a href="/" class="title"><h1>Test</h1></a>
            <div class="nav">
                <a href="/">nuvolosità variabile</a>
            </div>


<ul class="posts">
    <li>
        <h2>foo</h2>
        <hr />
    </li>
    <li>
        <h2>bar</h2>
        <hr />
    </li>
</ul>

        </div>
        <div>footer</div>

    </body>
</html>"""


def test_html(templater_html):
    r = templater_html.render(
        'test.html', {
            'posts': [{'title': 'foo'}, {'title': 'bar'}]
        }
    )
    assert "\n".join([l.rstrip() for l in r.splitlines()]) == \
        html_rendered[1:]


html_indent_rendered = """
<!DOCTYPE html>
<html>
    <head>
        <title>Test</title>

    </head>
    <body>
        <div>header1</div>

        <div>header2</div>
        <div class="page">
            <a href="/" class="title"><h1>Test</h1></a>
            <div class="nav">
                <a href="/">nuvolosit&#224; variabile</a>
            </div>


            <ul class="posts">
                <li>
                    <h2>foo</h2>
                    <hr />
                </li>
                <li>
                    <h2>bar</h2>
                    <hr />
                </li>
            </ul>

        </div>
        <div>footer</div>

    </body>
</html>"""


def test_html_indent(templater_html_indent):
    r = templater_html_indent.render(
        'test.html', {
            'posts': [{'title': 'foo'}, {'title': 'bar'}]
        }
    )
    assert "\n".join([l.rstrip() for l in r.splitlines()]) == \
        html_indent_rendered[1:]


html_pre_rendered = """
<div>
    <pre>
        <code>
var foo = 'foo';
var bar = '{{ bar }}';
var baz = 'baz';
var list = [
    '0',
    '1',
];
        </code>
    </pre>
</div>"""


def test_html_indent_pre(templater_html_indent):
    r = templater_html_indent.render('pre.html')
    assert "\n".join([l.rstrip() for l in r.splitlines()]) == \
        html_pre_rendered[1:]


def test_pyerror(templater_html):
    with pytest.raises(ZeroDivisionError) as exc:
        templater_html.render('pyerror.html')

    tbs = ''.join(traceback.format_exception(exc.type, exc.value, exc.tb))
    frame = exc.traceback[-1]

    frames = []
    tb = exc.tb
    while tb:
        frames.append(tb)
        tb = tb.tb_next
    tb_frame = frames[-1]

    tpath = os.sep.join(['html', 'pyerror.html'])

    assert frame.name == 'template'
    assert str(frame.path).endswith(tpath)
    assert tb_frame.tb_lineno == 2

    assert f'{tpath}", line 2, in template' in tbs


@pytest.fixture(scope='function')
def templater_blocks():
    return Renoir(
        mode='plain', debug=True, path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'blocks'
        )
    )


_target_b1 = """
super b2
parent b2
child b2
parent l1
child b1
parent l2
child l3
parent l4
child l1
child l2"""


def test_blocks_include(templater_blocks):
    r = templater_blocks.render('child.txt', {'parent_name': './parent_incl.txt'})
    assert "\n".join(
        filter(None, [l.rstrip() for l in r.splitlines()])
    ) == _target_b1[1:]


_target_b2 = """
super b2
parent b2
child b2
parent l1
child b1
parent l2
child l3
parent l4"""


def test_blocks_noinclude(templater_blocks):
    r = templater_blocks.render('child.txt', {'parent_name': './parent_noincl.txt'})
    assert "\n".join(
        filter(None, [l.rstrip() for l in r.splitlines()])
    ) == _target_b2[1:]
