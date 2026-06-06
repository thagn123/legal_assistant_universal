/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  ShieldAlert,
  History,
  Search,
  AlertTriangle,
  CheckSquare,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Loader2,
  CheckCircle2,
  XCircle,
  Info,
  ChevronRight,
  Bookmark,
  Check,
} from 'lucide-react';
import { apiFetch, RiskAssessment, logInteraction, analyzeRisk, RiskAnalysisResult, saveAnalysis } from '../lib/api';

// ── Risk score gauge ──────────────────────────────────────────────────────────

function RiskGauge({ score, level }: { score: number; level: string }) {
  const color =
    level === 'critical' ? '#ef4444' :
    level === 'high'     ? '#f97316' :
    level === 'medium'   ? '#eab308' : '#22c55e';
  const label =
    level === 'critical' ? 'Rất cao' :
    level === 'high'     ? 'Cao' :
    level === 'medium'   ? 'Trung bình' : 'Thấp';

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-32 h-32">
        <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
          <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="12" />
          <circle
            cx="60" cy="60" r="50"
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeDasharray={`${(score / 100) * 314} 314`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 0.8s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-white">{Math.round(score)}</span>
          <span className="text-[10px] text-slate-400">/100</span>
        </div>
      </div>
      <span className="text-sm font-bold" style={{ color }}>{label}</span>
    </div>
  );
}

// ── List section ──────────────────────────────────────────────────────────────

