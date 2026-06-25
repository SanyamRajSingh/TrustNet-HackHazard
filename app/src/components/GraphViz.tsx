import { useEffect, useRef } from 'react';
import { Network } from 'lucide-react';

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
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    if (!graphData || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;

    // Build node positions with force simulation
    const nodeMap = new Map<number, { x: number; y: number; vx: number; vy: number; node: GraphNode }>();
    graphData.nodes.forEach((n, i) => {
      const angle = (i / graphData.nodes.length) * Math.PI * 2;
      const dist = Math.min(w, h) * 0.25;
      nodeMap.set(n.id, {
        x: w / 2 + Math.cos(angle) * dist,
        y: h / 2 + Math.sin(angle) * dist,
        vx: 0, vy: 0,
        node: n,
      });
    });

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

    function getNodeLabel(n: GraphNode): string {
      const p = n.properties;
      return p.value || p.name || n.labels[0] || String(n.id);
    }

    let tickCount = 0;
    const MAX_TICKS = 300;

    function tick() {
      if (tickCount >= MAX_TICKS) {
        // Just draw the final frame and stop
        animRef.current = 0;
        return;
      }
      tickCount++;

      // Repulsion
      const nodes = Array.from(nodeMap.values());
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = b.x - a.x, dy = b.y - a.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 2000 / (dist * dist);
          const fx = (dx / dist) * force, fy = (dy / dist) * force;
          a.vx -= fx; a.vy -= fy;
          b.vx += fx; b.vy += fy;
        }
      }

      // Attraction (edges)
      graphData.relationships.forEach((rel) => {
        const a = nodeMap.get(rel.start), b = nodeMap.get(rel.end);
        if (!a || !b) return;
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = dist * 0.001;
        const fx = (dx / dist) * force, fy = (dy / dist) * force;
        a.vx += fx; a.vy += fy;
        b.vx -= fx; b.vy -= fy;
      });

      // Center gravity
      nodes.forEach((n) => {
        n.vx += (w / 2 - n.x) * 0.005;
        n.vy += (h / 2 - n.y) * 0.005;
        n.vx *= 0.85;
        n.vy *= 0.85;
        n.x += n.vx;
        n.y += n.vy;
        n.x = Math.max(30, Math.min(w - 30, n.x));
        n.y = Math.max(30, Math.min(h - 30, n.y));
      });

      // Draw
      ctx!.clearRect(0, 0, w, h);

      // Edges
      graphData.relationships.forEach((rel) => {
        const a = nodeMap.get(rel.start), b = nodeMap.get(rel.end);
        if (!a || !b) return;
        ctx!.beginPath();
        ctx!.strokeStyle = rel.type === 'IMPERSONATES' ? '#EF4444' :
                          rel.type === 'BELONGS_TO_RING' ? '#DC2626' :
                          rel.type === 'REPORTED_WITH' ? '#6366F1' : '#CBD5E1';
        ctx!.lineWidth = rel.type === 'IMPERSONATES' ? 2.5 : 1.5;
        if (rel.type === 'IMPERSONATES' || rel.type === 'BELONGS_TO_RING') {
          ctx!.setLineDash([5, 5]);
        } else {
          ctx!.setLineDash([]);
        }
        ctx!.moveTo(a.x, a.y);
        ctx!.lineTo(b.x, b.y);
        ctx!.stroke();
        ctx!.setLineDash([]);

        // Edge label
        const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        ctx!.fillStyle = '#94A3B8';
        ctx!.font = '9px sans-serif';
        ctx!.textAlign = 'center';
        ctx!.fillText(rel.type, mx, my - 4);
      });

      // Nodes
      nodes.forEach((n) => {
        const color = getNodeColor(n.node.labels, n.node.properties);
        const isFlagged = n.node.properties.is_flagged;

        // Glow for flagged
        if (isFlagged) {
          ctx!.beginPath();
          ctx!.arc(n.x, n.y, 22, 0, Math.PI * 2);
          ctx!.fillStyle = 'rgba(239, 68, 68, 0.15)';
          ctx!.fill();
        }

        ctx!.beginPath();
        ctx!.arc(n.x, n.y, 14, 0, Math.PI * 2);
        ctx!.fillStyle = color;
        ctx!.fill();
        ctx!.strokeStyle = '#fff';
        ctx!.lineWidth = 2.5;
        ctx!.stroke();

        // Label
        const label = getNodeLabel(n.node);
        ctx!.fillStyle = '#1E293B';
        ctx!.font = '11px sans-serif';
        ctx!.textAlign = 'center';
        ctx!.fillText(label.length > 20 ? label.slice(0, 20) + '...' : label, n.x, n.y + 28);

        // Type label
        ctx!.fillStyle = '#64748B';
        ctx!.font = '9px sans-serif';
        ctx!.fillText(n.node.labels[0] || '', n.x, n.y + 40);
      });

      animRef.current = requestAnimationFrame(tick);
    }

    tick();

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [graphData]);

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-8 text-center">
        <Network className="h-8 w-8 text-slate-300 mx-auto mb-2" />
        <p className="text-sm text-slate-500">No graph connections found for this entity yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-slate-900">Connection Graph</h3>
        {graphData.nodes.some(n => n.properties.is_flagged || n.labels.includes('ScamRing')) && (
          <span className="text-xs px-2 py-1 rounded-full bg-red-100 text-red-700 font-medium">
            Connected to flagged entities
          </span>
        )}
      </div>
      <div className="rounded-xl border border-slate-200 overflow-hidden">
        <canvas
          ref={canvasRef}
          style={{ width: '100%', height: '400px' }}
          className="cursor-grab active:cursor-grabbing"
        />
      </div>
      <div className="flex flex-wrap gap-3 text-xs text-slate-500">
        {[
          { color: '#6366F1', label: 'Domain' },
          { color: '#8B5CF6', label: 'Email' },
          { color: '#06B6D4', label: 'Phone' },
          { color: '#10B981', label: 'Company' },
          { color: '#DC2626', label: 'Flagged / Scam Ring' },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}