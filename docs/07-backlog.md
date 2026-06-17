# the-short-list — Scrum Backlog

**Version:** 0.1  
**Planning horizon:** Father's Day MVP  

---

## Epic 1 — Product Foundation

### Story 1.1 — Create repository structure

**As a developer,** I want a clean monorepo structure so that frontend, backend, docs, and tests are easy to navigate.

**Acceptance criteria**

- Repo contains `/frontend`, `/backend`, `/docs`, and `/tests`.
- README explains product goal and local setup.
- Docs from this folder are committed under `/docs`.

**Priority:** High  
**Sprint:** 1

---

### Story 1.2 — Define shared domain models

**As a developer,** I want shared domain contracts so that the UI, API, and agents use the same vocabulary.

**Acceptance criteria**

- Domain models exist for SearchIntent, Requirement, CategoryModel, ProductCandidate, EvidenceItem, EvaluationResult, and RecommendationSet.
- Backend uses these models for typed responses.
- Frontend has matching TypeScript interfaces.

**Priority:** High  
**Sprint:** 1

---

## Epic 2 — Frontend Shell

### Story 2.1 — Convert prototype to Vue shell

**As a user,** I want the prototype flow in Vue so that the MVP stack matches the intended implementation.

**Acceptance criteria**

- Vue app has Understand, Confirm, Research, and Results stages.
- UI visually matches the prototype closely enough for demo.
- Static mock data renders correctly.

**Priority:** High  
**Sprint:** 1

---

### Story 2.2 — Requirements panel from API state

**As a user,** I want to see requirements update as I talk so that I know the system understands me.

**Acceptance criteria**

- Requirements panel renders from SearchIntent requirements.
- Requirement count updates.
- Empty state displays before requirements exist.

**Priority:** High  
**Sprint:** 2

---

### Story 2.3 — Activity feed

**As a user,** I want to see what the research workflow is doing so that I trust the process.

**Acceptance criteria**

- Research screen renders activity events from backend.
- Events support complete, warning, running, and failed states.
- Fake fixed timers are removed or isolated as demo fallback.

**Priority:** High  
**Sprint:** 3

---

### Story 2.4 — Product cards with evidence

**As a user,** I want expandable product cards so that I can see summary first and evidence when needed.

**Acceptance criteria**

- Product cards render score, verdict, confidence, and price.
- Expanded card shows requirement results.
- Evidence snippets are linked to requirement results.

**Priority:** High  
**Sprint:** 4

---

## Epic 3 — Backend and LangGraph Skeleton

### Story 3.1 — Create FastAPI backend

**As a developer,** I want a FastAPI backend so the frontend can call real endpoints.

**Acceptance criteria**

- `/health` returns ok.
- `/sessions` creates a session.
- Local dev server runs with one command.

**Priority:** High  
**Sprint:** 1

---

### Story 3.2 — Create LangGraph state and stub workflow

**As a developer,** I want a stub LangGraph workflow so that orchestration is visible before agents are smart.

**Acceptance criteria**

- Graph state includes session, messages, search intent, activity events, and errors.
- Stub graph runs end-to-end.
- Each node emits an activity event.

**Priority:** High  
**Sprint:** 1

---

### Story 3.3 — Wire frontend to backend

**As a developer,** I want the frontend to call backend APIs so that static prototype data is removed.

**Acceptance criteria**

- App creates session on load.
- User message calls `/clarify`.
- Search button calls `/search`.
- Results render from API response.

**Priority:** High  
**Sprint:** 2

---

## Epic 4 — Clarification and Requirements

### Story 4.1 — Implement Intent Agent

**As a user,** I want the system to understand what product category I mean so that the search starts in the right domain.

**Acceptance criteria**

- Agent returns category label and confidence.
- Agent distinguishes shopper from final user when possible.
- Unsupported requests are handled gracefully.

**Priority:** High  
**Sprint:** 2

---

### Story 4.2 — Implement Requirements Agent

**As a user,** I want my messy input translated into clear requirements so that I can confirm the system understood me.

**Acceptance criteria**

- Agent returns structured SearchIntent.
- Requirements preserve user language and interpreted need.
- Agent asks missing follow-up questions.
- `ready_to_search` becomes true when enough information exists.

**Priority:** High  
**Sprint:** 2

---

### Story 4.3 — Confirm and edit requirements

**As a user,** I want to review and edit my requirements before research begins.

**Acceptance criteria**

- Confirm stage appears when backend indicates ready.
- User can approve search.
- User can return to clarify and add/change requirements.

