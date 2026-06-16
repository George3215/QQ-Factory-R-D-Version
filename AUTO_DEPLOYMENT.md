# QQ 农场科研版：自动部署与自动租赁方案

> 目标：把“接入一台电脑”变成自动化流程；未来把“租服务器、跑实验、释放资源”也变成自动化流程。

## 1. 结论

可以做，而且应该做。

但不要把它做成“一个 Docker 镜像解决所有问题”。Docker 适合封装任务环境，不适合作为唯一控制层。因为你需要：

```text
接入 Tailscale
安装系统服务
访问 GPU/CUDA/驱动
控制 RustDesk/MeshCentral
读写本机科研软件
处理许可证
启动/停止整台云主机
```

推荐做一个自动化部署程序：

```text
farmctl
```

它负责：

```text
1. 给已有电脑安装 Agent
2. 给云服务器生成初始化脚本
3. 自动租用 CPU/GPU 服务器
4. 自动把服务器接入控制中心
5. 自动下发任务
6. 自动回收结果
7. 自动释放服务器
```

一句话：

```text
Docker/容器只负责“任务运行环境”；
farmctl 负责“机器生命周期”；
EvoScientist Agent 负责“科研执行”；
Mac 负责“统一调度和高级批准”。
```

## 2. 推荐架构

```text
Mac
  farmctl CLI / Web Dashboard
      |
      v
控制中心
  FastAPI
  PostgreSQL
  NATS JetStream
  Provider Adapter
      |
      +--> 已有电脑：SSH / 本地安装脚本
      |
      +--> CPU 云服务器：OpenTofu / cloud-init / Ansible
      |
      +--> GPU 云服务器：RunPod / Vast.ai / Lambda Cloud API
```

每台新机器启动后自动做：

```text
1. 安装基础依赖
2. 加入 Tailscale
3. 拉取 EvoScientist Agent fork
4. 写入机器 token 和配置
5. 注册到控制中心
6. 启动 loop-farm-agent 服务
7. 等待任务
8. 任务完成后上传结果
9. 如果是租赁机器，自动释放
```

## 3. 不同机器的部署方式

| 机器类型 | 推荐方式 | 原因 |
| --- | --- | --- |
| 自己的 Linux 工作站 | install script + systemd | 最简单、稳定 |
| 自己的 macOS 机器 | install script + launchd | 适合长期在线 Mac |
| 自己的 Windows 机器 | PowerShell installer + Windows Service | Windows GUI/仿真软件常见 |
| 普通云 CPU 服务器 | cloud-init + Ansible，可选 OpenTofu | 适合批量创建和销毁 |
| GPU 云服务器 | Provider API + cloud-init/container image | 适合按需租赁，用完释放 |
| 临时 GPU Pod | Provider container template + Agent entrypoint | 快速启动，适合短任务 |

## 4. 为什么不是纯 Docker

Docker 仍然有用，但定位要对。

Docker 适合：

```text
Python 环境
CUDA/PyTorch 环境
可复现实验
短生命周期任务
云 GPU Pod 镜像
```

Docker 不适合作为唯一方案：

```text
系统服务安装
Tailscale 主机级网络
RustDesk GUI 远控
Windows/MATLAB/COMSOL/Abaqus 这类本机软件
许可证和桌面交互
机器关机/重启/释放
```

最终策略：

```text
Agent 跑在宿主机。
科研任务可以跑在宿主机，也可以由 Agent 启动 Docker/Podman/conda 环境。
云 GPU 短任务可以直接用容器镜像启动 Agent。
```

## 5. farmctl 命令设计

第一版 `farmctl` 是 Mac 上的 CLI，也可以被 Dashboard 调用。

### 5.1 接入已有电脑

```bash
farmctl worker add \
  --name lab-gpu-01 \
  --os linux \
  --ssh user@lab-gpu-01
```

它做：

```text
1. 检查 SSH
2. 安装 Python/Git/依赖
3. 安装 Tailscale，如果需要
4. 拉取 loop-farm-evoscientist-agent
5. 写 config.yaml
6. 安装 systemd 服务
7. 启动 agent
8. 等待控制中心看到 heartbeat
```

### 5.2 生成一键安装命令

适合你手动复制到某台电脑上运行：

```bash
farmctl worker bootstrap-command --name lab-gpu-01
```

