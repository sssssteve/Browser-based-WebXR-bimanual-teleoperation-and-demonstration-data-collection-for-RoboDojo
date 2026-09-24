# 验证记录 · 2026-09-17

## GPU 布料初始化与布局切换 · 2026-09-24

- Piper/Isaac Sim 5.1 上复现并修复 `fold_clothes` 的 particle-cloth view 初始化失败：场景创建布料 prim 后先同步一次 PhysX，再初始化 cloth tensor view。
- 修复 GPU 布料顶点已经是世界坐标、但奖励函数仍收到空姿态的问题；用单位姿态保持接口契约，避免二次坐标变换。
- 修复 garment 材质 USD 的默认 prim 本身就是 `Material` 时绑定逻辑错误地要求子节点的问题；Piper 重启后不再出现 `Material prim ... has no children`，动态观察期间也未再出现法线回退警告。
- 实测 `fold_clothes` 启动并持续运行；同一进程随机切换到 seed 43 后操作返回 `complete/ready`，随后仍持续执行 physics/render/capture。
- 这不等于所有粒子任务通过：`fold_clothes_random` 未单独运行，fluid 在当前 CUDA 上游路径仍被禁用。

## 遥操停顿与生命周期 watchdog · 2026-09-21

- Piper 工作站的 CPU/协议测试为 `25 passed`。新增输入间歇、超时、积压序号、重连、环境代次隔离、生命周期串行化、writer 背压、latest-only 预览、外部 watchdog 卡死终止/有限重启及初始化宽限测试；Python、JavaScript、shell 语法检查通过。
- `AsyncRecorder` 队列满不再无限 `put()`；会报 `RecorderBackpressure`、停止当前录制并保留 incomplete 文件。终止状态行保持 `action_valid=false`。
- 跨任务和随机 layout 切换不再调用进程内 `close/rebuild`；固定 layout 同任务 reset 仍为软 reset，底层不返回时由进程外阶段超时兜底。
- 诊断状态覆盖输入、控制安全门、IK、physics/render/capture、writer、preview、operation_id、env_epoch 和阶段持续时间。
- 真实仿真验证了 `stack_blocks → align_blocks → stack_blocks`：两次操作均返回 operation_id，supervisor PID 保持不变，Isaac 子进程与 env_epoch 更新，新任务核对 layout 和新三相机帧后到达 ready。随后关闭随机场景，在 `stack_blocks_0` 上执行两次软 reset，PID/env_epoch 保持不变；两个并发 reset 得到一个 HTTP 202 和一个 409，没有重入。最后已恢复随机场景开启，当前任务为 `stack_blocks`。
- input-only 在 18444 端口绑定指定 Quest ADB 设备，状态明确为 `input_only`，未启动第二个 Isaac。tmux HUP 验证中 supervisor 与专属 Isaac 子进程均退出，8443 释放后正常重启，没有遗留孤立进程。设备序列号不进入公开仓库。
- 当前刚体空载运行观察到一次 render/周期、5 个 physics 子步，writer 队列为 0，预览线程无积压。短窗口周期约 p50 62.1 ms、p95 69.5 ms、p99 74.1 ms、max 83.7 ms；这是无人手柄、未录制的短时测量，不能替代 30 分钟验收。
- 真实三相机写盘短测录制 57 帧后丢弃：writer 队列深度 1/16、背压 0、入队耗时低于 0.1 ms；周期 p50 61.9 ms、p95 70.2 ms、p99 75.7 ms、max 83.4 ms。该片段无真人动作且已丢弃，只验证写盘链路，不是可用示范。
- 30 分钟真人遥操、录制/不录制各一轮、20 次连续 reset 及三个任务往返属于工作站人工验收，未完成前不得标记为通过。

## Pico 错误恢复与任务菜单 · 2026-09-19

