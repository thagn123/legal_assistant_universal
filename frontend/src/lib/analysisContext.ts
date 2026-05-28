/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect, useState } from 'react';

export interface AnalysisNavState {
  domain?: string;
  sessionId?: string;
  traceId?: string;
  summary?: string;
  situation?: string;
  citations?: string[];
}

const SITUATION_KEY = 'lexai_current_situation';

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
    situation: asString(state.situation),
    citations: Array.isArray(state.citations)
      ? state.citations.filter((item): item is string => typeof item === 'string')
      : undefined,
  };
}

export function getStoredSituation(): string {
  try {
    return sessionStorage.getItem(SITUATION_KEY) || '';
  } catch {
    return '';
  }
}

export function setStoredSituation(value: string): void {
  try {
    const trimmed = value.trim();
    if (trimmed) {
      sessionStorage.setItem(SITUATION_KEY, trimmed);
    }
  } catch {
    // sessionStorage can be disabled in private or embedded browsers.
  }
}

export function getContextSummary(state: unknown, fallback = ''): string {
  const context = getAnalysisContext(state);
  return context.situation || context.summary || getStoredSituation() || fallback;
}

export function getContextDomain(state: unknown, fallback = 'general'): string {
  return getAnalysisContext(state).domain || fallback;
}

export function useSyncedSituation(state: unknown, fallback = '') {
  const [situation, setSituationState] = useState(() => getContextSummary(state, fallback));

  useEffect(() => {
    const next = getContextSummary(state, fallback);
    if (next && next !== situation && !situation.trim()) {
      setSituationState(next);
    }
  }, [fallback, state]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    setStoredSituation(situation);
  }, [situation]);

  const setSituation = (value: string) => {
    setSituationState(value);
    setStoredSituation(value);
  };

  return [situation, setSituation] as const;
}
