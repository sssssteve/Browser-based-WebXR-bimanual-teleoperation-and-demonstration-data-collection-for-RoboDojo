# RoboDojo VR Collector

**English** | [简体中文](README.zh-CN.md)

Browser-based WebXR teleoperation and demonstration collection for RoboDojo bimanual simulation.

The workstation runs Isaac Sim, RoboDojo, control, rendering, and HDF5 recording. A VR headset sends controller poses through the browser; the desktop provides a read-only spectator view.

> Research tool, not a general product release. Current validation does not cover every task, headset, or real robot. See [VALIDATION.md](VALIDATION.md).

## Requirements

- Ubuntu Linux with an NVIDIA GPU
- Isaac Sim 5.1 and RoboDojo/Isaac Lab
- Miniconda, Git LFS, `adb`, and `tmux`
- One USB-connected WebXR headset, such as Meta Quest or Pico

RoboDojo assets, Isaac Sim, collected data, and credentials are not included in this repository.

## Quick start

```bash
git clone https://github.com/YOUR_ACCOUNT/robodojo-vr-collector.git
cd robodojo-vr-collector

git clone --recurse-submodules \
  https://github.com/RoboDojo-Benchmark/RoboDojo.git external/RoboDojo
git -C external/RoboDojo checkout e0703b03bb1af6075400e9d60dc17a792793960c
git -C external/RoboDojo submodule update --init --recursive
git -C external/RoboDojo apply ../../patches/robodojo_piper_runtime.patch

cd external/RoboDojo
bash scripts/install.sh
bash scripts/init_assets.sh
cd ../..

cp config.example.env config.env
conda activate RoboDojo
python -m pip install -r requirements.txt
./start_desktop.sh
```

Edit `config.env` only when RoboDojo, Isaac Lab, the output directory, or `adb` is installed elsewhere.

Before starting, unlock the headset, allow USB debugging, and confirm that `adb devices -l` reports one target device as `device`.

## Collection workflow

1. Wait for the page to report `ready` and enter VR.
2. Release both grip buttons, then hold a grip button to control the corresponding arm.
3. Reset to the standard initial state.
4. Start recording, complete the task, and save the episode.
5. Do not label failed or debug episodes as successful demonstrations.

| Input | Action |
|---|---|
| Left/right grip | Control the corresponding arm |
| Left/right trigger | Control the corresponding gripper |
| Left X / Left Y | Start recording / Save |
| Right A / Right B | Pause or recenter / Reset or back |
| Press either thumbstick | Open or close the task menu |

Verify the actual button mapping without recording whenever the headset model or browser changes.

## Data

Episodes are saved as raw HDF5 with three camera streams, 14D bimanual state/actions, commands, timestamps, and task/layout metadata.

```bash
./launch.sh --inspect data/episode_xxx.hdf5
```

Export a complete, successful, quality-approved episode to the official RoboDojo HDF5 field layout:

```bash
python export_official_hdf5.py data/episode_xxx.hdf5 data/episode_xxx_official.hdf5
```

Accepted data must have decodable cameras, aligned state/actions, preserved timestamps, no valid-sample gap above 200 ms, and no recorder backpressure. Keep debug and synthetic outputs in `validation/`, never in `data/`.

Runtime tokens, logs, PID files, TLS material, scene state, external assets, and collected data must not be committed.

## Documentation

- [Validation evidence and known limitations](VALIDATION.md)
- [Example machine configuration](config.example.env)

## Updates

Every code, configuration, or documentation change must update this section with the date, specific changes, verification performed, and remaining limitations.

### 2026-09-25

- Aligned the portable package with the active Piper collector: synchronized `run.py`, `watchdog.py`, and their tests; added supervised CPU/CUDA task-device switching and in-process task reload support.
- Integrated the newer Meta WebXR/menu and PC spectator implementation from the Mac workspace, plus quality-gated official HDF5 export. Piper's tests referenced these files before the active Piper Web directory received them.
- Kept deployment wrappers portable through `config.env`; Piper-specific absolute paths and runtime state were not copied into the repository.
- Verification: the exact Mac package passed 37 CPU/protocol tests in an isolated Piper-side staging directory, plus Python compilation and JavaScript/Shell syntax checks.
- Remaining boundary: the separate `shucai` host was unreachable during this sync, and no Isaac Sim or headset session was restarted.
- Shortened both READMEs to focus on setup, collection, data acceptance, and evidence boundaries.
- Removed duplicated deployment detail, task planning, and historical validation results from the project homepage; `VALIDATION.md` remains the evidence record.
- Documentation check: language links, relative links, code fences, pinned commit, port-independent commands, and section parity were checked.
- Not rerun: unit tests, Isaac Sim, and end-to-end headset collection; this update changes documentation only.

### 2026-09-24

- Added bilingual documentation and prepared the package for GitHub publication.
- Sanitized machine identifiers and expanded ignore rules for data, credentials, external dependencies, and runtime files.
