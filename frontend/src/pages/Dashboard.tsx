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
  Zap,
  AlertTriangle,
  CheckCircle,
  Info,
  ChevronRight,
  Loader2,
  Database,
  Target,
  CalendarDays,
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
import { apiFetch, BehaviorProfile, DigestResponse, FeedItem, FeedResult, getBehaviorProfile, getPersonalizedFeed, LAW_TYPE_LABELS, classifySituation, ClassifyResult, NextBestAction, getNextBestActions } from '../lib/api';
import { LawTypeBadge } from '../components/ui/Shared';
import { setStoredSituation } from '../lib/analysisContext';

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

const RISK_CONFIG = {
  high:   { label: 'Rủi ro cao',   color: 'text-red-400 bg-red-400/10 border-red-400/30',    icon: <AlertTriangle size={12} /> },
  medium: { label: 'Rủi ro trung bình', color: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30', icon: <Info size={12} /> },
  low:    { label: 'Rủi ro thấp',  color: 'text-green-400 bg-green-400/10 border-green-400/30', icon: <CheckCircle size={12} /> },
} as const;

const DOMAIN_LABELS: Record<string, string> = {
  dat_dai: 'Đất đai', hop_dong: 'Hợp đồng', lao_dong: 'Lao động',
  doanh_nghiep: 'Doanh nghiệp', dan_su: 'Dân sự', hinh_su: 'Hình sự',
  hanh_chinh: 'Hành chính', gia_dinh: 'Gia đình', general: 'Chưa xác định',
};

type LocalDashboardStats = {
  sessions: number;
  conversationTurns: number;
  savedAnalyses: number;
  daysActive: number;
  lastActive?: string;
  domainCounts: Record<string, number>;
};

const SESSION_STORAGE_KEY = 'lexai_sessions';
const HISTORY_STORAGE_KEY = 'lexai_analysis_history';

function parseJsonArray<T>(key: string): T[] {
  try {
    const value = localStorage.getItem(key);
    const parsed = value ? JSON.parse(value) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function deriveLocalStats(): LocalDashboardStats {
  const sessions = parseJsonArray<any>(SESSION_STORAGE_KEY);
  const analyses = parseJsonArray<any>(HISTORY_STORAGE_KEY);
  const domainCounts: Record<string, number> = {};
  const activeDays = new Set<string>();
  let conversationTurns = 0;
  let lastActive = '';

  const touchDate = (value?: string) => {
    if (!value) return;
    const parsed = Date.parse(value);
    if (!Number.isFinite(parsed)) return;
    const iso = new Date(parsed).toISOString();
    activeDays.add(iso.slice(0, 10));
    if (!lastActive || parsed > Date.parse(lastActive)) lastActive = iso;
  };

  const touchDomain = (domain?: string) => {
    if (domain && domain !== 'general') {
      domainCounts[domain] = (domainCounts[domain] || 0) + 1;
    }
  };

  for (const session of sessions) {
    const turns = Array.isArray(session.turns) ? session.turns : [];
    conversationTurns += turns.length;
    touchDomain(session.domain || session.metadata?.domain);
    touchDate(session.lastActive || session.createdAt || session.date);
  }

  for (const item of analyses) {
    touchDomain(item.domain || item.data?.domain || item.data?.query_domain || item.data?.detected_domain);
    touchDate(item.savedAt);
  }

  return {
    sessions: sessions.length,
    conversationTurns,
    savedAnalyses: analyses.length,
    daysActive: activeDays.size,
    lastActive,
    domainCounts,
  };
}

function toPercent(value: number): string {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

export function Dashboard() {
  const navigate = useNavigate();
  const [digest, setDigest] = useState<DigestResponse | null>(null);
  const [profile, setProfile] = useState<BehaviorProfile | null>(null);
  const [proactive, setProactive] = useState<any[]>([]);
  const [feed, setFeed] = useState<FeedItem[] | null>(null);
  const [feedLoading, setFeedLoading] = useState(true);
  const [localStats, setLocalStats] = useState<LocalDashboardStats>(() => deriveLocalStats());

  // Quick classify widget state
  const [quickInput, setQuickInput] = useState('');
  const [classifying, setClassifying] = useState(false);
  const [classifyResult, setClassifyResult] = useState<ClassifyResult | null>(null);
  const [classifyError, setClassifyError] = useState('');
  const [nextActions, setNextActions] = useState<NextBestAction[]>([]);
  const [actionsLoading, setActionsLoading] = useState(false);

  async function handleQuickClassify() {
    if (!quickInput.trim()) return;
    setStoredSituation(quickInput);
    setClassifying(true);
    setClassifyResult(null);
    setNextActions([]);
    setClassifyError('');
    try {
      const result = await classifySituation(quickInput.trim());
      setClassifyResult(result);
      // Fire-and-forget next-best-actions after classify
      setActionsLoading(true);
      getNextBestActions({
        situation: quickInput.trim(),
        domain: result.domain,
        domain_confidence: result.domain_confidence,
        warnings: result.law_references?.map(r => r.title) ?? [],
        limit: 4,
      }).then(actions => setNextActions(actions)).catch(() => {}).finally(() => setActionsLoading(false));
    } catch {
      setClassifyError('Không thể phân loại. Vui lòng thử lại.');
    } finally {
      setClassifying(false);
    }
  }

  useEffect(() => {
    setLocalStats(deriveLocalStats());
    apiFetch<DigestResponse>('/recommendations/behavior/digest').then(setDigest).catch(() => {});
    getBehaviorProfile().then(setProfile).catch(() => {});
    apiFetch<any[]>('/recommendations/behavior/proactive?limit=4').then(setProactive).catch(() => {});
    getPersonalizedFeed()
      .then((r: FeedResult) => setFeed(r.feed_items))
      .catch(() => setFeed([]))
      .finally(() => setFeedLoading(false));
  }, []);

  const mergedWeights: Record<string, number> = {
    ...(digest?.law_type_weights || {}),
    ...(profile?.law_type_weights || {}),
  };
  if (Object.keys(mergedWeights).length === 0) {
    const maxCount = Math.max(...Object.values(localStats.domainCounts), 1);
    for (const [domain, count] of Object.entries(localStats.domainCounts)) {
      mergedWeights[domain] = count / maxCount;
    }
  }

  const chartData = Object.entries(mergedWeights)
    .map(([domain, w]) => ({ name: LAW_TYPE_LABELS[domain] ?? DOMAIN_LABELS[domain] ?? domain, value: Math.round(w * 100) }))
    .filter(d => d.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 7);

  const totalInteractions = Math.max(
    digest?.total_interactions || 0,
    profile?.total_interactions || 0,
    localStats.conversationTurns + localStats.savedAnalyses,
  );
  const daysActive = Math.max(digest?.days_active || 0, profile?.days_active || 0, localStats.daysActive);
  const topDomain = digest?.top_domain && digest.top_domain !== 'general'
    ? digest.top_domain
    : profile?.top_domain && profile.top_domain !== 'general'
      ? profile.top_domain
      : Object.entries(localStats.domainCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || 'general';
  const recommendationScores = [
    ...(digest?.recommendations || []).map(r => r.score),
    ...(feed || []).map(item => item.score),
    ...proactive.map(item => Number(item.score || 0)),
  ].filter(score => Number.isFinite(score) && score > 0);
  const averageRecommendationScore = recommendationScores.length
    ? recommendationScores.reduce((sum, score) => sum + score, 0) / recommendationScores.length
    : 0;
  const profileCoverage = (
    Math.min(totalInteractions, 20) / 20 * 0.45
    + Math.min(Object.keys(mergedWeights).length, 4) / 4 * 0.3
    + Math.min(daysActive, 7) / 7 * 0.25
  );
  const lastActiveLabel = digest?.last_active_date && digest.last_active_date !== 'N/A'
    ? digest.last_active_date
    : localStats.lastActive
      ? new Date(localStats.lastActive).toLocaleDateString('vi-VN')
      : 'Chưa có';
  const recCount = (digest?.recommendations.length || 0) + (feed?.length || 0);
  const dataSource = totalInteractions > 0
    ? profile?.total_interactions || digest?.total_interactions
      ? 'Backend behavior + lịch sử cục bộ'
      : 'Lịch sử cục bộ'
    : 'Chưa có dữ liệu';

  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-500">
      {/* HEADER SECTION */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Scale className="text-legal-gold" size={28} />
            LexAI — Trợ Lý Pháp Lý Thông Minh
          </h2>
          <p className="text-slate-400 mt-1">Hôm nay LexAI có {recCount} gợi ý từ dữ liệu hành vi và lịch sử phân tích thực tế.</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => navigate('/analyze')}
            className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy rounded-xl font-bold shadow-lg shadow-legal-gold/20 hover:scale-105 active:scale-95 transition-all"
          >
            <Search size={18} />
            Phân tích mới
          </button>
        </div>
      </div>

      {/* QUICK CLASSIFY WIDGET */}
      <div className="glass-card p-6 space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Zap className="text-legal-gold" size={16} />
          Phân loại nhanh tình huống pháp lý
        </h3>
        <div className="flex gap-3">
          <textarea
            value={quickInput}
            onChange={e => setQuickInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleQuickClassify(); }}
            placeholder="Mô tả ngắn tình huống của bạn... (Ctrl+Enter để phân loại)"
            rows={2}
            className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
          />
          <button
            onClick={handleQuickClassify}
            disabled={classifying || !quickInput.trim()}
            className="px-5 py-2 bg-legal-gold text-legal-navy rounded-xl font-bold text-sm disabled:opacity-40 hover:scale-105 active:scale-95 transition-all self-end"
          >
            {classifying ? '...' : 'Phân loại'}
          </button>
        </div>

        {classifyError && (
          <p className="text-xs text-red-400">{classifyError}</p>
        )}

        {classifyResult && (
          <div className="space-y-3 pt-1">
            <div className="flex flex-wrap gap-2 items-center">
              {/* Domain */}
              <span className="px-3 py-1 rounded-full bg-legal-gold/15 text-legal-gold border border-legal-gold/30 text-xs font-bold">
                {DOMAIN_LABELS[classifyResult.domain] ?? classifyResult.domain}
                <span className="ml-1 opacity-60">{Math.round(classifyResult.domain_confidence * 100)}%</span>
              </span>
              {/* Risk */}
              <span className={`flex items-center gap-1 px-3 py-1 rounded-full border text-xs font-bold ${RISK_CONFIG[classifyResult.risk_level].color}`}>
                {RISK_CONFIG[classifyResult.risk_level].icon}
                {RISK_CONFIG[classifyResult.risk_level].label}
              </span>
              {/* Stage */}
              <span className="px-3 py-1 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/20 text-xs font-medium">
                {classifyResult.stage_label}
              </span>
              {/* Intent */}
              <span className="px-3 py-1 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/20 text-xs font-medium">
                {classifyResult.intent_label}
              </span>
            </div>
            <p className="text-xs text-slate-400 italic">{classifyResult.summary}</p>
            <button
              onClick={() => navigate('/journey', { state: { situation: quickInput, domain: classifyResult.domain } })}
              className="flex items-center gap-1 text-xs text-legal-gold hover:underline"
            >
              Xem hành trình pháp lý đầy đủ <ArrowRight size={12} />
            </button>

            {/* Next Best Actions */}
            {(actionsLoading || nextActions.length > 0) && (
              <div className="pt-2 border-t border-white/10">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Zap size={10} className="text-legal-gold" />
                  Bước tiếp theo đề xuất
                  {actionsLoading && <Loader2 size={10} className="animate-spin ml-1" />}
                </p>
                {nextActions.length > 0 && (
                  <div className="grid grid-cols-2 gap-2">
                    {nextActions.map(action => (
                      <button
                        key={action.action_id}
                        onClick={() => navigate(action.action_url, { state: { situation: quickInput, domain: classifyResult.domain, summary: classifyResult.summary } })}
                        className="flex items-start gap-2 p-2.5 bg-white/5 border border-white/10 rounded-xl text-left hover:border-legal-gold/40 hover:bg-white/8 transition-all group"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-[11px] font-bold text-white group-hover:text-legal-gold transition-colors line-clamp-1">{action.title}</p>
                          <p className="text-[10px] text-slate-500 line-clamp-1 mt-0.5">{action.reason}</p>
                        </div>
                        <ChevronRight size={12} className="text-slate-600 group-hover:text-legal-gold shrink-0 mt-0.5 transition-colors" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
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
              <span className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">Cập nhật: {lastActiveLabel}</span>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Tương tác thật" value={totalInteractions} icon={<Clock size={16} />} />
            <StatCard label="Ngày hoạt động" value={daysActive} icon={<CalendarDays size={16} />} />
            <StatCard label="Lĩnh vực chính" value={LAW_TYPE_LABELS[topDomain] || DOMAIN_LABELS[topDomain] || 'Chưa có'} icon={<Scale size={16} />} />
            <StatCard label="Độ phủ hồ sơ" value={toPercent(profileCoverage)} icon={<Target size={16} />} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <MiniMetric label="Phiên hội thoại" value={localStats.sessions} />
            <MiniMetric label="Kết quả đã lưu" value={localStats.savedAnalyses} />
            <MiniMetric label="Điểm gợi ý TB" value={averageRecommendationScore ? toPercent(averageRecommendationScore) : 'Chưa đủ'} />
          </div>

          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-slate-400">
            <Database size={13} className="text-legal-gold" />
            <span>Nguồn số liệu: {dataSource}. Không còn dùng tỷ lệ demo cố định.</span>
          </div>

          <div className="space-y-4">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Khuyến nghị xếp hạng</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(digest?.recommendations || []).length > 0 ? digest?.recommendations.map((rec) => (
                <button
                  key={rec.id}
                  type="button"
                  onClick={() => navigate(rec.law_type ? '/law-search' : '/profile', { state: { domain: rec.law_type || topDomain } })}
                  className="bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/10 transition-all cursor-pointer group text-left"
                >
                  <div className="flex items-start justify-between mb-2">
                    <span className="px-2 py-0.5 bg-legal-gold/20 text-legal-gold rounded text-[10px] font-bold">{(rec.score * 100).toFixed(0)}%</span>
                    <ArrowRight size={14} className="text-slate-600 group-hover:text-legal-gold" />
                  </div>
                  <h4 className="text-sm font-bold text-white line-clamp-1">{rec.title}</h4>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 italic">"{rec.reason}"</p>
                </button>
              )) : (
                <div className="col-span-2 rounded-xl border border-dashed border-white/10 bg-white/5 p-5 text-sm text-slate-500">
                  Chưa đủ lịch sử để xếp hạng khuyến nghị. Hãy phân tích một tình huống hoặc lưu kết quả để Dashboard bắt đầu có số liệu.
                </div>
              )}
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
                <XAxis type="number" hide domain={[0, 100]} />
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
                <button
                  type="button"
                  onClick={() => navigate(item.action_url || '/analyze')}
                  className="text-[10px] text-legal-gold font-bold uppercase tracking-widest hover:underline"
                >
                  {item.action_hint} ↗
                </button>
              </div>
              <h4 className="font-bold text-white mb-2 leading-tight">{item.title}</h4>
              <p className="text-xs text-slate-400 line-clamp-2">{item.reason}</p>
              <div className="mt-auto pt-6">
                <button
                  type="button"
                  onClick={() => navigate(item.action_url || '/analyze')}
                  className="w-full py-2 bg-white/5 border border-white/10 rounded-lg text-[11px] font-bold hover:bg-white/10 transition-all"
                >
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

function MiniMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-bold text-white">{value}</p>
    </div>
  );
}
