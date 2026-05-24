/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  FileSearch,
  Loader2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ShieldAlert,
  Shield,
} from 'lucide-react';
import { searchSimilarClauses, ClauseSearchResult, ClauseItem } from '../lib/api';
import { cn } from '../lib/api';

// ── Config ────────────────────────────────────────────────────────────────────

const CLAUSE_TYPES = [
  { value: '',                     label: 'Tất cả loại điều khoản' },
  { value: 'termination',          label: 'Điều khoản chấm dứt' },
  { value: 'penalty',              label: 'Điều khoản phạt / bồi thường' },
  { value: 'payment',              label: 'Điều khoản thanh toán' },
  { value: 'confidentiality',      label: 'Điều khoản bảo mật' },
  { value: 'intellectual_property',label: 'Sở hữu trí tuệ' },
  { value: 'force_majeure',        label: 'Bất khả kháng' },
  { value: 'dispute_resolution',   label: 'Giải quyết tranh chấp' },
  { value: 'scope',                label: 'Phạm vi công việc' },
  { value: 'employment',           label: 'Lao động' },
];

const RISK_LEVELS = [
  { value: '',         label: 'Tất cả mức rủi ro' },
  { value: 'critical', label: 'Rất rủi ro' },
  { value: 'high',     label: 'Rủi ro cao' },
  { value: 'medium',   label: 'Rủi ro trung bình' },
  { value: 'low',      label: 'Ít rủi ro' },
  { value: 'safe',     label: 'An toàn' },
];

const RISK_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-500/10 border-red-500/30',
  high:     'text-orange-400 bg-orange-500/10 border-orange-500/30',
  medium:   'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  low:      'text-blue-400 bg-blue-500/10 border-blue-500/30',
  safe:     'text-green-400 bg-green-500/10 border-green-500/30',
};

const SAMPLE_CLAUSES = [
  'Bên A được quyền đơn phương chấm dứt hợp đồng mà không cần thông báo.',
  'Thông tin bảo mật bao gồm tất cả dữ liệu kinh doanh, kỹ thuật, tài chính.',
  'Trong trường hợp vi phạm, bên vi phạm phải bồi thường toàn bộ mọi thiệt hại.',
  'Mọi tranh chấp được giải quyết tại Tòa án nhân dân có thẩm quyền tại Hà Nội.',
];

// ── Similarity bar ────────────────────────────────────────────────────────────

function SimilarityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 85 ? '#22c55e' :
    pct >= 70 ? '#eab308' :
    pct >= 55 ? '#f97316' : '#94a3b8';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[11px] font-bold shrink-0" style={{ color }}>{pct}%</span>
    </div>
  );
}

// ── Clause card ───────────────────────────────────────────────────────────────

