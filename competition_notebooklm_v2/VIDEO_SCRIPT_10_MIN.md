# LexAI Video Script - 10 Minutes

## Goal

Create a competition demo video that proves LexAI is a working MongoDB-powered Recommendation Engine, not only a chatbot.

Target length: 9:30-10:00.

Tone: clear, professional, confident, practical.

---

## 0:00-0:40 - Hook

**Visual:** Dark screen or LexAI dashboard, then quick cuts of legal text, analysis page, recommendation cards, MongoDB Atlas.

**Voiceover:**

"Most legal tools wait for users to know what to search. But real people do not start with legal keywords. They start with a situation: a divorce, a labor dispute, a risky contract, a land conflict. LexAI treats legal access as a recommendation problem: given a messy situation, what should the user read, prepare, and do next?"

---

## 0:40-1:30 - Product Introduction

**Visual:** LexAI homepage / Analyze page.

**Voiceover:**

"LexAI is a legal recommendation engine built on MongoDB Atlas. It analyzes a user's situation, retrieves relevant legal evidence, recommends similar cases and missing documents, and ranks the next-best actions based on context and behavior. The demo uses Vietnamese legal knowledge, but the architecture can support any high-stakes knowledge domain."

**On-screen bullets:**

- Situation analysis
- Evidence-grounded retrieval
- Next-best-action recommendations
- Behavior-based personalization
- MongoDB Vector Search + Aggregation Pipeline

---

## 1:30-3:30 - Live Demo: Analyze a Legal Situation

**Visual:** Open `/analyze`.

**Action:** Enter one prepared situation:

"Tôi muốn ly hôn, giành quyền nuôi hai con và muốn biết tài sản chung sẽ được chia như thế nào."

**Voiceover:**

"Here I enter a realistic legal situation in natural language. The user does not need to know the name of the law, the article number, or the court procedure. LexAI first identifies the legal domain, summarizes the key facts, then produces an analysis with confidence, risks, legal citations, and recommended next steps."

**Visual highlight:**

- domain label,
- confidence/risk score,
- legal basis,
- next-best-action cards,
- citations or evidence area.

**Voiceover continuation:**

"The important point is that the response is not the final product. The response becomes a launchpad for recommendations: which evidence to collect, which timeline to follow, which risk to check, and which similar cases to compare."

---

## 3:30-5:00 - Recommendation Flow: Context Retention and Similar Cases

**Visual:** Click a recommendation card such as "Vụ việc tương tự" or "Thiếu chứng cứ".

**Voiceover:**

"When I click a recommended action, LexAI carries the legal situation into the next module. This context retention is critical for a real assistant: users should not have to retype the same facts in every tool."

**Visual:** Similar Cases page prefilled / auto-run result.

**Voiceover:**

"On the Similar Cases page, MongoDB Vector Search can compare this situation with stored legal cases by meaning, not only by exact keyword. If Vector Search or Atlas search indexes are unavailable during a demo, LexAI degrades gracefully to keyword or demo fallback so the experience remains stable instead of returning a broken page."

**Highlight:**

- result cards,
- similarity score,
- search mode label,
- legal domain / stage metadata.

---

## 5:00-6:30 - Dashboard: Behavior-Based Personalization

**Visual:** Open Dashboard.

**Voiceover:**

"Every useful interaction can become a recommendation signal. LexAI logs impressions, clicks, dismisses, and useful or not-useful feedback. The Dashboard turns those signals into a behavior profile: active sessions, dominant legal domain, saved analyses, and personalized recommendations."

**Visual highlight:**

- behavior digest,
- proactive recommendation cards,
- real metrics note,
- top legal domain,
- interaction count.

**Voiceover continuation:**

"This is where the recommendation engine becomes adaptive. The next-best-action ranking is influenced by behavior scores, not only static rules."

---

## 6:30-8:30 - MongoDB Deep Dive

### Scene A - Vector Search

**Visual:** MongoDB Atlas collection with legal chunks or cases.

**Voiceover:**

"MongoDB Atlas stores legal chunks, similar cases, user sessions, and interaction events. For semantic retrieval, legal text and user situations are embedded into 384-dimensional vectors. MongoDB Atlas Vector Search retrieves the closest legal evidence using cosine similarity and metadata filters."

**On-screen code concept:**

```javascript
{
  $vectorSearch: {
    index: "law_chunks_embedding",
    path: "embedding",
    queryVector: userSituationEmbedding,
    numCandidates: 150,
    limit: 20,
    filter: { $or: [{ user_id }, { is_global: true }] }
  }
}
```

### Scene B - Aggregation Pipeline

**Visual:** Show interactions collection or aggregation concept.

**Voiceover:**

"For recommendation, LexAI uses MongoDB Aggregation Pipelines to compute behavior profiles and peer-trending signals. The pipeline can group user interactions by legal domain, count clicks and saves, calculate active days, and feed behavior scores back into next-best-action ranking."

**On-screen bullets:**

- interactions -> behavior profile
- clicks / feedback -> action score
- legal domain frequency -> personalization
- dashboard metrics -> real product insight

---

## 8:30-9:30 - Stability, Feedback Loop, and Impact

**Visual:** Show recommendation feedback buttons and fallback-friendly result.

**Voiceover:**

"LexAI is designed for a reliable MVP demo. API errors show friendly messages. Retrieval endpoints have keyword or demo fallback. MongoDB logging failures do not break the user request. Recommendation cards log impressions, clicks, dismisses, and feedback, so the system can learn which suggestions are useful."

**Visual:** Show a recommendation card with useful/not useful buttons if available.

**Voiceover continuation:**

"The product impact is simple: people get earlier legal orientation, businesses can detect contract risk, and legal teams can triage cases faster. The same architecture can be adapted to compliance, tax, insurance, or any complex knowledge domain."

---

## 9:30-10:00 - Closing

**Visual:** LexAI logo + MongoDB Atlas + final app screen.

**Voiceover:**

"LexAI demonstrates a complete MongoDB-powered recommendation engine: semantic retrieval with Vector Search, behavior learning with Aggregation Pipelines, session memory, evidence-grounded legal analysis, and actionable next-best recommendations. LexAI recommends not just information, but the next responsible legal step."

---

## Recording Notes

- Keep the demo flow narrow and smooth.
- Do not show every sidebar module.
- Prepare data before recording so Dashboard is not empty.
- Record voice separately if possible.
- Keep browser zoom high enough for judges to read.
- Have screenshots ready in case live API or Atlas is slow.
