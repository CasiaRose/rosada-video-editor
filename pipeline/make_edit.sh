#!/usr/bin/env bash
# make_edit.sh recipe.json  -> cut, graphics, sound, finish, checks. Exit 1 = not deliverable.
set -e; D="$(cd "$(dirname "$0")" && pwd)"; python3 "$D/make_edit.py" "$@"
