"use client";

import { Check, Loader2 } from 'lucide-react';
import React from 'react';
import styles from './WorkflowStepper.module.css';

export type StepStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface Step {
    id: string;
    label: string;
    status: StepStatus;
    duration?: number;
}

interface WorkflowStepperProps {
    steps: Step[];
}

const WorkflowStepper: React.FC<WorkflowStepperProps> = ({ steps }) => {
    return (
        <div className={styles.stepper}>
            {steps.map((step, index) => (
                <div
                    key={step.id}
                    className={styles.step}
                    data-status={step.status}
                >
                    <div className={styles.circle}>
                        {step.status === 'completed' ? (
                            <Check size={20} />
                        ) : step.status === 'running' ? (
                            <Loader2 size={20} className="animate-spin" />
                        ) : (
                            <span style={{ fontSize: '0.8rem' }}>{index + 1}</span>
                        )}
                    </div>
                    <div className={styles.label}>
                        {step.label}
                        {step.status === 'running' && step.duration !== undefined && (
                            <div className={styles.timer}>{step.duration}s</div>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default WorkflowStepper;
