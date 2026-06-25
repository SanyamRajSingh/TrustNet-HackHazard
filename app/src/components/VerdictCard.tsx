import { AlertTriangle, CheckCircle, Info, ShieldAlert, ShieldCheck, XCircle, Building, Mail, Phone, Link, Briefcase, IndianRupee } from 'lucide-react';
import type { InvestigationResult } from '../store/useStore';

interface Props {
  result: InvestigationResult;
}

const VERDICT_ICONS: Record<string, React.ElementType> = {
  HIGH_RISK: XCircle,
  SUSPICIOUS: ShieldAlert,
  UNVERIFIED: Info,
  LIKELY_LEGITIMATE: ShieldCheck,
  VERIFIED: CheckCircle,
  INSUFFICIENT_DATA: Info,
};

export default function VerdictCard({ result }: Props) {
  const Icon = VERDICT_ICONS[result.verdict] || Info;
  const score = result.trust_score;

  // Calculate stroke dash for circular gauge
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const strokeDash = (score / 100) * circumference;

  return (
    <div
      className="rounded-2xl border-2 overflow-hidden"
      style={{
        borderColor: result.verdict_color,
        backgroundColor: result.verdict === 'HIGH_RISK' ? '#FEF2F2' : result.verdict === 'SUSPICIOUS' ? '#FFFBEB' : result.verdict === 'VERIFIED' ? '#F0FDF4' : result.verdict === 'LIKELY_LEGITIMATE' ? '#EFF6FF' : '#F8FAFC',
      }}
    >
      {/* Header */}
      <div className="px-6 py-4 flex items-center gap-3" style={{ backgroundColor: result.verdict_color }}>
        <Icon className="h-6 w-6 text-white" />
        <div>
          <h2 className="text-lg font-bold text-white">{result.verdict_label}</h2>
          <p className="text-xs text-white/80 capitalize">{result.verdict.replace(/_/g, ' ')}</p>
        </div>
      </div>

      {/* Body */}
      <div className="px-6 py-6 flex flex-col sm:flex-row items-center gap-6">
        {/* Circular Score Gauge */}
        <div className="relative flex-shrink-0">
          <svg width="180" height="180" className="transform -rotate-90">
            <circle cx="90" cy="90" r={radius} fill="none" stroke="#E2E8F0" strokeWidth="12" />
            <circle
              cx="90" cy="90" r={radius}
              fill="none"
              stroke={result.verdict_color}
              strokeWidth="12"
              strokeLinecap="round"
              strokeDasharray={`${strokeDash} ${circumference}`}
              className="transition-all duration-1000 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-4xl font-extrabold text-slate-900">{score}</span>
            <span className="text-xs text-slate-500">/ 100</span>
          </div>
        </div>

        {/* Score Details */}
        <div className="flex-1 space-y-3 w-full">
          <div>
            <p className="text-sm text-slate-600 mb-1">Confidence</p>
            <div className="w-full bg-slate-200 rounded-full h-2.5">
              <div
                className="h-2.5 rounded-full transition-all duration-700"
                style={{
                  width: `${result.confidence_score}%`,
                  backgroundColor: result.verdict_color,
                }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-1">{result.confidence_score}% data confidence</p>
          </div>

          {result.entities.fee_amount && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-50 border border-red-200">
              <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0" />
              <span className="text-sm font-medium text-red-700">
                Fee Requested: Rs. {result.entities.fee_amount.toLocaleString('en-IN')}
              </span>
            </div>
          )}

          {result.graph_connections && result.graph_connections.rings.length > 0 && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-orange-50 border border-orange-200">
              <ShieldAlert className="h-4 w-4 text-orange-500 flex-shrink-0" />
              <span className="text-sm font-medium text-orange-700">
                Connected to: {result.graph_connections.rings.join(', ')}
              </span>
            </div>
          )}

          {result.processing_ms && (
            <p className="text-xs text-slate-400">Analyzed in {result.processing_ms}ms</p>
          )}
        </div>
      </div>

      {/* Extracted Entities */}
      <div className="px-6 py-4 border-t border-slate-200 bg-white/50">
        <h3 className="text-sm font-semibold text-slate-700 mb-3 uppercase tracking-wider">
          Extracted Information
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {result.entities.company_name && (
            <div className="flex items-start gap-2">
              <Building className="h-4 w-4 text-slate-400 mt-0.5" />
              <div className="text-sm">
                <p className="text-slate-500 text-xs">Company</p>
                <p className="font-medium text-slate-900 truncate" title={result.entities.company_name}>{result.entities.company_name}</p>
              </div>
            </div>
          )}
          {result.entities.job_title && (
            <div className="flex items-start gap-2">
              <Briefcase className="h-4 w-4 text-slate-400 mt-0.5" />
              <div className="text-sm">
                <p className="text-slate-500 text-xs">Job Title</p>
                <p className="font-medium text-slate-900 truncate" title={result.entities.job_title}>{result.entities.job_title}</p>
              </div>
            </div>
          )}
          {result.entities.salary_mentioned && (
            <div className="flex items-start gap-2">
              <IndianRupee className="h-4 w-4 text-slate-400 mt-0.5" />
              <div className="text-sm">
                <p className="text-slate-500 text-xs">Salary</p>
                <p className="font-medium text-slate-900 truncate">₹ {result.entities.salary_mentioned.toLocaleString('en-IN')}</p>
              </div>
            </div>
          )}
          {result.entities.email && (
            <div className="flex items-start gap-2">
              <Mail className="h-4 w-4 text-slate-400 mt-0.5" />
              <div className="text-sm overflow-hidden">
                <p className="text-slate-500 text-xs">Email</p>
                <p className="font-medium text-slate-900 truncate" title={result.entities.email}>{result.entities.email}</p>
              </div>
            </div>
          )}
          {result.entities.phone_number && (
            <div className="flex items-start gap-2">
              <Phone className="h-4 w-4 text-slate-400 mt-0.5" />
              <div className="text-sm">
                <p className="text-slate-500 text-xs">Phone</p>
                <p className="font-medium text-slate-900 truncate">{result.entities.phone_number}</p>
              </div>
            </div>
          )}
          {result.entities.website_url && (
            <div className="flex items-start gap-2">
              <Link className="h-4 w-4 text-slate-400 mt-0.5" />
              <div className="text-sm overflow-hidden">
                <p className="text-slate-500 text-xs">Website</p>
                <a href={result.entities.website_url.startsWith('http') ? result.entities.website_url : `https://${result.entities.website_url}`} target="_blank" rel="noopener noreferrer" className="font-medium text-blue-600 hover:underline truncate block" title={result.entities.website_url}>
                  {result.entities.website_url.replace(/^https?:\/\//, '')}
                </a>
              </div>
            </div>
          )}
          
          {/* Empty state fallback if nothing is extracted */}
          {!result.entities.company_name && !result.entities.job_title && !result.entities.salary_mentioned && !result.entities.email && !result.entities.phone_number && !result.entities.website_url && (
            <div className="col-span-full text-sm text-slate-500 italic">
              No specific entities could be reliably extracted from the text.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}