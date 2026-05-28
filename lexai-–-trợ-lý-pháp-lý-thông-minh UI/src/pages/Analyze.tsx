/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Search,
  ChevronRight,
  Info,
  AlertTriangle,
  Scale,
  CheckCircle2,
  ChevronDown,
  Download,
  Save,
  Clock,
  Loader2,
  Send,
  Zap,
  Wrench,
  User,
  History,
  Paperclip,
  X as XIcon,
  BrainCircuit,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { apiFetch, AnalysisResponse, LAW_TYPE_LABELS, RecommendedAction, RiskWarning, uploadEvidence, logInteraction, getTrace, ReasoningTrace } from '../lib/api';
import { LawTypeBadge, InteractionButtons } from '../components/ui/Shared';
import { StagePipeline } from '../components/ui/StagePipeline';
import { cn } from '../lib/api';

interface ChatTurn {
  role: 'user' | 'assistant';
  content?: string;
  result?: AnalysisResponse;
  situation?: string;
}

// ---------------------------------------------------------------------------
// Chitchat helpers (frontend routing — no API call for greetings)
// ---------------------------------------------------------------------------

const _CHITCHAT_STARTERS = [
  'chào', 'hello', 'hi', 'xin chào', 'hey', 'alo',
  'cảm ơn', 'cam on', 'thanks', 'thank you',
  'bạn là ai', 'bạn là gì', 'mày là ai',
  'ok', 'oke', 'okay', 'được rồi', 'tốt',
  'xin lỗi', 'sorry',
];

const _LEGAL_KW = [
  'luật', 'điều', 'khoản', 'hợp đồng', 'đất', 'tòa', 'kiện',
  'vi phạm', 'quyền', 'nghĩa vụ', 'tranh chấp', 'bồi thường',
  'lao động', 'sa thải', 'nợ', 'tiền', 'thuê', 'mua', 'bán',
  'thừa kế', 'di chúc', 'ly hôn', 'công ty', 'cổ đông',
];

function _isChitchat(text: string): boolean {
  const t = text.trim().toLowerCase();
  if (t.length > 80) return false;
  if (_LEGAL_KW.some(kw => t.includes(kw))) return false;
  return _CHITCHAT_STARTERS.some(p => t === p || t.startsWith(p + ' ') || t.startsWith(p + '!') || t.startsWith(p + ','));
}

function _chitchatReply(text: string): string {
  const t = text.trim().toLowerCase();
  if (_LEGAL_KW.some(kw => t.includes(kw))) return '';
  if (t.includes('cảm ơn') || t.includes('cam on') || t.includes('thanks')) {
    return 'Không có gì! Nếu bạn có câu hỏi pháp lý, tôi luôn sẵn sàng hỗ trợ.';
  }
  if (t.includes('là ai') || t.includes('là gì') || t.includes('mày là')) {
    return 'Tôi là LexAI — trợ lý pháp lý AI chuyên về luật Việt Nam. Tôi có thể giúp phân tích tình huống, trích dẫn điều luật và đề xuất hành động trong các lĩnh vực: đất đai, hợp đồng, lao động, doanh nghiệp, dân sự, hình sự và hành chính.';
  }
  if (t.includes('xin lỗi') || t.includes('sorry')) {
    return 'Không sao! Bạn cần tôi giúp gì về pháp lý không?';
  }
  return 'Xin chào! Tôi là LexAI, trợ lý pháp lý AI. Bạn hãy mô tả tình huống pháp lý — tôi sẽ phân tích quyền lợi, trích dẫn điều luật và đề xuất các bước thực hiện cụ thể.';
}

// ---------------------------------------------------------------------------

const stages_list = [
  { id: 1, name: 'Query Planner' },
  { id: 2, name: 'Session Memory' },
  { id: 3, name: 'Retrieval Fusion' },
  { id: 4, name: 'Graph RAG' },
  { id: 5, name: 'LLM Reasoning' },
  { id: 6, name: 'Ranker' },
  { id: 7, name: 'Persist' },
];

