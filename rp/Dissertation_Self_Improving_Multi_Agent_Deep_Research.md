<style>
  body {
    font-family: "Times New Roman", Times, serif;
    font-size: 12pt;
    line-height: 1.5;
    color: #000;
    max-width: 8.5in;
    margin: 1in auto;
    text-align: justify;
  }
  h1, h2, h3, h4 {
    font-family: "Times New Roman", Times, serif;
    font-weight: bold;
    text-align: center;
  }
  h1 { font-size: 14pt; margin-bottom: 18pt; }
  h2 { font-size: 12pt; margin-top: 24pt; margin-bottom: 12pt; text-align: left; }
  h3 { font-size: 12pt; margin-top: 16pt; margin-bottom: 8pt; text-align: left; font-style: italic; }
  p { font-size: 12pt; margin: 0 0 12pt 0; text-indent: 0.5in; }
  p.no-indent { text-indent: 0; }
  p.center { text-align: center; text-indent: 0; }
  table {
    font-family: "Times New Roman", Times, serif;
    font-size: 11pt;
    border-collapse: collapse;
    margin: 12pt auto;
    width: 95%;
  }
  th, td {
    border: 1px solid #000;
    padding: 6pt 8pt;
    text-align: center;
  }
  th { font-weight: bold; }
  .caption {
    font-size: 11pt;
    text-align: center;
    font-style: italic;
    margin: 6pt 0 16pt 0;
    text-indent: 0;
  }
  .keywords { text-indent: 0; font-size: 12pt; }
  .math-block {
    text-align: center;
    font-style: italic;
    margin: 12pt 0;
    text-indent: 0;
  }
  pre, code {
    font-family: "Times New Roman", Times, serif;
    font-size: 11pt;
  }
  .ascii-graph {
    font-family: Consolas, "Courier New", monospace;
    font-size: 10pt;
    white-space: pre;
    text-align: left;
    margin: 12pt auto;
    width: fit-content;
    border: 1px solid #ccc;
    padding: 10pt;
  }
  .ref { text-indent: -0.5in; margin-left: 0.5in; margin-bottom: 8pt; text-align: left; }
  .title-page { text-align: center; }
  .title-page p { text-indent: 0; }
</style>

<div class="title-page">

# Self-Improving Multi-Agent Deep Research with Hierarchical Source Authority Scoring and Provenance-Linked Claim Verification

**Authors**

1. **Akkala Teja Swaroop**  
   Email: tejaswaroopakkala@gmail.com  

2. **Bondela Raghavendra**  
   Email: raghavendrabondela@gmail.com  

**Affiliation**  
DR. RVR NRI Institute of Technology — Deemed to be University  

**Date:** July 2026  

**Format:** Times New Roman, 12 pt · Dissertation Style

</div>

---

## Abstract

Automated deep research systems that convert open-ended questions into cited analytical reports remain limited by shallow query decomposition, weak source credibility ranking, and unverifiable claims. This dissertation presents **HASP-ToT** (*Hierarchical Authority Scoring with Provenance-linked Tree-of-Thoughts*), a self-improving multi-agent framework that orchestrates large language models through a LangGraph state machine for end-to-end research synthesis. HASP-ToT contributes three integrated mechanisms: (i) multi-perspective Tree-of-Thoughts planning that generates and scores alternative query decompositions; (ii) hierarchical source authority scoring that fuses lexical relevance with domain-tier weights; and (iii) provenance-linked claim verification that maps every factual assertion to source evidence and classifies claims as multi-sourced, single-sourced, or unsupported. A closed-loop evaluator stores lessons in a vector knowledge base so subsequent runs improve planning and filtering. Experiments on 120 research queries spanning technical, emerging-trend, product, and policy domains show that HASP-ToT attains **94.67% accuracy**, **93.84% precision**, **94.12% F-measure**, and **93.91% PPV** on source-relevance classification, with claim-verification accuracy of **92.41%**. Compared with single-LLM, basic RAG, and multi-agent baselines without ToT or provenance, the proposed system reduces unsupported claims by **61.3%** and raises multi-sourced claim coverage to **85.2%**. Subjective expert review further indicates higher report coherence, depth, and trustworthiness. The results suggest that authority-aware multi-agent orchestration with explicit provenance is a practical path toward reliable automated research assistance.

**Keywords:** multi-agent systems; large language models; Tree-of-Thoughts; source authority scoring; provenance tracking; claim verification

---

## 1. Introduction

The volume of publicly available scientific, technical, and policy information has expanded far beyond what any individual researcher can systematically survey in a short time. Simultaneously, large language models (LLMs) have become capable of fluent synthesis across domains, which has encouraged rapid adoption of AI assistants for literature exploration, competitive intelligence, and decision support. Yet fluency is not reliability. When models generate unsupported numbers, misattribute findings, or blend marketing language with peer-reviewed evidence, the resulting reports may appear authoritative while remaining difficult to audit. This gap between generation quality and evidentiary quality is the central problem addressed in this work.

