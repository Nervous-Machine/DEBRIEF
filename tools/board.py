#!/usr/bin/env python3
"""The claims board. usage: board.py OUTDIR REPO_URL=LEDGER.json [REPO_URL=LEDGER.json ...]

Reads every audit mission (a claim under checking) and writes OUTDIR/board.json and OUTDIR/index.html: three numbers
(claims on the board, claims with an independent machine check, claims with a signed human read), a count per stage,
and one table of claims ordered by most recent activity. Five columns: the claim, its stage and what it needs next,
who checked it by machine, who read it as a person, and what other registries say. Stage is read off the ledger
mechanically; the words are the protocol's. Nothing is ranked by person. The page's own words live in
tools/board_copy.yaml; relations between claims that only a person can see live in tools/relations.yaml.

Stages (0-4): registered only; checks rerun by someone; reading guide written; read independently (a signed `read`
cycle by a non-author); claim rule met.
"""
import datetime, html, json, os, re, sys

try:
    import yaml
except ImportError:
    sys.exit("board.py needs PyYAML (pip install pyyaml)")

HERE = os.path.dirname(os.path.abspath(__file__))
APPS = yaml.safe_load(open(os.path.join(HERE, "applications.yaml"), encoding="utf-8")) or {}
COPY = yaml.safe_load(open(os.path.join(HERE, "board_copy.yaml"), encoding="utf-8"))
RELATIONS = (yaml.safe_load(open(os.path.join(HERE, "relations.yaml"), encoding="utf-8")) or {}).get("relations", []) if os.path.exists(os.path.join(HERE, "relations.yaml")) else []

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


def registries(ext):
    """What other registries and authorities say, as one list: name, status word, url. Hash-only watched pages are left out."""
    out = []
    pal, fc, ep = ext.get("palomar") or {}, ext.get("formal_conjectures") or {}, ext.get("erdosproblems") or {}
    if pal.get("status") == "registered":
        out.append({"name": "Palomar registry", "status": "registered", "url": pal.get("url") or "https://palomar-registry.org"})
    s = str(fc.get("main_statement") or "")
    if s and s != "not applicable":
        out.append({"name": "DeepMind formal-conjectures", "status": s + (", proof linked" if fc.get("formal_proof_linked") else ""), "url": fc.get("url") or "https://github.com/google-deepmind/formal-conjectures", "dim": s == "no file"})
    st = str(ep.get("state") or "")
    if st and st != "not applicable":
        out.append({"name": "erdosproblems.com", "status": st, "url": ep.get("url") or "https://www.erdosproblems.com/"})
    for p in ext.get("pages") or []:  # tools/watch_pages.py snapshots; hash-only pages (no status word) are not shown
        if p.get("status") and p.get("url"):
            out.append({"name": str(p.get("name") or p["url"]), "status": str(p["status"]), "url": p["url"], "read": p.get("read", "")})
    return out


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
    dates = sorted(d for c in L["cycles"] for d in re.findall(r"\d{4}-\d{2}-\d{2}", str(c.get("dated", ""))))  # a cycle dated "A to B" counts as B
    first_ask = gaps[0] if gaps else None
    name = url.rstrip("/").split("/")[-1]
    ext = {}
    for c in L["cycles"]:  # external snapshots are replay cycles (no new checking); later readings override earlier ones key by key
        x = (c.get("outcome", {}).get("numbers") or {}).get("external")
        if c.get("kind") == "replay" and x:
            ext.update(x); ext["dated"] = c.get("dated")
    reruns = list(dict.fromkeys(c["by"].split(" (")[0] for c in sorted(cyc, key=lambda c: str(c.get("dated", ""))) if c.get("kind") == "rerun"))
    reads = [c for c in cyc if c.get("kind") == "read" and c.get("not_an_author_of_the_claim", True)]
    reports = [r for r in ext.get("reports", []) if r.get("who") and r.get("url")]
    check = {"rerun": reruns, "trace": "trace" in kinds, "reads": len(reads),
             "signed": sum(c.get("outcome", {}).get("verdict") == "signed" for c in reads),
             "refused": sum(c.get("outcome", {}).get("verdict") == "refused" for c in reads),
             "reports": reports, "registries": registries(ext), "external": ext, "application": APPS.get(name, "none"),
             "notes": sum(c.get("kind") == "note" for c in cyc)}
    machine = bool(reruns or reports or (ext.get("palomar") or {}).get("status") == "registered")
    # handles for relations: the problem page and the owners of pinned source repositories
    srcs = m.get("sources") or []
    srcs = srcs if isinstance(srcs, list) else []
    problem = next((s.get("ref", "").split()[0] for s in srcs if s.get("kind") == "problem" and s.get("ref")), "")
    owners = sorted({mo.group(1).lower() for s in srcs if s.get("kind") in ("repo", "repository") for mo in [re.search(r"github\.com/([^/\s]+)/", s.get("ref", ""))] if mo})
    nolean = "no formal deduction" in (m.get("rests_on") or "") or "no fixed file" in (m.get("rests_on") or "")
    return {"repo": name, "url": url, "label": m.get("label") or name, "title": m["title"], "area": m.get("area") or "Unclassified", "rests_on": m.get("rests_on") or "",
            "stage": stage, "stage_name": STAGES[stage], "needs_next": STAGE_NEXT[stage], "certified": n["certified"], "accepted": n["accepted"], "refuted": n["refuted"],
            "open_gaps": len(gaps), "first_ask": (first_ask["title"] if first_ask else ""), "first_ask_what": (first_ask["closes_with"][0]["what"] if first_ask and first_ask.get("closes_with") else ""),
            "people": people, "outside": outside, "checks": check, "machine_checked": machine, "human_signed": check["signed"] > 0, "no_lean": nolean,
            "problem_url": problem, "source_owners": owners, "related": [],
            "cycles": len(cyc), "last": dates[-1] if dates else "", "last_text": when(dates[-1]) if dates else "none yet"}


