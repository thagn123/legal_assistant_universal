import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Upload, Trash2, RefreshCw, FileText, CheckCircle, AlertCircle, Clock, Loader } from 'lucide-react';
import {
  adminUploadDocuments,
  adminGetDocuments,
  adminDeleteDocument,
  adminReprocessDocument,
  adminGetJobs,
  AdminDocument,
  AdminJob,
} from '../../lib/api';

type DocWithJob = AdminDocument & { job?: AdminJob };

const STATUS_ICON: Record<string, React.ReactNode> = {
  complete: <CheckCircle size={14} className="text-emerald-400" />,
  failed: <AlertCircle size={14} className="text-red-400" />,
  running: <Loader size={14} className="text-amber-400 animate-spin" />,
  queued: <Clock size={14} className="text-slate-400" />,
  uploaded: <Clock size={14} className="text-slate-400" />,
};

const STATUS_LABEL: Record<string, string> = {
  complete: 'Hoàn thành',
  failed: 'Lỗi',
  running: 'Đang xử lý',
  queued: 'Chờ xử lý',
  uploaded: 'Đã tải lên',
};

const ALLOWED_EXT = ['.pdf', '.docx', '.doc', '.html', '.htm', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp'];

export function AdminDocuments() {
  const [docs, setDocs] = useState<DocWithJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<number | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [docsData, jobsData] = await Promise.all([
        adminGetDocuments({ limit: 200 }),
        adminGetJobs({ limit: 200 }),
      ]);
      const jobsByDoc: Record<string, AdminJob> = {};
      for (const j of jobsData) {
        if (!jobsByDoc[j.doc_id] || new Date(j.created_at) > new Date(jobsByDoc[j.doc_id].created_at)) {
          jobsByDoc[j.doc_id] = j;
        }
      }
      setDocs(docsData.map((d) => ({ ...d, job: jobsByDoc[d.doc_id] })));
    } catch (e) {
      console.error('Load admin docs failed:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll every 3s when there are active jobs
  useEffect(() => {
    const hasActive = docs.some((d) => d.job && ['queued', 'running'].includes(d.job.status));
    if (hasActive) {
      pollRef.current = window.setInterval(loadData, 3000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [docs, loadData]);

  async function handleFiles(files: FileList | File[]) {
    const arr = Array.from(files);
    const valid = arr.filter((f) => ALLOWED_EXT.some((ext) => f.name.toLowerCase().endsWith(ext)));
    const invalid = arr.filter((f) => !ALLOWED_EXT.some((ext) => f.name.toLowerCase().endsWith(ext)));

    if (invalid.length > 0) {
      setUploadErrors(invalid.map((f) => `${f.name}: định dạng không được hỗ trợ`));
    } else {
      setUploadErrors([]);
    }

    if (valid.length === 0) return;

    setUploading(true);
    try {
      const result = await adminUploadDocuments(valid);
      if (result.errors.length > 0) {
        setUploadErrors(result.errors.map((e) => `${e.filename}: ${e.error}`));
      }
      await loadData();
    } catch (e: any) {
      setUploadErrors([e.message || 'Upload thất bại']);
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(docId: string) {
    if (!confirm('Xóa tài liệu này? Tất cả chunks trong MongoDB cũng sẽ bị xóa.')) return;
    try {
      await adminDeleteDocument(docId);
      setDocs((prev) => prev.filter((d) => d.doc_id !== docId));
    } catch (e: any) {
      alert(e.message || 'Xóa thất bại');
    }
  }

  async function handleReprocess(docId: string) {
    try {
      await adminReprocessDocument(docId);
      await loadData();
    } catch (e: any) {
      alert(e.message || 'Reprocess thất bại');
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-xl font-bold text-white">Quản lý tài liệu</h1>
        <p className="text-sm text-slate-400 mt-1">Upload văn bản luật, hợp đồng mẫu — tự động nhúng vào MongoDB cho tất cả người dùng.</p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
          dragOver ? 'border-amber-400 bg-amber-400/5' : 'border-white/10 hover:border-white/20 hover:bg-white/3'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ALLOWED_EXT.join(',')}
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <Loader size={32} className="text-amber-400 animate-spin" />
            <p className="text-amber-400 font-medium">Đang upload và xử lý…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <Upload size={32} className="text-slate-500" />
            <p className="text-slate-300 font-medium">Kéo thả file vào đây hoặc nhấn để chọn</p>
            <p className="text-xs text-slate-500">Hỗ trợ: PDF, DOCX, DOC, HTML, PNG, JPG và các định dạng ảnh khác</p>
          </div>
        )}
      </div>

      {uploadErrors.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 space-y-1">
          {uploadErrors.map((e, i) => (
            <p key={i} className="text-red-400 text-sm">{e}</p>
          ))}
        </div>
      )}

      {/* Document table */}
      <div className="bg-[#0f1729] border border-white/10 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <h2 className="text-sm font-semibold text-slate-200">
            Tất cả tài liệu <span className="text-slate-500 font-normal">({docs.length})</span>
          </h2>
          <button onClick={loadData} className="text-slate-500 hover:text-slate-300 transition-colors">
            <RefreshCw size={15} />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-slate-500">
            <Loader size={20} className="animate-spin mr-2" /> Đang tải…
          </div>
        ) : docs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-600">
            <FileText size={32} className="mb-3 opacity-40" />
            <p>Chưa có tài liệu nào. Hãy upload để bắt đầu.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-slate-500 uppercase tracking-wide border-b border-white/5">
                <th className="text-left px-4 py-2 font-medium">Tên file</th>
                <th className="text-left px-4 py-2 font-medium">Trạng thái</th>
                <th className="text-left px-4 py-2 font-medium">Chunks</th>
                <th className="text-left px-4 py-2 font-medium">Ngày tải</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {docs.map((doc) => {
                const jobStatus = doc.job?.status || doc.status;
                const chunks = doc.job?.checkpoint?.chunks_embedded ?? '—';
                return (
                  <tr key={doc.doc_id} className="hover:bg-white/3 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileText size={14} className="text-slate-500 flex-shrink-0" />
                        <span className="text-slate-200 truncate max-w-xs">{doc.filename}</span>
                        {doc.is_global && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-400/10 text-amber-400 border border-amber-400/20 flex-shrink-0">
                            GLOBAL
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        {STATUS_ICON[jobStatus] || STATUS_ICON['uploaded']}
                        <span className="text-slate-400">{STATUS_LABEL[jobStatus] || jobStatus}</span>
                      </div>
                      {doc.job?.error && (
                        <p className="text-red-400 text-xs mt-0.5 truncate max-w-xs">{doc.job.error}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-500">{chunks}</td>
                    <td className="px-4 py-3 text-slate-500">
                      {new Date(doc.created_at).toLocaleDateString('vi-VN')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 justify-end">
                        {(jobStatus === 'failed' || jobStatus === 'complete') && (
                          <button
                            onClick={() => handleReprocess(doc.doc_id)}
                            title="Xử lý lại"
                            className="p-1.5 rounded text-slate-500 hover:text-amber-400 hover:bg-amber-400/10 transition-colors"
                          >
                            <RefreshCw size={13} />
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(doc.doc_id)}
                          title="Xóa"
                          className="p-1.5 rounded text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