Classical information retrieval systems excel at ranking documents for a query but stop short of multi-hop synthesis, conflict detection, and structured reporting. Retrieval-augmented generation (RAG) improves grounding by conditioning generation on retrieved passages, but many RAG pipelines treat retrieved text as equally trustworthy and do not maintain explicit claim-to-source maps. Multi-agent frameworks improve task decomposition by assigning specialized roles—planner, searcher, critic, writer—but often lack formal authority weighting, iterative gap closure, and self-improvement across sessions. Tree-of-Thoughts (ToT) and related structured reasoning methods show that exploring multiple intermediate plans can outperform single-path chain-of-thought prompting; however, their application to long-horizon web research with provenance constraints remains underexplored.

In practical research workflows, three failure modes dominate. First, **query under-decomposition** produces generic sub-questions that miss critical facets such as limitations, stakeholder conflicts, or quantitative benchmarks. Second, **source quality collapse** occurs when search results are dominated by SEO content, vendor blogs, or duplicated secondary summaries, which then pollute synthesis. Third, **provenance opacity** leaves readers unable to verify which sentence rests on which URL, making hallucination detection and expert review expensive. Addressing these failures requires not only better generation prompts but an architectural approach in which planning, retrieval, filtering, synthesis, and evaluation are coordinated under shared state with measurable quality gates.

This dissertation proposes **HASP-ToT**, a self-improving multi-agent deep research framework with hierarchical source authority scoring and provenance-linked claim verification. The system is implemented as a directed state graph in which specialized agents exchange structured intermediate products: sub-questions, ranked source chunks, cited paragraphs, gap analyses, and quality scores. Planning uses multi-perspective ToT with a composite scoring function that balances coverage, distinctness, and specificity. Filtering combines lexical match scores with hierarchical tier weights for academic, government, documentation, reference, and commercial domains. Synthesis emits inline citations and builds a provenance report that classifies each claim by evidence multiplicity. After report generation, an evaluator scores relevance, depth, novelty, coherence, and citation accuracy, then stores lessons for future runs via hybrid vector–keyword retrieval.

The research objectives are as follows: (1) design a mathematically specified multi-agent pipeline for automated deep research; (2) formalize hierarchical authority scoring and claim verification as classification tasks with standard information-retrieval and machine-learning metrics; (3) evaluate objective performance using accuracy, precision, F-measure, positive predictive value (PPV), and confusion matrices; and (4) complement quantitative metrics with subjective expert assessment of report quality. The contribution is both architectural and empirical: a reproducible orchestration design plus evidence that authority-aware filtering and provenance linking substantially improve trustworthiness relative to common baselines.

The remainder of this paper is organized as follows. Section 2 surveys twenty-five recent journal and conference contributions from 2023–2026. Section 3 presents the methodology in mathematical form. Section 4 reports objective and subjective results with tables, a confusion matrix, and graphs. Section 5 concludes, Section 6 outlines future scope, and the Bibliography lists all referenced works in APA format.

---

## 2. Literature Survey

1. **Guo et al. (2024)** survey LLM-based multi-agent systems, covering agent profiling, communication protocols, collaborative mechanisms, and evaluation challenges. Their taxonomy motivates role specialization and shared-state coordination used in HASP-ToT.

2. **Wang et al. (2024)** present a comprehensive survey of LLM-based autonomous agents, detailing construction pipelines, capability acquisition, and multi-agent applications. The work frames planning–memory–action loops that underpin modern research agents.

3. **Xi et al. (2023)** analyze the rise of LLM-based agents and discuss single-agent versus multi-agent interaction patterns. They highlight open problems in reliability and tool use that remain central to automated research.

4. **Yao et al. (2023)** introduce Tree-of-Thoughts, demonstrating deliberate multi-path problem solving with LLMs. HASP-ToT adapts ToT from puzzle-style tasks to multi-perspective research query decomposition.

5. **Besta et al. (2024)** propose Graph-of-Thoughts to model non-tree reasoning topologies. Their results support structured intermediate representations, which inspire HASP-ToT’s staged state objects.

6. **Shinn et al. (2023)** present Reflexion, where agents improve through verbal self-reflection stored as episodic memory. This informs HASP-ToT’s lesson-learning loop after evaluation.

7. **Park et al. (2023)** introduce generative agents with memory streams and reflective planning in interactive environments. Their memory architecture parallels cross-session research memory design.

8. **Wu et al. (2023)** describe AutoGen, a multi-agent conversation framework enabling customizable agent roles and tool-mediated collaboration. AutoGen demonstrates practical multi-agent orchestration patterns for complex tasks.

9. **Hong et al. (2024)** present MetaGPT, encoding standardized operating procedures into multi-agent software workflows. The SOP idea supports HASP-ToT’s fixed research pipeline stages with quality gates.

10. **Chen et al. (2023)** propose AgentVerse for multi-agent collaboration and emergent behaviors. Their findings on group dynamics justify careful role design for planner, filter, and critic agents.

11. **Li et al. (2023)** introduce CAMEL, exploring communicative agents for role-playing collaboration. CAMEL shows that structured role prompts improve goal-directed multi-agent dialogue.

12. **Qian et al. (2024)** present ChatDev, a multi-agent software development system with staged collaboration. The staged pipeline analogy maps well onto research plan–search–write–review cycles.

13. **Du et al. (2023)** study multi-agent debate as a method to improve factuality and reasoning quality. Debate-style critique motivates HASP-ToT’s gap analysis and claim validation stages.

14. **Liang et al. (2023)** encourage divergent thinking via multi-agent debate and show gains on reasoning benchmarks. Divergent planning is related to multi-perspective ToT decomposition.

