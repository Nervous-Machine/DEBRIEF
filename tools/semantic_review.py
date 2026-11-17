#!/usr/bin/env python3
"""Automatic second review of meaning: does the formal statement say what the problem asks?

usage: semantic_review.py prereg --repo DIR --ledger LEDGER.json [--model MODEL]
       semantic_review.py review --repo DIR --ledger LEDGER.json
       semantic_review.py needed --repo DIR --ledger LEDGER.json      prints yes/no

Two stages, committed separately so git history shows the pre-registration came first:

  prereg  gathers the inputs (the problem as posed, from erdosproblems.com; the pinned DeepMind formal-conjectures
          file; the Challenge.lean of any Palomar-registered development pinned in the ledger), hashes each, and
          writes prereg_review.yaml naming the model, the inputs and their hashes, and the rules. Registered with
          tools/prereg.py. Nothing is reviewed yet.
  review  refuses unless the inputs still hash as registered, asks the model for a structured list of differences
          (by default through the local Claude Code login, `claude -p`, so no API key is needed; `--via api` uses
          the Anthropic API and ANTHROPIC_API_KEY instead), and writes:
            trace/DEFINITIONAL-TRACE.md  if the record has no reading guide yet (the lean form, with a checklist), or
            trace/SECOND-REVIEW.md       beside an existing guide (differences only; the guide's checklist stays),
          plus one `trace` cycle in the ledger. A difference the model marks as possibly changing the meaning is
          listed for a maintainer in the summary; it is not opened as an anomaly automatically.

The review is a second, independent reading beside Palomar's model judgement, not a human reading; it changes no
standing. It records which AI systems the claimants listed, and flags it when the reviewer is the same family.
`needed` says whether a review is due: none yet, or the inputs changed since the last one.
"""
import argparse, datetime, hashlib, html, json, os, re, subprocess, sys, urllib.request

try:
    import yaml
except ImportError:
    sys.exit("semantic_review.py needs PyYAML (pip install pyyaml)")

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL = "claude-opus-5-5"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "DEBRIEF-review (github.com/Nervous-Machine/DEBRIEF)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def problem_text(number, claim):
    """The statement as the problem page shows it; falls back to the record's own summary, marked as such."""
    if number:
        try:
            page = fetch(f"https://www.erdosproblems.com/{number}")
            t = re.sub(r"(?s)<(script|style).*?</\1>", "", page)
            t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
            m = re.search(rf"Random (.+?) #{number} :", t)
            if m and len(m.group(1)) > 40:
                return {"source": f"https://www.erdosproblems.com/{number}", "text": m.group(1).strip(), "verbatim": True}
        except Exception as e:
            print(f"problem page not read: {e}", file=sys.stderr)
    p = claim.get("problem") or {}
    return {"source": "claim.yaml problem.plain (the record's own summary; the page could not be read)", "text": (p.get("plain") or "").strip(), "verbatim": False}


def inputs(repo, ledger):
    name = os.path.basename(os.path.abspath(repo))
    m = re.search(r"erdos(\d+)$", name); number = m.group(1) if m else None
    claim = yaml.safe_load(open(os.path.join(repo, "claim.yaml"), encoding="utf-8")) if os.path.exists(os.path.join(repo, "claim.yaml")) else {}
    L = json.load(open(os.path.join(repo, ledger)))
    out = {"problem": problem_text(number, claim), "statements": []}
    fs = (claim.get("problem") or {}).get("formal_statement")
    if fs:
        url = f"https://raw.githubusercontent.com/{fs['repo']}/{fs['commit']}/{fs['path']}"
        try:
            out["statements"].append({"name": f"{fs['repo']} {fs['path']}", "url": url, "commit": fs["commit"], "text": fetch(url)})
        except Exception as e:
            print(f"formal statement not read: {e}", file=sys.stderr)
    for c in L["cycles"]:  # Palomar-registered developments: their Challenge.lean is the statement Palomar checked
        if c.get("by") == "Palomar registry" and c.get("kind") == "rerun":
            n = c["outcome"]["numbers"]; repo_, commit = n.get("repository"), n.get("commit")
            if repo_ and commit:
                url = f"https://raw.githubusercontent.com/{repo_}/{commit}/Challenge.lean"
                try:
                    out["statements"].append({"name": f"{repo_} Challenge.lean (registered with Palomar)", "url": url, "commit": commit,
                                              "palomar": (c.get("preregistered") or {}).get("results", [None])[0] or n.get("palomar_id"), "text": fetch(url)})
                except Exception:
                    pass
    out["claimant_ai"] = [c.get("ai", "") for c in claim.get("claims", [])]
    out["number"] = number
    return out, L


