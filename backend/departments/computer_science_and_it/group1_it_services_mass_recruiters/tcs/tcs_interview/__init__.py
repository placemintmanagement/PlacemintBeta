# -*- coding: utf-8 -*-
"""TCS NQT interview package. Re-exports every public name from .core, same
pattern as capgemini_interview/__init__.py, so `from ...tcs import
tcs_interview` / `tcs_interview.<name>` reaches everything in core.py."""
from .core import *  # noqa: F401,F403
