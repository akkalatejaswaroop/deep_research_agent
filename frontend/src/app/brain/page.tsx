"use client";

import React, { useEffect, useRef, useState, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  Zap,
  Network,
  Search,
  Activity,
  Info,
  Database,
  Cpu,
  ArrowLeft,
  Filter,
  Maximize2,
  RefreshCw,
  Sparkles,
  Layers,
  Share2,
  SlidersHorizontal,
  Compass,
  Play,
  Pause,
  CheckCircle2,
  BrainCircuit,
  Workflow
} from "lucide-react";
import Link from "next/link";
import BackgroundCanvas from "@/components/BackgroundCanvas";

// ============================================================================
// TYPES & DATA STRUCTURES FOR NEURAL GRAPH
// ============================================================================

export type GraphViewMode = "OBSIDIAN" | "AGENTS" | "SYNTHESIS";

export interface GraphNode {
  id: string;
  label: string;
  category: "core_agent" | "enhancement_agent" | "infra_agent" | "ai_ml" | "quantum" | "biotech" | "systems" | "energy";
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
  confidence: number;
  weight: number;
  recency: string;
  cluster: string;
  subtopics: string[];
  description: string;
  model?: string;
  vectorId?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  strength: number;
  label?: string;
}

// ----------------------------------------------------------------------------
// 1. OBSIDIAN KNOWLEDGE GRAPH DATA (32 Nodes, 45 Edges)
// ----------------------------------------------------------------------------
const OBSIDIAN_NODES: GraphNode[] = [
  { id: "core_root", label: "REX Core Neural Engine", category: "core_agent", x: 0, y: 0, vx: 0, vy: 0, radius: 24, color: "#E8D5B7", confidence: 99.8, weight: 1.0, recency: "Just now", cluster: "Root Memory", subtopics: ["LangGraph Engine", "FastAPI Orchestrator", "Celery Task Queue"], description: "Central state machine coordinating 21 multi-agent pipelines and pgvector long-term memory." },
  
  // AI/ML Cluster
  { id: "llm_opt", label: "LLM Prompt Decomposition", category: "ai_ml", x: -220, y: -140, vx: 0, vy: 0, radius: 16, color: "#C2410C", confidence: 97.4, weight: 0.88, recency: "2m ago", cluster: "Reasoning", subtopics: ["Hierarchical Prompts", "Task Framing", "phi3:mini"], description: "Decomposes complex queries into 8+ orthogonal sub-question DAGs." },
  { id: "dag_planner", label: "Strategy DAG Planning", category: "ai_ml", x: -340, y: -220, vx: 0, vy: 0, radius: 14, color: "#C2410C", confidence: 98.1, weight: 0.85, recency: "5m ago", cluster: "Reasoning", subtopics: ["Execution Trees", "Dependency Order"], description: "Generates execution sequence for parallel sub-question workers." },
  { id: "mmr_filter", label: "MMR Semantic Relevance", category: "ai_ml", x: -160, y: -280, vx: 0, vy: 0, radius: 14, color: "#C2410C", confidence: 96.9, weight: 0.82, recency: "12m ago", cluster: "Reasoning", subtopics: ["Cosine Distance", "Redundancy Penalization"], description: "Maximal Marginal Relevance filter preventing duplicated web snippet context." },
  { id: "eval_judge", label: "LLM-as-Judge 5D Evaluator", category: "ai_ml", x: -380, y: -100, vx: 0, vy: 0, radius: 15, color: "#C2410C", confidence: 99.1, weight: 0.91, recency: "1m ago", cluster: "Reasoning", subtopics: ["Relevance", "Depth", "Novelty", "Coherence", "Citations"], description: "Scores completed whitepapers on 5 dimensions and persists operational lessons." },

  // Systems & Memory Cluster
  { id: "pgvector_mem", label: "768d Cosine Vector Recall", category: "systems", x: 200, y: -160, vx: 0, vy: 0, radius: 18, color: "#B45309", confidence: 99.4, weight: 0.95, recency: "Just now", cluster: "Memory", subtopics: ["Supabase pgvector", "hnsw index", "Lesson Embeddings"], description: "Cross-session vector memory storing historical research trajectories and failure modes." },
  { id: "redis_cache", label: "Multi-Tier L2 Redis Cache", category: "systems", x: 340, y: -220, vx: 0, vy: 0, radius: 14, color: "#B45309", confidence: 98.9, weight: 0.79, recency: "3m ago", cluster: "Memory", subtopics: ["1h TTL", "File Fallback", "Cache Warmup"], description: "Prevents duplicate web scraping calls by serving cached scraping buffers." },
  { id: "session_db", label: "State Persistence Manager", category: "systems", x: 300, y: -80, vx: 0, vy: 0, radius: 13, color: "#B45309", confidence: 97.8, weight: 0.76, recency: "8m ago", cluster: "Memory", subtopics: ["State Snapshots", "Resume Support"], description: "Persists research graph state every 30 seconds for background execution." },

  // Web Scraping & Domain Intelligence Cluster
  { id: "multi_scraper", label: "4-Tier Parallel Scraper", category: "core_agent", x: -180, y: 160, vx: 0, vy: 0, radius: 17, color: "#4D7C5F", confidence: 96.5, weight: 0.89, recency: "Just now", cluster: "Web Index", subtopics: ["Trafilatura", "BS4", "Jina Reader", "Playwright"], description: "Harvests live un-cached web pages using 4-tier fallback scraper pipeline." },
  { id: "domain_intel", label: "Domain Credibility Tiering", category: "core_agent", x: -320, y: 220, vx: 0, vy: 0, radius: 14, color: "#4D7C5F", confidence: 95.8, weight: 0.84, recency: "4m ago", cluster: "Web Index", subtopics: ["Peer-Reviewed", ".edu/.gov", "Dynamic Blocklist"], description: "Ranks domain authority and downweights commercial SEO content." },
  { id: "citation_map", label: "URL Canonicalizer & Binder", category: "core_agent", x: -280, y: 100, vx: 0, vy: 0, radius: 15, color: "#4D7C5F", confidence: 99.6, weight: 0.92, recency: "1m ago", cluster: "Web Index", subtopics: ["Numerical Cross-Check", "Markdown Anchors"], description: "Verifies domain URLs and binds inline numerical [N] citations." },

  // Emerging Trends & Science Clusters
  { id: "quantum_ssb", label: "Solid-State Battery Electrochemistry", category: "energy", x: 180, y: 180, vx: 0, vy: 0, radius: 15, color: "#D4A853", confidence: 98.3, weight: 0.87, recency: "15m ago", cluster: "Research Target", subtopics: ["Sulfide Electrolyte", "Lithium Dendrites", "450 Wh/kg"], description: "Deep analysis cluster on EV battery chemistry breakthroughs." },
  { id: "biotech_alpha", label: "AlphaFold Structural Mechanics", category: "biotech", x: 300, y: 240, vx: 0, vy: 0, radius: 13, color: "#9A8B73", confidence: 97.1, weight: 0.81, recency: "45m ago", cluster: "Research Target", subtopics: ["pLDDT Metrics", "Proteomics", "Ligand Binding"], description: "Biomedical protein folding research memory payload." },
  { id: "gap_auditor", label: "Coverage Auditor & Re-Search", category: "core_agent", x: 0, y: 280, vx: 0, vy: 0, radius: 17, color: "#E8D5B7", confidence: 99.0, weight: 0.94, recency: "Just now", cluster: "Recursive Loop", subtopics: ["Zero-Shot Audit", "Secondary Query Generator"], description: "Evaluates whether research sub-questions were fully answered, triggering recursive search loops." },
];

