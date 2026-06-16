# Report Schema

Workers send reports with `POST /api/reports`.

```json
{
  "worker_id": "wkr_xxx",
  "agent_token": "lfat_xxx",
  "source": "codex",
  "level": "needs_human",
  "title": "Short title",
  "message": "Human-readable detail",
  "payload": {
    "job_id": "job_xxx",
    "options": ["approve", "reject"],
    "recommended": "approve"
  }
}
```

Allowed `source` values:

- `agent`
- `codex`
- `claude_code`
- `system`
- `human`

Allowed `level` values:

- `debug`
- `info`
- `warning`
- `error`
- `blocked`
- `needs_human`

Use `needs_human` only when Mac-side human input is required. Include `options`, `recommended`, `risk`, and `expires_at` in `payload` when they help the human make a fast decision.

Mac-side read paths:

```bash
python3 -m farmctl reports list --source codex
python3 -m farmctl reports list --source claude_code --limit 20
```

The dashboard also shows reports in the `Reports` tab.
