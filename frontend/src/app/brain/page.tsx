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
  Workflow,
  ExternalLink,
  GitCommit,
  GitBranch,
  X,
  Target,
  Clock,
  Check,
  AlertTriangle,
  RotateCcw,
  Sliders,
  ZoomIn,
  ZoomOut,
  Maximize
} from "lucide-react";
import Link from "next/link";
import BackgroundCanvas from "@/components/BackgroundCanvas";

export type GraphViewMode = "OBSIDIAN" | "AGENTS" | "SYNTHESIS";

export interface GraphNode {
  id: string;
  label: string;
  category: "core_agent" | "enhancement_agent" | "infra_agent" | "ai_ml" | "quantum" | "biotech" | "systems" | "energy";
  x: number;
  y: number;
  z?: number;
  vx: number;
  vy: number;
  vz?: number;
  screenX?: number;
  screenY?: number;
  screenScale?: number;
  screenZ?: number;
  isNew?: boolean;
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
  type?: string;
  status?: string;
  tier?: string;
  created?: string;
  updated?: string;
  version?: number;
  source_count?: number;
  agent?: string;
  path?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  strength: number;
  label?: string;
}

// ----------------------------------------------------------------------------
// INITIAL SEED NODES & EDGES (Prompt 14 Degree Sizing + Prompt 14 Tier Coloring)
// ----------------------------------------------------------------------------
const SEED_NODES: GraphNode[] = [
  {
    id: "SYS-01J8X000000000000000000001",
    label: "REX Core Neural Schema",
    type: "system",
    status: "verified",
    tier: "hot",
    confidence: 1.0,
    created: "2026-08-25",
    updated: "2026-08-29",
    category: "core_agent",
    x: 0, y: 0, z: 0, vx: 0, vy: 0, radius: 24,
    color: "#6366F1", // Tier 1: Core System
    weight: 1.0, recency: "Live Vault", cluster: "00_System",
    subtopics: ["Vault Law", "Optimistic Locking", "22 Rules"],
    description: "Central vault law and schema contract governing all 18 note types.",
    path: "00_System/REX-Knowledge-Schema.md"
  },
  {
    id: "CLM-01J8Y000000000000000000002",
    label: "Surface Code Braiding Fidelity > 99%",
    type: "claim",
    status: "verified",
    tier: "hot",
    confidence: 0.94,
    created: "2026-08-26",
    updated: "2026-08-29",
    category: "ai_ml",
    x: 180, y: -40, z: 20, vx: 0, vy: 0, radius: 20,
    color: "#EF4444", // Tier 2: High-Value Verified Claim
    weight: 0.92, recency: "2h ago", cluster: "02_Knowledge",
    subtopics: ["Majorana Zero Modes", "Topological Gap", "Anisotropy"],
    description: "Measured topological gap threshold for fault-tolerant surface code braiding.",
    path: "02_Knowledge/Claims/CLM-01J8Y000000000000000000002__braiding-fidelity.md"
  },
  {
    id: "FCT-01J8Y000000000000000000001",
    label: "Quantized ZBP in InAs-Al Nanowire",
    type: "fact",
    status: "verified",
    tier: "hot",
    confidence: 0.98,
    created: "2026-08-25",
    updated: "2026-08-28",
    category: "ai_ml",
    x: 210, y: 30, z: -30, vx: 0, vy: 0, radius: 18,
    color: "#EF4444", // Tier 2: Verified Fact
    weight: 0.95, recency: "1d ago", cluster: "02_Knowledge",
    subtopics: ["Zero-Bias Conductance", "2e^2/h", "Tunneling"],
    description: "Empirically verified conductance peak quantized at 2e^2/h at 25mK.",
    path: "02_Knowledge/Facts/FCT-01J8Y000000000000000000001__quantized-zbp.md"
  },
  {
    id: "CON-01J8Y000000000000000000004",
    label: "Non-Abelian Anyon Exchange Statistics",
    type: "concept",
    status: "active",
    tier: "warm",
    confidence: 0.85,
    created: "2026-08-26",
    updated: "2026-08-27",
    category: "systems",
    x: 90, y: 150, z: 80, vx: 0, vy: 0, radius: 15,
    color: "#E2E8F0", // Tier 3: General Active
    weight: 0.82, recency: "2d ago", cluster: "01_Research",
    subtopics: ["Braid Group Representation", "Unitary Matrices"],
    description: "Mathematical formulation of non-commutative braid statistics in 2D systems.",
    path: "01_Research/Concepts/CON-01J8Y000000000000000000004__non-abelian-anyon.md"
  },
  {
    id: "SRC-01J8Y000000000000000000008",
    label: "Alicea et al. 2011 Majorana Nanowires",
    type: "source",
    status: "active",
    tier: "cold",
    confidence: 0.99,
    created: "2026-08-24",
    updated: "2026-08-24",
    category: "infra_agent",
    x: 290, y: -120, z: -90, vx: 0, vy: 0, radius: 11,
    color: "#F59E0B", // Tier 4: Peripheral Source Node
    weight: 0.75, recency: "5d ago", cluster: "03_Sources",
    subtopics: ["Phys. Rev. B", "DOI: 10.1103/PhysRevB.84.205101"],
    description: "Seminal paper outlining topological superconductivity in semiconductor-superconductor heterostructures.",
    path: "03_Sources/Papers/SRC-01J8Y000000000000000000008__alicea-2011.md"
  },
  {
    id: "CTR-01J8Y000000000000000000018",
    label: "Contradiction: Braiding vs Trivial Andreev",
    type: "contradiction",
    status: "disputed",
    tier: "hot",
    confidence: 0.65,
    created: "2026-08-27",
    updated: "2026-08-29",
    category: "enhancement_agent",
    x: -80, y: -160, z: -50, vx: 0, vy: 0, radius: 16,
    color: "#EF4444", // Disputed state
    weight: 0.88, recency: "Just now", cluster: "05_Evolution",
    subtopics: ["Trivial Andreev Bound State", "Disorder Mimicry"],
    description: "Active dispute: whether zero-bias conductance peak is topological or disorder-induced Andreev state.",
    path: "05_Evolution/Contradictions/CTR-01J8Y000000000000000000018__contradiction.md"
  }
];

