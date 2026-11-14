#!/usr/bin/env python3
"""The contribution board. usage: contributors.py OUT.md REPO_URL=LEDGER.json [REPO_URL=LEDGER.json ...]

One entry per person named in a cycle's `by` field, across every mission given, newest first. Each cycle is
described in plain words: what kind of work it was, the first sentences of the ledger's own spoken account, and
which open question it bore on. Nothing is counted or ranked. Replay cycles (the public record retold) have no
contributor and are left out.
"""
import datetime, json, re, sys

KIND = {"rerun": "Reran the checks independently", "read": "Read the formal statements against the paper", "data": "Supplied data",
        "claim": "Opened a claim for checking", "learning": "Ran a test written down before looking at the data",
        "trace": "Wrote a reading guide for the formal statements", "correction": "Corrected the record"}


def when(d):
    d = str(d or "")
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", d)
    if not m:
        return d
    t = datetime.date(int(m[1]), int(m[2]), int(m[3]))
    return f"{t.day} {t.strftime('%B %Y')}"


def first_sentences(text, n=2):
    parts = re.split(r"(?<=[.!?])\s+", " ".join((text or "").split()))
    return " ".join(parts[:n])


def entries(url, path):
    L = json.load(open(path)); m = L["missions"][0]
    gaps = {g["gap_id"]: g for g in L["gaps"]}
    out = []
    for c in L["cycles"]:
        by = c.get("by")
        if not by:
            continue
        bore = []
        for gid in c.get("gap_ids", []):
            g = gaps.get(gid)
            if not g or g.get("audience", "briefing") != "briefing":
                continue
            t = g["title"].rstrip(".")
            bore.append(f"Closed: {t}." if str(g["status"]).startswith("resolved") else f"Bears on the open question: {t}" + ("" if t.endswith("?") else "."))
        src = (c.get("provenance") or {}).get("source", "")
        f = re.search(r"contributed cycle file (\S+)", src)
        link = f"{url}/blob/main/cycles/{f[1]}" if f else f"{url}/blob/main/SCORECARD.md"
        key = re.match(r"\d{4}-\d{2}-\d{2}", str(c.get("dated", "")))
        out.append({"by": by, "github": c.get("github"), "sort": key[0] if key else "", "date": when(c.get("dated")), "mission": m["title"], "url": url,
                    "kind": KIND.get(c.get("kind"), "Contributed a cycle"), "what": first_sentences(c.get("spoken", ""), 1), "bore": bore, "link": link})
    return out


def main(argv):
    out, pairs = argv[0], [a.split("=", 1) for a in argv[1:]]
    rows = [e for url, path in pairs for e in entries(url, path)]
    people = {}
    for e in rows:
        people.setdefault(e["by"], []).append(e)
    text = ["# Who has contributed", "",
            "Every entry here is a piece of checking work that is now part of a public record: someone ran a computation again on",
            "their own machine, read a proof's formal statements against the paper, supplied data, or ran a test they had written",
            "down before looking. Each entry links to the record it belongs to. Names appear exactly as the contributor asked.", "",
            "Newest first. Generated from the mission ledgers by `tools/contributors.py`; to be added, contribute a cycle (see `CONTRIBUTING.md`).", ""]
    for by, es in sorted(people.items(), key=lambda kv: max(e["sort"] for e in kv[1]), reverse=True):
        handles = sorted({e["github"] for e in es if e.get("github")})
        text += [f"## {by}" + (f" (GitHub: {', '.join('@' + h for h in handles)})" if handles else ""), ""]
        for e in sorted(es, key=lambda e: e["sort"], reverse=True):
            text += [f"**{e['date']}** · {e['kind']} · [{e['mission']}]({e['url']})  ", f"{e['what']}" + "".join(" " + b for b in e["bore"]) + f" [Record]({e['link']})", ""]
    open(out, "w").write("\n".join(text)); print(f"wrote {out}: {len(people)} contributors, {len(rows)} cycles")


if __name__ == "__main__":
    main(sys.argv[1:])
