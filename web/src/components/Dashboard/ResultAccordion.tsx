"use client";

import { ChevronDown, CircleCheck } from 'lucide-react';
import React, { useState } from 'react';
import styles from './ResultAccordion.module.css';

interface ResultAccordionProps {
    title: string;
    isOpen?: boolean;
    children: React.ReactNode;
}

const ResultAccordion: React.FC<ResultAccordionProps> = ({
    title,
    isOpen: initialOpen = false,
    children
}) => {
    const [isOpen, setIsOpen] = useState(initialOpen);

    return (
        <div className={styles.accordion}>
            <button
                className={styles.header}
                onClick={() => setIsOpen(!isOpen)}
                data-open={isOpen}
            >
                <div className={styles.title}>
                    <CircleCheck size={18} className={styles.badgeSuccess} />
                    {title}
                </div>
                <ChevronDown size={18} className={styles.chevron} />
            </button>

            {isOpen && (
                <div className={styles.content}>
                    {children}
                </div>
            )}
        </div>
    );
};

export default ResultAccordion;
