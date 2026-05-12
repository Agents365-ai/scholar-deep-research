# 对比 — 用 vs 不用

[English](COMPARISON.md) · [← 返回 README](../README_CN.md)

| 能力 | 原生 agent | 本 skill |
|------|-----------|---------|
| 多源联邦检索 | 一次一个源 | 7 个源联邦 |
| 多轮检索 + 饱和度门控 | 一次性 | 三轴饱和度检查（论文 / 作者 / 期刊） |
| 跨源去重 | 无 | DOI 优先、标题相似度兜底 |
| 透明排序公式 | 黑盒 | 公式 + 每篇论文分量写入 state |
| 正向 / 反向引用追踪 | 无 | OpenAlex + Semantic Scholar 双后端图扩展 |
| 可断点续做 | 每轮无状态 | `research_state.json`（原子、独占锁） |
| 报告原型选择 | 通用大纲 | 5 种原型按意图选择 |
| 自我批判环节 | 无 | 强制 14 项检查（Phase 6） |
| 引用锚点强制 | 论断悬空 | 每条论断必须 `[^id]`，门控拒绝悬空文段 |
| BibTeX / CSL-JSON / RIS 导出 | 无 | 从 state 生成，无需重打 |
| PDF 文本提取 | 偶尔 | `pypdf` 自动升级到 **docling**（版面感知、OCR）处理扫描/稀疏 PDF；OA 链 DOI 解析；宿主 WebFetch 兜底拉 landing page abstract |
| 并行精读派发 | 逐篇串行 | 波次式 agent 派发（每波 8–10）+ 分档 triage |
| 幂等重试 | 不适用 | 所有变更命令都接受 `--idempotency-key` |
| 跨进程限流 | 不适用 | per-source 文件锁 + 429 cooldown 观测 |
| 数据源发现 | 逐脚本阅读 | `list_sources.py` — 按 domain / index-type / auth 过滤 |
| MCP 优雅降级 | 不适用 | MCP 超时时脚本仍可完成 |
