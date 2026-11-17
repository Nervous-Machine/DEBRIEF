#!/bin/sh
# Regenerate the cross-mission pages from the sibling mission repositories: INDEX.md, CONTRIBUTORS.md, docs/ (the board).
# usage: tools/regen.sh [DIR holding the DEBRIEF-* checkouts; default ..]
set -e
cd "$(dirname "$0")/.."
D="${1:-..}"; B=https://github.com/Nervous-Machine
P=""
# Only public repositories feed these public pages. Visibility is asked of GitHub; if it cannot be read, the
# repository is left out (fail closed). Set DEBRIEF_ASSUME_PUBLIC=1 where only public repositories were cloned (CI).
for r in "$D"/DEBRIEF-*/ledger/*.json; do
  name=$(basename "$(dirname "$(dirname "$r")")")
  if [ "${DEBRIEF_ASSUME_PUBLIC:-}" != 1 ]; then
    vis=$(gh repo view "Nervous-Machine/$name" --json visibility -q .visibility 2>/dev/null || echo UNKNOWN)
    if [ "$vis" != PUBLIC ]; then echo "skip $name ($vis)" >&2; continue; fi
  fi
  P="$P $B/$name=$r"
done
# shellcheck disable=SC2086
python3 tools/index.py INDEX.md $P
python3 tools/contributors.py CONTRIBUTORS.md $P
python3 tools/board.py docs $P
