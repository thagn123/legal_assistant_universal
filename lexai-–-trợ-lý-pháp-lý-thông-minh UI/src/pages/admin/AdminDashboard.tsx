import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, Briefcase, BarChart2, ArrowRight, Upload } from 'lucide-react';

export function AdminDashboard() {
  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-bold text-white">Chào mừng đến Admin Panel</h1>
        <p className="text-sm text-slate-400 mt-1">Quản lý dữ liệu và theo dõi hệ thống LexAI.</p>
      </div>

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
            <ArrowRight size={16} className="text-slate-600 group-hover:text-amber-400 transition-colors" />
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
          <h2 className="font-semibold text-white mb-1">Thống kê</h2>
          <p className="text-sm text-slate-400">Số chunks, collections MongoDB, tỉ lệ thành công.</p>
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

      <div className="bg-amber-400/5 border border-amber-400/20 rounded-xl p-4">
        <p className="text-sm text-amber-400/80">
          <strong className="text-amber-400">Quy trình:</strong> Upload tài liệu → Pipeline tự động xử lý (extract → chunk → embed) →
          Chunks được đánh dấu <code className="bg-amber-400/10 px-1 rounded">is_global=true</code> → Tất cả người dùng có thể tìm kiếm và nhận recommendations.
        </p>
      </div>
    </div>
  );
}
