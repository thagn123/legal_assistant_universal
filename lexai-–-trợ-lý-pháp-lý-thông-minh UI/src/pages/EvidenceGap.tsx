/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Search,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  FileSearch,
  ChevronDown,
  ChevronUp,
  Bookmark,
  Check,
  HelpCircle,
} from 'lucide-react';
import { getEvidenceGap, EvidenceGapResult, EvidenceItem, saveAnalysis } from '../lib/api';
import { cn } from '../lib/api';
import { getAnalysisContext, getContextDomain, useSyncedSituation } from '../lib/analysisContext';
import { useToast } from '../lib/useToast';
import { ToastContainer } from '../components/ui/ToastContainer';

// ── Config ────────────────────────────────────────────────────────────────────

const DOMAIN_OPTIONS = [
  { value: 'general',      label: 'Tự động nhận dạng' },
  { value: 'dat_dai',      label: 'Đất đai / BĐS' },
  { value: 'hop_dong',     label: 'Hợp đồng' },
  { value: 'lao_dong',     label: 'Lao động' },
  { value: 'gia_dinh',     label: 'Hôn nhân gia đình' },
  { value: 'dan_su',       label: 'Dân sự / Thừa kế' },
  { value: 'doanh_nghiep', label: 'Doanh nghiệp' },
  { value: 'hinh_su',      label: 'Hình sự' },
  { value: 'hanh_chinh',   label: 'Hành chính' },
];

