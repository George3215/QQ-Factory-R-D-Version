# QQ 农场科研版实现 Pipeline

目标：你只在 Mac 上对话和批准；所有其他电脑安装一个循环工程 Agent，自动执行科研任务，只有重要问题才请求你。

## 最终推荐工具栈

不要再横向比较，直接按这个选：

| 模块 | 推荐工具/框架 | 为什么选它 |
| --- | --- | --- |
| 组网 | Tailscale | 最简单，先解决校园网 IP 变化和 NAT |
| 远控兜底 | RustDesk + rustdesk-server | 替代 ToDesk，用于必须接管桌面时 |
| 多机管理兜底 | MeshCentral，可选 | 统一看在线状态、终端、文件、远程桌面 |
| 控制后端 | FastAPI | Python 生态好，适合科研和 agent 系统 |
| Agent | EvoScientist fork + Python worker wrapper | 不从零写 Agent，直接爆改 EvoScientist |
| 消息队列 | NATS JetStream | 轻量，适合多 agent 任务、状态、事件 |
| 数据库 | PostgreSQL | 长期稳定，记录机器、任务、审批、日志 |
| 前端 Dashboard | 轻量 HTML/CSS/JS，参考 EvoScientist-Studio | 直接由 control server 托管，安装简单 |
| Mac 对话入口 | 先做 Web Chat，再做 CLI | 简单、稳定、跨设备 |
| 本地部署 | Docker Compose | 长期够用，不要一开始上 Kubernetes |
| 监控 | Grafana + Prometheus，第二阶段再加 | 第一阶段先别复杂化 |

## 一句话架构

```text
Mac Web Chat
  -> FastAPI 控制后端
  -> NATS JetStream
  -> 每台电脑的 EvoScientist 循环工程 Agent
  -> Agent 执行任务 / 上报状态 / 请求批准
```

RustDesk 和 MeshCentral 不参与日常自动化，只做兜底远控。

## Phase 0：先把机器连起来

目标：无论校园网 IP 怎么变，Mac 都能找到每台电脑。

工具：

```text
Tailscale
RustDesk
```

要做：

1. Mac 安装 Tailscale。
2. 每台科研电脑安装 Tailscale。
3. 每台电脑命名：
   - `lab-gpu-01`
   - `lab-gpu-02`
   - `lab-cpu-01`
   - `office-win-01`
4. 部署 RustDesk Server。
5. 每台电脑安装 RustDesk，并配置自建 server。

完成标准：

```text
Mac 可以稳定访问每台电脑。
Mac 可以用 RustDesk 接管任意电脑桌面。
```

## Phase 1：做控制中心

目标：所有机器、任务、审批都进入同一个控制中心。

工具：

```text
FastAPI
PostgreSQL
NATS JetStream
Docker Compose
```

要做：

1. 建一个 `control-server` 项目。
2. 用 Docker Compose 启动：
   - FastAPI
   - PostgreSQL
   - NATS JetStream
3. FastAPI 提供这些接口：
   - 注册机器
   - 查看机器列表
   - 创建任务
   - 查看任务状态
   - 创建审批请求
   - 批准/拒绝请求
4. PostgreSQL 保存：
   - machines
   - jobs
   - job_events
   - approval_requests
   - audit_logs

完成标准：

```text
Mac 打开网页，能看到所有机器。
Mac 能创建一个任务。
任务能进入队列。
审批请求能被记录。
```

## Phase 2：做循环工程 Agent

目标：每台电脑装一个基于 EvoScientist 爆改的 Agent，主动连回控制中心。

工具：

```text
EvoScientist fork
Python 3.11+
nats.py
psutil
SQLite
```

EvoScientist 负责：

```text
科研任务理解
实验流程执行
结果分析
自动修复尝试
任务上下文管理
```

需要你爆改/新增的 worker 能力：

