"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BrainCircuit, Activity, Zap, ShieldCheck, Target, Layers, Clock, TrendingUp,
  Cpu, Database, Award, CheckCircle2, RefreshCw, Wifi, WifiOff, BarChart3,
  LineChart, PieChart, AlertTriangle, BookOpen, Search, Filter, ArrowUp, ArrowDown,
  GitBranch, MessageSquare, Network, Globe, Server, Radio,
} from "lucide-react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer,
  LineChart as ReLineChart, Line, CartesianGrid, Legend,
} from "recharts";
import BackgroundCanvas from "@/components/BackgroundCanvas";

type ScoreMap = {
  relevance?: number;
  depth?: number;
  novelty?: number;
  coherence?: number;
  citation_accuracy?: number;
};

type LearningEvent = {
  id: string;
  content_hash?: string;
  created_at: string;
  content: string;
  topic?: string;
  query?: string;
  proof?: string;
  optimization?: string;
  analysis?: {
    scores?: ScoreMap;
    lesson?: string;
  };
};

type KpiData = {
  total_lessons: number;
  avg_quality: number;
  quality_delta: number;
  token_efficiency: number;
  recent_scores: { id: string; query: string; scores: ScoreMap; created_at: string }[];
};

type ProtocolAudit = {
  protocols: { name: string; layer: string; reliability: string; risk: string }[];
};

const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

const PROTOCOL_INFO: ProtocolAudit = {
  protocols: [
    { name: "LangGraph State", layer: "In-process", reliability: "High", risk: "Low" },
    { name: "Event Queue", layer: "In-process", reliability: "Medium", risk: "Low-Med" },
    { name: "SSE Streaming", layer: "HTTP", reliability: "High", risk: "Low" },
    { name: "REST API", layer: "HTTP", reliability: "High", risk: "Low" },
    { name: "n8n Webhook", layer: "HTTP", reliability: "Medium", risk: "Low" },
  ],
};

const RADAR_DIMS = ["relevance", "depth", "novelty", "coherence", "citation_accuracy"];

