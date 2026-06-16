# Integrated Installation

This document is the practical install path for QQ Factory R&D Version.

## Architecture Rule

The default deployment model is:

```text
Mac = the only control host / human command center
Linux = normal worker
Windows = normal worker
macOS worker = advanced fallback only, not the default path
```

Do not install the control server on every computer. Other computers only install the worker agent.

## 1. Mac Control Host

Run this on your Mac. It starts the control server, serves the web UI, and hosts worker installer scripts:

```bash
make control
```

Equivalent command:

```bash
python3 -m control.server \
  --host 127.0.0.1 \
  --port 8787 \
  --db data/dev.sqlite3 \
  --admin-token dev-admin-token \
  --ui apps/control-ui \
  --install-dir install
```

Open:

```text
http://127.0.0.1:8787
```

Enter the admin token in the top-right field:

```text
dev-admin-token
```

## 2. Create Worker Bootstrap Token

Use the web UI:

```text
Install -> Create Bootstrap Token
```

Or CLI:

```bash
python3 -m farmctl tokens create \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token \
  --machine-name lab-gpu-01 \
  --ttl 3600
```

## 3. Generate Worker Install Command

Use the web UI:

```text
Install -> Generate Worker Install Command
```

Or CLI:

```bash
python3 -m farmctl install worker-command \
  --platform linux \
  --control-url http://127.0.0.1:8787 \
  --machine-name lab-gpu-01 \
  --token lfbt_xxx \
  --install-base-url http://127.0.0.1:8787/install \
  --repo-url https://github.com/George3215/QQ-Factory-R-D-Version.git
```

## 4. Linux Worker

Run on the Linux worker:

```bash
curl -fsSL http://CONTROL_HOST:8787/install/worker-linux.sh \
  | sudo bash -s -- \
    --control-url http://CONTROL_HOST:8787 \
    --bootstrap-token lfbt_xxx \
    --machine-name lab-gpu-01 \
    --repo-url https://github.com/George3215/QQ-Factory-R-D-Version.git
```

Check:

```bash
systemctl status loop-farm-agent
```

## 5. Windows Worker

Run in PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $script = Join-Path $env:TEMP 'worker-windows.ps1'; Invoke-WebRequest -UseBasicParsing -Uri 'http://CONTROL_HOST:8787/install/worker-windows.ps1' -OutFile $script; & $script -ControlUrl 'http://CONTROL_HOST:8787' -BootstrapToken 'lfbt_xxx' -MachineName 'office-win-01' -RepoUrl 'https://github.com/George3215/QQ-Factory-R-D-Version.git' }"
```

Check:

```powershell
Get-ScheduledTask -TaskName LoopFarmAgent
```

## 6. Optional macOS Worker

The normal architecture uses Mac as the control host, not as a worker. Only use this if you intentionally want to add another Mac as a worker:

```bash
curl -fsSL http://CONTROL_HOST:8787/install/worker-macos.sh \
  | bash -s -- \
    --control-url http://CONTROL_HOST:8787 \
    --bootstrap-token lfbt_xxx \
    --machine-name lab-mac-01 \
    --repo-url https://github.com/George3215/QQ-Factory-R-D-Version.git
```

## 7. Tailscale Auth Key

All installers accept an optional Tailscale auth key:

```text
--tailscale-auth-key tskey-auth-...
```

Keep auth keys short-lived and scoped. Do not commit them.

## 8. Smoke Job

Create a smoke job from the UI or CLI:

```bash
python3 -m farmctl jobs create \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token \
  --recipe smoke_test \
  --target-worker-id wkr_xxx \
  --payload-json '{"message":"hello loop farm"}'
```

Worker executes it on the next daemon cycle. For manual test:

```bash
python3 -m agent run-once --config data/lab-gpu-01-agent.json
```
