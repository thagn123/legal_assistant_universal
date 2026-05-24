/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  UserCircle,
  TrendingUp,
  Clock,
  Activity,
  Map as MapIcon,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Calendar,
  Briefcase,
  CheckCircle2,
  Loader2,
  Tag,
} from 'lucide-react';
import { 
  Radar, 
  RadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip as ChartTooltip
} from 'recharts';
import { apiFetch, getRecommendationsByRole, PersonaRecommendResult, UserProfile, LAW_TYPE_LABELS } from '../lib/api';

const ROLE_OPTIONS = [
  { value: 'individual',   label: 'Cá nhân',              emoji: '👤' },
  { value: 'hr',           label: 'Nhân sự (HR)',          emoji: '🏢' },
  { value: 'startup',      label: 'Startup',               emoji: '🚀' },
  { value: 'sme',          label: 'Doanh nghiệp SME',      emoji: '🏪' },
  { value: 'legal_staff',  label: 'Nhân viên pháp chế',   emoji: '⚖️' },
];

const ROLE_STORAGE_KEY = 'lexai_user_role';

export function Profile() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [peers, setPeers] = useState<any[]>([]);
  const [selectedRole, setSelectedRole] = useState<string>(() => localStorage.getItem(ROLE_STORAGE_KEY) || '');
  const [roleRecs, setRoleRecs] = useState<PersonaRecommendResult | null>(null);
  const [roleLoading, setRoleLoading] = useState(false);

  useEffect(() => {
    apiFetch<UserProfile>('/recommendations/behavior/profile').then(setProfile).catch(() => {});
    apiFetch<any[]>('/recommendations/behavior/peers?limit=5').then(res => setPeers(Array.isArray(res) ? res : [])).catch(() => {});
  }, []);

  async function handleRoleSelect(role: string) {
    setSelectedRole(role);
    localStorage.setItem(ROLE_STORAGE_KEY, role);
    setRoleLoading(true);
    try {
      const result = await getRecommendationsByRole(role);
      setRoleRecs(result);
    } catch {
      setRoleRecs(null);
    } finally {
      setRoleLoading(false);
    }
  }

  if (!profile) return <div className="p-8 animate-skeleton h-screen" />;

  const radarData = Object.entries(profile.law_type_weights || {}).map(([k, v]) => ({
    subject: LAW_TYPE_LABELS[k] || k,
    A: (v || 0) * 100,
    fullMark: 100,
  }));

  const pieData = Object.entries(profile.action_frequencies || {}).map(([k, v]) => ({
    name: k === 'view' ? 'Xem' : k === 'save' ? 'Lưu' : k === 'download' ? 'Tải' : 'Hỏi',
    value: v || 0
  }));

  const COLORS = ['#d4a843', '#059669', '#3b82f6', '#f59e0b'];

  return (
    <div className="p-8 space-y-10 animate-in fade-in duration-500 max-w-7xl mx-auto">
      {/* HEADER */}
      <div className="glass-card p-8 flex flex-col md:flex-row items-center gap-10">
        <div className="relative">
          <div className="w-32 h-32 rounded-full border-4 border-legal-gold/20 flex items-center justify-center bg-white/5 overflow-hidden">
             <UserCircle size={80} className="text-legal-gold/50" />
          </div>
          <div className="absolute bottom-1 right-1 w-8 h-8 bg-legal-success rounded-full border-4 border-legal-navy flex items-center justify-center">
             <ShieldCheck size={16} className="text-white" />
          </div>
        </div>
        
        <div className="flex-1 space-y-4 text-center md:text-left">
           <div>
              <h2 className="text-3xl font-bold text-white tracking-tight">{profile.user_id}</h2>
              <p className="text-slate-400 mt-1">Gia nhập từ tháng 04/2024 • {profile.days_active} ngày hoạt động</p>
           </div>
           <div className="flex flex-wrap justify-center md:justify-start gap-4">
              <Badge icon={<Activity size={14} />} label={`${profile.total_interactions} Tương tác`} color="bg-legal-gold/20 text-legal-gold" />
              <Badge icon={<Clock size={14} />} label={`T.gian hoạt động chính: 21:00h`} color="bg-blue-500/20 text-blue-400" />
              <Badge icon={<MapIcon size={14} />} label={`Vị thế: Chuyên môn ${LAW_TYPE_LABELS[profile.top_law_type]}`} color="bg-emerald-500/20 text-emerald-400" />
           </div>
        </div>

        <button className="px-8 py-3 bg-white/5 border border-white/10 rounded-xl font-bold text-sm hover:bg-white/10 transition-all">
           Chỉnh sửa hồ sơ
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        {/* RADAR CHART - Interest */}
        <div className="glass-card p-8 flex flex-col h-[500px]">
           <h3 className="text-lg font-bold text-white mb-8 flex items-center gap-2">
             <TrendingUp className="text-legal-gold" size={20} />
             Trọng số quan tâm Lĩnh vực
           </h3>
           <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                  <PolarGrid stroke="rgba(255,255,255,0.05)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <Radar
                    name="Mức độ quan tâm"
                    dataKey="A"
                    stroke="#d4a843"
                    fill="#d4a843"
                    fillOpacity={0.3}
                  />
                  <ChartTooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                    itemStyle={{ color: '#d4a843' }}
                  />
                </RadarChart>
              </ResponsiveContainer>
           </div>
        </div>

        {/* PIE CHART - Actions */}
        <div className="glass-card p-8 flex flex-col h-[500px]">
           <h3 className="text-lg font-bold text-white mb-8 flex items-center gap-2">
             <Activity className="text-legal-gold" size={20} />
             Phân bổ loại hành vi
           </h3>
           <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <ChartTooltip 
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
           </div>
           <div className="grid grid-cols-2 gap-4 mt-4">
              {pieData.map((d, i) => (
                <div key={d.name} className="flex items-center gap-2">
                   <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[i] }} />
                   <span className="text-xs text-slate-400">{d.name}: <span className="text-white font-bold">{d.value}</span></span>
                </div>
              ))}
           </div>
        </div>
      </div>

      {/* HEATMAP - Active Hours */}
      <div className="glass-card p-8 space-y-6">
         <h3 className="text-lg font-bold text-white flex items-center gap-2">
           <Calendar className="text-legal-gold" size={20} />
           Biểu đồ nhiệt hoạt động (24h)
         </h3>
         <div className="grid grid-cols-12 md:grid-cols-24 gap-1 h-32">
            {(profile.active_hours || Array(24).fill(0)).map((val, i) => (
              <div 
                key={i} 
                className="rounded cursor-help relative group"
                style={{ 
                  backgroundColor: `rgba(212, 168, 67, ${val / 100})`, 
                  border: val === 0 ? '1px solid rgba(255,255,255,0.05)' : 'none' 
                }}
              >
                 <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 p-2 bg-slate-900 border border-white/10 rounded text-[9px] font-bold text-white opacity-0 group-hover:opacity-100 transition-opacity z-50 pointer-events-none whitespace-nowrap">
                   {i}:00h - Level: {val}%
                 </div>
              </div>
            ))}
         </div>
         <div className="flex justify-between text-[10px] text-slate-500 font-mono">
            <span>00:00</span>
            <span>12:00</span>
            <span>23:59</span>
         </div>
      </div>

      {/* ADJACENT DOMAINS */}
      <div className="space-y-6">
         <h3 className="text-lg font-bold text-white flex items-center gap-2">
           <Sparkles className="text-legal-gold" size={20} />
           Gợi ý mở rộng kiến thức
         </h3>
         <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {['hinh_su', 'hanh_chinh', 'gia_dinh'].map(d => (
              <div key={d} className="glass-card p-6 flex flex-col hover:border-blue-500/30 transition-all">
                 <div className="flex items-center justify-between mb-4">
                    <span className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-slate-400">
                      <MapIcon size={20} />
                    </span>
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest italic">Chưa khám phá</span>
                 </div>
                 <h4 className="font-bold text-white text-lg">{LAW_TYPE_LABELS[d]}</h4>
                 <p className="text-xs text-slate-400 mt-2 mb-6">Mở rộng hồ sơ năng lực pháp lý của bạn ở mảng {LAW_TYPE_LABELS[d].toLowerCase()}.</p>
                 <button className="mt-auto flex items-center gap-2 text-xs font-bold text-legal-gold hover:underline">
                    Khám phá ngay <ArrowRight size={14} />
                 </button>
              </div>
            ))}
         </div>
      </div>

      {/* ROLE SELECTION */}
      <div className="glass-card p-8 space-y-6">
        <div className="flex items-center gap-2">
          <Briefcase className="text-legal-gold" size={20} />
          <h3 className="text-lg font-bold text-white">Vai trò của bạn</h3>
        </div>
        <p className="text-sm text-slate-400">Chọn vai trò để nhận gợi ý pháp lý phù hợp nhất với công việc của bạn.</p>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {ROLE_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => handleRoleSelect(opt.value)}
              className={`flex flex-col items-center gap-2 p-4 rounded-2xl border transition-all ${
                selectedRole === opt.value
                  ? 'bg-legal-gold/10 border-legal-gold text-white'
                  : 'bg-white/5 border-white/10 text-slate-400 hover:border-white/30 hover:text-white'
              }`}
            >
              <span className="text-2xl">{opt.emoji}</span>
              <span className="text-xs font-semibold text-center leading-tight">{opt.label}</span>
              {selectedRole === opt.value && <CheckCircle2 size={14} className="text-legal-gold" />}
            </button>
          ))}
        </div>

        {roleLoading && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2 size={16} className="animate-spin" />
            Đang tải gợi ý...
          </div>
        )}

        {roleRecs && !roleLoading && (
          <div className="space-y-4 pt-2 border-t border-white/10">
            <p className="text-sm text-slate-300 italic">{roleRecs.pack_explanation}</p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                  <Tag size={11} /> Chủ đề quan tâm
                </p>
                <div className="flex flex-wrap gap-1">
                  {roleRecs.recommended_topics.map(t => (
                    <span key={t} className="px-2 py-0.5 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-full text-[10px] font-semibold">
                      {LAW_TYPE_LABELS[t] || t}
                    </span>
                  ))}
                </div>
              </div>
              <div className="space-y-2">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                  <Tag size={11} /> Mẫu hợp đồng gợi ý
                </p>
                <ul className="space-y-1">
                  {roleRecs.recommended_templates.slice(0, 4).map((t, i) => (
                    <li key={i} className="text-xs text-slate-300 flex gap-1">
                      <span className="text-legal-gold/60 shrink-0">•</span> {t}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="space-y-2">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                  <Tag size={11} /> Checklist phù hợp
                </p>
                <ul className="space-y-1">
                  {roleRecs.recommended_checklists.slice(0, 4).map((c, i) => (
                    <li key={i} className="text-xs text-slate-300 flex gap-1">
                      <span className="text-legal-gold/60 shrink-0">•</span> {c}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 pt-2">
              {roleRecs.quick_links.map(lnk => (
                <a
                  key={lnk.url}
                  href={lnk.url}
                  className="flex items-center gap-1 px-3 py-1.5 bg-legal-gold/10 border border-legal-gold/20 text-legal-gold rounded-xl text-xs font-semibold hover:bg-legal-gold/20 transition-all"
                >
                  {lnk.label} <ArrowRight size={11} />
                </a>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* PEER RECOMMENDATIONS */}
      <div className="space-y-6">
         <h3 className="text-sm font-bold text-slate-500 uppercase tracking-[0.2em]">Người có cùng hành vi quan tâm</h3>
         <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
            {peers.map((p, i) => (
               <div key={i} className="glass-card p-4 min-w-[240px] flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-legal-navy border border-white/10 flex items-center justify-center text-slate-500">
                     <UserCircle size={24} />
                  </div>
                  <div className="min-w-0">
                     <p className="text-xs font-bold text-white truncate">User #{Math.floor(Math.random()*1000)}</p>
                     <p className="text-[10px] text-slate-500">89% Tương đồng</p>
                  </div>
               </div>
            ))}
         </div>
      </div>
    </div>
  );
}

function Badge({ icon, label, color }: { icon: React.ReactNode; label: string; color: string }) {
  return (
    <div className={`px-3 py-1.5 rounded-full flex items-center gap-2 text-xs font-semibold ${color}`}>
      {icon}
      {label}
    </div>
  );
}
