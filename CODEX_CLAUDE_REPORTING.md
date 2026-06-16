# Codex / Claude Code Report Channel

目标：其他 Linux/Windows worker 上的 Codex、Claude Code、EvoScientist 或本地 agent，不再要求你远控登录机器看状态，而是主动把进度、错误、阻塞点和需要人类判断的问题推回 Mac。

## 1. 主流程

```text
Worker 上的 Codex / Claude Code
  -> 读取 worker config
  -> POST /api/reports
  -> Mac control server 写入 SQLite
  -> Mac Dashboard 的 Reports 页展示
  -> Mac Dashboard 的 Chat 页按 worker 归档
  -> farmctl reports list 可查询
```

Mac 是唯一控制主机。其他机器只需要安装 worker agent，并主动连回 Mac 控制端。

## 2. Mac 启动控制端

```bash
make control
```

浏览器打开：

```text
http://127.0.0.1:8787
```

填入 admin token：

```text
dev-admin-token
```

真实多机部署时，worker 的 `control_url` 必须是 Linux/Windows worker 能访问到的 Mac 地址，例如 Tailscale IP、局域网地址或反向隧道地址。

## 3. Worker 安装后自带配置

Linux/Windows worker 注册成功后会有一个配置文件，默认位置：

```text
~/.loop-farm-agent/config.json
```

里面包含：

```json
{
  "control_url": "http://MAC_CONTROL_HOST:8787",
  "machine_name": "lab-gpu-01",
  "worker_id": "wkr_xxx",
  "agent_token": "lfat_xxx"
}
```

Codex/Claude Code 上报时优先复用这个配置，不需要人工重复输入 token。

## 4. 直接用 worker agent 上报

在 worker 上运行：

```bash
python3 -m agent report \
  --source codex \
  --level info \
  --title "Sweep finished" \
  --message "Parameter sweep A finished and artifacts are ready."
```

Claude Code 上报：

```bash
python3 -m agent report \
  --source claude_code \
  --level warning \
  --title "Patch compiled but tests missing" \
  --message "The code change compiles, but no domain regression test exists yet."
```

需要人类判断时：

```bash
python3 -m agent report \
  --source codex \
  --level needs_human \
  --title "COMSOL license decision" \
  --message "The next simulation needs a license allocation decision." \
  --payload-json '{"options":["wait","move_to_lab-gpu-02","reduce_parallelism"],"recommended":"move_to_lab-gpu-02","risk":"L4"}'
```

## 5. 用 Codex Skill 上报

仓库内置 skill：

```text
skills/loop-farm-reporter
```

Linux/Windows worker installer 会把它复制到默认 Codex skills 目录：

```text
Linux:   ~/.codex/skills/loop-farm-reporter
Windows: %USERPROFILE%\.codex\skills\loop-farm-reporter
```

Codex 遇到远程科研任务状态、失败、blocked、needs_human 时，可以调用：

```bash
python3 skills/loop-farm-reporter/scripts/report.py \
  --source codex \
  --level needs_human \
  --title "Boundary condition decision" \
  --message "The current simulation diverges under the requested boundary condition." \
  --payload-json '{"options":["shrink_range","change_solver","stop"],"recommended":"shrink_range"}'
```

脚本读取凭据的顺序：

```text
1. --control-url / --worker-id / --agent-token
2. LOOP_FARM_CONTROL_URL / LOOP_FARM_WORKER_ID / LOOP_FARM_AGENT_TOKEN
3. LOOP_FARM_AGENT_CONFIG
4. ~/.loop-farm-agent/config.json
```

## 6. Mac 查看报告

Web UI：

```text
Reports
Chat
```

CLI：

```bash
python3 -m farmctl reports list \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token
```

只看 Codex：

```bash
python3 -m farmctl reports list \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token \
  --source codex
```

只看 Claude Code：

```bash
python3 -m farmctl reports list \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token \
  --source claude_code
```

查看某台 worker 的对话线程：

```bash
python3 -m farmctl chat list \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token \
  --worker-id wkr_xxx
```

## 7. Agent 和人类分工

AI 应该自动上报：

```text
任务开始/结束
关键阶段完成
自动修复成功
实验摘要
失败原因摘要
低风险重试记录
artifact 路径
```

AI 必须请求人类：

```text
授权、账号、许可证
不可逆删除
重启机器
扩大权限
改变研究方向
改变边界条件
继续消耗大量算力
远控进入机器
```

每天推进只看三件事：

```text
1. 今天能不能通过 Mac 统一调度更多事情？
2. 今天是否还需要每台电脑现场调试，能不能少一次？
3. 今天 Agent 自动处理的问题是不是变多了？
```
