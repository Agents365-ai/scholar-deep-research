# scholar-deep-research — 从问题到带引用的研究报告

[English](README.md) · 🌐 **官网:** [agents365-ai.github.io/scholar-deep-research/zh.html](https://agents365-ai.github.io/scholar-deep-research/zh.html)

8 阶段（Phase 0..7）、脚本驱动的学术研究工作流，将研究问题转化为结构化、带引用的研究报告。跨 7 个数据库联邦检索，强制自我批判，Phase 3 并行精读派发，Phase 4 双 backend（OpenAlex + Semantic Scholar）引用追溯。

**流水线内部不含任何 LLM 调用**。`scripts/` 下每个脚本都是纯数据处理 — 检索、去重、排序、追引、参考文献导出。宿主 LLM 在外部通过 stdout 的 JSON 信封编排。这种分工换来可复现性、可审计性，以及一套 330 项的冒烟测试，约 12 秒跑完，无需 API key。

支持 Claude Code、Cursor、Codex、OpenCode、OpenClaw / ClawHub、Hermes Agent、pi-mono、SkillsMP — 任何兼容 [Agent Skills](https://agentskills.io) 格式的 agent。

## 能力概览

| 能力 | 细节 |
|---|---|
| Phase 0..7 带引用报告流水线 | 7 道强制阶段跃迁门控（`_gates.py` 中的 G1..G7），无法通过直接设置 `phase` 跳过 |
| 7 个联邦数据源 | OpenAlex、arXiv、Crossref、PubMed、DBLP、bioRxiv（全部免费、无 key）；Exa（可选，需 `EXA_API_KEY`） |
| 跨源去重 | DOI 优先、标题相似度兜底；一篇论文一条记录 |
| 三轴饱和度 | 论文 / 作者 / 期刊新增率必须**同时**低于阈值才结束 Phase 1 |
| 并行精读派发 | 选中论文切成 `deep` / `skim` / `defer` 三档；deep 档每波 8–10 个独立上下文 agent 派发 |
| 透明排序 | 公开公式 `α·相关性 + β·引用 + γ·时效 + δ·期刊先验`，各分量写入 state |
| 强制 Phase 6 自我批判 | 14 项对抗性检查清单，发现写入报告附录 |
| 引用严谨 | 每条非平凡论断必须带 `[^id]` 锚点，无锚点不通过门控 |
| 5 种报告原型 | `literature_review` / `systematic_review` / `scoping_review` / `comparative_analysis` / `grant_background` |
| BibTeX / CSL-JSON / RIS 导出 | 参考文献从 state 生成，无需重打 |
| Markdown 报告 + Agent 渲染 HTML | pipeline 产物 `reports/<slug>_<YYYYMMDD>.md` + `.bib`；HTML 交付页面交由宿主 coding agent 按需渲染 |

## 工作流（每阶段一句话）

```
Phase 0  Scope        问题拆解 + 原型选择 + 状态初始化
Phase 1  Discovery    多源检索 → 去重 → 三轴饱和度检查
Phase 2  Triage       排序 → top-N 选择 → 分档 triage → 可选 PDF 预取
Phase 3  Deep read    deep 档并行 agent 派发 + skim 档摘要证据片段
Phase 4  Chasing      引用网络（正向 + 反向，OpenAlex + S2 双后端）
Phase 5  Synthesis    主题聚类 → 张力图谱
Phase 6  Self-critique  14 项对抗性检查清单（强制）
Phase 7  Report       渲染原型模板 → 导出参考文献
```

完整图示 + Mermaid 流程图 + 门控语义见 [docs/ARCHITECTURE_CN.md](docs/ARCHITECTURE_CN.md)。

## 快速开始

```bash
# 任意 agent
npx skills add Agents365-ai/365-skills -g

# 仅 Claude Code
> /plugin marketplace add Agents365-ai/365-skills
> /plugin install scholar-deep-research
```

随后在安装目录执行 `pip install -r requirements.txt`。完整说明见 [docs/INSTALL_CN.md](docs/INSTALL_CN.md)。

装完后直接描述你要的：

```
帮我做一份关于 CRISPR 碱基编辑治疗杜氏肌营养不良的深度研究报告。
```

skill 自动走完 8 个阶段，把报告写到 `reports/<slug>_<YYYYMMDD>.md` 并附带同名 `.bib`。完整示例见 [docs/WALKTHROUGH_CN.md](docs/WALKTHROUGH_CN.md)。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/WALKTHROUGH_CN.md](docs/WALKTHROUGH_CN.md) | 完整 CRISPR 碱基编辑示例，逐阶段展示 |
| [docs/ARCHITECTURE_CN.md](docs/ARCHITECTURE_CN.md) | 8 阶段、门控、状态模型、幂等、CLI 契约、MCP/WebFetch 边界 |
| [docs/COMPARISON_CN.md](docs/COMPARISON_CN.md) | 与原生 agent 对比能力表 |
| [docs/INSTALL_CN.md](docs/INSTALL_CN.md) | 插件市场、手动 clone、跨平台路径、环境变量 |
| [docs/LIMITATIONS_CN.md](docs/LIMITATIONS_CN.md) | 覆盖范围、引用计数缺口、语言偏倚、饱和度语义 |
| [skills/scholar-deep-research/SKILL.md](skills/scholar-deep-research/SKILL.md) | 宿主 LLM 读的工作流指引 |
| [examples/](examples/) | 完整审计轨迹的端到端实例:**GLP-1 系统综述**(生物医学,833 篇)、**Mamba vs Transformer 对比分析**(CS,1005 篇)、**AAV 衣壳工程脑递送基金背景**(生物医学,681 篇,4 篇精读,lint 通过) |

## 社群

- **Discord:** [discord.gg/pCV3P9hNY](https://discord.gg/pCV3P9hNY)
- **微信交流群:** 扫描下方二维码

<p align="center">
  <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/agents365ai_wechat_1.png" width="200" alt="微信交流群">
</p>

## 支持作者

如果这个 skill 对你有帮助，欢迎请作者喝杯咖啡：

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/wechat-pay.png" width="180" alt="微信支付">
      <br>
      <b>微信支付</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/alipay.png" width="180" alt="支付宝">
      <br>
      <b>支付宝</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/buymeacoffee.png" width="180" alt="Buy Me a Coffee">
      <br>
      <b>Buy Me a Coffee</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="给个鼓励">
      <br>
      <b>给个鼓励</b>
    </td>
  </tr>
</table>

## 作者

**Agents365-ai**

- Bilibili: https://space.bilibili.com/441831884
- GitHub: https://github.com/Agents365-ai

## 许可证

MIT
