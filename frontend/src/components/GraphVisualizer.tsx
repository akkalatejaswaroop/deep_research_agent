import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  MarkerType
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';

const initialNodes: Node[] = [
  { id: 'planner', position: { x: 0, y: 0 }, data: { label: 'Plan' }, style: { background: 'var(--card)', color: 'var(--text-1)', border: '1px solid var(--border)', borderRadius: '10px', padding: '12px 16px', fontSize: '13px', fontWeight: 600 } },
  { id: 'memory_retrieval', position: { x: 0, y: 0 }, data: { label: 'Memory' }, style: { background: 'var(--card)', color: 'var(--text-1)', border: '1px solid var(--border)', borderRadius: '10px', padding: '12px 16px', fontSize: '13px', fontWeight: 600 } },
  { id: 'searcher', position: { x: 0, y: 0 }, data: { label: 'Search' }, style: { background: 'var(--card)', color: 'var(--text-1)', border: '1px solid var(--border)', borderRadius: '10px', padding: '12px 16px', fontSize: '13px', fontWeight: 600 } },
  { id: 'filter', position: { x: 0, y: 0 }, data: { label: 'Filter' }, style: { background: 'var(--card)', color: 'var(--text-1)', border: '1px solid var(--border)', borderRadius: '10px', padding: '12px 16px', fontSize: '13px', fontWeight: 600 } },
  { id: 'synthesis', position: { x: 0, y: 0 }, data: { label: 'Synthesize' }, style: { background: 'var(--card)', color: 'var(--text-1)', border: '1px solid var(--border)', borderRadius: '10px', padding: '12px 16px', fontSize: '13px', fontWeight: 600 } },
  { id: 'gap_detector', position: { x: 0, y: 0 }, data: { label: 'Detect Gaps' }, style: { background: 'var(--card)', color: 'var(--text-1)', border: '1px solid var(--border)', borderRadius: '10px', padding: '12px 16px', fontSize: '13px', fontWeight: 600 } },
  { id: 'citation_mapper', position: { x: 0, y: 0 }, data: { label: 'Cite' }, style: { background: 'var(--card)', color: 'var(--text-1)', border: '1px solid var(--border)', borderRadius: '10px', padding: '12px 16px', fontSize: '13px', fontWeight: 600 } },
  { id: 'report', position: { x: 0, y: 0 }, data: { label: 'Report' }, style: { background: 'var(--card)', color: 'var(--text-1)', border: '1px solid var(--border)', borderRadius: '10px', padding: '12px 16px', fontSize: '13px', fontWeight: 600 } },
  { id: 'evaluator', position: { x: 0, y: 0 }, data: { label: 'Evaluate' }, style: { background: 'var(--card)', color: 'var(--text-1)', border: '1px solid var(--border)', borderRadius: '10px', padding: '12px 16px', fontSize: '13px', fontWeight: 600 } },
];

const initialEdges: Edge[] = [
  { id: 'e1-1b', source: 'planner', target: 'memory_retrieval', animated: true, style: { stroke: 'var(--brand-primary)', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--brand-primary)' } },
  { id: 'e1b-2', source: 'memory_retrieval', target: 'searcher', animated: true, style: { stroke: 'var(--brand-primary)', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--brand-primary)' } },
  { id: 'e2-3', source: 'searcher', target: 'filter', animated: true, style: { stroke: 'var(--brand-primary)', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--brand-primary)' } },
  { id: 'e3-4', source: 'filter', target: 'synthesis', animated: true, style: { stroke: 'var(--brand-primary)', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--brand-primary)' } },
  { id: 'e4-5', source: 'synthesis', target: 'gap_detector', animated: true, style: { stroke: 'var(--brand-primary)', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--brand-primary)' } },
  { id: 'e5-2', source: 'gap_detector', target: 'searcher', animated: true, style: { stroke: 'var(--accent-ember)', strokeDasharray: '6 4', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--accent-ember)' } },
  { id: 'e5-6', source: 'gap_detector', target: 'citation_mapper', animated: true, style: { stroke: 'var(--brand-primary)', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--brand-primary)' } },
  { id: 'e6-7', source: 'citation_mapper', target: 'report', animated: true, style: { stroke: 'var(--brand-primary)', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--brand-primary)' } },
  { id: 'e7-8', source: 'report', target: 'evaluator', animated: true, style: { stroke: 'var(--brand-primary)', strokeWidth: 2 }, markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--brand-primary)' } },
];

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 130;
const nodeHeight = 44;

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'TB') => {
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: 'top',
      sourcePosition: 'bottom',
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

export default function GraphVisualizer({ activeNode }: { activeNode: string | null }) {
  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(
    () => getLayoutedElements(initialNodes, initialEdges),
    []
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes as Node[]);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);

  useEffect(() => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === activeNode) {
          return {
            ...node,
            style: {
              ...node.style,
              background: 'var(--brand-primary)',
              color: 'var(--background)',
              border: 'none',
              boxShadow: '0 0 20px rgba(212, 168, 83, 0.3), 0 0 40px rgba(212, 168, 83, 0.1)',
            },
          };
        }
        return {
          ...node,
          style: {
            ...node.style,
            background: 'var(--card)',
            color: 'var(--text-1)',
            border: '1px solid var(--border)',
            boxShadow: 'none',
          },
        };
      })
    );
  }, [activeNode, setNodes]);

  const onConnect = useCallback(
    (params: Connection | Edge) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  return (
    <div className="w-full h-[500px] glass-panel overflow-hidden relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
      >
        <Controls className="bg-[var(--surface)] border-[var(--border)] fill-[var(--text-1)] [&_button]:hover:bg-[var(--card)] [&_button]:border-[var(--border)]" />
        <MiniMap nodeColor="var(--brand-muted)" maskColor="var(--background)" style={{ border: '1px solid var(--border)', borderRadius: 8 }} />
        <Background color="var(--brand-muted)" gap={20} size={1} />
      </ReactFlow>
    </div>
  );
}
