#!/usr/bin/env bash
set -eo pipefail
COLLECTOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${ISAACLAB_ROOT:-}" ]]; then
  printf '%s\n' 'Set ISAACLAB_ROOT to the existing Isaac Lab install.' >&2
  exit 2
fi
if [[ -n "${CONDA_PREFIX:-}" && -x "${CONDA_PREFIX}/bin/python" ]]; then
  exec "${CONDA_PREFIX}/bin/python" "${COLLECTOR_DIR}/run.py" "$@"
fi
exec "${ISAACLAB_ROOT}/isaaclab.sh" -p "${COLLECTOR_DIR}/run.py" "$@"
