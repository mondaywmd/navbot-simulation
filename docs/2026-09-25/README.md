# 2026-09-25 实验记录

四篇网站日志的完整内容同步到本目录，图片在仓库内展示；视频链接指向网站的公开 MP4。

| 实验 | 图文记录 | 视频数 | 配套材料 |
| --- | --- | --- | --- |
| 先看见障碍， 再决定往哪里走。 | [阅读全文](01-lidar-navigation.md) | 1 | [打开](../../examples/published-bundles/navbot-lidar-navigation-scripts), [打开](../../results/navbot_fixed_suite_results.json), [打开](../../results/lidar_stop_report.json) |
| 把家里的物品， 变成能碰撞的数字资产。 | [阅读全文](02-scanned-assets-physics.md) | 1 | [打开](../../examples/published-bundles/ball-shower-scripts) |
| 让真实的椅子， 进入机器人走廊测试。 | [阅读全文](03-chair-navigation.md) | 1 | [打开](../../results/report.json), [打开](../../examples/published-bundles/chair-test-script) |
| 看见地上的鞋， 再决定怎样通过。 | [阅读全文](04-depth-obstacles.md) | 2 | [打开](../../examples/published-bundles/scripts), [打开](../../results/navigation-report.json), [打开](../../results/detection-report.json), [打开](../../results/push-report.json) |

## 本次补齐

- LiDAR 安装、近距离与方向校准、停车报告、六个固定布局结果及轨迹图。
- 四组扫描资产的 Blender 清理／重建、资产库结构、鞋口碰撞修正和 200 球录像。
- 椅子通行、相机机位、灯光与机器人材质调整。
- 深度相机、地面过滤、规划失败与改进、分散避障和独立推撞。
- 网站已发布下载包中的脚本及 README，保存在 examples/published-bundles；其中补齐了独立录像编码脚本。

## 范围

这是已有实验的文档与媒体同步，没有重新运行仿真。通过结论仍限于各日志注明的测试条件。历史文章中的“下一步”保留当时语境；后续进展见下一篇。原始扫描、USD/Blender 模型与大体积视频不重复入库。

[机器可读对照清单](coverage.json)记录每篇来源、图片、视频和配套材料。
