"""Configurable locations. Scripts never assume a home directory or a machine path.

VEDIT_ROOT       repo root (default: the parent of this file)
VEDIT_WORK       per-edit working directory (default: the current directory)
VEDIT_MUSIC      folder for generated or supplied beds (default: <root>/assets/music)
VEDIT_SFX        folder for generated effects (default: the project cache)
VEDIT_HOTWORDS   optional faster-whisper hotwords
VEDIT_NAMES      comma-separated names a profile may require on screen
VEDIT_FONT_TEXT / VEDIT_FONT_DISPLAY   hook fonts
"""
import os

ROOT = os.environ.get("VEDIT_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def work_dir():
    return os.environ.get("VEDIT_WORK") or os.getcwd()

def music_dir():
    return os.environ.get("VEDIT_MUSIC") or os.path.join(ROOT, "assets", "music")

def sfx_dir():
    return os.environ.get("VEDIT_SFX") or os.path.join(ROOT, "assets", "sfx")

def hotwords():
    return os.environ.get("VEDIT_HOTWORDS") or ""

def agents():
    return [a.strip() for a in os.environ.get("VEDIT_NAMES", "").split(",") if a.strip()]

def out_path(*parts):
    return os.path.join(work_dir(), *parts)
