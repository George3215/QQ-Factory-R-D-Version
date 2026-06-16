const state = {
  view: "overview",
  apiOnline: false,
  workers: [],
  jobs: [],
  approvals: [],
  events: [],
  reports: [],
  token: localStorage.getItem("loopFarmAdminToken") || "",
};

const views = [
  ["overview", "OV", "Overview", "统一调度"],
  ["install", "IN", "Install", "多端安装"],
  ["workers", "WK", "Workers", "机器"],
  ["jobs", "JB", "Jobs", "任务"],
  ["approvals", "AP", "Approvals", "审批"],
  ["reports", "RP", "Reports", "Codex/Claude"],
  ["events", "EV", "Events", "事件"],
];

const viewHost = document.querySelector("#viewHost");
const viewTitle = document.querySelector("#viewTitle");
const viewKicker = document.querySelector("#viewKicker");
const adminTokenInput = document.querySelector("#adminToken");

adminTokenInput.value = state.token;

function h(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
}

function statusTone(status) {
  const value = String(status || "").toLowerCase();
  if (["online", "succeeded", "approved", "ok", "registered"].includes(value)) return "ok";
  if (["queued", "running", "pending", "blocked"].includes(value)) return "warn";
  if (["failed", "rejected", "offline"].includes(value)) return "danger";
  return "";
}