def relate(claims):
    """Relations between claims: read off the ledgers (same problem page, same claimant's repositories) and from
    tools/relations.yaml (what only a person can see). Each claim gets a list of {repo, label, url, relation, source}."""
    by = {c["repo"]: c for c in claims}
    def add(a, b, rel, source):
        if a is b or any(r["repo"] == b["repo"] and r["relation"] == rel for r in a["related"]):
            return
        a["related"].append({"repo": b["repo"], "label": b["label"], "url": b["url"], "relation": rel, "source": source})
    for a in claims:
        for b in claims:
            if a is b: continue
            if a["problem_url"] and a["problem_url"] == b["problem_url"]:
                add(a, b, "same problem page", "ledger")
            if set(a["source_owners"]) & set(b["source_owners"]):
                add(a, b, "same claimant", "ledger")
    for r in RELATIONS:
        a, b = by.get(r.get("a")), by.get(r.get("b"))
        if not (a and b): continue
        add(a, b, r["relation"], "maintainer")
        add(b, a, r.get("reverse", r["relation"]), "maintainer")
    for c in claims:  # one chip per related claim; the maintainer's words first, then what the ledgers show
        merged = {}
        for r in sorted(c["related"], key=lambda r: (r["source"] != "maintainer", r["label"])):
            m = merged.setdefault(r["repo"], {**r, "relations": []})
            m["relations"].append(r["relation"])
        for m in merged.values():
            m["relation"] = "; ".join(m["relations"])
        c["related"] = sorted(merged.values(), key=lambda r: (r["source"] != "maintainer", r["label"]))
    return claims


