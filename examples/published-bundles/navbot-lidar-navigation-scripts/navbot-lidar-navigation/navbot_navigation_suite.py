"""Isaac Sim Script Editor: six fixed Rule-only navigation tests.
Open a scene under this project's isaacsim/scenes before running.
Videos are encoded separately from 5 Hz viewport frames and frame timestamps.
"""
import asyncio,builtins,json,math
from pathlib import Path
import numpy as np
import omni.usd,omni.timeline,omni.kit.app
from pxr import Usd,UsdGeom,UsdPhysics,PhysxSchema,Gf

CASES={
 'clear':[],
 'center':[(-.28,-2.,.2)],
 'left':[(-.45,-2.,.2)],
 'right':[(-.11,-2.,.2)],
 'staggered':[(-.43,-2.3,.16),(-.13,-1.5,.16)],
 'blocked':[(-.28,-2.15,1.2)],
}

async def run_case(name,record=True):
 ctx=omni.usd.get_context();t=omni.timeline.get_timeline_interface();app=omni.kit.app.get_app()
 root=Path(ctx.get_stage().GetRootLayer().identifier).parents[2]
 assert (root/'isaacsim/scenes/navbot_lidar_stop_test.usda').exists(),'Open a project scene first'
 folder=root/'tests/navigation/fixed_suite'/name;folder.mkdir(parents=True,exist_ok=True)
 async def frames(n):
  for _ in range(n):await app.next_update_async()
 t.stop();t.commit();await frames(15)
 if hasattr(builtins,'navbot_lidar_sensor'):
  builtins.navbot_lidar_sensor._invalidate_sensor();del builtins.navbot_lidar_sensor
 # Each case uses a fresh stage and its own saved layer, without runtime poses.
 st=Usd.Stage.CreateInMemory();st.GetRootLayer().subLayerPaths=['navbot_lidar_stop_test.usda']
 st.OverridePrim('/World');st.GetRootLayer().defaultPrim='World'
 st.SetStartTimeCode(0);st.SetEndTimeCode(1000000);st.SetTimeCodesPerSecond(60)
 UsdGeom.SetStageMetersPerUnit(st,1);UsdGeom.SetStageUpAxis(st,'Z')
 targets=[]
 for i,(x,y,width) in enumerate(CASES[name]):
  path='/World/SuiteObstacle_'+str(i);targets.append(path)
  cube=UsdGeom.Cube.Define(st,path);cube.CreateSizeAttr(1)
  UsdGeom.XformCommonAPI(cube).SetTranslate(Gf.Vec3d(x,y,.15))
  UsdGeom.XformCommonAPI(cube).SetScale(Gf.Vec3f(width,.2,.3))
  cube.CreateDisplayColorAttr([Gf.Vec3f(1,.25,.05)]);UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
 filename=root/'isaacsim/scenes'/('navbot_suite_'+name+'.usda')
 st.GetRootLayer().Export(str(filename));await ctx.open_stage_async(str(filename));await frames(90)
 s=ctx.get_stage();em=app.get_extension_manager()
 for ext in ['isaacsim.sensors.experimental.rtx','isaacsim.sensors.rtx.nodes']:em.set_extension_enabled_immediate(ext,True)
 from isaacsim.sensors.experimental.rtx import Lidar,LidarSensor,parse_generic_model_output_data
 from omni.physics.tensors import create_simulation_view
 from omni.kit.viewport.utility import get_active_viewport,capture_viewport_to_file
 sensor=LidarSensor(Lidar('/World/NavBot/Geometry/base_footprint/base_link/base_scan/Lidar',aux_output_level='FULL',reset_xform_op_properties=False),annotators=['generic-model-output'])
 builtins.navbot_lidar_sensor=sensor
 bodies=[str(p.GetPath()) for p in s.Traverse() if str(p.GetPath()).startswith('/World/NavBot/') and p.HasAPI(UsdPhysics.RigidBodyAPI)]
 for path in bodies:PhysxSchema.PhysxContactReportAPI.Apply(s.GetPrimAtPath(path)).CreateThresholdAttr(0)
 filters=targets+[str(p.GetPath()) for p in s.Traverse() if str(p.GetPath()).startswith('/World/Corridor/Collision/') and p.HasAPI(UsdPhysics.CollisionAPI) and p.GetName()!='Floor']
 assert len(filters)>0
 drives=[UsdPhysics.DriveAPI.Get(s.GetPrimAtPath('/World/NavBot/Physics/'+n),'angular') for n in ['wheel_left_joint','wheel_right_joint']]
 def command(v,w):
  for d,side in zip(drives,[-1,1]):d.GetTargetVelocityAttr().Set(math.degrees((v+side*w*.16/2)/.033))
 command(0,0);t.play();t.commit();await frames(90)
 sim=create_simulation_view('numpy',stage_id=ctx.get_stage_id())
 body=sim.create_rigid_body_view('/World/NavBot/Geometry/base_footprint/base_link')
 contact=sim.create_rigid_contact_view(bodies,[filters for _ in bodies])
 assert contact.sensor_count==len(bodies) and contact.filter_count==len(filters)
 goal=np.array([-.28,-.9]);begin=t.get_current_time();last=None;fresh=begin;previous=0.;history=[];max_force=0.;reason='timeout'
 best=float('inf');progress_time=begin;captures=[];next_capture=begin
 vp=get_active_viewport();vp.set_active_camera('/World/Camera')
 if record:(folder/'frames').mkdir(exist_ok=True)
 try:
  while t.get_current_time()-begin<65:
   await frames(1);now=t.get_current_time()
   forces=contact.get_contact_force_matrix(1/60);max_force=max(max_force,float(np.abs(forces).max()))
   if max_force>.1:reason='contact';break
   data,_=sensor.get_data('generic-model-output');g=parse_generic_model_output_data(data)
   if g.numElements and g.scanComplete and g.frameId!=last:
    last=g.frameId;fresh=now;tr=body.get_transforms().copy()[0];pos=tr[:2].astype(float);qx,qy,qz,qw=tr[3:7]
    yaw=math.atan2(2*(qw*qz+qx*qy),1-2*(qy*qy+qz*qz));dist=float(np.linalg.norm(goal-pos))
    if dist<.12:reason='goal_reached';break
    if dist<best-.025:best=dist;progress_time=now
    if now-progress_time>5:reason='blocked_no_progress';break
    a=np.deg2rad(np.array(g.x,copy=True));r=np.array(g.z,copy=True);valid=np.isfinite(r)&(r>=.12)&(r<=3.5)
    points=np.column_stack((r[valid]*np.cos(a[valid])-.032,r[valid]*np.sin(a[valid])))
    c,ss=math.cos(yaw),math.sin(yaw);local=np.array([[c,ss],[-ss,c]])@(goal-pos);choices=[]
    for angle in np.deg2rad(np.arange(-85,86,5)):
     u=np.array([math.cos(angle),math.sin(angle)]);proj=points@u;perp=np.abs(points[:,0]*u[1]-points[:,1]*u[0]);hits=(proj>0)&(perp<.17)
     free=float(np.min(proj[hits]-np.sqrt(.17**2-perp[hits]**2))) if np.any(hits) else 3.5
     step=min(.5,free-.04)
     if step<.08:continue
     score=dist-float(np.linalg.norm(local-step*u))-.035*abs(angle)-.02*abs(angle-previous);choices.append((score,angle,free))
    if not choices:reason='no_safe_gap';break
    _,angle,free=max(choices);previous=angle
    v=.08*max(0,math.cos(angle)) if abs(angle)<math.radians(55) else 0.;w=float(np.clip(1.5*angle,-.6,.6))
    command(v,w);history.append(dict(time_s=now-begin,x=float(pos[0]),y=float(pos[1]),yaw_rad=yaw,goal_distance_m=dist,heading_deg=math.degrees(angle),free_distance_m=free,v_mps=v,w_radps=w))
    if not -.04<tr[2]<.12:reason='left_floor';break
   if now-fresh>.6:reason='stale_scan';break
   if record and now>=next_capture:
    index=len(captures);path=folder/'frames'/f'{index:05d}.png'
    await capture_viewport_to_file(vp,str(path)).wait_for_result(completion_frames=0)
    captures.append({'file':path.name,'simulation_time_s':now-begin});next_capture=now+.2
  command(0,0);stop_position=body.get_transforms().copy()[0,:3].tolist();stop_time=t.get_current_time()-begin
  await frames(60);final=body.get_transforms().copy()[0,:3].tolist()
  drift=math.dist(stop_position,final)
  blocked=reason in ['no_safe_gap','blocked_no_progress'] and final[1]<-2.25
  passed=(blocked if name=='blocked' else reason=='goal_reached') and max_force<=.1 and drift<.03
  await capture_viewport_to_file(vp,str(folder/'final.png')).wait_for_result()
 finally:
  command(0,0);t.pause();t.commit()
  report=dict(case=name,passed=locals().get('passed',False),reason=reason,goal=goal.tolist(),obstacles=CASES[name],final=locals().get('final'),duration_s=locals().get('stop_time'),braking_drift_m=locals().get('drift'),max_contact_force_n=max_force,contact_body_count=contact.sensor_count,monitored_colliders=filters,trajectory=history,video_frames=captures,localization='simulator ground truth')
  (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k not in ['trajectory','video_frames','monitored_colliders']}))
 return report

async def main():
 for name in CASES:await run_case(name)

if __name__=='__main__':asyncio.ensure_future(main())
