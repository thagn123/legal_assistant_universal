/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  GitCompare,
  Loader2,
  AlertTriangle,
  Scale,
  ChevronRight,
  BookOpen,
  Gavel,
  Lightbulb,
  Tag,
} from 'lucide-react';
import { getSimilarCases, SimilarCaseItem, SimilarCasesResult } from '../lib/api';

// ── Similarity bar ────────────────────────────────────────────────────────────

function SimilarityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.85 ? 'bg-green-500' :
    score >= 0.70 ? 'bg-legal-gold' :
    score >= 0.55 ? 'bg-orange-500' :
    'bg-slate-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-[11px] font-bold tabular-nums ${
        score >= 0.85 ? 'text-green-400' :
        score >= 0.70 ? 'text-legal-gold' :
        score >= 0.55 ? 'text-orange-400' : 'text-slate-400'
      }`}>{pct}%</span>
    </div>
  );
}

// ── Case card ─────────────────────────────────────────────────────────────────

function CaseCard({ item, index }: { item: SimilarCaseItem; index: number }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="bg-white/5 border border-white/8 rounded-xl overflow-hidden hover:bg-white/8 transition-all">
      {/* header */}
      <button
        onClick={() => setExpanded(p => !p)}
        className="w-full flex items-start gap-3 p-4 text-left"
      >
        <span className="flex-none w-7 h-7 rounded-full bg-legal-gold/15 text-legal-gold text-[11px] font-bold flex items-center justify-center border border-legal-gold/20 mt-0.5">
          {index + 1}
        </span>
        <div className="flex-1 min-w-0 space-y-1.5">
          <p className="text-sm font-semibold text-white leading-snug">
            {item.title || 'Vụ việc không có tiêu đề'}
          </p>
          <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
            {item.situation_summary}
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-legal-gold/10 text-legal-gold border border-legal-gold/20 font-medium">
              {item.domain_label}
            </span>
            <span className="text-[10px] text-slate-500">{item.similarity_label}</span>
          </div>
          <SimilarityBar score={item.similarity_score} />
        </div>
        <ChevronRight
          size={16}
          className={`flex-none text-slate-500 mt-0.5 transition-transform ${expanded ? 'rotate-90' : ''}`}
        />
      </button>

      {/* expanded detail */}
      {expanded && (
        <div className="border-t border-white/8 p-4 space-y-3 animate-in fade-in duration-200">
          {item.outcome && (
            <div className="flex gap-2">
              <Gavel size={14} className="text-legal-gold shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-0.5">Kết quả</p>
                <p className="text-sm text-slate-300 leading-relaxed">{item.outcome}</p>
              </div>
            </div>
          )}
          {item.lesson && (
            <div className="flex gap-2">
              <Lightbulb size={14} className="text-yellow-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-0.5">Bài học</p>
                <p className="text-sm text-slate-300 leading-relaxed italic">{item.lesson}</p>
              </div>
            </div>
          )}
          {item.key_laws.length > 0 && (
            <div className="flex gap-2">
              <BookOpen size={14} className="text-blue-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Căn cứ pháp lý</p>
                <div className="flex flex-wrap gap-1.5">
                  {item.key_laws.map((law, i) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-300 border border-blue-500/20">
                      {law}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Summary bar ───────────────────────────────────────────────────────────────

function QueryBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <Tag size={11} className="text-slate-500" />
      <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}:</span>
      <span className="text-xs text-white font-medium">{value}</span>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function SimilarCases() {
  const [situation, setSituation] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimilarCasesResult | null>(null);
  const [error, setError] = useState('');

  async function handleSearch() {
    if (!situation.trim()) return;
    setLoading(true);
    setResult(null);
    setError('');
    try {
      const r = await getSimilarCases(situation.trim());
      setResult(r);
    } catch {
      setError('Không thể kết nối máy chủ. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-legal-gold/10 border border-legal-gold/20 rounded-xl flex items-center justify-center">
          <GitCompare size={20} className="text-legal-gold" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Vụ Việc Tương Tự</h1>
          <p className="text-sm text-slate-400">Tìm kiếm case pháp lý gần giống để tham khảo kết quả và bài học</p>
        </div>
      </div>

      {/* Input */}
      <div className="glass-card p-6 space-y-4">
        <label className="text-sm font-semibold text-white">Mô tả tình huống của bạn</label>
        <textarea
          value={situation}
          onChange={e => setSituation(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSearch(); }}
          placeholder="Ví dụ: Tôi bị công ty sa thải không báo trước, không trả lương tháng cuối và không chi trả trợ cấp thôi việc..."
          rows={3}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
        />
        <div className="flex items-center gap-3">
          <button
            onClick={handleSearch}
            disabled={loading || !situation.trim()}
            className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy font-bold rounded-xl disabled:opacity-40 hover:scale-105 active:scale-95 transition-all text-sm"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <GitCompare size={16} />}
            {loading ? 'Đang tìm kiếm...' : 'Tìm vụ việc tương tự'}
          </button>
          <span className="text-[11px] text-slate-500">Ctrl+Enter để tìm</span>
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
          {/* Query metadata bar */}
          <div className="glass-card p-4 flex flex-wrap gap-x-6 gap-y-2 items-center">
            <QueryBadge label="Lĩnh vực" value={result.query_domain_label} />
            <QueryBadge label="Giai đoạn" value={result.query_stage_label} />
            <QueryBadge label="Tìm kiếm" value={result.search_mode === 'vector' ? 'Ngữ nghĩa' : 'Từ khóa'} />
            <span className="ml-auto text-xs text-slate-400 italic">{result.summary}</span>
          </div>

          {/* Case list */}
          {result.similar_cases.length > 0 ? (
            <div className="space-y-3">
              {result.similar_cases.map((item, i) => (
                <CaseCard key={item.case_id || i} item={item} index={i} />
              ))}
            </div>
          ) : (
            <div className="py-12 flex flex-col items-center text-center space-y-3 opacity-50">
              <Scale size={48} className="text-slate-500" />
              <p className="text-sm text-slate-400">Không tìm thấy vụ việc tương tự trong cơ sở dữ liệu.</p>
              <p className="text-xs text-slate-500">Thử cung cấp thêm chi tiết hoặc mô tả theo hướng khác.</p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="py-20 flex flex-col items-center text-center space-y-3 opacity-30">
          <GitCompare size={64} className="text-slate-500" />
          <p className="text-sm font-bold text-slate-500">Nhập tình huống để tìm vụ việc có điểm tương đồng</p>
        </div>
      )}
    </div>
  );
}
