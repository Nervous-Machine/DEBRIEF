#!/usr/bin/env python3
"""Watch other registries for one claim and record what changed.

usage: watch_external.py --repo DIR --ledger LEDGER.json [--date YYYY-MM-DD] [--write] [--summary OUT.md]

Reads three public sources and compares them with the claim's latest external snapshot (a `replay` cycle whose
outcome.numbers.external holds the last reading):

  Palomar registry       data.palomar-registry.org (CC0): entries matching a repository pinned in claim.yaml,
                         or titled with this Erdős problem number
  DeepMind formal-conjectures  FormalConjectures/ErdosProblems/<N>.lean on main: the main statement's
                         `category` tag and any `formal_proof` link
  erdosproblems.com      the site's public database, teorth/erdosproblems data/problems.yaml: the problem's state

Nothing is written unless a reading changed. With --write, a change appends:
  - one `replay` cycle `external-<date>` holding the new reading (no new checking; not a contribution);
  - for each Palomar entry not seen before, a `rerun` cycle credited to "Palomar registry", recorded from its
    public data. If the entry's repository is pinned in claim.yaml, the claim's build gap gets a history line, and
    when every pinned Lean repository has a Palomar check the gap is resolved (DEBRIEF defers to Palomar for
    machine checks). An entry for a repository that is not pinned is credited but flagged for a maintainer,
    who decides whether to pin it.
Standing (findings) never changes here. --summary writes a markdown note for the pull request.
Exit code: 0 always on success; the summary's first line says whether anything changed.
"""
import argparse, datetime, json, os, re, sys, urllib.parse, urllib.request

try:
    import yaml
except ImportError:
    sys.exit("watch_external.py needs PyYAML (pip install pyyaml)")

PALOMAR = "https://data.palomar-registry.org/api/v1/results?q="
PALOMAR_ENTRY = "https://palomar-registry.org/entry.html?id="
FC_REPO = "google-deepmind/formal-conjectures"
EP_REPO = "teorth/erdosproblems"


def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": "DEBRIEF-watch (github.com/Nervous-Machine/DEBRIEF)"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and url.startswith("https://api.github.com/"):
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8")
    return body if raw else json.loads(body)


def gh_head(repo):
    return get(f"https://api.github.com/repos/{repo}/commits/HEAD")["sha"]


def palomar(number, repos):
    queries = ([f"Erdős {number}", f"erdos {number}"] if number else []) + sorted({r.split("/")[0] for r in repos} | {r.split("/")[1] for r in repos})
    seen = {}
    for q in queries:
        try:
            d = get(PALOMAR + urllib.parse.quote(q))
        except Exception as e:
            print(f"palomar query {q!r} failed: {e}", file=sys.stderr); continue
        for x in d.get("entries", []):
            src = (x.get("source") or {}).get("repository", "")
            titled = number and re.search(rf"Erd[őo]s(?:\s+Problem)?\s*#?\s*{number}\b", x.get("title", ""), re.I)
            if src.lower() in {r.lower() for r in repos} or titled:
                seen[x["id"]] = {"id": x["id"], "url": PALOMAR_ENTRY + x["id"], "title": x.get("title", ""), "repository": src,
                                 "commit": (x.get("source") or {}).get("commit"), "published_at": x.get("published_at"),
                                 "authors": [a.get("name") for a in x.get("authors", [])], "status": x.get("status"),
                                 "pinned_here": src.lower() in {r.lower() for r in repos}}
    detail = {}
    for i, e in seen.items():  # trust level, kernels and statement review live in the full entry
        try:
            full = get(f"https://data.palomar-registry.org/entries/{i}-v1.json")
            detail[i] = {"trust_level": (full.get("trust") or {}).get("level"),
                         "kernels": [k.get("name") for k in (full.get("verification") or {}).get("kernels", [])],
                         "statement_review": ", ".join((full.get("review") or {}).get("reviewer_models", [])) + f" (outcome {(full.get('review') or {}).get('outcome')})"}
        except Exception:
            detail[i] = {}
        e.update(detail[i])
    return sorted(seen.values(), key=lambda e: e["id"])