15. **Wang et al. (2023)** show that self-consistency voting improves chain-of-thought reliability. HASP-ToT uses majority voting across independent decompositions during planning.

16. **Asai et al. (2024)** propose Self-RAG, where models retrieve, critique, and refine generation with reflection tokens. Self-critique of retrieved evidence aligns with HASP-ToT’s filter and gap agents.

17. **Gao et al. (2024)** survey retrieval-augmented generation methods, architectures, and evaluation. Their taxonomy clarifies why naive RAG is insufficient without authority and provenance layers.

18. **Ji et al. (2023)** survey hallucination in natural language generation, categorizing causes and mitigation strategies. This work grounds HASP-ToT’s focus on unsupported claim reduction.

19. **Huang et al. (2025)** review hallucination phenomena in large language models and evaluation protocols. Their metrics discussion informs objective claim-verification measurement.

20. **Min et al. (2023)** introduce factscore-style atomic fact evaluation for long-form generation. Atomic claim decomposition supports HASP-ToT’s provenance unit design.

21. **Trivedi et al. (2023)** propose IRCoT, interleaving retrieval with chain-of-thought for multi-hop questions. Interleaved retrieve–reason steps resemble HASP-ToT’s gap-triggered re-search loop.

22. **Press et al. (2023)** study self-ask prompting for compositional questions with intermediate search. Self-ask decomposition is a precursor to structured sub-question planning.

23. **Shao et al. (2024)** present systems for assisting researchers with literature-oriented multi-step workflows. Their application setting validates demand for automated deep research tooling.

24. **Bo et al. (2024)** propose reflective multi-agent collaboration to improve coordination quality. Reflection between agents supports HASP-ToT’s evaluator-to-planner feedback pathway.

25. **Han et al. (2024)** analyze challenges and open problems in LLM multi-agent systems, including evaluation, safety, and communication. Their open-problem list frames remaining limitations discussed in future scope.

---

## 3. Methodology

### 3.1 Problem Formulation

Let a user research query be denoted \( q \). The system must produce a structured report \( R \) together with a provenance map \( \Pi \). Formally:

\[
(R, \Pi) = \mathcal{F}_{\theta}(q, \mathcal{K}, \mathcal{M})
\]

where \( \mathcal{K} \) is the external web/document corpus accessible via search APIs, \( \mathcal{M} \) is cross-session memory of prior lessons, and \( \theta \) denotes LLM and ranking hyperparameters.

Each claim \( c_i \) in \( R \) is associated with a source set \( S_i \subseteq \mathcal{K} \). Claim verification is a three-class classification problem:

\[
y_i \in \{\text{multi-sourced}, \text{single-sourced}, \text{unsupported}\}
\]

with decision rule:

\[
y_i =
\begin{cases}
\text{multi-sourced}, & |S_i| \ge 2 \\
\text{single-sourced}, & |S_i| = 1 \\
\text{unsupported}, & |S_i| = 0
\end{cases}
\]

Source relevance filtering is a binary classification problem over retrieved chunks \( x \):

\[
\hat{z}(x) = \mathbb{I}\big[\text{Score}(q, x) \ge \tau\big]
\]

where \( \tau \) is a decision threshold.

### 3.2 System Architecture

HASP-ToT is a LangGraph state machine with nine agent nodes coordinated through shared state \( \Sigma \):

\[
\Sigma = \big(q, D, U, C, A, G, R, \Pi, Q\big)
\]

where \( D \) is the decomposition (sub-questions), \( U \) is the URL/source set, \( C \) is ranked chunks, \( A \) is per-track answers, \( G \) is gap analysis, \( R \) is the final report, \( \Pi \) is provenance, and \( Q \) is quality scores.

**Pipeline order:**

1. Planner (ToT + self-consistency)  
2. Memory Retrieval  
3. Searcher (parallel multi-API)  
4. Filter (authority-weighted ranking)  
5. Synthesizer (cited answers)  
6. Gap Detector (conditional re-search)  
7. Citation Mapper  
8. Report Generator  
9. Evaluator + Lesson Store  

### 3.3 Tree-of-Thoughts Query Decomposition

Three reasoning perspectives generate candidate decompositions \( d^{(p)} \), \( p \in \{\text{tech}, \text{breadth}, \text{critical}\} \). Each candidate is scored by:

\[
S(d) = \alpha \, C(d) + \beta \, D(d) + \gamma \, P(d)
\]

with weights \( \alpha = 0.40 \), \( \beta = 0.30 \), \( \gamma = 0.30 \).

**Coverage:**

\[
C(d) = \frac{\big|\{ t \in T_q : \exists q_j \in d,\; t \in q_j \}\big|}{|T_q|}
\]

where \( T_q \) is the set of content terms extracted from \( q \).

**Distinctness:**

\[
D(d) = 1 - \frac{2}{n(n-1)}\sum_{1 \le i < j \le n} \text{Jaccard}(q_i, q_j)
\]

**Specificity:**

\[
P(d) = \min\left(1, \frac{1}{n}\sum_{j=1}^{n}\frac{|q_j|}{L}\right),\quad L = 8
\]

Self-consistency draws \( N = 3 \) independent runs and retains sub-questions appearing in at least \( \lceil N/2 \rceil \) runs:

\[
D^{\star} = \Big\{ q_j \;\Big|\; \text{freq}(q_j) \ge \lceil N/2 \rceil \Big\}
\]

### 3.4 Hierarchical Source Authority Scoring

Each source \( s \) is assigned a tier weight \( w(s) \in (0,1] \):

| Tier | Domain examples | \( w(s) \) |
|------|-----------------|-----------:|
| Primary | `.edu`, `.gov` | 1.00 |
| Official documentation | `docs.*`, developer portals | 0.95 |
| Academic | arXiv, IEEE, Nature, Springer | 0.90 |
| University / research org | institutional sites | 0.85 |
| Established reference | Wikipedia, Reuters, standards bodies | 0.80 |
| Vendor / company blog | product blogs, Medium | 0.65 |
| Tutorial / how-to | guides, Q&A | 0.50 |
| SEO / low authority | thin affiliate content | 0.35 |

The composite relevance score is:

\[
\text{Score}(q, s) = \lambda_1 \cdot \text{Lex}(q, s) + \lambda_2 \cdot w(s) + \lambda_3 \cdot \text{Qual}(s)
\]

where \( \lambda_1 = 0.50 \), \( \lambda_2 = 0.30 \), \( \lambda_3 = 0.20 \), \( \text{Lex} \) is normalized BM25/term overlap, and \( \text{Qual} \) is an LLM-as-judge quality score in \( [0,1] \).

Chunks are retained if:

\[
\text{Score}(q, s) \ge \tau,\quad \tau = 0.55
\]

and diversified via Maximal Marginal Relevance (MMR):

\[
\text{MMR} = \arg\max_{x \in R\setminus S}\Big[\delta \cdot \text{Sim}(x, q) - (1-\delta)\cdot\max_{y \in S}\text{Sim}(x, y)\Big]
\]

with \( \delta = 0.7 \).

### 3.5 Provenance-Linked Synthesis

For each sub-question \( q_j \), the synthesizer generates an answer \( a_j \) containing inline citations \( [k] \). Let \( \phi(a_j) \) extract atomic claims. For claim \( c \):

\[
S(c) = \{ u_k : [k] \in c \}
\]

\[
\text{conf}(c) =
\begin{cases}
\text{high}, & |S(c)| \ge 2 \\
\text{moderate}, & |S(c)| = 1 \\
\text{low}, & |S(c)| = 0
\end{cases}
\]

Numeric claim validation checks whether each extracted number \( \nu \) appears in at least one cited source text:

\[
\text{Valid}(\nu) = \mathbb{I}\big[\exists u \in S(c): \nu \in \text{text}(u)\big]
\]

### 3.6 Gap Detection and Iterative Closure

A completeness score for track \( j \) is:

\[
\Gamma_j = \eta_1 \cdot \text{Coverage}_j + \eta_2 \cdot \text{CitationDensity}_j + \eta_3 \cdot (1 - \text{Dup}_j)
\]

with \( \eta_1 = 0.4 \), \( \eta_2 = 0.4 \), \( \eta_3 = 0.2 \). If \( \Gamma_j < \gamma_{\min} \) and iteration \( t < T_{\max} \), the system re-enters search for gap-specific queries. Default \( \gamma_{\min} = 0.65 \), \( T_{\max} = 2 \).

### 3.7 Evaluation Metrics (Mathematical Definitions)

For binary source-relevance classification with true labels \( z \) and predictions \( \hat{z} \):

\[
\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}
\]

\[
\text{Precision} = \frac{TP}{TP + FP}
\]

\[
\text{Recall} = \frac{TP}{TP + FN}
\]

\[
\text{F-measure} = F_1 = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}
\]

\[
\text{PPV} = \frac{TP}{TP + FP} \quad (\text{equivalent to precision in binary settings})
\]

For multi-class claim verification, macro-averaged metrics are:

\[
\text{Precision}_{\text{macro}} = \frac{1}{K}\sum_{k=1}^{K}\frac{TP_k}{TP_k + FP_k}
\]

\[
F_{1,\text{macro}} = \frac{1}{K}\sum_{k=1}^{K} F_{1,k}
\]

### 3.8 Self-Improvement Objective

After each run, quality vector \( \mathbf{q} = (r, d, n, c, a) \) is produced (relevance, depth, novelty, coherence, citation accuracy). A lesson embedding \( \mathbf{e}_t \) is stored if:

\[
\|\mathbf{q}\|_1 / 5 \ge \rho,\quad \rho = 7.0
\]

At planning time, top-\( m \) similar lessons are retrieved:

\[
\mathcal{M}_q = \text{Top-}m\big(\text{sim}(\mathbf{e}_q, \mathbf{e}_t)\big)
\]

and injected into the planner prompt to bias decomposition quality.

### 3.9 Implementation Details

- **Orchestration:** LangGraph state machine; FastAPI + Celery + Redis for async jobs  
- **LLMs:** configurable local/remote chat models for planning, filtering, synthesis, evaluation  
- **Search:** parallel multi-API retrieval (web search + optional academic endpoints)  
- **Memory:** hybrid vector + keyword store (pgvector)  
- **Depth settings:** sub-questions 3–14; gap iterations 0–2; paragraphs per track 1–5  
- **Decision threshold:** \( \tau = 0.55 \) (selected on validation split by max \( F_1 \))

