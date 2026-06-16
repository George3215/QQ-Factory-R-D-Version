# QQ 农场科研版：构建流程与工作计划

> 日期：2026-06-16  
> 目标：Mac 统一调度，多台电脑自动科研；低价值问题交给 AI，高价值判断回到你。

## 0. 固定方案

不要再横向选型，第一版就按这套做：

```text
Mac 主机：
  Control server
  Web Dashboard + Chat 输入框
  farmctl CLI
  RustDesk 客户端

控制节点：
  默认就是 Mac 主机，后续可迁到长期在线服务器
  Tailscale
  Docker Compose
  FastAPI
  PostgreSQL
  NATS JetStream
  Next.js + shadcn/ui
  rustdesk-server
  可选 MeshCentral

每台科研电脑：
  Linux worker 或 Windows worker
  Tailscale
  RustDesk Client
  Python 3.11+
  EvoScientist fork
  loop-farm worker wrapper
  本机科研软件
```

一句话结构：

```text
Mac Chat
  -> 控制中心
  -> NATS 任务队列
  -> 某台电脑的 EvoScientist Agent
  -> 自动执行科研任务
  -> 只把关键问题推回 Mac
```

## 1. 调研结论

### 1.1 现成工具能直接解决的部分

| 问题 | 直接用什么 | 结论 |
| --- | --- | --- |
| 校园网 IP 变化、NAT、机器找不到 | Tailscale | 直接用，不自研 |
| 必须接管桌面 | RustDesk + rustdesk-server | 直接用，不自研 |
| 多机器终端/文件/远控后台 | MeshCentral | 可选直接用 |
| Agent 任务消息、事件流、断线恢复 | NATS JetStream | 直接用，不自研 MQ |
| 控制 API | FastAPI | 用框架写业务 |
| Mac 控制台 | 轻量 HTML/CSS/JS，参考 EvoScientist-Studio | 第一版直接由 control server 托管 |
| 控制节点部署 | Docker Compose | 直接用，不上 Kubernetes |
| 科研自动化核心 | EvoScientist fork | 爆改，不从零写科研 Agent |

### 1.2 需要自己构建的部分

| 模块 | 为什么必须自己做 |
| --- | --- |
| `loop-farm-control` | 要定义你的机器、任务、审批、审计、数据飞轮 |
| `loop-farm-evoscientist-agent` | EvoScientist 需要改造成长期常驻 worker |
| `loop-farm-recipes` | 每种科研软件/任务的执行模板和成功标准不同 |
| Mac Chat 工作流 | 你的自然语言需要变成可审计任务 |
| 审批队列 | 需要区分低价值自动化和高价值人类决策 |
| 数据飞轮 | 需要把你的每次判断沉淀成规则、模板、经验 |

### 1.3 为什么这样选

1. Tailscale 官方 quickstart 明确支持添加多设备、设备命名和 MagicDNS；它会给设备稳定的 `100.x.y.z` 地址，并且适合在换网络或防火墙后保持连接。
2. RustDesk 自建服务由 `hbbs` 和 `hbbr` 两个核心服务组成：前者做 ID/rendezvous/signaling，后者做 relay；直连失败时走中继，所以适合做远控兜底。
3. MeshCentral 的定位就是自托管的 Web 远程管理站点，安装 agent 后可以远程桌面、终端和文件管理，适合多机后台。
4. NATS JetStream 提供消息持久化、重放、work queue 和 pull consumers，适合“agent 离线后恢复、任务不能丢、状态可回放”。
5. EvoScientist 的公开论文路线是 Researcher Agent、Engineer Agent、Evolution Manager Agent 加持久记忆；这和你的“科研数据飞轮”高度一致。
6. control server 直接托管轻量 Web UI，和 EvoScientist-Studio 的 sidecar 模式一致；Docker Compose 后续用于长期部署。

## 2. 仓库规划

第一版可以做 monorepo，后面再拆。

```text
loop-farm/
  control/       # FastAPI 控制中心
  dashboard/     # Next.js Mac 控制台
  agent/         # EvoScientist fork + worker wrapper
  recipes/       # 科研任务模板
  infra/         # docker-compose、NATS、PostgreSQL、RustDesk 配置
  docs/          # 设计、安装、工作流、操作手册
```