def formal_conjectures(number):
    if not number:
        return {"main_statement": "not applicable", "formal_proof_linked": None, "url": None, "commit": None}
    sha = gh_head(FC_REPO)
    path = f"FormalConjectures/ErdosProblems/{number}.lean"
    try:
        src = get(f"https://raw.githubusercontent.com/{FC_REPO}/{sha}/{path}", raw=True)
    except Exception:
        return {"main_statement": "no file", "formal_proof_linked": None, "url": None, "commit": sha}
    # attribute blocks directly above `theorem erdos_<N>` or its `.parts.*` (not `.variants.*`)
    blocks = re.findall(rf"@\[((?:[^\]\"]|\"[^\"]*\")*)\]\s*theorem\s+erdos_{number}(\.parts\.[\w.]+)?\s", src)
    cats, proofs = [], []
    for attrs, _ in blocks:
        m = re.search(r"category\s+research\s+(\w+)", attrs)
        cats.append(m.group(1) if m else "unknown")
        p = re.search(r"formal_proof\s+using\s+\w+\s+at\s+\"([^\"]+)\"", attrs)
        if p: proofs.append(p.group(1))
    variants = re.findall(r"category\s+research\s+(\w+)[^\]]*\]\s*theorem\s+erdos_\d+\.variants\.", src)
    if not cats:
        main = "no main statement found"
    elif all(c == "solved" for c in cats):
        main = "solved"
    else:
        main = "open" if all(c == "open" for c in cats) else "partly solved"
    if main != "solved" and "solved" in variants:
        main += "; variants solved"
    return {"main_statement": main, "formal_proof_linked": proofs[0] if proofs else None,
            "url": f"https://github.com/{FC_REPO}/blob/{sha}/{path}", "commit": sha}


def erdosproblems(number):
    if not number:
        return {"state": "not applicable", "source": None, "commit": None}
    sha = gh_head(EP_REPO)
    data = yaml.safe_load(get(f"https://raw.githubusercontent.com/{EP_REPO}/{sha}/data/problems.yaml", raw=True))
    p = next((p for p in data if str(p.get("number")) == str(number)), None)
    state = ((p or {}).get("status") or {}).get("state", "not listed")
    return {"state": state, "source": f"https://github.com/{EP_REPO}/blob/{sha}/data/problems.yaml", "commit": sha}


