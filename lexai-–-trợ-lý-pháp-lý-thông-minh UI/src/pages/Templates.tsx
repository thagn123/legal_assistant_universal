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
  Sparkles,
  X,
  Scale
} from 'lucide-react';
import { apiFetch, TemplateRecommendation, logInteraction } from '../lib/api';
import { cn } from '../lib/api';

// ---------------------------------------------------------------------------
// Preview modal
// ---------------------------------------------------------------------------

function TemplatePreviewModal({ tpl, onClose }: { tpl: TemplateRecommendation; onClose: () => void }) {
  const downloadTemplate = () => {
    logInteraction({ action_type: 'download', context: { contract_type: tpl.contract_type, industry: tpl.industry, template_id: tpl.id } });
    const lines = [
      `MẪU HỢP ĐỒNG: ${tpl.name.toUpperCase()}`,
      `Ngành nghề: ${tpl.industry}`,
      `Loại hợp đồng: ${tpl.contract_type}`,
      '',
      `Mô tả: ${tpl.description}`,
      '',
      '=== ĐIỀU KHOẢN CHỦ CHỐT ===',
      ...tpl.key_clauses.map((c, i) => `${i + 1}. ${c}`),
      '',
      '=== VĂN BẢN PHÁP LUẬT THAM CHIẾU ===',
      ...tpl.related_laws.map(l => `- ${l}`),
      '',
      '---',
      tpl.download_hint,
      '',
      '[Phần nội dung hợp đồng cụ thể sẽ được điền theo tình huống thực tế]',
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lexai_mau_${tpl.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-legal-navy border border-white/10 rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 bg-white/5 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Scale size={18} className="text-legal-gold" />
            <div>
              <h3 className="text-sm font-bold text-white">{tpl.name}</h3>
              <p className="text-[10px] text-slate-500">{tpl.industry} · {tpl.contract_type}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-500 hover:text-white transition-colors rounded-lg hover:bg-white/10">
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 max-h-[65vh] overflow-y-auto">
          <p className="text-sm text-slate-300 leading-relaxed">{tpl.description}</p>

          <div className="space-y-3">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Điều khoản chủ chốt</p>
            <div className="space-y-2">
              {tpl.key_clauses.map((clause, i) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-white/5 border border-white/10 rounded-xl">
                  <span className="text-[10px] font-bold text-legal-gold shrink-0 mt-0.5">{i + 1}.</span>
                  <p className="text-xs text-slate-300 leading-relaxed">{clause}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Văn bản pháp luật tham chiếu</p>
            <div className="flex flex-wrap gap-2">
              {tpl.related_laws.map(law => (
                <span key={law} className="px-2 py-1 bg-legal-gold/10 border border-legal-gold/20 rounded text-[10px] text-legal-gold font-mono">#{law}</span>
              ))}
            </div>
          </div>

          <div className="p-4 bg-legal-gold/5 border border-legal-gold/20 rounded-xl">
            <p className="text-xs text-slate-400 italic">💡 {tpl.download_hint}</p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-white/5 border-t border-white/10 flex justify-end gap-3">
          <button
            onClick={downloadTemplate}
            className="flex items-center gap-2 px-4 py-2 bg-legal-gold text-legal-navy rounded-xl text-xs font-bold hover:scale-105 transition-all"
          >
            <Download size={14} /> Tải mẫu
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white/5 border border-white/10 text-slate-300 rounded-xl text-xs font-bold hover:bg-white/10 transition-all"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function Templates() {
  const [industry, setIndustry] = useState('bat_dong_san');
  const [context, setContext] = useState('');
  const [templates, setTemplates] = useState<TemplateRecommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [previewTpl, setPreviewTpl] = useState<TemplateRecommendation | null>(null);

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

  useEffect(() => { fetchTemplates(); }, []);

  const downloadTemplate = (tpl: TemplateRecommendation) => {
    logInteraction({ action_type: 'download', context: { contract_type: tpl.contract_type, industry: tpl.industry, template_id: tpl.id } });
    const lines = [
      `MẪU HỢP ĐỒNG: ${tpl.name.toUpperCase()}`,
      `Ngành nghề: ${tpl.industry} · ${tpl.contract_type}`,
      `Mô tả: ${tpl.description}`,
      '',
      '=== ĐIỀU KHOẢN CHỦ CHỐT ===',
      ...tpl.key_clauses.map((c, i) => `${i + 1}. ${c}`),
      '',
      '=== VĂN BẢN PHÁP LUẬT THAM CHIẾU ===',
      ...tpl.related_laws.map(l => `- ${l}`),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lexai_mau_${tpl.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8 space-y-12 animate-in fade-in duration-500">
      {previewTpl && <TemplatePreviewModal tpl={previewTpl} onClose={() => setPreviewTpl(null)} />}

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
          ) : templates.length === 0 ? (
            <div className="py-16 text-center text-slate-500 opacity-30">
              <Sparkles size={48} className="mx-auto mb-4" />
              <p className="text-sm">Chưa có mẫu nào. Hãy chọn ngành nghề và bấm "Tìm mẫu".</p>
            </div>
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
                  <button
                    onClick={() => downloadTemplate(tpl)}
                    className="w-full py-2 bg-legal-gold text-legal-navy rounded-lg font-bold text-xs flex items-center justify-center gap-2 hover:scale-[1.02] transition-all"
                  >
                    <Download size={14} /> Tải mẫu
                  </button>
                  <button
                    onClick={() => setPreviewTpl(tpl)}
                    className="w-full py-2 bg-white/5 border border-white/10 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-2 hover:bg-white/10 transition-all"
                  >
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
