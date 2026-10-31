#!/usr/bin/env python3
"""Run the configurable checks. Exit 1 when the file is not deliverable.

  python qa/verify.py cut.mp4 --style style.yaml --layout layout.json --json report.json
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import main

if __name__ == "__main__":
    sys.exit(main())
