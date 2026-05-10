# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`scholar-deep-research` is an **Agent Skills package**, not a runnable application. Its purpose is to make *other* LLM sessions (Claude Code, OpenCode, OpenClaw, Codex, pi-mono, Hermes) perform a disciplined 8-phase (Phase 0..7) literature review. The repo ships three layers:

- **`SKILL.md`** — the instructions the host LLM reads when the skill activates. This is the primary "source code" of the skill's behavior. Editing it changes agent behavior immediately.
- **`scripts/`** — the deterministic Python spine. Search, dedupe, rank, citation-chase, PDF extract, bibliography export. Called from the host LLM via Bash; never imported as a library.
- **`references/` + `assets/`** — progressive-disclosure markdown the host LLM loads on demand (per-archetype report templates, self-critique checklist, pitfall catalog, quality-assessment rubrics).

There is no server, no package entry point, and no test suite. Everything is a CLI tool plus docs.

## Layout

The shipped skill lives under `skills/scholar-deep-research/` (mirrors the [`Agents365-ai/365-skills`](https://github.com/Agents365-ai/365-skills) plugin spec). All path references in this doc — `SKILL.md`, `scripts/`, `references/`, `assets/`, `requirements.txt` — are relative to that directory. `cd skills/scholar-deep-research` before running the commands below, or prepend the prefix.

`.github/workflows/sync-365-skills.yml` mirrors `skills/scholar-deep-research/` into `Agents365-ai/365-skills:plugins/scholar-deep-research/skills/scholar-deep-research/` on every push to `main`, and bumps the `version` field in `marketplace.json` from the `metadata.version` in `SKILL.md`.

## Pipeline at a glance

The 8-phase workflow (Phase 0..7) with its scripts, gates, and `research_state.json` as the single source of truth is diagrammed in `README.md` (and `README_CN.md`). When auditing a change, use that diagram to verify four invariants:

1. **Every phase writes to `research_state.json` through a dedicated `research_state.py` subcommand or the matching `apply_*` library function** — never by direct file edits. `save_state` is private (`_save_state`) and only reachable from inside the state lock via `_locked_rmw`. If you add a new phase output, add a subcommand + apply_ function; do not reach around the single-writer boundary.
2. **Phase gates are enforced code, not prose.** G1..G7 live in `scripts/_gates.py` as predicate functions; the agent advances one gate at a time via `python scripts/research_state.py --state <path> advance`, which refuses with a structured `gate_not_met` envelope when criteria aren't met. `set --field phase` is rejected — phase changes cannot bypass the gate path.
3. **Every mutating command is retry-idempotent by contract.** `--idempotency-key` accepted on `ingest`, `rank`, `dedupe`, `citation-chase`, `rank_papers.py`, `dedupe_papers.py`, `build_citation_graph.py`. Retried calls with the same key replay the cached response; signature mismatches return `idempotency_key_mismatch`, not stale data.
4. **MCP is a dashed side-input**, never on the critical path. If you find yourself drawing a solid arrow from MCP into a phase output, you have broken the "scripts are the spine, MCP is the skin" invariant.

## Common commands

```bash
# Install runtime deps (httpx, pypdf only)
pip install -r requirements.txt

# Every script self-describes — run this before assuming flags:
python scripts/<name>.py --schema       # machine-readable JSON schema (preferred)
python scripts/<name>.py --help         # human-readable

# Quick sanity check against the live workflow (no API keys needed):
python scripts/research_state.py --state /tmp/s.json init --question "test" --archetype literature_review
python scripts/search_openalex.py --query "transformer" --limit 5 --state /tmp/s.json
python scripts/research_state.py --state /tmp/s.json query papers

# Single-script dry runs for the expensive one:
python scripts/build_citation_graph.py --state /tmp/s.json --seed-top 3 --direction both --depth 1 --dry-run
```

A minimal CLI-contract smoke suite lives at `scripts/tests/` (stdlib only, no network):

```bash
python scripts/tests/run.py          # ~1-2 seconds, 16 tests
```

It covers: `--schema` on every public script, ingest idempotency and payload validation, export-format sentinels (catches the 0.3.0 `import json` NameError), gate pass/fail cases, and 20-way concurrent-ingest serialization through the state lock. Run it after any change under `scripts/`. For new scripts, add one more `subTest` in `test_schema.py` automatically — `all_script_names()` picks them up as long as they follow the standard `maybe_emit_schema` pattern.

Beyond the smoke suite there is no lint / typecheck target configured. For behavior not yet covered, verify by running the script end-to-end against a throwaway state file — the JSON envelope on stdout is the contract.

## The CLI contract (critical invariant)

Every script in `scripts/` obeys a strict agent-native contract defined in `scripts/_common.py`. This contract is a direct application of the **`agent-native-design` skill** (installed at `~/.claude/skills/agent-native-design/`) — when designing a new script, reviewing the interface, or refactoring an existing command, **invoke that skill first**. It is the source of the seven principles that shape `_common.py` and the 14-criterion rubric you should score any change against before shipping it. Any change that breaks this contract will silently break host LLMs that depend on it.

The repo currently scores 28/28 on the skill's rubric (status as of v0.5.0 — see release notes). The goal for any future change is: *do not regress this score*.

### The seven principles, as implemented in this repo

| # | Principle | How it's implemented here |
|---|-----------|---------------------------|
| **P0** | One CLI, three audiences | Default JSON envelope serves agents; `stdout_is_tty()` in `_common.py` flips `export_bibtex.py` to raw text for humans at a terminal; env-var config (`SCHOLAR_*`, `NCBI_API_KEY`) serves systems/orchestrators. |
| **P1** | Structured output is the interface | `ok()` / `err()` in `_common.py` are the ONLY emission paths. Success: `{ok: true, data, meta}`. Failure: `{ok: false, error: {code, message, retryable, ...}, meta}`. `meta` auto-populated with `request_id` / `latency_ms` / `cli_version` / `schema_version`. No `print()` / `json.dumps()` / `sys.exit()` anywhere else in `scripts/`. |
| **P2** | Trust is directional | `SETTABLE_FIELDS = {"archetype", "report_path"}` whitelist in `research_state.py` — phase is removed; every other collection field (papers, queries, themes, tensions, self_critique) is only mutable through its dedicated subcommand. Env vars (human-set) are higher-trust than CLI args (agent-set). |
| **P3** | The CLI must describe itself | `maybe_emit_schema()` is called pre-`parse_args()` in every script's `main()`, so `--schema` works even when required flags are missing. `research_state.py --schema` recurses into `subcommands`. Progressive: top-level → subcommand → schema. |
| **P4** | Safety through graduated visibility | `init --force` returns `confirmation_required` unless paired with `--dangerous`; the envelope lists what would be destroyed (paper count, query count, themes/tensions) so the host LLM cannot destroy state without explicitly acknowledging. `set_command_meta(..., tier="write", dangerous_if=...)` surfaces the tier in `--schema` for automated safety UIs. |
| **P5** | Validate at the boundary | `_validate_state_shape(state, path)` runs at every `load_state`; `_validate_ingest_payload(payload)` runs at the entry of `apply_ingest`. Downstream code assumes the shape. No internal re-validation. |
| **P6** | The schema is the source of truth | Schema drives: CLI subcommand layout (argparse), validation (`_validate_*` helpers), help text, `--schema` output, and the `exit_codes` vocabulary emitted with every schema response. Schema now carries `cli_version` at top level and per-subcommand `meta.{since, tier, dangerous_if}` so agents can detect drift against a cached schema. |
| **P7** | Authentication must be delegatable | Every env var is human/orchestrator-set. No `login` / `auth` / `token` subcommand the agent can invoke; `SCHOLAR_MAILTO` / `NCBI_API_KEY` land in the process env via the human's shell or supervisor. |

### The 14-criterion rubric scorecard

All 14 must stay at "pass" (2/2). Review any change against this table; do not ship a regression.

| Criterion | Evidence in this repo |
|-----------|-----------------------|
| Three-audience support (P0) | JSON by default; TTY fallback on `export_bibtex`; env-var config layer for orchestrators |
| Stdout contract (P1) | `ok` / `err` are the only emission paths; body-inline envelope even for `export_bibtex` when stdout is not a TTY |
| Stderr separation (P1) | Diagnostics (e.g. `_record_failure` in `build_citation_graph.py`) go to stderr; stdout stays envelope-only |
| Exit code semantics (P1/P2) | `EXIT_*` constants: 0 ok / 1 runtime / 2 upstream (retryable) / 3 validation / 4 state. Surfaced under `exit_codes` in every `--schema` output. |
| Self-description — help (P3) | `--help` at every level; `--schema` at every level; subparsers recurse in schema output |
| Schema introspection (P6) | `--schema` emits JSON; top-level includes `cli_version`; subcommands carry `meta.{since, tier}` so agents detect drift |
| Dry-run (P3/P4) | `--dry-run` on `rank_papers`, `dedupe_papers`, `build_citation_graph`, and the `rank` / `dedupe` / `citation-chase` replay subcommands; `advance --check-only` is the dry-run of the gate predicate |
| Idempotent retries (P1) | `--idempotency-key` on every mutating command; signature via `command_signature()` excludes `func` and callables to survive cross-process replay; `idempotency_with_dry_run` rejected at the boundary (`reject_dry_run_with_idempotency`) |
| Non-interactive operation (P0) | No `input()`, no `confirm`, no pagers anywhere in `scripts/`. `--dangerous` (on init) is the agent-compatible confirmation pattern |
| Safety tiers (P4) | `init --force --dangerous` paired-flag; destructive subcommands carry `meta.dangerous_if` in the schema |
| Boundary validation (P5) | `_validate_state_shape` on every load; `_validate_ingest_payload` at `apply_ingest`; `SETTABLE_FIELDS` whitelist on `set`; DOI normalization at ID-assignment boundary |
| Auth delegation (P7) | Env vars only; no login/token subcommand; agent inherits credentials from a boundary it did not build |
| Error recoverability (P1) | Every `err()` carries `code` + `message` + `retryable` + context fields. `gate_not_met` carries a `next: [commands]` hint via `_gates.next_hints_for()` so agents recover without a discovery round-trip |
| Trust boundary (P2) | Env vars (`SCHOLAR_*`, `NCBI_API_KEY`) are human/orchestrator-set; CLI args from the agent are validated at boundary; `SETTABLE_FIELDS` whitelist prevents escalation |

### Concrete implementation rules

1. **Use the helpers from `_common.py`** — `ok()`, `err()`, `UpstreamError`, `make_paper()`, `make_payload()`, `emit()`, `with_idempotency()`, `reject_dry_run_with_idempotency()`, `set_command_meta()`, `stdout_is_tty()`. Do not hand-roll `json.dumps` / `sys.exit`.
2. **Search scripts end with `emit(payload, args.output, args.state)`** — this routes through `apply_ingest()` (direct library call, no subprocess) when `--state` is given. Concurrent searches are serialized by the state lock.
3. **State writes only through `research_state.apply_*`** — `apply_ingest`, `apply_ranking`, `apply_dedupe`, `apply_citation_chase`. All four wrap `_locked_rmw` for atomic + exclusive-locked writes. `save_state` / `_save_state` are private and not reachable from other scripts.
4. **Idempotency for every mutating command** — wire through `with_idempotency(args, compute, signature_exclude=...)` or the lower-level `read_cache` / `write_cache` / `command_signature` helpers. Do not invent a second cache. If the command also has `--dry-run`, call `reject_dry_run_with_idempotency(args)` up front — caching a no-op is nonsense.
5. **Schema metadata on every new subcommand** — `set_command_meta(parser, since="X.Y.Z", tier="read|write")`; add `dangerous_if="..."` if paired-flag acknowledgement is required. This is what lets a cached-schema agent detect drift.
6. **Skill directory is read-only.** No script may modify the skill's own files. Updates flow through the marketplace (`/plugin update`), not through in-skill `git pull`.
7. **Gates live in `_gates.py`, advanced via `research_state.py advance`.** Each gate is a pure function `(state) -> GateResult` returning a `checks: [Check]` list. Add new gates only for new phases. Update the `_NEXT_HINTS` map in the same commit so gate-failure envelopes carry actionable `next:` suggestions.

**When adding a new script or changing an existing one**, invoke the `agent-native-design` skill and walk the 14-criterion rubric against your change. The smoke suite at `scripts/tests/run.py` pins the observable contract — `test_schema.py` iterates every script, so a new script that follows the `maybe_emit_schema` pattern is automatically covered. Adding a "just this once" prose warning to stdout or a bare `print` is a regression against the contract even if tests pass.

## Central state architecture

`research_state.json` is the single source of truth. All phases read and write it. The schema lives at the top of `scripts/research_state.py` and is versioned (`SCHEMA_VERSION`). `_validate_state_shape()` runs on every `load_state` — a state file from an unsupported `schema_version` returns `state_schema_mismatch` / exit 4 instead of silently loading with missing keys.

- Paper IDs are normalized in priority order: `doi:...` → `openalex:W...` → `arxiv:...` → `pmid:...`. Dedup logic in `dedupe_papers.py` depends on this ordering.
- `research_state.py` exposes subcommands: `init`, `ingest`, `select`, `saturation`, `set`, `advance`, `query`, `evidence`, `theme`, `tension`, `critique`, plus the replay subcommands `rank` / `dedupe` / `citation-chase`. Every mutation goes through one of these or through the matching `apply_*` library function — scripts no longer touch the state file directly. Writes are atomic + exclusive-locked via `_locked_rmw` so Phase 1 parallel search ingests are race-free.
- The `set` subcommand has a whitelist (`SETTABLE_FIELDS = {"archetype", "report_path"}`). `phase` is NOT in the whitelist — it's advanced only via `research_state.py advance`, which runs the `G1..G7` gate predicates in `_gates.py` and refuses with `gate_not_met` when criteria aren't met. Widening `SETTABLE_FIELDS` is a security decision.
- Every script is idempotent on the state file — re-running a search round merges new papers without duplicating, and `dedupe_papers.py` is safe to re-run. Additionally, every mutating command accepts `--idempotency-key` for contract-level retry safety.

## Idempotency cache

**Every mutating command** accepts `--idempotency-key <k>`: `research_state.py ingest` / `rank` / `dedupe` / `citation-chase`, `rank_papers.py`, `dedupe_papers.py`, `build_citation_graph.py`. On first success, `{response, signature}` is written to `${SCHOLAR_CACHE_DIR:-.scholar_cache}/<sha256>.json`. Retries with the same key replay the cached response; the same key with *different* semantic arguments returns `idempotency_key_mismatch` rather than silently serving stale data. The signature computation (`command_signature()` in `_common.py`) excludes `idempotency_key`, `dry_run`, `schema`, `func`, and any other callable from the hash — if you add new "doesn't affect output" flags, exclude them too. Combining `--idempotency-key` with `--dry-run` is rejected at the boundary by `reject_dry_run_with_idempotency()` — a dry run doesn't mutate and there's nothing to cache.

Most new mutating commands should use the `with_idempotency(args, compute, signature_exclude=...)` wrapper — it handles cache hit / miss / mismatch in one call so the command doesn't re-implement the 30-line boilerplate. Only `build_citation_graph.py` keeps a custom flow (it needs to short-circuit before the state read on cache hit).

## MCP tools are enrichment, never dependency

The workflow is designed to run offline-first on stdlib HTTP. Semantic Scholar (`mcp__asta__*`) and Brave Search MCP tools are enrichment — if they time out or the server is unreachable, the phase continues. **Never place a phase-critical step behind an MCP call.** Scripts are the spine; MCP is the skin. This is called out in SKILL.md and must stay true when adding new capabilities.

## Environment variables (trust-boundary config)

Set by the human or orchestrator, never by the agent itself:

| Variable | Used by | Purpose |
|----------|---------|---------|
| `SCHOLAR_STATE_PATH` | every script with `--state` | Default state path |
| `SCHOLAR_MAILTO` | OpenAlex / Crossref / citation graph | Polite-pool email for higher rate limits |
| `NCBI_API_KEY` | PubMed | NCBI E-utilities rate limit |
| `SCHOLAR_CACHE_DIR` | idempotency cache | Default `.scholar_cache/` in cwd |

CLI flags override env vars where both are present.

## Multi-platform sidecars

The skill runs unmodified across platforms because the frontmatter in `SKILL.md` carries namespaced metadata for each host:

- `metadata.openclaw` — dependency gating (`requires.bins`), emoji
- `metadata.hermes` — tags + category for Hermes Agent
- `metadata.pimo` — pi-mono tags

When editing the frontmatter, remember the OpenClaw parser only supports **single-line** frontmatter keys — do not split the `metadata` object across lines.

## README conventions

Per the workspace `CLAUDE.md` at `~/myagents/myskills/CLAUDE.md`, published skills use:
- `README.md` — Chinese is the default, but this repo ships English as `README.md` and Chinese as `README_CN.md` (inverted vs the workspace default — keep both in sync).
- GitHub topics required for SkillsMP indexing: `claude-code`, `claude-code-skill`, `claude-skills`, `agent-skills`, `skillsmp`, `openclaw`, `skill-md`.

## When modifying behavior, edit in this order

1. **SKILL.md** first if you're changing the workflow, phase definitions, or completion gates. The LLM reads this — scripts only execute what it orchestrates.
2. **`scripts/_common.py`** if you're changing the envelope, exit codes, cache semantics, or schema introspection. Every script depends on it. Before touching it, **invoke the `agent-native-design` skill** and score the proposed change against its 14-criterion rubric — `_common.py` *is* that rubric crystallized in code, so regressions here propagate to every script at once.
3. Individual script files for new data sources or ranking tweaks. Preserve the CLI contract (all seven points above). New expensive commands reuse the idempotency cache from `_common.py`; new error classes use `err()` with a snake_case `code`, not `raise` with a prose message.
4. `references/` / `assets/` for new archetypes, templates, or the self-critique checklist. These are loaded on demand by the host LLM, so updates take effect without code changes.
