# NavBot 固定导航测试集

项目根目录：`<PROJECT_ROOT>`

本轮在修复机器人 visual mesh 显示后执行，使用真实 RTX LiDAR、差速轮驱动和 PhysX 接触监测。目标方向由仿真器真实位姿计算，未使用 PPO、ROS2 或 SLAM。

## 六个固定场景

| 名称 | 内容 | 预期 |
|---|---|---|
| clear | 无额外障碍 | 到达目标 |
| center | 居中方块 | 绕行到达 |
| left | 偏左方块 | 绕行到达 |
| right | 偏右方块 | 绕行到达 |
| staggered | 两个左右错开的方块 | 连续绕行到达 |
| blocked | 横向挡住通道 | 停车，不能碰撞或硬挤 |

场景文件为 `isaacsim/scenes/navbot_suite_<名称>.usda`。它们分别引用已经校准的 LiDAR 场景，保留原始走廊与机器人资产。

## 通过标准

通行场景：最终进入目标 0.12 m 范围，记录到的非地板接触力分量不超过 0.1 N，发出停止指令后位移小于 0.03 m。

堵路场景：触发无可用通路或连续 5 s 没有明显目标进展的停车条件，在横向障碍前停止，并满足相同的接触力和制动位移要求。测试超时不算通过。

控制逻辑对所有场景一致；障碍位置只用于建立场景和输出报告，不作为控制器输入。候选通路来自当前扫描点，机器人用 0.17 m 半径圆形包络估算通行空间。线速度上限 0.08 m/s，角速度上限 0.6 rad/s。

## 在 UI 重跑

1. 使用 `isaacsim/mcp/launch_lidar_sync.ps1` 启动，并等待场景加载。
2. 打开上述任意测试场景。
3. Window → Script Editor，载入 `isaacsim/scripts/navbot_navigation_suite.py`，点击 Run。
4. 脚本会依次创建并运行六个固定场景，输出每轮报告，最后暂停。

只想跑一轮，可把脚本最下方的 `asyncio.ensure_future(main())` 改成 `asyncio.ensure_future(run_case('center'))`。将 `record=False` 传给 `run_case` 可不采集视频帧。

重跑会覆盖同名报告、场景和同名视频帧；旧视频不会自动重新编码。结果目录是 `tests/navigation/fixed_suite/<名称>/`。

## 结果和视频

每轮包括 `report.json`、`final.png`、原始 `frames/` 和编码后的 MP4。总表是 `summary.json`，对比轨迹是 `trajectories.png`，合集是 `navbot_fixed_suite.mp4`。

画面由 Kit 的 `capture_viewport_to_file` 在实际控制循环中采集，大约每 0.2 s 一帧。报告保存每帧仿真时间。编码脚本按时间间隔生成视频，再转换成 25 fps 容器；重复帧不代表原始采样达到 25 fps，也没有生成中间运动帧。每段末尾保留约 1 s 的最终画面。

编码脚本：`isaacsim/scripts/encode_navigation_suite.py`。它在普通 Python 环境中运行，需要可用的 FFmpeg；用法和参数见脚本顶部。UI 测试脚本本身不调用编码器。

## 接触监测范围与限制

监测机器人的六个刚体对测试障碍和走廊中带 CollisionAPI 的非 Floor 物体的接触力；完整名单保存在报告。地板接触是正常运动所需，因此排除。记录是控制循环读取的采样结果，不是连续接触事件的形式化证明。

本轮每种场景执行一次，证明这些固定布局可以通过；没有证明随机场景、动态障碍、透明物体、窄小目标、传感器断流或定位误差下都可靠。仍需扩展重复测试，再接真实扫描资产和原有 PPO 策略。
