/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import { 
  Sparkles, 
  Users, 
  FileCheck, 
  CheckSquare, 
  Download, 
  Eye, 
  ArrowRight,
  TrendingUp,
  Clock,
  ExternalLink,
  Scale,
  ChevronDown
} from 'lucide-react';
import { motion } from 'motion/react';

type SubTab = 'Personalized' | 'Community' | 'Templates' | 'Checklists';

export function RecommendationsTab() {
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('Personalized');

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="p-6 space-y-8"
    >
      {/* Sub-tabs row */}
      <div className="flex flex-wrap items-center gap-2">
        <SubTabButton active={activeSubTab === 'Personalized'} onClick={() => setActiveSubTab('Personalized')} icon={<Sparkles size={14} />} label="Dành cho bạn" />
        <SubTabButton active={activeSubTab === 'Community'} onClick={() => setActiveSubTab('Community')} icon={<Users size={14} />} label="Từ cộng đồng" />
        <SubTabButton active={activeSubTab === 'Templates'} onClick={() => setActiveSubTab('Templates')} icon={<FileCheck size={14} />} label="Tài liệu mẫu" />
        <SubTabButton active={activeSubTab === 'Checklists'} onClick={() => setActiveSubTab('Checklists')} icon={<CheckSquare size={14} />} label="Danh sách kiểm tra" />
      </div>

      <div className="space-y-6">
        {activeSubTab === 'Personalized' && (
          <div className="space-y-8">
            {/* Header Profiling */}
            <div className="bg-gradient-to-br from-indigo-900 to-violet-900 rounded-2xl p-8 text-white space-y-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl -mr-32 -mt-32" />
              <div className="space-y-2">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <TrendingUp size={24} className="text-violet-300" />
                  Dựa trên thói quen của bạn
                </h2>
                <p className="text-sm text-indigo-100 font-medium italic opacity-80">"Được cá nhân hóa dựa trên 142 tương tác"</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-end">
                <div className="space-y-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-indigo-200">Lĩnh vực hàng đầu:</p>
                  <div className="space-y-3">
                    {[
                      { label: 'Đất đai', val: 78, color: 'bg-blue-400' },
                      { label: 'Hợp đồng', val: 45, color: 'bg-violet-400' },
                      { label: 'Lao động', val: 22, color: 'bg-emerald-400' },
                    ].map(d => (
                      <div key={d.label} className="space-y-1">
                        <div className="flex justify-between text-[10px] font-bold">
                          <span>{d.label}</span>
                          <span>{d.val}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-indigo-950/50 rounded-full overflow-hidden">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${d.val}%` }} className={`h-full ${d.color}`} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="bg-white/5 rounded-xl p-4 border border-white/10 backdrop-blur-sm">
                   <p className="text-[10px] font-bold uppercase tracking-wider text-indigo-200 mb-4">Hoạt động trong ngày (0-23h)</p>
                   <div className="flex items-end gap-1 h-12">
                     {[2,5,10,12,15,30,45,60,80,95,70,40,25,30,55,85,100,90,70,50,30,15,10,5].map((h, i) => (
                       <div key={i} className="flex-1 bg-violet-400/30 rounded-t-sm hover:bg-violet-400 transition-all cursor-crosshair" style={{ height: `${h}%` }} />
                     ))}
                   </div>
                </div>
              </div>
            </div>

            {/* Recommendations List */}
            <div className="space-y-4">
              {[
                { type: 'law', title: 'Nghị định 12/2024/NĐ-CP - Hướng dẫn Luật Đất đai', desc: 'Có 3 điều khoản mới liên quan trực tiếp đến hồ sơ dự án Vinhomes của bạn.', score: 0.98, fresh: 'Mới 3 ngày' },
                { type: 'case', title: 'Án lệ số 14/2023/AL - Tranh chấp cọc', desc: 'Lập luận trong bản án này giúp củng cố vị thế của bạn trong vụ kiện hàng xóm.', score: 0.85, fresh: '6 tháng' },
                { type: 'template', title: 'Mẫu hợp đồng thuê mặt bằng thương mại (Chuẩn)', desc: 'Tài liệu mẫu được cập nhật theo thông tư mới nhất của Bộ Xây dựng.', score: 0.72, fresh: '1 tuần' },
              ].map((rec, i) => (
                <div key={i} className="bg-white border border-legal-border rounded-2xl p-5 flex items-center gap-6 group hover:shadow-md transition-all">
                  <div className={`w-1 h-12 rounded-full ${i % 3 === 0 ? 'bg-blue-500' : i % 3 === 1 ? 'bg-emerald-500' : 'bg-violet-500'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-bold text-slate-800 text-sm truncate group-hover:text-legal-primary transition-colors">{rec.title}</h4>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${rec.fresh.startsWith('Mới') ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-400'}`}>
                        {rec.fresh}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 line-clamp-1 italic">"{rec.desc}"</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col items-end">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Correlation</span>
                      <span className="text-lg font-bold text-legal-primary">{(rec.score * 100).toFixed(0)}%</span>
                    </div>
                    <button className="p-2 bg-slate-50 text-legal-primary rounded-full hover:bg-slate-100 transition-colors">
                      <ArrowRight size={18} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeSubTab === 'Templates' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { name: 'Hợp đồng thuê nhà ở', type: 'Dân sự', chips: ['Tiền cọc', 'Chi phí điện nước', 'Thời hạn'] },
              { name: 'Hợp đồng mua bán căn hộ', type: 'Bất động sản', chips: ['Pháp lý dự án', 'Bảo hành', 'Bàn giao'] },
              { name: 'Hợp đồng lao động không thời hạn', type: 'Lao động', chips: ['Bảo mật', 'Phụ cấp', 'Chấm dứt'] },
              { name: 'Thỏa thuận cổ đông sáng lập', type: 'Doanh nghiệp', chips: ['Vesting', 'Quyền biểu quyết', 'Thoái vốn'] },
              { name: 'Hợp đồng cung cấp dịch vụ phần mềm', type: 'Dịch vụ', chips: ['Sở hữu trí tuệ', 'SLA', 'Giới hạn trách nhiệm'] },
              { name: 'Biên bản thỏa thuận bồi thường', type: 'Dân sự', chips: ['Quyền từ chối', 'Mức phạt', 'Xác nhận'] },
            ].map(tpl => (
              <div key={tpl.name} className="bg-white p-6 rounded-2xl border border-legal-border flex flex-col space-y-4 hover:shadow-lg transition-all group">
                <div className="flex items-start justify-between">
                  <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-[9px] font-bold uppercase">{tpl.type}</span>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                     <button className="p-1.5 text-slate-400 hover:text-legal-primary hover:bg-slate-50 rounded"><Download size={14} /></button>
                     <button className="p-1.5 text-slate-400 hover:text-legal-primary hover:bg-slate-50 rounded"><Eye size={14} /></button>
                  </div>
                </div>
                <h3 className="font-bold text-slate-800 text-sm group-hover:text-legal-primary transition-colors">{tpl.name}</h3>
                <div className="flex flex-wrap gap-1.5">
                  {tpl.chips.map(c => (
                    <span key={c} className="px-2 py-0.5 bg-slate-100 text-slate-500 rounded-full text-[9px] font-medium">{c}</span>
                  ))}
                </div>
                <div className="pt-4 mt-auto">
                    <button className="w-full py-2 bg-slate-50 text-legal-primary font-bold text-xs rounded-lg hover:bg-slate-100 transition-colors">Sử dụng mẫu</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeSubTab === 'Checklists' && (
          <div className="space-y-4">
            <details className="group" open>
              <summary className="flex items-center justify-between p-4 bg-white border border-legal-border rounded-xl cursor-pointer hover:bg-slate-50 transition-all list-none">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
                    <Scale size={16} />
                  </div>
                  <h3 className="text-sm font-bold text-slate-800">Thủ tục khởi kiện tranh chấp Đất đai</h3>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <div className="w-24 bg-slate-100 h-1.5 rounded-full overflow-hidden">
                       <div className="h-full bg-legal-primary" style={{ width: '40%' }} />
                    </div>
                    <span className="text-[10px] font-bold text-slate-500">40%</span>
                  </div>
                  <ChevronDown className="group-open:rotate-180 transition-transform text-slate-400" size={16} />
                </div>
              </summary>
              <div className="p-6 bg-white border border-legal-border border-t-0 rounded-b-xl space-y-4">
                {[
                  { text: 'Xác định thẩm quyền của Tòa án (TAND cấp huyện nơi có đất)', law: 'Điều 35 BLTTDS', done: true },
                  { text: 'Chuẩn bị đơn khởi kiện theo đúng biểu mẫu pháp luật', law: 'Điều 189 BLTTDS', done: true },
                  { text: 'Nộp biên bản hòa giải không thành tại UBND cấp xã', law: 'Điều 202 Luật Đất đai', done: false },
                  { text: 'Chuẩn bị bản sao GCNQSDĐ (Sổ đỏ) có công chứng', law: '', done: false },
                  { text: 'Ảnh chụp, biên bản đo đạc hiện trạng thực tế', law: '', done: false },
                ].map((item, idx) => (
                  <div key={idx} className="flex items-start gap-4">
                    <input type="checkbox" checked={item.done} className="mt-1 w-4 h-4 rounded text-legal-primary focus:ring-legal-primary border-slate-300" readOnly />
                    <div className="flex-1 min-w-0">
                       <p className={`text-sm ${item.done ? 'text-slate-400 line-through' : 'text-slate-700 font-medium'}`}>{item.text}</p>
                       {item.law && <span className="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-mono mt-1 inline-block">Ref: {item.law}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}
      </div>
    </motion.div>
  );
}

function SubTabButton({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold transition-all border ${
        active 
          ? 'bg-legal-primary text-white border-legal-primary shadow-md' 
          : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
