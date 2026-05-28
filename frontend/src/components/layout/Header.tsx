/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { useLocation } from 'react-router-dom';
import { User, Bell, ChevronRight } from 'lucide-react';
import { USER_ID } from '../../lib/api';

const routeLabels: Record<string, string> = {
  '/': 'Tổng quan',
  '/analyze': 'Phân tích tình huống',
  '/documents': 'Tài liệu pháp lý',
  '/templates': 'Mẫu hợp đồng',
  '/risks': 'Rủi ro pháp lý',
  '/checklists': 'Danh sách tuân thủ',
  '/profile': 'Hồ sơ cá nhân',
};

export function Header() {
  const location = useLocation();
  const currentLabel = routeLabels[location.pathname] || 'LexAI';

  return (
    <header className="h-16 border-b border-legal-border flex items-center justify-between px-8 bg-legal-navy/50 backdrop-blur-md sticky top-0 z-30">
      <div className="flex items-center gap-2 text-slate-400 text-sm">
        <span>LexAI</span>
        <ChevronRight size={14} />
        <span className="text-white font-medium">{currentLabel}</span>
      </div>

      <div className="flex items-center gap-6">
        <button
          type="button"
          onClick={() => window.alert('Chưa có thông báo mới. LexAI sẽ hiển thị nhắc việc và cập nhật hồ sơ tại đây.')}
          className="relative text-slate-400 hover:text-white transition-colors"
          aria-label="Mở thông báo"
        >
          <Bell size={20} />
          <span className="absolute top-0 right-0 w-2 h-2 bg-legal-danger rounded-full border-2 border-legal-navy" />
        </button>
        
        <div className="flex items-center gap-3 pl-6 border-l border-legal-border">
          <div className="text-right">
            <p className="text-xs font-bold text-white leading-none">{USER_ID}</p>
            <p className="text-[10px] text-legal-gold font-medium mt-1 uppercase tracking-tighter">Pro Member</p>
          </div>
          <div className="w-8 h-8 rounded-full bg-legal-gold/20 flex items-center justify-center text-legal-gold border border-legal-gold/30">
            <User size={18} />
          </div>
        </div>
      </div>
    </header>
  );
}
