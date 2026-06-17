---
name: loop-farm-reporter
description: Report Codex or Claude Code progress, results, errors, blocked tasks, approval needs, and other worker-side status from Linux/Windows research machines to the QQ Factory R&D / Loop Farm Mac control host. Use when Codex needs to push information from a remote worker to the central Mac dashboard, especially for needs_human decisions, failed jobs, experiment summaries, or low-value issues handled automatically.
---

# Loop Farm Reporter

## Core Rule

Report worker-side state to the Mac control host instead of asking the human to log into each machine.

Use `scripts/report.py` whenever a Codex, Claude Code, EvoScientist, or local worker process needs to send a durable message to the central Loop Farm dashboard.

## Quick Command

Run from this skill directory or pass the absolute path to the script:

```bash
python3 scripts/report.py \
  --source codex \
  --level info \
  --title "Experiment stage finished" \
  --message "lab-gpu-01 finished sweep A and wrote artifacts."
```

The script reads worker credentials from, in order:

1. Explicit arguments: `--control-url`, `--worker-id`, `--agent-token`
2. Environment variables: `LOOP_FARM_CONTROL_URL`, `LOOP_FARM_WORKER_ID`, `LOOP_FARM_AGENT_TOKEN`
3. Worker config: `LOOP_FARM_AGENT_CONFIG`, `~/.loop-farm-agent/config.json`, or Windows `%LOCALAPPDATA%\LoopFarmAgent\config.json`

## Levels

- `info`: normal progress, summaries, artifacts, successful automation.
- `warning`: suspicious but recoverable condition.
- `error`: failed operation that does not require immediate human judgment.
- `blocked`: local automation cannot continue.
- `needs_human`: the human must decide authorization, boundary conditions, research direction, credentials, licenses, or high-risk actions.
- `debug`: detailed state useful during setup only.

For human approvals or high-value decisions, always use `--level needs_human` and include concrete options in `--payload-json`.

```bash
python3 scripts/report.py \
  --source claude_code \
  --level needs_human \
  --title "COMSOL license boundary" \
  --message "The queued simulation requires a license decision before retrying." \
  --payload-json '{"options":["wait","move_to_lab-gpu-02","reduce_parallelism"],"recommended":"move_to_lab-gpu-02"}'
```

## Source Values

Use one of:

- `codex`
- `claude_code`
- `agent`
- `system`
- `human`

## Reference

Read `references/report_schema.md` when changing payload fields, adding report producers, or debugging API compatibility with the Mac control server.
