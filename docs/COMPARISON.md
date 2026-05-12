# Comparison — with vs without this skill

[中文](COMPARISON_CN.md) · [← back to README](../README.md)

| Capability | Native agent | This skill |
|------------|--------------|------------|
| Multi-source federated search | One source per turn | 7 sources, federated |
| Multi-round search with saturation gate | One-shot | Three-axis saturation check (paper / author / venue) |
| Cross-source deduplication | None | DOI-first, title-similarity fallback |
| Transparent ranking formula | Opaque | Formula + per-paper component scores in state |
| Forward/backward citation chase | None | OpenAlex + Semantic Scholar dual-backend graph expansion |
| Resumable state | Stateless per turn | `research_state.json` (atomic, exclusive-locked) |
| Choice of report archetype | Generic outline | 5 archetypes selected from intent |
| Self-critique pass | None | Mandatory 14-point checklist (Phase 6) |
| Citation anchors enforced | Claims float | Every claim needs `[^id]`; gate rejects unanchored prose |
| BibTeX / CSL-JSON / RIS export | None | Generated from state, never retyped |
| PDF text extraction | Sometimes | `pypdf` with auto-upgrade to **docling** (layout-aware, OCR) for scanned/sparse PDFs; OA-chain DOI resolution; host-native WebFetch fallback for landing-page abstracts |
| Parallel deep-read fan-out | Sequential | Wave-based agent dispatch (8–10 / wave) + tier-aware triage |
| Idempotent retries | N/A | `--idempotency-key` on every mutating command |
| Cross-process rate limiting | N/A | Per-source file-lock + 429 cooldown observation |
| Source discovery | Read each script | `list_sources.py` — filter by domain / index-type / auth |
| MCP graceful degradation | N/A | Scripts work even when MCP times out |