后期稳定后拆成：

```text
loop-farm-control
loop-farm-dashboard
loop-farm-evoscientist-agent
loop-farm-recipes
loop-farm-infra
```

## 3. 第一版必须打通的闭环

MVP 不追求功能多，只追求闭环真实。

```text
1. Mac 页面输入一个任务
2. 控制中心创建 job
3. job 进入 NATS 队列
4. 某台电脑的 Agent 收到 job
5. Agent 调 EvoScientist 执行一个真实脚本
6. Agent 上报日志摘要和任务状态
7. Agent 遇到一个需要批准的问题
8. Mac 页面显示审批请求
9. 你批准/拒绝/修改边界条件
10. Agent 继续执行或停止
11. 结果和你的决策进入数据飞轮
```

MVP 成功标准：

```text
你不用远控进入其他电脑，也能让一台工作机完成一次真实科研任务。
只有审批请求和结果摘要回到 Mac。
```

## 4. 构建流程

### Phase 0：准备物理和账号

目标：不要写代码前就卡在账号、网络、权限上。

人要做：

```text
1. 确认控制节点是哪台机器：VPS 或长期在线电脑
2. 准备 Tailscale 账号
3. 准备 GitHub 仓库
4. 准备 EvoScientist 源码地址
5. 确认每台科研电脑的系统、GPU、科研软件、许可证
6. 给每台机器命名：lab-gpu-01、lab-gpu-02、office-win-01
```

AI 可以做：

```text
1. 生成机器清单模板
2. 生成仓库 README
3. 生成安装步骤
4. 生成风险清单
5. 生成项目 issue 列表
```

完成标准：

```text
你知道控制节点是哪台。
你知道第一批接入哪 1-2 台工作机。
你有 EvoScientist 代码来源。
```

### Phase 1：打通网络和远控兜底

目标：Mac 能稳定找到每台电脑，必要时能接管桌面。

人要做：

```text
1. 在 Mac、控制节点、第一台工作机安装 Tailscale
2. 登录同一个 tailnet
3. 在控制节点部署 rustdesk-server
4. 在工作机安装 RustDesk Client
5. 手动验证 Mac 能远控工作机
```

AI 可以做：

```text
1. 写 Tailscale 命名规范
2. 写 RustDesk 部署脚本草稿
3. 写 worker 安装检查脚本
4. 写故障排查手册
```

完成标准：

```text
Mac 可以通过 Tailscale 访问控制节点。
Mac 可以用 RustDesk 进入第一台工作机。
```

### Phase 2：搭控制中心骨架

目标：控制节点能保存机器、任务、审批、审计。

要做的模块：

```text
FastAPI
PostgreSQL
NATS JetStream
Docker Compose
```

AI 可以做：

```text
1. 生成 Docker Compose
2. 生成 FastAPI 项目骨架
3. 生成数据库 schema
4. 生成 API：
   - machines
   - jobs
   - job_events
   - approval_requests
   - audit_logs
5. 生成基本测试
6. 生成 OpenAPI 文档
```

人要做：

```text
1. 决定控制节点域名或 Tailscale 地址
2. 设置管理员密码和密钥
3. 确认哪些端口只允许 Tailscale 访问
4. 审查数据库字段是否符合你的科研流程
```

完成标准：

```text
Mac 能打开 API。
控制中心能创建机器、创建任务、创建审批请求。
NATS 能收到一条测试任务。
```

### Phase 3：爆改 EvoScientist 成常驻 Agent

目标：EvoScientist 不再只是本地运行脚本，而是每台电脑上的常驻 worker。

EvoScientist 保留：

```text
研究想法生成
实验执行
结果分析
失败修复
历史记忆
```

新增 worker wrapper：

```text
heartbeat
inventory
metrics
job_receiver
job_runner
approval_client
artifact_uploader
local_state
permission_guard
```

AI 可以做：

```text
1. 阅读 EvoScientist 源码结构
2. 找到原来的任务入口
3. 包一层 job_runner
4. 写 NATS 消费者
5. 写 heartbeat 上报
6. 写本地 SQLite 状态
7. 写 Linux/macOS/Windows 安装脚本
8. 写 systemd/launchd/Windows Service 配置
9. 写单元测试和模拟控制中心
```

