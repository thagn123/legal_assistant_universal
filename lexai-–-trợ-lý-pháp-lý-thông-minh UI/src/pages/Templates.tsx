/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { 
  Search, 
  FileCheck, 
  Download, 
  Eye, 
  Plus,
  Info,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { apiFetch, TemplateRecommendation } from '../lib/api';

export function Templates() {
  const [industry, setIndustry] = useState('bat_dong_san');
  const [context, setContext] = useState('');
  const [templates, setTemplates] = useState<TemplateRecommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchTemplates = async () => {
    setIsLoading(true);
    try {
      const data = await apiFetch<TemplateRecommendation[]>('/recommendations/templates', {
        method: 'POST',
        body: JSON.stringify({ context, industry })
      });
      setTemplates(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  return (
    <div className="p-8 space-y-12 animate-in fade-in duration-500">
      <div className="max-w-4xl mx-auto glass-card p-8 space-y-6">
        <div className="space-y-4">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Ngữ cảnh hợp đồng</label>
          <textarea 
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="Mô tả mục đích hợp đồng của bạn... (VD: Hợp đồng thuê mặt bằng kinh doanh tại Quận 1, thời hạn 5 năm)"
            className="w-full h-24 bg-legal-navy/50 border border-white/10 rounded-xl p-4 text-sm focus:border-legal-gold focus:ring-1 focus:ring-legal-gold transition-all resize-none"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Ngành nghề</label>
            <select 
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="w-full bg-legal-navy/50 border border-white/10 rounded-lg p-2.5 text-xs font-bold text-slate-300 focus:border-legal-gold transition-all"
            >
              <option value="bat_dong_san">Bất động sản</option>
              <option value="lao_dong">Lao động</option>
              <option value="thuong_mai">Thương mại</option>
              <option value="dich_vu">Dịch vụ</option>
              <option value="tai_chinh">Tài chính</option>
            </select>
          </div>
          <div className="flex items-end">
            <button 
              onClick={fetchTemplates}
              className="w-full py-2.5 bg-legal-gold text-legal-navy rounded-lg font-bold hover:scale-[1.02] active:scale-[0.98] transition-all"
            >
              Tìm mẫu phù hợp
            </button>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
           <h3 className="text-sm font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
             <Sparkles className="text-legal-gold" size={18} />
             Mẫu hợp đồng tối ưu cho bạn
           </h3>
           <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">{templates.length} kết quả</span>
        </div>

        <div className="grid grid-cols-1 gap-6">
          {isLoading ? (
            Array(3).fill(0).map((_, i) => <div key={i} className="glass-card h-48 animate-skeleton" />)
          ) : templates.map((tpl) => (
            <div key={tpl.id} className="glass-card p-8 flex flex-col md:flex-row gap-8 hover:border-legal-gold/30 transition-all group">
               <div className="flex-1 space-y-4">
                  <div className="flex items-center gap-2">
                     <span className="px-2 py-0.5 bg-legal-gold/20 text-legal-gold rounded text-[9px] font-bold uppercase">{tpl.industry}</span>
                     <span className="px-2 py-0.5 bg-white/5 border border-white/10 text-slate-400 rounded text-[9px] font-bold uppercase">{tpl.contract_type}</span>
                  </div>
                  <h4 className="text-xl font-bold text-white group-hover:text-legal-gold transition-colors">{tpl.name}</h4>
                  <p className="text-xs text-slate-400 leading-relaxed max-w-2xl">{tpl.description}</p>
                  
                  <div className="flex flex-wrap gap-2 pt-2">
                    {tpl.related_laws.map(law => (
                      <span key={law} className="px-2 py-1 bg-white/5 border border-white/10 rounded text-[10px] text-slate-500">#{law}</span>
                    ))}
                  </div>
               </div>

               <div className="w-full md:w-72 bg-white/5 rounded-2xl p-6 border border-white/10 space-y-4">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 border-b border-white/5 pb-2">Điều khoản chủ chốt</p>
                  <ul className="space-y-2">
                    {tpl.key_clauses.map((clause, i) => (
                      <li key={i} className="flex gap-2 text-[11px] text-slate-300">
                        <FileCheck size={14} className="text-legal-gold shrink-0" />
                        {clause}
                      </li>
                    ))}
                  </ul>
                  <div className="pt-4 mt-auto space-y-3">
                    <p className="text-[10px] text-slate-500 italic text-center">"{tpl.download_hint}"</p>
                    <button className="w-full py-2 bg-legal-gold text-legal-navy rounded-lg font-bold text-xs flex items-center justify-center gap-2">
                      <Download size={14} /> Tải mẫu
                    </button>
                    <button className="w-full py-2 bg-white/5 border border-white/10 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-2 hover:bg-white/10">
                      <Eye size={14} /> Xem trước
                    </button>
                  </div>
               </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
