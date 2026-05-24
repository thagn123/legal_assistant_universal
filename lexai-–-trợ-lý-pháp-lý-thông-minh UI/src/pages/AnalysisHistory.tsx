/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  History,
  Clock,
  FileSearch,
  Gavel,
  Search,
  Trash2,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle2,
  CalendarDays,
  GitCompare,
  ListChecks,
  Radar,
  TrendingUp,
  X,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  loadHistory,
  deleteHistoryItem,
  clearHistory,
  AnalysisHistoryItem,
  AnalysisType,
  LAW_TYPE_LABELS,
} from '../lib/api';
import { cn } from '../lib/api';

// ── Config ────────────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<AnalysisType, { label: string; icon: React.ReactNode; color: string; path: string }> = {
  timeline:        { label: 'Tiến trình pháp lý', icon: <Clock size={14} />,      color: 'text-blue-400 bg-blue-500/10 border-blue-500/25',      path: '/timeline' },
  evidence_gap:    { label: 'Kiểm tra chứng cứ',  icon: <FileSearch size={14} />, color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/25', path: '/evidence-gap' },
  clause_coach:    { label: 'Tư vấn điều khoản',  icon: <Gavel size={14} />,      color: 'text-purple-400 bg-purple-500/10 border-purple-500/25', path: '/clause-coach' },
  clause_search:   { label: 'Tìm điều khoản',     icon: <Search size={14} />,     color: 'text-green-400 bg-green-500/10 border-green-500/25',   path: '/clause-search' },
  similar_cases:   { label: 'Vụ việc tương tự',   icon: <GitCompare size={14} />, color: 'text-orange-400 bg-orange-500/10 border-orange-500/25', path: '/similar-cases' },
  action_plan:     { label: 'Kế hoạch hành động', icon: <ListChecks size={14} />, color: 'text-red-400 bg-red-500/10 border-red-500/25',          path: '/actions' },
  compliance_radar:{ label: 'Compliance Radar',    icon: <Radar size={14} />,      color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/25',       path: '/compliance-radar' },
  risk_analysis:   { label: 'Phân tích rủi ro',   icon: <TrendingUp size={14} />, color: 'text-pink-400 bg-pink-500/10 border-pink-500/25',       path: '/analyze' },
};

const ALL_TYPES = Object.keys(TYPE_CONFIG) as AnalysisType[];

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
  }
}

// ── Formatted preview per type ────────────────────────────────────────────────

