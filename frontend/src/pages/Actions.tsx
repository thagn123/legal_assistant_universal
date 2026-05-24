/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  ListChecks,
  Zap,
  Star,
  Circle,
  Loader2,
  AlertTriangle,
  FileSearch,
  Scale,
  MessageSquare,
  ClipboardList,
  Shield,
  Clock,
  Bookmark,
  Check,
} from 'lucide-react';
import { getActionPlan, ActionPlanResult, ActionItem, saveAnalysis } from '../lib/api';
import { getContextSummary } from '../lib/analysisContext';

// ── Helpers ───────────────────────────────────────────────────────────────────

const CATEGORY_ICON: Record<ActionItem['category'], React.ReactNode> = {
  evidence:      <FileSearch size={14} className="text-blue-400 shrink-0" />,
  legal:         <Scale size={14} className="text-legal-gold shrink-0" />,
  communication: <MessageSquare size={14} className="text-purple-400 shrink-0" />,
  procedure:     <ClipboardList size={14} className="text-green-400 shrink-0" />,
  prevention:    <Shield size={14} className="text-slate-400 shrink-0" />,
};

const URGENCY_CONFIG = {
  critical: { label: 'Cực kỳ khẩn cấp', bar: 'bg-red-500',    text: 'text-red-400',    border: 'border-red-500/30' },
  high:     { label: 'Khẩn cấp',         bar: 'bg-orange-500', text: 'text-orange-400', border: 'border-orange-500/30' },
  medium:   { label: 'Nên thực hiện sớm',bar: 'bg-yellow-500', text: 'text-yellow-400', border: 'border-yellow-500/30' },
  low:      { label: 'Có thể lên kế hoạch', bar: 'bg-green-500', text: 'text-green-400', border: 'border-green-500/30' },
} as const;

// ── Action card ───────────────────────────────────────────────────────────────