输出类似：

```bash
curl -fsSL https://control.example.com/install/worker.sh \
  | sudo bash -s -- --token lfwt_xxx --name lab-gpu-01
```

### 5.3 租一台普通 CPU 服务器

```bash
farmctl cloud create \
  --provider hetzner \
  --type cpu \
  --name cpu-worker-001 \
  --ttl 6h
```

它做：

```text
1. 调 provider API 创建服务器
2. 注入 cloud-init
3. 自动加入 Tailscale
4. 自动安装 Agent
5. 注册到控制中心
6. 到期自动销毁
```

### 5.4 租一台 GPU 服务器跑任务

```bash
farmctl cloud run \
  --provider runpod \
  --gpu "RTX 4090" \
  --max-price 0.8 \
  --ttl 4h \
  --recipe gpu_training \
  --input experiments/job-001.yaml
```

它做：

```text
1. 查可用 GPU
2. 按价格/显存/地区过滤
3. 创建 GPU Pod/Instance
4. 启动 Agent
5. 下发任务
6. 监控运行
7. 上传结果
8. 自动释放机器
```

### 5.5 手动释放资源

```bash
farmctl cloud destroy --worker gpu-worker-20260616-001
```

### 5.6 成本和安全开关

```bash
farmctl budget set --daily 20
farmctl budget set --monthly 300
farmctl cloud kill-all --provider runpod
farmctl approvals list
```

## 6. 控制中心需要新增的模块

在 `loop-farm-control` 里新增：

```text
providers/
  base.py
  hetzner.py
  runpod.py
  vastai.py
  lambda_cloud.py

provisioning/
  cloud_init.py
  ansible.py
  install_tokens.py
  worker_registry.py

billing/
  budget.py
  lease.py
  cleanup.py

api/
  cloud_workers.py
  bootstrap_tokens.py
  leases.py
```

新增数据库表：

```text
cloud_providers
cloud_credentials
worker_bootstrap_tokens
worker_leases
worker_cost_events
worker_lifecycle_events
provider_instances
```

## 7. Agent 需要支持的自动部署能力

EvoScientist Agent fork 需要支持：

```text
--register
--once
--daemon
--self-test
--run-job <job_id>
--shutdown-after-job
```

含义：

| 命令 | 用途 |
| --- | --- |
| `--register` | 第一次启动时向控制中心注册机器 |
| `--once` | 临时云机器只跑一次任务 |
| `--daemon` | 自有机器长期常驻 |
| `--self-test` | 检查 Python/GPU/网络/磁盘/权限 |
| `--run-job` | 直接执行指定任务 |
| `--shutdown-after-job` | 任务结束后申请释放机器 |

## 8. 自动租赁流程

```text
1. 你在 Mac 输入任务
2. 控制中心判断本地机器是否够用
3. 如果够用，直接下发给已有 Agent
4. 如果不够用，生成租赁计划
5. 如果租赁成本低于预算，自动租
6. 如果超过预算或风险高，问你批准
7. 云机器启动后自动注册
8. Agent 拉取任务并运行
9. 结果上传
10. 云机器自动释放
11. 成本、结果、失败原因进入数据飞轮
```

## 9. Provider 优先级

第一批不要接太多 provider。建议顺序：

| 阶段 | Provider | 用途 |
| --- | --- | --- |
| P1 | 自有机器 | 先验证 Agent 和控制中心 |
| P2 | Hetzner / 其他便宜 VPS | 低价 CPU worker、控制节点 |
| P3 | RunPod | GPU Pod 自动租赁，API 明确 |
| P4 | Vast.ai | 便宜 GPU 市场，适合价格优化 |
| P5 | Lambda Cloud | 稳定 GPU 云，适合严肃任务 |

先做 RunPod 的原因：

```text
它有明确的 Pod API。
Pod 天然适合“租 GPU、跑容器、跑完释放”。
对短期 GPU 任务友好。
```

Vast.ai 适合后面做价格优化，但市场型 GPU 资源波动更明显，第一版不要一上来就依赖它。

## 10. 最小实现顺序

### Stage A：一键安装已有电脑

目标：

```text
任何 Linux 电脑运行一条命令后，自动变成 worker。
```

交付物：

