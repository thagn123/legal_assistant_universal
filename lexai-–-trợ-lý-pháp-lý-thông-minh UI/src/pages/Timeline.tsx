/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Clock,
  Loader2,
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Map,
  Bookmark,
  Check,
} from 'lucide-react';
import { getTimeline, TimelineResult, saveAnalysis } from '../lib/api';
import { cn } from '../lib/api';
import { getContextDomain, useSyncedSituation } from '../lib/analysisContext';
import { useToast } from '../lib/useToast';
import { ToastContainer } from '../components/ui/ToastContainer';

// ── Config ────────────────────────────────────────────────────────────────────

const DOMAIN_OPTIONS = [
  { value: 'general',      label: 'Tự động nhận dạng' },
  { value: 'dat_dai',      label: 'Đất đai / BĐS' },
  { value: 'hop_dong',     label: 'Hợp đồng' },
  { value: 'lao_dong',     label: 'Lao động' },
  { value: 'dan_su',       label: 'Dân sự / Gia đình' },
  { value: 'doanh_nghiep', label: 'Doanh nghiệp' },
  { value: 'hinh_su',      label: 'Hình sự' },
  { value: 'hanh_chinh',   label: 'Hành chính' },
];

const STAGE_COLORS: Record<string, string> = {
  preparation:       'bg-blue-500/20 border-blue-500/40 text-blue-300',
  dispute_emerging:  'bg-yellow-500/20 border-yellow-500/40 text-yellow-300',
  negotiation:       'bg-purple-500/20 border-purple-500/40 text-purple-300',
  violation_occurred:'bg-orange-500/20 border-orange-500/40 text-orange-300',
  pre_litigation:    'bg-red-500/20 border-red-500/40 text-red-300',
  in_litigation:     'bg-red-600/20 border-red-600/40 text-red-400',
  awaiting_decision: 'bg-slate-500/20 border-slate-500/40 text-slate-300',
  post_decision:     'bg-green-500/20 border-green-500/40 text-green-300',
};

const URGENCY_COLORS = (days: number) =>
  days <= 7  ? 'text-red-400 bg-red-500/10 border-red-500/30' :
  days <= 30 ? 'text-orange-400 bg-orange-500/10 border-orange-500/30' :
  days <= 90 ? 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30' :
               'text-slate-400 bg-white/5 border-white/10';

const SAMPLE_SITUATIONS = [
  'Tôi mua đất bằng giấy tay năm 2020, bên bán đang đòi lại đất',
  'Công ty không trả lương 3 tháng, tôi muốn khởi kiện',
  'Hợp đồng dịch vụ bị vi phạm, bên kia không thực hiện đúng cam kết',
  'Đang trong quá trình thương lượng bồi thường tai nạn giao thông',
];

// ── Progress bar ──────────────────────────────────────────────────────────────

