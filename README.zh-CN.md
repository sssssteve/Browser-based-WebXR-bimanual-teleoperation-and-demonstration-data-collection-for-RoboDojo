# RoboDojo VR Teleoperation Collector

[English](README.md) | **简体中文**

面向 RoboDojo 仿真的浏览器 WebXR 双臂遥操作与示范数据采集工具。推荐 GitHub 仓库名：`robodojo-vr-teleop-collector`。

代码快照：2026-09-24。Piper 与 ymq 上的采集器核心文件已核对为同一版本；部署脚本仍通过 `config.env` 保留各机器自己的路径，不应把某台机器的绝对路径提交到公开仓库。

本压缩包只包含 VR 数采代码，不包含 RoboDojo 资产、Isaac Sim、Isaac Lab、cuRobo、采集数据或任何机器密钥。接收方按下面步骤配置环境后，运行一个脚本即可启动仿真、USB 转发、头显控制页和电脑监看页。

已在 Piper 工作站使用 Isaac Sim 5.1、RoboDojo/Isaac Lab 环境以及 Meta Quest、Pico 的浏览器 WebXR 路径联调。其他支持 WebXR 和 `xr-standard` 手柄映射的设备可以尝试，但必须先核对按键和 tracking，不能默认视为已验收。

> 项目状态：研究与内部采集工具，尚未作为通用产品发布。当前证据覆盖部分 CPU/协议测试、RoboDojo 仿真和指定头显链路；不代表所有任务、所有头显或真实机器人均已验收。详细边界见 [`VALIDATION.md`](VALIDATION.md)。

## 1. 目录

```text
robodojo-vr-teleop-collector/
├── external/RoboDojo/   # 接收方下载代码与 Assets
├── external/isaac-sim/  # 可选：解压 Isaac Sim 5.1 二进制版
├── data/                # 默认 HDF5 输出目录
├── patches/             # Piper 当前运行环境所需的 RoboDojo 补丁
├── web/                 # 头显控制页和电脑监看页
├── config.example.env   # 唯一需要复制并修改的配置
├── start_desktop.sh     # 日常启动入口
└── run_4090.sh          # 服务与 watchdog 入口
```

## 2. 一次性安装

要求：Ubuntu Linux、NVIDIA GPU/驱动、Git LFS、Miniconda、Android Platform Tools（`adb`）、`tmux`。Isaac Sim 5.x 使用 Python 3.11。

### 2.1 下载 RoboDojo 与资产

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

上述 commit 和补丁与 Piper 当前运行环境一致；不要直接追随上游最新版本后仍宣称兼容。`scripts/init_assets.sh` 会把机器人、物体和 layout 资产下载到 RoboDojo 的 `Assets/`，资产不在本压缩包中。

如果使用 NVIDIA 的 Isaac Sim 5.1 二进制压缩包，可将其解压到 `external/isaac-sim/`，并按 Isaac Lab 官方二进制安装说明把 `external/RoboDojo/third_party/IsaacLab/_isaac_sim` 指向该目录。若 `scripts/install.sh` 已成功安装并通过 RoboDojo 自检，则不需要重复安装二进制版。

官方参考：

- RoboDojo：<https://github.com/RoboDojo-Benchmark/RoboDojo>
- Isaac Sim 5.1 工作站安装：<https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_workstation.html>
- Isaac Lab 二进制安装：<https://isaac-sim.github.io/IsaacLab/main/source/setup/installation/binaries_installation.html>

### 2.2 配置采集器

```bash
cd robodojo-vr-teleop-collector
cp config.example.env config.env
```

通常保持相对路径即可。若 RoboDojo、Isaac Lab、数据目录或 `adb` 位于其他位置，只修改 `config.env`。启动脚本不包含用户名、IP 或固定安装路径。

激活 RoboDojo 环境后安装采集器的小型依赖：

```bash
conda activate RoboDojo
python -m pip install -r requirements.txt
chmod +x launch.sh run_4090.sh start_desktop.sh pico_wireless.sh
```

## 3. 每次采集

1. 用 USB 连接并解锁 VR 头显，在头显内允许 USB 调试。
2. 运行 `adb devices -l`，确认目标设备状态是 `device`。启动时只连接一台 USB VR 设备。
3. 启动：

```bash
cd robodojo-vr-teleop-collector
./start_desktop.sh
```

脚本会重启本包自己的 `tmux robodojo` 服务、建立 `adb reverse tcp:8443 tcp:8443`，在头显打开控制页，并在电脑打开只读监看页 `/spectator`。地址与 token 由本机运行时生成，不写入压缩包。

页面显示 `ready` 后，在头显进入 VR；先松开双手侧握键，再按住侧握键接管左右机械臂。扳机控制夹爪。录制前先重置到标准初态：开始录制 → 完成任务 → 保存；失败片段不要当作成功示范。

常用按键：

| 输入 | 功能 |
|---|---|
| 左右侧握键 | 按住控制对应机械臂，松开保持 |
| 左右扳机 | 控制对应夹爪 |
| 左手 X | 开始录制 |
| 左手 Y | 保存 |
| 右手 A | 暂停/重新对齐 |
| 右手 B | 重置；菜单中返回 |
| 任一摇杆按下 | 打开/关闭任务菜单 |

