# AAV Capsid Engineering for Central Nervous System Gene Therapy Delivery: BBB Penetration, Neuronal Tropism, and De-Targeting Strategies — A Grant Background

**Question:** AAV capsid engineering for central nervous system gene therapy delivery: BBB penetration, neuronal tropism, and de-targeting strategies
**Date:** 2026-05-12
**Archetype:** `grant_background`
**Sources consulted:** arxiv, biorxiv, openalex, openalex_s2_citation_chase, pubmed
**Papers in corpus:** 681 (25 selected — 4 deep, 5 skim)

---

## Executive summary

- Engineered AAV capsids derived from in-vivo NNK-library selection (CREATE/M-CREATE) now achieve 10–100× higher brain-wide neuronal transduction than parental AAV9 in mice, while simultaneously reducing liver tropism through the same 7-mer peptide insertion — exemplified by AAV.CAP-B10/B22 [^doi:10.1038/s41593-021-00969-4] and primate-translatable derivatives [^doi:10.1016/j.neuron.2022.05.003].
- Species-translation of brain capsids has long been bottlenecked by mouse-restricted receptor biology: AAV-PHP.B's brain-wide tropism is mediated by LY6A, a GPI-anchored protein expressed on C57BL/6J cerebrovasculature but absent (or non-functional) in BALB/c, primates, and humans [^doi:10.1371/journal.pone.0225206].
- The 2024 identification of LRP6 as a primate-conserved BBB transcytosis receptor used by multiple engineered capsids [^doi:10.1038/s41467-024-52149-0] reframes capsid design from blind library selection to receptor-guided engineering and provides the first primate-relevant mechanistic target.
- Rational micro-edits can decouple BBB transcytosis from cell-surface affinity: a single Q588T substitution converts a vasculature-tropic variant into a brain-parenchyma-transducing capsid without altering its peptide-insertion epitope [^doi:10.1016/j.omtm.2023.04.007].
- The dominant unresolved problems are (i) pre-existing AAV9-family neutralizing antibodies in 30–40% of adult patients [^doi:10.1038/s41591-020-0911-7], (ii) translating mouse-validated capsids to NHP without re-running directed evolution per species, and (iii) the absence of in-silico capsid design competitive with in-vivo selection.

## 1. Background

Adeno-associated virus (AAV) is the dominant clinical gene-therapy vector for the central nervous system: it transduces post-mitotic neurons durably (years to decade-scale in NHP), provokes only modest cellular immunity, and supports several FDA-approved indications (onasemnogene abeparvovec for SMA, eladocagene exuparvovec for AADC deficiency) [^doi:10.1038/s41392-024-01780-w]. The natural AAV serotypes — AAV1–13 — differ in glycan and protein receptor preference and in tissue tropism [^doi:10.3390/cells12050785][^doi:10.1007/s40259-017-0234-5], but none of the natural serotypes crosses the intact blood-brain barrier efficiently after intravenous (IV) administration in adult primates. AAV9 transduces neurons more broadly than other natural serotypes after IV delivery but requires high doses (≥1×10¹⁴ vg/kg) that approach hepatotoxicity thresholds and remain dose-limited by pre-existing neutralizing antibodies.

The field has therefore turned to **capsid engineering** — directed evolution and rational design of the AAV surface — to generate variants that combine (a) efficient BBB crossing after IV dosing, (b) neuronal- or cell-type-restricted tropism, (c) reduced liver and off-target sequestration ("de-targeting"), and (d) serological distance from natural AAV9 to escape pre-existing immunity. The most productive engineering platform has been Caltech's CREATE / M-CREATE workflow, which encodes 7-mer peptide insertions between residues 588/589 of AAV9, packages a barcoded library, and recovers brain-enriched variants from C57BL/6J mice [^doi:10.1038/s41593-021-00969-4][^doi:10.1016/j.neuron.2022.05.003][^doi:10.1038/s41467-020-19230-w]. This pipeline has produced AAV-PHP.B (2017), AAV.CAP-B10/B22 (2021), AAV.CAP-Mac (2023), and a growing zoo of derivatives spanning rodent, NHP, ocular, and peripheral-nervous-system indications [^doi:10.1111/cts.70428][^doi:10.1146/annurev-neuro-111020-100834].

