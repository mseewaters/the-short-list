# the-short-list — Domain Model

**Version:** 0.1  
**Purpose:** Define the core product concepts independent of UI, API, or storage implementation.

---

## 1. Domain Model Overview

the-short-list should separate stable user context, decision-specific intent, discovered product facts, evidence, and recommendations.

The most important distinction:

```text
UserContext ≠ SearchIntent
```

A user's general preferences may persist across sessions. A search intent belongs to one product decision.

---

## 2. Core Entities

```text
UserContext
  ↓
SearchSession
  ↓
SearchIntent
  ↓
CategoryModel
  ↓
ProductCandidate
  ↓
EvidenceItem
  ↓
EvaluationResult
  ↓
RecommendationSet
```

---

## 3. UserContext

Stable information that may help personalize future searches.

Examples:

- Prefers simple controls.
- Avoids app-heavy products.
- Budget-conscious.
- Buying for elderly parent.
- Likes quiet products.

Do not store sensitive or irrelevant information unless explicitly needed.

```typescript
interface UserContext {
  user_id: string;
  created_at: string;
  updated_at: string;
  stable_preferences: UserPreference[];
  default_persona?: PersonaType;
  notes?: string[];
}

type PersonaType =
  | "family_helper"
  | "self_shopper"
  | "low_confidence_shopper";

interface UserPreference {
  id: string;
  label: string;
  value: string;
  confidence: "low" | "medium" | "high";
  source: "explicit" | "inferred";
  last_confirmed_at?: string;
}
```

---

## 4. SearchSession

A single product decision workflow.

```typescript
interface SearchSession {
  session_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  status: "clarifying" | "confirmed" | "researching" | "complete" | "failed";
  messages: ConversationMessage[];
  search_intent?: SearchIntent;
  category_model?: CategoryModel;
  candidates?: ProductCandidate[];
  evaluations?: EvaluationResult[];
  recommendation_set?: RecommendationSet;
}

interface ConversationMessage {
  role: "user" | "agent" | "system";
  text: string;
  timestamp: string;
}
```

---

## 5. SearchIntent

The structured expression of what the user wants for this specific decision.

```typescript
interface SearchIntent {
  id: string;
  category_label: string | null;
  category_confidence: "low" | "medium" | "high";
  raw_requirements: Record<string, string>;
  requirements: Requirement[];
  constraints: Constraint[];
  missing_information: MissingInformation[];
  ready_to_search: boolean;
}
```

### Requirement

```typescript
interface Requirement {
  id: string;
  label: string;
  user_language: string;
  interpreted_need: string;
  priority: "must_have" | "should_have" | "nice_to_have";
  confidence: "low" | "medium" | "high";
  derived_from_message_ids: string[];
  mapped_attributes?: string[];
}
```

Example:

```json
{
  "id": "req_001",
  "label": "Easy emptying",
  "user_language": "My knees aren't great so I can't be bending down all the time",
  "interpreted_need": "Minimize frequent bending and manual maintenance",
  "priority": "must_have",
  "confidence": "high",
  "derived_from_message_ids": ["msg_001"],
  "mapped_attributes": ["self_emptying", "bin_accessibility", "maintenance_frequency"]
}
```

### Constraint

```typescript
interface Constraint {
  id: string;
  type: "budget" | "compatibility" | "environment" | "availability" | "avoidance" | "other";
  label: string;
  value: unknown;
  hard: boolean;
  confidence: "low" | "medium" | "high";
}
```

### MissingInformation

```typescript
interface MissingInformation {
  field: string;
  reason: string;
  question: string;
  required_before_search: boolean;
}
```

---

## 6. CategoryModel

A temporary product-domain model created for the search category.

```typescript
interface CategoryModel {
  id: string;
  category_label: string;
  aliases: string[];
  decision_attributes: DecisionAttribute[];
  category_segments: CategorySegment[];
  disqualifiers: string[];
  source_summary?: string;
  confidence: "low" | "medium" | "high";
}
```

### DecisionAttribute

```typescript
interface DecisionAttribute {
  id: string;
  name: string;
  label: string;
  description: string;
  value_type: "boolean" | "number" | "string" | "enum" | "range";
  possible_values?: string[];
  importance: "core" | "important" | "situational";
  related_requirements?: string[];
  evidence_priority: "manufacturer_manual" | "manufacturer_page" | "review_site" | "retailer";
}
```

Example for ceiling fans:

```json
{
  "id": "attr_001",
  "name": "blade_span_inches",
  "label": "Blade span",
  "description": "Fan diameter. Must fit room size and ceiling proportions.",
  "value_type": "number",
  "importance": "core",
  "evidence_priority": "manufacturer_page"
}
```

---

## 7. ProductCandidate

A product being considered.

```typescript
interface ProductCandidate {
  id: string;
  name: string;
  brand: string | null;
  model_number?: string;
  category_label: string;
  product_url?: string;
  image_url?: string;
  price_display?: string;
  price_numeric?: number;
  discovered_from: SourceReference[];
  attributes: ProductAttribute[];
}
```

### ProductAttribute

```typescript
interface ProductAttribute {
  attribute_id: string;
  name: string;
  value: unknown;
  normalized_value?: unknown;
  confidence: "low" | "medium" | "high";
  evidence_ids: string[];
}
```

---

## 8. EvidenceItem

Evidence is the foundation of trust. Every important product claim should link to one or more EvidenceItems.

```typescript
interface EvidenceItem {
  id: string;
  product_id?: string;
  source: SourceReference;
  source_type:
    | "manufacturer_manual"
    | "manufacturer_product_page"
    | "retailer_page"
    | "review_site"
    | "user_review"
    | "other";
  extracted_claim: string;
  normalized_attribute?: string;
  normalized_value?: unknown;
  page_number?: number;
  quote?: string;
  confidence: "low" | "medium" | "high";
  extraction_method: "llm" | "parser" | "manual" | "api";
  fetched_at: string;
}

interface SourceReference {
  url: string;
  title?: string;
  publisher?: string;
  accessed_at: string;
}
```

---

## 9. EvaluationResult

How a product fits the search intent.

```typescript
interface EvaluationResult {
  product_id: string;
  score: number;
  verdict: "best_match" | "good_match" | "partial_match" | "not_recommended" | "insufficient_evidence";
  requirement_results: RequirementResult[];
  tradeoffs: Tradeoff[];
  confidence: "low" | "medium" | "high";
}

interface RequirementResult {
  requirement_id: string;
  label: string;
  status: "met" | "partially_met" | "not_met" | "unknown";
  explanation: string;
  evidence_ids: string[];
  impact: "major_positive" | "positive" | "neutral" | "negative" | "major_negative";
}

interface Tradeoff {
  label: string;
  explanation: string;
  severity: "low" | "medium" | "high";
}
```

---

## 10. RecommendationSet

The final output of the workflow.

```typescript
interface RecommendationSet {
  session_id: string;
  created_at: string;
  summary_markdown: string;
  top_recommendation_product_id: string | null;
  ranked_product_ids: string[];
  not_recommended_product_ids: string[];
  overall_confidence: "low" | "medium" | "high";
  caveats: string[];
}
```

---

## 11. Requirement Traceability

The system should be able to explain any recommendation through this chain:

```text
User statement
→ Requirement
→ Category attribute
→ Product evidence
→ Requirement result
→ Product score
→ Recommendation
```

This is the central inspectability model of the-short-list.
