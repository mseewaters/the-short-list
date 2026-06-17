# the-short-list — UI/UX Specification

**Version:** 0.2  
**Reference:** Initial React prototype converted conceptually to Vue 3  
**Target stack:** Vue 3 Composition API  

---

## 1. UX Goal

the-short-list should feel like a calm, capable helper sitting next to the user while they make a product decision. The interface should reduce cognitive load, not display everything the system knows.

The core UX pattern is:

```text
Conversation on the left
Decision structure on the right
Evidence-backed results at the end
```

---

## 2. Primary Flow

### Stage 1 — Understand

User enters a natural-language request. The agent responds conversationally while the requirements panel updates.

The user should feel:

- Heard.
- Not interrogated.
- Progressively more clear about what matters.

### Stage 2 — Confirm

The user reviews the structured requirements before search starts.

The goal is to prevent garbage-in, garbage-out.

### Stage 3 — Research

The system runs the agent workflow and shows a real activity feed.

The user should see progress, not fake animation.

### Stage 4 — Results

The user sees a ranked product list with expandable detail.

Summary first. Evidence on demand.

### Stage 5 — Recommendation

The user can request a final recommendation in plain English.

This should feel like advice, not a data dump.

---

## 3. Layout

### Understand / Confirm Layout

```text
┌────────────────────────────────────────────┐
│ Stage bar                                  │
├──────────────────────────────┬─────────────┤
│ Conversation                  │ Requirement │
│                               │ panel       │
│ Agent and user messages       │             │
│                               │             │
│ Input / confirm controls      │             │
└──────────────────────────────┴─────────────┘
```

Recommended desktop/tablet layout:

```css
grid-template-columns: 1fr 320px;
gap: 28px;
max-width: 1020px;
```

### Research Layout

Single-column centered layout with activity feed.

### Results Layout

Single-column layout, max width around 800px.

---

## 4. Design System

### Typography

Prototype uses Georgia for warmth and readability. Keep this initially, but test with users.

Recommended stack:

```css
font-family: Georgia, 'Times New Roman', serif;
```

Do not require Georgia as the only font. Accessibility comes from size, spacing, contrast, and clarity more than one font choice.

### Base Sizes

- Body text: 17–19px.
- Primary controls: 18–20px.
- Small labels: minimum 13–14px.
- Tap targets: minimum 50px height.

### Color Tokens

```css
--ink:          #0f172a;
--ink-mid:      #475569;
--ink-light:    #94a3b8;
--paper:        #f8f7f4;
--card:         #ffffff;
--accent:       #1d4ed8;
--accent-light: #dbeafe;
--accent-mid:   #3b82f6;
--success:      #059669;
--success-light:#d1fae5;
--warn:         #d97706;
--warn-light:   #fef3c7;
--border:       #e2e8f0;
--border-mid:   #cbd5e1;
--danger:       #dc2626;
--unknown:      #64748b;
```

### Accessibility Rules

- Never use color alone to show pass/fail/unknown.
- Use text labels plus icons.
- Avoid hover-only interactions.
- Keep controls large enough for tablet use.
- Provide visible focus states.
- Sanitize rendered markdown or HTML.

---

## 5. Components

### StageBar

Shows workflow stages:

1. Understand
2. Confirm
3. Research
4. Results

Back button rules:

| Stage | Back allowed? | Destination |
|---|---:|---|
| Understand | No | N/A |
| Confirm | Yes | Understand |
| Research | No | N/A |
| Results | Yes | Confirm |

Research is not interruptible for MVP.

---

### ConversationPanel

Renders user and agent messages.

Agent messages:

- Left aligned.
- Agent icon.
- Warm card background.
- Supports limited markdown.

User messages:

- Right aligned.
- Dark background.

Typewriter effect:

- Use only for the most recent agent message.
- Render prior messages instantly.
- Provide a user setting or simple flag to disable animation later.

---

### RequirementsPanel

The panel is the visual representation of the search intent.

Displays:

- Human-readable requirements.
- Requirement count.
- Optional priority/confidence badges.
- Missing information, if any.

Recommended item structure:

```text
Requirement label
Requirement value
Priority: Must-have / Nice-to-have / Preference
Confidence: High / Medium / Low
```

The MVP can initially show label/value only, but the data contract should support richer metadata.

---

### ActivityFeed

Replace fake fixed search steps with live workflow events.

Example events:

```text
✓ Category identified: Ceiling fan
✓ Decision attributes created: size, airflow, controls, ceiling height, lighting
✓ Found 18 candidate models
✓ Excluded 7 products outside budget
⚠ Manual unavailable for 2 candidates; using manufacturer specs
✓ Scored 5 finalists
```

Each event should include:

- Status: pending, running, complete, warning, failed.
- Label.
- Optional detail.
- Timestamp.

---

### ProductCard

Expandable result card.

Collapsed state:

- Product name.
- Price or price range.
- Score.
- Verdict.
- Confidence.

Expanded state:

- Requirement fit rows.
- Evidence snippets.
- Tradeoffs.
- Why it may not be right.

Verdict values:

- Best match.
- Good match.
- Partial match.
- Not recommended.
- Insufficient evidence.

---

### RequirementTraceabilityPanel

This is a high-value addition and should become a core component.

For each requirement, show:

```text
User said
↓
System interpreted
↓
Mapped product attributes
↓
Evidence checked
↓
Recommendation impact
```

Example:

```text
User said:
"I don't want to deal with apps."

Interpreted as:
Low tech-comfort / app avoidance.

Mapped attributes:
Physical remote, wall switch compatible, no app required.

Evidence:
Manual confirms included remote.
Manufacturer page indicates app is optional.

Impact:
Products requiring app setup are downgraded or excluded.
```

This can be post-MVP visually, but the data contract should support it now.

---

## 6. Results Interaction

Initial results should show:

1. Best match expanded by default.
2. Other candidates collapsed.
3. Clear warning if evidence is incomplete.
4. Button: "What do you recommend for me?"

The recommendation should be generated from the same structured results already shown, not from a separate hidden reasoning process.

---

## 7. Empty, Error, and Uncertainty States

### No Candidates Found

Show:

- What was searched.
- Which constraints may be too narrow.
- Suggested edits.

### Evidence Missing

Show:

```text
Manual not found. Using manufacturer product page instead. Confidence: medium.
```

### Contradiction Found

Show:

```text
Retailer says this product includes feature X, but manufacturer manual does not confirm it. Treating as unverified.
```

### Agent Failure

Show partial progress and allow restart.

---

## 8. MVP UX Priorities

For Father's Day MVP, focus on:

1. Requirements panel.
2. Real stage transitions.
3. Activity feed.
4. Product cards.
5. Evidence/confidence display.
6. Plain-English recommendation.

Defer:

- Advanced animation.
- Mobile-first redesign.
- Account/profile settings.
- Saved comparisons.
- Voice input.
