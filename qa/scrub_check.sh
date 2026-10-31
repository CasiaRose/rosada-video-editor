#!/bin/bash
# Refuse a commit that still has machine paths, mail addresses, or token-shaped strings.
# Names that belong in a local edit stay in the project file or in VEDIT_NAMES.
# and examples that use placeholders. This script does not download anything.
set -u
root=$(git rev-parse --show-toplevel)
cd "$root"
pat='/home/|/workspace|/cursor/stores|api[_-]?key[[:space:]]*[:=]|sk-[A-Za-z0-9]|AKIA[A-Z0-9]{16}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
if git grep -n -I -E "$pat" -- . ':!*.wav' ':!qa/scrub_check.sh'; then
  echo "scrub_check: remove the matches above before committing" >&2
  exit 1
fi
echo "scrub_check: ok"
