"use client";

import { Check, Loader2 } from 'lucide-react';
import React from 'react';

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
        <div className="flex justify-between w-full py-8 relative after:content-[''] after:absolute after:top-1/2 after:left-0 after:right-0 after:h-[2px] after:bg-white/5 after:-translate-y-1/2 after:z-0">
            {steps.map((step, index) => (
                <div
                    key={step.id}
                    className="flex flex-col items-center gap-4 z-10 relative flex-1"
                    data-status={step.status}
                >
                    <div className={`
                        w-12 h-12 rounded-full bg-[#0f0f0f] border-2 flex items-center justify-center transition-all duration-400 ease-out
                        ${step.status === 'completed' ? 'bg-accent-primary border-accent-primary text-black shadow-[0_0_20px_rgba(16,185,129,0.15)]' :
                            step.status === 'running' ? 'border-accent-secondary text-accent-secondary shadow-[0_0_15px_rgba(59,130,246,0.2)]' :
                                'border-white/10 text-text-muted'}
                    `}>
                        {step.status === 'completed' ? (
                            <Check size={20} />
                        ) : step.status === 'running' ? (
                            <Loader2 size={20} className="animate-spin" />
                        ) : (
                            <span className="text-[0.8rem]">{index + 1}</span>
                        )}
                    </div>
                    <div className={`
                        flex flex-col items-center gap-1 text-[0.85rem] font-medium text-center transition-colors duration-300
                        ${step.status === 'completed' || step.status === 'running' ? 'text-foreground' : 'text-text-muted'}
                    `}>
                        <span>{step.label}</span>
                        {step.status !== 'pending' && (
                            <div className="text-[0.7rem] text-accent-secondary font-mono px-2 py-0.5 bg-accent-secondary/10 rounded-sm border border-accent-secondary/20">
                                {step.duration || 0}s
                            </div>
                        )}
                    </div>
                </div>
            ))}
        </div>
    );
};

export default WorkflowStepper;