def page(claims, generated):
    e = html.escape
    T = {k: v for k, v in COPY.items() if v not in (None, "")}  # a deleted or blank line in board_copy.yaml drops the element
    def opt(key, before, after, escape=False):
        return (before + (e(T[key]) if escape else str(T[key])) + after) if key in T else ""
    dim = lambda s: f'<span class="dim">{s}</span>'
    n_all, n_machine, n_human = len(claims), sum(c["machine_checked"] for c in claims), sum(c["human_signed"] for c in claims)
    counts = [sum(c["stage"] == s for c in claims) for s in range(5)]
    numbers = "".join(f'<div class="num"><div class="n">{v}</div><div class="l">{e(T.get(k, k))}</div></div>'
                      for k, v in (("num_claims", n_all), ("num_machine", n_machine), ("num_human", n_human)))
    stage_line = " ".join(f'<span class="stage s{s}">{e(STAGES[s])} <b>{counts[s]}</b></span>' for s in range(5))
    # most recent activity first; ties by stage (closest to the rule), then fewest open gaps
    closest = sorted(claims, key=lambda c: (str(c["last"]), c["stage"], -c["open_gaps"]), reverse=True)

    def row(c):
        k = c["checks"]
        names = [(f'<span class="who-outside">{e(n)}</span>' if not MAINTAINER.match(n) else e(n)) for n in k["rerun"]]
        reported = [f'<a class="who-outside" href="{e(r["url"])}" title="{e(r.get("what", ""))}">{e(r["who"])}</a>' for r in k["reports"]]
        machine = ", ".join(names) if names else dim("no Lean to check" if c["no_lean"] else "nobody yet")
        if reported:
            machine += '<div class="sub">' + ", ".join(reported) + dim(" " + e(T.get("reported_elsewhere", "reported elsewhere, not filed here"))) + "</div>"
        guide = f'<a href="{e(c["url"])}/blob/main/trace/DEFINITIONAL-TRACE.md">{e(T.get("reading_guide", "reading guide"))}</a>' if k["trace"] else dim(e(T.get("no_reading_guide", "no reading guide")))
        human = (f'<span class="who-outside">{k["signed"]} signed' + (f', {k["refused"]} refused' if k["refused"] else "") + '</span>') if k["reads"] else dim(e(T.get("not_read", "nobody yet")))
        human += f'<div class="sub">{guide}' + (f' · {k["notes"]} note{"s" if k["notes"] != 1 else ""}' if k["notes"] else "") + f' · <a href="{e(c["url"])}/issues/new?template=reasoning-note.yml">{e(T.get("leave_reasoning", "leave your reasoning →"))}</a></div>'
        regs = [f'<div class="reg{" dim" if r.get("dim") else ""}"><a href="{e(r["url"])}">{e(r["name"])}</a>: {e(r["status"])}</div>' for r in k["registries"]]
        elsewhere = "".join(regs) if regs else dim("—")
        chips = "".join(f'<a class="rel" href="{e(r["url"])}" title="{e(r["relation"])}{" (from the ledgers)" if r["source"] == "ledger" else ""}">{e(r["label"])} <span class="dim">{e(r["relation"])}</span></a>' for r in c["related"])
        use = f'<a class="chip-use" href="https://github.com/Nervous-Machine/DEBRIEF/blob/main/APPLICATIONS.md">{e(T.get("use_candidate", "engineering use: candidate"))}</a>' if k["application"] == "candidate" else ""
        standing = " · ".join(f"{c[w]} {w}" for w in ("certified", "accepted", "refuted") if c[w]) or "nothing has standing yet"
        return (f'<tr><td class="lab"><a href="{e(c["url"])}">{e(c["label"])}</a><div class="sub">{e(c["title"])}</div>{("<div class=rels>" + chips + "</div>") if chips else ""}{use}</td>'
                f'<td><span class="stage s{c["stage"]}">{e(c["stage_name"])}</span><div class="sub">{e(standing)} · {c["open_gaps"]} open</div>'
                f'<div class="sub next">{e(T.get("needs", "needs"))} {e(c["first_ask"] or c["needs_next"])} <a href="{e(c["url"])}/blob/main/ASKS.md">{e(T.get("what_would_close", "what would close it →"))}</a></div></td>'
                f'<td>{machine}</td><td>{human}</td><td>{elsewhere}</td></tr>')
    head = "".join(f"<th>{e(T.get(k, ''))}</th>" for k in ("col_claim", "col_stage", "col_machine", "col_human", "col_elsewhere"))
    rows = "\n".join(row(c) for c in closest) or '<tr><td colspan="5" class="empty">Nothing yet.</td></tr>'
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
.hero{{padding:36px 0 24px}}.hero h2{{font-size:2rem;line-height:1.15;font-weight:700;letter-spacing:-.5px;max-width:860px;margin-bottom:14px}}
.hero .lede{{font-size:1.08rem;color:#c0c0c0;max-width:760px;margin-bottom:22px}}
.numbers{{display:flex;flex-wrap:wrap;gap:14px 40px;margin-bottom:18px}}.num .n{{font-size:2.6rem;font-weight:700;line-height:1;letter-spacing:-1px}}.num .l{{font-size:.8rem;color:var(--muted);margin-top:4px;max-width:200px}}
.num:nth-child(2) .n{{color:var(--cyan)}}.num:nth-child(3) .n{{color:var(--green)}}
.stages{{display:flex;flex-wrap:wrap;gap:8px;font-size:.8rem;color:var(--muted)}}.stages .stage b{{color:var(--text);font-weight:600;margin-left:4px}}
section.block{{padding:30px 0;border-top:1px solid var(--border)}}
.eyebrow{{font-size:.72rem;letter-spacing:2px;text-transform:uppercase;color:var(--purple);margin-bottom:8px}}
h3{{font-size:1.35rem;margin-bottom:8px}}.lede2{{color:var(--muted);max-width:760px;margin-bottom:18px}}
.table-scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:top;text-align:left}}
thead th{{font-size:.72rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);font-weight:600}}
td.lab{{min-width:220px}}td.lab a{{font-weight:600;color:var(--text)}}.sub{{font-size:.8rem;color:var(--muted);margin-top:3px}}.dim{{color:var(--dim)}}
.sub.next{{color:#b8b8c0}}.sub.next a{{font-size:.78rem}}
.rels{{margin-top:6px;display:flex;flex-wrap:wrap;gap:4px}}.rel{{display:inline-block;padding:2px 7px;border-radius:4px;font-size:.72rem;border:1px solid var(--border);color:#cfd6de;background:rgba(255,255,255,.02)}}.rel:hover{{text-decoration:none;border-color:var(--cyan)}}
.chip-use{{display:inline-block;margin-top:6px;padding:2px 7px;border-radius:4px;font-size:.72rem;border:1px solid rgba(0,212,100,.5);color:var(--green)}}
.reg{{font-size:.85rem}}.reg.dim,.reg.dim a{{color:var(--dim)}}
.stage{{display:inline-block;padding:3px 9px;border-radius:999px;font-size:.72rem;letter-spacing:.3px;border:1px solid var(--border);color:#cfd6de;white-space:nowrap}}
.stage.s0{{border-color:rgba(255,255,255,.2)}}.stage.s1{{border-color:rgba(0,212,255,.5);color:var(--cyan)}}.stage.s2{{border-color:rgba(123,47,247,.6);color:#b58cff}}
.stage.s3{{border-color:rgba(0,212,100,.6);color:var(--green)}}.stage.s4{{background:rgba(0,212,100,.15);border-color:var(--green);color:var(--green)}}
.who-outside{{color:var(--green)}}
footer{{padding:30px 0 50px;border-top:1px solid var(--border);font-size:.85rem;color:var(--muted)}}
footer p{{margin-bottom:6px}}
</style>
</head>
<body>
<header><div class="container">{opt('brand', '<div class="brand">', '</div>', True)}{('<div class="by">' + e(T['byline'].format(generated=generated)) + '</div>') if 'byline' in T else ''}</div></header>
<section class="hero"><div class="container">{opt('hero_heading', '<h2>', '</h2>')}{opt('hero_lede', '<p class="lede">', '</p>')}
<div class="numbers">{numbers}</div>
<div class="stages">{stage_line}</div>
</div></section>
<section class="block" id="claims"><div class="container">
{opt('claims_eyebrow', '<div class="eyebrow">', '</div>')}{opt('claims_heading', '<h3>', '</h3>')}{opt('claims_lede', '<p class="lede2">', '</p>')}
<div class="table-scroll"><table><thead><tr>{head}</tr></thead><tbody>
{rows}
</tbody></table></div>
</div></section>
{('<footer><div class="container">' + opt('footer_1', '<p>', '</p>') + opt('footer_2', '<p>', '</p>') + '</div></footer>') if 'footer_1' in T or 'footer_2' in T else ''}
</body></html>
"""


def main(argv):
    out, pairs = argv[0], [a.split("=", 1) for a in argv[1:]]
    claims = relate([c for c in (claim(u, p) for u, p in pairs) if c])
    gen = max((c["last"] for c in claims if c["last"]), default=datetime.date.today().isoformat())  # newest ledger date, so an unchanged board regenerates identically
    os.makedirs(out, exist_ok=True)
    json.dump({"generated": gen, "stages": STAGES, "claims": claims}, open(os.path.join(out, "board.json"), "w"), indent=1, ensure_ascii=False)
    open(os.path.join(out, "index.html"), "w").write(page(claims, gen))
    print(f"wrote {out}/index.html and board.json: {len(claims)} claims, {sum(c['machine_checked'] for c in claims)} machine-checked, {sum(c['human_signed'] for c in claims)} human-signed; stages "
          + ", ".join(f"{c['label']}={c['stage']}" for c in claims))


if __name__ == "__main__":
    main(sys.argv[1:])
