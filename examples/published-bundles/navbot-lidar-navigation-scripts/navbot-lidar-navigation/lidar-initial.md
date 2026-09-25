# NavBot RTX LiDAR：静止扫描与已知距离验证

日期：2026-09-25。Isaac Sim Full 6.1.0 / Windows / RTX 4070。

## 已完成

- 在独立场景 `isaacsim/scenes/navbot_lidar_test.usda` 中添加真实 RTX LiDAR。
- 单水平扫描面、5 Hz、360 个名义发射角、距离 0.12–3.5 m；本轮不添加测距噪声。
- 机器人保持静止。先记录走廊，再在雷达前方 1 m 放置边长 0.2 m 的静态校准方块。
- 预期前表面距离 0.90 m，实测约 0.899998 m；独立的最终重跑脚本也通过。
- 原始命中点、360 距离槽和 36 个扇区最小距离已输出到 JSON。

## 文件

- `isaacsim/scenes/navbot_lidar_test.usda`：引用原走廊测试场景，不替换昨天的场景。
- `usd/sensors/navbot_planar_lidar.usda`：本地传感器配置；基于 NVIDIA Example_Rotary 配置调整并展开，不再依赖在线传感器引用。
- `isaacsim/scripts/navbot_lidar_test.py`：重复执行测试并显示绿色点云。
- `tests/sensors/lidar/2026-09-25_stationary_scan.json`：第一次已知距离测试。
- `tests/sensors/lidar/latest_stationary_scan.json`：最近一次重跑结果，会覆盖。
- 同目录 PNG：视口截图与俯视数据图。

## 如何在 UI 重跑

1. 关闭已有 Isaac Sim 后，运行 `isaacsim/mcp/launch_lidar_sync.ps1`（可右键使用 PowerShell 运行）。
2. 等待走廊和机器人加载完毕。第一次启用 Motion BVH 可能需要几分钟编译 shader。
3. 打开 Window → Script Editor，将 `isaacsim/scripts/navbot_lidar_test.py` 的完整内容载入或粘贴进去，点击 Run。
4. 脚本会停止机器人、移除旧校准方块、采集基线，再创建校准方块并测量；最后暂停并显示绿色点云。
5. 输出 `LiDAR test: pass | expected 0.900 m | measured ...` 即距离检查通过。重新点击 Play 可继续看点云更新。

校准方块是静态、悬空的测量靶，刻意放在扫描高度；不是重力落体实验。脚本不自动保存 USD，运行时的 RenderProduct/OmniGraph 每次重建。

## 渲染配置与诊断范围

启动器保留昨天的同步渲染设置，并在启动时启用 Motion BVH，统一 viewport tickRate 为 0。初始运行曾出现 Hydra engine 配置不匹配和空输出；重启后默认雷达成功输出。自定义单线配置修正后也成功。本轮没有通过单变量实验确定每一项设置的因果关系，不能据此断言旧 Play 崩溃的根因。

## 尚未完成：策略迁移

- 传感器位于 `base_scan` 局部 Z +0.04 m，需在接策略前校准真实安装位置。
- RTX 读取可见几何，不能把它等同于 PhysX collision raycast；视觉与碰撞模型可能存在差异。
- 返回的是有效命中点，点数不一定为 360。脚本把角度归入 `[-180,179]` 的一度距离槽，缺失返回填 3.5 m，再每 10 槽取最小值得到 36 扇区。
- 旧 Gazebo 配置是包含两端点的 `[-pi,+pi]`、360 样本；精确角度重采样和左右方向验证仍待完成。当前 JSON 不是可直接替换训练观测的承诺。
- 旧 clean_start_temporal_lidar_v1 的 78 维观测包含 36 距离、36 有符号距离变化率、2 上次动作及 4 目标量。本轮只验证静态距离；没有接 PPO，也未验证移动扫描或动态避障。

下一步：校准安装位置和左右方向、统一角度网格，再做低速前进时的连续扫描及前方障碍停车测试。

## 后续校准修正
2026-09-25 的方向与停车测试发现并修正了近距离回波过滤问题。原静态测试只验证了 0.9 m，不能据此证明整个标称量程都有效。请使用 navbot_lidar_stop_test.usda 的修正配置；安装位置已恢复 base_scan 原点，详见 STOP_TEST.md。
