import { FileText } from 'lucide-react';

interface Props {
  hindiExplanation: string | null;
  verdict: string;
  trustScore: number;
}

export default function HindiReport({ hindiExplanation, verdict, trustScore }: Props) {
  if (!hindiExplanation) return null;

  const bgColors: Record<string, string> = {
    HIGH_RISK: 'bg-red-50 border-red-200',
    SUSPICIOUS: 'bg-amber-50 border-amber-200',
    UNVERIFIED: 'bg-yellow-50 border-yellow-200',
    LIKELY_LEGITIMATE: 'bg-blue-50 border-blue-200',
    VERIFIED: 'bg-emerald-50 border-emerald-200',
    INSUFFICIENT_DATA: 'bg-slate-50 border-slate-200',
  };

  return (
    <div className={`rounded-xl border p-5 ${bgColors[verdict] || bgColors.UNVERIFIED}`}>
      <div className="flex items-center gap-2 mb-3">
        <FileText className="h-5 w-5 text-indigo-600" />
        <h3 className="font-semibold text-slate-900">Report in Hindi</h3>
        <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium">
          Sarvam AI
        </span>
      </div>
      <p className="text-slate-800 text-base leading-relaxed font-medium" style={{ fontFamily: `'Noto Sans Devanagari', 'Noto Sans', sans-serif` }}>
        {hindiExplanation}
      </p>
      <div className="mt-3 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-indigo-500" />
        <span className="text-xs text-slate-500">
          Trust Score: {trustScore}/100 — {verdict.replace(/_/g, ' ')}
        </span>
      </div>
    </div>
  );
}