- 单元测试：4090 的 RoboDojo/Isaac Python 环境中 `12 passed`。
- 状态快照：`stack_blocks` 5 步仿真生成 `recoverable=true`，包含左右臂关节状态和 3 个刚体对象状态；三相机和软重置检查通过。该次墙钟速度为 11.09 Hz，不能证明 30 Hz。
- 协议闭环：实际执行“从当前错误状态录制 → 保存失败轨迹 → 从末状态接手 → 丢弃恢复录制 → 删除测试轨迹”，全部成功；测试轨迹已删除。
- 任务选择：`stack_blocks`、`align_blocks` 和 `arrange_largest_number` 均返回 `ready`；后者还连续运行 22 秒，修复了官方 geometry 对象 pose 的 CPU/CUDA 设备不一致。固定网页 token 保持不变。页面展示 54 个同时具有官方 layout、配置和任务模块的任务，其他任务尚未逐个运行。
- Pico 4 Ultra：ADB 识别指定设备，USB `reverse tcp:8443 tcp:8443` 已恢复。Pico Browser 4.0.38 加载新页面，`client.js` 语法检查通过，`immersive-vr=true`，“进入 VR”可用；页面实际显示任务选择、错误恢复、删除及退出入口。同一可见标签页发起任务切换后自动重连并显示 `stack_blocks · ready`。设备序列号不进入公开仓库。
- VR 菜单：代码与浏览器页面加载已验证，摇杆按下/上下、扳机确认、右 B 返回的这组新交互仍需佩戴头显做一次人工按键确认。
- 进程：正式服务在 4090 的 `tmux` 会话 `robodojo` 中运行，当前任务为 `stack_blocks`；任务 supervisor 已验证能在 Isaac Sim 以退出码 0 完成关闭后继续加载新任务。
- 边界：旧 HDF5 没有对象状态，只能视频回看；衣物/液体的粒子速度还原未验证，因此历史接手被明确禁用。在线错误状态恢复不受此限制。

## 4090 工作站复验 · 2026-09-18

- 工作站：RTX 4090 48 GB，驱动 570.153.02；Isaac Sim 5.1 / Isaac Lab 2.3.2。
- 目录：Piper 工作站的机器本地项目目录；RoboDojo commit 为 `e0703b03bb1af6075400e9d60dc17a792793960c`。
- 资产：从 L20Y 源主机使用增量 `rsync` 同步，15,367 个文件、41,269,510,261 字节；同步后零差异检查通过。公网地址不进入公开仓库。
- 环境：RoboDojo/Pico 单元测试 11 passed；Isaac Lab、cuRobo 与 CUDA 导入通过。
- 仿真：`stack_blocks` 合成输入 25 个控制步，保存 26 帧 HDF5；三相机存在，状态/动作对齐通过，IK 拒绝 0 次，软重置后仍为 3 个渲染产品。
- 性能：25 步测试墙钟速度 10.17 Hz，仿真时间采样配置仍为 25 Hz。当前结果不能证明达到 30 Hz。
- 回放：25 步命令回放最大关节误差 `5.82e-11 rad`；只验证关节命令回放，不证明物体接触状态精确重放。
- 证据：远端 `validation/4090_smoke25_20260918T155042/` 与 `validation/4090_replay_20260918T155357/`。

Pico 4 Ultra 实机 WebXR、按键映射和端到端延迟仍未验证；本次输入明确为 `synthetic_smoke / integration_check`，不是人类示范数据。

## L20Y 原始验证 · 2026-09-17

代码曾部署在 L20Y 源主机的机器本地项目目录。本地交付目录可直接复制到已安装 RoboDojo 的 Linux + NVIDIA 工作站；主机地址和个人绝对路径不进入公开仓库。

## 已验证

