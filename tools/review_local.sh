#!/bin/bash
# Run the automated second review of meaning on this machine, never in CI.
#
# usage: tools/review_local.sh            review every claim that is due, opening one pull request per claim
#        tools/review_local.sh --check    list which claims are due; no model call, no key needed
#        tools/review_local.sh erdos1133  only the named claim(s)
#
# The Anthropic API key lives only in your macOS login Keychain. Add it once with:
#     security add-generic-password -a "$USER" -s debrief-anthropic -w
# (it prompts for the key, so the key never lands in shell history). The key is read for the one model call and
# passed to that process alone; it is never written to disk, exported to the shell or sent to GitHub.
#
# Each claim gets: pull main, check a review is due and no review PR is open, then on branch review/second-review
# commit the pre-registration, run the review, render, validate, commit, push, and open a pull request.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"          # the folder holding DEBRIEF and the DEBRIEF-math-* repos
TOOLS="$ROOT/DEBRIEF/tools"
VENV="$HOME/.debrief-review-venv"
MODEL="${DEBRIEF_REVIEW_MODEL:-claude-opus-5-5}"
CHECK=0; ONLY=()
for arg in "$@"; do
  case "$arg" in
    --check) CHECK=1 ;;
    -h|--help) sed -n 2,14p "$0"; exit 0 ;;
    *) ONLY+=("DEBRIEF-math-${arg#DEBRIEF-math-}") ;;
  esac
done

if [ ! -x "$VENV/bin/python" ]; then
  echo "setting up $VENV (one time)"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet anthropic pyyaml jsonschema
fi
PY="$VENV/bin/python"

key() { security find-generic-password -a "$USER" -s debrief-anthropic -w 2>/dev/null; }
if [ "$CHECK" = 0 ] && ! key >/dev/null; then
  echo "no key in Keychain. Add it with: security add-generic-password -a \"\$USER\" -s debrief-anthropic -w"; exit 1
fi

reviewed=0
for dir in "$ROOT"/DEBRIEF-math-*; do
  name="$(basename "$dir")"
  if [ ${#ONLY[@]} -gt 0 ] && [[ ! " ${ONLY[*]} " == *" $name "* ]]; then continue; fi
  [ -f "$dir/claim.yaml" ] || { echo "$name: no claim.yaml, skipped"; continue; }
  ledger="$(grep -m1 -E '^\s+ledger:' "$dir/.github/workflows/debrief.yml" | awk '{print $2}')"
  [ -n "$ledger" ] || { echo "$name: no ledger path in debrief.yml, skipped"; continue; }
  (
    cd "$dir"
    if [ -n "$(git status --porcelain --untracked-files=no)" ]; then echo "$name: uncommitted changes, skipped"; exit 0; fi
    git checkout --quiet main && git pull --quiet --ff-only
    if gh pr list --head review/second-review --state open --json number -q '.[0].number' | grep -q .; then
      echo "$name: a review pull request is already open"; exit 0; fi
    due="$("$PY" "$TOOLS/semantic_review.py" needed --repo . --ledger "$ledger")"
    if [ "$due" != yes ]; then echo "$name: up to date"; exit 0; fi
    if [ "$CHECK" = 1 ]; then echo "$name: due"; exit 0; fi

    echo "$name: reviewing with $MODEL"
    git checkout --quiet -B review/second-review
    "$PY" "$TOOLS/semantic_review.py" prereg --repo . --ledger "$ledger" --model "$MODEL"
    git add prereg_review.yaml prereg_review.yaml.sha256
    git commit --quiet -m "Pre-register the automated second review of meaning ($MODEL), before it runs"
    summary="$(mktemp)"
    ANTHROPIC_API_KEY="$(key)" "$PY" "$TOOLS/semantic_review.py" review --repo . --ledger "$ledger" --summary "$summary"
    "$PY" "$TOOLS/render.py" "$ledger" --scorecard SCORECARD.md
    "$PY" "$TOOLS/render.py" "$ledger" --asks ASKS.md
    "$PY" "$TOOLS/validate.py" "$ledger" --repo .
    git add trace/ "$ledger" SCORECARD.md ASKS.md
    git commit --quiet -m "Automated second review of meaning ($MODEL), run locally"
    git push --quiet --force -u origin review/second-review
    gh pr create --head review/second-review --title "Second review of meaning ($(date -u +%F))" --body-file "$summary"
    rm -f "$summary"
    git checkout --quiet main
  ) || echo "$name: FAILED (left on its branch for a look)"
  reviewed=$((reviewed+1))
done
[ "$reviewed" -gt 0 ] || echo "no claims matched"