function RiskSection({
  title, items, icon, itemColor,
}: {
  title: string;
  items: string[];
  icon: React.ReactNode;
  itemColor: string;
}) {
  if (!items.length) return null;
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{title}</p>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className={`flex gap-2 text-xs ${itemColor}`}>
            <span className="shrink-0 mt-0.5">{icon}</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── AI Risk Analysis panel ────────────────────────────────────────────────────

function AiRiskPanel() {
  const location = useLocation();
  const [situation, setSituation] = useState(() => {
    const state = location.state as { situation?: string; prefill?: { situation?: string } } | null;
    return state?.situation || state?.prefill?.situation || sessionStorage.getItem('lexai_current_situation') || '';
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RiskAnalysisResult | null>(null);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  // Pre-fill and auto-run when navigated with context
  useEffect(() => {
    const state = location.state as { situation?: string; prefill?: { situation?: string } } | null;
    const initialSituation = state?.situation || state?.prefill?.situation;
    if (initialSituation) {
      setSituation(initialSituation);
      sessionStorage.setItem('lexai_current_situation', initialSituation);
      
      const runAuto = async () => {
        setLoading(true);
        setResult(null);
        setError('');
        setSaved(false);
        try {
          const r = await analyzeRisk(initialSituation.trim());
          setResult(r);
        } catch {
          setError('Không thể kết nối máy chủ. Vui lòng thử lại.');
        } finally {
          setLoading(false);
        }
      };
      runAuto();
      window.history.replaceState({}, '');
    }
  }, [location.state]);

  async function handleAnalyze() {
    if (!situation.trim() || situation.trim().length < 10) {
      setError('Mô tả tình huống quá ngắn. Vui lòng cung cấp thêm chi tiết (ít nhất 10 ký tự).');
      return;
    }
    sessionStorage.setItem('lexai_current_situation', situation.trim());
    setLoading(true);
    setResult(null);
    setError('');
    setSaved(false);
    try {
      const r = await analyzeRisk(situation.trim());
      setResult(r);
    } catch {
      setError('Không thể kết nối máy chủ. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Input */}
      <div className="glass-card p-6 space-y-4">
        <label className="text-sm font-semibold text-white">Mô tả tình huống cần đánh giá rủi ro</label>
        <textarea
          value={situation}
          onChange={e => setSituation(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleAnalyze(); }}
          placeholder="Ví dụ: Tôi mua đất bằng giấy tay năm 2020, bên bán nay đòi lại và không chịu ký công chứng..."
          rows={3}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
        />
        <div className="flex items-center gap-3">
          <button
            onClick={handleAnalyze}
            disabled={loading || situation.trim().length < 10}
            className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy font-bold rounded-xl disabled:opacity-40 hover:scale-105 active:scale-95 transition-all text-sm"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            {loading ? 'Đang phân tích...' : 'Đánh giá rủi ro AI'}
          </button>
          <span className="text-[11px] text-slate-500">Ctrl+Enter để gửi</span>
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>

      {/* Result */}
      {result && (
        <div className="space-y-4 animate-in fade-in duration-300">
          {/* Gauge + summary row */}
          <div className="glass-card p-6 flex flex-col md:flex-row items-center gap-8">
            <RiskGauge score={result.risk_score} level={result.risk_level} />
            <div className="flex-1 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-xs text-slate-400 italic flex-1">{result.summary}</p>
                <button
                  onClick={() => {
                    saveAnalysis({ type: 'risk_analysis', title: situation.slice(0, 80), summary: result.summary, data: result });
                    setSaved(true);
                  }}
                  disabled={saved}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border bg-white/5 border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 disabled:opacity-60 shrink-0"
                >
                  {saved ? <><Check size={12} className="text-green-400" /> Đã lưu</> : <><Bookmark size={12} /> Lưu</>}
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-slate-300">
                  Giai đoạn: <span className="text-white font-semibold">{result.stage_label}</span>
                </span>
                <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-slate-300">
                  Phủ chứng cứ: <span className="text-white font-semibold">{Math.round(result.evidence_coverage * 100)}%</span>
                </span>
                <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-slate-300">
                  Độ tin cậy: <span className="text-white font-semibold">{Math.round(result.confidence * 100)}%</span>
                </span>
              </div>
            </div>
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

          {/* 2-col: strengths + weaknesses */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="glass-card p-5 space-y-3">
              <RiskSection
                title="Điểm mạnh"
                items={result.strengths}
                icon={<CheckCircle2 size={13} className="text-green-400" />}
                itemColor="text-slate-300"
              />
            </div>
            <div className="glass-card p-5 space-y-3">
              <RiskSection
                title="Điểm yếu / rủi ro"
                items={result.weaknesses}
                icon={<XCircle size={13} className="text-red-400" />}
                itemColor="text-slate-300"
              />
            </div>
          </div>

          {/* Missing + Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {result.missing_points.length > 0 && (
              <div className="glass-card p-5">
                <RiskSection
                  title="Chứng cứ còn thiếu"
                  items={result.missing_points}
                  icon={<Info size={13} className="text-yellow-400" />}
                  itemColor="text-slate-300"
                />
              </div>
            )}
            <div className="glass-card p-5">
              <RiskSection
                title="Hành động được đề xuất"
                items={result.recommended_actions}
                icon={<ChevronRight size={13} className="text-legal-gold" />}
                itemColor="text-slate-300"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Generic risk recommendations (existing) ───────────────────────────────────

function GenericRisksPanel() {
  const [activeTab, setActiveTab] = useState<'situation' | 'history'>('situation');
  const [situation, setSituation] = useState('');
  const [risks, setRisks] = useState<RiskAssessment[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<'all' | 'cao' | 'trung_binh' | 'thap'>('all');

  const fetchRisks = async (useHistory: boolean = false) => {
    if (!useHistory && (!situation.trim() || situation.trim().length < 10)) {
      alert('Mô tả tình huống quá ngắn. Vui lòng cung cấp thêm chi tiết (ít nhất 10 ký tự).');
      return;
    }
    setIsLoading(true);
    try {
      const data = await apiFetch<RiskAssessment[]>('/recommendations/risks', {
        method: 'POST',
        body: JSON.stringify({ situation, use_history: useHistory }),
      });
      const result = Array.isArray(data) ? data : [];
      setRisks(result);
      if (result.length > 0) {
        logInteraction({ action_type: 'view', context: { situation_snippet: situation.slice(0, 100) } });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredRisks = severityFilter === 'all' ? risks : risks.filter(r => r.severity === severityFilter);

  useEffect(() => {
    if (activeTab === 'history') fetchRisks(true);
  }, [activeTab]);

  return (
    <div className="space-y-8">
      <div className="flex border-b border-legal-border gap-8">
        {(['situation', 'history'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-4 px-2 text-sm font-bold transition-all relative ${activeTab === tab ? 'text-legal-gold' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <div className="flex items-center gap-2">
              {tab === 'situation' ? <Search size={16} /> : <History size={16} />}
              {tab === 'situation' ? 'Theo tình huống' : 'Theo lịch sử hội thoại'}
            </div>
            {activeTab === tab && <div className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-legal-gold" />}
          </button>
        ))}
      </div>

      {activeTab === 'situation' && (
        <div className="max-w-4xl mx-auto glass-card p-8 flex gap-4">
          <input
            type="text"
            value={situation}
            onChange={e => setSituation(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && fetchRisks(false)}
            placeholder="Nhập tình huống hoặc điều khoản cần rà soát rủi ro..."
            className="flex-1 bg-legal-navy/50 border border-white/10 rounded-xl px-6 py-4 text-sm focus:border-legal-gold transition-all"
          />
          <button
            onClick={() => fetchRisks(false)}
            className="px-8 bg-legal-gold text-legal-navy rounded-xl font-bold hover:scale-105 transition-all shadow-lg shadow-legal-gold/20"
          >
            Đánh giá
          </button>
        </div>
      )}

      <div className="space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <h3 className="text-sm font-bold text-slate-500 uppercase tracking-[0.2em] flex items-center gap-2">
            <ShieldAlert className="text-legal-gold" size={18} />
            Phân tích rủi ro pháp lý
            {risks.length > 0 && <span className="text-[10px] text-slate-600 normal-case tracking-normal font-normal">({filteredRisks.length}/{risks.length})</span>}
          </h3>
          <div className="flex items-center gap-3">
            {isLoading && <span className="text-[10px] text-legal-gold animate-pulse font-bold uppercase tracking-widest">Đang tải...</span>}
            {risks.length > 0 && (
              <select
                value={severityFilter}
                onChange={e => setSeverityFilter(e.target.value as typeof severityFilter)}
                className="bg-legal-navy/50 border border-white/10 rounded-lg px-3 py-1.5 text-[11px] font-bold text-slate-300 focus:border-legal-gold transition-all"
              >
                <option value="all">Tất cả mức độ</option>
                <option value="cao">Nguy cấp</option>
                <option value="trung_binh">Cảnh báo</option>
                <option value="thap">Ổn định</option>
              </select>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {isLoading ? (
            Array(3).fill(0).map((_, i) => <div key={i} className="glass-card aspect-square animate-skeleton" />)
          ) : filteredRisks.map(risk => (
            <div
              key={risk.id}
              className={`glass-card p-8 space-y-6 border-t-4 transition-all hover:scale-[1.02] ${
                risk.severity === 'cao' ? 'border-t-legal-danger' :
                risk.severity === 'trung_binh' ? 'border-t-legal-warning' : 'border-t-legal-success'
              }`}
            >
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-white text-lg">{risk.name}</h4>
                <span className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase ${
                  risk.severity === 'cao' ? 'bg-legal-danger/20 text-legal-danger' :
                  risk.severity === 'trung_binh' ? 'bg-legal-warning/20 text-legal-warning' : 'bg-legal-success/20 text-legal-success'
                }`}>
                  {risk.severity === 'cao' ? 'Nguy cấp' : risk.severity === 'trung_binh' ? 'Cảnh báo' : 'Ổn định'}
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">{risk.description}</p>
              <div className="space-y-4">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Chỉ số cảnh báo</p>
                <ul className="space-y-2">
                  {risk.indicators.map((ind, i) => (
                    <li key={i} className="flex gap-2 text-[11px] text-slate-300">
                      <AlertTriangle size={14} className="text-legal-warning shrink-0" />
                      {ind}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="space-y-4">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Kế hoạch giảm thiểu</p>
                <ul className="space-y-2">
                  {risk.mitigation_steps.map((step, i) => (
                    <li key={i} className="flex gap-2 text-[11px] text-slate-400">
                      <CheckSquare size={14} className="text-legal-success shrink-0" />
                      {step}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="pt-4 border-t border-white/5 mt-auto flex items-center justify-between">
                <div className="flex gap-1">
                  {risk.related_law_types.map(lt => (
                    <span key={lt} className="px-1.5 py-0.5 bg-white/5 border border-white/10 rounded text-[8px] text-slate-500 uppercase">{lt}</span>
                  ))}
                </div>
                <span className="text-[10px] font-mono text-slate-600">ID: {risk.id}</span>
              </div>
            </div>
          ))}
        </div>

        {filteredRisks.length === 0 && !isLoading && (
          <div className="py-20 flex flex-col items-center opacity-30 text-center space-y-4">
            <ShieldCheck size={64} className="text-slate-500" />
            <p className="text-sm font-bold text-slate-500">Chưa phát hiện rủi ro nào. Tuyệt vời!</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function Risks() {
  const [mainTab, setMainTab] = useState<'ai' | 'generic'>('ai');

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-500">
      {/* Top tab switcher */}
      <div className="flex items-center gap-1 p-1 bg-white/5 rounded-xl w-fit border border-white/10">
        <button
          onClick={() => setMainTab('ai')}
          className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-bold transition-all ${
            mainTab === 'ai' ? 'bg-legal-gold text-legal-navy shadow' : 'text-slate-400 hover:text-white'
          }`}
        >
          <Sparkles size={15} />
          Đánh giá AI
        </button>
        <button
          onClick={() => setMainTab('generic')}
          className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-bold transition-all ${
            mainTab === 'generic' ? 'bg-legal-gold text-legal-navy shadow' : 'text-slate-400 hover:text-white'
          }`}
        >
          <ShieldAlert size={15} />
          Gợi ý rủi ro
        </button>
      </div>

      {mainTab === 'ai' ? <AiRiskPanel /> : <GenericRisksPanel />}
    </div>
  );
}
