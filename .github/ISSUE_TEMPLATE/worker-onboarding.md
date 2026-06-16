---
name: Worker onboarding
about: Track adding a new computer or server to Loop Farm
title: "worker: onboard <machine-name>"
labels: worker,onboarding
---

## Machine

- Machine name:
- OS:
- Location/provider:
- CPU:
- GPU:
- Memory:
- Disk:

## Access

- [ ] Tailscale installed
- [ ] RustDesk installed
- [ ] Python 3.11+ installed
- [ ] Git installed
- [ ] `loop-farm-agent` registered
- [ ] Heartbeat visible from Mac/control

## Research software

- Required software:
- License/account notes:
- Data directories:
- Forbidden directories:

## Acceptance

- [ ] `farmctl worker list` shows the machine online
- [ ] A smoke job can be queued for this worker
- [ ] Agent can create an approval request

