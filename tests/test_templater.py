# -*- coding: utf-8 -*-
"""
    tests.templater
    ---------------

    Tests templater module.

    :copyright: (c) 2014-2019 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

import os
import pytest
import traceback

from renoir import Renoir


@pytest.fixture(scope='function')
def templater_pretty():
    return Renoir(
        escape='all', prettify=True, debug=True,
        path=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'templates'
        )
    )


rendered_value = """
<!DOCTYPE html>
<html>
    <head>
        <title>Test</title>
    </head>
    <body>
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
    </body>
</html>"""


def test_render(templater_pretty):
    r = templater_pretty.render(
        'test.html', {
            'posts': [{'title': 'foo'}, {'title': 'bar'}]
        }
    )
    assert "\n".join([l.rstrip() for l in r.splitlines()]) == \
        rendered_value[1:]


def test_render_pyerror(templater_pretty):
    with pytest.raises(ZeroDivisionError) as exc:
        templater_pretty.render('pyerror.html')

    tbs = ''.join(traceback.format_exception(exc.type, exc.value, exc.tb))
    frame = exc.traceback[-1]

    frames = []
    tb = exc.tb
    while tb:
        frames.append(tb)
        tb = tb.tb_next
    tb_frame = frames[-1]

    assert frame.name == 'template'
    assert str(frame.path).endswith('/templates/pyerror.html')
    assert tb_frame.tb_lineno == 2

    assert '/templates/pyerror.html", line 2, in template' in tbs
