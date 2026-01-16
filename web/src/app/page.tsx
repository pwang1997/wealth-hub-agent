"use client";

import InvestmentDecision from '@/components/Dashboard/InvestmentDecision';
import ResultAccordion from '@/components/Dashboard/ResultAccordion';
import { Step } from '@/components/Dashboard/WorkflowStepper';
import { useWorkflow } from '@/lib/useWorkflow';
import { LayoutDashboard, Loader2, TrendingUp } from 'lucide-react';
import { useState } from 'react';

export default function Home() {
  const [ticker, setTicker] = useState('NVDA');
  const [query, setQuery] = useState('Analyze the impact of recent AI chip regulations on long-term growth.');
  const { state, runWorkflow } = useWorkflow();

  const stepsData: Step[] = [
    { id: 'retrieval', label: 'Data Retrieval', status: state.steps.retrieval, duration: state.durations.retrieval },
    { id: 'fundamental', label: 'Fundamental Analysis', status: state.steps.fundamental, duration: state.durations.fundamental },
    { id: 'news', label: 'News Sentiment', status: state.steps.news, duration: state.durations.news },
    { id: 'research', label: 'Research Synthesis', status: state.steps.research, duration: state.durations.research },
    { id: 'investment', label: 'Investment Decision', status: state.steps.investment, duration: state.durations.investment },
  ];

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="glass-panel w-[280px] m-4 flex flex-col">
        <div className="p-8 flex items-center gap-4">
          <div className="w-10 h-10 bg-accent-primary rounded-sm flex items-center justify-center text-black">
            <TrendingUp size={24} />
          </div>
          <h1 className="text-xl font-bold tracking-tight">Wealth Hub</h1>
        </div>

        <nav className="px-4 flex-1">
          {[
            { icon: <LayoutDashboard size={20} />, label: 'Dashboard', active: true },
            // { icon: <Briefcase size={20} />, label: 'Portfolio' },
            // { icon: <Search size={20} />, label: 'Market Analysis' },
            // { icon: <Settings size={20} />, label: 'Settings' },
          ].map((item, idx) => (
            <div
              key={idx}
              className={`glass-card p-3 mb-2 flex items-center gap-3 cursor-pointer ${item.active ? 'text-foreground' : 'text-text-muted'}`}
            >
              {item.icon}
              <span className="font-medium text-sm">{item.label}</span>
            </div>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto px-12 py-8">
        <div className="max-w-[1000px] mx-auto w-full">
          <header className="mb-12 flex justify-between items-center">
            <div>
              <h2 className="text-3xl font-semibold mb-2">AI Market Analyst</h2>
              <p className="text-text-muted text-sm">Enter a ticker and research objective to initiate an agent workflow.</p>
            </div>
            <div className="glass-card px-4 py-2 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-accent-primary shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
              <span className="text-[0.75rem] font-medium uppercase tracking-wider">System Operational</span>
            </div>
          </header>

          {/* Search Controls */}
          <section className="glass-panel p-8 mb-8">
            <div className="flex gap-4 mb-6">
              <div className="flex-1">
                <label className="text-text-muted text-[0.65rem] uppercase font-bold tracking-widest block mb-2">Ticker Symbol</label>
                <input
                  type="text"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  className="w-full bg-white/5 border border-white/10 rounded-sm px-4 py-3 text-white text-base focus:outline-none focus:border-accent-primary transition-all"
                  placeholder="e.g. NVDA"
                />
              </div>
              <div className="flex-[3]">
                <label className="text-text-muted text-[0.65rem] uppercase font-bold tracking-widest block mb-2">Research Query</label>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-sm px-4 py-3 text-white text-base focus:outline-none focus:border-accent-primary transition-all"
                  placeholder="What would you like the agents to analyze?"
                />
              </div>
              <div className="flex items-end">
                <button
                  className={`btn-primary h-[50px] px-8 disabled:opacity-50 disabled:cursor-not-allowed`}
                  onClick={() => runWorkflow(ticker, query)}
                  disabled={state.status === 'running'}
                >
                  {state.status === 'running' ? (
                    <div className="flex items-center gap-2">
                      <Loader2 size={18} className="animate-spin" />
                      <span>Analyzing...</span>
                    </div>
                  ) : 'Run Analysis'}
                </button>
              </div>
            </div>
          </section>

          {/* Results */}
          <section className="pb-12">
            <div className="space-y-4">
              {state.steps.retrieval !== 'pending' && (
                <ResultAccordion title="Data Retrieval Results" status={state.steps.retrieval}>
                  <div className="text-[0.9rem] text-text-muted leading-relaxed">
                    <p className="mb-3">Successfully retrieved and processed regulatory filings and news for <span className="text-foreground font-medium">{ticker}</span>.</p>
                    <p><strong>Synthesized Context:</strong> {state.results.retrieval?.answer}</p>
                  </div>
                </ResultAccordion>
              )}

              {state.steps.fundamental !== 'pending' && (
                <ResultAccordion title="Fundamental Analysis Summary" status={state.steps.fundamental}>
                  <div className="text-[0.9rem] text-text-muted leading-relaxed">
                    <div className="flex items-center gap-3 mb-4 bg-white/5 p-3 rounded-sm w-fit">
                      <span className="text-xs uppercase font-bold tracking-tighter">Health Score</span>
                      <span className="text-2xl font-black text-accent-primary">{state.results.fundamental?.health_score}<span className="text-sm font-normal text-text-muted">/10</span></span>
                    </div>
                    <p>{state.results.fundamental?.summary}</p>
                  </div>
                </ResultAccordion>
              )}

              {state.steps.news !== 'pending' && (
                <ResultAccordion title="News Sentiment Analysis" status={state.steps.news}>
                  <div className="text-[0.9rem] text-text-muted leading-relaxed">
                    <div className="flex items-center gap-3 mb-4 bg-white/5 p-3 rounded-sm w-fit">
                      <span className="text-xs uppercase font-bold tracking-tighter">Overall Sentiment</span>
                      <span className={`text-sm font-bold uppercase ${state.results.news?.overall_sentiment_score > 0 ? 'text-accent-primary' : 'text-red-400'}`}>
                        {state.results.news?.overall_sentiment_label} ({state.results.news?.overall_sentiment_score})
                      </span>
                    </div>
                    <p>{state.results.news?.rationale}</p>
                  </div>
                </ResultAccordion>
              )}

              {state.steps.research !== 'pending' && (
                <ResultAccordion title="Research Synthesis" status={state.steps.research}>
                  <div className="text-[0.9rem] text-text-muted leading-relaxed">
                    {state.results.research?.composed_analysis.split('\n').map((para: string, i: number) => (
                      <p key={i} className={i > 0 ? "mt-3" : ""}>{para}</p>
                    ))}
                  </div>
                </ResultAccordion>
              )}

              {state.steps.investment === 'completed' && state.results.investment && (
                <div className="animate-in zoom-in-95 duration-1000 slide-in-from-bottom-8 mt-12">
                  <InvestmentDecision
                    ticker={ticker}
                    decision={state.results.investment.decision}
                    confidence={state.results.investment.confidence}
                    rationale={state.results.investment.rationale}
                  />
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
