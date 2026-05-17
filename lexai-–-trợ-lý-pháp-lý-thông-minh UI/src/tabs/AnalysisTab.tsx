/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect } from 'react';
import { 
  Paperclip, 
  Send, 
  ChevronDown, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  ExternalLink,
  MessageSquare,
  Copy,
  Bookmark,
  Scale
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { AnalysisResult, Message } from '../types';

export function AnalysisTab({ domain, onDomainChange }: { domain: string, onDomainChange: (d: string) => void }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStep, setAnalysisStep] = useState(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const steps = [
    'Nhận diện domain',
    'Tải bộ nhớ phiên',
    'Tổng hợp truy vấn',
    'Duyệt đồ thị pháp lý',
    'Suy luận AI',
    'Xếp hạng kết quả',
    'Lưu kết quả'
  ];

  useEffect(() => {
    if (isAnalyzing) {
      const interval = setInterval(() => {
        setAnalysisStep((prev) => {
          if (prev >= steps.length - 1) {
            clearInterval(interval);
            setIsAnalyzing(false);
            setResult(mockResult);
            return prev;
          }
          return prev + 1;
        });
      }, 500);
      return () => clearInterval(interval);
    }
  }, [isAnalyzing]);

  const handleSend = () => {
    if (!inputValue.trim()) return;
    const newUserMsg: Message = { id: Date.now().toString(), role: 'user', content: inputValue };
    setMessages([...messages, newUserMsg]);
    setInputValue('');
    setIsAnalyzing(true);
    setAnalysisStep(0);
    setResult(null);
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col h-full p-6 space-y-6"
    >
      {/* Input Area */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-legal-border space-y-4">
        <textarea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Mô tả tình huống pháp lý của bạn... (VD: Hàng xóm lấn 50cm đất sổ đỏ, tôi cần làm gì?)"
          className="w-full h-32 p-4 bg-slate-50 rounded-xl border-none focus:ring-2 focus:ring-legal-primary transition-all resize-none text-sm"
        />
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <ChipDropdown 
              selected={domain} 
              onSelect={onDomainChange} 
              options={['Tự động phát hiện', 'Đất đai', 'Hợp đồng', 'Lao động', 'Doanh nghiệp', 'Dân sự', 'Hình sự', 'Hành chính', 'Gia đình']} 
            />
            <ChipDropdown 
              selected="Nguyên đơn" 
              onSelect={() => {}} 
              options={['Nguyên đơn', 'Bị đơn', 'Tư vấn']} 
            />
            <button className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-full text-xs font-medium text-slate-600 hover:bg-slate-100">
              <Paperclip size={14} />
              Đính kèm
            </button>
          </div>
          <button 
            onClick={handleSend}
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-legal-primary to-legal-accent text-white rounded-full font-semibold shadow-lg hover:shadow-xl transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <span>Phân tích</span>
            <Send size={18} />
          </button>
        </div>
      </div>

      {messages.length === 0 && !isAnalyzing && !result && (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-12 space-y-6">
          <div className="w-24 h-24 bg-blue-50 text-legal-primary rounded-full flex items-center justify-center">
            <Scale size={48} />
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-bold text-slate-700">Nhập tình huống pháp lý để bắt đầu</h2>
            <p className="text-sm text-slate-400 max-w-sm">LexAI sẽ phân tích các điều luật, án lệ và đưa ra các hành động khuyến nghị cho bạn.</p>
          </div>
          <div className="flex flex-wrap justify-center gap-2">
            {[
              "Hàng xóm lấn chiếm 50cm đất sổ đỏ của tôi",
              "Công ty sa thải tôi không báo trước 45 ngày",
              "Hợp đồng mua bán nhà bị bên bán đơn phương hủy"
            ].map(q => (
              <button 
                key={q}
                onClick={() => setInputValue(q)}
                className="px-4 py-2 bg-white border border-slate-200 rounded-full text-xs font-medium text-slate-600 hover:border-legal-primary transition-all"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Analysis Pipeline */}
      {isAnalyzing && (
        <div className="py-8 space-y-6">
          <div className="flex justify-between relative px-4">
            <div className="absolute top-4 left-4 right-4 h-0.5 bg-slate-200 -z-10" />
            {steps.map((s, idx) => (
              <div key={idx} className="flex flex-col items-center gap-2 w-20 text-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                  idx < analysisStep 
                    ? 'bg-legal-success text-white' 
                    : idx === analysisStep 
                      ? 'bg-legal-primary text-white animate-pulse-glow scale-110' 
                      : 'bg-white border-2 border-slate-200 text-slate-300'
                }`}>
                  {idx < analysisStep ? <CheckCircle2 size={16} /> : <div className="w-2 h-2 rounded-full bg-current" />}
                </div>
                <span className={`text-[10px] font-medium leading-tight ${idx === analysisStep ? 'text-legal-primary' : 'text-slate-400'}`}>
                  {s}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Result Cards */}
      {result && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card A: Position Strength */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl p-6 shadow-sm border border-legal-border flex flex-col items-center text-center space-y-4"
          >
            <div className="flex items-center justify-between w-full">
              <h3 className="text-sm font-bold text-slate-700">Vị thế pháp lý</h3>
              <div className={`px-3 py-1 rounded-full text-[10px] font-bold ${
                result.status === 'Strong' ? 'bg-emerald-100 text-emerald-700' : 
                result.status === 'Average' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'
              }`}>
                {result.status === 'Strong' ? 'MẠNH' : result.status === 'Average' ? 'TRUNG BÌNH' : 'YẾU'}
              </div>
            </div>

            <div className="relative w-32 h-32">
              <svg className="w-full h-full" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" fill="none" stroke="#E2E8F0" strokeWidth="8" />
                <motion.circle 
                  cx="50" cy="50" r="40" fill="none" 
                  stroke={result.status === 'Strong' ? '#059669' : result.status === 'Average' ? '#D97706' : '#DC2626'} 
                  strokeWidth="8" 
                  strokeDasharray="251.2"
                  initial={{ strokeDashoffset: 251.2 }}
                  animate={{ strokeDashoffset: 251.2 - (251.2 * result.score) / 100 }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-slate-800">{result.score}</span>
                <span className="text-[10px] text-slate-400 font-medium font-mono">LEX_SCORE</span>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed italic">
              "{result.reasoning}"
            </p>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-[10px] font-bold">⚖ {result.domain}</span>
            </div>
          </motion.div>

          {/* Card B: Relevant Laws */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl p-6 shadow-sm border border-legal-border space-y-4"
          >
            <h3 className="text-sm font-bold text-slate-700">Điều luật áp dụng</h3>
            <div className="space-y-3">
              {result.laws.map((law) => (
                <div key={law.id} className="group p-3 bg-slate-50 rounded-xl border border-slate-100 hover:border-legal-primary transition-all cursor-pointer">
                  <div className="flex items-center justify-between mb-2">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 font-mono text-[9px] rounded font-bold uppercase tracking-tighter">
                      {law.title}
                    </span>
                    <div className="flex items-center gap-1">
                      {law.sources.map(s => (
                        <span key={s} className="text-[8px] font-mono text-slate-400 border border-slate-200 px-1 rounded">[{s}]</span>
                      ))}
                    </div>
                  </div>
                  <p className="text-xs text-slate-600 line-clamp-2 italic mb-3">"{law.content}"</p>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 bg-slate-200 h-1.5 rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${law.score * 100}%` }}
                        className="h-full bg-legal-primary" 
                      />
                    </div>
                    <span className="text-[10px] font-bold text-legal-primary">{(law.score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="hidden group-hover:flex items-center justify-end gap-2 mt-2">
                    <button className="p-1.5 text-slate-400 hover:text-legal-primary hover:bg-white rounded transition-all"><Copy size={14} /></button>
                    <button className="p-1.5 text-slate-400 hover:text-legal-primary hover:bg-white rounded transition-all"><Bookmark size={14} /></button>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Card C: Recommended Actions */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-2xl p-6 shadow-sm border border-legal-border space-y-4"
          >
            <h3 className="text-sm font-bold text-slate-700">Hành động khuyến nghị</h3>
            <div className="space-y-3">
              {result.actions.map((action, idx) => (
                <div key={action.id} className="flex items-start gap-3 p-3 bg-white border border-slate-100 rounded-xl">
                  <div className="w-6 h-6 rounded-full bg-legal-primary text-white font-bold flex items-center justify-center text-[10px] shrink-0">
                    {idx + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-xs font-bold text-slate-800 truncate">{action.title}</h4>
                    <p className="text-[11px] text-slate-500 line-clamp-1">{action.description}</p>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase shrink-0 ${
                    action.urgency === 'Immediately' ? 'bg-red-100 text-red-700' :
                    action.urgency === 'Within30Days' ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'
                  }`}>
                    {action.urgency === 'Immediately' ? 'Ngay lập tức' :
                     action.urgency === 'Within30Days' ? 'Trong 30 ngày' : 'Tùy chọn'}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Card D: Risk Warnings */}
          {result.warnings.length > 0 && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-white rounded-2xl p-6 shadow-sm border border-legal-border border-l-4 border-l-legal-danger space-y-4"
            >
              <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
                <AlertTriangle className="text-legal-danger" size={18} />
                Cảnh báo rủi ro
              </h3>
              <div className="space-y-3">
                {result.warnings.map(w => (
                  <div key={w.id} className="flex items-center justify-between gap-3">
                    <p className="text-xs text-slate-600 leading-relaxed">
                      • {w.content}
                    </p>
                    <span className="bg-red-50 text-red-700 px-2 py-0.5 rounded font-bold text-[9px] uppercase">{w.level}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Card E: Ranking Explanation */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="md:col-span-2"
          >
            <details className="group">
              <summary className="flex items-center justify-between p-4 bg-slate-100 rounded-xl cursor-pointer hover:bg-slate-200 transition-all list-none">
                <h3 className="text-xs font-bold text-slate-700">Giải thích xếp hạng của AI</h3>
                <ChevronDown size={14} className="group-open:rotate-180 transition-transform" />
              </summary>
              <div className="p-6 bg-white border border-slate-100 border-t-0 rounded-b-xl grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {result.rankingSignals.map(sig => (
                  <div key={sig.label} className="space-y-2">
                    <div className="flex items-center justify-between text-[11px] font-medium text-slate-500">
                      <span>{sig.label}</span>
                      <span>{sig.score.toFixed(2)}</span>
                    </div>
                    <div className="bg-slate-100 h-2 rounded-full overflow-hidden">
                      <div className="h-full bg-legal-accent" style={{ width: `${sig.value * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </details>
          </motion.div>
        </div>
      )}

      {/* Chat Thread */}
      <div className="space-y-6 pt-12 pb-32">
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-2xl p-4 shadow-sm border ${
              m.role === 'user' 
                ? 'bg-legal-primary text-white rounded-tr-none' 
                : 'bg-white text-slate-700 border-legal-border rounded-tl-none border-l-4 border-l-legal-accent'
            }`}>
              {m.role === 'assistant' && (
                <div className="flex items-center justify-between mb-2">
                  <span className="px-2 py-0.5 bg-violet-100 text-violet-700 rounded text-[9px] font-bold">⚖ {m.domain || 'Pháp lý'}</span>
                  <span className="text-[8px] text-slate-400 font-mono">Trace ID: {m.traceId || 'TX-8291'}</span>
                </div>
              )}
              <p className="text-sm leading-relaxed">{m.content}</p>
              {m.role === 'assistant' && (
                <div className="flex items-center justify-end mt-2">
                  <button className="p-1 px-2 text-[10px] text-slate-400 hover:text-legal-primary rounded flex items-center gap-1">
                    <Copy size={12} />
                    Sao chép
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {/* Pinned Input Area */}
      <div className="fixed bottom-0 left-[280px] right-[360px] p-6 hidden md:block bg-gradient-to-t from-legal-bg via-legal-bg to-transparent">
        <div className="max-w-4xl mx-auto bg-white rounded-full shadow-2xl border border-legal-border p-2 pr-4 flex items-center gap-3">
          <button className="p-2 text-slate-400 hover:text-legal-primary rounded-full hover:bg-slate-50">
            <Paperclip size={20} />
          </button>
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Đặt câu hỏi tiếp theo cho LexAI..."
            className="flex-1 bg-transparent border-none focus:ring-0 text-sm"
          />
          <button 
            onClick={handleSend}
            className="w-10 h-10 bg-legal-primary text-white rounded-full flex items-center justify-center hover:scale-105 active:scale-95 transition-all shadow-md"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

function ChipDropdown({ selected, onSelect, options }: { selected: string; onSelect: (val: string) => void; options: string[] }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-full text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors"
      >
        <span>{selected}</span>
        <ChevronDown size={14} className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-48 bg-white rounded-xl shadow-xl border border-slate-100 py-2 z-50">
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => {
                onSelect(opt);
                setIsOpen(false);
              }}
              className="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 font-medium text-slate-600"
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const mockResult: AnalysisResult = {
  status: 'Strong',
  score: 78,
  reasoning: 'Quyền sử dụng đất của bạn được bảo hộ mạnh mẽ bởi Luật Đất đai 2024. Tuy nhiên, thủ tục hòa giải tại địa phương là bắt buộc trước khi khởi kiện.',
  domain: 'Đất đai',
  laws: [
    {
      id: '1',
      title: 'Điều 166 Luật Đất đai 2024',
      content: 'Người sử dụng đất có quyền được Nhà nước bảo hộ khi người khác xâm phạm quyền, lợi ích hợp pháp về đất đai của mình.',
      score: 0.91,
      sources: ['vector', 'graph']
    },
    {
      id: '2',
      title: 'Điều 202 Luật Đất đai 2024',
      content: 'Tranh chấp đất đai mà các bên tranh chấp không hòa giải được thì gửi đơn đến UBND cấp xã nơi có đất tranh chấp để hòa giải.',
      score: 0.84,
      sources: ['vector', 'bm25']
    },
    {
      id: '3',
      title: 'Điều 176 BLTTDS 2015',
      content: 'Cơ quan, tổ chức, cá nhân có quyền tự mình hoặc thông qua người đại diện hợp pháp khởi kiện vụ án tại Tòa án có thẩm quyền.',
      score: 0.71,
      sources: ['bm25']
    }
  ],
  actions: [
    {
      id: 'a1',
      title: 'Ghi nhận hiện trạng',
      description: 'Chụp ảnh, đo đạc, lập biên bản có xác nhận của nhân chứng.',
      urgency: 'Immediately'
    },
    {
      id: 'a2',
      title: 'Hòa giải tại UBND xã/phường',
      description: 'Bắt buộc trước khi khởi kiện theo quy định tại Điều 202.',
      urgency: 'Within30Days'
    },
    {
      id: 'a3',
      title: 'Khởi kiện TAND',
      description: 'Nếu hòa giải thất bại, nộp đơn khởi kiện lên Tòa án nhân dân.',
      urgency: 'Optional'
    }
  ],
  warnings: [
    {
      id: 'w1',
      content: 'Thời hiệu khiếu nại đất đai là 30 ngày kể từ khi nhận quyết định.',
      level: 'High'
    }
  ],
  rankingSignals: [
    { label: 'Ngữ nghĩa', score: 0.35, value: 0.8 },
    { label: 'Đồ thị pháp lý', score: 0.20, value: 0.6 },
    { label: 'Thói quen', score: 0.15, value: 0.4 },
    { label: 'Độ mới', score: 0.15, value: 0.3 },
    { label: 'Phổ biến', score: 0.10, value: 0.2 },
    { label: 'Được lưu', score: 0.05, value: 0.1 }
  ]
};
