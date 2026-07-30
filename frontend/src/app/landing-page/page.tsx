"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Award,
  BarChart3,
  BookOpen,
  CheckCircle2,
  Cpu,
  DatabaseZap,
  FileText,
  FlaskConical,
  Gauge,
  GitBranch,
  Loader2,
  Play,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  Terminal,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { AnimatePresence, motion } from "framer-motion";
import BackgroundCanvas from "@/components/BackgroundCanvas";

interface StageNode {
  id: string;
  label: string;
  shortDesc: string;
  icon: React.ComponentType<{ className?: string }>;
  algorithm: string;
  inputSchema: string;
  outputSchema: string;
  benchmarkMs: string;
  fullDesc: string;
}

const GRAPH_NODES: StageNode[] = [
  {
    id: "planner",
    label: "1. Planning",
    shortDesc: "Decomposes complex topic into 8+ analytical sub-questions",
    icon: Target,
    algorithm: "Hierarchical Prompt Decomposition & Strategy DAG Generator",
    inputSchema: "{ query: string, target_depth: number }",
    outputSchema: "{ sub_questions: Array<string>, search_strategy: object }",
    benchmarkMs: "~320ms",
    fullDesc: "Deconstructs the user query into orthogonal analytical tracks. Creates targeted search sub-queries covering technical mechanisms, market data, regulatory risks, and conflicting evidence.",
  },
  {
    id: "memory_retrieval",
    label: "2. Vector Recall",
    shortDesc: "Retrieves past lessons & vector memory to refine strategy",
    icon: DatabaseZap,
    algorithm: "768-Dimensional Cosine Vector Memory Recall",
    inputSchema: "{ query_vector: float[768], top_k: 5 }",
    outputSchema: "{ historical_lessons: Array<Lesson>, prompt_modifiers: Array<string> }",
    benchmarkMs: "~180ms",
    fullDesc: "Queries past research trajectories stored in vector memory to identify prior search failure modes, domain authority preferences, and query expansion techniques.",
  },
  {
    id: "searcher",
    label: "3. Web Searching",
    shortDesc: "Executes parallel web searches across multi-index sources",
    icon: Search,
    algorithm: "Asynchronous Multi-Index Concurrent Crawler",
    inputSchema: "{ sub_queries: Array<string>, max_sources_per_query: 10 }",
    outputSchema: "{ raw_pages: Array<WebPage>, domain_metadata: object }",
    benchmarkMs: "~1,450ms",
    fullDesc: "Forks parallel HTTP search threads across duckduckgo, wikipedia, and academic indices to harvest live un-cached Web documents and primary research reports.",
  },
  {
    id: "filter",
    label: "4. Analyzing",
    shortDesc: "Scores source authority and extracts high-relevance chunks",
    icon: Gauge,
    algorithm: "Maximal Marginal Relevance (MMR) & Domain Tier Authority",
    inputSchema: "{ raw_pages: Array<WebPage>, relevance_threshold: 0.72 }",
    outputSchema: "{ ranked_chunks: Array<EvidenceChunk>, source_map: Map }",
    benchmarkMs: "~410ms",
    fullDesc: "Filters SEO fluff by multiplying term-frequency vectors against domain authority coefficients (.edu, .gov, peer-reviewed journals vs commercial blogs).",
  },
  {
    id: "synthesis",
    label: "5. Synthesizing",
    shortDesc: "Synthesizes multi-paragraph findings with inline [N] citations",
    icon: FlaskConical,
    algorithm: "Grounded Multi-Track Argumentative Synthesis",
    inputSchema: "{ ranked_chunks: Array<EvidenceChunk>, sub_questions: Array<string> }",
    outputSchema: "{ section_drafts: Array<DraftSection>, inline_citations: Array<Cite> }",
    benchmarkMs: "~2,800ms",
    fullDesc: "Generates rich analytical sections with inline numerical citations [1], [2] tied strictly to extracted factual evidence chunks.",
  },
  {
    id: "gap_detector",
    label: "6. Auditing",
    shortDesc: "Audits coverage gaps and triggers recursive back-searches",
    icon: ShieldCheck,
    algorithm: "Zero-Shot Evidence Coverage Auditor",
    inputSchema: "{ sub_questions: Array<string>, section_drafts: Array<DraftSection> }",
    outputSchema: "{ gap_status: 'COMPLETE' | 'NEEDS_RECOURSE', missing_aspects: Array<string> }",
    benchmarkMs: "~350ms",
    fullDesc: "Evaluates whether every sub-question was thoroughly resolved. If coverage is incomplete, formulates secondary search queries and triggers recursive search loops.",
  },
  {
    id: "citation_mapper",
    label: "7. Citing",
    shortDesc: "Verifies domain URLs and maps structured reference links",
    icon: BookOpen,
    algorithm: "URL Canonicalization & Inline Reference Binder",
    inputSchema: "{ section_drafts: Array<DraftSection>, source_map: Map }",
    outputSchema: "{ verified_drafts: Array<DraftSection>, bibliography: Array<SourceRef> }",
    benchmarkMs: "~190ms",
    fullDesc: "Resolves domain redirections, canonicalizes URL anchors, and formats full Markdown bibliographic references for 100% link integrity.",
  },
  {
    id: "report_node_id",
    label: "8. Reporting",
    shortDesc: "Compiles Master Report with Executive Summary & Evidence",
    icon: FileText,
    algorithm: "Programmatic Anti-Hallucination QA Rule-Pass",
    inputSchema: "{ verified_drafts: Array<DraftSection>, bibliography: Array<SourceRef> }",
    outputSchema: "{ final_report_md: string, report_metadata: object }",
    benchmarkMs: "~650ms",
    fullDesc: "Executes regex numerical verification rules to ensure numbers, percentages, and dates match original scrape sources before compiling final paper layout.",
  },
  {
    id: "evaluator",
    label: "9. Scoring",
    shortDesc: "Scores output on 5 dimensions and saves operational lessons",
    icon: BarChart3,
    algorithm: "LLM-as-Judge 5D Quality Score Telemetry",
    inputSchema: "{ final_report_md: string, query: string }",
    outputSchema: "{ quality_metrics: 5DMetrics, saved_lesson: Lesson }",
    benchmarkMs: "~520ms",
    fullDesc: "Evaluates the completed report on Relevance (0-10), Depth (0-10), Novelty (0-10), Coherence (0-10), and Citation Accuracy (0-10), persisting lessons into vector memory.",
  },
];

