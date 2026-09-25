"""Execute in Isaac Sim Python Server. Differential-drive smoke test, no ROS/RL."""
import json
import math
from pathlib import Path
import omni.usd
import omni.kit.app
import omni.timeline
from pxr import UsdPhysics
from omni.physics.tensors import create_simulation_view

root=Path('C:/Users/User/Documents/navbot/_isaacsim')
ctx=omni.usd.get_context()
timeline=omni.timeline.get_timeline_interface()
if not timeline.is_stopped():
    timeline.stop(); timeline.commit()
    for _ in range(10): await omni.kit.app.get_app().next_update_async()
stage=ctx.get_stage()
if not stage or not stage.GetPrimAtPath('/World/NavBot/Physics/wheel_left_joint'):
    raise RuntimeError('Open the NavBot robot test scene first.')
destination=root/'isaacsim/scenes/navbot_drive_test.usda'
if stage.GetRootLayer().identifier.replace('\\','/') != str(destination).replace('\\','/'):
    if destination.exists():
        raise RuntimeError('Drive scene exists. Open it first to repeat; no overwrite performed.')
    # Same directory retains the relative robot reference. Original scene stays untouched.
    stage.GetRootLayer().Export(str(destination))
    ok,error=await ctx.open_stage_async(str(destination))
    assert ok,error
    for _ in range(30): await omni.kit.app.get_app().next_update_async()
    stage=ctx.get_stage()
from omni.kit.viewport.utility import get_active_viewport
get_active_viewport().set_active_camera('/World/Camera')
drives=[UsdPhysics.DriveAPI.Get(stage.GetPrimAtPath('/World/NavBot/Physics/'+name),'angular')
        for name in ('wheel_left_joint','wheel_right_joint')]
for drive in drives:
    assert drive
    drive.CreateTargetVelocityAttr(0.0)
    drive.CreateStiffnessAttr(0.0)
# Keep the importer's damping and original force limits.
stage.GetRootLayer().Save()

async def frames(count):
    for _ in range(count): await omni.kit.app.get_app().next_update_async()

def targets(left,right):
    for drive,value in zip(drives,(left,right)):
        drive.GetTargetVelocityAttr().Set(math.degrees(value))

def pose(view):
    values=view.get_transforms().copy()[0].tolist()
    assert all(math.isfinite(x) for x in values)
    x,y,z,w=values[3:7]
    yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))
    return {'position':values[:3],'quaternion_xyzw':values[3:7],'yaw_rad':yaw}

results=[]
try:
    for name,left,right in [('forward',3.0,3.0),('turn_left',-2.0,2.0)]:
        targets(0,0)
        timeline.play(); timeline.commit()
        await frames(60)
        sim=create_simulation_view('numpy',stage_id=ctx.get_stage_id())
        body=sim.create_rigid_body_view('/World/NavBot/Geometry/base_footprint/base_link')
        before=pose(body)
        start=timeline.get_current_time()
        targets(left,right)
        await frames(180)
        after=pose(body)
        elapsed=timeline.get_current_time()-start
        targets(0,0)
        await frames(60)
        stopped=pose(body)
        distance=math.hypot(after['position'][0]-before['position'][0],after['position'][1]-before['position'][1])
        angle=math.atan2(math.sin(after['yaw_rad']-before['yaw_rad']),math.cos(after['yaw_rad']-before['yaw_rad']))
        result={'test':name,'wheel_targets_rad_s':[left,right],'duration_s':elapsed,
                'before':before,'after':after,'after_braking':stopped,'distance_m':distance,'yaw_change_deg':math.degrees(angle)}
        result['passed']=(distance>0.15 and abs(math.degrees(angle))<15) if name=='forward' else (angle>0.5 and distance<0.1)
        results.append(result)
        del body,sim
        timeline.stop(); timeline.commit()
        await frames(60)
finally:
    targets(0,0)
    timeline.stop(); timeline.commit()
    await frames(10)
    stage.GetRootLayer().Save()
report=root/'tests/physics/robot_import/drive_test_report.json'
report.write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
assert all(item['passed'] for item in results), 'Drive test failed; inspect recorded results.'

