#!/usr/bin/env python3
"""Merge contributed cycle files into a ledger.

usage: merge_cycles.py LEDGER.json CYCLES_DIR [--out MERGED.json] [--authors "name1;name2"]

Each YAML file in CYCLES_DIR is one contributed cycle (see templates/cycle-*.yaml). The tool appends cycles not
already in the ledger (matched on `cycle`), fills in the base fields from the mission document, and applies the
semantic-gap rule to any gap a `read` cycle names: two independent `signed` cycles by people who are not authors
of the claim, with no standing `refused` cycle, resolve the gap; one refusal reopens it. An admitted `data` cycle
that names an immovable gap moves it to in_cycle. It writes the merged
ledger to --out (default: in place). Requires PyYAML.
"""
import datetime, glob, json, os, sys

try:
    import yaml
except ImportError:
    sys.exit("merge_cycles.py needs PyYAML (pip install pyyaml)")


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    ledger_path, cdir = argv[0], argv[1]
    out, authors = ledger_path, set()
    i = 2
    while i < len(argv):
        if argv[i] == "--out": out = argv[i + 1]; i += 2
        elif argv[i] == "--authors": authors = {x.strip() for x in argv[i + 1].split(";") if x.strip()}; i += 2
        else: print("unknown argument", argv[i]); return 2
    L = json.load(open(ledger_path))
    m = L["missions"][0]
    base = {"schema_version": "nm-debrief-v1", "mission_id": m["mission_id"], "pod": m["pod"], "created_by": "contributed cycle (merge_cycles.py)",
            "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "provenance": {"source": "contributed cycle file"}, "audience": "briefing"}
    have = {str(c["cycle"]) for c in L["cycles"]}
    added = []
    for f in sorted(glob.glob(os.path.join(cdir, "*.yaml")) + glob.glob(os.path.join(cdir, "*.yml"))):
        c = yaml.safe_load(open(f, encoding="utf-8"))
        if not isinstance(c, dict) or "cycle" not in c:
            print(f"skip {f}: not a cycle"); continue
        if str(c["cycle"]) in have:
            continue
        doc = {**base, "provenance": {"source": f"contributed cycle file {os.path.basename(f)}"}, **c}
        doc.setdefault("finding_ids", []); doc.setdefault("gap_ids", [])
        doc.setdefault("preregistered", {}).setdefault("predictions", [])
        doc["preregistered"].setdefault("question", ""); doc["preregistered"].setdefault("rule", ""); doc["preregistered"].setdefault("before_data", "unknown")
        doc.setdefault("outcome", {}).setdefault("verdict", "mixed")
        doc.setdefault("spoken", "")
        L["cycles"].append(doc); have.add(str(c["cycle"])); added.append(str(c["cycle"]))
    # data rule: an admitted dataset that names an immovable gap moves it to in_cycle (nothing is resolved by arrival)
    gaps = {g["gap_id"]: g for g in L["gaps"]}
    for c in L["cycles"]:
        if c.get("kind") != "data" or c.get("outcome", {}).get("verdict") != "admitted" or str(c["cycle"]) not in added:
            continue
        for gid in c.get("gap_ids", []):
            g = gaps.get(gid)
            if g and g["status"] == "immovable":
                g.setdefault("history", []).append({"cycle": str(c["cycle"]), "hypothesis": "data rule: an admitted dataset addresses this gap",
                                                   "before_data": True, "result": f"dataset from {c.get('by', '?')} admitted; status immovable -> in_cycle"})
                g["status"] = "in_cycle"
    # semantic-gap rule
    for gid, g in gaps.items():
        reads = [c for c in L["cycles"] if c.get("kind") == "read" and gid in c.get("gap_ids", [])]
        if not reads:
            continue
        signers = {c.get("by") for c in reads if c["outcome"]["verdict"] == "signed" and c.get("by") not in authors and c.get("not_an_author_of_the_claim", True)}
        refusals = [c for c in reads if c["outcome"]["verdict"] == "refused"]
        withdrawn = {c.get("withdraws") for c in L["cycles"] if c.get("withdraws")}
        signers -= withdrawn
        if refusals:
            new = "proposed" if g["status"] in ("resolved_learned",) else g["status"]
        elif len(signers) >= 2:
            new = "resolved_learned"
        else:
            new = "in_cycle" if g["status"] == "proposed" else g["status"]
        if new != g["status"]:
            g.setdefault("history", []).append({"cycle": added[-1] if added else "merge", "hypothesis": "semantic-gap rule: two independent signatures and no refusal",
                                               "before_data": True, "result": f"{len(signers)} independent signature(s), {len(refusals)} refusal(s); status {g['status']} -> {new}"})
            g["status"] = new
    json.dump(L, open(out, "w"), indent=1, ensure_ascii=False)
    print(f"merged {len(added)} cycle(s) {added} into {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
