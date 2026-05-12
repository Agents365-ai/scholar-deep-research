# Run notes — GLP-1 / non-diabetic obesity (systematic_review)

**Date:** 2026-05-12
**Skill version:** 0.16.3
**Archetype:** `systematic_review`
**Strict-saturation env:** initial run used `SCHOLAR_SATURATION_NEW_PCT=20`

## Final artifacts

| File | What |
|---|---|
| `reports/what-is-the-efficacy-and-safety_20260512.md` | 201-line systematic-review report, 12 inline citations, 30-paper bibliography |
| `reports/what-is-the-efficacy-and-safety_20260512.bib` | BibTeX export, 309 lines, 30 entries |
| `research_state.json` | Full audit trail (1.8 MB): 833 papers, 18 queries × 4 sources, 165 citation-chase additions, 5 deep-tier evidence stubs, 4 themes, 2 tensions, 9 critique findings + resolves |
| `evidence/*.json` | 5 deep-tier evidence records (one per deep-tier paper) |

## Phase-by-phase numbers

| Phase | Output | Time |
|---|---|---|
| 0 — Scope | PICO + archetype + state init | ~5 s |
| 1 — Discovery | 5 rounds × 4 sources × ~50 hits → 668 unique papers | ~90 s |
| 2 — Triage | Top 30 selected, triaged into 5 deep / 25 skim | ~10 s |
| 3 — Deep read | 5 deep-tier records (all `evidence_unavailable: oa_paywall`); 25 skim auto-filled | ~30 s |
| 4 — Citation chasing | 3 seeds × OpenAlex (S2 hit bug, see below) → +165 papers, 833 total | ~60 s |
| 5 — Synthesis | 4 themes + 2 tensions | ~5 s |
| 6 — Self-critique | 9 findings + 9 resolutions + appendix | ~15 s |
| 7 — Render report | Scaffold + agent prose + lint pass + bibtex | ~30 s |

## Friction findings (the point of this run)

### Bugs caught and fixed

1. **`_s2_citations.py:114` TypeError on `data: null`** — *fixed in this session.*
   S2 occasionally returns `{"data": null, ...}` (especially after a 429). `body.get("data", [])` returns `None` (not the default `[]`) when the key is present but null. The result is `out.extend(None)` → `TypeError`, exception bubbles up, script dies with **no JSON envelope on stdout** — direct P1 violation.
   Fix: `body.get("data") or []` (one-line change).

### Documentation gaps

2. **Strict 20% saturation effectively unreachable on hot biomedical topics.**
   After 5 rounds and 695 papers, paper-axis novelty stayed at 70–98% across sources (Crossref highest, 98%). Author/venue axes saturated cleanly (PubMed authors=22% < threshold 25%) but `max_new_citations` kept pulling >100-citation papers (OpenAlex r5: 988). The strict gate could not fire.
   This is correct conservative behavior, but the SKILL.md `systematic_review` archetype guidance currently recommends `SCHOLAR_SATURATION_NEW_PCT=20` without a sibling caveat ("hot fields may require relaxing to 30–40 + bumping `MAX_CITATIONS`"). **Add the caveat.**

3. **`saturation` subcommand displays the env-var threshold but `advance` evaluates the gate.**
   When the user runs `python scripts/research_state.py saturation` without env vars, output shows `threshold=50.0%` even if they intend to advance with `SCHOLAR_SATURATION_NEW_PCT=20`. Two sources of truth. **Either auto-read the env in `saturation`, or print "effective threshold under SCHOLAR_SATURATION_NEW_PCT" hint.**

4. **`saturation_overall` gate detail is terse.**
   `detail` field reads `per_source=['pubmed', 'openalex', 'crossref', 'biorxiv']` — just the keys. Doesn't say *why* each failed. Agent has to call `saturation` separately to get a useful diagnosis. **Inline per-source mini-breakdown (`pubmed: new=70%/30%, max_cit=118/100`).** _Source: `scripts/_gates.py:106`._

5. **`rank_papers.py` has no `--archetype` flag.**
   Agents reading SKILL.md (which mentions archetype-aware weighting) may try `rank_papers.py --archetype systematic_review`. Argparse errors silently. Either accept-and-ignore the flag with deprecation hint, or document that archetype affects skim/render but not rank weights.

6. **`extract_pdf.py` paper-fetch latency for not-found cases.**
   Annals 2025: 16,191 ms before returning `not_found`. paper-fetch tries Unpaywall → S2 → sci-hub sequentially. Each timeout dominates. **Out-of-scope for this skill** but worth noting as a paper-fetch optimization candidate.

7. **bioRxiv on hot biomedical topics returns negligible volume but blocks the gate.**
   bioRxiv had 2 hits last round (r3) — effectively exhausted, but `new_pct=72%` from a 1/2 fraction blocks `saturation_overall`. **Saturation logic should treat `hits_last_round < N_min` (e.g. 5) as "negligible / exhausted" rather than computing a percent on a tiny denominator.**

### Working as designed (showcase wins)

- **G4 `evidence_unavailable:` failure-mode escape hatch.** All 5 deep-tier papers were paywalled; paper-fetch returned `not_found` from all 3 sources. The depth='shallow' + method='evidence_unavailable:' contract let the gate advance with full honesty — exactly as phase3_deep_read.md describes.
- **Citation chase with `--source openalex`** added 165 papers on 3 seeds with one minor SSL error logged to stderr, envelope-clean.
- **Render scaffold** populated themes + tensions + bibliography correctly with no editing required; agent only filled the prose slots.
- **Lint pass** caught 0 typos and 0 undefined-in-text anchors across the report.

## Optimization candidates (prioritized)

| # | Change | Cost | Value |
|---|---|---|---|
| 1 | Fix `_s2_citations.py:114` `data: null` guard | ✅ done | high (any S2 hit could crash citation chase) |
| 2 | Inline per-source breakdown in `saturation_overall` gate detail | ~10 LoC | high (saves agent a round-trip) |
| 3 | `saturation` subcommand reads env-var threshold | ~5 LoC | medium |
| 4 | Add `negligible_volume` guard (`hits_last_round < 5` → saturated) | ~10 LoC + 1 test | medium |
| 5 | SKILL.md systematic_review archetype: add "relax for hot fields" caveat | doc only | medium |
| 6 | `rank_papers.py --archetype` accepts-and-ignores with hint | ~5 LoC | low |

## Decisions on next steps

- **Items 1, 2, 3** look like the right batch for the next code change (one bug fix + two UX wins, all in `_s2_citations.py` / `_gates.py` / `research_state.py`).
- **Items 4, 5** are independent and small; bundle with whichever release ships next.
- **Item 6** is the lowest priority — friction is mild and a doc note in SKILL.md suffices.
