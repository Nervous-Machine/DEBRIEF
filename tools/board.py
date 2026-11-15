#!/usr/bin/env python3
"""The claims board. usage: board.py OUTDIR REPO_URL=LEDGER.json [REPO_URL=LEDGER.json ...]

Reads every audit mission (a claim under checking) and writes OUTDIR/board.json and OUTDIR/index.html: a map strip
(area of mathematics × stage toward the claim rule) and one table of claims ordered by how close each is to its rule,
with who has contributed and what each needs next. Stage is read off the ledger mechanically; the words are the
protocol's. Nothing is ranked by person. The page's own words live in tools/board_copy.yaml.

Stages (0-4): registered only; checks rerun by someone; reading guide written; read independently (a signed `read`
cycle by a non-author); claim rule met.
"""
import datetime, html, json, os, re, sys

try:
    import yaml
except ImportError:
    sys.exit("board.py needs PyYAML (pip install pyyaml)")

COPY = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "board_copy.yaml"), encoding="utf-8"))

OPEN_GAP = {"proposed", "in_cycle", "immovable"}
STAGES = ["Registered", "Checks rerun", "Reading guide written", "Read independently", "Claim rule met"]
STAGE_NEXT = ["an independent rerun of whatever is machine-checkable", "a reading guide that traces each formal statement to its definitions",
              "two independent readers to sign the semantic read", "the remaining open gaps, usually a referee report", "nothing; the rule is met"]
MAINTAINER = re.compile(r"^nervous machine", re.I)


def when(d):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(d or ""))
    if not m:
        return str(d or "")
    t = datetime.date(int(m[1]), int(m[2]), int(m[3]))
    return f"{t.day} {t.strftime('%b %Y')}"


def claim(url, path):
    L = json.load(open(path)); m = L["missions"][0]
    if m.get("kind") != "audit":
        return None
    cyc = [c for c in L["cycles"] if c.get("kind") != "replay" and c.get("by")]
    kinds = {c.get("kind") for c in cyc}
    signed = any(c.get("kind") == "read" and c.get("outcome", {}).get("verdict") == "signed" and c.get("not_an_author_of_the_claim", True) for c in cyc)
    stage = 4 if m.get("claim_rule_met") else 3 if signed else 2 if "trace" in kinds else 1 if "rerun" in kinds else 0
    fs = [f for f in L["findings"] if f.get("audience", "briefing") == "briefing"]
    n = {k: sum(f["standing"]["status"] == k for f in fs) for k in ("certified", "accepted", "refuted")}
    gaps = sorted([g for g in L["gaps"] if g.get("audience", "briefing") == "briefing" and g["status"] in OPEN_GAP], key=lambda g: g["priority"])
    seen = []
    for c in sorted(cyc, key=lambda c: str(c.get("dated", ""))):
        if c["by"] not in seen: seen.append(c["by"])
    people = seen
    outside = [p for p in people if not MAINTAINER.match(p)]
    dates = sorted(re.match(r"\d{4}-\d{2}-\d{2}", str(c.get("dated", ""))).group(0) for c in L["cycles"] if re.match(r"\d{4}-\d{2}-\d{2}", str(c.get("dated", ""))))
    first_ask = gaps[0] if gaps else None
    name = url.rstrip("/").split("/")[-1]
    return {"repo": name, "url": url, "label": m.get("label") or name, "title": m["title"], "area": m.get("area") or "Unclassified", "rests_on": m.get("rests_on") or "",
            "stage": stage, "stage_name": STAGES[stage], "needs_next": STAGE_NEXT[stage], "certified": n["certified"], "accepted": n["accepted"], "refuted": n["refuted"],
            "open_gaps": len(gaps), "first_ask": (first_ask["title"] if first_ask else ""), "first_ask_what": (first_ask["closes_with"][0]["what"] if first_ask and first_ask.get("closes_with") else ""),
            "people": people, "outside": outside, "cycles": len(cyc), "last": dates[-1] if dates else "", "last_text": when(dates[-1]) if dates else "none yet"}


