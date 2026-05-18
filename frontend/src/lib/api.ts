/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// UTILITIES
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const API_BASE: string =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

const USER_ID_KEY = 'lexai_user_id';
const DEFAULT_USER_ID = 'demo_user_001';

export function getUserId(): string {
  return localStorage.getItem(USER_ID_KEY) || DEFAULT_USER_ID;
}

export function setUserId(id: string): void {
  localStorage.setItem(USER_ID_KEY, id);
}

// Kept for backward compat in transformProfile fallback
export const USER_ID = DEFAULT_USER_ID;

export const LAW_TYPE_LABELS: Record<string, string> = {
  dat_dai: "Đất đai",
  hop_dong: "Hợp đồng",
  lao_dong: "Lao động",
  doanh_nghiep: "Doanh nghiệp",
  dan_su: "Dân sự",
  hinh_su: "Hình sự",
  hanh_chinh: "Hành chính",
  gia_dinh: "Gia đình",
  general: "Tổng hợp",
};

// TYPES
export interface InteractionLogPayload {
  doc_id: string;
  action_type: 'view' | 'save' | 'download';
  context: Record<string, any>;
}

export interface LawChunk {
  id: string;
  law_reference: string;
  content: string;
  relevance_score: number;
}

export interface RecommendedAction {
  id: string;
  title: string;
  description: string;
  urgency: 'cao' | 'trung_binh' | 'thap';
}

export interface RiskWarning {
  id: string;
  content: string;
  severity: 'cao' | 'trung_binh' | 'thap';
}

export interface StageTiming {
  stage: string;
  duration_ms: number;
}

export interface AnalysisResponse {
  session_id: string;
  status: 'manh' | 'trung_binh' | 'yeu';
  position_score: number;
  position_reasoning: string;
  domain: string;
  domain_confidence: number;
  laws: LawChunk[];
  actions: RecommendedAction[];
  warnings: RiskWarning[];
  full_assessment: string;
  citations: string[];
  stage_timings: StageTiming[];
  used_llm: boolean;
  is_chitchat?: boolean;
  trace_id?: string;
  tool_calls_made?: Array<{
    tool: string;
    description: string;
  }>;
}

export interface ContractAnalysisResult {
  loai_hop_dong: string;
  cac_ben: string[];
  pham_vi: string;
  gia_tri: string;
  compliance_score: number;
  risk_clauses: Array<{
    name: string;
    risk: string;
    legal_basis: string;
    before: string;
    after: string;
  }>;
  missing_clauses: string[];
  recommendations: string[];
  used_llm: boolean;
  tool_calls_made: any[];
}

export interface DocRecommendation {
  id: string;
  law_type: string;
  snippet: string;
  final_score: number;
  reason: string;
  scores: {
    vector: number;
    collab: number;
    item_cf: number;
    user_user: number;
  };
}

export interface CaseRecommendation {
  id: string;
  title: string;
  situation_summary: string;
  outcome: string;
  lesson: string;
  similarity_score: number;
}

export interface TemplateRecommendation {
  id: string;
  name: string;
  industry: string;
  contract_type: string;
  description: string;
  key_clauses: string[];
  related_laws: string[];
  download_hint: string;
  vector_score: number;
}

export interface RiskAssessment {
  id: string;
  name: string;
  severity: 'cao' | 'trung_binh' | 'thap';
  description: string;
  indicators: string[];
  mitigation_steps: string[];
  related_law_types: string[];
  source: string;
  score: number;
}

export interface ChecklistItem {
  description: string;
  is_required: boolean;
  related_law: string;
  deadline_note: string;
}

export interface ChecklistCategory {
  name: string;
  items: ChecklistItem[];
}

export interface Checklist {
  id: string;
  name: string;
  priority: string;
  description: string;
  categories: ChecklistCategory[];
  related_laws: string[];
}

export interface UserProfile {
  user_id: string;
  top_law_type: string;
  last_active: string;
  total_interactions: number;
  days_active: number;
  law_type_weights: Record<string, number>;
  action_frequencies: Record<string, number>;
  active_hours: number[];
}

export interface DigestResponse {
  top_domain: string;
  total_interactions: number;
  days_active: number;
  last_active_date: string;
  recommendations: Array<{
    id: string;
    title: string;
    reason: string;
    score: number;
  }>;
}

// RESPONSE TRANSFORMERS

