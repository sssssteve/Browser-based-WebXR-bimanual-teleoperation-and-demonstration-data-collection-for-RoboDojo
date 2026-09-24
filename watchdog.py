#!/usr/bin/env python3
"""Atomic runtime progress and a process-out Isaac watchdog."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


class ProgressFile:
    def __init__(self, path, epoch_path=None):
        self.path = Path(path)
        self.epoch_path = Path(epoch_path) if epoch_path else self.path.with_suffix(".epoch")
        self.state = {}
        self.phase_started = time.monotonic()

    def start_epoch(self, task):
        previous = read_progress(self.path) or {}
        try:
            epoch = int(self.epoch_path.read_text()) + 1
        except (OSError, ValueError):
            epoch = int(previous.get("env_epoch", 0)) + 1
        atomic_write(self.epoch_path, f"{epoch}\n")
        previous_operation = previous.get("operation")
        carry_operation = (previous.get("restart_requested") or
                           (isinstance(previous_operation, dict) and
                            previous_operation.get("status") in ("accepted", "running")))
        operation = previous_operation if carry_operation else None
        if operation:
            operation = dict(operation, status="running", phase="process_start")
        self.state = {
            "pid": os.getpid(), "env_epoch": epoch, "task": task,
            "phase": "starting", "sim_tick": 0, "restart_requested": False,
            "operation": operation,
        }
        self.phase_started = time.monotonic()
        self.update("starting")
        return epoch, operation

    def update(self, phase=None, **fields):
        now = time.monotonic()
        if phase is not None and phase != self.state.get("phase"):
            self.phase_started = now
            self.state["phase"] = phase
        self.state.update(fields)
        self.state["updated_monotonic"] = now
        self.state["phase_started_monotonic"] = self.phase_started
        self.state["phase_duration_ms"] = round((now - self.phase_started) * 1000, 1)
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        atomic_write(self.path, json.dumps(self.state, ensure_ascii=False) + "\n")
        return dict(self.state)


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text)
    os.replace(temporary, path)


def read_progress(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def phase_timeout(phase, initial, runtime, reset, shutdown):
    phase = phase or "starting"
    if phase.startswith(("starting", "initialize", "first_observation")):
        return initial
    if phase.startswith(("reset", "restore")):
        return reset
    if phase.startswith(("shutdown", "restart")):
        return shutdown
    return runtime


def terminate_group(process, grace):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=grace)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=max(grace, 1))


def archive_diagnostic(progress_path, directory, reason, state):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {"reason": reason, "captured_at": datetime.now(timezone.utc).isoformat(),
               "progress": state}
    target = directory / f"watchdog_{stamp}_{os.getpid()}_{time.monotonic_ns()}.json"
    atomic_write(target, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return target


def supervise(command, progress_path, diagnostics_dir, *, initial_timeout=360,
              runtime_timeout=20, reset_timeout=90, shutdown_timeout=30,
              terminate_grace=10, max_restarts=3, poll_interval=.25, task_file=None):
    failures = 0
    stop_signal = [None]

    def request_stop(signum, _frame):
        stop_signal[0] = signum

    previous_handlers = {}
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        previous_handlers[signum] = signal.signal(signum, request_stop)
    while True:
        child_command = list(command)
        if task_file is not None:
            task = Path(task_file).read_text().strip()
            child_command = [task if item == "__TASK__" else item for item in child_command]
        process = subprocess.Popen(child_command, start_new_session=True)
        launched = time.monotonic()
        timed_out = False
        state = None
        while process.poll() is None:
            if stop_signal[0] is not None:
                print(f"[watchdog] forwarding signal {stop_signal[0]} to child group", flush=True)
                terminate_group(process, terminate_grace)
                for signum, handler in previous_handlers.items():
                    signal.signal(signum, handler)
                return 128 + int(stop_signal[0])
            state = read_progress(progress_path)
            if state and state.get("pid") == process.pid:
                age = time.monotonic() - float(state.get("updated_monotonic", launched))
                allowed = phase_timeout(state.get("phase"), initial_timeout, runtime_timeout,
                                        reset_timeout, shutdown_timeout)
            else:
                age = time.monotonic() - launched
                allowed = initial_timeout
            if age > allowed:
                reason = (f"phase={None if state is None else state.get('phase')} "
                          f"stalled_for={age:.1f}s timeout={allowed:.1f}s")
                target = archive_diagnostic(progress_path, diagnostics_dir, reason, state)
                print(f"[watchdog] {reason}; diagnostic={target}", flush=True)
                terminate_group(process, terminate_grace)
                timed_out = True
                break
            time.sleep(poll_interval)
        status = process.poll()
        state = read_progress(progress_path) or state or {}
        intentional = bool(state.get("restart_requested"))
        print(f"[watchdog] child pid={process.pid} exit={status} intentional={intentional}", flush=True)
        if intentional and not timed_out:
            continue
        if status == 0 and not timed_out:
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
            return 0
        failures += 1
        if failures > max_restarts:
            print(f"[watchdog] restart limit reached ({max_restarts})", flush=True)
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
            return status if isinstance(status, int) and status != 0 else 1
        print(f"[watchdog] controlled restart {failures}/{max_restarts}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--progress", required=True)
    parser.add_argument("--diagnostics", required=True)
    parser.add_argument("--initial-timeout", type=float, default=360)
    parser.add_argument("--runtime-timeout", type=float, default=20)
    parser.add_argument("--reset-timeout", type=float, default=90)
    parser.add_argument("--shutdown-timeout", type=float, default=30)
    parser.add_argument("--terminate-grace", type=float, default=10)
    parser.add_argument("--max-restarts", type=int, default=3)
    parser.add_argument("--task-file")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a child command is required after --")
    return supervise(command, args.progress, args.diagnostics,
                     initial_timeout=args.initial_timeout,
                     runtime_timeout=args.runtime_timeout,
                     reset_timeout=args.reset_timeout,
                     shutdown_timeout=args.shutdown_timeout,
                     terminate_grace=args.terminate_grace,
                     max_restarts=args.max_restarts, task_file=args.task_file)


if __name__ == "__main__":
    sys.exit(main())
