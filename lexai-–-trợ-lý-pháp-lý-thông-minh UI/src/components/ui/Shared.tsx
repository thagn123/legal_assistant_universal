/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { cn, LAW_TYPE_LABELS } from '../../lib/api';

// SCORE BADGE
export function ScoreBadge({ score }: { score: number }) {
  let label = "Có liên quan";
  let color = "bg-slate-500/20 text-slate-400 border-slate-500/30";
  
  if (score >= 0.7) {
    label = "Rất phù hợp";
    color = "bg-legal-success/20 text-legal-success border-legal-success/30";
  } else if (score >= 0.4) {
    label = "Phù hợp";
    color = "bg-legal-warning/20 text-legal-warning border-legal-warning/30";
  }
  
  return (
    <span className={cn("px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide border", color)}>
      {label} {(score * 100).toFixed(0)}%
    </span>
  );
}

// LAW TYPE BADGE
export function LawTypeBadge({ type }: { type: string }) {
  const label = LAW_TYPE_LABELS[type] || type;
  return (
    <span className="px-2 py-0.5 bg-legal-gold/10 text-legal-gold border border-legal-gold/20 rounded text-[10px] font-bold uppercase tracking-wider">
      {label}
    </span>
  );
}

// INTERACTION BUTTONS
import { Eye, Save, Download } from 'lucide-react';
import { apiFetch } from '../../lib/api';

export function InteractionButtons({ docId }: { docId: string }) {
  const logInteraction = async (action: 'view' | 'save' | 'download') => {
    try {
      await apiFetch('/interactions/log', {
        method: 'POST',
        body: JSON.stringify({ doc_id: docId, action_type: action, context: {} })
      });
      // In a real app, maybe show a toast
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button 
        onClick={() => logInteraction('view')}
        className="p-1.5 text-slate-400 hover:text-white hover:bg-white/5 rounded transition-all" 
        title="Xem"
      >
        <Eye size={16} />
      </button>
      <button 
        onClick={() => logInteraction('save')}
        className="p-1.5 text-slate-400 hover:text-white hover:bg-white/5 rounded transition-all" 
        title="Lưu"
      >
        <Save size={16} />
      </button>
      <button 
        onClick={() => logInteraction('download')}
        className="p-1.5 text-slate-400 hover:text-white hover:bg-white/5 rounded transition-all" 
        title="Tải xuống"
      >
        <Download size={16} />
      </button>
    </div>
  );
}
