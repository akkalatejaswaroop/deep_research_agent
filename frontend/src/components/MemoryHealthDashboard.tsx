"use client";

import React, { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ResponsiveContainer,
  LineChart, Line, CartesianGrid
} from "recharts";
import { Database, Archive, TrendingUp, Timer, GitBranch, Layers } from "lucide-react";

interface MemoryHealthData {
  tiers: { hot: number; warm: number; cold: number; total: number };
  consolidation: { events_this_period: number; avg_cluster_size: number; max_depth: number };
  index: { main_vectors: number; cold_vectors: number; total_vectors: number };
  config: {
    hot_runs: number; hot_days: number; cold_idle_days: number; cold_confidence: number;
    min_cluster: number; every_n_runs: number; cluster_sim_threshold: number; max_depth: number;
  };
}

export default function MemoryHealthDashboard() {
  const [data, setData] = useState<MemoryHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchHealth() {
      try {
        const res = await fetch("/api/v1/memory/health");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to fetch memory health");
      } finally {
        setLoading(false);
      }
    }
    fetchHealth();
  }, []);

  if (loading) {
    return (
      <div className="glass-panel p-6 sm:p-8">
        <div className="flex items-center justify-between mb-6 border-b border-[var(--border)] pb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[var(--accent-sage)]/10 border border-[var(--accent-sage)]/15 flex items-center justify-center">
              <Database className="w-4 h-4 text-[var(--accent-sage)]" strokeWidth={1.5} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[var(--text-1)] font-display">Memory Health</h3>
              <p className="text-xs text-[var(--text-3)] font-mono">Tier distribution, consolidation activity, index scaling</p>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-[var(--accent-sage)] border-t-transparent" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="glass-panel p-6 sm:p-8">
        <div className="flex items-center justify-between mb-6 border-b border-[var(--border)] pb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[var(--accent-ember)]/10 border border-[var(--accent-ember)]/15 flex items-center justify-center">
              <Database className="w-4 h-4 text-[var(--accent-ember)]" strokeWidth={1.5} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[var(--text-1)] font-display">Memory Health</h3>
              <p className="text-xs text-[var(--text-3)] font-mono">Tier distribution, consolidation activity, index scaling</p>
            </div>
          </div>
        </div>
        <p className="text-sm text-[var(--text-3)] italic">Unable to load memory health: {error || "unknown error"}</p>
      </div>
    );
  }

  const { tiers, consolidation, index, config } = data;
  const tierData = [
    { tier: "HOT", count: tiers.hot, color: "#C2410C", desc: `Last ${config.hot_runs} runs / ${config.hot_days} days` },
    { tier: "WARM", count: tiers.warm, color: "#B45309", desc: "Active, not recently touched" },
    { tier: "COLD", count: tiers.cold, color: "#78716C", desc: `Idle >${config.cold_idle_days}d, conf <${config.cold_confidence}` },
  ];

  const total = tiers.total || 1;
  const hotPct = Math.round((tiers.hot / total) * 100);
  const warmPct = Math.round((tiers.warm / total) * 100);
  const coldPct = Math.round((tiers.cold / total) * 100);

  return (
    <div className="glass-panel p-6 sm:p-8">
      <div className="flex items-center justify-between mb-6 border-b border-[var(--border)] pb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[var(--accent-sage)]/10 border border-[var(--accent-sage)]/15 flex items-center justify-center">
            <Database className="w-4 h-4 text-[var(--accent-sage)]" strokeWidth={1.5} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-[var(--text-1)] font-display">Memory Health</h3>
            <p className="text-xs text-[var(--text-3)] font-mono">Tier distribution, consolidation activity, index scaling</p>
          </div>
        </div>
      </div>

      {/* Tier Distribution Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8">
        {tierData.map((t) => (
          <div key={t.tier} className="stat-card flex items-center gap-3 p-4" style={{ borderColor: `${t.color}40` }}>
            <div className="w-12 h-12 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${t.color}15`, border: `1px solid ${t.color}30` }}>
              <span className="text-xl font-bold" style={{ color: t.color }}>{t.tier}</span>
            </div>
            <div>
              <div className="text-2xl font-bold text-[var(--text-1)]">{t.count}</div>
              <div className="text-[10px] text-[var(--text-3)] uppercase tracking-wider font-mono">{t.tier} — {Math.round((t.count / total) * 100)}%</div>
              <div className="text-[9px] text-[var(--text-3)] mt-0.5">{t.desc}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Tier Breakdown Bar Chart */}
      <div className="stat-card mb-8">
        <h4 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-4 flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-[var(--accent-sage)]" strokeWidth={1.5} />
          Tier Distribution
        </h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={tierData} layout="vertical" margin={{ left: 60, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis type="number" tick={{ fontSize: 10, fill: "var(--text-3)" }} />
            <YAxis type="category" dataKey="tier" width={60} tick={{ fontSize: 11, fill: "var(--text-2)", fontWeight: 600 }} />
            <Tooltip
              contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12, color: "var(--text-1)" }}
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              formatter={(val: any) => val !== undefined ? [`${val} notes`, "Count"] : ["", "Count"]}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]}>
              {tierData.map((entry) => (
                <Cell key={entry.tier} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Consolidation & Index Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <div className="stat-card">
          <h4 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-4 flex items-center gap-2">
            <GitBranch className="w-3.5 h-3.5 text-[var(--accent-gold)]" strokeWidth={1.5} />
            Consolidation Activity
          </h4>
          <div className="space-y-2.5 text-sm">
            <Row label="Events This Period" value={String(consolidation.events_this_period)} />
            <Row label="Avg Cluster Size" value={String(consolidation.avg_cluster_size)} />
            <Row label="Max Recursion Depth" value={`${consolidation.max_depth} / ${config.max_depth || 3}`} />
            <Row label="Min Cluster Size" value={String(config.min_cluster)} />
            <Row label="Cluster Sim Threshold" value={String(config.cluster_sim_threshold)} />
            <Row label="Trigger Every N Runs" value={String(config.every_n_runs)} />
          </div>
        </div>

        <div className="stat-card">
          <h4 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-4 flex items-center gap-2">
            <Archive className="w-3.5 h-3.5 text-[var(--brand-primary)]" strokeWidth={1.5} />
            Embedding Index Scaling
          </h4>
          <div className="space-y-2.5 text-sm">
            <Row label="Main Index (HOT+WARM)" value={String(index.main_vectors)} />
            <Row label="Cold Index (lazy)" value={String(index.cold_vectors)} />
            <Row label="Total Vectors" value={String(index.total_vectors)} />
            <Row label="Cold % of Total" value={`${total > 0 ? Math.round((index.cold_vectors / index.total_vectors) * 100) : 0}%`} />
          </div>
        </div>
      </div>

      {/* Decay Policy */}
      <div className="stat-card border border-[var(--accent-ember)]/20 bg-[var(--accent-ember)]/3">
        <h4 className="text-xs font-semibold text-[var(--text-2)] uppercase tracking-wider mb-4 flex items-center gap-2">
          <Timer className="w-3.5 h-3.5 text-[var(--accent-ember)]" strokeWidth={1.5} />
          Decay Policy (Forgetting ≠ Deleting)
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2 p-2 rounded-lg bg-[var(--card)] border border-[var(--border)]">
            <TrendingUp className="w-3.5 h-3.5 text-[var(--accent-ember)]" strokeWidth={1.5} />
            <div>
              <div className="font-medium text-[var(--text-1)]">Demotion</div>
              <div className="text-[10px] text-[var(--text-3)]">{`Idle >${config.cold_idle_days}d & conf <${config.cold_confidence} → COLD`}</div>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-lg bg-[var(--card)] border border-[var(--border)]">
            <TrendingUp className="w-3.5 h-3.5 text-[var(--accent-sage)]" strokeWidth={1.5} />
            <div>
              <div className="font-medium text-[var(--text-1)]">Promotion</div>
              <div className="text-[10px] text-[var(--text-3)]">Any retrieval or new link → WARM</div>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-lg bg-[var(--card)] border border-[var(--border)]">
            <Layers className="w-3.5 h-3.5 text-[var(--brand-primary)]" strokeWidth={1.5} />
            <div>
              <div className="font-medium text-[var(--text-1)]">Status Independence</div>
              <div className="text-[10px] text-[var(--text-3)]">tier ⊥ status — verified claims can go COLD</div>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-lg bg-[var(--card)] border border-[var(--border)]">
            <GitBranch className="w-3.5 h-3.5 text-[var(--accent-gold)]" strokeWidth={1.5} />
            <div>
              <div className="font-medium text-[var(--text-1)]">Recursion Cap</div>
              <div className="text-[10px] text-[var(--text-3)]">Max depth {config.max_depth || 3} — grounded in originals</div>
            </div>
          </div>
        </div>
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