# RoboDojo VR Teleoperation Collector

**English** | [简体中文](README.zh-CN.md)

A browser-based WebXR bimanual teleoperation and demonstration data collection tool for RoboDojo simulation. Recommended GitHub repository name: `robodojo-vr-teleop-collector`.

Code snapshot: 2026-09-24. The core collector files on the Piper and ymq workstations were checked against the same version. Machine-specific paths remain in each workstation's local `config.env`; do not commit absolute paths from a deployment machine to a public repository.

This package contains only the VR data collection code. It does not include RoboDojo assets, Isaac Sim, Isaac Lab, cuRobo, collected data, or machine credentials. After installing and configuring the external environment, one script starts the simulator, USB forwarding, headset controller page, and desktop spectator page.

The browser WebXR paths have been integrated on the Piper workstation with Isaac Sim 5.1, the RoboDojo/Isaac Lab environment, Meta Quest, and Pico. Other headsets that support WebXR and the `xr-standard` controller mapping may work, but their button mapping and tracking must be checked before they are treated as validated.

> Project status: research and internal data collection tool, not a general-purpose product release. Current evidence covers selected CPU/protocol tests, RoboDojo simulation, and specific headset paths. It does not validate every task, every headset, or real-robot operation. See [`VALIDATION.md`](VALIDATION.md) for detailed evidence boundaries.

## 1. Repository layout

```text
robodojo-vr-teleop-collector/
├── external/RoboDojo/   # Download RoboDojo code and assets here
├── external/isaac-sim/  # Optional Isaac Sim 5.1 binary installation
├── data/                # Default HDF5 output directory
├── patches/             # RoboDojo patch required by the current Piper runtime
├── web/                 # Headset controller and desktop spectator pages
├── config.example.env   # Copy and edit this configuration file
├── start_desktop.sh     # Normal operator entry point
└── run_4090.sh          # Service and watchdog entry point
```

## 2. One-time installation

Requirements: Ubuntu Linux, an NVIDIA GPU and driver, Git LFS, Miniconda, Android Platform Tools (`adb`), and `tmux`. Isaac Sim 5.x uses Python 3.11.

### 2.1 Download RoboDojo and its assets

```bash
cd robodojo-vr-teleop-collector
git clone --recurse-submodules https://github.com/RoboDojo-Benchmark/RoboDojo.git external/RoboDojo
git -C external/RoboDojo checkout e0703b03bb1af6075400e9d60dc17a792793960c
git -C external/RoboDojo submodule update --init --recursive
git -C external/RoboDojo apply ../../patches/robodojo_piper_runtime.patch

cd external/RoboDojo
bash scripts/install.sh
bash scripts/init_assets.sh
```

The pinned commit and patch match the current Piper runtime. Do not follow the latest upstream revision and continue to claim compatibility without revalidation. `scripts/init_assets.sh` downloads robot, object, and layout assets into RoboDojo's `Assets/` directory; those assets are not included in this package.

If you use NVIDIA's Isaac Sim 5.1 binary archive, extract it into `external/isaac-sim/`, then follow the Isaac Lab binary installation guide and point `external/RoboDojo/third_party/IsaacLab/_isaac_sim` to that directory. If `scripts/install.sh` already completed successfully and RoboDojo passes its own checks, do not install a second binary copy.

Official references:

- RoboDojo: <https://github.com/RoboDojo-Benchmark/RoboDojo>
- Isaac Sim 5.1 workstation installation: <https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_workstation.html>
- Isaac Lab binary installation: <https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/binaries_installation.html>

### 2.2 Configure the collector

```bash
cd robodojo-vr-teleop-collector
cp config.example.env config.env
```

The relative paths normally work as-is. If RoboDojo, Isaac Lab, the output directory, or `adb` is elsewhere, edit only `config.env`. The launch scripts do not contain a username, IP address, or fixed installation path.

Activate the RoboDojo environment and install the collector's small dependency set:

```bash
conda activate RoboDojo
python -m pip install -r requirements.txt
chmod +x launch.sh run_4090.sh start_desktop.sh pico_wireless.sh
```

## 3. Running a collection session

1. Connect and unlock one VR headset over USB, then allow USB debugging inside the headset.
2. Run `adb devices -l` and confirm that the target device status is `device`. Connect only one USB VR headset during startup.
3. Start the collector:

```bash
cd robodojo-vr-teleop-collector
./start_desktop.sh
```

The script restarts this package's own `tmux robodojo` service, creates `adb reverse tcp:8443 tcp:8443`, opens the controller page in the headset, and opens the read-only `/spectator` page on the workstation. The address and token are generated locally at runtime and are not stored in the package.

When the page reports `ready`, enter VR in the headset. Release both grip buttons first, then hold a grip button to take control of the corresponding arm. The triggers control the grippers. Before recording, reset to the standard initial state. Use the sequence: start recording → complete the task → save. Do not label failed attempts as successful demonstrations.

Common controls:

| Input | Action |
|---|---|
| Left/right grip | Hold to control the corresponding arm; release to hold position |
| Left/right trigger | Control the corresponding gripper |
| Left X | Start recording |
| Left Y | Save |
| Right A | Pause/recenter |
| Right B | Reset; go back while in a menu |
| Press either thumbstick | Open or close the task menu |

