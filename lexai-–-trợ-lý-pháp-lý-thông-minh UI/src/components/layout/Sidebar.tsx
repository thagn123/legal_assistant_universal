/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Search,
  FileText,
  FileCheck,
  ShieldAlert,
  ClipboardList,
  UserCircle,
  Scale,
  ScrollText,
  Info,
  Map,
  ListChecks,
  GitCompare,
  BookOpen,
  Radar,
  Gavel,
  FileSearch,
  Clock,
  History,
} from 'lucide-react';
import { cn } from '../../lib/api';

const menuItems = [
  { path: '/', label: 'Tổng quan', icon: LayoutDashboard },
  { path: '/analyze', label: 'Phân tích', icon: Search },
  { path: '/journey', label: 'Hành Trình', icon: Map },
  { path: '/timeline', label: 'Tiến trình pháp lý', icon: Clock },
  { path: '/actions', label: 'Kế hoạch hành động', icon: ListChecks },
  { path: '/law-search', label: 'Tra cứu điều luật', icon: BookOpen },
  { path: '/similar-cases', label: 'Vụ việc tương tự', icon: GitCompare },
  { path: '/evidence-gap', label: 'Kiểm tra chứng cứ', icon: FileSearch },
  { path: '/contract', label: 'Rà soát hợp đồng', icon: FileCheck },
  { path: '/clause-coach', label: 'Tư vấn điều khoản', icon: Gavel },
  { path: '/clause-search', label: 'Tìm điều khoản', icon: FileSearch },
  { path: '/documents', label: 'Tài liệu', icon: FileText },
  { path: '/templates', label: 'Mẫu hợp đồng', icon: ScrollText },
  { path: '/risks', label: 'Rủi ro pháp lý', icon: ShieldAlert },
  { path: '/compliance-radar', label: 'Compliance Radar', icon: Radar },
  { path: '/checklists', label: 'Liên kết tuân thủ', icon: ClipboardList },
  { path: '/history', label: 'Lịch sử phân tích', icon: History },
  { path: '/profile', label: 'Hồ sơ của tôi', icon: UserCircle },
];

export function Sidebar() {
  return (
    <aside className="w-64 bg-legal-navy border-r border-legal-border flex flex-col shrink-0">
      <div className="p-6 flex items-center gap-3">
        <div className="w-10 h-10 bg-legal-gold rounded-xl flex items-center justify-center shadow-lg shadow-legal-gold/20">
          <Scale className="text-legal-navy" size={24} />
        </div>
        <div>
          <h1 className="font-bold text-xl text-white tracking-tight">LexAI</h1>
          <p className="text-[10px] text-legal-gold font-bold uppercase tracking-widest mt-[-2px]">ULKA Project</p>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all group",
              isActive 
                ? "bg-legal-gold text-legal-navy shadow-lg shadow-legal-gold/20" 
                : "text-slate-400 hover:text-white hover:bg-white/5"
            )}
          >
            <item.icon size={20} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* AI GUIDE INFO BOX */}
      <div className="p-4 mx-4 mb-4 bg-legal-gold/5 border border-legal-gold/10 rounded-2xl">
        <div className="flex items-start gap-2 mb-2">
          <Info className="text-legal-gold shrink-0 mt-0.5" size={14} />
          <h4 className="text-[10px] font-bold text-legal-gold uppercase tracking-wider font-mono">Hướng dẫn AI</h4>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed italic">
          "Trợ lý chỉ căn cứ pháp luật Việt Nam hiện hành. Luôn trích dẫn nguồn cụ thể. Cảnh báo về thời hiệu và rủi ro. Không bịa đặt điều luật."
        </p>
      </div>

      <div className="p-4">
        <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Trạng thái hệ thống</p>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-legal-success animate-pulse" />
            <span className="text-xs text-slate-300">Hoạt động bình thường</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
