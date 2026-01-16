"use client";

import React from 'react';

interface InvestmentDecisionProps {
    ticker: string;
    decision: 'buy' | 'hold' | 'sell';
    confidence: number;
    rationale: string;
}

const InvestmentDecision: React.FC<InvestmentDecisionProps> = ({
    ticker,
    decision,
    confidence,
    rationale
}) => {
    const decisionStyles = {
        buy: 'bg-accent-primary/20 text-accent-primary border-accent-primary/30 shadow-[0_0_30px_rgba(16,185,129,0.1)]',
        sell: 'bg-red-500/20 text-red-500 border-red-500/30 shadow-[0_0_30px_rgba(239,68,68,0.1)]',
        hold: 'bg-accent-secondary/20 text-accent-secondary border-accent-secondary/30 shadow-[0_0_30px_rgba(59,130,246,0.1)]',
    };

    return (
        // <div className="glass-panel p-8 mb-8 text-center relative overflow-hidden flex flex-col items-center gap-6">
        <>
            <h2 className="text-xl font-bold uppercase tracking-wider text-text-muted mb-2">{ticker} Analysis Final Result</h2>

            <div className={`text-3xl font-black uppercase tracking-tighter py-3 px-8 rounded-md inline-block border ${decisionStyles[decision]}`}>
                {decision} Recommendation
            </div>

            <div className="flex flex-col items-center gap-2">
                <div className="text-5xl font-bold font-mono text-foreground">
                    {Math.round(confidence * 100)}%
                </div>
                <div className="text-muted">Confidence Score</div>
            </div>

            <div className="text-lg text-text-muted max-w-2xl leading-relaxed italic">
                {rationale}
            </div>
        </>
        // </div>
    );
};

export default InvestmentDecision;
