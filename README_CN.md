# scholar-deep-research — 从问题到带引用的研究报告

[English](README.md) · 🌐 **官网:** [agents365-ai.github.io/scholar-deep-research/zh.html](https://agents365-ai.github.io/scholar-deep-research/zh.html)

让 LLM "帮我写一份 X 领域的综述",你会撞到三种失败:引用瞎编、跑一轮就停所以遗漏领域里的标志性论文、报告里没有任何记录解释"为什么选这些论文"。`scholar-deep-research` 用 8 阶段(Phase 0..7)、脚本驱动的工作流修这三件事 —— 强制引文锚点、多轮饱和度门控、每篇论文都有完整审计轨迹。

**流水线内部不含任何 LLM 调用**。`scripts/` 下每个脚本都是纯数据处理 —— 检索、去重、排序、追引、参考文献导出。宿主 LLM 在外部通过 stdout 的 JSON 信封编排。这种分工换来可复现性、可审计性,以及一套 343 项的冒烟测试,约 13 秒跑完,无需 API key。

支持 Claude Code、Cursor、Codex、OpenCode、OpenClaw / ClawHub、Hermes Agent、pi-mono、SkillsMP —— 任何兼容 [Agent Skills](https://agentskills.io) 格式的 agent。

## 实例展示

三次端到端真实跑都原样提交进仓库,带完整审计轨迹(state、证据文件、报告、BibTeX、记录摩擦点的 run notes):

- **[GLP-1 用于非糖尿病肥胖治疗](examples/glp1-obesity-systematic-review/)** —— `systematic_review`,833 篇文献,5 篇精读,围绕疗效/安全性/停药的 12-引用报告。
- **[Mamba vs Transformer 长上下文对比](examples/mamba-vs-transformer-comparative/)** —— `comparative_analysis`,1005 篇文献,3 篇精读(Mamba、Jamba、xLSTM),5 个维度对比 + 结论。
- **[AAV 衣壳工程用于脑内基因递送](examples/aav-capsid-cns-grant-background/)** —— `grant_background`,681 篇文献,4 篇机制论文精读(LY6A、CAP-B10、Q588T 单残基、LRP6)。

## 跟"直接问 LLM"有什么不同

| | 原生 agent | 本 skill |
|---|---|---|
| 检索覆盖 | 一轮一个源 | 7 源联邦,多轮 + 饱和度门控 |
| 引文严谨度 | 论断游荡,引文有时瞎编 | 每条论断必须带 `[^id]` 锚点;无锚点不通过门控 |
| 审计轨迹 | 无 | 每篇论文的打分分量、证据、来源源信都写进 `research_state.json` |
| 自我批判 | 无 | 报告出炉前强制走 14 项对抗性检查清单(Phase 6) |
| 报告形态 | 通用大纲 | 5 种原型(`literature_review` / `systematic_review` / `scoping_review` / `comparative_analysis` / `grant_background`) |

完整能力对比见 [docs/COMPARISON_CN.md](docs/COMPARISON_CN.md)。

## 工作流(每阶段一句话)

```
Phase 0  Scope        问题拆解 + 原型选择 + 状态初始化
Phase 1  Discovery    多源检索 → 去重 → 多轴饱和度检查
Phase 2  Triage       排序 → top-N 选择 → 分档 triage → 可选 PDF 预取
Phase 3  Deep read    deep 档并行 agent 派发 + skim 档摘要证据片段
Phase 4  Chasing      引用网络(正向 + 反向,OpenAlex + S2 双后端)
Phase 5  Synthesis    主题聚类 → 张力图谱
Phase 6  Self-critique  14 项对抗性检查清单(强制)
Phase 7  Report       渲染原型模板 → 导出参考文献
```

完整图示、Mermaid 流程图、门控语义见 [docs/ARCHITECTURE_CN.md](docs/ARCHITECTURE_CN.md)。

## 快速开始

```bash
# 任意 agent
npx skills add Agents365-ai/365-skills -g

# 仅 Claude Code
> /plugin marketplace add Agents365-ai/365-skills
> /plugin install scholar-deep-research
```

随后在安装目录执行 `pip install -r requirements.txt`。

装完后直接描述你要的:

```
帮我做一份关于 CRISPR 碱基编辑治疗杜氏肌营养不良的深度研究报告。
```

skill 自动走完 8 个阶段,把报告写到 `reports/<slug>_<YYYYMMDD>.md` 并附带同名 `.bib`。完整安装说明见 [docs/INSTALL_CN.md](docs/INSTALL_CN.md);逐阶段示例见 [docs/WALKTHROUGH_CN.md](docs/WALKTHROUGH_CN.md)。

## 它**不**做什么

- **不查 Google Scholar / Web of Science / Scopus** —— 没有公开 API;如果你的主题需要,在报告附录里标注"未查询"。
- **不自动获取付费墙后的全文** —— 只走开放获取;闭源论文回退到 landing page 摘要。
- **开箱不带语义重排序** —— 相关性是词袋打分;如果需要,把 embedding 模型的结果写回 `state.papers[*].score_components.relevance`,流水线为此设计。
- **饱和度是基于新增率,不是基于穷尽** —— 它能判断"探索停滞了",但不能判断"所有相关论文都找齐了"。需要更严格的覆盖用 `systematic_review` + `SCHOLAR_SATURATION_NEW_PCT=20`。

完整清单见 [docs/LIMITATIONS_CN.md](docs/LIMITATIONS_CN.md)。

## 文档

| 文档 | 内容 |
|---|---|
| [WALKTHROUGH](docs/WALKTHROUGH_CN.md) | 完整 CRISPR 碱基编辑示例,逐阶段展示 |
| [ARCHITECTURE](docs/ARCHITECTURE_CN.md) | 8 阶段、门控、状态模型、幂等、CLI 契约、MCP/WebFetch 边界 |
| [COMPARISON](docs/COMPARISON_CN.md) | 与原生 agent 对比的完整能力表 |
| [COMPETITORS](docs/COMPETITORS_CN.md) | 与其它开源 deep research 工具的对比矩阵(GPT-Researcher、STORM、open_deep_research、ARS) |
| [INSTALL](docs/INSTALL_CN.md) | 插件市场、手动 clone、跨平台路径、环境变量 |
| [LIMITATIONS](docs/LIMITATIONS_CN.md) | 覆盖范围、引用计数缺口、语言偏倚 |

## 社群

- **Discord:** [discord.gg/pCV3P9hNY](https://discord.gg/pCV3P9hNY)
- **微信交流群:** 扫描下方二维码

<p align="center">
  <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/agents365ai_wechat_1.png" width="200" alt="微信交流群">
</p>

## 支持作者

如果这个 skill 对你有帮助,欢迎请作者喝杯咖啡:

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

## 作者 / 许可证

**Agents365-ai** · [Bilibili](https://space.bilibili.com/441831884) · [GitHub](https://github.com/Agents365-ai) · MIT
