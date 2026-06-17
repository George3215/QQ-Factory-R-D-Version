# Loop Farm Mac Bridge

Use the `loop-farm-mac` skill to communicate with the Mac control host.

Arguments from the user:

```text
$ARGUMENTS
```

Interpret the arguments as one of these actions:

- `pull`: run `chat-list --limit 20`, read Mac messages, and continue if safe.
- `health`: run `heartbeat`.
- `report <text>`: send a `source=claude_code` report with a short title and the provided text as the message.
- `reply <text>`: reply to this worker's Mac chat thread.
- `approval <question>`: create an approval request and send a `needs_human` report.
- Empty arguments: run `heartbeat`, then `chat-list --limit 20`, then summarize what the worker should do next.

Never request the Mac admin token. Use the worker config and agent token that already exist on this machine.