人要做：

```text
1. 提供 EvoScientist 真实仓库地址
2. 决定哪些 EvoScientist 功能保留，哪些先关掉
3. 在第一台真实工作机上授权安装
4. 提供科研软件许可证、账号、API key
5. 判断 Agent 是否可以访问某些数据目录
```

完成标准：

```text
第一台工作机开机后自动启动 loop-farm-agent。
Dashboard 能看到它在线。
控制中心下发 job 后，它能调用 EvoScientist 执行。
```

### Phase 4：做 Mac 控制台

目标：你只在 Mac 页面上看状态、发任务、批请求。

页面只做 5 个：

```text
1. Chat：自然语言任务入口
2. Machines：机器列表
3. Jobs：任务列表
4. Approvals：审批队列
5. Results：结果摘要
```

AI 可以做：

```text
1. 生成 Next.js 项目
2. 用 shadcn/ui 做页面
3. 对接 FastAPI
4. 做审批按钮
5. 做任务状态实时刷新
6. 做结果摘要展示
```

人要做：

```text
1. 决定页面上最重要的字段
2. 亲自试用审批流程
3. 判断哪些通知需要弹出，哪些只放在列表里
```

完成标准：

```text
你可以在 Mac 页面创建任务。
你可以在 Mac 页面批准或拒绝 Agent 的请求。
你可以看到任务结果摘要。
```

### Phase 5：做审批和权限分级

目标：Agent 自动处理低价值问题，高价值问题必须找你。

权限分级：

```text
L0 只读状态：自动
L1 工作目录操作：自动
L2 启动/停止自己的任务：自动
L3 白名单修复：条件自动
L4 系统级高风险操作：必须批准
L5 人类远控/授权/研究方向：必须批准
```

AI 可以做：

```text
1. 生成权限策略配置
2. 在 Agent 加 permission_guard
3. 自动判断操作风险级别
4. 生成审批请求文本
5. 记录审计日志
6. 合并重复请求
```

人要做：

```text
1. 定义第一版 L3 白名单
2. 决定哪些目录绝不能删
3. 决定哪些任务能自动重跑
4. 审批高风险操作
5. 调整风险边界
```

完成标准：

```text
低风险任务不打扰你。
删除数据、重启电脑、改许可证、改方向必须找你。
所有批准都有记录。
```

### Phase 6：接入真实科研任务模板

目标：从“能跑命令”升级为“能跑科研流程”。

第一批 recipes：

```text
python_simulation
matlab_batch
comsol_batch
gpu_training
parameter_sweep
result_summary
```

每个 recipe 必须定义：

```text
输入是什么
运行命令是什么
需要什么资源
成功怎么判断
失败怎么判断
日志怎么摘要
结果文件在哪里
什么情况必须找你
```

AI 可以做：

```text
1. 生成 recipe 模板
2. 根据现有脚本包装成 recipe
3. 解析日志
4. 总结失败原因
5. 生成结果摘要
6. 把一次人工修复沉淀为自动修复规则
```

人要做：

```text
1. 提供真实科研脚本
2. 判断成功/失败标准是否科学
3. 决定边界条件
4. 决定实验方向
5. 批准消耗大量算力的实验
```

完成标准：

```text
至少一个真实科研任务可以从 Mac 发起、远程执行、自动总结、沉淀结果。
```

### Phase 7：科研数据飞轮

目标：系统越用越少问你，越用越懂你的科研流程。

数据飞轮表：

```text
experiments
results
failures
human_decisions
repair_rules
boundary_rules
research_memories
recipe_versions
```

AI 可以做：

```text
1. 从结果中提取结构化摘要
2. 从失败中归类原因
3. 从你的批准中生成规则草稿
4. 从多次任务中总结最佳参数
5. 自动更新 recipe 草案
6. 生成下一轮实验建议
```

人要做：

```text
1. 审核新规则是否科学
2. 决定是否把一次经验固化进系统
3. 设定研究方向优先级
4. 判断结果是否有科研价值
```

完成标准：

