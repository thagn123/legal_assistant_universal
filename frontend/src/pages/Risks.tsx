/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  History, 
  Search, 
  AlertTriangle, 
  CheckSquare, 
  ArrowRight,
  ShieldCheck,
  TrendingUp
} from 'lucide-react';
import { apiFetch, RiskAssessment, logInteraction } from '../lib/api';

export function Risks() {
  const [activeTab, setActiveTab] = useState<'situation' | 'history'>('situation');
  const [situation, setSituation] = useState('');
  const [risks, setRisks] = useState<RiskAssessment[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<'all' | 'cao' | 'trung_binh' | 'thap'>('all');

  const fetchRisks = async (useHistory: boolean = false) => {
    setIsLoading(true);
    try {
      const data = await apiFetch<RiskAssessment[]>('/recommendations/risks', {
        method: 'POST',
        body: JSON.stringify({ situation, use_history: useHistory })
      });
      const result = Array.isArray(data) ? data : [];
      setRisks(result);
      if (result.length > 0) {
        logInteraction({ action_type: 'view', context: { situation_snippet: situation.slice(0, 100) } });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredRisks = severityFilter === 'all' ? risks : risks.filter(r => r.severity === severityFilter);

  useEffect(() => {
    if (activeTab === 'history') {
      fetchRisks(true);
    }
  }, [activeTab]);

  return (
    <div className="p-8 space-y-12 animate-in fade-in duration-500">
      {/* TABS HEADER */}
      <div className="flex border-b border-legal-border gap-8">
        <button 
          onClick={() => setActiveTab('situation')}
          className={`pb-4 px-2 text-sm font-bold transition-all relative ${
            activeTab === 'situation' ? 'text-legal-gold' : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          <div className="flex items-center gap-2">
            <Search size={18} />
            Theo tình huống
          </div>
          {activeTab === 'situation' && (
            <div className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-legal-gold" />
          )}
        </button>
        <button 
          onClick={() => setActiveTab('history')}
          className={`pb-4 px-2 text-sm font-bold transition-all relative ${
            activeTab === 'history' ? 'text-legal-gold' : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          <div className="flex items-center gap-2">
            <History size={18} />
            Theo lịch sử hội thoại
          </div>
          {activeTab === 'history' && (
            <div className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-legal-gold" />
          )}
        </button>
      </div>

      {activeTab === 'situation' && (
        <div className="max-w-4xl mx-auto glass-card p-8 flex gap-4">
          <input 
            type="text" 
            value={situation}
            onChange={(e) => setSituation(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchRisks(false)}
            placeholder="Nhập tình huống hoặc điều khoản cần rà soát rủi ro..." 
            className="flex-1 bg-legal-navy/50 border border-white/10 rounded-xl px-6 py-4 text-sm focus:border-legal-gold transition-all"
          />
          <button 
            onClick={() => fetchRisks(false)}
            className="px-8 bg-legal-gold text-legal-navy rounded-xl font-bold hover:scale-105 transition-all shadow-lg shadow-legal-gold/20"
          >
            Đánh giá
          </button>
        </div>
      )}

      {/* RISK GRID */}
      <div className="space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
           <h3 className="text-sm font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
             <ShieldAlert className="text-legal-gold" size={18} />
             Phân tích rủi ro pháp lý
             {risks.length > 0 && <span className="text-[10px] text-slate-600 normal-case tracking-normal font-normal">({filteredRisks.length}/{risks.length})</span>}
           </h3>
           <div className="flex items-center gap-3">
             {isLoading && <span className="text-[10px] text-legal-gold animate-pulse font-bold uppercase tracking-widest">Đang tải...</span>}
             {risks.length > 0 && (
               <select
                 value={severityFilter}
                 onChange={(e) => setSeverityFilter(e.target.value as typeof severityFilter)}
                 className="bg-legal-navy/50 border border-white/10 rounded-lg px-3 py-1.5 text-[11px] font-bold text-slate-300 focus:border-legal-gold transition-all"
               >
                 <option value="all">Tất cả mức độ</option>
                 <option value="cao">Nguy cấp</option>
                 <option value="trung_binh">Cảnh báo</option>
                 <option value="thap">Ổn định</option>
               </select>
             )}
           </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
           {isLoading ? (
             Array(3).fill(0).map((_, i) => <div key={i} className="glass-card aspect-square animate-skeleton" />)
           ) : filteredRisks.map((risk) => (
             <div 
               key={risk.id} 
               className={`glass-card p-8 space-y-6 border-t-4 transition-all hover:scale-[1.02] ${
                 risk.severity === 'cao' ? 'border-t-legal-danger' : 
                 risk.severity === 'trung_binh' ? 'border-t-legal-warning' : 'border-t-legal-success'
               }`}
             >
                <div className="flex items-center justify-between">
                   <h4 className="font-bold text-white text-lg">{risk.name}</h4>
                   <span className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase ${
                     risk.severity === 'cao' ? 'bg-legal-danger/20 text-legal-danger' : 
                     risk.severity === 'trung_binh' ? 'bg-legal-warning/20 text-legal-warning' : 'bg-legal-success/20 text-legal-success'
                   }`}>
                     {risk.severity === 'cao' ? 'Nguy cấp' : risk.severity === 'trung_binh' ? 'Cảnh báo' : 'Ổn định'}
                   </span>
                </div>
                
                <p className="text-xs text-slate-400 leading-relaxed">{risk.description}</p>
                
                <div className="space-y-4">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Chỉ số cảnh báo</p>
                  <ul className="space-y-2">
                    {risk.indicators.map((ind, i) => (
                      <li key={i} className="flex gap-2 text-[11px] text-slate-300">
                        <AlertTriangle size={14} className="text-legal-warning shrink-0" />
                        {ind}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="space-y-4">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Kế hoạch giảm thiểu</p>
                  <ul className="space-y-2">
                    {risk.mitigation_steps.map((step, i) => (
                      <li key={i} className="flex gap-2 text-[11px] text-slate-400">
                        <CheckSquare size={14} className="text-legal-success shrink-0" />
                        {step}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="pt-4 border-t border-white/5 mt-auto flex items-center justify-between">
                  <div className="flex gap-1">
                    {risk.related_law_types.map(lt => (
                      <span key={lt} className="px-1.5 py-0.5 bg-white/5 border border-white/10 rounded text-[8px] text-slate-500 uppercase">{lt}</span>
                    ))}
                  </div>
                  <span className="text-[10px] font-mono text-slate-600">ID: {risk.id}</span>
                </div>
             </div>
           ))}
        </div>

        {filteredRisks.length === 0 && !isLoading && (
          <div className="py-20 flex flex-col items-center opacity-30 text-center space-y-4">
             <ShieldCheck size={64} className="text-slate-500" />
             <p className="text-sm font-bold text-slate-500">Chưa phát hiện rủi ro nào. Tuyệt vời!</p>
          </div>
        )}
      </div>
    </div>
  );
}
