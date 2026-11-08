#!/usr/bin/env python3
"""Turn a completed issue form into a cycle file.

usage: issue_to_cycle.py --kind read|rerun|data --issue N --author HANDLE --body FILE --out DIR [--date YYYY-MM-DD]

Reads the issue body as GitHub renders a form ("### Label" headings followed by the answer), writes
DIR/<kind>-issue-N.yaml. Nothing in the answers is reworded; free text is copied into the cycle verbatim.
Standard library only; the output is YAML written by hand so it needs no dependency.
"""
import argparse, datetime, json, re, sys


def sections(body):
    out, cur = {}, None
    for line in body.splitlines():
        m = re.match(r"^###\s+(.*?)\s*$", line)
        if m:
            cur = m.group(1).strip().lower(); out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def q(s):
    return json.dumps(s if s is not None else "", ensure_ascii=False)


def checklist(text):
    items = []
    for line in text.splitlines():
        m = re.match(r"^\s*([A-Za-z]\d*|D)\s*:\s*(signed|refused)\s*(?:[—\-–:]\s*(.*))?$", line.strip(), re.I)
        if m:
            items.append({"item": m.group(1).upper(), "signed": m.group(2).lower() == "signed", "note": (m.group(3) or "").strip()})
    return items


def read_cycle(a, s):
    items = checklist(s.get("checklist", ""))
    refused = [i for i in items if not i["signed"]]
    verdict = "refused" if refused or s.get("overall", "").startswith("refused") else "signed"
    by = s.get("name as you want it recorded", a.author)
    lines = [f"# read cycle from issue #{a.issue}; answers copied verbatim", "kind: read", f"cycle: {q('read-' + str(a.issue))}", f"dated: {q(a.date)}",
             f"by: {q(by)}", f"github: {q(a.author)}", "not_an_author_of_the_claim: true", "preregistered:",
             f"  commit: {q('trace/DEFINITIONAL-TRACE.md@' + s.get('trace commit', ''))}",
             "  question: \"Do the formal statements say what the paper claims, as rendered in the trace?\"",
             "  rule: \"Each checklist item is signed or refused by name. A refusal names the item and the reason.\"", "  before_data: true",
             "checklist:"] + [f"  - {{item: {q(i['item'])}, signed: {'true' if i['signed'] else 'false'}, note: {q(i['note'])}}}" for i in items]
    misses = [m for m in s.get("renderings you found wrong, even if harmless", "").splitlines() if m.strip() and m.strip() != "_No response_"]
    lines += ["outcome:", f"  verdict: {verdict}", "  misses:" + (" []" if not misses else "")] + [f"    - {q(m)}" for m in misses]
    n_s, n_r = sum(i["signed"] for i in items), len(refused)
    spoken = f"{by} read the definitional trace and {'signed every item' if not refused else f'signed {n_s} and refused {n_r}'} of its checklist."
    lines += [f"spoken: {q(spoken)}", "finding_ids: []", "gap_ids: []  # maintainer fills in the semantic gap id at merge"]
    return "\n".join(lines) + "\n"


def rerun_cycle(a, s):
    by = s.get("name as you want it recorded", a.author)
    pre = s.get("pre-registration", "none")
    lines = [f"# rerun cycle from issue #{a.issue}; answers copied verbatim", "kind: rerun", f"cycle: {q('rerun-' + str(a.issue))}", f"dated: {q(a.date)}",
             f"by: {q(by)}", f"github: {q(a.author)}", "preregistered:", f"  commit: {q(pre)}", "  question: \"Independent rerun of the mission's checks.\"",
             "  rule: \"As registered in the linked pre-registration, if any.\"", f"  before_data: {'false' if pre.strip().lower() in ('none', '', '_no response_') else 'true'}",
             f"environment: {q(s.get('environment', ''))}", "outcome:", f"  verdict: {s.get('verdict', 'mixed').split()[0]}",
             f"  results_text: {q(s.get('results', ''))}", "  misses:"]
    misses = [m for m in s.get("predictions that did not hold", "").splitlines() if m.strip() and m.strip() != "_No response_"]
    lines += [f"    - {q(m)}" for m in misses] if misses else []
    if not misses: lines[-1] = "  misses: []"
    lines += [f"spoken: {q(by + ' reran the mission checks. Verdict: ' + s.get('verdict', '').split()[0] + '.')}", "finding_ids: []", "gap_ids: []"]
    return "\n".join(lines) + "\n"


def data_cycle(a, s):
    by = s.get("supplier, as they want to be named", a.author)
    lines = [f"# data cycle from issue #{a.issue}; answers copied verbatim; terms to be confirmed with the supplier before merge", "kind: data",
             f"cycle: {q('data-' + str(a.issue))}", f"dated: {q(a.date)}", f"by: {q(by)}", f"github: {q(a.author)}",
             f"institution: {q(s.get('institution, as confirmed by the supplier', ''))}", f"licence: {q(s.get('licence or data-use terms', ''))}",
             f"dataset: {q(s.get('dataset', ''))}", f"addresses_gap: {q(s.get('mission repository and gap id', ''))}", "preregistered:",
             f"  question: {q('What the data allows: ' + s.get('dataset', '')[:120])}", f"  rule: {q(s.get('what will be done with it first', ''))}", "  before_data: true",
             "outcome:", "  verdict: admitted", f"spoken: {q('A dataset arrived from ' + by + '.')}", "finding_ids: []", "gap_ids: []"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["read", "rerun", "data"]); ap.add_argument("--issue", required=True, type=int)
    ap.add_argument("--author", required=True); ap.add_argument("--body", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    s = sections(open(a.body, encoding="utf-8").read())
    text = {"read": read_cycle, "rerun": rerun_cycle, "data": data_cycle}[a.kind](a, s)
    import os; os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, f"{a.kind}-issue-{a.issue}.yaml")
    open(path, "w", encoding="utf-8").write(text)
    print(path)


if __name__ == "__main__":
    main()
