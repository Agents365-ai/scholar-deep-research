# scholar-deep-research — From Question to Cited Report

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/scholar-deep-research?style=flat&logo=github)](https://github.com/Agents365-ai/scholar-deep-research/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/scholar-deep-research?style=flat&logo=github)](https://github.com/Agents365-ai/scholar-deep-research/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/scholar-deep-research?logo=github)](https://github.com/Agents365-ai/scholar-deep-research/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/scholar-deep-research?logo=github)](https://github.com/Agents365-ai/scholar-deep-research/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com/skills/agents365-ai-scholar-deep-research-skills-scholar-deep-research-skill-md)
[![ClawHub](https://img.shields.io/badge/ClawHub-listed-ff6b35)](https://clawhub.ai/agents365-ai/scholar-deep-research-pro-skill)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white)](https://discord.gg/79JF5Atuk)

**English** · [中文](README_CN.md) · [📖 Online Docs](https://agents365-ai.github.io/scholar-deep-research/)

Ask an LLM to "write a literature review on X" and you get three failure modes: citations that don't exist, the canonical paper missing because the search ran once and stopped, and no record of *why* any paper made the cut. `scholar-deep-research` fixes those by running an 8-phase (Phase 0..7), script-driven workflow with enforced citation anchoring, multi-round saturation gating, and a per-paper audit trail.

**Zero LLM calls inside the pipeline.** Every script under `scripts/` is pure data — search, dedupe, rank, citation-chase, bibliography export. The host LLM orchestrates from outside via JSON envelopes on stdout. That separation buys reproducibility, auditability, and a 343-test smoke suite that runs in ~13 s with no API keys.

Works with Claude Code, Cursor, Codex, OpenCode, OpenClaw / ClawHub, Hermes Agent, pi-mono, and SkillsMP — any agent that supports the [Agent Skills](https://agentskills.io) format.

## See it in action

Three end-to-end runs committed verbatim with full audit trail (state, evidence, report, BibTeX, run notes):

- **[GLP-1 for Non-Diabetic Obesity](examples/glp1-obesity-systematic-review/)** — `systematic_review`, 833 papers, 5 deep reads, 12-citation report on efficacy / safety / discontinuation.
- **[Mamba vs Transformer for Long Context](examples/mamba-vs-transformer-comparative/)** — `comparative_analysis`, 1005 papers, 3 deep reads (Mamba, Jamba, xLSTM), 5-axis verdict.
- **[AAV Capsids for CNS Gene Therapy](examples/aav-capsid-cns-grant-background/)** — `grant_background`, 681 papers, 4 mechanistic deep reads (LY6A, CAP-B10, single-residue BBB, LRP6).

## What's different from "just ask the LLM"

| | Native agent | This skill |
|---|---|---|
| Search coverage | One source per turn | 7 federated sources, multi-round with saturation gate |
| Citation rigor | Claims float, citations sometimes fabricated | Every claim needs `[^id]` anchor; gate rejects unanchored prose |
| Audit trail | None | Per-paper score components, evidence, source provenance in `research_state.json` |
| Self-critique | None | Mandatory 14-point adversarial checklist (Phase 6) before report ships |
| Report shape | Generic outline | 5 archetypes (`literature_review` / `systematic_review` / `scoping_review` / `comparative_analysis` / `grant_background`) |

Full feature matrix in [docs/COMPARISON.md](docs/COMPARISON.md).

## How it works (1-line per phase)

```
Phase 0  Scope        question decomposition + archetype + state init
Phase 1  Discovery    multi-source search → dedupe → multi-axis saturation check
Phase 2  Triage       ranking → top-N selection → tier triage → optional PDF prefetch
Phase 3  Deep read    parallel agent fan-out (deep tier) + abstract stub (skim tier)
Phase 4  Chasing      citation graph (forward + backward, OpenAlex + S2)
Phase 5  Synthesis    thematic clustering → tension map
Phase 6  Self-critique  14-point adversarial checklist (mandatory)
Phase 7  Report       render archetype template → export bibliography
```

Full diagram, gate semantics, and state model in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quick Start

```bash
# Any agent
npx skills add Agents365-ai/365-skills -g

# Claude Code only
> /plugin marketplace add Agents365-ai/365-skills
> /plugin install scholar-deep-research
```

Then `pip install -r requirements.txt` inside the install dir.

Once installed, just describe what you want:

```
Run a deep research report on CRISPR base editing for Duchenne muscular dystrophy.
```

The skill walks the 8 phases automatically and writes the report to
`reports/<slug>_<YYYYMMDD>.md` with a matching `.bib`. Full install details in
[docs/INSTALL.md](docs/INSTALL.md); phase-by-phase walkthrough in
[docs/WALKTHROUGH.md](docs/WALKTHROUGH.md).

## What this *doesn't* do

- **No Google Scholar / Web of Science / Scopus** — no public API; cite as "not consulted" in the report appendix if your topic needs them.
- **No automatic full-text for paywalled papers** — open-access only; gated papers fall back to landing-page abstracts.
- **No semantic re-ranking out of the box** — relevance is bag-of-words; plug an embedding model into `state.papers[*].score_components.relevance` if you need it.
- **Saturation is novelty-based, not exhaustiveness-based** — catches "exploration has stalled", not "every relevant paper found". Use `systematic_review` + `SCHOLAR_SATURATION_NEW_PCT=20` for stricter coverage.

Full list in [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## Documentation

| Doc | What's inside |
|---|---|
| [WALKTHROUGH](docs/WALKTHROUGH.md) | Concrete CRISPR-base-editing run, phase by phase |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | 8 phases, gates, state model, idempotency, CLI contract, MCP boundary |
| [COMPARISON](docs/COMPARISON.md) | Full side-by-side capability table vs. native agents |
| [COMPETITORS](docs/COMPETITORS.md) | Matrix vs other open-source deep research tools (GPT-Researcher, STORM, open_deep_research, ARS) |
| [INSTALL](docs/INSTALL.md) | Plugin marketplace, manual clone, multi-platform paths, env vars |
| [LIMITATIONS](docs/LIMITATIONS.md) | Coverage caveats, citation-count gaps, language bias |

## 🔗 Related Skills

Pick the right tool for the research workflow you're running:

| Skill | Niche | When to use |
|---|---|---|
| [semanticscholar-skill](https://github.com/Agents365-ai/semanticscholar-skill) | Semantic Scholar API search | When you want a quick search, not a full structured review |
| [asta-skill](https://github.com/Agents365-ai/asta-skill) | Same corpus via Ai2 Asta MCP | When your host supports MCP and you have an Asta API key |
| [paper-fetch](https://github.com/Agents365-ai/paper-fetch) | DOI → PDF, 7-source fallback | When you have IDs and need the actual full text |
| [zotero-research-assistant](https://github.com/Agents365-ai/zotero-research-assistant) | Zotero library workflows | When references go into Zotero |

## 💬 Community

- **Discord:** https://discord.gg/79JF5Atuk
- **WeChat:** scan the QR code below

<p align="center">
  <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/agents365ai_wechat_1.png" width="200" alt="WeChat Community Group">
</p>

## ❤️ Support

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
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="Give a Reward">
      <br>
      <b>Give a Reward</b>
    </td>
  </tr>
</table>

## 👤 Author

**Agents365-ai**

- GitHub: https://github.com/Agents365-ai
- Bilibili: https://space.bilibili.com/441831884

## 📄 License

[MIT](LICENSE)
