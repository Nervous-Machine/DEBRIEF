#!/usr/bin/env python3
"""Scaffold a tier-0 mission repository from a claim file.

usage: new_mission.py CLAIM.yaml OUTDIR [--protocol DIR]

Tier 0 means: the claim and its public artifacts are pinned (URLs, commits, hashes, dates), the claim is drawn as
open gaps with what would close each, and nothing has been run. The result validates under protocol 0.1.0 and goes
on the claims board at stage "Registered". The first rerun, read or trace is a contribution like any other.

CLAIM.yaml fields (see templates/claim.yaml): name, label, title, area, rests_on, problem{url, posed, plain,
formal_statement?}, claims[]{by, ai, submitted, where, summary_plain, notes_plain?, artifacts[]}, record[]{dated,
text}, site_status, extra_gaps[]?{title, spoken, what, who, kind, expected_signal}.

Words: nothing here may call the claim proved, verified or a theorem. The validator checks that; this tool writes
in the protocol's words and quotes nobody.
"""
import datetime, json, os, re, shutil, sys

try:
    import yaml
except ImportError:
    sys.exit("new_mission.py needs PyYAML")

TODAY = datetime.date.today().isoformat()
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
KIND_WORDS = {"lean": "a Lean development", "pdf": "a PDF write-up", "repo": "a public repository", "arxiv": "an arXiv preprint", "overleaf": "an Overleaf document (read link)", "zenodo": "a Zenodo deposit", "drive": "a shared document", "url": "a web page"}


def artifact_line(a):
    k = a.get("kind")
    if k == "repo":
        s = f"github.com/{a['repo']} at commit {a['commit']}" + (f" ({a['commit_date'][:10]})" if a.get("commit_date") else "")
        s += f"; licence {a['license']}" if a.get("license") else "; no licence file"
        if a.get("lean_files") is not None: s += f"; {a['lean_files']} Lean files" + ("; has a lakefile" if a.get("lakefile") else "; no lakefile at the root")
        return s
    if k == "arxiv":
        return f"arXiv:{a['id']} \"{a.get('title', '')}\" (published {a.get('published', '?')}, last revised {a.get('updated', '?')})"
    s = a.get("url", "")
    if a.get("sha256"): s += f" (sha256 {a['sha256']}, {a.get('bytes', '?')} bytes, fetched {a.get('fetched', TODAY)})"
    return s


