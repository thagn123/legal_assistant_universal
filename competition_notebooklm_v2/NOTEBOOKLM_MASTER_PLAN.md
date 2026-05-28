# LexAI Competition Master Plan

## NotebookLM Instruction

Use this document to generate a professional competition slide deck and demo video outline for LexAI. The target audience is a judging panel for a MongoDB-focused AI / Recommendation Engine competition. The tone should be confident, clear, technical but easy to understand. Avoid hype. Emphasize working MVP, MongoDB Atlas, Vector Search, Aggregation Pipeline, behavior-based recommendation, session memory, and a real legal-analysis user flow.

---

## One-Sentence Pitch

LexAI is a MongoDB-powered legal recommendation engine that turns a user's natural-language legal situation into grounded analysis, relevant legal evidence, similar cases, and next-best actions personalized by user behavior.

---

## Competition Positioning

LexAI should not be presented as only a legal chatbot.

It should be positioned as:

> A domain-specialized Recommendation Engine, demonstrated on one of the hardest domains: Vietnamese legal knowledge.

This framing is stronger because:

- Legal users often do not know the right keywords, articles, or procedures.
- Legal text is long, formal, frequently updated, and citation-sensitive.
- Wrong recommendations can create real risk, so the engine must combine semantic retrieval, evidence grounding, user context, and fallback behavior.
- MongoDB Atlas is used as the operational core: vector retrieval, document storage, behavior logs, aggregation-based analytics, and recommendation signals.

---

## Why LexAI Matters

Most people do not start with a legal question. They start with a messy story:

- "I want a divorce and custody of my children."
- "My company fired me without notice."
- "I signed a land purchase agreement by handwritten paper."
- "This contract clause looks risky but I do not know why."

Traditional search expects keywords. LexAI understands situations.

LexAI turns a messy situation into:

- The likely legal domain.
- A concise legal analysis.
- Relevant laws and citations.
- Similar cases or patterns.
- Missing evidence.
- Risks and timelines.
- Next-best actions ranked for the user.

---

## Recommended Submission Choice

### Best Base Folder: `competition/`

Use this as the primary source because it is already aligned with the judging lens:

- MongoDB Recommendation Engine.
- Vector Search.
- Aggregation Pipeline.
- Collaborative filtering.
- Personalization.
- Slide content ready for NotebookLM.
- Technical documentation with schema and code-oriented proof points.

### Best Narrative Source: `video/`

Use this as supporting material because it has:

- Stronger voiceover style.
- More concrete demo scenes.
- Better product storytelling.
- A clear sense of premium UX.

### Final Strategy

Submit and present the V2 hybrid:

> Start with the human legal-access problem, prove the product through one complete legal-analysis flow, then prove the engineering depth through MongoDB Vector Search and Aggregation-based recommendations.

---

## Slide Deck

### Slide 1 - Title

**Title:** LexAI - MongoDB-Powered Legal Recommendation Engine

**Subtitle:** Personalized legal guidance from situation analysis to next-best action

**Tagline:** Legal knowledge, recommended at the moment of need.

**Visual:** LexAI interface + MongoDB Atlas + scales of justice.

---

### Slide 2 - The Problem

Legal access is a recommendation problem.

Users rarely know:

- Which law applies.
- Which evidence is missing.
- Which risk is urgent.
- Which action should come first.

Vietnamese legal information is difficult for non-experts because:

- Regulations are long and formal.
- Legal concepts are interconnected.
- People describe problems in everyday language, not legal keywords.
- A generic answer without evidence can be misleading.

**Key message:** The hard part is not only answering. The hard part is recommending the right legal path.

---

### Slide 3 - The Solution

LexAI analyzes a user's legal situation and recommends what to do next.

Core capabilities:

- **Situation analysis:** classify legal domain and summarize facts.
- **Evidence-grounded retrieval:** find relevant law chunks, similar cases, clauses, and checklists.
- **Recommendation engine:** rank next-best actions using legal context and behavior signals.
- **Memory and personalization:** keep cross-session context and adapt recommendations over time.
- **Fallback stability:** continue demo and retrieval even when vector index or external services are unavailable.

---

### Slide 4 - MVP User Flow

Recommended demo flow:

1. User enters a legal situation in "Analyze".
2. LexAI returns legal analysis, confidence, risks, and evidence-backed suggestions.
3. User sees Next Best Actions.
4. User clicks "Similar Cases" or "Evidence Gap".
5. Context is retained automatically.
6. Dashboard updates with real behavior and recommendation signals.

