---
name: Cloud provider adapter
about: Add or improve automated CPU/GPU server rental
title: "provider: <provider-name>"
labels: cloud,provider
---

## Provider

- Name:
- API docs:
- Resource type: CPU / GPU / pod / VM

## Required credentials

- API key name:
- Required account setup:
- Billing/verification requirements:

## Lifecycle

- Create server/pod:
- Inject bootstrap/cloud-init:
- Detect ready:
- Collect cost:
- Destroy server/pod:

## Safety

- Default TTL:
- Budget guard:
- Kill-all support:
- Artifact upload before release:

## Acceptance

- [ ] `farmctl cloud create` works
- [ ] Worker registers automatically
- [ ] Test job can run
- [ ] Worker is released after TTL or completion
- [ ] Cost and lifecycle events are recorded