function FormattedPreview({ item }: { item: AnalysisHistoryItem }) {
  const d = item.data as any;
  if (!d) return <p className="text-[11px] text-slate-400 italic">Không có dữ liệu chi tiết.</p>;

  switch (item.type) {
    case 'timeline':
      return (
        <div className="space-y-2 text-[11px]">
          <p className="text-slate-300"><span className="text-slate-500 font-semibold">Giai đoạn:</span> {d.stage_label ?? '—'} ({d.progress_percent ?? 0}%)</p>
          <p className="text-slate-300"><span className="text-slate-500 font-semibold">Tiếp theo:</span> {d.next_stage_label ?? '—'}</p>
          {d.typical_deadlines?.length > 0 && (
            <div>
              <p className="text-slate-500 font-semibold mb-1">Thời hiệu:</p>
              <ul className="space-y-0.5 pl-3">
                {d.typical_deadlines.slice(0, 3).map((dl: any, i: number) => (
                  <li key={i} className="text-slate-300 list-disc">
                    {dl.label} — {dl.days} {dl.unit}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {d.warnings?.length > 0 && (
            <p className="text-orange-400 italic">⚠ {d.warnings[0]}</p>
          )}
        </div>
      );

    case 'evidence_gap':
      return (
        <div className="space-y-2 text-[11px]">
          <p className="text-slate-300"><span className="text-slate-500 font-semibold">Độ phủ:</span> {Math.round((d.coverage_score ?? 0) * 100)}%</p>
          {d.priority_items?.length > 0 && (
            <div>
              <p className="text-slate-500 font-semibold mb-1">Ưu tiên cao cần bổ sung:</p>
              <ul className="space-y-0.5 pl-3">
                {d.priority_items.slice(0, 3).map((it: any, i: number) => (
                  <li key={i} className="text-red-300 list-disc">{it.item}</li>
                ))}
              </ul>
            </div>
          )}
          {d.strong_evidence?.length > 0 && (
            <p className="text-green-400">{d.strong_evidence.length} chứng cứ mạnh</p>
          )}
        </div>
      );

    case 'clause_coach':
      return (
        <div className="space-y-2 text-[11px]">
          <p className="text-slate-300">
            <span className="text-slate-500 font-semibold">Điểm rủi ro:</span> {d.risk_score ?? 0}/100
            <span className="ml-2 capitalize text-slate-400">({d.risk_level ?? '—'})</span>
          </p>
          {d.risks?.length > 0 && (
            <div>
              <p className="text-slate-500 font-semibold mb-1">Rủi ro phát hiện:</p>
              <ul className="space-y-0.5 pl-3">
                {d.risks.slice(0, 3).map((r: any, i: number) => (
                  <li key={i} className="text-orange-300 list-disc">{r.description}</li>
                ))}
              </ul>
            </div>
          )}
          {d.missing_clauses?.length > 0 && (
            <p className="text-yellow-400">{d.missing_clauses.length} điều khoản cần bổ sung</p>
          )}
        </div>
      );

    case 'clause_search':
      return (
        <div className="space-y-2 text-[11px]">
          <p className="text-slate-300"><span className="text-slate-500 font-semibold">Tìm thấy:</span> {d.total ?? 0} điều khoản tương tự</p>
          {d.results?.length > 0 && (
            <ul className="space-y-0.5 pl-3">
              {d.results.slice(0, 3).map((r: any, i: number) => (
                <li key={i} className="text-slate-300 list-disc line-clamp-1">
                  <span className={`font-semibold ${r.risk_level === 'critical' || r.risk_level === 'high' ? 'text-red-400' : 'text-slate-400'}`}>
                    [{r.risk_label}]
                  </span>{' '}
                  {r.clause_text?.slice(0, 80)}…
                </li>
              ))}
            </ul>
          )}
        </div>
      );

    case 'similar_cases':
      return (
        <div className="space-y-2 text-[11px]">
          <p className="text-slate-300"><span className="text-slate-500 font-semibold">Tìm thấy:</span> {d.total ?? 0} vụ việc tương tự</p>
          <p className="text-slate-400">{d.query_domain_label ?? ''} · Giai đoạn: {d.query_stage_label ?? ''}</p>
          {d.similar_cases?.length > 0 && (
            <ul className="space-y-0.5 pl-3">
              {d.similar_cases.slice(0, 3).map((c: any, i: number) => (
                <li key={i} className="text-slate-300 list-disc line-clamp-1">
                  {Math.round(c.similarity_score * 100)}% — {c.title}
                </li>
              ))}
            </ul>
          )}
        </div>
      );

    case 'action_plan':
      return (
        <div className="space-y-2 text-[11px]">
          <p className="text-slate-300">
            <span className="text-slate-500 font-semibold">Tổng hành động:</span> {d.total_actions ?? 0}
            {' '}({d.immediate_actions?.length ?? 0} khẩn cấp)
          </p>
          {d.immediate_actions?.length > 0 && (
            <div>
              <p className="text-slate-500 font-semibold mb-1">Khẩn cấp:</p>
              <ul className="space-y-0.5 pl-3">
                {d.immediate_actions.slice(0, 3).map((a: any, i: number) => (
                  <li key={i} className="text-red-300 list-disc line-clamp-1">{a.step}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      );

    case 'compliance_radar':
      return (
        <div className="space-y-2 text-[11px]">
          <p className="text-slate-300">
            <span className="text-slate-500 font-semibold">Điểm tuân thủ:</span>{' '}
            {Math.round((d.compliance_score ?? 0) * 100)}%
          </p>
          <p className="text-slate-400">{d.business_type_label ?? ''} — {d.transaction_type_label ?? ''}</p>
          <p className="text-red-400">{d.critical_count ?? 0} mục bắt buộc quan trọng còn thiếu</p>
        </div>
      );

    default:
      return (
        <pre className="text-[11px] text-slate-300 whitespace-pre-wrap break-words max-h-48 overflow-y-auto leading-relaxed">
          {JSON.stringify(d, null, 2)}
        </pre>
      );
  }
}

// ── History card ──────────────────────────────────────────────────────────────

function HistoryCard({
  item,
  onDelete,
  onReopen,
}: {
  item: AnalysisHistoryItem;
  onDelete: (id: string) => void;
  onReopen: (item: AnalysisHistoryItem) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const cfg = TYPE_CONFIG[item.type] ?? TYPE_CONFIG.timeline;

  return (
    <div className="glass-card overflow-hidden">
      <div className="p-4 flex items-start gap-3">
        {/* type badge */}
        <div className={cn('flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-semibold shrink-0', cfg.color)}>
          {cfg.icon}
          {cfg.label}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white truncate">{item.title}</p>
          <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">{item.summary}</p>
          <div className="flex items-center gap-3 mt-1.5">
            {item.domain && item.domain !== 'general' && (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-legal-gold/10 text-legal-gold border border-legal-gold/20 font-medium">
                {LAW_TYPE_LABELS[item.domain] ?? item.domain}
              </span>
            )}
            <span className="flex items-center gap-1 text-[10px] text-slate-500">
              <CalendarDays size={10} />
              {formatDate(item.savedAt)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => onReopen(item)}
            title="Mở lại trang phân tích"
            className="p-1.5 rounded-lg text-slate-400 hover:text-legal-gold hover:bg-legal-gold/10 transition-all"
          >
            <RotateCcw size={14} />
          </button>
          <button
            onClick={() => setExpanded(v => !v)}
            title="Xem chi tiết"
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all"
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          <button
            onClick={() => onDelete(item.id)}
            title="Xóa"
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-white/5 px-4 py-3 bg-white/2 animate-in fade-in duration-150">
          <FormattedPreview item={item} />
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function AnalysisHistory() {
  const navigate = useNavigate();
  const [items, setItems] = useState<AnalysisHistoryItem[]>([]);
  const [filter, setFilter] = useState<AnalysisType | 'all'>('all');
  const [searchText, setSearchText] = useState('');
  const [confirmClear, setConfirmClear] = useState(false);

  useEffect(() => {
    setItems(loadHistory());
  }, []);

  function handleDelete(id: string) {
    deleteHistoryItem(id);
    setItems(prev => prev.filter(i => i.id !== id));
  }

  function handleClear() {
    if (!confirmClear) { setConfirmClear(true); return; }
    clearHistory();
    setItems([]);
    setConfirmClear(false);
  }

  function handleReopen(item: AnalysisHistoryItem) {
    navigate((TYPE_CONFIG[item.type] ?? TYPE_CONFIG.timeline).path);
  }

  const filtered = useMemo(() => {
    let list = filter === 'all' ? items : items.filter(i => i.type === filter);
    if (searchText.trim()) {
      const q = searchText.toLowerCase();
      list = list.filter(i =>
        i.title.toLowerCase().includes(q) ||
        i.summary.toLowerCase().includes(q)
      );
    }
    return list;
  }, [items, filter, searchText]);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-legal-gold/10 border border-legal-gold/20 rounded-xl flex items-center justify-center">
            <History size={20} className="text-legal-gold" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Lịch sử phân tích</h1>
            <p className="text-sm text-slate-400">Kết quả đã lưu từ các công cụ phân tích pháp lý</p>
          </div>
        </div>

        {items.length > 0 && (
          <button
            onClick={handleClear}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all',
              confirmClear
                ? 'bg-red-500/20 border border-red-500/40 text-red-400 hover:bg-red-500/30'
                : 'bg-white/5 border border-white/10 text-slate-400 hover:text-red-400 hover:border-red-500/30'
            )}
          >
            <Trash2 size={13} />
            {confirmClear ? 'Xác nhận xóa tất cả?' : 'Xóa tất cả'}
          </button>
        )}
      </div>

      {/* Search box */}
      {items.length > 0 && (
        <div className="relative">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            placeholder="Tìm kiếm theo tiêu đề hoặc tóm tắt..."
            className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-9 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-legal-gold/50 transition-colors"
          />
          {searchText && (
            <button
              onClick={() => setSearchText('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
            >
              <X size={14} />
            </button>
          )}
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setFilter('all')}
          className={cn(
            'px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border',
            filter === 'all'
              ? 'bg-legal-gold text-legal-navy border-legal-gold'
              : 'bg-white/5 border-white/10 text-slate-400 hover:text-white'
          )}
        >
          Tất cả ({items.length})
        </button>
        {ALL_TYPES.filter(t => items.some(i => i.type === t)).map(t => {
          const count = items.filter(i => i.type === t).length;
          const cfg = TYPE_CONFIG[t];
          return (
            <button
              key={t}
              onClick={() => setFilter(t)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border',
                filter === t
                  ? 'bg-legal-gold text-legal-navy border-legal-gold'
                  : 'bg-white/5 border-white/10 text-slate-400 hover:text-white'
              )}
            >
              {cfg.icon}
              {cfg.label} ({count})
            </button>
          );
        })}
      </div>

      {/* List */}
      {filtered.length === 0 ? (
        <div className="py-20 flex flex-col items-center text-center space-y-3 opacity-30">
          {items.length === 0 ? (
            <>
              <History size={56} className="text-slate-500" />
              <p className="text-sm font-bold text-slate-500">Chưa có kết quả nào được lưu</p>
              <p className="text-xs text-slate-600">Nhấn nút "Lưu kết quả" trên các trang phân tích để lưu vào đây</p>
            </>
          ) : (
            <>
              <CheckCircle2 size={40} className="text-slate-500" />
              <p className="text-sm font-bold text-slate-500">
                {searchText ? 'Không tìm thấy kết quả phù hợp' : 'Không có kết quả loại này'}
              </p>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(item => (
            <HistoryCard key={item.id} item={item} onDelete={handleDelete} onReopen={handleReopen} />
          ))}
        </div>
      )}

      {/* Tips */}
      {items.length > 0 && (
        <div className="flex items-start gap-2 p-3 rounded-xl bg-white/3 border border-white/8 text-xs text-slate-500">
          <AlertTriangle size={12} className="text-slate-600 mt-0.5 shrink-0" />
          Lịch sử được lưu trong trình duyệt này. Xóa cache trình duyệt sẽ mất dữ liệu.
        </div>
      )}
    </div>
  );
}