def build(C):
    name, label = C["name"], C["label"]
    repo = f"DEBRIEF-math-{name}"
    mid = f"{name}-{TODAY[:7]}"
    base = {"schema_version": "nm-debrief-v1", "created_by": "DEBRIEF/tools/new_mission.py", "created_at": NOW, "mission_id": mid, "pod": repo,
            "provenance": {"source": f"public record to {TODAY}: the problem page, its proof-claims thread and the claimants' public artifacts, pinned in claim.yaml"}, "audience": "briefing"}
    doc = lambda **k: {**base, **k}
    claims = C["claims"]
    has_lean = any(a.get("kind") in ("lean", "repo") and (a.get("kind") == "lean" or a.get("lean_files")) for c in claims for a in c["artifacts"])
    has_formal_stmt = bool(C["problem"].get("formal_statement"))
    gaps = []
    pri = 1
    if has_lean:
        gaps.append(doc(gap_id="EG1", title="The Lean development has not been built or kernel-checked by anyone outside the claimant", status="proposed", opened_cycle=0, priority=pri, history=[],
                        closes_with=[{"what": "a pre-registered rerun: fetch at the pinned commit, build, confirm no sorry or admit, print the axioms", "kind": "rerun", "external": True, "who_could_act": "anyone with a machine and a few hours"}],
                        spoken="The claimant reports a Lean development that compiles with standard axioms only. Nobody outside the claimant has reported building it.",
                        ask={"spoken": "A rerun of the Lean build on an independent machine, written down first."},
                        expected_signal="a rerun cycle reporting build exit status, the sorry/admit scan and the axiom list for the main theorem", resolution_by="none registered")); pri += 1
        gaps.append(doc(gap_id="EG2", title="Do the formal statements say what the problem asks?", status="proposed", opened_cycle=0, priority=pri, history=[],
                        closes_with=([{"what": "a machine comparison of the claimant's main theorem with the third-party formal statement in google-deepmind/formal-conjectures, then a human read of any difference", "kind": "trace", "external": True, "who_could_act": "anyone who can read Lean; the two statements are public"}] if has_formal_stmt else []) +
                                    [{"what": "two independent mathematicians read the formal statement against the problem as posed and sign, or refuse", "kind": "read", "external": True, "who_could_act": "a mathematician in the problem's area, about an hour with a reading guide"}],
                        spoken="A Lean check establishes that the formal statement follows from its hypotheses. Whether that formal statement is the problem Erdős posed is a separate question that a person has to answer." + (" A third-party formalization of the problem statement exists, so part of this can be compared by machine." if has_formal_stmt else " No third-party formalization of the problem statement is recorded, so the comparison is entirely a human read."),
                        ask={"spoken": "A reading of the formal statement against the problem as posed, by someone who did not write it."},
                        expected_signal="a trace cycle and two signed read cycles, or a refusal naming the difference", resolution_by="none registered")); pri += 1
    else:
        gaps.append(doc(gap_id="EG1", title="No formal deduction exists for the claimed proof", status="proposed", opened_cycle=0, priority=pri, history=[],
                        closes_with=[{"what": "a Lean formalization of the main theorem, by the claimant or anyone else, with the statement written by a third party", "kind": "claim", "external": True, "who_could_act": "the claimant, or anyone who formalizes it"}],
                        spoken="The proof exists as a written argument only. There is no machine-checkable form of it, so nothing here can be settled by a rerun yet.",
                        ask={"spoken": "A formalization of the main theorem, with the statement written by someone other than the prover."},
                        expected_signal="a claim cycle pinning a Lean development, which opens the rerun and semantic gaps", resolution_by="none registered")); pri += 1
    gaps.append(doc(gap_id=f"EG{pri}", title="No independent mathematician has reported reading the proof, and there is no referee report", status="proposed", opened_cycle=0, priority=pri, history=[],
                    closes_with=[{"what": "a read cycle by a mathematician in the area who is not an author, signing or refusing each main step", "kind": "read", "external": True, "who_could_act": "a mathematician in the problem's area"},
                                 {"what": "a referee report or journal acceptance, recorded by date", "kind": "measurement", "external": True, "who_could_act": "a journal; the record notes the date when it happens"}],
                    spoken="The claim is listed on the problem's page, which states that appearing there is no guarantee of correctness and that nobody associated with the site has examined it." + (" The site has since marked this proof as accepted." if C.get("site_status", "").startswith("accepted") else "") + " No independent reading is on the public record" + (" beyond that." if C.get("site_status", "").startswith("accepted") else "."),
                    ask={"spoken": "Someone in the field reads it and says, under their name, what holds and what does not."},
                    expected_signal="a signed or refused read cycle; a dated referee report", resolution_by="none registered")); pri += 1
    for g in C.get("extra_gaps", []):
        gaps.append(doc(gap_id=f"EG{pri}", title=g["title"], status="proposed", opened_cycle=0, priority=pri, history=[],
                        closes_with=[{"what": g["what"], "kind": g.get("kind", "read"), "external": True, "who_could_act": g.get("who", "anyone")}], spoken=g["spoken"], ask={"spoken": g.get("ask", g["what"])},
                        expected_signal=g.get("expected_signal", "a cycle addressing it"), resolution_by="none registered")); pri += 1
    gids = [g["gap_id"] for g in gaps]
    rec = sorted(C.get("record", []), key=lambda r: str(r["dated"]))
    dated = f"{rec[0]['dated']} to {rec[-1]['dated']}" if len(rec) > 1 else (str(rec[0]["dated"]) if rec else TODAY)
    spoken0 = " ".join(r["text"].strip() for r in rec)
    cycle0 = doc(cycle=0, dated=dated, kind="replay", preregistered={"question": "What is on the public record about this claim?", "rule": "no look-ahead; each event dated by its first public posting; artifacts pinned by commit or hash", "predictions": [], "commit": None, "before_data": False},
                 outcome={"verdict": "admitted", "numbers": {"claims": len(claims), "artifacts": sum(len(c["artifacts"]) for c in claims)}}, spoken=spoken0, finding_ids=[], gap_ids=gids)
    background = [doc(term=f"Erdős Problem {label.replace('Erdős ', '')}", spoken=C["problem"]["plain"], source=C["problem"]["url"]),
                  doc(term="Proof claims on erdosproblems.com", spoken="The site lets anyone list a claimed proof. Its own text says that appearing there is no guarantee of correctness and does not mean anyone associated with the site has examined it. A listed claim is where checking starts, not where it ends.", source=C["claims"][0]["where"])]
    for c in claims:
        background.append(doc(term=f"The claim by {c['by']}", spoken=c["summary_plain"] + (" " + c["notes_plain"] if c.get("notes_plain") else ""), source=c["where"]))
    rests = C["rests_on"]
    mission = doc(title=C["title"], kind="audit", protocol_version="0.1.0", claim_rule_met=False, label=label, area=C["area"], rests_on=rests, pods=[repo], began=TODAY, status="active",
                  record_quality="full_ledger", record_note="Opened at tier zero: the claim and its artifacts are pinned, the gaps are drawn, nothing has been run or read by Nervous Machine.",
                  record_limits=["Nothing in this record has been checked by Nervous Machine or by anyone independent of the claimants; every item is an open gap."],
                  scope_limits=["Nervous Machine keeps score of the checks; it does not check the mathematics line by line.", f"Public record through {TODAY}."],
                  opening={"spoken": f"This record covers the claimed solution of {label.replace('Erdős', 'Erdős problem')}: what has been claimed, what it rests on, and what would have to be checked by whom."},
                  short_version={"spoken": C["short_version"]},
                  what_happened={"spoken": "The claim was pinned from the public record: the problem page, the proof-claims thread, and every artifact the claimants made public, by commit or hash. Nothing was run. The gaps that follow are the checks still owed."},
                  implications={"rely_on": [], "do_not_rely_on": [{"spoken": "the claimed solution as settled; nothing in it has standing yet", "finding_ids": []}], "stop": [], "new": []},
                  certainty_statement={"spoken": "Nothing is certified or accepted. Every item is open."},
                  sources=[{"kind": "problem", "ref": C["problem"]["url"]}] + [{"kind": a.get("kind", "url"), "ref": artifact_line(a)} for c in claims for a in c["artifacts"]]
                          + ([{"kind": "formal statement (third party)", "ref": f"github.com/{C['problem']['formal_statement']['repo']} {C['problem']['formal_statement']['path']} at {C['problem']['formal_statement']['commit']}"}] if has_formal_stmt else []))
    return {"missions": [mission], "cycles": [cycle0], "findings": [], "gaps": gaps, "anomalies": [], "background": background, "sessions": []}


