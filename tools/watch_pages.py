#!/usr/bin/env python3
"""Watch the public pages a mission names and record what changed.

usage: watch_pages.py --repo DIR --ledger LEDGER.json [--date YYYY-MM-DD] [--write] [--summary OUT.md]

DIR/watch.yaml lists the pages:

  pages:
    - name: Clay Mathematics Institute            # who says it
      url: https://www.claymath.org/millennium/riemann-hypothesis/
      status: 'Riemann Hypothesis\\s+(Unsolved|Solved)'   # optional regex over the page text; group 1 is the status word
      role: problem authority                     # optional, for the record
    - name: Andrew Sutherland (MIT), verification page
      url: https://math.mit.edu/~drew/grh/
      status: 'Page last updated ([0-9-]+ [0-9:]+ UTC)'
    - name: Lean and Mathlib communities, joint statement
      url: https://leanprover-community.github.io/blog/posts/riemann-hypothesis/
      status_fixed: certify the statement and the proof (RH only)   # the status word when the page is present

Each page is fetched, reduced to text and the text hashed (markup carries per-request tokens); the status word is read where a pattern is given. The reading is
compared with the latest snapshot in the ledger (a `replay` cycle whose outcome.numbers.external.pages holds it).
Nothing is written unless a page's hash or status changed, or a page is new. With --write, a change appends one
`replay` cycle `pages-<date>` holding the new reading (no new checking; not a contribution) and appends the hashes to
DIR/source/external.sha256. Standing never changes here; the board (tools/board.py) shows the status words under
"elsewhere". Exit code 0 on success; the summary's first line says whether anything changed."""
import argparse, datetime, hashlib, html, json, os, re, sys, urllib.request

try:
    import yaml
except ImportError:
    sys.exit("watch_pages.py needs PyYAML (pip install pyyaml)")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "DEBRIEF-watch (github.com/Nervous-Machine/DEBRIEF)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def text_of(raw):
    t = raw.decode("utf-8", errors="replace")
    t = re.sub(r"<(script|style).*?</\1>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def read(page, stamp):
    out = {"name": page["name"], "url": page["url"], "read": stamp}
    if page.get("role"): out["role"] = page["role"]
    try:
        raw = fetch(page["url"])
    except Exception as ex:  # a page that cannot be read is recorded as such, never guessed
        out.update({"status": "", "error": f"{type(ex).__name__}: {ex}"[:200]}); return out
    text = text_of(raw)  # the hash is of the page's text, not its bytes: pages carry per-request tokens in their markup
    out.update({"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "bytes": len(raw), "hash_of": "text"})
    if page.get("status"):
        m = re.search(page["status"], text, re.I)
        out["status"] = m.group(1).strip() if m else "status pattern not found"
    elif page.get("status_fixed"):
        out["status"] = page["status_fixed"]
    else:
        out["status"] = ""
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True); ap.add_argument("--ledger", required=True)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--write", action="store_true"); ap.add_argument("--summary")
    a = ap.parse_args()
    cfg = os.path.join(a.repo, "watch.yaml")
    if not os.path.exists(cfg):
        print(f"no watch.yaml in {a.repo}; nothing to watch"); return
    pages = (yaml.safe_load(open(cfg, encoding="utf-8")) or {}).get("pages") or []
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    reading = [read(p, stamp) for p in pages]

    path = os.path.join(a.repo, a.ledger); L = json.load(open(path))
    last = {}
    for c in L["cycles"]:
        x = (c.get("outcome", {}).get("numbers") or {}).get("external") or {}
        if c.get("kind") == "replay" and x.get("pages"):
            last = {p["url"]: p for p in x["pages"]}
    changes = []
    for p in reading:
        q = last.get(p["url"])
        if p.get("error"):
            p["changed"] = False; changes.append(f"- {p['name']}: could not be read ({p['error']})"); continue
        if q is None:
            p["changed"] = True; changes.append(f"- {p['name']}: first reading; status {p['status'] or '(hash only)'}; sha256 {p['sha256'][:8]}…")
        elif q.get("sha256") != p["sha256"] or q.get("status", "") != p["status"]:
            p["changed"] = True
            changes.append(f"- {p['name']}: status {q.get('status') or '(hash only)'} -> {p['status'] or '(hash only)'}; sha256 {str(q.get('sha256', ''))[:8]}… -> {p['sha256'][:8]}…")
        else:
            p["changed"] = False
    changed = any(p.get("changed") for p in reading)
    name = os.path.basename(os.path.abspath(a.repo))
    lines = [(f"Change in watched pages for {name} on {a.date}." if changed else f"No change in watched pages for {name} on {a.date}.")] + changes

    if a.write and changed:
        base = {k: L["cycles"][0][k] for k in ("schema_version", "mission_id", "pod", "audience") if k in L["cycles"][0]}
        cid = f"pages-{a.date}"
        if any(str(c.get("cycle")) == cid for c in L["cycles"]):
            cid += "-" + stamp[11:16].replace(":", "")
        said = "; ".join(f"{p['name']}: {p['status']}" for p in reading if p.get("status"))
        L["cycles"].append({**base, "created_by": "DEBRIEF/tools/watch_pages.py", "created_at": stamp,
            "provenance": {"source": "public pages named in watch.yaml, fetched and hashed; status words read by the patterns there; hashes in source/external.sha256"},
            "cycle": cid, "dated": a.date, "kind": "replay", "by": None,
            "preregistered": {"question": "What do the pages this record watches say today?", "rule": "each page fetched, hashed and its status word read by a fixed pattern; no new checking", "predictions": [], "commit": None, "before_data": False},
            "outcome": {"verdict": "admitted", "numbers": {"external": {"pages": reading}}},
            "spoken": f"What the watched pages said on {a.date}. " + (said + ". " if said else "") + "A page's status word is what its keeper says; it gives nothing here a standing.",
            "finding_ids": [], "gap_ids": []})
        json.dump(L, open(path, "w"), indent=1, ensure_ascii=False); open(path, "a").write("\n")
        os.makedirs(os.path.join(a.repo, "source"), exist_ok=True)
        with open(os.path.join(a.repo, "source", "external.sha256"), "a", encoding="utf-8") as f:
            f.write(f"# watched pages read {stamp} (tools/watch_pages.py)\n")
            for p in reading:
                if p.get("sha256"):
                    f.write(f"{p['sha256']}  {p['url']}  ({p['name']}" + (f"; status: {p['status']}" if p.get("status") else "") + ")\n")
        lines.append(f"- recorded as replay cycle {cid}")
    out = "\n".join(lines) + "\n"
    print(out)
    if a.summary:
        open(a.summary, "w").write(out)


if __name__ == "__main__":
    main()
