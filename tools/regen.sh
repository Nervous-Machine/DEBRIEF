#!/bin/sh
# Regenerate the cross-mission pages from the sibling mission repositories: INDEX.md, CONTRIBUTORS.md, docs/ (the board).
# usage: tools/regen.sh [DIR holding the DEBRIEF-* checkouts; default ..]
set -e
cd "$(dirname "$0")/.."
D="${1:-..}"; B=https://github.com/Nervous-Machine
P=""
for r in "$D"/DEBRIEF-*/ledger/*.json; do
  name=$(basename "$(dirname "$(dirname "$r")")"); P="$P $B/$name=$r"
done
# shellcheck disable=SC2086
python3 tools/index.py INDEX.md $P
python3 tools/contributors.py CONTRIBUTORS.md $P
python3 tools/board.py docs $P
