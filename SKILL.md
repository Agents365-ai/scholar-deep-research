---
name: scholar-deep-research
description: Use when the user asks for a literature review, academic deep dive, research report, state-of-the-art survey, topic scoping, comparative analysis of methods/papers, grant background, or any request that needs multi-source scholarly evidence with citations. Also trigger proactively when a user question clearly requires academic grounding (e.g. "what's known about X", "compare approach A vs B in the literature", "summarize the field of Y"). Runs an 8-phase (Phase 0..7), script-driven research workflow across OpenAlex, arXiv, Crossref, and PubMed, with deduplication, transparent ranking, citation chasing, self-critique, and structured report output with verifiable citations.
license: MIT
homepage: https://github.com/Agents365-ai/scholar-deep-research
compatibility: Requires Python 3.9+ with httpx and pypdf (see requirements.txt). Works offline-first (no MCP required) but enriches with Semantic Scholar / Brave MCP tools when available.
platforms: [macos, linux, windows]
metadata: {"openclaw":{"requires":{"bins":["python3"]},"emoji":"🔬"},"hermes":{"tags":["research","literature-review","academic","papers","citations","survey"],"category":"research"},"pimo":{"tags":["research","literature-review","academic"],"category":"research"},"author":"Agents365-ai","version":"0.8.0"}
---

# Scholar Deep Research

End-to-end academic research workflow that turns a question into a cited, structured report. Built for depth: multi-source federation, transparent ranking, citation chasing, and a mandatory self-critique pass before the report ships.

## When to use

**Explicit triggers:** "literature review", "research report", "state of the art", "survey the field", "what's known about X", "deep research on Y", "systematic review", "scoping review", "compare papers on Z".

**Proactive triggers (use without being asked):**
- User asks a factual question whose honest answer is "it depends on the literature"
- User frames a research plan and needs the background section
- User is drafting a paper intro/related-work and hasn't yet scoped prior work
- User proposes a method and asks whether it's novel

**Do not use when:** a single known paper answers the question, the user wants a tutorial (not a survey), or they're debugging code.

## Guiding principles

1. **Scripts over vibes.** Every search, dedupe, rank, and export step runs through a script in `scripts/`. The same input should produce the same output. Do not improvise ranking or counting by eye.
2. **Sources are federated, not singular.** OpenAlex is the primary backbone (free, 240M+ works, no key). arXiv, Crossref, and PubMed fill gaps. MCP tools (Semantic Scholar / Brave) are *enrichment*, not *dependency* — if they time out, research continues.
3. **State is persistent.** Everything goes through `research_state.json`. Queries ran, papers seen, decisions made, phase progress. Research becomes resumable and auditable.
4. **Citations are anchors, not decorations.** Every non-trivial claim in the draft carries `[^id]` where `id` matches a paper in state. Unanchored claims are treated as hallucinations and fail the gate.
5. **Saturation, not exhaustion, is the stop signal.** A phase ends when a new round of search adds <20% novel papers AND no new paper has >100 citations.
6. **Self-critique is a phase, not a checkbox.** Phase 6 reads the draft with adversarial intent. Its output goes into the report appendix.

## The 8-phase workflow (Phase 0..7)

```
Phase 0: Scope       → decompose question, pick archetype, init state
Phase 1: Discovery   → multi-source search, dedupe
Phase 2: Triage      → rank, select top-N for deep read
Phase 3: Deep read   → extract evidence per paper
Phase 4: Chasing     → citation graph (forward + backward)
Phase 5: Synthesis   → cluster by theme, map tensions
Phase 6: Self-critique → adversarial review, gap finding
Phase 7: Report      → render archetype template, export bibliography
```

Each phase writes to `research_state.json` before advancing. If the user pauses or a session crashes, the next run reads the state and picks up from the last completed phase.

### Phase 0 — Scope

**Step 0 — Check for skill updates (silent, once per day).** Before anything else, run:

```bash
python scripts/check_update.py
```

The script self-throttles to one real check per 24 hours (via a `.last_update_check` timestamp in the skill root); running it every session is cheap. It always exits 0 and never fails the workflow — route on `data.action` only when you need to tell the user something:

- **`updated`** → one line: `[Skill updated: <from> → <to> (<commits_behind> commits). Continuing with new version.]`. If `requirements_changed: true`, append: `Python deps changed — run` `` `pip install -r requirements.txt` `` `before next use.`
- **`skipped_dirty`** → one line: `[Skill update skipped — you have local changes in <dirty_count> file(s). Review with` `` `cd <skill_root> && git status` `` `.]` so the user knows they're running a stale version on purpose.
- Everything else (`up_to_date`, `skipped_throttled`, `skipped_disabled`, `not_a_git_repo`, `check_failed`) → continue silently. Don't mention to the user.

Escape hatches: `SCHOLAR_SKIP_UPDATE_CHECK=1` pins the version permanently; `python scripts/check_update.py --force` bypasses the 24h throttle for an immediate check.

Before searching anything, decompose the question.

1. **Restate the question** in one sentence. Surface ambiguities.
2. **PICO-style decomposition** (or equivalent for non-biomedical fields):
   - **P**opulation / **P**roblem — what system, species, setting, or phenomenon?
   - **I**ntervention / **I**ndependent var — what method, factor, or manipulation?
   - **C**omparison — against what baseline or alternative?
   - **O**utcome — what is being measured or claimed?
3. **Pick an archetype** that matches user intent (see `references/report_templates.md`):
   - `literature_review` — what is known about X (default)
   - `systematic_review` — rigorous PRISMA-lite, comparison of many studies on one narrow question
   - `scoping_review` — what has been studied and how (breadth over depth)
   - `comparative_analysis` — X vs Y, head-to-head
   - `grant_background` — narrative background + gap for a proposal
4. **Draft keyword clusters** — 3-5 Boolean clusters covering synonyms, acronyms, and variant spellings. Include a "negative" cluster (terms to exclude).
5. **Initialize state:**
   ```bash
   python scripts/research_state.py --state research_state.json init \
     --question "<restated question>" \
     --archetype literature_review
   ```
   (`--state` is top-level and applies to every subcommand; `init` itself takes `--question`, `--archetype`, and optional `--force`.)

When in doubt about archetype, ask the user. The choice shapes everything downstream.

### Phase 1 — Discovery

Run searches across all available sources in parallel. OpenAlex is primary; the others fill gaps.

```bash
# Primary (no API key, always available)
python scripts/search_openalex.py --query "<cluster 1>" --limit 50 --state research_state.json
python scripts/search_openalex.py --query "<cluster 2>" --limit 50 --state research_state.json

# Domain-specific (use when relevant)
python scripts/search_arxiv.py  --query "<cluster>" --limit 50 --state research_state.json  # CS/ML/physics
python scripts/search_pubmed.py --query "<cluster>" --limit 50 --state research_state.json  # biomedical
python scripts/search_crossref.py --query "<cluster>" --limit 50 --state research_state.json  # DOI-backed metadata

# Open-web coverage (optional, requires EXA_API_KEY) — finds material the
# scholarly APIs miss: lab sites, institutional PDFs, conference mirrors,
# preprints parked outside arXiv, NGO/government reports.
python scripts/search_exa.py --query "<cluster>" --limit 50 --state research_state.json

# Dedupe across sources (DOI-first, title-similarity fallback)
python scripts/dedupe_papers.py --state research_state.json
```

**MCP enrichment (optional, run if available):** call `mcp__asta__search_papers_by_relevance` and `mcp__asta__snippet_search` and feed results via `scripts/research_state.py ingest`. If the MCP call errors or times out, do not retry — move on.

**Iterate.** Read the state file. Are there keyword gaps? Are there authors appearing 3+ times whose other work you haven't pulled? Run another round. Stop when saturation hits — **every source, not just the last one queried:**

```bash
python scripts/research_state.py saturation --state research_state.json
# Returns { "per_source": {...}, "overall_saturated": true/false, ... }
```

`overall_saturated` is true only when every queried source has run at least `--min-rounds` (default 2) rounds AND each is individually below the new-paper percentage and new-citation thresholds. A source that has been queried only once cannot be declared saturated, which rules out the failure mode where a single quiet source falsely ends discovery. Use `--source openalex` to check one source in isolation.

### Phase 2 — Triage

Rank the deduplicated corpus and pick the top-N for deep reading.