def input_hashes(inp):
    return {"problem": sha(inp["problem"]["text"]), **{s["name"]: sha(s["text"]) for s in inp["statements"]}}


SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "two or three plain sentences: does each formal statement say what the problem asks?"},
        "differences": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string", "description": "D1, D2, ..."},
            "where": {"type": "string", "description": "which formal statement and which part of it"},
            "problem_says": {"type": "string"}, "formal_says": {"type": "string"},
            "kind": {"type": "string", "enum": ["convention", "encoding", "strength", "boundary", "type", "wording", "scope", "other"]},
            "could_change_meaning": {"type": "string", "enum": ["yes", "no", "uncertain"]},
            "why": {"type": "string"}},
            "required": ["id", "where", "problem_says", "formal_says", "kind", "could_change_meaning", "why"], "additionalProperties": False}},
        "checklist": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string", "description": "A1, A2, ...; A0 for an item that needs the original source"},
            "item": {"type": "string"}, "optional": {"type": "boolean"}},
            "required": ["id", "item", "optional"], "additionalProperties": False}},
        "not_checked": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]}},
    "required": ["summary", "differences", "checklist", "not_checked", "confidence"], "additionalProperties": False}

SYSTEM = """You review whether formal (Lean 4 / Mathlib) statements say what a mathematical problem asks. You do not judge any proof.

Compare the problem as posed with each formal statement. Record every difference you can see, harmless or not: quantifier order, hypotheses added or dropped, boundary and trivial cases, Lean conventions (truncated subtraction, division by zero, junk values, coercions, universes), encodings of a notion, strength (stronger or weaker than asked), and wording the problem leaves open. Quote the formal text exactly where you cite it. Mark could_change_meaning "yes" only when a reader who accepted the formal statement would have accepted a different mathematical claim than the problem's; "uncertain" when it depends on how the problem's wording is read or on a definition you cannot see; otherwise "no", with the reason.

Then write a short checklist (three to six items) a mathematician could sign or refuse in under an hour, each pointing at the differences it covers. Mark an item optional if it needs a source you were not given. List what you did not check. Be plain and exact; no praise, no hedging beyond what the evidence requires."""


def cmd_prereg(a):
    inp, L = inputs(a.repo, a.ledger)
    if not inp["statements"]:
        sys.exit("no formal statement to review")
    family = "Claude" if a.model.startswith("claude") else a.model
    overlap = [x for x in inp["claimant_ai"] if family.lower() in x.lower()]
    p = os.path.join(a.repo, "prereg_review.yaml")
    if os.path.exists(p):  # a later review is an amendment, never an edit of the registered body
        n = len(re.findall(r"^# ---- Amendment", open(p).read(), re.M)) + 1
        body = yaml.safe_dump({"model": a.model, "inputs": input_hashes(inp), "sources": {s["name"]: s["url"] for s in inp["statements"]} | {"problem": inp["problem"]["source"]}}, sort_keys=False, allow_unicode=True)
        subprocess.run([sys.executable, os.path.join(HERE, "prereg.py"), "amend", p, f"R{n}", "Re-review because the inputs changed. " + body.replace("\n", " | ")], check=True)
        print(p); return
    doc = {
        "mission": os.path.basename(os.path.abspath(a.repo)), "dated": datetime.date.today().isoformat(),
        "by": f"Nervous Machine (automated second review, {a.model})",
        "question": "Does each formal statement say what the problem asks? A second reading beside Palomar's model judgement, not a human reading.",
        "model": a.model,
        "via": "Claude Code (claude -p, local login, no tools)" if a.via == "claude-code" else "Anthropic API",
        "inputs": input_hashes(inp),
        "sources": {"problem": inp["problem"]["source"], **{s["name"]: s["url"] for s in inp["statements"]}},
        "problem_text_verbatim": inp["problem"]["verbatim"],
        "rules": {
            "R1": "the review reads only the inputs hashed above; it refuses to run if any hash has changed",
            "R2": "every difference is recorded, harmless or not, with the formal text quoted exactly",
            "R3": "a difference marked yes or uncertain is listed for a maintainer, who decides whether to open an anomaly and send it upstream",
            "R4": "standing is unchanged by construction; the review is a reading, not a check"},
        "independence": {"reviewer_family": family, "claimant_ai_listed": inp["claimant_ai"],
                         "same_family_as_a_claimant_tool": bool(overlap)},
        "predictions": {"P1": "at least one convention or encoding difference will need a sentence",
                        "P2": "no difference will be marked yes unless the record already flags one"}}
    with open(p, "w", encoding="utf-8") as f:
        f.write("# Pre-registration: automated second review of meaning. Written and hashed BEFORE the review runs.\n")
        yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True, width=120)
    subprocess.run([sys.executable, os.path.join(HERE, "prereg.py"), "register", p], check=True)
    print(p)


