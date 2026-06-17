# The Short List - Project Context

## Project Goal

Build an agentic application that helps overwhelmed people make good consumer decisions.

The inspiration came from my dad. He frequently needs help researching products (robot vacuums, appliances, electronics, etc.) but becomes overwhelmed by choices and conflicting information.

The system should:

* Accept messy natural language input
* Convert it into structured requirements
* Research current products
* Verify important claims against source material
* Explain tradeoffs
* Produce a small set of trustworthy recommendations

The goal is NOT a shopping assistant.

The goal is a **cognitive load reducer** and **decision support system**.

The output is not "the best product".

The output is **The Short List**.

---

## Project Name

Project Name: The Short List

Repository Name:

the-short-list

Tagline (working):

Less guesswork. Better choices.

Other ideas:

* Helping real people make good decisions
* From messy requirements to trustworthy recommendations

---

## Technical Goals

Primary goal:

Learn multi-agent systems and orchestration.

Secondary goal:

Ship a Father's Day MVP.

Technology stack:

Frontend:

* Vue

Backend:

* FastAPI

Agent Framework:

* LangChain
* LangGraph

Future AWS components:

* DynamoDB
* S3
* Bedrock
* Possibly Step Functions later

Important rule:

Use LangGraph as the orchestrator first.

Do NOT introduce Step Functions for the MVP.

---

## Architectural Principles

1. Evidence over hallucination

Every recommendation should be traceable.

2. Requirements over products

The system is fundamentally a requirements translation engine.

3. Dynamic categories

The user may search for:

* Robot vacuums
* Ceiling fans
* TVs
* Routers
* Coffee makers
* Etc.

The system determines category dynamically.

4. Human-first UX

The experience should feel like a trusted person helping another person.

5. Trust over optimization

The system should say:

"I don't know."

instead of inventing answers.

---

## Important Design Changes

We intentionally moved away from an appliance finder.

The product is for:

People helping other people make decisions.

Personas:

1. Family helper (me helping my parents)

2. Independent shopper (me researching house renovation purchases)

3. Senior shopper

---

## Current Repo Structure

Repository already exists.

Current status:

✅ Repo created

✅ Documentation created

✅ Starter Python files created

Current folders:

the-short-list/
(or eventually renamed to the-short-list)

docs/

backend/
app/

frontend/

README.md

---

## Documentation Structure

01-product-spec.md

02-ui-ux-spec.md

03-domain-model.md

04-agent-contracts.md

05-api-contracts.md

06-system-architecture.md

07-backlog.md

README.md

---

## Key Architecture Decision

Think:

Experience + Orchestrator

NOT:

Frontend + Backend

The backend is the product.

Vue is simply the window into it.

---

## Today's Goal

Target completion: End of day

Deliverable:

A local full-stack skeleton.

The user can type:

"I need a ceiling fan for an old house bedroom. I care about quiet, low profile, and not ugly."

And:

1. Vue displays the message

2. FastAPI receives the request

3. LangGraph executes a fake workflow

4. Backend returns structured requirements JSON

5. Requirements panel updates

No intelligence required yet.

Just orchestration.

---

## Today's Exact Scope

Do:

✅ FastAPI

✅ Vue

✅ Fake LangGraph

✅ Requirements panel

✅ End-to-end communication

Do NOT do:

❌ AWS

❌ DynamoDB

❌ Step Functions

❌ Authentication

❌ Deployment

❌ LangSmith

❌ Caching

❌ Infrastructure optimization

❌ Architecture polishing

---

## Files to Create Today

backend/app/

main.py

graph.py

schemas.py

state.py

agents/

intent_agent.py

requirements_agent.py

response_agent.py

---

## shortlistState

Everything flows through this object.

Start simple.

```python
from typing import TypedDict

class shortlistState(TypedDict):
    user_message: str

    category: str | None

    raw_requirements: dict

    missing_fields: list[str]

    agent_message: str

    ready_to_search: bool
```

Keep it intentionally small.

---

## Project Rules

No basement waterproofing.

Translation:

Do not disappear into beautiful infrastructure work that does not advance the MVP.

Examples:

* AWS account setup
* Terraform
* Docker
* CI/CD
* Logging
* Monitoring
* Authentication
* DynamoDB

If an infrastructure idea appears:

Write it down in:

docs/parking-lot.md

Then return to the task.

---

## Success Metric For Today

By end of day I should be able to say:

"Vue is talking to FastAPI which is talking to LangGraph."

Nothing more.
