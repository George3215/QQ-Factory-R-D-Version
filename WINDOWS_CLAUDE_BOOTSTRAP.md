# Windows Claude Code Bootstrap

目标：Windows 机器已经安装 Claude Code 时，不再依赖 ToDesk 大量键盘输入。Mac 生成一个部署提示词，Windows 上的 Claude Code 按提示词完成本机安装、注册、验证和上报。

## 适用场景

```text
Mac = 唯一控制主机
Windows = 被添加的 worker
Windows 上已有 Claude Code
Windows 能访问 Mac 控制端 URL
```

这个流程把 Claude Code 当成 Windows 本地执行代理。ToDesk/RustDesk 只用于打开 Claude Code 或处理极少数人工授权，不再承担长命令输入。

## 1. Mac 启动控制端

在 Mac 上启动控制端，并让 Windows 能访问到这个地址：

```bash
python3 -m control.server \
  --host 0.0.0.0 \
  --port 8787 \
  --db data/dev.sqlite3 \
  --admin-token dev-admin-token \
  --ui apps/control-ui \
  --install-dir install
```

确认 Mac 地址，例如：

```text
http://10.207.219.100:8787
```

Windows 上要能打开：

```text
http://10.207.219.100:8787/api/health
```

## 2. 生成一次性 token

在 Mac 上执行：

```bash
python3 -m farmctl tokens create \
  --control-url http://10.207.219.100:8787 \
  --admin-token dev-admin-token \
  --machine-name win-lab-01 \
  --ttl 7200
```

复制输出里的 `token`。

## 3. 生成 Windows Claude Code 提示词

在 Mac 上执行：

```bash
python3 -m farmctl install claude-windows-prompt \
  --control-url http://10.207.219.100:8787 \
  --machine-name win-lab-01 \
  --token lfbt_xxx \
  --install-base-url http://10.207.219.100:8787/install \
  --repo-url https://github.com/George3215/QQ-Factory-R-D-Version.git
```

把输出整段复制给 Windows 上的 Claude Code。

## 4. Windows Claude Code 做什么

Claude Code 应该自动完成：

```text
1. 检查 python、git、Mac /api/health。
2. 下载 install/worker-windows.ps1。
3. 用 bootstrap token 注册 worker。
4. 创建 %LOCALAPPDATA%\LoopFarmAgent。
5. 创建 Python venv，安装 loop-farm。
6. 注册 Windows Scheduled Task：LoopFarmAgent。
7. 运行 heartbeat。
8. 发送 source=claude_code 的报告到 Mac。
9. 在仓库中启用 `.claude/skills/loop-farm-mac` 和 `/loop-farm-mac`，作为后续长期交互入口。
```

如果 Python/Git 缺失，Claude Code 应停止并说明建议安装命令，不要未经批准擅自扩大权限。

## 5. Mac 验证

在 Mac 上查看 worker：

```bash
python3 -m farmctl worker list \
  --control-url http://10.207.219.100:8787 \
  --admin-token dev-admin-token
```

查看 Claude Code 报告：

```bash
python3 -m farmctl reports list \
  --control-url http://10.207.219.100:8787 \
  --admin-token dev-admin-token \
  --source claude_code
```

也可以打开 Dashboard：

```text
http://10.207.219.100:8787
```

查看：

```text
Workers
Reports
Chat
```

## 6. 后续用法

Windows worker 注册成功后，Claude Code 遇到科研任务进展、失败、阻塞、需要人类判断时，应通过本机 agent 上报：

```powershell
$Config = Join-Path $env:LOCALAPPDATA "LoopFarmAgent\config.json"
$Agent = Join-Path $env:LOCALAPPDATA "LoopFarmAgent\venv\Scripts\loop-farm-agent.exe"
& $Agent report --config $Config --source claude_code --level info --title "Experiment stage finished" --message "The Windows worker finished the current setup stage."
```

更推荐的长期方式是在 Claude Code 里直接用本仓库的 slash command：

```text
/loop-farm-mac pull
/loop-farm-mac health
/loop-farm-mac report Experiment stage finished.
/loop-farm-mac reply I will continue with the smaller parameter range.
/loop-farm-mac approval Should I use the paid GPU worker for this run?
```

这些命令会通过 worker 自己的 `agent_token` 和 Mac 通信，不需要也不应该获取 Mac `admin-token`。

需要人类判断时：

```powershell
& $Agent report --config $Config --source claude_code --level needs_human --title "Human approval needed" --message "The next action needs a license/account/boundary-condition decision." --payload-json '{"options":["approve","wait","stop"],"recommended":"wait","risk":"L4"}'
```

主线目标不变：

```text
Mac 统一调度
Windows/Linux 主动上报
低价值问题自动处理
高价值问题才找人
```
