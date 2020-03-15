# -*- coding: utf-8 -*-
"""
    renoir.typing
    -------------

    Provides typing helpers.

    :copyright: 2014 Giovanni Barillari
    :license: BSD-3-Clause
"""


from typing import Any, Callable, Dict, Tuple


LoaderType = Callable[[str, str], Tuple[str, str]]
RenderType = Callable[[str, str], str]
ContextType = Callable[[Dict[str, Any]], None]
