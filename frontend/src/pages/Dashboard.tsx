/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import {
  Scale,
  Search,
  TrendingUp,
  ArrowRight,
  Clock,
  Sparkles,
  BookOpen,
  ScrollText,
  ClipboardList,
  MapPin,
  Newspaper,
  RefreshCw,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';
import { apiFetch, DigestResponse, FeedItem, FeedResult, getPersonalizedFeed, LAW_TYPE_LABELS, UserProfile } from '../lib/api';
import { LawTypeBadge } from '../components/ui/Shared';

const FEED_TYPE_ICON: Record<FeedItem['type'], React.ReactNode> = {
  law:       <BookOpen size={14} className="text-blue-400" />,
  template:  <ScrollText size={14} className="text-green-400" />,
  checklist: <ClipboardList size={14} className="text-purple-400" />,
  case:      <Scale size={14} className="text-orange-400" />,
  topic:     <Newspaper size={14} className="text-legal-gold" />,
};

const FEED_TYPE_LABEL: Record<FeedItem['type'], string> = {
  law:       'Văn bản luật',
  template:  'Mẫu hợp đồng',
  checklist: 'Checklist',
  case:      'Vụ án',
  topic:     'Chủ đề',
};

export function Dashboard() {
  const navigate = useNavigate();
  const [digest, setDigest] = useState<DigestResponse | null>(null);
  const [proactive, setProactive] = useState<any[]>([]);
  const [feed, setFeed] = useState<FeedItem[] | null>(null);
  const [feedLoading, setFeedLoading] = useState(true);
  const [behaviorProfile, setBehaviorProfile] = useState<UserProfile | null>(null);

  const loadAll = () => {
    apiFetch<DigestResponse>('/recommendations/behavior/digest').then(setDigest).catch(() => {});
    apiFetch<any[]>('/recommendations/behavior/proactive?limit=4').then(setProactive).catch(() => {});
    apiFetch<UserProfile>('/recommendations/behavior/profile').then(setBehaviorProfile).catch(() => {});
    getPersonalizedFeed()
      .then((r: FeedResult) => setFeed(r.feed_items))
      .catch(() => setFeed([]))
      .finally(() => setFeedLoading(false));
  };

  useEffect(() => { loadAll(); }, []);

  const chartData = behaviorProfile
    ? Object.entries(behaviorProfile.law_type_weights || {})
        .map(([k, v]) => ({ name: LAW_TYPE_LABELS[k] || k, value: Math.round((v || 0) * 100) }))
        .filter(d => d.value > 0)
        .sort((a, b) => b.value - a.value)
        .slice(0, 6)
    : [];

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-500">
      {/* HEADER SECTION */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Scale className="text-legal-gold" size={28} />
            LexAI — Trợ Lý Pháp Lý Thông Minh
          </h2>
          <p className="text-slate-400 mt-1">Hôm nay LexAI có {digest?.recommendations.length || 0} khuyến nghị mới dựa trên hành vi của bạn.</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={loadAll}
            className="flex items-center gap-2 px-4 py-2.5 bg-white/5 border border-white/10 text-slate-400 rounded-xl font-semibold text-sm hover:bg-white/10 transition-all"
            title="Làm mới dữ liệu"
          >
            <RefreshCw size={16} />
          </button>
          <button
            onClick={() => navigate('/analyze')}
            className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy rounded-xl font-bold shadow-lg shadow-legal-gold/20 hover:scale-105 active:scale-95 transition-all"
          >
            <Search size={18} />
            Phân tích mới
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* DAILY DIGEST WIDGET */}
        <div className="lg:col-span-2 glass-card p-8 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold flex items-center gap-2 text-white">
              <TrendingUp className="text-legal-gold" size={20} />
              Tổng quan hoạt động
            </h3>
            {digest && (
              <span className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">Cập nhật: {digest.last_active_date}</span>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Tương tác" value={digest?.total_interactions || 0} icon={<Clock size={16} />} />
            <StatCard label="Ngày hoạt động" value={digest?.days_active || 0} icon={<TrendingUp size={16} />} />
            <StatCard label="Lĩnh vực chính" value={LAW_TYPE_LABELS[digest?.top_domain || ''] || '—'} icon={<Scale size={16} />} />
            <StatCard label="Lĩnh vực đã dùng" value={Object.keys(behaviorProfile?.law_type_weights || {}).length || '—'} icon={<Sparkles size={16} />} />
          </div>

          <div className="space-y-4">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Khuyến nghị xếp hạng</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {digest?.recommendations.map((rec) => (
                <div key={rec.id} className="bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/10 transition-all cursor-pointer group">
                  <div className="flex items-start justify-between mb-2">
                    <span className="px-2 py-0.5 bg-legal-gold/20 text-legal-gold rounded text-[10px] font-bold">{(rec.score * 100).toFixed(0)}%</span>
                    <ArrowRight size={14} className="text-slate-600 group-hover:text-legal-gold" />
                  </div>
                  <h4 className="text-sm font-bold text-white line-clamp-1">{rec.title}</h4>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 italic">"{rec.reason}"</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* BEHAVIOR STATS BAR */}
        <div className="glass-card p-8 flex flex-col">
          <h3 className="text-lg font-bold text-white mb-6">Trọng số quan tâm</h3>
          <div className="flex-1 min-h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                <XAxis type="number" hide />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#94a3b8', fontSize: 10 }}
                  width={80}
                />
                <Tooltip 
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#d4a843' : 'rgba(212, 168, 67, 0.4)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-[11px] text-slate-500 mt-4 text-center">Dựa trên lịch sử tìm kiếm và phân tích của bạn</p>
        </div>
      </div>

      {/* PROACTIVE RECOMMENDATIONS STRIP */}
      <div className="space-y-6">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <Sparkles className="text-legal-gold" size={20} />
          Gợi ý chủ động
        </h3>
        <div className="flex overflow-x-auto gap-6 pb-4 scrollbar-hide">
          {proactive.map((item) => (
            <div key={item.id} className="glass-card p-6 min-w-[320px] max-w-[320px] flex flex-col shrink-0 hover:border-legal-gold/50 transition-all">
              <div className="flex items-center justify-between mb-4">
                <LawTypeBadge type={item.law_type} />
                <button className="text-[10px] text-legal-gold font-bold uppercase tracking-widest hover:underline">{item.action_hint} ↗</button>
              </div>
              <h4 className="font-bold text-white mb-2 leading-tight">{item.title}</h4>
              <p className="text-xs text-slate-400 line-clamp-2">{item.reason}</p>
              <div className="mt-auto pt-6">
                <button className="w-full py-2 bg-white/5 border border-white/10 rounded-lg text-[11px] font-bold hover:bg-white/10 transition-all">
                  Chi tiết
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* PERSONALIZED FEED — "Dành cho bạn" */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <MapPin className="text-legal-gold" size={20} />
            Dành cho bạn
          </h3>
          <button
            onClick={() => navigate('/journey')}
            className="flex items-center gap-1 text-xs text-legal-gold hover:underline"
          >
            Xem hành trình pháp lý <ArrowRight size={12} />
          </button>
        </div>

        {feedLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-24 bg-white/5 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : feed && feed.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {feed.map((item, i) => (
              <button
                key={i}
                onClick={() => navigate(item.action_url)}
                className="glass-card p-4 text-left hover:border-legal-gold/40 transition-all group"
              >
                <div className="flex items-center gap-2 mb-2">
                  {FEED_TYPE_ICON[item.type]}
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    {FEED_TYPE_LABEL[item.type]}
                  </span>
                  <span className="ml-auto text-[10px] text-slate-600 font-mono">
                    {Math.round(item.score * 100)}%
                  </span>
                </div>
                <p className="text-sm font-semibold text-white line-clamp-2 group-hover:text-legal-gold transition-colors">
                  {item.title}
                </p>
                <p className="text-[11px] text-slate-500 mt-1 line-clamp-1 italic">{item.reason}</p>
              </button>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500 text-sm">
            Bắt đầu tra cứu để nhận gợi ý phù hợp với bạn
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: string | number; icon: React.ReactNode }) {
  return (
    <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
      <div className="flex items-center gap-2 text-slate-500 mb-2">
        {icon}
        <span className="text-[10px] font-bold uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-lg font-bold text-white">{value}</p>
    </div>
  );
}