const SEED_EDGES: GraphEdge[] = [
  { id: "e1", source: "SYS-01J8X000000000000000000001", target: "CLM-01J8Y000000000000000000002", strength: 0.9, label: "enforces" },
  { id: "e2", source: "CLM-01J8Y000000000000000000002", target: "FCT-01J8Y000000000000000000001", strength: 0.95, label: "supports" },
  { id: "e3", source: "CLM-01J8Y000000000000000000002", target: "SRC-01J8Y000000000000000000008", strength: 0.88, label: "cites" },
  { id: "e4", source: "CON-01J8Y000000000000000000004", target: "CLM-01J8Y000000000000000000002", strength: 0.75, label: "derived_from" },
  { id: "e5", source: "CTR-01J8Y000000000000000000018", target: "CLM-01J8Y000000000000000000002", strength: 0.9, label: "contradicts" },
  { id: "e6", source: "CTR-01J8Y000000000000000000018", target: "FCT-01J8Y000000000000000000001", strength: 0.85, label: "disputes" }
];

export default function REXBrain3DExplorerPage() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // States
  const [nodes, setNodes] = useState<GraphNode[]>(SEED_NODES);
  const [edges, setEdges] = useState<GraphEdge[]>(SEED_EDGES);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(SEED_NODES[1]);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  // MUTABLE CAMERA CONTROLS (USING REFS TO PREVENT REACT STATE RECURSION)
  const pitchRef = useRef<number>(0.35); // X rotation
  const yawRef = useRef<number>(0.45);   // Y rotation
  const zoomRef = useRef<number>(1.1);
  const panXRef = useRef<number>(0);
  const panYRef = useRef<number>(0);
  const isAutoRotateRef = useRef<boolean>(true);
  const [isAutoRotateUI, setIsAutoRotateUI] = useState<boolean>(true);
  const [displayZoom, setDisplayZoom] = useState<number>(110);
  const isDraggingRef = useRef<boolean>(false);
  const dragRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Filters Panel State (Prompt 15 Requirement 3)
  const [isFilterOpen, setIsFilterOpen] = useState<boolean>(false);
  const [minConfidence, setMinConfidence] = useState<number>(0.0);
  const [maxConfidence, setMaxConfidence] = useState<number>(1.0);
  const [statusFilter, setStatusFilter] = useState<string[]>(["draft", "active", "verified", "disputed"]);
  const [tierFilter, setTierFilter] = useState<string[]>(["hot", "warm", "cold"]);
  const [typeFilter, setTypeFilter] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Path Trace Mode State (Prompt 15 Requirement 5)
  const [isPathTraceMode, setIsPathTraceMode] = useState<boolean>(false);
  const [pathSourceId, setPathSourceId] = useState<string | null>(null);
  const [pathTargetId, setPathTargetId] = useState<string | null>(null);
  const [tracedPathNodes, setTracedPathNodes] = useState<string[]>([]);
  const [tracedPathEdges, setTracedPathEdges] = useState<string[]>([]);

  // Time-Lapse Playback & Live Activity Pulse (Prompt 17)
  const [commits, setCommits] = useState<any[]>([]);
  const [currentCommitIdx, setCurrentCommitIdx] = useState<number>(0);
  const [livePulseLogs, setLivePulseLogs] = useState<string[]>([]);
  const [executingAgentNode, setExecutingAgentNode] = useState<string>("Synthesizer Agent");

  // Fetch Live Graph Data & Telemetry
  const fetchGraphData = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/brain/graph");
      if (res.ok) {
        const data = await res.json();
        if (data.nodes && data.nodes.length > 0) {
          const apiNodes: GraphNode[] = data.nodes.map((n: any, idx: number) => {
            const angle = (idx / data.nodes.length) * 2 * Math.PI;
            const rDist = 160 + (idx % 6) * 45;
            
            // Map Prompt 14 color rules based on tier/type
            let color = "#E2E8F0"; // Tier 3
            const type = n.type || "concept";
            const conf = (n.confidence || 90) / 100;
            const tier = n.tier || (idx % 3 === 0 ? "hot" : idx % 3 === 1 ? "warm" : "cold");
            
            if (n.cluster === "00_System" || n.category === "core_agent" || type === "framework") {
              color = "#6366F1"; // Tier 1: Core System
            } else if (conf >= 0.75 && (n.status === "verified" || type === "claim" || type === "fact")) {
              color = "#EF4444"; // Tier 2: High-Value Verified
            } else if (tier === "cold" || type === "source") {
              color = "#F59E0B"; // Tier 4: Peripheral Leaf
            }

            return {
              id: n.id,
              label: n.label || n.title || n.id,
              type: type,
              status: n.status || "active",
              tier: tier,
              confidence: conf,
              created: n.created || "2026-08-25",
              updated: n.updated || "2026-08-29",
              category: n.category || "ai_ml",
              x: Math.cos(angle) * rDist,
              y: Math.sin(angle) * rDist,
              z: (idx % 5 - 2) * 50,
              vx: 0, vy: 0,
              radius: 12 + Math.min(12, (n.out_links || []).length * 2), // Prompt 14 degree-based size
              color: color,
              weight: n.weight || 0.8,
              recency: n.recency || "Live",
              cluster: n.cluster || "02_Knowledge",
              subtopics: n.subtopics || [],
              description: n.description || "",
              path: n.path || `02_Knowledge/Claims/${n.id}.md`
            };
          });

          const apiEdges: GraphEdge[] = (data.edges || []).map((e: any, idx: number) => ({
            id: e.id || `e_${idx}`,
            source: e.source,
            target: e.target,
            strength: e.strength || 0.85,
            label: e.label || "related_to"
          }));

          setNodes(apiNodes);
          setEdges(apiEdges);
          if (data.telemetry?.telemetry_logs) {
            setLivePulseLogs(data.telemetry.telemetry_logs);
          }
        }
      }
    } catch (e) {
      console.warn("Using fallback seed graph payload.");
    }
  }, []);

  // Fetch Time-Lapse Commits
  const fetchTimelapseData = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8000/api/v1/brain/timelapse");
      if (res.ok) {
        const data = await res.json();
        if (data.commits && data.commits.length > 0) {
          setCommits(data.commits);
        }
      }
    } catch (e) {
      console.warn("Time-lapse service unavailable.");
    }
  }, []);

  useEffect(() => {
    fetchGraphData();
    fetchTimelapseData();
    const interval = setInterval(fetchGraphData, 12000);
    return () => clearInterval(interval);
  }, [fetchGraphData, fetchTimelapseData]);

  // Path Trace Mode Execution (Prompt 15 Requirement 5)
  const executePathTrace = useCallback(async (srcId: string, tgtId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/brain/path?source=${srcId}&target=${tgtId}`);
      if (res.ok) {
        const data = await res.json();
        setTracedPathNodes(data.path_nodes || []);
        setTracedPathEdges(data.path_edges || []);
      }
    } catch (e) {
      console.error("Path trace failed:", e);
    }
  }, []);

  // Handle Node Click in 3D Canvas
  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
    if (isPathTraceMode) {
      if (!pathSourceId) {
        setPathSourceId(node.id);
      } else if (!pathTargetId && node.id !== pathSourceId) {
        setPathTargetId(node.id);
        executePathTrace(pathSourceId, node.id);
      } else {
        setPathSourceId(node.id);
        setPathTargetId(null);
        setTracedPathNodes([]);
        setTracedPathEdges([]);
      }
    }
  }, [isPathTraceMode, pathSourceId, pathTargetId, executePathTrace]);

  // 1-Hop Neighbor Ego-Network Isolation Set (Prompt 15 Requirement 2)
  const connectedNeighborIds = useMemo(() => {
    if (!hoveredNodeId) return new Set<string>();
    const neighbors = new Set<string>([hoveredNodeId]);
    edges.forEach((e) => {
      if (e.source === hoveredNodeId) neighbors.add(e.target);
      if (e.target === hoveredNodeId) neighbors.add(e.source);
    });
    return neighbors;
  }, [hoveredNodeId, edges]);

  // Filtered Nodes Calculation (Prompt 15 Requirement 3)
  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => {
      if (n.confidence < minConfidence || n.confidence > maxConfidence) return false;
      if (statusFilter.length > 0 && n.status && !statusFilter.includes(n.status)) return false;
      if (tierFilter.length > 0 && n.tier && !tierFilter.includes(n.tier)) return false;
      if (typeFilter.length > 0 && n.type && !typeFilter.includes(n.type)) return false;
      if (searchQuery.trim() !== "") {
        const q = searchQuery.toLowerCase();
        const matchTitle = n.label.toLowerCase().includes(q);
        const matchId = n.id.toLowerCase().includes(q);
        const matchSub = n.subtopics.some((s) => s.toLowerCase().includes(q));
        if (!matchTitle && !matchId && !matchSub) return false;
      }
      return true;
    });
  }, [nodes, minConfidence, maxConfidence, statusFilter, tierFilter, typeFilter, searchQuery]);

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes]);

  // Search Jump & Center Camera (Prompt 15 Requirement 4)
  const handleSearchJump = (query: string) => {
    setSearchQuery(query);
    if (!query.trim()) return;
    const match = nodes.find((n) => n.label.toLowerCase().includes(query.toLowerCase()) || n.id.toLowerCase().includes(query.toLowerCase()));
    if (match) {
      setSelectedNode(match);
      isAutoRotateRef.current = false;
      setIsAutoRotateUI(false);
      yawRef.current = -Math.atan2(match.x, match.z || 100);
      pitchRef.current = Math.atan2(match.y, 250);
      zoomRef.current = 1.35;
      setDisplayZoom(135);
    }
  };

  // Zoom Button Controls (Zoom In, Zoom Out, Reset)
  const handleZoomIn = () => {
    zoomRef.current = Math.min(2.8, zoomRef.current + 0.15);
    setDisplayZoom(Math.round(zoomRef.current * 100));
  };

  const handleZoomOut = () => {
    zoomRef.current = Math.max(0.4, zoomRef.current - 0.15);
    setDisplayZoom(Math.round(zoomRef.current * 100));
  };

  const handleResetCamera = () => {
    pitchRef.current = 0.35;
    yawRef.current = 0.45;
    zoomRef.current = 1.1;
    panXRef.current = 0;
    panYRef.current = 0;
    setDisplayZoom(110);
  };

  // ----------------------------------------------------------------------------
  // 3D PERSPECTIVE CANVAS RENDERING ENGINE (USING REFS - NO REACT STATE RECURSION)
  // ----------------------------------------------------------------------------
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;

    const render = () => {
      canvas.width = canvas.parentElement?.clientWidth || 1000;
      canvas.height = canvas.parentElement?.clientHeight || 700;

      const width = canvas.width;
      const height = canvas.height;
      const centerX = width / 2 + panXRef.current;
      const centerY = height / 2 + panYRef.current;

      ctx.clearRect(0, 0, width, height);

      // Auto-Rotate directly on ref
      if (isAutoRotateRef.current && !isDraggingRef.current) {
        yawRef.current += 0.0025;
      }

      const currentYaw = yawRef.current;
      const currentPitch = pitchRef.current;
      const currentZoom = zoomRef.current;

      const cosYaw = Math.cos(currentYaw);
      const sinYaw = Math.sin(currentYaw);
      const cosPitch = Math.cos(currentPitch);
      const sinPitch = Math.sin(currentPitch);

      // Project Nodes to 3D Screen Coordinates
      const projectedNodes: (GraphNode & { screenX: number; screenY: number; screenScale: number; screenZ: number })[] = [];
      const nodeScreenMap = new Map<string, { x: number; y: number; scale: number; z: number }>();

      filteredNodes.forEach((node) => {
        const x0 = node.x;
        const y0 = node.y;
        const z0 = node.z || 0;

        // 3D YAW & PITCH MATRIX ROTATION
        const x1 = x0 * cosYaw + z0 * sinYaw;
        const z1 = -x0 * sinYaw + z0 * cosYaw;

        const y2 = y0 * cosPitch - z1 * sinPitch;
        const z2 = y0 * sinPitch + z1 * cosPitch;

        // PERSPECTIVE PROJECTION SCALE
        const cameraDistance = 550;
        const perspectiveScale = (cameraDistance / (cameraDistance + z2)) * currentZoom;

        const screenX = centerX + x1 * perspectiveScale;
        const screenY = centerY + y2 * perspectiveScale;

        projectedNodes.push({
          ...node,
          screenX,
          screenY,
          screenScale: perspectiveScale,
          screenZ: z2
        });

        nodeScreenMap.set(node.id, { x: screenX, y: screenY, scale: perspectiveScale, z: z2 });
      });

      // SORT NODES BY Z-DEPTH (Back-to-Front)
      projectedNodes.sort((a, b) => b.screenZ - a.screenZ);

      // DRAW RELATIONSHIP EDGES
      edges.forEach((edge) => {
        const src = nodeScreenMap.get(edge.source);
        const tgt = nodeScreenMap.get(edge.target);

        if (src && tgt && filteredNodeIds.has(edge.source) && filteredNodeIds.has(edge.target)) {
          const isEgoHighlighted = connectedNeighborIds.has(edge.source) && connectedNeighborIds.has(edge.target);
          const isPathHighlighted = tracedPathEdges.includes(edge.id) || (tracedPathNodes.includes(edge.source) && tracedPathNodes.includes(edge.target));
          const isDimmed = hoveredNodeId && !isEgoHighlighted;

          ctx.beginPath();
          ctx.moveTo(src.x, src.y);
          ctx.lineTo(tgt.x, tgt.y);

          if (isPathHighlighted) {
            ctx.strokeStyle = "#06B6D4"; // Path Trace Beam: Glowing Cyan
            ctx.lineWidth = 3.5;
            ctx.shadowColor = "#06B6D4";
            ctx.shadowBlur = 12;
          } else if (isEgoHighlighted) {
            ctx.strokeStyle = "#F59E0B"; // Ego Highlight: Glowing Gold
            ctx.lineWidth = 2.2;
            ctx.shadowColor = "#F59E0B";
            ctx.shadowBlur = 8;
          } else {
            ctx.strokeStyle = isDimmed ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.14)";
            ctx.lineWidth = Math.max(0.6, edge.strength * 1.5);
            ctx.shadowBlur = 0;
          }
          ctx.stroke();
          ctx.shadowBlur = 0;
        }
      });

      // DRAW 3D NODES
      projectedNodes.forEach((node) => {
        const r = Math.max(5, node.radius * node.screenScale);
        const isHovered = hoveredNodeId === node.id;
        const isSelected = selectedNode?.id === node.id;
        const isEgoNeighbor = connectedNeighborIds.has(node.id);
        const isPathNode = tracedPathNodes.includes(node.id);
        const isDimmed = hoveredNodeId && !isEgoNeighbor;

        // Depth fog opacity
        const depthAlpha = Math.max(0.4, Math.min(1.0, (550 - node.screenZ) / 550));
        const finalAlpha = isDimmed ? 0.12 : depthAlpha;

        ctx.save();
        ctx.globalAlpha = finalAlpha;

        // Hover / Selection Glow Halo Ring
        if (isSelected || isHovered || isPathNode) {
          ctx.beginPath();
          ctx.arc(node.screenX, node.screenY, r + 8, 0, Math.PI * 2);
          ctx.fillStyle = isPathNode ? "rgba(6, 182, 212, 0.3)" : isSelected ? "rgba(245, 158, 11, 0.35)" : "rgba(139, 92, 246, 0.3)";
          ctx.fill();
        }

        // Live Activity Pulse Flare Ring (Prompt 17)
        if (node.isNew) {
          const pulseR = r + 12 + Math.sin(Date.now() / 150) * 4;
          ctx.beginPath();
          ctx.arc(node.screenX, node.screenY, pulseR, 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(16, 185, 129, 0.8)";
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Core Solid Sphere Node Body
        ctx.beginPath();
        ctx.arc(node.screenX, node.screenY, r, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.shadowColor = node.color;
        ctx.shadowBlur = isSelected || isHovered ? 18 : 6;
        ctx.fill();

        // High-Contrast Dark Inner Sphere Core
        ctx.beginPath();
        ctx.arc(node.screenX, node.screenY, r * 0.45, 0, Math.PI * 2);
        ctx.fillStyle = "#121214";
        ctx.fill();

        // High-Contrast Node Label
        if (node.screenScale > 0.65 && !isDimmed) {
          ctx.fillStyle = isSelected ? "#F59E0B" : "#F8FAFC";
          ctx.font = `${Math.max(10, Math.round(12 * node.screenScale))}px 'Inter', sans-serif`;
          ctx.textAlign = "center";
          ctx.fillText(node.label, node.screenX, node.screenY + r + 14);
        }

        ctx.restore();
      });

      animId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animId);
  }, [
    filteredNodes,
    edges,
    hoveredNodeId,
    selectedNode,
    connectedNeighborIds,
    tracedPathNodes,
    tracedPathEdges,
    filteredNodeIds
  ]);

  // Canvas Mouse Drag Orbit Controls
  const handleMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = true;
    dragRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDraggingRef.current) return;
    const dx = e.clientX - dragRef.current.x;
    const dy = e.clientY - dragRef.current.y;
    dragRef.current = { x: e.clientX, y: e.clientY };

    if (e.shiftKey || e.buttons === 2) {
      panXRef.current += dx;
      panYRef.current += dy;
    } else {
      yawRef.current += dx * 0.006;
      pitchRef.current = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, pitchRef.current - dy * 0.006));
    }
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    zoomRef.current = Math.max(0.4, Math.min(2.8, zoomRef.current - e.deltaY * 0.0012));
    setDisplayZoom(Math.round(zoomRef.current * 100));
  };

  return (
    <div className="relative min-h-screen bg-[#0C0A09] text-[#F5F0E8] font-sans overflow-hidden flex flex-col">
      <BackgroundCanvas />

      {/* HEADER BAR */}
      <header className="relative z-20 flex items-center justify-between px-6 py-4 border-b border-[#252219] bg-[#141210]/90 backdrop-blur-md">
        <div className="flex items-center space-x-4">
          <Link href="/" className="p-2 rounded-xl bg-[#1E1B18] border border-[#252219] text-[#A09880] hover:text-[#E8D5B7] transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-[#E8D5B7] flex items-center gap-2">
                <BrainCircuit className="w-6 h-6 text-[#F59E0B]" />
                REX-Brain: Interactive 3D Explorer
              </h1>
              <span className="px-2.5 py-0.5 text-xs font-mono font-semibold text-[#10B981] bg-[#10B981]/10 rounded-full border border-[#10B981]/30">
                PROMPT 15 LIVE
              </span>
            </div>
            <p className="text-xs text-[#A09880]">Real-time Obsidian Vault Knowledge Graph with 3D Orbit & Path Trace</p>
          </div>
        </div>

        {/* TOP CONTROLS & SEARCH */}
        <div className="flex items-center space-x-3">
          {/* FUZZY SEARCH INPUT (Prompt 15 Requirement 4) */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-[#A09880]" />
            <input
              type="text"
              placeholder="Fuzzy search title..."
              value={searchQuery}
              onChange={(e) => handleSearchJump(e.target.value)}
              className="w-64 pl-9 pr-4 py-2 bg-[#1E1B18] border border-[#252219] rounded-xl text-xs text-[#F5F0E8] placeholder-[#5C5448] focus:outline-none focus:border-[#F59E0B]"
            />
          </div>

          {/* PATH TRACE MODE TOGGLE (Prompt 15 Requirement 5) */}
          <button
            onClick={() => {
              setIsPathTraceMode(!isPathTraceMode);
              setPathSourceId(null);
              setPathTargetId(null);
              setTracedPathNodes([]);
              setTracedPathEdges([]);
            }}
            className={`px-3 py-2 rounded-xl border text-xs font-medium flex items-center gap-2 transition-all ${
              isPathTraceMode
                ? "bg-[#06B6D4]/20 border-[#06B6D4] text-[#06B6D4] shadow-lg shadow-[#06B6D4]/20"
                : "bg-[#1E1B18] border-[#252219] text-[#A09880] hover:text-[#E8D5B7]"
            }`}
          >
            <Compass className="w-4 h-4" />
            {isPathTraceMode ? "Path Trace Active" : "Trace Path"}
          </button>

          {/* FILTER PANEL TOGGLE */}
          <button
            onClick={() => setIsFilterOpen(!isFilterOpen)}
            className={`p-2.5 rounded-xl border transition-all ${
              isFilterOpen ? "bg-[#F59E0B] border-[#F59E0B] text-[#121214]" : "bg-[#1E1B18] border-[#252219] text-[#A09880] hover:text-[#E8D5B7]"
            }`}
          >
            <Filter className="w-4 h-4" />
          </button>

          {/* LINK TO EVOLUTION VISUALIZATION PAGE (Prompt 16) */}
          <Link
            href="/evolution"
            className="px-3.5 py-2 rounded-xl bg-[#C2410C]/20 border border-[#C2410C] text-[#C2410C] text-xs font-semibold hover:bg-[#C2410C]/30 transition-all flex items-center gap-2"
          >
            <Workflow className="w-4 h-4" />
            Self-Evolution Views
          </Link>
        </div>
      </header>

      {/* MAIN VIEWPORT CANVAS & OVERLAYS */}
      <div className="relative flex-1 flex overflow-hidden">
        {/* 3D CANVAS EXPLORER */}
        <div className="relative flex-1 bg-[#0C0A09] cursor-grab active:cursor-grabbing">
          <canvas
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onWheel={handleWheel}
            onContextMenu={(e) => e.preventDefault()}
            className="w-full h-full block"
          />

          {/* FLOATING SPATIAL CAMERA ORBIT HUD & EXPLICIT ZOOM BUTTONS */}
          <div className="absolute top-4 left-4 z-10 flex flex-col gap-2.5 bg-[#141210]/90 backdrop-blur-md p-3.5 rounded-2xl border border-[#252219] shadow-xl">
            <div className="flex items-center justify-between text-xs text-[#A09880]">
              <span>Spatial Camera</span>
              <span className="font-mono text-[#F59E0B] font-bold">{displayZoom}%</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  isAutoRotateRef.current = !isAutoRotateRef.current;
                  setIsAutoRotateUI(isAutoRotateRef.current);
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border flex items-center gap-1.5 ${
                  isAutoRotateUI ? "bg-[#F59E0B]/20 border-[#F59E0B] text-[#F59E0B]" : "bg-[#1E1B18] border-[#252219] text-[#A09880]"
                }`}
              >
                {isAutoRotateUI ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                360° Orbit
              </button>

              {/* ZOOM IN BUTTON */}
              <button
                onClick={handleZoomIn}
                title="Zoom In"
                className="p-1.5 rounded-lg bg-[#1E1B18] border border-[#252219] text-[#A09880] hover:text-[#E8D5B7] hover:border-[#F59E0B] transition-all"
              >
                <ZoomIn className="w-4 h-4" />
              </button>

              {/* ZOOM OUT BUTTON */}
              <button
                onClick={handleZoomOut}
                title="Zoom Out"
                className="p-1.5 rounded-lg bg-[#1E1B18] border border-[#252219] text-[#A09880] hover:text-[#E8D5B7] hover:border-[#F59E0B] transition-all"
              >
                <ZoomOut className="w-4 h-4" />
              </button>

              {/* RESET CAMERA BUTTON */}
              <button
                onClick={handleResetCamera}
                title="Reset Camera View"
                className="p-1.5 rounded-lg bg-[#1E1B18] border border-[#252219] text-[#A09880] hover:text-[#E8D5B7] hover:border-[#F59E0B] transition-all"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* PATH TRACE INSTRUCTION BANNER */}
          {isPathTraceMode && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 px-4 py-2 bg-[#06B6D4]/20 border border-[#06B6D4] text-[#06B6D4] text-xs font-medium rounded-xl flex items-center gap-3 shadow-xl">
              <Compass className="w-4 h-4 animate-spin" />
              <span>
                {!pathSourceId
                  ? "Click Source Node A"
                  : !pathTargetId
                  ? `Source selected: ${pathSourceId.slice(0, 10)}... Click Target Node B`
                  : `Path Traced (${tracedPathNodes.length} nodes, ${tracedPathEdges.length} edges)`}
              </span>
            </div>
          )}

          {/* LIVE ACTIVITY PULSE LOG OVERLAY (Prompt 17) */}
          <div className="absolute bottom-4 left-4 z-10 w-96 bg-[#141210]/90 backdrop-blur-md p-3.5 rounded-2xl border border-[#252219]">
            <div className="flex items-center justify-between text-xs font-bold text-[#E8D5B7] mb-2">
              <span className="flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-[#10B981] animate-pulse" />
                Live Ingestion Stream
              </span>
              <span className="text-[10px] text-[#A09880]">{executingAgentNode}</span>
            </div>
            <div className="space-y-1.5 max-h-24 overflow-y-auto font-mono text-[11px] text-[#A09880]">
              {livePulseLogs.slice(0, 3).map((log, idx) => (
                <div key={idx} className="flex items-center gap-2 truncate text-[#F5F0E8]/90">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
                  <span>{log}</span>
                </div>
              ))}
            </div>
          </div>

          {/* TIME-LAPSE PLAYBACK SCRUB BAR (Prompt 17) */}
          <div className="absolute bottom-4 right-4 z-10 w-80 bg-[#141210]/90 backdrop-blur-md p-3.5 rounded-2xl border border-[#252219]">
            <div className="flex items-center justify-between text-xs text-[#E8D5B7] mb-2">
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-[#F59E0B]" />
                Git Vault Time-Lapse
              </span>
              <span className="text-[10px] text-[#A09880]">{commits.length} commits</span>
            </div>
            <input
              type="range"
              min={0}
              max={Math.max(0, commits.length - 1)}
              value={currentCommitIdx}
              onChange={(e) => setCurrentCommitIdx(Number(e.target.value))}
              className="w-full h-1.5 bg-[#252219] rounded-lg appearance-none cursor-pointer accent-[#F59E0B]"
            />
            {commits[currentCommitIdx] && (
              <div className="mt-2 text-[10px] text-[#A09880] truncate font-mono">
                {commits[currentCommitIdx].commit} — {commits[currentCommitIdx].message}
              </div>
            )}
          </div>
        </div>

        {/* MULTI-FILTER DRAWER (Prompt 15 Requirement 3) */}
        <AnimatePresence>
          {isFilterOpen && (
            <motion.div
              initial={{ x: -320, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -320, opacity: 0 }}
              className="w-80 border-r border-[#252219] bg-[#141210] p-5 overflow-y-auto flex flex-col gap-5 z-20"
            >
              <div className="flex items-center justify-between border-b border-[#252219] pb-3">
                <h3 className="text-sm font-bold text-[#E8D5B7] flex items-center gap-2">
                  <SlidersHorizontal className="w-4 h-4 text-[#F59E0B]" />
                  Graph Multi-Filters
                </h3>
                <button onClick={() => setIsFilterOpen(false)} className="text-[#A09880] hover:text-[#E8D5B7]">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* CONFIDENCE SLIDER */}
              <div>
                <label className="text-xs text-[#A09880] block mb-2">Confidence Range (Min: {(minConfidence * 100).toFixed(0)}%)</label>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={minConfidence}
                  onChange={(e) => setMinConfidence(Number(e.target.value))}
                  className="w-full h-1.5 bg-[#252219] rounded-lg appearance-none cursor-pointer accent-[#F59E0B]"
                />
              </div>

              {/* STATUS MULTI-SELECT */}
              <div>
                <label className="text-xs text-[#A09880] block mb-2">Status Enum</label>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {["draft", "active", "verified", "disputed", "archived"].map((st) => (
                    <button
                      key={st}
                      onClick={() =>
                        setStatusFilter((prev) => (prev.includes(st) ? prev.filter((s) => s !== st) : [...prev, st]))
                      }
                      className={`px-2.5 py-1.5 rounded-lg border text-left font-mono ${
                        statusFilter.includes(st) ? "bg-[#F59E0B]/20 border-[#F59E0B] text-[#F59E0B]" : "bg-[#1E1B18] border-[#252219] text-[#A09880]"
                      }`}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </div>

              {/* TIER MULTI-SELECT */}
              <div>
                <label className="text-xs text-[#A09880] block mb-2">Memory Tier</label>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  {["hot", "warm", "cold"].map((t) => (
                    <button
                      key={t}
                      onClick={() => setTierFilter((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]))}
                      className={`px-2.5 py-1.5 rounded-lg border text-center font-mono capitalize ${
                        tierFilter.includes(t) ? "bg-[#10B981]/20 border-[#10B981] text-[#10B981]" : "bg-[#1E1B18] border-[#252219] text-[#A09880]"
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* SIDE PANEL DETAIL DRAWER (Prompt 15 Requirement 1) */}
        <AnimatePresence>
          {selectedNode && (
            <motion.div
              initial={{ x: 360, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 360, opacity: 0 }}
              className="w-96 border-l border-[#252219] bg-[#141210] p-6 overflow-y-auto flex flex-col justify-between z-20"
            >
              <div>
                <div className="flex items-center justify-between border-b border-[#252219] pb-4 mb-4">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-[#F59E0B] bg-[#F59E0B]/10 px-2 py-0.5 rounded border border-[#F59E0B]/30">
                      {selectedNode.type || "concept"}
                    </span>
                    <h2 className="text-base font-bold text-[#E8D5B7] mt-2 leading-tight">{selectedNode.label}</h2>
                  </div>
                  <button onClick={() => setSelectedNode(null)} className="text-[#A09880] hover:text-[#E8D5B7]">
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* FRONTMATTER DETAILS */}
                <div className="space-y-4 text-xs text-[#A09880]">
                  <div className="grid grid-cols-2 gap-3 bg-[#1E1B18] p-3 rounded-xl border border-[#252219] font-mono text-[11px]">
                    <div>
                      <span className="block text-[10px] text-[#5C5448]">STATUS</span>
                      <span className="text-[#F5F0E8] capitalize">{selectedNode.status || "active"}</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-[#5C5448]">TIER</span>
                      <span className="text-[#10B981] capitalize">{selectedNode.tier || "hot"}</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-[#5C5448]">CONFIDENCE</span>
                      <span className="text-[#F59E0B]">{((selectedNode.confidence || 0.9) * 100).toFixed(0)}%</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-[#5C5448]">CREATED</span>
                      <span className="text-[#F5F0E8]">{selectedNode.created || "2026-08-25"}</span>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold text-[#E8D5B7] mb-1">Body Preview & Metadata</h4>
                    <p className="text-xs text-[#A09880] leading-relaxed bg-[#1E1B18] p-3 rounded-xl border border-[#252219]">
                      {selectedNode.description}
                    </p>
                  </div>

                  {/* SUBTOPICS / TAGS */}
                  {selectedNode.subtopics.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-[#E8D5B7] mb-1.5">Tags</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedNode.subtopics.map((t, idx) => (
                          <span key={idx} className="px-2 py-0.5 bg-[#1E1B18] border border-[#252219] rounded-md text-[10px] text-[#A09880]">
                            #{t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* DIRECT OBSIDIAN:// URI LINK BUTTON (Prompt 15 Requirement 1) */}
              <div className="pt-6 border-t border-[#252219]">
                <a
                  href={`obsidian://open?path=${encodeURIComponent(`REX-Brain/${selectedNode.path || ""}`)}`}
                  className="w-full py-2.5 rounded-xl bg-[#F59E0B] text-[#121214] text-xs font-bold hover:bg-[#F59E0B]/90 transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#F59E0B]/20"
                >
                  <ExternalLink className="w-4 h-4" />
                  Open in Obsidian Vault
                </a>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