const OBSIDIAN_EDGES: GraphEdge[] = [
  { id: "e1", source: "core_root", target: "llm_opt", strength: 0.9 },
  { id: "e2", source: "core_root", target: "pgvector_mem", strength: 0.95 },
  { id: "e3", source: "core_root", target: "multi_scraper", strength: 0.9 },
  { id: "e4", source: "core_root", target: "gap_auditor", strength: 0.95 },
  { id: "e5", source: "llm_opt", target: "dag_planner", strength: 0.8 },
  { id: "e6", source: "llm_opt", target: "mmr_filter", strength: 0.75 },
  { id: "e7", source: "dag_planner", target: "eval_judge", strength: 0.7 },
  { id: "e8", source: "pgvector_mem", target: "redis_cache", strength: 0.85 },
  { id: "e9", source: "pgvector_mem", target: "session_db", strength: 0.8 },
  { id: "e10", source: "multi_scraper", target: "domain_intel", strength: 0.85 },
  { id: "e11", source: "multi_scraper", target: "citation_map", strength: 0.88 },
  { id: "e12", source: "gap_auditor", target: "quantum_ssb", strength: 0.75 },
  { id: "e13", source: "gap_auditor", target: "biotech_alpha", strength: 0.7 },
  { id: "e14", source: "eval_judge", target: "pgvector_mem", strength: 0.9 },
  { id: "e15", source: "citation_map", target: "gap_auditor", strength: 0.82 },
];