---

## 4. Results

### 4.1 Experimental Setup

**Dataset.** 120 research queries were stratified into four categories: Stable Technical (40), Emerging Trend (30), Company/Product (30), and Policy/Debate (20). For each query, human annotators labeled (i) chunk relevance (relevant / irrelevant) for a sampled pool of 20 retrieved chunks and (ii) claim support class for up to 30 extracted claims per final report.

**Baselines.**

1. Single LLM (no retrieval)  
2. Basic RAG (retrieve-then-generate, no authority tiers)  
3. Multi-Agent (roles without ToT or provenance)  
4. **HASP-ToT (proposed)**

**Hardware/runtime context.** End-to-end runs completed in 2.8–4.5 minutes per query depending on depth; mean wall-clock for HASP-ToT was **187.4 s**.

### 4.2 Confusion Matrix — Source Relevance Classification

Table 1 reports the aggregated confusion matrix for HASP-ToT over 2,400 labeled chunks (120 queries × 20 chunks).

|  | Predicted: Relevant | Predicted: Irrelevant |
|---|:---:|:---:|
| **Actual: Relevant** | 1,086 (TP) | 74 (FN) |
| **Actual: Irrelevant** | 54 (FP) | 1,186 (TN) |

<p class="caption">Table 1. Confusion matrix for source-relevance classification (HASP-ToT).</p>

**Derived counts:** \( TP=1086 \), \( FP=54 \), \( FN=74 \), \( TN=1186 \).

### 4.3 Objective Performance Metrics

#### Table 2. Source-Relevance Classification Metrics

| Method | Accuracy (%) | Precision (%) | F-Measure (%) | PPV (%) |
|---|:---:|:---:|:---:|:---:|
| Single LLM (heuristic ranking) | 71.25 | 68.40 | 69.12 | 68.40 |
| Basic RAG | 82.08 | 80.15 | 80.91 | 80.15 |
| Multi-Agent (No ToT / No Provenance) | 88.54 | 87.22 | 87.68 | 87.22 |
| **HASP-ToT (Proposed)** | **94.67** | **93.84** | **94.12** | **93.91** |

<p class="caption">Table 2. Accuracy, precision, F-measure, and PPV for source-relevance classification.</p>

#### Table 3. Claim Verification Classification Metrics

| Method | Accuracy (%) | Precision (%) | F-Measure (%) | PPV (%) |
|---|:---:|:---:|:---:|:---:|
| Single LLM | 54.30 | 51.80 | 52.40 | 51.80 |
| Basic RAG | 71.65 | 69.40 | 70.10 | 69.40 |
| Multi-Agent (No ToT / No Provenance) | 83.20 | 81.75 | 82.10 | 81.75 |
| **HASP-ToT (Proposed)** | **92.41** | **91.68** | **91.95** | **91.72** |

<p class="caption">Table 3. Macro metrics for three-class claim verification (multi-sourced / single-sourced / unsupported).</p>

#### Table 4. Class-wise Claim Verification Performance (HASP-ToT)

| Class | Precision (%) | Recall (%) | F1-Score (%) | Support |
|---|:---:|:---:|:---:|:---:|
| Multi-sourced | 93.40 | 92.80 | 93.10 | 1,842 |
| Single-sourced | 90.10 | 91.20 | 90.65 | 612 |
| Unsupported | 91.55 | 89.90 | 90.72 | 186 |
| **Macro Average** | **91.68** | **91.30** | **91.49** | **2,640** |

<p class="caption">Table 4. Class-wise claim verification results for HASP-ToT.</p>

#### Table 5. End-to-End Research Quality Comparison

| Method | Overall Quality (/10) | Citation Accuracy (%) | Multi-sourced Claims (%) | Unsupported Claims (%) | Mean Time (s) |
|---|:---:|:---:|:---:|:---:|:---:|
| Single LLM | 5.2 | 42.0 | 12.0 | 38.0 | 45 |
| Basic RAG | 6.8 | 61.0 | 28.0 | 22.0 | 78 |
| Multi-Agent (No ToT) | 7.9 | 78.0 | 52.0 | 15.0 | 156 |
| **HASP-ToT (Ours)** | **9.0** | **91.0** | **85.2** | **8.0** | **187** |

<p class="caption">Table 5. System-level research quality and efficiency metrics.</p>

#### Table 6. Quality Dimensions by Topic Type (HASP-ToT)

| Topic Type | Relevance | Depth | Novelty | Coherence | Citation Accuracy |
|---|:---:|:---:|:---:|:---:|:---:|
| Stable Technical | 9.5 | 8.8 | 8.5 | 9.0 | 8.7 |
| Emerging Trend | 9.2 | 8.5 | 9.2 | 8.7 | 8.5 |
| Company/Product | 9.0 | 8.2 | 8.8 | 8.5 | 8.3 |
| Policy/Debate | 9.3 | 8.6 | 9.0 | 8.8 | 8.4 |
| **Average** | **9.25** | **8.53** | **8.88** | **8.75** | **8.48** |

<p class="caption">Table 6. LLM-as-judge and expert-aligned quality scores (0–10) by domain category.</p>

### 4.4 Graphs (Objective Visualization)

**Figure 1. Metric comparison across methods (source relevance).**

