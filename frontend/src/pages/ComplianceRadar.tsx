/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  Radar,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Scale,
  ChevronDown,
  ChevronUp,
  Bookmark,
  Check,
} from 'lucide-react';
import { getComplianceRadar, ComplianceItem, ComplianceRadarResult, saveAnalysis } from '../lib/api';
import { cn } from '../lib/api';
import { useToast } from '../lib/useToast';
import { ToastContainer } from '../components/ui/ToastContainer';

// ── Config ────────────────────────────────────────────────────────────────────

const BUSINESS_TYPES = [
  { value: 'startup',           label: 'Startup / Khởi nghiệp' },
  { value: 'sme',               label: 'Doanh nghiệp vừa và nhỏ' },
  { value: 'hr',                label: 'Bộ phận HR / Nhân sự' },
  { value: 'freelancer',        label: 'Freelancer / Tự do' },
  { value: 'individual',        label: 'Cá nhân' },
  { value: 'contract_reviewer', label: 'Người soát hợp đồng' },
];

const TRANSACTION_TYPES = [
  { value: 'thanh_lap',          label: 'Thành lập công ty' },
  { value: 'tuyen_dung',         label: 'Tuyển dụng / HĐLĐ' },
  { value: 'hop_dong_thuong_mai',label: 'Hợp đồng thương mại' },
  { value: 'mua_ban_tai_san',    label: 'Mua bán tài sản / BĐS' },
  { value: 'tham_gia_du_an',     label: 'Tham gia dự án' },
  { value: 'general',            label: 'Tổng hợp' },
];