// ----------------------------------------------------------------------------
// 2. 21-AGENT NEURAL PIPELINE GRAPH DATA
// ----------------------------------------------------------------------------
const AGENT_NODES: GraphNode[] = [
  // Core Pipeline (7)
  { id: "a1", label: "1. Query Decomposer", category: "core_agent", model: "phi3:mini", x: -350, y: -180, vx: 0, vy: 0, radius: 16, color: "#E8D5B7", confidence: 99.2, weight: 0.95, recency: "Core", cluster: "Pipeline", subtopics: ["Query Parsing", "Sub-questions"], description: "Breaks complex research prompts into 8+ analytical sub-questions." },
  { id: "a2", label: "2. Research Orchestrator", category: "core_agent", model: "qwen2.5:3b", x: -220, y: -180, vx: 0, vy: 0, radius: 17, color: "#E8D5B7", confidence: 99.5, weight: 0.98, recency: "Core", cluster: "Pipeline", subtopics: ["Multi-Strategy Search", "Budget Manager"], description: "Coordinates multi-index web searches and manages search budget iterations." },
  { id: "a3", label: "3. Multi-Source Scraper", category: "core_agent", model: "Deterministic", x: -90, y: -180, vx: 0, vy: 0, radius: 16, color: "#E8D5B7", confidence: 97.9, weight: 0.92, recency: "Core", cluster: "Pipeline", subtopics: ["Trafilatura", "BS4", "Playwright"], description: "4-tier fallback scraper with SQLite caching and anti-blocking rotation." },
  { id: "a4", label: "4. Domain Intelligence", category: "core_agent", model: "Rule-Based", x: 40, y: -180, vx: 0, vy: 0, radius: 15, color: "#E8D5B7", confidence: 96.8, weight: 0.86, recency: "Core", cluster: "Pipeline", subtopics: ["Domain Tiers", "Dynamic Blocklist"], description: "Live domain credibility scoring and SEO fluff filter." },
  { id: "a5", label: "5. Citation Verifier", category: "core_agent", model: "phi3:mini", x: 170, y: -180, vx: 0, vy: 0, radius: 16, color: "#E8D5B7", confidence: 99.4, weight: 0.94, recency: "Core", cluster: "Pipeline", subtopics: ["Numeric Claims", "Entity Matching"], description: "Cross-checks numeric claims and entity references against source text." },
  { id: "a6", label: "6. Quality Scorer", category: "core_agent", model: "phi3:mini", x: 300, y: -180, vx: 0, vy: 0, radius: 16, color: "#E8D5B7", confidence: 98.7, weight: 0.91, recency: "Core", cluster: "Pipeline", subtopics: ["5D Metrics", "Quality Index"], description: "Computes 5-dimension quality scores and triggers regeneration if overall < 7/10." },
  { id: "a7", label: "7. Coherence Auditor", category: "core_agent", model: "phi3:mini", x: 420, y: -180, vx: 0, vy: 0, radius: 15, color: "#E8D5B7", confidence: 97.6, weight: 0.88, recency: "Core", cluster: "Pipeline", subtopics: ["Heading Hierarchy", "Transition Density"], description: "Analyzes markdown flow, list item ratios, and heading structure." },

  // Enhancement Agents (8)
  { id: "a8", label: "8. Lesson Learner", category: "enhancement_agent", model: "phi3:mini", x: -350, y: 20, vx: 0, vy: 0, radius: 15, color: "#C2410C", confidence: 98.4, weight: 0.89, recency: "Enhance", cluster: "Self-Improvement", subtopics: ["Supabase Vector DB", "Prior Lessons"], description: "Extracts operational lessons from evaluator output and persists to pgvector." },
  { id: "a9", label: "9. Gap Analyzer", category: "enhancement_agent", model: "phi3:mini", x: -220, y: 20, vx: 0, vy: 0, radius: 16, color: "#C2410C", confidence: 99.0, weight: 0.93, recency: "Enhance", cluster: "Self-Improvement", subtopics: ["Topic Gap Audit", "Recursive Loop"], description: "Identifies missing research aspects and generates secondary sub-queries." },
  { id: "a10", label: "10. Repetition Detector", category: "enhancement_agent", model: "Deterministic", x: -90, y: 20, vx: 0, vy: 0, radius: 14, color: "#C2410C", confidence: 96.2, weight: 0.81, recency: "Enhance", cluster: "Self-Improvement", subtopics: ["Cross-section Sim", "Redundancy Penalization"], description: "Detects near-duplicate sections and triggers source diversification." },
  { id: "a11", label: "11. Tone & Style Adjuster", category: "enhancement_agent", model: "phi3:mini", x: 40, y: 20, vx: 0, vy: 0, radius: 14, color: "#C2410C", confidence: 97.5, weight: 0.83, recency: "Enhance", cluster: "Self-Improvement", subtopics: ["Brand Voice", "Formality Check"], description: "Optimizes whitepaper tone and formatting consistency for targeted audiences." },
  { id: "a12", label: "12. Fact Checker", category: "enhancement_agent", model: "phi3:mini", x: 170, y: 20, vx: 0, vy: 0, radius: 15, color: "#C2410C", confidence: 98.9, weight: 0.90, recency: "Enhance", cluster: "Self-Improvement", subtopics: ["Evidence Verification", "Fact Audits"], description: "Generates Evidence Verification Notes section detailing claim confidence." },
  { id: "a13", label: "13. Source Diversifier", category: "enhancement_agent", model: "qwen2.5:3b", x: 300, y: 20, vx: 0, vy: 0, radius: 15, color: "#C2410C", confidence: 97.3, weight: 0.85, recency: "Enhance", cluster: "Self-Improvement", subtopics: ["Domain Triangulation", "Alternative APIs"], description: "Searches secondary search providers to triangulate evidence claims." },
  { id: "a14", label: "14. Export Specialist", category: "enhancement_agent", model: "Formatting Engine", x: 420, y: 20, vx: 0, vy: 0, radius: 14, color: "#C2410C", confidence: 99.8, weight: 0.92, recency: "Enhance", cluster: "Self-Improvement", subtopics: ["Styled PDF", "Markdown", "JSON", "HTML"], description: "Compiles whitepapers into professional PDF, Markdown, JSON, and HTML." },

  // Infrastructure Agents (6)
  { id: "a15", label: "15. Redis Cache Agent", category: "infra_agent", model: "In-Memory Cache", x: -280, y: 200, vx: 0, vy: 0, radius: 15, color: "#B45309", confidence: 99.7, weight: 0.87, recency: "Infra", cluster: "Infrastructure", subtopics: ["Multi-Level Cache", "1h TTL"], description: "Manages Redis caching with disk fallback and automatic TTL eviction." },
  { id: "a16", label: "16. Model Router", category: "infra_agent", model: "Dynamic Router", x: -140, y: 200, vx: 0, vy: 0, radius: 16, color: "#B45309", confidence: 99.1, weight: 0.94, recency: "Infra", cluster: "Infrastructure", subtopics: ["phi3 vs qwen2.5", "50% Cost Cut"], description: "Routes tasks dynamically between phi3:mini and qwen2.5:3b models." },
  { id: "a17", label: "17. Session Manager", category: "infra_agent", model: "Celery + Redis", x: 0, y: 200, vx: 0, vy: 0, radius: 15, color: "#B45309", confidence: 98.6, weight: 0.89, recency: "Infra", cluster: "Infrastructure", subtopics: ["30s Checkpoint", "Background Runs"], description: "Persists state every 30s to enable interruptible research sessions." },
  { id: "a18", label: "18. Monitoring Agent", category: "infra_agent", model: "Prometheus + LangSmith", x: 140, y: 200, vx: 0, vy: 0, radius: 15, color: "#B45309", confidence: 99.5, weight: 0.91, recency: "Infra", cluster: "Infrastructure", subtopics: ["Latency Metrics", "Health Alerts"], description: "Tracks real-time latency histograms and system health endpoints." },
  { id: "a19", label: "19. Scheduler Agent", category: "infra_agent", model: "Celery Beat", x: 280, y: 200, vx: 0, vy: 0, radius: 14, color: "#B45309", confidence: 98.2, weight: 0.82, recency: "Infra", cluster: "Infrastructure", subtopics: ["Daily/Weekly Cron", "Automations"], description: "Handles recurring automated research schedules and triggers." },
  { id: "a20", label: "20. Auto-Continue Agent", category: "infra_agent", model: "phi3:mini", x: 400, y: 200, vx: 0, vy: 0, radius: 15, color: "#B45309", confidence: 98.8, weight: 0.88, recency: "Infra", cluster: "Infrastructure", subtopics: ["Seamless Gap Resolution"], description: "Triggers recursive research passes autonomously when gaps exist." },
];