```text
同类失败第二次出现时，Agent 能引用历史经验先自动处理。
你做过的高级判断能变成规则、模板或记忆。
```

## 5. 工作计划

### 第 1 周：连通和兜底

目标：

```text
Mac 能找到控制节点和第一台工作机。
RustDesk 能兜底远控。
```

任务：

| 编号 | 任务 | AI 做 | 人做 | 验收 |
| --- | --- | --- | --- | --- |
| W1-1 | 建机器清单 | 生成模板 | 填真实机器信息 | `machines.yaml` 完成 |
| W1-2 | Tailscale 接入 | 写步骤 | 登录安装 | Mac 能 ping 工作机 |
| W1-3 | RustDesk 接入 | 写部署方案 | 安装和授权 | Mac 能远控工作机 |
| W1-4 | 建仓库 | 生成结构 | 创建 GitHub 仓库 | monorepo 可用 |

### 第 2 周：控制中心 MVP

目标：

```text
任务、机器、审批能被控制中心记录。
```

任务：

| 编号 | 任务 | AI 做 | 人做 | 验收 |
| --- | --- | --- | --- | --- |
| W2-1 | FastAPI 骨架 | 写代码 | 审查接口 | API 跑起来 |
| W2-2 | PostgreSQL schema | 写迁移 | 审查字段 | 表可用 |
| W2-3 | NATS JetStream | 写 compose 和 topic 设计 | 确认部署 | 测试消息可收发 |
| W2-4 | 审计日志 | 写模型和 API | 确认哪些要记录 | 操作有日志 |

### 第 3 周：EvoScientist Agent 常驻化

目标：

```text
第一台工作机装上 EvoScientist Agent，并能收任务。
```

任务：

| 编号 | 任务 | AI 做 | 人做 | 验收 |
| --- | --- | --- | --- | --- |
| W3-1 | 读 EvoScientist 源码 | 分析入口 | 提供仓库和背景 | 找到执行入口 |
| W3-2 | worker wrapper | 写 heartbeat/job_receiver | 审查权限 | Agent 在线 |
| W3-3 | job_runner | 调 EvoScientist | 提供测试任务 | 能跑一次任务 |
| W3-4 | 本地服务 | 写 systemd/launchd/Windows Service | 授权安装 | 开机自启 |

### 第 4 周：Mac 控制台和审批闭环

目标：

```text
你能在 Mac 页面发任务、看状态、批请求。
```

任务：

| 编号 | 任务 | AI 做 | 人做 | 验收 |
| --- | --- | --- | --- | --- |
| W4-1 | Dashboard 页面 | 写 Next.js 页面 | 反馈字段 | 五个页面可用 |
| W4-2 | Chat 到 job | 写请求解析原型 | 测试说法 | 能创建 job |
| W4-3 | 审批队列 | 写审批 API 和 UI | 亲自批准 | Agent 收到决策 |
| W4-4 | 日志摘要 | 写摘要格式 | 判断够不够用 | Mac 看摘要即可 |

### 第 5-6 周：真实科研任务

目标：

```text
接入至少一个真实科研 workflow。
```

任务：

| 编号 | 任务 | AI 做 | 人做 | 验收 |
| --- | --- | --- | --- | --- |
| W5-1 | 选第一个任务 | 提建议 | 选一个低风险真实任务 | 任务明确 |
| W5-2 | 写 recipe | 包装脚本 | 定义成功/失败 | recipe 可重复跑 |
| W5-3 | 结果收集 | 写 uploader/summary | 判断结果价值 | 结果进入库 |
| W5-4 | 失败处理 | 写自动重试和分类 | 确认边界 | 普通失败不打扰 |

### 第 7-8 周：数据飞轮

目标：

```text
你的判断能沉淀为下一次自动化能力。
```

任务：

| 编号 | 任务 | AI 做 | 人做 | 验收 |
| --- | --- | --- | --- | --- |
| W7-1 | human_decisions 表 | 写 schema/API | 定义字段 | 决策可追踪 |
| W7-2 | repair_rules | 从失败总结规则 | 审核规则 | 下次自动应用 |
| W7-3 | research_memory | 总结研究经验 | 审核是否科学 | 可被 Agent 引用 |
| W7-4 | 周报 | 自动生成 | 你调整方向 | 下周计划更准 |