function ActionCard({ item, index }: { item: ActionItem; index: number }) {
  return (
    <div className="flex gap-3 p-4 bg-white/5 border border-white/8 rounded-xl hover:bg-white/8 transition-all">
      <div className="flex-none flex flex-col items-center gap-2 pt-0.5">
        <span className="w-6 h-6 rounded-full bg-legal-gold/15 text-legal-gold text-[10px] font-bold flex items-center justify-center border border-legal-gold/20">
          {index + 1}
        </span>
      </div>
      <div className="flex-1 min-w-0 space-y-1.5">
        <p className="text-sm font-semibold text-white leading-snug">{item.step}</p>
        <p className="text-xs text-slate-400 italic">{item.reason}</p>
        <div className="flex items-center gap-3 flex-wrap">
          {CATEGORY_ICON[item.category]}
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
            {item.category === 'evidence' ? 'Chứng cứ' :
             item.category === 'legal' ? 'Pháp lý' :
             item.category === 'communication' ? 'Liên lạc' :
             item.category === 'procedure' ? 'Thủ tục' : 'Phòng ngừa'}
          </span>
          {item.deadline && (
            <span className="flex items-center gap-1 text-[10px] text-slate-500">
              <Clock size={10} />
              {item.deadline}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Priority section ──────────────────────────────────────────────────────────

function PrioritySection({
  title, actions, icon, emptyText,
}: {
  title: string;
  actions: ActionItem[];
  icon: React.ReactNode;
  emptyText: string;
}) {
  return (
    <div className="space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-bold text-white">
        {icon}
        {title}
        <span className="ml-auto text-[10px] font-normal text-slate-500">{actions.length} hành động</span>
      </h3>
      {actions.length > 0 ? (
        <div className="space-y-2">
          {actions.map((a, i) => <ActionCard key={i} item={a} index={i} />)}
        </div>
      ) : (
        <p className="text-xs text-slate-600 italic pl-2">{emptyText}</p>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function Actions() {
  const location = useLocation();
  const [situation, setSituation] = useState(() => getContextSummary(location.state));
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ActionPlanResult | null>(null);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  async function handlePlan() {
    if (!situation.trim()) return;
    setLoading(true);
    setResult(null);
    setError('');
    setSaved(false);
    try {
      const r = await getActionPlan(situation.trim());
      setResult(r);
    } catch {
      setError('Không thể kết nối máy chủ. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  }

  const urgency = result ? URGENCY_CONFIG[result.urgency] : null;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-legal-gold/10 border border-legal-gold/20 rounded-xl flex items-center justify-center">
          <ListChecks size={20} className="text-legal-gold" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Kế Hoạch Hành Động</h1>
          <p className="text-sm text-slate-400">Sinh kế hoạch hành động pháp lý ưu tiên theo giai đoạn và chứng cứ hiện có</p>
        </div>
      </div>

      {/* Input */}
      <div className="glass-card p-6 space-y-4">
        <label className="text-sm font-semibold text-white">Mô tả tình huống pháp lý của bạn</label>
        <textarea
          value={situation}
          onChange={e => setSituation(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handlePlan(); }}
          placeholder="Ví dụ: Công ty tôi bị đối tác vi phạm hợp đồng không giao hàng đúng hạn, gây thiệt hại 500 triệu đồng..."
          rows={3}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
        />
        <div className="flex items-center gap-3">
          <button
            onClick={handlePlan}
            disabled={loading || !situation.trim()}
            className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy font-bold rounded-xl disabled:opacity-40 hover:scale-105 active:scale-95 transition-all text-sm"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <ListChecks size={16} />}
            {loading ? 'Đang lập kế hoạch...' : 'Lập kế hoạch hành động'}
          </button>
          <span className="text-[11px] text-slate-500">Ctrl+Enter để gửi</span>
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
          {/* Summary bar */}
          <div className={`glass-card p-5 border ${urgency?.border}`}>
            <div className="flex items-start justify-between gap-4 mb-3">
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-400 mb-1">Giai đoạn: <span className="text-white font-semibold">{result.stage_label}</span></p>
                <p className="text-xs text-slate-400 italic">{result.summary}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={`text-xs font-bold px-3 py-1 rounded-full border ${urgency?.text} ${urgency?.border} bg-white/5`}>
                  {urgency?.label}
                </span>
                <button
                  onClick={() => {
                    saveAnalysis({ type: 'action_plan', title: situation.slice(0, 80), domain: result.domain, summary: result.summary, data: result });
                    setSaved(true);
                  }}
                  disabled={saved}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border bg-white/5 border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 disabled:opacity-60"
                >
                  {saved ? <><Check size={12} className="text-green-400" /> Đã lưu</> : <><Bookmark size={12} /> Lưu</>}
                </button>
              </div>
            </div>
            <div className="flex gap-4 text-xs">
              <span className="text-red-400 font-bold">{result.immediate_actions.length} Khẩn cấp</span>
              <span className="text-yellow-400 font-bold">{result.important_actions.length} Quan trọng</span>
              <span className="text-slate-400">{result.optional_actions.length} Tùy chọn</span>
            </div>
          </div>

          {/* Immediate */}
          <div className="glass-card p-5">
            <PrioritySection
              title="Hành động khẩn cấp"
              actions={result.immediate_actions}
              icon={<Zap size={16} className="text-red-400" />}
              emptyText="Không có hành động khẩn cấp nào cần thực hiện ngay."
            />
          </div>

          {/* Important */}
          <div className="glass-card p-5">
            <PrioritySection
              title="Hành động quan trọng"
              actions={result.important_actions}
              icon={<Star size={16} className="text-yellow-400" />}
              emptyText="Không có hành động quan trọng bổ sung."
            />
          </div>

          {/* Optional */}
          {result.optional_actions.length > 0 && (
            <div className="glass-card p-5">
              <PrioritySection
                title="Hành động tùy chọn"
                actions={result.optional_actions}
                icon={<Circle size={16} className="text-slate-400" />}
                emptyText=""
              />
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="py-20 flex flex-col items-center text-center space-y-3 opacity-30">
          <ListChecks size={64} className="text-slate-500" />
          <p className="text-sm font-bold text-slate-500">Nhập tình huống để nhận kế hoạch hành động cụ thể</p>
        </div>
      )}
    </div>
  );
}
