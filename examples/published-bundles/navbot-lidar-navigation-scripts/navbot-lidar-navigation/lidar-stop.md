# NavBot：雷达方向校准与低速遇障停车

2026-09-25；项目目录：`<PROJECT_ROOT>`。

## 验证结果

雷达安装位置恢复到 URDF 的 `base_scan` 原点，不再额外抬高 4 cm。测试的是仿真模型坐标对齐，不代表真实硬件标定。

| 测试 | 预期 | 实测 |
|---|---:|---:|
| 前方目标，0° | 0.900 m | 约 0.900 m |
| 左侧目标，+90° | 0.300 m | 约 0.300 m |
| 右侧目标，−90° | 0.300 m | 约 0.300 m |
| 无校准方块，前进 2 s | 正常前进 | 约 0.147 m |
| 停车阈值 0.60 m | 接近目标后停车 | 最终前方距离约 0.596 m |
| 停车阈值 0.45 m | 比上一轮更靠近目标 | 最终前方距离约 0.434 m |

速度指令为 0.08 m/s。两个停车阈值分别产生约 0.304 m、0.466 m 的行程，确认停车由扫描距离触发。制动指令后继续移动不到 1 mm；5 Hz 扫描的离散采样会让触发距离略低于设置值。距离均从雷达原点量到目标表面，不是机器人外壳的净空。

## 修正的近距离问题

初始配置在约 0.4 m 以下丢失回波。只设置 `nearRangeM=0.12` 不足以改变这一行为：默认 `minDistBetweenEchosM=0.4` 仍限制近距离返回。本次设为 0.01 m，并重新加载场景使传感器重新初始化，随后 0.3 m 左右目标验证通过。单纯运行时修改属性，在本次实例中没有立即生效。

NVIDIA 的[参数说明](https://docs.isaacsim.omniverse.nvidia.com/4.1.0/features/sensors_simulation/isaac_sim_sensors_rtx_based_lidar/lidar_config.html)也指出，回波间距阈值应低于最小量程。这里的修复结果以实际安装的 6.1.0 实测为准。

## 在 UI 重跑

1. 使用 `isaacsim/mcp/launch_lidar_sync.ps1` 启动 Isaac Sim，等加载完成。
2. File → Open，打开 `isaacsim/scenes/navbot_lidar_stop_test.usda`。
3. Window → Script Editor，载入或粘贴 `isaacsim/scripts/navbot_lidar_stop.py`，点击 Run。
4. 等待方向检查和三轮运动测试完成。机器人会数次回到起点，这是测试重置。
5. 输出报告中 `passed: true` 表示通过。结束后轮速指令归零、时间轴暂停，并显示绿色点云。

脚本自动创建静态校准方块，无需手动摆放。它不自动保存运行中的机器人姿态或 RenderProduct。

## 控制方式

读取真实 RTX LiDAR 的完整扫描；取前方 ±10° 的最短有效距离。收到新扫描且距离大于阈值时，给两侧轮子相同速度；达到阈值则将轮速设为零。没有新扫描超过 0.6 s 时也会归零并报错。最后一项是代码保护逻辑，本次未单独做断流故障注入验证。

轮半径 0.033 m，轮角速度为 `v / 0.033` rad/s，转换成 USD Drive 的 deg/s 后写入左右 wheel joint。

原始结果：`tests/sensors/lidar/lidar_stop_report.json`。图表：同目录 `navbot_lidar_stop.png`。

## 边界与下一步

这是静态目标、低速、固定前向扇区的仿真停车验证，不是通用避障或安全认证。没有运行 PPO、ROS2、路径规划，也没有绕行。前方扇区之外的障碍、窄小目标、无返回值原因分类和动态障碍仍需扩展测试。

下一步可加入左右空闲空间判断，先做 Rule-only 转弯绕障，再统一 Gazebo 的角度采样与时间观测格式，最后接原有策略。