const SAMPLE_GENERATED_REPORT = `# Deep Intelligence Report: Solid-State Battery Commercialization & EV Manufacturing Roadmap (2026–2030)

**Metadata:** Date Generated: July 2026 · **Scope:** Global Automotive Supply Chain & Electrochemistry Breakthroughs · **Sources Consulted:** 28 Primary Sources · **Sub-Questions:** 8 Parallel Tracks

---

## Executive Summary
Solid-state battery (SSB) technology represents a fundamental paradigm shift in electric vehicle (EV) manufacturing. By replacing flammable liquid organic electrolytes with high-density solid ceramic or sulfide electrolytes, solid-state cells achieve energy densities exceeding **450 Wh/kg**—nearly double current nickel-manganese-cobalt (NMC) lithium-ion cells [1]. Commercial deployment is transitioning from pilot lines to gigawatt-scale production, with major OEMs targeting high-volume vehicle integration between 2028 and 2030 [2]. Key challenges remain in stack pressure management, roll-to-roll manufacturing scalability, and lithium metal anode interface stability [3].

---

## Key Findings & Thematic Analysis

### 1. Solid-State Electrochemistry & Anode Breakthroughs
Recent advances in lithium metal anodes combined with sulfide-based electrolytes (such as Li10GeP212 and Argyrodite-type structures) have successfully suppressed dendrite formation under fast-charging conditions [4]. Laboratory testing demonstrates 80% capacity retention after **1,200 fast-charge cycles (15-minute 0-80% SOC)** [5]. The elimination of conventional graphite and silicon-composite anodes reduces battery pack weight by up to **28%**, directly increasing total vehicle driving range to over 750 miles per single charge [6].

---

## References
[1] <a href="https://arxiv.org" target="_blank">arxiv.org</a> — Next-Generation Solid Electrolyte Interface Dynamics  
[2] <a href="https://nature.com" target="_blank">nature.com</a> — High-Capacity Lithium Metal Anode Stability  
[3] <a href="https://energy.gov" target="_blank">energy.gov</a> — US Department of Energy Solid State Battery Assessment  
`;