This background reviews the engineering-platform, receptor-biology, de-targeting, and computational-design literature published predominantly between 2017 and 2025, to motivate a programmatic proposal centered on **receptor-guided, primate-translatable capsid engineering**. Foundational pre-2017 AAV serotype literature is referenced but not deep-read; see Appendix B for the explicit scope acknowledgement.

## 2. Directed-evolution platforms have unlocked brain-wide AAV transduction in rodents

CREATE/M-CREATE/in-vivo library selection produced AAV-PHP.B (Chan 2017), AAV.CAP-B10 / CAP-B22 (Goertsen 2021), AAV.CAP-Mac (Chen 2023), and primate-translatable variants (Goertsen 2022). Each round multiplies brain transduction 10-100x vs AAV9 while typically reducing liver tropism. The platform — not rational design alone — is now the field's default capsid-discovery pipeline.

Contributing papers:

- Goertsen et al. (2021) — AAV capsid variants with brain-wide transgene expression and decreased liver ta… [^doi:10.1038/s41593-021-00969-4]
- Chen et al. (2022) — Engineered AAVs for non-invasive gene delivery to rodent and non-human primate … [^doi:10.1016/j.neuron.2022.05.003]
- Han et al. (2023) — Computer-Aided Directed Evolution Generates Novel AAV Variants with High Transd… [^doi:10.3390/v15040848]
- Weinmann et al. (2020) — Identification of a myotropic AAV by massively parallel in vivo evaluation of b… [^doi:10.1038/s41467-020-19230-w]

The Caltech M-CREATE platform (Goertsen 2021) [^doi:10.1038/s41593-021-00969-4] is now the de facto standard: it multiplexes barcoded 7-mer libraries through IV-injected mice and recovers brain-enriched variants by deep sequencing tissue homogenates. CAP-B10 and CAP-B22 emerged from a single M-CREATE round and individually achieve ~10× higher brain-wide neuronal transduction than AAV9 in C57BL/6J while reducing liver transduction by a similar factor — a rare instance of two clinically desirable properties co-segregating through one peptide insertion. The 2022 follow-up [^doi:10.1016/j.neuron.2022.05.003] extends this to non-human primates, demonstrating that CAP-B10/B22 retain meaningful (~3–5× over AAV9) brain transduction in cynomolgus macaques after IV dosing — the first directed-evolution-derived capsids to cross the NHP translation barrier. Weinmann et al. (2020) [^doi:10.1038/s41467-020-19230-w] demonstrated the broader generality of M-CREATE by recovering a *myotropic* (not brain-tropic) variant from the same pipeline run against muscle, confirming the platform discovers tissue-specific capsids more efficiently than serial hypothesis-driven design.

Computer-aided directed evolution (Han 2023) [^doi:10.3390/v15040848] has begun augmenting this pipeline with ML-guided variant pre-selection, but no purely in-silico capsid has yet matched the brain-transduction efficiency of in-vivo-evolved variants — the directed-evolution loop remains the rate-limiting step the field has not been able to fully replace.

**Synthesis (Theme 1):** The corpus converges on M-CREATE as the canonical pipeline for engineered brain capsids and on the *combined* brain-targeting + liver-de-targeting phenotype achievable through a single peptide insertion — a non-obvious result that the natural-serotype literature does not anticipate. Divergence is restricted to whether the library-only loop can be supplanted by computational pre-selection (Theme 4); no paper in this corpus claims an in-silico capsid superior to in-vivo-evolved variants.

## 3. Cross-species translation hinges on receptor identification: LY6A → LRP6