function ProgressBar({ pct }: { pct: number }) {
  const color =
    pct >= 75 ? '#ef4444' :
    pct >= 50 ? '#f97316' :
    pct >= 25 ? '#eab308' : '#3b82f6';
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">Tiến trình vụ việc</span>
        <span className="font-bold" style={{ color }}>{pct}%</span>
      </div>
      <div className="h-2.5 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

// ── Deadline card ─────────────────────────────────────────────────────────────

function DeadlineCard({ label, days, unit, note }: { label: string; days: number; unit: string; note: string }) {
  const colorClass = URGENCY_COLORS(days);
  return (
    <div className={cn('flex items-start gap-3 p-3.5 rounded-xl border', colorClass)}>
      <CalendarDays size={16} className="flex-none mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-semibold text-white">{label}</p>
          <span className="text-xs font-bold shrink-0">{days} {unit}</span>
        </div>
        <p className="text-[11px] text-slate-400 mt-0.5">{note}</p>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function Timeline() {
  const location = useLocation();
  const [situation, setSituation] = useSyncedSituation(location.state);
  const [domain, setDomain]       = useState(() => getContextDomain(location.state));
  const [factsText, setFactsText] = useState('');
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState<TimelineResult | null>(null);
  const [error, setError]         = useState('');
  const [saved, setSaved]         = useState(false);
  const { toasts, toast, dismiss } = useToast();

  async function handleTrack() {
    if (!situation.trim() || situation.trim().length < 10) {
      setError('Mô tả tình huống quá ngắn. Vui lòng cung cấp thêm chi tiết (ít nhất 10 ký tự).');
      return;
    }
    setLoading(true);
    setResult(null);
    setError('');
    setSaved(false);
    try {
      const facts = factsText
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean);
      const r = await getTimeline(situation.trim(), domain, facts);
      setResult(r);
    } catch {
      setError('Không thể kết nối máy chủ. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  }

  const stageClass = result
    ? (STAGE_COLORS[result.stage] ?? 'bg-slate-500/20 border-slate-500/40 text-slate-300')
    : '';

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <ToastContainer toasts={toasts} dismiss={dismiss} />
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-legal-gold/10 border border-legal-gold/20 rounded-xl flex items-center justify-center">
          <Clock size={20} className="text-legal-gold" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Theo dõi tiến trình pháp lý</h1>
          <p className="text-sm text-slate-400">Xác định giai đoạn, thời hiệu quan trọng và hướng dẫn bước tiếp theo</p>
        </div>
      </div>

      {/* Input card */}
      <div className="glass-card p-6 space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Mô tả tình huống</label>
          <textarea
            value={situation}
            onChange={e => setSituation(e.target.value)}
            placeholder="Mô tả vụ việc của bạn, càng chi tiết càng tốt..."
            rows={3}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
          />
        </div>

        {/* Samples */}
        <div className="flex flex-wrap gap-1.5">
          {SAMPLE_SITUATIONS.map((s, i) => (
            <button
              key={i}
              onClick={() => setSituation(s)}
              className="text-[10px] px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-legal-gold/30 transition-colors text-left max-w-xs truncate"
            >
              {s.slice(0, 55)}…
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Lĩnh vực pháp lý</label>
            <select
              value={domain}
              onChange={e => setDomain(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-legal-gold/50 transition-colors"
            >
              {DOMAIN_OPTIONS.map(d => (
                <option key={d.value} value={d.value} className="bg-slate-900">{d.label}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Sự kiện đã xảy ra (mỗi dòng 1 mục)
            </label>
            <textarea
              value={factsText}
              onChange={e => setFactsText(e.target.value)}
              placeholder={'Ví dụ:\nĐã gửi thông báo vi phạm\nChưa nhận được phản hồi'}
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
            />
          </div>
        </div>

        <button
          onClick={handleTrack}
          disabled={loading || situation.trim().length < 10}
          className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy font-bold rounded-xl disabled:opacity-40 hover:scale-105 active:scale-95 transition-all text-sm"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Clock size={16} />}
          {loading ? 'Đang phân tích...' : 'Phân tích tiến trình'}
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
          {/* Stage + progress */}
          <div className="glass-card p-5 space-y-4">
            <div className="flex items-center gap-3 flex-wrap">
              <div className={cn('px-4 py-2 rounded-xl border text-sm font-bold', stageClass)}>
                {result.stage_label}
              </div>
              <span className="text-xs text-slate-500">
                Độ tin cậy: {Math.round(result.stage_confidence * 100)}%
              </span>
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <ChevronRight size={14} />
                <span>Tiếp theo: <span className="text-white font-medium">{result.next_stage_label}</span></span>
              </div>
              <button
                onClick={() => {
                  saveAnalysis({ type: 'timeline', title: situation.slice(0, 80), domain, summary: result.summary, data: result }).then(() => toast('Đã lưu vào lịch sử'));
                  setSaved(true);
                }}
                disabled={saved}
                className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border bg-white/5 border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 disabled:opacity-60"
              >
                {saved ? <><Check size={12} className="text-green-400" /> Đã lưu</> : <><Bookmark size={12} /> Lưu kết quả</>}
              </button>
            </div>
            <ProgressBar pct={result.progress_percent} />
            <p className="text-sm text-slate-300 leading-relaxed">{result.summary}</p>
            {result.warnings?.map((w, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-orange-400 p-2.5 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                <AlertTriangle size={12} />
                {w}
              </div>
            ))}
          </div>

          {/* Deadlines */}
          {result.typical_deadlines?.length > 0 && (
            <div className="glass-card p-5 space-y-3">
              <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <CalendarDays size={14} className="text-legal-gold" />
                Thời hiệu và thời hạn quan trọng
              </h2>
              {result.typical_deadlines.map((d, i) => (
                <DeadlineCard key={i} {...d} />
              ))}
            </div>
          )}

          {/* Alerts */}
          {result.alerts?.length > 0 && (
            <div className="glass-card p-5 space-y-2">
              <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <AlertTriangle size={14} className="text-yellow-400" />
                Cảnh báo
              </h2>
              {result.alerts.map((a, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-yellow-300 p-2.5 bg-yellow-500/8 border border-yellow-500/20 rounded-lg">
                  <AlertTriangle size={12} className="flex-none mt-0.5" />
                  {a}
                </div>
              ))}
            </div>
          )}

          {/* All clear on deadlines */}
          {(!result.typical_deadlines || result.typical_deadlines.length === 0) && (
            <div className="glass-card p-4 flex items-center gap-3 text-slate-400">
              <CheckCircle2 size={18} />
              <p className="text-sm">Không có thời hiệu khẩn cấp nào phát hiện ở giai đoạn này.</p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="py-20 flex flex-col items-center text-center space-y-3 opacity-30">
          <Map size={64} className="text-slate-500" />
          <p className="text-sm font-bold text-slate-500">Mô tả tình huống để xem tiến trình và thời hiệu pháp lý</p>
        </div>
      )}
    </div>
  );
}
