# Governance

## Maintainers

Nervous Machine (Heidi Bennett) is the maintainer of record for the protocol and, at the start, for each mission
repository. A contributor becomes eligible to maintain a mission repository after one merged cycle on a claim
they did not author. Maintainers merge; they do not change the content of a contribution.

## What a maintainer may and may not do

May: merge a cycle that passes validation; refuse a cycle that fails it, with the validator output; open and
label gaps; cut releases; correct the protocol by a dated, versioned change.

May not: edit a contributor's cycle, signature or refusal; edit a pre-registration body after registration;
delete anything from a ledger; change a standing without a cycle that justifies it; call a claim verified,
proved or a theorem unless the mission's claim rule is met and the validator shows it.

## Disputes

A dispute about a standing is itself a cycle: the disputing party writes down what they expect to find, under
what rule, and the outcome is recorded whichever way it falls. Authors of a claim may answer any gap with a
cycle. The register says "conditionally supported" and names what is open; it never says "refuted" without a
check or a published objection.

## Independence

The register's value is that the keeper has no stake in the score. Nervous Machine does not accept payment from
the authors of a claim for the standing of that claim. Paid work, where it exists, is for running reruns and
traces whose outcome is recorded whichever way it falls, under a pre-registration committed first.

## Decisions taken (2026-11-08)

- Identity for sign-offs: Git identity; ORCID optional; no institution required or checked.
- Closing a semantic gap: two independent `signed` read cycles by people who are not authors of the claim, with
  no standing `refused` cycle. One refusal reopens the gap.
- Licences: Apache-2.0 for code; CC-BY-4.0 for ledger text, traces and scorecards.
- Claim authors may open their own claim; they may never sign its semantic read.

## Versioning

The protocol is versioned (`0.1.0` now). A mission pins the version it validated against. A rule that becomes
stricter is announced one minor version ahead as a warning (rule 9 is the first example).
