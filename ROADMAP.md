# Roadmap

## M0: Repository Foundation

- [x] GitHub-ready monorepo layout
- [x] Minimal control API
- [x] Minimal worker agent wrapper
- [x] Mac-side `farmctl`
- [x] Linux one-command worker installer
- [x] Tests, smoke test, CI

## M1: Worker Onboarding

- [x] Bootstrap token creation
- [x] Worker registration
- [x] Heartbeat
- [x] Approval request creation
- [ ] Tailscale auth key support in installer
- [ ] macOS launchd installer
- [ ] Windows Service installer

## M2: Job Execution

- [ ] Agent job polling
- [ ] Job claim/lock API
- [ ] Job event logs
- [ ] Smoke runner
- [ ] EvoScientist runner adapter
- [ ] Artifact upload
- [ ] Approval decision API

## M3: Mac Control Surface

- [ ] Minimal Web Dashboard
- [ ] Machines page
- [ ] Jobs page
- [ ] Approvals page
- [ ] Results page
- [ ] Chat-to-job prototype

## M4: Research Recipes

- [ ] `python_simulation`
- [ ] `gpu_training`
- [ ] `parameter_sweep`
- [ ] `result_summary`
- [ ] MATLAB/COMSOL/Abaqus adapters as needed

## M5: Resource Automation

- [ ] `farmctl cloud create`
- [ ] cloud-init templating
- [ ] Hetzner adapter
- [ ] RunPod adapter
- [ ] TTL cleanup
- [ ] budget guard
- [ ] kill-all

## M6: Data Flywheel

- [ ] `human_decisions`
- [ ] `repair_rules`
- [ ] `failure_taxonomy`
- [ ] `research_memories`
- [ ] weekly loop-engineering report

