# DEBRIEF ledger schema, protocol 0.1.0

A mission is a domain worked over a period: a learning run on data, or an audit of a claim made by someone else.
Its ledger is one JSON file, `ledger.json`, with seven collections. Anything a briefing voice says comes from this
file and from nothing else. Anything not in it is not said.

`schema_version` is `nm-debrief-v1`. `protocol_version` on the mission document is the version of this schema the
mission validated against. The machine-checkable shape is `ledger.schema.json`; the rules below are what
`tools/validate.py` enforces beyond shape.

## 1. Collections

| collection | one document is | used for |
|---|---|---|
| `missions` | the mission | opening, short version, scope limits, record quality |
| `cycles` | one unit of work: what was written first, what happened | recounting in order; "the reasoning" |
| `findings` | one thing learned, retracted, ruled out, discovered or corrected | "what was learned"; "what it changes" |
| `gaps` | one unknown, with history and what would close it | "what was escalated"; "what needs attention" |
| `anomalies` | one event that disagreed with a trusted expectation | outstanding anomalies; alerts |
| `background` | one concept explained, apart from results | teaching |
| `sessions` | one briefing: who, what was asked, what was proposed | follow-ups |

Every document carries `mission_id`, `pod`, `schema_version`, `created_by`, `created_at`, `provenance`.
Text meant to be read aloud is in a field called `spoken`: plain prose, no symbols.

## 2. Fields

**missions** — `mission_id`, `title`, `kind` (`learning` | `audit`), `pods[]`, `began`, `status` (`active` |
`closed`), `record_quality` (`full_ledger` | `reconstructed`) with `record_note`, `scope_limits[]`,
`record_limits[]`, `opening.spoken`, `short_version.spoken`, `what_happened.spoken`, `implications`
{`rely_on[]`, `do_not_rely_on[]`, `stop[]`, `new[]`; each item {`spoken`, `finding_ids[]`}},
`certainty_statement.spoken`, `sources[]` {`kind`, `ref`}, `protocol_version`, `claim_rule_met` (audit only;
true only when every step is certified or accepted from refereed literature and the formal deduction has been
rerun independently).

**cycles** — `cycle` (number or label), `dated`, `by` (who did the work: a Git identity, optionally an ORCID),
`kind` (`learning` | `rerun` | `read` | `claim` | `data` | `correction` | `trace` | `replay`), `preregistered` {`question`, `rule`,
`predictions[]`, `commit` (path to the pre-registration file, or a commit id), `results[]` (paths to the files
holding the outcome, used for the ordering check), `before_data` (true | false | unknown)}, `outcome` {`verdict`,
`numbers{}`, `misses[]`}, `spoken`, `finding_ids[]`, `gap_ids[]`, `audience`.
`verdict` ∈ `admitted`, `not_admitted`, `confirmed`, `refuted`, `unavailable`, `corrected`, `withdrawn`,
`classified`, `learned`, `mixed`, `signed`, `refused`.

**findings** — `finding_id`, `kind` (`learned` | `retracted` | `ruled_out` | `discovery` | `correction`),
`spoken`, `evidence` {`numbers{}`, `cycles[]`, `confirmed_by[]`}, `standing` {`status`, `basis`, `note`},
`certainty` {`earned`: true | false | null, `note`}, `edge_refs[]`, `audience`.

**gaps** — `gap_id`, `title`, `spoken`, `status` (`proposed` | `in_cycle` | `resolved_learned` |
`resolved_refuted` | `immovable`), `opened_cycle`, `history[]` {`cycle`, `hypothesis`, `before_data`, `result`,
`by`}, `closes_with[]` {`what`, `kind` (`data_release` | `measurement` | `research` | `decision` | `rerun` |
`read`), `external` (bool), `who_could_act`}, `expected_signal` (what evidence would arrive and how it would be
recognised), `resolution_by` (an ISO date, or `"none registered"`), `ask.spoken`, `priority` (1 = first),
`audience`.

**anomalies** — `anomaly_id`, `when`, `node`, `spoken`, `status` (`open` | `explained` | `confirmed`), `urgency`
(`immediate` | `daily`), `from_trusted_node`, `evidence{}`, `gap_id`, `alert` {`sent`, `channel`, `at`}.

**background** — `term`, `also_called[]`, `spoken`, `source` (`general` | `literature`, with `citation`),
`mission_tie.spoken` (optional).

**sessions** — `session_id`, `at`, `audience`, `questions[]`, `ideas[]`, `asks_accepted[]`.

**audience** on findings, gaps, cycles and implications: `briefing` or `internal`. Internal items are kept in
the ledger but not rendered into the spoken knowledge base. Leaving something out of a briefing is done by
marking it internal, never by deleting it.

## 3. Standing

