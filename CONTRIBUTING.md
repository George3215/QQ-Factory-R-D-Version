# Contributing

This repository is currently optimized for rapid private iteration on QQ Farm research automation.

## Development Loop

Run these before opening a pull request:

```bash
make pycheck
make test
make smoke
```

## Boundaries

Keep these boundaries intact:

```text
control/   owns API, state, audit, approval, worker registry
agent/     owns worker registration, heartbeat, job execution wrapper
farmctl/   owns Mac-side CLI and operator workflows
install/   owns one-command worker bootstrap scripts
infra/     owns deploy templates, service files, cloud-init
examples/  owns safe sample configuration
```

## Human-in-the-loop Rules

Any change that lets the Agent do more automatically must document:

```text
1. What problem it handles
2. What permission level it requires
3. What it must never do
4. When it must ask for human approval
5. How the action is audited
```

Use the `Agent capability` or `Approval flow` issue template before implementing risky automation.

## Secrets

Never commit:

```text
agent tokens
bootstrap tokens
cloud API keys
license keys
research credentials
real private data paths
```