Meta/Pico 浏览器的实际按钮索引以现场测试为准。切换设备后先用非录制状态检查左右手、夹爪、暂停和重置，再开始正式采集。

## 4. 首轮采集顺序

每个任务目标 100 条合格轨迹，原计划按 OpenWAM 成功率较高的两档推进：

1. `put_bottles_into_dustbin`, `stack_bowls`, `fold_clothes`, `play_tic_tac_toe`, `pour_liquid_into_cup`, `build_tower`, `match_and_pick_from_conveyor`, `make_kong`
2. `store_laptop_and_headphones`, `fold_clothes_random`, `pour_balls_into_vase`, `cover_blocks`, `pour_liquid_into_cup_random`, `stack_blocks`, `organize_table`, `hang_mugs`

`*_random` 是随机布局任务，不是错误恢复任务。首轮共 16 个任务、目标 1600 条；错误恢复与低成功率任务另行安排。

当前运行边界：2026-09-24 已在 Piper/Isaac Sim 5.1 上修复 particle-cloth view 的初始化时序、GPU 布料顶点缺少刚体姿态时的奖励计算兼容问题，以及材质 USD 的根 prim 本身为 `Material` 时未绑定纹理的问题。`fold_clothes` 已实测启动、持续运行，并在同一进程切换到另一个官方布局后恢复 `ready`；刚体任务 `stack_blocks` 也已通过同样的布局切换检查。`fold_clothes_random` 尚未单独实测；fluid 在 CUDA 路径仍会被上游禁用，不得列为可采任务。

布局操作分为两种：

- “快速重置当前场景”复用当前 layout 和 seed。
- 开启“官方布局轮换”后，使用“更换下一份官方布局”才会重建到下一 layout；录制中两种操作都会被拒绝，需先保存或丢弃。

## 5. 数据验收

原始输出是逐 episode 的 HDF5，包含三路相机、14D 双臂状态/动作、控制命令、真实墙钟/仿真时间戳、任务和 layout 元数据。它是训练转换前的原始格式，不要直接声称为官方 LeRobot 发布目录。

每条采完后至少检查：

```bash
conda activate RoboDojo
./launch.sh --inspect data/episode_xxx.hdf5
```

正式数据要求：三路相机均可解码；状态和动作逐帧对齐；保留真实时间戳；无大于 200 ms 的有效样本间隔；writer 无 backpressure；WebXR 序号无异常跳变。调试、键盘或合成 smoke 数据只能放在 `validation/`，不得混入 `data/`。

## 6. 常见问题

- 头显网页打不开：重新允许 USB 调试，执行 `adb reverse tcp:8443 tcp:8443`，再运行 `start_desktop.sh`。
- 电脑只想监看：打开终端打印的同一 token 地址，将路径改为 `/spectator#token=...`；监看页不发送机械臂控制。
- 页面提示断开重连：先查 `robodojo_current.log`、USB 连接和 `/status`，不要只刷新页面掩盖服务阻塞。
- 切换任务较慢：任务切换会重建 Isaac 场景；页面应自动重连。录制中不允许切换或重置。
- 查看后台：`tmux attach -t robodojo`，按 `Ctrl-b d` 退出查看但不停止服务。
- 停止服务：在 `tmux` 中按 `Ctrl-C`，或只终止本包占用的 8443 端口进程；不要使用全局 `pkill` 杀其他 Isaac 作业。

运行时生成的 `web_token.txt`、日志、PID、场景状态和采集数据都不应回传或再次打进公开压缩包。

## 7. README 更新规则

本项目要求每次代码、配置、脚本或文档更新时同步修改本节，按时间倒序说明：

1. 更新日期和版本或提交；
2. 具体改动；
3. 实际执行的验证；
4. 仍未验证或已知限制。

不要只写“优化”“修复问题”等无法复核的描述，也不要把语法检查、单元测试、仿真 smoke 和头显真人数采混为同一种验证。

### 更新记录

#### 2026-09-24 · 双语 README

- 将中文文档保存为 `README.zh-CN.md`，新增英文默认文档 `README.md`。
- 两份文档顶部增加语言切换链接，并保持安装、采集、验收、故障排查和更新记录结构一致。
- 文档验证：相对链接、章节、代码块和关键命令已逐项核对。
- 未验证：本次仅修改文档，没有重新运行单元测试、Isaac Sim 或头显端到端采集。

#### 2026-09-24 · GitHub 首次整理

- 推荐稳定仓库名 `robodojo-vr-teleop-collector`，日期移到更新记录和后续 release/tag，不再放进长期仓库名。
- 补充项目定位、当前验证边界和 README 强制更新规则。
- 将安装与启动示例中的目录名统一为推荐仓库名。
- 扩充 `.gitignore`，避免误提交数据目录、外部依赖、TLS 材料和运行时文件。
- 将 `VALIDATION.md` 中的设备序列号、公网地址和个人绝对路径替换为角色说明或占位路径，同时保留验证结论。
- 本机验证：Python 文件编译检查和四个 shell 脚本语法检查通过。
- 未验证：本机缺少 `pytest` 和 `node`，因此本次未重新执行单元测试和 JavaScript 语法检查；未重新运行 Isaac Sim 或头显端到端采集。
