/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
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
  timeline:     { label: 'Tiến trình pháp lý', icon: <Clock size={14} />,      color: 'text-blue-400 bg-blue-500/10 border-blue-500/25',   path: '/timeline' },
  evidence_gap: { label: 'Kiểm tra chứng cứ',  icon: <FileSearch size={14} />, color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/25', path: '/evidence-gap' },
  clause_coach: { label: 'Tư vấn điều khoản',  icon: <Gavel size={14} />,      color: 'text-purple-400 bg-purple-500/10 border-purple-500/25', path: '/clause-coach' },
  clause_search:{ label: 'Tìm điều khoản',     icon: <Search size={14} />,     color: 'text-green-400 bg-green-500/10 border-green-500/25',  path: '/clause-search' },
};

const ALL_TYPES: AnalysisType[] = ['timeline', 'evidence_gap', 'clause_coach', 'clause_search'];

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
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
  const cfg = TYPE_CONFIG[item.type];

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
        <div className="border-t border-white/5 px-4 py-3 bg-white/2">
          <pre className="text-[11px] text-slate-300 whitespace-pre-wrap break-words max-h-72 overflow-y-auto leading-relaxed">
            {JSON.stringify(item.data, null, 2)}
          </pre>
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
    navigate(TYPE_CONFIG[item.type].path);
  }

  const filtered = filter === 'all' ? items : items.filter(i => i.type === filter);

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
        {ALL_TYPES.map(t => {
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
              <p className="text-sm font-bold text-slate-500">Không có kết quả loại này</p>
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
