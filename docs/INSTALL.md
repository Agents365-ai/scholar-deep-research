# Install

[中文](INSTALL_CN.md) · [← back to README](../README.md)

## Prerequisites

- **Python ≥ 3.9**
- After install, `pip install -r requirements.txt` in the install dir — pulls in `httpx` (HTTP client) and `pypdf` (PDF text extraction).
- Optional: `pip install docling` for layout-aware markdown PDF extraction with OCR. Auto-used as a fallback when `pypdf` output looks scanned/sparse.

No API keys required. For higher OpenAlex / Crossref / PubMed rate limits, set `SCHOLAR_MAILTO=<you@host>` (polite pool) and / or `NCBI_API_KEY=<key>`. All scripts work without them.

## Install via marketplace

```bash
# Any agent (Claude Code, Cursor, Copilot, etc.)
npx skills add Agents365-ai/365-skills -g

# Claude Code only
> /plugin marketplace add Agents365-ai/365-skills
> /plugin install scholar-deep-research
```

Also published on [SkillsMP](https://skillsmp.com/) and [ClawHub](https://clawhub.ai/) — each handles updates through its own marketplace.

## Manual install (direct git clone)

```bash
git clone https://github.com/Agents365-ai/scholar-deep-research.git
ln -s "$PWD/scholar-deep-research/skills/scholar-deep-research" ~/.claude/skills/scholar-deep-research
pip install -r ~/.claude/skills/scholar-deep-research/requirements.txt
```

Replace `~/.claude/skills/` with the path appropriate for your host:

| Host | Skills directory |
|---|---|
| Claude Code | `~/.claude/skills/` |
| OpenCode | `~/.config/opencode/skills/` |
| OpenClaw / ClawHub | `~/.openclaw/skills/` |
| Hermes Agent | `~/.hermes/skills/research/` |
| pi-mono | `~/.pimo/skills/` |
| Generic (skillsmp etc.) | `~/.agents/skills/` |

## Environment variables

| Variable | Used by | Purpose |
|----------|---------|---------|
| `SCHOLAR_MAILTO` | OpenAlex / Crossref / citation graph | Polite-pool email for higher rate limits |
| `NCBI_API_KEY` | PubMed | NCBI E-utilities rate limit boost |
| `SCHOLAR_STATE_PATH` | every script with `--state` | Default state path |
| `SCHOLAR_CACHE_DIR` | idempotency + rate limiter cache | Default `.scholar_cache/` in cwd |
| `SCHOLAR_SATURATION_NEW_PCT` | Phase 1 saturation gate | Default 50% — set to 20 for systematic-review rigor |
| `EXA_API_KEY` | `search_exa.py` | Optional open-web search |