export default function LearningHistoryPage() {
  const [lessons, setLessons] = useState<LearningEvent[]>([]);
  const [kpi, setKpi] = useState<KpiData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"all" | "high" | "critical">("all");
  const [viewTab, setViewTab] = useState<"timeline" | "analytics" | "protocols">("timeline");
  const [connected, setConnected] = useState(false);
  const [selectedLesson, setSelectedLesson] = useState<LearningEvent | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const seenHashes = useRef<Set<string>>(new Set());

  const fetchInitial = useCallback(async () => {
    try {
      const [lessonsRes, kpiRes] = await Promise.all([
        fetch(`${apiBase}/api/v1/learning-history`),
        fetch(`${apiBase}/api/v1/learning-history/kpi`),
      ]);
      if (lessonsRes.ok) {
        const data = await lessonsRes.json();
        if (Array.isArray(data) && data.length > 0) {
          setLessons(data);
          data.forEach((l: LearningEvent) => {
            if (l.content_hash) seenHashes.current.add(l.content_hash);
            else if (l.id) seenHashes.current.add(l.id);
          });
        }
      }
      if (kpiRes.ok) setKpi(await kpiRes.json());
    } catch (err) {
      console.error("Failed to fetch learning history", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchInitial();
    const es = new EventSource(`${apiBase}/api/v1/learning-history/stream`);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (evt) => {
      try {
        const lesson = JSON.parse(evt.data) as LearningEvent;
        const key = lesson.content_hash || lesson.id;
        if (key && !seenHashes.current.has(key)) {
          seenHashes.current.add(key);
          setLessons((prev) => [lesson, ...prev]);
          fetch(`${apiBase}/api/v1/learning-history/kpi`)
            .then((r) => { if (r.ok) r.json().then(setKpi).catch(() => {}); })
            .catch(() => {});
        }
      } catch {}
    };
    eventSourceRef.current = es;
    return () => { es.close(); eventSourceRef.current = null; };
  }, [fetchInitial]);

  const getOverallScore = (l: LearningEvent) => {
    const scores = l.analysis?.scores || {};
    const values = Object.values(scores).filter((s): s is number => typeof s === "number");
    return values.length ? Number((values.reduce((a, b) => a + b, 0) / values.length).toFixed(1)) : 0;
  };

  const filteredLessons = lessons.filter((l) => {
    const o = getOverallScore(l);
    if (activeTab === "high") return o >= 8.5;
    if (activeTab === "critical") return o < 8.5 && o > 0;
    return true;
  });

  // Chart data
  const timelineData = [...lessons].reverse().map((l, i) => {
    const scores = l.analysis?.scores || {};
    const overall = getOverallScore(l);
    return {
      index: i + 1,
      overall,
      ...Object.fromEntries(RADAR_DIMS.map((d) => [d, scores[d as keyof ScoreMap] ?? null])),
      label: l.query?.slice(0, 24) || l.content_hash?.slice(0, 8) || `Run ${i + 1}`,
    };
  });

  const radarData = selectedLesson?.analysis?.scores
    ? RADAR_DIMS.map((d) => ({
        dimension: d.charAt(0).toUpperCase() + d.slice(1).replace("_", " "),
        score: selectedLesson.analysis?.scores?.[d as keyof ScoreMap] ?? 0,
      }))
    : lessons.length > 0
    ? (() => {
        const avg: Record<string, number[]> = {};
        lessons.forEach((l) => {
          RADAR_DIMS.forEach((d) => {
            const v = l.analysis?.scores?.[d as keyof ScoreMap];
            if (typeof v === "number") {
              (avg[d] = avg[d] || []).push(v);
            }
          });
        });
        return RADAR_DIMS.map((d) => ({
          dimension: d.charAt(0).toUpperCase() + d.slice(1).replace("_", " "),
          score: avg[d] ? Number((avg[d].reduce((a, b) => a + b, 0) / avg[d].length).toFixed(1)) : 0,
        }));
      })()
    : [];

  const stageColors = ["#C2410C", "#B45309", "#A16207", "#4D7C5F", "#D4A853", "#92400E", "#78716C", "#E8D5B7", "#9A8B73"];
  const protocolColors = ["#4D7C5F", "#C2410C", "#D4A853", "#B45309", "#78716C"];

  return (
    <main className="min-h-screen relative bg-black text-white p-4 sm:p-8 md:p-12 lg:p-16 pb-32 mx-auto w-full pt-16 max-w-[1400px]">
      <BackgroundCanvas />

      {/* Connection badge */}
      <div className="fixed top-4 right-4 z-50 flex items-center gap-2 text-[10px] font-mono">
        <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-400 shadow-[0_0_6px_rgba(74,222,128,0.6)]" : "bg-red-400"}`} />
        <span className="text-zinc-500">{connected ? "Live" : "Disconnected"}</span>
        {!connected && (
          <button onClick={fetchInitial} className="text-zinc-400 hover:text-white transition-colors">
            <RefreshCw className="w-3 h-3" />
          </button>
        )}
      </div>

      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }} className="mb-8 relative z-10 space-y-3">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-4 py-1.5 text-xs font-mono font-semibold tracking-wider text-white shadow-[0_0_20px_rgba(255,255,255,0.15)]">
          <BrainCircuit className="h-3.5 w-3.5" />
          <span>Self-Learning Neural Dashboard</span>
          {connected ? <Wifi className="h-3 w-3 text-green-400 ml-1" /> : <WifiOff className="h-3 w-3 text-red-400 ml-1" />}
        </div>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-black font-display tracking-tight text-white flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-white text-black font-bold flex items-center justify-center shadow-md">
                <Activity className="w-5 h-5" strokeWidth={2.5} />
              </div>
              Learning & Adaptation Dashboard
            </h1>
            <p className="text-zinc-300 mt-2 max-w-3xl text-sm leading-relaxed">
              Real-time self-improvement metrics, quality scoring, cross-run analysis, and agent protocol telemetry.
            </p>
          </div>
        </div>
      </motion.div>

      {/* View Tabs */}
      <div className="flex items-center gap-1.5 mb-8 bg-zinc-950 border border-white/25 rounded-xl p-1 text-xs shadow-md w-fit relative z-10">
        {(["timeline", "analytics", "protocols"] as const).map((tab) => (
          <button key={tab} onClick={() => setViewTab(tab)}
            className={`px-4 py-2 rounded-lg font-semibold font-mono transition-all flex items-center gap-2 ${
              viewTab === tab ? "bg-white text-black shadow-md font-bold" : "text-zinc-400 hover:text-white"
            }`}>
            {tab === "timeline" ? <Activity className="w-3.5 h-3.5" /> : tab === "analytics" ? <BarChart3 className="w-3.5 h-3.5" /> : <Network className="w-3.5 h-3.5" />}
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* KPI Cards */}
      <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8 relative z-10">
        <div className="rounded-2xl border border-white/25 bg-zinc-950 p-5 space-y-2 shadow-[0_10px_35px_rgba(0,0,0,0.8)] card-hover-tilt">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-zinc-400 font-semibold font-mono uppercase tracking-wider">Reflection Loops</span>
            <div className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center text-white border border-white/30">
              <BrainCircuit className="w-4 h-4" />
            </div>
          </div>
          <h3 className="text-3xl font-black font-display text-white">{kpi?.total_lessons ?? lessons.length}</h3>
          <p className="text-xs text-zinc-400 flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5 text-white" />
            {kpi?.total_lessons ? `${kpi.total_lessons} lesson${kpi.total_lessons !== 1 ? "s" : ""} archived` : "Run a query to start learning"}
          </p>
        </div>

        <div className="rounded-2xl border border-white/25 bg-zinc-950 p-5 space-y-2 shadow-[0_10px_35px_rgba(0,0,0,0.8)] card-hover-tilt">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-zinc-400 font-semibold font-mono uppercase tracking-wider">Avg Quality Index</span>
            <div className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center text-white border border-white/30">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <h3 className="text-3xl font-black font-display text-white">{kpi?.avg_quality ? `${kpi.avg_quality}` : "—"}</h3>
          <p className="text-xs text-zinc-400 flex items-center gap-1">
            {kpi?.quality_delta !== undefined && kpi.quality_delta !== 0 ? (
              <span className={`inline-flex items-center gap-0.5 font-bold ${kpi.quality_delta > 0 ? "text-green-400" : "text-red-400"}`}>
                {kpi.quality_delta > 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
                {kpi.quality_delta > 0 ? "+" : ""}{kpi.quality_delta} delta
              </span>
            ) : "Baseline — more runs needed"}
            <span className="text-zinc-500 ml-1">/10</span>
          </p>
        </div>

        <div className="rounded-2xl border border-white/25 bg-zinc-950 p-5 space-y-2 shadow-[0_10px_35px_rgba(0,0,0,0.8)] card-hover-tilt">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-zinc-400 font-semibold font-mono uppercase tracking-wider">Quality Trend</span>
            <div className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center text-white border border-white/30">
              <LineChart className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-1 flex-wrap">
            {kpi?.recent_scores && kpi.recent_scores.length > 0 ? (
              kpi.recent_scores.slice(0, 6).map((r, i) => {
                const vals = Object.values(r.scores).filter((v): v is number => typeof v === "number");
                const avg = vals.length ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1) : "—";
                return <span key={i} className="text-xs font-mono bg-white/10 px-1.5 py-0.5 rounded border border-white/20">{avg}</span>;
              })
            ) : <span className="text-xs text-zinc-400">—</span>}
          </div>
          <p className="text-xs text-zinc-400">Per-run quality scores</p>
        </div>

        <div className="rounded-2xl border border-white/25 bg-zinc-950 p-5 space-y-2 shadow-[0_10px_35px_rgba(0,0,0,0.8)] card-hover-tilt">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-zinc-400 font-semibold font-mono uppercase tracking-wider">Adaptation Velocity</span>
            <div className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center text-white border border-white/30">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <h3 className="text-3xl font-black font-display text-white">
            {kpi?.total_lessons && kpi.total_lessons > 0
              ? (kpi.avg_quality / Math.max(1, kpi.total_lessons)).toFixed(2) + "x"
              : "—"}
          </h3>
          <p className="text-xs text-zinc-400">Quality per learning iteration</p>
        </div>
      </motion.div>

      {/* Content by tab */}
      {viewTab === "timeline" && (
        <>
          {/* Filter tabs */}
          <div className="flex items-center gap-1.5 mb-6 bg-zinc-950 border border-white/25 rounded-xl p-1 text-xs shadow-md w-fit relative z-10">
            {(["all", "high", "critical"] as const).map((tab) => (
              <button key={tab} onClick={() => setActiveTab(tab)}
                className={`px-3.5 py-2 rounded-lg font-semibold font-mono transition-all ${
                  activeTab === tab ? "bg-white text-black shadow-md font-bold" : "text-zinc-400 hover:text-white"
                }`}>
                {tab === "all" ? "All Runs" : tab === "high" ? "High Quality (\u22658.5)" : "Critical (<8.5)"}
              </button>
            ))}
          </div>

          {/* Timeline */}
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-20 space-y-3">
              <span className="w-8 h-8 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              <p className="text-xs text-zinc-400 font-mono uppercase tracking-widest">Compiling neural history...</p>
            </div>
          ) : filteredLessons.length === 0 ? (
            <div className="rounded-2xl border border-white/20 bg-zinc-950 p-12 text-center space-y-3">
              <Activity className="w-12 h-12 text-zinc-600 mx-auto" strokeWidth={1.5} />
              <h3 className="text-base font-bold font-display text-white">
                {lessons.length === 0 ? "No Learning Events" : "No Runs Match Filter"}
              </h3>
              <p className="text-xs text-zinc-400">
                {lessons.length === 0 ? "Submit a research query to generate the first learning event." : "Try adjusting the quality filter."}
              </p>
            </div>
          ) : (
            <div className="relative border-l border-white/25 ml-3 sm:ml-5 space-y-6 pb-10">
              <AnimatePresence mode="popLayout">
                {filteredLessons.map((lesson, i) => {
                  const scores = lesson.analysis?.scores || {};
                  const overall = getOverallScore(lesson);
                  const date = new Date(lesson.created_at || "1970-01-01T00:00:00.000Z").toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
                  const isSelected = selectedLesson?.content_hash === lesson.content_hash;
                  return (
                    <motion.div key={lesson.content_hash || lesson.id || i}
                      initial={{ opacity: 0, x: -20 }} whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true, margin: "-30px" }}
                      transition={{ duration: 0.4, delay: i * 0.05 }}
                      className="relative pl-6 sm:pl-10">
                      <div className="absolute -left-2 top-2.5 w-4 h-4 rounded-full bg-black border-2 border-white z-10 flex items-center justify-center">
                        <div className="w-1.5 h-1.5 rounded-full bg-white" />
                      </div>
                      <div className={`rounded-2xl border ${isSelected ? "border-white/50" : "border-white/25"} bg-zinc-950 p-5 space-y-4 shadow-[0_10px_35px_rgba(0,0,0,0.8)] cursor-pointer transition-all hover:border-white/40`}
                        onClick={() => setSelectedLesson(isSelected ? null : lesson)}>
                        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                          <div className="flex-1 min-w-0 space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="text-[10px] bg-white/15 text-white px-2.5 py-0.5 rounded font-mono font-bold uppercase tracking-wider flex items-center gap-1 border border-white/30">
                                <Zap className="w-3 h-3" /> Reflection
                              </span>
                              <span className="text-xs text-zinc-500">&bull;</span>
                              <span className="text-[10px] text-zinc-400 font-mono flex items-center gap-1">
                                <Clock className="w-3 h-3" />{date}
                              </span>
                              {lesson.query && <>
                                <span className="text-xs text-zinc-500">&bull;</span>
                                <span className="text-[10px] text-zinc-400 font-mono truncate max-w-[200px]">{lesson.query}</span>
                              </>}
                            </div>
                            <h3 className="text-sm sm:text-base font-bold font-display text-white leading-snug">
                              <span className="text-zinc-400 mr-1.5">Lesson:</span>
                              {lesson.analysis?.lesson || lesson.content}
                            </h3>
                          </div>
                          {overall > 0 && (
                            <div className="flex-shrink-0 flex items-center gap-3 bg-black border border-white/25 rounded-xl px-4 py-3">
                              <div className="text-center">
                                <p className="text-[9px] text-zinc-500 font-mono uppercase tracking-widest">Overall</p>
                                <p className="text-2xl font-black font-display text-white">{overall}</p>
                              </div>
                              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono">
                                <span className="text-zinc-400">Rel <span className="font-bold text-white">{scores.relevance ?? "-"}</span></span>
                                <span className="text-zinc-400">Dpt <span className="font-bold text-white">{scores.depth ?? "-"}</span></span>
                                <span className="text-zinc-400">Nov <span className="font-bold text-white">{scores.novelty ?? "-"}</span></span>
                                <span className="text-zinc-400">Coh <span className="font-bold text-white">{scores.coherence ?? "-"}</span></span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          )}
        </>
      )}

      {viewTab === "analytics" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative z-10">
          {/* Quality Score Radar */}
          <div className="rounded-2xl border border-white/25 bg-zinc-950 p-6 shadow-[0_10px_35px_rgba(0,0,0,0.8)]">
            <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Target className="w-3.5 h-3.5 text-white" />
              {selectedLesson ? "Selected Run Quality" : "Average Quality Scores"} ({lessons.length} runs)
            </h4>
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="rgba(255,255,255,0.15)" />
                  <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 11, fill: "rgba(255,255,255,0.6)" }} />
                  <PolarRadiusAxis domain={[0, 10]} tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }} />
                  <Radar name="Score" dataKey="score" stroke="#C2410C" fill="#C2410C" fillOpacity={0.15} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            ) : <p className="text-sm text-zinc-500 italic">No quality data yet</p>}
            {selectedLesson && (
              <button onClick={() => setSelectedLesson(null)}
                className="mt-3 text-xs text-zinc-400 hover:text-white font-mono flex items-center gap-1">
                <RefreshCw className="w-3 h-3" /> Show averages
              </button>
            )}
          </div>

          {/* Quality Trend Line */}
          <div className="rounded-2xl border border-white/25 bg-zinc-950 p-6 shadow-[0_10px_35px_rgba(0,0,0,0.8)]">
            <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <TrendingUp className="w-3.5 h-3.5 text-white" />
              Quality Score Trend
            </h4>
            {timelineData.length >= 2 ? (
              <ResponsiveContainer width="100%" height={300}>
                <ReLineChart data={timelineData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                  <XAxis dataKey="label" tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }} />
                  <Tooltip contentStyle={{ background: "#09090B", border: "1px solid rgba(255,255,255,0.2)", borderRadius: 8, fontSize: 12 }} />
                  <Line type="monotone" dataKey="overall" stroke="#C2410C" strokeWidth={2} dot={{ fill: "#C2410C", r: 3 }} name="Overall" />
                  {RADAR_DIMS.map((d, i) => (
                    <Line key={d} type="monotone" dataKey={d} stroke={stageColors[i]} strokeWidth={1} dot={false} strokeDasharray="4 2" name={d} />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 10, color: "rgba(255,255,255,0.6)" }} />
                </ReLineChart>
              </ResponsiveContainer>
            ) : <p className="text-sm text-zinc-500 italic">{timelineData.length === 1 ? "One run recorded — need 2+ for trend" : "No trend data yet"}</p>}
          </div>

          {/* Dimension Breakdown */}
          <div className="rounded-2xl border border-white/25 bg-zinc-950 p-6 shadow-[0_10px_35px_rgba(0,0,0,0.8)]">
            <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <BarChart3 className="w-3.5 h-3.5 text-white" />
              Per-Dimension Score History
            </h4>
            {timelineData.length >= 2 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={timelineData}>
                  <XAxis dataKey="label" tick={{ fontSize: 9, fill: "rgba(255,255,255,0.4)" }} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)" }} />
                  <Tooltip contentStyle={{ background: "#09090B", border: "1px solid rgba(255,255,255,0.2)", borderRadius: 8, fontSize: 12 }} />
                  {RADAR_DIMS.map((d, i) => (
                    <Bar key={d} dataKey={d} stackId="a" fill={stageColors[i]} name={d.charAt(0).toUpperCase() + d.slice(1).replace("_", " ")} />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 10, color: "rgba(255,255,255,0.6)" }} />
                </BarChart>
              </ResponsiveContainer>
            ) : <p className="text-sm text-zinc-500 italic">Need 2+ runs for dimension breakdown</p>}
          </div>

          {/* Adaptive Profile Stats */}
          <div className="rounded-2xl border border-white/25 bg-zinc-950 p-6 shadow-[0_10px_35px_rgba(0,0,0,0.8)]">
            <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-white" />
              Adaptive Profile Adjustments
            </h4>
            <div className="space-y-3 text-sm">
              <p className="text-zinc-300">
                Pipeline parameters are automatically adjusted based on past per-dimension quality scores.
                Low <span className="text-orange-400 font-bold">citation_accuracy</span> increases sub-question count.
                Low <span className="text-orange-400 font-bold">depth</span> increases target paragraphs and recursion depth.
              </p>
              <div className="grid grid-cols-2 gap-3 mt-4">
                <div className="bg-black border border-white/20 rounded-xl p-3">
                  <p className="text-[10px] text-zinc-500 font-mono uppercase">Parameter</p>
                  <p className="text-xs text-zinc-300 mt-1">depth, complexity, paragraphs, sub_questions</p>
                </div>
                <div className="bg-black border border-white/20 rounded-xl p-3">
                  <p className="text-[10px] text-zinc-500 font-mono uppercase">Trigger</p>
                  <p className="text-xs text-zinc-300 mt-1">Per-dimension score below threshold (6/10)</p>
                </div>
                <div className="bg-black border border-white/20 rounded-xl p-3">
                  <p className="text-[10px] text-zinc-500 font-mono uppercase">Persistence</p>
                  <p className="text-xs text-zinc-300 mt-1">quality_history.json (survives restarts)</p>
                </div>
                <div className="bg-black border border-white/20 rounded-xl p-3">
                  <p className="text-[10px] text-zinc-500 font-mono uppercase">Status</p>
                  <p className="text-xs text-green-400 mt-1">Active</p>
                </div>
              </div>
            </div>
          </div>

          {/* Self-Improvement Summary */}
          <div className="rounded-2xl border border-white/25 bg-zinc-950 p-6 shadow-[0_10px_35px_rgba(0,0,0,0.8)] col-span-1 lg:col-span-2">
            <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-4 flex items-center gap-2">
              <GitBranch className="w-3.5 h-3.5 text-white" />
              Feedback Loop Architecture
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
              <div className="bg-black border border-white/20 rounded-xl p-4 space-y-1">
                <p className="text-white font-bold flex items-center gap-1"><Search className="w-3 h-3" /> 1. Evaluate</p>
                <p className="text-zinc-400">Quality scores computed on 5 dims (relevance, depth, novelty, coherence, citation)</p>
              </div>
              <div className="bg-black border border-white/20 rounded-xl p-4 space-y-1">
                <p className="text-white font-bold flex items-center gap-1"><Database className="w-3 h-3" /> 2. Persist</p>
                <p className="text-zinc-400">Lessons + scores saved to SQLite + Supabase + in-memory knowledge base</p>
              </div>
              <div className="bg-black border border-white/20 rounded-xl p-4 space-y-1">
                <p className="text-white font-bold flex items-center gap-1"><MessageSquare className="w-3 h-3" /> 3. Retrieve</p>
                <p className="text-zinc-400">get_lessons_by_topic fetches relevant lessons with score context for planner</p>
              </div>
              <div className="bg-black border border-white/20 rounded-xl p-4 space-y-1">
                <p className="text-white font-bold flex items-center gap-1"><Cpu className="w-3 h-3" /> 4. Adapt</p>
                <p className="text-zinc-400">Adaptive profile adjusts 4 pipeline params based on prior dimension history</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {viewTab === "protocols" && (
        <div className="space-y-6 relative z-10">
          {PROTOCOL_INFO.protocols.map((p, i) => {
            const riskColor = p.risk === "Low" ? "text-green-400" : p.risk === "Low-Med" ? "text-yellow-400" : "text-red-400";
            const relColor = p.reliability === "High" ? "text-green-400" : "text-yellow-400";
            return (
              <motion.div key={p.name} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
                className="rounded-2xl border border-white/25 bg-zinc-950 p-6 shadow-[0_10px_35px_rgba(0,0,0,0.8)]">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-white/10 border border-white/30 flex items-center justify-center">
                      {i === 0 ? <GitBranch className="w-5 h-5 text-white" /> :
                       i === 1 ? <Server className="w-5 h-5 text-white" /> :
                       i === 2 ? <Radio className="w-5 h-5 text-white" /> :
                       i === 3 ? <Globe className="w-5 h-5 text-white" /> :
                       <Network className="w-5 h-5 text-white" />}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold font-display text-white">{p.name}</h3>
                      <p className="text-[10px] text-zinc-500 font-mono">Layer: {p.layer}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-[11px] font-mono">
                    <span className="flex items-center gap-1">
                      <span className={`w-2 h-2 rounded-full ${p.reliability === "High" ? "bg-green-400" : "bg-yellow-400"}`} />
                      Reliability: <span className={relColor}>{p.reliability}</span>
                    </span>
                    <span className="flex items-center gap-1">
                      Risk: <span className={riskColor}>{p.risk}</span>
                    </span>
                  </div>
                </div>
                <p className="text-xs text-zinc-400">
                  {p.name === "LangGraph State" && "TypedDict-based AgentState flows through 9 LangGraph nodes. List fields use operator.add for automatic merging. MemorySaver checkpointing enabled."}
                  {p.name === "Event Queue" && "Thread-safe queue.Queue per session passed via RunnableConfig. Nodes push structured events (node transitions, thoughts, track status, source URLs). SSE generator polls on 50ms interval."}
                  {p.name === "SSE Streaming" && "FastAPI StreamingResponse with text/event-stream. Events: node transitions, thought traces, track status, quality_scores, source URLs. Frontend reads via EventSource API."}
                  {p.name === "REST API" && "8 endpoints under /api/v1/. Research trigger (POST -> SSE), cancel, sessions, metrics, export, learning history, learning stream, learning KPI."}
                  {p.name === "n8n Webhook" && "HTTP POST to localhost:5678 for parallel Ollama sub-question processing. 30s timeout. Graceful degradation — falls back to web search if n8n offline."}
                </p>
              </motion.div>
            );
          })}
        </div>
      )}
    </main>
  );
}
