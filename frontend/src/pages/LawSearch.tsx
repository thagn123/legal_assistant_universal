/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  BookOpen,
  Search,
  Loader2,
  AlertTriangle,
  ChevronRight,
  Globe,
  User,
  ExternalLink,
  Bookmark,
  Check,
} from 'lucide-react';
import { searchLaws, LawArticle, LawSearchResult, saveAnalysis } from '../lib/api';
import { getContextSummary } from '../lib/analysisContext';
import { useToast } from '../lib/useToast';
import { ToastContainer } from '../components/ui/ToastContainer';

// ── Relevance badge ───────────────────────────────────────────────────────────

function RelevanceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const { bg, text } =
    score >= 0.85 ? { bg: 'bg-green-500/15 border-green-500/30', text: 'text-green-400' } :
    score >= 0.70 ? { bg: 'bg-legal-gold/15 border-legal-gold/30', text: 'text-legal-gold' } :
    score >= 0.55 ? { bg: 'bg-orange-500/15 border-orange-500/30', text: 'text-orange-400' } :
    { bg: 'bg-white/5 border-white/10', text: 'text-slate-400' };
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${bg} ${text} tabular-nums`}>
      {pct}% phù hợp
    </span>
  );
}

// ── Law card ──────────────────────────────────────────────────────────────────

function LawCard({ article, index }: { article: LawArticle; index: number }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="bg-white/5 border border-white/8 rounded-xl overflow-hidden hover:bg-white/8 transition-all">
      <button
        onClick={() => setExpanded(p => !p)}
        className="w-full flex items-start gap-3 p-4 text-left"
      >
        <span className="flex-none w-7 h-7 rounded-full bg-legal-gold/15 text-legal-gold text-[11px] font-bold flex items-center justify-center border border-legal-gold/20 mt-0.5">
          {index + 1}
        </span>
        <div className="flex-1 min-w-0 space-y-1.5">
          {article.law_reference && (
            <p className="text-[11px] font-bold text-legal-gold font-mono tracking-wide">
              {article.law_reference}
            </p>
          )}
          <p className="text-sm text-slate-300 leading-relaxed line-clamp-3">
            {article.snippet}
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-legal-gold/10 text-legal-gold border border-legal-gold/20">
              {article.law_type_label}
            </span>
            <RelevanceBadge score={article.relevance_score} />
            {article.is_global ? (
              <span className="flex items-center gap-1 text-[10px] text-blue-400">
                <Globe size={10} /> Toàn hệ thống
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[10px] text-slate-500">
                <User size={10} /> Tài liệu của bạn
              </span>
            )}
          </div>
        </div>
        <ChevronRight
          size={16}
          className={`flex-none text-slate-500 mt-0.5 transition-transform ${expanded ? 'rotate-90' : ''}`}
        />
      </button>

      {expanded && (
        <div className="border-t border-white/8 p-4 animate-in fade-in duration-200">
          <div className="bg-legal-navy/50 rounded-xl p-4 border border-white/5">
            <p className="text-sm text-slate-300 leading-7 whitespace-pre-wrap">{article.content}</p>
          </div>
          {article.doc_id && (
            <p className="text-[10px] text-slate-600 mt-2">
              doc_id: {article.doc_id} · chunk_id: {article.chunk_id}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

const QUICK_QUERIES = [
  'Thời hiệu khởi kiện tranh chấp hợp đồng',
  'Điều kiện chấm dứt hợp đồng lao động',
  'Thủ tục khiếu nại quyết định hành chính',
  'Quyền sử dụng đất sau khi mua bằng giấy tay',
];

export function LawSearch() {
  const location = useLocation();
  const [query, setQuery] = useState(() => getContextSummary(location.state));
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LawSearchResult | null>(null);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const { toasts, toast, dismiss } = useToast();

  async function handleSearch(q?: string) {
    const text = (q ?? query).trim();
    if (!text) return;
    if (q) setQuery(q);
    setLoading(true);
    setResult(null);
    setError('');
    setSaved(false);
    try {
      const r = await searchLaws(text);
      setResult(r);
    } catch {
      setError('Không thể kết nối máy chủ. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <ToastContainer toasts={toasts} dismiss={dismiss} />
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-legal-gold/10 border border-legal-gold/20 rounded-xl flex items-center justify-center">
          <BookOpen size={20} className="text-legal-gold" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Tra Cứu Điều Luật</h1>
          <p className="text-sm text-slate-400">Tìm kiếm ngữ nghĩa trên toàn bộ văn bản pháp luật Việt Nam</p>
        </div>
      </div>

      {/* Search input */}
      <div className="glass-card p-6 space-y-4">
        <label className="text-sm font-semibold text-white">Nhập từ khóa hoặc câu hỏi pháp lý</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSearch(); }}
            placeholder="Ví dụ: Điều kiện chấm dứt hợp đồng lao động đúng luật..."
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-legal-gold/50 transition-colors"
          />
          <button
            onClick={() => handleSearch()}
            disabled={loading || !query.trim()}
            className="flex items-center gap-2 px-5 py-2.5 bg-legal-gold text-legal-navy font-bold rounded-xl disabled:opacity-40 hover:scale-105 active:scale-95 transition-all text-sm shrink-0"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            {loading ? 'Đang tìm...' : 'Tìm kiếm'}
          </button>
        </div>

        {/* Quick query chips */}
        <div>
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Gợi ý nhanh</p>
          <div className="flex flex-wrap gap-2">
            {QUICK_QUERIES.map(q => (
              <button
                key={q}
                onClick={() => handleSearch(q)}
                className="text-xs px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-slate-300 hover:border-legal-gold/40 hover:text-legal-gold transition-all"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-xs text-red-400 p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
            <AlertTriangle size={13} />
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4 animate-in fade-in duration-300">
          {/* Meta bar */}
          <div className="glass-card p-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs">
            <span className="text-slate-400">
              Lĩnh vực: <span className="text-white font-semibold">{result.detected_domain_label}</span>
            </span>
            <span className="text-slate-400">
              Tìm kiếm: <span className="text-white font-semibold">{result.search_mode === 'vector' ? 'Ngữ nghĩa' : 'Từ khóa'}</span>
            </span>
            <span className="text-slate-400 italic flex-1 min-w-0 truncate">{result.summary}</span>
            <button
              onClick={() => {
                saveAnalysis({ type: 'law_search', title: query.slice(0, 80), summary: result.summary, data: result }).then(() => toast('Đã lưu vào lịch sử'));
                setSaved(true);
              }}
              disabled={saved}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold transition-all border bg-white/5 border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 disabled:opacity-60 shrink-0"
            >
              {saved ? <><Check size={12} className="text-green-400" /> Đã lưu</> : <><Bookmark size={12} /> Lưu kết quả</>}
            </button>
          </div>

          {/* Law articles */}
          {result.results.length > 0 ? (
            <div className="space-y-3">
              {result.results.map((a, i) => (
                <LawCard key={a.chunk_id || i} article={a} index={i} />
              ))}
            </div>
          ) : (
            <div className="py-12 flex flex-col items-center text-center space-y-3 opacity-50">
              <BookOpen size={48} className="text-slate-500" />
              <p className="text-sm text-slate-400">Không tìm thấy điều luật phù hợp.</p>
              <p className="text-xs text-slate-500">
                Thử từ khóa khác hoặc tải thêm văn bản pháp luật qua Admin.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="py-20 flex flex-col items-center text-center space-y-3 opacity-30">
          <BookOpen size={64} className="text-slate-500" />
          <p className="text-sm font-bold text-slate-500">
            Nhập truy vấn để tìm điều luật liên quan
          </p>
        </div>
      )}
    </div>
  );
}
