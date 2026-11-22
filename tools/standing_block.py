#!/usr/bin/env python3
"""Write the generated standing block into a mission README. usage: standing_block.py README.md BOARD.json REPO_NAME

Reads the claim's row from the board data (tools/board.py) and replaces the block between the markers
`<!-- standing:begin -->` and `<!-- standing:end -->` in the README. If the README has no markers yet, the first
paragraph that begins with `**Standing` is replaced by the block. Everything in the block comes from the ledger;
to change it, change the ledger and regenerate. Exit code 0 whether or not the file changed; prints which."""
import json, re, sys

BEGIN = "<!-- standing:begin -->"
END = "<!-- standing:end -->"


def block(c):
    k = c["checks"]
    rel = c.get("url", "")
    machine = ", ".join(k["rerun"]) if k["rerun"] else ("no Lean to check" if c.get("no_lean") else "nobody yet")
    if k["reports"]:
        machine += "; reported elsewhere, not filed here: " + ", ".join(f"[{r['who']}]({r['url']})" for r in k["reports"])
    human = (f"{k['signed']} signed" + (f", {k['refused']} refused" if k["refused"] else "")) if k["reads"] else "nobody yet"
    human += "; [reading guide](trace/DEFINITIONAL-TRACE.md)" if k["trace"] else "; no reading guide yet"
    if k["notes"]:
        human += f"; {k['notes']} reasoning note" + ("s" if k["notes"] != 1 else "")
    regs = " · ".join(f"[{r['name']}]({r['url']}): {r['status']}" for r in k["registries"]) or "—"
    def rel(r):
        if r.get("links"):
            return r["relation"] + ": " + ", ".join(f"[{l}]({u})" for l, u in r["links"])
        return f"[{r['label']}]({r['url']}): {r['relation']}"
    related = " · ".join(rel(r) for r in c.get("related_display", c.get("related", []))) or "—"
    standing = " · ".join(f"{c[w]} {w}" for w in ("certified", "accepted", "refuted") if c[w]) or "nothing has standing yet"
    lines = [BEGIN,
             f"**Standing, {c['last_text']}.** Stage: {c['stage_name']}. Needs next: {c['first_ask'] or c['needs_next']} ([what would close it](ASKS.md)).",
             "",
             "| certified | accepted | refuted | open gaps | cycles filed | last cycle |",
             "|---|---|---|---|---|---|",
             f"| {c['certified']} | {c['accepted']} | {c['refuted']} | {c['open_gaps']} | {c['cycles']} | {c['last_text']} |",
             "",
             "| | |",
             "|---|---|",
             f"| checked by machine | {machine} |",
             f"| read by a person | {human} |",
             f"| elsewhere | {regs} |",
             f"| related | {related} |",
             "",
             f"Rendered from `ledger/` at regeneration; the full record is `SCORECARD.md`, what is owed is `ASKS.md`. Standing words: {standing}.",
             END]
    return "\n".join(lines)


def main(readme, board, repo):
    rows = {c["repo"]: c for c in json.load(open(board))["claims"]}
    if repo not in rows:
        print(f"{repo}: not an audit claim on the board; README untouched"); return
    new = block(rows[repo])
    s = open(readme, encoding="utf-8").read()
    if BEGIN in s and END in s:
        out = s[:s.index(BEGIN)] + new + s[s.index(END) + len(END):]
    else:
        m = re.search(r"^\*\*Standing.*?(?=\n\s*\n|\Z)", s, re.S | re.M)
        if not m:
            print(f"{repo}: no standing paragraph found; README untouched"); return
        out = s[:m.start()] + new + s[m.end():]
    if out != s:
        open(readme, "w", encoding="utf-8").write(out); print(f"{repo}: README standing block updated")
    else:
        print(f"{repo}: README unchanged")


if __name__ == "__main__":
    main(*sys.argv[1:4])
