# -*- coding: utf-8 -*-
"""Capgemini interview package (reorganized from the single capgemini_interview.py
module -- see core.py's own docstring for what actually lives here).

Pure move: re-exports every public name from .core so every existing
`from ...capgemini import capgemini_interview` / `capgemini_interview.<name>`
call site keeps working unchanged. core.py defines no __all__, so this picks
up every name that isn't underscore-prefixed, exactly matching what was
reachable as capgemini_interview.<name> before the move.
"""
from .core import *  # noqa: F401,F403
