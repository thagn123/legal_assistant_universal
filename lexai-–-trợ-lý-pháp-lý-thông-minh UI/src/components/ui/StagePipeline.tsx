/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { CheckCircle2, Loader2 } from 'lucide-react';
import { cn } from '../../lib/api';

export interface Stage {
  name: string;
  id: number;
}

export interface StageTiming {
  stage: string;
  duration_ms: number;
}

interface StagePipelineProps {
  currentStage?: number;
  stages?: Stage[];
  timings?: StageTiming[];
}

export function StagePipeline({ currentStage, stages, timings }: StagePipelineProps) {
  if (timings) {
    return (
      <div className="flex flex-wrap items-center justify-center gap-y-6 gap-x-2 py-4">
        {timings.map((t, i) => {
          const color = t.duration_ms < 50 ? 'bg-emerald-500/20 text-emerald-500 border-emerald-500/20' : 
                        t.duration_ms < 500 ? 'bg-amber-500/20 text-amber-500 border-amber-500/20' : 
                        'bg-orange-500/20 text-orange-500 border-orange-500/20';
          
          return (
            <React.Fragment key={i}>
              <div className={cn("px-3 py-1.5 rounded-full border flex flex-col items-center gap-0.5 min-w-[80px]", color)}>
                <span className="text-[9px] font-bold uppercase tracking-tight whitespace-nowrap">{t.stage}</span>
                <span className="text-[10px] font-mono font-bold leading-none">{t.duration_ms}ms</span>
              </div>
              {i < timings.length - 1 && (
                <div className="w-4 h-px bg-white/10 hidden sm:block" />
              )}
            </React.Fragment>
          );
        })}
      </div>
    );
  }

  if (!stages) return null;

  return (
    <div className="flex items-center justify-between gap-2 px-4 py-8">
      {stages.map((stage) => {
        const isComplete = stage.id < currentStage;
        const isActive = stage.id === currentStage;
        
        return (
          <div key={stage.id} className="flex flex-col items-center gap-3 flex-1 relative">
            {/* Line connector */}
            {stage.id !== stages.length && (
              <div 
                className={cn(
                  "absolute h-0.5 top-5 left-[calc(50%+20px)] right-[calc(-50%+20px)] z-0",
                  isComplete ? "bg-legal-success" : "bg-white/10"
                )} 
              />
            )}
            
            <div className={cn(
              "w-10 h-10 rounded-full flex items-center justify-center z-10 transition-all duration-300",
              isComplete ? "bg-legal-success text-white" : 
              isActive ? "bg-legal-gold text-legal-navy animate-pulse" : 
              "bg-white/5 text-slate-500 border border-white/10"
            )}>
              {isComplete ? <CheckCircle2 size={20} /> : 
               isActive ? <Loader2 size={20} className="animate-spin" /> : 
               <span className="text-xs font-bold">{stage.id}</span>}
            </div>
            
            <span className={cn(
              "text-[10px] font-bold uppercase tracking-widest text-center px-1",
              isComplete ? "text-legal-success" : isActive ? "text-legal-gold" : "text-slate-500"
            )}>
              {stage.name}
            </span>
          </div>
        );
      })}
    </div>
  );
}
