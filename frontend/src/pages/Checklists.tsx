/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
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
import { apiFetch, Checklist, getChecklistProgress, saveChecklistProgress, logInteraction } from '../lib/api';
import { cn } from '../lib/api';

export function Checklists() {
  const [businessType, setBusinessType] = useState('cong_ty_tnhh');
  const [transactionType, setTransactionType] = useState('thanh_lap');
  const [checklists, setChecklists] = useState<Checklist[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  // checked items: key = `${checklistId}:${categoryIdx}:${itemIdx}`
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const saveTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const fetchChecklists = async () => {
    setIsLoading(true);
    try {
      const data = await apiFetch<Checklist[]>('/recommendations/checklists', {
        method: 'POST',
        body: JSON.stringify({ business_type: businessType, transaction_type: transactionType })
      });
      const cls = Array.isArray(data) ? data : [];
      setChecklists(cls);
      logInteraction({ action_type: 'view', context: { business_type: businessType, transaction_type: transactionType } });

      // Load persisted progress for each checklist
      const initialChecked = new Set<string>();
      await Promise.all(cls.map(async (cl) => {
        try {
          const prog = await getChecklistProgress(cl.id);
          prog.checked_items.forEach(k => initialChecked.add(k));
        } catch { /* ignore if no progress saved yet */ }
      }));
      setChecked(initialChecked);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchChecklists(); }, []);

  const toggleItem = (key: string) => {
    setChecked(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);

      // Debounce save for the affected checklist
      const checklistId = key.split(':')[0];
      if (saveTimers.current[checklistId]) clearTimeout(saveTimers.current[checklistId]);
      saveTimers.current[checklistId] = setTimeout(() => {
        const checkedForList = [...next].filter(k => k.startsWith(checklistId + ':'));
        saveChecklistProgress(checklistId, checkedForList).catch(() => {});
      }, 800);

      return next;
    });
  };

  const handlePrint = () => window.print();

  // progress per checklist
  const getProgress = (cl: Checklist) => {
    const total = cl.categories.reduce((s, cat) => s + cat.items.length, 0);
    const done = cl.categories.reduce((s, cat, ci) =>
      s + cat.items.filter((_, ii) => checked.has(`${cl.id}:${ci}:${ii}`)).length, 0);
    return { total, done };
  };

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
          <button
            onClick={handlePrint}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-xs font-bold text-slate-300 hover:bg-white/10 transition-all"
          >
            <Printer size={16} />
            In danh sách
          </button>
        </div>

        <div className="space-y-6">
          {isLoading ? (
            Array(2).fill(0).map((_, i) => <div key={i} className="glass-card h-64 animate-skeleton" />)
          ) : checklists.length === 0 ? (
            <div className="py-16 text-center text-slate-500 opacity-30">
              <CheckSquare size={48} className="mx-auto mb-4" />
              <p className="text-sm">Chưa có biểu mẫu nào. Chọn loại hình và bấm "Tải biểu mẫu".</p>
            </div>
          ) : checklists.map((cl) => {
            const { total, done } = getProgress(cl);
            const pct = total > 0 ? Math.round((done / total) * 100) : 0;

            return (
              <div key={cl.id} className="glass-card overflow-hidden">
                <div className="p-6 bg-white/5 border-b border-white/10">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-4">
                      <h4 className="font-bold text-white text-lg">{cl.name}</h4>
                      <span className="px-2 py-0.5 bg-legal-gold/20 text-legal-gold rounded text-[10px] font-bold uppercase">{cl.priority}</span>
                    </div>
                    <p className="text-[10px] text-slate-500 italic max-w-sm text-right hidden md:block">"{cl.description}"</p>
                  </div>
                  {/* Progress bar */}
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-legal-gold rounded-full transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-[10px] font-mono text-slate-400 shrink-0">{done}/{total} hoàn thành</span>
                  </div>
                </div>

                <div className="p-8 space-y-10">
                  {cl.categories.map((cat, ci) => (
                    <div key={ci} className="space-y-4">
                      <h5 className="text-xs font-bold text-legal-gold uppercase tracking-widest pb-2 border-b border-white/5">{cat.name}</h5>
                      <div className="space-y-4">
                        {cat.items.map((item, ii) => {
                          const key = `${cl.id}:${ci}:${ii}`;
                          const isChecked = checked.has(key);
                          return (
                            <div
                              key={ii}
                              className={cn("flex items-start gap-4 group cursor-pointer rounded-xl p-2 -mx-2 transition-all", isChecked ? "opacity-60" : "hover:bg-white/5")}
                              onClick={() => toggleItem(key)}
                            >
                              <div className={cn(
                                "mt-1 w-5 h-5 rounded border-2 flex items-center justify-center shrink-0 transition-all",
                                isChecked
                                  ? "bg-legal-gold border-legal-gold text-legal-navy"
                                  : "border-white/20 text-transparent group-hover:border-legal-gold/50"
                              )}>
                                <CheckCircle2 size={12} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-3 mb-1">
                                  <p className={cn("text-sm transition-colors", isChecked ? "line-through text-slate-500" : "text-slate-200 group-hover:text-white")}>
                                    {item.description}
                                  </p>
                                  {item.is_required && (
                                    <span className="px-1.5 py-0.5 bg-legal-danger/20 text-legal-danger rounded text-[8px] font-bold uppercase shrink-0">Bắt buộc</span>
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
                              {isChecked && (
                                <CheckCircle2 size={16} className="text-legal-gold shrink-0 mt-1" />
                              )}
                            </div>
                          );
                        })}
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
            );
          })}
        </div>
      </div>
    </div>
  );
}
