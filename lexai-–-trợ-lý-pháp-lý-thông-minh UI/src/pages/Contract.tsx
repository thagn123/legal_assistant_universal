/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import {
  FileText,
  Search,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Download,
  Scale,
  Zap,
  Wrench,
  ChevronDown,
  Info,
  Check,
  Upload,
  FilePlus2,
  X,
  Bookmark,
} from 'lucide-react';
import { apiFetch, ContractAnalysisResult, API_BASE, getUserId, saveAnalysis } from '../lib/api';
import { cn } from '../lib/api';
import { useToast } from '../lib/useToast';
import { ToastContainer } from '../components/ui/ToastContainer';
import { StagePipeline } from '../components/ui/StagePipeline';
import { getAnalysisContext } from '../lib/analysisContext';

const contractTypes = [
  { id: 'thue_nha', label: 'Thuê nhà' },
  { id: 'lao_dong', label: 'Lao động' },
  { id: 'mua_ban', label: 'Mua bán' },
  { id: 'dich_vu', label: 'Dịch vụ' },
  { id: 'vay_von', label: 'Vay vốn' },
  { id: 'khac', label: 'Khác' },
];

const analysis_stages = [
  { id: 1, name: 'Lexical Analysis' },
  { id: 2, name: 'Entity Extraction' },
  { id: 3, name: 'Clause Segment' },
  { id: 4, name: 'Risk Scoring' },
  { id: 5, name: 'LLM Comparison' },
  { id: 6, name: 'Validation' },
];

function contractTypeFromDomain(domain?: string): string {
  if (domain === 'lao_dong') return 'lao_dong';
  if (domain === 'dat_dai') return 'mua_ban';
  if (domain === 'hop_dong') return 'dich_vu';
  return 'thue_nha';
}

