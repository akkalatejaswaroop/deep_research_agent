"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  GitBranch,
  Sparkles,
  Search,
  ShieldCheck,
  Layers,
  Database,
  FileCheck,
  Sliders,
  Activity,
  Cpu,
  Gauge,
  BarChart3,
  RefreshCw,
  Server,
  Clock,
  Terminal,
  Zap,
  CheckCircle2,
  AlertCircle,
  Loader2,
  HardDrive,
  ChevronDown,
  ChevronUp,
  X,
  Filter,
  FileText,
  BarChart2,
  Square,
  Sparkle
} from "lucide-react";

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

export type AgentStatus = "running" | "processing" | "completed" | "waiting" | "error";

export interface AgentDefinition {
  id: number;
  code: string;
  name: string;
  category: "planning" | "gathering" | "processing" | "analysis" | "synthesis" | "review" | "output";
  stageName: string;
  role: string;
  model: string;
  icon: React.ElementType;
  phaseId: string;
  defaultStatus: AgentStatus;
  defaultProgress: number;
  defaultDuration: string;
  themeColor?: string;
  gradient?: string;
}

export interface TelemetryLog {
  id: string;
  timestamp: string;
  agentId?: number;
  agentName: string;
  event: string;
  status: AgentStatus;
  duration: string;
}

interface Props {
  activeNode?: string;
  completedNodes?: Set<string>;
  progress?: number;
  telemetryLogs?: { timestamp: string; stage: string; message: string }[];
  queryTitle?: string;
  researchId?: string;
  startedTime?: string;
  isLive?: boolean;
  onStop?: () => void;
  isCancelled?: boolean;
  interactiveMode?: boolean;
}

// ============================================================================
// COMPLETE 21-AGENT FLEET DEFINITION
// ============================================================================

