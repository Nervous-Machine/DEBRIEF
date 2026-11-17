# Reading guide: <claim>

The one question a machine cannot settle: does the formal statement say what the problem asks? This guide sets the
problem as posed beside each formal statement and lists every difference between them, harmless or not, then asks a
reader to sign or refuse a short checklist. It does not trace every Lean symbol to Mathlib: where the statement is
registered with Palomar, its rendered page explains each term on hover. It changes no standing.

Written after a pre-registration (`prereg_review.yaml`, hashed and committed first). The differences are the
reviewer's reading, marked with who or what reviewed. Leave your own reasoning with the **Reasoning note** form.

## A. The problem as posed

Source: <url>, as of <date>. Verbatim:

> <statement>

## B. The formal statements

### B1. <name> (<repo> <path> at <commit>)

```lean
<verbatim statement>
```

Rendered with term explanations: <Palomar entry link, if registered; otherwise "not registered with Palomar">

## C. Differences

| id | where | the problem says | the formal statement says | kind | could it change the meaning? | why |
|---|---|---|---|---|---|---|
| D1 | | | | convention / encoding / strength / boundary / type / wording / scope | yes / no / uncertain | |

A difference marked **yes** or **uncertain** is opened as an anomaly in the ledger and sent upstream (to the
statement's maintainers) as an issue.

## D. What this review did not check

- <e.g. the original 1967 source; the proof; definitions behind a name the statement imports>

## Sign-off checklist

Sign or refuse each item with the **Semantic read** form. Items marked optional may be left out.

- [ ] A1: <the formal statement's hypotheses are the problem's hypotheses (D…)>
- [ ] A2: <its conclusion is the problem's conclusion (D…)>
- [ ] A3: <each difference above is harmless as stated, or I name the one that is not>
- [ ] A0 (optional, needs the original source): <the problem page's wording is the original problem>
