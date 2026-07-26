/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { Suspense } from 'react';
import { Routes, Route, Navigate, NavLink, useLocation } from 'react-router-dom';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { AdminLayout } from './components/admin/AdminLayout';
import { LayoutDashboard, Search, FileText, UserCircle } from 'lucide-react';

const lazyNamed = <T extends React.ComponentType<any>>(
  loader: () => Promise<Record<string, T>>,
  exportName: string,
) =>
  React.lazy(async () => {
    const mod = await loader();
    return { default: mod[exportName] };
  });

const Dashboard = lazyNamed(() => import('./pages/Dashboard'), 'Dashboard');
const Analyze = lazyNamed(() => import('./pages/Analyze'), 'Analyze');
const Contract = lazyNamed(() => import('./pages/Contract'), 'Contract');
const Documents = lazyNamed(() => import('./pages/Documents'), 'Documents');
const Templates = lazyNamed(() => import('./pages/Templates'), 'Templates');
const Risks = lazyNamed(() => import('./pages/Risks'), 'Risks');
const Checklists = lazyNamed(() => import('./pages/Checklists'), 'Checklists');
const Profile = lazyNamed(() => import('./pages/Profile'), 'Profile');
const Journey = lazyNamed(() => import('./pages/Journey'), 'Journey');
const Actions = lazyNamed(() => import('./pages/Actions'), 'Actions');
const SimilarCases = lazyNamed(() => import('./pages/SimilarCases'), 'SimilarCases');
const LawSearch = lazyNamed(() => import('./pages/LawSearch'), 'LawSearch');
const ComplianceRadar = lazyNamed(() => import('./pages/ComplianceRadar'), 'ComplianceRadar');
const ClauseCoach = lazyNamed(() => import('./pages/ClauseCoach'), 'ClauseCoach');
const EvidenceGap = lazyNamed(() => import('./pages/EvidenceGap'), 'EvidenceGap');
const ClauseSearch = lazyNamed(() => import('./pages/ClauseSearch'), 'ClauseSearch');
const Timeline = lazyNamed(() => import('./pages/Timeline'), 'Timeline');
const AnalysisHistory = lazyNamed(() => import('./pages/AnalysisHistory'), 'AnalysisHistory');
const AdminLogin = lazyNamed(() => import('./pages/admin/AdminLogin'), 'AdminLogin');
const AdminDashboard = lazyNamed(() => import('./pages/admin/AdminDashboard'), 'AdminDashboard');
const AdminDocuments = lazyNamed(() => import('./pages/admin/AdminDocuments'), 'AdminDocuments');
const AdminJobs = lazyNamed(() => import('./pages/admin/AdminJobs'), 'AdminJobs');
const AdminStats = lazyNamed(() => import('./pages/admin/AdminStats'), 'AdminStats');

function RouteFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-xs font-bold uppercase tracking-widest text-slate-500">
      Đang tải...
    </div>
  );
}

export default function App() {
  const location = useLocation();
  const isAdmin = location.pathname.startsWith('/admin');

  if (isAdmin) {
    return (
      <Suspense fallback={<RouteFallback />}>
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
      </Suspense>
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
          <Suspense fallback={<RouteFallback />}>
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
              <Route path="/actions" element={<Actions />} />
              <Route path="/law-search" element={<LawSearch />} />
              <Route path="/compliance-radar" element={<ComplianceRadar />} />
              <Route path="/similar-cases" element={<SimilarCases />} />
              <Route path="/clause-coach" element={<ClauseCoach />} />
              <Route path="/evidence-gap" element={<EvidenceGap />} />
              <Route path="/clause-search" element={<ClauseSearch />} />
              <Route path="/timeline" element={<Timeline />} />
              <Route path="/history" element={<AnalysisHistory />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>

        {/* MOBILE BOTTOM NAV */}
        <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 bg-legal-navy/80 backdrop-blur-lg border-t border-legal-border flex items-center justify-around px-4 z-50">
          <MobileNavLink to="/" icon={<LayoutDashboard size={20} />} label="Home" />
          <MobileNavLink to="/analyze" icon={<Search size={20} />} label="Analyze" />
          <MobileNavLink to="/documents" icon={<FileText size={20} />} label="Docs" />
          <MobileNavLink to="/profile" icon={<UserCircle size={20} />} label="Profile" />
        </nav>
      </div>
    </div>
  );
}

function MobileNavLink({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) {
  return (
    <NavLink 
      to={to} 
      className={({ isActive }) => `flex flex-col items-center gap-1 transition-colors ${isActive ? 'text-legal-gold' : 'text-slate-500'}`}
    >
      {icon}
      <span className="text-[10px] font-bold uppercase">{label}</span>
    </NavLink>
  );
}
