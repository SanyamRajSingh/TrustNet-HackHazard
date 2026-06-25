import { AlertTriangle, CheckCircle2, Info, ShieldAlert } from 'lucide-react';
import type { EvidenceItem } from '../store/useStore';

interface Props {
  evidence: EvidenceItem[];
}

const SEVERITY_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  critical: { icon: ShieldAlert, color: 'text-red-600', bg: 'bg-red-50 border-red-200', label: 'Critical' },
  warning: { icon: AlertTriangle, color: 'text-amber-600', bg: 'bg-amber-50 border-amber-200', label: 'Warning' },
  info: { icon: Info, color: 'text-blue-600', bg: 'bg-blue-50 border-blue-200', label: 'Info' },
  positive: { icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50 border-emerald-200', label: 'Positive' },
};

export default function EvidenceList({ evidence }: Props) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-lg font-semibold text-slate-900">Evidence Details</h3>
      <div className="space-y-2">
        {evidence.map((item, i) => {
          const config = SEVERITY_CONFIG[item.severity] || SEVERITY_CONFIG.info;
          const Icon = config.icon;
          return (
            <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border ${config.bg}`}>
              <Icon className={`h-5 w-5 ${config.color} flex-shrink-0 mt-0.5`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-medium text-slate-500">{item.category}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${config.color} bg-white/80`}>
                    {config.label}
                  </span>
                </div>
                <p className="text-sm font-medium text-slate-800">{item.finding}</p>
                {item.details && (
                  <p className="text-xs text-slate-500 mt-1">{item.details}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}