def page(claims, generated):
    e = html.escape
    T = {k: v for k, v in COPY.items() if v not in (None, "")}  # a deleted or blank line in board_copy.yaml drops the element
    def opt(key, before, after, escape=False):
        return (before + (e(T[key]) if escape else str(T[key])) + after) if key in T else ""
    areas = sorted({c["area"] for c in claims})
    by_cell = {}
    for c in claims:
        by_cell.setdefault((c["area"], c["stage"]), []).append(c)
    rows = []
    for a in areas:
        cells = []
        for s in range(5):
            chips = "".join(f'<a class="chip {"solid" if c["outside"] else "dashed"}" href="{e(c["url"])}" title="{e(c["title"])}">{e(c["label"])}</a>' for c in by_cell.get((a, s), []))
            cells.append(f'<td class="cell s{s}">{chips or "<span class=empty>·</span>"}</td>')
        rows.append(f'<tr><th scope="row">{e(a)}</th>{"".join(cells)}</tr>')
    maprows = "\n".join(rows) if rows else '<tr><td colspan="6" class="empty">No claims registered yet.</td></tr>'
    closest = sorted(claims, key=lambda c: (-c["stage"], c["open_gaps"], c["last"]), reverse=False)
    closest = sorted(closest, key=lambda c: (-c["stage"], c["open_gaps"]))
    def row(c):
        checked = f'{c["certified"]} certified, {c["accepted"]} accepted' + (f', {c["refuted"]} refuted' if c["refuted"] else "")
        short = lambda p: p.split(" (")[0]
        first = c["outside"][0] if c["outside"] else (c["people"][0] if c["people"] else "")
        who = (f'<span class="who-outside">{e(short(first))}</span>' if c["outside"] else e(short(first))) if first else e(T.get("no_contributions", ""))
        others = len(c["people"]) - (1 if first else 0)
        # with an outside contributor, link the rest of the names; otherwise invite the first independent contribution
        who += (f'<div class="sub"><a href="https://github.com/Nervous-Machine/DEBRIEF/blob/main/CONTRIBUTORS.md">{e(T.get("and_more", "and {n} more").format(n=others))}</a></div>' if c["outside"] and others
                else f'<div class="sub"><a href="{e(c["url"])}/blob/main/ASKS.md">{e(T.get("be_first", "be the first"))}</a></div>')
        return (f'<tr><td class="lab"><a href="{e(c["url"])}">{e(c["label"])}</a><div class="sub">{e(c["title"])}</div><div class="sub dim">Rests on {e(c["rests_on"])}.</div></td>'
                f'<td><span class="stage s{c["stage"]}">{e(c["stage_name"])}</span><div class="sub">{e(checked)} · {c["open_gaps"]} open</div></td>'
                f'<td>{e(c["first_ask"] or c["needs_next"])}<div class="sub">{e(c["first_ask_what"])}</div><div class="sub"><a href="{e(c["url"])}/blob/main/ASKS.md">{e(T.get("what_would_close", "What would close it"))}</a></div></td>'
                f'<td>{who}<div class="sub">last cycle {e(c["last_text"])}</div></td></tr>')
    closest_rows = "\n".join(row(c) for c in closest) or '<tr><td colspan="4" class="empty">Nothing yet.</td></tr>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(T.get('title', 'Claims Board'))}</title>
{opt('meta_description', '<meta name="description" content="', '">', True)}
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--bg:#0a0a0f;--card:#12121a;--border:#2a2a3a;--text:#e0e0e0;--muted:#888;--dim:#666;--cyan:#00d4ff;--purple:#7b2ff7;--green:#00d464;--yellow:#ffd700}}
:root:not([data-theme="dark"]) {{}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);line-height:1.55;-webkit-font-smoothing:antialiased}}
a{{color:var(--cyan);text-decoration:none}}a:hover{{text-decoration:underline}}
.container{{max-width:1100px;margin:0 auto;padding:0 16px}}
header{{padding:28px 0 16px;border-bottom:1px solid var(--border)}}
header .brand{{font-size:1.4rem;font-weight:700;background:linear-gradient(135deg,#00d4ff,#7b2ff7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:.5px}}
header .by{{font-size:.8rem;color:var(--muted)}}
.hero{{padding:40px 0 28px}}.hero h2{{font-size:2rem;line-height:1.15;font-weight:700;letter-spacing:-.5px;max-width:860px;margin-bottom:14px}}
.hero .lede{{font-size:1.08rem;color:#c0c0c0;max-width:760px}}
section.block{{padding:34px 0;border-top:1px solid var(--border)}}
.eyebrow{{font-size:.72rem;letter-spacing:2px;text-transform:uppercase;color:var(--purple);margin-bottom:8px}}
h3{{font-size:1.35rem;margin-bottom:8px}}.lede2{{color:var(--muted);max-width:760px;margin-bottom:18px}}
.table-scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:top;text-align:left}}
thead th{{font-size:.72rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);font-weight:600}}
td.lab a{{font-weight:600;color:var(--text)}}.sub{{font-size:.8rem;color:var(--muted);margin-top:3px}}.dim{{color:var(--dim)}}
table.map th[scope=row]{{white-space:nowrap;color:#cfd6de;font-weight:500}}
table.map td.cell{{min-width:140px;background:rgba(255,255,255,.015)}}
.chip{{display:inline-block;margin:2px 4px 2px 0;padding:5px 9px;border-radius:5px;font-size:.72rem;color:#cfd6de;background:rgba(0,212,255,.05)}}
.chip.dashed{{border:1.5px dashed rgba(255,215,0,.55);color:var(--yellow)}}.chip.solid{{border:1px solid rgba(0,212,100,.6);color:var(--green);background:rgba(0,212,100,.08)}}
.chip:hover{{text-decoration:none;transform:scale(1.05)}}.empty{{color:var(--dim)}}
.stage{{display:inline-block;padding:3px 9px;border-radius:999px;font-size:.72rem;letter-spacing:.3px;border:1px solid var(--border);color:#cfd6de;white-space:nowrap}}
.stage.s0{{border-color:rgba(255,255,255,.2)}}.stage.s1{{border-color:rgba(0,212,255,.5);color:var(--cyan)}}.stage.s2{{border-color:rgba(123,47,247,.6);color:#b58cff}}
.stage.s3{{border-color:rgba(0,212,100,.6);color:var(--green)}}.stage.s4{{background:rgba(0,212,100,.15);border-color:var(--green);color:var(--green)}}
.legend{{display:flex;flex-wrap:wrap;gap:10px 18px;font-size:.8rem;color:var(--muted);margin-top:14px;align-items:center}}
.legend .chip{{margin:0}}
.who-outside{{color:var(--green)}}
footer{{padding:30px 0 50px;border-top:1px solid var(--border);font-size:.85rem;color:var(--muted)}}
footer p{{margin-bottom:6px}}
</style>
</head>
<body>
<header><div class="container">{opt('brand', '<div class="brand">', '</div>', True)}{('<div class="by">' + e(T['byline'].format(generated=generated)) + '</div>') if 'byline' in T else ''}</div></header>
{('<section class="hero"><div class="container">' + opt('hero_heading', '<h2>', '</h2>') + opt('hero_lede', '<p class="lede">', '</p>') + '</div></section>') if 'hero_heading' in T or 'hero_lede' in T else ''}
<section class="block" id="map"><div class="container">
{opt('map_eyebrow', '<div class="eyebrow">', '</div>')}{opt('map_heading', '<h3>', '</h3>')}{opt('map_lede', '<p class="lede2">', '</p>')}
<div class="table-scroll"><table class="map"><thead><tr><th>area</th>{"".join(f"<th>{e(s)}</th>" for s in STAGES)}</tr></thead><tbody>
{maprows}
</tbody></table></div>
{('<div class="legend">' + opt('legend_dashed', '<span class="chip dashed">', '</span>', True) + opt('legend_solid', '<span class="chip solid">', '</span>', True) + '</div>') if 'legend_dashed' in T or 'legend_solid' in T else ''}
</div></section>
<section class="block" id="closest"><div class="container">
{opt('claims_eyebrow', '<div class="eyebrow">', '</div>')}{opt('claims_heading', '<h3>', '</h3>')}{opt('claims_lede', '<p class="lede2">', '</p>')}
<div class="table-scroll"><table><thead><tr><th>{e(T.get('col_claim', ''))}</th><th>{e(T.get('col_stage', ''))}</th><th>{e(T.get('col_needs', ''))}</th><th>{e(T.get('col_contributors', ''))}</th></tr></thead><tbody>
{closest_rows}
</tbody></table></div>
</div></section>
{('<footer><div class="container">' + opt('footer_1', '<p>', '</p>') + opt('footer_2', '<p>', '</p>') + '</div></footer>') if 'footer_1' in T or 'footer_2' in T else ''}
</body></html>
"""


def main(argv):
    out, pairs = argv[0], [a.split("=", 1) for a in argv[1:]]
    claims = [c for c in (claim(u, p) for u, p in pairs) if c]
    gen = datetime.date.today().isoformat()
    import os; os.makedirs(out, exist_ok=True)
    json.dump({"generated": gen, "stages": STAGES, "claims": claims}, open(os.path.join(out, "board.json"), "w"), indent=1, ensure_ascii=False)
    open(os.path.join(out, "index.html"), "w").write(page(claims, gen))
    print(f"wrote {out}/index.html and board.json: {len(claims)} claims; stages " + ", ".join(f"{c['label']}={c['stage']}" for c in claims))


if __name__ == "__main__":
    main(sys.argv[1:])