| 层次 | 结果 | 证据 |
|---|---|---|
| 控制与存储测试 | 11 passed；坐标变换、旋转、重新接管、跟踪丢失、限幅、输入校验、JPEG/HDF5 对齐 | `validation/pytest.txt` |
| HTTP/WebSocket | 令牌校验、单操作员、序号去重、过期输入、独立视频通道、停更时不重复冒充新帧 | 同上 |
| 真实 RoboDojo 仿真 | `stack_blocks`，25 次控制步，26 帧三相机轨迹，最后一帧为无效动作填充 | `validation/smoke_final/episode_20260917T074242_3abc218a.hdf5` |
| 实际运动 | 左右末端各移动约 0.006 m；夹爪从约 1.0 到 0.900006；IK 拒绝 0 次 | `validation/smoke_final/motion_report.json` |
| 场景重置 | 初始布局通过稳定性检查；重复重置后仍为 3 个相机渲染产品 | `validation/smoke_final/smoke_report.json`；浏览器重复重置 |
| 命令回放 | 25 步；最大关节误差 5.82e-11 rad | `validation/replay/replay_report.json` |
| 真实桌面浏览器 | Chrome + Playwright 连接真实仿真，显示相机、开始录制、丢弃、重置均通过；录制中重置被拒绝；浏览器错误 0 | `validation/browser.json`、`validation/browser_final.png` |
| 本地辅助检查 | Python 编译、JavaScript 语法、shell 语法通过；生成证书通过 `openssl verify` | 本地执行记录 |

回放检查只覆盖同初态下的关节命令，不证明物体接触、粒子或整个仿真状态的精确回放。仿真轨迹明确标记 `synthetic_smoke / integration_check`，任务结果为失败，不是真人 Pico 示范或叠块任务成功。浏览器操作测试生成的片段已丢弃。

`smoke_report.json` 原始汇总里的 `frames=25` 是控制循环步数；HDF5 和 `motion_report.json` 中的样本数为 26。最终代码已将运行时状态放入 `runtime`，避免覆盖样本数。

## 环境与实测性能

- RoboDojo commit：`e0703b03bb1af6075400e9d60dc17a792793960c`。
- Isaac Lab 2.3.2 / Isaac Sim 5.1 / Python 3.11.13 / NVIDIA L20Y。
- 使用现有官方资产和默认公开评测 layout 0，元数据包含完整布局及 hash。该调试轨迹不得作为独立 benchmark 的训练数据。
- 三相机 640×480，仿真时间采样率 25 Hz；本次合成轨迹墙钟实测 **5.55 Hz**，浏览器测试期间约 **4.9 Hz**。GPU 当时还有其他任务，未中断它们。
- 当前验证不能证明目标本地电脑达到实时 25 Hz。需要在该电脑独占显卡时测吞吐和头显端到端延迟。

## 尚未验证

- Pico 4 Ultra 实机进入 WebXR、左右手柄按键映射、追踪丢失行为和端到端延迟。
- Pico 的 USB localhost 访问，以及局域网 HTTPS 的证书信任。
- 其他任务与其他 RoboDojo / Isaac Lab 版本。
- 真人完成任务、持续多小时采集、训练策略效果。
- 显示是固定相机画面的 VR 虚拟屏幕，不是 CloudXR 双目立体场景。

## 服务器复现

这里复用服务器原有 CUDA/runtime 依赖目录；迁移到本地时使用本地已经跑通 RoboDojo 的环境，不需要复制整个 recovery 项目。

```bash
cd /path/to/robodojo-vr-teleop-collector
export CUDA_PATH=/path/to/cuda/runtime
export PYTHONPATH=/path/to/runtime/dependencies
/path/to/isaac-sim/python.sh run.py \
  --robodojo-root /path/to/RoboDojo \
  --task stack_blocks --headless --device cuda:0 --port 18443 \
  --smoke-steps 25 --output validation/new_smoke
```

Isaac 应用退出码可能被 Kit 的关闭流程覆盖，必须检查报告是否实际生成及日志中的异常，不能仅凭进程返回 0 判断通过。

相机同步沿用[官方修复中的渲染等待设置与派发时钟](https://github.com/RoboDojo-Benchmark/RoboDojo/blob/08b7ee46034c3d0c8a389b2b7bfc138f4d55ee4d/env/camera_manager/capture/render_sync.py)。兼容处理位于本适配器内；未改写共享 RoboDojo/Isaac 安装。
