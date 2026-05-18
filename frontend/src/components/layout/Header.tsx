/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { User, Bell, ChevronRight, X, Check, Edit2, LogOut, UserCircle } from 'lucide-react';
import { getUserId, setUserId } from '../../lib/api';

const routeLabels: Record<string, string> = {
  '/':           'Tổng quan',
  '/analyze':    'Phân tích tình huống',
  '/contract':   'Rà soát hợp đồng',
  '/documents':  'Tài liệu pháp lý',
  '/templates':  'Mẫu hợp đồng',
  '/risks':      'Rủi ro pháp lý',
  '/checklists': 'Danh sách tuân thủ',
  '/profile':    'Hồ sơ cá nhân',
  '/journey':    'Hành trình pháp lý',
};

export function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentLabel = routeLabels[location.pathname] || 'LexAI';

  const [userId, setUserIdState] = useState(getUserId);
  const [showMenu, setShowMenu] = useState(false);
  const [editingId, setEditingId] = useState(false);
  const [editValue, setEditValue] = useState('');
  const menuRef = useRef<HTMLDivElement>(null);
  const editRef = useRef<HTMLInputElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
        setEditingId(false);
      }
    }
    if (showMenu) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showMenu]);

  useEffect(() => {
    if (editingId) editRef.current?.focus();
  }, [editingId]);

  function handleSaveId() {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== userId) {
      setUserId(trimmed);
      setUserIdState(trimmed);
    }
    setEditingId(false);
  }

  function handleStartEdit() {
    setEditValue(userId);
    setEditingId(true);
  }

  return (
    <header className="h-16 border-b border-legal-border flex items-center justify-between px-8 bg-legal-navy/50 backdrop-blur-md sticky top-0 z-30">
      <div className="flex items-center gap-2 text-slate-400 text-sm">
        <span className="text-slate-500">LexAI</span>
        <ChevronRight size={14} className="text-slate-600" />
        <span className="text-white font-medium">{currentLabel}</span>
      </div>

      <div className="flex items-center gap-4">
        {/* Notification bell */}
        <button className="relative text-slate-400 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/5">
          <Bell size={19} />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-legal-danger rounded-full" />
        </button>

        {/* User menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => { setShowMenu(v => !v); setEditingId(false); }}
            className="flex items-center gap-3 pl-4 border-l border-legal-border hover:opacity-80 transition-opacity"
          >
            <div className="text-right hidden sm:block">
              <p className="text-xs font-bold text-white leading-none max-w-[120px] truncate">{userId}</p>
              <p className="text-[10px] text-legal-gold font-medium mt-0.5 uppercase tracking-tighter">Pro Member</p>
            </div>
            <div className="w-8 h-8 rounded-full bg-legal-gold/20 flex items-center justify-center text-legal-gold border border-legal-gold/30 shrink-0">
              <User size={17} />
            </div>
          </button>

          {showMenu && (
            <div className="absolute right-0 top-full mt-2 w-64 bg-[#0f1729] border border-white/10 rounded-2xl shadow-2xl shadow-black/50 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              {/* User info header */}
              <div className="px-4 py-3 bg-white/5 border-b border-white/10">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-legal-gold/10 border border-legal-gold/20 flex items-center justify-center text-legal-gold">
                    <UserCircle size={22} />
                  </div>
                  <div className="flex-1 min-w-0">
                    {editingId ? (
                      <div className="flex items-center gap-1">
                        <input
                          ref={editRef}
                          value={editValue}
                          onChange={e => setEditValue(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') handleSaveId(); if (e.key === 'Escape') setEditingId(false); }}
                          className="flex-1 text-xs bg-white/10 border border-legal-gold/40 rounded px-2 py-1 text-white focus:outline-none w-full"
                        />
                        <button onClick={handleSaveId} className="text-emerald-400 hover:text-emerald-300 p-0.5"><Check size={13} /></button>
                        <button onClick={() => setEditingId(false)} className="text-slate-500 hover:text-slate-300 p-0.5"><X size={13} /></button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 group">
                        <p className="text-sm font-bold text-white truncate flex-1">{userId}</p>
                        <button onClick={handleStartEdit} className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-white transition-all p-0.5">
                          <Edit2 size={11} />
                        </button>
                      </div>
                    )}
                    <p className="text-[10px] text-legal-gold font-semibold uppercase tracking-wide mt-0.5">Pro Member</p>
                  </div>
                </div>
              </div>

              {/* Menu items */}
              <div className="p-1.5">
                <button
                  onClick={() => { navigate('/profile'); setShowMenu(false); }}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm text-slate-300 hover:bg-white/5 hover:text-white transition-all"
                >
                  <UserCircle size={15} className="text-slate-500" />
                  Hồ sơ cá nhân
                </button>
                <div className="my-1 border-t border-white/5" />
                <button
                  onClick={() => { setUserId('demo_user_001'); setUserIdState('demo_user_001'); setShowMenu(false); }}
                  className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm text-red-400 hover:bg-red-500/10 transition-all"
                >
                  <LogOut size={15} />
                  Đặt lại ID người dùng
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
