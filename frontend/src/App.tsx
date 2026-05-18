/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Routes, Route, Navigate, NavLink, useLocation } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { AdminLayout } from './components/admin/AdminLayout';
import { Dashboard } from './pages/Dashboard';
import { Analyze } from './pages/Analyze';
import { Contract } from './pages/Contract';
import { Documents } from './pages/Documents';
import { Templates } from './pages/Templates';
import { Risks } from './pages/Risks';
import { Checklists } from './pages/Checklists';
import { Profile } from './pages/Profile';
import { Journey } from './pages/Journey';
import { AdminLogin } from './pages/admin/AdminLogin';
import { AdminDashboard } from './pages/admin/AdminDashboard';
import { AdminDocuments } from './pages/admin/AdminDocuments';
import { AdminJobs } from './pages/admin/AdminJobs';
import { AdminStats } from './pages/admin/AdminStats';
import { LayoutDashboard, Search, FileText, UserCircle, ShieldAlert, ScrollText } from 'lucide-react';

export default function App() {
  const location = useLocation();
  const isAdmin = location.pathname.startsWith('/admin');

  if (isAdmin) {
    return (
      <Routes>
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="documents" element={<AdminDocuments />} />
          <Route path="jobs" element={<AdminJobs />} />
          <Route path="stats" element={<AdminStats />} />
        </Route>
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    );
  }

  return (
    <div className="flex h-screen bg-legal-navy text-slate-100 overflow-hidden">
      <div className="hidden md:flex">
        <Sidebar />
      </div>

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden navy-gradient">
        <Header />
        <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/contract" element={<Contract />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/risks" element={<Risks />} />
            <Route path="/checklists" element={<Checklists />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/journey" element={<Journey />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        {/* MOBILE BOTTOM NAV */}
        <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-legal-navy/95 backdrop-blur-lg border-t border-legal-border flex items-center justify-around px-2 z-50">
          <MobileNavLink to="/" icon={<LayoutDashboard size={20} />} label="Tổng quan" />
          <MobileNavLink to="/analyze" icon={<Search size={20} />} label="Phân tích" />
          <MobileNavLink to="/documents" icon={<FileText size={20} />} label="Tài liệu" />
          <MobileNavLink to="/risks" icon={<ShieldAlert size={20} />} label="Rủi ro" />
          <MobileNavLink to="/profile" icon={<UserCircle size={20} />} label="Hồ sơ" />
        </nav>
      </div>
    </div>
  );
}

function MobileNavLink({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) => `flex flex-col items-center gap-0.5 px-2 transition-colors ${isActive ? 'text-legal-gold' : 'text-slate-500'}`}
    >
      {icon}
      <span className="text-[9px] font-semibold">{label}</span>
    </NavLink>
  );
}
