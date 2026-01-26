#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

IGNORE_FILE="docs/tree.ignore"

# Build a pipe-separated pattern for `tree -I`
# - remove comments/blank lines
# - escape literal dots
# - join with |
PATTERN="$(
  sed -e 's/#.*$//' -e '/^[[:space:]]*$/d' "$IGNORE_FILE" \
  | sed -e 's/[.[\*^$()+?{|\\]/\\&/g' \
  | paste -sd'|' -
)"

# If file is empty, don’t pass -I
if [[ -n "${PATTERN}" ]]; then
  tree -a --dirsfirst -L 5 -I "$PATTERN" > docs/TREE_REPO.clean.txt
else
  tree -a --dirsfirst -L 5 > docs/TREE_REPO.clean.txt
fi

echo "Wrote docs/TREE_REPO.clean.txt"
