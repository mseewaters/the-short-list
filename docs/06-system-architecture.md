# the-short-list — System Architecture

**Version:** 0.1  
**Purpose:** Define the target architecture and phased implementation approach.

---

## 1. Architecture Goals

the-short-list is both a product prototype and a learning vehicle for multi-agent orchestration.

The architecture should optimize for:

- Fast iteration.
- Visible intermediate state.
- Structured outputs.
- Easy debugging.
- Clean separation between agents, deterministic code, and UI.
- Ability to grow into AWS deployment without starting there.

---

## 2. MVP Architecture

```text
Vue 3 Frontend
  ↓ REST JSON
FastAPI Backend
  ↓
LangGraph Workflow
  ↓
Agent Nodes + Deterministic Tools
  ↓
Local Storage / Cache
```

---

## 3. Why LangGraph First

The goal is to learn agent orchestration. Therefore, LangGraph should own orchestration in the MVP.

Avoid adding Step Functions, SQS, or distributed workflow infrastructure until the graph itself is useful and stable.

The first learning objective is:

```text
Can we see each agent node receive state, transform it, and pass it forward?
```

---

## 4. Logical Components

### Frontend

- Vue 3 Composition API.
- Stage-based UI.
- Requirements panel.
- Activity feed.
- Results and traceability views.

### Backend API

- FastAPI.
- Session endpoints.
- Clarify endpoint.
- Search endpoint.
- Optional polling endpoint.

### LangGraph Runtime

- Maintains graph state.
- Executes nodes.
- Emits activity events.
- Returns structured results.

### Tool Layer

Tools should be deterministic where possible:

- Web search tool.
- Page fetch tool.
- PDF/manual parser.
- Spec extractor.
- Scoring function.
- Cache lookup.

Agents call tools. Agents should not secretly browse or mutate state outside the graph contract.

### Storage

MVP progression:

1. In-memory.
2. Local JSON/SQLite.
3. DynamoDB/S3.

---

## 5. Suggested Repository Structure

```text
the-short-list/
  README.md
  docs/
    01-product-spec.md
    02-ui-ux-spec.md
    03-domain-model.md
    04-agent-contracts.md
    05-api-contracts.md
    06-system-architecture.md
    07-backlog.md
  frontend/
    package.json
    src/
      components/
      views/
      stores/
      api/
  backend/
    pyproject.toml
    app/
      main.py
      api/
      graph/
        state.py
        workflow.py
        nodes/
      domain/
        models.py
        scoring.py
      tools/
        web_search.py
        fetch_page.py
        evidence.py
      storage/
  tests/
    fixtures/
    evals/
```

---

## 6. Graph Shape

### Clarification Graph

```text
User Message
  ↓
Intent Agent
  ↓
Requirements Agent
  ↓
Ready Decision
  ├── Not ready → Agent question to UI
  └── Ready → Confirm stage
```

### Search Graph

```text
Confirmed SearchIntent
  ↓
Category Schema Agent
  ↓
Product Discovery Agent
  ↓
Evidence Collection Agent
  ↓
Verification Agent
  ↓
Scoring Agent
  ↓
Recommendation Agent
  ↓
Results
```

---

## 7. Deterministic vs Agentic Responsibilities

### Use LLM/Agent For

- Interpreting messy user language.
- Creating category decision attributes.
- Normalizing marketing language.
- Explaining tradeoffs.
- Generating final human-readable recommendations.

### Use Deterministic Code For

- Stage transitions.
- Scoring math where possible.
- Budget filtering.
- Deduplication.
- Cache lookup.
- Source precedence rules.
- Retry limits.

---

## 8. Evidence and Trust Architecture

Evidence is a first-class object.

Do not let product cards contain unsupported claims.

```text
Source page/manual
  ↓
Extracted claim
  ↓
Normalized attribute/value
  ↓
EvidenceItem
  ↓
ProductAttribute
  ↓
RequirementResult
  ↓
Recommendation
```

Source precedence:

1. Manufacturer manual.
2. Manufacturer product page.
3. Reputable specialist review.
4. Retailer page.
5. User reviews for experiential claims only.

When sources conflict, prefer technical primary sources or mark unknown.

---

## 9. Activity Events

Every graph node should emit activity events.

Example:

```json
{
  "node": "product_discovery_agent",
  "status": "complete",
  "label": "Found 6 candidate products",
  "detail": "Filtered out 4 products above budget"
}
```

The frontend activity feed should render these events instead of fake timed steps.

---

## 10. MVP Implementation Phases

### Phase 0 — Prototype Shell

- Existing UI shell.
- Hardcoded script/data.
- No backend.

### Phase 1 — Backend Skeleton

- FastAPI app.
- `/sessions`, `/clarify`, `/search` endpoints.
- LangGraph workflow with stub nodes.
- UI calls backend.

### Phase 2 — Real Clarification

- Real Requirements Agent.
- Structured SearchIntent.
- Confirm stage driven by API.

### Phase 3 — Real Category Model

- Category Schema Agent.
- Dynamic decision attributes.
- Initial tests for robot vacuum, ceiling fan, and projector.

### Phase 4 — First Research Tooling

- Product discovery.
- Evidence capture.
- Cache evidence.

### Phase 5 — Trust Layer

- Verification.
- Contradiction detection.
- Requirement traceability.

### Phase 6 — Polish and Demo

- Father's Day demo flow.
- Error states.
- Deployed or locally hosted demo.

---

## 11. Future AWS Architecture

When ready:

```text
CloudFront / S3 or Amplify
  ↓
API Gateway
  ↓
Lambda / FastAPI Adapter
  ↓
LangGraph Runtime
  ↓
DynamoDB for sessions/profiles/results
S3 for raw evidence artifacts
Bedrock for model calls
CloudWatch for logs
```

Potential later additions:

- SQS for long-running extraction tasks.
- Step Functions for durable workflow orchestration.
- OpenSearch for evidence retrieval.
- Cognito for user accounts.
- EventBridge for scheduled catalog refresh.

---

## 12. Architecture Risks

### Risk: Web research becomes too broad

Mitigation: candidate cap, category restrictions, source precedence, cache.

### Risk: Agents produce unsupported recommendations

Mitigation: evidence-first model, explicit evidence IDs, recommendation guardrails.

### Risk: Overengineering delays MVP

Mitigation: no Step Functions/SQS until core graph works.

### Risk: Dynamic schemas become incoherent

Mitigation: inspect category models and add evaluation fixtures.

### Risk: UI hides uncertainty

Mitigation: confidence and missing evidence displayed in product cards.
