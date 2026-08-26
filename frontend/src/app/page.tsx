"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  Download,
  Eye,
  EyeOff,
  FileJson,
  FileText,
  Search,
  ArrowRight,
  RefreshCw,
  Loader2,
  ListTodo,
  Terminal,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import rehypeSanitize from "rehype-sanitize";
import { defaultSchema } from "hast-util-sanitize";
import { AnimatePresence, motion } from "framer-motion";
import MetricsDashboard from "@/components/MetricsDashboard";
import MemoryHealthDashboard from "@/components/MemoryHealthDashboard";
import BackgroundCanvas from "@/components/BackgroundCanvas";
import Link from "next/link";
import { Brain, BrainCircuit, Sparkles } from "lucide-react";

// ============================================
// SEO CONFIGURATION
// ============================================

// Base site metadata
const SITE_TITLE = "REX — Recursive Exploration eXplorer";
const SITE_DESCRIPTION = "AI-powered deep research multi-agent system that conducts comprehensive multi-source research with quality verification and citation tracking";
const SITE_KEYWORDS = "deep research, AI research, multi-agent system, neuro-symbolic AI, quantum computing, automation, LLM research, quality verification, citation tracking";
const SITE_AUTHOR = "REX Research System";
const SITE_URL = process.env.NEXT_PUBLIC_URL || "http://localhost:3000";

// Schema.org structured data types
const RESEARCH_SCHEMA = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": SITE_TITLE,
  "description": SITE_DESCRIPTION,
  "applicationCategory": "ResearchApplication",
  "operatingSystem": "Web-based",
  "softwareSourceCode": {
    "@type": "SoftwareSourceCode",
    "codeRepository": "https://github.com/deep-research-agent/deep-research-agent",
  },
  "version": "2.0.0",
};

// Open Graph / Social Media metadata
const OG_METADATA = {
  title: SITE_TITLE,
  description: SITE_DESCRIPTION,
  url: SITE_URL,
  siteName: SITE_TITLE,
  images: [
    "/hero-image.png",
  ],
  type: "website",
};

// Twitter Card metadata
const TWITTER_METADATA = {
  card: "summary_large_image",
  title: SITE_TITLE,
  description: SITE_DESCRIPTION,
  images: ["/hero-image.png"],
  creator: "@rexiiresearch",
};

// ============================================
// SEO Enhancement Components
// ============================================

// Helper to generate schema JSON-LD
function generateSchemaJSONLD(schema: object) {
  return (
    <script
      type="application/ld+json"
      className="hidden"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  );
}

function generateOGMeta(og: typeof OG_METADATA) {
  return (
    <>
      <meta property="og:title" content={og.title} />
      <meta property="og:description" content={og.description} />
      <meta property="og:url" content={og.url} />
      <meta property="og:type" content={og.type} />
      {og.images && og.images.length > 0 && (
        <meta property="og:image" content={og.images[0]} />
      )}
      {og.images && og.images.length > 1 && (
        <>
          {og.images.map((img, i) => (
            <meta key={i} property="og:image" content={img} />
          ))}
        </>
      )}
      <meta property="og:site_name" content={og.siteName} />
    </>
  );
}

function generateTwitterMeta(twitter: typeof TWITTER_METADATA) {
  return (
    <>
      <meta name="twitter:card" content={twitter.card} />
      <meta name="twitter:title" content={twitter.title} />
      <meta name="twitter:description" content={twitter.description} />
      {twitter.images && twitter.images.length > 0 && (
        <meta name="twitter:image" content={twitter.images[0]} />
      )}
      <meta name="twitter:creator" content={twitter.creator} />
    </>
  );
}

// ============================================
// Enhanced Home Component
// ============================================

const MARKDOWN_SCHEMA = {
  ...defaultSchema,
  attributes: {
    ...(defaultSchema.attributes ?? {}),
    a: [...(defaultSchema.attributes?.a ?? []), ["target"], ["rel"]],
  },
};