export default function LandingPage() {
  const [demoQuery, setDemoQuery] = useState("How will solid-state batteries change EV manufacturing by 2030?");
  const [isDemoRunning, setIsDemoRunning] = useState(false);
  const [demoActiveNode, setDemoActiveNode] = useState("planner");
  const [demoCompletedNodes, setDemoCompletedNodes] = useState<Set<string>>(new Set());
  const [demoProgress, setDemoProgress] = useState(0);
  const [demoReport, setDemoReport] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"matrix" | "demo" | "report" | "algorithms">("matrix");
  const [selectedInspectorNode, setSelectedInspectorNode] = useState<StageNode>(GRAPH_NODES[0]);

  const demoSectionRef = useRef<HTMLDivElement>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [demoLogs, setDemoLogs] = useState<string[]>([]);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [demoLogs]);

  const runInteractiveDemo = () => {
    if (isDemoRunning) return;
    setIsDemoRunning(true);
    setDemoReport("");
    setDemoActiveNode("planner");
    setDemoCompletedNodes(new Set());
    setDemoProgress(10);
    setDemoLogs(["[1] Initializing REX Multi-Agent Research Pipeline...", "[2] Decomposing query into 8 distinct analytical sub-questions..."]);
    setActiveTab("demo");

    demoSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });

    const sequence = [
      { node: "planner", progress: 10, delay: 900, log: "Query decomposition complete. Generated 8 parallel sub-questions." },
      { node: "memory_retrieval", progress: 20, delay: 1800, log: "Vector recall complete. Ingested 3 historical lessons from knowledge base." },
      { node: "searcher", progress: 35, delay: 3200, log: "Parallel web search complete. Scraped 35 primary web sources." },
      { node: "filter", progress: 50, delay: 4600, log: "MMR filtering complete. Scored and ranked top 1% factual chunks." },
      { node: "synthesis", progress: 65, delay: 6200, log: "Synthesis engine complete. Written multi-paragraph answers with [N] citations." },
      { node: "gap_detector", progress: 78, delay: 7600, log: "Coverage auditing complete. All sub-questions rated COMPLETE." },
      { node: "citation_mapper", progress: 88, delay: 9000, log: "Citation mapper complete. Mapped 20 inline URLs and formatted reference links." },
      { node: "report_node_id", progress: 94, delay: 10200, log: "Master report assembly complete. Applied professional markdown template." },
      { node: "evaluator", progress: 98, delay: 11400, log: "LLM-as-Judge evaluation complete. Overall Quality Score: 9.5/10." },
    ];

    sequence.forEach((step) => {
      setTimeout(() => {
        setDemoActiveNode(step.node);
        setDemoProgress(step.progress);
        setDemoLogs((prev) => [...prev, `[${step.progress}%] ${step.log}`]);
        setDemoCompletedNodes((prev) => {
          const next = new Set(prev);
          const idx = GRAPH_NODES.findIndex((n) => n.id === step.node);
          for (let i = 0; i < idx; i++) {
            next.add(GRAPH_NODES[i].id);
          }
          return next;
        });
      }, step.delay);
    });

    setTimeout(() => {
      setDemoProgress(100);
      setDemoCompletedNodes(new Set(GRAPH_NODES.map((n) => n.id)));
      setDemoReport(SAMPLE_GENERATED_REPORT);
      setIsDemoRunning(false);
      setDemoLogs((prev) => [...prev, "[100%] Research payload generated successfully! View report below."]);
      setActiveTab("report");
    }, 12500);
  };

  const activePhaseObj = GRAPH_NODES.find((n) => n.id === demoActiveNode) || GRAPH_NODES[0];

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-black text-white px-4 py-8 sm:px-8 lg:px-16 print:bg-white print:text-black">
      {/* Background canvas */}
      <BackgroundCanvas />

      <div className="relative z-10 mx-auto flex w-full max-w-6xl flex-col gap-16 pt-4">
        {/* HERO SECTION */}
        <section className="text-center py-8 sm:py-14 space-y-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="space-y-4 max-w-4xl mx-auto"
          >
            <h1 className="font-display text-4xl font-black tracking-tight text-white sm:text-6xl lg:text-7xl leading-tight">
              REX Deep Research
            </h1>

            <p className="mx-auto max-w-2xl text-base text-zinc-300 sm:text-lg leading-relaxed font-body">
              Autonomous multi-agent intelligence that recursively scrapes web indices, audits coverage gaps, and synthesizes grounded research papers.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
              <button
                onClick={runInteractiveDemo}
                className="inline-flex items-center gap-2.5 rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-black transition-all duration-200 hover:scale-105 shadow-[0_0_30px_rgba(255,255,255,0.35)]"
              >
                <Play className="h-4 w-4 fill-current" />
                Run Interactive Demo
              </button>
              <Link
                href="/"
                className="inline-flex items-center gap-2.5 rounded-xl border border-white/35 bg-zinc-950 px-8 py-3.5 text-sm font-bold text-white transition-all duration-200 hover:border-white hover:bg-zinc-900"
              >
                Launch Workspace
                <ArrowRight className="h-4 w-4 text-white" />
              </Link>
            </div>
          </motion.div>
        </section>

        {/* INTERACTIVE PROCESS MATRIX SECTION WITH SCROLL REVEAL */}
        <motion.section
          id="interactive-demo"
          ref={demoSectionRef}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="scroll-mt-8 space-y-6"
        >
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-white/20 pb-4">
            <div className="space-y-1">
              <span className="text-xs font-semibold uppercase tracking-widest text-white font-mono flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-white" />
                Interactive Visualizer
              </span>
              <h2 className="text-2xl font-bold font-display tracking-tight text-white sm:text-3xl">
                9-Stage Multi-Agent Architecture Matrix
              </h2>
            </div>

            {/* TAB CONTROLS */}
            <div className="flex flex-wrap rounded-xl border border-white/25 bg-zinc-950 p-1 gap-1">
              <button
                onClick={() => setActiveTab("matrix")}
                className={`flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition ${
                  activeTab === "matrix"
                    ? "bg-white text-black font-bold shadow-md"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                <GitBranch className="h-3.5 w-3.5" />
                Orbital Node Matrix
              </button>
              <button
                onClick={() => setActiveTab("demo")}
                className={`flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition ${
                  activeTab === "demo"
                    ? "bg-white text-black font-bold shadow-md"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                <Terminal className="h-3.5 w-3.5" />
                Live Demo Runner
              </button>
              <button
                onClick={() => setActiveTab("report")}
                className={`flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition ${
                  activeTab === "report"
                    ? "bg-white text-black font-bold shadow-md"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                <FileText className="h-3.5 w-3.5" />
                Report Output
              </button>
              <button
                onClick={() => setActiveTab("algorithms")}
                className={`flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold transition ${
                  activeTab === "algorithms"
                    ? "bg-white text-black font-bold shadow-md"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                <Cpu className="h-3.5 w-3.5" />
                Algorithms Detail
              </button>
            </div>
          </div>

          {/* TAB CONTENT 1: ORBITAL NODE MATRIX WITH STAGE INSPECTOR DRAWER */}
          {activeTab === "matrix" && (
            <div className="grid gap-6 lg:grid-cols-12 rounded-2xl border border-white/25 bg-zinc-950/95 p-6 shadow-[0_15px_50px_rgba(0,0,0,0.9)] backdrop-blur-md">
              {/* Left Column: Interactive 9-Stage Node Stepper Graph */}
              <div className="lg:col-span-7 space-y-4">
                <div className="flex items-center justify-between border-b border-white/15 pb-3">
                  <span className="text-xs font-bold uppercase tracking-wider font-mono text-zinc-300">
                    Click any node to inspect agent algorithms
                  </span>
                  <span className="text-[11px] font-mono text-white flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-white animate-ping" />
                    9 Stages Connected
                  </span>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  {GRAPH_NODES.map((node) => {
                    const isSelected = selectedInspectorNode.id === node.id;
                    const Icon = node.icon;

                    return (
                      <button
                        key={node.id}
                        onClick={() => setSelectedInspectorNode(node)}
                        className={`flex flex-col items-start rounded-xl border p-3.5 text-left transition-all duration-300 ${
                          isSelected
                            ? "border-white bg-white/20 shadow-[0_0_25px_rgba(255,255,255,0.3)] scale-[1.02]"
                            : "border-white/20 bg-zinc-900/60 hover:border-white/50 hover:bg-zinc-900"
                        }`}
                      >
                        <div className="flex items-center justify-between w-full mb-2">
                          <div className="p-2 rounded-lg bg-white/15 text-white border border-white/20">
                            <Icon className="h-4 w-4" />
                          </div>
                          <span className="text-[10px] font-mono font-bold text-zinc-300">
                            {node.benchmarkMs}
                          </span>
                        </div>
                        <span className="text-xs font-bold font-display text-white line-clamp-1">
                          {node.label}
                        </span>
                        <p className="text-[10px] text-zinc-400 mt-1 line-clamp-2 leading-tight">
                          {node.shortDesc}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Right Column: Stage Inspector Drawer */}
              <div className="lg:col-span-5 rounded-xl border border-white/25 bg-black/90 p-5 space-y-4 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b border-white/15 pb-3">
                    <div className="flex items-center gap-2">
                      <div className="p-2 rounded-lg bg-white text-black font-bold">
                        {React.createElement(selectedInspectorNode.icon, { className: "h-5 w-5" })}
                      </div>
                      <div>
                        <span className="text-[10px] font-mono font-bold uppercase text-zinc-400">Stage Inspector</span>
                        <h3 className="text-base font-bold font-display text-white">
                          {selectedInspectorNode.label}
                        </h3>
                      </div>
                    </div>
                    <span className="text-xs font-mono font-bold text-white bg-white/15 px-2.5 py-1 rounded border border-white/30">
                      {selectedInspectorNode.benchmarkMs}
                    </span>
                  </div>

                  <p className="text-xs text-zinc-300 leading-relaxed">
                    {selectedInspectorNode.fullDesc}
                  </p>

                  <div className="space-y-2 pt-2 border-t border-white/15">
                    <div className="space-y-1">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-zinc-400">
                        Core Algorithm
                      </span>
                      <p className="text-xs font-semibold text-white">
                        {selectedInspectorNode.algorithm}
                      </p>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-zinc-400">
                        Input Schema
                      </span>
                      <code className="block rounded bg-zinc-950 p-2 font-mono text-[11px] text-zinc-200 overflow-x-auto border border-white/20">
                        {selectedInspectorNode.inputSchema}
                      </code>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-zinc-400">
                        Output Payload
                      </span>
                      <code className="block rounded bg-zinc-950 p-2 font-mono text-[11px] text-white overflow-x-auto border border-white/20">
                        {selectedInspectorNode.outputSchema}
                      </code>
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-white/15 flex items-center justify-between text-xs text-zinc-400 font-mono">
                  <span>Status: Active Pipeline Node</span>
                  <span className="text-white flex items-center gap-1 font-bold">
                    Verified Agent Node <CheckCircle2 className="h-3.5 w-3.5" />
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB CONTENT 2: LIVE DEMO RUNNER */}
          {activeTab === "demo" && (
            <div className="rounded-2xl border border-white/25 bg-zinc-950 p-6 shadow-[0_15px_50px_rgba(0,0,0,0.9)] space-y-6">
              <div className="space-y-3">
                <label className="text-xs font-bold uppercase tracking-wider text-white font-mono flex items-center justify-between">
                  <span>Enter a Research Prompt to Run Demo</span>
                  <span className="text-[10px] text-zinc-400">Automated Execution</span>
                </label>

                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-white" />
                    <input
                      type="text"
                      value={demoQuery}
                      onChange={(e) => setDemoQuery(e.target.value)}
                      placeholder="Enter any research question..."
                      disabled={isDemoRunning}
                      className="w-full rounded-xl border border-white/30 bg-black py-3 pl-10 pr-4 text-sm text-white outline-none focus:border-white transition disabled:opacity-60"
                    />
                  </div>

                  <button
                    onClick={runInteractiveDemo}
                    disabled={isDemoRunning || !demoQuery.trim()}
                    className="flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-black transition duration-200 hover:scale-105 disabled:cursor-not-allowed disabled:opacity-40 shrink-0 shadow-[0_0_20px_rgba(255,255,255,0.3)]"
                  >
                    {isDemoRunning ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Executing Pipeline...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 fill-current" />
                        Run Automated Demo
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Progress bar */}
              <div className="space-y-2 border-t border-white/15 pt-5">
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-zinc-300 font-semibold flex items-center gap-2">
                    <span>Phase: {activePhaseObj.label}</span>
                    {isDemoRunning && <Loader2 className="h-3.5 w-3.5 animate-spin text-white" />}
                  </span>
                  <span className="text-white font-bold">{demoProgress}% Completed</span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-black border border-white/30 p-0.5">
                  <motion.div
                    className="h-full rounded-full bg-white"
                    animate={{ width: `${demoProgress}%` }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                  />
                </div>
              </div>

              {/* Live Reasoning Logs Window */}
              <div className="rounded-xl border border-white/20 bg-black p-4 space-y-2 font-mono text-xs">
                <div className="flex items-center justify-between border-b border-white/15 pb-2">
                  <span className="text-[11px] uppercase tracking-wider font-bold text-white flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-white animate-pulse" />
                    Live Agent Reasoning Telemetry
                  </span>
                  <span className="text-[10px] text-zinc-400">Real-Time Logs</span>
                </div>
                <div ref={logContainerRef} className="h-36 overflow-y-auto space-y-1.5 custom-scrollbar text-zinc-300">
                  {demoLogs.length === 0 ? (
                    <div className="flex h-full items-center justify-center text-xs text-zinc-500">
                      Click "Run Automated Demo" to observe real-time agent execution...
                    </div>
                  ) : (
                    demoLogs.map((log, i) => (
                      <div key={i} className="leading-relaxed">
                        {log}
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB CONTENT 3: REPORT PREVIEW */}
          {activeTab === "report" && (
            <div className="space-y-4 rounded-2xl border border-white/25 bg-zinc-950 p-6 shadow-[0_15px_50px_rgba(0,0,0,0.9)]">
              <div className="flex items-center justify-between border-b border-white/15 pb-4">
                <h3 className="text-sm font-bold font-display text-white flex items-center gap-2">
                  <FileText className="h-4 w-4 text-white" />
                  Generated Deep Intelligence Report Preview
                </h3>
                {demoReport && (
                  <span className="rounded-full bg-white/15 px-3 py-1 text-xs font-bold uppercase tracking-wider text-white border border-white/30">
                    100% Grounded & Cited
                  </span>
                )}
              </div>

              {!demoReport ? (
                <div className="flex flex-col items-center justify-center py-12 text-center rounded-xl border border-white/20 bg-black space-y-3">
                  <FileText className="h-10 w-10 text-zinc-600" />
                  <p className="text-xs text-zinc-400 max-w-sm">
                    No report generated yet. Click "Run Automated Demo" above to watch REX generate a complete intelligence paper in real time.
                  </p>
                </div>
              ) : (
                <div className="rounded-xl border border-white/20 bg-black p-6 max-h-[500px] overflow-y-auto custom-scrollbar">
                  <article className="prose prose-invert max-w-none text-left">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                      {demoReport}
                    </ReactMarkdown>
                  </article>
                </div>
              )}
            </div>
          )}

          {/* TAB CONTENT 4: ALGORITHMS DETAIL */}
          {activeTab === "algorithms" && (
            <div className="space-y-6 rounded-2xl border border-white/25 bg-zinc-950 p-6 shadow-[0_15px_50px_rgba(0,0,0,0.9)]">
              <div className="space-y-1 border-b border-white/15 pb-4">
                <h3 className="text-base font-bold font-display text-white">
                  Proprietary Algorithmic Innovations in REX
                </h3>
                <p className="text-xs text-zinc-400">
                  Architectural breakthroughs designed specifically to outperform traditional RAG pipelines.
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-xl border border-white/20 bg-black p-4 space-y-2 card-hover-tilt">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-white" />
                    <div>
                      <h4 className="text-xs font-bold text-white font-display">1. Dynamic Knowledge Gap Detection Loop</h4>
                      <span className="text-[10px] text-zinc-400 font-mono">Iterative Coverage Auditor</span>
                    </div>
                  </div>
                  <p className="text-xs text-zinc-300 leading-relaxed">Audits multi-track synthesis for evidence deficits or partial answers, triggering targeted secondary back-search iterations before final paper assembly.</p>
                </div>

                <div className="rounded-xl border border-white/20 bg-black p-4 space-y-2 card-hover-tilt">
                  <div className="flex items-center gap-2">
                    <Gauge className="h-5 w-5 text-white" />
                    <div>
                      <h4 className="text-xs font-bold text-white font-display">2. Maximal Marginal Relevance (MMR) Chunking</h4>
                      <span className="text-[10px] text-zinc-400 font-mono">Lexical & Semantic Precision Filter</span>
                    </div>
                  </div>
                  <p className="text-xs text-zinc-300 leading-relaxed">Combines semantic vector embeddings with domain authority tier scoring to filter out SEO fluff and prioritize high-density empirical evidence.</p>
                </div>
              </div>
            </div>
          )}
        </motion.section>



        {/* CTA FOOTER */}
        <section className="text-center py-12 rounded-2xl border border-white/25 bg-zinc-950 p-8 space-y-6 shadow-[0_15px_50px_rgba(0,0,0,0.9)]">
          <h2 className="text-3xl font-bold font-display text-white sm:text-4xl">
            Ready to Experience Autonomous Intelligence?
          </h2>
          <p className="mx-auto max-w-xl text-sm text-zinc-300 leading-relaxed">
            Launch REX to generate comprehensive, fully-cited research papers on any complex technology, market, or scientific topic in minutes.
          </p>
          <div className="flex justify-center gap-4 pt-2">
            <Link
              href="/"
              className="inline-flex items-center gap-2.5 rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-black transition-all duration-200 hover:scale-105 shadow-[0_0_30px_rgba(255,255,255,0.35)]"
            >
              Launch Deep Research Workspace
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="text-center text-xs text-zinc-500 font-mono border-t border-white/15 pt-8 space-y-2">
          <p>© {new Date().getFullYear()} REX. All rights reserved.</p>
          <Link href="/copyright" className="underline text-white">Copyrights & Terms</Link>
        </footer>
      </div>
    </div>
  );
}
