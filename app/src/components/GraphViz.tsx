import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Network } from 'lucide-react';
import ForceGraph2D from 'react-force-graph-2d';
import type { ForceGraphMethods } from 'react-force-graph-2d';
import * as d3 from 'd3-force';

interface GraphNode {
  id: number;
  labels: string[];
  properties: Record<string, any>;
}

interface GraphRel {
  start: number;
  end: number;
  type: string;
}

interface Props {
  graphData: { nodes: GraphNode[]; relationships: GraphRel[] };
}

export default function GraphViz({ graphData }: Props) {
  const fgRef = useRef<ForceGraphMethods>(null as any);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [initialCenterDone, setInitialCenterDone] = useState(false);

  // Handle responsive resize
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(entries => {
      setDimensions({
        width: entries[0].contentRect.width,
        height: entries[0].contentRect.height
      });
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Transform Neo4j data to ForceGraph format
  const fgData = useMemo(() => {
    if (!graphData) return { nodes: [], links: [] };
    return {
      nodes: graphData.nodes.map(n => ({ ...n, val: getNodeSize(n.labels) })),
      links: graphData.relationships.map(r => ({
        source: r.start,
        target: r.end,
        type: r.type
      }))
    };
  }, [graphData]);

  // Sizing logic
  function getNodeSize(labels: string[]) {
    if (labels.includes('ScamRing')) return 20;
    if (labels.includes('Domain')) return 14;
    return 10;
  }

  // Coloring logic
  function getNodeColor(labels: string[], props: Record<string, any>): string {
    if (labels.includes('ScamRing')) return '#DC2626';
    if (props.is_flagged) return '#F97316';
    if (props.risk_score !== undefined && props.risk_score < 25) return '#EF4444';
    if (labels.includes('Domain')) return '#6366F1';
    if (labels.includes('Email')) return '#8B5CF6';
    if (labels.includes('Phone')) return '#06B6D4';
    if (labels.includes('Company')) return '#10B981';
    if (labels.includes('Person')) return '#F59E0B';
    return '#94A3B8';
  }

  function getNodeLabel(n: any): string {
    const p = n.properties;
    return p.value || p.name || n.labels[0] || String(n.id);
  }

  // Custom Physics config
  useEffect(() => {
    const fg = fgRef.current;
    if (fg) {
      // Modify existing forces instead of overwriting to preserve internal linkages
      fg.d3Force('charge')?.strength(-600);
      fg.d3Force('link')?.distance(120);
      fg.d3Force('collide', d3.forceCollide().radius((node: any) => node.val + 20));
      
      // Trigger a reheat to apply the new forces
      fg.d3ReheatSimulation();
    }
  }, [fgData, dimensions]);

  const handleEngineStop = useCallback(() => {
    if (!initialCenterDone && fgRef.current) {
      fgRef.current.zoomToFit(400, 50);
      setInitialCenterDone(true);
    }
  }, [initialCenterDone]);

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-8 text-center">
        <Network className="h-8 w-8 text-slate-300 mx-auto mb-2" />
        <p className="text-sm text-slate-500">No graph connections found for this entity yet.</p>
      </div>
    );
  }

  const isHierarchical = fgData.nodes.length <= 8;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900">Connection Graph</h3>
        {graphData.nodes.some(n => n.properties.is_flagged || n.labels.includes('ScamRing')) && (
          <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
            High Risk Network
          </span>
        )}
      </div>

      <div 
        ref={containerRef} 
        className="h-[450px] w-full rounded-xl border border-slate-200 bg-slate-50 overflow-hidden relative cursor-grab active:cursor-grabbing"
      >
        {dimensions.width > 0 && (
          <ForceGraph2D
            ref={fgRef as any}
            width={dimensions.width}
            height={dimensions.height}
            graphData={fgData}
            dagMode={isHierarchical ? 'td' : undefined}
            dagLevelDistance={100}
            nodeRelSize={1}
            nodeId="id"
            // Tooltip (hover text)
            nodeLabel={getNodeLabel}
            // Rendering nodes
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              const label = getNodeLabel(node);
              const fontSize = 12 / globalScale;
              const r = node.val;
              const color = getNodeColor(node.labels, node.properties);

              // Glow for flagged
              if (node.properties.is_flagged) {
                ctx.beginPath();
                ctx.arc(node.x, node.y, r + 8, 0, 2 * Math.PI, false);
                ctx.fillStyle = 'rgba(239, 68, 68, 0.15)';
                ctx.fill();
              }

              // Node circle
              ctx.beginPath();
              ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
              ctx.fillStyle = color;
              ctx.fill();
              ctx.strokeStyle = '#fff';
              ctx.lineWidth = 2 / globalScale;
              ctx.stroke();

              // Text Label
              ctx.font = `${fontSize}px Sans-Serif`;
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = '#1E293B';
              
              const shortLabel = label.length > 20 ? label.slice(0, 20) + '...' : label;
              ctx.fillText(shortLabel, node.x, node.y + r + 10 / globalScale);
              
              // Node Type Label
              ctx.fillStyle = '#64748B';
              ctx.font = `${fontSize * 0.8}px Sans-Serif`;
              ctx.fillText(node.labels[0] || '', node.x, node.y + r + 22 / globalScale);
            }}
            // Edge styling
            linkColor={(link: any) => {
              if (link.type === 'IMPERSONATES') return '#EF4444';
              if (link.type === 'BELONGS_TO_RING') return '#DC2626';
              if (link.type === 'REPORTED_WITH') return '#6366F1';
              return '#CBD5E1';
            }}
            linkWidth={(link: any) => link.type === 'IMPERSONATES' ? 2 : 1}
            linkLineDash={(link: any) => 
              ['IMPERSONATES', 'BELONGS_TO_RING'].includes(link.type) ? [5, 5] : []
            }
            // Link Labels
            linkCanvasObjectMode={() => 'after'}
            linkCanvasObject={(link: any, ctx, globalScale) => {
              // Hide edge labels until zoomed in
              if (globalScale < 1.5) return;

              const start = link.source;
              const end = link.target;
              if (typeof start !== 'object' || typeof end !== 'object') return;
              
              const PosX = start.x + (end.x - start.x) / 2;
              const PosY = start.y + (end.y - start.y) / 2;
              
              ctx.font = `${9 / globalScale}px Sans-Serif`;
              ctx.fillStyle = '#94A3B8';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              
              // Add a slight white background to text to avoid edge overlap
              const textWidth = ctx.measureText(link.type).width;
              ctx.fillStyle = 'rgba(248, 250, 252, 0.8)'; // matches slate-50
              ctx.fillRect(PosX - textWidth/2 - 2, PosY - 6/globalScale, textWidth + 4, 12/globalScale);
              
              ctx.fillStyle = '#94A3B8';
              ctx.fillText(link.type, PosX, PosY);
            }}
            onEngineStop={handleEngineStop}
          />
        )}
      </div>
    </div>
  );
}