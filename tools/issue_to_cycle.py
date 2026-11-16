#!/usr/bin/env python3
"""Turn a completed issue form into a cycle file.

usage: issue_to_cycle.py --kind read|rerun|data|hypothesis --issue N --author HANDLE --body FILE --out DIR [--date YYYY-MM-DD]
                         [--repo DIR]

Reads the issue body as GitHub renders a form ("### Label" headings followed by the answer), writes
DIR/<kind>-issue-N.yaml. Nothing in the answers is reworded; free text is copied into the cycle verbatim.
Standard library only; the output is YAML written by hand so it needs no dependency.

A read is written only if its checklist can be read: at least one line of the form `A1: signed` or
`A1: refused — reason`, no item answered twice. With --repo (the mission repository, full history), the trace commit
must exist and contain trace/DEFINITIONAL-TRACE.md, and every answered item must be on that trace's sign-off
checklist. The verdict is `signed` only if every item of that checklist is signed, `refused` if any is refused, and
`mixed` if some items are signed and the rest unanswered; only `signed` counts as a signature. Without --repo the
checklist cannot be compared with the trace, so an unrefused read is written as `mixed` for a maintainer to settle.
A read's free-text position, if given, is copied verbatim into outcome.position.
A form that fails these checks writes nothing, prints each problem, and exits 2.
"""
import hashlib, argparse, datetime, json, re, subprocess, sys

TRACE = "trace/DEFINITIONAL-TRACE.md"


class FormProblem(Exception):
    pass


def sections(body):
    out, cur = {}, None
    for line in body.splitlines():
        m = re.match(r"^###\s+(.*?)\s*$", line)
        if m:
            cur = m.group(1).strip().lower(); out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    vals = {k: "\n".join(v).strip() for k, v in out.items()}
    return {k: ("" if v == "_No response_" else v) for k, v in vals.items()}  # GitHub writes _No response_ for an empty optional field


def q(s):
    return json.dumps(s if s is not None else "", ensure_ascii=False)


