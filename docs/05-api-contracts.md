# the-short-list — API Contracts

**Version:** 0.2  
**Scope:** Vue frontend to FastAPI backend for MVP  
**Transport:** REST JSON  

---

## 1. API Philosophy

For MVP, keep the backend simple:

```text
Vue
  ↓ REST
FastAPI
  ↓
LangGraph workflow
  ↓
Tools and external sources
```

Do not introduce AWS Step Functions until needed.

---

## 2. Base URL

Local development:

```text
http://localhost:8000
```

Frontend environment variable:

```text
VITE_API_BASE_URL=http://localhost:8000
```

---

## 3. Authentication

MVP: none.

Use a hardcoded user ID:

```json
{
  "user_id": "default"
}
```

Post-MVP: add Cognito or another identity provider.

---

## 4. Endpoints

### POST /sessions

Create a new session.

#### Request

```json
{
  "user_id": "default"
}
```

#### Response

```json
{
  "status": "ok",
  "session_id": "sess_abc123",
  "user_context": null,
  "messages": [],
  "search_intent": null
}
```

---

### GET /sessions/{session_id}

Retrieve a session.

#### Response

```json
{
  "status": "ok",
  "session": {}
}
```

---

### POST /clarify

Send a user message and receive an agent response plus updated search intent.

#### Request

```json
{
  "session_id": "sess_abc123",
  "user_id": "default",
  "message": "I need a ceiling fan for a bedroom with low ceilings. I want it quiet and not ugly."
}
```

#### Response

```json
{
  "status": "ok",
  "agent_message": "Got it. I’m hearing low ceiling, quiet operation, and style matters. What size is the room, roughly?",
  "search_intent": {},
  "ready_to_search": false,
  "activity_events": []
}
```

When ready:

```json
{
  "status": "ok",
  "agent_message": "I think I have enough to start. Please review the requirements.",
  "search_intent": {},
  "ready_to_search": true,
  "activity_events": []
}
```

---

### POST /search

Start the research workflow.

For MVP, this may run synchronously or pseudo-asynchronously in-process.

#### Request

```json
{
  "session_id": "sess_abc123",
  "user_id": "default",
  "search_intent": {}
}
```

#### Response — synchronous MVP option

```json
{
  "status": "complete",
  "activity_events": [],
  "category_model": {},
  "candidates": [],
  "evidence_items": [],
  "evaluation_results": [],
  "recommendation_set": {}
}
```

#### Response — asynchronous option

```json
{
  "status": "accepted",
  "run_id": "run_xyz789"
}
```

---

### GET /search/{run_id}

Poll workflow state if async mode is used.

#### Running Response

```json
{
  "status": "running",
  "activity_events": [
    {
      "id": "evt_001",
      "timestamp": "2026-05-11T14:30:00Z",
      "node": "category_schema_agent",
      "status": "complete",
      "label": "Category model created",
      "detail": "Ceiling fan: size, airflow, mount type, controls, light kit, noise"
    }
  ],
  "partial_results": null,
  "error": null
}
```

#### Complete Response

```json
{
  "status": "complete",
  "activity_events": [],
  "category_model": {},
  "candidates": [],
  "evidence_items": [],
  "evaluation_results": [],
  "recommendation_set": {},
  "error": null
}
```

#### Failed Response

```json
{
  "status": "failed",
  "activity_events": [],
  "partial_results": {},
  "error": "Product discovery failed. Try broadening the request."
}
```

---

## 5. Frontend App State

```typescript
type Stage = "clarify" | "confirm" | "research" | "results";

interface AppState {
  stage: Stage;
  session_id: string | null;
  user_context: UserContext | null;
  messages: ConversationMessage[];
  search_intent: SearchIntent | null;
  category_model: CategoryModel | null;
  candidates: ProductCandidate[];
  evidence_items: EvidenceItem[];
  evaluation_results: EvaluationResult[];
  recommendation_set: RecommendationSet | null;
  activity_events: ActivityEvent[];
  run_id: string | null;
  polling: boolean;
  error: string | null;
}
```

---

## 6. Stage Transitions

| From | To | Trigger |
|---|---|---|
| clarify | confirm | `/clarify` returns `ready_to_search: true` |
| confirm | clarify | User clicks Edit |
| confirm | research | User approves search |
| research | results | Search returns complete or failed with partial results |
| results | confirm | User clicks Back |
| results | clarify | User starts a new search |

---

## 7. Error Handling

### Clarify Error

Show:

```text
I had trouble updating the requirements. Please try that message again.
```

Keep the user's typed message in the input if possible.

### Search Error with Partial Results

Show partial results with warning banner.

### Search Error with No Results

Show:

- What was attempted.
- What failed.
- Suggested next action.

### Evidence Missing

Represent as low confidence or unavailable evidence, not as a system failure.

---

## 8. Storage for MVP

Start with local JSON or SQLite if fastest.

Move to DynamoDB only when needed for deployment or learning objective.

Recommended progression:

1. In-memory local development.
2. SQLite file for persistence.
3. DynamoDB for AWS deployment.

---

## 9. Future AWS API Shape

When deploying serverlessly:

```text
API Gateway
  ↓
Lambda FastAPI adapter or individual Lambda handlers
  ↓
LangGraph runtime
  ↓
DynamoDB / S3 / external tools
```

Step Functions is deferred until workflow duration, observability, or retry requirements justify it.
