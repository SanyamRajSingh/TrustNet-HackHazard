import { useState } from 'react';
import { Building2, Globe, Mail, MessageSquare, Users, ChevronDown, ChevronUp } from 'lucide-react';
import type { InvestigationResult } from '../store/useStore';

interface Props {
  result: InvestigationResult;
}

const CATEGORY_CONFIG: Record<string, { icon: React.ElementType; label: string; description: string }> = {
  identity_company: { icon: Building2, label: 'Identity & Company', description: 'MCA registration, company age, director lookup' },
  domain_infrastructure: { icon: Globe, label: 'Domain Intelligence', description: 'WHOIS age, registrar, blacklist status' },
  communication_channel: { icon: Mail, label: 'Communication Channel', description: 'Email auth, SPF/DKIM/DMARC, disposable check' },
  content_red_flags: { icon: MessageSquare, label: 'Content & Red Flags', description: 'Fee requests, urgency, salary analysis' },
  community_intelligence: { icon: Users, label: 'Community Intelligence', description: 'Graph connections, community reports, rings' },
};

export default function CategoryBreakdown({ result }: Props) {
  const categories = Object.entries(result.category_scores || {});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggleExpand = (key: string) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-slate-900">Category Breakdown</h3>
      {categories.map(([key, data]) => {
        const config = CATEGORY_CONFIG[key] || { icon: Globe, label: key, description: '' };
        const Icon = config.icon;
        const score = data?.score ?? 0;
        const weighted = data?.weighted_score ?? 0;
        const weight = data?.weight ?? 0;
        const isExpanded = expanded[key];

        const barColor = score >= 70 ? 'bg-emerald-500' : score >= 45 ? 'bg-amber-500' : score >= 25 ? 'bg-orange-500' : 'bg-red-500';

        const visibleEvidence = isExpanded ? data?.evidence : data?.evidence?.slice(0, 3);
        const hasMore = data?.evidence && data.evidence.length > 3;

        return (
          <div key={key} className="p-4 rounded-xl bg-white border border-slate-100">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 rounded-lg bg-slate-50 flex items-center justify-center">
                <Icon className="h-4.5 w-4.5 text-slate-600" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-sm text-slate-900">{config.label}</span>
                  <span className="text-sm font-bold text-slate-700">{score}/100</span>
                </div>
                <p className="text-xs text-slate-400">{config.description}</p>
              </div>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2.5 mb-2">
              <div
                className={`h-2.5 rounded-full transition-all duration-700 ${barColor}`}
                style={{ width: `${score}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-400">
              <span>Weight: {(weight * 100).toFixed(0)}%</span>
              <span>Weighted: {weighted.toFixed(1)}</span>
            </div>

            {/* Evidence items */}
            {visibleEvidence && visibleEvidence.length > 0 && (
              <div className="mt-3 space-y-1.5 pt-3 border-t border-slate-50">
                {visibleEvidence.map((e: any, i: number) => (
                  <div key={i} className="flex items-start gap-2 text-xs">
                    <div className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${
                      e.severity === 'critical' ? 'bg-red-500' :
                      e.severity === 'warning' ? 'bg-amber-500' :
                      e.severity === 'positive' ? 'bg-emerald-500' : 'bg-blue-400'
                    }`} />
                    <span className="text-slate-600">{e.finding}</span>
                  </div>
                ))}
                
                {hasMore && (
                  <button 
                    onClick={() => toggleExpand(key)}
                    className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 font-medium mt-2 focus:outline-none"
                  >
                    {isExpanded ? (
                      <><ChevronUp className="w-3 h-3" /> Show less</>
                    ) : (
                      <><ChevronDown className="w-3 h-3" /> Show {data.evidence.length - 3} more finding{data.evidence.length - 3 !== 1 ? 's' : ''}</>
                    )}
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}