function token(label, status) {
  return `<span class="status-token ${statusTone(status)}">${label}: ${status || "unknown"}</span>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function api(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `${path} ${response.status}`);
  return data;
}

async function refresh() {
  try {
    await api("/api/health");
    state.apiOnline = true;
  } catch {
    state.apiOnline = false;
  }
  if (state.token) {
    const [workers, jobs, approvals, events, reports] = await Promise.allSettled([
      api("/api/workers"),
      api("/api/jobs"),
      api("/api/approvals"),
      api("/api/job-events"),
      api("/api/reports"),
    ]);
    if (workers.status === "fulfilled") state.workers = workers.value.workers || [];
    if (jobs.status === "fulfilled") state.jobs = jobs.value.jobs || [];
    if (approvals.status === "fulfilled") state.approvals = approvals.value.approvals || [];
    if (events.status === "fulfilled") state.events = events.value.events || [];
    if (reports.status === "fulfilled") state.reports = reports.value.reports || [];
  }
  updateShell();
  renderView();
}

function updateShell() {
  document.querySelector("#healthPill").textContent = state.apiOnline ? "online" : "offline";
  document.querySelector("#healthPill").classList.toggle("ok", state.apiOnline);
  document.querySelector("#workerCount").textContent = `${state.workers.length} workers`;
  document.querySelector("#metricWorkers").textContent = state.workers.length;
  document.querySelector("#metricJobs").textContent = state.jobs.length;
  document.querySelector("#metricApprovals").textContent = state.approvals.filter((item) => item.status === "pending").length;
  document.querySelector("#metricAuto").textContent = state.jobs.filter((item) => ["succeeded", "failed", "blocked"].includes(item.status)).length;

  const eventList = document.querySelector("#eventList");
  eventList.replaceChildren();
  state.reports.slice(0, 12).forEach((report) => {
    const item = h("div", "event-item");
    item.append(
      h("strong", "", `${report.source} · ${report.level} · ${report.title}`),
      h("small", "", `${report.worker_id} · ${report.message || JSON.stringify(report.payload || {})}`)
    );
    eventList.append(item);
  });
}

function renderNav() {
  const host = document.querySelector("#navList");
  host.replaceChildren();
  views.forEach(([id, icon, title]) => {
    const item = h("button", `nav-item ${state.view === id ? "active" : ""}`);
    item.append(h("span", "nav-icon", icon), h("span", "", title));
    item.addEventListener("click", () => {
      state.view = id;
      renderNav();
      renderView();
    });
    host.append(item);
  });
}

function setTitle() {
  const item = views.find(([id]) => id === state.view) || views[0];
  viewKicker.textContent = item[3].toUpperCase();
  viewTitle.textContent = item[2];
}

function panel(title, body, badge = "") {
  return `
    <section class="panel">
      <div class="panel-head">
        <h2>${escapeHtml(title)}</h2>
        ${badge ? `<span class="panel-badge">${escapeHtml(badge)}</span>` : ""}
      </div>
      ${body}
    </section>
  `;
}

function renderOverview() {
  viewHost.innerHTML = `
    <div class="grid two">
      ${panel("Mac 统一调度", `
        <div class="row"><div class="row-main"><strong>控制中心</strong><small>${state.apiOnline ? "已连接" : "离线"}</small></div>${token("API", state.apiOnline ? "online" : "offline")}</div>
        <div class="row"><div class="row-main"><strong>Worker</strong><small>已注册机器</small></div><strong>${state.workers.length}</strong></div>
        <div class="row"><div class="row-main"><strong>待审批</strong><small>需要你判断的问题</small></div><strong>${state.approvals.filter((x) => x.status === "pending").length}</strong></div>
        <div class="row"><div class="row-main"><strong>Codex/Claude 报告</strong><small>其他电脑主动发回的信息</small></div><strong>${state.reports.length}</strong></div>
      `, "M2")}
      ${panel("今日推进标准", `
        <div class="row"><div class="row-main"><strong>能否通过 Mac 调度更多事情</strong><small>新增 job / install / approval 操作都算</small></div></div>
        <div class="row"><div class="row-main"><strong>能否减少现场调试</strong><small>新机器一条命令接入 worker</small></div></div>
        <div class="row"><div class="row-main"><strong>Agent 能否处理更多问题</strong><small>smoke runner 已能成功/失败/blocked</small></div></div>
      `)}
    </div>
  `;
}

function renderInstall() {
  viewHost.innerHTML = `
    <div class="grid two">
      ${panel("生成 Worker 安装命令", `
        <div class="form-grid">
          <select id="installPlatform"><option value="linux">Linux worker</option><option value="windows">Windows worker</option></select>
          <input id="installMachine" placeholder="machine name, e.g. lab-gpu-01" />
          <input id="installToken" placeholder="bootstrap token lfbt_xxx" />
          <input id="installRepo" placeholder="repo url" value="https://github.com/George3215/QQ-Factory-R-D-Version.git" />
          <input id="installBase" class="wide" placeholder="install base url" value="${location.origin}/install" />
          <input id="installTailscale" class="wide" placeholder="optional tailscale auth key" />
        </div>
        <p style="height:10px"></p>
        <button class="primary" id="genInstall">Generate</button>
        <p style="height:10px"></p>
        <pre class="code-box" id="installCommand"></pre>
      `)}
      ${panel("创建 Bootstrap Token", `
        <div class="form-grid">
          <input id="tokenMachine" placeholder="machine name" />
          <input id="tokenTtl" placeholder="ttl seconds" value="3600" />
        </div>
        <p style="height:10px"></p>
        <button class="primary" id="createToken">Create Token</button>
        <p style="height:10px"></p>
        <pre class="code-box" id="tokenOutput"></pre>
      `)}
      ${panel("分布式架构", `
        <div class="row"><div class="row-main"><strong>Mac</strong><small>唯一主控入口：Dashboard、farmctl、审批、调度</small></div>${token("role", "control")}</div>
        <div class="row"><div class="row-main"><strong>Linux</strong><small>常规 worker：GPU、CPU、云服务器</small></div>${token("role", "worker")}</div>
        <div class="row"><div class="row-main"><strong>Windows</strong><small>常规 worker：GUI 仿真、MATLAB/COMSOL/Abaqus</small></div>${token("role", "worker")}</div>
      `)}
    </div>
  `;
  document.querySelector("#genInstall").addEventListener("click", generateInstallCommand);
  document.querySelector("#createToken").addEventListener("click", createBootstrapToken);
}

function renderWorkers() {
  viewHost.innerHTML = panel("Workers", state.workers.map((worker) => `
    <div class="row">
      <div class="row-main">
        <strong>${escapeHtml(worker.machine_name)}</strong>
        <small>${escapeHtml(worker.id)} · ${escapeHtml(worker.os)}</small>
      </div>
      ${token("status", worker.status)}
    </div>
  `).join("") || "<p>No workers.</p>");
}

function renderJobs() {
  viewHost.innerHTML = `
    <div class="grid two">
      ${panel("Create smoke_test Job", `
        <div class="form-grid">
          <select id="jobWorker">${state.workers.map((w) => `<option value="${escapeHtml(w.id)}">${escapeHtml(w.machine_name)}</option>`).join("")}</select>
          <input id="jobMessage" placeholder="message" value="hello loop farm" />
          <label><input type="checkbox" id="jobApproval" /> request approval</label>
        </div>
        <p style="height:10px"></p>
        <button class="primary" id="createJob">Create Job</button>
      `)}
      ${panel("Jobs", state.jobs.map((job) => `
        <div class="row">
          <div class="row-main">
            <strong>${escapeHtml(job.recipe)}</strong>
            <small>${escapeHtml(job.id)} · ${escapeHtml(job.target_worker_id || "any worker")}</small>
          </div>
          ${token("status", job.status)}
        </div>
      `).join("") || "<p>No jobs.</p>")}
    </div>
  `;
  const btn = document.querySelector("#createJob");
  if (btn) btn.addEventListener("click", createSmokeJob);
}

function renderApprovals() {
  viewHost.innerHTML = panel("Approval Queue", state.approvals.map((item) => `
    <div class="row">
      <div class="row-main">
        <strong>${escapeHtml(item.title)}</strong>
        <small>${escapeHtml(item.id)} · job ${escapeHtml(item.job_id || "none")} · ${escapeHtml(JSON.stringify(item.body))}</small>
      </div>
      <div>
        ${token("status", item.status)}
        ${item.status === "pending" ? `<button data-approve="${item.id}" class="primary">Approve</button><button data-reject="${item.id}" class="danger">Reject</button>` : ""}
      </div>
    </div>
  `).join("") || "<p>No approvals.</p>");
  viewHost.querySelectorAll("[data-approve]").forEach((button) => button.addEventListener("click", () => resolveApproval(button.dataset.approve, "approved")));
  viewHost.querySelectorAll("[data-reject]").forEach((button) => button.addEventListener("click", () => resolveApproval(button.dataset.reject, "rejected")));
}

function renderEvents() {
  viewHost.innerHTML = panel("Job Events", state.events.map((event) => `
    <div class="row">
      <div class="row-main">
        <strong>${escapeHtml(event.event_type)} · ${escapeHtml(event.message)}</strong>
        <small>${escapeHtml(event.id)} · job ${escapeHtml(event.job_id || "none")} · worker ${escapeHtml(event.worker_id || "none")}</small>
      </div>
    </div>
  `).join("") || "<p>No events.</p>");
}

function renderReports() {
  viewHost.innerHTML = panel("Codex / Claude Code Reports", state.reports.map((report) => `
    <div class="row">
      <div class="row-main">
        <strong>${escapeHtml(report.source)} · ${escapeHtml(report.title)}</strong>
        <small>${escapeHtml(report.worker_id)} · ${escapeHtml(report.level)} · ${escapeHtml(report.message)}</small>
        <small>${escapeHtml(JSON.stringify(report.payload || {}))}</small>
      </div>
      ${token("level", report.level)}
    </div>
  `).join("") || "<p>No Codex/Claude reports yet.</p>");
}

function renderView() {
  setTitle();
  if (state.view === "overview") renderOverview();
  if (state.view === "install") renderInstall();
  if (state.view === "workers") renderWorkers();
  if (state.view === "jobs") renderJobs();
  if (state.view === "approvals") renderApprovals();
  if (state.view === "reports") renderReports();
  if (state.view === "events") renderEvents();
}

function buildInstallCommand({ platform, controlUrl, machineName, tokenValue, repoUrl, installBase, tailscaleKey }) {
  if (platform === "windows") {
    return `powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $script = Join-Path $env:TEMP 'worker-windows.ps1'; Invoke-WebRequest -UseBasicParsing -Uri '${installBase}/worker-windows.ps1' -OutFile $script; & $script -ControlUrl '${controlUrl}' -BootstrapToken '${tokenValue}' -MachineName '${machineName}'${repoUrl ? ` -RepoUrl '${repoUrl}'` : ""}${tailscaleKey ? ` -TailscaleAuthKey '${tailscaleKey}'` : ""} }"`;
  }
  const script = platform === "macos" ? "worker-macos.sh" : "worker-linux.sh";
  const prefix = platform === "linux" ? "sudo bash" : "bash";
  return `curl -fsSL ${installBase}/${script} | ${prefix} -s -- --control-url '${controlUrl}' --bootstrap-token '${tokenValue}' --machine-name '${machineName}'${repoUrl ? ` --repo-url '${repoUrl}'` : ""}${tailscaleKey ? ` --tailscale-auth-key '${tailscaleKey}'` : ""}`;
}