const RESEARCH_PHASES = [
  { id: "planner", label: "Planning", desc: "Decomposing query into 8+ analytical sub-questions" },
  { id: "memory_retrieval", label: "Recall", desc: "Retrieving vector memory lessons and prior trajectories" },
  { id: "searcher", label: "Searching", desc: "Executing parallel web searches across web indices" },
  { id: "filter", label: "Analyzing", desc: "Scoring domain authority and extracting factual chunks" },
  { id: "synthesis", label: "Synthesizing", desc: "Synthesizing findings into grounded analytical arguments" },
  { id: "gap_detector", label: "Auditing", desc: "Checking coverage gaps and filling missing evidence" },
  { id: "citation_mapper", label: "Citing", desc: "Mapping inline [N] citations and verifying URLs" },
  { id: "report_node_id", label: "Reporting", desc: "Assembling comprehensive research report" },
  { id: "evaluator", label: "Scoring", desc: "Evaluating report quality metrics & extracting lessons" },
];

const PHASE_BOUNDS: Record<string, { floor: number; ceil: number }> = {
  planner: { floor: 0, ceil: 19 },
  memory_retrieval: { floor: 20, ceil: 34 },
  searcher: { floor: 35, ceil: 49 },
  filter: { floor: 50, ceil: 64 },
  synthesis: { floor: 65, ceil: 77 },
  gap_detector: { floor: 78, ceil: 87 },
  citation_mapper: { floor: 88, ceil: 93 },
  report_node_id: { floor: 94, ceil: 97 },
  evaluator: { floor: 98, ceil: 99 },
};

const PROGRESS_FLOORS: Record<string, number> = Object.fromEntries(
  Object.entries(PHASE_BOUNDS).map(([k, v]) => [k, v.floor])
);

type DashboardMetrics = React.ComponentProps<typeof MetricsDashboard>["metrics"];

interface TelemetryLogEntry {
  timestamp: string;
  stage: string;
  message: string;
}

function cleanReport(raw: string): string {
  // Backend (main.py) already strips ((reported by source)) patterns
  // and ### Source Notes sections during report assembly (lines 2334-2336).
  // This function is kept as a no-op for forward compatibility but does not
  // perform any stripping to avoid double-removal of content that the backend
  // has already properly handled.
  return raw;
}

