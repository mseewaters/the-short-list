# the-short-list — Agent Contracts

**Version:** 0.1  
**Purpose:** Define LangGraph node responsibilities, inputs, outputs, and guardrails.

---

## 1. Orchestration Principle

LangGraph owns the agent workflow for MVP.

Do not introduce AWS Step Functions until the LangGraph workflow is stable and worth externalizing.

The MVP graph should be explicit, inspectable, and easy to debug.

```text
User Message
  ↓
Intent Agent
  ↓
Requirements Agent
  ↓
Clarification Decision
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
```

---

## 2. Shared Graph State

```typescript
interface the-short-listGraphState {
  session_id: string;
  user_id: string;
  messages: ConversationMessage[];
  user_context?: UserContext;
  search_intent?: SearchIntent;
  category_model?: CategoryModel;
  candidate_products?: ProductCandidate[];
  evidence_items?: EvidenceItem[];
  evaluation_results?: EvaluationResult[];
  recommendation_set?: RecommendationSet;
  activity_events: ActivityEvent[];
  errors: AgentError[];
}

interface ActivityEvent {
  id: string;
  timestamp: string;
  node: string;
  status: "pending" | "running" | "complete" | "warning" | "failed";
  label: string;
  detail?: string;
}

interface AgentError {
  node: string;
  message: string;
  recoverable: boolean;
  detail?: string;
}
```

---

## 3. Intent Agent

### Responsibility

Determine what the user is trying to buy or decide, and whether the request fits the-short-list's supported scope.

### Input

- Latest user message.
- Conversation history.
- Optional prior search intent.

### Output

```typescript
interface IntentAgentOutput {
  category_label: string | null;
  category_confidence: "low" | "medium" | "high";
  decision_type: "product_purchase" | "comparison" | "research" | "unsupported";
  inferred_persona?: "family_helper" | "self_shopper" | "low_confidence_shopper";
  notes: string[];
}
```

### Guardrails

- Do not force a category when confidence is low.
- If the user is asking for a service, medical advice, legal advice, or another unsupported domain, return unsupported.
- Distinguish the shopper from the eventual user when possible.

---

## 4. Requirements Agent

### Responsibility

Extract structured requirements and identify missing information.

### Input

- Messages.
- Intent Agent output.
- Existing SearchIntent, if any.

### Output

```typescript
interface RequirementsAgentOutput {
  search_intent: SearchIntent;
  agent_message: string;
  ready_to_search: boolean;
}
```

### Guardrails

- Preserve the user's own language in `user_language`.
- Separate hard constraints from preferences.
- Ask one or two questions at a time.
- Do not over-interrogate if enough information exists to begin.
- Confidence must decrease when assumptions are made.

---

## 5. Clarification Decision Node

### Responsibility

Deterministic routing node.

### Logic

```text
If ready_to_search = true:
    route to confirm stage / category schema
Else:
    return agent question to UI
```

This should be code, not an LLM.

---

## 6. Category Schema Agent

### Responsibility

Build a temporary decision model for the product category.

### Input

- SearchIntent.
- Category label.

### Output

```typescript
interface CategorySchemaAgentOutput {
  category_model: CategoryModel;
}
```

### Guardrails

- Focus on decision attributes, not exhaustive product taxonomy.
- Include attributes implied by user context.
- Include common disqualifiers.
- Mark confidence low when category is unfamiliar or ambiguous.

### Example

For ceiling fans, attributes may include:

- Room size / blade span.
- Ceiling height / mount type.
- Airflow.
- Lighting.
- Noise.
- Controls.
- Indoor/outdoor rating.
- Style/finish.

---

## 7. Product Discovery Agent

### Responsibility

Find candidate products for the category and constraints.

### Input

- SearchIntent.
- CategoryModel.

### Output

```typescript
interface ProductDiscoveryAgentOutput {
  candidate_products: ProductCandidate[];
  discovery_notes: string[];
}
```

### Guardrails

- Prefer manufacturer and reputable retailer sources.
- Limit MVP candidates to 3–7 products.
- Avoid discontinued or unavailable products when possible.
- Capture source references for discovery.
- Do not fabricate products.

---

## 8. Evidence Collection Agent

### Responsibility

Gather evidence for important product claims.

### Input

- Candidate products.
- CategoryModel.
- SearchIntent.

### Output

```typescript
interface EvidenceCollectionAgentOutput {
  evidence_items: EvidenceItem[];
}
```

### Guardrails

- Prefer manufacturer manuals and product pages.
- Use retailer pages as secondary evidence.
- Use review sites/user reviews for experiential claims, not hard specs.
- Store source URL, accessed timestamp, and extracted claim.
- Mark unavailable evidence explicitly.

---

## 9. Verification Agent

### Responsibility

Normalize, compare, and verify product claims across sources.

### Input

- Candidate products.
- EvidenceItems.
- CategoryModel.

### Output

```typescript
interface VerificationAgentOutput {
  candidate_products: ProductCandidate[];
  contradictions: Contradiction[];
}

interface Contradiction {
  product_id: string;
  attribute: string;
  claim_a: string;
  source_a: string;
  claim_b: string;
  source_b: string;
  resolution: "prefer_manufacturer" | "prefer_manual" | "mark_unknown" | "needs_review";
  explanation: string;
}
```

### Guardrails

- Manufacturer manual beats retailer copy for technical specs.
- If sources conflict and cannot be resolved, mark unknown.
- Do not silently choose the more favorable claim.

---

## 10. Scoring Agent

### Responsibility

Evaluate each product against requirements.

This can be partly deterministic and partly LLM-assisted.

### Input

- SearchIntent.
- CategoryModel.
- Verified ProductCandidates.
- EvidenceItems.

### Output

```typescript
interface ScoringAgentOutput {
  evaluation_results: EvaluationResult[];
}
```

### Guardrails

- Must-have failures should strongly reduce score.
- Unknown evidence should reduce confidence.
- Do not let price dominate if a hard constraint fails.
- Include negative tradeoffs.

---

## 11. Recommendation Agent

### Responsibility

Generate the final plain-English recommendation.

### Input

- SearchIntent.
- EvaluationResults.
- ProductCandidates.
- EvidenceItems.

### Output

```typescript
interface RecommendationAgentOutput {
  recommendation_set: RecommendationSet;
}
```

### Guardrails

- Recommend at most three products.
- Clearly name the best choice if confidence is sufficient.
- Include when not to buy the top choice.
- Mention uncertainty and missing evidence.
- Do not introduce new unsupported claims.

---

## 12. MVP Node Sequencing

### Phase 1 — Fake but Wired

- Intent Agent: stubbed.
- Requirements Agent: real LLM.
- Category Schema Agent: stubbed.
- Product Discovery Agent: stubbed.
- Evidence Collection Agent: stubbed.
- Scoring Agent: deterministic mock.
- Recommendation Agent: real LLM over mock data.

### Phase 2 — First Real Research

- Replace Product Discovery Agent with real web search/tooling.
- Keep evidence and scoring simple.

### Phase 3 — Trust Layer

- Add Evidence Collection and Verification.
- Add confidence and contradiction display.

---

## 13. Evaluation Questions

For every agent run, log enough information to answer:

- What did the agent receive?
- What did it output?
- What assumptions did it make?
- What confidence did it assign?
- What evidence supports the result?
- Could a deterministic function have done this better?