```bash
python scripts/rank_papers.py \
  --state research_state.json \
  --question "<phase 0 question>" \
  --alpha 0.4 --beta 0.3 --gamma 0.2 --delta 0.1 \
  --top 20
```

The formula is transparent — the script prints it and writes the components to state so the report can cite its own methodology:

```
score = α·relevance + β·log10(citations+1)/3 + γ·recency_decay(half-life=5yr) + δ·venue_prior
```

Defaults target a literature review. For a *scoping* review prefer higher `α` (relevance) and lower `β` (citations). For a *systematic* review of a narrow question, lower `α` and higher `β`.

Write the top-N selection to state:

```bash
python scripts/research_state.py select --state research_state.json --top 20
```

**Triage the selection into deep / skim / defer tiers** before advancing. Phase 3 fan-out is the most expensive stage of the workflow; not every selected paper deserves a full agent dispatch:

```bash
python scripts/skim_papers.py --state research_state.json \
  --deep-ratio 0.5 --skim-ratio 0.5
```

Defaults split the top-N evenly: top half → `deep` (agent dispatch in Phase 3), bottom half → `skim` (abstract-derived evidence stub auto-filled, `depth=shallow`). For tighter budgets, use `--deep-ratio 0.3 --skim-ratio 0.5` — the remaining 20% gets `tier=defer` and is removed from `selected_ids` (still queryable as candidates for citation chase).

The script emits `data.deep_tier_preview` listing the deep-tier papers by triage_score. **Show this to the user before advancing** so they can hand-override before agents fan out (re-run with different ratios, or manually re-rank in state). Triage is required before G3 passes — the gate's `triage_applied` check rejects the advance otherwise.

**Optional but recommended — prefetch deep-tier PDFs** before agent fan-out:

```bash
python scripts/prefetch_pdfs.py --state research_state.json \
  --tier deep --concurrency 4
```

Fetches every deep-tier paper's PDF into `${SCHOLAR_CACHE_DIR:-.scholar_cache}/pdfs/<id-hash>/` via `paper-fetch` (with Unpaywall fallback), in parallel waves, and writes `pdf_path` / `pdf_status` / `pdf_source` / `pdf_bytes` per paper. Phase 3 agents then **read the local file directly** instead of each running its own download — Agent context stays focused on reading + reasoning, not on retrying paywalls.

Failures land as `pdf_status='failed'` with a `pdf_failure_code` (`paper_fetch_error`, `no_open_access_pdf`, `pdf_download_failed`, …); papers without a DOI get `pdf_status='no_doi'`. Phase 3 agents check `pdf_path` first and only fall back to `extract_pdf.py --doi` if the prefetched path is missing. Re-running prefetch is cheap: papers with an existing `pdf_path` on disk are skipped (`pdf_status='cached'`).

Skip prefetch entirely when paper-fetch is not installed AND you don't want Unpaywall traffic — Phase 3 agents will then download per-paper inside their own contexts (slower, noisier, but functionally identical).

### Phase 3 — Deep read (parallel agent fan-out)

Phase 3 splits by tier:

- **`tier=skim`** — `apply_triage()` already wrote an abstract-derived evidence stub with `depth=shallow`. No further action needed.
- **`tier=deep`** — dispatch one agent per paper, in parallel waves of 8–10. Each agent reads the PDF, writes structured evidence back to state, and returns one JSON line. The host's main context never sees the full PDF text.

The agent prompt template lives at `references/agent_prompts/phase3_deep_read.md`. Load it once, instantiate per paper, and dispatch all N tool_use calls in a **single message** so they fan out concurrently. Per-agent contract:

- **Input:** `paper_id`, `doi`, `pdf_url`, `abstract`, `question`, `state_path`
- **Action:** `extract_pdf.py --doi <doi> --output <tmp>` → read text → write `evidence add --depth full`
- **Output:** one line `{"paper_id": "...", "status": "ok"|"evidence_unavailable", ...}`

The state CLI is exclusive-locked, so N agents writing concurrent `evidence add` calls are serialized automatically — no coordination needed.

```bash
# After all wave(s) complete, verify deep-tier coverage:
python scripts/research_state.py advance --state research_state.json \
  --to 4 --check-only
```

