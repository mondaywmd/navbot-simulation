# NavBot：RTX LiDAR → Rule-only 导航

Isaac Sim Full 6.1.0 / Windows，2026-09-25 实测。这里是本项目实际运行的脚本；需要既有 NavBot、走廊 USD 与传感器场景。下载包不含这些资产，因此不是开箱即用的完整项目。

阅读顺序：lidar-initial.md（初始安装与 0.9 m 验证）、lidar-stop.md（修正安装位置和近距过滤，方向与停车验证）、navigation-suite.md（六轮导航及录像编码）。初始场景有历史配置限制，后续使用 navbot_lidar_stop_test.usda 修正层。

## UI 与启动前提
在本项目中以 launch_lidar_sync.ps1 启动；外部复现需自行配置安装路径。启动时启用 Motion BVH（/renderer/raytracingMotion/enabled=true），viewport tickRate=0，enable_async=false、asyncRendering=false、asyncRenderingLowLatency=false；启用 isaacsim.sensors.experimental.rtx 与 isaacsim.sensors.rtx.nodes。Python Server 只是远程执行通道，用 Script Editor 不要求启用它。

File → Open 对应场景，Window → Script Editor 载入完整脚本，Run。等一份脚本完成再运行下一份，勿重复点击。脚本末尾已包含 asyncio 入口。测试会切换场景并更新输出；请先保存自己的编辑。导航脚本会覆盖同名测试场景、报告和帧。编码脚本在普通 Python 中使用 FFmpeg，需另外运行；没有把 5 Hz 采集变成 25 Hz 的真实运动采样。

图表和 JSON 对应已完成的单次固定布局实测。控制器使用 RTX 扫描与仿真真实位姿，不是原 Gazebo 策略直接迁移，也没有接 PPO、ROS2 或 SLAM。
