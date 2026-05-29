/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import {
  GitCompare,
  Loader2,
  AlertTriangle,
  Scale,
  ChevronRight,
  BookOpen,
  Gavel,
  Lightbulb,
  Tag,
  Bookmark,
  Check,
  Users,
  ThumbsUp,
  ThumbsDown,
  Globe,
  ArrowRight,
} from 'lucide-react';
import {
  getSimilarCases,
  SimilarCaseItem,
  CommunityCaseItem,
  SimilarCasesResult,
  saveAnalysis,
  logCommunityCaseSignal,
} from '../lib/api';
import { useSyncedSituation } from '../lib/analysisContext';
import { useToast } from '../lib/useToast';
import { ToastContainer } from '../components/ui/ToastContainer';

// ── Similarity bar ────────────────────────────────────────────────────────────

function SimilarityBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.85 ? 'bg-green-500' :
    score >= 0.70 ? 'bg-legal-gold' :
    score >= 0.55 ? 'bg-orange-500' :
    'bg-slate-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-[11px] font-bold tabular-nums ${
        score >= 0.85 ? 'text-green-400' :
        score >= 0.70 ? 'text-legal-gold' :
        score >= 0.55 ? 'text-orange-400' : 'text-slate-400'
      }`}>{pct}%</span>
    </div>
  );
}

// ── Case card ─────────────────────────────────────────────────────────────────

function CaseCard({ item, index }: { item: SimilarCaseItem; index: number }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="bg-white/5 border border-white/8 rounded-xl overflow-hidden hover:bg-white/8 transition-all">
      {/* header */}
      <button
        onClick={() => setExpanded(p => !p)}
        className="w-full flex items-start gap-3 p-4 text-left"
      >
        <span className="flex-none w-7 h-7 rounded-full bg-legal-gold/15 text-legal-gold text-[11px] font-bold flex items-center justify-center border border-legal-gold/20 mt-0.5">
          {index + 1}
        </span>
        <div className="flex-1 min-w-0 space-y-1.5">
          <p className="text-sm font-semibold text-white leading-snug">
            {item.title || 'Vụ việc không có tiêu đề'}
            {item.is_demo && (
              <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-medium">
                Ví dụ tham khảo
              </span>
            )}
          </p>
          <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
            {item.situation_summary}
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-legal-gold/10 text-legal-gold border border-legal-gold/20 font-medium">
              {item.domain_label}
            </span>
            <span className="text-[10px] text-slate-500">{item.similarity_label}</span>
          </div>
          <SimilarityBar score={item.similarity_score} />
        </div>
        <ChevronRight
          size={16}
          className={`flex-none text-slate-500 mt-0.5 transition-transform ${expanded ? 'rotate-90' : ''}`}
        />
      </button>

      {/* expanded detail */}
      {expanded && (
        <div className="border-t border-white/8 p-4 space-y-3 animate-in fade-in duration-200">
          {item.outcome && (
            <div className="flex gap-2">
              <Gavel size={14} className="text-legal-gold shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-0.5">Kết quả</p>
                <p className="text-sm text-slate-300 leading-relaxed">{item.outcome}</p>
              </div>
            </div>
          )}
          {item.lesson && (
            <div className="flex gap-2">
              <Lightbulb size={14} className="text-yellow-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-0.5">Bài học</p>
                <p className="text-sm text-slate-300 leading-relaxed italic">{item.lesson}</p>
              </div>
            </div>
          )}
          {item.key_laws.length > 0 && (
            <div className="flex gap-2">
              <BookOpen size={14} className="text-blue-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Căn cứ pháp lý</p>
                <div className="flex flex-wrap gap-1.5">
                  {item.key_laws.map((law, i) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-300 border border-blue-500/20">
                      {law}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Community case card ───────────────────────────────────────────────────────

function CommunityCaseCard({ item, index }: { item: CommunityCaseItem; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const [feedback, setFeedback] = useState<'useful' | 'not_useful' | null>(null);

  function handleFeedback(signal: 'useful' | 'not_useful') {
    setFeedback(signal);
    logCommunityCaseSignal(item.pattern_id, signal).catch(() => undefined);
  }

  const pct = Math.round(item.similarity_score * 100);
  const color =
    item.similarity_score >= 0.85 ? 'text-green-400' :
    item.similarity_score >= 0.70 ? 'text-legal-gold' :
    item.similarity_score >= 0.55 ? 'text-orange-400' : 'text-slate-400';

  return (
    <div className="bg-white/5 border border-white/8 rounded-xl overflow-hidden hover:bg-white/8 transition-all">
      {/* header */}
      <button
        onClick={() => setExpanded(p => !p)}
        className="w-full flex items-start gap-3 p-4 text-left"
      >
        <span className="flex-none w-7 h-7 rounded-full bg-blue-500/15 text-blue-400 text-[11px] font-bold flex items-center justify-center border border-blue-500/20 mt-0.5">
          {index + 1}
        </span>
        <div className="flex-1 min-w-0 space-y-1.5">
          <p className="text-sm font-semibold text-white leading-snug line-clamp-2">
            {item.summary}
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300 border border-blue-500/20 font-medium">
              {item.domain_label}
            </span>
            <span className={`text-[10px] font-bold tabular-nums ${color}`}>{pct}% tương đồng</span>
            <span className="text-[10px] text-slate-600 flex items-center gap-0.5">
              <Users size={9} /> Cộng đồng
            </span>
          </div>
          {item.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {item.tags.slice(0, 4).map(t => (
                <span key={t} className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-slate-500 border border-white/5">{t}</span>
              ))}
            </div>
          )}
        </div>
        <ChevronRight
          size={16}
          className={`flex-none text-slate-500 mt-0.5 transition-transform ${expanded ? 'rotate-90' : ''}`}
        />
      </button>

      {/* expanded detail */}
      {expanded && (
        <div className="border-t border-white/8 p-4 space-y-3 animate-in fade-in duration-200">
          {item.resolution_summary && (
            <div className="flex gap-2">
              <Gavel size={14} className="text-legal-gold shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-0.5">Hướng giải quyết</p>
                <p className="text-sm text-slate-300 leading-relaxed">{item.resolution_summary}</p>
              </div>
            </div>
          )}
          {item.recommended_steps.length > 0 && (
            <div className="flex gap-2">
              <ArrowRight size={14} className="text-blue-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Bước nên làm</p>
                <ul className="space-y-1">
                  {item.recommended_steps.map((step, i) => (
                    <li key={i} className="flex gap-1.5 text-xs text-slate-400">
                      <span className="text-blue-400 font-bold shrink-0">{i + 1}.</span>
                      {step}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
          {item.citations.length > 0 && (
            <div className="flex gap-2">
              <BookOpen size={14} className="text-blue-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-bold mb-1">Căn cứ</p>
                <div className="flex flex-wrap gap-1.5">
                  {item.citations.map((c, i) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-300 border border-blue-500/20">{c}</span>
                  ))}
                </div>
              </div>
            </div>
          )}
          {/* Feedback */}
          <div className="flex items-center gap-2 pt-1">
            <span className="text-[10px] text-slate-500">Tình huống này có hữu ích không?</span>
            <button
              onClick={() => handleFeedback('useful')}
              disabled={feedback !== null}
              className={`flex items-center gap-1 text-[10px] px-2 py-1 rounded-lg border transition-all ${
                feedback === 'useful'
                  ? 'bg-green-500/20 border-green-500/30 text-green-400'
                  : 'bg-white/5 border-white/10 text-slate-400 hover:text-green-400 hover:border-green-500/20'
              } disabled:cursor-default`}
            >
              <ThumbsUp size={10} /> Có
            </button>
            <button
              onClick={() => handleFeedback('not_useful')}
              disabled={feedback !== null}
              className={`flex items-center gap-1 text-[10px] px-2 py-1 rounded-lg border transition-all ${
                feedback === 'not_useful'
                  ? 'bg-red-500/20 border-red-500/30 text-red-400'
                  : 'bg-white/5 border-white/10 text-slate-400 hover:text-red-400 hover:border-red-500/20'
              } disabled:cursor-default`}
            >
              <ThumbsDown size={10} /> Không
            </button>
            {feedback && (
              <span className="text-[10px] text-slate-500 italic">Cảm ơn phản hồi!</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Summary bar ───────────────────────────────────────────────────────────────

function QueryBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <Tag size={11} className="text-slate-500" />
      <span className="text-[10px] text-slate-500 uppercase tracking-wider">{label}:</span>
      <span className="text-xs text-white font-medium">{value}</span>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

const MIN_QUERY_LENGTH = 10;

function getSearchModeLabel(mode: string) {
  if (mode === 'vector') return 'Ngữ nghĩa';
  if (mode === 'demo_fallback') return 'Dữ liệu demo';
  return 'Từ khóa';
}

export function SimilarCases() {
  const location = useLocation();
  const [situation, setSituation] = useSyncedSituation(location.state);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimilarCasesResult | null>(null);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const { toasts, toast, dismiss } = useToast();

  async function handleSearch(nextSituation = situation) {
    const query = nextSituation.trim();
    if (!query) {
      setError('Nhập mô tả tình huống để tìm vụ việc tương tự.');
      return;
    }
    if (query.length < MIN_QUERY_LENGTH) {
      setError(`Mô tả cần ít nhất ${MIN_QUERY_LENGTH} ký tự để kết quả có ý nghĩa.`);
      return;
    }
    setLoading(true);
    setResult(null);
    setError('');
    setSaved(false);
    setSituation(query);
    try {
      const r = await getSimilarCases(query);
      setResult(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể kết nối máy chủ. Vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const initialSituation = situation.trim();
    if (initialSituation.length >= MIN_QUERY_LENGTH) {
      void handleSearch(initialSituation);
    }
    // Run once on direct navigation so the page can hydrate from the shared legal context.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const canSearch = situation.trim().length >= MIN_QUERY_LENGTH && !loading;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <ToastContainer toasts={toasts} dismiss={dismiss} />
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-legal-gold/10 border border-legal-gold/20 rounded-xl flex items-center justify-center">
          <GitCompare size={20} className="text-legal-gold" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Vụ Việc Tương Tự</h1>
          <p className="text-sm text-slate-400">Tìm kiếm case pháp lý gần giống để tham khảo kết quả và bài học</p>
        </div>
      </div>

      {/* Input */}
      <div className="glass-card p-6 space-y-4">
        <label className="text-sm font-semibold text-white">Mô tả tình huống của bạn</label>
        <textarea
          value={situation}
          onChange={e => {
            setSituation(e.target.value);
            if (error) setError('');
          }}
          onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSearch(); }}
          placeholder="Ví dụ: Tôi bị công ty sa thải không báo trước, không trả lương tháng cuối và không chi trả trợ cấp thôi việc..."
          rows={3}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-legal-gold/50 transition-colors"
        />
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleSearch()}
            disabled={!canSearch}
            className="flex items-center gap-2 px-6 py-2.5 bg-legal-gold text-legal-navy font-bold rounded-xl disabled:opacity-40 hover:scale-105 active:scale-95 transition-all text-sm"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <GitCompare size={16} />}
            {loading ? 'Đang tìm kiếm...' : 'Tìm vụ việc tương tự'}
          </button>
          <span className="text-[11px] text-slate-500">Ctrl+Enter để tìm</span>
        </div>
        {error && (
          <div className="flex items-center gap-2 text-xs text-red-400 p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
            <AlertTriangle size={13} />
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4 animate-in fade-in duration-300">
          {/* Query metadata bar */}
          <div className="glass-card p-4 flex flex-wrap gap-x-6 gap-y-2 items-center">
            <QueryBadge label="Lĩnh vực" value={result.query_domain_label} />
            <QueryBadge label="Giai đoạn" value={result.query_stage_label} />
            <QueryBadge label="Tìm kiếm" value={getSearchModeLabel(result.search_mode)} />
            {result.cross_language_used && (
              <span className="flex items-center gap-1 text-[10px] text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-full">
                <Globe size={9} /> Tìm chéo ngôn ngữ
              </span>
            )}
            <span className="text-xs text-slate-400 italic flex-1 min-w-0 truncate">{result.summary}</span>
            <button
              onClick={() => {
                saveAnalysis({ type: 'similar_cases', title: situation.slice(0, 80), summary: result.summary, data: result }).then(() => toast('Đã lưu vào lịch sử'));
                setSaved(true);
              }}
              disabled={saved}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border bg-white/5 border-white/10 text-slate-400 hover:text-legal-gold hover:border-legal-gold/30 disabled:opacity-60 shrink-0"
            >
              {saved ? <><Check size={12} className="text-green-400" /> Đã lưu</> : <><Bookmark size={12} /> Lưu kết quả</>}
            </button>
          </div>

          {/* Official case list */}
          {result.similar_cases.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider px-1">
                Vụ việc chính thống ({result.similar_cases.length})
              </h2>
              {result.similar_cases.map((item, i) => (
                <CaseCard key={item.case_id || i} item={item} index={i} />
              ))}
            </div>
          )}

          {result.similar_cases.length === 0 && (result.community_cases?.length ?? 0) === 0 && (
            <div className="py-12 flex flex-col items-center text-center space-y-3 opacity-50">
              <Scale size={48} className="text-slate-500" />
              <p className="text-sm text-slate-400">Không tìm thấy vụ việc tương tự trong cơ sở dữ liệu.</p>
              <p className="text-xs text-slate-500">Thử cung cấp thêm chi tiết hoặc mô tả theo hướng khác.</p>
            </div>
          )}

          {/* Community cases section */}
          {(result.community_cases?.length ?? 0) > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 px-1">
                <Users size={13} className="text-blue-400" />
                <h2 className="text-xs font-bold text-blue-400 uppercase tracking-wider">
                  Vụ việc cộng đồng đã tìm ({result.community_cases!.length})
                </h2>
              </div>
              {result.community_cases!.map((item, i) => (
                <CommunityCaseCard key={item.pattern_id || i} item={item} index={i} />
              ))}
            </div>
          ) : (
            <div className="glass-card p-4">
              <div className="flex gap-2">
                <Users size={14} className="text-slate-500 shrink-0 mt-0.5" />
                <p className="text-xs text-slate-500 italic leading-relaxed">
                  Các tình huống cộng đồng sẽ chỉ được hiển thị sau khi đã ẩn danh, không chứa tên, số điện thoại, địa chỉ, email hoặc thông tin định danh cá nhân.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div className="py-20 flex flex-col items-center text-center space-y-3 opacity-30">
          <GitCompare size={64} className="text-slate-500" />
          <p className="text-sm font-bold text-slate-500">Nhập tình huống để tìm vụ việc có điểm tương đồng</p>
          <p className="text-xs text-slate-600">Cần tối thiểu {MIN_QUERY_LENGTH} ký tự để tránh kết quả nhầm từ câu hỏi quá ngắn.</p>
        </div>
      )}
    </div>
  );
}
