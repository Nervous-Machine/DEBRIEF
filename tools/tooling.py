#!/usr/bin/env python3
"""Write a claim's tooling disclosure into its ledger. usage: tooling.py REPO_DIR [--check]

Reads REPO_DIR/tooling.yaml, one entry per claim:

  claims:
    - by: "Eric Li"                      # matches the claim's author line
      models: [gpt-5-5-pro]              # ids from DEBRIEF/tools/models.yaml; a name not in the registry is kept as text
      tier: subscription-pro             # none | free | subscription | subscription-pro | api | internal | mixed | unknown
      basis: "stated by the claimant: GPT-5.5 Pro, a ChatGPT Pro model"   # stated | inferred, and from what
      work: {from: "2026-06-01", to: "2026-07-17"}   # dates the work ran, if stated; else only `to` = date submitted
      duration: "not stated"
      compute: "not stated"

and writes missions[0].tooling in the ledger: the same fields plus, per model, its public release date and whether it
was public when the work began (`public_at_the_time`: yes, no, partly, unknown). The claimant's statement is recorded
as stated; anything inferred says so in `basis`. Nothing here is a standing. With --check, prints without writing."""
import datetime, glob, json, os, sys

try:
    import yaml
except ImportError:
    sys.exit("tooling.py needs PyYAML")

HERE = os.path.dirname(os.path.abspath(__file__))
TIERS = ["none", "free", "subscription", "subscription-pro", "api", "internal", "mixed", "unknown"]
MODELS = {m["id"]: m for m in yaml.safe_load(open(os.path.join(HERE, "models.yaml"), encoding="utf-8"))["models"]}


def d(s):
    return datetime.date.fromisoformat(str(s)[:10]) if s else None


def resolve(mid, work):
    m = MODELS.get(mid)
    if not m:
        return {"model": mid, "public_release": None, "public_at_the_time": "unknown", "note": "not in the model registry"}
    rel = d(m.get("public_release"))
    out = {"model": m["name"], "id": mid, "vendor": m.get("vendor"), "public_release": m.get("public_release"), "tiers_at_release": m.get("tiers_at_release", [])}
    start, end = d((work or {}).get("from")), d((work or {}).get("to"))
    if rel is None or (start is None and end is None):
        out["public_at_the_time"] = "unknown"
    elif start and rel <= start:
        out["public_at_the_time"] = "yes"
    elif start and end and start < rel <= end:
        out["public_at_the_time"] = "partly"; out["note"] = f"public from {rel.isoformat()}, after the work began"
    elif start and rel > (end or start):
        out["public_at_the_time"] = "no"; out["note"] = f"public from {rel.isoformat()}, after the work"
    elif end and rel <= end:
        out["public_at_the_time"] = "yes" if (rel <= end) else "no"
        if (end - rel).days < 14: out["note"] = f"public {(end - rel).days} days before the date submitted; the work's start is not stated"
    else:
        out["public_at_the_time"] = "no"; out["note"] = f"public from {rel.isoformat()}, after the date submitted"
    return out


def main(repo, check=False):
    repo = os.path.normpath(repo)
    cfg = os.path.join(repo, "tooling.yaml")
    if not os.path.exists(cfg):
        print(f"{os.path.basename(repo)}: no tooling.yaml"); return
    T = yaml.safe_load(open(cfg, encoding="utf-8")) or {}
    out = []
    for c in T.get("claims", []):
        tier = c.get("tier", "unknown")
        if tier not in TIERS:
            sys.exit(f"{repo}: tier {tier!r} is not one of {TIERS}")
        out.append({"by": c.get("by"), "tier": tier, "basis": c.get("basis", ""), "models": [resolve(m, c.get("work")) for m in (c.get("models") or [])],
                    "work": c.get("work"), "duration": c.get("duration", "not stated"), "compute": c.get("compute", "not stated")})
    path = glob.glob(os.path.join(repo, "ledger", "*.json"))[0]
    L = json.load(open(path))
    L["missions"][0]["tooling"] = out
    summary = "; ".join(f"{t['by']}: {t['tier']} (" + ", ".join(m["model"] + (f", public {m['public_at_the_time']}" if m["public_at_the_time"] != "unknown" else "") for m in t["models"]) + ")" for t in out)
    if check:
        print(f"{os.path.basename(repo)}: {summary}"); return
    json.dump(L, open(path, "w"), indent=1, ensure_ascii=False); open(path, "a").write("\n")
    print(f"{os.path.basename(repo)}: tooling written: {summary}")


if __name__ == "__main__":
    main(sys.argv[1], "--check" in sys.argv[2:])
