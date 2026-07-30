"use client";

import React from "react";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer
} from "recharts";
import { TrendingUp, Cpu, BookOpen, Target, Zap, Activity, ArrowUp, ArrowDown } from "lucide-react";

interface MetricsData {
  execution: { total_duration_ms: number; node_timings_ms: Record<string, number>; node_order: string[] };
  breadth: { depth: number; sub_questions: number; search_queries: number; sources_found: number; gap_iterations: number };
  efficiency: { total_llm_calls: number; llm_calls_per_stage: Record<string, number>; estimated_input_tokens: number; estimated_output_tokens: number };
  quality: { scores: Record<string, number>; overall: number | null };
  proof_of_improvement: {
    prior_lessons_count: number; prior_lessons: string[];
    history_count?: number; average_prior_quality?: number; quality_delta?: number;
  };
}

// Warm palette stage colors — no blue/purple/cyan
const STAGE_COLORS: Record<string, string> = {
  planner: "#C2410C",       // ember
  searcher: "#B45309",      // deep amber
  filter: "#A16207",        // warm gold
  synthesis: "#4D7C5F",     // sage
  gap_detector: "#D4A853",  // amber
  citation_mapper: "#92400E", // terracotta
  report: "#78716C",        // warm gray
  report_node_id: "#78716C", // alias used by backend timings
  evaluator: "#E8D5B7",     // cream
  memory_retrieval: "#9A8B73", // khaki
};