def readme(C, L, repo):
    m = L["missions"][0]; p = C["problem"]
    lines = [f"# {repo}", "", f"A DEBRIEF mission record (protocol https://github.com/Nervous-Machine/DEBRIEF) for **{m['title']}**.", "",
             "**Standing.** Certified 0. Accepted 0. Refuted 0. Open gaps " + str(len(L["gaps"])) + ". This record is at tier zero: the claim and its public artifacts are pinned, the checks still owed are listed, and nothing has been run or read yet. The first contribution is open.", "",
             "This claim is on the public claims board, https://math-board.nervousmachine.com, which shows its stage, who has contributed, and what it needs next.", "",
             "## The problem", "", p["plain"], "", f"Source: {p['url']} (posed: {p.get('posed', 'see the problem page')}).", ""]
    if p.get("formal_statement"):
        f = p["formal_statement"]; lines += [f"A third-party formalization of the problem statement exists: `{f['path']}` in github.com/{f['repo']} at commit `{f['commit']}` (blob `{f.get('blob_sha', '')}`). It is the natural reference for whether a claimant's Lean theorem states this problem.", ""]
    lines += ["## The claim" + ("s" if len(C["claims"]) > 1 else ""), ""]
    for c in C["claims"]:
        lines += [f"**{c['by']}**, using {c['ai']}, submitted {c['submitted']} at {c['where']}.", "", c["summary_plain"] + (" " + c["notes_plain"] if c.get("notes_plain") else ""), "", "Artifacts, pinned:", ""]
        lines += [f"- {KIND_WORDS.get(a.get('kind'), 'a file')}: {artifact_line(a)}" for a in c["artifacts"]] + [""]
    lines += [f"Status on the problem page as of {TODAY}: {C.get('site_status', 'listed as a proof claim; not marked accepted')}.", "",
              "## What is owed", "", "Each open gap is in `ASKS.md` with what closes it and who could act. In order:", ""]
    lines += [f"{g['priority']}. **{g['title']}** ({g['gap_id']}): {g['ask']['spoken']}" for g in L["gaps"]]
    lines += ["", "## Contributing", "",
              "- **Rerun** (if there is a Lean development): copy `prereg_rerun.yaml`, fill in your predictions, register it with `tools/prereg.py register` from the protocol repository and commit it *before* running anything. Run. Report with the **Rerun report** issue form; it becomes a `rerun` cycle under your name.",
              "- **Read**: a trace (reading guide) does not exist yet. Writing one is itself a `trace` cycle. Once it exists, the **Semantic read** form takes signatures and refusals.",
              "- **Anything else**: open a plain issue.", "",
              "Rules and templates: https://github.com/Nervous-Machine/DEBRIEF/blob/main/CONTRIBUTING.md. Every contribution is one dated cycle under your own name and goes into `CITATION.cff` and the next release.", "",
              "## Layout", "", "```", f"ledger/{C['name']}.json   the ledger (protocol 0.1.0)", "claim.yaml            the pinned claim this record was opened from", "SCORECARD.md / ASKS.md  generated from the ledger", "prereg_rerun.yaml     a pre-registration template for the first rerun (unregistered)", "cycles/               contributed cycles, one file each", "```", "",
              "## Words", "", "This record never calls the claim proved, verified or a theorem. It records what was claimed, what was checked by whom under what rule, and what is still open. Nothing here has standing until a cycle gives it one."]
    return "\n".join(lines) + "\n"