interface ChatInputProps {
  onAnalyze: (text: string) => void;
  isAnalyzing: boolean;
  evidenceUploading: boolean;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  handleFileAttach: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

function ChatInput({ onAnalyze, isAnalyzing, evidenceUploading, fileInputRef, handleFileAttach }: ChatInputProps) {
  const [text, setText] = useState('');

  const handleSubmit = () => {
    if (!text.trim() || isAnalyzing) return;
    onAnalyze(text);
    setText('');
  };

  return (
    <div className="relative group">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
          }
        }}
        placeholder="Nhập câu hỏi hoặc tình huống pháp lý..."
        className="w-full bg-white/5 border border-white/10 rounded-2xl p-4 pr-28 text-sm text-white placeholder-slate-500 outline-none focus:border-legal-gold/50 focus:bg-white/[0.08] transition-all resize-none min-h-[60px]"
        rows={2}
      />
      <div className="absolute right-4 bottom-4 flex items-center gap-2">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isAnalyzing || evidenceUploading}
          title="Đính kèm tài liệu bổ sung"
          className="w-9 h-9 text-slate-500 hover:text-legal-gold hover:bg-white/5 rounded-xl flex items-center justify-center disabled:opacity-40 transition-all"
        >
          {evidenceUploading ? <Loader2 size={16} className="animate-spin" /> : <Paperclip size={16} />}
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isAnalyzing || !text.trim()}
          className="w-10 h-10 bg-legal-gold text-legal-navy rounded-xl flex items-center justify-center shadow-lg shadow-legal-gold/20 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:grayscale transition-all"
        >
          <Send size={20} />
        </button>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.doc,.txt"
        className="hidden"
        onChange={handleFileAttach}
      />
    </div>
  );
}

