# Definitional trace — <claim>

A reading guide for a human semantic review. It traces each formal statement to its definitions, gives a
rendering in ordinary mathematical language, and points at where the paper makes the same statement. The
renderings are the tracer's; a signature has to be a person's. This document changes no standing.

Rules followed (also in prereg): R1 every formal statement is quoted verbatim with file and line. R2 every
rendering is marked as the tracer's. R3 every discrepancy is recorded, harmless or not. R4 the truth of axioms is
not judged here.

## 0. Conventions that change meaning

| convention | in the formal library | consequence for reading |
|---|---|---|
| <e.g. division by zero> | <definition and location> | <what a reader must keep in mind> |

## A. Goals

### A1. <formal name> ↔ <paper location>

Formal text (<file>:<lines>):
```
<verbatim>
```
Depends on: <definitions, each with file and line>
Rendering (tracer's): <plain statement>
Paper: <theorem/corollary number and its statement>
Discrepancies: <none | list>

## B. Axioms or inputs taken on trust

### B1. <formal name> ↔ <paper location>
(same structure; include a term-by-term table if the statement has several parts)

## C. Numerical inputs

C1 shape; C2 data table and how it was compared mechanically; C3 meaning chain.

## D. Discrepancies found

| id | where | what | harmless? |
|---|---|---|---|

## E. Sign-off checklist

A reader signs or refuses each item by name. Submit through the "Semantic read" issue form or a `read` cycle.

- [ ] A1 The rendering of <goal 1> is what the paper states.
- [ ] A2 ...
- [ ] B1 The rendering of <axiom 1> is the classical statement the paper cites.
- [ ] B2 ...
- [ ] D The discrepancies listed are the only ones I found, or I have added mine above.