function transformIntelligenceAnalyze(raw: any): AnalysisResponse {
  const strengthRaw: string = raw.legal_position_strength || '';
  const status: 'manh' | 'trung_binh' | 'yeu' =
    (strengthRaw === 'Mạnh' || strengthRaw === 'manh') ? 'manh' :
    (strengthRaw === 'Yếu' || strengthRaw === 'yeu') ? 'yeu' :
    'trung_binh';

  const laws: LawChunk[] = (raw.relevant_laws || []).map((l: any, i: number) => ({
    id: l.chunk_id || `law-${i}`,
    law_reference: l.law_reference || '',
    content: l.content || '',
    relevance_score: l.relevance_score ?? 0.5,
  }));

  const actions: RecommendedAction[] = (raw.recommended_actions || []).map((a: string, i: number) => ({
    id: `action-${i}`,
    title: a.length > 60 ? a.substring(0, 60) + '…' : a,
    description: a,
    urgency: (i === 0 ? 'cao' : i === 1 ? 'trung_binh' : 'thap') as 'cao' | 'trung_binh' | 'thap',
  }));

  const warnings: RiskWarning[] = (raw.warnings || []).map((w: string, i: number) => ({
    id: `warn-${i}`,
    content: w,
    severity: 'cao' as const,
  }));

  const stage_timings: StageTiming[] = Object.entries(raw.stage_timings || {}).map(
    ([stage, ms]) => ({ stage, duration_ms: ms as number })
  );

  const rawScore = raw.position_score ?? 0;
  const position_score = rawScore <= 1 ? Math.round(rawScore * 100) : Math.round(rawScore);

  return {
    session_id: raw.session_id || '',
    status,
    position_score,
    position_reasoning: raw.position_reasoning || raw.situation_summary || '',
    domain: raw.detected_domain || raw.domain || 'general',
    domain_confidence: raw.domain_confidence ?? 0.5,
    laws,
    actions,
    warnings,
    full_assessment: raw.full_assessment || '',
    citations: raw.citations || [],
    stage_timings,
    used_llm: raw.used_llm ?? false,
    is_chitchat: raw.is_chitchat ?? false,
    trace_id: raw.trace_id || '',
    tool_calls_made: (raw.tool_calls_made || []).map((t: any) => ({
      tool: typeof t === 'string' ? t : t.tool || t.name || '',
      description: t.description || '',
    })),
  };
}

function transformDocuments(raw: any[]): DocRecommendation[] {
  return raw.map((r: any) => ({
    id: r.doc_id || r.id || '',
    law_type: r.law_type || 'general',
    snippet: r.snippet || '',
    final_score: r.final_score ?? 0,
    reason: r.reason || '',
    scores: {
      vector: r.vector_score ?? 0,
      collab: r.collab_score ?? 0,
      item_cf: r.item_cf_score ?? 0,
      user_user: r.user_user_score ?? 0,
    },
  }));
}

function transformCases(raw: any[]): CaseRecommendation[] {
  return raw.map((c: any) => ({
    id: c.case_id || c.id || '',
    title: c.title || '',
    situation_summary: c.situation_summary || '',
    outcome: c.outcome || c.result || '',
    lesson: c.lesson || '',
    similarity_score: c.similarity_score ?? 0.5,
  }));
}

function transformTemplates(raw: any[]): TemplateRecommendation[] {
  return raw.map((t: any) => ({
    id: t.template_id || t.id || '',
    name: t.name || '',
    industry: t.industry || '',
    contract_type: t.contract_type || '',
    description: t.description || '',
    key_clauses: t.key_clauses || [],
    related_laws: t.related_laws || [],
    download_hint: t.download_hint || '',
    vector_score: t.vector_score ?? 0,
  }));
}

function transformRisks(raw: any[]): RiskAssessment[] {
  return raw.map((r: any) => ({
    id: r.risk_id || r.id || '',
    name: r.name || '',
    severity: (['cao', 'trung_binh', 'thap'].includes(r.severity) ? r.severity : 'trung_binh') as 'cao' | 'trung_binh' | 'thap',
    description: r.description || '',
    indicators: r.indicators || [],
    mitigation_steps: r.mitigation || r.mitigation_steps || [],
    related_law_types: r.related_law_types || [],
    source: r.source || '',
    score: r.score ?? 0,
  }));
}

