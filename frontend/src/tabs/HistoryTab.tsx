/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import { 
  Search, 
  ChevronRight, 
  RefreshCw, 
  Copy, 
  MessageSquare,
  Filter,
  History
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { Session } from '../types';

export function HistoryTab() {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(mockSessions[0].id);

  const selectedSession = mockSessions.find(s => s.id === selectedSessionId);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex h-full overflow-hidden"
    >
      {/* Session List Sidebar */}
      <div className="w-[320px] border-r border-legal-border flex flex-col bg-white">
        <div className="p-4 space-y-4 shadow-sm relative z-10 bg-white">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input 
              type="text" 
              placeholder="Tìm trong lịch sử..." 
              className="w-full bg-slate-50 border-none rounded-lg pl-10 pr-4 py-2 text-xs focus:ring-2 focus:ring-legal-primary"
            />
          </div>
          <div className="flex items-center justify-between">
            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Lịch sử hội thoại</h3>
            <button className="p-1.5 text-slate-400 hover:text-legal-primary hover:bg-slate-50 rounded"><Filter size={14} /></button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto overflow-x-hidden p-2 space-y-1">
          {mockSessions.map((session) => (
            <div 
              key={session.id}
              onClick={() => setSelectedSessionId(session.id)}
              className={`p-4 rounded-xl cursor-pointer transition-all border-l-4 group ${
                selectedSessionId === session.id 
                  ? 'bg-blue-50 border-legal-primary shadow-sm' 
                  : 'bg-white border-transparent hover:bg-slate-50'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-slate-400 font-medium">{session.date}</span>
                <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                  session.domain === 'Đất đai' ? 'bg-blue-100 text-blue-700' : 'bg-violet-100 text-violet-700'
                }`}>
                  {session.domain}
                </span>
              </div>
              <p className={`text-xs line-clamp-1 font-medium ${selectedSessionId === session.id ? 'text-legal-primary' : 'text-slate-700'}`}>
                {session.firstQuery}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Session Detail */}
      <div className="flex-1 flex flex-col bg-slate-50 overflow-hidden">
        {selectedSession ? (
          <div className="flex flex-col h-full">
            {/* Thread Header */}
            <div className="p-6 bg-white border-b border-legal-border flex items-center justify-between shrink-0">
               <div className="space-y-1 min-w-0 flex-1 mr-4">
                 <div className="flex items-center gap-2 mb-1">
                   <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                     selectedSession.domain === 'Đất đai' ? 'bg-blue-100 text-blue-700' : 'bg-violet-100 text-violet-700'
                   }`}>
                     {selectedSession.domain}
                   </span>
                   <span className="text-[10px] text-slate-400 font-mono">ID: {selectedSessionId}</span>
                 </div>
                 <h2 className="font-bold text-slate-800 text-lg line-clamp-1 leading-tight" title={selectedSession.firstQuery}>
                   {selectedSession.firstQuery}
                 </h2>
               </div>
               <button className="flex items-center gap-2 px-4 py-2 bg-legal-primary text-white rounded-lg text-xs font-bold shadow-md hover:bg-blue-800 transition-all shrink-0">
                 <RefreshCw size={14} />
                 Phân tích lại
               </button>
            </div>

            {/* Conversation Thread Replay */}
            <div className="flex-1 overflow-y-auto p-8 space-y-10">
              {selectedSession.messages.map((m, idx) => (
                <div key={m.id} className="space-y-4">
                  {/* Stages Timeline for the first AI response */}
                  {m.role === 'assistant' && idx === 1 && (
                     <div className="flex items-center gap-4 text-[9px] font-mono text-slate-400 px-4">
                        <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Stage 1: 8ms</span>
                        <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Stage 3: 142ms</span>
                        <span className="flex items-center gap-1"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Stage 5: 2.1s</span>
                     </div>
                  )}
                  
                  <div className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-2xl p-5 shadow-sm border ${
                      m.role === 'user' 
                        ? 'bg-legal-primary text-white rounded-tr-none' 
                        : 'bg-white text-slate-700 border-legal-border rounded-tl-none border-l-4 border-l-legal-accent'
                    }`}>
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{m.content}</p>
                      {m.role === 'assistant' && (
                        <div className="flex items-center justify-end mt-4 gap-2 border-t border-slate-50 pt-2">
                           <button className="p-1 px-2 text-[10px] text-slate-400 hover:text-legal-primary flex items-center gap-1"><Copy size={12} /> Sao chép</button>
                           <button className="p-1 px-2 text-[10px] text-slate-400 hover:text-legal-primary flex items-center gap-1"><MessageSquare size={12} /> Trích dẫn</button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-12 space-y-4">
            <div className="w-24 h-24 bg-slate-200 rounded-full flex items-center justify-center text-slate-400">
               <History size={48} />
            </div>
            <h2 className="text-xl font-bold text-slate-400">Chọn một phiên để xem nội dung</h2>
          </div>
        )}
      </div>
    </motion.div>
  );
}

const mockSessions: Session[] = [
  {
    id: 'LX-1102',
    date: '10:42 AM, Hôm qua',
    firstQuery: 'Tranh chấp ranh giới đất ở với hàng xóm tại Quận 2',
    domain: 'Đất đai',
    messages: [
      { id: '1', role: 'user', content: 'Chào LexAI, tôi muốn hỏi về thủ tục giải quyết tranh chấp đất đai khi hàng xóm lấn chiếm ranh giới đã được cấp sổ đỏ.' },
      { id: '2', role: 'assistant', content: 'Chào bạn, theo quy định của Luật Đất đai 2024, bạn cần thực hiện các bước sau:\n1. Gửi đơn yêu cầu hòa giải tại UBND phường.\n2. Nếu hòa giải không thành, bạn có quyền khởi kiện tại Tòa án nhân dân quận/huyện nơi có đất.' }
    ]
  },
  {
    id: 'LX-0982',
    date: '02:15 PM, 14/05/2024',
    firstQuery: 'Review các điều khoản bồi thường trong Hợp đồng mua bán',
    domain: 'Hợp đồng',
    messages: [
      { id: '3', role: 'user', content: 'Vui lòng kiểm tra điều 5 của hợp đồng này về mức phạt vi phạm 15%.' },
      { id: '4', role: 'assistant', content: 'Mức phạt 15% là rủi ro cao vì Luật Thương mại giới hạn ở mức 8% giá trị phần nghĩa vụ vi phạm.' }
    ]
  },
  {
    id: 'LX-0451',
    date: '09:00 AM, 12/05/2024',
    firstQuery: 'Hợp đồng lao động mẫu cho nhân viên IT',
    domain: 'Lao động',
    messages: [
      { id: '5', role: 'user', content: 'Tôi cần mẫu hợp đồng lao động có điều khoản NDA và sở hữu trí tuệ.' },
      { id: '6', role: 'assistant', content: 'Đã chuẩn bị mẫu hợp đồng lao động theo chuẩn mới nhất của Bộ LĐ-TB&XH, tích hợp phụ lục bảo mật đặc thù ngành CNTT.' }
    ]
  },
];
