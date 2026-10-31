#!/usr/bin/env python3
"""Same entry as qa/verify.py. Prints which checks failed or did not run."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import main

if __name__ == "__main__":
    sys.exit(main())
