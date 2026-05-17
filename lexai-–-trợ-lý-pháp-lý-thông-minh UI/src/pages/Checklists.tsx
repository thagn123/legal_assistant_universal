/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { 
  CheckSquare, 
  Printer, 
  ChevronDown, 
  Scale, 
  Clock, 
  AlertCircle,
  CheckCircle2,
  Lock
} from 'lucide-react';
import { apiFetch, Checklist } from '../lib/api';

export function Checklists() {
  const [businessType, setBusinessType] = useState('cong_ty_tnhh');
  const [transactionType, setTransactionType] = useState('thanh_lap');
  const [checklists, setChecklists] = useState<Checklist[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchChecklists = async () => {
    setIsLoading(true);
    try {
      const data = await apiFetch<Checklist[]>('/recommendations/checklists', {
        method: 'POST',
        body: JSON.stringify({ business_type: businessType, transaction_type: transactionType })
      });
      setChecklists(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchChecklists();
  }, []);

  return (
    <div className="p-8 space-y-12 animate-in fade-in duration-500">
      {/* SELECTION BAR */}
      <div className="max-w-4xl mx-auto glass-card p-8 grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
        <div className="space-y-4">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-widest text-[9px]">Loại hình doanh nghiệp</label>
          <select 
            value={businessType}
            onChange={(e) => setBusinessType(e.target.value)}
            className="w-full bg-legal-navy/50 border border-white/10 rounded-lg p-2.5 text-xs font-bold text-slate-300"
          >
            <option value="cong_ty_tnhh">Công ty TNHH</option>
            <option value="cong_ty_co_phan">Công ty Cổ phần</option>
            <option value="ho_kinh_doanh">Hộ kinh doanh</option>
            <option value="ca_nhan">Cá nhân</option>
          </select>
        </div>
        <div className="space-y-4">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-widest text-[9px]">Loại giao dịch</label>
          <select 
            value={transactionType}
            onChange={(e) => setTransactionType(e.target.value)}
            className="w-full bg-legal-navy/50 border border-white/10 rounded-lg p-2.5 text-xs font-bold text-slate-300"
          >
            <option value="thanh_lap">Thành lập</option>
            <option value="mua_ban">Mua bán</option>
            <option value="cho_thue">Cho thuê</option>
            <option value="lao_dong">Lao động</option>
            <option value="vay_von">Vay vốn</option>
          </select>
        </div>
        <button 
          onClick={fetchChecklists}
          className="py-2.5 bg-legal-gold text-legal-navy rounded-lg font-bold hover:scale-[1.02] active:scale-[0.98] transition-all"
        >
          Tải biểu mẫu
        </button>
      </div>

      <div className="space-y-8">
        <div className="flex items-center justify-between">
           <h3 className="text-sm font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
             <CheckSquare className="text-legal-gold" size={18} />
             Danh sách tuân thủ pháp luật
           </h3>
           <button className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-xs font-bold text-slate-300 hover:bg-white/10 transition-all">
             <Printer size={16} />
             In danh sách
           </button>
        </div>

        <div className="space-y-6">
          {isLoading ? (
             Array(2).fill(0).map((_, i) => <div key={i} className="glass-card h-64 animate-skeleton" />)
          ) : checklists.map((cl) => (
             <div key={cl.id} className="glass-card overflow-hidden">
                <div className="p-6 bg-white/5 border-b border-white/10 flex items-center justify-between">
                   <div className="flex items-center gap-4">
                      <h4 className="font-bold text-white text-lg">{cl.name}</h4>
                      <span className="px-2 py-0.5 bg-legal-gold/20 text-legal-gold rounded text-[10px] font-bold uppercase">{cl.priority}</span>
                   </div>
                   <p className="text-[10px] text-slate-500 italic max-w-sm text-right">"{cl.description}"</p>
                </div>
                <div className="p-8 space-y-10">
                   {cl.categories.map((cat, ci) => (
                     <div key={ci} className="space-y-4">
                        <h5 className="text-xs font-bold text-legal-gold uppercase tracking-widest pb-2 border-b border-white/5">{cat.name}</h5>
                        <div className="space-y-4">
                           {cat.items.map((item, ii) => (
                             <div key={ii} className="flex items-start gap-4 group">
                                <div className="mt-1 w-5 h-5 rounded border-2 border-white/10 flex items-center justify-center text-transparent group-hover:text-legal-gold transition-all">
                                   <CheckCircle2 size={12} />
                                </div>
                                <div className="flex-1 min-w-0">
                                   <div className="flex items-center gap-3 mb-1">
                                      <p className="text-sm text-slate-200 group-hover:text-white transition-colors">{item.description}</p>
                                      {item.is_required && (
                                        <span className="px-1.5 py-0.5 bg-legal-danger/20 text-legal-danger rounded text-[8px] font-bold uppercase">Bắt buộc</span>
                                      )}
                                   </div>
                                   <div className="flex items-center gap-3">
                                      <span className="text-[10px] bg-white/5 px-1.5 py-0.5 rounded text-slate-500">#{item.related_law}</span>
                                      <span className="text-[10px] text-slate-400 italic flex items-center gap-1">
                                         <Clock size={10} />
                                         Deadline: {item.deadline_note}
                                      </span>
                                   </div>
                                </div>
                                <button className="p-1 opacity-0 group-hover:opacity-100 transition-opacity text-slate-600 hover:text-white">
                                   <Lock size={14} />
                                </button>
                             </div>
                           ))}
                        </div>
                     </div>
                   ))}
                </div>
                <div className="px-8 py-4 bg-white/5 border-t border-white/10 flex flex-wrap gap-2">
                   <p className="text-[10px] font-bold text-slate-600 uppercase tracking-widest mr-2 self-center">Căn cứ nguồn:</p>
                   {cl.related_laws.map(rl => (
                     <span key={rl} className="px-2 py-0.5 bg-white/5 border border-white/10 rounded text-[9px] text-slate-500 font-mono italic">[{rl}]</span>
                   ))}
                </div>
             </div>
          ))}
        </div>
      </div>
    </div>
  );
}