def prereg_template(C):
    leans = [a for c in C["claims"] for a in c["artifacts"] if a.get("kind") == "repo" and a.get("lean_files")]
    lines = ["# Pre-registration for the first rerun of this claim's Lean development. Fill in, then register BEFORE running:",
             "#   python3 <DEBRIEF>/tools/prereg.py register prereg_rerun.yaml   (writes prereg_rerun.yaml.sha256; commit both)",
             f"mission: DEBRIEF-math-{C['name']}", "by: \"<your name as you want it recorded>\"", f"dated: \"<YYYY-MM-DD>\"",
             "question: \"Does the claimant's Lean development build at the pinned commit on an independent machine, with no sorry or admit, and which axioms does the main theorem use?\"",
             "rule: \"All checks below pass as predicted; any miss is recorded under misses.\"", "checks:"]
    for a in leans:
        lines += [f"  - id: R1", f"    what: \"fetch github.com/{a['repo']} at {a['commit']}; confirm the tree matches\"", "    prediction: \"commit present; tree unchanged\"",
                  "  - id: R2", "    what: \"lake exe cache get (if Mathlib) and lake build; record wall time and peak memory\"", "    prediction: \"exit 0, 0 errors; <your predicted time and memory>\"",
                  "  - id: R3", "    what: \"scan every .lean file of the development (excluding .lake and vendored dependencies) for sorry, admit, native_decide, axiom declarations, implemented_by and extern; list each hit by file and line\"", "    prediction: \"no hit in any file of the default build target's import closure; a hit in a file outside that closure (a statement-only or test file) is listed but is not a miss\"",
                  "  - id: R4", "    what: \"#print axioms on the main theorem\"", "    prediction: \"propext, Classical.choice, Quot.sound only\""]
        if C["problem"].get("formal_statement"):
            f = C["problem"]["formal_statement"]
            lines += ["  - id: R5", f"    what: \"compare the main theorem statement with FormalConjectures/{f['path'].split('/', 1)[-1]} at {f['commit']}; state identical, equivalent (with proof), or different\"", "    prediction: \"<your prediction>\""]
    if not leans:
        lines += ["  - id: R1", "    what: \"<there is no Lean development to rerun; a rerun cycle here would be a formalization claim; see EG1>\"", "    prediction: \"\""]
    return "\n".join(lines) + "\n"


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    cpath, out = argv[0], argv[1]
    proto = argv[argv.index("--protocol") + 1] if "--protocol" in argv else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    C = yaml.safe_load(open(cpath, encoding="utf-8"))
    repo = f"DEBRIEF-math-{C['name']}"
    L = build(C)
    d = os.path.join(out, repo)
    for sub in ("ledger", "cycles", ".github/workflows", ".github/ISSUE_TEMPLATE"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    json.dump(L, open(os.path.join(d, "ledger", f"{C['name']}.json"), "w"), indent=1, ensure_ascii=False)
    shutil.copy(cpath, os.path.join(d, "claim.yaml"))
    open(os.path.join(d, "README.md"), "w").write(readme(C, L, repo))
    open(os.path.join(d, "prereg_rerun.yaml"), "w").write(prereg_template(C))
    shutil.copy(os.path.join(proto, "LICENSE"), os.path.join(d, "LICENSE"))
    open(os.path.join(d, "LICENSE-CONTENT"), "w").write("The ledger text, README and reports in this repository are licensed CC-BY-4.0 (https://creativecommons.org/licenses/by/4.0/). Code is Apache-2.0 (LICENSE). Claimants' artifacts are not vendored; they are pinned by URL, commit and hash and remain under their own terms.\n")
    open(os.path.join(d, "cycles", "README.md"), "w").write("# Contributed cycles\n\nOne file per contribution, written from the issue forms or by hand from the templates in\nhttps://github.com/Nervous-Machine/DEBRIEF/tree/main/templates. The validation workflow merges these into the\nledger before checking it. Files here are never edited after merge; a correction or withdrawal is a new file.\n\nMaintainer step after a cycle's pull request is merged: run `merge_cycles.py` in place, re-render `SCORECARD.md` and\n`ASKS.md`, add the contributor to `CITATION.cff`, and commit.\n")
    open(os.path.join(d, "CITATION.cff"), "w").write(f'cff-version: 1.2.0\ntitle: "{repo}: DEBRIEF record of {C["title"]}"\nmessage: "Cite this record by version. Contributors of record are listed as authors; each is credited for the cycles they contributed."\ntype: dataset\nversion: 0.1.0\ndate-released: {TODAY}\nlicense: CC-BY-4.0\nrepository-code: https://github.com/Nervous-Machine/{repo}\nauthors:\n  - family-names: Bennett\n    given-names: Heidi\n    affiliation: Nervous Machine\n    # opened the record at tier zero ({TODAY}), with Claude Code as the operating agent\n')
    open(os.path.join(d, ".github", "workflows", "debrief.yml"), "w").write(f"name: DEBRIEF\non:\n  push:\n    branches: [main]\n  pull_request:\n  issues:\n    types: [opened, edited]\njobs:\n  validate:\n    if: github.event_name != 'issues'\n    uses: Nervous-Machine/DEBRIEF/.github/workflows/validate.yml@main\n    with:\n      ledger: ledger/{C['name']}.json\n  issue-to-cycle:\n    if: github.event_name == 'issues'\n    uses: Nervous-Machine/DEBRIEF/.github/workflows/issue-to-cycle.yml@main\n    with:\n      ledger: ledger/{C['name']}.json\n    permissions:\n      contents: write\n      pull-requests: write\n      issues: write\n")
    for f in ("rerun-report.yml", "semantic-read.yml", "config.yml"):
        src = os.path.join(proto, ".github", "ISSUE_TEMPLATE", f)
        if os.path.exists(src): shutil.copy(src, os.path.join(d, ".github", "ISSUE_TEMPLATE", f))
    open(os.path.join(d, ".gitignore"), "w").write("raw/\n.DS_Store\n")
    print(f"wrote {d}: {len(L['gaps'])} gaps, {len(L['background'])} background items")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
