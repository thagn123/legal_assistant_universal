/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import { 
  Upload, 
  File, 
  MoreVertical, 
  Plus, 
  CheckCircle2, 
  Loader2,
  Share2,
  LayoutGrid,
  FileText,
  FileCode,
  Image as ImageIcon,
  MoreHorizontal
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Document } from '../types';

export function DocumentsTab() {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState(0);

  const steps = [
    { label: 'Nhận tệp', icon: <File size={14} /> },
    { label: 'Phân tích bố cục', icon: <LayoutGrid size={14} /> },
    { label: 'Trích xuất nội dung', icon: <FileText size={14} /> },
    { label: 'Làm sạch OCR', icon: <ImageIcon size={14} /> },
    { label: 'Chuẩn hóa cấu trúc', icon: <FileCode size={14} /> },
    { label: 'Tạo chunk', icon: <MoreHorizontal size={14} /> },
    { label: 'Xây dựng đồ thị', icon: <Share2 size={14} /> },
    { label: 'Lập chỉ mục', icon: <CheckCircle2 size={14} /> }
  ];

  const handleUpload = () => {
    setIsUploading(true);
    setUploadStep(0);
    const interval = setInterval(() => {
      setUploadStep(prev => {
        if (prev >= steps.length - 1) {
          clearInterval(interval);
          setTimeout(() => setIsUploading(false), 1000);
          return prev;
        }
        return prev + 1;
      });
    }, 600);
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="p-6 space-y-8"
    >
      {/* Upload Zone */}
      <div className="bg-white p-8 rounded-2xl border-2 border-dashed border-slate-200 flex flex-col items-center justify-center text-center space-y-4 hover:border-legal-primary transition-all group cursor-pointer" onClick={handleUpload}>
        <div className="w-16 h-16 bg-slate-50 text-slate-400 group-hover:text-legal-primary group-hover:bg-blue-50 rounded-full flex items-center justify-center transition-all">
          <Upload size={32} />
        </div>
        <div className="space-y-1">
          <h3 className="text-lg font-bold text-slate-700">Kéo thả tài liệu pháp lý vào đây</h3>
          <p className="text-sm text-slate-400">PDF, DOCX, HTML, PNG, JPG (Tối đa 25MB)</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="h-px w-8 bg-slate-200" />
          <span className="text-xs font-bold text-slate-400 uppercase">hoặc</span>
          <div className="h-px w-8 bg-slate-200" />
        </div>
        <button className="px-6 py-2 bg-legal-primary text-white rounded-full font-semibold text-sm shadow-md hover:shadow-lg transition-all">
          Chọn tệp
        </button>
        <div className="flex flex-wrap items-center gap-2 pt-2">
          {['PDF', 'DOCX', 'HTML', 'Hình ảnh'].map(t => (
            <span key={t} className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded text-[10px] font-bold">{t}</span>
          ))}
        </div>
      </div>

      {/* Processing Pipeline */}
      <AnimatePresence>
        {isUploading && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-white rounded-2xl p-6 shadow-sm border border-legal-border space-y-6 overflow-hidden"
          >
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
              {steps.map((step, idx) => (
                <div key={idx} className="flex flex-col items-center gap-2 text-center">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                    idx < uploadStep ? 'bg-emerald-100 text-emerald-600' :
                    idx === uploadStep ? 'bg-blue-100 text-blue-600 animate-pulse' : 'bg-slate-50 text-slate-300'
                  }`}>
                    {idx < uploadStep ? <CheckCircle2 size={20} /> : 
                     idx === uploadStep ? <Loader2 size={20} className="animate-spin" /> : step.icon}
                  </div>
                  <span className={`text-[10px] font-bold uppercase ${idx <= uploadStep ? 'text-slate-700' : 'text-slate-300'}`}>
                    {step.label}
                  </span>
                </div>
              ))}
            </div>
            <div className="bg-slate-100 h-2 rounded-full overflow-hidden">
              <motion.div 
                className="h-full bg-legal-primary" 
                initial={{ width: 0 }}
                animate={{ width: `${((uploadStep + 1) / steps.length) * 100}%` }}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Document Library */}
      <div className="space-y-4">
        <h2 className="text-xl font-bold text-legal-primary">Thư viện tài liệu</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {mockDocs.map((doc) => (
            <div key={doc.id} className="bg-white p-5 rounded-2xl shadow-sm border border-legal-border hover:shadow-md transition-all flex flex-col group">
              <div className="flex items-start justify-between mb-4">
                <div className={`p-2 rounded-lg ${
                  doc.type === 'pdf' ? 'bg-red-50 text-red-500' :
                  doc.type === 'docx' ? 'bg-blue-50 text-blue-500' : 'bg-amber-50 text-amber-500'
                }`}>
                  <FileText size={24} />
                </div>
                <button className="p-1 text-slate-300 hover:text-slate-600 rounded">
                  <MoreHorizontal size={20} />
                </button>
              </div>
              <h3 className="font-bold text-slate-800 text-sm mb-2 line-clamp-2 leading-tight group-hover:text-legal-primary transition-colors">
                {doc.name}
              </h3>
              <div className="flex items-center gap-2 mb-4">
                <span className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded text-[9px] font-bold uppercase tracking-wide">
                  {doc.domain}
                </span>
                <span className="text-[10px] text-slate-400 font-medium">{doc.date}</span>
                <span className="text-[10px] text-slate-400 font-medium">• {doc.chunkCount} chunks</span>
              </div>
              <div className="mt-auto flex items-center justify-between pt-4 border-t border-slate-50">
                <button className="text-xs font-bold text-legal-primary hover:underline">Phân tích</button>
                <button className="text-xs font-medium text-slate-400 hover:text-legal-primary">Xem đồ thị ↗</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

const mockDocs: Document[] = [
  { id: '1', name: 'Hợp đồng mua bán Đất đai Dự án Vinhomes - Block A12.pdf', type: 'pdf', domain: 'Đất đai', date: '21/04/2024', chunkCount: 142 },
  { id: '2', name: 'Phụ lục hợp đồng lao động - Điều khoản bảo mật NDA.docx', type: 'docx', domain: 'Lao động', date: '19/04/2024', chunkCount: 38 },
  { id: '3', name: 'Quy định nội bộ Công ty TNHH Giải pháp AI Sovereign.html', type: 'html', domain: 'Doanh nghiệp', date: '15/04/2024', chunkCount: 89 },
  { id: '4', name: 'Biên bản thỏa thuận mức bồi thường thiệt hại tài sản.pdf', type: 'pdf', domain: 'Dân sự', date: '12/04/2024', chunkCount: 22 },
  { id: '5', name: 'Điều lệ Công ty Cổ phần Công nghệ LexAI Việt Nam.docx', type: 'docx', domain: 'Doanh nghiệp', date: '05/04/2024', chunkCount: 256 },
  { id: '6', name: 'Hợp đồng thuê căn hộ chung cư cao cấp Landmark 81.pdf', type: 'pdf', domain: 'Dân sự', date: '01/04/2024', chunkCount: 54 },
];
