/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
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
  BookOpen,
  FileSearch,
  GitCompare,
  ShieldAlert,
  FileCheck,
  Map,
  ListChecks,
  ClipboardList,
  ThumbsUp,
  ThumbsDown,
  EyeOff,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useNavigate } from 'react-router-dom';
import { apiFetch, AnalysisResponse, LAW_TYPE_LABELS, RecommendedAction, RiskWarning, uploadEvidence, logInteraction, getTrace, ReasoningTrace, NextBestAction, loadConversationSessions, saveConversationSession } from '../lib/api';
import { LawTypeBadge, InteractionButtons } from '../components/ui/Shared';
import { StagePipeline } from '../components/ui/StagePipeline';
import { cn } from '../lib/api';
import { useSyncedSituation } from '../lib/analysisContext';

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
  'chao', 'xin chao', 'hello', 'hi', 'hey', 'alo',
  'cam on', 'thanks', 'thank you',
  'ban la ai', 'ban la gi', 'may la ai',
  'ok', 'oke', 'okay', 'duoc roi', 'tot',
  'xin loi', 'sorry',
];

const _LEGAL_KW = [
  'luat', 'dieu', 'khoan', 'hop dong', 'dat', 'toa', 'kien',
  'vi pham', 'quyen', 'nghia vu', 'tranh chap', 'boi thuong',
  'lao dong', 'sa thai', 'no', 'tien', 'thue', 'mua', 'ban',
  'thua ke', 'di chuc', 'ly hon', 'con', 'nuoi con', 'tai san',
  'cong ty', 'co dong', 'bao hiem', 'thue nha', 'lua dao', 'danh',
  'khoi kien', 'khieu nai', 'to cao', 'dat coc', 'so do',
];

function _foldText(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/\s+/g, ' ');
}

function _hasLegalSignal(text: string): boolean {
  const t = _foldText(text);
  return _LEGAL_KW.some(kw => t.includes(kw));
}

function _isChitchat(text: string): boolean {
  const t = _foldText(text);
  if (t.length > 80) return false;
  if (_hasLegalSignal(t)) return false;
  return _CHITCHAT_STARTERS.some(p => t === p || t.startsWith(p + ' ') || t.startsWith(p + '!') || t.startsWith(p + ','));
}

function _isLowSignalInput(text: string): boolean {
  const t = _foldText(text);
  if (!t) return true;
  if (_hasLegalSignal(t)) return false;
  const compact = t.replace(/[^a-z0-9]/g, '');
  const words = t.split(' ').filter(Boolean);
  if (compact.length < 4) return true;
  if (/^[a-z]+$/.test(compact) && compact.length <= 12 && words.length <= 2) return true;
  if (words.length <= 2 && compact.length <= 8) return true;
  return false;
}

function _chitchatReply(text: string): string {
  const t = _foldText(text);
  if (_hasLegalSignal(t)) return '';
  if (t.includes('cam on') || t.includes('thanks')) {
    return 'Không có gì! Nếu bạn có câu hỏi pháp lý, tôi luôn sẵn sàng hỗ trợ.';
  }
  if (t.includes('la ai') || t.includes('la gi')) {
    return 'Tôi là LexAI, trợ lý pháp lý AI cho luật Việt Nam. Bạn có thể mô tả tình huống pháp lý, tôi sẽ phân tích quyền lợi, rủi ro, căn cứ và bước nên làm tiếp.';
  }
  if (t.includes('xin loi') || t.includes('sorry')) {
    return 'Không sao. Bạn cần tôi hỗ trợ tình huống pháp lý nào?';
  }
  return 'Xin chào! Bạn hãy mô tả tình huống pháp lý cụ thể, tôi sẽ giúp phân tích căn cứ, rủi ro và đề xuất bước tiếp theo.';
}

