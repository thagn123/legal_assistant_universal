import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Loader, RefreshCw, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { adminGetJobs, AdminJob } from '../../lib/api';

const STATUS_ICON: Record<string, React.ReactNode> = {
  complete: <CheckCircle size={13} className="text-emerald-400" />,
  failed: <AlertCircle size={13} className="text-red-400" />,
  running: <Loader size={13} className="text-amber-400 animate-spin" />,
  queued: <Clock size={13} className="text-slate-400" />,
};

const STATUS_LABEL: Record<string, string> = {
  complete: 'Hoàn thành',
  failed: 'Lỗi',
  running: 'Đang chạy',
  queued: 'Chờ',
};

export function AdminJobs() {
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await adminGetJobs({ limit: 200 });
      setJobs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const hasActive = jobs.some((j) => ['queued', 'running'].includes(j.status));
    if (hasActive) {
      pollRef.current = window.setInterval(load, 3000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [jobs, load]);

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Lịch sử Jobs <span className="text-slate-500 font-normal text-base">({jobs.length})</span></h1>
        <button onClick={load} className="text-slate-500 hover:text-slate-300 transition-colors">
          <RefreshCw size={15} />
        </button>
      </div>

      <div className="bg-[#0f1729] border border-white/10 rounded-xl overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-slate-500">
            <Loader size={20} className="animate-spin mr-2" /> Đang tải…
          </div>
        ) : jobs.length === 0 ? (
          <div className="py-16 text-center text-slate-600">Chưa có job nào.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-slate-500 uppercase tracking-wide border-b border-white/5">
                <th className="text-left px-4 py-2 font-medium">Job ID</th>
                <th className="text-left px-4 py-2 font-medium">Doc ID</th>
                <th className="text-left px-4 py-2 font-medium">User</th>
                <th className="text-left px-4 py-2 font-medium">Trạng thái</th>
                <th className="text-left px-4 py-2 font-medium">Chunks</th>
                <th className="text-left px-4 py-2 font-medium">Thời gian</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {jobs.map((job) => (
                <tr key={job.job_id} className="hover:bg-white/3 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{job.job_id.slice(0, 8)}…</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{job.doc_id.slice(0, 8)}…</td>
                  <td className="px-4 py-3 text-slate-400">{job.user_id}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      {STATUS_ICON[job.status] || STATUS_ICON['queued']}
                      <span className="text-slate-400">{STATUS_LABEL[job.status] || job.status}</span>
                    </div>
                    {job.error && <p className="text-red-400 text-xs mt-0.5 truncate max-w-xs">{job.error}</p>}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {job.checkpoint?.chunks_embedded ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs">
                    {new Date(job.created_at).toLocaleString('vi-VN')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