export function Contract() {
  const location = useLocation();
  const analysisContext = getAnalysisContext(location.state);
  const [content, setContent] = useState(() => analysisContext.summary || '');
  const [type, setType] = useState(() => contractTypeFromDomain(analysisContext.domain));
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  const [result, setResult] = useState<ContractAnalysisResult | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState('');
  const [uploadedFilename, setUploadedFilename] = useState('');
  const [saved, setSaved] = useState(false);
  const { toasts, toast, dismiss } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileExtract = useCallback(async (file: File) => {
    setExtractError('');
    setUploadedFilename(file.name);
    const suffix = file.name.split('.').pop()?.toLowerCase() || '';

    if (suffix === 'txt') {
      const text = await file.text();
      setContent(text.slice(0, 60000));
      return;
    }

    // PDF / DOCX / DOC — send to backend extraction endpoint
    setExtracting(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const resp = await fetch(`${API_BASE}/contract/extract-text`, {
        method: 'POST',
        headers: { 'X-User-ID': getUserId() },
        body: formData,
      });
      const data = await resp.json();
      if (data.error) {
        setExtractError(data.error);
        setUploadedFilename('');
      } else {
        setContent(data.text || '');
      }
    } catch (e: any) {
      setExtractError(`Không thể trích xuất: ${e.message}`);
      setUploadedFilename('');
    } finally {
      setExtracting(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileExtract(file);
  }, [handleFileExtract]);

  const downloadReport = () => {
    if (!result) return;
    const lines = [
      `BÁO CÁO RÀ SOÁT HỢP ĐỒNG — LexAI`,
      `Loại hợp đồng: ${result.loai_hop_dong}`,
      `Các bên: ${result.cac_ben.join(', ')}`,
      `Phạm vi: ${result.pham_vi}`,
      `Giá trị: ${result.gia_tri}`,
      `Điểm tuân thủ: ${result.compliance_score}/100`,
      '',
      '=== ĐIỀU KHOẢN RỦI RO ===',
      ...result.risk_clauses.map((c, i) =>
        `${i + 1}. ${c.name}\n   Rủi ro: ${c.risk}\n   Căn cứ: ${c.legal_basis}\n   Hiện tại: ${c.before}\n   Đề xuất: ${c.after}`
      ),
      '',
      '=== ĐIỀU KHOẢN CÒN THIẾU ===',
      ...result.missing_clauses.map((c, i) => `${i + 1}. ${c}`),
      '',
      '=== KHUYẾN NGHỊ ===',
      ...result.recommendations.map((r, i) => `${i + 1}. ${r}`),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'lexai_contract_report.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleAnalyze = async () => {
    if (!content.trim()) return;

    setResult(null);
    setIsAnalyzing(true);
    setSaved(false);
    setCurrentStage(1);
    
    const stageInterval = setInterval(() => {
      setCurrentStage(prev => (prev < 5 ? prev + 1 : prev));
    }, 1500);

    try {
      const data = await apiFetch<ContractAnalysisResult>('/agent/contract', {
        method: 'POST',
        body: JSON.stringify({ content, type })
      });
      clearInterval(stageInterval);
      setCurrentStage(6);
      setTimeout(() => {
        setResult(data);
        setIsAnalyzing(false);
        setCurrentStage(0);
      }, 500);
    } catch (e) {
      console.error(e);
      setIsAnalyzing(false);
      setCurrentStage(0);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <ToastContainer toasts={toasts} dismiss={dismiss} />
      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
          <FileText className="text-legal-gold" size={28} />
          Rà soát hợp đồng thông minh
        </h2>
        <p className="text-slate-400 text-sm">Phân tích rủi ro và tuân thủ pháp luật Việt Nam dựa trên AI</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-card p-8 space-y-6">
            <div className="space-y-4">
              {/* FILE UPLOAD ZONE */}
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  "border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all",
                  isDragging ? "border-legal-gold bg-legal-gold/10" : "border-white/10 hover:border-legal-gold/40 hover:bg-white/[0.03]"
                )}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.pdf,.docx,.doc"
                  className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileExtract(f); }}
                />
                {extracting ? (
                  <div className="flex items-center justify-center gap-2 text-legal-gold">
                    <Loader2 size={18} className="animate-spin" />
                    <span className="text-xs font-bold">Đang trích xuất nội dung...</span>
                  </div>
                ) : uploadedFilename ? (
                  <div className="flex items-center justify-center gap-2">
                    <CheckCircle2 size={16} className="text-legal-success" />
                    <span className="text-xs font-bold text-legal-success">{uploadedFilename}</span>
                    <button onClick={(e) => { e.stopPropagation(); setContent(''); setUploadedFilename(''); }} className="ml-2 text-slate-500 hover:text-white">
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <FilePlus2 size={24} className="mx-auto text-slate-500" />
                    <p className="text-xs text-slate-400">Kéo thả hoặc <span className="text-legal-gold font-bold">bấm để tải lên</span> file hợp đồng</p>
                    <p className="text-[10px] text-slate-600">Hỗ trợ: TXT, PDF, DOCX, DOC</p>
                  </div>
                )}
              </div>
              {extractError && (
                <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                  <AlertTriangle size={14} />
                  {extractError}
                </div>
              )}

              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Nội dung hợp đồng</label>
                <span className="text-[10px] text-slate-500 font-mono">{content.length} ký tự</span>
              </div>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Dán nội dung hợp đồng vào đây — hệ thống sẽ phân tích theo pháp luật Việt Nam..."
                className="w-full h-[400px] bg-legal-navy/50 border border-white/10 rounded-xl p-6 text-sm font-mono text-slate-300 focus:border-legal-gold focus:ring-1 focus:ring-legal-gold transition-all resize-none leading-relaxed"
              />
            </div>

            <div className="flex flex-wrap items-center gap-4">
               <div className="flex-1 min-w-[200px] space-y-4">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Loại hợp đồng</label>
                  <select 
                    value={type}
                    onChange={(e) => setType(e.target.value)}
                    className="w-full bg-legal-navy/50 border border-white/10 rounded-lg p-3 text-xs font-bold text-white focus:border-legal-gold transition-all"
                  >
                    {contractTypes.map(t => (
                      <option key={t.id} value={t.id}>{t.label}</option>
                    ))}
                  </select>
               </div>
               <div className="pt-8">
                  <button 
                    onClick={handleAnalyze}
                    disabled={isAnalyzing || !content.trim()}
                    className="px-8 py-3 bg-legal-gold text-legal-navy rounded-xl font-bold flex items-center justify-center gap-3 shadow-lg shadow-legal-gold/20 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:grayscale transition-all sm:w-auto w-full"
                  >
                    {isAnalyzing ? <Loader2 className="animate-spin" size={20} /> : <Search size={20} />}
                    Bắt đầu rà soát
                  </button>
               </div>
            </div>
          </div>

          {isAnalyzing && (
            <div className="glass-card p-6 animate-pulse">
               <div className="flex items-center gap-2 mb-6">
                 <Loader2 className="animate-spin text-legal-gold" size={20} />
                 <span className="text-xs font-bold text-legal-gold uppercase tracking-widest">Hệ thống đang rà soát từng điều khoản...</span>
               </div>
               <StagePipeline currentStage={currentStage} stages={analysis_stages} />
            </div>
          )}

          {result && (
            <div className="space-y-8 pb-12 animate-in fade-in zoom-in-95 duration-500">
               {/* SCORE SECTION */}
               <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="glass-card p-8 flex flex-col items-center justify-center text-center space-y-6">
                     <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest">Điểm tuân thủ</h3>
                     <div className="relative w-32 h-32">
                        <svg className="w-full h-full" viewBox="0 0 100 100">
                          <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
                          <circle 
                            cx="50" cy="50" r="45" fill="none" 
                            stroke={result.compliance_score >= 70 ? '#059669' : result.compliance_score >= 40 ? '#f59e0b' : '#ef4444'} 
                            strokeWidth="10" 
                            strokeDasharray="283"
                            strokeDashoffset={283 - (283 * result.compliance_score) / 100}
                            strokeLinecap="round"
                            className="transition-all duration-1000 ease-out"
                          />
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center">
                          <span className="text-3xl font-bold text-white">{result.compliance_score}</span>
                        </div>
                     </div>
                     <p className="text-xs text-slate-300 font-medium">Hợp đồng của bạn có mức độ rủi ro {result.compliance_score < 40 ? 'CAO' : result.compliance_score < 70 ? 'TRUNG BÌNH' : 'THẤP'}</p>
                  </div>

                  <div className="glass-card p-8 space-y-4">
                     <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest mb-4">Tổng quan hợp đồng</h3>
                     <div className="space-y-3">
                        <SummaryItem label="Loại" value={result.loai_hop_dong} />
                        <SummaryItem label="Các bên" value={result.cac_ben.join(', ')} />
                        <SummaryItem label="Phạm vi" value={result.pham_vi} />
                        <SummaryItem label="Giá trị" value={result.gia_tri} />
                     </div>
                  </div>
               </div>

               {/* RISK CLAUSES */}
               <div className="space-y-6">
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <AlertTriangle className="text-legal-danger" size={20} />
                    Điều khoản rủi ro cao ({result.risk_clauses.length})
                  </h3>
                  <div className="space-y-4">
                    {result.risk_clauses.map((clause, idx) => (
                      <div key={idx} className="glass-card border-l-4 border-l-legal-danger overflow-hidden">
                        <div className="p-6 space-y-4">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <h4 className="text-sm font-bold text-white">{clause.name}</h4>
                            <span className="text-[10px] bg-legal-danger/20 text-legal-danger px-2 py-1 rounded font-bold uppercase tracking-widest">{clause.legal_basis}</span>
                          </div>
                          <p className="text-xs text-slate-400 bg-legal-danger/5 p-3 rounded-lg border border-legal-danger/10">
                            <span className="font-bold text-legal-danger mr-2">Rủi ro:</span>
                            {clause.risk}
                          </p>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                             <div className="space-y-2">
                                <span className="text-[10px] font-bold text-slate-500 uppercase">Hiện tại</span>
                                <div className="p-4 bg-red-900/10 border border-red-500/20 rounded-xl text-xs text-slate-400 line-through">
                                  {clause.before}
                                </div>
                             </div>
                             <div className="space-y-2">
                                <span className="text-[10px] font-bold text-legal-success uppercase">Đề xuất sửa đổi</span>
                                <div className="p-4 bg-emerald-900/10 border border-emerald-500/20 rounded-xl text-xs text-white">
                                  {clause.after}
                                </div>
                             </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
               </div>

               {/* MISSING CLAUSES */}
               <div className="space-y-4">
                 <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Info className="text-legal-warning" size={20} />
                    Điều khoản còn thiếu
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {result.missing_clauses.map((clause, idx) => (
                       <div key={idx} className="p-4 bg-legal-warning/5 border border-legal-warning/20 rounded-2xl flex items-center gap-3">
                          <AlertTriangle className="text-legal-warning shrink-0" size={16} />
                          <span className="text-xs font-bold text-slate-300">{clause}</span>
                       </div>
                    ))}
                  </div>
               </div>
            </div>
          )}
        </div>

        <div className="space-y-8">
           {/* ACTION RECOMMENDATIONS */}
           {result && (
             <div className="glass-card p-6 space-y-6">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Khuyến nghị hành động</h3>
                <div className="space-y-4">
                   {result.recommendations.map((rec, idx) => (
                     <div key={idx} className={cn(
                       "flex gap-3 p-4 rounded-xl border",
                       idx === 0 ? "bg-legal-danger/10 border-legal-danger/20" : "bg-white/5 border-white/10"
                     )}>
                        <div className={cn(
                          "w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0",
                          idx === 0 ? "bg-legal-danger text-white" : "bg-legal-gold text-legal-navy"
                        )}>
                          {idx + 1}
                        </div>
                        <div>
                          {idx === 0 && <span className="text-[10px] font-bold text-legal-danger uppercase block mb-1">Trước khi ký</span>}
                          <p className="text-xs text-slate-300 leading-relaxed font-medium">{rec}</p>
                        </div>
                     </div>
                   ))}
                </div>
                <button onClick={downloadReport} className="w-full py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-xs font-bold text-white flex items-center justify-center gap-3 transition-all">
                  <Download size={16} /> Tải báo cáo phân tích
                </button>
                <button
                  onClick={() => {
                    const title = uploadedFilename || content.slice(0, 60) || 'Hợp đồng';
                    saveAnalysis({ type: 'contract_analysis', title, summary: `Điểm tuân thủ: ${result.compliance_score}/100 · ${result.loai_hop_dong}`, data: result }).then(() => toast('Đã lưu vào lịch sử'));
                    setSaved(true);
                  }}
                  disabled={saved}
                  className="w-full py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-xs font-bold flex items-center justify-center gap-3 transition-all disabled:opacity-60 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30"
                >
                  {saved ? <><Check size={16} className="text-green-400" /> Đã lưu vào lịch sử</> : <><Bookmark size={16} /> Lưu vào lịch sử</>}
                </button>
             </div>
           )}

           {/* TOOL CALLS */}
           {result && (
             <div className="glass-card p-6 space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                    <Zap className="text-legal-success" size={14} fill="currentColor" />
                    AI Insights
                  </h3>
                  <span className="text-[10px] font-mono text-slate-500">gpt-4o-mini</span>
                </div>
                <div className="space-y-4">
                  {result.tool_calls_made.map((tool, i) => (
                    <div key={i} className="flex gap-3 items-start relative pl-4 before:absolute before:left-0 before:top-2 before:bottom-0 before:w-px before:bg-white/10">
                       <Wrench className="text-legal-gold shrink-0 bg-legal-navy p-1 rounded border border-white/10" size={18} />
                       <div className="space-y-1">
                          <h6 className="text-[10px] font-bold text-legal-gold uppercase font-mono">{tool.tool}</h6>
                          <p className="text-[10px] text-slate-500 italic lowercase">{tool.description}</p>
                       </div>
                    </div>
                  ))}
                </div>
             </div>
           )}

           {/* SIDEBAR HELP */}
           {!result && !isAnalyzing && (
             <div className="glass-card p-6 space-y-4">
                <div className="w-12 h-12 bg-legal-gold/10 rounded-xl flex items-center justify-center text-legal-gold">
                  <Scale size={24} />
                </div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Hệ thống ULKA hỗ trợ:</h3>
                <ul className="space-y-3">
                   <HelpItem text="Phát hiện điều khoản bất lợi/vi phạm pháp luật" />
                   <HelpItem text="Kiểm tra đối chiếu với Bộ luật Dân sự 2015" />
                   <HelpItem text="Đề xuất các điều khoản còn thiếu" />
                   <HelpItem text="Gợi ý văn phong pháp lý chuẩn xác" />
                </ul>
             </div>
           )}
        </div>
      </div>
    </div>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-start gap-4 py-2 border-b border-white/5 last:border-0">
      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider shrink-0 mt-1">{label}</span>
      <span className="text-xs text-slate-300 font-medium text-right line-clamp-2">{value}</span>
    </div>
  );
}

function HelpItem({ text }: { text: string }) {
  return (
    <li className="flex items-start gap-2">
      <CheckCircle2 className="text-legal-gold shrink-0 mt-0.5" size={14} />
      <span className="text-xs text-slate-400">{text}</span>
    </li>
  );
}
