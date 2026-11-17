#!/usr/bin/env python3
"""List Erdős claims that other registries show but DEBRIEF does not track, for a maintainer to triage.

usage: watch_candidates.py --tracked 306,550,... [--days 7] [--out OUT.md]

Two sources, both public:
  - Palomar registry entries whose title names an Erdős problem, published in the last N days;
  - commits in google-deepmind/formal-conjectures in the last N days that touch FormalConjectures/ErdosProblems/
    and mention solved, resolution or a formal proof.
Problems already tracked are left out. Writes nothing (an empty OUT) when there is nothing new. Nothing is opened
as a record; a maintainer chooses.
"""
import argparse, datetime, json, os, re, sys, urllib.parse, urllib.request


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "DEBRIEF-watch (github.com/Nervous-Machine/DEBRIEF)"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and url.startswith("https://api.github.com/"):
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def palomar(since):
    out, cursor = [], None
    for _ in range(40):
        d = get("https://data.palomar-registry.org/api/v1/results?q=erdos" + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else ""))
        for e in d.get("entries", []):
            m = re.search(r"Erd[őo]s(?:\s+[Pp]roblem)?\s*#?\s*(\d{1,4})\b", e.get("title", ""))
            if m and str(e.get("published_at", ""))[:10] >= since:
                out.append((m.group(1), e))
        n = d.get("next")
        cursor = n if isinstance(n, str) else (n or {}).get("cursor") if isinstance(n, dict) else None
        if not cursor:
            break
    return out


def deepmind(since):
    out = []
    commits = get(f"https://api.github.com/repos/google-deepmind/formal-conjectures/commits?path=FormalConjectures/ErdosProblems&since={since}T00:00:00Z&per_page=100")
    for c in commits:
        msg = c["commit"]["message"].split("\n")[0]
        if re.search(r"solved|resolution|resolve|formal proof|formal_proof", msg, re.I):
            for n in re.findall(r"(?:Erd[őo]s(?:\s+[Pp]roblem)?|ErdosProblems/|[Pp]roblem)\s*#?\s*(\d{1,4})\b", msg):
                out.append((n, c["html_url"], msg, c["commit"]["author"]["date"][:10]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracked", default=""); ap.add_argument("--days", type=int, default=7); ap.add_argument("--out")
    a = ap.parse_args()
    tracked = {t for t in a.tracked.split(",") if t}
    since = (datetime.date.today() - datetime.timedelta(days=a.days)).isoformat()
    lines = []
    pal = [(n, e) for n, e in palomar(since) if n not in tracked]
    if pal:
        lines.append(f"**Palomar registry**: Erdős entries registered since {since}, not tracked here\n")
        for n, e in sorted(pal, key=lambda x: int(x[0])):
            lines.append(f"- #{n}: [{e['title']}](https://palomar-registry.org/entry.html?id={e['id']}) ({(e.get('source') or {}).get('repository', '')}; {str(e.get('published_at'))[:10]})")
    dm = [x for x in deepmind(since) if x[0] not in tracked]
    if dm:
        lines.append(f"\n**DeepMind formal-conjectures**: commits since {since} that mark or link a solution, not tracked here\n")
        seen = set()
        for n, url, msg, d in sorted(dm, key=lambda x: int(x[0])):
            if (n, url) in seen: continue
            seen.add((n, url)); lines.append(f"- #{n}: [{msg}]({url}) ({d})")
    if lines:
        lines.append("\nTo open a record for one of these, write `claims/<name>.yaml` from `templates/claim.yaml` and run `tools/new_mission.py`. "
                     "Nothing here is opened automatically.")
    out = "\n".join(lines) + ("\n" if lines else "")
    print(out or f"nothing new since {since}")
    if a.out:
        open(a.out, "w").write(out)


if __name__ == "__main__":
    main()
