/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useMemo, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
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
  Map,
  ListChecks,
  GitCompare,
  BookOpen,
  Radar,
  Gavel,
  FileSearch,
  Clock,
  History,
  ChevronDown,
  BriefcaseBusiness,
  FolderSearch,
  ShieldCheck,
  Sparkles,
  Wifi,
  WifiOff,
  type LucideIcon,
} from 'lucide-react';
import { API_BASE, cn } from '../../lib/api';

type NavItem = {
  path: string;
  label: string;
  icon: LucideIcon;
  description?: string;
};

type NavGroup = {
  id: string;
  label: string;
  icon: LucideIcon;
  items: NavItem[];
};

type SystemStatus = 'checking' | 'online' | 'offline';

const primaryItems: NavItem[] = [
  { path: '/', label: 'Tổng quan', icon: LayoutDashboard },
  {
    path: '/analyze',
    label: 'Phân tích pháp lý',
    icon: Search,
    description: 'MVP: đánh giá, gợi ý, dẫn chứng',
  },
  { path: '/profile', label: 'Hồ sơ của tôi', icon: UserCircle },
];

const navGroups: NavGroup[] = [
  {
    id: 'case-flow',
    label: 'Hồ sơ vụ việc',
    icon: BriefcaseBusiness,
    items: [
      { path: '/journey', label: 'Hành trình pháp lý', icon: Map },
      { path: '/timeline', label: 'Tiến trình & thời hạn', icon: Clock },
      { path: '/evidence-gap', label: 'Thiếu chứng cứ', icon: FileSearch },
      { path: '/actions', label: 'Kế hoạch hành động', icon: ListChecks },
    ],
  },
  {
    id: 'research',
    label: 'Tra cứu & dẫn chứng',
    icon: FolderSearch,
    items: [
      { path: '/law-search', label: 'Tra cứu điều luật', icon: BookOpen },
      { path: '/similar-cases', label: 'Vụ việc tương tự', icon: GitCompare },
      { path: '/documents', label: 'Tài liệu', icon: FileText },
      { path: '/history', label: 'Lịch sử phân tích', icon: History },
    ],
  },
  {
    id: 'contracts',
    label: 'Hợp đồng & điều khoản',
    icon: FileCheck,
    items: [
      { path: '/contract', label: 'Rà soát hợp đồng', icon: FileCheck },
      { path: '/clause-coach', label: 'Tư vấn điều khoản', icon: Gavel },
      { path: '/clause-search', label: 'Tìm điều khoản tương tự', icon: FileSearch },
      { path: '/templates', label: 'Mẫu hợp đồng', icon: ScrollText },
    ],
  },
  {
    id: 'risk',
    label: 'Rủi ro & tuân thủ',
    icon: ShieldCheck,
    items: [
      { path: '/risks', label: 'Đánh giá rủi ro', icon: ShieldAlert },
      { path: '/compliance-radar', label: 'Compliance Radar', icon: Radar },
      { path: '/checklists', label: 'Checklist tuân thủ', icon: ClipboardList },
    ],
  },
];

function isPathActive(pathname: string, path: string): boolean {
  if (path === '/') return pathname === '/';
  return pathname === path || pathname.startsWith(`${path}/`);
}

export function Sidebar() {
  const location = useLocation();
  const [status, setStatus] = useState<SystemStatus>('checking');
  const activeGroupIds = useMemo(() => {
    return navGroups
      .filter(group => group.items.some(item => isPathActive(location.pathname, item.path)))
      .map(group => group.id);
  }, [location.pathname]);

  const [openGroups, setOpenGroups] = useState<Set<string>>(() => new Set(['case-flow']));

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
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    if (!activeGroupIds.length) return;
    setOpenGroups(prev => {
      const next = new Set(prev);
      activeGroupIds.forEach(id => next.add(id));
      return next;
    });
  }, [activeGroupIds]);

  const toggleGroup = (groupId: string) => {
    setOpenGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  };

  return (
    <aside className="w-72 bg-legal-navy border-r border-legal-border flex flex-col shrink-0">
      <div className="p-6 flex items-center gap-3">
        <div className="w-11 h-11 bg-legal-gold rounded-xl flex items-center justify-center shadow-lg shadow-legal-gold/20">
          <Scale className="text-legal-navy" size={24} />
        </div>
        <div>
          <h1 className="font-bold text-xl text-white tracking-tight">LexAI</h1>
          <p className="text-[10px] text-legal-gold font-bold uppercase tracking-widest mt-[-2px]">ULKA Project</p>
        </div>
      </div>

      <nav className="flex-1 px-4 pb-4 overflow-y-auto space-y-5">
        <div className="space-y-1">
          {primaryItems.map((item) => (
            <PrimaryLink key={item.path} item={item} />
          ))}
        </div>

        <div className="space-y-3">
          <p className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-600">
            Công cụ theo nhu cầu
          </p>

          {navGroups.map(group => {
            const isOpen = openGroups.has(group.id);
            const isActive = activeGroupIds.includes(group.id);
            return (
              <div key={group.id} className="rounded-2xl border border-white/5 bg-white/[0.02]">
                <button
                  type="button"
                  onClick={() => toggleGroup(group.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-3 py-3 text-left transition-colors',
                    isActive ? 'text-legal-gold' : 'text-slate-300 hover:text-white',
                  )}
                >
                  <group.icon size={17} className={isActive ? 'text-legal-gold' : 'text-slate-500'} />
                  <span className="flex-1 text-xs font-bold uppercase tracking-wider">{group.label}</span>
                  <ChevronDown
                    size={14}
                    className={cn('text-slate-600 transition-transform', isOpen ? 'rotate-180' : '')}
                  />
                </button>

                {isOpen && (
                  <div className="px-2 pb-2 space-y-1">
                    {group.items.map(item => (
                      <SubLink key={item.path} item={item} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </nav>

      <div className="p-4 space-y-3">
        <div className="bg-legal-gold/5 border border-legal-gold/10 rounded-2xl p-4">
          <div className="flex items-start gap-2 mb-2">
            <Sparkles className="text-legal-gold shrink-0 mt-0.5" size={14} />
            <h4 className="text-[10px] font-bold text-legal-gold uppercase tracking-wider font-mono">Luồng MVP</h4>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            Bắt đầu ở Phân tích pháp lý. Từ kết quả, mở tiếp chứng cứ, rủi ro, điều luật, vụ việc tương tự hoặc hợp đồng.
          </p>
        </div>

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

function PrimaryLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.path}
      className={({ isActive }) => cn(
        'flex items-center gap-3 px-4 py-3 rounded-2xl text-sm transition-all group',
        isActive
          ? 'bg-legal-gold text-legal-navy shadow-lg shadow-legal-gold/20'
          : 'text-slate-400 hover:text-white hover:bg-white/5',
      )}
    >
      <item.icon size={20} />
      <span className="flex-1 font-bold">{item.label}</span>
      {item.description && (
        <span className="hidden group-hover:inline text-[9px] font-semibold opacity-70">
          MVP
        </span>
      )}
    </NavLink>
  );
}

function SubLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.path}
      className={({ isActive }) => cn(
        'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all',
        isActive
          ? 'bg-white/10 text-white'
          : 'text-slate-500 hover:bg-white/5 hover:text-slate-200',
      )}
    >
      <item.icon size={16} />
      <span className="truncate">{item.label}</span>
    </NavLink>
  );
}