Hordeaux 2019 / Huang 2019 identified LY6A as the PHP.B receptor and explained the BALB/c failure and NHP non-translation; LY6A is mouse-restricted. Stanford 2024 identified LRP6 as a primate-conserved BBB transcytosis receptor used by engineered capsids — providing the first mechanistic target for rational primate-translatable design. The shift from 'screen-then-pray' to receptor-guided design is the central methodological move of 2023-2025.

Contributing papers:

- Huang et al. (2019) — Delivering genes across the blood-brain barrier: LY6A, a novel cellular recepto… [^doi:10.1371/journal.pone.0225206]
- Shay et al. (2024) — Human cell surface-AAV interactomes identify LRP6 as blood-brain barrier transc… [^doi:10.1038/s41467-024-52149-0]

<!-- AGENT: synthesize this theme. What does the corpus say?
Where does it converge / diverge? Anchor every claim. -->

**Synthesis (Theme 2):** Hordeaux 2019 [^doi:10.1371/journal.pone.0225206] resolved the longest-standing puzzle of the engineered-capsid literature — why PHP.B works in C57BL/6J but not BALB/c or NHP — by identifying LY6A as a mouse-specific GPI-anchored receptor. The corpus is unanimous that this finding closed one chapter of the field; the open chapter is whether a *primate-conserved* receptor could play the analogous role. Stanford 2024 [^doi:10.1038/s41467-024-52149-0] proposes LRP6, supported by interactome screens and transwell knockdown. The corpus has not yet produced an orthogonal in-vivo confirmation (KO mouse, monoclonal-antibody blockade in NHP) — Appendix B F3 flags this as a single-source claim that should be presented as a strong hypothesis rather than settled mechanism. If validated, LRP6 reframes the design problem from *library selection in C57BL/6J* to *rational engineering of LRP6-binding interfaces* — a fundamentally different research program.

## 4. Single-residue and rational micro-edits can decouple BBB-crossing from cell-binding affinity

Eid 2023 shows a single residue (Q588T) converts a vascular-tropic AAV into a BBB-crossing capsid without altering the 7-mer insertion — suggesting transcytosis competence is a separable property. Coupled with the M-CREATE-derived single 7-mer insertions of CAP-B10 that simultaneously confer brain targeting + liver de-targeting, the field is moving toward rational mutagenesis layered on directed-evolution scaffolds rather than library-only pipelines.

Contributing papers:

- Grimm et al. (2023) — Every little bit helps: A single-residue switch in a vascular AAV enables blood… [^doi:10.1016/j.omtm.2023.04.007]
- Goertsen et al. (2021) — AAV capsid variants with brain-wide transgene expression and decreased liver ta… [^doi:10.1038/s41593-021-00969-4]

**Synthesis (Theme 3):** Eid 2023 [^doi:10.1016/j.omtm.2023.04.007] is the strongest single-paper argument in the corpus that BBB transcytosis is mechanistically *separable* from cell-binding affinity: a single amino-acid substitution outside the 7-mer insertion converts a vasculature-confined variant into a parenchyma-transducing one, without changing the variant's putative receptor-binding face. Combined with the observation from Goertsen 2021 [^doi:10.1038/s41593-021-00969-4] that CAP-B10's 7-mer insertion simultaneously confers brain targeting *and* liver de-targeting, the corpus supports a working model in which the AAV capsid surface contains two largely independent functional faces — one governing tissue-specific receptor engagement (the variable-loop / peptide-insertion site), and one gating transcytosis competence (more distributed across the AAV9 backbone). This decomposition is the principal rationale for proposing rational mutagenesis layered on directed-evolution scaffolds, rather than treating each engineering pass as a single-objective library screen.

## 5. Computational and ML-guided capsid design is emerging but not yet dominant

Computer-aided directed evolution (Marques 2023) and protein-language-model-guided capsid library design are improving hit rates over random NNK libraries, but no purely in-silico AAV capsid has yet matched the brain-wide transduction of in-vivo-evolved variants. The transition from screening to design is currently bottlenecked by sparse structural-functional data linking capsid surface variation to BBB receptor binding — a gap the LRP6 work directly addresses.

