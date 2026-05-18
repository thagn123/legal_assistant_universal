import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { AdminStats } from '../../lib/api';
import { adminGetStats, adminSeedData } from '../../lib/api';
import { Database, FileText, Layers, Activity, RefreshCw, Loader2, CheckCircle2 } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  complete: '#10b981',
  failed: '#ef4444',
  running: '#f59e0b',
  queued: '#64748b',
};

function StatCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: number | string; sub?: string }) {
  return (
    <div className="bg-[#0f1729] border border-white/10 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className="text-amber-400">{icon}</div>
        <span className="text-xs text-slate-400 uppercase tracking-wide font-medium">{label}</span>
      </div>
      <p className="text-3xl font-bold text-white">{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

export function AdminStats() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<string>('');

  const fetchStats = () => {
    setLoading(true);
    adminGetStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchStats(); }, []);

  const handleSeed = async () => {
    setSeeding(true);
    setSeedResult('');
    try {
      const result = await adminSeedData();
      setSeedResult(`Đã seed: ${result.templates} templates, ${result.risks} risks, ${result.checklists} checklists.`);
      fetchStats(); // refresh stats after seeding
    } catch (e: any) {
      setSeedResult(`Lỗi: ${e.message}`);
    } finally {
      setSeeding(false);
    }
  };

  if (loading) return <div className="text-slate-500 py-12 text-center">Đang tải thống kê…</div>;
  if (error) return <div className="text-red-400 py-12 text-center">{error}</div>;
  if (!stats) return null;

  const jobChartData = Object.entries(stats.jobs_by_status).map(([status, count]) => ({ status, count }));
  const mongoData = Object.entries(stats.mongodb).map(([name, count]) => ({ name, count }));

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Thống kê hệ thống</h1>
        <div className="flex items-center gap-3">
          {seedResult && (
            <span className="flex items-center gap-1.5 text-xs text-emerald-400">
              <CheckCircle2 size={13} /> {seedResult}
            </span>
          )}
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="flex items-center gap-2 px-4 py-2 bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20 text-amber-400 text-xs font-semibold rounded-lg disabled:opacity-50 transition-colors"
          >
            {seeding ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Seed dữ liệu mẫu
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={<FileText size={18} />} label="Tổng tài liệu" value={stats.documents_total} sub={`${stats.documents_global} global`} />
        <StatCard icon={<Layers size={18} />} label="Chunks nhúng" value={stats.mongodb.chunks_total ?? 0} sub={`${stats.mongodb.chunks_global ?? 0} global`} />
        <StatCard icon={<Activity size={18} />} label="Tổng jobs" value={stats.jobs_total} sub={`${stats.jobs_by_status['complete'] ?? 0} hoàn thành`} />
        <StatCard icon={<Database size={18} />} label="MongoDB" value={Object.values(stats.mongodb).reduce((a, b) => a + b, 0)} sub="tổng documents" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Jobs by status */}
        {jobChartData.length > 0 && (
          <div className="bg-[#0f1729] border border-white/10 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-slate-200 mb-4">Jobs theo trạng thái</h2>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={jobChartData} barSize={32}>
                <XAxis dataKey="status" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#0f1729', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                  labelStyle={{ color: '#e2e8f0' }}
                  itemStyle={{ color: '#94a3b8' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {jobChartData.map((entry) => (
                    <Cell key={entry.status} fill={STATUS_COLORS[entry.status] || '#64748b'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* MongoDB collections */}
        {mongoData.length > 0 && (
          <div className="bg-[#0f1729] border border-white/10 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-slate-200 mb-4">MongoDB collections</h2>
            <div className="space-y-2">
              {mongoData.map(({ name, count }) => (
                <div key={name} className="flex items-center justify-between py-1.5">
                  <span className="text-sm text-slate-400 font-mono">{name}</span>
                  <span className="text-sm font-semibold text-white tabular-nums">{count.toLocaleString('vi-VN')}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
