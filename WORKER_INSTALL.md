# 其他电脑安装清单

这里的“其他电脑”指所有被 Mac 调度的科研/仿真电脑，例如实验室 GPU 机器、Windows 仿真机、Linux 服务器、办公室电脑。

结论：**其他电脑只装 worker 侧软件，不装控制中心。**

## 每台其他电脑必须安装

| 软件/仓库 | 是否必须 | 用途 |
| --- | --- | --- |
| Tailscale | 必须 | 让 Mac 和控制中心稳定找到这台电脑，不怕校园网 IP 变化 |
| RustDesk Client | 必须 | 远控兜底，Agent 解决不了时你可以接管桌面 |
| Python 3.11+ | 必须 | 运行 EvoScientist 循环工程 Agent |
| Git | 推荐必须 | 拉取/更新 EvoScientist fork |
| EvoScientist Agent fork | 必须 | 接收任务、执行任务、上报状态、申请批准 |
| 本机科研软件 | 按需 | Python/MATLAB/COMSOL/Abaqus/ANSYS/自研仿真程序 |

最小安装结果：

```text
Tailscale
+ RustDesk Client
+ Python 3.11+
+ Git
+ EvoScientist Agent fork
+ 本机科研软件
```

## 每台其他电脑不要安装

这些只装在控制节点，不装在每台工作电脑上：

```text
FastAPI 控制后端
PostgreSQL
NATS JetStream Server
Next.js Dashboard
Grafana
Prometheus Server
RustDesk Server
```

其他电脑只需要主动连接控制节点。

## 推荐仓库划分

建议你后面建 3 个仓库，不要全塞进一个大仓库。

| 仓库 | 安装位置 | 作用 |
| --- | --- | --- |
| `loop-farm-control` | 控制节点 | FastAPI、数据库、消息队列配置、Dashboard |
| `loop-farm-evoscientist-agent` | 每台其他电脑 | EvoScientist fork，常驻执行任务、上报状态、请求批准 |
| `loop-farm-recipes` | 控制节点和工作机都可用 | 科研任务模板，例如 Python/MATLAB/COMSOL/Abaqus |

如果前期想简单，也可以先做一个 monorepo：

```text
loop-farm/
  control/
  agent/      # EvoScientist fork
  recipes/
  docs/
```

等项目稳定后再拆仓库。

## 每台电脑安装后的目录

Linux/macOS：

```text
/opt/loop-farm-agent/
  config.yaml
  agent.db
  logs/
  workspaces/
  artifacts/
```

Windows：

```text
C:\LoopFarmAgent\
  config.yaml
  agent.db
  logs\
  workspaces\
  artifacts\
```

## EvoScientist Agent fork 应该提供什么

你的 Agent 不从零写，直接 fork EvoScientist，然后加一层 worker 外壳。建议仓库名：

```text
loop-farm-evoscientist-agent/
  pyproject.toml
  README.md
  evoscientist/              # EvoScientist 原核心代码
  src/loop_farm_worker/      # 你新增的 worker 层
    main.py                  # 常驻进程入口
    config.py
    heartbeat.py
    inventory.py
    metrics.py
    job_runner.py            # 调用 EvoScientist 执行任务
    approval.py
    artifacts.py
    recipes.py
  scripts/
    install-linux.sh
    install-macos.sh
    install-windows.ps1
  service/
    loop-farm-agent.service
    com.loopfarm.agent.plist
    loop-farm-agent.xml
```

第一版功能：

```text
evoscientist_core EvoScientist 原有科研自动化能力
heartbeat       上报在线
inventory       上报机器配置
metrics         上报资源占用
job_runner      调用 EvoScientist 执行任务
log_tail        摘要日志
approval_client 请求批准
artifact_upload 上传结果
```

## 按系统安装什么

下面的 `loop-farm-agent` 指安装到机器上的常驻服务名；它的代码实现来自你的 `loop-farm-evoscientist-agent` 仓库，也就是 EvoScientist fork。

### Linux 工作机

必须：

```text
Tailscale
RustDesk
Python 3.11+
Git
loop-farm-agent
systemd service
```

推荐：

```text
OpenSSH Server
NVIDIA driver / CUDA / nvidia-smi，GPU 机器需要
Docker，只有任务需要容器时再装
rclone，结果文件需要上传到网盘/对象存储时再装
```

Agent 作为 systemd 服务常驻。

### Windows 工作机

必须：

```text
Tailscale
RustDesk
Python 3.11+
Git
loop-farm-agent
Windows Service
```

推荐：

```text
OpenSSH Server，可选
MeshCentral Agent，可选
NVIDIA driver / CUDA，GPU 机器需要
本机仿真软件，例如 COMSOL/Abaqus/ANSYS/MATLAB
```

Agent 作为 Windows Service 常驻。

### macOS 工作机

必须：

```text
Tailscale
RustDesk
Python 3.11+
Git
loop-farm-agent
launchd service
```

推荐：

```text
Homebrew
rclone
科研软件运行环境
```

Agent 作为 launchd 服务常驻。

## 是否需要 MeshCentral Agent

不是必须。

建议规则：

| 场景 | 是否装 MeshCentral Agent |
| --- | --- |
| 只有 2-3 台电脑 | 可以先不装 |
| 电脑很多，需要统一看在线状态、终端、文件 | 装 |
| Windows 机器很多 | 推荐装 |
| 已经用 RustDesk 足够稳定 | 可以后面再装 |

最小方案先不装 MeshCentral，等机器多了再加。

## 是否需要 Docker

不是每台都必须。

建议规则：

| 场景 | 是否装 Docker |
| --- | --- |
| 只跑本机已有软件 | 不需要 |
| 每个任务环境不同 | 推荐 |
| 需要复现实验环境 | 推荐 |
| Windows GUI 仿真软件 | 通常不适合 Docker |
| Linux Python/CUDA 任务 | 很适合 Docker |

第一版可以不强制 Docker。Agent 先直接调用本机命令。

## 每台电脑的配置文件

每台电脑有一个 `config.yaml`：

```yaml
machine_id: lab-gpu-01
control_url: https://control.example.com
nats_url: nats://control.example.com:4222
agent_token: "每台机器独立 token"
work_dir: /opt/loop-farm-agent/workspaces
artifact_dir: /opt/loop-farm-agent/artifacts
allow_levels:
  - L0
  - L1
  - L2
tags:
  - linux
  - gpu
  - cuda
resources:
  gpu: true
  max_parallel_jobs: 1
```

Windows 的路径改成：

```yaml
work_dir: C:\LoopFarmAgent\workspaces
artifact_dir: C:\LoopFarmAgent\artifacts
```

## 其他电脑的最终状态

每台其他电脑最后应该是这样：

```text
开机后自动：
  1. 连上 Tailscale
  2. 启动 RustDesk
  3. 启动 loop-farm-agent
  4. Agent 主动连接控制节点
  5. Agent 等待任务
  6. Agent 自动执行低风险任务
  7. 高风险问题发回 Mac 等你批准
```

你平时不需要登录这些电脑。只有 Agent 处理不了时，才用 RustDesk 接管。