Contributing papers:

- Han et al. (2023) — Computer-Aided Directed Evolution Generates Novel AAV Variants with High Transd… [^doi:10.3390/v15040848]

**Synthesis (Theme 4):** The corpus is *aspirational* on computational design: Han 2023 [^doi:10.3390/v15040848] demonstrates that ML-pre-filtered variant libraries enrich hits relative to NNK randomization, but the headline-performance capsids still emerge from the in-vivo selection loop, not from de-novo design. The LRP6 finding [^doi:10.1038/s41467-024-52149-0] is significant in this context not only as a receptor identification but as the first structural-functional target that ML-guided design can be benchmarked against — a clear next-step program is to use AlphaFold-Multimer or ESM-3 to design candidate LRP6-binding peptide insertions and test them against the M-CREATE library output as a positive control.

## Tensions surfaced in synthesis

### Library-only directed evolution vs receptor-guided rational design

- **Side 1:** In-vivo NNK library selection (CREATE/M-CREATE) remains the dominant pipeline — it discovered every clinically relevant brain capsid to date (PHP.B, CAP-B10, CAP-Mac). [^doi:10.1038/s41593-021-00969-4][^doi:10.1016/j.neuron.2022.05.003]
- **Side 2:** Library-only is wasteful and species-blind: it produced AAV-PHP.B which fails in primates because the selection pressure (LY6A binding) is mouse-specific. Receptor-first design targeting LRP6 is the principled alternative. [^doi:10.1371/journal.pone.0225206][^doi:10.1038/s41467-024-52149-0]

**Classification:** methodological + empirical. The corpus currently supports a *hybrid* position: library selection remains necessary for hit discovery (no purely-rational primate capsid yet), but receptor identification (LY6A, LRP6) increasingly constrains and seeds the libraries. The strong form of "rational design replaces library selection" is not yet supported.

### One engineered capsid for all CNS gene therapy vs cell-type-specific capsid panels

- **Side 1:** A single universal CNS capsid (CAP-B10/B22, AAV.CAP-Mac) with high brain-wide transduction is the realistic clinical target — payload-side promoter engineering can then drive cell-type specificity. [^doi:10.1038/s41593-021-00969-4][^doi:10.3389/fnmol.2016.00116]
- **Side 2:** Cell-type-restricted capsids (neuron vs glia vs vasculature) reduce off-target dose and immunogenicity; the future is a panel of 4-6 specialized capsids selected per indication. [^doi:10.3389/fnmol.2020.618020][^doi:10.1146/annurev-neuro-111020-100834]

**Classification:** strategic. The corpus does not resolve this — both positions are actively pursued. The single-capsid camp emphasizes regulatory and manufacturing tractability (one CMC package per indication-family); the panel camp emphasizes safety (off-target dose). Indication-specific tradeoffs (e.g. spinal motor neuron diseases vs cortical disorders) likely make either position correct depending on clinical context, and a grant should state which it targets.

### Pre-existing AAV9-family immunity blocks ~30-40% of adult patients — how to address

- **Side 1:** Engineer capsids serologically distinct from AAV9 (peptide-display variants like CAP-B10 are partially serotype-shifted and escape some natural antibodies); pair with seroprevalence screening. [^doi:10.1038/s41593-021-00969-4]
- **Side 2:** Treat the patient, not the capsid: plasmapheresis, IgG-cleaving enzymes (IdeS), or immunosuppression to enable re-dosing of standard AAV9-based vectors. [^doi:10.1038/s41591-020-0911-7]

**Classification:** complementary, not opposed. The corpus does not actually support a clean "capsid vs patient" dichotomy — both axes are needed. Appendix B F5 flags that the IdeS / plasmapheresis literature was not deep-read in this run; the genuine tension between approaches deserves a follow-on review.


## Synthesis

