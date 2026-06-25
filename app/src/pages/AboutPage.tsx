import { ArrowRight, BarChart3, Brain, Globe, Mic, Network, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router';

const techStack = [
  { category: 'Frontend', items: ['React 18 + Vite', 'Tailwind CSS', 'Zustand State', 'D3.js Graph Viz', 'Noto Sans Devanagari'] },
  { category: 'Backend', items: ['FastAPI (Python 3.11)', 'SQLAlchemy 2.0 (async)', 'Celery + Redis', 'JWT Authentication', 'Pydantic Validation'] },
  { category: 'Databases', items: ['PostgreSQL 16 (JSONB)', 'Neo4j 5 (AuraDB)', 'Redis 7 (Upstash)', 'Full-text Search'] },
  { category: 'AI & APIs', items: ['Sarvam AI (NLP + Voice)', 'WHOIS XML API', 'Google Safe Browsing', 'PhishTank', 'NumVerify'] },
  { category: 'Blockchain', items: ['Base Sepolia (Coinbase L2)', 'Solidity 0.8.20', 'Ethers.js v6', 'EIP-191 Signatures'] },
  { category: 'DevOps', items: ['Docker + Docker Compose', 'Render.com', 'GitHub Actions', 'Sentry Monitoring'] },
];

const processFlow = [
  { step: 1, title: 'Input', desc: 'User pastes job offer text, uploads screenshot, or speaks in Hindi', icon: Mic },
  { step: 2, title: 'Extraction', desc: 'Sarvam AI extracts entities from Hinglish/Hindi/English mix', icon: Brain },
  { step: 3, title: 'Verification', desc: 'Parallel async calls to MCA, WHOIS, DNS, Safe Browsing, PhishTank', icon: Globe },
  { step: 4, title: 'Graph Analysis', desc: 'Neo4j queries for ring connections and impersonation patterns', icon: Network },
  { step: 5, title: 'Scoring', desc: '5-category weighted trust engine calculates 0-100 score', icon: BarChart3 },
  { step: 6, title: 'Verdict', desc: 'Hindi report generated, blockchain write if HIGH_RISK', icon: Shield },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="py-16 sm:py-20 bg-gradient-to-b from-indigo-50 to-white">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center mx-auto mb-6 shadow-lg">
            <Shield className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 mb-4">
            About TrustNet
          </h1>
          <p className="text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto mb-8">
            TrustNet is a real-time job offer fraud investigation platform built for Indian students
            and job seekers. We combine AI, graph intelligence, and blockchain to protect you from scams.
          </p>
          <Link to="/">
            <Button className="h-12 px-8 bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-semibold text-base">
              Start Investigating <ArrowRight className="h-5 w-5 ml-2" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Problem & Solution */}
      <section className="py-16 bg-white">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
            <div>
              <h2 className="text-2xl font-bold text-slate-900 mb-4">The Problem</h2>
              <div className="space-y-4">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center flex-shrink-0">
                    <span className="text-red-600 font-bold text-sm">1L+</span>
                  </div>
                  <p className="text-slate-600">Indians lost money to fake job offers in 2023, mostly students aged 18-25</p>
                </div>
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center flex-shrink-0">
                    <span className="text-red-600 font-bold text-sm">35K</span>
                  </div>
                  <p className="text-slate-600">Average loss per victim — registration fees ranging from Rs. 1,500 to Rs. 5,000</p>
                </div>
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center flex-shrink-0">
                    <span className="text-red-600 font-bold text-xs">500M</span>
                  </div>
                  <p className="text-slate-600">Indians communicate via WhatsApp — the primary scam delivery channel</p>
                </div>
              </div>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-900 mb-4">Our Solution</h2>
              <div className="space-y-4">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
                    <span className="text-indigo-600 font-bold text-sm">8s</span>
                  </div>
                  <p className="text-slate-600">Complete investigation in under 8 seconds — faster than reading the scam message twice</p>
                </div>
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
                    <span className="text-indigo-600 font-bold text-xs">100%</span>
                  </div>
                  <p className="text-slate-600">Transparent scoring — every category explained with evidence, not a black box</p>
                </div>
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center flex-shrink-0">
                    <span className="text-indigo-600 font-bold text-xs">Hindi</span>
                  </div>
                  <p className="text-slate-600">Built for India — Hindi/Hinglish input, voice support, and bilingual reports</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Process Flow */}
      <section className="py-16 bg-slate-50">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-center text-slate-900 mb-12">
            How TrustNet Investigates
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {processFlow.map((step) => (
              <div key={step.step} className="relative p-6 rounded-2xl bg-white border border-slate-100 hover:shadow-md transition-shadow">
                <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center mb-4">
                  <step.icon className="h-5 w-5 text-indigo-600" />
                </div>
                <span className="absolute top-4 right-4 text-2xl font-bold text-slate-100">{step.step}</span>
                <h3 className="font-semibold text-slate-900 mb-1">{step.title}</h3>
                <p className="text-sm text-slate-500">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech Stack */}
      <section className="py-16 bg-white">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-2xl sm:text-3xl font-bold text-center text-slate-900 mb-12">
            Technology Stack
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {techStack.map((group) => (
              <div key={group.category} className="p-6 rounded-2xl border border-slate-100 bg-slate-50/50">
                <h3 className="font-semibold text-slate-900 mb-3">{group.category}</h3>
                <ul className="space-y-2">
                  {group.items.map((item) => (
                    <li key={item} className="text-sm text-slate-600 flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-gradient-to-b from-indigo-50 to-white">
        <div className="mx-auto max-w-2xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-slate-900 mb-4">
            Protect Yourself and Others
          </h2>
          <p className="text-slate-600 mb-8">
            Every investigation helps map scam infrastructure and protect the next job seeker.
            Share TrustNet with friends and family.
          </p>
          <Link to="/">
            <Button className="h-12 px-8 bg-gradient-to-r from-indigo-600 to-violet-600 text-white font-semibold text-base">
              Start an Investigation
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}