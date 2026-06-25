import { useParams } from 'react-router';
import { AlertTriangle, ArrowLeft, CheckCircle, Clock, ExternalLink, Globe, Hash, Shield, ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router';

export default function EntityPage() {
  const { hash } = useParams<{ hash: string }>();

  // Demo data - in production would fetch from API
  const entity = {
    entity_type: 'domain',
    entity_value: 'infosys-careers.in',
    entity_hash: hash || '',
    first_seen_at: '2024-01-15T08:30:00Z',
    investigation_count: 23,
    aggregate_score: 12,
    on_chain: true,
    ring_name: 'Infosys Impersonation Ring',
    blockchain_tx: '0xabc123...def789',
  };

  const investigations = [
    { id: '1', verdict: 'HIGH_RISK', score: 15, date: '2024-01-15', fee: 2499 },
    { id: '2', verdict: 'HIGH_RISK', score: 12, date: '2024-01-14', fee: 2999 },
    { id: '3', verdict: 'HIGH_RISK', score: 18, date: '2024-01-13', fee: 2499 },
  ];

  return (
    <div className="min-h-screen py-8 sm:py-12">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <Link to="/">
          <Button variant="ghost" className="mb-6 text-slate-600">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </Link>

        {/* Entity Header */}
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 mb-6">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-xl bg-red-100 flex items-center justify-center flex-shrink-0">
              <Globe className="h-7 w-7 text-red-600" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h1 className="text-2xl font-bold text-slate-900">{entity.entity_value}</h1>
                <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-xs font-medium">
                  HIGH RISK
                </span>
              </div>
              <p className="text-sm text-slate-600">
                Part of the <span className="font-semibold text-red-700">{entity.ring_name}</span>
              </p>
              <div className="flex flex-wrap gap-3 mt-3">
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <Shield className="h-3.5 w-3.5" />
                  Score: {entity.aggregate_score}/100
                </span>
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <Clock className="h-3.5 w-3.5" />
                  First seen: {new Date(entity.first_seen_at).toLocaleDateString('en-IN')}
                </span>
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <Hash className="h-3.5 w-3.5" />
                  {entity.investigation_count} investigations
                </span>
              </div>
            </div>
          </div>

          {entity.on_chain && entity.blockchain_tx && (
            <div className="mt-4 pt-4 border-t border-red-200 flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-600" />
              <span className="text-sm text-emerald-700 font-medium">Recorded on Base Blockchain</span>
              <a href={`https://sepolia.basescan.org/tx/${entity.blockchain_tx}`} target="_blank" rel="noopener noreferrer"
                 className="text-sm text-indigo-600 hover:underline flex items-center gap-1 ml-auto">
                View <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          )}
        </div>

        {/* Investigation History */}
        <div className="space-y-3 mb-8">
          <h2 className="text-lg font-semibold text-slate-900">Investigation History</h2>
          {investigations.map((inv) => (
            <div key={inv.id} className="p-4 rounded-xl border border-slate-100 bg-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <ShieldAlert className="h-5 w-5 text-red-500" />
                  <div>
                    <p className="font-medium text-slate-900">Investigation #{inv.id}</p>
                    <p className="text-xs text-slate-500">{inv.date}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold text-red-600">{inv.score}/100</span>
                  <p className="text-xs text-red-500">Fee: Rs. {inv.fee?.toLocaleString('en-IN')}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Ring Information */}
        <div className="rounded-xl border border-orange-200 bg-orange-50 p-5">
          <div className="flex items-center gap-3 mb-3">
            <AlertTriangle className="h-5 w-5 text-orange-600" />
            <h3 className="font-semibold text-orange-800">Scam Ring Alert</h3>
          </div>
          <p className="text-sm text-orange-700 mb-3">
            This domain is part of the <strong>Infosys Impersonation Ring</strong>, a known scam operation
            that impersonates legitimate companies to extract registration fees from job seekers.
          </p>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-3 rounded-lg bg-white/60">
              <p className="text-xl font-bold text-orange-800">22</p>
              <p className="text-xs text-orange-600">Connected Entities</p>
            </div>
            <div className="p-3 rounded-lg bg-white/60">
              <p className="text-xl font-bold text-orange-800">23</p>
              <p className="text-xs text-orange-600">Victims Reported</p>
            </div>
            <div className="p-3 rounded-lg bg-white/60">
              <p className="text-xl font-bold text-orange-800">Active</p>
              <p className="text-xs text-orange-600">Ring Status</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}