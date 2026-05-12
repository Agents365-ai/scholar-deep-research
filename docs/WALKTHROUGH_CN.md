# 实际运行示例

[English](WALKTHROUGH.md) · [← 返回 README](../README_CN.md)

你只需描述你想要的，skill 自动走完 8 个阶段，每一步都持久化到 `research_state.json`。

```
帮我做一份关于 CRISPR 碱基编辑治疗杜氏肌营养不良的深度研究报告。
```

```
[Phase 0] 重述："CRISPR 碱基编辑作为杜氏肌营养不良治疗手段的当前进展？"
          原型：literature_review
          → research_state.json 已初始化

[Phase 1] OpenAlex + PubMed + arXiv + Crossref 跨 3 个 cluster 检索...
          第 1 轮：187 命中，142 唯一。第 2 轮：94 命中，31 新增。
          饱和度：论文=11%, 作者=18%, 期刊=14% → 已饱和

[Phase 2] 按文献综述权重排序...
          选出 top 20。各项分量已写入 state。
          Triage：10 deep + 10 skim（--deep-ratio 0.5）。
          预取：deep 档 8/10 已缓存，2 篇付费墙(无 OA)。

[Phase 3] Deep 档：派发 8 个并行 agent（1 波）—— 各自读本地 pdf_path,
          不再走网络下载。
          8 个返回完整证据；2 篇付费墙论文已带 evidence_unavailable
          (来自预取阶段)。Skim 档：10 篇自动生成摘要级证据片段。

[Phase 4] 对 top 8 种子做 depth=1 引用追踪。
          新增 24 个候选，6 个进入 top 20。

[Phase 5] 主题：递送、编辑效率、脱靶安全、临床前、临床转化。
          张力：AAV 血清型最优解（3 篇论文意见相左）。

[Phase 6] 自我批判发现 2 条单源论断与 1 个时效缺口。
          运行精准检索；新增 4 篇论文。

[Phase 7] reports/crispr-base-editing-dmd_20260411.md（84 篇引用）
```

输出：`reports/<slug>_<YYYYMMDD>.md`，并附带同名 `.bib`。

每个阶段跃迁都通过 `python scripts/research_state.py advance` 进行，该命令执行门控谓词，不满足时返回结构化的 `gate_not_met` 信封（列出失败的检查项**并**给出建议下一步命令）。无法通过直接设置 `phase` 绕过门控。Phase 6 自我批判如果发现覆盖不足，会回到 Phase 1 补检索；其余阶段是线性的。
