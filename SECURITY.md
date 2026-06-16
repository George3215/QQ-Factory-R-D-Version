# Security Policy

Loop Farm is designed around a strict boundary:

```text
AI handles low-value, reversible work.
Humans approve high-risk, expensive, irreversible, or scientific-direction decisions.
```

## Secrets

Do not commit:

```text
LOOP_FARM_ADMIN_TOKEN
worker bootstrap tokens
agent tokens
Tailscale auth keys
cloud provider API keys
software license keys
research data credentials
```

Use environment variables, a private secret manager, or the control node filesystem with restricted permissions.

## Worker Tokens

Each worker must have its own agent token.

Bootstrap tokens should be:

```text
short-lived
single-use
scoped to one machine name
audited
```

## Automation Levels

The default safety policy:

```text
L0 read-only status: automatic
L1 task workspace operations: automatic
L2 start/stop own jobs: automatic
L3 whitelisted repair: conditional
L4 system/high-risk operation: human approval
L5 authorization/research direction/boundary condition: human approval
```

## Cloud Cost Controls

Before enabling cloud rental:

```text
set daily and monthly budgets
set default TTL for rented workers
implement kill-all
upload artifacts before release
audit every create/destroy event
```

