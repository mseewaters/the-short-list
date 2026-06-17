# the-short-list — Product Specification

**Version:** 0.2  
**Status:** Prototype-to-MVP design  
**Target:** Father's Day MVP  

---

## 1. Product Summary

the-short-list is a conversational decision-support assistant that helps people make trustworthy consumer product decisions when the market is confusing, specs are inconsistent, and personal constraints matter.

The user describes what they need in natural language. the-short-list translates that messy input into structured requirements, builds a temporary product-domain model, researches candidate products, verifies important claims against source evidence, and produces a small set of understandable recommendations.

The first motivating use case was helping an elderly parent choose a robot vacuum. The broader product is not an appliance finder. It is a system for turning ambiguous human needs into evidence-backed consumer decisions.

---

## 2. Problem Statement

Consumer product research is overwhelming because:

- Product categories have specialized vocabulary that ordinary shoppers do not know.
- Retailer pages, manufacturer pages, reviews, and manuals often disagree.
- General-purpose AI tools may produce plausible but incorrect specs.
- Search engines optimize for discovery, not decision quality.
- The person doing the research may not be the person who will use the product.

the-short-list solves this by:

1. Capturing the user's real-world context in plain language.
2. Translating that context into structured requirements and constraints.
3. Dynamically identifying the important attributes for the product category.
4. Researching and constructing a curated candidate catalog.
5. Verifying important claims using source evidence.
6. Producing recommendations with visible reasoning and confidence.

---

## 3. Target Users and Personas

### Persona 1 — Family Helper

A technically confident person helping a parent, spouse, friend, or relative make a product decision.

Typical needs:

- Convert another person's rambling request into requirements.
- Avoid buying something that fails a hidden constraint.
- Produce a simple explanation that the final user can understand.
- Keep evidence available in case the recommendation is challenged.

### Persona 2 — Self Shopper

A capable adult researching an unfamiliar product category for their own needs.

Example: choosing ceiling fans, projector TVs, routers, smart home devices, appliances, cameras, or garden equipment.

Typical needs:

- Learn what attributes matter in the category.
- Understand tradeoffs without reading 30 product pages.
- Separate marketing claims from meaningful differences.
- Get a short list that fits personal constraints.

### Persona 3 — Low-Confidence Shopper

A user with low technical confidence, low patience for apps/settings, accessibility needs, or limited mobility.

Typical needs:

- Simple interface.
- Large text and clear controls.
- No forms packed with jargon.
- Recommendations explained in plain English.

---

## 4. MVP Positioning

The MVP is not a universal shopping engine. It is a prototype of a trustworthy, agentic decision workflow.

### MVP Promise

Given a freeform product request, the-short-list will:

1. Understand and confirm the user's requirements.
2. Identify the product category and relevant decision attributes.
3. Discover a small candidate set.
4. Verify key claims using available evidence.
5. Recommend the top options with confidence and traceability.

### MVP Non-Promise

the-short-list does not guarantee:

- Exhaustive market coverage.
- Real-time price optimization.
- Purchase completion.
- Perfect product data.
- Full support for every consumer product category.

When evidence is missing or weak, the-short-list must say so.

---

## 5. Core User Journey

```text
1. UNDERSTAND
   User describes the need in natural language.
   Agent extracts requirements and asks clarifying questions.
   Requirements panel builds in real time.

2. CONFIRM
   User reviews structured requirements.
   User edits, adds context, or approves the search.

3. RESEARCH
   Agents identify category attributes, discover products, gather evidence, and evaluate candidates.
   UI shows a live activity feed.

4. RESULTS
   User sees ranked product cards.
   Each card shows fit against requirements, evidence confidence, and tradeoffs.

5. RECOMMENDATION
   User can request a plain-English final recommendation.
```

---

## 6. Design Principles

### Open Input, Not Forms

The user should be able to type naturally. The system extracts structure.

### Search Context, Not Static Profile

Most requirements are tied to a specific decision. A user's floor type matters for a robot vacuum but not for a ceiling fan. Persist stable preferences separately from decision-specific search intent.

### Evidence Before Recommendation

A recommendation is only as trustworthy as the evidence behind it. Evidence is a first-class domain object, not a footnote.

### Semantic Fit Beats Spec Matching

A product can technically satisfy a spec while failing the actual human need. Example: a robot vacuum with a small manual bin may be inexpensive and button-operated, but it fails the mobility constraint if the user has to empty it daily.

### Progressive Disclosure

Show summary first. Let the user expand details when needed.

### Non-Intimidating Uncertainty

When the system cannot verify a claim, it should say so clearly and continue with lower confidence rather than pretending certainty.

---

## 7. Functional Scope

### In Scope for MVP

- Single user, no authentication.
- Conversational intake.
- Requirements extraction.
- Dynamic category/schema generation.
- Candidate product discovery.
- Evidence capture from accessible web sources.
- Basic verification and contradiction flagging.
- Ranked recommendation cards.
- Requirement traceability.
- Markdown-based recommendation summary.
- Local or simple hosted deployment.

### Out of Scope for MVP

- User accounts.
- Purchase checkout.
- Real-time price tracking.
- Voice input.
- Browser extension.
- Mobile-native app.
- Full market exhaustiveness.
- Complex long-term personalization.
- AWS Step Functions orchestration.

---

## 8. Success Criteria

The MVP is successful if:

1. A user can complete the journey without instruction.
2. The system produces a structured requirement list from messy input.
3. The system can research a product category not hardcoded in the frontend.
4. Each final recommendation shows why it fits or does not fit the requirements.
5. Important claims are traceable to evidence or explicitly marked uncertain.
6. The user can understand the final recommendation without reading the detailed evidence.

---

## 9. MVP Guardrails

To keep the project shippable:

- Support consumer appliances, electronics, home devices, and similar durable goods first.
- Limit candidate set to 3–7 products.
- Limit final recommendations to top 3.
- Prefer manufacturer pages/manuals over retailer copy when available.
- Cache extracted evidence for repeat searches.
- Use LangGraph for orchestration before adding cloud workflow engines.

---

## 10. Product Differentiator

the-short-list's differentiator is not that it finds products. Search engines already do that.

the-short-list's differentiator is requirement traceability:

```text
User said:
"My knees aren't great."

System translated this to:
Mobility constraint: avoid frequent bending.

Mapped product implications:
Self-emptying preferred.
Large, easy-access bin acceptable.
Small manual bin is a negative.

Evidence checked:
Manual confirms whether product self-empties.
Reviews checked for emptying complaints.

Recommendation impact:
Products requiring frequent manual emptying are downgraded.
```
