"""Isaac Sim 6.1 Script Editor: angle calibration + LiDAR-controlled braking.
Open navbot_lidar_stop_test.usda with the LiDAR launcher settings first.
No ROS or PPO is used. Target wheel velocities are in USD degrees/second.
"""
import asyncio,builtins,json,math
from pathlib import Path
import numpy as np
import omni.usd,omni.timeline,omni.kit.app
from pxr import UsdGeom,UsdPhysics,Gf

async def main():
 ctx=omni.usd.get_context();s=ctx.get_stage();app=omni.kit.app.get_app();t=omni.timeline.get_timeline_interface()
 scene=Path(s.GetRootLayer().identifier)
 if scene.name!='navbot_lidar_stop_test.usda':raise RuntimeError('Open navbot_lidar_stop_test.usda first')
 t.stop();t.commit()
 for _ in range(10):await app.next_update_async()
 em=app.get_extension_manager()
 for ext in ['isaacsim.sensors.experimental.rtx','isaacsim.sensors.rtx.nodes']:em.set_extension_enabled_immediate(ext,True)
 from isaacsim.sensors.experimental.rtx import Lidar,LidarSensor,parse_generic_model_output_data
 from omni.physics.tensors import create_simulation_view
 path='/World/NavBot/Geometry/base_footprint/base_link/base_scan/Lidar'
 s.GetPrimAtPath(path).GetAttribute('xformOp:translate').Set(Gf.Vec3d(0,0,0))
 s.GetPrimAtPath(path).GetAttribute('omni:sensor:Core:minDistBetweenEchosM').Set(.01)
 if hasattr(builtins,'navbot_lidar_sensor'):builtins.navbot_lidar_sensor._invalidate_sensor()
 sensor=LidarSensor(Lidar(path,aux_output_level='FULL',reset_xform_op_properties=False),annotators=['generic-model-output'])
 builtins.navbot_lidar_sensor=sensor
 drives=[UsdPhysics.DriveAPI.Get(s.GetPrimAtPath('/World/NavBot/Physics/'+name),'angular') for name in ['wheel_left_joint','wheel_right_joint']]
 def speed(mps):
  for d in drives:d.GetTargetVelocityAttr().Set(math.degrees(mps/.033))
 async def frames(n):
  for _ in range(n):await app.next_update_async()
 def scan():
  data,_=sensor.get_data('generic-model-output');g=parse_generic_model_output_data(data)
  if not g.numElements or not g.scanComplete:return None
  angles=(np.array(g.x,copy=True)+180)%360-180;ranges=np.array(g.z,copy=True)
  valid=np.isfinite(ranges)&(ranges>=.12)&(ranges<=3.5)
  return int(g.frameId),angles[valid],ranges[valid]
 def distance(row,angle,width=5):
  delta=(row[1]-angle+180)%360-180;values=row[2][abs(delta)<=width]
  return float(values.min()) if len(values) else 3.5
 target='/World/StopTestTarget'
 s.GetPrimAtPath('/World/LidarCalibrationCube').SetActive(False)
 def remove_target():
  s.RemovePrim(target)
 def create_target(local):
  matrix=UsdGeom.Xformable(s.GetPrimAtPath(path)).ComputeLocalToWorldTransform(0)
  position=matrix.Transform(Gf.Vec3d(*local))
  cube=UsdGeom.Cube.Define(s,target);cube.CreateSizeAttr(.2)
  UsdGeom.XformCommonAPI(cube).SetTranslate(position)
  cube.CreateDisplayColorAttr([Gf.Vec3f(1,.2,.05)]);UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
  return list(position)
 async def settle():
  speed(0);t.stop();t.commit();await frames(15)
  remove_target();t.play();t.commit();await frames(90)
 results={'mount_offset_m':0.,'min_echo_separation_m':.01,'speed_mps':.08,'angles':[],'runs':[]}
 try:
  for name,local,angle,expected in [('front',(1,0,0),0,.9),('left',(0,.4,0),90,.3),('right',(0,-.4,0),-90,.3)]:
   await settle();create_target(local);await frames(60)
   row=scan()
   if row is None:raise RuntimeError('No scan for angle calibration')
   measured=distance(row,angle,2)
   results['angles'].append(dict(direction=name,angle_deg=angle,expected_m=expected,measured_m=measured,passed=abs(measured-expected)<.04))
  if not all(r['passed'] for r in results['angles']):raise AssertionError('Angle calibration failed')
  for name,threshold,target_present,duration in [('clear_path',.45,False,2.),('stop_060',.60,True,12.),('stop_045',.45,True,12.)]:
   await settle()
   target_position=create_target((1,0,0)) if target_present else None
   await frames(45)
   sim=create_simulation_view('numpy',stage_id=ctx.get_stage_id())
   body=sim.create_rigid_body_view('/World/NavBot/Geometry/base_footprint/base_link')
   pos=lambda:body.get_transforms().copy()[0,:3].tolist()
   start=pos();begin=t.get_current_time();last_frame=None;last_fresh=begin;stopped=None;samples=[]
   # Wait for a fresh complete scan before authorizing motion.
   speed(0)
   while t.get_current_time()-begin<duration:
    await frames(1);now=t.get_current_time();row=scan()
    if row is not None and row[0]!=last_frame:
     last_frame=row[0];last_fresh=now;front=distance(row,0,10);p=pos()
     samples.append(dict(time_s=now-begin,front_m=front,position=p))
     if not -.04<p[2]<.12:raise AssertionError('Robot left floor')
     if front<=threshold:
      speed(0);stopped={'reason':'obstacle','front_m':front,'time_s':now-begin,'position':p};break
     speed(.08)
    if now-last_fresh>.6:
     speed(0);raise RuntimeError('Scan stale: braking')
   speed(0);await frames(60)
   final=pos();travel=final[1]-start[1]
   last=scan();final_distance=distance(last,0,10) if last else None
   passed=(stopped is None and .10<travel<.22) if not target_present else (stopped is not None and .2<travel<.65 and final_distance is not None and final_distance>threshold-.06 and math.dist(final,stopped['position'])<.03)
   results['runs'].append(dict(name=name,threshold_m=threshold,target_position=target_position,start=start,final=final,travel_m=travel,final_front_m=final_distance,stop=stopped,samples=samples,passed=passed))
   del body,sim
   if not passed:raise AssertionError('Run failed: '+name)
  results['passed']=True
  sensor.attach_writer('draw-point-cloud',size=.012,color=[0,1,.5,1]);await frames(30)
 finally:
  speed(0);t.pause();t.commit()
  folder=scene.parents[2]/'tests/sensors/lidar';folder.mkdir(parents=True,exist_ok=True)
  (folder/'lidar_stop_report.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
 print(json.dumps({k:([{a:b for a,b in x.items() if a!='samples'} for x in v] if k=='runs' else v) for k,v in results.items()},indent=2))

asyncio.ensure_future(main())
