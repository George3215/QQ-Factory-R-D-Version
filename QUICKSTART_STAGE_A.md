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

当前 job 只会入库，还不会被 agent 拉取执行。下一阶段会把 job receiver 接到 EvoScientist runner。

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

## 8. 下一步

下一阶段要实现：

```text
1. Agent 拉取 queued job
2. job_runner 调 EvoScientist
3. job_events 上报日志摘要
4. Approvals 支持批准/拒绝
5. Linux installer 支持 Tailscale auth key 自动入网
6. RunPod/云服务器复用同一套 bootstrap 流程
```

