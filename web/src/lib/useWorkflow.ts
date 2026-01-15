"use client";

import { StepStatus } from '@/components/Dashboard/WorkflowStepper';
import { useCallback, useRef, useState } from 'react';

interface WorkflowState {
  id: string | null;
  status: 'idle' | 'running' | 'completed' | 'failed';
  currentStep: string | null;
  steps: {
    retrieval: StepStatus;
    fundamental: StepStatus;
    news: StepStatus;
    research: StepStatus;
    investment: StepStatus;
  };
  durations: {
    retrieval: number;
    fundamental: number;
    news: number;
    research: number;
    investment: number;
  };
  results: any;
}

const initialState: WorkflowState = {
  id: null,
  status: 'idle',
  currentStep: null,
  steps: {
    retrieval: 'pending',
    fundamental: 'pending',
    news: 'pending',
    research: 'pending',
    investment: 'pending',
  },
  durations: {
    retrieval: 0,
    fundamental: 0,
    news: 0,
    research: 0,
    investment: 0,
  },
  results: {},
};

export function useWorkflow() {
  const [state, setState] = useState<WorkflowState>(initialState);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const startTimer = useCallback((step: string) => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setState(prev => ({
        ...prev,
        durations: {
          ...prev.durations,
          [step]: prev.durations[step as keyof typeof prev.durations] + 1
        }
      }));
    }, 1000);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const runWorkflow = useCallback(async (ticker: string, query: string) => {
    setState({ ...initialState, status: 'running' });

    try {
      const response = await fetch('http://localhost:8000/v1/workflow/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ticker, query }),
      });

      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Save the potentially incomplete last line back to the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue;

          try {
            const event = JSON.parse(trimmedLine.slice(6));
            
            if (event.event === 'step_start') {
              setState(prev => ({
                ...prev,
                steps: { ...prev.steps, [event.step]: 'running' },
                currentStep: event.step
              }));
              startTimer(event.step);
            } else if (event.event === 'step_complete') {
              setState(prev => ({
                ...prev,
                steps: { ...prev.steps, [event.step]: event.status },
                results: { ...prev.results, [event.step]: event.payload.output }
              }));
              stopTimer();
            } else if (event.event === 'workflow_complete') {
              setState(prev => ({ ...prev, status: 'completed' }));
              stopTimer();
            }
          } catch (e) {
            console.error('Failed to parse SSE event:', trimmedLine, e);
          }
        }
      }
    } catch (error) {
      console.error('Workflow failed:', error);
      setState(prev => ({ ...prev, status: 'failed' }));
      stopTimer();
    }
  }, [startTimer, stopTimer]);

  return { state, runWorkflow };
}
