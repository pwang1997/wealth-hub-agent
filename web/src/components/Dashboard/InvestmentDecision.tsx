"use client";

import React from 'react';
import styles from './InvestmentDecision.module.css';

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
    return (
        <div className={`${styles.card} glass-panel`}>
            <h2 className={styles.title}>{ticker} Analysis Final Result</h2>

            <div className={styles.decision} data-value={decision}>
                {decision} Recommendation
            </div>

            <div className={styles.confidence}>
                <div className={styles.gauge}>
                    {Math.round(confidence * 100)}%
                </div>
                <div className="text-muted">Confidence Score</div>
            </div>

            <div className={styles.rationale}>
                {rationale}
            </div>
        </div>
    );
};

export default InvestmentDecision;