async function fetchSessionReport(sid: string): Promise<{
  report: string;
  metrics?: DashboardMetrics;
} | null> {
  for (let attempt = 0; attempt < 12; attempt += 1) {
    if (attempt > 0) {
      await new Promise((r) => setTimeout(r, 1500));
    }
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/sessions/${sid}`).catch(
        () => fetch(`/api/v1/sessions/${sid}`)
      );
      if (res.ok) {
        const sess = (await res.json()) as { report?: string; _metrics?: DashboardMetrics };
        if (sess?.report && sess.report.trim().length > 100) {
          return { report: sess.report, metrics: sess._metrics };
        }
      }
    } catch {
      // retry
    }
  }
  return null;
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [report, setReport] = useState<string>("");
  const [activeNode, setActiveNode] = useState("planner");
  const [completedNodes, setCompletedNodes] = useState<Set<string>>(new Set());
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [sessionId, setSessionId] = useState("");
  const sessionIdRef = useRef("");
  const [showMetrics, setShowMetrics] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isCancelled, setIsCancelled] = useState(false);

  const [telemetryLogs, setTelemetryLogs] = useState<TelemetryLogEntry[]>([]);

  const reportRef = useRef<HTMLDivElement>(null);
  const telemetryContainerRef = useRef<HTMLDivElement>(null);
  const maxPhaseIdxRef = useRef(-1);

  const activePhase = RESEARCH_PHASES.find((phase) => phase.id === activeNode) || RESEARCH_PHASES[0];

  useEffect(() => {
    if (telemetryContainerRef.current) {
      telemetryContainerRef.current.scrollTop = telemetryContainerRef.current.scrollHeight;
    }
  }, [telemetryLogs]);

  const addTelemetryLog = (msg: string, stageName?: string) => {
    const timeStr = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const currentPhaseLabel = stageName || activePhase.label;
    setTelemetryLogs((prev) => [
      ...prev,
      { timestamp: timeStr, stage: currentPhaseLabel, message: msg }
    ]);
  };

  useEffect(() => {
    if (report) {
      reportRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [report]);

  const handleNodeTransition = (node: string) => {
    const idx = RESEARCH_PHASES.findIndex((p) => p.id === node);
    if (idx < 0) return;
    // Monotonic guard: ignore duplicate / out-of-order node events so the
    // workflow is never replayed (backend can emit a node more than once).
    if (idx <= maxPhaseIdxRef.current) return;
    maxPhaseIdxRef.current = idx;
    setActiveNode(node);
    const bounds = PHASE_BOUNDS[node];
    if (bounds) {
      setProgress((current) => Math.max(current, bounds.floor));
    }
    setCompletedNodes((prev) => {
      const next = new Set(prev);
      for (let i = 0; i < idx; i++) {
        next.add(RESEARCH_PHASES[i].id);
      }
      return next;
    });
  };

  useEffect(() => {
    if (!isLoading) return;

    const interval = window.setInterval(() => {
      setProgress((current) => {
        if (report) return 100;

        const bounds = PHASE_BOUNDS[activeNode] || { floor: 0, ceil: 98 };
        if (current < bounds.floor) {
          return bounds.floor;
        }
        if (current >= bounds.ceil) {
          return bounds.ceil;
        }

        const step = 0.4;
        return Math.min(bounds.ceil, current + step);
      });
    }, 200);

    return () => window.clearInterval(interval);
  }, [isLoading, report, activeNode]);

  useEffect(() => {
    if (report) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setProgress(100);
      setCompletedNodes(new Set(RESEARCH_PHASES.map((p) => p.id)));
    }
  }, [report]);

  const startResearch = async (overrideQuery?: string) => {
    const activeQuery = (overrideQuery || query).trim();
    if (!activeQuery || isLoading) return;

    setQuery(activeQuery);
    setIsLoading(true);
    setReport("");
    setActiveNode("planner");
    setCompletedNodes(new Set());
    setMetrics(null);
    setSessionId("");
    sessionIdRef.current = "";
    setShowMetrics(false);
    setProgress(PROGRESS_FLOORS.planner);
    setIsCancelled(false);
    setTelemetryLogs([]);
    maxPhaseIdxRef.current = 0;

    addTelemetryLog(`Initializing REX multi-agent pipeline for query: "${activeQuery}"`, "Planning");
    addTelemetryLog("Decomposing query into multi-dimensional sub-questions...", "Planning");

    let receivedEnd = false;
    try {
      let response: Response;
      const fetchOpts: RequestInit = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: activeQuery }),
      };
      // Try direct backend first — avoids Next.js proxy SSE buffering
      // Falls back to proxy if the direct port is unreachable
      const directUrl = "http://127.0.0.1:8000/api/v1/research/";
      const proxyUrl = `${process.env.NEXT_PUBLIC_API_URL || ""}/api/v1/research/`;
      try {
        response = await fetch(directUrl, fetchOpts);
      } catch {
        try {
          response = await fetch(proxyUrl, fetchOpts);
        } catch {
          throw new Error("Backend server unavailable. Please ensure the backend is running on port 8000.");
        }
      }

      if (!response.ok) {
        const errText = await response.text().catch(() => "");
        throw new Error(`HTTP ${response.status}${errText ? `: ${errText}` : ""}`);
      }

      const sessionHeader = response.headers.get("X-Session-Id");
      if (sessionHeader) {
        sessionIdRef.current = sessionHeader;
        setSessionId(sessionHeader);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("Streaming response was unavailable.");

      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          // SSE heartbeat comment lines — skip
          if (trimmed.startsWith(":")) continue;
          if (!trimmed.startsWith("data: ")) continue;

          let data: Record<string, unknown>;
          try {
            data = JSON.parse(trimmed.slice(6));
          } catch {
            continue;
          }

          if (typeof data.session_id === "string") {
            sessionIdRef.current = data.session_id;
            setSessionId(data.session_id);
          }

          // ── Telemetry: pick up message from ANY event type ──
          if (typeof data.message === "string" && data.message) {
            addTelemetryLog(data.message);
          }

          if (typeof data.track_text === "string") {
            addTelemetryLog(
              `Track ${data.track_id}: ${data.track_status || ''} — ${data.track_text}`,
              "Searching"
            );
          }
          if (Array.isArray(data.source_urls) && data.source_urls.length > 0) {
            addTelemetryLog(
              `Scraped ${(data.source_urls as string[]).length} verified web sources from search indices`,
              "Searching"
            );
          }
          if (typeof data.source_url === "string") {
            addTelemetryLog(`Verified source: ${data.source_url}`, "Searching");
          }

          if (typeof data.node === "string") {
            const node = data.node;
            if (node === "cancelled") {
              addTelemetryLog("Research cancelled by user.", "Cancelled");
              setIsLoading(false);
              setIsCancelled(false);
              return;
            } else if (node === "end") {
              receivedEnd = true;
              addTelemetryLog("✅ Final Master Research Paper successfully generated & evaluated.", "Scoring");
              if (typeof data.report === "string" && data.report.trim()) {
                setReport(cleanReport(data.report));
                setProgress(100);
                setCompletedNodes(new Set(RESEARCH_PHASES.map((p) => p.id)));
              } else {
                // report field empty in the SSE event — recover from the session store
                const sid = sessionIdRef.current;
                if (sid) {
                  const sess = await fetchSessionReport(sid);
                  if (sess) {
                    setReport(cleanReport(sess.report));
                    setProgress(100);
                    setCompletedNodes(new Set(RESEARCH_PHASES.map((p) => p.id)));
                    if (sess.metrics) setMetrics(sess.metrics);
                    addTelemetryLog("Report loaded from session store.", "Reporting");
                  }
                }
              }
              if (data.metrics) setMetrics(data.metrics as DashboardMetrics);
            } else if (node !== "start") {
              const matchedPhase = RESEARCH_PHASES.find((p) => p.id === node);
              const phaseLabel = matchedPhase ? matchedPhase.label : node;
              handleNodeTransition(node);
              // Only log phase advance if there was no message field (avoid duplicate)
              if (!data.message) {
                addTelemetryLog(`Advancing to phase: ${phaseLabel}`, phaseLabel);
              }
            }
          }
        }
      }

      if (!receivedEnd) {
        console.warn("Stream ended before the report completed.");
        addTelemetryLog("Stream ended — attempting to recover report from session store...", "Error");
        const sid = sessionIdRef.current;
        if (sid) {
          const sess = await fetchSessionReport(sid);
          if (sess) {
            setReport(cleanReport(sess.report));
            setProgress(100);
            setCompletedNodes(new Set(RESEARCH_PHASES.map((p) => p.id)));
            if (sess.metrics) setMetrics(sess.metrics);
            addTelemetryLog("✅ Report recovered from session store.", "Reporting");
          } else {
            addTelemetryLog("Stream ended before report was complete. Please try again.", "Error");
          }
        } else {
          addTelemetryLog("Stream ended before report was complete. Please try again.", "Error");
        }
      }
    } catch (err) {
      console.error("Research pipeline error:", err);
      addTelemetryLog(`Pipeline error: ${err instanceof Error ? err.message : String(err)}`, "Error");
    } finally {
      setIsLoading(false);
    }
  };

  const cancelResearch = async () => {
    const sid = sessionIdRef.current;
    if (!sid) return;
    setIsCancelled(true);
    addTelemetryLog("User requested cancellation — stopping research pipeline...", "Cancelling");
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
    try {
      await fetch(`${apiBase}/api/v1/research/${sid}/cancel`, { method: "POST" });
    } catch {
      try {
        await fetch(`http://127.0.0.1:8000/api/v1/research/${sid}/cancel`, { method: "POST" });
      } catch {}
    }
  };

  const downloadPDF = () => {
    window.setTimeout(() => {
      window.print();
    }, 100);
  };

