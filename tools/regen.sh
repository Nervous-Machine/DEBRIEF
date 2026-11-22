#!/bin/sh
# Regenerate the cross-mission pages from the sibling mission repositories: INDEX.md, CONTRIBUTORS.md, docs/ (the board),
# and the standing block in each public mission README.
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
# Each mission's tooling disclosure (tooling.yaml) is written into its ledger first, so the pages read it.
for kv in $P; do
  dir=$(dirname "$(dirname "${kv#*=}")")
  [ -f "$dir/tooling.yaml" ] && python3 tools/tooling.py "$dir" > /dev/null
done
# shellcheck disable=SC2086
python3 tools/index.py INDEX.md $P
python3 tools/contributors.py CONTRIBUTORS.md $P
python3 tools/board.py docs $P
# The standing block at the top of each public mission README is written from the board data; commit each mission
# repository whose README changed.
for kv in $P; do
  name=$(basename "${kv%%=*}"); dir=$(dirname "$(dirname "${kv#*=}")")
  [ -f "$dir/README.md" ] && python3 tools/standing_block.py "$dir/README.md" docs/board.json "$name"
done
