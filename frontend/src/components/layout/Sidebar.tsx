/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
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
  Wifi,
  WifiOff,
} from 'lucide-react';
import { cn, API_BASE } from '../../lib/api';

const menuItems = [
  { path: '/', label: 'Tổng quan', icon: LayoutDashboard },
  { path: '/analyze', label: 'Phân tích', icon: Search },
  { path: '/journey', label: 'Hành Trình', icon: Map },
  { path: '/contract', label: 'Rà soát hợp đồng', icon: FileCheck },
  { path: '/documents', label: 'Tài liệu', icon: FileText },
  { path: '/templates', label: 'Mẫu hợp đồng', icon: ScrollText },
  { path: '/risks', label: 'Rủi ro pháp lý', icon: ShieldAlert },
  { path: '/checklists', label: 'Liên kết tuân thủ', icon: ClipboardList },
  { path: '/profile', label: 'Hồ sơ của tôi', icon: UserCircle },
];

type SystemStatus = 'checking' | 'online' | 'offline';

export function Sidebar() {
  const [status, setStatus] = useState<SystemStatus>('checking');

  useEffect(() => {
    let mounted = true;
    async function checkStatus() {
      try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
        if (mounted) setStatus(res.ok ? 'online' : 'offline');
      } catch {
        if (mounted) setStatus('offline');
      }
    }
    checkStatus();
    const interval = setInterval(checkStatus, 30_000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  return (
    <aside className="w-64 bg-legal-navy border-r border-legal-border flex flex-col shrink-0">
      {/* Logo */}
      <div className="p-6 flex items-center gap-3">
        <div className="w-10 h-10 bg-legal-gold rounded-xl flex items-center justify-center shadow-lg shadow-legal-gold/20">
          <Scale className="text-legal-navy" size={24} />
        </div>
        <div>
          <h1 className="font-bold text-xl text-white tracking-tight">LexAI</h1>
          <p className="text-[10px] text-legal-gold font-bold uppercase tracking-widest mt-[-2px]">ULKA Project</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {menuItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
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

      {/* AI Guide */}
      <div className="p-4 mx-4 bg-legal-gold/5 border border-legal-gold/10 rounded-2xl">
        <div className="flex items-start gap-2 mb-2">
          <Info className="text-legal-gold shrink-0 mt-0.5" size={14} />
          <h4 className="text-[10px] font-bold text-legal-gold uppercase tracking-wider font-mono">Hướng dẫn AI</h4>
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed italic">
          "Trợ lý chỉ căn cứ pháp luật Việt Nam hiện hành. Luôn trích dẫn nguồn cụ thể. Cảnh báo về thời hiệu và rủi ro. Không bịa đặt điều luật."
        </p>
      </div>

      {/* System status */}
      <div className="p-4">
        <div className="bg-white/5 border border-white/10 rounded-2xl p-4">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Trạng thái hệ thống</p>
          <div className="flex items-center gap-2">
            {status === 'checking' && (
              <>
                <div className="w-2 h-2 rounded-full bg-slate-500 animate-pulse" />
                <span className="text-xs text-slate-400">Đang kiểm tra...</span>
              </>
            )}
            {status === 'online' && (
              <>
                <Wifi size={13} className="text-legal-success" />
                <span className="text-xs text-legal-success font-medium">Backend hoạt động</span>
              </>
            )}
            {status === 'offline' && (
              <>
                <WifiOff size={13} className="text-legal-danger" />
                <span className="text-xs text-legal-danger font-medium">Backend ngoại tuyến</span>
              </>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}