const PRIORITY_CONFIG = {
  critical: { label: 'Bắt buộc — Quan trọng', color: 'text-red-400',    bg: 'bg-red-500/10 border-red-500/30' },
  high:     { label: 'Bắt buộc',               color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30' },
  medium:   { label: 'Nên có',                 color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30' },
  low:      { label: 'Tùy chọn',               color: 'text-slate-400',  bg: 'bg-white/5 border-white/10' },
} as const;

// ── Compliance score ring ─────────────────────────────────────────────────────

function ScoreRing({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const circumference = 2 * Math.PI * 36;
  const dash = (pct / 100) * circumference;
  const color =
    pct >= 80 ? '#22c55e' :
    pct >= 55 ? '#eab308' :
    pct >= 30 ? '#f97316' : '#ef4444';
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
        <p className="text-2xl font-bold text-white">{pct}%</p>
        <p className="text-[9px] text-slate-400 uppercase tracking-wider">Tuân thủ</p>
      </div>
    </div>
  );
}

// ── Compliance item row ───────────────────────────────────────────────────────

function ComplianceRow({ item }: { item: ComplianceItem }) {
  const [open, setOpen] = useState(false);
  const cfg = PRIORITY_CONFIG[item.priority] ?? PRIORITY_CONFIG.low;
  return (
    <div className={cn("rounded-xl border transition-all", cfg.bg, item.missing ? '' : 'opacity-60')}>
      <button
        onClick={() => setOpen(p => !p)}
        className="w-full flex items-start gap-3 p-3.5 text-left"
      >
        <div className="flex-none mt-0.5">
          {item.missing
            ? <XCircle size={16} className={cfg.color} />
            : <CheckCircle2 size={16} className="text-green-400" />}
        </div>
        <div className="flex-1 min-w-0">
          <p className={cn("text-sm font-medium leading-snug", item.missing ? 'text-white' : 'text-slate-400 line-through')}>
            {item.requirement}
          </p>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            <span className="text-[10px] text-slate-500 font-medium">{item.category}</span>
            <span className={cn("text-[10px] font-bold", cfg.color)}>{cfg.label}</span>
          </div>
        </div>
        {open ? <ChevronUp size={14} className="flex-none text-slate-500 mt-0.5" /> : <ChevronDown size={14} className="flex-none text-slate-500 mt-0.5" />}
      </button>
      {open && (
        <div className="border-t border-white/8 px-4 py-3 space-y-1.5 animate-in fade-in duration-150">
          <p className="text-[11px] text-slate-400">
            <span className="text-slate-500 font-semibold">Căn cứ: </span>{item.law_basis}
          </p>
          <p className="text-[11px] text-slate-400 flex items-center gap-1">
            <Clock size={10} className="text-slate-500" />
            <span className="text-slate-500 font-semibold">Thời hạn: </span>&nbsp;{item.deadline_note}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Category group ────────────────────────────────────────────────────────────

function CategoryGroup({ category, items }: { category: string; items: ComplianceItem[] }) {
  const missingCount = items.filter(it => it.missing).length;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">{category}</h3>
        {missingCount > 0 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/20">
            {missingCount} thiếu
          </span>
        )}
      </div>
      <div className="space-y-2">
        {items.map(it => <ComplianceRow key={it.id} item={it} />)}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ComplianceRadar() {
  const [businessType, setBusinessType] = useState('startup');
  const [transactionType, setTransactionType] = useState('thanh_lap');
  const [situation, setSituation] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ComplianceRadarResult | null>(null);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const { toasts, toast, dismiss } = useToast();

  async function handleCheck() {
    setLoading(true);
    setResult(null);
    setError('');
    setSaved(false);
    try {
      const r = await getComplianceRadar(businessType, transactionType, [], situation);
      setResult(r);
    } catch {
      setError('Không thể kết nối máy chủ. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  }

  // Group items by category
  const categories: Record<string, ComplianceItem[]> = {};
  if (result) {
    for (const it of result.items) {
      if (!categories[it.category]) categories[it.category] = [];
      categories[it.category].push(it);
    }
    // Sort: missing first within each category
    for (const cat of Object.keys(categories)) {
      categories[cat].sort((a, b) => (b.missing ? 1 : 0) - (a.missing ? 1 : 0));
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <ToastContainer toasts={toasts} dismiss={dismiss} />
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-legal-gold/10 border border-legal-gold/20 rounded-xl flex items-center justify-center">
          <Radar size={20} className="text-legal-gold" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Compliance Radar</h1>
          <p className="text-sm text-slate-400">Kiểm tra danh sách tuân thủ pháp lý theo loại hình doanh nghiệp và giao dịch</p>
        </div>
      </div>

      {/* Filter card */}
      <div className="glass-card p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Loại hình</label>
            <select
              value={businessType}
              onChange={e => setBusinessType(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-legal-gold/50 transition-colors"
            >
              {BUSINESS_TYPES.map(bt => (
                <option key={bt.value} value={bt.value} className="bg-slate-900">{bt.label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Loại giao dịch</label>
            <select
              value={transactionType}
              onChange={e => setTransactionType(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-legal-gold/50 transition-colors"
            >
              {TRANSACTION_TYPES.map(tt => (
                <option key={tt.value} value={tt.value} className="bg-slate-900">{tt.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Tình huống / sự kiện đã có (tùy chọn)
          </label>
          <textarea
            value={situation}
            onChange={e => setSituation(e.target.value)}
            placeholder="Ví dụ: Đã có hợp đồng lao động, đã đăng ký BHXH, chưa có nội quy lao động..."
            rows={2}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
          />
        </div>

        <button
          onClick={handleCheck}
          disabled={loading}
          className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy font-bold rounded-xl disabled:opacity-40 hover:scale-105 active:scale-95 transition-all text-sm"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Radar size={16} />}
          {loading ? 'Đang kiểm tra...' : 'Kiểm tra tuân thủ'}
        </button>

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
            <ScoreRing score={result.compliance_score} />
            <div className="flex-1 min-w-0 space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-400 mb-0.5">
                    {result.business_type_label} — {result.transaction_type_label}
                  </p>
                  <p className="text-sm text-slate-300 leading-relaxed">{result.summary}</p>
                </div>
                <button
                  onClick={() => {
                    saveAnalysis({ type: 'compliance_radar', title: `${result.business_type_label} — ${result.transaction_type_label}`, summary: result.summary, data: result }).then(() => toast('Đã lưu vào lịch sử'));
                    setSaved(true);
                  }}
                  disabled={saved}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border bg-white/5 border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 disabled:opacity-60 shrink-0"
                >
                  {saved ? <><Check size={12} className="text-green-400" /> Đã lưu</> : <><Bookmark size={12} /> Lưu</>}
                </button>
              </div>
              <div className="flex gap-4 text-xs">
                <span className="text-red-400 font-bold">{result.critical_count} Bắt buộc quan trọng thiếu</span>
                <span className="text-orange-400 font-bold">{result.missing_count} Tổng mục thiếu</span>
                <span className="text-slate-400">{result.items.length - result.missing_count} Đã đáp ứng</span>
              </div>
              {result.alerts.map((a, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-orange-400 p-2.5 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                  <AlertTriangle size={12} />
                  {a}
                </div>
              ))}
            </div>
          </div>

          {/* Checklist by category */}
          <div className="glass-card p-5 space-y-6">
            {Object.entries(categories).map(([cat, items]) => (
              <CategoryGroup key={cat} category={cat} items={items} />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="py-20 flex flex-col items-center text-center space-y-3 opacity-30">
          <Radar size={64} className="text-slate-500" />
          <p className="text-sm font-bold text-slate-500">Chọn loại hình và giao dịch để xem danh sách tuân thủ</p>
        </div>
      )}
    </div>
  );
}
