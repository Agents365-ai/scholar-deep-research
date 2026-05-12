# scholar-deep-research — From Question to Cited Report

[中文文档](README_CN.md) · 🌐 **Website:** [agents365-ai.github.io/scholar-deep-research](https://agents365-ai.github.io/scholar-deep-research/)

An 8-phase (Phase 0..7), script-driven academic research workflow that turns a research question into a structured, cited report. Multi-source federation across 7 databases, mandatory self-critique, parallel deep-read agent fan-out, dual-backend citation chasing.

**Zero LLM calls inside the pipeline.** Every script under `scripts/` is pure data — search, dedupe, rank, citation-chase, bibliography export. The host LLM orchestrates from outside via JSON envelopes on stdout. That separation buys reproducibility, auditability, and a 330-test smoke suite that runs in ~12 s with no API keys.

Works with Claude Code, Cursor, Codex, OpenCode, OpenClaw / ClawHub, Hermes Agent, pi-mono, and SkillsMP — any agent that supports the [Agent Skills](https://agentskills.io) format.

## What it does

| Capability | Detail |
|---|---|
| Phase 0..7 cited-report pipeline | 7 enforced phase-transition gates (G1..G7 in `_gates.py`); no way to skip a gate by setting `phase` directly |
| 7 federated sources | OpenAlex, arXiv, Crossref, PubMed, DBLP, bioRxiv (all free, no key); Exa (opt-in via `EXA_API_KEY`) |
| Cross-source deduplication | DOI-first, title-similarity fallback; one paper, one record |
| Three-axis saturation | paper / author / venue novelty all must drop below threshold for Phase 1 to terminate |
| Parallel deep-read fan-out | Selected papers split into `deep` / `skim` / `defer`; deep tier dispatched as 8–10 isolated-context agents per wave |
| Transparent ranking | Published formula `α·relevance + β·citations + γ·recency + δ·venue_prior`, components written into state |
| Mandatory Phase 6 self-critique | 14-point adversarial checklist; findings ship in report appendix |
| Citation rigor | Every claim carries a `[^id]` anchor; unanchored prose fails the gate |
| 5 archetype templates | `literature_review` / `systematic_review` / `scoping_review` / `comparative_analysis` / `grant_background` |
| BibTeX / CSL-JSON / RIS export | Bibliography generated from state, never retyped |
| Markdown report + agent-rendered HTML | Pipeline outputs `reports/<slug>_<YYYYMMDD>.md` + `.bib`; hand it to your coding agent for a polished HTML delivery page |

## How it works (1-line per phase)

```
Phase 0  Scope        question decomposition + archetype + state init
Phase 1  Discovery    multi-source search → dedupe → 3-axis saturation check
Phase 2  Triage       ranking → top-N selection → tier triage → optional PDF prefetch
Phase 3  Deep read    parallel agent fan-out (deep tier) + abstract stub (skim tier)
Phase 4  Chasing      citation graph (forward + backward, OpenAlex + S2)
Phase 5  Synthesis    thematic clustering → tension map
Phase 6  Self-critique  14-point adversarial checklist (mandatory)
Phase 7  Report       render archetype template → export bibliography
```

Full diagram + Mermaid flowchart + gate semantics in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quick Start

```bash
# Any agent
npx skills add Agents365-ai/365-skills -g

# Claude Code only
> /plugin marketplace add Agents365-ai/365-skills
> /plugin install scholar-deep-research
```

Then `pip install -r requirements.txt` inside the install dir. Full instructions in [docs/INSTALL.md](docs/INSTALL.md).

Once installed, just describe what you want:

```
Run a deep research report on CRISPR base editing for Duchenne muscular dystrophy.
```

The skill walks the 8 phases automatically and writes the report to `reports/<slug>_<YYYYMMDD>.md` with a matching `.bib`. See [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md) for a complete example.

## Documentation

| Doc | What's inside |
|---|---|
| [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md) | Concrete CRISPR-base-editing run, phase by phase |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 8 phases, gates, state model, idempotency, CLI contract, MCP/WebFetch boundary |
| [docs/COMPARISON.md](docs/COMPARISON.md) | Side-by-side capability table vs. native agents |
| [docs/INSTALL.md](docs/INSTALL.md) | Plugin marketplace, manual clone, multi-platform paths, env vars |
| [docs/LIMITATIONS.md](docs/LIMITATIONS.md) | Coverage caveats, citation-count gaps, language bias, saturation semantics |
| [skills/scholar-deep-research/SKILL.md](skills/scholar-deep-research/SKILL.md) | The workflow guide the host LLM reads |

## Community

Join us for help, Q&A, and updates:

- **Discord:** [discord.gg/pCV3P9hNY](https://discord.gg/pCV3P9hNY)
- **WeChat:** scan the QR code below

<p align="center">
  <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/agents365ai_wechat_1.png" width="200" alt="WeChat Community Group">
</p>

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
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="Give a Reward">
      <br>
      <b>Give a Reward</b>
    </td>
  </tr>
</table>

## Author

**Agents365-ai**

- Bilibili: https://space.bilibili.com/441831884
- GitHub: https://github.com/Agents365-ai

## License

MIT
