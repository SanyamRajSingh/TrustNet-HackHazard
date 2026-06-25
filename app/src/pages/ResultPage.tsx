import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router';
import { ArrowLeft, ExternalLink, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import CategoryBreakdown from '../components/CategoryBreakdown';
import EvidenceList from '../components/EvidenceList';
import GraphViz from '../components/GraphViz';
import HindiReport from '../components/HindiReport';
import VerdictCard from '../components/VerdictCard';
import { useStore } from '../store/useStore';

export default function ResultPage() {
  const { id: _id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentResult, isLoading } = useStore();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  if (isLoading && !currentResult) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="h-10 w-10 animate-spin text-indigo-600 mx-auto" />
          <p className="text-slate-600 font-medium">Analyzing your job offer...</p>
          <p className="text-sm text-slate-400">Checking MCA records, WHOIS, DNS, and scam databases</p>
        </div>
      </div>
    );
  }

  if (!currentResult) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-slate-600">No investigation result found.</p>
          <Button onClick={() => navigate('/')} variant="outline">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Start New Investigation
          </Button>
        </div>
      </div>
    );
  }

  const result = currentResult;

  return (
    <div className="min-h-screen py-6 sm:py-10">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        {/* Back button */}
        <Button
          variant="ghost"
          className="mb-6 text-slate-600 hover:text-slate-900"
          onClick={() => navigate('/')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          New Investigation
        </Button>

        {/* Verdict Card */}
        <div className="mb-6">
          <VerdictCard result={result} />
        </div>

        {/* Hindi Report */}
        {result.hindi_explanation && (
          <div className="mb-6">
            <HindiReport
              hindiExplanation={result.hindi_explanation}
              verdict={result.verdict}
              trustScore={result.trust_score}
            />
          </div>
        )}

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <CategoryBreakdown result={result} />
          <EvidenceList evidence={result.evidence} />
        </div>

        {/* Graph Visualization */}
        {result.graph_connections && result.graph_connections.nodes && result.graph_connections.nodes.length > 0 && (
          <div className="mb-6">
            <GraphViz graphData={result.graph_connections} />
          </div>
        )}

        {/* Extracted Entities Summary */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 mb-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Extracted Information</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { label: 'Company', value: result.entities.company_name },
              { label: 'Email', value: result.entities.email },
              { label: 'Phone', value: result.entities.phone_number },
              { label: 'Website', value: result.entities.website_url },
              { label: 'Recruiter', value: result.entities.recruiter_name },
              { label: 'Salary', value: result.entities.salary_mentioned ? `Rs. ${result.entities.salary_mentioned.toLocaleString('en-IN')}/month` : null },
              { label: 'Fee Requested', value: result.entities.fee_amount ? `Rs. ${result.entities.fee_amount.toLocaleString('en-IN')}` : null },
              { label: 'Language', value: result.entities.language_detected },
            ].map((item) => (
              item.value ? (
                <div key={item.label} className="flex justify-between items-center py-2 px-3 rounded-lg bg-slate-50">
                  <span className="text-xs text-slate-500">{item.label}</span>
                  <span className="text-sm font-medium text-slate-900 truncate ml-4">{item.value}</span>
                </div>
              ) : null
            ))}
          </div>

          {result.entities.red_flags && result.entities.red_flags.length > 0 && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <p className="text-xs text-slate-500 mb-2">Red Flags Detected</p>
              <div className="flex flex-wrap gap-2">
                {result.entities.red_flags.map((flag, i) => (
                  <span key={i} className="text-xs px-2.5 py-1 rounded-full bg-red-50 text-red-700 border border-red-200">
                    {flag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Blockchain verification */}
        {result.blockchain_tx_hash && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 mb-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center">
                <ExternalLink className="h-4 w-4 text-white" />
              </div>
              <div>
                <p className="text-sm font-medium text-emerald-800">Recorded on Base Blockchain</p>
                <p className="text-xs text-emerald-600 font-mono truncate max-w-xs">
                  {result.blockchain_tx_hash}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 mb-10">
          <Button
            onClick={() => navigate('/')}
            className="flex-1 h-12 bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-semibold"
          >
            Investigate Another Offer
          </Button>
          <Button
            variant="outline"
            onClick={() => navigate('/community')}
            className="h-12 border-slate-200"
          >
            Submit Community Report
          </Button>
        </div>
      </div>
    </div>
  );
}