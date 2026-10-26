---
name: learn
description: Turn logged clip decisions into a proposed rules.md change for human approval. Use when the user says /learn, "Regeln verbessern", or after several reviewed clips.
---

# /learn

1. Find last proposal: newest file in `knowledge/proposals/` (its date = cutoff; none → all decisions).
2. Count `knowledge/decisions.jsonl` lines after cutoff. < 3 → say so, stop.
3. Spawn `rules-distiller` with paths: `knowledge/rules.md`, `knowledge/decisions.jsonl` (tell it the cutoff ts), `knowledge/examples/approved/`, `knowledge/examples/rejected/`.
4. Save its output to `knowledge/proposals/rules-<YYYY-MM-DD>.md` (diff + evidence), also if `NO CHANGE` (marks the cutoff).
5. Show the diff to the user. **Apply only on explicit approval**, then edit `knowledge/rules.md` exactly per diff and add `applied: <date>` at the top of the proposal file. Rejected → add `rejected: <date> <reason>`.

Never edit the Legal section of rules.md via /learn.
