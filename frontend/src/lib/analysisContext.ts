/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export interface AnalysisNavState {
  domain?: string;
  sessionId?: string;
  traceId?: string;
  summary?: string;
  citations?: string[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object';
}

function asString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined;
}

export function getAnalysisContext(state: unknown): AnalysisNavState {
  if (!isRecord(state)) return {};

  return {
    domain: asString(state.domain),
    sessionId: asString(state.sessionId),
    traceId: asString(state.traceId),
    summary: asString(state.summary),
    citations: Array.isArray(state.citations)
      ? state.citations.filter((item): item is string => typeof item === 'string')
      : undefined,
  };
}

export function getContextSummary(state: unknown, fallback = ''): string {
  return getAnalysisContext(state).summary || fallback;
}

export function getContextDomain(state: unknown, fallback = 'general'): string {
  return getAnalysisContext(state).domain || fallback;
}
