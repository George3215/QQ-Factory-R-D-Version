param(
  [Parameter(Mandatory=$true)][string]$ControlUrl,
  [Parameter(Mandatory=$true)][string]$BootstrapToken,
  [string]$MachineName = $env:COMPUTERNAME,
  [string]$RepoUrl = "",
  [string]$TailscaleAuthKey = "",
  [string]$InstallRoot = "$env:LOCALAPPDATA\LoopFarm\repo",
  [string]$AgentHome = "$env:LOCALAPPDATA\LoopFarmAgent"
)

$ErrorActionPreference = "Stop"

function Require-Command($Name, $Hint) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "$Name is required. $Hint"
  }
}

Require-Command "python" "Install Python 3.11+ and add it to PATH."
Require-Command "git" "Install Git for Windows and add it to PATH."

if ($TailscaleAuthKey -and (Get-Command "tailscale" -ErrorAction SilentlyContinue)) {
  tailscale up --auth-key $TailscaleAuthKey --hostname $MachineName
}

New-Item -ItemType Directory -Force -Path $InstallRoot, $AgentHome, "$AgentHome\logs", "$AgentHome\workspaces", "$AgentHome\artifacts" | Out-Null

if ($RepoUrl) {
  if (Test-Path "$InstallRoot\.git") {
    git -C $InstallRoot pull --ff-only
  } else {
    if (Test-Path $InstallRoot) {
      Remove-Item -Recurse -Force $InstallRoot
    }
    git clone $RepoUrl $InstallRoot
  }
} elseif (-not (Test-Path "$InstallRoot\pyproject.toml")) {
  throw "No -RepoUrl provided and $InstallRoot does not contain pyproject.toml."
}

$skillSource = Join-Path $InstallRoot "skills\loop-farm-reporter"
if (Test-Path $skillSource) {
  $skillsDir = Join-Path $env:USERPROFILE ".codex\skills"
  $skillTarget = Join-Path $skillsDir "loop-farm-reporter"
  New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null
  if (Test-Path $skillTarget) {
    Remove-Item -Recurse -Force $skillTarget
  }
  Copy-Item -Recurse -Force $skillSource $skillTarget
  Write-Host "Installed Codex skill: $skillTarget"
}

python -m venv "$AgentHome\venv"
& "$AgentHome\venv\Scripts\python.exe" -m pip install --upgrade pip
& "$AgentHome\venv\Scripts\pip.exe" install -e $InstallRoot

& "$AgentHome\venv\Scripts\loop-farm-agent.exe" register `
  --control-url $ControlUrl `
  --bootstrap-token $BootstrapToken `
  --machine-name $MachineName `
  --config "$AgentHome\config.json" `
  --work-dir "$AgentHome\workspaces" `
  --artifact-dir "$AgentHome\artifacts"

$taskName = "LoopFarmAgent"
$action = New-ScheduledTaskAction `
  -Execute "$AgentHome\venv\Scripts\loop-farm-agent.exe" `
  -Argument "daemon --config `"$AgentHome\config.json`"" `
  -WorkingDirectory $AgentHome
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Loop Farm EvoScientist Agent" | Out-Null
Start-ScheduledTask -TaskName $taskName

Write-Host "Installed LoopFarmAgent for $MachineName."
Write-Host "Agent home: $AgentHome"
Write-Host "Check task: Get-ScheduledTask -TaskName LoopFarmAgent"
