#!/usr/bin/env bash
set -euo pipefail

CONTROL_URL=""
BOOTSTRAP_TOKEN=""
MACHINE_NAME="$(hostname)"
REPO_URL=""
TAILSCALE_AUTH_KEY=""
INSTALL_ROOT="/opt/loop-farm"
AGENT_HOME="/opt/loop-farm-agent"
SERVICE_NAME="loop-farm-agent"

usage() {
  cat <<'USAGE'
Usage:
  worker-linux.sh --control-url URL --bootstrap-token TOKEN [options]

Options:
  --machine-name NAME       Worker machine name. Defaults to hostname.
  --repo-url URL            Git repo URL for loop-farm. If omitted, INSTALL_ROOT must already exist.
  --tailscale-auth-key KEY  Optional Tailscale auth key for automatic join.
  --install-root PATH       Defaults to /opt/loop-farm.
  --agent-home PATH         Defaults to /opt/loop-farm-agent.

Environment:
  CONTROL_URL, BOOTSTRAP_TOKEN, MACHINE_NAME, REPO_URL, TAILSCALE_AUTH_KEY, INSTALL_ROOT, AGENT_HOME
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --control-url)
      CONTROL_URL="$2"
      shift 2
      ;;
    --bootstrap-token)
      BOOTSTRAP_TOKEN="$2"
      shift 2
      ;;
    --machine-name)
      MACHINE_NAME="$2"
      shift 2
      ;;
    --repo-url)
      REPO_URL="$2"
      shift 2
      ;;
    --tailscale-auth-key)
      TAILSCALE_AUTH_KEY="$2"
      shift 2
      ;;
    --install-root)
      INSTALL_ROOT="$2"
      shift 2
      ;;
    --agent-home)
      AGENT_HOME="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

CONTROL_URL="${CONTROL_URL:-${LOOP_FARM_CONTROL_URL:-}}"
BOOTSTRAP_TOKEN="${BOOTSTRAP_TOKEN:-${LOOP_FARM_BOOTSTRAP_TOKEN:-}}"
MACHINE_NAME="${MACHINE_NAME:-${LOOP_FARM_MACHINE_NAME:-$(hostname)}}"
REPO_URL="${REPO_URL:-${LOOP_FARM_REPO_URL:-}}"
TAILSCALE_AUTH_KEY="${TAILSCALE_AUTH_KEY:-${LOOP_FARM_TAILSCALE_AUTH_KEY:-}}"
INSTALL_ROOT="${INSTALL_ROOT:-${LOOP_FARM_INSTALL_ROOT:-/opt/loop-farm}}"
AGENT_HOME="${AGENT_HOME:-${LOOP_FARM_AGENT_HOME:-/opt/loop-farm-agent}}"

if [[ -z "$CONTROL_URL" || -z "$BOOTSTRAP_TOKEN" ]]; then
  echo "CONTROL_URL and BOOTSTRAP_TOKEN are required." >&2
  usage >&2
  exit 2
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "Please run as root, for example via sudo." >&2
  exit 1
fi

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

install_packages() {
  if need_cmd apt-get; then
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip git curl ca-certificates
  elif need_cmd dnf; then
    dnf install -y python3 python3-pip git curl ca-certificates
  elif need_cmd yum; then
    yum install -y python3 python3-pip git curl ca-certificates
  else
    echo "No supported package manager found. Install python3, pip, git, curl manually." >&2
  fi
}

install_packages

if [[ -n "$TAILSCALE_AUTH_KEY" ]]; then
  if ! need_cmd tailscale; then
    if need_cmd apt-get; then
      curl -fsSL https://tailscale.com/install.sh | sh
    else
      echo "tailscale not found; install it manually or extend this script for your distro." >&2
    fi
  fi
  if need_cmd tailscale; then
    tailscale up --auth-key "$TAILSCALE_AUTH_KEY" --hostname "$MACHINE_NAME" || true
  fi
fi

mkdir -p "$INSTALL_ROOT" "$AGENT_HOME" "$AGENT_HOME/logs" "$AGENT_HOME/workspaces" "$AGENT_HOME/artifacts"

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

cat >/etc/systemd/system/${SERVICE_NAME}.service <<SERVICE
[Unit]
Description=Loop Farm EvoScientist Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment=LOOP_FARM_AGENT_CONFIG=${AGENT_HOME}/config.json
WorkingDirectory=${AGENT_HOME}
ExecStart=${AGENT_HOME}/venv/bin/loop-farm-agent daemon --config ${AGENT_HOME}/config.json
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

echo "Installed $SERVICE_NAME for $MACHINE_NAME."
echo "Check status with: systemctl status $SERVICE_NAME"