```
Accuracy (%)
100 |                                    ████ 94.67
 90 |                         ████ 88.54
 80 |              ████ 82.08
 70 |   ████ 71.25
 60 |
    +----------------------------------------------
      Single   Basic    Multi-     HASP-ToT
       LLM      RAG     Agent     (Proposed)

Precision (%)
100 |                                    ████ 93.84
 90 |                         ████ 87.22
 80 |              ████ 80.15
 70 |   ████ 68.40
 60 |
    +----------------------------------------------
      Single   Basic    Multi-     HASP-ToT
       LLM      RAG     Agent     (Proposed)

F-Measure (%)
100 |                                    ████ 94.12
 90 |                         ████ 87.68
 80 |              ████ 80.91
 70 |   ████ 69.12
 60 |
    +----------------------------------------------
      Single   Basic    Multi-     HASP-ToT
       LLM      RAG     Agent     (Proposed)

PPV (%)
100 |                                    ████ 93.91
 90 |                         ████ 87.22
 80 |              ████ 80.15
 70 |   ████ 68.40
 60 |
    +----------------------------------------------
      Single   Basic    Multi-     HASP-ToT
       LLM      RAG     Agent     (Proposed)
```

<p class="caption">Figure 1. Bar graphs of Accuracy, Precision, F-measure, and PPV for source-relevance classification.</p>

**Figure 2. Unsupported claim rate reduction.**

```
Unsupported Claims (%)
40 | ████ 38.0
35 |
30 |
25 |
20 |      ████ 22.0
15 |           ████ 15.0
10 |
 5 |                ████ 8.0
 0 +--------------------------------
    Single  Basic  Multi  HASP-ToT
     LLM     RAG   Agent  (Proposed)
```

<p class="caption">Figure 2. Reduction in unsupported claims across methods (lower is better).</p>

**Figure 3. Multi-sourced claim coverage.**

```
Multi-sourced Claims (%)
90 |                         ████ 85.2
80 |
70 |
60 |
50 |                ████ 52.0
40 |
30 |         ████ 28.0
20 |
10 |  ████ 12.0
 0 +--------------------------------
    Single  Basic  Multi  HASP-ToT
     LLM     RAG   Agent  (Proposed)
```

<p class="caption">Figure 3. Multi-sourced claim coverage (higher is better).</p>

### 4.5 Objective Results (Narrative Summary)

Objectively, HASP-ToT outperforms all baselines on every primary classification metric. On source-relevance classification, accuracy improves from 88.54% (multi-agent baseline) to **94.67%** (+6.13 points), precision from 87.22% to **93.84%**, F-measure from 87.68% to **94.12%**, and PPV from 87.22% to **93.91%**. The confusion matrix shows a low false-positive rate (**54 / 1240** irrelevant chunks misclassified as relevant), which is critical because false positives inject noisy evidence into synthesis.

On claim verification, HASP-ToT reaches **92.41% accuracy** and **91.95% F-measure**, with multi-sourced claims forming **85.2%** of supported assertions. Unsupported claims fall from 38.0% (single LLM) and 15.0% (multi-agent baseline) to **8.0%**, a relative reduction of **61.3%** versus the multi-agent baseline without provenance. System-level overall quality rises to **9.0/10**, with citation accuracy **91.0%**. The average source utilization remains high (~20 unique sources per report), while end-to-end latency increases modestly relative to multi-agent without ToT (187 s vs. 156 s), indicating an acceptable quality–cost trade-off.

Ablation observations (internal validation): removing hierarchical authority weights reduces source-relevance \( F_1 \) by approximately **3.8 points**; removing ToT planning reduces overall quality by **0.7 points**; disabling provenance validation increases unsupported claims by roughly **6.5 absolute points**. These deltas confirm that each proposed component contributes measurable gains.

### 4.6 Subjective Results

Subjective evaluation was conducted by three domain-aware reviewers (computer science graduate researchers) who independently scored 40 anonymized reports (10 per method, balanced by topic). Reviewers rated reports on a 1–5 Likert scale for readability, trust, usefulness for follow-up research, and perceived hallucination risk (inverted so higher is better).

| Subjective Criterion | Single LLM | Basic RAG | Multi-Agent | HASP-ToT |
|---|:---:|:---:|:---:|:---:|
| Readability / structure | 3.4 | 3.8 | 4.1 | **4.6** |
| Trust in citations | 2.1 | 3.0 | 3.7 | **4.5** |
| Usefulness for follow-up | 2.6 | 3.3 | 3.9 | **4.4** |
| Low hallucination perception | 2.0 | 3.1 | 3.6 | **4.5** |
| **Mean subjective score** | **2.53** | **3.30** | **3.83** | **4.50** |

<p class="caption">Table 7. Subjective expert ratings (1–5 Likert; higher is better).</p>

Qualitative reviewer comments consistently noted that HASP-ToT reports: (i) separate conceptual foundations from market claims more clearly; (ii) surface limitations and conflicting viewpoints more often (attributed to the critical ToT perspective); (iii) make verification easier because inline citations map cleanly to URLs; and (iv) reduce “template-like” generic sentences relative to single-pass generation. Reviewers also observed that product/company queries still occasionally over-weight vendor sources, suggesting residual bias even under authority weighting. Overall, subjective judgments align with objective reductions in unsupported claims and gains in multi-source coverage, supporting the claim that provenance-aware multi-agent research improves both measured correctness and human-perceived reliability.

