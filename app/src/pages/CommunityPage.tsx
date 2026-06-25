import { useState } from 'react';
import { AlertTriangle, CheckCircle, FileText, Loader2, Send, ShieldAlert, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

export default function CommunityPage() {
  const [form, setForm] = useState({
    entity: '',
    reportType: 'SCAM',
    lossAmount: '',
    description: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.entity || !form.description) {
      toast.error('Please fill in all required fields');
      return;
    }
    setSubmitting(true);
    // Simulate API call
    await new Promise(r => setTimeout(r, 1000));
    toast.success('Report submitted successfully!');
    setSubmitting(false);
    setForm({ entity: '', reportType: 'SCAM', lossAmount: '', description: '' });
  };

  return (
    <div className="min-h-screen py-8 sm:py-12">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10">
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 flex items-center justify-center mx-auto mb-4">
            <Users className="h-7 w-7 text-indigo-600" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Community Reports</h1>
          <p className="text-slate-600">
            Help protect other job seekers by reporting suspicious companies, emails, and phone numbers.
          </p>
        </div>

        {/* Submit Form */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 mb-8">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5 text-indigo-600" />
            Submit a Report
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Entity (company, email, phone, or website) *
              </label>
              <input
                type="text"
                value={form.entity}
                onChange={(e) => setForm({ ...form, entity: e.target.value })}
                placeholder="e.g., infosys-careers.in"
                className="w-full px-4 py-2.5 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Report Type</label>
              <div className="flex gap-3">
                {[
                  { value: 'SCAM', label: 'Scam', color: 'bg-red-50 border-red-200 text-red-700' },
                  { value: 'SUSPICIOUS', label: 'Suspicious', color: 'bg-amber-50 border-amber-200 text-amber-700' },
                  { value: 'LEGITIMATE', label: 'Legitimate', color: 'bg-emerald-50 border-emerald-200 text-emerald-700' },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setForm({ ...form, reportType: opt.value })}
                    className={`flex-1 py-2.5 rounded-lg border text-sm font-medium transition-all ${
                      form.reportType === opt.value ? opt.color : 'bg-white border-slate-200 text-slate-600'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Loss Amount (INR, optional)
              </label>
              <input
                type="number"
                value={form.lossAmount}
                onChange={(e) => setForm({ ...form, lossAmount: e.target.value })}
                placeholder="e.g., 2500"
                className="w-full px-4 py-2.5 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Description *
              </label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Describe your experience..."
                rows={4}
                className="w-full px-4 py-2.5 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-y"
              />
            </div>

            <Button
              onClick={handleSubmit}
              disabled={submitting}
              className="w-full h-11 bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-semibold"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
              Submit Report
            </Button>
          </div>
        </div>

        {/* Recent Reports */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900">Recent Community Reports</h2>
          {[
            { entity: 'infosys-careers.in', type: 'SCAM', loss: 2499, date: '2 hours ago', desc: 'Asked for registration fee of Rs. 2,499' },
            { entity: 'wiprojobs24.com', type: 'SCAM', loss: 3500, date: '5 hours ago', desc: 'Fake Wipro recruitment portal' },
            { entity: 'tcs.com', type: 'LEGITIMATE', loss: null, date: '1 day ago', desc: 'Verified legitimate TCS careers page' },
          ].map((report, i) => (
            <div key={i} className="p-4 rounded-xl border border-slate-100 bg-white">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  {report.type === 'SCAM' ? (
                    <ShieldAlert className="h-5 w-5 text-red-500 flex-shrink-0" />
                  ) : report.type === 'SUSPICIOUS' ? (
                    <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0" />
                  ) : (
                    <CheckCircle className="h-5 w-5 text-emerald-500 flex-shrink-0" />
                  )}
                  <div>
                    <p className="font-medium text-slate-900">{report.entity}</p>
                    <p className="text-sm text-slate-500">{report.desc}</p>
                  </div>
                </div>
                <div className="text-right flex-shrink-0 ml-3">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                    report.type === 'SCAM' ? 'bg-red-50 text-red-700' :
                    report.type === 'SUSPICIOUS' ? 'bg-amber-50 text-amber-700' :
                    'bg-emerald-50 text-emerald-700'
                  }`}>
                    {report.type}
                  </span>
                  <p className="text-xs text-slate-400 mt-1">{report.date}</p>
                </div>
              </div>
              {report.loss && (
                <p className="mt-2 text-xs text-red-600 font-medium">Reported loss: Rs. {report.loss.toLocaleString('en-IN')}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

