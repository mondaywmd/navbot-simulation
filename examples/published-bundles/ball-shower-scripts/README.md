需要 Isaac Sim、既有 asset_acceptance.usda 和本地资产库；不包含扫描模型和纹理。修改 YOUR_PROJECT_ROOT，保存当前场景，在 Script Editor 运行。脚本切换场景并覆盖同名测试输出。输出 PNG 帧序列；可用 FFmpeg -framerate 30 -i ball_shower_200.%04d.png -c:v libx264 -pix_fmt yuv420p result.mp4 编码。

# 200 球随机落下实验

12 秒、1280×720、30 fps，固定机位，360 张原始帧。保留此前 24 球和 100 球版本。

200 个球以固定随机种子分配不同位置、高度、三轴速度和旋转速度。188 球半径 2.6 cm，12 个瞄准鞋口的小球半径 1.6 cm。球弹性 0.68，初始位置不重叠。

本测试场景禁用鞋子的 6 个 Convex Hull，并在静态鞋子网格上添加 Triangle Mesh collision，保留真实凹陷。原资产文件不修改；此设置不用于动态刚体鞋子。

独立 Play 位置采样确认有 10 个球进入鞋内检查区域。随后重置录制视频，录像与数值验证为两次独立运行。

场景 isaacsim/scenes/asset_ball_shower_200.usda；脚本 isaacsim/scripts/record_ball_shower_200.py。