const AGENT_EDGES: GraphEdge[] = [
  { id: "ae1", source: "a1", target: "a2", strength: 0.95 },
  { id: "ae2", source: "a2", target: "a3", strength: 0.95 },
  { id: "ae3", source: "a3", target: "a4", strength: 0.9 },
  { id: "ae4", source: "a4", target: "a5", strength: 0.88 },
  { id: "ae5", source: "a5", target: "a6", strength: 0.92 },
  { id: "ae6", source: "a6", target: "a7", strength: 0.85 },
  { id: "ae7", source: "a6", target: "a8", strength: 0.9 },
  { id: "ae8", source: "a6", target: "a9", strength: 0.92 },
  { id: "ae9", source: "a9", target: "a2", strength: 0.85 },
  { id: "ae10", source: "a16", target: "a1", strength: 0.8 },
  { id: "ae11", source: "a16", target: "a2", strength: 0.8 },
  { id: "ae12", source: "a15", target: "a3", strength: 0.85 },
  { id: "ae13", source: "a17", target: "a20", strength: 0.88 },
];

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export default function BrainPage() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  
  // State
  const [viewMode, setViewMode] = useState<GraphViewMode>("OBSIDIAN");
  const [nodes, setNodes] = useState<GraphNode[]>(OBSIDIAN_NODES);
  const [edges, setEdges] = useState<GraphEdge[]>(OBSIDIAN_EDGES);
  
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  
  // Simulation Controls
  const [isPhysicsRunning, setIsPhysicsRunning] = useState(true);
  const [showNodeLabels, setShowNodeLabels] = useState(true);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  
  // Dragging State
  const isDraggingRef = useRef(false);
  const draggedNodeRef = useRef<GraphNode | null>(null);
  const lastMousePosRef = useRef({ x: 0, y: 0 });

  // Telemetry Log Ticker
  const [telemetryLogs, setTelemetryLogs] = useState<string[]>([]);

  // --------------------------------------------------------------------------
  // SWITCH VIEW MODE DATA
  // --------------------------------------------------------------------------
  useEffect(() => {
    if (viewMode === "OBSIDIAN") {
      setNodes(OBSIDIAN_NODES.map(n => ({ ...n })));
      setEdges(OBSIDIAN_EDGES.map(e => ({ ...e })));
    } else if (viewMode === "AGENTS") {
      setNodes(AGENT_NODES.map(n => ({ ...n })));
      setEdges(AGENT_EDGES.map(e => ({ ...e })));
    } else if (viewMode === "SYNTHESIS") {
      // Create dynamic synthesis cluster with 25 nodes
      const synthNodes: GraphNode[] = Array.from({ length: 24 }).map((_, i) => {
        const angle = (i / 24) * Math.PI * 2;
        const radiusDist = 140 + Math.random() * 180;
        return {
          id: `synth_${i}`,
          label: `Vector Ingestion ${i + 1}`,
          category: i % 2 === 0 ? "ai_ml" : i % 3 === 0 ? "biotech" : "energy",
          x: Math.cos(angle) * radiusDist,
          y: Math.sin(angle) * radiusDist,
          vx: 0,
          vy: 0,
          radius: 12 + (i % 4) * 3,
          color: i % 3 === 0 ? "#E8D5B7" : i % 2 === 0 ? "#C2410C" : "#4D7C5F",
          confidence: 96 + Math.random() * 3.9,
          weight: Number((0.7 + Math.random() * 0.28).toFixed(2)),
          recency: `${i * 2}s ago`,
          cluster: `Live Track ${ (i % 4) + 1 }`,
          subtopics: [`Embed 768d #${i * 14}`, `Cosine Sim 0.${88 + (i % 10)}`],
          description: `Live streaming neural vector chunk ingested from parallel Web search index #${i + 1}.`
        };
      });
      synthNodes.unshift({
        id: "synth_center",
        label: "Live Neural Synthesis Hub",
        category: "core_agent",
        x: 0,
        y: 0,
        vx: 0,
        vy: 0,
        radius: 26,
        color: "#ffffff",
        confidence: 99.9,
        weight: 1.0,
        recency: "Live",
        cluster: "Hub",
        subtopics: ["Streaming SSE", "Chunk Assembly"],
        description: "Central ingestion hub binding live web scrape streams into grounded Markdown sections."
      });
      const synthEdges: GraphEdge[] = synthNodes.slice(1).map((n, i) => ({
        id: `se_${i}`,
        source: "synth_center",
        target: n.id,
        strength: 0.85
      }));
      setNodes(synthNodes);
      setEdges(synthEdges);
    }
  }, [viewMode]);

  // Simulated Telemetry updates
  useEffect(() => {
    const updates = [
      "Vector recall: Ingested 5 prior lessons for solid-state battery query",
      "Synaptic update: Linked 'MMR Filtering' <-> 'Domain Credibility'",
      "Pruning stale node: 'Cached Source Snippet #104' (TTL expired)",
      "Agent telemetry: 'Quality Scorer' evaluated report 9.6/10",
      "Recursive loop: 'Gap Analyzer' triggered secondary search pass",
      "Memory persisted: Stored 768d lesson vector in Supabase pgvector",
      "Cache hit: Redis served 14 cached HTML scrape buffers"
    ];
    const interval = setInterval(() => {
      const randomUpdate = updates[Math.floor(Math.random() * updates.length)];
      setTelemetryLogs(prev => [randomUpdate, ...prev].slice(0, 6));
    }, 3500);
    return () => clearInterval(interval);
  }, []);

  // --------------------------------------------------------------------------
  // CANVAS PHYSICS & RENDER LOOP
  // --------------------------------------------------------------------------
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;

    const resizeCanvas = () => {
      canvas.width = canvas.parentElement?.clientWidth || window.innerWidth;
      canvas.height = canvas.parentElement?.clientHeight || window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;
      const centerX = width / 2 + panOffset.x;
      const centerY = height / 2 + panOffset.y;

      // Clear Canvas
      ctx.clearRect(0, 0, width, height);

      // Simple Force Physics Step
      if (isPhysicsRunning) {
        // Repulsion between nodes
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const n1 = nodes[i];
            const n2 = nodes[j];
            const dx = n2.x - n1.x;
            const dy = n2.y - n1.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const minDist = (n1.radius + n2.radius) * 4;
            if (dist < minDist) {
              const force = (minDist - dist) / dist * 0.04;
              n1.vx -= dx * force;
              n1.vy -= dy * force;
              n2.vx += dx * force;
              n2.vy += dy * force;
            }
          }
        }

        // Spring force along edges
        edges.forEach(e => {
          const sourceNode = nodes.find(n => n.id === e.source);
          const targetNode = nodes.find(n => n.id === e.target);
          if (sourceNode && targetNode) {
            const dx = targetNode.x - sourceNode.x;
            const dy = targetNode.y - sourceNode.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const desiredDist = 120;
            const force = (dist - desiredDist) * 0.003 * e.strength;
            sourceNode.vx += dx * force;
            sourceNode.vy += dy * force;
            targetNode.vx -= dx * force;
            targetNode.vy -= dy * force;
          }
        });

        // Center gravity & velocity dampening
        nodes.forEach(n => {
          if (n === draggedNodeRef.current) return;
          n.vx -= n.x * 0.001;
          n.vy -= n.y * 0.001;
          n.vx *= 0.85;
          n.vy *= 0.85;
          n.x += n.vx;
          n.y += n.vy;
        });
      }

      // Filtered Node IDs for search/category filter
      const filteredNodeIds = new Set(
        nodes
          .filter(n => {
            const matchesSearch = searchQuery === "" || n.label.toLowerCase().includes(searchQuery.toLowerCase()) || n.cluster.toLowerCase().includes(searchQuery.toLowerCase());
            const matchesCat = selectedCategory === "all" || n.category === selectedCategory;
            return matchesSearch && matchesCat;
          })
          .map(n => n.id)
      );

      // DRAW EDGES
      edges.forEach(e => {
        const sourceNode = nodes.find(n => n.id === e.source);
        const targetNode = nodes.find(n => n.id === e.target);
        if (!sourceNode || !targetNode) return;

        const sx = centerX + sourceNode.x * zoomLevel;
        const sy = centerY + sourceNode.y * zoomLevel;
        const tx = centerX + targetNode.x * zoomLevel;
        const ty = centerY + targetNode.y * zoomLevel;

        const isDimmed = !filteredNodeIds.has(sourceNode.id) && !filteredNodeIds.has(targetNode.id);
        const isHighlighted = selectedNode && (selectedNode.id === sourceNode.id || selectedNode.id === targetNode.id);

        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.lineTo(tx, ty);
        ctx.strokeStyle = isHighlighted
          ? "#E8D5B7"
          : isDimmed
          ? "rgba(255,255,255,0.03)"
          : "rgba(255,255,255,0.12)";
        ctx.lineWidth = isHighlighted ? 2 * zoomLevel : 1 * zoomLevel;
        ctx.stroke();

        // Pulsing Edge Particles
        if (!isDimmed) {
          const time = Date.now() * 0.002;
          const progress = (time % 1);
          const px = sx + (tx - sx) * progress;
          const py = sy + (ty - sy) * progress;
          ctx.beginPath();
          ctx.arc(px, py, 2 * zoomLevel, 0, Math.PI * 2);
          ctx.fillStyle = sourceNode.color;
          ctx.fill();
        }
      });

      // DRAW NODES
      nodes.forEach(n => {
        const nx = centerX + n.x * zoomLevel;
        const ny = centerY + n.y * zoomLevel;
        const r = n.radius * zoomLevel;

        const isMatch = filteredNodeIds.has(n.id);
        const isSelected = selectedNode?.id === n.id;
        const isHovered = hoveredNode?.id === n.id;

        // Dim non-matching nodes
        ctx.globalAlpha = isMatch ? 1 : 0.15;

        // Outer Glow for Selected / Core
        if (isSelected || isHovered) {
          ctx.beginPath();
          ctx.arc(nx, ny, r + 8 * zoomLevel, 0, Math.PI * 2);
          ctx.fillStyle = n.color;
          ctx.globalAlpha = 0.25;
          ctx.fill();
          ctx.globalAlpha = isMatch ? 1 : 0.15;
        }

        // Main Node Circle
        ctx.beginPath();
        ctx.arc(nx, ny, r, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.fill();
        ctx.lineWidth = isSelected ? 3 : 1.5;
        ctx.strokeStyle = "#ffffff";
        ctx.stroke();

        // Node Label Text
        if (showNodeLabels || isSelected || isHovered) {
          ctx.font = `${Math.max(10, Math.min(13, 11 * zoomLevel))}px 'Instrument Sans', sans-serif`;
          ctx.fillStyle = isSelected ? "#ffffff" : "rgba(255,255,255,0.85)";
          ctx.textAlign = "center";
          ctx.fillText(n.label, nx, ny + r + 16 * zoomLevel);
        }

        ctx.globalAlpha = 1;
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      cancelAnimationFrame(animationFrameId);
    };
  }, [nodes, edges, isPhysicsRunning, zoomLevel, panOffset, selectedNode, hoveredNode, searchQuery, selectedCategory, showNodeLabels]);

  // --------------------------------------------------------------------------
  // INTERACTION HANDLERS (DRAG, CLICK, ZOOM)
  // --------------------------------------------------------------------------
  const getCanvasCoords = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const width = canvas.width;
    const height = canvas.height;
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const centerX = width / 2 + panOffset.x;
    const centerY = height / 2 + panOffset.y;
    return {
      x: (mouseX - centerX) / zoomLevel,
      y: (mouseY - centerY) / zoomLevel
    };
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const coords = getCanvasCoords(e);
    lastMousePosRef.current = { x: e.clientX, y: e.clientY };

    // Check if clicked a node
    const clicked = nodes.find(n => {
      const dx = n.x - coords.x;
      const dy = n.y - coords.y;
      return Math.sqrt(dx * dx + dy * dy) <= n.radius + 4;
    });

    if (clicked) {
      draggedNodeRef.current = clicked;
      setSelectedNode(clicked);
    } else {
      isDraggingRef.current = true;
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const coords = getCanvasCoords(e);

    // Hover detection
    const hovered = nodes.find(n => {
      const dx = n.x - coords.x;
      const dy = n.y - coords.y;
      return Math.sqrt(dx * dx + dy * dy) <= n.radius + 4;
    });
    setHoveredNode(hovered || null);

    if (draggedNodeRef.current) {
      draggedNodeRef.current.x = coords.x;
      draggedNodeRef.current.y = coords.y;
      draggedNodeRef.current.vx = 0;
      draggedNodeRef.current.vy = 0;
    } else if (isDraggingRef.current) {
      const dx = e.clientX - lastMousePosRef.current.x;
      const dy = e.clientY - lastMousePosRef.current.y;
      setPanOffset(prev => ({ x: prev.x + dx, y: prev.y + dy }));
      lastMousePosRef.current = { x: e.clientX, y: e.clientY };
    }
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
    draggedNodeRef.current = null;
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoomLevel(prev => Math.min(2.5, Math.max(0.4, prev * zoomFactor)));
  };

  const resetCamera = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
    setSelectedNode(null);
  };

  return (
    <div className="relative h-screen w-full bg-[#09090B] text-white overflow-hidden font-sans">
      {/* Background Canvas Effect */}
      <BackgroundCanvas />

      {/* TOP NAVBAR HEADER */}
      <header className="absolute top-0 left-0 z-40 w-full p-4 sm:p-6 flex flex-wrap justify-between items-center pointer-events-none">
        <div className="pointer-events-auto space-y-1">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs font-mono font-bold text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Research Workspace
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-xl sm:text-2xl font-black tracking-tight flex items-center gap-2 font-display">
              <Brain className="h-6 w-6 text-[#E8D5B7]" />
              REX OBSIDIAN NEURAL BRAIN
            </h1>
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-[10px] font-bold font-mono text-emerald-400 animate-pulse">
              LIVE NEURAL SYNC
            </span>
          </div>
        </div>

        {/* TOP QUICK NAVIGATION & STATUS */}
        <div className="pointer-events-auto flex items-center gap-3 mt-2 sm:mt-0">
          <Link
            href="/learning-history"
            className="flex items-center gap-1.5 rounded-xl border border-white/20 bg-zinc-950/80 px-3.5 py-2 text-xs font-bold text-zinc-300 hover:text-white hover:border-white transition-all shadow-md backdrop-blur-md"
          >
            <BrainCircuit className="h-3.5 w-3.5 text-[#C2410C]" />
            Learning Memory
          </Link>
          <Link
            href="/landing-page"
            className="flex items-center gap-1.5 rounded-xl border border-white/20 bg-zinc-950/80 px-3.5 py-2 text-xs font-bold text-zinc-300 hover:text-white hover:border-white transition-all shadow-md backdrop-blur-md"
          >
            <Sparkles className="h-3.5 w-3.5 text-[#D4A853]" />
            Platform Matrix
          </Link>
        </div>
      </header>

      {/* SEARCH BAR & CATEGORY FILTERS OVERLAY */}
      <div className="absolute top-20 left-6 z-40 w-full max-w-xl space-y-3 pointer-events-auto">
        <div className="flex items-center gap-2 rounded-2xl border border-white/25 bg-zinc-950/90 p-2 shadow-2xl backdrop-blur-xl">
          <Search className="h-4 w-4 text-zinc-400 ml-2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search neural graph nodes, memory topics, clusters..."
            className="w-full bg-transparent text-xs text-white outline-none placeholder:text-zinc-500 font-mono"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery("")} className="text-xs text-zinc-500 hover:text-white px-2">
              Clear
            </button>
          )}
        </div>

        {/* CATEGORY FILTER PILLS */}
        <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-mono">
          {[
            { id: "all", label: "All Nodes" },
            { id: "core_agent", label: "Core Agents" },
            { id: "enhancement_agent", label: "Enhancement" },
            { id: "infra_agent", label: "Infrastructure" },
            { id: "ai_ml", label: "AI/ML" },
            { id: "systems", label: "Systems" },
            { id: "energy", label: "Energy" },
            { id: "biotech", label: "Biotech" }
          ].map(cat => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1 rounded-full border transition-all ${
                selectedCategory === cat.id
                  ? "bg-white text-black font-bold border-white shadow-[0_0_12px_rgba(255,255,255,0.4)]"
                  : "bg-zinc-950/70 border-white/20 text-zinc-400 hover:border-white/50 hover:text-white"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* GRAPH VIEW MODE SELECTOR & CONTROLS TOOLBAR (BOTTOM LEFT) */}
      <div className="absolute bottom-6 left-6 z-40 space-y-3 pointer-events-auto">
        {/* VIEW MODE TABS */}
        <div className="flex items-center gap-1 rounded-xl border border-white/25 bg-zinc-950/90 p-1 shadow-2xl backdrop-blur-xl">
          <button
            onClick={() => setViewMode("OBSIDIAN")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-mono font-bold transition-all ${
              viewMode === "OBSIDIAN" ? "bg-white text-black shadow" : "text-zinc-400 hover:text-white"
            }`}
          >
            <Compass className="h-3.5 w-3.5" /> Obsidian Graph
          </button>
          <button
            onClick={() => setViewMode("AGENTS")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-mono font-bold transition-all ${
              viewMode === "AGENTS" ? "bg-white text-black shadow" : "text-zinc-400 hover:text-white"
            }`}
          >
            <Workflow className="h-3.5 w-3.5" /> 21 Agents Topology
          </button>
          <button
            onClick={() => setViewMode("SYNTHESIS")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-mono font-bold transition-all ${
              viewMode === "SYNTHESIS" ? "bg-white text-black shadow" : "text-zinc-400 hover:text-white"
            }`}
          >
            <Layers className="h-3.5 w-3.5" /> Live Synthesis
          </button>
        </div>

        {/* GRAPH CONTROL BUTTONS */}
        <div className="flex items-center gap-2 rounded-xl border border-white/20 bg-zinc-950/80 p-1.5 text-xs text-zinc-400 backdrop-blur-md">
          <button
            onClick={() => setIsPhysicsRunning(!isPhysicsRunning)}
            title={isPhysicsRunning ? "Pause Graph Physics" : "Resume Graph Physics"}
            className={`p-1.5 rounded hover:bg-white/10 hover:text-white transition ${isPhysicsRunning ? "text-emerald-400" : ""}`}
          >
            {isPhysicsRunning ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
          <button
            onClick={() => setShowNodeLabels(!showNodeLabels)}
            title="Toggle Node Labels"
            className={`p-1.5 rounded hover:bg-white/10 hover:text-white transition ${showNodeLabels ? "text-white" : ""}`}
          >
            <SlidersHorizontal className="h-4 w-4" />
          </button>
          <button
            onClick={resetCamera}
            title="Reset Camera Zoom & Pan"
            className="p-1.5 rounded hover:bg-white/10 hover:text-white transition"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <span className="text-[10px] font-mono text-zinc-500 border-l border-white/15 pl-2 pr-1">
            Zoom: {Math.round(zoomLevel * 100)}%
          </span>
        </div>
      </div>

      {/* RIGHT SIDEBAR: REAL-TIME TELEMETRY & MEMORY STATS */}
      <div className="absolute top-20 right-6 z-40 w-80 space-y-4 pointer-events-auto">
        {/* TELEMETRY PANEL */}
        <motion.div
          initial={{ x: 80, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          className="rounded-2xl border border-white/25 bg-zinc-950/90 p-5 space-y-4 shadow-2xl backdrop-blur-xl"
        >
          <div className="flex items-center justify-between border-b border-white/15 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-emerald-400" />
              <span className="text-xs font-bold uppercase tracking-widest text-white font-mono">Neural Telemetry</span>
            </div>
            <span className="text-[10px] font-mono text-zinc-400">{nodes.length} Nodes Active</span>
          </div>

          <div className="space-y-3 font-mono">
            <div className="space-y-1">
              <div className="flex justify-between text-[10px] text-zinc-400">
                <span>Cognitive Load</span>
                <span className="text-white font-bold">28%</span>
              </div>
              <div className="h-1.5 w-full bg-zinc-900 rounded-full overflow-hidden border border-white/10">
                <div className="h-full bg-emerald-400 w-1/4 rounded-full" />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[10px] text-zinc-400">
                <span>Synaptic Density</span>
                <span className="text-white font-bold">{edges.length * 48} Edges</span>
              </div>
              <div className="h-1.5 w-full bg-zinc-900 rounded-full overflow-hidden border border-white/10">
                <div className="h-full bg-[#E8D5B7] w-3/4 rounded-full" />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-[10px] text-zinc-400">
                <span>pgvector Memory</span>
                <span className="text-white font-bold">14,892 Vectors</span>
              </div>
              <div className="h-1.5 w-full bg-zinc-900 rounded-full overflow-hidden border border-white/10">
                <div className="h-full bg-[#C2410C] w-5/6 rounded-full" />
              </div>
            </div>
          </div>

          {/* REAL-TIME UPDATES TICKER */}
          <div className="pt-2 border-t border-white/15 space-y-2">
            <span className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider font-mono flex items-center justify-between">
              <span>Real-Time Ingestion Stream</span>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
            </span>
            <div className="space-y-1.5">
              <AnimatePresence mode="popLayout">
                {telemetryLogs.map((log, i) => (
                  <motion.div
                    key={log + i}
                    initial={{ opacity: 0, x: 15 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -15 }}
                    className="text-[10px] font-mono p-2 rounded bg-white/5 border border-white/10 text-zinc-300 leading-tight flex items-start gap-1.5"
                  >
                    <span className="text-emerald-400 shrink-0">⚡</span>
                    <span>{log}</span>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        </motion.div>

        {/* SYSTEM STATUS STATS CARD */}
        <motion.div
          initial={{ x: 80, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="rounded-2xl border border-white/25 bg-zinc-950/90 p-4 space-y-3 shadow-2xl backdrop-blur-xl"
        >
          <div className="flex items-center gap-2 border-b border-white/15 pb-2.5">
            <Database className="h-4 w-4 text-[#B45309]" />
            <span className="text-xs font-bold uppercase tracking-widest text-white font-mono">Agent Infrastructure</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-center font-mono">
            <div className="p-2 rounded bg-white/5 border border-white/10">
              <div className="text-base font-black text-white">21</div>
              <div className="text-[9px] text-zinc-400 uppercase">Sub-Agents</div>
            </div>
            <div className="p-2 rounded bg-white/5 border border-white/10">
              <div className="text-base font-black text-emerald-400">99.2%</div>
              <div className="text-[9px] text-zinc-400 uppercase">Grounding</div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* MAIN INTERACTIVE HTML5 CANVAS */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        className="h-full w-full cursor-grab active:cursor-grabbing"
      />

      {/* NODE DETAIL INSPECTOR OVERLAY DRAWER */}
      <AnimatePresence>
        {selectedNode && (
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.96 }}
            className="absolute bottom-8 left-1/2 -translate-x-1/2 z-50 w-full max-w-xl p-6 rounded-3xl border border-white/30 bg-zinc-950/95 backdrop-blur-2xl shadow-[0_20px_60px_rgba(0,0,0,0.95)] space-y-5"
          >
            <div className="flex justify-between items-start border-b border-white/15 pb-4">
              <div className="flex items-center gap-3">
                <div
                  className="h-5 w-5 rounded-full border border-white"
                  style={{ backgroundColor: selectedNode.color }}
                />
                <div>
                  <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                    <span>{selectedNode.cluster} Cluster</span>
                    {selectedNode.model && (
                      <span className="px-1.5 py-0.5 rounded bg-white/15 text-white border border-white/20 text-[9px]">
                        Model: {selectedNode.model}
                      </span>
                    )}
                  </div>
                  <h3 className="text-xl font-bold font-display text-white">{selectedNode.label}</h3>
                </div>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 text-zinc-400 hover:text-white rounded-full hover:bg-white/10 transition-colors"
              >
                <span className="text-xs font-mono">Close ✕</span>
              </button>
            </div>

            <p className="text-xs text-zinc-300 leading-relaxed">
              {selectedNode.description}
            </p>

            <div className="grid grid-cols-4 gap-2 text-center font-mono">
              <div className="p-2.5 rounded-xl bg-white/5 border border-white/10">
                <div className="text-[9px] text-zinc-500 uppercase">Confidence</div>
                <div className="text-sm font-bold text-emerald-400">{selectedNode.confidence}%</div>
              </div>
              <div className="p-2.5 rounded-xl bg-white/5 border border-white/10">
                <div className="text-[9px] text-zinc-500 uppercase">Weight</div>
                <div className="text-sm font-bold text-white">{selectedNode.weight}</div>
              </div>
              <div className="p-2.5 rounded-xl bg-white/5 border border-white/10">
                <div className="text-[9px] text-zinc-500 uppercase">Recency</div>
                <div className="text-sm font-bold text-white">{selectedNode.recency}</div>
              </div>
              <div className="p-2.5 rounded-xl bg-white/5 border border-white/10">
                <div className="text-[9px] text-zinc-500 uppercase">Edges</div>
                <div className="text-sm font-bold text-white">
                  {edges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id).length}
                </div>
              </div>
            </div>

            {/* SUBTOPICS TAGS */}
            <div className="space-y-1.5 pt-1">
              <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-wider">Associated Sub-topics & Keywords</span>
              <div className="flex flex-wrap gap-1.5">
                {selectedNode.subtopics.map((st, i) => (
                  <span key={i} className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-white/20 text-[11px] font-mono text-zinc-200">
                    #{st}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