## 6. AI 和人的任务边界

### 6.1 AI 应该做的任务

AI 适合做重复、结构化、低风险、可回滚的事情：

```text
写代码骨架
写 API
写数据库迁移
写 Docker Compose
写安装脚本
写 worker wrapper
写 recipe 模板
解析日志
生成摘要
自动重试
分类错误
生成测试
写文档
生成周报
根据历史失败提出修复方案
把你的批准沉淀成规则草案
```

运行时 Agent 可以自动做：

```text
L0：查看机器状态
L1：操作任务目录
L2：启动/停止自己创建的任务
L3：执行白名单修复
```

### 6.2 人必须做的任务

人负责授权、边界和科研判断：

```text
选择控制节点/VPS
登录 Tailscale、GitHub、RustDesk
输入许可证、API key、账号密码
批准安装系统服务
批准访问重要数据目录
决定研究方向
定义边界条件
判断科学结果是否可信
批准大量算力消耗
批准删除数据、重启机器、改网络
批准高风险权限
远控处理 GUI、验证码、许可证异常
审查 AI 生成的规则是否能固化
```

运行时必须找你：

```text
L4：删除数据、重启电脑、改系统配置、改网络
L5：授权、研究方向、边界条件、远控、人类判断
```

## 7. 第一批不要做的事

```text
不要自研远程桌面
不要上 Kubernetes
不要一开始做复杂 Mac 原生 App
不要让 Agent 拿无限 root/admin 权限
不要直接暴露 RDP/VNC/SSH 到公网
不要一次接入所有电脑
不要先追求漂亮 UI
不要先做复杂多用户系统
```

第一版只接入：

```text
1 台 Mac
1 台控制节点
1 台工作机
1 个真实科研任务
1 个审批闭环
```

## 8. 项目里程碑

| 里程碑 | 标志 |
| --- | --- |
| M0 连通 | Mac 能稳定访问控制节点和第一台工作机 |
| M1 远控兜底 | RustDesk 能接管第一台工作机 |
| M2 控制中心 | 机器、任务、审批、审计能记录 |
| M3 Agent 在线 | EvoScientist Agent 能常驻并上报 |
| M4 任务执行 | Agent 能执行一个真实任务 |
| M5 审批闭环 | 高风险动作能回到 Mac 等你批准 |
| M6 结果沉淀 | 结果、失败、人工决策进入数据库 |
| M7 数据飞轮 | 第二次同类问题能自动引用历史经验 |

## 9. 每天怎么推进

每天只问三个问题：

```text
1. 今天能不能通过 Mac 统一调度更多事情？
2. 今天能不能减少一次“必须到每台电脑现场调试/单独远控”的需求？
3. 今天 Agent 能自动处理的问题类型或数量是不是变多了？
```

如果答案不是至少一个“能”，这项工作就可能偏离了 QQ 农场科研版的主线。

每天最好记录 4 个数：

```text
Mac 统一调度任务数
需要单独远控/现场调试的次数
Agent 自动处理的问题数
需要你人工批准/判断的问题数
```

长期目标不是完全不找你，而是：

```text
Mac 统一调度任务数持续上升。
单独远控/现场调试次数持续下降。
Agent 自动处理问题数持续上升。
找你的问题越来越集中在授权、方向、边界条件和科研判断。
```

## 10. 参考资料

1. EvoScientist 论文：<https://arxiv.org/abs/2603.08127>
2. Tailscale Quickstart：<https://tailscale.com/docs/how-to/quickstart>
3. Tailscale ACL：<https://tailscale.com/docs/features/access-control/acls>
4. RustDesk Self-host：<https://rustdesk.com/docs/en/self-host/>
5. MeshCentral GitHub：<https://github.com/Ylianst/MeshCentral>
6. NATS JetStream：<https://docs.nats.io/nats-concepts/jetstream>
7. FastAPI：<https://fastapi.tiangolo.com/>
8. Next.js Docs：<https://nextjs.org/docs>
9. shadcn/ui Docs：<https://ui.shadcn.com/docs>
10. Docker Compose Docs：<https://docs.docker.com/compose/>
