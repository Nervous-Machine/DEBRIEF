# Contributing

Every contribution to a DEBRIEF mission is one **cycle** in that mission's ledger, dated, under your own name.
There are five kinds. Pick the one that fits, follow its rule, and your name goes into the ledger, the mission's
`CITATION.cff` and the next release's author list.

You never edit `ledger.json` by hand. You add a file under `cycles/` (or fill in an issue form, which does that
for you) and the protocol tools merge it.

## The one-hour path: a semantic read

For a claim whose mission has a definitional trace (`trace/DEFINITIONAL-TRACE.md`):

1. Read the trace on GitHub. Each formal statement is quoted verbatim with file and line, traced to its
   definitions, rendered in plain mathematical language (marked as the tracer's), and set beside the paper's
   statement.
2. Open the **Semantic read** issue form in the mission repository. For each checklist item, sign or refuse.
   A refusal names the item and the reason. Add anything you found wrong in the renderings, however small.
3. Submit. A workflow turns your form into a `read` cycle under your GitHub handle and opens a pull request. A
   maintainer merges it once validation passes. Nothing about the content is changed on the way.

Your signature can be withdrawn later by a new cycle. It is never deleted.

You must not be an author of the claim you are reading. The form asks you to confirm that.

## A rerun

1. Copy `templates/prereg.yaml` into the mission repository as `prereg_<label>.yaml`. Write down what you will
   run, the pass condition, and your predicted outcome for each check. Run `tools/prereg.py register` on it and
   commit both files **before** running anything.
2. Run. Keep logs.
3. Copy `templates/cycle-rerun.yaml` to `cycles/<label>.yaml`, fill it in, list your results and log files under
   `preregistered.results`, record every prediction that did not hold under `outcome.misses`. Commit and open a
   pull request.

The validator checks from git history that the pre-registration was committed before the results. If you need
to change the pre-registration after registering it, use `tools/prereg.py amend`; the body is never edited.

## A new claim

Copy `templates/cycle-claim.yaml` and `templates/prereg.yaml`. Pin the source: repository, full commit id, file
hashes, paper PDF hash and date. Draw the claim as steps, each with how it is checked. If the source licence
allows, vendor the files you transcribe from under `source/`; otherwise store hashes and a fetch script. Authors
may open their own claim and may not sign its semantic read.

A new claim usually means a new mission repository, named `DEBRIEF-<domain>-<regime>`. Open a **New claim**
issue on this repository and a maintainer will create it, or fork a mission repository and adapt it.

## A dataset

Offer a **public** dataset that bears on an open gap or on a low-certainty relationship in a learning mission. Open
the **Data contribution** issue form: the public endpoint where the data can be fetched, what it measures, its
licence or terms, the gap it addresses, and how you want to be named. The data is not uploaded here; the cycle
records the link, the provenance and your terms, and your terms govern every use. On merge the gap moves from
`immovable` to `in_cycle` with your name in its history. The mission keeper then runs learning cycles on the data
against the outstanding gaps and low-certainty relationships; each such cycle carries `credits` naming you, and so
does every finding it produces.

## A hypothesis

Register a hypothesis and the signals that would test it, with the **Hypothesis** issue form: one falsifiable
claim, what observation would count for or against it, public endpoints for those signals if they exist, and the
measurement that does not exist yet if they do not. Your answers are copied verbatim into a `hypothesis` cycle and
hashed; the hash and the issue are your pin. The ledger opens a gap in your name. If the signals are public, the
keeper runs a learning cycle against them under your registered rule, and the cycle cites you. If the measurement
does not exist, the gap waits as `immovable` with your name on it until someone makes it. All certainty and
certification later gained on the hypothesis is credited to you.

## Learning missions and the kernel

In a learning mission (Mars, lunar) the learning cycles run through the keeper's kernel. An outside contributor
supplies data or a hypothesis and is credited on every cycle run on it. Anyone can also confirm or refute a
finding against the public data under its registered rule; that is recorded as independent confirmation and
strengthens `accepted`. `certified` requires the registered learning cycle to have run.

## What goes in the record

The ledger is for what a reader can reproduce, contribute to, or locate as the frontier. A finding carries its
standing, basis, what was written first, what happened, and its numbers. A cycle carries the question, the rule,
the predictions, the outcome and the misses; a confound stays with its cycle, once, in a line. Record history
(a lost file, a reconstruction) is stated once, in the mission's record note, and nowhere else. Corrections are
new cycles; old text is not annotated in place. How the file reached you belongs in the commit message.

## Words

`certified`, `accepted`, `refuted` have fixed meanings (`schema/SCHEMA.md` §3). An unchecked input is a gap,
not a finding, and has no standing. Do not write that a claim under audit "is verified", "is proved" or "is a
theorem"; the validator rejects it unless the mission's claim rule is met.

## Identity

Your Git identity is your name on the record. An ORCID is welcome and optional. No institution is required and
none is checked. Readers weigh names; the register records them.

## Licence

Code you contribute is Apache-2.0. Ledger text, traces and scorecards are CC-BY-4.0, so that attribution travels
with the record.