```text
heartbeat       上报在线状态
inventory       上报机器配置
metrics         上报 CPU/GPU/内存/磁盘
job_runner      执行指定任务
log_tail        摘要任务日志
approval_client 遇到高风险动作时请求批准
local_state     本地保存任务状态，断线可恢复
```

完成标准：

```text
每台电脑启动 EvoScientist Agent 后，Dashboard 能看到它在线。
Mac 创建任务后，Agent 能收到并执行。
Agent 能上报任务成功/失败。
```

## Phase 3：做 Mac 对话入口

目标：你不需要进每台电脑，只在 Mac 上说话。

工具：

```text
轻量 HTML/CSS/JS control-ui
FastAPI
OpenAI API 或本地模型
```

第一版页面：

```text
机器列表
任务列表
对话输入框
审批队列
日志摘要
结果文件
```

你在 Mac 输入：

```text
把 lab-gpu-01 和 lab-gpu-02 上昨天失败的任务重新跑一遍，只在失败超过 2 次时找我。
```

系统执行：

```text
解析请求
生成任务计划
判断风险
低风险任务自动下发
高风险动作进入审批队列
Agent 执行并上报
Mac 只看到重要问题
```

完成标准：

```text
你可以用自然语言创建任务。
系统会把任务分配给指定电脑。
只有审批请求和失败摘要会打扰你。
```

## Phase 4：权限分级

目标：Agent 能做尽可能多的事，但不能失控。

工具：

```text
FastAPI 权限策略
PostgreSQL 审计日志
Agent 本地权限白名单
```

权限分级：

| 级别 | 自动执行 | 示例 |
| --- | --- | --- |
| L0 | 是 | 查看状态 |
| L1 | 是 | 操作任务目录 |
| L2 | 是 | 启动/停止自己的任务 |
| L3 | 条件允许 | 安装白名单包、重启自己的服务 |
| L4 | 必须批准 | 删除目录、重启电脑、改网络 |
| L5 | 必须批准 | 请求人类远控 |

完成标准：

```text
普通任务不用你批准。
危险操作必须进入审批队列。
所有操作都有审计日志。
```

## Phase 5：自动化科研任务

目标：从“远程控制电脑”升级为“自动运行科研流程”。

工具：

```text
Python 插件系统
任务模板 YAML
结果解析器
日志摘要器
```

要做：

1. 给常见科研任务写模板：
   - Python 仿真
   - MATLAB
   - COMSOL
   - Abaqus
   - 自研脚本
2. 每个模板定义：
   - 输入文件
   - 运行命令
   - 资源需求
   - 成功判断
   - 失败判断
   - 结果收集方式
3. Agent 按模板执行，不让模型随便拼危险 shell 命令。

完成标准：

```text
你提交一个实验目标。
系统自动选机器、跑任务、收结果、总结失败。
只有关键决策请求你批准。
```

## 最小 MVP

先只做这个：

```text
Tailscale
+ RustDesk
+ FastAPI
+ PostgreSQL
+ NATS JetStream
+ EvoScientist Agent fork
+ 简单 Web Dashboard
```

不要先做：

```text
Headscale
Kubernetes
复杂 Mac App
完整权限系统
自研远程桌面
过度漂亮的前端
```

## 推荐开发顺序

```text
1. 搭 Tailscale + RustDesk
2. 搭 FastAPI + PostgreSQL + NATS
3. fork EvoScientist，改成常驻 worker
4. 加 Agent heartbeat
5. 写 Web Dashboard
6. 写审批队列
7. 接入自然语言对话
8. 接入具体科研软件
9. 加权限分级
10. 加监控和备份
```

## 最终形态

```text
你：
  只在 Mac 上说话、查看摘要、批准重要请求。

控制中心：
  负责任务调度、权限判断、审计、消息分发。

每台电脑：
  跑循环工程 Agent，自动执行任务，主动汇报。

远控工具：
  RustDesk/MeshCentral 只在 agent 处理不了时使用。
```
