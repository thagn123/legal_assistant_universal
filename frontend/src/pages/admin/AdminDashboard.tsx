import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Briefcase, BarChart2, ArrowRight, Upload, Database, Activity, CheckCircle, Clock, AlertCircle, Loader2 } from 'lucide-react';
import type { AdminStats } from '../../lib/api';
import { adminGetStats } from '../../lib/api';

export function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    adminGetStats()
      .then(setStats)
      .catch(() => {})
      .finally(() => setStatsLoading(false));
  }, []);

  const chunksTotal = stats?.mongodb?.chunks_total ?? stats?.mongodb?.chunks_vec ?? 0;
  const completedJobs = stats?.jobs_by_status?.['complete'] ?? 0;
  const failedJobs = stats?.jobs_by_status?.['failed'] ?? 0;
  const activeJobs = (stats?.jobs_by_status?.['running'] ?? 0) + (stats?.jobs_by_status?.['queued'] ?? 0);

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-bold text-white">Chào mừng đến Admin Panel</h1>
        <p className="text-sm text-slate-400 mt-1">Quản lý dữ liệu và theo dõi hệ thống LexAI.</p>
      </div>

      {/* Live stats mini-cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {statsLoading ? (
          Array(4).fill(0).map((_, i) => (
            <div key={i} className="bg-[#0f1729] border border-white/10 rounded-xl p-4 animate-pulse h-20" />
          ))
        ) : (
          <>
            <MiniStat icon={<FileText size={16} className="text-amber-400" />} label="Tài liệu" value={stats?.documents_total ?? 0} sub={`${stats?.documents_global ?? 0} global`} />
            <MiniStat icon={<Database size={16} className="text-blue-400" />} label="Chunks" value={chunksTotal} sub="MongoDB" />
            <MiniStat icon={<CheckCircle size={16} className="text-emerald-400" />} label="Jobs xong" value={completedJobs} sub={failedJobs > 0 ? `${failedJobs} lỗi` : 'Không có lỗi'} subColor={failedJobs > 0 ? 'text-red-400' : undefined} />
            <MiniStat icon={<Activity size={16} className="text-purple-400" />} label="Đang chạy" value={activeJobs} sub={`${stats?.jobs_total ?? 0} tổng`} />
          </>
        )}
      </div>

      {/* Action cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          to="/admin/documents"
          className="bg-[#0f1729] border border-white/10 rounded-xl p-5 hover:border-amber-400/30 hover:bg-amber-400/5 transition-colors group"
        >
          <div className="flex items-center justify-between mb-3">
            <FileText size={22} className="text-amber-400" />
            <ArrowRight size={16} className="text-slate-600 group-hover:text-amber-400 transition-colors" />
          </div>
          <h2 className="font-semibold text-white mb-1">Upload tài liệu</h2>
          <p className="text-sm text-slate-400">Nạp văn bản luật, hợp đồng mẫu, ảnh vào hệ thống.</p>
        </Link>

        <Link
          to="/admin/jobs"
          className="bg-[#0f1729] border border-white/10 rounded-xl p-5 hover:border-amber-400/30 hover:bg-amber-400/5 transition-colors group"
        >
          <div className="flex items-center justify-between mb-3">
            <Briefcase size={22} className="text-amber-400" />
            {activeJobs > 0 && (
              <span className="flex items-center gap-1 text-[10px] text-amber-400 font-bold">
                <Loader2 size={11} className="animate-spin" /> {activeJobs} đang chạy
              </span>
            )}
            {activeJobs === 0 && <ArrowRight size={16} className="text-slate-600 group-hover:text-amber-400 transition-colors" />}
          </div>
          <h2 className="font-semibold text-white mb-1">Theo dõi Jobs</h2>
          <p className="text-sm text-slate-400">Xem trạng thái xử lý pipeline của các tài liệu.</p>
        </Link>

        <Link
          to="/admin/stats"
          className="bg-[#0f1729] border border-white/10 rounded-xl p-5 hover:border-amber-400/30 hover:bg-amber-400/5 transition-colors group"
        >
          <div className="flex items-center justify-between mb-3">
            <BarChart2 size={22} className="text-amber-400" />
            <ArrowRight size={16} className="text-slate-600 group-hover:text-amber-400 transition-colors" />
          </div>
          <h2 className="font-semibold text-white mb-1">Thống kê & Seed</h2>
          <p className="text-sm text-slate-400">Số chunks, collections MongoDB, seed dữ liệu mẫu.</p>
        </Link>

        <a
          href="/"
          target="_blank"
          rel="noreferrer"
          className="bg-[#0f1729] border border-white/10 rounded-xl p-5 hover:border-white/20 transition-colors group"
        >
          <div className="flex items-center justify-between mb-3">
            <Upload size={22} className="text-slate-400" />
            <ArrowRight size={16} className="text-slate-600 group-hover:text-slate-400 transition-colors" />
          </div>
          <h2 className="font-semibold text-white mb-1">Xem trang người dùng</h2>
          <p className="text-sm text-slate-400">Mở trang chính để kiểm tra kết quả.</p>
        </a>
      </div>

      {/* Pipeline info */}
      <div className="bg-amber-400/5 border border-amber-400/20 rounded-xl p-4">
        <p className="text-sm text-amber-400/80">
          <strong className="text-amber-400">Quy trình:</strong> Upload tài liệu → Pipeline tự động xử lý (extract → chunk → embed) →
          Chunks được đánh dấu <code className="bg-amber-400/10 px-1 rounded">is_global=true</code> → Tất cả người dùng có thể tìm kiếm và nhận recommendations.
        </p>
      </div>

      {/* Alerts */}
      {!statsLoading && failedJobs > 0 && (
        <div className="flex items-start gap-3 bg-red-500/5 border border-red-500/20 rounded-xl p-4">
          <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-400">{failedJobs} job(s) thất bại</p>
            <p className="text-xs text-slate-400 mt-0.5">Vào <Link to="/admin/jobs" className="text-amber-400 hover:underline">Theo dõi Jobs</Link> để xem chi tiết và reprocess.</p>
          </div>
        </div>
      )}

      {!statsLoading && chunksTotal === 0 && (stats?.documents_total ?? 0) > 0 && (
        <div className="flex items-start gap-3 bg-amber-500/5 border border-amber-500/20 rounded-xl p-4">
          <Clock size={16} className="text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-400">Chưa có chunks nào trong MongoDB</p>
            <p className="text-xs text-slate-400 mt-0.5">Vào <Link to="/admin/stats" className="text-amber-400 hover:underline">Thống kê</Link> để seed dữ liệu mẫu hoặc reprocess tài liệu.</p>
          </div>
        </div>
      )}
    </div>
  );
}

function MiniStat({ icon, label, value, sub, subColor }: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  sub?: string;
  subColor?: string;
}) {
  return (
    <div className="bg-[#0f1729] border border-white/10 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-xl font-bold text-white">{typeof value === 'number' ? value.toLocaleString('vi-VN') : value}</p>
      {sub && <p className={`text-[10px] mt-0.5 ${subColor || 'text-slate-500'}`}>{sub}</p>}
    </div>
  );
}
