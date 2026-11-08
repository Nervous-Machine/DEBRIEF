#!/usr/bin/env python3
"""Register or check a pre-registration file.

usage: prereg.py register PREREG.yaml         write PREREG.yaml.sha256 (refuses if a sidecar already exists)
       prereg.py check PREREG.yaml            confirm the file, or its body above the first amendment marker,
                                              still hashes to the registered value
       prereg.py amend PREREG.yaml ID TEXT    append a dated amendment block; never edits the body

The sidecar records the sha256 of the file at registration and the UTC time. Later changes go in an amendment
block after a marker line `# ---- Amendment <ID>, <date>. Written AFTER ... ----`; `check` hashes only what is
above the first marker, so amendments are allowed and body edits are not.
"""
import datetime, hashlib, os, re, sys

MARKER = re.compile(r"^(?:# ---- Amendment|amendments:)", re.M)


def body(text):
    m = MARKER.search(text)
    return text[:m.start()] if m else text


def sha(b):
    return hashlib.sha256(b).hexdigest()


def register(p):
    side = p + ".sha256"
    if resolve(p)[1]:
        sys.exit(f"refusing: {side} exists; a pre-registration is hashed once")
    raw = open(p, "rb").read()
    if MARKER.search(raw.decode("utf-8", "replace")):
        sys.exit("refusing: file already contains an amendment marker; register the body first")
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    open(side, "w").write(f"{sha(raw)}  {os.path.basename(p)}\nregistered_utc: {now}\n")
    print(f"registered {p}: {sha(raw)} at {now}")


def resolve(p):
    """Accept the pre-registration path or its sidecar; return (prereg, sidecar)."""
    if p.endswith(".sha256"):
        stem = p[:-7]
        for cand in (stem, stem + ".yaml", stem + ".yml", stem + ".md"):
            if os.path.exists(cand):
                return cand, p
        sys.exit(f"no pre-registration file for sidecar {p}")
    for side in (p + ".sha256", os.path.splitext(p)[0] + ".sha256"):
        if os.path.exists(side):
            return p, side
    return p, None


def check(p):
    p, side = resolve(p)
    if not side:
        print(f"no sidecar for {p}"); return 1
    recorded = set(re.findall(r"\b[0-9a-f]{64}\b", open(side).read()))
    raw = open(p, "rb").read()
    text = raw.decode("utf-8", "replace")
    b = body(text)
    ok = recorded & {sha(raw), sha(b.encode()), sha(b.rstrip("\n").encode()), sha((b.rstrip("\n") + "\n").encode())}
    print(("unchanged" if ok else "BODY EDITED") + f": {p}")
    return 0 if ok else 1


def amend(p, aid, text):
    today = datetime.date.today().isoformat()
    block = f"\n# ---- Amendment {aid}, {today}. Written AFTER registration. ----\n" + "\n".join("# " + ln for ln in text.splitlines()) + "\n"
    open(p, "a").write(block)
    print(f"appended amendment {aid} to {p}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "register": register(a[1])
    elif len(a) >= 2 and a[0] == "check": sys.exit(check(a[1]))
    elif len(a) >= 4 and a[0] == "amend": amend(a[1], a[2], " ".join(a[3:]))
    else: print(__doc__); sys.exit(2)