**Why this flow wins:** It shows product value, context retention, recommendation ranking, and MongoDB-backed behavior analytics in one story.

---

### Slide 5 - Architecture Overview

LexAI uses a staged intelligence pipeline:

1. **Query Planning:** detect domain, entities, intent.
2. **Session and User Memory:** load recent conversation and long-term preferences.
3. **Retrieval Fusion:** combine vector search, keyword/BM25, graph links, and behavior boost.
4. **GraphRAG:** traverse legal relationships such as cites, amends, overrides, and related concepts.
5. **Reasoning:** generate grounded legal analysis with citations.
6. **Recommendation Ranking:** rank laws, risks, actions, cases, and documents.
7. **Persist and Learn:** store sessions, interactions, feedback, and future signals.

**Core stack:** FastAPI, MongoDB Atlas, React/Vite/TypeScript, sentence-transformers, OpenAI, local deterministic fallbacks.

---

### Slide 6 - MongoDB Atlas as the Engine

MongoDB is not only used as a storage layer.

LexAI uses MongoDB for:

- Legal chunks and embeddings.
- Similar legal cases.
- Contract clause examples.
- User interactions.
- Conversation sessions.
- Long-term user memory.
- Recommendation feedback.
- Aggregation-based behavioral profiles.

**Key message:** MongoDB powers retrieval, analytics, personalization, and resilience.

---

### Slide 7 - Vector Search

LexAI uses MongoDB Atlas Vector Search for semantic legal retrieval.

Instead of searching exact keywords, the system embeds legal text and user situations into a shared vector space.

This enables:

- Natural-language legal search.
- Cross-wording matches.
- Similar-case retrieval.
- Clause and document recommendations.
- Vietnamese/English semantic matching when supported by the embedding model.

Example:

> A user says "company fired me without notice."  
> LexAI can retrieve labor-law provisions about termination even if the user never says the exact article name.

---

### Slide 8 - Aggregation Pipeline Recommendations

LexAI uses MongoDB Aggregation Pipelines to turn behavior into recommendations.

Signals include:

- What the user viewed.
- Which recommendations were clicked.
- Which recommendations were dismissed.
- Useful / not useful feedback.
- Legal domains repeatedly analyzed.
- Similar users or similar sessions.

Aggregation can produce:

- Top legal domains for a user.
- Active usage patterns.
- Peer-trending documents.
- Behavior scores for next-best-action ranking.
- Dashboard metrics based on real interaction history.

**Key message:** Recommendation quality improves as users interact.

---

### Slide 9 - Recommendation Engine

LexAI ranks recommendations with multiple signals:

- Semantic relevance.
- Legal graph relevance.
- User behavior score.
- Freshness / recency.
- Popularity across interactions.
- Feedback acceptance rate.

The most important MVP point:

> Recommendations are actionable. They do not only say "read more"; they send the user to the next useful module, such as similar cases, evidence gaps, timelines, risks, or legal clauses.

---

### Slide 10 - Feedback Loop

The product includes a demo-ready recommendation feedback loop:

- Recommendation impression is logged when a card is shown.
- Click is logged when the user opens a recommended module.
- Dismiss is logged when the user hides it.
- Useful / not useful feedback is stored.
- Behavior score feeds back into next-best-action ranking.

This proves LexAI is not a static prompt system. It is a learning recommendation experience.

---

### Slide 11 - Demo Scene

Demo example:

> "I want to divorce, keep custody of my children, and understand how shared property will be divided."

LexAI should show:

- Domain: civil / family law.
- Analysis summary.
- Legal basis with citations.
- Confidence and risk signals.
- Recommended next actions:
  - collect marriage and child documents,
  - review custody criteria,
  - estimate property split,
  - search similar cases,
  - prepare court timeline.

Then click into "Similar Cases" and show that the previous situation is retained.

---

### Slide 12 - Product Modules That Matter for MVP

For the competition video, avoid showing every module.

Show only the modules that reinforce the recommendation story:

- **Analyze:** main input and legal analysis.
- **Next Best Actions:** recommendation cards.
- **Similar Cases:** semantic retrieval and fallback.
- **Evidence Gap:** actionability and missing proof.
- **Dashboard:** behavior-based personalization.
- **MongoDB Atlas:** technical proof.

Optional if time remains:

- Contract review.
- Admin ingestion pipeline.

---

### Slide 13 - Stability and Fallbacks

LexAI is designed for demo stability:

- API errors show clear frontend messages.
- Retrieval endpoints degrade to keyword / demo fallback when vector search is unavailable.
- MongoDB interaction logging failures do not break user requests.
- Local SQLite fallback supports behavior recommendations in reduced environments.
- Context is synchronized through session storage so module navigation does not lose the situation.

**Why judges care:** a recommendation engine must keep working under real-world failure modes.

---

### Slide 14 - Impact

LexAI can help:

- Individuals understand their rights earlier.
- Small businesses detect contract risk.
- Legal teams triage cases faster.
- Public legal services make legal knowledge more accessible.

The broader insight:

> If this recommendation engine works for legal knowledge, it can be adapted to any high-stakes knowledge domain: compliance, tax, finance, healthcare policy, insurance, or enterprise knowledge bases.

---

### Slide 15 - Closing

LexAI demonstrates a complete MongoDB-powered recommendation engine:

- Semantic retrieval with Vector Search.
- Behavior learning with Aggregation Pipelines.
- Session and user memory.
- Evidence-grounded legal analysis.
- Actionable next-best recommendations.
- Stable fallbacks for production-like reliability.

**Closing line:**

> LexAI recommends not just information, but the next responsible legal step.

---

## Technical Proof Points

Use these when NotebookLM generates speaker notes or technical slides.

### MongoDB Collections

- `law_chunks`: legal text chunks, embeddings, references, metadata.
- `legal_cases` / `law_cases`: similar cases and outcome patterns.
- `interactions`: behavior logs such as view, click, save, dismiss, feedback.
- `conversation_sessions`: short-term chat/session history.
- `user_memory`: long-term cross-session user context.
- `reasoning_traces`: staged pipeline execution traces.

### Vector Search

- 384-dimensional sentence-transformer embeddings.
- Cosine similarity.
- Used for legal document retrieval, similar cases, contract clauses, and recommendations.
- Works with metadata filters for user-specific and global documents.

### Aggregation Pipeline

Used for:

- behavior profile,
- top legal domain,
- active days,
- recommendation score,
- collaborative or peer-trending suggestions,
- dashboard metrics,
- feedback-influenced ranking.

### Recommendation Feedback Loop

Events:

- `recommendation_impression`
- `recommendation_click`
- `recommendation_dismiss`
- `recommendation_feedback`

Ranking impact:

- Useful feedback increases priority.
- Not useful and dismiss decrease priority.
- Clicks indicate intent.
- Impressions allow basic exposure tracking.

---

## Demo Checklist

Before recording:

- Prepare one strong legal situation.
- Clear browser notifications.
- Open app at `localhost:3000/analyze`.
- Open MongoDB Atlas collections in another tab.
- Prepare one screenshot backup for each critical screen.
- Make sure Dashboard has at least a few interaction logs.
- Test `similar-cases` route before recording.
- Keep the video under 10 minutes.

---

## Recommended Video Structure

Total: 9:30 to 10:00.

1. **0:00-0:40 Hook:** Legal access is a recommendation problem.
2. **0:40-1:30 Product promise:** LexAI turns messy legal situations into next steps.
3. **1:30-3:30 Live demo Analyze:** user enters situation, sees grounded analysis.
4. **3:30-5:00 Recommendation flow:** click next-best action, show retained context and similar cases.
5. **5:00-6:30 Dashboard personalization:** real behavior metrics and proactive recommendations.
6. **6:30-8:30 MongoDB deep dive:** Vector Search + Aggregation + interactions collection.
7. **8:30-9:30 Stability and impact:** fallback, memory, feedback loop.
8. **9:30-10:00 Closing:** MongoDB-powered recommendation engine for legal knowledge.

---

## Recommended Visual Style

- Dark premium UI screenshots.
- Minimal text per slide.
- One core diagram: user situation -> retrieval -> recommendation -> feedback loop.
- Use MongoDB green only as highlight, not full background.
- Use legal gold as product accent.
- Prefer real app screenshots over abstract illustrations.

---

## Final Submission Summary

LexAI is a strong competition entry because it demonstrates:

1. A difficult, meaningful domain.
2. A working MVP with end-to-end user flow.
3. Real MongoDB integration beyond CRUD.
4. A recommendation engine with behavior signals and feedback.
5. Clear social and product impact.

The strongest submission angle is:

> MongoDB Atlas powers a legal recommendation engine that understands user situations, retrieves grounded evidence, ranks next-best actions, and learns from user behavior.