Every finding has a standing. Open items are gaps and have no standing. The standing line always prints open gaps
next to the counts: "Certified 5. Accepted 5. Refuted 0. Open gaps 3."

| status | learning mission | audit mission |
|---|---|---|
| `accepted` | the hypothesis passed its test (a rule or prediction written down beforehand, or independent confirmation); in the model with a direction; certainty not yet earned | a published, refereed theorem; a formal check reported by the authors' own toolchain; or a step inside a formally checked deduction. `basis` says which |
| `certified` | accepted, and certainty was earned under a settled rule (`certainty.earned: true`) | a deterministic check run under a rule written down first, or a formal check rerun by a party independent of the authors (`certainty.earned: true` records deterministic and reproducible; it is not a certainty score) |
| `refuted` | the hypothesis did not stand | a counterexample, a failed check, or a published objection the authors have not answered |

Numeric spot checks corroborate a literature input but never raise its standing. Anything transcribed from a claim
(a tuple, a definition, an axiom text) is pinned to a source commit and file hash in `provenance`, and the check
that reads it fails if the pin breaks.

**Reserved words.** No `spoken` text, scorecard or knowledge base may say that the claim under audit "is verified",
"is proved", "is proven" or "is a theorem" unless the mission's `claim_rule_met` is true. Negated uses ("has not
been verified") are allowed. The validator checks this.

## 4. Contribution kinds

Every contribution is one cycle. (`replay` cycles record what was public at a date, with no new work; `learning` cycles are a learning run's own; neither is a contribution kind.) A cycle carries `by`, `dated`, what was written first, what happened and the
misses. Nothing else enters the ledger.

| kind | who | submits | rule |
|---|---|---|---|
| `rerun` | anyone with hardware | pre-registration with predictions, then logs and results | the pre-registration commit precedes the results commit; predictions are compared and misses recorded |
| `read` | a person reading a definitional trace | a signed or refused checklist, with comments | by name; a refusal names the item and why; a signature may be withdrawn by a later cycle, never deleted |
| `claim` | anyone | source pin (repo, commit, file hashes), pre-registration, steps graph, first checks | the claim's author may open it but may not sign its own read |
| `trace` | the keeper or a contributor | a definitional trace prepared for human review, with its pre-registration | renderings are marked as the tracer's; a trace changes no standing |
| `data` | a data supplier | source, licence, hashes, collection dates, the gap it addresses, how to be named | the gap's history records the contributor; the gap moves `immovable` → `in_cycle` on receipt |

Closing a semantic gap (proposed, 0.1.0): two independent `signed` cycles by people who are not authors of the
claim, with no standing `refused` cycle. One refusal reopens the gap.

## 5. What goes in the record

The protocol exists to make validation or computation reproducible, to make contributing easy, and to make the
boundary of the frontier obvious. Judgement decides what is a critical detail; the test is whether a detail
changes what a reader can reproduce, contribute to, or locate as the frontier. If not, it belongs in a commit
message or internal notes, not the ledger.

- A finding carries its standing, basis, what was written first, what happened, and its numbers. Nothing about how
  the file reached us.
- A gap carries what is unknown, what closes it, who could act, the expected signal and a resolution date.
- A cycle carries the question, the rule, the predictions, the outcome and the misses. A confound or erratum stays
  with its cycle, once, in a line.
- Record history (a lost file, a reconstruction) lives in one place: the mission's `record_quality` and
  `record_note`, stated once. Findings and cycles never repeat it.
- Corrections are cycles of kind `correction`, dated, with the corrected text. Old text is not annotated in place.
- A rerun run differently from the original is a separate cycle with its own pre-registration. Its results are
  never merged into the original's claims.

## 6. Rules the validator enforces

1. Every finding names the cycles it came from, or the mission's record note says the cycle record is unavailable.
2. Every finding with a standing has a `basis`. `certified` requires `certainty.earned: true`.
3. A gap is not `immovable` unless `closes_with` names something outside the mission's reach.
4. An anomaly is `immediate` only if `from_trusted_node` is true.
5. Nothing is deleted; corrections are new documents that name what they replace.
6. Reserved words (section 3) do not appear in affirmative form unless `claim_rule_met` is true.
7. For any cycle whose `preregistered.commit` is a file in the repository and whose `preregistered.results[]` are
   files in the repository, the first commit touching the pre-registration is not later than the first commit
   touching any results file (checked from git history when the validator is given `--repo`).
8. A pre-registration with a `.sha256` sidecar still hashes to the recorded value, either whole or for its body
   above the first amendment marker (`# ---- Amendment` or a top-level `amendments:` key). Edits to the body
   after registration fail.
9. Every gap that is not resolved has `expected_signal` and `resolution_by`. In 0.1.0 this is a warning; from 0.2.0
   an error.
10. The rendered standing line prints open gaps next to the finding counts.
