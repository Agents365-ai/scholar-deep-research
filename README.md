# scholar-deep-research — From Question to Cited Report

[中文文档](README_CN.md) &middot; 🌐 **Website:** [agents365-ai.github.io/scholar-deep-research](https://agents365-ai.github.io/scholar-deep-research/)

An 8-phase (Phase 0..7), script-driven academic research workflow that turns a research question into a structured, cited report. Multi-source federation across 6 databases, mandatory self-critique, parallel deep-read agent fan-out.

## Why this exists

Every script under `scripts/` is pure data — search, dedupe, rank, citation-chase, bibliography export. **Zero LLM calls inside the pipeline.** The host LLM is the orchestrator: it reads `SKILL.md`, calls the CLI tools, decides what to do next based on JSON envelopes coming back. That separation buys three properties that LLM-in-the-loop pipelines can't have:

- **Reproducible** — same state → same output, no model nondeterminism.
- **Auditable** — every mutation flows through one `research_state.py` boundary.
- **Testable** — the 148-test smoke suite at `scripts/tests/run.py` runs in ~4 s with no API keys, no network, no model.

MCP tools and the host LLM enrich the agent's decisions; they never sit on the critical path.

## What a run looks like

Just describe what you want:

```
Run a deep research report on CRISPR base editing for Duchenne muscular dystrophy.
```

The skill walks the 8 phases automatically:

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

## What you get

- **Phase 0..7 cited-report pipeline** with 7 enforced phase-transition gates (G1..G7 in `scripts/_gates.py`)
- **6 federated sources** — OpenAlex, arXiv, Crossref, PubMed, DBLP, bioRxiv. All free, none require an API key
- **Cross-source deduplication** — DOI-first, title-similarity fallback; one paper, one record
- **Three-axis saturation** — paper / author / venue novelty all must drop below threshold for Phase 1 to terminate. Catches the failure mode where queries keep surfacing different papers from the same lab while exploration has stalled
- **Parallel deep-read fan-out (Phase 3)** — selected papers split into `deep` / `skim` / `defer` tiers. Deep tier dispatched in waves of 8–10 isolated-context agents, each reading one PDF; optional PDF prefetch ahead of dispatch surfaces paywalled papers as `evidence_unavailable` *before* a wave starts
- **Transparent ranking** — published formula `α·relevance + β·citations + γ·recency + δ·venue_prior`, components written into state, every paper inspectable
- **Mandatory Phase 6 self-critique** — 14-point adversarial checklist; findings ship in the report appendix
- **Citation rigor** — every claim in the body carries a `[^id]` anchor; unanchored prose fails the gate
- **5 archetype templates** — `literature_review` / `systematic_review` / `scoping_review` / `comparative_analysis` / `grant_background`, picked from user intent
- **BibTeX / CSL-JSON / RIS export** — bibliography generated from state, never retyped

## How it works

```
Phase 0  Scope        question decomposition + archetype + state init
Phase 1  Discovery    multi-source search → dedupe → 3-axis saturation check
Phase 2  Triage       ranking → top-N selection → tier triage → optional PDF prefetch
Phase 3  Deep read    parallel agent fan-out (deep tier) + abstract stub (skim tier)
Phase 4  Chasing      citation graph (forward + backward)
Phase 5  Synthesis    thematic clustering → tension map
Phase 6  Self-critique  14-point adversarial checklist (mandatory)
Phase 7  Report       render archetype template → export bibliography
```

```mermaid
flowchart LR
    Q([Question]) --> P0[0 · Scope]
    P0 --> P1[1 · Discover]
    P1 --> P2[2 · Triage]
    P2 --> P3[3 · Deep read]
    P3 --> P4[4 · Chase]
    P4 --> P5[5 · Synthesize]
    P5 --> P6[6 · Self-critique]
    P6 -- blockers --> P1
    P6 --> P7[7 · Report]
    P7 --> OUT([Cited report + .bib])

    STATE[(research_state.json)]
    P0 & P1 & P2 & P3 & P4 & P5 & P6 & P7 <-.-> STATE

    classDef phase fill:#eef5ff,stroke:#1F6FEB,color:#0b2e66;
    classDef state fill:#f6ffed,stroke:#389e0d,color:#135200;
    class P0,P1,P2,P3,P4,P5,P6,P7 phase;
    class STATE state;
```

Each phase transition runs through `python scripts/research_state.py advance`, which executes the gate predicate and refuses with a structured `gate_not_met` envelope (listing failing checks **and** suggested next commands) when criteria aren't met. There is no way to skip a gate by setting `phase` directly. Phase 6 (self-critique) can loop back to Phase 1 when it finds gaps; everything else is linear.

Every mutating command (`ingest`, `rank`, `dedupe`, `citation-chase`) accepts `--idempotency-key` — a retried call with the same key returns the original result without re-mutating state, so agent crash-recovery is contract-idempotent. The state file itself is written under a sibling `.lock` file with atomic `os.replace`, so concurrent Phase 1 searches are race-free.

## Comparison: with vs without this skill

| Capability | Native agent | This skill |
|------------|--------------|------------|
| Multi-source federated search | One source per turn | 6 sources, federated |
| Multi-round search with saturation gate | One-shot | Three-axis saturation check |
| Cross-source deduplication | None | DOI-first, title-similarity fallback |
| Transparent ranking formula | Opaque | Formula + per-paper component scores in state |
| Forward/backward citation chase | None | OpenAlex graph expansion |
| Resumable state | Stateless per turn | `research_state.json` |
| Choice of report archetype | Generic outline | 5 archetypes selected from intent |
| Self-critique pass | None | Mandatory 14-point checklist (Phase 6) |
| Citation anchors enforced | Claims float | Every claim needs `[^id]`; gate rejects unanchored |
| BibTeX / CSL-JSON / RIS export | None | Generated from state |
| PDF text extraction | Sometimes | `pypdf` with scanned-PDF detection + OA-chain DOI resolution |
| Parallel deep-read fan-out | Sequential | Wave-based agent dispatch + tier-aware triage |
| MCP graceful degradation | N/A | Scripts work even when MCP times out |

## Quick start

### Prerequisites

- **Python ≥ 3.9**
- **Install dependencies:**
  ```bash
  pip install -r requirements.txt
  ```
  Pulls in `httpx` (HTTP client) and `pypdf` (PDF text extraction).

No API keys required. For higher OpenAlex / Crossref / PubMed rate limits, pass `--email <you@host>` (polite pool) or `--api-key` (NCBI). All scripts work without these.

### Install — let your agent do it

The simplest install is to let your coding agent do it. In **Claude Code**, **OpenAI Codex**, **OpenCode**, **OpenClaw**, **Hermes Agent**, or **pi-mono**, paste:

```
Install https://github.com/Agents365-ai/scholar-deep-research for me, then run pip install -r requirements.txt inside it.
```

The agent recognizes Agent Skills repos (`SKILL.md` at root), `git clone`s into the right skills directory for whichever platform is hosting it, installs Python deps, and confirms the skill is loaded. Then ask for a research report — the skill triggers automatically.

### Installation paths

| Platform | Global path | Project path |
|----------|-------------|--------------|
| Claude Code | `~/.claude/skills/scholar-deep-research/` | `.claude/skills/scholar-deep-research/` |
| OpenCode | `~/.config/opencode/skills/scholar-deep-research/` | `.opencode/skills/scholar-deep-research/` |
| OpenClaw / ClawHub | `~/.openclaw/skills/scholar-deep-research/` | `skills/scholar-deep-research/` |
| Hermes Agent | `~/.hermes/skills/research/scholar-deep-research/` | Via `external_dirs` config |
| pi-mono | `~/.pimo/skills/scholar-deep-research/` | — |
| OpenAI Codex | `~/.agents/skills/scholar-deep-research/` | `.agents/skills/scholar-deep-research/` |
| SkillsMP | `skills install scholar-deep-research` | N/A |

<details>
<summary>Manual per-platform commands</summary>

**Claude Code**
```bash
git clone https://github.com/Agents365-ai/scholar-deep-research.git ~/.claude/skills/scholar-deep-research
# or project-level: .claude/skills/scholar-deep-research
```

**OpenCode**
```bash
git clone https://github.com/Agents365-ai/scholar-deep-research.git ~/.config/opencode/skills/scholar-deep-research
# or project-level: .opencode/skills/scholar-deep-research
```

**OpenClaw / ClawHub**
```bash
clawhub install scholar-deep-research
# or manual: git clone … ~/.openclaw/skills/scholar-deep-research
```

**Hermes Agent**
```bash
git clone https://github.com/Agents365-ai/scholar-deep-research.git ~/.hermes/skills/research/scholar-deep-research
```
Or add an external directory in `~/.hermes/config.yaml`:
```yaml
skills:
  external_dirs:
    - ~/myskills/scholar-deep-research
```

**pi-mono**
```bash
git clone https://github.com/Agents365-ai/scholar-deep-research.git ~/.pimo/skills/scholar-deep-research
```

**OpenAI Codex**
```bash
git clone https://github.com/Agents365-ai/scholar-deep-research.git ~/.agents/skills/scholar-deep-research
# or project-level: .agents/skills/scholar-deep-research
```

**SkillsMP**
```bash
skills install scholar-deep-research
```

</details>

## Multi-platform support

| Platform | Status | Details |
|----------|--------|---------|
| **[Claude Code](https://claude.ai/code)** | ✅ Full support | Native SKILL.md format |
| **[OpenCode](https://opencode.ai/)** | ✅ Full support | Reads from `~/.config/opencode/skills/`, `.opencode/skills/`, and (cross-compat) `~/.claude/skills/` and `~/.agents/skills/` |
| **[OpenClaw](https://openclaw.ai/) / [ClawHub](https://clawhub.ai/)** | ✅ Full support | `metadata.openclaw` namespace, dependency gating, `clawhub install` |
| **Hermes Agent** | ✅ Full support | `metadata.hermes` namespace, category: research |
| **[pi-mono](https://github.com/badlogic/pi-mono)** | ✅ Full support | `metadata.pimo` namespace |
| **[OpenAI Codex](https://openai.com/index/introducing-codex/)** | ✅ Full support | `agents/openai.yaml` sidecar with capabilities and prerequisites |
| **[SkillsMP](https://skillsmp.com/)** | ✅ Indexable | GitHub topics configured |

## Updating

The skill **auto-updates on invocation.** Every time a host LLM activates `scholar-deep-research` for a new research task, Phase 0 Step 0 runs `python scripts/check_update.py`, which:

1. `git fetch`es the upstream remote (the one network call) — typically a few hundred milliseconds
2. Fast-forwards the local checkout if an update is available
3. Refuses to touch your working tree if you have local edits — you'll see a one-line `[Skill update skipped — you have local changes …]` notice instead of having work clobbered
4. Detects `requirements.txt` drift and surfaces a hint; **pip install is never run automatically** (the skill doesn't know which Python / venv is yours)
5. Never fails the workflow — offline, no remote, or package-manager install all degrade silently to `check_failed` / `not_a_git_repo` and research proceeds with the current version

When an update is applied you'll see a single line in the chat, e.g. `[Skill updated: abc123 → def456 (3 commits). Continuing with new version.]`. The success envelope also carries a `what_changed` field listing the top 5 `feat:` / `fix:` commit subjects from the new range, so the host LLM can summarize "what's new" without you having to run `git log` yourself.

**Pinning a version.** If you want to hold a specific commit — for a paper submission, a reproducibility run, or while a downstream script is being validated — set:

```bash
export SCHOLAR_SKIP_UPDATE_CHECK=1
```

With that set, the auto-update check short-circuits and the skill runs exactly the version on disk until you unset the variable. You can also combine with a `git checkout <sha>` to pin a specific historical version.

**Manual update** (also works as a last resort):

```bash
cd ~/.claude/skills/scholar-deep-research   # or your install path
git pull --ff-only
pip install -r requirements.txt              # only if you see the deps-changed hint
```

Users installed through a package manager (ClawHub, SkillsMP, Hermes registry) should use that manager's own update command instead; `check_update.py` will detect the non-git install and stay out of its way.

## Reference

### Files

```
scholar-deep-research/
├── SKILL.md                       # Skill instructions (the only required file)
├── README.md / README_CN.md       # This file / 中文文档
├── requirements.txt               # httpx, pypdf
├── agents/
│   └── openai.yaml                # OpenAI Codex sidecar (interface, capabilities, prereqs)
├── scripts/
│   ├── _common.py                 # Envelope, schema, idempotency cache, search-result TTL cache
│   ├── _gates.py                  # G1..G7 gate predicates for phase advance
│   ├── _locking.py                # Atomic state writer (single-writer, exclusive lock)
│   ├── _pdf_fetch.py              # Shared PDF-fetch helper (paper-fetch + Unpaywall fallback)
│   ├── research_state.py          # Central state file management (init/ingest/advance/query/...)
│   ├── search_openalex.py         # OpenAlex (primary)
│   ├── search_arxiv.py            # arXiv preprints
│   ├── search_crossref.py         # Crossref REST
│   ├── search_pubmed.py           # NCBI E-utilities
│   ├── search_dblp.py             # DBLP — CS bibliography gold standard (no abstracts/citations)
│   ├── search_biorxiv.py          # bioRxiv/medRxiv preprints (via Europe PMC)
│   ├── search_exa.py              # Exa AI-powered search (optional, key-gated)
│   ├── dedupe_papers.py           # Cross-source deduplication
│   ├── rank_papers.py             # Transparent scoring
│   ├── resolve_id.py              # Read-only paper-ID canonicalizer (DOI/OpenAlex/arXiv/PMID)
│   ├── skim_papers.py             # Phase-3 tier triage (deep/skim/defer)
│   ├── prefetch_pdfs.py           # Pull deep-tier PDFs ahead of agent fan-out (concurrent)
│   ├── build_citation_graph.py    # Forward + backward snowball
│   ├── extract_pdf.py             # PDF extraction with DOI resolution (paper-fetch / Unpaywall)
│   ├── export_bibtex.py           # BibTeX / CSL-JSON / RIS
│   ├── check_update.py            # 24h-throttled fast-forward of the skill itself
│   └── tests/                     # 148-test smoke suite (stdlib only, no network)
├── references/                    # Progressive-disclosure resources (loaded on demand)
│   ├── search_strategies.md       # Boolean, PICO, snowballing, saturation
│   ├── source_selection.md        # Which database for which question
│   ├── quality_assessment.md      # CRAAP, tier, retraction, preprints
│   ├── report_templates.md        # Archetype selection guide
│   ├── pitfalls.md                # 14 failure modes with fixes
│   └── agent_prompts/
│       └── phase3_deep_read.md    # Per-paper prompt for parallel agent fan-out
└── assets/
    ├── templates/                 # Per-archetype report skeletons
    │   ├── literature_review.md
    │   ├── systematic_review.md
    │   ├── scoping_review.md
    │   ├── comparative_analysis.md
    │   └── grant_background.md
    └── prompts/
        └── self_critique.md       # 14-point Phase 6 checklist
```

> Only `SKILL.md` and `scripts/` are required for the skill to work. `references/` and `assets/` are progressive-disclosure resources the model loads on demand.

### Known Limitations

- **No Google Scholar / Web of Science / Scopus** — these have no public API or require institutional access. Mention in report appendix as "not consulted" if it matters.
- **Scanned PDFs** — `extract_pdf.py` detects them but doesn't OCR. Use a separate OCR step if needed.
- **DOI resolution requires open access** — `--doi` mode only finds legally open-access PDFs (via [paper-fetch](https://github.com/Agents365-ai/paper-fetch) or Unpaywall). Paywalled papers fall back to abstract-only.
- **arXiv has no citation counts** — arXiv-only papers get `citations=null` and a 0 contribution from the citation component of the rank score.
- **PubMed full abstracts** — fetched on demand only (`--with-abstracts`); the default round-trip uses esummary for speed.
- **English-language bias** — all sources index non-English work but search quality varies. Note in the report's limitations if the topic has substantial non-English literature.
- **Ranking is bag-of-words for relevance** — for semantic re-ranking, plug an embedding model and write the result back into `state.papers[*].score_components.relevance`. The pipeline is designed for that override.

## License

MIT

## Support

If this skill helps you, consider supporting the author:

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/wechat-pay.png" width="180" alt="WeChat Pay">
      <br>
      <b>WeChat Pay</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/alipay.png" width="180" alt="Alipay">
      <br>
      <b>Alipay</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/buymeacoffee.png" width="180" alt="Buy Me a Coffee">
      <br>
      <b>Buy Me a Coffee</b>
    </td>
  </tr>
</table>

## Author

**Agents365-ai**

- Bilibili: https://space.bilibili.com/441831884
- GitHub: https://github.com/Agents365-ai
