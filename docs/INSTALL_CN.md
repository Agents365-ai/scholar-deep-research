# 安装

[English](INSTALL.md) · [← 返回 README](../README_CN.md)

## 前置条件

- **Python ≥ 3.9**
- 安装后在安装目录执行 `pip install -r requirements.txt` — 仅引入 `httpx`（HTTP 客户端）与 `pypdf`（PDF 文本提取）。
- 可选：`pip install docling` 启用版面感知的 markdown PDF 提取（带 OCR）。pypdf 输出像扫描件/过于稀疏时自动升级到 docling 兜底。

无需 API key。如需更高的 OpenAlex / Crossref / PubMed 限流配额，可设置 `SCHOLAR_MAILTO=<你@主机>`（礼貌池）和/或 `NCBI_API_KEY=<key>`。所有脚本不带这些参数也能正常工作。

## 通过 marketplace 安装

```bash
# 任意 agent（Claude Code、Cursor、Copilot 等）
npx skills add Agents365-ai/365-skills -g

# 仅 Claude Code
> /plugin marketplace add Agents365-ai/365-skills
> /plugin install scholar-deep-research
```

也已发布到 [SkillsMP](https://skillsmp.com/) 与 [ClawHub](https://clawhub.ai/)，各自的市场负责升级。

## 手动安装（直接 git clone）

```bash
git clone https://github.com/Agents365-ai/scholar-deep-research.git
ln -s "$PWD/scholar-deep-research/skills/scholar-deep-research" ~/.claude/skills/scholar-deep-research
pip install -r ~/.claude/skills/scholar-deep-research/requirements.txt
```

将 `~/.claude/skills/` 替换为对应宿主平台的 skills 路径：

| 宿主 | Skills 目录 |
|---|---|
| Claude Code | `~/.claude/skills/` |
| OpenCode | `~/.config/opencode/skills/` |
| OpenClaw / ClawHub | `~/.openclaw/skills/` |
| Hermes Agent | `~/.hermes/skills/research/` |
| pi-mono | `~/.pimo/skills/` |
| 通用（skillsmp 等） | `~/.agents/skills/` |

## 环境变量

| 变量 | 谁在用 | 用途 |
|----------|---------|---------|
| `SCHOLAR_MAILTO` | OpenAlex / Crossref / 引用图 | 礼貌池邮箱，换更高限流 |
| `NCBI_API_KEY` | PubMed | NCBI E-utilities 限流提升 |
| `SCHOLAR_STATE_PATH` | 所有带 `--state` 的脚本 | 默认 state 路径 |
| `SCHOLAR_CACHE_DIR` | 幂等缓存 + 限流缓存 | 默认当前目录下 `.scholar_cache/` |
| `SCHOLAR_SATURATION_NEW_PCT` | Phase 1 饱和度门控 | 默认 50% — 系统综述严格场景可设为 20 |
| `EXA_API_KEY` | `search_exa.py` | 可选开放网检索 |