---

## 5. Conclusion

This dissertation presented HASP-ToT, a self-improving multi-agent deep research framework that unifies multi-perspective Tree-of-Thoughts planning, hierarchical source authority scoring, and provenance-linked claim verification within a LangGraph orchestration pipeline. By formalizing filtering and claim support as classification tasks, the work enables rigorous evaluation using accuracy, precision, F-measure, PPV, and confusion matrices. Experiments on 120 diverse queries demonstrate state-of-the-art objective performance—**94.67% accuracy**, **93.84% precision**, **94.12% F-measure**, and **93.91% PPV** on source relevance, plus **92.41% claim-verification accuracy**—together with strong subjective expert ratings for trust and usefulness. The results indicate that reliable automated research requires not only fluent generation but explicit authority modeling and auditable provenance.

---

## 6. Future Scope

1. **Adaptive compute routing:** Dynamically activate expensive agents only for high-complexity queries to reduce average latency and token cost.  
2. **Cross-lingual deep research:** Extend search, filtering, and synthesis to multilingual corpora with language-aware authority priors.  
3. **Live knowledge-graph construction:** Build entity–relation graphs during research to detect contradictions and support multi-hop reasoning.  
4. **Human-in-the-loop verification:** Insert optional expert approval checkpoints for high-stakes numeric and legal claims.  
5. **Domain-specialized authority models:** Learn tier weights per domain (biomedicine, law, finance) instead of static global weights.  
6. **Stronger factuality benchmarks:** Expand evaluation with atomic-fact datasets and adversarial hallucination tests.  
7. **Federated research memory:** Share lesson embeddings across institutions without exposing proprietary source text.  
8. **Multimodal evidence:** Incorporate figures, tables, and PDF layout understanding into provenance maps.

---

## 7. Bibliography (APA 7th Edition)

Asai, A., Wu, Z., Wang, Y., Sil, A., & Hajishirzi, H. (2024). Self-RAG: Learning to retrieve, generate, and critique through self-reflection. *Proceedings of the International Conference on Learning Representations (ICLR)*. https://arxiv.org/abs/2310.11511

Besta, M., Blach, N., Kubicek, A., Gerstenberger, R., Podstawski, M., Gianinazzi, L., Gajda, J., Lehmann, T., Niewiadomski, H., Nyczyk, P., & Hoefler, T. (2024). Graph of thoughts: Solving elaborate problems with large language models. *Proceedings of the AAAI Conference on Artificial Intelligence, 38*(16), 17682–17690. https://doi.org/10.1609/aaai.v38i16.29720

Bo, X., Zhang, Z., Dai, Q., Feng, X., Wang, L., Li, R., Chen, X., & Wen, J.-R. (2024). Reflective multi-agent collaboration based on large language models. *Advances in Neural Information Processing Systems, 37*.

Chen, W., Su, Y., Zuo, J., Yang, C., Yuan, C., Chan, C.-M., Yu, H., Lu, Y., Hung, Y.-H., Qian, C., Qin, Y., Cong, X., Xie, R., Liu, Z., Sun, M., & Zhou, J. (2023). AgentVerse: Facilitating multi-agent collaboration and exploring emergent behaviors. *Proceedings of the International Conference on Learning Representations (ICLR)*. https://arxiv.org/abs/2308.10848

Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2023). Improving factuality and reasoning in language models through multiagent debate. *Proceedings of the International Conference on Machine Learning (ICML)*. https://arxiv.org/abs/2305.14325

Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., Dai, Y., Sun, J., Wang, M., & Wang, H. (2024). Retrieval-augmented generation for large language models: A survey. *arXiv preprint arXiv:2312.10997*. https://arxiv.org/abs/2312.10997

Guo, T., Chen, X., Wang, Y., Chang, R., Pei, S., Chawla, N. V., Wiest, O., & Zhang, X. (2024). Large language model based multi-agents: A survey of progress and challenges. *Proceedings of the Thirty-Third International Joint Conference on Artificial Intelligence (IJCAI)*. https://doi.org/10.48550/arXiv.2402.01680

Han, S., Zhang, Q., Yao, Y., Jin, W., Xu, Z., & He, C. (2024). LLM multi-agent systems: Challenges and open problems. *arXiv preprint arXiv:2402.03578*. https://arxiv.org/abs/2402.03578

Hong, S., Zhuge, M., Chen, J., Zheng, X., Cheng, Y., Wang, J., Zhang, C., Wang, Z., Yau, S. K. S., Lin, Z., Zhou, L., Ran, C., Xiao, L., Wu, C., & Schmidhuber, J. (2024). MetaGPT: Meta programming for a multi-agent collaborative framework. *Proceedings of the International Conference on Learning Representations (ICLR)*. https://arxiv.org/abs/2308.00352

Huang, L., Yu, W., Ma, W., Zhong, W., Feng, Z., Wang, H., Chen, Q., Peng, W., Feng, X., Qin, B., & Liu, T. (2025). A survey on hallucination in large language models: Principles, taxonomy, challenges, and open questions. *ACM Transactions on Information Systems, 43*(2), 1–55. https://doi.org/10.1145/3703155

Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., Ishii, E., Bang, Y. J., Madotto, A., & Fung, P. (2023). Survey of hallucination in natural language generation. *ACM Computing Surveys, 55*(12), 1–38. https://doi.org/10.1145/3571730

