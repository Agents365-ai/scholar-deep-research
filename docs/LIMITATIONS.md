# Known limitations

[中文](LIMITATIONS_CN.md) · [← back to README](../README.md)

- **No Google Scholar / Web of Science / Scopus** — these have no public API or require institutional access. Mention in report appendix as "not consulted" if it matters for your topic.
- **DOI resolution requires open access** — `--doi` mode finds legally open-access PDFs (via [paper-fetch](https://github.com/Agents365-ai/paper-fetch) or Unpaywall). For gated papers, Phase 3 step (d) tries `WebFetch` on the publisher landing page; failing that, the paper is marked `evidence_unavailable` and excluded from full-evidence claims.
- **arXiv has no citation counts** — arXiv-only papers get `citations=null` and a 0 contribution from the citation component of the rank score.
- **PubMed full abstracts** — fetched on demand only (`--with-abstracts`); the default round-trip uses esummary for speed.
- **English-language bias** — all sources index non-English work but search quality varies. Note in the report's limitations if your topic has substantial non-English literature.
- **Ranking is bag-of-words for relevance** — for semantic re-ranking, plug an embedding model and write the result back into `state.papers[*].score_components.relevance`. The pipeline is designed for that override.
- **Saturation gate is novelty-based, not exhaustiveness-based** — three-axis (paper / author / venue) saturation catches "exploration has stalled" but won't tell you "you have all the relevant papers." Use systematic-review archetype + `SCHOLAR_SATURATION_NEW_PCT=20` for stricter coverage.