return (
    <main className="relative min-h-screen overflow-x-hidden bg-black text-white px-4 py-8 sm:px-8 lg:px-16 print:bg-white print:text-black">
      {/* SEO: Structured Data & Meta Tags */}
      <div className="hidden">
        {generateSchemaJSONLD(RESEARCH_SCHEMA)}
        {generateOGMeta(OG_METADATA)}
        {generateTwitterMeta(TWITTER_METADATA)}
        <meta name="keywords" content={SITE_KEYWORDS} />
        <meta name="author" content={SITE_AUTHOR} />
      </div>
      
      {/* Background Canvas */}
      <BackgroundCanvas />
      
      <div className="relative z-10 mx-auto flex w-full max-w-4xl flex-col gap-12 pt-4">
        {/* SEARCH MODE (Empty State) */}
        {!isLoading && !report && (
          <section className="flex min-h-[70vh] flex-col justify-center py-6 sm:py-10">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="mx-auto w-full max-w-2xl text-center space-y-5"
            >
              {/* TOP QUICK NAVIGATION PILLS */}
              <div className="flex flex-wrap items-center justify-center gap-2 font-mono text-xs pb-2">
                <Link
                  href="/brain"
                  className="flex items-center gap-1.5 rounded-full border border-white/20 bg-zinc-950/80 px-3.5 py-1.5 text-zinc-300 hover:text-white hover:border-white transition shadow-md"
                >
                  <Brain className="h-3.5 w-3.5 text-[#E8D5B7]" />
                  Neural Brain Visualizer
                </Link>
                <Link
                  href="/learning-history"
                  className="flex items-center gap-1.5 rounded-full border border-white/20 bg-zinc-950/80 px-3.5 py-1.5 text-zinc-300 hover:text-white hover:border-white transition shadow-md"
                >
                  <BrainCircuit className="h-3.5 w-3.5 text-[#C2410C]" />
                  Learning Memory
                </Link>
                <Link
                  href="/landing-page"
                  className="flex items-center gap-1.5 rounded-full border border-white/20 bg-zinc-950/80 px-3.5 py-1.5 text-zinc-300 hover:text-white hover:border-white transition shadow-md"
                >
                  <Sparkles className="h-3.5 w-3.5 text-[#D4A853]" />
                  Platform Benchmarks
                </Link>
              </div>

              {/* TWO-LINE TITLE HEADER ABOVE SEARCH BOX */}
              <div className="text-center pb-2 space-y-1">
                <h1
                  className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-widest text-white uppercase drop-shadow-[0_0_25px_rgba(255,255,255,0.3)] leading-none"
                  style={{ fontFamily: "'Times New Roman', Times, serif" }}
                >
                  REX
                </h1>
                <p
                  className="text-lg sm:text-xl lg:text-2xl font-normal tracking-wide text-zinc-300 drop-shadow-[0_0_15px_rgba(255,255,255,0.15)] leading-snug"
                  style={{ fontFamily: "'Times New Roman', Times, serif" }}
                >
                  Multi - Agentic Self Improving Deep Research System
                </p>
              </div>

              {/* COMPACT SEARCH INPUT SHELL CONTAINER */}
              <div className="overflow-hidden rounded-2xl border border-white/30 bg-zinc-950 shadow-[0_10px_35px_rgba(0,0,0,0.9)] focus-within:border-white focus-within:shadow-[0_0_25px_rgba(255,255,255,0.25)] transition-all duration-300 text-left">
                <div className="flex flex-col p-3 sm:p-3.5 relative min-h-[90px] justify-between">
                  <div className="flex items-start gap-2.5">
                    <Search className="mt-1 h-4 w-4 shrink-0 text-white" />
                    <textarea
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Describe your deep research query..."
                      className="min-h-[46px] w-full resize-none bg-transparent text-sm leading-6 text-white outline-none placeholder:text-zinc-500 custom-scrollbar"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          startResearch();
                        }
                      }}
                    />
                  </div>

                  {/* BOTTOM COMPACT ACTION ROW */}
                  <div className="flex items-center justify-between pt-2 border-t border-white/15 mt-1.5">
                    <span className="text-[10px] font-mono text-zinc-400">
                      Press <kbd className="px-1.5 py-0.5 rounded border border-white/20 bg-black text-[9px] text-white">Enter ↵</kbd> to execute
                    </span>
                    <button
                      onClick={() => startResearch()}
                      disabled={!query.trim()}
                      aria-label="Start deep research"
                      className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-black transition-all duration-200 hover:scale-105 disabled:cursor-not-allowed disabled:opacity-30 shadow-[0_0_15px_rgba(255,255,255,0.3)] ml-auto"
                    >
                      <ArrowRight className="h-4 w-4" strokeWidth={2.5} />
                    </button>
                  </div>
                </div>
              </div>

            </motion.div>
          </section>
        )}

        {/* ACTIVE PIPELINE RUNNING MODE */}
        <AnimatePresence>
          {isLoading && (
            <motion.section
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex flex-col gap-6 rounded-2xl border border-white/30 bg-zinc-950 p-6 md:p-8 shadow-[0_15px_45px_rgba(0,0,0,0.9)]"
            >
              {/* Progress Overview Header */}
              <div className="rounded-xl border border-white/20 bg-black p-6 space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-white font-mono">
                      <ListTodo className="h-4 w-4" />
                      Research Pipeline Progress
                    </div>
                    <div className="text-xl font-bold text-white font-display flex items-center gap-2">
                      <span>{activePhase.label}</span>
                      <Loader2 className="h-4 w-4 animate-spin text-white" />
                    </div>
                    <p className="text-xs text-zinc-400">{activePhase.desc}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <div className="text-right">
                      <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-mono">Completion</div>
                      <div className="text-3xl font-extrabold text-white font-mono">{Math.round(progress)}%</div>
                    </div>
                    {!isCancelled && (
                      <button
                        onClick={cancelResearch}
                        className="flex items-center gap-1.5 rounded-lg border border-white bg-white/20 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-white hover:bg-white hover:text-black transition duration-200"
                      >
                        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                          <rect x="1" y="1" width="10" height="10" rx="2" fill="currentColor" />
                        </svg>
                        Stop
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="space-y-1.5">
                  <div className="h-3.5 overflow-hidden rounded-full bg-black border border-white/30 p-0.5">
                    <div
                      className="h-full rounded-full bg-white transition-[width] duration-300 ease-out shadow-[0_0_15px_rgba(255,255,255,0.4)]"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-zinc-400 font-mono">
                    <span>Phase: {activePhase.label}</span>
                    <span>{progress >= 98 ? "Finalizing report output..." : `${Math.round(progress)}% completed`}</span>
                  </div>
                </div>

                {/* 9 RESEARCH PHASES GRID */}
                <div className="grid gap-2.5 sm:grid-cols-3 pt-2">
                  {RESEARCH_PHASES.map((phase, idx) => {
                    const isActivePhase = phase.id === activeNode;
                    const isDonePhase = completedNodes.has(phase.id);
                    const phaseFloor = PROGRESS_FLOORS[phase.id];

                    return (
                      <div
                        key={phase.id}
                        className={`flex items-start gap-3 rounded-xl border p-3 transition-all duration-300 ${
                          isActivePhase
                            ? "border-white bg-white/20 text-white shadow-[0_0_20px_rgba(255,255,255,0.3)]"
                            : isDonePhase
                            ? "border-white/50 bg-white/10 text-white"
                            : "border-white/15 bg-black/40 text-zinc-500 opacity-60"
                        }`}
                      >
                        <div className="mt-0.5 shrink-0 font-mono text-xs font-bold">
                          {isDonePhase ? (
                            <CheckCircle2 className="h-4 w-4 text-white" />
                          ) : isActivePhase ? (
                            <Loader2 className="h-4 w-4 animate-spin text-white" />
                          ) : (
                            <span className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-white/30 text-[10px]">
                              {idx + 1}
                            </span>
                          )}
                        </div>
                        <div className="min-w-0 flex-1 space-y-0.5">
                          <div className="flex items-center justify-between gap-1">
                            <span className="text-xs font-bold tracking-tight font-display">{phase.label}</span>
                            <span className="text-[9px] uppercase font-mono tracking-wider">
                              {isDonePhase ? "Done" : isActivePhase ? `${phaseFloor}%` : "Queued"}
                            </span>
                          </div>
                          <p className="text-[10px] leading-tight text-zinc-400 line-clamp-1">{phase.desc}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* REAL-TIME LIVE AGENT REASONING TELEMETRY WINDOW */}
              <div className="rounded-xl border border-white/20 bg-black p-5 space-y-3 shadow-inner">
                <div className="flex items-center justify-between border-b border-white/15 pb-2.5">
                  <div className="flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-white" />
                    <span className="text-xs font-bold font-display uppercase tracking-wider text-white">
                      Live Agent Reasoning Telemetry
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-0.5 text-[10px] font-mono font-bold text-white border border-white/30">
                    <span className="h-1.5 w-1.5 rounded-full bg-white animate-ping" />
                    LIVE STREAMING
                  </div>
                </div>

                <div
                  ref={telemetryContainerRef}
                  className="h-44 overflow-y-auto font-mono text-xs space-y-2 custom-scrollbar p-1"
                >
                  {telemetryLogs.length === 0 ? (
                    <div className="flex h-full items-center justify-center text-xs text-zinc-500">
                      Connecting to agent event stream...
                    </div>
                  ) : (
                    telemetryLogs.map((log, i) => (
                      <div key={i} className="flex items-start gap-2.5 text-zinc-300 leading-relaxed border-b border-white/10 pb-1.5">
                        <span className="text-[10px] text-zinc-500 shrink-0 pt-0.5">[{log.timestamp}]</span>
                        <span className="rounded bg-zinc-900 px-1.5 py-0.5 text-[9px] font-bold uppercase text-white border border-white/20 shrink-0">
                          {log.stage}
                        </span>
                        <span className="text-xs text-white">{log.message}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </motion.section>
          )}
        </AnimatePresence>

        {/* REPORT PRESENTATION — shown immediately when report is ready, even if still loading */}
        <AnimatePresence>
          {Boolean(report) && (
            <motion.section
              ref={reportRef}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-col gap-8 rounded-2xl border border-white/30 bg-zinc-950 p-6 md:p-10 shadow-[0_20px_60px_rgba(0,0,0,0.95)] print:border-0 print:bg-white print:p-0 print:shadow-none"
            >
              {/* Report Header Actions */}
              <div className="flex flex-wrap items-start justify-between gap-6 border-b border-white/15 pb-6 print:hidden">
                <div className="space-y-1">
                  <div className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-0.5 text-xs font-semibold text-white border border-white/30">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Report Ready
                  </div>
                  <h2 className="font-display text-2xl font-black text-white sm:text-3xl lg:text-4xl">{query}</h2>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button onClick={downloadPDF} className="flex items-center gap-2 rounded-lg border border-white/30 bg-black px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-zinc-300 hover:border-white hover:text-white transition duration-200">
                    <Download className="h-3.5 w-3.5" />
                    PDF
                  </button>
                  {sessionId ? (
                    <>
                      <a href={`/api/v1/research/${sessionId}/export?format=html`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 rounded-lg border border-white/30 bg-black px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-zinc-300 hover:border-white hover:text-white transition duration-200">
                        <FileText className="h-3.5 w-3.5" />
                        HTML
                      </a>
                      <a href={`/api/v1/research/${sessionId}/export?format=json`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 rounded-lg border border-white/30 bg-black px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-zinc-300 hover:border-white hover:text-white transition duration-200">
                        <FileJson className="h-3.5 w-3.5" />
                        JSON
                      </a>
                    </>
                  ) : (
                    <span className="flex items-center gap-2 rounded-lg border border-white/10 bg-black px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-zinc-600 cursor-not-allowed" title="Export requires a session id">
                      <FileText className="h-3.5 w-3.5" />
                      Export
                    </span>
                  )}
                  <button onClick={() => { setReport(""); setQuery(""); }} className="flex items-center gap-2 rounded-lg border border-white/30 bg-black px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-zinc-300 hover:border-white hover:text-white transition duration-200">
                    <RefreshCw className="h-3.5 w-3.5" />
                    New Run
                  </button>
                </div>
              </div>

              {/* Markdown Body */}
              <article className="prose prose-invert max-w-none text-left print:text-black">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw, [rehypeSanitize, MARKDOWN_SCHEMA]]}
                >
                  {report}
                </ReactMarkdown>
              </article>

              {/* Telemetry Show/Hide and Grid */}
              {metrics && (
                <div className="border-t border-white/15 pt-8 print:hidden">
                  <div className="flex justify-center mb-6">
                    <button
                      onClick={() => setShowMetrics(!showMetrics)}
                      className="flex items-center gap-2 rounded-lg border border-white/30 bg-black px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:border-white transition duration-200"
                    >
                      {showMetrics ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      {showMetrics ? "Hide Telemetry" : "Show Quality Telemetry"}
                    </button>
                  </div>
                  {showMetrics && <MetricsDashboard metrics={metrics} />}
                  <div className="mt-8">
                    <MemoryHealthDashboard />
                  </div>
                </div>
              )}
            </motion.section>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