const PRIORITY_CONFIG = {
  high:   { label: 'Ưu tiên cao',   color: 'text-red-400',    bg: 'bg-red-500/10 border-red-500/30' },
  medium: { label: 'Ưu tiên vừa',   color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30' },
  low:    { label: 'Ưu tiên thấp',  color: 'text-slate-400',  bg: 'bg-white/5 border-white/10' },
} as const;

const CATEGORY_LABELS: Record<string, string> = {
  title: "Giấy tờ giao dịch / quyền sử dụng",
  confirmation: "Xác nhận của cơ quan địa phương",
  certificate: "Giấy chứng nhận",
  map: "Bản đồ / sơ đồ thửa đất",
  witness: "Nhân chứng",
  payment: "Chứng từ thanh toán",
  contract: "Hợp đồng / thỏa thuận",
  termination: "Quyết định / thông báo chấm dứt",
  salary: "Chứng từ lương / thu nhập",
  income: "Chứng minh thu nhập",
  marriage: "Giấy tờ hôn nhân",
  birth: "Giấy khai sinh",
  custody: "Điều kiện chăm sóc con",
  ownership: "Chứng minh quyền sở hữu",
  identity: "Giấy tờ tùy thân",
  other: "Tài liệu khác",
};

function categoryLabel(item: EvidenceItem): string {
  const key = (item.category || '').toLowerCase();
  return item.category_label || CATEGORY_LABELS[key] || item.category || 'Tài liệu khác';
}

// ── Coverage bar ──────────────────────────────────────────────────────────────

function CoverageBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 70 ? '#22c55e' :
    pct >= 45 ? '#eab308' :
    pct >= 25 ? '#f97316' : '#ef4444';
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-slate-400 font-semibold">Độ phủ chứng cứ</span>
        <span className="font-bold" style={{ color }}>{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

// ── Evidence item row ─────────────────────────────────────────────────────────

function EvidenceRow({
  item,
  tone = 'missing',
}: {
  item: EvidenceItem;
  tone?: 'present' | 'missing' | 'uncertain' | 'contradicted';
}) {
  const cfg = PRIORITY_CONFIG[item.priority] ?? PRIORITY_CONFIG.low;
  const toneCfg = {
    present: {
      icon: <CheckCircle2 size={15} className="flex-none mt-0.5 text-green-400" />,
      bg: 'bg-green-500/10 border-green-500/25',
      label: 'Đã có',
      labelColor: 'text-green-400',
    },
    missing: {
      icon: <XCircle size={15} className={cn('flex-none mt-0.5', cfg.color)} />,
      bg: cfg.bg,
      label: 'Cần bổ sung',
      labelColor: cfg.color,
    },
    uncertain: {
      icon: <HelpCircle size={15} className="flex-none mt-0.5 text-blue-300" />,
      bg: 'bg-blue-500/10 border-blue-500/25',
      label: 'Chưa rõ',
      labelColor: 'text-blue-300',
    },
    contradicted: {
      icon: <AlertTriangle size={15} className="flex-none mt-0.5 text-orange-400" />,
      bg: 'bg-orange-500/10 border-orange-500/25',
      label: 'Mâu thuẫn',
      labelColor: 'text-orange-400',
    },
  }[tone];
  return (
    <div className={cn('flex items-start gap-3 p-3 rounded-xl border', toneCfg.bg)}>
      {toneCfg.icon}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white font-medium">{item.title || item.item}</p>
        {item.matched_text && (
          <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{item.matched_text}</p>
        )}
        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
          <span className="text-[10px] text-slate-500">{categoryLabel(item)}</span>
          <span className={cn('text-[10px] font-bold', toneCfg.labelColor)}>{toneCfg.label}</span>
          <span className={cn('text-[10px] font-bold', cfg.color)}>{cfg.label}</span>
        </div>
      </div>
    </div>
  );
}

function EvidenceGroupSection({
  title,
  icon,
  items,
  tone,
}: {
  title: string;
  icon: React.ReactNode;
  items: EvidenceItem[];
  tone: 'present' | 'missing' | 'uncertain' | 'contradicted';
}) {
  if (!items.length) return null;
  const grouped: Record<string, EvidenceItem[]> = {};
  for (const item of items) {
    const label = categoryLabel(item);
    if (!grouped[label]) grouped[label] = [];
    grouped[label].push(item);
  }
  return (
    <div className="glass-card p-5 space-y-5">
      <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
        {icon}
        {title}
      </h2>
      {Object.entries(grouped).map(([cat, group]) => (
        <div key={cat} className="space-y-2">
          <div className="flex items-center gap-2">
            <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">{cat}</h3>
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/5 text-slate-400 border border-white/10">
              {group.length} mục
            </span>
          </div>
          {group.map((item, idx) => (
            <EvidenceRow key={`${item.evidence_id || item.item}-${idx}`} item={item} tone={tone} />
          ))}
        </div>
      ))}
    </div>
  );
}

// ── Strong/Weak evidence list ─────────────────────────────────────────────────

function EvidenceStrengthSection({
  strong, weak,
}: { strong: string[]; weak: string[] }) {
  const [open, setOpen] = useState(false);
  if (!strong.length && !weak.length) return null;
  return (
    <div className="rounded-xl border border-white/10 bg-white/5">
      <button
        onClick={() => setOpen(p => !p)}
        className="w-full flex items-center justify-between px-4 py-3"
      >
        <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
          Đánh giá chứng cứ hiện có
        </span>
        {open ? <ChevronUp size={14} className="text-slate-500" /> : <ChevronDown size={14} className="text-slate-500" />}
      </button>
      {open && (
        <div className="border-t border-white/8 px-4 py-3 space-y-3 animate-in fade-in duration-150">
          {strong.length > 0 && (
            <div>
              <p className="text-[10px] font-bold text-green-400 uppercase tracking-wider mb-1.5">Chứng cứ mạnh</p>
              {strong.map((s, i) => (
                <div key={i} className="flex items-start gap-2 py-1">
                  <CheckCircle2 size={13} className="text-green-400 flex-none mt-0.5" />
                  <span className="text-[11px] text-slate-300">{s}</span>
                </div>
              ))}
            </div>
          )}
          {weak.length > 0 && (
            <div>
              <p className="text-[10px] font-bold text-yellow-400 uppercase tracking-wider mb-1.5">Chứng cứ yếu</p>
              {weak.map((s, i) => (
                <div key={i} className="flex items-start gap-2 py-1">
                  <AlertTriangle size={13} className="text-yellow-400 flex-none mt-0.5" />
                  <span className="text-[11px] text-slate-300">{s}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function EvidenceGap() {
  const location = useLocation();
  const [situation, setSituation] = useSyncedSituation(location.state);
  const [domain, setDomain]       = useState(() => getContextDomain(location.state));
  const sessionId = getAnalysisContext(location.state).sessionId ?? '';
  const [factsText, setFactsText] = useState('');
  const [loading, setLoading]     = useState(false);
  const [result, setResult]       = useState<EvidenceGapResult | null>(null);
  const [error, setError]         = useState('');
  const [saved, setSaved]         = useState(false);
  const { toasts, toast, dismiss } = useToast();

  async function handleCheck() {
    if (!situation.trim()) return;
    setLoading(true);
    setResult(null);
    setError('');
    setSaved(false);
    try {
      const facts = factsText
        .split('\n')
        .map(s => s.trim())
        .filter(Boolean);
      const r = await getEvidenceGap(situation.trim(), domain, facts, sessionId);
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
          <FileSearch size={20} className="text-legal-gold" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Phát hiện thiếu chứng cứ</h1>
          <p className="text-sm text-slate-400">Kiểm tra chứng cứ hiện có và phát hiện những gì còn thiếu để bảo vệ vụ việc</p>
        </div>
      </div>

      {/* Input card */}
      <div className="glass-card p-6 space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Mô tả tình huống</label>
          <textarea
            value={situation}
            onChange={e => setSituation(e.target.value)}
            placeholder="Ví dụ: Tôi mua đất bằng giấy tay năm 2020, bên bán đang đòi lại..."
            rows={3}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
          />
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
              Chứng cứ đã có (mỗi dòng một mục)
            </label>
            <textarea
              value={factsText}
              onChange={e => setFactsText(e.target.value)}
              placeholder={'Ví dụ:\nGiấy tờ mua bán viết tay\nBiên lai chuyển khoản'}
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
            />
          </div>
        </div>

        <button
          onClick={handleCheck}
          disabled={loading || !situation.trim()}
          className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy font-bold rounded-xl disabled:opacity-40 hover:scale-105 active:scale-95 transition-all text-sm"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
          {loading ? 'Đang kiểm tra...' : 'Kiểm tra chứng cứ'}
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
          {/* Summary */}
          <div className="glass-card p-5 space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <CoverageBar score={result.coverage_score} />
              <button
                onClick={() => {
                  saveAnalysis({ type: 'evidence_gap', title: situation.slice(0, 80), domain, summary: result.summary, data: result }).then(() => toast('Đã lưu vào lịch sử'));
                  setSaved(true);
                }}
                disabled={saved}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border bg-white/5 border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 disabled:opacity-60"
              >
                {saved ? <><Check size={12} className="text-green-400" /> Đã lưu</> : <><Bookmark size={12} /> Lưu kết quả</>}
              </button>
            </div>
            <p className="text-sm text-slate-300 leading-relaxed">{result.summary}</p>
            <div className="flex gap-4 text-xs flex-wrap">
              <span className="text-green-400 font-bold">
                {result.present_evidence?.length || result.strong_evidence.length} Chứng cứ đã có
              </span>
              <span className="text-red-400 font-bold">
                {result.priority_items.length} Ưu tiên cao cần bổ sung
              </span>
              <span className="text-blue-300 font-bold">
                {result.uncertain_evidence?.length || 0} Mục cần xác minh
              </span>
              <span className="text-yellow-400 font-bold">
                {result.missing_evidence.length} Tổng mục còn thiếu
              </span>
            </div>
            {result.warnings?.map((w, i) => (
              <div key={i} className="flex items-center gap-2 text-xs text-orange-400 p-2.5 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                <AlertTriangle size={12} />
                {w}
              </div>
            ))}
            <p className="text-[11px] text-slate-400 italic">{result.advice}</p>
          </div>

          <EvidenceGroupSection
            title="Chứng cứ đã có"
            icon={<CheckCircle2 size={14} className="text-green-400" />}
            items={result.present_evidence || []}
            tone="present"
          />

          <EvidenceGroupSection
            title="Chứng cứ cần bổ sung"
            icon={<ShieldAlert size={14} className="text-red-400" />}
            items={result.missing_evidence}
            tone="missing"
          />

          <EvidenceGroupSection
            title="Chứng cứ chưa rõ / nên xác minh"
            icon={<HelpCircle size={14} className="text-blue-300" />}
            items={result.uncertain_evidence || []}
            tone="uncertain"
          />

          <EvidenceGroupSection
            title="Mâu thuẫn cần làm rõ"
            icon={<AlertTriangle size={14} className="text-orange-400" />}
            items={result.contradictions || []}
            tone="contradicted"
          />

          {result.recommendations?.length > 0 && (
            <div className="glass-card p-5 space-y-3">
              <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <CheckCircle2 size={14} className="text-legal-gold" />
                Gợi ý tiếp theo
              </h2>
              <ul className="space-y-2">
                {result.recommendations.map((rec, i) => (
                  <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-legal-gold flex-none" />
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Existing evidence assessment */}
          <EvidenceStrengthSection strong={result.strong_evidence} weak={result.weak_evidence} />

          {/* All clear */}
          {result.missing_evidence.length === 0 && (result.contradictions?.length || 0) === 0 && (
            <div className="glass-card p-5 flex items-center gap-3 text-green-400">
              <CheckCircle2 size={20} />
              <p className="text-sm font-medium">Không phát hiện chứng cứ ưu tiên cao còn thiếu theo thông tin hiện có.</p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="py-20 flex flex-col items-center text-center space-y-3 opacity-30">
          <FileSearch size={64} className="text-slate-500" />
          <p className="text-sm font-bold text-slate-500">Mô tả tình huống để kiểm tra chứng cứ cần thiết</p>
        </div>
      )}
    </div>
  );
}
