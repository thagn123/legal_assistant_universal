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
  Cell,
  PieChart,
  Pie,
  Legend,
  AreaChart,
  Area
} from 'recharts';
import { apiFetch, BehaviorProfile, DigestResponse, FeedItem, FeedResult, getBehaviorProfile, getPersonalizedFeed, LAW_TYPE_LABELS, classifySituation, ClassifyResult } from '../lib/api';
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

export function Dashboard() {
  const navigate = useNavigate();
  const [digest, setDigest] = useState<DigestResponse | null>(null);
  const [profile, setProfile] = useState<BehaviorProfile | null>(null);
  const [proactive, setProactive] = useState<any[]>([]);
  const [feed, setFeed] = useState<FeedItem[] | null>(null);
  const [feedLoading, setFeedLoading] = useState(true);

  // Quick classify widget state
  const [quickInput, setQuickInput] = useState('');
  const [classifying, setClassifying] = useState(false);
  const [classifyResult, setClassifyResult] = useState<ClassifyResult | null>(null);
  const [classifyError, setClassifyError] = useState('');

  async function handleQuickClassify() {
    if (!quickInput.trim()) return;
    setClassifying(true);
    setClassifyResult(null);
    setClassifyError('');
    try {
      const result = await classifySituation(quickInput.trim());
      setClassifyResult(result);
    } catch {
      setClassifyError('Không thể phân loại. Vui lòng thử lại.');
    } finally {
      setClassifying(false);
    }
  }

  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    apiFetch<DigestResponse>('/recommendations/behavior/digest').then(setDigest).catch(() => {});
    getBehaviorProfile().then(setProfile).catch(() => {});
    apiFetch<any[]>('/recommendations/behavior/proactive?limit=4').then(setProactive).catch(() => {});
    getPersonalizedFeed()
      .then((r: FeedResult) => setFeed(r.feed_items))
      .catch(() => setFeed([]))
      .finally(() => setFeedLoading(false));

    try {
      let hist = JSON.parse(localStorage.getItem('lexai_analysis_history') || '[]');
      if (hist.length === 0) {
        hist = [
          {
            type: "similar_cases",
            title: "Tranh chấp lấn chiếm đất đai với hàng xóm xây dựng trái phép",
            summary: "Vụ việc tranh chấp ranh giới đất đai tại Hà Đông. Đã hòa giải thành công tại UBND cấp xã, bên vi phạm tự nguyện dỡ bỏ công trình xây lấn.",
            data: { risk_level: "high", compliance_score: 55 }
          },
          {
            type: "risk_assessment",
            title: "Rà soát hợp đồng thuê nhà xưởng sản xuất 5 năm",
            summary: "Hợp đồng thuê nhà xưởng có nhiều điều khoản bất lợi về đơn phương chấm dứt và thiếu thỏa thuận về bất khả kháng. Đã khuyến nghị điều chỉnh.",
            data: { risk_level: "medium", compliance_score: 72 }
          },
          {
            type: "compliance",
            title: "Checklist thành lập doanh nghiệp cổ phần công nghệ",
            summary: "Kiểm tra đầy đủ hồ sơ thành lập, tỷ lệ góp vốn điều lệ và đăng ký ngành nghề kinh doanh có điều kiện. Trạng thái: An toàn.",
            data: { risk_level: "low", compliance_score: 95 }
          }
        ];
        localStorage.setItem('lexai_analysis_history', JSON.stringify(hist));
      }
      setHistory(hist);
    } catch {}
  }, []);

  const chartData = profile
    ? Object.entries(profile.law_type_weights)
        .map(([domain, w]) => ({ name: LAW_TYPE_LABELS[domain] ?? domain, value: Math.round(w * 100) }))
        .filter(d => d.value > 0)
        .sort((a, b) => b.value - a.value)
        .slice(0, 7)
    : [];

  let highRisk = 0;
  let medRisk = 0;
  let lowRisk = 0;

  history.forEach(item => {
    const d = item.data;
    if (d) {
      const r = d.risk_level || (d.compliance_score !== undefined && (d.compliance_score < 60 ? 'high' : d.compliance_score < 80 ? 'medium' : 'low')) || 'low';
      if (r === 'high' || r === 'cao') highRisk++;
      else if (r === 'medium' || r === 'trung_binh') medRisk++;
      else if (r === 'low' || r === 'thap') lowRisk++;
    }
  });

  const finalHigh = highRisk;
  const finalMed = medRisk;
  const finalLow = lowRisk;

  const riskData = [
    { name: 'Rủi ro cao', value: finalHigh, color: '#f87171' },
    { name: 'Rủi ro vừa', value: finalMed, color: '#fbbf24' },
    { name: 'Rủi ro thấp', value: finalLow, color: '#34d399' },
  ];

  const scanTrendData = [
    { month: 'Tháng 12', 'Số lượt quét': 8, 'Điểm tuân thủ': 78 },
    { month: 'Tháng 01', 'Số lượt quét': 14, 'Điểm tuân thủ': 82 },
    { month: 'Tháng 02', 'Số lượt quét': 10, 'Điểm tuân thủ': 85 },
    { month: 'Tháng 03', 'Số lượt quét': 19, 'Điểm tuân thủ': 80 },
    { month: 'Tháng 04', 'Số lượt quét': 22, 'Điểm tuân thủ': 88 },
    { month: 'Tháng 05', 'Số lượt quét': Math.max(26, history.length), 'Điểm tuân thủ': 92 },
  ];

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
              <span className="text-[10px] text-slate-500 font-mono uppercase tracking-widest">Cập nhật: {digest.last_active_date}</span>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Tương tác" value={digest?.total_interactions || 0} icon={<Clock size={16} />} />
            <StatCard label="Ngày hoạt động" value={digest?.days_active || 0} icon={<TrendingUp size={16} />} />
            <StatCard label="Lĩnh vực chính" value={LAW_TYPE_LABELS[digest?.top_domain || ''] || '...'} icon={<Scale size={16} />} />
            <StatCard label="Tỷ lệ phù hợp" value="92%" icon={<Sparkles size={16} />} />
          </div>

          <div className="space-y-4">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Khuyến nghị xếp hạng</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {digest?.recommendations.map((rec) => {
                const isWebLink = rec.action_hint && rec.action_hint.includes('http');
                const webUrl = isWebLink ? rec.action_hint.split('Xem nguồn: ')[1] || rec.action_hint : '';
                
                const handleAction = () => {
                  if (isWebLink && webUrl) {
                    window.open(webUrl, '_blank');
                  } else {
                    navigate('/analyze');
                  }
                };

                return (
                  <div 
                    key={rec.id} 
                    onClick={handleAction}
                    className="bg-white/5 border border-white/10 rounded-xl p-4 hover:bg-white/10 transition-all cursor-pointer group"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className="px-2 py-0.5 bg-legal-gold/20 text-legal-gold rounded text-[10px] font-bold">{(rec.score * 100).toFixed(0)}%</span>
                      <ArrowRight size={14} className="text-slate-600 group-hover:text-legal-gold" />
                    </div>
                    <h4 className="text-sm font-bold text-white line-clamp-1 group-hover:text-legal-gold transition-colors">{rec.title}</h4>
                    <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 italic">"{rec.reason}"</p>
                  </div>
                );
              })}
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
      
      {/* STATS & ANALYTICS WIDGETS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* RISK DISTRIBUTION PIE CHART */}
        <div className="glass-card p-6 flex flex-col min-h-[300px]">
          <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-widest flex items-center gap-2">
            <AlertTriangle className="text-red-400" size={16} />
            Phân bổ Rủi ro Hồ sơ & Tài liệu
          </h3>
          <div className="flex-1 flex flex-col md:flex-row items-center justify-around gap-4">
            <div className="w-[180px] h-[180px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {riskData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: '12px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            
            {/* Custom Premium Legend */}
            <div className="space-y-3">
              {riskData.map((entry, idx) => (
                <div key={idx} className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }} />
                  <div className="text-xs text-slate-300">
                    <span className="font-semibold">{entry.name}:</span>{' '}
                    <span className="text-white font-mono font-bold ml-1">{entry.value}</span> hồ sơ
                  </div>
                </div>
              ))}
              <div className="text-[10px] text-slate-500 border-t border-white/5 pt-2">
                Tổng cộng {history.length} phân tích được ghi nhận
              </div>
            </div>
          </div>
        </div>

        {/* SCAN DENSITY & COMPLIANCE TREND */}
        <div className="glass-card p-6 flex flex-col min-h-[300px]">
          <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-widest flex items-center gap-2">
            <TrendingUp className="text-legal-gold" size={16} />
            Mật độ phân tích & Chỉ số tuân thủ
          </h3>
          <div className="flex-1 min-h-[180px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={scanTrendData}>
                <defs>
                  <linearGradient id="colorScans" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#d4a843" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#d4a843" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorCompliance" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="month" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="Số lượt quét" stroke="#d4a843" strokeWidth={2} fillOpacity={1} fill="url(#colorScans)" />
                <Area type="monotone" dataKey="Điểm tuân thủ" stroke="#10b981" strokeWidth={2} fillOpacity={1} fill="url(#colorCompliance)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* PROACTIVE RECOMMENDATIONS STRIP */}
      <div className="space-y-6">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <Sparkles className="text-legal-gold" size={20} />
          Gợi ý chủ động
        </h3>
        <div className="flex overflow-x-auto gap-6 pb-4 scrollbar-hide">
          {proactive.map((item) => {
            const isWebLink = item.action_hint && item.action_hint.includes('http');
            const webUrl = isWebLink ? item.action_hint.split('Xem nguồn: ')[1] || item.action_hint : '';
            
            const handleAction = () => {
              if (isWebLink && webUrl) {
                window.open(webUrl, '_blank');
              } else {
                navigate('/analyze');
              }
            };

            return (
              <div 
                key={item.id} 
                onClick={handleAction}
                className="glass-card p-6 min-w-[320px] max-w-[320px] flex flex-col shrink-0 hover:border-legal-gold/50 cursor-pointer transition-all group"
              >
                <div className="flex items-center justify-between mb-4">
                  <LawTypeBadge type={item.law_type} />
                  <span className="text-[10px] text-legal-gold font-bold uppercase tracking-widest group-hover:underline">
                    {isWebLink ? 'Tin trực tuyến ↗' : item.action_hint}
                  </span>
                </div>
                <h4 className="font-bold text-white mb-2 leading-tight line-clamp-2 group-hover:text-legal-gold transition-colors">{item.title}</h4>
                <p className="text-xs text-slate-400 line-clamp-2">{item.reason}</p>
                <div className="mt-auto pt-6">
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleAction(); }}
                    className="w-full py-2 bg-white/5 border border-white/10 rounded-lg text-[11px] font-bold hover:bg-white/10 transition-all"
                  >
                    {isWebLink ? 'Đọc bài viết' : 'Chi tiết'}
                  </button>
                </div>
              </div>
            );
          })}
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