export function Analyze() {
  const [activeTab, setActiveTab] = useState<'chat' | 'history'>('chat');
  const [userRole, setUserRole] = useState('nguyen_don');
  const [lawType, setLawType] = useState('all');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [history, setHistory] = useState<ChatTurn[]>([]);
  const [analyzeError, setAnalyzeError] = useState('');
  const [evidenceChip, setEvidenceChip] = useState<{ filename: string; evidenceId: string } | null>(null);
  const [evidenceUploading, setEvidenceUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Sessions persisted in localStorage
  const SESSION_STORAGE_KEY = 'lexai_sessions';
  function loadStoredSessions() {
    try {
      return JSON.parse(localStorage.getItem(SESSION_STORAGE_KEY) || '[]');
    } catch { return []; }
  }
  const [sessionHistory, setSessionHistory] = useState<Array<{
    id: string; title: string; domain: string; date: string; turns: ChatTurn[];
  }>>(loadStoredSessions);

  const [selectedSession, setSelectedSession] = useState<typeof sessionHistory[0] | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history, isAnalyzing, activeTab, selectedSession]);

  const handleAnalyze = async (text: string) => {
    if (!text.trim()) return;

    const currentSituation = text;
    const userMessage: ChatTurn = { role: 'user', content: currentSituation };
    setHistory(prev => [...prev, userMessage]);

    // Greetings / small-talk — respond locally without calling the API
    if (_isChitchat(currentSituation)) {
      const reply = _chitchatReply(currentSituation);
      setHistory(prev => [...prev, { role: 'assistant', content: reply }]);
      return;
    }

    setIsAnalyzing(true);
    setAnalyzeError('');
    setCurrentStage(1);
    
    // Simulate stage progress
    const stageInterval = setInterval(() => {
      setCurrentStage(prev => (prev < 6 ? prev + 1 : prev));
    }, 1200);

    try {
      const data = await apiFetch<AnalysisResponse>('/intelligence/analyze', {
        method: 'POST',
        body: JSON.stringify({ 
          situation: currentSituation, 
          user_role: userRole, 
          law_type: lawType === 'all' ? null : lawType,
          session_id: sessionId,
          top_k: 8
        })
      });
      clearInterval(stageInterval);
      setCurrentStage(7);
      setSessionId(data.session_id);
      logInteraction({ action_type: 'situation_analysis', context: { law_type: data.domain, situation_snippet: currentSituation.slice(0, 200) } });

      const newTurns: ChatTurn[] = [userMessage, { role: 'assistant', result: data }];
      setHistory(prev => [...prev, { role: 'assistant', result: data }]);
      setIsAnalyzing(false);
      setCurrentStage(0);

      // Persist session to localStorage
      const newSession = {
        id: data.session_id || `sess_${Date.now()}`,
        title: currentSituation.length > 50 ? currentSituation.slice(0, 50) + '…' : currentSituation,
        domain: data.domain || 'general',
        date: new Date().toLocaleDateString('vi-VN'),
        turns: newTurns,
      };
      setSessionHistory(prev => {
        const updated = [newSession, ...prev.filter(s => s.id !== newSession.id)].slice(0, 20);
        localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(updated));
        return updated;
      });
    } catch (e: any) {
      setAnalyzeError(e.message || 'Phân tích thất bại. Vui lòng thử lại.');
      setIsAnalyzing(false);
      setCurrentStage(0);
    }
  };

  const handleFileAttach = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!sessionId) {
      setAnalyzeError('Vui lòng gửi ít nhất một câu hỏi trước khi đính kèm tài liệu.');
      return;
    }
    setEvidenceUploading(true);
    try {
      const result = await uploadEvidence(sessionId, file);
      setEvidenceChip({ filename: result.filename, evidenceId: result.evidence_id });
    } catch (err: any) {
      setAnalyzeError(err.message || 'Không thể tải tài liệu lên.');
    } finally {
      setEvidenceUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] relative overflow-hidden">
      {/* TABS */}
      <div className="flex bg-legal-navy/30 border-b border-legal-border px-8">
        <button 
          onClick={() => setActiveTab('chat')}
          className={cn(
            "pb-3 pt-4 px-4 text-xs font-bold uppercase tracking-widest transition-all relative",
            activeTab === 'chat' ? "text-legal-gold" : "text-slate-500 hover:text-slate-300"
          )}
        >
          <div className="flex items-center gap-2">
            <Zap size={14} className={activeTab === 'chat' ? "text-legal-gold" : ""} />
            Hội thoại mới
          </div>
          {activeTab === 'chat' && <div className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-legal-gold" />}
        </button>
        <button 
          onClick={() => setActiveTab('history')}
          className={cn(
            "pb-3 pt-4 px-4 text-xs font-bold uppercase tracking-widest transition-all relative",
            activeTab === 'history' ? "text-legal-gold" : "text-slate-500 hover:text-slate-300"
          )}
        >
          <div className="flex items-center gap-2">
            <History size={14} className={activeTab === 'history' ? "text-legal-gold" : ""} />
            Lịch sử
          </div>
          {activeTab === 'history' && <div className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-legal-gold" />}
        </button>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* HISTORY SIDEBAR (Only in History Tab) */}
        {activeTab === 'history' && (
          <div className="w-80 border-r border-legal-border bg-legal-navy/10 flex flex-col overflow-hidden">
            <div className="p-4 border-b border-white/5">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
                <input 
                  type="text" 
                  placeholder="Tìm lịch sử..." 
                  className="w-full bg-white/5 border border-white/10 rounded-lg py-2 pl-9 pr-4 text-xs text-slate-300 outline-none focus:border-legal-gold/30"
                />
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {sessionHistory.map(session => (
                <button 
                  key={session.id}
                  onClick={() => setSelectedSession(session)}
                  className={cn(
                    "w-full text-left p-3 rounded-xl transition-all group",
                    selectedSession?.id === session.id 
                      ? "bg-legal-gold/10 border border-legal-gold/20" 
                      : "hover:bg-white/5 border border-transparent"
                  )}
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs font-bold text-white group-hover:text-legal-gold transition-colors truncate pr-2">{session.title}</span>
                    <span className="text-[9px] text-slate-500 shrink-0">{session.date}</span>
                  </div>
                  <LawTypeBadge type={session.domain} />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* CHAT/HISTORY CONTENT */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          {/* HEADER FOR SELECTED SESSION (PROMINENT INITIAL QUERY & DOMAIN) */}
          {activeTab === 'history' && selectedSession && (
            <div className="p-6 bg-legal-gold/5 border-b border-legal-gold/20 animate-in fade-in slide-in-from-top-4 duration-500">
              <div className="max-w-4xl mx-auto space-y-3">
                <div className="flex items-center gap-3">
                  <div className="px-2 py-0.5 bg-legal-gold text-legal-navy rounded text-[10px] font-bold uppercase tracking-widest">
                    {LAW_TYPE_LABELS[selectedSession.domain] || selectedSession.domain}
                  </div>
                  <div className="h-px flex-1 bg-legal-gold/20" />
                  <span className="text-[10px] font-mono text-slate-500">ID: {selectedSession.id}</span>
                </div>
                <h3 className="text-xl font-bold text-white leading-tight">
                  {selectedSession.turns[0].content}
                </h3>
              </div>
            </div>
          )}

          {/* CHAT MESSAGE LIST */}
          <div 
            ref={scrollRef}
            className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 scroll-smooth"
          >
            {activeTab === 'chat' ? (
              <>
                {history.length === 0 && !isAnalyzing && (
                  <div className="h-full flex flex-col items-center justify-center text-center space-y-6 opacity-40">
                    <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center text-slate-600">
                       <Scale size={40} />
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-lg font-bold text-slate-400">Trình phân tích LexAI</h3>
                      <p className="text-sm text-slate-500 max-w-sm">Mô tả tình huống pháp lý của bạn để gpt-4o-mini bắt đầu phân tích và đưa ra giải pháp.</p>
                    </div>
                  </div>
                )}

                {history.map((turn, idx) => (
                  <div key={idx} className={cn("flex flex-col", turn.role === 'user' ? "items-end" : "items-start")}>
                    {turn.role === 'user' ? (
                      <div className="max-w-[80%] bg-legal-navy/80 border border-white/10 p-4 rounded-2xl rounded-tr-none text-slate-200 text-sm shadow-xl">
                        {turn.content}
                      </div>
                    ) : turn.result ? (
                      <AIResponseCard 
                        result={turn.result} 
                        onSelectQuestion={handleAnalyze} 
                        userSituation={idx > 0 ? history[idx - 1]?.content : ''} 
                      />
                    ) : turn.content ? (
                      <AssistantBubble content={turn.content} />
                    ) : null}
                  </div>
                ))}

                {analyzeError && (
                  <div className="flex flex-col items-start">
                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start gap-3 max-w-2xl">
                      <AlertTriangle size={16} className="text-red-400 shrink-0 mt-0.5" />
                      <p className="text-sm text-red-400">{analyzeError}</p>
                    </div>
                  </div>
                )}

                {isAnalyzing && (
                  <div className="flex flex-col items-start space-y-4">
                    <div className="glass-card p-6 w-full max-w-2xl border-l-4 border-l-legal-gold animate-pulse">
                       <div className="flex items-center gap-2 mb-4">
                         <Loader2 className="animate-spin text-legal-gold" size={18} />
                         <span className="text-xs font-bold text-legal-gold uppercase tracking-wider">LexAI đang xử lý...</span>
                       </div>
                       <StagePipeline currentStage={currentStage} stages={stages_list} />
                    </div>
                  </div>
                )}
              </>
            ) : (
              /* HISTORY VIEW */
              <div className="space-y-8">
                {selectedSession ? (
                  selectedSession.turns.map((turn, idx) => (
                    <div key={idx} className={cn("flex flex-col", turn.role === 'user' ? "items-end" : "items-start")}>
                      {turn.role === 'user' ? (
                        <div className="max-w-[80%] bg-legal-navy/80 border border-white/10 p-4 rounded-2xl rounded-tr-none text-slate-200 text-sm shadow-xl">
                          {turn.content}
                        </div>
                      ) : turn.result ? (
                        <AIResponseCard 
                          result={turn.result} 
                          onSelectQuestion={handleAnalyze} 
                          userSituation={idx > 0 ? selectedSession.turns[idx - 1]?.content : ''} 
                        />
                      ) : turn.content ? (
                        <AssistantBubble content={turn.content} />
                      ) : null}
                    </div>
                  ))
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-center space-y-6 opacity-30 py-20">
                    <History size={60} className="text-slate-600" />
                    <p className="text-sm font-bold text-slate-500">Chọn một phiên làm việc để xem lại</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* INPUT AREA (Only in Chat Tab) */}
          {activeTab === 'chat' && (
            <div className="p-4 md:p-6 bg-legal-navy/40 backdrop-blur-xl border-t border-legal-border">
        <div className="max-w-4xl mx-auto space-y-4">
          <div className="flex flex-wrap items-center gap-3">
             <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 overflow-hidden">
                <User size={14} className="text-legal-gold" />
                <select 
                  value={userRole}
                  onChange={(e) => setUserRole(e.target.value)}
                  className="bg-transparent text-[10px] font-bold text-white uppercase tracking-wider outline-none cursor-pointer"
                >
                  <option value="nguyen_don">Nguyên đơn</option>
                  <option value="bi_don">Bị đơn</option>
                  <option value="tu_van">Tư vấn</option>
                </select>
             </div>
             <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 overflow-hidden">
                <History size={14} className="text-slate-500" />
                <select 
                  value={lawType}
                  onChange={(e) => setLawType(e.target.value)}
                  className="bg-transparent text-[10px] font-bold text-slate-400 border-none outline-none cursor-pointer"
                >
                  <option value="all">Tất cả lĩnh vực</option>
                  {Object.entries(LAW_TYPE_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
             </div>
          </div>

          {/* Evidence chip */}
          {evidenceChip && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-legal-gold/10 border border-legal-gold/20 rounded-xl w-fit">
              <Paperclip size={12} className="text-legal-gold" />
              <span className="text-[11px] text-legal-gold font-medium">{evidenceChip.filename}</span>
              <button onClick={() => setEvidenceChip(null)} className="text-slate-500 hover:text-white ml-1">
                <XIcon size={12} />
              </button>
            </div>
          )}

          <ChatInput
            onAnalyze={handleAnalyze}
            isAnalyzing={isAnalyzing}
            evidenceUploading={evidenceUploading}
            fileInputRef={fileInputRef}
            handleFileAttach={handleFileAttach}
          />
        </div>
      </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// TracePanel — reasoning trace accordion (Phase 14)
// ---------------------------------------------------------------------------

function TracePanel({ traceId }: { traceId: string }) {
  const [trace, setTrace] = useState<ReasoningTrace | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleToggle = async () => {
    const next = !open;
    setOpen(next);
    if (next && !trace && !loading) {
      setLoading(true);
      const data = await getTrace(traceId);
      setTrace(data);
      setLoading(false);
    }
  };

  const stageColor = (s: any) => {
    if (s.error) return 'border-red-500/30 bg-red-500/5';
    if (s.warnings?.length) return 'border-yellow-500/30 bg-yellow-500/5';
    return 'border-green-500/20 bg-green-500/5';
  };

  return (
    <div className="mt-4 border-t border-white/10 pt-4">
      <button
        onClick={handleToggle}
        className="flex items-center gap-2 text-slate-500 hover:text-legal-gold transition-colors text-[11px] font-bold uppercase tracking-wider"
      >
        {loading ? <Loader2 size={13} className="animate-spin" /> : <BrainCircuit size={13} />}
        Xem lý luận AI
        <ChevronDown size={12} className={cn("transition-transform", open ? "rotate-180" : "")} />
      </button>

      {open && trace && (
        <div className="mt-3 space-y-2 animate-in fade-in duration-200">
          {trace.stages.map((s, i) => (
            <div key={i} className={`border rounded-xl p-3 ${stageColor(s)}`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold text-white uppercase tracking-wider">{s.stage_name}</span>
                <span className="text-[9px] font-mono text-slate-500">{s.duration_ms?.toFixed(0) ?? '—'}ms</span>
              </div>
              {s.output_summary && <p className="text-[11px] text-slate-400 leading-snug">{s.output_summary}</p>}
              {s.warnings?.length > 0 && (
                <p className="text-[10px] text-yellow-400 mt-1">⚠ {s.warnings.join('; ')}</p>
              )}
            </div>
          ))}
        </div>
      )}

      {open && !trace && !loading && (
        <p className="mt-2 text-[11px] text-slate-500 italic">Không tìm thấy dữ liệu lý luận.</p>
      )}
    </div>
  );
}

function AssistantBubble({ content }: { content: string }) {
  return (
    <div className="max-w-[80%] bg-legal-navy/50 border border-legal-gold/20 p-4 rounded-2xl rounded-tl-none shadow-xl animate-in fade-in slide-in-from-left-4 duration-300">
      <div className="flex items-center gap-2 mb-2">
        <Zap size={12} className="text-legal-gold" />
        <span className="text-[10px] font-bold text-legal-gold uppercase tracking-wider">LexAI</span>
      </div>
      <p className="text-sm text-slate-200 leading-relaxed">{content}</p>
    </div>
  );
}

function AIResponseCard({ result, onSelectQuestion, userSituation }: { result: AnalysisResponse; onSelectQuestion?: (text: string) => void; userSituation?: string }) {
  const navigate = useNavigate();
  const [expandedAction, setExpandedAction] = useState<number | null>(null);
  const totalMs = result.stage_timings.reduce((a, b) => a + b.duration_ms, 0);

  const MODULE_ROUTE_MAP: Record<string, { path: string; name: string }> = {
    evidence_gap: { path: '/evidence-gap', name: 'Phát hiện thiếu chứng cứ' },
    evidence: { path: '/evidence-gap', name: 'Phát hiện thiếu chứng cứ' },
    timeline: { path: '/timeline', name: 'Tiến độ & Thời hiệu' },
    contract: { path: '/contract', name: 'Rà soát hợp đồng' },
    risks: { path: '/risks', name: 'Phân tích rủi ro' },
    compliance: { path: '/compliance-radar', name: 'Compliance Radar' },
    journey: { path: '/journey', name: 'Hành trình vụ việc' },
    templates: { path: '/templates', name: 'Mẫu văn bản pháp lý' },
    similar_cases: { path: '/similar-cases', name: 'Vụ việc tương tự' },
    cases: { path: '/similar-cases', name: 'Vụ việc tương tự' },
    law_search: { path: '/law-search', name: 'Tra cứu Luật' },
    laws: { path: '/law-search', name: 'Tra cứu Luật' },
    checklists: { path: '/checklists', name: 'Liên kết tuân thủ' },
    checklist: { path: '/checklists', name: 'Liên kết tuân thủ' },
    actions: { path: '/actions', name: 'Hành động khuyến nghị' },
    action_plan: { path: '/actions', name: 'Hành động khuyến nghị' },
  };

  const nbas = result.next_best_actions || [];
  const firstAction = nbas.find(n => (n.journey_steps && n.journey_steps.length > 0) || (n.next_questions && n.next_questions.length > 0));
  
  const journeySteps = firstAction?.journey_steps || [];
  const nextQuestions = firstAction?.next_questions || [];
  const detectedGoals = firstAction?.detected_goals || [];
  const userPosition = firstAction?.user_position || '';

  return (
    <div className="w-full max-w-4xl glass-card overflow-hidden border-l-4 border-l-legal-gold shadow-2xl animate-in fade-in slide-in-from-left-4 duration-500">
      {/* Header */}
      <div className="px-6 py-3 bg-white/5 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn(
            "flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase",
            result.used_llm ? "bg-legal-success/20 text-legal-success" : "bg-slate-500/20 text-slate-400"
          )}>
            <Zap size={12} fill="currentColor" />
            {result.used_llm ? "AI" : "Xác định luật"}
          </div>
          <span className="text-[10px] font-mono text-slate-500">⚡ gpt-4o-mini | {totalMs.toFixed(0)}ms</span>
        </div>
        <InteractionButtons docId={result.session_id} />
      </div>

      <div className="p-6 md:p-8 space-y-6">
        {/* Position meter + domain */}
        <div className="flex flex-col md:flex-row gap-6 items-start">
          <div className="flex flex-col items-center gap-3 shrink-0">
            <div className="relative w-20 h-20">
              <svg className="w-full h-full" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
                <circle
                  cx="50" cy="50" r="45" fill="none"
                  stroke={result.status === 'manh' ? '#059669' : result.status === 'trung_binh' ? '#f59e0b' : '#ef4444'}
                  strokeWidth="6"
                  strokeDasharray="283"
                  strokeDashoffset={283 - (283 * result.position_score) / 100}
                  strokeLinecap="round"
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-bold text-white">{result.position_score}%</span>
              </div>
            </div>
            <span className={cn(
              "px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest",
              result.status === 'manh' ? 'bg-legal-success/20 text-legal-success border border-legal-success/30' :
              result.status === 'trung_binh' ? 'bg-legal-warning/20 text-legal-warning border border-legal-warning/30' :
              'bg-legal-danger/20 text-legal-danger border border-legal-danger/30'
            )}>
              {result.status === 'manh' ? 'Vị thế Mạnh' : result.status === 'trung_binh' ? 'Vị thế Trung bình' : 'Vị thế Yếu'}
            </span>
          </div>

          <div className="flex-1 space-y-3">
            <div className="flex items-center gap-3">
              <div className="px-2 py-1 bg-white/5 border border-white/10 rounded flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-legal-gold" />
                <span className="text-[10px] font-bold text-slate-400">{LAW_TYPE_LABELS[result.domain] || result.domain}</span>
              </div>
              <span className="text-[10px] text-slate-500 font-mono">Độ tin cậy: {(result.domain_confidence * 100).toFixed(1)}%</span>
            </div>
            {result.position_reasoning && (
              <p className="text-xs text-slate-500 italic">{result.position_reasoning}</p>
            )}
          </div>
        </div>

        {/* ── Main AI Assessment ── shown prominently when LLM responded */}
        {result.full_assessment && (
          <div className="bg-legal-gold/5 border border-legal-gold/20 rounded-2xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <Zap size={14} className="text-legal-gold" />
              <span className="text-xs font-bold text-white uppercase tracking-wider">Phân tích của LexAI</span>
            </div>
            <div className="text-sm text-slate-200 leading-relaxed prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{result.full_assessment}</ReactMarkdown>
            </div>
          </div>
        )}

        {/* Pipeline timings */}
        <div className="bg-white/[0.02] border-y border-white/10 px-4 -mx-6 md:-mx-8 overflow-x-auto scrollbar-hide">
          <StagePipeline timings={result.stage_timings} />
        </div>

        {/* Laws Accordion */}
        {result.laws.length > 0 && (
          <details className="group border border-white/10 rounded-2xl overflow-hidden bg-white/[0.02]">
            <summary className="list-none flex items-center justify-between p-4 cursor-pointer hover:bg-white/5 transition-colors">
              <div className="flex items-center gap-3">
                <Scale className="text-legal-gold" size={16} />
                <span className="text-xs font-bold text-white uppercase tracking-wider">
                  Điều luật liên quan ({result.laws.length})
                </span>
              </div>
              <ChevronDown size={16} className="text-slate-500 group-open:rotate-180 transition-transform" />
            </summary>
            <div className="px-4 pb-4 space-y-2">
              {result.laws.map(law => (
                <div key={law.id} className="p-4 bg-white/5 border border-white/10 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-legal-gold uppercase">{law.law_reference || 'Điều luật'}</span>
                    <span className="text-[10px] font-mono text-slate-500">Match: {(law.relevance_score * 100).toFixed(0)}%</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed italic">"{law.content}"</p>
                </div>
              ))}
            </div>
          </details>
        )}

        {/* Recommended Actions — expandable */}
        {result.actions.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="text-legal-gold" size={16} />
              <span className="text-xs font-bold text-white uppercase tracking-wider">Hành động khuyến nghị</span>
              <span className="text-[10px] text-slate-500">(bấm để xem thêm)</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {result.actions.map((action, i) => (
                <button
                  key={i}
                  onClick={() => setExpandedAction(expandedAction === i ? null : i)}
                  className="p-4 bg-white/5 border border-white/10 rounded-2xl relative overflow-hidden text-left group hover:border-legal-gold/30 transition-all"
                >
                  <div className="absolute top-0 left-0 w-1 h-full bg-legal-gold/30 group-hover:bg-legal-gold transition-colors" />
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2 min-w-0">
                      <span className="text-[10px] font-bold text-legal-gold shrink-0 mt-0.5">#{i + 1}</span>
                      <h5 className="text-xs font-bold text-white leading-snug">{action.title}</h5>
                    </div>
                    <ChevronDown
                      size={12}
                      className={cn("text-slate-500 shrink-0 mt-1 transition-transform", expandedAction === i ? "rotate-180" : "")}
                    />
                  </div>
                  {expandedAction === i && (
                    <div className="mt-3 pt-3 border-t border-white/10 space-y-2 animate-in fade-in duration-200">
                      <p className="text-[11px] text-slate-300 leading-relaxed">{action.description}</p>
                      <span className={cn(
                        "inline-block text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider",
                        action.urgency === 'cao' ? 'bg-red-500/20 text-red-400' :
                        action.urgency === 'trung_binh' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-green-500/20 text-green-400'
                      )}>
                        {action.urgency === 'cao' ? 'Ưu tiên cao' : action.urgency === 'trung_binh' ? 'Ưu tiên trung bình' : 'Ưu tiên thấp'}
                      </span>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Dynamic Case Journey Timeline / Personalized Roadmap (Phase 2/3) */}
        {journeySteps.length > 0 && (
          <div className="space-y-4 bg-white/[0.02] border border-white/10 rounded-2xl p-5 shadow-inner">
            <div className="flex items-center gap-2">
              <Clock className="text-legal-gold" size={16} />
              <span className="text-xs font-bold text-white uppercase tracking-wider">Hành trình giải quyết vụ việc (Lộ trình đề xuất)</span>
            </div>
            
            {detectedGoals.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="text-[10px] text-slate-400 font-medium">Mục tiêu nhận diện:</span>
                {detectedGoals.map((g, i) => (
                  <span key={i} className="text-[9px] font-bold bg-legal-gold/20 text-legal-gold border border-legal-gold/30 px-2 py-0.5 rounded-full uppercase">
                    {g}
                  </span>
                ))}
                {userPosition && (
                  <>
                    <span className="text-[10px] text-slate-500">|</span>
                    <span className="text-[9px] font-bold bg-white/10 text-slate-300 border border-white/20 px-2 py-0.5 rounded-full uppercase">
                      {userPosition}
                    </span>
                  </>
                )}
              </div>
            )}

            <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-white/10">
              {journeySteps.map((step, idx) => (
                <div key={idx} className="relative group">
                  {/* Stepper Dot */}
                  <div className="absolute -left-[22px] top-1 w-3.5 h-3.5 rounded-full bg-slate-900 border-2 border-slate-700 group-hover:border-legal-gold group-hover:bg-legal-gold/20 transition-all flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-slate-500 group-hover:bg-legal-gold" />
                  </div>
                  <div className="space-y-0.5">
                    <span className="text-[9px] font-mono text-slate-500 font-bold">BƯỚC {idx + 1}</span>
                    <p className="text-xs text-slate-300 group-hover:text-white transition-colors">{step}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Next Best Actions Dynamic Recommendations Grid (Phase 2/3) */}
        {nbas.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Zap className="text-legal-gold" size={16} fill="currentColor" />
              <span className="text-xs font-bold text-white uppercase tracking-wider">Hành động Phù hợp Tiếp theo (Next Best Actions)</span>
              <span className="text-[10px] text-slate-500">(LexAI đề xuất dựa trên vụ việc)</span>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {nbas.map((nba) => {
                const rawPath = nba.action_url || '';
                let path = rawPath;
                if (rawPath === '/laws') path = '/law-search';
                if (rawPath === '/checklist') path = '/checklists';

                const routeInfo = MODULE_ROUTE_MAP[nba.module] || { path: path || '#', name: nba.title };
                return (
                  <div 
                    key={nba.action_id}
                    className="p-5 bg-white/5 border border-white/10 rounded-2xl flex flex-col justify-between hover:border-legal-gold/40 hover:bg-white/[0.08] transition-all relative overflow-hidden group"
                  >
                    {/* Top border color matching priority */}
                    <div className={cn(
                      "absolute top-0 left-0 right-0 h-1",
                      nba.priority === 'urgent' ? 'bg-red-500' :
                      nba.priority === 'high' ? 'bg-orange-500' :
                      nba.priority === 'medium' ? 'bg-yellow-500' : 'bg-slate-500'
                    )} />

                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <span className={cn(
                          "text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider",
                          nba.priority === 'urgent' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                          nba.priority === 'high' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                          nba.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
                          'bg-white/10 text-slate-400'
                        )}>
                          {nba.priority === 'urgent' ? 'Khẩn cấp' : nba.priority === 'high' ? 'Ưu tiên cao' : nba.priority === 'medium' ? 'Ưu tiên vừa' : 'Khuyến nghị'}
                        </span>
                        
                        <span className="text-[10px] font-mono font-bold text-legal-gold uppercase tracking-wider">{routeInfo.name}</span>
                      </div>

                      <h4 className="text-sm font-bold text-white leading-snug group-hover:text-legal-gold transition-colors">{nba.title}</h4>
                      <p className="text-xs text-slate-400 leading-relaxed">{nba.description}</p>
                      
                      {nba.reason && (
                        <p className="text-[11px] text-slate-500 italic bg-white/[0.02] border border-white/5 p-2 rounded-lg leading-relaxed mt-2">
                          <span className="font-bold text-legal-gold not-italic mr-1">Lý do đề xuất:</span>
                          {nba.reason}
                        </p>
                      )}
                    </div>

                    <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between">
                      <span className="text-[9px] text-slate-500 uppercase tracking-widest font-mono">Độ tự tin: {(nba.score * 100).toFixed(0)}%</span>
                      <button
                        onClick={() => {
                          logInteraction({ action_type: 'nba_click', context: { action_id: nba.action_id, target: routeInfo.path } });
                          navigate(routeInfo.path, { state: { prefill: nba.prefill, situation: userSituation || result.position_reasoning || result.full_assessment || '' } });
                        }}
                        className="px-3 py-1.5 bg-legal-gold text-legal-navy text-xs font-bold rounded-lg hover:scale-105 active:scale-95 transition-all shadow-md flex items-center gap-1"
                      >
                        Bắt đầu
                        <ChevronRight size={12} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Warnings */}
        {result.warnings.length > 0 && (
          <div className="space-y-2">
            {result.warnings.map((w, i) => (
              <div key={i} className="p-4 bg-legal-danger/10 border border-legal-danger/20 rounded-2xl flex gap-3">
                <AlertTriangle className="text-legal-danger shrink-0 mt-0.5" size={16} />
                <p className="text-xs text-slate-300">{w.content}</p>
              </div>
            ))}
          </div>
        )}

        {/* Tool calls */}
        {result.tool_calls_made && result.tool_calls_made.length > 0 && (
          <details className="group">
            <summary className="list-none cursor-pointer flex items-center justify-between text-slate-500 py-2 border-t border-white/10 hover:text-white transition-all">
              <div className="flex items-center gap-2">
                <Wrench size={14} />
                <span className="text-[10px] font-bold uppercase tracking-widest">Công cụ AI đã dùng ({result.tool_calls_made.length})</span>
              </div>
              <ChevronDown size={14} className="group-open:rotate-180 transition-transform" />
            </summary>
            <div className="pt-3 relative pl-4 space-y-3 before:absolute before:left-0 before:top-2 before:bottom-2 before:w-px before:bg-white/10">
              {result.tool_calls_made.map((tool, i) => (
                <div key={i} className="relative pl-4 before:absolute before:-left-[17px] before:top-2 before:w-2 before:h-2 before:rounded-full before:bg-legal-gold/50">
                  <h6 className="text-[10px] font-bold text-legal-gold font-mono uppercase">{tool.tool}</h6>
                  <p className="text-[10px] text-slate-500 italic mt-0.5">{tool.description}</p>
                </div>
              ))}
            </div>
          </details>
        )}

        {/* Proactive Prompts Chips */}
        {nextQuestions.length > 0 && onSelectQuestion && (
          <div className="space-y-2 pt-4 border-t border-white/10">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
              <Zap size={10} className="text-legal-gold" />
              Bạn có thể muốn hỏi tiếp theo (Proactive Prompts):
            </p>
            <div className="flex flex-wrap gap-2">
              {nextQuestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => onSelectQuestion(q)}
                  className="text-xs px-3.5 py-2 bg-white/5 hover:bg-legal-gold/10 border border-white/10 hover:border-legal-gold/30 rounded-full text-slate-300 hover:text-white transition-all text-left flex items-center gap-2 group animate-in fade-in duration-200"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-legal-gold opacity-60 group-hover:scale-125 transition-all" />
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Reasoning trace */}
        {result.trace_id && <TracePanel traceId={result.trace_id} />}
      </div>
    </div>
  );
}
