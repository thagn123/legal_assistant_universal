/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type TabType = 'Analysis' | 'Documents' | 'Recommendations' | 'History';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  domain?: string;
  traceId?: string;
}

export interface LawChunk {
  id: string;
  title: string;
  content: string;
  score: number;
  sources: string[];
}

export interface RecommendedAction {
  id: string;
  title: string;
  description: string;
  urgency: 'Immediately' | 'Within30Days' | 'Optional';
}

export interface RiskWarning {
  id: string;
  content: string;
  level: 'High' | 'Medium' | 'Low';
}

export interface RankingSignal {
  label: string;
  value: number;
  score: number;
}

export interface AnalysisResult {
  status: 'Strong' | 'Average' | 'Weak';
  score: number;
  reasoning: string;
  domain: string;
  laws: LawChunk[];
  actions: RecommendedAction[];
  warnings: RiskWarning[];
  rankingSignals: RankingSignal[];
}

export interface Document {
  id: string;
  name: string;
  type: 'pdf' | 'docx' | 'html' | 'image';
  domain: string;
  date: string;
  chunkCount: number;
}

export interface Session {
  id: string;
  date: string;
  firstQuery: string;
  domain: string;
  messages: Message[];
}
