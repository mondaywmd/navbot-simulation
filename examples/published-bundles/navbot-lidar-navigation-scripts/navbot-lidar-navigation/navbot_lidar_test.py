"""Run in Isaac Sim Script Editor with navbot_lidar_test.usda open.
Reads real RTX returns, validates a target 1 m ahead, and leaves green points visible.
Requires the LiDAR launcher settings documented in tests/sensors/lidar/README.md.
"""
import asyncio
import builtins
import json
from pathlib import Path
import numpy as np
import carb
import omni.kit.app
import omni.timeline
import omni.usd
from pxr import Gf, UsdGeom, UsdPhysics

SENSOR = '/World/NavBot/Geometry/base_footprint/base_link/base_scan/Lidar'
TARGET = '/World/LidarCalibrationCube'

async def main():
    app = omni.kit.app.get_app()
    stage = omni.usd.get_context().get_stage()
    scene = Path(stage.GetRootLayer().identifier)
    if scene.name != 'navbot_lidar_test.usda':
        raise RuntimeError('Open isaacsim/scenes/navbot_lidar_test.usda first.')
    if not carb.settings.get_settings().get('/renderer/raytracingMotion/enabled'):
        raise RuntimeError('Restart with the LiDAR launcher: Motion BVH must be enabled at startup.')
    timeline = omni.timeline.get_timeline_interface()
    timeline.stop(); timeline.commit()
    for _ in range(10):
        await app.next_update_async()
    for name in ['wheel_left_joint', 'wheel_right_joint']:
        UsdPhysics.DriveAPI.Get(stage.GetPrimAtPath('/World/NavBot/Physics/' + name), 'angular').GetTargetVelocityAttr().Set(0)
    stage.RemovePrim(TARGET)
    manager = app.get_extension_manager()
    manager.set_extension_enabled_immediate('isaacsim.sensors.experimental.rtx', True)
    manager.set_extension_enabled_immediate('isaacsim.sensors.rtx.nodes', True)
    from isaacsim.sensors.experimental.rtx import Lidar, LidarSensor, parse_generic_model_output_data
    if hasattr(builtins, 'navbot_lidar_sensor'):
        # Release this script's runtime before creating another render product.
        builtins.navbot_lidar_sensor._invalidate_sensor()
    sensor = LidarSensor(Lidar(SENSOR, aux_output_level='FULL', reset_xform_op_properties=False),
                         annotators=['generic-model-output'])
    builtins.navbot_lidar_sensor = sensor

    async def collect():
        rows, last = [], None
        for k in range(300):
            await app.next_update_async()
            data, _ = sensor.get_data('generic-model-output')
            g = parse_generic_model_output_data(data)
            if k < 40 or not g.numElements or not g.scanComplete or g.frameId == last:
                continue
            last = g.frameId
            az, el, ranges = (np.array(v, copy=True) for v in (g.x, g.y, g.z))
            if 'SPHERICAL' not in str(g.elementsCoordsType):
                raise RuntimeError('Expected azimuth/elevation in degrees and range in meters.')
            # Bins are [-180, 179] degrees. Absent/invalid returns use maximum range.
            bins = np.full(360, 3.5)
            indices = (np.rint(az).astype(int) + 180) % 360
            valid = np.isfinite(ranges) & (ranges >= .12) & (ranges <= 3.5)
            np.minimum.at(bins, indices[valid], ranges[valid])
            rows.append(dict(frame_id=int(g.frameId), simulation_time=timeline.get_current_time(),
                             azimuth_deg=az.tolist(), elevation_deg=el.tolist(), range_m=ranges.tolist(),
                             ranges360=bins.tolist(), sectors36=bins.reshape(36, 10).min(axis=1).tolist()))
            if len(rows) == 3:
                return rows
        raise RuntimeError('Timed out waiting for three distinct full scans.')

    try:
        timeline.play(); timeline.commit()
        baseline = await collect()
        timeline.pause(); timeline.commit()
        matrix = UsdGeom.Xformable(stage.GetPrimAtPath(SENSOR)).ComputeLocalToWorldTransform(0)
        position = matrix.Transform(Gf.Vec3d(1, 0, 0))
        cube = UsdGeom.Cube.Define(stage, TARGET)
        cube.CreateSizeAttr(.2)
        UsdGeom.XformCommonAPI(cube).SetTranslate(position)
        cube.CreateDisplayColorAttr([Gf.Vec3f(1, .2, .05)])
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
        timeline.play(); timeline.commit()
        obstacle = await collect()
        front = lambda row: min(row['ranges360'][178:183])
        measured = front(obstacle[-1])
        report = dict(status='pass' if abs(measured - .9) < .06 else 'fail',
                      expected_front_surface_m=.9, baseline_front_m=front(baseline[-1]),
                      obstacle_front_m=measured, cube_center_world=list(position),
                      baseline=baseline, obstacle=obstacle,
                      note='RTX visual geometry; sensor raised 4 cm from base_scan. '
                           '360 one-degree bins are not yet the exact Gazebo inclusive-angle grid.')
        folder = scene.parents[2] / 'tests/sensors/lidar'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'latest_stationary_scan.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        sensor.attach_writer('draw-point-cloud', size=.012, color=[0., 1., .5, 1.])
        for _ in range(30):
            await app.next_update_async()
        print('LiDAR test:', report['status'], '| expected 0.900 m | measured', round(measured, 6), 'm')
        if report['status'] != 'pass':
            raise AssertionError('Calibration distance outside tolerance.')
    finally:
        timeline.pause(); timeline.commit()
    # Runtime graphs are deliberately not saved. Rerun this script after reopening.

asyncio.ensure_future(main())
