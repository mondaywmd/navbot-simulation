# NavBot: depth-assisted navigation and pushing tests

Isaac Sim 6.1; requires the existing local NavBot project, corridor, RTX LiDAR, and simforge_assets library. Models are not included. Save your work before running: scripts open separate test stages, run physics, and overwrite their named result folders. Run ONE script at a time in Script Editor; Play alone does not invoke the controller.

navbot_depth_validation.py: static empty/shoe/book/dumbbell check, with a downward-facing rendered depth camera and RANSAC ground plane removal. The target ROI uses the known test placement for evaluation only. Ideal noiseless depth, one distance, no real-sensor guarantee for a 2 cm book.

navbot_depth_navigation.py: fixed random seed 20260925, scattered STATIC assets. Horizontal LiDAR + depth above the fitted ground by 1.2 cm. Accumulates sensed obstacle points in a 2.5 cm grid; A-star with 17.5 cm footprint inflation. Goal/localization use simulator ground truth, but obstacle coordinates are not passed to the planner. Unknown map cells are initially free. This is a static-scene prototype, not SLAM or a dynamic-obstacle planner. Depth frame age is not independently timestamp-verified; the guard checks usable processed depth. One passing layout does not establish general reliability.

navbot_push_comparison.py: separate isolated dynamic asset tests, one shoe 0.188 kg, book approx 1 kg, dumbbell 2 kg, chair 5 kg lower-bound assumption. Object friction 0.5/0.4 and wheel effort cap 0.15 Nm are assumptions. No deformable foam. This is deliberate contact, not avoidance. It cannot prove all real heavy objects are immovable.

Recordings: viewport PNGs sampled about 5 Hz. Encode using report video_frames simulation_time_s deltas (not by playing sampled frames directly at 25 fps); delivered MP4 uses a 25 fps container and a final hold.
