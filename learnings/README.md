# Learnings

Engineering learnings about the pipeline: source quirks, tool gotchas, failed approaches, decisions and their reasons. Read before refactoring.

Not for clip taste. What makes a good clip lives in `knowledge/` (rules.md, decisions, examples).

## Files
- [pipeline.md](pipeline.md): all entries, grouped by area.

## Entry format
```
### <short title>  (YYYY-MM-DD, status: verified | unverified | superseded)
- Observed: what happened, with exact error text or numbers.
- Cause: why, if known.
- Action: what we did about it (file:line), or what to do.
```
Add an entry when something surprising happens, a workaround goes in, or an assumption turns out wrong. Do not delete superseded entries. Mark them `superseded` and link the newer entry.
