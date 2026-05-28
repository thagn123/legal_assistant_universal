/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  Gavel,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  ListChecks,
  ShieldAlert,
  Bookmark,
  Check,
} from 'lucide-react';
import { analyzeClause, ClauseCoachResult, ClauseRisk, SaferVersion, MissingClause, saveAnalysis } from '../lib/api';
import { cn } from '../lib/api';

// ── Config ────────────────────────────────────────────────────────────────────

const CONTRACT_TYPES = [
  { value: '', label: 'Tự động nhận dạng' },
  { value: 'general', label: 'Hợp đồng chung' },
  { value: 'termination', label: 'Điều khoản chấm dứt' },
  { value: 'penalty', label: 'Điều khoản phạt / bồi thường' },
  { value: 'payment', label: 'Điều khoản thanh toán' },
  { value: 'scope', label: 'Điều khoản phạm vi công việc' },
  { value: 'confidentiality', label: 'Điều khoản bảo mật' },
  { value: 'employment', label: 'Hợp đồng lao động' },
];

const SEVERITY_CONFIG = {
  critical: { label: 'Nghiêm trọng', color: 'text-red-400',    bg: 'bg-red-500/10 border-red-500/30' },
  high:     { label: 'Cao',          color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30' },
  medium:   { label: 'Trung bình',   color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30' },
  low:      { label: 'Thấp',         color: 'text-slate-400',  bg: 'bg-white/5 border-white/10' },
} as const;

const IMPORTANCE_CONFIG = {
  required:    { label: 'Bắt buộc',   color: 'text-red-400' },
  recommended: { label: 'Nên có',     color: 'text-yellow-400' },
  optional:    { label: 'Tùy chọn',   color: 'text-slate-400' },
} as const;

const RISK_LEVEL_CONFIG = {
  low:      { label: 'Thấp',         color: '#22c55e' },
  medium:   { label: 'Trung bình',   color: '#eab308' },
  high:     { label: 'Cao',          color: '#f97316' },
  critical: { label: 'Rất cao',      color: '#ef4444' },
} as const;

// ── Score Ring ────────────────────────────────────────────────────────────────

function RiskRing({ score, level }: { score: number; level: string }) {
  const pct = Math.round(score);
  const circumference = 2 * Math.PI * 36;
  const dash = (pct / 100) * circumference;
  const color = RISK_LEVEL_CONFIG[level as keyof typeof RISK_LEVEL_CONFIG]?.color ?? '#94a3b8';
  const label = RISK_LEVEL_CONFIG[level as keyof typeof RISK_LEVEL_CONFIG]?.label ?? level;
  return (
    <div className="relative w-24 h-24 flex items-center justify-center">
      <svg width="96" height="96" className="-rotate-90">
        <circle cx="48" cy="48" r="36" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="8" />
        <circle
          cx="48" cy="48" r="36" fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      <div className="absolute text-center">
        <p className="text-2xl font-bold text-white">{pct}</p>
        <p className="text-[9px] uppercase tracking-wider" style={{ color }}>{label}</p>
      </div>
    </div>
  );
}

// ── Risk Card ─────────────────────────────────────────────────────────────────

function RiskCard({ risk, safer }: { risk: ClauseRisk; safer?: SaferVersion }) {
  const [open, setOpen] = useState(false);
  const cfg = SEVERITY_CONFIG[risk.severity] ?? SEVERITY_CONFIG.low;
  return (
    <div className={cn('rounded-xl border transition-all', cfg.bg)}>
      <button
        onClick={() => setOpen(p => !p)}
        className="w-full flex items-start gap-3 p-3.5 text-left"
      >
        <XCircle size={16} className={cn('flex-none mt-0.5', cfg.color)} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white leading-snug">{risk.type}</p>
          <div className="flex gap-3 mt-1 flex-wrap">
            <span className={cn('text-[10px] font-bold', cfg.color)}>{cfg.label}</span>
            <span className="text-[10px] text-slate-500 font-mono">"{risk.matched_phrase}"</span>
          </div>
        </div>
        {open ? <ChevronUp size={14} className="flex-none text-slate-500 mt-0.5" /> : <ChevronDown size={14} className="flex-none text-slate-500 mt-0.5" />}
      </button>
      {open && (
        <div className="border-t border-white/8 px-4 py-3 space-y-2 animate-in fade-in duration-150">
          <p className="text-[11px] text-slate-300">{risk.description}</p>
          <p className="text-[11px] text-slate-500">
            <span className="font-semibold text-slate-400">Căn cứ: </span>{risk.law_basis}
          </p>
          {safer && (
            <div className="mt-2 p-2.5 bg-legal-gold/5 border border-legal-gold/15 rounded-lg space-y-1">
              <p className="text-[10px] font-bold text-legal-gold uppercase tracking-wider flex items-center gap-1">
                <Lightbulb size={10} /> Gợi ý viết lại
              </p>
              <p className="text-[11px] text-slate-300 italic">"{safer.suggested_phrase}"</p>
              <p className="text-[10px] text-slate-500">{safer.reason}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Missing Clause Card ───────────────────────────────────────────────────────

function MissingCard({ item }: { item: MissingClause }) {
  const [open, setOpen] = useState(false);
  const cfg = IMPORTANCE_CONFIG[item.importance as keyof typeof IMPORTANCE_CONFIG] ?? IMPORTANCE_CONFIG.optional;
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 transition-all">
      <button
        onClick={() => setOpen(p => !p)}
        className="w-full flex items-start gap-3 p-3.5 text-left"
      >
        <CheckCircle2 size={16} className="flex-none mt-0.5 text-slate-500" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-300 leading-snug">{item.clause_type}</p>
          <span className={cn('text-[10px] font-bold mt-0.5 block', cfg.color)}>{cfg.label}</span>
        </div>
        {open ? <ChevronUp size={14} className="flex-none text-slate-500 mt-0.5" /> : <ChevronDown size={14} className="flex-none text-slate-500 mt-0.5" />}
      </button>
      {open && (
        <div className="border-t border-white/8 px-4 py-3 space-y-2 animate-in fade-in duration-150">
          <p className="text-[10px] text-slate-500">
            <span className="font-semibold text-slate-400">Căn cứ: </span>{item.law_basis}
          </p>
          <div className="p-2.5 bg-legal-gold/5 border border-legal-gold/15 rounded-lg">
            <p className="text-[10px] font-bold text-legal-gold uppercase tracking-wider mb-1">Mẫu điều khoản</p>
            <p className="text-[11px] text-slate-300 italic leading-relaxed">"{item.template}"</p>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Sample clauses ────────────────────────────────────────────────────────────

const SAMPLE_CLAUSES = [
  'Bên A được quyền đơn phương chấm dứt hợp đồng này mà không cần thông báo trước nếu Bên B vi phạm bất kỳ điều khoản nào.',
  'Trong trường hợp vi phạm, bên vi phạm phải chịu phạt 50% giá trị hợp đồng và bồi thường toàn bộ mọi thiệt hại phát sinh.',
  'Phạm vi công việc sẽ được thực hiện theo thỏa thuận giữa hai bên khi cần thiết.',
  'Mọi quyền sở hữu trí tuệ phát sinh trong quá trình thực hiện hợp đồng thuộc về Bên A, Bên B không bảo lưu bất kỳ quyền nào.',
];

interface IsolatedTextAreaProps {
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
  rows?: number;
  className?: string;
}

function IsolatedTextArea({ value, onChange, placeholder, rows = 3, className }: IsolatedTextAreaProps) {
  const [text, setText] = useState(value);

  useEffect(() => {
    setText(value);
  }, [value]);

  return (
    <textarea
      value={text}
      onChange={(e) => setText(e.target.value)}
      onBlur={() => onChange(text)}
      placeholder={placeholder}
      rows={rows}
      className={className}
    />
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ClauseCoach() {
  const [clauseText, setClauseText] = useState('');
  const [contractType, setContractType] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClauseCoachResult | null>(null);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  async function handleAnalyze() {
    if (!clauseText.trim()) return;
    setLoading(true);
    setResult(null);
    setError('');
    setSaved(false);
    try {
      const r = await analyzeClause(clauseText.trim(), contractType || undefined);
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
          <Gavel size={20} className="text-legal-gold" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Clause Coach</h1>
          <p className="text-sm text-slate-400">Phát hiện rủi ro trong điều khoản hợp đồng và gợi ý viết lại an toàn hơn</p>
        </div>
      </div>

      {/* Input card */}
      <div className="glass-card p-6 space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Điều khoản cần phân tích
          </label>
          <IsolatedTextArea
            value={clauseText}
            onChange={setClauseText}
            placeholder="Dán điều khoản hợp đồng vào đây..."
            rows={5}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
          />
        </div>

        {/* Sample clauses */}
        <div>
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">Thử với mẫu</p>
          <div className="flex flex-wrap gap-1.5">
            {SAMPLE_CLAUSES.map((s, i) => (
              <button
                key={i}
                onClick={() => setClauseText(s)}
                className="text-[10px] px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-legal-gold/30 transition-colors text-left max-w-xs truncate"
              >
                {s.slice(0, 60)}…
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-end gap-4">
          <div className="flex-1 space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Loại điều khoản</label>
            <select
              value={contractType}
              onChange={e => setContractType(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-legal-gold/50 transition-colors"
            >
              {CONTRACT_TYPES.map(ct => (
                <option key={ct.value} value={ct.value} className="bg-slate-900">{ct.label}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleAnalyze}
            disabled={loading || !clauseText.trim()}
            className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy font-bold rounded-xl disabled:opacity-40 hover:scale-105 active:scale-95 transition-all text-sm whitespace-nowrap"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Gavel size={16} />}
            {loading ? 'Đang phân tích...' : 'Phân tích điều khoản'}
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
        <div className="space-y-5 animate-in fade-in duration-300">
          {/* Summary row */}
          <div className="glass-card p-5 flex flex-wrap gap-6 items-center">
            <RiskRing score={result.risk_score} level={result.risk_level} />
            <div className="flex-1 min-w-0 space-y-1.5">
              <p className="text-[11px] text-legal-gold font-mono font-bold uppercase tracking-wider">
                {result.clause_type_label}
              </p>
              <p className="text-sm text-slate-300 leading-relaxed">{result.summary}</p>
              <div className="flex gap-4 text-xs flex-wrap items-center">
                <span className="text-red-400 font-bold">{result.risks.filter(r => r.severity === 'critical').length} Nghiêm trọng</span>
                <span className="text-orange-400 font-bold">{result.risks.length} Tổng rủi ro</span>
                <span className="text-slate-400">{result.missing_clauses.length} Điều khoản thiếu</span>
                <button
                  onClick={() => {
                    saveAnalysis({ type: 'clause_coach', title: clauseText.slice(0, 80), summary: result.summary, data: result });
                    setSaved(true);
                  }}
                  disabled={saved}
                  className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border bg-white/5 border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 disabled:opacity-60"
                >
                  {saved ? <><Check size={12} className="text-green-400" /> Đã lưu</> : <><Bookmark size={12} /> Lưu kết quả</>}
                </button>
              </div>
            </div>
          </div>

          {/* Risks */}
          {result.risks.length > 0 && (
            <div className="glass-card p-5 space-y-3">
              <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <ShieldAlert size={14} className="text-red-400" />
                Rủi ro phát hiện ({result.risks.length})
              </h2>
              {result.risks.map((risk, i) => (
                <RiskCard
                  key={risk.id}
                  risk={risk}
                  safer={result.safer_versions[i]}
                />
              ))}
            </div>
          )}

          {/* Missing clauses */}
          {result.missing_clauses.length > 0 && (
            <div className="glass-card p-5 space-y-3">
              <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <ListChecks size={14} className="text-yellow-400" />
                Điều khoản còn thiếu ({result.missing_clauses.length})
              </h2>
              {result.missing_clauses.map(mc => (
                <MissingCard key={mc.clause_type} item={mc} />
              ))}
            </div>
          )}

          {/* All clear */}
          {result.risks.length === 0 && result.missing_clauses.length === 0 && (
            <div className="glass-card p-5 flex items-center gap-3 text-green-400">
              <CheckCircle2 size={20} />
              <p className="text-sm font-medium">{result.summary}</p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="py-20 flex flex-col items-center text-center space-y-3 opacity-30">
          <Gavel size={64} className="text-slate-500" />
          <p className="text-sm font-bold text-slate-500">Dán điều khoản hợp đồng để phân tích rủi ro</p>
        </div>
      )}
    </div>
  );
}
