# Mamba vs Transformer — Run Notes (2026-05-12)

End-to-end run of `scholar-deep-research` v0.16.4 on a `comparative_analysis` archetype to (a) validate 0.16.4 fixes in real flow, (b) explore CS / arXiv source mix vs the GLP-1 biomedical baseline.

## Outcome

Cited, lint-clean comparative_analysis report:
- 1005 papers in state · 25 selected · 10 deep / 15 skim · 3 deep-full reads
- 5 themes · 2 tensions · 5 self-critique findings + resolutions
- 3 distinct anchors used = 3 defined = 0 unknown
- Skill version: 0.16.4

Report: `reports/mamba-vs-transformer-long-context_20260512.md` (lint OK).
Bibliography: `reports/mamba-vs-transformer-long-context_20260512.bib` (247 lines).
Evidence: `evidence/{mamba,jamba,xlstm}.json` (3 full deep reads).

## 0.16.4 features validated in this run

1. **`_s2_citations.py` null-data guard (bugfix)** — not exercised; S2 backend was hit but returned 429 (no API key) rather than `{"data": null}`. Guard is defensive coverage.
2. **G2 verbose saturation detail (feature)** — load-bearing. The `arxiv=SAT(...) | openalex=FAIL(...) | crossref=FAIL(...)` per-source inline diagnosis let me identify *which axis* was blocking *which source* without a separate `saturation` call. Saved 5+ round-trips during Phase 1 tuning.
3. **`negligible_hits` guard (feature)** — not exercised here (all queries returned ≥10 hits). Defensive coverage.

## Friction findings (second confirmation)

### F1. Saturation papers-axis too tight for hot ML topics

Repeated friction from the GLP-1 run. After 9 rounds × 3 sources (5–9 rounds per source) and 768 papers, author/venue/max-citation axes all converged but papers-axis stayed 70–100% on broad keyword reformulations.

**Tuning needed:** `SCHOLAR_SATURATION_NEW_PCT=80` (default 50), `SCHOLAR_SATURATION_MAX_CITATIONS=500` (default 100).

**Mechanism:** ML literature is broad and citation-rich; each query reformulation surfaces a fresh slice (papers-axis high), while authors + venues converge cleanly (3/4 axes sat). The current gate ANDs all 4 axes — too strict for fast-moving broad fields.

**Suggested fix:** soft-saturation rule — "≥3 of 4 axes sat for ≥N rounds → SAT". Or: per-archetype default thresholds (comparative on a hot topic vs systematic_review on a niche topic should have different defaults).

**Second-time-this-bites status:** CONFIRMED systemic. Worth implementing the soft-saturation rule before the v0.17 cut.

### F2. Ranker is keyword-only — promotes off-topic Mamba derivatives

5 of 10 deep-tier papers were vision-domain Mamba applications (VMamba, Cobra, FusionMamba, IGroupSS-Mamba, Visual Mamba survey). Ranker has no semantic discrimination between "long-context LM" and "image classification with Mamba blocks".

**Workaround used:** mark all 5 as `evidence_unavailable: out_of_scope_vision_domain` (the documented escape hatch). G4 accepts them; they appear in the audit trail but contribute no claims.

**Suggested fix:** Phase 2 could surface a "domain-cluster" signal (cluster on venue / abstract keywords) and let the host LLM either accept or filter by cluster. The 0.13.x relevance work already moved toward this; would benefit from another pass for cross-domain "famous architecture" topics.

### F3. `rank_papers.py` doesn't take `--archetype`

When I tried `python scripts/rank_papers.py --archetype comparative_analysis ...` (intuitive guess for archetype-specific weights), it errored with `unrecognized arguments`. The script only takes `--alpha/beta/gamma/delta` weights and infers archetype from state.

**Status:** documentation friction, not a bug. The state has archetype set, so the script does pick it up. But the CLI surface is misleading — agents will try the obvious flag first.

**Suggested fix:** add `--archetype` as an explicit no-op flag with help text "archetype is read from state; included for self-documentation".

### F4. DBLP SSL handshake failures

Both Phase 1 DBLP queries failed with `ConnectTimeout` / `UNEXPECTED_EOF`. Skill correctly classified as `upstream_error`, retryable, and excluded DBLP from saturation calculation. Sources_breadth gate still passed at 3/3 (arxiv + openalex + crossref) without DBLP.

**Status:** transient upstream issue, not a skill bug. The graceful degradation worked exactly as designed.

### F5. S2 citation chase rate-limited

All 4 seeds returned 429 on the Semantic Scholar citation backend. Skill correctly fell back to OpenAlex-only chase (155 new papers added).

**Status:** expected without `S2_API_KEY` set. Documented friction; user-fixable.

## How this run informs the next iteration

| Friction | Severity | Action |
|----------|----------|--------|
| F1 — saturation papers-axis | High (2nd confirmation) | Implement soft-saturation rule in v0.17 |
| F2 — ranker keyword-only on cross-domain topics | Medium | Add domain-cluster surfacing in Phase 2 selection (post-0.17) |
| F3 — `--archetype` no-op missing | Low | Add as documentation flag (trivial) |
| F4 — DBLP upstream flake | Low (env) | None — graceful degradation works |
| F5 — S2 rate-limit | Low (env) | None — user delegates auth |

## Notable observations

- **arXiv-heavy run = much better PDF access.** All 3 deep-tier reads got OA PDFs (cf. GLP-1 where 5/5 deep-tier reads hit paywall and used `evidence_unavailable`). arXiv preprints + OpenAlex citation chase is a much smoother path for CS than biomedical for synthesis.
- **Citation chase: OpenAlex backend added 155 papers from 4 seeds.** Healthy ratio. S2 backend would have been pure redundancy given OpenAlex coverage.
- **End-to-end runtime:** ~25 minutes including 18 search queries + 1 citation chase + 3 PDF extracts + report drafting + lint. Saturation tuning iteration was the longest phase (≈10 min).