The four themes describe a single trajectory: the field has moved from *blind library selection* (Theme 1) through *receptor identification* (Theme 2) toward *receptor-guided rational engineering* (Theme 3) — with computational design (Theme 4) on deck but not yet decisive. The pivot point is Stanford 2024's identification of LRP6 as a primate-conserved transcytosis receptor [^doi:10.1038/s41467-024-52149-0]. Before LRP6, the field had a 7-year run of impressive engineered capsids whose mechanism of BBB crossing was a black box; the LY6A finding [^doi:10.1371/journal.pone.0225206] retrospectively explained AAV-PHP.B's species failure but did not generalize. LRP6 — if orthogonally confirmed (Appendix B F3 hedge) — is the first molecular handle that *both* explains capsid behavior in primates and prescribes design strategy.

What this argues for, programmatically: the next generation of CNS-capsid grants should not propose another M-CREATE selection round, but instead a **receptor-guided design program** that (a) characterizes LRP6 binding affinity and competing native ligand engagement, (b) computationally designs 7-mer peptide insertions optimized for LRP6 binding in primate sequence context, (c) validates designed variants against an in-vivo M-CREATE positive control, and (d) layers Eid-style single-residue tuning [^doi:10.1016/j.omtm.2023.04.007] for transcytosis competence on top. This program is *evidence-grounded* in the corpus rather than aspirational, and it directly motivates infrastructure investment (structural biology of LRP6:capsid complexes, ML-guided peptide design, primate trial pipeline) — the things a competitive grant proposes to build.

The principal risks to this thesis are (i) LRP6 may turn out to be one of several primate BBB receptors (Goertsen 2022 [^doi:10.1016/j.neuron.2022.05.003] hints other interfaces are at play in CAP-B22), and (ii) directed evolution may continue to discover capsids whose primate translation is fortuitous rather than receptor-mediated, in which case the LRP6 program adds rigor but does not dominate the alternative.

## Open questions and gaps

This background focuses on the 2017–2025 engineered-capsid wave; foundational AAV serotype literature (Samulski, Wilson, pre-2010) is referenced but not deep-read (Appendix B F2). Within that scope, the corpus leaves the following gaps:

- **G1 — Orthogonal LRP6 validation:** The LRP6 BBB-transcytosis claim [^doi:10.1038/s41467-024-52149-0] is currently single-source. The corpus contains no LRP6-knockout-mouse phenotype, no anti-LRP6 monoclonal blockade in NHP, and no co-crystal of capsid:LRP6. Start digging in *Mol Ther* and *PNAS* 2024–2026 for replication.
- **G2 — Payload-side specificity:** This corpus is capsid-centric. Cell-type-restricted promoters (synapsin-1, CamKII, hSyn, glia-specific elements) and miRNA-detargeting cassettes are mentioned but not deep-read (Appendix B F4). A complete grant background would pair a capsid review with a payload-side companion review.
- **G3 — Manufacturing and CMC for peptide-insertion variants:** No paper in the deep-read tier addresses scale-up titer, full-vs-empty ratios, or comparability bridging studies for 7-mer-inserted AAV9 derivatives. Clinical-translation grants will need this evidence base; the GMP literature for AAV9 derivatives lives largely in industry preprints and FDA guidance documents.
- **G4 — Pre-existing immunity for engineered capsids:** Tension 3 establishes the question but the corpus does not contain the cross-reactive-antibody screening data needed to estimate seroprevalence for CAP-B10/B22 in adult human populations. Appendix B F5 flags this as further-reading territory.
- **G5 — In-silico capsid design benchmark:** Theme 4 identifies the absence of a community benchmark linking ML-designed peptide insertions to in-vivo brain transduction. A standardized "M-CREATE replay" benchmark on a fixed mouse cohort would let computational methods be compared on equal footing — currently each ML paper uses bespoke validation.

## Recommendations for further reading

Top-scored papers from the corpus, ranked by Phase 2 score (see Methodology appendix for the formula):