```text
install/worker-linux.sh
install/worker-macos.sh
install/worker-windows.ps1
farmctl worker bootstrap-command
worker_bootstrap_tokens 表
Agent --register
Agent --self-test
```

验收：

```text
一台新 Linux 机器 10 分钟内出现在 Mac Dashboard。
```

### Stage B：云 CPU 自动创建和释放

目标：

```text
控制中心能自动创建一台便宜 CPU 云服务器，装 Agent，跑任务，释放。
```

交付物：

```text
cloud-init 模板
provider adapter: hetzner
farmctl cloud create
farmctl cloud destroy
TTL 自动清理
成本记录
```

验收：

```text
一条命令创建云 CPU worker。
任务完成后自动释放。
```

### Stage C：GPU Pod 自动租赁

目标：

```text
需要 GPU 时自动租赁，跑完自动释放。
```

交付物：

```text
provider adapter: runpod
GPU 任务镜像
Agent container entrypoint
artifact uploader
budget guard
TTL guard
```

验收：

```text
Mac 发起一个 GPU 任务。
系统自动租 GPU、运行、上传结果、释放机器。
```

### Stage D：价格优化和多 provider

目标：

```text
系统自动选择最便宜、可用、符合条件的资源。
```

交付物：

```text
provider adapter: vastai
provider adapter: lambda_cloud
GPU 价格缓存
资源选择器
失败自动换 provider
```

验收：

```text
同一个任务能根据预算自动选择 GPU 资源。
```

## 11. 什么由 AI 做，什么由人做

### AI 可以做

```text
写 farmctl CLI
写 cloud-init 模板
写 Ansible playbook
写 provider adapter
写安装脚本
写 Agent 注册逻辑
写 self-test
写成本记录
写 TTL 清理
写 Dashboard 页面
写日志摘要
写 release worker 流程
写 provider 失败切换逻辑
```

### 人必须做

```text
开通云平台账号
充值或绑定付款方式
创建 API key
决定每日/月度预算
批准首次租赁某类 GPU
批准高成本任务
批准访问敏感数据
批准许可证使用
判断实验方向和边界条件
审核自动释放策略是否安全
处理平台风控、验证码、实名认证
```

## 12. 安全和成本底线

必须有：

```text
每台 worker 独立 token
bootstrap token 一次性或短有效期
租赁机器默认 TTL
任务完成自动释放
预算上限
kill-all 紧急按钮
云 API key 只放控制节点
不要把 API key 写进镜像
结果先上传，再释放机器
释放前做 artifact 检查
所有租赁/释放/审批写审计日志
```

禁止：

```text
无限期租 GPU
无预算上限
把云 API key 给 Agent
让 Agent 自己决定高成本租赁
任务失败但机器一直挂着
结果没上传就释放机器
```

## 13. 最终形态

未来你在 Mac 上说：

```text
跑这个新参数扫描，预算 20 美元以内。
本地有空机器就用本地，没有就租 4090。
失败先自动修复两次，超过预算或需要改边界条件再找我。
```

系统执行：

```text
1. 检查本地 worker
2. 发现 GPU 不够
3. 查询可租 GPU
4. 估算成本
5. 成本在预算内，自动租赁
6. 启动 EvoScientist Agent
7. 跑实验
8. 上传结果
9. 总结日志
10. 释放 GPU
11. 把结果和失败经验写入数据飞轮
```

你只处理：

```text
是否扩大预算
是否授权许可证
是否改变实验方向
是否修改边界条件
是否接受某个科研判断
```

这就是 QQ 农场科研版的资源自动化层。

## 14. 参考资料

1. Tailscale Auth Keys：<https://tailscale.com/kb/1085/auth-keys>
2. cloud-init examples：<https://docs.cloud-init.io/en/latest/reference/examples.html>
3. Ansible getting started：<https://docs.ansible.com/projects/ansible/latest/getting_started/index.html>
4. OpenTofu docs：<https://opentofu.org/docs/>
5. RunPod Create Pod API：<https://docs.runpod.io/api-reference/pods/POST/pods>
6. Vast.ai Create Instance API：<https://docs.vast.ai/api-reference/instances/create-instance>
7. Lambda Cloud API：<https://docs-api.lambda.ai/api/cloud>
8. Hetzner Cloud API：<https://docs.hetzner.cloud/reference/cloud>