def review_claude_code(inp, model):
    """The same review through the local Claude Code login: no tools, no settings, no session saved."""
    import tempfile
    prompt = "\n\n---\n\n".join(review_parts(inp))
    import shutil
    exe = os.environ.get("DEBRIEF_CLAUDE") or shutil.which("claude") or next(
        (x for x in ("/opt/homebrew/bin/claude", "/usr/local/bin/claude", os.path.expanduser("~/.local/bin/claude"), os.path.expanduser("~/.claude/local/claude")) if os.path.exists(x)), None)
    if not exe:
        sys.exit("the claude command was not found; set DEBRIEF_CLAUDE to its path")
    cmd = [exe, "-p", "--model", model, "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
           "--system-prompt", SYSTEM, "--tools", "", "--no-session-persistence", "--effort", "high", "--setting-sources", ""]
    with tempfile.TemporaryDirectory() as d:  # an empty folder, so no project instructions are picked up
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=d, timeout=1800)
    try:
        out = json.loads(p.stdout)
    except json.JSONDecodeError:
        sys.exit(f"claude -p failed: {p.stderr.strip() or p.stdout[:500]}")
    if out.get("is_error") or not out.get("structured_output"):
        sys.exit(f"claude -p returned no review: {out.get('subtype')} {str(out.get('result'))[:500]}")
    served = next(iter(out.get("modelUsage") or {model: 0}))
    return out["structured_output"], f"{served} via Claude Code", f"session {out.get('session_id')}"


def review_parts(inp):
    parts = [f"Problem as posed ({inp['problem']['source']}{'' if inp['problem']['verbatim'] else '; a summary, not verbatim'}):\n\n{inp['problem']['text']}"]
    for s in inp["statements"]:
        parts.append(f"Formal statement: {s['name']} at {s['commit']}\n\n```lean\n{s['text']}\n```")
    return parts


def review_model(inp, model):
    import anthropic
    client = anthropic.Anthropic()
    parts = review_parts(inp)
    resp = client.beta.messages.create(
        model=model, max_tokens=16000, system=SYSTEM,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": "\n\n---\n\n".join(parts)}])
    if resp.stop_reason == "refusal":
        sys.exit(f"the model declined ({getattr(resp.stop_details, 'category', None)}); request {resp._request_id}")
    if resp.stop_reason == "max_tokens":
        sys.exit(f"the review was cut off at max_tokens; request {resp._request_id}")
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text), resp.model, resp._request_id


def render(inp, r, model, first):
    L = [f"# {'Reading guide' if first else 'Second review'}: {'Erdős Problem #' + inp['number'] if inp['number'] else 'the claim'}", "",
         f"An automated second reading of meaning by {model}, written after a hashed pre-registration (`prereg_review.yaml`). "
         "It sets the problem as posed beside each formal statement and lists every difference the reviewer saw. "
         "It is a reading, not a check, and not a human signature; it changes no standing. "
         "Leave your own reasoning with the **Reasoning note** form, or sign or refuse with the **Semantic read** form.", "",
         f"**Summary.** {r['summary']} (reviewer's confidence: {r['confidence']})", "",
         "## A. The problem as posed", "", f"Source: {inp['problem']['source']}" + ("" if inp["problem"]["verbatim"] else " (not verbatim)") + ".", "",
         "> " + inp["problem"]["text"], "", "## B. The formal statements", ""]
    for i, s in enumerate(inp["statements"], 1):
        L += [f"### B{i}. {s['name']} at `{s['commit'][:7]}`", "", f"Source: {s['url']}" + (f". Rendered with term explanations: {s['palomar']}" if s.get("palomar") else ". Not registered with Palomar."), "",
              "<details><summary>The file, verbatim</summary>", "", "```lean", s["text"].rstrip(), "```", "", "</details>", ""]
    L += ["## C. Differences", "", "| id | where | the problem says | the formal statement says | kind | could it change the meaning? | why |", "|---|---|---|---|---|---|---|"]
    cell = lambda x: str(x).replace("|", "\\|").replace("\n", " ")
    for d in r["differences"]:
        L.append("| " + " | ".join(cell(d[k]) for k in ("id", "where", "problem_says", "formal_says", "kind", "could_change_meaning", "why")) + " |")
    L += ["", "## D. What this review did not check", ""] + [f"- {x}" for x in r["not_checked"]] + [""]
    if first:
        L += ["## Sign-off checklist", "", "Sign or refuse each item with the **Semantic read** form. Items marked optional may be left out.", ""]
        L += [f"- [ ] {c['id']}{' (optional)' if c['optional'] else ''}: {c['item']}" for c in r["checklist"]]
    return "\n".join(L) + "\n"