export default function MetricsDashboard({ metrics }: { metrics: MetricsData }) {
  const { execution, breadth, efficiency, quality, proof_of_improvement: proof } = metrics;

  const radarData = Object.entries(quality.scores).map(([key, val]) => ({
    dimension: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    score: val,
    fullMark: 10,
  }));

  const timingData = Object.entries(execution.node_timings_ms || {})
    .filter(([, v]) => v > 0)
    .sort(([, a], [, b]) => b - a)
    .map(([stage, ms]) => ({ stage: stage.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()), ms }));

  const llmStageData = Object.entries(efficiency.llm_calls_per_stage || {})
    .map(([stage, count]) => ({ stage: stage.replace(/\b\w/g, (c) => c.toUpperCase()), count }));

  const overall = quality.overall;
  const delta = proof.quality_delta;
  const hasHistory = (proof.history_count ?? 0) > 0;

  return (
    <div className="w-full mb-10">
      <div className="glass-panel p-6 sm:p-8">
        <div className="flex items-center justify-between mb-6 border-b border-[var(--border)] pb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[var(--accent-ember)]/10 border border-[var(--accent-ember)]/15 flex items-center justify-center">
              <Activity className="w-4 h-4 text-[var(--accent-ember)]" strokeWidth={1.5} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[var(--text-1)] font-display">Research Metrics</h3>
              <p className="text-xs text-[var(--text-3)] font-mono">Quantitative performance analysis</p>
            </div>
          </div>
          {overall !== null && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)]">
              <span className="text-xs text-[var(--text-3)] font-mono uppercase tracking-wider">Quality</span>
              <span className="text-xl font-bold text-[var(--accent-ember)]">{overall}<span className="text-sm text-[var(--text-3)]">/10</span></span>
            </div>
          )}
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          <StatCard
            icon={<Cpu className="w-4 h-4" strokeWidth={1.5} />}
            value={`${(execution.total_duration_ms / 1000).toFixed(1)}s`}
            label="Total Time"
            color="var(--accent-ember)"
          />
          <StatCard
            icon={<Zap className="w-4 h-4" strokeWidth={1.5} />}
            value={String(efficiency.total_llm_calls)}
            label="LLM Calls"
            color="var(--accent-gold)"
          />
          <StatCard
            icon={<Target className="w-4 h-4" strokeWidth={1.5} />}
            value={String(breadth.sub_questions)}
            label="Sub-Questions"
            color="var(--brand-primary)"
          />
          <StatCard
            icon={<BookOpen className="w-4 h-4" strokeWidth={1.5} />}
            value={String(breadth.sources_found)}
            label="Sources"
            color="var(--accent-sage)"
          />
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Quality Radar */}
          <div className="stat-card">
            <h4 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-4 flex items-center gap-2">
              <Target className="w-3.5 h-3.5 text-[var(--accent-ember)]" strokeWidth={1.5} />
              Quality Scores
            </h4>
            {radarData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 11, fill: "var(--text-2)" }} />
                  <PolarRadiusAxis domain={[0, 10]} tick={{ fontSize: 10, fill: "var(--text-3)" }} />
                  <Radar name="Score" dataKey="score" stroke="#C2410C" fill="#C2410C" fillOpacity={0.12} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-[var(--text-3)] italic">No quality scores available</p>
            )}
          </div>

          {/* Time per Stage */}
          <div className="stat-card">
            <h4 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-4 flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-[var(--accent-gold)]" strokeWidth={1.5} />
              Time per Stage (ms)
            </h4>
            {timingData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={timingData} layout="vertical" margin={{ left: 20, right: 20 }}>
                  <XAxis type="number" tick={{ fontSize: 10, fill: "var(--text-3)" }} />
                  <YAxis type="category" dataKey="stage" width={100} tick={{ fontSize: 10, fill: "var(--text-2)" }} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      fontSize: 12,
                      color: "var(--text-1)"
                    }}
                    formatter={(val) => [`${Number(val).toFixed(0)} ms`, "Duration"]}
                  />
                  <Bar dataKey="ms" radius={[0, 4, 4, 0]}>
                    {timingData.map((entry) => (
                      <Cell key={entry.stage} fill={STAGE_COLORS[entry.stage.toLowerCase().replace(/ /g, "_")] || "#D4A853"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-[var(--text-3)] italic">No timing data available</p>
            )}
          </div>
        </div>

        {/* Efficiency & Improvement */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="stat-card">
            <h4 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-4 flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-[var(--accent-gold)]" strokeWidth={1.5} />
              Efficiency
            </h4>
            <div className="space-y-2.5 text-sm">
              <Row label="Total LLM Calls" value={String(efficiency.total_llm_calls)} />
              <Row label="Est. Input Tokens" value={String(efficiency.estimated_input_tokens)} />
              <Row label="Est. Output Tokens" value={String(efficiency.estimated_output_tokens)} />
              <Row label="Gap-Fill Iterations" value={String(breadth.gap_iterations)} />
              <Row label="Recursion Depth" value={String(breadth.depth)} />
            </div>
          </div>

          <div className="stat-card">
            <h4 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-4 flex items-center gap-2">
              <TrendingUp className="w-3.5 h-3.5 text-[var(--accent-sage)]" strokeWidth={1.5} />
              Proof of Improvement
            </h4>
            <div className="space-y-2.5 text-sm">
              <Row label="Prior Lessons Applied" value={String(proof.prior_lessons_count)} />
              {proof.prior_lessons.length > 0 && (
                <div className="mt-3 pl-3 border-l-2 border-[var(--accent-ember)]/30 space-y-1.5">
                  {proof.prior_lessons.slice(0, 3).map((l, i) => (
                    <p key={i} className="text-xs text-[var(--text-3)] italic leading-relaxed">&ldquo;{l}&rdquo;</p>
                  ))}
                </div>
              )}
              {hasHistory ? (
                <div className="mt-4 p-4 rounded-xl bg-[var(--accent-ember)]/6 border border-[var(--accent-ember)]/12 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[var(--text-2)]">Historical Runs</span>
                    <span className="text-sm font-bold text-[var(--text-1)]">{proof.history_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-[var(--text-2)]">Avg Prior Quality</span>
                    <span className="text-sm font-bold text-[var(--text-1)]">{proof.average_prior_quality}/10</span>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-[var(--accent-ember)]/10">
                    <span className="text-xs text-[var(--text-2)]">Quality Delta</span>
                    <span className={`text-sm font-bold flex items-center gap-1 ${delta && delta >= 0 ? 'text-[var(--accent-sage)]' : 'text-[var(--accent-ember)]'}`}>
                      {delta && delta >= 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
                      {delta !== undefined ? `${delta >= 0 ? "+" : ""}${delta}/10` : "N/A"}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-xs italic text-[var(--text-3)] mt-2">
                  No historical data yet. This run becomes the baseline.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* LLM Calls per Stage */}
        {llmStageData.length > 0 && (
          <div className="mt-8 pt-6 border-t border-[var(--border)]">
            <h4 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-4 flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-[var(--brand-primary)]" strokeWidth={1.5} />
              LLM Calls per Stage
            </h4>
            <div className="flex flex-wrap gap-2">
              {llmStageData.map(({ stage, count }) => (
                <span key={stage} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--card)] border border-[var(--border)] text-[var(--text-1)]">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: STAGE_COLORS[stage.toLowerCase().replace(/ /g, "_")] || "#D4A853" }} />
                  {stage}: {count}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon, value, label, color }: { icon: React.ReactNode; value: string; label: string; color: string }) {
  return (
    <div className="stat-card flex items-center gap-3">
      <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}15`, border: `1px solid ${color}25` }}>
        <span style={{ color }}>{icon}</span>
      </div>
      <div>
        <div className="text-lg sm:text-xl font-bold text-[var(--text-1)]">{value}</div>
        <div className="text-[10px] text-[var(--text-3)] uppercase tracking-wider font-mono">{label}</div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-[var(--border)]/20 last:border-0">
      <span className="text-[var(--text-3)] text-xs">{label}</span>
      <span className="font-mono text-sm font-medium text-[var(--text-1)]">{value}</span>
    </div>
  );
}
