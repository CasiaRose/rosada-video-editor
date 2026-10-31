"""Progress border for the frame compositor (composite.py, delivery_check.py).

Frame count N comes from PB_N, or from timeline.json in the working directory.
The geometry is border/pborder_core.py. finish.py burns the same border through border/border.py.
"""
import json, os, sys

if "PB_N" not in os.environ and os.path.exists("timeline.json"):
    os.environ["PB_N"] = str(json.load(open("timeline.json"))["N"])
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "border"))
from pborder_core import *  # noqa: F401,F403