function _lowSignalReply(): string {
  return 'Tôi chưa thấy đủ thông tin pháp lý để phân tích. Bạn hãy mô tả rõ hơn: sự việc xảy ra khi nào, các bên là ai, bạn muốn đạt mục tiêu gì, và hiện có giấy tờ/chứng cứ nào.';
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

export function Analyze() {
  const [activeTab, setActiveTab] = useState<'chat' | 'history'>('chat');
  const [situation, setSituation] = useSyncedSituation(null);
  const [userRole, setUserRole] = useState('nguyen_don');
  const [lawType, setLawType] = useState('all');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  // Sessions persisted in localStorage
  const SESSION_STORAGE_KEY = 'lexai_sessions';
  const CURRENT_SESSION_ID_KEY = 'lexai_current_session_id';
  function loadStoredSessions() {
    try {
      return JSON.parse(localStorage.getItem(SESSION_STORAGE_KEY) || '[]');
    } catch { return []; }
  }

  // Restore the in-progress conversation on page refresh instead of starting empty.
  const [sessionId, setSessionId] = useState<string | null>(() => (
    sessionStorage.getItem(CURRENT_SESSION_ID_KEY) || null
  ));
  const sessionIdRef = useRef<string | null>(sessionId);
  const [history, setHistory] = useState<ChatTurn[]>(() => {
    const savedSessionId = sessionStorage.getItem(CURRENT_SESSION_ID_KEY);
    if (!savedSessionId) return [];
    const existing = loadStoredSessions().find((s: any) => s.id === savedSessionId);
    return existing?.turns || [];
  });
  const historyRef = useRef<ChatTurn[]>(history);
  const [analyzeError, setAnalyzeError] = useState('');
  const [evidenceChip, setEvidenceChip] = useState<{ filename: string; evidenceId: string } | null>(null);
  const [evidenceUploading, setEvidenceUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const [sessionHistory, setSessionHistory] = useState<Array<{
    id: string; title: string; domain: string; date: string; turns: ChatTurn[];
  }>>(loadStoredSessions);

  const [selectedSession, setSelectedSession] = useState<typeof sessionHistory[0] | null>(null);

  const titleFromText = (text: string) => (
    text.length > 64 ? `${text.slice(0, 64)}...` : text
  );

  const writeHistory = (turns: ChatTurn[]) => {
    historyRef.current = turns;
    setHistory(turns);
  };

  const startNewConversation = () => {
    sessionIdRef.current = null;
    setSessionId(null);
    sessionStorage.removeItem(CURRENT_SESSION_ID_KEY);
    writeHistory([]);
    setSelectedSession(null);
    setAnalyzeError('');
    setEvidenceChip(null);
    setActiveTab('chat');
  };

  const persistConversation = (
    id: string,
    title: string,
    domain: string,
    turns: ChatTurn[],
    metadata: Record<string, any>,
  ) => {
    const date = new Date().toLocaleDateString('vi-VN');
    const item = { id, title, domain, date, turns };
    saveConversationSession({ id, title, domain, turns, metadata });
    setSessionHistory(prevSessions => {
      const updated = [item, ...prevSessions.filter(s => s.id !== id)].slice(0, 20);
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
    setSelectedSession(prev => prev?.id === id ? item : prev);
  };

  useEffect(() => {
    loadConversationSessions()
      .then(items => {
        if (!items.length) return;
        setSessionHistory(items.map(item => ({
          id: item.id,
          title: item.title,
          domain: item.domain || 'general',
          date: item.lastActive ? new Date(item.lastActive).toLocaleDateString('vi-VN') : '',
          turns: item.turns as ChatTurn[],
        })));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history, isAnalyzing, activeTab, selectedSession]);

  const handleAnalyze = async () => {
    if (!situation.trim()) return;
    if (situation.trim().length < 10) {
      setAnalyzeError('Mô tả tình huống quá ngắn. Vui lòng cung cấp thêm chi tiết (ít nhất 10 ký tự).');
      return;
    }

    const currentSituation = situation;
    const userMessage: ChatTurn = { role: 'user', content: currentSituation };
    const activeSessionId = sessionIdRef.current || sessionId || `chat_${Date.now()}`;
    sessionIdRef.current = activeSessionId;
    setSessionId(activeSessionId);
    sessionStorage.setItem(CURRENT_SESSION_ID_KEY, activeSessionId);
    const historyWithUser = [...historyRef.current, userMessage];
    writeHistory(historyWithUser);
    setSituation('');

    // Greetings / small-talk — respond locally without calling the API
    if (_isChitchat(currentSituation)) {
      const reply = _chitchatReply(currentSituation);
      const assistantTurn: ChatTurn = { role: 'assistant', content: reply };
      const fullHistory = [...historyWithUser, assistantTurn];
      writeHistory(fullHistory);
      const firstUserTurn = fullHistory.find(turn => turn.role === 'user' && turn.content)?.content || currentSituation;
      persistConversation(activeSessionId, titleFromText(firstUserTurn), 'general', fullHistory, {
        source: 'chitchat',
      });
      return;
    }

    if (_isLowSignalInput(currentSituation)) {
      const assistantTurn: ChatTurn = { role: 'assistant', content: _lowSignalReply() };
      const fullHistory = [...historyWithUser, assistantTurn];
      writeHistory(fullHistory);
      const firstUserTurn = fullHistory.find(turn => turn.role === 'user' && turn.content)?.content || currentSituation;
      persistConversation(activeSessionId, titleFromText(firstUserTurn), 'general', fullHistory, {
        source: 'input_guard',
      });
      logInteraction({
        action_type: 'low_signal_input',
        context: {
          session_id: activeSessionId,
          input_snippet: currentSituation.slice(0, 80),
        },
      });
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
          session_id: activeSessionId,
          top_k: 8
        })
      });
      clearInterval(stageInterval);
      setCurrentStage(7);
      const conversationId = activeSessionId || data.session_id || `chat_${Date.now()}`;
      sessionIdRef.current = conversationId;
      setSessionId(conversationId);
      sessionStorage.setItem(CURRENT_SESSION_ID_KEY, conversationId);
      logInteraction({ action_type: 'situation_analysis', context: { law_type: data.domain, situation_snippet: currentSituation.slice(0, 200) } });

      const assistantTurn: ChatTurn = { role: 'assistant', result: data };
      setIsAnalyzing(false);
      setCurrentStage(0);

      const fullHistory = [...historyWithUser, assistantTurn];
      writeHistory(fullHistory);
      const firstUserTurn = fullHistory.find(turn => turn.role === 'user' && turn.content)?.content || currentSituation;
      persistConversation(conversationId, titleFromText(firstUserTurn), data.domain || 'general', fullHistory, {
        source: 'analyze',
        traceId: data.trace_id,
        backendSessionId: data.session_id,
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
          onClick={startNewConversation}
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
                      <AIResponseCard result={turn.result} />
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
                        <AIResponseCard result={turn.result} />
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

          <div className="relative group">
            <textarea
              value={situation}
              onChange={(e) => setSituation(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleAnalyze();
                }
              }}
              placeholder="Nhập câu hỏi hoặc tình huống pháp lý..."
              className="w-full bg-white/5 border border-white/10 rounded-2xl p-4 pr-28 text-sm text-white placeholder-slate-500 outline-none focus:border-legal-gold/50 focus:bg-white/[0.08] transition-all resize-none min-h-[60px]"
              rows={2}
            />
            <div className="absolute right-4 bottom-4 flex items-center gap-2">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isAnalyzing || evidenceUploading}
                title="Đính kèm tài liệu bổ sung"
                className="w-9 h-9 text-slate-500 hover:text-legal-gold hover:bg-white/5 rounded-xl flex items-center justify-center disabled:opacity-40 transition-all"
              >
                {evidenceUploading ? <Loader2 size={16} className="animate-spin" /> : <Paperclip size={16} />}
              </button>
              <button
                onClick={handleAnalyze}
                disabled={isAnalyzing || situation.trim().length < 10}
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

function AIResponseCard({ result }: { result: AnalysisResponse }) {
  const [expandedAction, setExpandedAction] = useState<number | null>(null);
  const totalMs = result.stage_timings.reduce((a, b) => a + b.duration_ms, 0);

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

        <DynamicRelatedModuleGrid result={result} />

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

        {/* Reasoning trace */}
        {result.trace_id && <TracePanel traceId={result.trace_id} />}
      </div>
    </div>
  );
}

function RelatedModuleGrid({ result }: { result: AnalysisResponse }) {
  const navigate = useNavigate();
  const context = {
    domain: result.domain,
    sessionId: result.session_id,
    traceId: result.trace_id,
    summary: result.accumulated_situation || result.position_reasoning || result.full_assessment,
    citations: result.citations,
  };

  const modules = [
    {
      path: '/evidence-gap',
      title: 'Kiểm tra chứng cứ',
      description: 'Xác định giấy tờ còn thiếu và mức độ bao phủ.',
      icon: FileSearch,
      group: 'Chứng cứ',
    },
    {
      path: '/law-search',
      title: 'Tra cứu điều luật',
      description: 'Tìm căn cứ pháp lý sát với nhận định.',
      icon: BookOpen,
      group: 'Dẫn chứng',
    },
    {
      path: '/similar-cases',
      title: 'Vụ việc tương tự',
      description: 'So sánh với tình huống đã có kết quả.',
      icon: GitCompare,
      group: 'Dẫn chứng',
    },
    {
      path: '/risks',
      title: 'Đánh giá rủi ro',
      description: 'Rà các điểm yếu, thời hiệu và nguy cơ thủ tục.',
      icon: ShieldAlert,
      group: 'Đánh giá',
    },
    {
      path: '/actions',
      title: 'Kế hoạch hành động',
      description: 'Chuyển kết quả thành các bước cần làm.',
      icon: ListChecks,
      group: 'Gợi ý',
    },
    {
      path: '/timeline',
      title: 'Tiến trình pháp lý',
      description: 'Ước lượng giai đoạn, mốc thời gian và hạn cần lưu ý.',
      icon: Clock,
      group: 'Gợi ý',
    },
    {
      path: '/contract',
      title: 'Rà soát hợp đồng',
      description: 'Dùng khi tình huống có hợp đồng hoặc điều khoản.',
      icon: FileCheck,
      group: 'Hợp đồng',
    },
    {
      path: '/checklists',
      title: 'Checklist tuân thủ',
      description: 'Theo dõi việc cần hoàn thành sau phân tích.',
      icon: ClipboardList,
      group: 'Thực thi',
    },
  ];

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between mb-4">
        <div>
          <p className="text-xs font-bold text-white uppercase tracking-wider">Dùng tiếp với module liên quan</p>
          <p className="text-[11px] text-slate-500 mt-1">
            Kết quả phân tích là trung tâm. Mở công cụ chuyên sâu khi cần chứng cứ, rủi ro, điều luật hoặc kế hoạch.
          </p>
        </div>
        <button
          onClick={() => navigate('/journey', { state: context })}
          className="flex items-center gap-2 self-start md:self-auto px-3 py-2 rounded-xl bg-legal-gold/10 text-legal-gold border border-legal-gold/20 text-[11px] font-bold hover:bg-legal-gold/20 transition-all"
        >
          <Map size={14} />
          Mở hành trình
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2">
        {modules.map(item => (
          <button
            key={item.path}
            onClick={() => navigate(item.path, { state: context })}
            className="group text-left rounded-xl border border-white/10 bg-white/5 p-3 hover:border-legal-gold/30 hover:bg-white/10 transition-all"
          >
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-legal-gold/10 text-legal-gold flex items-center justify-center shrink-0">
                <item.icon size={16} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500">{item.group}</span>
                </div>
                <p className="text-xs font-bold text-slate-100 group-hover:text-legal-gold transition-colors">{item.title}</p>
                <p className="text-[11px] text-slate-500 leading-snug mt-1">{item.description}</p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function DynamicRelatedModuleGrid({ result }: { result: AnalysisResponse }) {
  const navigate = useNavigate();
  const [feedback, setFeedback] = useState<Record<string, 'useful' | 'not_useful'>>({});
  const [dismissed, setDismissed] = useState<Record<string, boolean>>({});
  const context = {
    domain: result.domain,
    sessionId: result.session_id,
    traceId: result.trace_id,
    summary: result.accumulated_situation || result.position_reasoning || result.full_assessment,
    citations: result.citations,
  };

  const fallbackModules: NextBestAction[] = [
    {
      action_id: 'evidence_gap',
      action_url: '/evidence-gap',
      module: 'evidence_gap',
      title: 'Kiểm tra chứng cứ',
      description: 'Xác định giấy tờ còn thiếu và mức độ bao phủ.',
      category: 'evidence',
      priority: 'medium',
      score: 0.6,
      reason: 'Chứng cứ là đầu vào của mọi bước pháp lý tiếp theo.',
      evidence: result.citations,
      prefill: context,
      blocking_gaps: [],
    },
    {
      action_id: 'action_plan',
      action_url: '/actions',
      module: 'actions',
      title: 'Kế hoạch hành động',
      description: 'Chuyển kết quả thành các bước cần làm.',
      category: 'execution',
      priority: 'medium',
      score: 0.55,
      reason: 'Kết quả phân tích cần được chuyển thành việc làm cụ thể.',
      evidence: result.citations,
      prefill: context,
      blocking_gaps: [],
    },
  ];
  const recommendations = result.next_best_actions?.length ? result.next_best_actions : fallbackModules;
  const visibleRecommendations = recommendations.filter(item => !dismissed[item.action_id]);
  const goalMeta = recommendations.find(item => item.detected_goals?.length || item.next_questions?.length || item.journey_steps?.length);
  const impressionKey = `${result.session_id}:${recommendations.map(item => item.action_id).join('|')}`;

  useEffect(() => {
    recommendations.forEach(item => {
      logInteraction({
        action_type: 'recommendation_impression',
        doc_id: item.action_id,
        context: {
          action_id: item.action_id,
          module: item.module,
          law_type: result.domain,
          score: item.score,
          priority: item.priority,
          session_id: result.session_id,
        },
      });
    });
  }, [impressionKey, result.domain, result.session_id]);

  const sendFeedback = (item: NextBestAction, value: 'useful' | 'not_useful') => {
    setFeedback(prev => ({ ...prev, [item.action_id]: value }));
    logInteraction({
      action_type: value === 'useful' ? 'recommendation_useful' : 'recommendation_not_useful',
      doc_id: item.action_id,
      context: {
        action_id: item.action_id,
        module: item.module,
        law_type: result.domain,
        feedback: value,
        score: item.score,
        priority: item.priority,
        session_id: result.session_id,
      },
    });
  };

  const dismissRecommendation = (item: NextBestAction) => {
    setDismissed(prev => ({ ...prev, [item.action_id]: true }));
    logInteraction({
      action_type: 'recommendation_dismiss',
      doc_id: item.action_id,
      context: {
        action_id: item.action_id,
        module: item.module,
        law_type: result.domain,
        score: item.score,
        priority: item.priority,
        session_id: result.session_id,
      },
    });
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between mb-4">
        <div>
          <p className="text-xs font-bold text-white uppercase tracking-wider">Recommendation engine: bước nên làm tiếp</p>
          <p className="text-[11px] text-slate-500 mt-1">
            Các gợi ý được xếp hạng theo điểm vị thế, cảnh báo, domain và mức độ dẫn chứng.
          </p>
        </div>
        <button
          onClick={() => navigate('/journey', { state: context })}
          className="flex items-center gap-2 self-start md:self-auto px-3 py-2 rounded-xl bg-legal-gold/10 text-legal-gold border border-legal-gold/20 text-[11px] font-bold hover:bg-legal-gold/20 transition-all"
        >
          <Map size={14} />
          Mở hành trình
        </button>
      </div>

      {goalMeta && (
        <div className="mb-4 grid gap-3 lg:grid-cols-[1fr_1fr]">
          <div className="rounded-xl border border-legal-gold/20 bg-legal-gold/5 p-3">
            <p className="text-[10px] font-bold uppercase tracking-wider text-legal-gold mb-2">
              Hiểu nhu cầu của bạn
            </p>
            <div className="flex flex-wrap gap-2">
              {(goalMeta.detected_goals || []).map(goal => (
                <span key={goal} className="rounded-lg border border-legal-gold/20 bg-legal-gold/10 px-2 py-1 text-[10px] font-semibold text-legal-gold">
                  {goalLabel(goal)}
                </span>
              ))}
              {goalMeta.user_position && (
                <span className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[10px] font-semibold text-slate-300">
                  {positionLabel(goalMeta.user_position)}
                </span>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
              Câu hỏi nên bổ sung
            </p>
            <ul className="space-y-1.5">
              {(goalMeta.next_questions || []).slice(0, 3).map((question, idx) => (
                <li key={idx} className="flex gap-2 text-[11px] leading-relaxed text-slate-300">
                  <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-legal-gold/10 text-[9px] font-bold text-legal-gold">
                    {idx + 1}
                  </span>
                  <span>{question}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {goalMeta?.journey_steps?.length ? (
        <div className="mb-4 rounded-xl border border-white/10 bg-white/[0.03] p-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
            Lộ trình đề xuất
          </p>
          <div className="grid gap-2 md:grid-cols-4">
            {goalMeta.journey_steps.slice(0, 4).map((step, idx) => (
              <div key={idx} className="rounded-lg border border-white/8 bg-white/5 p-2">
                <span className="text-[9px] font-bold text-legal-gold">Bước {idx + 1}</span>
                <p className="mt-1 text-[11px] leading-relaxed text-slate-300">{step}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2">
        {visibleRecommendations.map(item => {
          const Icon = moduleIcon(item.module);
          const navState = {
            ...context,
            summary: item.prefill?.summary || context.summary,
            domain: item.prefill?.domain || context.domain,
            citations: item.prefill?.citations || context.citations,
          };
          return (
            <div
              key={item.action_id}
              className="group rounded-xl border border-white/10 bg-white/5 hover:border-legal-gold/30 hover:bg-white/10 transition-all overflow-hidden"
            >
              <button
                type="button"
                onClick={() => {
                  logInteraction({
                    action_type: 'recommendation_click',
                    doc_id: item.action_id,
                    context: {
                      action_id: item.action_id,
                      module: item.module,
                      law_type: result.domain,
                      score: item.score,
                      priority: item.priority,
                      session_id: result.session_id,
                    },
                  });
                  navigate(item.action_url, { state: navState });
                }}
                className="w-full text-left p-3"
              >
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-legal-gold/10 text-legal-gold flex items-center justify-center shrink-0">
                    <Icon size={16} />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500">{item.category}</span>
                      <span className={cn(
                        'text-[9px] font-bold px-1.5 py-0.5 rounded border',
                        item.priority === 'high' ? 'text-red-300 border-red-500/30 bg-red-500/10' :
                        item.priority === 'medium' ? 'text-yellow-300 border-yellow-500/30 bg-yellow-500/10' :
                        'text-slate-400 border-white/10 bg-white/5',
                      )}>
                        {Math.round(item.score * 100)}
                      </span>
                    </div>
                    <p className="text-xs font-bold text-slate-100 group-hover:text-legal-gold transition-colors">{item.title}</p>
                    <p className="text-[11px] text-slate-500 leading-snug mt-1">{item.description}</p>
                    {item.reason && <p className="text-[10px] text-slate-600 leading-snug mt-2">{item.reason}</p>}
                  </div>
                </div>
              </button>
              <div className="flex items-center justify-between gap-2 border-t border-white/8 px-3 py-2 bg-legal-navy/20">
                <span className="text-[10px] text-slate-600">Phản hồi để cá nhân hoá</span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    title="Gợi ý hữu ích"
                    onClick={() => sendFeedback(item, 'useful')}
                    className={cn(
                      'p-1.5 rounded-lg border transition-all',
                      feedback[item.action_id] === 'useful'
                        ? 'text-green-300 border-green-500/40 bg-green-500/10'
                        : 'text-slate-500 border-white/10 hover:text-green-300 hover:border-green-500/30',
                    )}
                  >
                    <ThumbsUp size={13} />
                  </button>
                  <button
                    type="button"
                    title="Gợi ý chưa phù hợp"
                    onClick={() => sendFeedback(item, 'not_useful')}
                    className={cn(
                      'p-1.5 rounded-lg border transition-all',
                      feedback[item.action_id] === 'not_useful'
                        ? 'text-red-300 border-red-500/40 bg-red-500/10'
                        : 'text-slate-500 border-white/10 hover:text-red-300 hover:border-red-500/30',
                    )}
                  >
                    <ThumbsDown size={13} />
                  </button>
                  <button
                    type="button"
                    title="Ẩn gợi ý này"
                    onClick={() => dismissRecommendation(item)}
                    className="p-1.5 rounded-lg border border-white/10 text-slate-500 hover:text-slate-300 hover:border-white/20 transition-all"
                  >
                    <EyeOff size={13} />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function moduleIcon(module: string) {
  const icons = {
    evidence_gap: FileSearch,
    law_search: BookOpen,
    similar_cases: GitCompare,
    risks: ShieldAlert,
    actions: ListChecks,
    timeline: Clock,
    contract: FileCheck,
    checklists: ClipboardList,
    journey: Map,
  } as const;
  return icons[module as keyof typeof icons] || ListChecks;
}

function goalLabel(goal: string) {
  const labels: Record<string, string> = {
    divorce: 'Ly hôn',
    child_custody: 'Quyền nuôi con',
    asset_division: 'Chia tài sản',
    asset_protection: 'Bảo vệ tài sản',
    debt_recovery: 'Đòi nợ',
    employment_termination: 'Chấm dứt lao động',
    land_dispute: 'Tranh chấp đất',
    contract_enforcement: 'Thực hiện hợp đồng',
    complaint_or_lawsuit: 'Khiếu nại/khởi kiện',
    risk_avoidance: 'Giảm rủi ro',
    clarify_legal_goal: 'Làm rõ mục tiêu',
  };
  return labels[goal] || goal.replace(/_/g, ' ');
}

function positionLabel(position: string) {
  const labels: Record<string, string> = {
    parent_seeking_custody: 'Vị thế: cha/mẹ muốn nuôi con',
    employer_or_company: 'Vị thế: doanh nghiệp/người sử dụng lao động',
    employee: 'Vị thế: người lao động',
    buyer: 'Vị thế: bên mua',
    seller: 'Vị thế: bên bán',
    creditor_or_claimant: 'Vị thế: người yêu cầu quyền lợi',
    respondent: 'Vị thế: bên bị yêu cầu',
    claimant_or_complainant: 'Vị thế: người khiếu nại/khởi kiện',
    general_user: 'Vị thế: người cần tư vấn',
  };
  return labels[position] || position.replace(/_/g, ' ');
}
