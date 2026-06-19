# progress.md

# The Short List

## Day 1 - Foundation & Orchestration

Date: June 17, 2026

## Goal

Build the first working end-to-end skeleton for The Short List.

The focus was intentionally **not intelligence**, but orchestration.

---

## Project Vision

The Short List is a consumer decision support application.

Goal:

Help overwhelmed people make good decisions by translating messy requirements into trustworthy recommendations.

This is not a shopping assistant.

This is a cognitive load reduction system.

Workflow:

Messy human input

↓

Requirements extraction

↓

Clarification

↓

Research

↓

The Short List

---

## Major Accomplishments

### Repository established

Repository name:

the-short-list

Initial docs structure created.

Documentation includes:

* product specification
* UX specification
* domain model
* agent contracts
* API contracts
* system architecture
* backlog

---

## Backend established

Technology:

* FastAPI
* LangGraph

Endpoints created:

* GET /health
* POST /sessions
* POST /clarify
* POST /search

FastAPI documentation available via Swagger.

---

## LangGraph established

Basic orchestration implemented.

Current flow:

Input

↓

Intent Agent

↓

Requirements Agent

↓

Response Agent

Current implementation is intentionally deterministic.

No LLMs yet.

---

## Session state implemented

Session state now persists across multiple interactions.

Subsequent responses no longer overwrite previous requirements.

The system can progressively build understanding over multiple turns.

Example:

User:

"I need a ceiling fan for an old house bedroom."

User:

"Budget is $300 and my ceiling is 8 feet."

The system accumulates understanding instead of replacing it.

---

## Clarification loop implemented

The system now:

* extracts requirements
* identifies missing information
* asks follow-up questions
* determines when enough information exists to proceed

The "Confirm" stage was intentionally removed.

New product flow:

Understand

↓

Research

↓

Your Short List

The requirements panel itself serves as confirmation.

---

## Search flow implemented

A mock research flow now exists.

The system can:

* trigger search
* generate hardcoded candidates
* produce recommendations

This is intentionally fake data.

The goal was proving orchestration.

---

## Key Architectural Decisions

### No infrastructure yet

Explicitly postponed:

* AWS
* DynamoDB
* Step Functions
* Docker
* Authentication
* CI/CD
* LangSmith

### Product architecture over visual design

Prioritized:

* state
* workflows
* information architecture

Deferred:

* colors
* fonts
* spacing
* animations

### Product language established

Project name:

The Short List

This is a decision support system, not an AI shopping assistant.

---

## Biggest Lesson Learned Today

Agents are less magical than expected.

Most of the work is:

state

↓

contracts

↓

workflows

↓

orchestration

The LLM is a small piece of the overall system.

Good system design matters more than AI cleverness.

---

# Day 2 Goal - Intelligence Day

Goal:

Replace one deterministic component with a real LLM implementation.

Only one.

Do not replace everything at once.

---

## Day 2 Priority Work

### 1. Introduce Category Intelligence

Current:

Hardcoded:

if "ceiling fan"

Tomorrow:

Allow the system to dynamically understand categories.

Input:

"I need a projector for a bright room."

Output:

Category:

Projector

Important attributes:

* brightness
* throw distance
* room lighting

---

### 2. Build Dynamic Category Schema

Introduce a new node.

Category Schema Agent

Input:

Category

Output:

Relevant attributes for that category.

Example:

Ceiling fan:

* room size
* ceiling height
* blade span
* profile
* noise

TV:

* brightness
* panel type
* refresh rate

This becomes foundational for future research.

---

### 3. Add Agent Trace Visibility

Add a developer panel.

Display:

Intent Agent

Requirements Agent

Category Schema Agent

Research Agent

This is a learning tool.

Do not optimize visually.

---

## Still Forbidden

No AWS

No DynamoDB

No Docker

No Step Functions

No Authentication

No CI/CD

No LangSmith

No Terraform

No basement waterproofing.

---

## Success Metric For Tomorrow

The Short List should be able to intelligently understand multiple categories without hardcoded category logic.

The user should be able to switch from:

Ceiling fan

to

Robot vacuum

to

TV

without changing application code.

---

## Future Motto

Less guesswork. Better choices.

---

## Day 2 - Category Intelligence Implemented

Date: June 17, 2026

## Goal

Complete yesterday's Intelligence Day priorities:

* Introduce Category Intelligence
* Build Dynamic Category Schema
* Add Agent Trace Visibility

---

## What Was Completed

### 1. Category Intelligence introduced

The system now performs category understanding dynamically instead of relying on hardcoded category checks.

Result:

Input can describe very different products, and the workflow infers category context without changing application code.

---

### 2. Dynamic category schema added

A category intelligence layer now produces category-aware attributes used downstream by requirements and research logic.

Result:

Each category can carry different attribute expectations (for example, fan sizing vs TV panel characteristics) using the same orchestration path.

---

### 3. Agent trace visibility added

Trace visibility was added so developer-facing flow execution is easier to inspect while iterating.

Result:

You can now see how intent, requirements, category intelligence, and response/research steps contribute to the final output.

---

## Success Metric Status

Yesterday's success metric is met.

The Short List can now move across categories (for example ceiling fan, robot vacuum, TV) without hardcoded category branching.

---

# Today's Goal - User Requirements Intelligence Day

Goal:

Make requirement extraction significantly smarter so the system captures, normalizes, and prioritizes what the user actually cares about.

---

## Today's Priority Work

### 1. Improve requirement extraction quality

Focus:

Extract explicit and implied requirements from natural language with less loss.

Target examples:

* hard constraints (budget cap, dimensions, compatibility)
* preference signals (quiet, premium feel, easy setup)
* context constraints (room type, household type, usage pattern)

---

### 2. Add requirement normalization and confidence

Focus:

Normalize user language into structured requirement fields and attach confidence.

Output should include:

* canonical attribute name
* normalized value/range
* source phrase from user text
* confidence score
* conflict flag (if contradictory statements exist)

---

### 3. Strengthen clarification intelligence

Focus:

Ask fewer, better follow-up questions.

Question selection should prioritize:

* high-impact missing constraints
* low-confidence extracted requirements
* conflict resolution when user inputs disagree

---

### 4. Add requirement trace and debugging hooks

Focus:

Expose how each requirement was extracted and transformed to accelerate iteration.

Include:

* raw phrase -> normalized field mapping
* dropped/ignored signals with reason
* per-turn requirement deltas

---

## Still Forbidden

No AWS

No DynamoDB

No Docker

No Step Functions

No Authentication

No CI/CD

No LangSmith

No Terraform

No basement waterproofing.

---

## Success Metric For Today

Given messy user input, The Short List should produce a trustworthy structured requirement set, identify gaps/conflicts, and ask the minimum clarifying questions needed before research.

---

## Working Motto

Understand the user before recommending the product.