export const ALL_21_AGENTS: AgentDefinition[] = [
  { id: 1, code: "01", name: "Query Analyzer", category: "planning", stageName: "Planning", role: "Decomposes complex prompt into micro-dimensional sub-queries", model: "phi3:mini", icon: Brain, phaseId: "planner", defaultStatus: "completed", defaultProgress: 100, defaultDuration: "00:00:45", themeColor: "#E8D5B7", gradient: "from-[#E8D5B7]/30 via-[#B45309]/20 to-transparent" },
  { id: 2, code: "02", name: "Research Planner", category: "planning", stageName: "Planning", role: "Establishes research topology & 9-phase execution budget", model: "qwen2.5:3b", icon: GitBranch, phaseId: "planner", defaultStatus: "completed", defaultProgress: 100, defaultDuration: "00:01:15", themeColor: "#E8D5B7", gradient: "from-[#E8D5B7]/30 via-[#B45309]/20 to-transparent" },
  { id: 3, code: "03", name: "Source Discoverer", category: "gathering", stageName: "Data Collection", role: "Discovers academic, web & preprint indices in parallel", model: "deterministic", icon: Search, phaseId: "searcher", defaultStatus: "running", defaultProgress: 78, defaultDuration: "00:02:31", themeColor: "#38BDF8", gradient: "from-sky-500/30 via-blue-600/20 to-transparent" },
  { id: 4, code: "04", name: "Web Scraper", category: "gathering", stageName: "Data Collection", role: "Executes multi-tier headless HTML DOM extraction & filtering", model: "deterministic", icon: Zap, phaseId: "searcher", defaultStatus: "running", defaultProgress: 63, defaultDuration: "00:01:58", themeColor: "#38BDF8", gradient: "from-sky-500/30 via-blue-600/20 to-transparent" },
  { id: 5, code: "05", name: "PDF Parser", category: "gathering", stageName: "Data Collection", role: "Parses mathematical tables and academic PDF paper structures", model: "deterministic", icon: FileText, phaseId: "searcher", defaultStatus: "processing", defaultProgress: 52, defaultDuration: "00:01:37", themeColor: "#38BDF8", gradient: "from-sky-500/30 via-blue-600/20 to-transparent" },
  { id: 6, code: "06", name: "Data Extractor", category: "gathering", stageName: "Data Collection", role: "Extracts key stats, charts & entity relationship matrices", model: "phi3:mini", icon: Database, phaseId: "filter", defaultStatus: "running", defaultProgress: 68, defaultDuration: "00:02:10", themeColor: "#C2410C", gradient: "from-[#C2410C]/30 via-amber-700/20 to-transparent" },
  { id: 7, code: "07", name: "Fact Checker", category: "gathering", stageName: "Data Collection", role: "Verifies claims against trusted baseline corpora & citations", model: "phi3:mini", icon: ShieldCheck, phaseId: "filter", defaultStatus: "running", defaultProgress: 74, defaultDuration: "00:01:26", themeColor: "#C2410C", gradient: "from-[#C2410C]/30 via-amber-700/20 to-transparent" },
  { id: 8, code: "08", name: "Citation Mapper", category: "processing", stageName: "Processing", role: "Builds cross-reference graph & verified URL anchor mapping", model: "phi3:mini", icon: FileCheck, phaseId: "citation_mapper", defaultStatus: "processing", defaultProgress: 41, defaultDuration: "00:01:12", themeColor: "#10B981", gradient: "from-emerald-500/30 via-teal-700/20 to-transparent" },
  { id: 9, code: "09", name: "Bias Detector", category: "processing", stageName: "Processing", role: "Audits source neutrality & publication skew across domains", model: "phi3:mini", icon: Sliders, phaseId: "synthesis", defaultStatus: "running", defaultProgress: 65, defaultDuration: "00:01:45", themeColor: "#F59E0B", gradient: "from-amber-500/30 via-orange-600/20 to-transparent" },
  { id: 10, code: "10", name: "Trend Analyzer", category: "processing", stageName: "Processing", role: "Detects temporal acceleration & market consensus shifts", model: "phi3:mini", icon: Sparkles, phaseId: "planner", defaultStatus: "waiting", defaultProgress: 0, defaultDuration: "--:--:--", themeColor: "#E8D5B7", gradient: "from-[#E8D5B7]/30 to-transparent" },
  { id: 11, code: "11", name: "Domain Intelligence", category: "analysis", stageName: "Analysis", role: "Evaluates domain trust scores & SEO spam filters", model: "deterministic", icon: ShieldCheck, phaseId: "filter", defaultStatus: "waiting", defaultProgress: 0, defaultDuration: "--:--:--", themeColor: "#C2410C", gradient: "from-[#C2410C]/30 to-transparent" },
  { id: 12, code: "12", name: "Source Diversifier", category: "analysis", stageName: "Analysis", role: "Ensures multi-jurisdiction triangulation of evidence", model: "qwen2.5:3b", icon: Layers, phaseId: "searcher", defaultStatus: "waiting", defaultProgress: 0, defaultDuration: "--:--:--", themeColor: "#38BDF8", gradient: "from-sky-500/30 to-transparent" },
  { id: 13, code: "13", name: "Cache Orchestrator", category: "analysis", stageName: "Analysis", role: "Retrieves semantic vector cache & prior embedding lessons", model: "deterministic", icon: HardDrive, phaseId: "memory_retrieval", defaultStatus: "completed", defaultProgress: 100, defaultDuration: "00:00:18", themeColor: "#A855F7", gradient: "from-purple-500/30 via-indigo-700/20 to-transparent" },
  { id: 14, code: "14", name: "Repetition Auditor", category: "synthesis", stageName: "Synthesis", role: "Eliminates cross-section text overlap & redundant paragraphs", model: "deterministic", icon: Activity, phaseId: "synthesis", defaultStatus: "waiting", defaultProgress: 0, defaultDuration: "--:--:--", themeColor: "#F59E0B", gradient: "from-amber-500/30 to-transparent" },
  { id: 15, code: "15", name: "Tone & Style Auditor", category: "synthesis", stageName: "Synthesis", role: "Enforces objective, authoritative academic voice", model: "phi3:mini", icon: Gauge, phaseId: "synthesis", defaultStatus: "waiting", defaultProgress: 0, defaultDuration: "--:--:--", themeColor: "#F59E0B", gradient: "from-amber-500/30 to-transparent" },
  { id: 16, code: "16", name: "Model Router", category: "review", stageName: "Review", role: "Optimizes LLM parameter allocation & latency limits", model: "deterministic", icon: Cpu, phaseId: "synthesis", defaultStatus: "waiting", defaultProgress: 0, defaultDuration: "--:--:--", themeColor: "#F59E0B", gradient: "from-amber-500/30 to-transparent" },
  { id: 17, code: "17", name: "Quality Scorer", category: "review", stageName: "Review", role: "Computes 5-axis report quality benchmarks & metrics", model: "phi3:mini", icon: BarChart3, phaseId: "evaluator", defaultStatus: "waiting", defaultProgress: 0, defaultDuration: "--:--:--", themeColor: "#EC4899", gradient: "from-pink-500/30 via-rose-700/20 to-transparent" },
  { id: 18, code: "18", name: "Coherence Auditor", category: "review", stageName: "Review", role: "Validates logical flow & markdown header hierarchy", model: "phi3:mini", icon: BarChart2, phaseId: "evaluator", defaultStatus: "waiting", defaultProgress: 0, defaultDuration: "--:--:--", themeColor: "#EC4899", gradient: "from-pink-500/30 to-transparent" },
  { id: 19, code: "19", name: "Lesson Learner", category: "output", stageName: "Output", role: "Persists self-reflection lessons into Obsidian knowledge vault", model: "phi3:mini", icon: Brain, phaseId: "evaluator", defaultStatus: "waiting", defaultProgress: 0, defaultDuration: "--:--:--", themeColor: "#EC4899", gradient: "from-pink-500/30 to-transparent" },
  { id: 20, code: "20", name: "Gap Analyzer", category: "output", stageName: "Output", role: "Identifies unaddressed questions and issues targeted sub-queries", model: "phi3:mini", icon: RefreshCw, phaseId: "gap_detector", defaultStatus: "waiting", defaultProgress: 0, defaultDuration: "--:--:--", themeColor: "#6366F1", gradient: "from-indigo-500/30 via-blue-700/20 to-transparent" },
  { id: 21, code: "21", name: "Report Engine", category: "output", stageName: "Output", role: "Assembles comprehensive master paper with citations & PDF export", model: "qwen2.5:3b", icon: Server, phaseId: "report_node_id", defaultStatus: "waiting", defaultProgress: 0, defaultDuration: "--:--:--", themeColor: "#E8D5B7", gradient: "from-[#E8D5B7]/30 via-amber-600/20 to-transparent" },
];

