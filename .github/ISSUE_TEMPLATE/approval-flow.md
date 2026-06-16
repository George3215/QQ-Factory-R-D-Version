---
name: Approval flow
about: Define a high-value decision that must return to the Mac for human approval
title: "approval: <decision-type>"
labels: approval,human-in-loop
---

## Decision

What decision must come back to the human?

## Why AI cannot decide alone

Explain the authorization, boundary condition, research direction, cost, or safety issue.

## Request format

The Agent must include:

- Machine:
- Job:
- Problem summary:
- What it already tried:
- Recommended option:
- Alternatives:
- Risks:
- Approval scope:

## Acceptance

- [ ] Agent creates `approval_request`
- [ ] Mac/control can list the request
- [ ] Request has enough context for a decision
- [ ] Decision is written to audit/data flywheel

