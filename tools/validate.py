#!/usr/bin/env python3
"""DEBRIEF ledger validator, protocol 0.1.0.

usage: validate.py LEDGER.json [--repo DIR] [--schema PATH] [--strict]

Checks the ledger's shape (against schema/ledger.schema.json when the `jsonschema` package is available, with a
built-in fallback otherwise) and the protocol rules in schema/SCHEMA.md §6. With --repo, rules 7 and 8 are checked
against the mission repository's files and git history. Warnings become errors with --strict. Exit 1 on any error.
Standard library only, apart from the optional jsonschema.
"""
import hashlib, json, os, re, subprocess, sys

VERDICTS = {"admitted", "not_admitted", "confirmed", "refuted", "unavailable", "corrected", "withdrawn", "classified", "learned", "mixed", "signed", "refused"}
KINDS = {"learned", "retracted", "ruled_out", "discovery", "correction"}
STANDING = {"accepted", "certified", "refuted"}
GAP_STATUS = {"proposed", "in_cycle", "resolved_learned", "resolved_refuted", "immovable"}
OPEN_GAP = {"proposed", "in_cycle", "immovable"}
CLOSE_KIND = {"data_release", "measurement", "research", "decision", "rerun", "read"}
AUDIENCE = {"briefing", "internal", None}
RESERVED = re.compile(r"\b(?:is|was|are|were|been|be|now|fully|formally|independently)\s+(?:verified|proved|proven)\b|\bis\s+(?:now\s+)?a\s+(?:proved\s+|proven\s+)?theorem\b", re.I)
NEGATION = re.compile(r"\b(?:not|no|never|nobody|none|nothing|neither|nor|hasn't|isn't|wasn't|cannot|can't|until|unless|before|whether|if|would|only if|do not|does not|did not|don't|doesn't)\b|n't\b", re.I)


ID_KEY = {"findings": "finding_id", "gaps": "gap_id", "anomalies": "anomaly_id", "background": "term", "cycles": "cycle", "missions": "mission_id", "sessions": "session_id"}


def ident(d):
    for k in ("finding_id", "anomaly_id", "gap_id", "term", "session_id"):
        if k in d:
            return d[k]
    return ("cycle " + str(d["cycle"])) if "cycle" in d else d.get("mission_id")


def sidecar(repo, p):
    """The registered hash file: <p>.sha256, or <stem>.sha256 beside it."""
    for cand in (p + ".sha256", os.path.splitext(p)[0] + ".sha256"):
        if os.path.exists(os.path.join(repo, cand)):
            return os.path.join(repo, cand)
    return None


def shape(L, schema_path, errs):
    try:
        import jsonschema  # type: ignore
    except ImportError:
        jsonschema = None
    if jsonschema and schema_path and os.path.exists(schema_path):
        v = jsonschema.Draft202012Validator(json.load(open(schema_path)))
        for e in sorted(v.iter_errors(L), key=lambda e: list(e.path)):
            errs.append("shape: " + "/".join(str(p) for p in e.path) + ": " + e.message[:160])
        return "jsonschema"
    need = {"missions": ["title", "record_quality", "short_version", "implications", "certainty_statement"],
            "cycles": ["cycle", "dated", "preregistered", "outcome", "spoken"],
            "findings": ["finding_id", "kind", "spoken", "evidence", "standing", "certainty"],
            "gaps": ["gap_id", "title", "status", "spoken", "closes_with", "ask", "priority"],
            "anomalies": ["anomaly_id", "when", "spoken", "status", "urgency", "from_trusted_node"],
            "background": ["term", "spoken", "source"]}
    for col in ("missions", "cycles", "findings", "gaps", "anomalies", "background", "sessions"):
        if col not in L:
            errs.append(f"shape: missing collection {col}")
    for col, docs in L.items():
        for d in docs:
            for k in ("mission_id", "pod", "schema_version", "created_by", "created_at", "provenance") + tuple(need.get(col, [])):
                if k not in d:
                    errs.append(f"shape: {col}: {ident(d)} missing {k}")
    return "builtin"


