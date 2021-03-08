"""Utility to setup sys.path.
"""

import sys
from os.path import abspath, dirname, join, pardir

INFOGAMI_PATH = abspath(join(dirname(__file__), pardir))
sys.path.insert(0, INFOGAMI_PATH)