function transformChecklists(raw: any[]): Checklist[] {
  return raw.map((cl: any) => {
    const categoryMap: Record<string, ChecklistItem[]> = {};
    for (const item of cl.items || []) {
      const cat = item.category || 'Chung';
      if (!categoryMap[cat]) categoryMap[cat] = [];
      categoryMap[cat].push({
        description: item.description || '',
        is_required: item.required ?? item.is_required ?? false,
        related_law: item.related_law || '',
        deadline_note: item.deadline_note || '',
      });
    }
    const priorityMap: Record<number, string> = { 1: 'cao', 2: 'trung_binh', 3: 'thap' };
    return {
      id: cl.checklist_id || cl.id || '',
      name: cl.name || '',
      priority: priorityMap[cl.priority] || 'thap',
      description: cl.description || '',
      categories: Object.entries(categoryMap).map(([name, items]) => ({ name, items })),
      related_laws: cl.related_laws || [],
    };
  });
}

function transformProfile(raw: any): UserProfile {
  let lastActive = 'N/A';
  if (raw.last_active) {
    try {
      lastActive = new Date(raw.last_active).toLocaleDateString('vi-VN');
    } catch {
      lastActive = raw.last_active;
    }
  }
  return {
    user_id: raw.user_id || USER_ID,
    top_law_type: raw.top_law_type || 'general',
    last_active: lastActive,
    total_interactions: raw.total_interactions ?? 0,
    days_active: raw.days_active ?? 0,
    law_type_weights: raw.law_type_weights || {},
    action_frequencies: raw.action_frequencies || {},
    active_hours: raw.active_hours || Array(24).fill(0),
  };
}

function transformDigest(raw: any): DigestResponse {
  const profile = raw.profile || raw;
  let lastActive = 'N/A';
  const isoStr = profile.last_active_iso || profile.last_active || raw.last_active_date;
  if (isoStr) {
    try {
      lastActive = new Date(isoStr).toLocaleDateString('vi-VN');
    } catch {
      lastActive = isoStr;
    }
  }
  return {
    top_domain: profile.top_law_type || raw.top_domain || 'general',
    total_interactions: profile.total_interactions ?? raw.total_interactions ?? 0,
    days_active: profile.days_active ?? raw.days_active ?? 0,
    last_active_date: lastActive,
    recommendations: (raw.recommendations || []).slice(0, 6).map((r: any, i: number) => ({
      id: r.rec_id || r.id || `rec-${i}`,
      title: r.title || '',
      reason: r.reason || '',
      score: r.score ?? 0,
    })),
  };
}

function transformContract(raw: any): ContractAnalysisResult {
  const rawScore = raw.position_score ?? 0;
  const score = rawScore <= 1 ? Math.round(rawScore * 100) : Math.round(rawScore);

  return {
    loai_hop_dong: raw.situation_summary?.split('\n')[0] || 'Hợp đồng',
    cac_ben: [],
    pham_vi: raw.situation_summary || '',
    gia_tri: '',
    compliance_score: score,
    risk_clauses: (raw.warnings || []).map((w: string, i: number) => ({
      name: `Điều khoản rủi ro ${i + 1}`,
      risk: w,
      legal_basis: raw.citations?.[i] || '',
      before: '',
      after: '',
    })),
    missing_clauses: raw.missing_evidence || [],
    recommendations: raw.recommended_actions || [],
    used_llm: raw.used_llm ?? false,
    tool_calls_made: raw.tool_calls_made || [],
  };
}

function applyTransform(path: string, method: string, raw: any): any {
  if (path.includes('/intelligence/analyze'))
    return transformIntelligenceAnalyze(raw);

  if (path.includes('/agent/contract'))
    return transformContract(raw);

  if (path.includes('/recommendations/documents'))
    return transformDocuments(Array.isArray(raw) ? raw : []);

  if (path.includes('/recommendations/cases'))
    return transformCases(Array.isArray(raw) ? raw : []);

  if (path.includes('/recommendations/templates'))
    return transformTemplates(Array.isArray(raw) ? raw : []);

  if (path.includes('/recommendations/risks'))
    return transformRisks(Array.isArray(raw) ? raw : []);

  if (path.includes('/recommendations/checklists'))
    return transformChecklists(Array.isArray(raw) ? raw : []);

  if (path.includes('/recommendations/behavior/profile'))
    return transformProfile(raw);

  if (path.includes('/recommendations/behavior/digest'))
    return transformDigest(raw);

  // proactive, peers, next-action, interactions/log — pass through
  return raw;
}

// REAL API INTERFACE
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-User-ID': getUserId(),
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || err.message || detail;
    } catch {
      // ignore parse error
    }
    throw new Error(`Lỗi ${res.status}: ${detail}`);
  }

  const raw = await res.json();
  return applyTransform(path, options.method || 'GET', raw) as T;
}

