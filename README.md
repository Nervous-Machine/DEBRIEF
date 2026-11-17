# DEBRIEF

The protocol behind the DEBRIEF register: a way to keep score of a claim, a computation or a learning run so that
anyone can see what was checked, under what rule written down first, what standing each piece has, and where the
frontier of what is known actually is. Contributions enter as dated cycles under the contributor's own name.

Status: public and under construction (November 2026), built and amended in the open. Protocol version 0.1.0.
Decisions still open are listed in GOVERNANCE.md.

## The family

Repositories are named `DEBRIEF-domain-regime`.

| repository | what it holds |
|---|---|
| `DEBRIEF` (this one) | schema, rules, tools, templates, the reusable validation workflow, and the cross-mission index |
| [`DEBRIEF-math-primegaps`](https://github.com/Nervous-Machine/DEBRIEF-math-primegaps) | independent rerun and definitional trace of openai/PrimeGaps186 (lim inf prime gaps ≤ 186) |
| [`DEBRIEF-math-zhang240`](https://github.com/Nervous-Machine/DEBRIEF-math-zhang240) | pre-registered rerun of Hanxin Zhang's exact certificate for ≤ 240 |
| [`DEBRIEF-space-lunar`](https://github.com/Nervous-Machine/DEBRIEF-space-lunar) | lunar-orbit radiation learning run, reconstructed record, the Mars-to-Moon cross-check, the open surface gap |
| `DEBRIEF-space-mars` | Mars surface radiation learning run (pending) |
| `DEBRIEF-math-erdos<N>` (ten, opened 2026-11-14) | records of claimed AI-assisted solutions to Erdős problems 306, 550, 593, 671, 731, 768, 856, 1061, 1133 and 1177: artifacts pinned, gaps drawn; two Lean reruns and seven reading guides so far; standing of each in `INDEX.md` and on the board |

The current standing of every mission is in [`INDEX.md`](INDEX.md). Who has contributed, and what, is in
[`CONTRIBUTORS.md`](CONTRIBUTORS.md), in plain words. The claims board, which places every claim by area and by stage toward its rule, is at
https://math-board.nervousmachine.com (generated into `docs/` by `tools/regen.sh`). To open a new claim at tier zero, write a `claims/<name>.yaml` from
`templates/claim.yaml` and run `tools/new_mission.py`.

**Other registries.** The [Palomar registry](https://palomar-registry.org/about) records machine-checked Lean proofs: it replays each proof through independent kernels and has a language model judge the statement. [DeepMind's formal-conjectures](https://github.com/google-deepmind/formal-conjectures) collects human-reviewed formal statements and marks which are solved. DEBRIEF does not duplicate either. It records their status in each ledger as a dated cycle, and it holds what they do not: pre-registered checks, named human readings of what a statement means, and learning runs on physical systems, where the error signal comes from the world. The board's "Who has checked what" table puts all of these side by side.

A mission repository holds its own `ledger.json`, pre-registrations with their hashes, checks, logs and traces. It
pins a protocol version and calls this repository's workflow to validate on every pull request.

## Automation

The register keeps itself current from public sources. Every change arrives as a pull request for a maintainer to merge.

| when | what | where |
|---|---|---|
| daily, per claim | reads the [Palomar registry](https://palomar-registry.org), DeepMind formal-conjectures and the erdosproblems.com database; on any change, records a dated cycle, credits a new Palomar check as a rerun, and opens a pull request | `tools/watch_external.py`, `.github/workflows/watch.yml` (called by each claim's `debrief.yml`) |
| daily | regenerates `INDEX.md`, `CONTRIBUTORS.md` and the claims board from every public claim repository; opens a pull request if anything changed | `tools/regen.sh`, `.github/workflows/board.yml` |
| weekly | lists Erdős claims those registries show that are not tracked here, as one issue to triage; nothing is opened automatically | `tools/watch_candidates.py`, `.github/workflows/candidates.yml` |

DEBRIEF defers to Palomar for machine checks: when Palomar has checked every Lean development pinned in a record, the
record's build gap is resolved by that check, and DEBRIEF's own reruns go where Palomar has nothing. A rerun run here
follows Palomar's form (a `Challenge.lean` statement, Comparator, a second kernel), so results line up across the two.
What only DEBRIEF records stays by hand: pre-registrations, named human readings of what a statement means, and use.
Only public repositories feed the public pages; `regen.sh` asks GitHub for each repository's visibility and leaves
out anything else.

## What the protocol gives you

- **Standing words that mean the same thing everywhere.** `certified`, `accepted`, `refuted`; and `open` for a gap.
  Their definitions are in `schema/SCHEMA.md` and the validator enforces their rules.
- **Written first, then checked.** A pre-registration is hashed and committed before results exist; it is never
  edited afterwards, only amended with a dated block. The validator reads git history to check this.
- **Four kinds of contribution**, each one cycle in a ledger: a rerun, a semantic read, a new claim, a dataset.
- **A legible record.** Rules for what goes into the ledger and what stays out, so a reader can follow it.
- **Credit.** Each cycle names who did it. Releases carry a citation file listing contributors.

## Layout

```
schema/SCHEMA.md            the written rules
schema/ledger.schema.json   the machine-checkable shape of ledger.json
tools/validate.py           structural and protocol checks; exit code 1 on any error
tools/prereg.py             hash a pre-registration; refuse edits after results exist
tools/render.py             ledger.json -> SCORECARD.md, ASKS.md and a spoken knowledge base
tools/merge_cycles.py       contributed cycles/ -> ledger, applying the two-signature rule
tools/issue_to_cycle.py     issue form -> cycle file, verbatim
tools/index.py              mission ledgers -> INDEX.md
templates/                  prereg.yaml, trace.md, one template per contribution kind
.github/workflows/validate.yml   reusable workflow a mission repository calls
```

## Licence

Code: Apache-2.0 (see LICENSE). Ledger text, traces and scorecards in mission repositories: CC-BY-4.0, so that
attribution travels with the record. Mission repositories state this in their own LICENSE files.
