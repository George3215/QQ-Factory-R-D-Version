---
name: Agent capability
about: Add one more low-value problem that the Agent can handle automatically
title: "agent: handle <problem-type>"
labels: agent,automation
---

## Problem

What low-value problem should the Agent handle?

## Current manual workflow

What do we currently do by hand or via remote desktop?

## Desired autonomous behavior

What should the Agent do automatically?

## Safety boundary

- Auto-allowed level: L0 / L1 / L2 / L3
- Must request approval when:
- Data or directories that must not be touched:

## Acceptance

- [ ] Agent detects this problem
- [ ] Agent tries the approved fix
- [ ] Agent reports summary to control
- [ ] Agent requests approval for boundary cases
- [ ] A regression test or smoke scenario exists