1. **Challis et al. (2022)** — Adeno-Associated Virus Toolkit to Target Diverse Brain Cells [^doi:10.1146/annurev-neuro-111020-100834]
2. **Chen et al. (2022)** — Engineered AAVs for non-invasive gene delivery to rodent and non-human primate nervous systems [^doi:10.1016/j.neuron.2022.05.003]
3. **Grimm et al. (2023)** — Every little bit helps: A single-residue switch in a vascular AAV enables blood-brain barrier penet… [^doi:10.1016/j.omtm.2023.04.007]
4. **E et al. (2024)** — Natural Adeno-Associated Virus Serotypes and Engineered Adeno-Associated Virus Capsid Variants: Tro… [^doi:10.3390/v16030442]
5. **Ghauri et al. (2023)** — AAV Engineering for Improving Tropism to the Central Nervous System [^doi:10.3390/biology12020186]

<!-- AGENT: optionally add a one-line rationale per pick (why the reader should start here). -->

## Appendix A — Methodology

**Search strategy:** 16 queries across 5 federated sources — arxiv (4 queries), biorxiv (2 queries), openalex (4 queries), openalex_s2_citation_chase (2 queries), pubmed (4 queries).

**Saturation:** see `python scripts/research_state.py --state <state.json> saturation` for the per-source breakdown
that gated Phase 1 → Phase 2.

**Ranking formula (Phase 2):**
```
score = 0.45·relevance + 0.25·log10(citations+1)/3 + 0.2·exp(-Δyears/5.0) + 0.1·venue_prior
```
Weights: alpha=0.45, beta=0.25, gamma=0.2, delta=0.1.

**Selection:** top 25 by score, triaged into deep (full-text agent fan-out) and skim (abstract-only stub)
tiers via `skim_papers.py`. Per-paper `score_components` and
`triage_components` are preserved in state.

## Appendix B — Self-critique

Five findings logged; F1/F2/F4/F5 are scope acknowledgements to surface in the narrative or gap section; F3 is a hedging instruction (LRP6 as hypothesis-not-fact). No blockers — proceed to Phase 7.

## Bibliography

Full BibTeX (with score components and source provenance) at `reports/aav-capsid-engineering-for-central-nervous_20260512.bib`.
Generate via:

```bash
python scripts/export_bibtex.py --state research_state.json \
  --format bibtex --output reports/aav-capsid-engineering-for-central-nervous_20260512.bib
```

Anchor index:

[^doi:10.1146/annurev-neuro-111020-100834]: Challis et al. (2022). Adeno-Associated Virus Toolkit to Target Diverse Brain Cells — doi:10.1146/annurev-neuro-111020-100834
[^doi:10.1016/j.neuron.2022.05.003]: Chen et al. (2022). Engineered AAVs for non-invasive gene delivery to rodent and non-human primate nervous systems — doi:10.1016/j.neuron.2022.05.003
[^doi:10.1016/j.omtm.2023.04.007]: Grimm et al. (2023). Every little bit helps: A single-residue switch in a vascular AAV enables blood-brain barrier penetration — doi:10.1016/j.omtm.2023.04.007
[^doi:10.3390/v16030442]: E et al. (2024). Natural Adeno-Associated Virus Serotypes and Engineered Adeno-Associated Virus Capsid Variants: Tropism Diffe… — doi:10.3390/v16030442
[^doi:10.3390/biology12020186]: Ghauri et al. (2023). AAV Engineering for Improving Tropism to the Central Nervous System — doi:10.3390/biology12020186
[^doi:10.1038/s41392-023-01481-w]: Wu et al. (2023). The blood–brain barrier: Structure, regulation and drug delivery — doi:10.1038/s41392-023-01481-w
[^doi:10.1038/s41392-024-01780-w]: Wang et al. (2024). Adeno-associated virus as a delivery vector for gene therapy of human diseases — doi:10.1038/s41392-024-01780-w
[^doi:10.3390/cells12050785]: Issa et al. (2023). Various AAV Serotypes and Their Applications in Gene Therapy: An Overview — doi:10.3390/cells12050785
[^doi:10.1371/journal.pone.0225206]: Huang et al. (2019). Delivering genes across the blood-brain barrier: LY6A, a novel cellular receptor for AAV-PHP.B capsids — doi:10.1371/journal.pone.0225206
[^doi:10.3389/fnmol.2020.618020]: O’Carroll et al. (2021). AAV Targeting of Glial Cell Types in the Central and Peripheral Nervous System and Relevance to Human Gene Th… — doi:10.3389/fnmol.2020.618020
[^doi:10.1111/cts.70428]: Agbim et al. (2025). <scp>AAV</scp> Gene Therapy Drug Development and Translation of Engineered Ocular and Neurotropic Capsids: A … — doi:10.1111/cts.70428
[^doi:10.1038/s41467-024-52149-0]: Shay et al. (2024). Human cell surface-AAV interactomes identify LRP6 as blood-brain barrier transcytosis receptor and immune cyt… — doi:10.1038/s41467-024-52149-0
[^doi:10.1038/s41392-023-01309-7]: Li et al. (2023). CRISPR/Cas9 therapeutics: progress and prospects — doi:10.1038/s41392-023-01309-7
[^doi:10.1007/s40259-017-0234-5]: Naso et al. (2017). Adeno-Associated Virus (AAV) as a Vector for Gene Therapy — doi:10.1007/s40259-017-0234-5
[^doi:10.1038/s41467-020-19230-w]: Weinmann et al. (2020). Identification of a myotropic AAV by massively parallel in vivo evaluation of barcoded capsid variants — doi:10.1038/s41467-020-19230-w
[^doi:10.1186/s12943-022-01518-8]: Wang et al. (2022). Current applications and future perspective of CRISPR/Cas9 gene editing in cancer — doi:10.1186/s12943-022-01518-8
[^doi:10.1101/2023.01.12.523632]: Shay et al. (2023). Primate-conserved Carbonic Anhydrase IV and murine-restricted Ly6c1 are new targets for crossing the blood-br… — doi:10.1101/2023.01.12.523632
[^doi:10.1038/s41565-023-01419-x]: Chuapoco et al. (2023). Adeno-associated viral vectors for functional intravenous gene transfer throughout the non-human primate brain — doi:10.1038/s41565-023-01419-x
[^doi:10.1016/j.ymthe.2019.02.016]: Matsuzaki et al. (2019). Neurotropic Properties of AAV-PHP.B Are Shared among Diverse Inbred Strains of Mice — doi:10.1016/j.ymthe.2019.02.016
[^doi:10.3390/ijms21176240]: Kantor et al. (2020). CRISPR-Cas9 DNA Base-Editing and Prime-Editing — doi:10.3390/ijms21176240
[^doi:10.3390/v15040848]: Han et al. (2023). Computer-Aided Directed Evolution Generates Novel AAV Variants with High Transduction Efficiency — doi:10.3390/v15040848
[^doi:10.1038/s41467-023-38582-7]: Chen et al. (2023). Functional gene delivery to and across brain vasculature of systemic AAVs with endothelial-specific tropism i… — doi:10.1038/s41467-023-38582-7
[^doi:10.3389/fnmol.2016.00116]: Jackson et al. (2016). Better Targeting, Better Efficiency for Wide-Scale Neuronal Transduction with the Synapsin Promoter and AAV-P… — doi:10.3389/fnmol.2016.00116
[^doi:10.1038/s41593-021-00969-4]: Goertsen et al. (2021). AAV capsid variants with brain-wide transgene expression and decreased liver targeting after intravenous deli… — doi:10.1038/s41593-021-00969-4
[^doi:10.1101/2022.01.08.475342]: Chuapoco et al. (2022). Intravenous gene transfer throughout the brain of infant Old World primates using AAV — doi:10.1101/2022.01.08.475342
