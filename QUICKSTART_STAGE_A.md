# Stage A Quickstart：一键接入 Worker

当前 Stage A 已实现最小闭环：

```text
farmctl 创建 bootstrap token
  -> worker agent 注册
  -> control API 保存 worker
  -> agent heartbeat
  -> Mac 侧 farmctl 看到 worker 在线
```

这版还没有接入 EvoScientist 的真实 job runner，也没有接入 NATS/Next.js。它先把“新机器快速接入控制中心”这条链路打通。

## 1. 启动控制中心

```bash
python3 -m control.server \
  --host 127.0.0.1 \
  --port 8787 \
  --db data/dev.sqlite3 \
  --admin-token dev-admin-token
```

健康检查：

```bash
curl http://127.0.0.1:8787/health
```

## 2. 创建 worker bootstrap token

```bash
python3 -m farmctl tokens create \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token \
  --machine-name lab-gpu-01 \
  --ttl 3600
```

保存输出里的 `token`。

## 3. 在 worker 上注册 agent

开发机本地测试：

```bash
python3 -m agent register \
  --control-url http://127.0.0.1:8787 \
  --bootstrap-token lfbt_xxx \
  --machine-name lab-gpu-01 \
  --config data/lab-gpu-01-agent.json \
  --work-dir data/lab-gpu-01/workspaces \
  --artifact-dir data/lab-gpu-01/artifacts
```

真实 Linux worker 一键安装：

```bash
curl -fsSL https://control.example.com/install/worker-linux.sh \
  | sudo bash -s -- \
    --control-url https://control.example.com \
    --bootstrap-token lfbt_xxx \
    --machine-name lab-gpu-01 \
    --repo-url https://github.com/yourname/loop-farm.git
```

也可以让 `farmctl` 生成命令：

```bash
python3 -m farmctl worker bootstrap-command \
  --control-url https://control.example.com \
  --machine-name lab-gpu-01 \
  --token lfbt_xxx \
  --install-url https://control.example.com/install/worker-linux.sh \
  --repo-url https://github.com/yourname/loop-farm.git
```

## 4. 发送 heartbeat

单次：

```bash
python3 -m agent heartbeat --config data/lab-gpu-01-agent.json
```

常驻：

```bash
python3 -m agent daemon --config data/lab-gpu-01-agent.json
```

执行一个 agent cycle：

```bash
python3 -m agent run-once --config data/lab-gpu-01-agent.json
```

真实 Linux 安装脚本会自动创建 systemd 服务：

```bash
systemctl status loop-farm-agent
```

## 5. 在 Mac 上查看 worker

```bash
python3 -m farmctl worker list \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token
```

## 6. 创建测试 job

```bash
python3 -m farmctl jobs create \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token \
  --recipe smoke_test \
  --target-worker-id wkr_xxx \
  --payload-json '{"message":"hello loop farm"}'
```

让 agent 领取并执行 job：

```bash
python3 -m agent run-once --config data/lab-gpu-01-agent.json
```

查看 job events：

```bash
python3 -m farmctl jobs events \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token \
  --job-id job_xxx
```

当前 `smoke_test` 已经会被 agent 拉取执行；下一阶段会把 runner 接到 EvoScientist。

## 7. 创建测试审批请求

```bash
python3 -m agent approval-request \
  --config data/lab-gpu-01-agent.json \
  --title "是否允许模拟高风险操作" \
  --body-json '{"risk":"L4","recommended":"reject"}'
```

Mac 查看：

```bash
python3 -m farmctl approvals list \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token
```

Mac 批准或拒绝：

```bash
python3 -m farmctl approvals resolve \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token \
  --approval-id apr_xxx \
  --decision reject \
  --comment "not allowed in smoke test"
```

## 8. 发送 Codex / Claude Code 报告

worker 上报：

```bash
python3 -m agent report \
  --config data/lab-gpu-01-agent.json \
  --source codex \
  --level needs_human \
  --title "需要人类判断的边界条件" \
  --message "当前参数会导致仿真发散，需要选择缩小范围或更换求解器。" \
  --payload-json '{"options":["shrink_range","change_solver","stop"],"recommended":"shrink_range"}'
```

Mac 查看：

```bash
python3 -m farmctl reports list \
  --control-url http://127.0.0.1:8787 \
  --admin-token dev-admin-token \
  --source codex
```

Web UI 也可以在 `Reports` 页查看。

## 9. 下一步

下一阶段要实现：

```text
1. job_runner 调 EvoScientist
2. blocked job 根据 approval decision 继续/停止
3. artifact uploader
4. Codex/Claude report 自动摘要和合并
5. RunPod/云服务器复用同一套 bootstrap 流程
```
