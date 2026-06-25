import { useNavigate } from 'react-router';
import { AlertTriangle, BarChart3, Globe, Mic, Shield, Type, Upload, Users } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import HeroInput from '../components/HeroInput';
import StatsCounter from '../components/StatsCounter';
import VoiceRecorder from '../components/VoiceRecorder';
import { api } from '../lib/api';
import { useStore, type InvestigationResult } from '../store/useStore';

export default function HomePage() {
  const navigate = useNavigate();
  const { isLoading, setIsLoading, setCurrentResult, addToHistory } = useStore();

  const handleInvestigate = async (rawInput: string, inputType: string) => {
    if (!rawInput.trim() || rawInput.trim().length < 10) {
      toast.error('Please provide at least 10 characters of job offer text');
      return;
    }

    setIsLoading(true);
    try {
      const result = await api.investigate({
        raw_input: rawInput,
        input_type: inputType as 'paste' | 'screenshot' | 'pdf' | 'voice',
      }) as InvestigationResult;
      setCurrentResult(result);
      addToHistory(result);
      navigate(`/result/${result.id}`);
    } catch (err: any) {
      toast.error(err.message || 'Investigation failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVoiceInvestigate = async (audioBase64: string) => {
    setIsLoading(true);
    try {
      const result = await api.voiceInvestigate({
        audio_base64: audioBase64,
        mime_type: 'audio/wav',
      }) as InvestigationResult;
      setCurrentResult(result);
      addToHistory(result);
      navigate(`/result/${result.id}`);
    } catch (err: any) {
      toast.error(err.message || 'Voice investigation failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-12 sm:py-20 lg:py-24">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-100/60 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-sm font-medium mb-6">
              <AlertTriangle className="h-4 w-4" />
              <span>Over 1 lakh Indians lost money to fake job offers in 2023</span>
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight mb-4">
              Is Your Job Offer{' '}
              <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
                Real or Fake?
              </span>
            </h1>
            <p className="text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto mb-2">
              Paste any job offer message, upload a screenshot, or speak in Hindi.
              TrustNet investigates in under 8 seconds.
            </p>
            <p className="text-sm text-slate-400">Supports English, Hindi, Hinglish, Tamil, Telugu</p>
          </div>

          {/* Input Section */}
          <div className="max-w-3xl mx-auto">
            <Tabs defaultValue="text" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-4">
                <TabsTrigger value="text" className="gap-2">
                  <Type className="h-4 w-4" /> Text / Paste
                </TabsTrigger>
                <TabsTrigger value="voice" className="gap-2">
                  <Mic className="h-4 w-4" /> Voice (Hindi)
                </TabsTrigger>
              </TabsList>
              <TabsContent value="text">
                <HeroInput onSubmit={handleInvestigate} isLoading={isLoading} />
              </TabsContent>
              <TabsContent value="voice">
                <VoiceRecorder onSubmit={handleVoiceInvestigate} isLoading={isLoading} />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <StatsCounter />

      {/* How It Works */}
      <section className="py-16 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-center text-slate-900 mb-12">
            How TrustNet Works
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: Type,
                title: 'Paste or Speak',
                desc: 'Paste a WhatsApp message, upload a screenshot, or speak in Hindi.',
                color: 'bg-blue-50 text-blue-600',
              },
              {
                icon: Globe,
                title: 'AI Extraction',
                desc: 'Sarvam AI extracts companies, emails, phone numbers, and fees from Indian languages.',
                color: 'bg-violet-50 text-violet-600',
              },
              {
                icon: Shield,
                title: 'Multi-Source Verify',
                desc: 'We check MCA records, WHOIS, DNS, Google Safe Browsing, and scam databases in parallel.',
                color: 'bg-emerald-50 text-emerald-600',
              },
              {
                icon: BarChart3,
                title: 'Trust Score',
                desc: 'Get a transparent 0-100 score with Hindi explanation and blockchain-verified record.',
                color: 'bg-amber-50 text-amber-600',
              },
            ].map((step, i) => (
              <div key={i} className="relative p-6 rounded-2xl border border-slate-100 bg-slate-50/50 hover:shadow-lg transition-shadow">
                <div className={`w-12 h-12 rounded-xl ${step.color} flex items-center justify-center mb-4`}>
                  <step.icon className="h-6 w-6" />
                </div>
                <div className="absolute top-4 right-4 text-2xl font-bold text-slate-200">{i + 1}</div>
                <h3 className="font-semibold text-slate-900 mb-2">{step.title}</h3>
                <p className="text-sm text-slate-500">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-16 bg-slate-50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-center text-slate-900 mb-12">
            Built for Indian Job Seekers
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Users,
                title: 'MCA Verification',
                desc: 'Checks company registration against Ministry of Corporate Affairs records.',
              },
              {
                icon: Globe,
                title: 'Domain Intelligence',
                desc: 'Analyzes domain age, registrar, and impersonation patterns via WHOIS.',
              },
              {
                icon: Shield,
                title: 'Email Authentication',
                desc: 'Verifies SPF, DKIM, DMARC records. Flags Gmail/Yahoo for corporate contacts.',
              },
              {
                icon: BarChart3,
                title: 'Graph-Powered Rings',
                desc: 'Neo4j graph reveals connected scam infrastructure and impersonation rings.',
              },
              {
                icon: Upload,
                title: 'Blockchain Registry',
                desc: 'Confirmed scam entities are written to Base blockchain for public transparency.',
              },
              {
                icon: Mic,
                title: 'Voice Input (Hindi)',
                desc: 'Speak your job offer details in Hindi. Our AI transcribes and investigates.',
              },
            ].map((feat, i) => (
              <div key={i} className="p-6 rounded-2xl bg-white border border-slate-100 hover:shadow-md transition-shadow">
                <feat.icon className="h-8 w-8 text-indigo-600 mb-4" />
                <h3 className="font-semibold text-slate-900 mb-2">{feat.title}</h3>
                <p className="text-sm text-slate-500">{feat.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}