If `deep_tier_full_evidence` is failing, dispatch a follow-up wave for the missing ids only. If a paper's full text is genuinely unreachable (paywall, exhausted OA chain), the agent should write a `depth=shallow` record with `method` starting `evidence_unavailable:` per the prompt's failure-mode section — that record satisfies `depth_marks_valid` without inflating the deep-tier coverage count.

**Manual fallback (no agents available).** Hosts that cannot dispatch parallel agents (some non-CC platforms) can run Phase 3 sequentially in the main session: for each `tier=deep` paper, `extract_pdf.py --doi <doi>` then `research_state.py evidence --id <pid> --depth full ...`. Slower and burns more context, but the gate logic is identical.

### Phase 4 — Citation chasing

Take the top 5-10 highest-ranked papers and expand the graph.

```bash
# Preview the request count first — this is the most expensive command
python scripts/build_citation_graph.py \
  --state research_state.json \
  --seed-top 8 --direction both --depth 1 --dry-run

# Run with an idempotency key so a retry after a network blip is free
python scripts/build_citation_graph.py \
  --state research_state.json \
  --seed-top 8 --direction both --depth 1 \
  --idempotency-key "chase-$(date -u +%Y%m%dT%H%M)"
```

The script pulls backward references (what did this paper cite?) and forward citations (who cited this paper?), deduplicates against existing state, and writes new candidate papers with `discovered_via: citation_chase`. Run rank + deep read again on any new high-scoring additions.

**Idempotency.** When `--idempotency-key <k>` is set, the first successful run writes `{response, signature}` to `.scholar_cache/<hash>.json`. A retried run with the same key replays the cached response without re-hitting OpenAlex or re-mutating state. Reusing the same key with different arguments returns `idempotency_key_mismatch` rather than silently serving stale data. Cache directory: `SCHOLAR_CACHE_DIR` env var, default `.scholar_cache/`.

**Special case — a highly cited paper has never been challenged.** If rank says a paper is top-3 by citations but no critiques appear in the corpus, search explicitly for `"<first author> <year>" critique OR limitations OR reanalysis OR failed replication`. This is the confirmation-bias backstop.

### Phase 5 — Synthesis

No scripts here — this is where the agent earns its keep. Cluster and structure:

1. **Thematic clustering.** Group the top-N into 3-6 themes that map onto the report outline. Themes should be orthogonal: a paper can be primary to one, secondary to at most one other.
2. **Tension map.** Where do papers disagree? For each disagreement, note: which papers, on what, and whether the disagreement is empirical (different data), methodological (different tools), or theoretical (different framings).
3. **Timeline.** When relevant, a chronological arc: seminal paper → consolidation → refinement → current frontier.
4. **Venn / gap.** What has been studied well, partially, and not at all? The gap is the pivot for Phase 7.

### Phase 6 — Self-critique

**This is not optional.** Load `assets/prompts/self_critique.md` and run the full checklist against your draft (still unpublished). The checklist covers:

- Single-source claims (any claim backed by only one paper?)
- Citation/recency skew (is the latest-2-years window covered?)
- Venue bias (is the corpus dominated by one journal/venue?)
- Author bias (does one lab dominate the citations?)
- Untested high-citation papers (anyone cite a paper without reading a critique?)
- Contradictions buried (any tension in Phase 5 that got glossed over?)
- Archetype fit (does the structure match the chosen archetype?)
- Unanchored claims (any statement without a `[^id]` anchor?)

Write findings to `research_state.json` under `self_critique` and fix blockers before Phase 7. Findings go into the report appendix verbatim — the reader deserves to see what the research process doubted itself about.

### Phase 7 — Report

Render the chosen archetype template from `assets/templates/`, filling from state:

```bash
# Export bibliography in the user's preferred format
python scripts/export_bibtex.py --state research_state.json --format bibtex --output refs.bib
python scripts/export_bibtex.py --state research_state.json --format csl-json --output refs.json
```

The report body uses `[^id]` anchors (the paper id from state). The bibliography section at the bottom lists each cited paper with DOI/URL. Any claim missing an anchor must be removed or cited.

**Save path convention:** `reports/<slug>_<YYYYMMDD>.md`. The skill does not write outside the working directory unless the user specifies a path.

## Report archetype selection

