---
name: loop-farm-mac
description: Use when Claude Code is running on a Loop Farm worker and needs to report to, read messages from, reply to, or request approval from the Mac control host.
---

# Loop Farm Mac Bridge

You are Claude Code running on a worker machine. The Mac is the only human control host. Your job is to reduce manual remote login by using the installed Loop Farm agent to communicate with the Mac.

## Rules

- Use the local worker config. Do not ask the human to paste worker tokens if the config exists.
- Do not use or request the Mac admin token.
- Only read and reply to this worker's own Mac chat thread.
- Report meaningful progress, failures, and blocked states to the Mac.
- Ask for human approval before credentials, licenses, account actions, destructive file operations, reboot/shutdown, network/security changes, spending money, renting cloud resources, or changing research direction/boundary conditions.

## Locate The Agent

Windows PowerShell:

```powershell
$Config = Join-Path $env:LOCALAPPDATA "LoopFarmAgent\config.json"
$AgentExe = Join-Path $env:LOCALAPPDATA "LoopFarmAgent\venv\Scripts\loop-farm-agent.exe"
function Invoke-LoopFarmAgent {
  param([Parameter(ValueFromRemainingArguments=$true)][string[]]$AgentArgs)
  if (Test-Path $AgentExe) {
    & $AgentExe @AgentArgs
  } else {
    python -m agent @AgentArgs
  }
}
```

Linux/macOS shell:

```bash
Config="${LOOP_FARM_AGENT_CONFIG:-$HOME/.loop-farm-agent/config.json}"
Agent="${LOOP_FARM_AGENT:-python3 -m agent}"
```

If the config is missing, the worker has not been registered yet. Stop and ask the Mac user to run the Windows/Linux bootstrap flow.

## Health Check

Windows:

```powershell
Invoke-LoopFarmAgent heartbeat --config $Config
```

Linux/macOS:

```bash
$Agent heartbeat --config "$Config"
```

## Pull Mac Messages

Windows:

```powershell
Invoke-LoopFarmAgent chat-list --config $Config --limit 20
```

Linux/macOS:

```bash
$Agent chat-list --config "$Config" --limit 20
```

Read the newest human/system messages, decide what action is required, then continue locally if the instruction is safe and clear.

## Reply To Mac

Windows:

```powershell
Invoke-LoopFarmAgent chat-reply --config $Config --role claude_code --content "Short, concrete reply."
```

Linux/macOS:

```bash
$Agent chat-reply --config "$Config" --role claude_code --content "Short, concrete reply."
```

Use replies for direct conversation. Use reports for structured progress/status.

## Report Progress

Windows:

```powershell
Invoke-LoopFarmAgent report --config $Config --source claude_code --level info --title "Short title" --message "What changed and what the next local step is."
```

Linux/macOS:

```bash
$Agent report --config "$Config" --source claude_code --level info --title "Short title" --message "What changed and what the next local step is."
```

Levels: `debug`, `info`, `warning`, `error`, `blocked`, `needs_human`.

## Request Human Approval

Use this for high-value human decisions, not routine status:

```powershell
Invoke-LoopFarmAgent approval-request --config $Config --title "Decision needed" --body-json '{"question":"Which boundary condition should be used?","options":["A","B","stop"],"recommended":"A","risk":"L4"}'
```

Also send a `needs_human` report so the issue appears in the Mac reports stream:

```powershell
Invoke-LoopFarmAgent report --config $Config --source claude_code --level needs_human --title "Decision needed" --message "Waiting for a Mac-side decision." --payload-json '{"risk":"L4"}'
```
