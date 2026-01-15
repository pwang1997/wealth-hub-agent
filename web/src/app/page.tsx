"use client";

import InvestmentDecision from '@/components/Dashboard/InvestmentDecision';
import ResultAccordion from '@/components/Dashboard/ResultAccordion';
import WorkflowStepper, { Step } from '@/components/Dashboard/WorkflowStepper';
import { useWorkflow } from '@/lib/useWorkflow';
import { Briefcase, LayoutDashboard, Search, Settings, TrendingUp } from 'lucide-react';
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
    <div className="flex" style={{ height: '100vh' }}>
      {/* Sidebar */}
      <aside className="glass-panel" style={{ width: '280px', margin: '1rem', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '2rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: '40px', height: '40px', background: 'var(--accent-primary)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#000' }}>
            <TrendingUp size={24} />
          </div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Wealth Hub</h1>
        </div>

        <nav style={{ padding: '0 1rem', flex: 1 }}>
          {[
            { icon: <LayoutDashboard size={20} />, label: 'Dashboard', active: true },
            { icon: <Briefcase size={20} />, label: 'Portfolio' },
            { icon: <Search size={20} />, label: 'Market Analysis' },
            { icon: <Settings size={20} />, label: 'Settings' },
          ].map((item, idx) => (
            <div key={idx} className="glass-card" style={{
              padding: '0.8rem 1rem',
              marginBottom: '0.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              cursor: 'pointer',
              color: item.active ? 'var(--foreground)' : 'var(--text-muted)'
            }}>
              {item.icon}
              <span style={{ fontWeight: 500 }}>{item.label}</span>
            </div>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, overflowY: 'auto', padding: '2rem 3rem' }}>
        <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '1.75rem', fontWeight: 600, marginBottom: '0.5rem' }}>AI Market Analyst</h2>
            <p className="text-muted">Enter a ticker and research objective to initiate an agent workflow.</p>
          </div>
          <div className="glass-card" style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-primary)' }}></div>
            <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>System Status: Operational</span>
          </div>
        </header>

        {/* Search Controls */}
        <section className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem' }}>
          <div className="flex gap-4" style={{ marginBottom: '1.5rem' }}>
            <div style={{ flex: 1 }}>
              <label className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', fontWeight: 600, display: 'block', marginBottom: '0.5rem' }}>Ticker Symbol</label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                style={{ width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '0.75rem 1rem', color: '#fff', fontSize: '1rem' }}
              />
            </div>
            <div style={{ flex: 3 }}>
              <label className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', fontWeight: 600, display: 'block', marginBottom: '0.5rem' }}>Research Query</label>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                style={{ width: '100%', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '0.75rem 1rem', color: '#fff', fontSize: '1rem' }}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button
                className="btn-primary"
                onClick={() => runWorkflow(ticker, query)}
                disabled={state.status === 'running'}
                style={{ height: '48px', padding: '0 2rem' }}
              >
                {state.status === 'running' ? 'Running Analysis...' : 'Run Analysis'}
              </button>
            </div>
          </div>
        </section>

        {/* Workflow Progress */}
        {state.status !== 'idle' && (
          <section className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem' }}>
            <WorkflowStepper steps={stepsData} />
          </section>
        )}

        {/* Results */}
        <section style={{ maxWidth: '900px', margin: '0 auto' }}>
          {state.results.investment && (
            <InvestmentDecision
              ticker={ticker}
              decision={state.results.investment.decision}
              confidence={state.results.investment.confidence}
              rationale={state.results.investment.rationale}
            />
          )}

          <div style={{ marginTop: '2rem' }}>
            {state.results.retrieval && (
              <ResultAccordion title="Data Retrieval Results">
                <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  <p>Successfully retrieved data for {ticker}.</p>
                  <p style={{ marginTop: '0.5rem' }}><strong>Answer:</strong> {state.results.retrieval.answer}</p>
                </div>
              </ResultAccordion>
            )}

            {state.results.fundamental && (
              <ResultAccordion title="Fundamental Analysis Summary">
                <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  <p><strong>Health Score:</strong> {state.results.fundamental.health_score} / 10</p>
                  <p style={{ marginTop: '0.5rem' }}>{state.results.fundamental.summary}</p>
                </div>
              </ResultAccordion>
            )}

            {state.results.news && (
              <ResultAccordion title="News Sentiment Analysis">
                <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  <p><strong>Overall Sentiment:</strong> {state.results.news.overall_sentiment_label} ({state.results.news.overall_sentiment_score})</p>
                  <p style={{ marginTop: '0.5rem' }}>{state.results.news.rationale}</p>
                </div>
              </ResultAccordion>
            )}

            {state.results.research && (
              <ResultAccordion title="Research Synthesis">
                <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  <p>{state.results.research.composed_analysis}</p>
                </div>
              </ResultAccordion>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
