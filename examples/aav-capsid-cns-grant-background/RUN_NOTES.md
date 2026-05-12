# Run notes — AAV capsid engineering for CNS gene therapy (`grant_background`)

End-to-end Phase 0..7 example run on 2026-05-12, completed against skill version **0.16.5**. Topic chosen as the third showcase archetype (`grant_background` was the only one still unverified post-0.16.5) and a deliberately narrow biomedical question to contrast with the broad GLP-1 (systematic_review) and hot-ML Mamba (comparative_analysis) examples.

## Topline

| Phase | Outcome |
|---|---|
| 0 — Scope | 5 keyword clusters identified (capsid engineering, BBB penetration, neuronal tropism, de-targeting, delivery routes); G1 passes. |
| 1 — Discovery | 4 federated sources × 4 rounds = **16 queries**, **681 papers** in corpus after dedupe + chase. Crossref timed out once (F-finding 4). |
| 2 — Triage | Ranked 250 unique selected-source papers, top-25 selected, **4 deep / 5 skim / 16 untriaged**. |
| 3 — Deep read | 4 mechanistic primary papers deep-read end-to-end: LY6A (Hordeaux 2019), CAP-B10 (Goertsen 2021), single-residue BBB (Eid 2023), LRP6 (Stanford 2024). |
| 4 — Chase | OpenAlex chase returned 545 refs across 4 seeds → 4 new papers added. S2 chase rate-limited (F-finding 5). |
| 5 — Synthesis | 4 themes + 3 tensions written. |
| 6 — Self-critique | 5 findings, 1 appendix, all resolved before G7. |
| 7 — Render | `reports/aav-capsid-cns-delivery_20260512.md` (380+ lines) + matching `.bib` (25 entries); **17 anchors used, 0 unknown** after one round of DOI correction. |

Total wall time: ~12 minutes including phase-by-phase manual review.

## Friction findings

### F1 — Saturation papers-axis still hot under strict mode (third confirmation)

Same friction pattern as the GLP-1 and Mamba runs. After 4 rounds with deliberately narrowing angle queries, the `papers_new_pct` axis remained at 70–100% on openalex / arxiv / pubmed even though the other three axes (authors, venues, citations) had converged into the saturated range.

`SCHOLAR_SATURATION_MIN_AXES=3` resolved it cleanly — 3 of 4 axes converged on all active sources, G2 advanced. This is the **third real-world data point** validating the 0.16.5 soft-saturation feature, and the first one on a *narrow biomedical* question (GLP-1 was broad biomedical, Mamba was broad ML). The "hot papers axis on a narrow question" finding suggests the friction is **not topic-specific** — it is a property of any field where authors prolifically reformulate around an active research front, regardless of breadth.

Action: none — F1 already shipped 0.16.5. This run is additional validation.

### F2 — Cross-domain ranker pulled CRISPR/Cancer tangentials into top-25 (second confirmation)

The keyword-only relevance scorer ranked 4 papers with prominent "gene therapy" / "CRISPR" content into the top 25, despite no capsid-engineering or CNS-delivery focus:

- `doi:10.1038/s41392-023-01309-7` "CRISPR/Cas9 therapeutics: progress and prospects" (cit=635)
- `doi:10.1186/s12943-022-01518-8` "Current applications of CRISPR/Cas9 gene editing in cancer" (cit=436)
- `doi:10.3390/ijms21176240` "CRISPR-Cas9 DNA Base-Editing and Prime-Editing" (cit=420)
- `doi:10.1007/s40259-017-0234-5` "Adeno-Associated Virus (AAV) as a Vector for Gene Therapy" (cit=1329, generic 2017 review)

Workaround: manual triage to defer tier during Phase 2. This is the **same friction as the Mamba run** (where 5 of 10 deep-tier picks were vision-Mamba derivatives), now confirmed cross-domain (biomedical, not just CS). Citation magnitude pulls high-citation tangentially-relevant papers up the rank with no semantic discriminator to push them down.

Action: F2 (semantic-cluster surfacing in Phase 2) is now confirmed twice in two different domains; this strengthens the case for prioritizing it in 0.17.

### F3 — Triage patch shape friction (new, minor)

`research_state.py triage --patch ...` required a wrapper `{"triage_records": {...}, "meta": {...}}` shape, but the schema introspection (`--schema` on `triage`) only exposed `params.patch.help = "Patch JSON file path"`. I initially sent the bare records dict and got `counts.deep=0` with no error — a silent no-op rather than a `validation_error`.

This is an **observability gap**, not a contract violation. The CLI didn't lie (the function signature is documented in `state_apply.py`), but a host LLM that hadn't read the source would burn a retry. Suggested improvement: `--patch-schema` or include a "shape" example in the schema body. Low priority.

### F4 — Crossref SSL/timeout (third occurrence)

`search_crossref.py` returned `upstream_error/retryable` after 36s on the first attempt and `JSONDecodeError` on the retry. Same flake pattern as the Mamba and GLP-1 runs.

The skill correctly degraded — Phase 1 advanced with 4 sources (openalex + arxiv + pubmed + biorxiv) and G2's sources-breadth check (≥3 required) passed. Graceful degradation works as designed; no skill-side action.

### F5 — Semantic Scholar 429 on citation chase (third occurrence)

`build_citation_graph.py` was rate-limited by S2 on all 4 seeds without `S2_API_KEY`. Fell back to OpenAlex-only chase (545 references retrieved, 4 new papers added) which was sufficient for G5.

Expected behavior per P7 (authentication delegation). No skill-side action.

## Observations specific to `grant_background`

- The archetype's narrative template is more open-ended than `systematic_review` (no PICO tables, no PRISMA flow). The Executive Summary + Background + Themes + Tensions + Synthesis + Gaps structure matches a competitive R-series proposal background section.
- The Phase 6 self-critique findings (especially F2 recency-skew and F3 single-source-LRP6 hedge) translate directly into hedging language in the rendered narrative — exactly what you want a reviewer to see surfaced.
- 4 deep reads were sufficient for a defensible 380-line background; the corpus's 681 papers stay accessible via the bib + state for follow-on questions.

## What this run validates in 0.16.5

- Soft-saturation (F1 shipped) works on a *narrow biomedical* question, not just hot ML — third independent confirmation.
- `grant_background` archetype renders correctly end-to-end with lint-clean DOI anchors.
- All 7 gates (G1..G7) advance correctly under the soft-saturation env override.
- Crossref / S2 / arXiv flakes all degrade gracefully without manual intervention.

Useful as a regression fixture for the `grant_background` archetype and for soft-saturation behavior.
