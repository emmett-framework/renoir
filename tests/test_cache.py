# -*- coding: utf-8 -*-
"""
    tests.cache
    -----------

    Tests cache module.
"""

import pytest

from renoir import Renoir


@pytest.fixture(scope='function')
def templater_reload():
    return Renoir(reload=True)


@pytest.fixture(scope='function')
def templater_noreload():
    return Renoir()


def test_noreload(templater_noreload):
    assert not templater_noreload.cache.parse.data

    templater_noreload._render(source='{{=a}}', context={'a': 1})
    assert templater_noreload.cache.parse.data['<string>']
    assert not templater_noreload.cache.parse.hashes
    data = templater_noreload.cache.parse.data['<string>']

    templater_noreload._render(source='{{=a}}', context={'a': 1})
    assert templater_noreload.cache.parse.data['<string>'] is data

    templater_noreload._render(source='{{=a}}\n', context={'a': 1})
    assert templater_noreload.cache.parse.data['<string>'] is data


def test_reload(templater_reload):
    assert not templater_reload.cache.parse.data

    templater_reload._render(source='{{=a}}', context={'a': 1})
    assert templater_reload.cache.parse.data['<string>']
    data = templater_reload.cache.parse.data['<string>']
    hashed = templater_reload.cache.parse.hashes['<string>']

    templater_reload._render(source='{{=a}}', context={'a': 1})
    assert templater_reload.cache.parse.hashes['<string>'] == hashed
    assert templater_reload.cache.parse.data['<string>'] is data

    templater_reload._render(source='{{=a}}\n', context={'a': 1})
    assert templater_reload.cache.parse.hashes['<string>'] != hashed
    assert templater_reload.cache.parse.data['<string>'] is not data
