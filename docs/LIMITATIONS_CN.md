# 已知限制

[English](LIMITATIONS.md) · [← 返回 README](../README_CN.md)

- **不含 Google Scholar / Web of Science / Scopus** — 这些数据源无公开 API 或需机构访问权限。如对主题重要，可在报告附录注明"未检索"
- **DOI 解析需开放获取** — `--doi` 模式仅能找到合法开放获取的 PDF（通过 [paper-fetch](https://github.com/Agents365-ai/paper-fetch) 或 Unpaywall）。付费墙论文走 Phase 3 step (d)：尝试 `WebFetch` 抓 publisher landing page；若仍失败，该论文标 `evidence_unavailable`，不进 full-evidence 引用
- **arXiv 无引用计数** — 仅出现在 arXiv 的论文 `citations=null`，排序公式中引用项贡献为 0
- **PubMed 完整摘要** — 默认只取 esummary 以提速；需要全文摘要请加 `--with-abstracts`
- **英文偏倚** — 多个数据源都收录非英文文献，但检索质量参差。若主题非英文文献多，请在报告局限性中注明
- **相关性使用 bag-of-words** — 如需语义重排，可接入 embedding 模型并将结果写回 `state.papers[*].score_components.relevance`，pipeline 已为此设计
- **饱和度门控基于"新颖度"而非"穷尽性"** — 三轴（论文/作者/期刊）饱和度能识破"探索已停滞"，但不能告诉你"相关论文已全部找到"。如需严格覆盖，请用 systematic_review 原型 + `SCHOLAR_SATURATION_NEW_PCT=20`
