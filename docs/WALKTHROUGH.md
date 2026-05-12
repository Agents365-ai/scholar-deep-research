# Walkthrough — what a run looks like

[中文](WALKTHROUGH_CN.md) · [← back to README](../README.md)

You describe the topic. The skill walks the 8 phases automatically, persisting everything to `research_state.json`.

```
Run a deep research report on CRISPR base editing for Duchenne muscular dystrophy.
```

```
[Phase 0] Restating: "What is the current state of CRISPR base editing as a
          therapeutic for Duchenne muscular dystrophy?"
          Archetype: literature_review
          → research_state.json initialized

[Phase 1] OpenAlex + PubMed + arXiv + Crossref across 3 clusters...
          Round 1: 187 hits, 142 unique. Round 2: 94 hits, 31 new.
          Saturation: paper=11%, author=18%, venue=14% → SATURATED

[Phase 2] Ranking with literature-review weights...
          Top 20 selected. Score components written to state.
          Triage: 10 deep + 10 skim (--deep-ratio 0.5).
          Prefetch: 8/10 deep-tier PDFs cached, 2 paywalled (no OA).

[Phase 3] Deep tier: 8 parallel agents dispatched (1 wave) — each reads
          a local pdf_path, no per-agent download.
          8 returned full evidence; 2 paywalled papers carry
          evidence_unavailable from prefetch. Skim tier: 10
          abstract-derived evidence stubs auto-filled.

[Phase 4] Citation chasing on top 8 seeds, depth 1.
          Added 24 candidates, 6 re-scored into top 20.

[Phase 5] Themes: delivery, editing efficiency, off-target safety,
          pre-clinical, clinical translation.
          Tensions: AAV serotype optimality (3 papers disagree).

[Phase 6] Self-critique flagged 2 single-source claims and a recency gap.
          Ran focused search; added 4 papers.

[Phase 7] reports/crispr-base-editing-dmd_20260411.md (84 refs)
```

Output: `reports/<slug>_<YYYYMMDD>.md` plus a matching `.bib`.

Every phase transition runs through `python scripts/research_state.py advance`, which executes the gate predicate and refuses with a structured `gate_not_met` envelope (listing failing checks **and** suggested next commands) when criteria aren't met. There is no way to skip a gate by setting `phase` directly. Phase 6 (self-critique) can loop back to Phase 1 when it finds gaps; everything else is linear.
