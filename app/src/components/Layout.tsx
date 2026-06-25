import { Outlet } from 'react-router';
import Navigation from './Navigation';

export default function Layout() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <Navigation />
      <main className="pt-16">
        <Outlet />
      </main>
      <footer className="border-t bg-white py-8 mt-auto">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-between">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center">
                <span className="text-white font-bold text-sm">TN</span>
              </div>
              <span className="font-semibold text-slate-800">TrustNet</span>
            </div>
            <p className="text-sm text-slate-500 text-center">
              Protecting Indian job seekers from fraud. Built for the community.
            </p>
            <p className="text-xs text-slate-400">
              Data sources: MCA, WHOIS, Google Safe Browsing, PhishTank, Neo4j Graph
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}