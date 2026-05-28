/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Map,
  ChevronRight,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Circle,
  FileSearch,
  Loader2,
  Shield,
  BookOpen,
  ExternalLink,
  Bookmark,
  Check,
} from 'lucide-react';
import { buildJourney, JourneyResult, JourneyMilestone, saveAnalysis } from '../lib/api';

// ── Helpers ──────────────────────────────────────────────────────────────────

const RISK_CONFIG = {
  low:    { label: 'Thấp',        className: 'bg-green-500/20 text-green-400 border-green-500/30' },
  medium: { label: 'Trung bình',  className: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  high:   { label: 'Cao',         className: 'bg-red-500/20 text-red-400 border-red-500/30' },
};

const STATUS_ICON: Record<JourneyMilestone['status'], React.ReactNode> = {
  done:        <CheckCircle2 size={20} className="text-green-400 shrink-0" />,
  in_progress: <Clock size={20} className="text-yellow-400 shrink-0" />,
  warning:     <AlertTriangle size={20} className="text-red-400 shrink-0" />,
  pending:     <Circle size={20} className="text-slate-500 shrink-0" />,
};

const STATUS_BORDER: Record<JourneyMilestone['status'], string> = {
  done:        'border-green-500/30',
  in_progress: 'border-yellow-500/30',
  warning:     'border-red-500/30',
  pending:     'border-slate-700',
};

// ── Sub-components ────────────────────────────────────────────────────────────

function ProgressBar({ percent }: { percent: number }) {
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>Chuẩn bị</span>
        <span className="font-semibold text-white">{percent}%</span>
        <span>Hoàn tất</span>
      </div>
      <div className="h-3 bg-white/5 rounded-full overflow-hidden border border-white/10">
        <div
          className="h-full bg-gradient-to-r from-legal-gold/80 to-legal-gold rounded-full transition-all duration-700"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function MilestoneCard({ milestone }: { milestone: JourneyMilestone }) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();

  return (
    <div
      className={`bg-white/5 border ${STATUS_BORDER[milestone.status]} rounded-2xl p-4 cursor-pointer transition-all hover:bg-white/8`}
      onClick={() => setExpanded(e => !e)}
    >
      <div className="flex items-start gap-3">
        {STATUS_ICON[milestone.status]}
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-white text-sm">{milestone.title}</p>
          <p className="text-xs text-slate-400 mt-0.5">{milestone.summary}</p>
        </div>
        <ChevronRight
          size={16}
          className={`text-slate-500 shrink-0 transition-transform ${expanded ? 'rotate-90' : ''}`}
        />
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-white/10 space-y-2">
          {milestone.detail && (
            <p className="text-xs text-slate-300 leading-relaxed">{milestone.detail}</p>
          )}
          {milestone.action_url && (
            <button
              onClick={(e) => { e.stopPropagation(); navigate(milestone.action_url); }}
              className="flex items-center gap-1 text-xs text-legal-gold hover:underline"
            >
              Xem chi tiết <ExternalLink size={12} />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function LawRefItem({ title, score }: { title: string; score: number }) {
  return (
    <div className="flex items-center justify-between gap-2 py-2 border-b border-white/5 last:border-0">
      <div className="flex items-center gap-2 min-w-0">
        <BookOpen size={14} className="text-legal-gold shrink-0" />
        <span className="text-xs text-slate-300 truncate">{title}</span>
      </div>
      <span className="text-xs text-slate-500 shrink-0">{Math.round(score * 100)}%</span>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function Journey() {
  const location = useLocation();
  const [situation, setSituation] = useState(() => {
    const state = location.state as { situation?: string; domain?: string } | null;
    return state?.situation || sessionStorage.getItem('lexai_current_situation') || '';
  });
  const [result, setResult] = useState<JourneyResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  async function handleAnalyze(overrideSituation?: string) {
    const trimmed = (overrideSituation ?? situation).trim();
    if (!trimmed) return;
    sessionStorage.setItem('lexai_current_situation', trimmed);
    setLoading(true);
    setError('');
    setSaved(false);
    try {
      const data = await buildJourney(trimmed, '', [], undefined);
      setResult(data);
    } catch (err: any) {
      setError(err?.message || 'Không thể kết nối đến máy chủ. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  }

  // Pre-fill and auto-analyze when navigated from Dashboard quick-classify
  useEffect(() => {
    const state = location.state as { situation?: string; domain?: string } | null;
    if (state?.situation) {
      setSituation(state.situation);
      sessionStorage.setItem('lexai_current_situation', state.situation);
      handleAnalyze(state.situation);
      // Clear state so navigating back + forward doesn't re-trigger
      window.history.replaceState({}, '');
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const riskCfg = result ? (RISK_CONFIG[result.risk_level] ?? RISK_CONFIG.medium) : null;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-legal-gold/10 border border-legal-gold/20 rounded-xl flex items-center justify-center">
          <Map size={20} className="text-legal-gold" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Hành Trình Pháp Lý</h1>
          <p className="text-sm text-slate-400">Xác định giai đoạn, phân tích chứng cứ và đề xuất bước tiếp theo cho vụ việc của bạn</p>
        </div>
      </div>

      {/* Input card */}
      <div className="bg-white/5 border border-legal-border rounded-2xl p-5 space-y-4">
        <label className="block text-sm font-semibold text-white">Mô tả tình huống của bạn</label>
        <textarea
          value={situation}
          onChange={e => setSituation(e.target.value)}
          placeholder="Ví dụ: Tôi mua đất bằng giấy tay năm 2020, đã thanh toán đầy đủ nhưng bên bán nay đòi lại và không chịu ký hợp đồng công chứng..."
          rows={4}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 focus:ring-1 focus:ring-legal-gold/30 transition-all"
        />
        <button
          onClick={() => handleAnalyze()}
          disabled={loading || !situation.trim()}
          className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy font-semibold rounded-xl hover:bg-legal-gold/90 disabled:opacity-40 disabled:cursor-not-allowed transition-all text-sm"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <FileSearch size={16} />}
          {loading ? 'Đang phân tích...' : 'Phân tích hành trình'}
        </button>

        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
            <AlertTriangle size={14} />
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-5 animate-in fade-in duration-300">
          {/* Stage + progress */}
          <div className="bg-white/5 border border-legal-border rounded-2xl p-5 space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-1">Giai đoạn hiện tại</p>
                <p className="text-lg font-bold text-white">{result.stage_label}</p>
                <p className="text-xs text-slate-500 mt-1">Lĩnh vực: <span className="text-slate-300">{result.domain}</span></p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {riskCfg && (
                  <span className={`px-3 py-1 rounded-full text-xs font-bold border ${riskCfg.className}`}>
                    <Shield size={10} className="inline mr-1" />
                    Rủi ro {riskCfg.label}
                  </span>
                )}
                <button
                  onClick={() => {
                    saveAnalysis({ type: 'journey', title: situation.slice(0, 80), domain: result.domain, summary: result.summary, data: result });
                    setSaved(true);
                  }}
                  disabled={saved}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border bg-white/5 border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 disabled:opacity-60"
                >
                  {saved ? <><Check size={12} className="text-green-400" /> Đã lưu</> : <><Bookmark size={12} /> Lưu</>}
                </button>
              </div>
            </div>
            <ProgressBar percent={result.progress_percent} />
            <p className="text-xs text-slate-400 italic">{result.summary}</p>
          </div>

          {/* Warnings */}
          {result.warnings.length > 0 && (
            <div className="space-y-2">
              {result.warnings.map((w, i) => (
                <div key={i} className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-xs text-red-300">
                  <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                  {w}
                </div>
              ))}
            </div>
          )}

          {/* Milestones */}
          <div className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Các mốc hành trình</h2>
            {result.milestones.map(m => (
              <MilestoneCard key={m.key} milestone={m} />
            ))}
          </div>

          {/* Two-column: next steps + law refs */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Next steps */}
            <div className="bg-white/5 border border-legal-border rounded-2xl p-4">
              <h3 className="text-sm font-semibold text-white mb-3">Bước tiếp theo đề xuất</h3>
              <ol className="space-y-2">
                {result.next_steps.map((step, i) => (
                  <li key={i} className="flex gap-2 text-xs text-slate-300">
                    <span className="flex-none w-5 h-5 bg-legal-gold/20 text-legal-gold rounded-full flex items-center justify-center font-bold text-[10px]">{i + 1}</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* Law references */}
            <div className="bg-white/5 border border-legal-border rounded-2xl p-4">
              <h3 className="text-sm font-semibold text-white mb-3">Văn bản pháp luật liên quan</h3>
              {result.law_references.length > 0 ? (
                result.law_references.map((ref, i) => (
                  <LawRefItem key={i} title={ref.title} score={ref.score} />
                ))
              ) : (
                <p className="text-xs text-slate-500 italic">Không tìm thấy văn bản pháp luật phù hợp.</p>
              )}
            </div>
          </div>

          {/* Alerts */}
          {result.alerts.length > 0 && (
            <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-2xl p-4">
              <h3 className="text-sm font-semibold text-yellow-400 mb-2">Cảnh báo quan trọng</h3>
              <ul className="space-y-1">
                {result.alerts.map((a, i) => (
                  <li key={i} className="text-xs text-slate-300 flex gap-2">
                    <span className="text-yellow-500 shrink-0">•</span> {a}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
