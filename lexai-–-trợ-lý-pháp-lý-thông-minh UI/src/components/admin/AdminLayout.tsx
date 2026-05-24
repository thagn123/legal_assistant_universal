import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, FileText, Briefcase, BarChart2, LogOut, Shield } from 'lucide-react';
import { clearAdminKey, isAdminAuthenticated } from '../../lib/adminAuth';

const NAV_ITEMS = [
  { to: '/admin', icon: <LayoutDashboard size={18} />, label: 'Tổng quan', end: true },
  { to: '/admin/documents', icon: <FileText size={18} />, label: 'Tài liệu' },
  { to: '/admin/jobs', icon: <Briefcase size={18} />, label: 'Jobs' },
  { to: '/admin/stats', icon: <BarChart2 size={18} />, label: 'Thống kê' },
];

export function AdminLayout() {
  const navigate = useNavigate();

  if (!isAdminAuthenticated()) {
    navigate('/admin/login', { replace: true });
    return null;
  }

  function handleLogout() {
    clearAdminKey();
    navigate('/admin/login', { replace: true });
  }

  return (
    <div className="flex h-screen bg-[#0a0f1e] text-slate-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex flex-col bg-[#0f1729] border-r border-white/10 flex-shrink-0">
        <div className="flex items-center gap-2 px-4 py-5 border-b border-white/10">
          <Shield size={20} className="text-amber-400" />
          <span className="font-bold text-amber-400 text-sm tracking-wide">LexAI Admin</span>
        </div>

        <nav className="flex-1 px-2 py-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-amber-400/10 text-amber-400 font-medium'
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                }`
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>

        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-5 py-4 text-sm text-slate-500 hover:text-red-400 transition-colors border-t border-white/10"
        >
          <LogOut size={16} />
          Đăng xuất
        </button>
      </aside>

      {/* Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="h-14 flex items-center px-6 bg-[#0f1729]/80 border-b border-white/10 flex-shrink-0">
          <span className="text-slate-400 text-sm">Bảng điều khiển quản trị • LexAI</span>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