def texts(L):
    """Every string a reader or listener will meet, with a locator."""
    for col, docs in L.items():
        for d in docs:
            for k, v in d.items():
                if isinstance(v, str) and k in ("spoken", "title", "basis", "record_note", "what", "result", "hypothesis"):
                    yield f"{col}/{ident(d)}/{k}", v
                elif isinstance(v, dict):
                    for k2, v2 in v.items():
                        if isinstance(v2, str) and k2 in ("spoken", "basis", "note"):
                            yield f"{col}/{ident(d)}/{k}.{k2}", v2
                        elif isinstance(v2, list):
                            for i, item in enumerate(v2):
                                if isinstance(item, dict) and isinstance(item.get("spoken"), str):
                                    yield f"{col}/{ident(d)}/{k}.{k2}[{i}]", item["spoken"]
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        if isinstance(item, str):
                            yield f"{col}/{ident(d)}/{k}[{i}]", item
                        elif isinstance(item, dict):
                            for k2 in ("spoken", "result", "hypothesis", "what"):
                                if isinstance(item.get(k2), str):
                                    yield f"{col}/{ident(d)}/{k}[{i}].{k2}", item[k2]


def reserved_words(L, errs):
    m = L["missions"][0]
    if m.get("claim_rule_met") is True:
        return
    for loc, s in texts(L):
        for hit in RESERVED.finditer(s):
            before = s[max(0, hit.start() - 90):hit.start()]
            sentence_start = max(before.rfind(". "), before.rfind("; "), before.rfind(": "), -1) + 1
            if NEGATION.search(before[sentence_start:]):
                continue
            errs.append(f"rule 6: reserved words at {loc}: '...{s[max(0, hit.start()-40):hit.end()+20]}...'")


def rules(L, errs, warns):
    m = L["missions"][0]
    fids = {f["finding_id"] for f in L["findings"]}
    gids = {g["gap_id"] for g in L["gaps"]}
    record_unavailable = m.get("record_quality") == "reconstructed"
    for c in L["cycles"]:
        if c["outcome"]["verdict"] not in VERDICTS:
            errs.append(f"cycle {c['cycle']}: unknown verdict {c['outcome']['verdict']}")
        errs += [f"cycle {c['cycle']}: unknown finding {x}" for x in c.get("finding_ids", []) if x not in fids]
        errs += [f"cycle {c['cycle']}: unknown gap {x}" for x in c.get("gap_ids", []) if x not in gids]
        if c.get("kind") in ("rerun", "read", "claim", "data") and not c.get("by"):
            errs.append(f"cycle {c['cycle']}: contribution cycle without `by`")
        if c["outcome"]["verdict"] in ("signed", "refused") and c.get("kind") != "read":
            errs.append(f"cycle {c['cycle']}: verdict {c['outcome']['verdict']} only on a read cycle")
    for f in L["findings"]:
        if f["kind"] not in KINDS:
            errs.append(f"{f['finding_id']}: unknown kind")
        if f.get("audience") not in AUDIENCE:
            errs.append(f"{f['finding_id']}: audience")
        st = f["standing"].get("status")
        if st not in STANDING:
            errs.append(f"{f['finding_id']}: unknown standing {st}")
        if st == "certified" and f["certainty"].get("earned") is not True:
            errs.append(f"{f['finding_id']}: rule 2: certified without earned certainty")
        if st in STANDING and not f["standing"].get("basis"):
            errs.append(f"{f['finding_id']}: rule 2: standing without a basis")
        if not f["evidence"].get("cycles") and not record_unavailable:
            errs.append(f"{f['finding_id']}: rule 1: no cycles and the record is not marked reconstructed")
    for g in L["gaps"]:
        if g["status"] not in GAP_STATUS:
            errs.append(f"{g['gap_id']}: unknown status")
        if g.get("audience") not in AUDIENCE:
            errs.append(f"{g['gap_id']}: audience")
        if any(c.get("kind") not in CLOSE_KIND for c in g["closes_with"]):
            errs.append(f"{g['gap_id']}: closes_with kind")
        if g["status"] == "immovable" and not any(c.get("external") for c in g["closes_with"]):
            errs.append(f"{g['gap_id']}: rule 3: immovable without an external dependency")
        if g["status"] in OPEN_GAP and (not g.get("expected_signal") or not g.get("resolution_by")):
            warns.append(f"{g['gap_id']}: rule 9: open gap without expected_signal and resolution_by")
    for a in L["anomalies"]:
        if a["urgency"] == "immediate" and a["from_trusted_node"] is not True:
            errs.append(f"{a['anomaly_id']}: rule 4: immediate alert without a trusted node")
        if a.get("gap_id") and a["gap_id"] not in gids:
            errs.append(f"{a['anomaly_id']}: unknown gap {a['gap_id']}")
    for col in ("findings", "gaps", "anomalies"):
        ids = [d.get(ID_KEY[col]) for d in L[col]]
        for dup in {x for x in ids if ids.count(x) > 1}:
            errs.append(f"{col}: duplicate id {dup}")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=False).stdout.strip()