function ClauseCard({ item }: { item: ClauseItem }) {
  const [open, setOpen] = useState(false);
  const riskClass = RISK_COLORS[item.risk_level] ?? RISK_COLORS.medium;
  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setOpen(p => !p)}
        className="w-full flex items-start gap-3 p-4 text-left"
      >
        <ShieldAlert size={16} className={cn('flex-none mt-0.5', riskClass.split(' ')[0])} />
        <div className="flex-1 min-w-0 space-y-1.5">
          <p className="text-[11px] text-slate-300 leading-relaxed line-clamp-2">{item.clause_text}</p>
          <div className="flex flex-wrap gap-2 items-center">
            <span className={cn('text-[10px] font-bold px-1.5 py-0.5 rounded-md border', riskClass)}>
              {item.risk_label}
            </span>
            <span className="text-[10px] text-slate-500">{item.similarity_label}</span>
          </div>
          <SimilarityBar score={item.similarity_score} />
        </div>
        {open ? <ChevronUp size={14} className="flex-none text-slate-500" /> : <ChevronDown size={14} className="flex-none text-slate-500" />}
      </button>
      {open && (
        <div className="border-t border-white/8 px-4 py-3 space-y-2 animate-in fade-in duration-150">
          <p className="text-[11px] text-slate-300 leading-relaxed whitespace-pre-wrap">{item.clause_text}</p>
          {item.suggestion && (
            <div className="mt-2 p-2.5 bg-legal-gold/5 border border-legal-gold/15 rounded-lg">
              <p className="text-[10px] font-bold text-legal-gold uppercase tracking-wider mb-1">Gợi ý cải thiện</p>
              <p className="text-[11px] text-slate-300 italic">{item.suggestion}</p>
            </div>
          )}
          <p className="text-[10px] text-slate-600 font-mono">doc: {item.doc_id || '—'}</p>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ClauseSearch() {
  const [clauseText, setClauseText]   = useState('');
  const [clauseType, setClauseType]   = useState('');
  const [riskLevel, setRiskLevel]     = useState('');
  const [loading, setLoading]         = useState(false);
  const [result, setResult]           = useState<ClauseSearchResult | null>(null);
  const [error, setError]             = useState('');

  async function handleSearch() {
    if (!clauseText.trim()) return;
    setLoading(true);
    setResult(null);
    setError('');
    try {
      const r = await searchSimilarClauses(
        clauseText.trim(),
        clauseType || undefined,
        riskLevel || undefined,
      );
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
          <FileSearch size={20} className="text-legal-gold" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Tìm điều khoản tương tự</h1>
          <p className="text-sm text-slate-400">So sánh điều khoản hợp đồng với cơ sở dữ liệu để tìm mẫu tương tự và đánh giá rủi ro</p>
        </div>
      </div>

      {/* Input card */}
      <div className="glass-card p-6 space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Điều khoản cần tìm</label>
          <textarea
            value={clauseText}
            onChange={e => setClauseText(e.target.value)}
            placeholder="Dán điều khoản hợp đồng vào đây để tìm điều khoản tương tự..."
            rows={4}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
          />
        </div>

        {/* Sample chips */}
        <div>
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">Thử với mẫu</p>
          <div className="flex flex-wrap gap-1.5">
            {SAMPLE_CLAUSES.map((s, i) => (
              <button
                key={i}
                onClick={() => setClauseText(s)}
                className="text-[10px] px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-legal-gold/30 transition-colors text-left max-w-xs truncate"
              >
                {s.slice(0, 55)}…
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-end gap-4">
          <div className="flex-1 space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Loại điều khoản</label>
            <select
              value={clauseType}
              onChange={e => setClauseType(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-legal-gold/50 transition-colors"
            >
              {CLAUSE_TYPES.map(ct => (
                <option key={ct.value} value={ct.value} className="bg-slate-900">{ct.label}</option>
              ))}
            </select>
          </div>
          <div className="flex-1 space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Mức rủi ro</label>
            <select
              value={riskLevel}
              onChange={e => setRiskLevel(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-legal-gold/50 transition-colors"
            >
              {RISK_LEVELS.map(rl => (
                <option key={rl.value} value={rl.value} className="bg-slate-900">{rl.label}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleSearch}
            disabled={loading || !clauseText.trim()}
            className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy font-bold rounded-xl disabled:opacity-40 hover:scale-105 active:scale-95 transition-all text-sm whitespace-nowrap"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <FileSearch size={16} />}
            {loading ? 'Đang tìm...' : 'Tìm tương tự'}
          </button>
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
          {/* Summary */}
          <div className="glass-card p-4 flex items-center justify-between">
            <p className="text-sm text-slate-300">{result.summary}</p>
            <span className="text-[10px] px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-500 font-mono shrink-0 ml-3">
              {result.search_mode}
            </span>
          </div>

          {result.results.length > 0 ? (
            <div className="space-y-3">
              {result.results.map((item, i) => (
                <ClauseCard key={item.clause_id || i} item={item} />
              ))}
            </div>
          ) : (
            <div className="py-12 flex flex-col items-center text-center space-y-3 opacity-50">
              <Shield size={48} className="text-slate-500" />
              <p className="text-sm text-slate-500">Chưa có điều khoản tương tự trong cơ sở dữ liệu.</p>
              <p className="text-xs text-slate-600">Tải lên hợp đồng qua trang Tài liệu để bổ sung dữ liệu.</p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="py-20 flex flex-col items-center text-center space-y-3 opacity-30">
          <FileSearch size={64} className="text-slate-500" />
          <p className="text-sm font-bold text-slate-500">Dán điều khoản để tìm mẫu tương tự trong cơ sở dữ liệu</p>
        </div>
      )}
    </div>
  );
}
