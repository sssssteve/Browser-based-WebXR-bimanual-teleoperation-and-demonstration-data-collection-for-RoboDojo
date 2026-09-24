#!/usr/bin/env bash
set -euo pipefail

PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$PROJECT/config.env" ]]; then
  # shellcheck disable=SC1091
  source "$PROJECT/config.env"
fi
SESSION=robodojo
PORT=${ROBODOJO_PORT:-8443}
ADB=${ROBODOJO_ADB:-$(command -v adb 2>/dev/null || true)}
ADB_LOG=/tmp/robodojo_adb.log
cd "$PROJECT"

# Close an older launcher terminal left waiting for input, but never kill this copy.
while read -r launcher_pid; do
  if [[ -n "$launcher_pid" && "$launcher_pid" != "$$" ]]; then
    kill "$launcher_pid" 2>/dev/null || true
  fi
done < <(pgrep -f "^bash $PROJECT/start_desktop\.sh$" || true)

echo "正在停止旧的 RoboDojo 服务……"
STATUS=$(curl -fsS --max-time 2 \
  "http://127.0.0.1:$PORT/status?token=$(cat "$PROJECT/web_token.txt")" \
  2>/dev/null || true)
if [[ "$STATUS" == *'"phase": "recording"'* ]]; then
  echo "警告：旧服务正在录制；本次重启会留下未完成的 .partial.hdf5。"
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux send-keys -t "$SESSION":0 C-c 2>/dev/null || true
  for _ in $(seq 1 20); do
    tmux has-session -t "$SESSION" 2>/dev/null || break
    sleep 0.5
  done
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux kill-session -t "$SESSION" 2>/dev/null || true
  fi
fi

# A crashed or detached older launch can outlive tmux. Only stop the process
# currently listening on RoboDojo's dedicated web port.
OLD_PIDS=$(fuser -n tcp "$PORT" 2>/dev/null || true)
if [[ -n "$OLD_PIDS" ]]; then
  kill -TERM $OLD_PIDS 2>/dev/null || true
  for _ in $(seq 1 20); do
    [[ -z "$(fuser -n tcp "$PORT" 2>/dev/null || true)" ]] && break
    sleep 0.5
  done
fi
OLD_PIDS=$(fuser -n tcp "$PORT" 2>/dev/null || true)
if [[ -n "$OLD_PIDS" ]]; then
  kill -KILL $OLD_PIDS 2>/dev/null || true
fi

echo "正在重启 ADB……"
: >"$ADB_LOG"
ADB_READY=false
if [[ -n "$ADB" && -x "$ADB" ]]; then
  timeout 8 "$ADB" kill-server >>"$ADB_LOG" 2>&1 || true
  if timeout 8 "$ADB" start-server >>"$ADB_LOG" 2>&1; then
    ADB_READY=true
    echo "ADB 已重启。"
  else
    echo "ADB 启动失败；详细信息：$ADB_LOG"
  fi
else
  echo "未找到 ADB：$ADB"
fi

echo "正在启动新的 RoboDojo 服务……"
tmux new-session -d -s "$SESSION" \
  "cd '$PROJECT' && exec ./run_4090.sh >>robodojo_current.log 2>&1"

for _ in $(seq 1 60); do
  [[ -s "$PROJECT/web_token.txt" ]] && break
  tmux has-session -t "$SESSION" 2>/dev/null || {
    echo "服务启动失败，请检查：$PROJECT/robodojo_current.log" >&2
    exit 1
  }
  sleep 0.5
done
[[ -s "$PROJECT/web_token.txt" ]] || {
  echo "等待网页 token 超时，请检查：$PROJECT/robodojo_current.log" >&2
  exit 1
}

# ADB does not expose a vendor-neutral VR-device class. Use the first authorized
# USB ADB device and ignore Wi-Fi ADB entries; collection machines should connect
# only the intended headset while launching.
VR_SERIAL=""
VR_FORWARD=false
if [[ "$ADB_READY" == true ]]; then
  for _ in $(seq 1 10); do
    VR_SERIAL=$(timeout 8 "$ADB" devices -l 2>>"$ADB_LOG" |
      awk 'NR > 1 && $2 == "device" && $1 !~ /:/ {print $1; exit}' || true)
    [[ -n "$VR_SERIAL" ]] && break
    sleep 1
  done
fi
if [[ -n "$VR_SERIAL" ]] && \
  timeout 8 "$ADB" -s "$VR_SERIAL" reverse "tcp:$PORT" "tcp:$PORT" >>"$ADB_LOG" 2>&1; then
  VR_FORWARD=true
  echo "VR USB 转发已建立：$VR_SERIAL · tcp:$PORT。"
else
  echo "未检测到已授权的 USB VR 设备；Piper 页面仍会正常打开。"
  echo "连接并解锁头显、允许 USB 调试后，可重新双击本启动器。"
fi

TOKEN=$(cat "$PROJECT/web_token.txt")
VR_PAGE="http://127.0.0.1:$PORT/#token=$TOKEN"
MONITOR_PAGE="http://127.0.0.1:$PORT/spectator#token=$TOKEN"
MONITOR_PAGE_OPENED=false
VR_PAGE_OPENED=false
echo "VR 数采页面：$VR_PAGE"
echo "正在等待仿真就绪……"

for _ in $(seq 1 180); do
  STATUS=$(curl -fsS --max-time 2 \
    "http://127.0.0.1:$PORT/status?token=$TOKEN" 2>/dev/null || true)
  if [[ "$MONITOR_PAGE_OPENED" == false && -n "$STATUS" ]]; then
    if command -v xdg-open >/dev/null; then
      nohup xdg-open "$MONITOR_PAGE" >/tmp/robodojo_browser.log 2>&1 &
    elif command -v gio >/dev/null; then
      nohup gio open "$MONITOR_PAGE" >/tmp/robodojo_browser.log 2>&1 &
    fi
    MONITOR_PAGE_OPENED=true
    echo "已在 Piper 默认浏览器中打开数采页面。"
  fi
  if [[ "$VR_FORWARD" == true && "$VR_PAGE_OPENED" == false && -n "$STATUS" ]]; then
    if timeout 8 "$ADB" -s "$VR_SERIAL" shell am start \
      -a android.intent.action.VIEW -d "$VR_PAGE" >>"$ADB_LOG" 2>&1; then
      echo "已请求在 VR 设备的默认浏览器中打开数采页面。"
    else
      echo "VR 页面自动打开失败；请在头显浏览器手动打开：$VR_PAGE"
    fi
    VR_PAGE_OPENED=true
  fi
  if [[ "$STATUS" == *'"phase": "ready"'* || "$STATUS" == *'"phase": "recording"'* ]]; then
    echo "RoboDojo 已就绪。"
    echo "$STATUS" | python3 -c 'import json,sys; s=json.load(sys.stdin); print("任务：{}  布局：{}  seed：{}  实际频率：{} Hz".format(s.get("task"), s.get("layout_name"), s.get("scene_seed"), s.get("wall_hz")))'
    if [[ -t 0 ]]; then
      read -r -t 10 -p "按 Enter 关闭此窗口；10 秒后自动关闭，服务会继续运行。" || true
    fi
    exit 0
  fi
  sleep 2
done

echo "等待超时，请检查日志：$PROJECT/robodojo_current.log"
echo "也可运行：tmux attach -t $SESSION"
if [[ -t 0 ]]; then read -r -p "按 Enter 关闭此窗口。"; fi
exit 1
