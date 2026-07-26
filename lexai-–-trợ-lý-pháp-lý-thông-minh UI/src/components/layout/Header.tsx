/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { User, Bell, ChevronRight, ChevronDown, Check, Users } from 'lucide-react';
import { getUserId, setUserId } from '../../lib/api';

const routeLabels: Record<string, string> = {
  '/': 'Tổng quan',
  '/analyze': 'Phân tích tình huống',
  '/documents': 'Tài liệu pháp lý',
  '/templates': 'Mẫu hợp đồng',
  '/risks': 'Rủi ro pháp lý',
  '/checklists': 'Danh sách tuân thủ',
  '/profile': 'Hồ sơ cá nhân',
  '/similar-cases': 'Vụ việc tương tự',
  '/history': 'Lịch sử phân tích',
};

// ── Demo persona definitions ──────────────────────────────────────────────────

const DEMO_PERSONAS = [
  {
    id: 'demo_user_family',
    label: 'Hồ sơ gia đình',
    description: 'Ly hôn · Nuôi con · Chia tài sản',
    color: 'text-pink-400',
    bg: 'bg-pink-500/10',
    border: 'border-pink-500/20',
  },
  {
    id: 'demo_user_employee',
    label: 'Người lao động',
    description: 'Sa thải · Lương · BHXH',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/20',
  },
  {
    id: 'demo_user_sme',
    label: 'Doanh nghiệp nhỏ',
    description: 'Hợp đồng · Phạt vi phạm · Tranh chấp',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/20',
  },
];

// ── Toast notification ────────────────────────────────────────────────────────

function PersonaSwitchToast({ label, onDone }: { label: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2400);
    return () => clearTimeout(t);
  }, [onDone]);
  return (
    <div className="fixed bottom-6 right-6 z-[9999] animate-in slide-in-from-bottom-4 fade-in duration-300">
      <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-legal-gold text-legal-navy font-semibold text-sm shadow-xl">
        <Check size={14} />
        Đã chuyển hồ sơ demo: {label}
      </div>
    </div>
  );
}

// ── Header ────────────────────────────────────────────────────────────────────

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentLabel = routeLabels[location.pathname] || 'LexAI';

  const [currentUserId, setCurrentUserId] = useState(getUserId);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [toast, setToast] = useState<{ label: string } | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentPersona = DEMO_PERSONAS.find(p => p.id === currentUserId) || null;

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    if (dropdownOpen) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [dropdownOpen]);

  function handlePersonaSwitch(persona: typeof DEMO_PERSONAS[number]) {
    setDropdownOpen(false);
    if (persona.id === currentUserId) return;
    setUserId(persona.id);
    setCurrentUserId(persona.id);
    setToast({ label: persona.label });
    // Reload current page to refresh data for new persona
    navigate(0);
  }

  return (
    <header className="h-16 border-b border-legal-border flex items-center justify-between px-8 bg-legal-navy/50 backdrop-blur-md sticky top-0 z-30">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-slate-400 text-sm">
        <span>LexAI</span>
        <ChevronRight size={14} />
        <span className="text-white font-medium">{currentLabel}</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Notification bell */}
        <button
          type="button"
          onClick={() => window.alert('Chưa có thông báo mới. LexAI sẽ hiển thị nhắc việc và cập nhật hồ sơ tại đây.')}
          className="relative text-slate-400 hover:text-white transition-colors"
          aria-label="Mở thông báo"
        >
          <Bell size={20} />
          <span className="absolute top-0 right-0 w-2 h-2 bg-legal-danger rounded-full border-2 border-legal-navy" />
        </button>

        {/* Demo persona switcher */}
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setDropdownOpen(p => !p)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-all hover:scale-105 ${
              currentPersona
                ? `${currentPersona.bg} ${currentPersona.border} ${currentPersona.color}`
                : 'bg-white/5 border-white/10 text-slate-300'
            }`}
            title="Chuyển hồ sơ demo"
          >
            <Users size={13} />
            <span className="hidden sm:inline">
              {currentPersona ? currentPersona.label : currentUserId}
            </span>
            <ChevronDown size={11} className={`transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 top-full mt-2 w-64 bg-legal-navy border border-white/10 rounded-xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150 z-50">
              <div className="px-3 py-2 border-b border-white/8">
                <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Demo hồ sơ người dùng</p>
              </div>
              {DEMO_PERSONAS.map(p => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handlePersonaSwitch(p)}
                  className="w-full flex items-start gap-3 px-3 py-2.5 hover:bg-white/5 transition-colors text-left"
                >
                  <div className={`w-8 h-8 rounded-lg flex-none flex items-center justify-center ${p.bg} border ${p.border} mt-0.5`}>
                    <User size={14} className={p.color} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-semibold ${p.color}`}>{p.label}</p>
                    <p className="text-[10px] text-slate-500 truncate">{p.description}</p>
                    <p className="text-[10px] text-slate-600 font-mono">{p.id}</p>
                  </div>
                  {p.id === currentUserId && (
                    <Check size={13} className="text-legal-gold flex-none mt-1" />
                  )}
                </button>
              ))}
              <div className="px-3 py-2 border-t border-white/8">
                <p className="text-[10px] text-slate-600">Chuyển hồ sơ để xem gợi ý được cá nhân hóa khác nhau</p>
              </div>
            </div>
          )}
        </div>

        {/* User pill */}
        <div className="flex items-center gap-3 pl-4 border-l border-legal-border">
          <div className="text-right">
            <p className="text-xs font-bold text-white leading-none">{currentUserId}</p>
            <p className="text-[10px] text-legal-gold font-medium mt-1 uppercase tracking-tighter">Pro Member</p>
          </div>
          <div className="w-8 h-8 rounded-full bg-legal-gold/20 flex items-center justify-center text-legal-gold border border-legal-gold/30">
            <User size={18} />
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <PersonaSwitchToast label={toast.label} onDone={() => setToast(null)} />
      )}
    </header>
  );
}