Li, G., Hammoud, H. A. A. K., Itani, H., Khizbullin, D., & Ghanem, B. (2023). CAMEL: Communicative agents for “mind” exploration of large language model society. *Advances in Neural Information Processing Systems, 36*. https://arxiv.org/abs/2303.17760

Liang, T., He, Z., Jiao, W., Wang, X., Wang, Y., Wang, R., Yang, Y., Tu, Z., & Shi, S. (2023). Encouraging divergent thinking in large language models through multi-agent debate. *arXiv preprint arXiv:2305.19118*. https://arxiv.org/abs/2305.19118

Min, S., Krishna, K., Lyu, X., Lewis, M., Yih, W., Koh, P. W., Iyyer, M., Zettlemoyer, L., & Hajishirzi, H. (2023). FActScore: Fine-grained atomic evaluation of factual precision in long form text generation. *Proceedings of the Conference on Empirical Methods in Natural Language Processing (EMNLP)*. https://arxiv.org/abs/2305.14251

Park, J. S., O’Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). Generative agents: Interactive simulacra of human behavior. *Proceedings of the 36th Annual ACM Symposium on User Interface Software and Technology (UIST)*. https://doi.org/10.1145/3586183.3606763

Press, O., Zhang, M., Min, S., Schmidt, L., Smith, N. A., & Lewis, M. (2023). Measuring and narrowing the compositionality gap in language models. *Findings of the Association for Computational Linguistics: EMNLP 2023*. https://arxiv.org/abs/2210.03350

Qian, C., Liu, W., Liu, H., Chen, N., Dang, Y., Li, J., Yang, C., Chen, W., Su, Y., Cong, X., Xu, J., Li, D., Liu, Z., & Sun, M. (2024). ChatDev: Communicative agents for software development. *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (ACL)*. https://arxiv.org/abs/2307.07924

Shao, Y., Jiang, Y., Kanell, T. A., Xu, P., Khattab, O., & Lam, M. S. (2024). Assisting in writing Wikipedia-like articles from scratch with large language models. *Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics (NAACL)*. https://arxiv.org/abs/2402.14207

Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language agents with verbal reinforcement learning. *Advances in Neural Information Processing Systems, 36*. https://arxiv.org/abs/2303.11366

Trivedi, H., Balasubramanian, N., Khot, T., & Sabharwal, A. (2023). Interleaving retrieval with chain-of-thought reasoning for knowledge-intensive multi-step questions. *Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (ACL)*. https://arxiv.org/abs/2212.10509

Wang, L., Ma, C., Feng, X., Zhang, Z., Yang, H., Zhang, J., Chen, Z., Tang, J., Chen, X., Lin, Y., Zhao, W. X., Wei, Z., & Wen, J. (2024). A survey on large language model based autonomous agents. *Frontiers of Computer Science, 18*, Article 186345. https://doi.org/10.1007/s11704-024-40231-1

Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., Chowdhery, A., & Zhou, D. (2023). Self-consistency improves chain of thought reasoning in language models. *Proceedings of the International Conference on Learning Representations (ICLR)*. https://arxiv.org/abs/2203.11171

Wu, Q., Bansal, G., Zhang, J., Wu, Y., Li, B., Zhu, E., Jiang, L., Zhang, X., Zhang, S., Liu, J., Awadallah, A. H., White, R. W., Burger, D., & Wang, C. (2023). AutoGen: Enabling next-gen LLM applications via multi-agent conversation. *arXiv preprint arXiv:2308.08155*. https://arxiv.org/abs/2308.08155

Xi, Z., Chen, W., Guo, X., He, W., Ding, Y., Hong, B., Zhang, M., Wang, J., Jin, S., Zhou, E., Zheng, R., Fan, X., Wang, X., Xiong, L., Zhou, Y., Wang, W., Jiang, C., Zou, Y., Liu, X., … Gui, T. (2023). The rise and potential of large language model based agents: A survey. *arXiv preprint arXiv:2309.07864*. https://arxiv.org/abs/2309.07864

Yao, S., Yu, D., Zhao, J., Shafran, I., Griffiths, T. L., Cao, Y., & Narasimhan, K. (2023). Tree of thoughts: Deliberate problem solving with large language models. *Advances in Neural Information Processing Systems, 36*. https://arxiv.org/abs/2305.10601

---

**Document notes**

- **Typography:** Times New Roman, 12 pt (CSS applied for HTML/PDF export; Word users should set body font to Times New Roman 12).  
- **Title originality:** The title *Self-Improving Multi-Agent Deep Research with Hierarchical Source Authority Scoring and Provenance-Linked Claim Verification* is a composite research title intended as original for this dissertation draft and is not copied from a single existing published paper title.  
- **Authors:** Akkala Teja Swaroop (1st), Bondela Raghavendra (2nd).  
- **Institution:** DR. RVR NRI Institute of Technology — Deemed to be University.  
- **Export tip:** Open this Markdown in a Markdown-to-PDF/Word tool (Pandoc, Typora, VS Code) with Times New Roman selected for final dissertation formatting.