def checklist(text):
    """Answered items, and the non-empty lines that could not be read as an answer."""
    items, unread = [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line == "_No response_":
            continue
        m = re.match(r"^(?:[-*]\s*)?([A-Za-z]\d*)\s*(?:\([^)]*\))?\s*:\s*(signed|refused)\s*(?:[—\-–:]\s*(.*))?$", line, re.I)
        if m:
            items.append({"item": m.group(1).upper(), "signed": m.group(2).lower() == "signed", "note": (m.group(3) or "").strip()})
        else:
            unread.append(line)
    return items, unread


def trace_items(repo, commit):
    """Item ids of the sign-off checklist in the trace as it stood at `commit`. Raises FormProblem if it cannot be read."""
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", commit or ""):
        raise FormProblem(f"Trace commit: `{commit}` is not a commit id. Give the 7 to 40 hex characters of the commit of the trace you read.")
    r = subprocess.run(["git", "-C", repo, "show", f"{commit}:{TRACE}"], capture_output=True, text=True)
    if r.returncode != 0:
        raise FormProblem(f"Trace commit: `{commit}` is not a commit of this repository that contains `{TRACE}`.")
    part = re.split(r"^##\s+(?:Part\s+)?E\b.*$", r.stdout, maxsplit=1, flags=re.M)
    ids = re.findall(r"^\s*[-*]\s*\[[ xX]\]\s*([A-Za-z]\d*)\b", part[1] if len(part) == 2 else "", flags=re.M)
    ids = list(dict.fromkeys(i.upper() for i in ids))
    if not ids:
        raise FormProblem(f"The trace at `{commit}` has no sign-off checklist (Part E) to sign.")
    return ids


def read_cycle(a, s):
    items, unread = checklist(s.get("checklist", ""))
    problems = [f"Checklist: this line is not in the form `A1: signed` or `A1: refused — reason`: `{u}`" for u in unread]
    if not items and not unread:
        problems.append("Checklist: no item is signed or refused. Write one line per item, `A1: signed` or `A1: refused — reason`.")
    seen = [i["item"] for i in items]
    problems += [f"Checklist: item {d} is answered more than once." for d in dict.fromkeys(x for x in seen if seen.count(x) > 1)]
    required = None
    if a.repo:
        try:
            required = trace_items(a.repo, s.get("trace commit", "").strip())
            problems += [f"Checklist: item {x} is not on the trace's checklist, whose items are {', '.join(required)}." for x in dict.fromkeys(seen) if x not in required]
        except FormProblem as e:
            problems.append(str(e))
    refused = [i for i in items if not i["signed"]]
    if s.get("overall", "").startswith("refused") and not refused:
        problems.append("Overall says refused, but no checklist item is refused. Name the item you refuse and the reason.")
    if problems:
        raise FormProblem("\n".join(problems))
    unanswered = [x for x in required if x not in seen] if required is not None else None
    verdict = "refused" if refused else "signed" if unanswered == [] else "mixed"
    by = s.get("name as you want it recorded", a.author)
    lines = [f"# read cycle from issue #{a.issue}; answers copied verbatim", "kind: read", f"cycle: {q('read-' + str(a.issue))}", f"dated: {q(a.date)}",
             f"by: {q(by)}", f"github: {q(a.author)}", "not_an_author_of_the_claim: true", "preregistered:",
             f"  commit: {q('trace/DEFINITIONAL-TRACE.md@' + s.get('trace commit', ''))}",
             "  question: \"Do the formal statements say what the paper claims, as rendered in the trace?\"",
             "  rule: \"Each checklist item is signed or refused by name. A refusal names the item and the reason.\"", "  before_data: true",
             "checklist:"] + [f"  - {{item: {q(i['item'])}, signed: {'true' if i['signed'] else 'false'}, note: {q(i['note'])}}}" for i in items]
    misses = [m for m in s.get("renderings you found wrong, even if harmless", "").splitlines() if m.strip() and m.strip() != "_No response_"]
    lines += ["outcome:", f"  verdict: {verdict}", "  misses:" + (" []" if not misses else "")] + [f"    - {q(m)}" for m in misses]
    position = s.get("your position, in your own words", "")
    if position:
        lines.append(f"  position: {q(position)}")
    n_s, n_r = sum(i["signed"] for i in items), len(refused)
    if verdict == "signed":
        spoken = f"{by} read the definitional trace and signed every item of its checklist."
    elif verdict == "refused":
        spoken = f"{by} read the definitional trace and signed {n_s} and refused {n_r} of its checklist."
    elif unanswered is None:
        spoken = f"{by} read the definitional trace and signed {n_s} of its checklist; the answers have not been compared with the trace."
    else:
        spoken = f"{by} read the definitional trace and signed {n_s} of its checklist; {len(unanswered)} not answered ({', '.join(unanswered)})."
    lines += [f"spoken: {q(spoken)}", "finding_ids: []", "gap_ids: []  # maintainer fills in the semantic gap id at merge"]
    return "\n".join(lines) + "\n"


def prereg_is_committed(text):
    """True only when the pre-registration answer points at something committed: a URL or a commit id, and the answer
    does not begin with "none". Free text such as "none (written locally, not committed)" is false."""
    t = (text or "").strip()
    if not t or t.lower().startswith("none") or t.lower() == "_no response_":
        return False
    return bool(re.search(r"https?://\S+|\b[0-9a-f]{7,40}\b", t))


def rerun_cycle(a, s):
    by = s.get("name as you want it recorded", a.author)
    pre = s.get("pre-registration", "none")
    lines = [f"# rerun cycle from issue #{a.issue}; answers copied verbatim", "kind: rerun", f"cycle: {q('rerun-' + str(a.issue))}", f"dated: {q(a.date)}",
             f"by: {q(by)}", f"github: {q(a.author)}", "preregistered:", f"  commit: {q(pre)}", "  question: \"Independent rerun of the mission's checks.\"",
             "  rule: \"As registered in the linked pre-registration, if any.\"", f"  before_data: {'true' if prereg_is_committed(pre) else 'false'}",
             f"environment: {q(s.get('environment', ''))}", "outcome:", f"  verdict: {s.get('verdict', 'mixed').split()[0]}",
             f"  results_text: {q(s.get('results', ''))}", "  misses:"]
    misses = [m for m in s.get("predictions that did not hold", "").splitlines() if m.strip() and m.strip() != "_No response_"]
    lines += [f"    - {q(m)}" for m in misses] if misses else []
    if not misses: lines[-1] = "  misses: []"
    lines += [f"spoken: {q(by + ' reran the mission checks. Verdict: ' + s.get('verdict', '').split()[0] + '.')}", "finding_ids: []", "gap_ids: []"]
    return "\n".join(lines) + "\n"


def gap_ids_in(text):
    """Ledger gap ids named in a free-text answer such as 'DEBRIEF-space-lunar, gap 1 (G2)': G2, ZG1."""
    return sorted(set(re.findall(r"\b[A-Z]{0,3}G\d+\b", text or "")))


def first_sentence(text, limit=200):
    t = " ".join((text or "").split())
    cut = t.find(". ")
    t = t[:cut + 1] if 0 < cut < limit else t
    return t if len(t) <= limit else t[:limit].rsplit(" ", 1)[0] + "…"


def data_cycle(a, s):
    by = s.get("supplier, as they want to be named", a.author)
    gids = gap_ids_in(s.get("mission repository and gap id", ""))
    endpoint = s.get("public endpoint", "")
    if not re.search(r"https?://", endpoint):
        raise FormProblem("the dataset must be public: give the URL of the endpoint where it can be fetched")
    lines = [f"# data cycle from issue #{a.issue}; answers copied verbatim; terms to be confirmed with the supplier before merge", "kind: data",
             f"cycle: {q('data-' + str(a.issue))}", f"dated: {q(a.date)}", f"by: {q(by)}", f"github: {q(a.author)}",
             f"institution: {q(s.get('institution (optional)', s.get('institution, as confirmed by the supplier', '')))}", f"licence: {q(s.get('licence or data-use terms', ''))}",
             f"endpoint: {q(endpoint)}", f"dataset: {q(s.get('dataset', ''))}", f"addresses_gap: {q(s.get('mission repository and gap id', ''))}", "preregistered:",
             f"  question: {q('What the data allows: ' + first_sentence(s.get('dataset', '')))}", f"  rule: {q(s.get('what will be done with it first', ''))}", "  before_data: true",
             "outcome:", "  verdict: admitted", f"spoken: {q('A dataset arrived from ' + by + '.')}", "finding_ids: []",
             "gap_ids: [" + ", ".join(q(g) for g in gids) + "]"]
    return "\n".join(lines) + "\n"


def hypothesis_cycle(a, s):
    hyp = s.get("hypothesis", "")
    if not hyp.strip():
        raise FormProblem("the hypothesis is empty")
    signals = s.get("signals that would validate or refute it", "")
    if not signals.strip():
        raise FormProblem("name the signals that would validate or refute the hypothesis")
    endpoints = s.get("public endpoints for those signals", "")
    needed = s.get("measurements needed that do not exist yet", "")
    bears = s.get("mission repository and the gaps or edges it bears on", "")
    by = s.get("name as you want it recorded", "") or a.author
    canon = "\n".join(x.strip() for x in (hyp, signals, endpoints, needed))
    sha = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    has_ep = bool(re.search(r"https?://", endpoints))
    gids = gap_ids_in(bears)
    spoken = by + " registered a hypothesis: " + first_sentence(hyp) + (" Its signals are public, so a cycle can be run on it." if has_ep else " The measurement it needs does not exist yet, so it waits, pinned, for that measurement.")
    lines = [f"# hypothesis cycle from issue #{a.issue}; answers copied verbatim and hashed; the hash is the submitter's pin", "kind: hypothesis",
             f"cycle: {q('hyp-' + str(a.issue))}", f"dated: {q(a.date)}", f"by: {q(by)}", f"github: {q(a.author)}",
             f"hypothesis: {q(hyp)}", f"signals: {q(signals)}", f"endpoints: {q(endpoints)}", f"measurements_needed: {q(needed)}", f"bears_on: {q(bears)}",
             "pinned:", f"  sha256: {q(sha)}", "  over: \"hypothesis, signals, endpoints, measurements_needed; each stripped, joined by newlines, UTF-8\"",
             f"  issue_url: {q(a.issue_url or '')}", f"  submitted_at: {q(a.submitted or '')}",
             "preregistered:", f"  question: {q(first_sentence(hyp))}", f"  rule: {q('the signals named by the submitter: ' + first_sentence(signals))}", "  before_data: true",
             "outcome:", "  verdict: admitted", f"  numbers: {{signals_have_public_endpoint: {'true' if has_ep else 'false'}}}",
             f"spoken: {q(spoken)}", "finding_ids: []", "gap_ids: [" + ", ".join(q(g) for g in gids) + "]"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["read", "rerun", "data", "hypothesis"]); ap.add_argument("--issue", required=True, type=int)
    ap.add_argument("--issue-url", dest="issue_url", default=""); ap.add_argument("--submitted", default="")
    ap.add_argument("--author", required=True); ap.add_argument("--body", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--repo", help="mission repository with full history; a read's trace commit and checklist are checked against it")
    a = ap.parse_args()
    s = sections(open(a.body, encoding="utf-8").read())
    try:
        text = {"read": read_cycle, "rerun": rerun_cycle, "data": data_cycle, "hypothesis": hypothesis_cycle}[a.kind](a, s)
    except FormProblem as e:
        print(e)
        sys.exit(2)
    import os; os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, f"{a.kind}-issue-{a.issue}.yaml")
    open(path, "w", encoding="utf-8").write(text)
    print(path)


if __name__ == "__main__":
    main()
