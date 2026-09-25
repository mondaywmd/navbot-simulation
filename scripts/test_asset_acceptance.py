"""Isaac Sim 6.1 Script Editor: static asset acceptance; saves current composed stage before switching. Requires local asset library and RTX setup. Overwrites same-name test outputs."""
import asyncio
async def main():
 import asyncio,builtins,json,math,os,time
 from pathlib import Path
 import numpy as np
 import omni.usd,omni.timeline,omni.kit.app,omni.physx
 from pxr import Usd,UsdGeom,UsdLux,UsdPhysics,PhysxSchema,Gf
 from omni.kit.viewport.utility import get_active_viewport,capture_viewport_to_file
 ctx=omni.usd.get_context();app=omni.kit.app.get_app();timeline=omni.timeline.get_timeline_interface()
 P=Path(r'C:/Users/User/Documents/navbot/_isaacsim');L=Path(r'C:/Users/User/Documents/simforge_assets');folder=P/'tests/assets/acceptance';folder.mkdir(parents=True,exist_ok=True)
 async def frames(n):
  for _ in range(n):await app.next_update_async()
 # Preserve current composed stage and session edits before switching away.
 old=ctx.get_stage();backup=folder/('previous_stage_'+time.strftime('%Y%m%d_%H%M%S')+'.usda');old.Export(str(backup));(folder/'previous_stage.json').write_text(json.dumps({'source':old.GetRootLayer().identifier,'snapshot':str(backup)},indent=2))
 timeline.stop();timeline.commit();await frames(15)
 if hasattr(builtins,'navbot_lidar_sensor'):
  try:builtins.navbot_lidar_sensor._invalidate_sensor()
  except Exception:pass
  del builtins.navbot_lidar_sensor
 if hasattr(builtins,'asset_test_sensor'):
  try:builtins.asset_test_sensor._invalidate_sensor()
  except Exception:pass
  del builtins.asset_test_sensor
 st=Usd.Stage.CreateInMemory();root=UsdGeom.Xform.Define(st,'/World');st.SetDefaultPrim(root.GetPrim());UsdGeom.SetStageMetersPerUnit(st,1);UsdGeom.SetStageUpAxis(st,'Z');st.SetStartTimeCode(0);st.SetEndTimeCode(1000000);st.SetTimeCodesPerSecond(60)
 ps=UsdPhysics.Scene.Define(st,'/World/PhysicsScene');ps.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1));ps.CreateGravityMagnitudeAttr(9.81)
 ground=UsdGeom.Cube.Define(st,'/World/Ground');ground.CreateSizeAttr(1);x=UsdGeom.XformCommonAPI(ground);x.SetScale(Gf.Vec3f(4,3,.04));x.SetTranslate(Gf.Vec3d(0,0,-.02));ground.CreateDisplayColorAttr([(.19,.21,.22)]);UsdPhysics.CollisionAPI.Apply(ground.GetPrim())
 names=['book_01','dumbbell_01','shoe_01','chair_01'];positions=dict(zip(names,[-.95,-.4,.2,.9]));scene=P/'isaacsim/scenes/asset_acceptance.usda'
 for name in names:
  prim=UsdGeom.Xform.Define(st,'/World/Assets/'+name);prim.GetPrim().GetReferences().AddReference(os.path.relpath(L/name/'usd'/f'{name}.usda',scene.parent).replace('\\','/'));UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(positions[name],0,0))
 light=UsdLux.DomeLight.Define(st,'/World/StudioDome');light.CreateIntensityAttr(650)
 key=UsdLux.DistantLight.Define(st,'/World/Key');key.CreateIntensityAttr(1500);UsdGeom.XformCommonAPI(key).SetRotate(Gf.Vec3f(25,-30,-20))
 cam=UsdGeom.Camera.Define(st,'/World/Camera');cam.CreateClippingRangeAttr(Gf.Vec2f(.01,100));cam.CreateFocalLengthAttr(42);view=Gf.Matrix4d().SetLookAt(Gf.Vec3d(2.7,-3.4,2),Gf.Vec3d(0,0,.25),Gf.Vec3d(0,0,1));UsdGeom.Xformable(cam).AddTransformOp().Set(view.GetInverse())
 # Sensor configuration is local; corrected echo interval is authored before initialization.
 sensorpath='/World/TestLidar';sensorprim=st.OverridePrim(sensorpath);sensorprim.GetReferences().AddReference(os.path.relpath(P/'usd/sensors/navbot_planar_lidar.usda',scene.parent).replace('\\','/'));sensorprim.CreateAttribute('omni:sensor:Core:minDistBetweenEchosM',__import__('pxr').Sdf.ValueTypeNames.Float).Set(.01)
 sensorprim.CreateAttribute('xformOp:translate',__import__('pxr').Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(0,-1,.182));sensorprim.CreateAttribute('xformOp:orient',__import__('pxr').Sdf.ValueTypeNames.Quatd).Set(Gf.Quatd(math.cos(math.pi/4),0,0,math.sin(math.pi/4)))
 st.GetRootLayer().Export(str(scene));await ctx.open_stage_async(str(scene));await frames(120);s=ctx.get_stage();vp=get_active_viewport();vp.set_active_camera('/World/Camera')
 report={'scene':str(scene),'tests':{},'notes':['Static assets; dimensions based on user approximate measurements.','Physics raycasts query colliders; RTX scans query rendered geometry.','LiDAR lower-height scan is a visibility diagnostic, not the normal robot mounting height.']}
 timeline.play();timeline.commit();await frames(60)
 query=omni.physx.get_physx_scene_query_interface()
 test_xy={'book_01':(0,0),'dumbbell_01':(0,.07),'shoe_01':(.095,0),'chair_01':(0,-.03)}
 expected={};r=.012
 for name in names:
  x,y=test_xy[name];x+=positions[name];hit=query.raycast_closest((x,y,1.5),(0,0,-1),2)
  assert hit['hit'] and '/Assets/'+name+'/' in hit['collision'],str((name,hit))
  z=float(hit['position'][2]);expected[name]=z+r
  prim=UsdGeom.Sphere.Define(s,'/World/Probes/'+name);prim.CreateRadiusAttr(r);UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(x,y,z+.18));prim.CreateDisplayColorAttr([(1,.25,.02)]);UsdPhysics.CollisionAPI.Apply(prim.GetPrim());UsdPhysics.RigidBodyAPI.Apply(prim.GetPrim());UsdPhysics.MassAPI.Apply(prim.GetPrim()).CreateMassAttr(.05);PhysxSchema.PhysxContactReportAPI.Apply(prim.GetPrim()).CreateThresholdAttr(0)
  report['tests'][name]={'top_raycast':{'collider':hit['collision'],'z_m':z},'expected_ball_center_z':z+r}
 await frames(1)
 from omni.physics.tensors import create_simulation_view
 sim=create_simulation_view('numpy',stage_id=ctx.get_stage_id());bodies={n:sim.create_rigid_body_view('/World/Probes/'+n) for n in names}
 filters=[str(p.GetPath()) for p in s.Traverse() if '/Assets/' in str(p.GetPath()) and p.HasAPI(UsdPhysics.CollisionAPI)]
 contacts=sim.create_rigid_contact_view(['/World/Probes/'+n for n in names],[filters for n in names]);forces_max=np.zeros(4);trajectories={n:[] for n in names}
 for step in range(210):
  await frames(1);forces=contacts.get_contact_force_matrix(1/60);forces_max=np.maximum(forces_max,np.max(np.linalg.norm(forces,axis=-1),axis=1))
  if step%6==0:
   for n in names:trajectories[n].append(bodies[n].get_transforms().copy()[0,:3].tolist())
 for name in names:
  pos=bodies[name].get_transforms().copy()[0,:3];velocity=bodies[name].get_velocities().copy()[0,:3];err=abs(float(pos[2])-expected[name]);passed=bool(forces_max[names.index(name)]>.01 and (err<.006 if name in ['book_01','chair_01'] else min(p[2] for p in trajectories[name])>.006))
  report['tests'][name]['drop_test']={'final_center_m':pos.tolist(),'speed_mps':float(np.linalg.norm(velocity)),'height_error_m':err,'passed':passed,'max_asset_contact_force_n':float(forces_max[names.index(name)]),'trajectory':trajectories[name]}
 gaps=[]
 for name,x,z in [('shoe_01',0,.05),('chair_01',0,.2)]:
  hit=query.raycast_closest((positions[name]+x,-.6,z),(0,1,0),1.2);gaps.append({'asset':name,'ray_local_x':x,'height_m':z,'hit':bool(hit['hit']),'collider':hit.get('collision'),'passed':not hit['hit']})
 report['gap_tests']=gaps
 (folder/'physics_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 await capture_viewport_to_file(vp,str(folder/'drop_tests.png')).wait_for_result()
 del bodies,contacts,sim
 timeline.stop();timeline.commit();await frames(20);s.RemovePrim('/World/Probes')
 em=app.get_extension_manager()
 for ext in ['isaacsim.sensors.experimental.rtx','isaacsim.sensors.rtx.nodes']:em.set_extension_enabled_immediate(ext,True)
 from isaacsim.sensors.experimental.rtx import Lidar,LidarSensor,parse_generic_model_output_data
 sensor=LidarSensor(Lidar(sensorpath,aux_output_level='FULL',reset_xform_op_properties=False),annotators=['generic-model-output']);builtins.asset_test_sensor=sensor
 def scan():
  data,_=sensor.get_data('generic-model-output');g=parse_generic_model_output_data(data)
  if not g.scanComplete:return None
  angles=(np.array(g.x,copy=True)+180)%360-180;ranges=np.array(g.z,copy=True);valid=np.isfinite(ranges)&(ranges>=.12)&(ranges<=1.35)&(abs(angles)<20)
  return {'frame_id':int(g.frameId),'hit_count':int(valid.sum()),'min_range_m':float(ranges[valid].min()) if valid.any() else None}
 for name in names:
  for other in names:s.GetPrimAtPath('/World/Assets/'+other).SetActive(other==name)
  for label,z in [('robot_height',.182),('low_diagnostic',{'book_01':.01,'dumbbell_01':.05,'shoe_01':.05,'chair_01':.40}[name])]:
   timeline.stop();timeline.commit();await frames(10);s.GetPrimAtPath(sensorpath).GetAttribute('xformOp:translate').Set(Gf.Vec3d(positions[name],-1,z));timeline.play();timeline.commit();await frames(100)
   rows=[];last=None
   for _ in range(90):
    await frames(1);row=scan()
    if row and row['frame_id']!=last:rows.append(row);last=row['frame_id']
   assert rows,'No complete RTX scans'
   detected=any(row['hit_count']>0 for row in rows);expect=(name=='chair_01' or label=='low_diagnostic')
   report['tests'][name][label]={'sensor_height_m':z,'detected':detected,'expected_detection':expect,'passed':detected==expect,'scans':rows}
 timeline.stop();timeline.commit();await frames(15)
 sensor._invalidate_sensor();del builtins.asset_test_sensor
 for name in names:s.GetPrimAtPath('/World/Assets/'+name).SetActive(True)
 s.RemovePrim(sensorpath)
 await frames(45);await capture_viewport_to_file(vp,str(folder/'asset_gallery.png')).wait_for_result();s.GetRootLayer().Save()
 report['passed']=all(t['drop_test']['passed'] and t['robot_height']['passed'] and t['low_diagnostic']['passed'] for t in report['tests'].values()) and all(t['passed'] for t in gaps)
 (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('ASSET_ACCEPTANCE',json.dumps({'passed':report['passed'],'tests':{n:{k:v for k,v in test.items() if k!='drop_test'} for n,test in report['tests'].items()}}))
 
 
 
 

asyncio.ensure_future(main())
