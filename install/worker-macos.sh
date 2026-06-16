#!/usr/bin/env bash
set -euo pipefail

CONTROL_URL=""
BOOTSTRAP_TOKEN=""
MACHINE_NAME="$(scutil --get ComputerName 2>/dev/null || hostname)"
REPO_URL=""
TAILSCALE_AUTH_KEY=""
INSTALL_ROOT="$HOME/Library/Application Support/LoopFarm/repo"
AGENT_HOME="$HOME/Library/Application Support/LoopFarmAgent"
PLIST="$HOME/Library/LaunchAgents/com.loopfarm.agent.plist"

usage() {
  cat <<'USAGE'
Usage:
  worker-macos.sh --control-url URL --bootstrap-token TOKEN [options]

Options:
  --machine-name NAME       Worker machine name. Defaults to macOS ComputerName/hostname.
  --repo-url URL            Git repo URL for loop-farm. If omitted, INSTALL_ROOT must already exist.
  --tailscale-auth-key KEY  Optional Tailscale auth key for automatic join.
  --install-root PATH       Defaults to ~/Library/Application Support/LoopFarm/repo.
  --agent-home PATH         Defaults to ~/Library/Application Support/LoopFarmAgent.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --control-url) CONTROL_URL="$2"; shift 2 ;;
    --bootstrap-token) BOOTSTRAP_TOKEN="$2"; shift 2 ;;
    --machine-name) MACHINE_NAME="$2"; shift 2 ;;
    --repo-url) REPO_URL="$2"; shift 2 ;;
    --tailscale-auth-key) TAILSCALE_AUTH_KEY="$2"; shift 2 ;;
    --install-root) INSTALL_ROOT="$2"; shift 2 ;;
    --agent-home) AGENT_HOME="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

CONTROL_URL="${CONTROL_URL:-${LOOP_FARM_CONTROL_URL:-}}"
BOOTSTRAP_TOKEN="${BOOTSTRAP_TOKEN:-${LOOP_FARM_BOOTSTRAP_TOKEN:-}}"
MACHINE_NAME="${MACHINE_NAME:-${LOOP_FARM_MACHINE_NAME:-$(hostname)}}"
REPO_URL="${REPO_URL:-${LOOP_FARM_REPO_URL:-}}"
TAILSCALE_AUTH_KEY="${TAILSCALE_AUTH_KEY:-${LOOP_FARM_TAILSCALE_AUTH_KEY:-}}"
INSTALL_ROOT="${INSTALL_ROOT:-${LOOP_FARM_INSTALL_ROOT:-$HOME/Library/Application Support/LoopFarm/repo}}"
AGENT_HOME="${AGENT_HOME:-${LOOP_FARM_AGENT_HOME:-$HOME/Library/Application Support/LoopFarmAgent}}"

if [[ -z "$CONTROL_URL" || -z "$BOOTSTRAP_TOKEN" ]]; then
  echo "CONTROL_URL and BOOTSTRAP_TOKEN are required." >&2
  usage >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required. Install it with Homebrew or python.org first." >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required. Install Xcode Command Line Tools or Git first." >&2
  exit 1
fi

if [[ -n "$TAILSCALE_AUTH_KEY" ]] && command -v tailscale >/dev/null 2>&1; then
  tailscale up --auth-key "$TAILSCALE_AUTH_KEY" --hostname "$MACHINE_NAME" || true
fi

mkdir -p "$INSTALL_ROOT" "$AGENT_HOME" "$AGENT_HOME/logs" "$AGENT_HOME/workspaces" "$AGENT_HOME/artifacts" "$HOME/Library/LaunchAgents"

if [[ -n "$REPO_URL" ]]; then
  if [[ -d "$INSTALL_ROOT/.git" ]]; then
    git -C "$INSTALL_ROOT" pull --ff-only
  else
    rm -rf "$INSTALL_ROOT"
    git clone "$REPO_URL" "$INSTALL_ROOT"
  fi
elif [[ ! -f "$INSTALL_ROOT/pyproject.toml" ]]; then
  echo "No --repo-url provided and $INSTALL_ROOT does not contain pyproject.toml." >&2
  exit 1
fi

python3 -m venv "$AGENT_HOME/venv"
"$AGENT_HOME/venv/bin/python" -m pip install --upgrade pip
"$AGENT_HOME/venv/bin/pip" install -e "$INSTALL_ROOT"

"$AGENT_HOME/venv/bin/loop-farm-agent" register \
  --control-url "$CONTROL_URL" \
  --bootstrap-token "$BOOTSTRAP_TOKEN" \
  --machine-name "$MACHINE_NAME" \
  --config "$AGENT_HOME/config.json" \
  --work-dir "$AGENT_HOME/workspaces" \
  --artifact-dir "$AGENT_HOME/artifacts"

cat >"$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.loopfarm.agent</string>
  <key>ProgramArguments</key>
  <array>
    <string>${AGENT_HOME}/venv/bin/loop-farm-agent</string>
    <string>daemon</string>
    <string>--config</string>
    <string>${AGENT_HOME}/config.json</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${AGENT_HOME}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${AGENT_HOME}/logs/agent.out.log</string>
  <key>StandardErrorPath</key>
  <string>${AGENT_HOME}/logs/agent.err.log</string>
</dict>
</plist>
PLIST

launchctl unload "$PLIST" >/dev/null 2>&1 || true
launchctl load "$PLIST"

echo "Installed com.loopfarm.agent for $MACHINE_NAME."
echo "Check logs at: $AGENT_HOME/logs"

