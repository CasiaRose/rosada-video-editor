#!/usr/bin/env python3
"""Older name for the check report. Delegates to qa/engine.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import main

if __name__ == "__main__":
    sys.exit(main())
