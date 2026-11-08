# DEBRIEF

The protocol behind the DEBRIEF register: a way to keep score of a claim, a computation or a learning run so that
anyone can see what was checked, under what rule written down first, what standing each piece has, and where the
frontier of what is known actually is. Contributions enter as dated cycles under the contributor's own name.

Status: in preparation (November 2026). Protocol version 0.1.0. This repository goes public when the first
mission repository validates against it in CI.

## The family

Repositories are named `DEBRIEF-domain-regime`.

| repository | what it holds |
|---|---|
| `DEBRIEF` (this one) | schema, rules, tools, templates, the reusable validation workflow, and the cross-mission index |
| `DEBRIEF-math-primegaps` | the first mission: an independent rerun and definitional trace of openai/PrimeGaps186 |
| `DEBRIEF-space-lunar` | lunar-orbit radiation learning run, reconstructed record, open surface gap |
| `DEBRIEF-space-mars` | Mars surface radiation learning run (pending) |

A mission repository holds its own `ledger.json`, pre-registrations with their hashes, checks, logs and traces. It
pins a protocol version and calls this repository's workflow to validate on every pull request.

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
tools/render.py             ledger.json -> SCORECARD.md and a spoken knowledge base
templates/                  prereg.yaml, trace.md, one template per contribution kind
.github/workflows/validate.yml   reusable workflow a mission repository calls
```

## Licence

Code: Apache-2.0 (see LICENSE). Ledger text, traces and scorecards in mission repositories: CC-BY-4.0, so that
attribution travels with the record. Mission repositories state this in their own LICENSE files.