| Archetype | When to use | Primary output shape |
|-----------|-------------|----------------------|
| `literature_review` | User wants to know what's established about a topic | Thematic sections + synthesis + gap |
| `systematic_review` | Narrow question, many studies, need rigorous comparison | PRISMA-lite flow + extraction table + pooled findings |
| `scoping_review` | Broad topic, "what has been studied?" | Coverage map + methods inventory + research gap |
| `comparative_analysis` | "A vs B" — methods, models, approaches | Axes of comparison + per-axis verdict + recommendation |
| `grant_background` | Narrative for a proposal introduction | Problem significance + what's known + what's missing + why our approach |

Templates live in `assets/templates/<archetype>.md`. Load only the one you need.

## Scripts reference

| Script | Purpose |
|--------|---------|
| `check_update.py` | Phase 0 Step 0 — fast-forward the skill against its origin; never blocks the workflow. |
| `research_state.py` | Init, read, write, query the state file. Central to every phase. |
| `search_openalex.py` | Primary search (no key, 240M works, citation counts). |
| `search_arxiv.py` | arXiv API — preprints and CS/ML/physics. |
| `search_crossref.py` | Crossref REST — authoritative DOI metadata. |
| `search_pubmed.py` | NCBI E-utilities — biomedical corpus with MeSH. |
| `search_exa.py` | Exa neural web search (optional, key-gated) — open-web coverage the scholarly APIs miss. |
| `dedupe_papers.py` | DOI normalization + title similarity merging across sources. |
| `rank_papers.py` | Transparent scoring formula. Prints the formula and per-paper components. |
| `skim_papers.py` | Phase-3 triage. Splits selected papers into `deep` / `skim` / `defer` tiers on cheap deterministic signals, refines `selected_ids`, auto-fills evidence stubs for skim tier. Runs at the close of Phase 2 before G3. |
| `prefetch_pdfs.py` | Optional. Pulls deep-tier PDFs into a stable cache via paper-fetch (with Unpaywall fallback) before Phase 3 agent fan-out. Concurrent (`--concurrency`), idempotent on re-run, fail-soft per paper. Writes `pdf_path` / `pdf_status` per paper so agents read a local file instead of re-downloading. |
| `build_citation_graph.py` | Forward/backward snowballing via OpenAlex. |
| `extract_pdf.py` | Full-text extraction (pypdf). Accepts `--input`, `--url`, or `--doi`. DOI mode resolves via [paper-fetch](https://github.com/Agents365-ai/paper-fetch) skill if installed, falls back to Unpaywall. Safe on scanned PDFs (skips, emits warning). |
| `export_bibtex.py` | BibTeX / CSL-JSON / RIS export from state. |

All scripts accept `--help`, `--schema`, emit a structured JSON envelope on stdout, and use `research_state.json` as the single source of truth. Every script is idempotent on the state file (network-layer idempotency is P1 work).

### CLI contract

Every script prints exactly one JSON envelope to stdout and exits with a code from the stable vocabulary below. No prose is ever mixed into stdout; diagnostics go to stderr.

**Success envelope:**

```json
{ "ok": true, "data": { ... } }
```

**Failure envelope:**

```json
{
  "ok": false,
  "error": {
    "code": "snake_case_routing_key",
    "message": "human sentence",
    "retryable": true,
    "...extra context fields...": "..."
  }
}
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | success |
| `1` | runtime error (e.g. malformed upstream response, missing dependency) |
| `2` | upstream / network error (retryable) |
| `3` | validation error (bad input) |
| `4` | state error (missing, corrupt, or schema mismatch) |

**Schema introspection.** Every script supports `--schema`, which prints its full parameter schema (types, defaults, choices, required flags, subcommands where applicable) as JSON and exits 0. An agent discovering an unfamiliar script should run `--schema` before `--help` — it is machine-parseable and covers everything `--help` does.

```bash
python scripts/search_openalex.py --schema
python scripts/research_state.py --schema   # includes every subcommand
```

**Export bibliography exception.** `export_bibtex.py` without `--output` writes raw BibTeX/RIS/CSL text to stdout for pipe compatibility (`export_bibtex.py --format bibtex > refs.bib`). Agents that need a structured response should always pass `--output` — that path returns `{"ok": true, "data": {"output": "...", "format": "bibtex", "count": N}}`.

### Environment variables

Trust-boundary configuration — set once by the human or orchestrator. CLI flags override where present.

| Variable | Used by | Purpose |
|----------|---------|---------|
| `SCHOLAR_STATE_PATH` | every script that takes `--state` | Default path to `research_state.json` |
| `SCHOLAR_MAILTO` | `search_openalex.py`, `search_crossref.py`, `build_citation_graph.py` | Polite-pool email for OpenAlex / Crossref — higher rate limits |
| `NCBI_API_KEY` | `search_pubmed.py` | NCBI E-utilities API key — higher rate limits |
| `EXA_API_KEY` | `search_exa.py` | Exa API key — required to enable the open-web search provider |
| `SCHOLAR_CACHE_DIR` | `build_citation_graph.py` (any command that takes `--idempotency-key`) | Cache directory for idempotent-retry responses; default `.scholar_cache/` in cwd |
| `PAPER_FETCH_SCRIPT` | `extract_pdf.py` | Path to paper-fetch's `fetch.py`. If unset, auto-discovers across all known skill install paths (Claude Code, OpenCode, OpenClaw, Hermes, ~/.agents). If not found, falls back to Unpaywall |
| `SCHOLAR_SKIP_UPDATE_CHECK` | `check_update.py` | Set to any non-empty value to pin the current version and skip Phase 0 Step 0's auto-update |

Agents should never set these themselves. They belong in the shell profile, a systemd unit, or the orchestrator's env injection.

## State file schema (abbreviated)

```json
{
  "schema_version": 1,
  "question": "...",
  "archetype": "literature_review",
  "phase": 3,
  "created_at": "...",
  "updated_at": "...",
  "queries": [{"source": "openalex", "query": "...", "hits": 42, "new": 30, "round": 1}],
  "papers": {
    "doi:10.1038/nature12373": {
      "id": "doi:10.1038/nature12373",
      "title": "...",
      "authors": ["..."],
      "year": 2013,
      "venue": "Nature",
      "citations": 523,
      "abstract": "...",
      "source": ["openalex", "crossref"],
      "score": 0.81,
      "score_components": {"relevance": 0.9, "citations": 0.8, "recency": 0.6, "venue": 1.0},
      "selected": true,
      "depth": "full",
      "tier": "deep",
      "triage_score": 0.74,
      "triage_components": {"relevance": 0.8, "citation_density": 0.6, "recency": 0.9, "has_pdf": 1.0, "abstract_quality": 1.0},
      "evidence": {"method": "...", "findings": ["..."], "limitations": "..."},
      "discovered_via": "search"
    }
  },
  "triage_complete": true,
  "triage_meta": {"weights": {...}, "deep_ratio": 0.5, "skim_ratio": 0.5, "triaged_at": "..."},
  "themes": [{"name": "...", "paper_ids": ["..."]}],
  "tensions": [{"topic": "...", "sides": [{"position": "...", "paper_ids": ["..."]}]}],
  "self_critique": {"findings": [], "resolved": [], "appendix": "..."},
  "report_path": "reports/slug_20260411.md"
}
```

See `scripts/research_state.py --help` for the full schema.

## Completion gates

Each phase transition has a gate (G1..G7). Advance ONLY via:

```bash
python scripts/research_state.py --state <path> advance          # advance by 1
python scripts/research_state.py --state <path> advance --check-only   # preview only
```

The gate predicates are enforced in `scripts/_gates.py`. Direct `set --field phase` is rejected — the `phase` field is no longer settable. If the gate fails, the envelope lists the failing checks by name so you know exactly what's missing.

| Target | Gate (enforced) |
|--------|-----------------|
| G1 (→ 1) | Question set, archetype valid, state initialized. *`≥3 keyword clusters` is host-checked.* |
| G2 (→ 2) | `overall_saturated == true` across all queried sources AND ≥3 distinct sources in `state.queries`. |
| G3 (→ 3) | `state.ranking` recorded; `selected_ids` non-empty; every selected paper has `score_components`; `state.triage_complete=true` (run `skim_papers.py`). |
| G4 (→ 4) | All selected papers have `depth ∈ {full, shallow}` AND **every `tier=deep` paper has `depth=full`** (skim-tier `depth=shallow` is by design and does not block). |
| G5 (→ 5) | ≥1 query with `source=openalex_citation_chase` and `hits > 0`. |
| G6 (→ 6) | `len(themes) ≥ 3` AND (`len(tensions) ≥ 1` OR a critique finding mentioning "no tensions"). |
| G7 (→ 7) | `state.self_critique.appendix` non-empty; `len(resolved) ≥ len(findings)`. |

## Enrichment with MCP tools

If the session has Semantic Scholar (asta) or Brave Search MCP tools available, use them as enrichment:

- `mcp__asta__search_papers_by_relevance` — good for dense relevance ranking
- `mcp__asta__get_citations` — lighter weight than citation graph for a few seed papers
- `mcp__asta__snippet_search` — grep-like search across abstracts
- Brave Search — non-academic sources (blog posts, press releases, pre-print discussion)

**Treat MCP tools as unreliable by design** — they may timeout or be unavailable. Never place a phase-critical step behind an MCP call. Scripts are the spine; MCP is the skin.

## Pitfalls (short list; see `references/pitfalls.md` for detail)

1. **Treating the first page of search results as "the literature"** — run multiple keyword clusters and chase citations.
2. **Unanchored claims** — every non-trivial statement in the report needs a `[^id]` pointing to a paper in state.
3. **Confirmation bias** — actively search for critiques of top-cited papers; see Phase 4 special case.
4. **Preprint conflation** — arXiv/bioRxiv are preprints; tag them as such in the report and weight evidence accordingly.
5. **Venue monoculture** — if >60% of top-N come from one journal/venue, broaden sources.
6. **Author monoculture** — same for a single lab or author.
7. **Recency collapse** — the last 2 years matter for "state of the art" framings; check explicit coverage.
8. **Stale MCP tool names** — MCP servers rename tools; always list available tools before assuming names. Script paths are stable; MCP names are not.
9. **Single-shot search** — budget for ≥3 search rounds per cluster, not one.
10. **Skipping self-critique** — the temptation to ship a clean draft is exactly when Phase 6 catches the most.

## Example interaction

```
User: Give me a deep research report on CRISPR base editing for Duchenne muscular dystrophy.

Agent:
[Phase 0] Restating: "What is the current state and evidence for CRISPR base editing
          as a therapeutic approach for Duchenne muscular dystrophy (DMD)?"
          Archetype: literature_review (default; confirmed — broad overview requested)
          Clusters:
            - ("base editing" OR "adenine base editor" OR "cytosine base editor" OR ABE OR CBE)
            - ("Duchenne muscular dystrophy" OR DMD OR dystrophin)
            - (in vivo OR AAV OR "muscle delivery")
          → research_state.json initialized

[Phase 1] Running OpenAlex + PubMed + arXiv + Crossref across 3 clusters...
          Round 1: 187 hits, 142 unique. Round 2: 94 hits, 31 new.
          Saturation check: new=11%, max_new_citations=23 → SATURATED
          143 unique papers in state.

[Phase 2] Ranking with default weights (literature review)...
          Top 20 selected. Score components written to state.

[Phase 3] Fetching full text... 17/20 full, 3 abstract-only (flagged shallow).
          Evidence extraction complete.

[Phase 4] Citation chasing on top 8 seeds, depth 1.
          Added 24 candidates, 6 re-scored into top 20.

[Phase 5] Themes: (a) delivery platforms, (b) editing efficiency, (c) off-target/safety,
          (d) pre-clinical outcomes, (e) clinical translation barriers.
          Tensions: AAV serotype optimality (Theme a) — 3 papers disagree.

[Phase 6] Self-critique flagged 2 single-source claims and a recency gap
          (no 2025 paper in top 20). Re-ran focused search; added 4 papers.

[Phase 7] Rendering literature_review template...
          Report: reports/crispr-base-editing-dmd_20260411.md
          Bibliography: reports/crispr-base-editing-dmd_20260411.bib (84 refs)
```

## References

Modular documentation, loaded only when needed:

- `references/search_strategies.md` — Boolean clusters, PICO, snowballing, saturation math
- `references/source_selection.md` — which database for which question
- `references/quality_assessment.md` — CRAAP, journal tier, retraction check, preprint handling
- `references/report_templates.md` — the 5 archetypes with section-by-section guidance
- `references/pitfalls.md` — long-form version of the pitfalls list with examples
- `references/agent_prompts/phase3_deep_read.md` — per-paper prompt for parallel agent fan-out in Phase 3