The actual button indices in Meta/Pico browsers must be verified on the device. After changing headsets, test both arms, both grippers, pause, and reset without recording before starting formal data collection.

## 4. Initial collection order

The target is 100 accepted trajectories per task. The initial plan prioritizes two groups with higher measured OpenWAM success rates:

1. `put_bottles_into_dustbin`, `stack_bowls`, `fold_clothes`, `play_tic_tac_toe`, `pour_liquid_into_cup`, `build_tower`, `match_and_pick_from_conveyor`, `make_kong`
2. `store_laptop_and_headphones`, `fold_clothes_random`, `pour_balls_into_vase`, `cover_blocks`, `pour_liquid_into_cup_random`, `stack_blocks`, `organize_table`, `hang_mugs`

Tasks ending in `*_random` are randomized-layout tasks, not error-recovery tasks. The initial batch contains 16 tasks and targets 1,600 accepted trajectories. Error recovery and lower-success-rate tasks are scheduled separately.

Current runtime boundary: on 2026-09-24, the Piper/Isaac Sim 5.1 runtime was updated to fix particle-cloth view initialization order, reward compatibility when GPU cloth vertices have no rigid-body pose, and texture binding when the root prim of a material USD is itself a `Material`. `fold_clothes` was observed starting and running continuously, then returning to `ready` after switching to another official layout in the same process. The rigid-body task `stack_blocks` passed the same layout-switch check. `fold_clothes_random` has not been tested separately. The upstream CUDA path still disables fluid tasks, so they must not be listed as collection-ready.

There are two layout operations:

- “Quick reset current scene” reuses the current layout and seed.
- When “official layout rotation” is enabled, “load next official layout” rebuilds the task with the next layout. Both operations are rejected while recording; save or discard the active recording first.

## 5. Data acceptance

Each raw episode is stored as HDF5 with three camera streams, 14D bimanual state/actions, control commands, real wall-clock and simulation timestamps, and task/layout metadata. This is the raw pre-conversion format; do not describe it as an official LeRobot release directory.

Inspect every collected episode at minimum:

```bash
conda activate RoboDojo
./launch.sh --inspect data/episode_xxx.hdf5
```

Formal data requirements: all three camera streams decode; state and action are aligned frame by frame; real timestamps are preserved; no valid-sample interval exceeds 200 ms; the writer reports no backpressure; and WebXR sequence numbers show no abnormal gaps. Debug, keyboard, and synthetic smoke outputs belong only in `validation/` and must not be mixed into `data/`.

## 6. Troubleshooting

- The headset page does not open: allow USB debugging again, run `adb reverse tcp:8443 tcp:8443`, then rerun `start_desktop.sh`.
- Desktop spectator only: use the same token URL printed in the terminal and change the path to `/spectator#token=...`. The spectator page does not send arm commands.
- The page repeatedly disconnects: inspect `robodojo_current.log`, the USB connection, and `/status`. Do not hide a blocked service by only refreshing the page.
- Task switching is slow: a task switch rebuilds the Isaac scene and the page should reconnect automatically. Switching and reset are disabled while recording.
- Inspect the background process: run `tmux attach -t robodojo`; press `Ctrl-b d` to detach without stopping it.
- Stop the service: press `Ctrl-C` inside the `tmux` session, or stop only the process using this package's port 8443. Do not use a global `pkill` that may terminate unrelated Isaac jobs.

Runtime-generated `web_token.txt`, logs, PID files, scene state, and collected data must not be uploaded or repackaged into a public archive.

## 7. README update policy

Every code, configuration, script, or documentation change must update this section. Add entries in reverse chronological order and include:

1. Date and version or commit;
2. Specific changes;
3. Verification actually performed;
4. Remaining unverified behavior or known limitations.

Do not use unverifiable summaries such as “optimized” or “fixed issues.” Keep syntax checks, unit tests, simulation smoke tests, and human VR collection as separate evidence levels.

### Change log

#### 2026-09-24 · Bilingual README

- Preserved the Chinese documentation as `README.zh-CN.md` and added the English default document `README.md`.
- Added language switch links to both documents and kept installation, collection, acceptance, troubleshooting, and update-history sections aligned.
- Documentation verification: relative links, sections, code blocks, and key commands were checked side by side.
- Not verified: this documentation-only update did not rerun unit tests, Isaac Sim, or an end-to-end headset collection session.

#### 2026-09-24 · Initial GitHub preparation

- Recommended the stable repository name `robodojo-vr-teleop-collector`; dates belong in this change log and future releases/tags rather than in the long-lived repository name.
- Added the project scope, current validation boundaries, and mandatory README update policy.
- Updated installation and startup examples to use the recommended repository name.
- Expanded `.gitignore` to prevent accidental commits of data directories, external dependencies, TLS material, and runtime files.
- Replaced device serial numbers, public addresses, and personal absolute paths in `VALIDATION.md` with role descriptions or placeholder paths while retaining the validation results.
- Local verification: Python compilation and syntax checks for four shell scripts passed.
- Not verified: the local machine did not have `pytest` or `node`, so unit tests and JavaScript syntax checks were not rerun; Isaac Sim and end-to-end headset collection were not rerun.