def first_commit_time(repo, path):
    out = git(repo, "log", "--diff-filter=A", "--follow", "--format=%ct", "--", path)
    times = [int(t) for t in out.split() if t.isdigit()]
    return min(times) if times else None


def prereg_rules(L, repo, errs, warns):
    """Rules 7 and 8, against the mission repository."""
    seen = set()
    for c in L["cycles"]:
        pre = c.get("preregistered", {})
        p = pre.get("commit")
        if not p:
            continue
        if not os.path.exists(os.path.join(repo, p)):
            if "/" in p or p.endswith((".yaml", ".yml", ".md")):
                warns.append(f"cycle {c['cycle']}: rule 7: pre-registration path {p} is not in the repository (use a repository-relative path)")
            continue
        results = [r for r in pre.get("results", []) if os.path.exists(os.path.join(repo, r))]
        t_pre = first_commit_time(repo, p)
        if t_pre is None:
            warns.append(f"cycle {c['cycle']}: rule 7: {p} is not in git history (uncommitted)")
        for r in results:
            t_res = first_commit_time(repo, r)
            if t_pre is not None and t_res is not None and t_res < t_pre:
                errs.append(f"cycle {c['cycle']}: rule 7: results {r} were committed before pre-registration {p}")
        if p in seen:
            continue
        seen.add(p)
        side = sidecar(repo, p)
        if not side:
            warns.append(f"cycle {c['cycle']}: rule 8: {p} has no .sha256 sidecar")
            continue
        recorded = set(re.findall(r"\b[0-9a-f]{64}\b", open(side).read()))
        raw = open(os.path.join(repo, p), "rb").read()
        whole = hashlib.sha256(raw).hexdigest()
        text = raw.decode("utf-8", "replace")
        mk = re.search(r"^(?:# ---- Amendment|amendments:)", text, re.M)
        body = text[:mk.start()] if mk else text
        candidates = {whole, hashlib.sha256(body.encode()).hexdigest(), hashlib.sha256(body.rstrip("\n").encode()).hexdigest(),
                      hashlib.sha256((body.rstrip("\n") + "\n").encode()).hexdigest()}
        if not (recorded & candidates):
            errs.append(f"cycle {c['cycle']}: rule 8: {p} no longer hashes to its registered value (body above the amendment marker was edited, or the sidecar is stale)")


def standing_line(L):
    fs = [f for f in L["findings"] if f.get("audience", "briefing") == "briefing"]
    n = {k: sum(f["standing"]["status"] == k for f in fs) for k in ("certified", "accepted", "refuted")}
    n_open = sum(g["status"] in OPEN_GAP for g in L["gaps"] if g.get("audience", "briefing") == "briefing")
    return f"Certified {n['certified']}. Accepted {n['accepted']}. Refuted {n['refuted']}. Open gaps {n_open}."


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    path, repo, schema_path, strict = argv[0], None, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schema", "ledger.schema.json"), False
    i = 1
    while i < len(argv):
        if argv[i] == "--repo": repo = argv[i + 1]; i += 2
        elif argv[i] == "--schema": schema_path = argv[i + 1]; i += 2
        elif argv[i] == "--strict": strict = True; i += 1
        else: print("unknown argument", argv[i]); return 2
    L = json.load(open(path))
    errs, warns = [], []
    how = shape(L, schema_path, errs)
    if not errs or how == "jsonschema":
        try:
            rules(L, errs, warns)
            reserved_words(L, errs)
            if repo:
                prereg_rules(L, repo, errs, warns)
        except (KeyError, TypeError) as e:
            errs.append(f"rules could not run on a malformed document: {e!r}")
    m = L["missions"][0]
    print(f"{m.get('mission_id')}: {len(L['cycles'])} cycles, {len(L['findings'])} findings, {len(L['gaps'])} gaps, {len(L['anomalies'])} anomalies; shape checked by {how}")
    print("standing line:", standing_line(L))
    for w in warns: print("warning:", w)
    for e in errs: print("error:", e)
    bad = errs or (strict and warns)
    print("INVALID" if bad else "valid")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
