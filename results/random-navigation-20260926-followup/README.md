# Navigation regression: 14 cm, bathmat removed

Same ten seeds, obstacle layouts and goals as the original suite. Only the minimum center clearance and bathmat presence changed. Unknown map cells still default to free space; topology is not fixed by this test.

| Case | Original | Updated | Duration (s) |
|---|---|---|---|
| 01_passage | goal_reached | goal_reached | 67.10 |
| 02_passage | blocked_no_progress | goal_reached | 65.90 |
| 03_passage | goal_reached | goal_reached | 66.10 |
| 04_passage | blocked_no_progress | goal_reached | 66.10 |
| 05_passage | goal_reached | goal_reached | 67.70 |
| 06_passage | blocked_no_progress | goal_reached | 65.90 |
| 07_passage | blocked_no_progress | goal_reached | 66.70 |
| 08_passage | blocked_no_progress | goal_reached | 65.70 |
| 09_blocked | blocked_no_progress | blocked_no_progress | 34.50 |
| 10_blocked | blocked_no_progress | blocked_no_progress | 19.50 |

Passage goal success: 8/8.
Blocked-control checks passed: 2/2.
Blocked checks test a safe stop, not proof that the robot understands a dead end.
No new videos were captured in this regression; individual case 02/07 videos are saved separately.