**Priority:** High  
**Sprint:** 2

---

## Epic 5 — Dynamic Category Modeling

### Story 5.1 — Implement Category Schema Agent

**As a user,** I want the system to know what matters for the product category so that recommendations are based on meaningful attributes.

**Acceptance criteria**

- Agent creates CategoryModel with decision attributes.
- Category model includes disqualifiers and situational attributes.
- Test categories include robot vacuum, ceiling fan, and projector.

**Priority:** High  
**Sprint:** 3

---

### Story 5.2 — Display category understanding in activity feed

**As a user,** I want to see how the system framed the category so that I can trust or challenge it.

**Acceptance criteria**

- Activity feed shows category identified.
- Activity feed summarizes key decision attributes.
- User can see a warning if category confidence is low.

**Priority:** Medium  
**Sprint:** 3

---

## Epic 6 — Product Discovery and Evidence

### Story 6.1 — Implement product discovery tool

**As a user,** I want the system to find candidate products so that I don't have to search manually.

**Acceptance criteria**

- Tool returns 3–7 candidate products.
- Candidates include name, brand, URL, and price if available.
- Discovery sources are captured.

**Priority:** High  
**Sprint:** 3

---

### Story 6.2 — Implement evidence extraction

**As a user,** I want product claims backed by sources so that I can trust the recommendation.

**Acceptance criteria**

- EvidenceItem objects are created for important claims.
- Evidence includes source URL, source type, extracted claim, normalized attribute, and confidence.
- Manufacturer sources are preferred when available.

**Priority:** High  
**Sprint:** 4

---

### Story 6.3 — Cache evidence

**As a developer,** I want evidence cached so repeated searches are faster and cheaper.

**Acceptance criteria**

- Evidence is stored locally or in a lightweight database.
- Cache key includes product identifier and source URL.
- Cached evidence includes fetched timestamp.

**Priority:** Medium  
**Sprint:** 4

---

## Epic 7 — Verification and Scoring

### Story 7.1 — Implement contradiction detection

**As a user,** I want conflicting product claims flagged so that I do not rely on bad specs.

**Acceptance criteria**

- System compares evidence across sources for key attributes.
- Contradictions are recorded.
- UI can display contradiction warnings.

**Priority:** High  
**Sprint:** 4

---

### Story 7.2 — Implement requirement scoring

**As a user,** I want products ranked according to my requirements so that the best fit rises to the top.

**Acceptance criteria**

- Each product receives requirement-level results.
- Must-have failures reduce score significantly.
- Unknown evidence reduces confidence.
- Product receives overall verdict.

**Priority:** High  
**Sprint:** 4

---

### Story 7.3 — Implement requirement traceability

**As a user,** I want to understand how my words affected the recommendation.

**Acceptance criteria**

- Requirement result links to source requirement and evidence.
- UI can show user statement → interpreted need → evidence → score impact.
- At least one traceability example works end-to-end.

**Priority:** Medium  
**Sprint:** 5

---

## Epic 8 — Recommendation Experience

### Story 8.1 — Implement Recommendation Agent

**As a user,** I want a clear final recommendation so that I can make a decision without reading every detail.

**Acceptance criteria**

- Agent generates summary from EvaluationResults only.
- Recommendation identifies best choice if confidence is sufficient.
- Recommendation includes caveats and tradeoffs.
- No unsupported new claims appear.

**Priority:** High  
**Sprint:** 5

---

### Story 8.2 — Show final recommendation on demand

**As a user,** I want the recommendation separate from the result details so that I am not overwhelmed.

**Acceptance criteria**

- Button reveals recommendation.
- Recommendation renders markdown safely.
- User can start a new search.

**Priority:** High  
**Sprint:** 5

---

## Epic 9 — Evaluation and Demo Readiness

### Story 9.1 — Create evaluation fixtures

**As a developer,** I want repeatable test cases so that I can tell if the agents are improving.

**Acceptance criteria**

- Fixtures exist for robot vacuum, ceiling fan, and projector.
- Expected requirements are defined for each fixture.
- Agent outputs can be compared manually or automatically.

**Priority:** Medium  
**Sprint:** 5

---

### Story 9.2 — Father's Day demo flow

**As a product owner,** I want a polished demo path so that the MVP can be shown confidently.

**Acceptance criteria**

- One end-to-end scenario runs reliably.
- UI handles errors gracefully.
- Recommendation includes evidence and confidence.
- Demo can be run locally or from a simple hosted URL.

**Priority:** High  
**Sprint:** 5