def cmd_review(a):
    p = os.path.join(a.repo, "prereg_review.yaml")
    reg = yaml.safe_load(open(p).read().split("# ---- Amendment")[0])
    inp, L = inputs(a.repo, a.ledger)
    now = input_hashes(inp)
    registered = open(p).read()  # the body or a later amendment must name every current input hash
    if not all(h in registered for h in now.values()):
        sys.exit("inputs changed since the pre-registration; run `prereg` again (it records an amendment)")
    model = reg["model"]
    r, served, req = (review_model if reg.get("via") == "Anthropic API" else review_claude_code)(inp, model)
    tdir = os.path.join(a.repo, "trace"); os.makedirs(tdir, exist_ok=True)
    first = not os.path.exists(os.path.join(tdir, "DEFINITIONAL-TRACE.md"))
    out = os.path.join(tdir, "DEFINITIONAL-TRACE.md" if first else "SECOND-REVIEW.md")
    open(out, "w", encoding="utf-8").write(render(inp, r, served, first))
    json.dump({"model": served, "request_id": req, "inputs": now, "review": r}, open(os.path.join(tdir, "second-review.json"), "w"), indent=1, ensure_ascii=False)
    flagged = [d for d in r["differences"] if d["could_change_meaning"] != "no"]
    base = {k: L["cycles"][0][k] for k in ("schema_version", "mission_id", "pod", "audience") if k in L["cycles"][0]}
    today = datetime.date.today().isoformat()
    L["cycles"].append({**base, "created_by": "DEBRIEF/tools/semantic_review.py", "created_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provenance": {"source": f"automated review by {served}, request {req}"},
        "kind": "trace", "cycle": f"review-{today}", "dated": today, "by": f"Nervous Machine (automated second review, {served})",
        "preregistered": {"commit": "prereg_review.yaml", "results": [os.path.relpath(out, a.repo), "trace/second-review.json"],
                          "question": reg["question"], "rule": "; ".join(reg["rules"].values()), "predictions": [f"{k}: {v}" for k, v in reg["predictions"].items()], "before_data": True},
        "outcome": {"verdict": "learned", "numbers": {"statements_compared": len(inp["statements"]), "differences_recorded": len(r["differences"]),
                    "possibly_meaning_changing": len(flagged), "checklist_items": len(r["checklist"]) if first else 0, "confidence": r["confidence"],
                    "human_review": False, "same_family_as_a_claimant_tool": reg["independence"]["same_family_as_a_claimant_tool"]}, "misses": []},
        "spoken": f"An automated second review by {served} compared the problem as posed with {len(inp['statements'])} formal statement(s) and recorded {len(r['differences'])} difference(s), "
                  + (f"{len(flagged)} of which might change the meaning. " if flagged else "none of which it judged to change the meaning. ")
                  + "It is a reading, not a human signature.",
        "finding_ids": [], "gap_ids": []})
    json.dump(L, open(os.path.join(a.repo, a.ledger), "w"), indent=1, ensure_ascii=False); open(os.path.join(a.repo, a.ledger), "a").write("\n")
    lines = [f"Automated second review of meaning ({served}) for {os.path.basename(os.path.abspath(a.repo))}.", "", r["summary"], "",
             f"{len(r['differences'])} difference(s) recorded in `{os.path.relpath(out, a.repo)}`."]
    if flagged:
        lines += ["", "For a maintainer, possibly meaning-changing (decide whether to open an anomaly and send it upstream):"] + [f"- {d['id']} ({d['could_change_meaning']}): {d['why']}" for d in flagged]
    if reg["independence"]["same_family_as_a_claimant_tool"]:
        lines += ["", f"Note: the reviewer is the same model family as a tool a claimant listed ({', '.join(reg['independence']['claimant_ai_listed'])})."]
    s = "\n".join(lines) + "\n"
    print(s)
    if a.summary: open(a.summary, "w").write(s)


def cmd_needed(a):
    p = os.path.join(a.repo, "prereg_review.yaml")
    if not os.path.exists(os.path.join(a.repo, "claim.yaml")):
        print("no"); return
    if not os.path.exists(p):
        print("yes"); return
    inp, _ = inputs(a.repo, a.ledger)
    print("no" if all(h in open(p).read() for h in input_hashes(inp).values()) else "yes")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["prereg", "review", "needed"])
    ap.add_argument("--repo", required=True); ap.add_argument("--ledger", required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL); ap.add_argument("--summary")
    ap.add_argument("--via", choices=["claude-code", "api"], default="claude-code")
    a = ap.parse_args()
    {"prereg": cmd_prereg, "review": cmd_review, "needed": cmd_needed}[a.stage](a)


if __name__ == "__main__":
    main()