function generateInstallCommand() {
  const command = buildInstallCommand({
    platform: document.querySelector("#installPlatform").value,
    controlUrl: location.origin,
    machineName: document.querySelector("#installMachine").value,
    tokenValue: document.querySelector("#installToken").value,
    repoUrl: document.querySelector("#installRepo").value,
    installBase: document.querySelector("#installBase").value,
    tailscaleKey: document.querySelector("#installTailscale").value,
  });
  document.querySelector("#installCommand").textContent = command;
}

async function createBootstrapToken() {
  const machine = document.querySelector("#tokenMachine").value;
  const ttl = Number(document.querySelector("#tokenTtl").value || "3600");
  const data = await api("/api/bootstrap-tokens", {
    method: "POST",
    body: JSON.stringify({ machine_name: machine, ttl_seconds: ttl }),
  });
  document.querySelector("#tokenOutput").textContent = JSON.stringify(data, null, 2);
  const installToken = document.querySelector("#installToken");
  const installMachine = document.querySelector("#installMachine");
  if (installToken) installToken.value = data.token;
  if (installMachine) installMachine.value = data.machine_name;
}

async function createSmokeJob() {
  const target = document.querySelector("#jobWorker").value || null;
  const message = document.querySelector("#jobMessage").value;
  const requestApproval = document.querySelector("#jobApproval").checked;
  await api("/api/jobs", {
    method: "POST",
    body: JSON.stringify({
      recipe: "smoke_test",
      target_worker_id: target,
      payload: requestApproval
        ? { request_approval: true, approval_title: "需要人类批准", risk: "L4", reason: message }
        : { message },
    }),
  });
  await refresh();
}

async function resolveApproval(id, decision) {
  await api("/api/approvals/resolve", {
    method: "POST",
    body: JSON.stringify({
      approval_id: id,
      decision,
      comment: "resolved from control-ui",
    }),
  });
  await refresh();
}

document.querySelector("#saveToken").addEventListener("click", () => {
  state.token = adminTokenInput.value;
  localStorage.setItem("loopFarmAdminToken", state.token);
  refresh();
});
document.querySelector("#refreshBtn").addEventListener("click", refresh);

renderNav();
refresh();
