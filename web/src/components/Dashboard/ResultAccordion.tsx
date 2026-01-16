import { ChevronDown, CircleCheck, Loader2 } from 'lucide-react';
import React, { useState } from 'react';

interface ResultAccordionProps {
    title: string;
    isOpen?: boolean;
    status?: 'pending' | 'running' | 'completed' | 'failed';
    children: React.ReactNode;
}

const ResultAccordion: React.FC<ResultAccordionProps> = ({
    title,
    isOpen: initialOpen = false,
    status = 'completed',
    children
}) => {
    const [isOpen, setIsOpen] = useState(initialOpen);

    if (status === 'pending') return null;

    return (
        <div className="glass-panel overflow-hidden mb-4 border border-white/5 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <button
                className={`w-full p-4 flex justify-between items-center transition-all duration-200 hover:bg-white/2 ${isOpen ? 'border-b border-white/5' : ''}`}
                onClick={() => setIsOpen(!isOpen)}
            >
                <div className="flex items-center gap-2 font-medium text-[0.95rem]">
                    {status === 'running' ? (
                        <Loader2 size={18} className="text-accent-secondary animate-spin" />
                    ) : (
                        <CircleCheck size={18} className="text-accent-primary" />
                    )}
                    <span className={status === 'running' ? 'text-accent-secondary' : 'text-foreground'}>
                        {title}
                        {status === 'running' && <span className="ml-2 text-[0.7rem] opacity-70 font-normal italic">Agent is analyzing...</span>}
                    </span>
                </div>
                <ChevronDown size={18} className={`text-text-muted transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="p-4 bg-white/1 animate-in fade-in zoom-in-95 duration-300">
                    {status === 'running' ? (
                        <div className="flex flex-col items-center justify-center py-8 gap-4 text-text-muted">
                            <div className="flex gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-accent-secondary animate-bounce [animation-delay:-0.3s]"></span>
                                <span className="w-1.5 h-1.5 rounded-full bg-accent-secondary animate-bounce [animation-delay:-0.15s]"></span>
                                <span className="w-1.5 h-1.5 rounded-full bg-accent-secondary animate-bounce"></span>
                            </div>
                            <span className="text-xs uppercase tracking-widest font-bold opacity-50">Synthesizing intelligence...</span>
                        </div>
                    ) : (
                        children
                    )}
                </div>
            )}
        </div>
    );
};

export default ResultAccordion;
