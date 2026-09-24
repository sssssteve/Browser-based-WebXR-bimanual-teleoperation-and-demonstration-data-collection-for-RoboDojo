#!/usr/bin/env bash
set -eo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$PROJECT/config.env" ]]; then
  # shellcheck disable=SC1091
  source "$PROJECT/config.env"
fi

ROBODOJO_ROOT=${ROBODOJO_ROOT:-$PROJECT/external/RoboDojo}
ISAACLAB_ROOT=${ISAACLAB_ROOT:-$ROBODOJO_ROOT/third_party/IsaacLab}
ROBODOJO_OUTPUT=${ROBODOJO_OUTPUT:-$PROJECT/data}
ROBODOJO_DEVICE=${ROBODOJO_DEVICE:-cuda:0}
ROBODOJO_PORT=${ROBODOJO_PORT:-8443}
export ISAACLAB_ROOT

if [[ ! -d "$ROBODOJO_ROOT" || ! -x "$ISAACLAB_ROOT/isaaclab.sh" ]]; then
  echo "RoboDojo/Isaac Lab 未配置。请复制 config.example.env 为 config.env 并检查路径。" >&2
  exit 2
fi
mkdir -p "$ROBODOJO_OUTPUT"

if [[ -n "${ROBODOJO_CONDA_ENV:-}" ]] && command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
  conda activate "$ROBODOJO_CONDA_ENV"
fi

export OMNI_KIT_ACCEPT_EULA=YES
if [[ -f /usr/share/vulkan/icd.d/nvidia_icd.json ]]; then
  export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/nvidia_icd.json
  export VK_ICD_FILENAMES="$VK_DRIVER_FILES"
fi

TASK_FILE="$PROJECT/current_task.txt"
TOKEN_FILE="$PROJECT/web_token.txt"
SCENE_FILE="$PROJECT/scene_state.json"
PROGRESS_FILE=${ROBODOJO_PROGRESS_FILE:-/dev/shm/robodojo_pico_progress.json}
EPOCH_FILE="$PROJECT/env_epoch.txt"
DIAGNOSTICS="$PROJECT/validation/watchdog"
[[ -s "$TASK_FILE" ]] || printf '%s\n' stack_blocks >"$TASK_FILE"

input_only=false
for arg in "$@"; do
  [[ "$arg" == "--input-only" ]] && input_only=true
done

if [[ "$input_only" == true ]]; then
  PROGRESS_FILE=${ROBODOJO_INPUT_PROGRESS_FILE:-/dev/shm/robodojo_pico_input_only_progress.json}
  EPOCH_FILE="$PROJECT/input_only_epoch.txt"
  DIAGNOSTICS="$PROJECT/validation/watchdog_input_only"
  child=("$PROJECT/launch.sh" --input-only --host 0.0.0.0 --port "$ROBODOJO_PORT" --allow-http-lan
         --output "$ROBODOJO_OUTPUT"
         --token-file "$TOKEN_FILE" --progress-file "$PROGRESS_FILE"
         --epoch-file "$EPOCH_FILE" "$@")
else
  child=("$PROJECT/launch.sh"
         --robodojo-root "$ROBODOJO_ROOT"
         --task __TASK__ --headless --device "$ROBODOJO_DEVICE"
         --host 0.0.0.0 --port "$ROBODOJO_PORT" --allow-http-lan
         --scale 1.0 --output "$ROBODOJO_OUTPUT"
         --max-wall-gap 0.2
         --token-file "$TOKEN_FILE" --task-state-file "$TASK_FILE"
         --scene-state-file "$SCENE_FILE" --progress-file "$PROGRESS_FILE"
         --epoch-file "$EPOCH_FILE" "$@")
fi

exec python "$PROJECT/watchdog.py" \
  --progress "$PROGRESS_FILE" --diagnostics "$DIAGNOSTICS" \
  --initial-timeout "${ROBODOJO_INIT_TIMEOUT:-360}" \
  --runtime-timeout "${ROBODOJO_RUNTIME_TIMEOUT:-20}" \
  --reset-timeout "${ROBODOJO_RESET_TIMEOUT:-90}" \
  --shutdown-timeout "${ROBODOJO_SHUTDOWN_TIMEOUT:-30}" \
  --terminate-grace "${ROBODOJO_TERMINATE_GRACE:-10}" \
  --max-restarts "${ROBODOJO_MAX_RESTARTS:-3}" --task-file "$TASK_FILE" -- "${child[@]}"
