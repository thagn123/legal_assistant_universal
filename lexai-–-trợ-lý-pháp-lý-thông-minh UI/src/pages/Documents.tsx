/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Search, FileText, LayoutGrid, List, Info,
  Download, X, Upload, Loader2, CheckCircle2,
  ExternalLink, AlertCircle
} from 'lucide-react';
import { apiFetch, DocRecommendation, CaseRecommendation, LAW_TYPE_LABELS, getUserId, getDocumentContent, downloadDocument, DocumentContent, logInteraction } from '../lib/api';
import { LawTypeBadge, ScoreBadge, InteractionButtons } from '../components/ui/Shared';
import { cn, API_BASE } from '../lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface UserDoc {
  doc_id: string;
  filename: string;
  status: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Detail modal
// ---------------------------------------------------------------------------

function DocDetailModal({ doc, onClose }: { doc: DocRecommendation; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState<'rec' | 'content'>('rec');
  const [content, setContent] = useState<DocumentContent | null>(null);
  const [contentLoading, setContentLoading] = useState(false);

  const loadContent = async () => {
    if (content) return;
    setContentLoading(true);
    try {
      const data = await getDocumentContent(doc.id);
      setContent(data);
    } catch {
      setContent({ doc_id: doc.id, filename: '', status: '', chunk_count: 0, law_type: '', extracted_text: 'Không thể tải nội dung tài liệu.' });
    } finally {
      setContentLoading(false);
    }
  };

  const handleTabChange = (tab: 'rec' | 'content') => {
    setActiveTab(tab);
    if (tab === 'content') loadContent();
  };

  const handleDownload = () => {
    logInteraction({ action_type: 'download', doc_id: doc.id });
    downloadDocument(doc.id);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-legal-navy border border-white/10 rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-6 py-4 bg-white/5 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText size={18} className="text-legal-gold" />
            <LawTypeBadge type={doc.law_type} />
            <ScoreBadge score={doc.final_score} />
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-500 hover:text-white transition-colors rounded-lg hover:bg-white/10">
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/10 bg-white/3">
          <button
            onClick={() => handleTabChange('rec')}
            className={cn("px-5 py-3 text-xs font-bold uppercase tracking-wider transition-all", activeTab === 'rec' ? 'text-legal-gold border-b-2 border-legal-gold' : 'text-slate-500 hover:text-white')}
          >
            Đề xuất
          </button>
          <button
            onClick={() => handleTabChange('content')}
            className={cn("px-5 py-3 text-xs font-bold uppercase tracking-wider transition-all", activeTab === 'content' ? 'text-legal-gold border-b-2 border-legal-gold' : 'text-slate-500 hover:text-white')}
          >
            Nội dung văn bản
          </button>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          {activeTab === 'rec' && (
            <div className="space-y-6">
              <div className="space-y-2">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">ID tài liệu</p>
                <p className="text-xs font-mono text-slate-400 break-all">{doc.id}</p>
              </div>
              <div className="space-y-2">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Nội dung trích xuất</p>
                <div className="p-4 bg-white/5 border border-white/10 rounded-xl">
                  <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">{doc.snippet}</p>
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Lý do đề xuất</p>
                <p className="text-xs text-slate-400 italic">"{doc.reason}"</p>
              </div>
              <div className="space-y-3">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Cơ cấu điểm số</p>
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(doc.scores).map(([key, val]) => (
                    <div key={key} className="p-3 bg-white/5 rounded-lg border border-white/10">
                      <p className="text-[9px] text-slate-500 uppercase mb-2">{key}</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                          <div className="h-full bg-legal-gold/70 rounded-full" style={{ width: `${val * 100}%` }} />
                        </div>
                        <span className="text-[10px] font-mono text-slate-300">{(val * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'content' && (
            <div>
              {contentLoading ? (
                <div className="flex items-center justify-center py-12 gap-3 text-slate-400">
                  <Loader2 size={18} className="animate-spin" />
                  <span className="text-sm">Đang tải nội dung...</span>
                </div>
              ) : content ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                    <span>{content.chunk_count} đoạn văn bản</span>
                    <span>{content.law_type && (LAW_TYPE_LABELS[content.law_type] || content.law_type)}</span>
                  </div>
                  <div className="bg-white/5 border border-white/10 rounded-xl p-4 max-h-[45vh] overflow-y-auto">
                    <pre className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap font-sans">
                      {content.extracted_text || 'Nội dung văn bản chưa được xử lý.'}
                    </pre>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-white/5 border-t border-white/10 flex justify-end gap-3">
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-4 py-2 bg-legal-gold text-legal-navy rounded-xl text-xs font-bold hover:scale-105 transition-all"
          >
            <Download size={14} /> Tải file gốc
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
// User document upload section
// ---------------------------------------------------------------------------

function UserDocUpload() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [userDocs, setUserDocs] = useState<UserDoc[]>([]);
  const [uploadMsg, setUploadMsg] = useState('');

  const loadUserDocs = async () => {
    try {
      const docs = await apiFetch<UserDoc[]>('/documents');
      setUserDocs(Array.isArray(docs) ? docs : []);
    } catch { /* ignore */ }
  };

  useEffect(() => { loadUserDocs(); }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const resp = await fetch(`${API_BASE}/documents/upload-file`, {
        method: 'POST',
        headers: { 'X-User-ID': getUserId() },
        body: formData,
      });
      if (!resp.ok) throw new Error(`${resp.status}`);
      setUploadMsg(`Đã tải lên: ${file.name}`);
      await loadUserDocs();
    } catch (e: any) {
      setUploadMsg(`Lỗi: ${e.message}`);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const statusColor = (s: string) =>
    s === 'complete' ? 'text-legal-success' : s === 'failed' ? 'text-legal-danger' : 'text-legal-warning';

  return (
    <div className="glass-card p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Upload size={16} className="text-legal-gold" />
          Tài liệu của bạn
        </h3>
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-2 px-4 py-2 bg-legal-gold text-legal-navy rounded-xl text-xs font-bold hover:scale-105 transition-all disabled:opacity-50"
        >
          {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
          Tải lên tài liệu
        </button>
        <input ref={fileRef} type="file" accept=".pdf,.docx,.doc,.txt,.html" className="hidden" onChange={handleFileUpload} />
      </div>

      {uploadMsg && (
        <div className={cn("flex items-center gap-2 text-xs px-3 py-2 rounded-lg", uploadMsg.startsWith('Lỗi') ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-legal-success/10 text-legal-success border border-legal-success/20')}>
          {uploadMsg.startsWith('Lỗi') ? <AlertCircle size={12} /> : <CheckCircle2 size={12} />}
          {uploadMsg}
        </div>
      )}

      {userDocs.length > 0 ? (
        <div className="space-y-2">
          {userDocs.slice(0, 8).map(doc => (
            <div key={doc.doc_id} className="flex items-center justify-between p-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all">
              <div className="flex items-center gap-3 min-w-0">
                <FileText size={14} className="text-legal-gold shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs font-bold text-white truncate">{doc.filename}</p>
                  <p className="text-[10px] text-slate-500">{new Date(doc.created_at).toLocaleDateString('vi-VN')}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={cn("text-[10px] font-bold uppercase", statusColor(doc.status))}>
                  {doc.status === 'complete' ? '✓ Xong' : doc.status === 'failed' ? '✗ Lỗi' : '⏳ Xử lý'}
                </span>
                <button
                  onClick={() => { logInteraction({ action_type: 'download', doc_id: doc.doc_id }); downloadDocument(doc.doc_id); }}
                  className="p-1.5 text-slate-500 hover:text-legal-gold hover:bg-white/5 rounded-lg transition-all"
                  title="Tải file gốc"
                >
                  <Download size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-slate-500 text-center py-4">Chưa có tài liệu nào. Tải lên để xây dựng kho tài liệu riêng.</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function Documents() {
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState('all');
  const [docs, setDocs] = useState<DocRecommendation[]>([]);
  const [cases, setCases] = useState<CaseRecommendation[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [detailDoc, setDetailDoc] = useState<DocRecommendation | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

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

  useEffect(() => { fetchDocs(); }, []);

  const downloadCase = (c: CaseRecommendation) => {
    const text = `Vụ việc: ${c.title}\nĐộ tương đồng: ${(c.similarity_score * 100).toFixed(0)}%\n\nTóm tắt tình huống:\n${c.situation_summary}\n\nKết quả: ${c.outcome}\n\nBài học: ${c.lesson}`;
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `anle_${c.id.slice(0, 16)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8 space-y-12 animate-in fade-in duration-500">
      {/* DETAIL MODAL */}
      {detailDoc && <DocDetailModal doc={detailDoc} onClose={() => setDetailDoc(null)} />}

      {/* USER UPLOAD SECTION */}
      <UserDocUpload />

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
            <button
              type="button"
              onClick={() => setViewMode('grid')}
              aria-pressed={viewMode === 'grid'}
              className={cn('p-1.5 rounded-md transition-colors', viewMode === 'grid' ? 'text-legal-gold bg-white/5' : 'text-slate-500 hover:text-white')}
              title="Xem dạng lưới"
            >
              <LayoutGrid size={16} />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('list')}
              aria-pressed={viewMode === 'list'}
              className={cn('p-1.5 rounded-md transition-colors', viewMode === 'list' ? 'text-legal-gold bg-white/5' : 'text-slate-500 hover:text-white')}
              title="Xem dạng danh sách"
            >
              <List size={16} />
            </button>
          </div>
        </div>

        <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6' : 'space-y-4'}>
          {isSearching ? (
            Array(6).fill(0).map((_, i) => <div key={i} className="glass-card aspect-[4/3] animate-skeleton" />)
          ) : docs.length === 0 ? (
            <div className="col-span-3 py-12 text-center text-slate-500">
              <FileText size={48} className="mx-auto mb-4 opacity-20" />
              <p className="text-sm">Chưa có tài liệu nào. Hãy tìm kiếm hoặc tải lên tài liệu.</p>
            </div>
          ) : docs.map((doc) => (
            <div key={doc.id} className={cn('glass-card p-6 flex group hover:border-legal-gold/30 transition-all', viewMode === 'grid' ? 'flex-col' : 'flex-col md:flex-row md:items-start md:gap-6')}>
              <div className="flex items-center justify-between mb-4">
                <LawTypeBadge type={doc.law_type} />
                <ScoreBadge score={doc.final_score} />
              </div>

              <div className="flex-1">
                <h4 className="text-[10px] font-mono text-slate-500 uppercase tracking-tighter mb-1 truncate">{doc.id}</h4>
                <p className="text-sm text-slate-200 line-clamp-3 leading-relaxed mb-4">"{doc.snippet}"</p>

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
                  <button
                    onClick={() => { logInteraction({ action_type: 'view', doc_id: doc.id }); setDetailDoc(doc); }}
                    className="text-xs font-bold text-legal-gold hover:underline flex items-center gap-1"
                  >
                    Chi tiết <ExternalLink size={10} />
                  </button>
                  <InteractionButtons docId={doc.id} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* SIMILAR CASES */}
      {cases.length > 0 && (
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
                <button
                  onClick={() => downloadCase(c)}
                  className="p-2 text-slate-500 hover:text-legal-gold hover:bg-white/5 rounded-lg transition-all"
                  title="Tải xuống"
                >
                  <Download size={18} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
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
