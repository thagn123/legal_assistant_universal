/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  FileText, 
  MoreVertical, 
  LayoutGrid, 
  List, 
  Info,
  ChevronRight,
  Plus
} from 'lucide-react';
import { apiFetch, DocRecommendation, CaseRecommendation, LAW_TYPE_LABELS } from '../lib/api';
import { LawTypeBadge, ScoreBadge, InteractionButtons } from '../components/ui/Shared';

export function Documents() {
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState('all');
  const [docs, setDocs] = useState<DocRecommendation[]>([]);
  const [cases, setCases] = useState<CaseRecommendation[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const fetchDocs = async () => {
    setIsSearching(true);
    try {
      const docData = await apiFetch<DocRecommendation[]>('/recommendations/documents', {
        method: 'POST',
        body: JSON.stringify({ query, domain })
      });
      setDocs(Array.isArray(docData) ? docData : []);
      
      const caseData = await apiFetch<CaseRecommendation[]>('/recommendations/cases', {
        method: 'POST',
        body: JSON.stringify({ query })
      });
      setCases(Array.isArray(caseData) ? caseData : []);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSearching(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  return (
    <div className="p-8 space-y-12 animate-in fade-in duration-500">
      {/* SEARCH BAR */}
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={20} />
            <input 
              type="text" 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && fetchDocs()}
              placeholder="Tìm tài liệu pháp lý..." 
              className="w-full bg-white/5 border border-white/10 rounded-2xl pl-12 pr-4 py-4 text-sm focus:border-legal-gold focus:ring-1 focus:ring-legal-gold transition-all"
            />
          </div>
          <select 
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-2xl px-6 text-xs font-bold text-slate-300 focus:border-legal-gold transition-all"
          >
            <option value="all">Tất cả</option>
            {Object.entries(LAW_TYPE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <button 
            onClick={fetchDocs}
            className="px-8 bg-legal-gold text-legal-navy rounded-2xl font-bold hover:scale-105 active:scale-95 transition-all shadow-lg shadow-legal-gold/20"
          >
            Tìm
          </button>
        </div>
      </div>

      {/* DOCUMENT RESULTS */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
            <FileText className="text-legal-gold" size={18} />
            Tài liệu đề xuất
          </h3>
          <div className="flex bg-white/5 p-1 rounded-lg border border-white/10">
             <button className="p-1.5 text-legal-gold bg-white/5 rounded-md"><LayoutGrid size={16} /></button>
             <button className="p-1.5 text-slate-500 hover:text-white"><List size={16} /></button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {isSearching ? (
            Array(6).fill(0).map((_, i) => <div key={i} className="glass-card aspect-[4/3] animate-skeleton" />)
          ) : docs.map((doc) => (
            <div key={doc.id} className="glass-card p-6 flex flex-col group hover:border-legal-gold/30 transition-all">
              <div className="flex items-center justify-between mb-4">
                 <LawTypeBadge type={doc.law_type} />
                 <ScoreBadge score={doc.final_score} />
              </div>
              
              <div className="flex-1">
                <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-tighter mb-1">ID: {doc.id}</h4>
                <p className="text-sm text-slate-200 line-clamp-3 leading-relaxed mb-4">"{doc.snippet}"</p>
                
                {/* Score Breakdown Tooltip simulation */}
                <div className="p-3 bg-white/5 rounded-xl border border-white/10 opacity-0 group-hover:opacity-100 transition-opacity space-y-2">
                   <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest mb-1">Cơ cấu điểm số</p>
                   <ScoreBar label="Vector" score={doc.scores.vector} />
                   <ScoreBar label="Collaborative" score={doc.scores.collab} />
                   <ScoreBar label="Item-Item" score={doc.scores.item_cf} />
                   <ScoreBar label="User-User" score={doc.scores.user_user} />
                </div>
              </div>

              <div className="mt-auto pt-6 border-t border-white/5">
                 <p className="text-[10px] text-slate-500 italic mb-4 line-clamp-1">"{doc.reason}"</p>
                 <div className="flex items-center justify-between">
                    <button className="text-xs font-bold text-legal-gold hover:underline">Chi tiết ↗</button>
                    <InteractionButtons docId={doc.id} />
                 </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* SIMILAR CASES */}
      <div className="space-y-6">
        <h3 className="text-sm font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
          <Info className="text-legal-gold" size={18} />
          Án lệ & Vụ việc tương tự
        </h3>
        <div className="space-y-4">
          {isSearching ? (
             Array(2).fill(0).map((_, i) => <div key={i} className="glass-card h-40 animate-skeleton" />)
          ) : cases.map((c) => (
            <div key={c.id} className="glass-card p-6 flex gap-8 items-start hover:bg-white/10 transition-all">
               <div className="w-16 h-16 rounded-2xl bg-legal-gold/10 flex items-center justify-center text-legal-gold shrink-0 border border-legal-gold/20">
                  <span className="text-xl font-bold">{(c.similarity_score * 100).toFixed(0)}%</span>
               </div>
               <div className="flex-1 min-w-0">
                  <h4 className="font-bold text-white text-lg mb-2">{c.title}</h4>
                  <p className="text-xs text-slate-400 mb-4 line-clamp-2 leading-relaxed">{c.situation_summary}</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                       <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest mb-1">Kết quả</p>
                       <span className="text-[11px] text-legal-success font-bold font-mono">{c.outcome}</span>
                    </div>
                    <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                       <p className="text-[9px] font-bold text-slate-500 uppercase tracking-widest mb-1">Bài học rút ra</p>
                       <p className="text-[11px] text-slate-300 italic">"{c.lesson}"</p>
                    </div>
                  </div>
               </div>
               <button className="p-2 text-slate-500 hover:text-white transition-colors">
                  <MoreVertical size={20} />
               </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  return (
    <div className="flex items-center gap-3">
       <span className="text-[9px] text-slate-500 w-16 uppercase">{label}</span>
       <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
          <div className="h-full bg-legal-gold/60" style={{ width: `${score * 100}%` }} />
       </div>
       <span className="text-[9px] font-mono text-slate-400">{(score * 100).toFixed(0)}</span>
    </div>
  );
}