export const PIPELINE_STAGES = [
  { id: "planner", label: "Planning", phase: "01" },
  { id: "memory_retrieval", label: "Recall", phase: "02" },
  { id: "searcher", label: "Searching", phase: "03" },
  { id: "filter", label: "Analyzing", phase: "04" },
  { id: "synthesis", label: "Synthesizing", phase: "05" },
  { id: "gap_detector", label: "Auditing", phase: "06" },
  { id: "citation_mapper", label: "Citing", phase: "07" },
  { id: "report_node_id", label: "Reporting", phase: "08" },
  { id: "evaluator", label: "Scoring", phase: "09" },
];

export default function AgentWorkflowMatrix({
  activeNode = "planner",
  completedNodes = new Set(),
  progress = 25,
  telemetryLogs = [],
  queryTitle = "Deep Multi-Agent Research Execution",
  researchId = "",
  startedTime = "",
  isLive = true,
  onStop,
  isCancelled = false,
}: Props) {
  const [showFleetDrawer, setShowFleetDrawer] = useState<boolean>(false);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);
  const [currentTimeStr, setCurrentTimeStr] = useState<string>("");
  const logsContainerRef = useRef<HTMLDivElement>(null);

  // Real-time dynamic clock & elapsed run time ticker
  useEffect(() => {
    const updateRealtime = () => {
      setCurrentTimeStr(new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    };
    updateRealtime();
    const clockInterval = setInterval(updateRealtime, 1000);
    const elapsedInterval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => {
      clearInterval(clockInterval);
      clearInterval(elapsedInterval);
    };
  }, []);

  // Format real-time elapsed timer (HH:MM:SS)
  const formattedElapsedTime = useMemo(() => {
    const hrs = Math.floor(elapsedSeconds / 3600);
    const mins = Math.floor((elapsedSeconds % 3600) / 60);
    const secs = elapsedSeconds % 60;
    return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }, [elapsedSeconds]);

  // Dynamic research run ID
  const activeRunId = useMemo(() => {
    if (researchId) return researchId;
    return `REX-RUN-${Date.now().toString().slice(-6)}`;
  }, [researchId]);

  // Dynamic run start timestamp
  const activeStartedTime = useMemo(() => {
    if (startedTime) return startedTime;
    return currentTimeStr || new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }, [startedTime, currentTimeStr]);

  // Determine the primary active agent for the current phase node
  const activeAgent = useMemo(() => {
    const matched = ALL_21_AGENTS.filter((a) => a.phaseId === activeNode);
    if (matched.length > 0) {
      const idx = Math.floor((progress % 100) / (100 / matched.length)) % matched.length;
      return matched[idx] || matched[0];
    }
    return ALL_21_AGENTS[0];
  }, [activeNode, progress]);

  // Compute status per agent for the expandable drawer
  const agentStates = useMemo(() => {
    return ALL_21_AGENTS.map((agent) => {
      const isDone = completedNodes.has(agent.phaseId) || progress >= 98;
      const isActive = activeNode === agent.phaseId && !isDone;

      let status: AgentStatus = "waiting";
      let prog = 0;

      if (isDone) {
        status = "completed";
        prog = 100;
      } else if (isActive) {
        status = "running";
        prog = Math.min(98, Math.max(25, Math.round(progress)));
      }

      return {
        ...agent,
        status,
        progress: prog,
      };
    });
  }, [activeNode, completedNodes, progress]);

  // Auto-scroll telemetry window
  useEffect(() => {
    if (autoScroll && logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [telemetryLogs, autoScroll]);

  const ActiveIcon = activeAgent.icon;

  return (
    <div className="w-full space-y-6 bg-[#141210] text-white p-4 sm:p-6 lg:p-8 rounded-3xl border border-white/15 shadow-[0_30px_90px_rgba(0,0,0,0.95)] backdrop-blur-2xl">
      {/* Dynamic Header Metadata Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4 font-mono text-xs text-zinc-400">
        <div className="flex items-center gap-3">
          <span className="bg-[#E8D5B7] text-black px-2 py-0.5 rounded text-[10px] font-black font-mono">REX ENGINE</span>
          <span>Run ID: <strong className="text-white">{activeRunId}</strong></span>
          <span>•</span>
          <span>Started: <strong className="text-white">{activeStartedTime}</strong></span>
        </div>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 text-[#E8D5B7]">
            <Clock className="h-3.5 w-3.5 text-[#C2410C]" />
            Elapsed: <strong className="text-white">{formattedElapsedTime}</strong>
          </span>
          <span className="flex items-center gap-1.5 text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
            REALTIME LOGGING
          </span>
        </div>
      </div>

      {/* ============================================================================ */}
      {/* 9-PHASE PIPELINE STEPPER TRACK */}
      {/* ============================================================================ */}
      <div className="rounded-2xl border border-white/10 bg-[#1E1B18]/80 p-3.5 sm:p-4 shadow-inner">
        <div className="flex items-center justify-between gap-1 overflow-x-auto custom-scrollbar pb-1">
          {PIPELINE_STAGES.map((st, idx) => {
            const isDone = completedNodes.has(st.id) || progress >= 99;
            const isActive = activeNode === st.id && !isDone;

            return (
              <React.Fragment key={st.id}>
                <div className="flex items-center gap-2 shrink-0 px-2 py-1 rounded-xl transition-all duration-300">
                  <div
                    className={`flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-mono font-bold transition-all ${
                      isDone
                        ? "bg-[#E8D5B7] text-black shadow-[0_0_12px_rgba(232,213,183,0.5)]"
                        : isActive
                        ? "bg-[#C2410C] text-white ring-4 ring-[#C2410C]/30 animate-pulse"
                        : "bg-zinc-800 text-zinc-500 border border-white/10"
                    }`}
                  >
                    {isDone ? "✓" : st.phase}
                  </div>
                  <span
                    className={`text-xs font-bold font-display uppercase tracking-wider ${
                      isDone
                        ? "text-[#E8D5B7]"
                        : isActive
                        ? "text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.4)]"
                        : "text-zinc-500"
                    }`}
                  >
                    {st.label}
                  </span>
                </div>
                {idx < PIPELINE_STAGES.length - 1 && (
                  <div
                    className={`h-[2px] w-6 shrink-0 transition-colors ${
                      isDone ? "bg-[#E8D5B7]/60" : "bg-white/10"
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* ============================================================================ */}
      {/* CINEMATIC MOVIE-STYLE SINGLE ACTIVE AGENT SHOWCASE */}
      {/* ============================================================================ */}
      <div className="relative overflow-hidden rounded-3xl border border-white/20 bg-gradient-to-br from-[#1E1B18] via-[#141210] to-black p-6 sm:p-8 shadow-[0_20px_70px_rgba(0,0,0,0.95)]">
        {/* Ambient Glowing Background Effect tailored to active agent */}
        <div
          className="absolute -top-24 -left-24 h-96 w-96 rounded-full blur-[110px] pointer-events-none opacity-40 transition-colors duration-700"
          style={{ backgroundColor: activeAgent.themeColor || "#E8D5B7" }}
        />
        <div
          className="absolute -bottom-24 -right-24 h-96 w-96 rounded-full blur-[110px] pointer-events-none opacity-30 transition-colors duration-700"
          style={{ backgroundColor: activeAgent.themeColor || "#C2410C" }}
        />

        {/* Holographic Laser Scanline Overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_0%,rgba(255,255,255,0.03)_50%,transparent_100%)] bg-[length:100%_4px] pointer-events-none opacity-30" />

        <AnimatePresence mode="wait">
          <motion.div
            key={activeAgent.id}
            initial={{ opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -16, scale: 0.97 }}
            transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
            className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center"
          >
            {/* Left Movie Badge & Visual Icon Stage */}
            <div className="lg:col-span-4 flex flex-col items-center justify-center text-center space-y-4">
              <div className="relative">
                {/* Outer Rotating Halo Ring */}
                <div
                  className="absolute -inset-4 rounded-full border-2 border-dashed opacity-60 animate-[spin_12s_linear_infinite]"
                  style={{ borderColor: activeAgent.themeColor || "#E8D5B7" }}
                />
                <div
                  className="absolute -inset-1.5 rounded-full blur-md opacity-70 animate-pulse"
                  style={{ backgroundColor: activeAgent.themeColor || "#E8D5B7" }}
                />

                {/* Hero Icon Card Frame */}
                <div className="relative h-28 w-28 sm:h-32 sm:w-32 rounded-3xl border-2 border-white/30 bg-black/80 flex items-center justify-center shadow-2xl backdrop-blur-xl">
                  <ActiveIcon
                    className="h-14 w-14 sm:h-16 sm:w-16 transition-all duration-300 transform group-hover:scale-110 drop-shadow-[0_0_20px_rgba(232,213,183,0.8)]"
                    style={{ color: activeAgent.themeColor || "#E8D5B7" }}
                  />
                </div>
              </div>

              {/* Agent ID & Status Badge */}
              <div className="space-y-1">
                <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-black/80 px-3.5 py-1 text-xs font-mono font-bold tracking-widest text-[#E8D5B7] shadow-lg">
                  <span className="h-2 w-2 rounded-full bg-[#E8D5B7] animate-ping" />
                  AGENT #{activeAgent.code} ACTIVE
                </div>
                <div className="text-[11px] font-mono uppercase tracking-widest text-zinc-400">
                  {activeAgent.stageName} Pipeline
                </div>
              </div>
            </div>

            {/* Center & Right Details Stage */}
            <div className="lg:col-span-8 space-y-6 text-left">
              {/* Header Title & Model Badge */}
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/15 pb-4">
                <div>
                  <h2 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold font-display text-white tracking-tight leading-none drop-shadow-[0_0_20px_rgba(255,255,255,0.2)]">
                    {activeAgent.name}
                  </h2>
                  <p className="text-sm text-zinc-300 mt-2 font-sans leading-relaxed max-w-xl">
                    {activeAgent.role}
                  </p>
                </div>

                <div className="flex flex-col items-end gap-2 shrink-0">
                  <div className="flex items-center gap-2 rounded-xl border border-white/20 bg-zinc-900/90 px-3 py-1.5 text-xs font-mono font-bold text-white shadow-md">
                    <Cpu className="h-3.5 w-3.5 text-[#E8D5B7]" />
                    <span>{activeAgent.model}</span>
                  </div>
                  <div className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider">
                    Execution Mode: Live LLM
                  </div>
                </div>
              </div>

              {/* Progress & Live Activity Metrics Bar */}
              <div className="space-y-3 font-mono">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-2">
                    <Activity className="h-4 w-4 text-[#C2410C] animate-spin" />
                    Current Step Progress
                  </span>
                  <span className="text-base font-extrabold text-[#E8D5B7]">
                    {Math.round(progress)}%
                  </span>
                </div>

                {/* Progress Bar with Glowing Particle Lead */}
                <div className="relative h-3 w-full rounded-full bg-black/80 border border-white/20 overflow-hidden p-0.5">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-[#B45309] via-[#C2410C] to-[#E8D5B7] shadow-[0_0_20px_rgba(232,213,183,0.8)]"
                    initial={{ width: "0%" }}
                    animate={{ width: `${Math.max(5, progress)}%` }}
                    transition={{ duration: 0.5 }}
                  />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-2">
                  <div className="rounded-xl border border-white/10 bg-black/60 p-2.5">
                    <span className="text-[10px] text-zinc-400 block uppercase">Phase</span>
                    <span className="font-bold text-white mt-0.5 block truncate">{activeAgent.stageName}</span>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/60 p-2.5">
                    <span className="text-[10px] text-zinc-400 block uppercase">Fleet Capacity</span>
                    <span className="font-bold text-[#E8D5B7] mt-0.5 block">21 Agents</span>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/60 p-2.5">
                    <span className="text-[10px] text-zinc-400 block uppercase">Real-Time Clock</span>
                    <span className="font-bold text-emerald-400 mt-0.5 block">{currentTimeStr}</span>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/60 p-2.5">
                    <span className="text-[10px] text-zinc-400 block uppercase">Verification</span>
                    <span className="font-bold text-white mt-0.5 block">100% Grounded</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* ============================================================================ */}
      {/* ORDERED REALTIME TELEMETRY LOGS BELOW THE ACTIVE AGENT */}
      {/* ============================================================================ */}
      <div className="rounded-3xl border border-white/20 bg-[#1E1B18]/90 p-5 sm:p-6 space-y-4 shadow-[0_15px_45px_rgba(0,0,0,0.9)] backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/15 pb-3">
          <div className="flex items-center gap-2.5">
            <Terminal className="h-5 w-5 text-[#E8D5B7]" />
            <h3 className="text-sm sm:text-base font-bold font-display uppercase tracking-wider text-white">
              Ordered Realtime Agent Reasoning Telemetry
            </h3>
          </div>

          <div className="flex items-center gap-3">
            {onStop && !isCancelled && (
              <button
                onClick={onStop}
                className="flex items-center gap-1.5 rounded-xl border border-rose-500/40 bg-rose-950/40 px-3 py-1 text-xs font-bold uppercase tracking-wider text-rose-300 hover:bg-rose-900 hover:text-white transition duration-200"
              >
                <Square className="h-3 w-3 fill-rose-400" />
                Stop Run
              </button>
            )}

            <div className="flex items-center gap-1.5 rounded-full bg-[#C2410C]/20 px-3 py-1 text-xs font-mono font-bold text-[#E8D5B7] border border-[#C2410C]/40">
              <span className="h-2 w-2 rounded-full bg-[#E8D5B7] animate-ping" />
              LIVE STREAMING ({currentTimeStr})
            </div>
          </div>
        </div>

        {/* Scrollable Telemetry Box */}
        <div
          ref={logsContainerRef}
          className="h-56 sm:h-64 overflow-y-auto font-mono text-xs space-y-2.5 custom-scrollbar p-2"
        >
          {telemetryLogs.length === 0 ? (
            <div className="flex h-full items-center justify-center text-xs text-zinc-500 gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-[#E8D5B7]" />
              Connecting to 21-agent event stream...
            </div>
          ) : (
            telemetryLogs.map((log, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                className="flex items-start gap-3 text-zinc-300 leading-relaxed border-b border-white/10 pb-2 hover:bg-white/5 p-1 rounded-lg transition-colors"
              >
                <span className="text-[10px] text-zinc-500 font-mono shrink-0 pt-0.5">
                  [{log.timestamp}]
                </span>
                <span className="rounded-md bg-[#252219] px-2 py-0.5 text-[10px] font-bold uppercase text-[#E8D5B7] border border-white/20 shrink-0">
                  {log.stage}
                </span>
                <span className="text-xs text-white font-sans">{log.message}</span>
              </motion.div>
            ))
          )}
        </div>
      </div>

      {/* ============================================================================ */}
      {/* OPTIONAL TOGGLE FOR COMPLETE 21-AGENT FLEET OVERVIEW */}
      {/* ============================================================================ */}
      <div className="pt-2">
        <button
          onClick={() => setShowFleetDrawer(!showFleetDrawer)}
          className="flex items-center justify-center gap-2 w-full py-2.5 rounded-2xl border border-white/15 bg-black/60 text-xs font-mono font-bold text-zinc-300 hover:text-white hover:border-white transition duration-200"
        >
          <span>{showFleetDrawer ? "Hide Full 21-Agent Fleet Overview" : "View All 21 Fleet Agents Standby Grid"}</span>
          {showFleetDrawer ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>

        <AnimatePresence>
          {showFleetDrawer && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden mt-4"
            >
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-7 gap-3 pt-2">
                {agentStates.map((agent) => {
                  const Icon = agent.icon;
                  const isCurrentActive = agent.id === activeAgent.id;

                  return (
                    <div
                      key={agent.id}
                      className={`rounded-2xl border p-3 text-left transition-all ${
                        isCurrentActive
                          ? "border-[#E8D5B7] bg-[#252219] shadow-[0_0_15px_rgba(232,213,183,0.3)]"
                          : agent.status === "completed"
                          ? "border-white/20 bg-zinc-950 opacity-80"
                          : "border-white/10 bg-black/60 opacity-50"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-mono text-[10px] font-bold text-zinc-400">#{agent.code}</span>
                        <Icon className="h-3.5 w-3.5 text-[#E8D5B7]" />
                      </div>
                      <h4 className="text-xs font-bold font-display text-white truncate">{agent.name}</h4>
                      <div className="text-[9px] font-mono text-zinc-400 uppercase mt-1">
                        {agent.status}
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