def key(ext):
    """The parts of a reading that count as a change (commit ids move daily and do not)."""
    pal = ext.get("palomar", {})
    ids = sorted(e["id"] for e in pal.get("entries", [])) or ([pal["id"]] if pal.get("id") else [])
    fc, ep = ext.get("formal_conjectures", {}), ext.get("erdosproblems", {})
    main = re.sub(r";.*variants? solved$", "; variants solved", str(fc.get("main_statement")))
    return json.dumps({"palomar": ids, "fc": [main, fc.get("formal_proof_linked")], "ep": ep.get("state")})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True); ap.add_argument("--ledger", required=True)
    ap.add_argument("--date", default=datetime.date.today().isoformat()); ap.add_argument("--write", action="store_true")
    ap.add_argument("--summary")
    a = ap.parse_args()
    name = os.path.basename(os.path.abspath(a.repo))
    m = re.search(r"erdos(\d+)$", name); number = m.group(1) if m else None
    cpath = os.path.join(a.repo, "claim.yaml")
    if os.path.exists(cpath):
        claim = yaml.safe_load(open(cpath, encoding="utf-8"))
        arts = [x for c in claim.get("claims", []) for x in c.get("artifacts", []) if x.get("kind") == "repo" and x.get("repo")]
        repos = sorted({x["repo"] for x in arts})
        lean_repos = sorted({x["repo"] for x in arts if x.get("lean_files") or x.get("lakefile")})
    else:  # older missions pin their repositories only in the ledger's sources
        refs = " ".join(s.get("ref", "") for s in json.load(open(os.path.join(a.repo, a.ledger)))["missions"][0].get("sources", []))
        repos = sorted({r.rstrip(".") for r in re.findall(r"github\.com/([\w.-]+/[\w.-]+)", refs) if not r.lower().startswith(("nervous-machine/", "google-deepmind/formal-conjectures"))})
        lean_repos = []  # unknown here, so the build gap is never resolved automatically

    entries = palomar(number, repos)
    pal = {"status": "registered" if entries else "none found", "entries": entries,
           "searched": f"data.palomar-registry.org by problem number and pinned repositories, {a.date}"}
    if entries:  # first entry's fields at top level, read by board.py
        e0 = entries[0]
        pal.update({"id": e0["id"], "url": e0["url"], "repository": e0["repository"], "claimant": ", ".join(e0["authors"])})
    reading = {"palomar": pal, "formal_conjectures": formal_conjectures(number), "erdosproblems": erdosproblems(number)}

    path = os.path.join(a.repo, a.ledger); L = json.load(open(path))
    last = {}
    for c in L["cycles"]:
        x = (c.get("outcome", {}).get("numbers") or {}).get("external")
        if c.get("kind") == "replay" and x: last = x
    changed = key(last) != key(reading)
    known = {c["outcome"]["numbers"].get("palomar_id") for c in L["cycles"] if c.get("kind") == "rerun" and c.get("by") == "Palomar registry"} \
        | {c.get("provenance", {}).get("source", "").split("entry ")[-1].split(" ")[0] for c in L["cycles"] if c.get("by") == "Palomar registry"}
    new_entries = [e for e in entries if e["id"] not in known]

    lines, flags = [], []
    fc, ep = reading["formal_conjectures"], reading["erdosproblems"]
    if changed or new_entries:
        lines.append(f"Change in other registries for {name} on {a.date}.")
        lines.append(f"- Palomar: {len(entries)} matching entr{'y' if len(entries) == 1 else 'ies'}" + "".join(f"\n  - [{e['id']}]({e['url']}) {e['title']} ({e['repository']}){'' if e['pinned_here'] else ' — repository not pinned in this record'}" for e in entries))
        lines.append(f"- DeepMind formal-conjectures: {fc['main_statement']}" + (f", formal proof linked: {fc['formal_proof_linked']}" if fc.get("formal_proof_linked") else ""))
        lines.append(f"- erdosproblems.com: {ep['state']}")
        prev = last or {}
        if prev:
            lines.append(f"- Previously: Palomar {len((prev.get('palomar') or {}).get('entries', [])) or (1 if (prev.get('palomar') or {}).get('id') else 0)} entr(ies), "
                         f"DeepMind {(prev.get('formal_conjectures') or {}).get('main_statement')}, erdosproblems.com {(prev.get('erdosproblems') or {}).get('state')}")
    else:
        lines.append(f"No change in other registries for {name} on {a.date}.")

    if a.write and (changed or new_entries):
        base = {k: L["cycles"][0][k] for k in ("schema_version", "mission_id", "pod", "audience") if k in L["cycles"][0]}
        stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        parts = ["Palomar: " + ("; ".join(f"{', '.join(e['authors']) or 'an author'}'s formalisation registered {str(e['published_at'])[:10]} ({e['id']})" for e in entries) or "no entry found"),
                 "DeepMind formal-conjectures: " + ("not an Erdős problem file" if not number else "no file for this problem" if fc["main_statement"] == "no file" else f"main statement marked {fc['main_statement']}" + (", linking a formal proof" if fc.get("formal_proof_linked") else "")),
                 "erdosproblems.com: " + ("not applicable" if not number else f"status {ep['state']}")]
        L["cycles"].append({**base, "created_by": "DEBRIEF/tools/watch_external.py", "created_at": stamp,
            "provenance": {"source": "public data of the Palomar registry, google-deepmind/formal-conjectures and the erdosproblems.com database"},
            "cycle": f"external-{a.date}", "dated": a.date, "kind": "replay", "by": None,
            "preregistered": {"question": "What do other registries show about this claim today?", "rule": "status read from each registry's public data, pinned by commit or entry id; no new checking", "predictions": [], "commit": None, "before_data": False},
            "outcome": {"verdict": "admitted", "numbers": {"external": reading}},
            "spoken": f"What other registries showed on {a.date}. " + ". ".join(parts) + ". None of these is a named human reading of the statement.",
            "finding_ids": [], "gap_ids": []})
        build_gap = next((g for g in L["gaps"] if re.search(r"has not been built", g.get("title", ""), re.I)), None)
        for e in new_entries:
            cyc = f"palomar-{str(e['published_at'])[:10]}-{e['id'][-6:]}"
            L["cycles"].append({**base, "created_by": "DEBRIEF/tools/watch_external.py", "created_at": stamp,
                "provenance": {"source": f"Palomar registry entry {e['id']} (public data); recorded from public data, not submitted to this repository"},
                "kind": "rerun", "cycle": cyc, "dated": str(e["published_at"])[:10], "by": "Palomar registry",
                "preregistered": {"question": "Does the formalisation prove its stated theorem, checked apart from its author?",
                                  "rule": "Palomar's published policy: Comparator separates statement from proof; the exported proof is replayed through independent kernels; a language model judges the statement",
                                  "predictions": [], "commit": None, "before_data": False, "results": [e["url"]]},
                "outcome": {"verdict": "confirmed", "numbers": {"palomar_id": e["id"], "repository": e["repository"], "commit": e["commit"], "kernels": e.get("kernels", []),
                                                                 "trust_level": e.get("trust_level"), "statement_review": e.get("statement_review"), "human_review": False}},
                "spoken": f"The Palomar registry registered {', '.join(e['authors']) or 'an author'}'s formalisation ({e['repository']}) after replaying its proof through independent kernels; a language model judged the statement. "
                          + ("This repository is pinned in this record. " if e["pinned_here"] else "This repository is not pinned in this record; a maintainer decides whether to pin it. ")
                          + "It is a machine check by a party other than the author, not a human reading of the statement.",
                "finding_ids": [], "gap_ids": [build_gap["gap_id"]] if (build_gap and e["pinned_here"]) else []})
            if not e["pinned_here"]:
                flags.append(f"Palomar entry {e['id']} is for `{e['repository']}`, which this record does not pin. Pin it in claim.yaml and the ledger's sources if it is the claimant's development, and narrow the build gap by hand.")
            elif build_gap:
                build_gap.setdefault("history", []).append({"cycle": cyc, "hypothesis": "a party other than the claimant has machine-checked a pinned development", "before_data": False,
                    "result": f"Palomar replayed {e['repository']} at {str(e['commit'])[:7]} through independent kernels and registered it ({e['id']})"})
        if build_gap and lean_repos:
            checked = {c["outcome"]["numbers"].get("repository", "").lower() for c in L["cycles"] if c.get("by") == "Palomar registry" and c.get("kind") == "rerun"}
            if all(r.lower() in checked for r in lean_repos) and build_gap["status"] in ("proposed", "in_cycle"):
                build_gap["status"] = "resolved_learned"
                build_gap["history"].append({"cycle": f"external-{a.date}", "hypothesis": "every pinned Lean development has an independent machine check", "before_data": False,
                                             "result": "every pinned Lean repository has a Palomar check; DEBRIEF defers to Palomar for machine checks; status -> resolved_learned"})
                lines.append(f"- Build gap {build_gap['gap_id']} resolved: every pinned Lean repository now has a Palomar check.")
        json.dump(L, open(path, "w"), indent=1, ensure_ascii=False); open(path, "a").write("\n")

    if flags:
        lines.append("\nFor a maintainer:\n" + "\n".join(f"- {f}" for f in flags))
    out = "\n".join(lines) + "\n"
    print(out)
    if a.summary:
        open(a.summary, "w").write(out)


if __name__ == "__main__":
    main()