// ADMIN API INTERFACE
import { getAdminKey } from './adminAuth';

export interface AdminDocument {
  doc_id: string;
  filename: string;
  status: string;
  created_at: string;
  is_global: boolean;
  metadata: Record<string, any>;
}

export interface AdminJob {
  job_id: string;
  doc_id: string;
  user_id: string;
  status: string;
  created_at: string;
  completed_at: string | null;
  error: string | null;
  checkpoint: Record<string, any> | null;
}

export interface AdminUploadResult {
  uploaded: AdminDocument[];
  errors: Array<{ filename: string; error: string }>;
}

export interface AdminStats {
  documents_total: number;
  documents_global: number;
  jobs_total: number;
  jobs_by_status: Record<string, number>;
  mongodb: Record<string, number>;
}

async function adminFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const adminKey = getAdminKey() || '';
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'X-Admin-Key': adminKey,
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || err.message || detail;
    } catch { /* ignore */ }
    throw new Error(`Lỗi ${res.status}: ${detail}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function adminUploadDocuments(files: File[]): Promise<AdminUploadResult> {
  const form = new FormData();
  for (const f of files) form.append('files', f);
  return adminFetch<AdminUploadResult>('/admin/documents/upload', { method: 'POST', body: form });
}

export async function adminGetDocuments(params?: { status?: string; limit?: number }): Promise<AdminDocument[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set('status', params.status);
  if (params?.limit) qs.set('limit', String(params.limit));
  const q = qs.toString() ? `?${qs}` : '';
  return adminFetch<AdminDocument[]>(`/admin/documents${q}`);
}

export async function adminDeleteDocument(docId: string): Promise<void> {
  return adminFetch<void>(`/admin/documents/${docId}`, { method: 'DELETE' });
}

export async function adminReprocessDocument(docId: string): Promise<AdminJob> {
  return adminFetch<AdminJob>(`/admin/documents/${docId}/reprocess`, { method: 'POST' });
}

export async function adminGetJobs(params?: { status?: string; limit?: number }): Promise<AdminJob[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set('status', params.status);
  if (params?.limit) qs.set('limit', String(params.limit));
  const q = qs.toString() ? `?${qs}` : '';
  return adminFetch<AdminJob[]>(`/admin/jobs${q}`);
}

export async function adminGetStats(): Promise<AdminStats> {
  return adminFetch<AdminStats>('/admin/stats');
}

// ---------------------------------------------------------------------------
// Phase 13 — Evidence Gap, Timeline, Journey, Feed, Role-based Recs
// ---------------------------------------------------------------------------

export interface EvidenceItem {
  item: string;
  priority: 'high' | 'medium' | 'low';
  category: string;
}

export interface EvidenceGapResult {
  request_id: string;
  domain: string;
  missing_evidence: EvidenceItem[];
  strong_evidence: string[];
  weak_evidence: string[];
  coverage_score: number;
  priority_items: EvidenceItem[];
  advice: string;
  summary: string;
  confidence: number;
  warnings: string[];
}

export async function getEvidenceGap(
  situation: string,
  domain: string,
  facts: string[],
  sessionId = '',
): Promise<EvidenceGapResult> {
  return apiFetch<EvidenceGapResult>('/analysis/evidence-gap', {
    method: 'POST',
    body: JSON.stringify({ situation, domain, facts, session_id: sessionId }),
  });
}

export interface DeadlineItem {
  label: string;
  days: number;
  unit: string;
  note: string;
}

export interface TimelineResult {
  request_id: string;
  stage: string;
  stage_label: string;
  stage_confidence: number;
  progress_percent: number;
  typical_deadlines: DeadlineItem[];
  alerts: string[];
  next_stage: string;
  next_stage_label: string;
  summary: string;
  warnings: string[];
}

export async function getTimeline(
  situation: string,
  domain: string,
  facts: string[] = [],
): Promise<TimelineResult> {
  return apiFetch<TimelineResult>('/analysis/timeline', {
    method: 'POST',
    body: JSON.stringify({ situation, domain, facts }),
  });
}

export interface JourneyMilestone {
  key: string;
  title: string;
  status: 'done' | 'in_progress' | 'pending' | 'warning';
  summary: string;
  detail: string;
  action_url: string;
}

export interface LawRef {
  title: string;
  score: number;
}

export interface JourneyResult {
  request_id: string;
  situation: string;
  domain: string;
  current_stage: string;
  stage_label: string;
  progress_percent: number;
  stage_confidence: number;
  milestones: JourneyMilestone[];
  evidence_coverage: number;
  evidence_missing_count: number;
  evidence_priority_count: number;
  risk_level: 'low' | 'medium' | 'high';
  risk_summary: string;
  next_steps: string[];
  alerts: string[];
  law_references: LawRef[];
  summary: string;
  confidence: number;
  warnings: string[];
}

export async function buildJourney(
  situation: string,
  sessionId = '',
  facts: string[] = [],
  domain?: string,
): Promise<JourneyResult> {
  return apiFetch<JourneyResult>('/journey/build', {
    method: 'POST',
    body: JSON.stringify({ situation, session_id: sessionId, facts, domain }),
  });
}

export interface FeedItem {
  type: 'law' | 'template' | 'checklist' | 'case' | 'topic';
  title: string;
  reason: string;
  score: number;
  action_url: string;
}

export interface FeedResult {
  user_id: string;
  feed_items: FeedItem[];
  source: 'behavior' | 'default';
}

export async function getPersonalizedFeed(): Promise<FeedResult> {
  return apiFetch<FeedResult>('/feed/personalized');
}

export interface QuickLink {
  label: string;
  url: string;
}

export interface PersonaRecommendResult {
  role: string;
  persona_label: string;
  pack_explanation: string;
  recommended_topics: string[];
  recommended_templates: string[];
  recommended_checklists: string[];
  quick_links: QuickLink[];
}

export async function getRecommendationsByRole(role: string): Promise<PersonaRecommendResult> {
  return apiFetch<PersonaRecommendResult>('/recommendations/by-role', {
    method: 'POST',
    body: JSON.stringify({ role }),
  });
}

// ---------------------------------------------------------------------------
// Phase 14 — Document viewer, evidence upload, interactions, trace, checklist
// ---------------------------------------------------------------------------

export interface DocumentContent {
  doc_id: string;
  filename: string;
  status: string;
  chunk_count: number;
  law_type: string;
  extracted_text: string;
}

export async function getDocumentContent(docId: string): Promise<DocumentContent> {
  return apiFetch<DocumentContent>(`/documents/${docId}/content`);
}

export function downloadDocument(docId: string): void {
  const url = `${API_BASE}/documents/${docId}/download`;
  const a = document.createElement('a');
  a.href = url;
  a.setAttribute('download', '');
  // pass X-User-ID via fetch + blob to support auth header
  fetch(url, { headers: { 'X-User-ID': getUserId() } })
    .then(r => r.blob())
    .then(blob => {
      const blobUrl = URL.createObjectURL(blob);
      a.href = blobUrl;
      a.click();
      URL.revokeObjectURL(blobUrl);
    })
    .catch(() => { window.open(url, '_blank'); });
}

export interface EvidenceUploadResult {
  evidence_id: string;
  session_id: string;
  filename: string;
  snippet: string;
  char_count: number;
  status: string;
}

export async function uploadEvidence(sessionId: string, file: File): Promise<EvidenceUploadResult> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/evidence`, {
    method: 'POST',
    headers: { 'X-User-ID': getUserId() },
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Lỗi ${res.status}`);
  }
  return res.json();
}

export interface InteractionLogPayload {
  action_type: string;
  doc_id?: string;
  chunk_id?: string;
  context?: Record<string, any>;
}

export function logInteraction(payload: InteractionLogPayload): void {
  apiFetch('/interactions/log', {
    method: 'POST',
    body: JSON.stringify(payload),
  }).catch(() => {});
}

export interface TraceStage {
  stage_name: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  input_summary: string;
  output_summary: string;
  warnings: string[];
  error: string | null;
}

export interface ReasoningTrace {
  trace_id: string;
  session_id: string;
  user_id: string;
  query: string;
  created_at: string;
  stages: TraceStage[];
}

export async function getTrace(traceId: string): Promise<ReasoningTrace | null> {
  try {
    return await apiFetch<ReasoningTrace>(`/intelligence/trace/${traceId}`);
  } catch {
    return null;
  }
}

export interface ChecklistProgressResult {
  checklist_id: string;
  checked_items: string[];
}

export async function getChecklistProgress(checklistId: string): Promise<ChecklistProgressResult> {
  return apiFetch<ChecklistProgressResult>(`/recommendations/checklists/${checklistId}/progress`);
}

export async function saveChecklistProgress(checklistId: string, checkedItems: string[]): Promise<void> {
  await apiFetch(`/recommendations/checklists/${checklistId}/progress`, {
    method: 'POST',
    body: JSON.stringify({ checked_items: checkedItems }),
  });
}
