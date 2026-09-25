import asyncio
async def main():
 import omni.usd,omni.timeline,omni.kit.app,builtins,math,json,numpy as np
 from pathlib import Path
 from pxr import Usd,UsdGeom,UsdPhysics,UsdShade,PhysxSchema,Gf
 from omni.kit.viewport.utility import get_active_viewport,capture_viewport_to_file
 from omni.physics.tensors import create_simulation_view
 P=Path('C:/Users/User/Documents/navbot/_isaacsim');app=omni.kit.app.get_app();ctx=omni.usd.get_context();t=omni.timeline.get_timeline_interface()
 async def frames(n):
  for _ in range(n):await app.next_update_async()
 for name,mass in [('shoe_01',.188),('book_01',1.),('dumbbell_01',2.),('chair_01',5.)]:
  t.stop();t.commit();await frames(10)
  if hasattr(builtins,'navbot_lidar_sensor'):builtins.navbot_lidar_sensor._invalidate_sensor();del builtins.navbot_lidar_sensor
  folder=P/'tests/physics/push_comparison_isolated'/name;folder.mkdir(parents=True,exist_ok=True);(folder/'frames').mkdir(exist_ok=True)
  st=Usd.Stage.CreateInMemory();st.GetRootLayer().ImportFromString((P/'isaacsim/scenes/navbot_scanned_chair.usda').read_text(encoding='utf-8'));st.SetTimeCodesPerSecond(60);st.SetEndTimeCode(100000);st.OverridePrim('/World/SuiteObstacle_0').SetActive(False)
  prim=UsdGeom.Xform.Define(st,'/World/PushObject');prim.GetPrim().GetReferences().AddReference(str(P.parent.parent/'simforge_assets'/name/'usd'/(name+'.usda')))
  xx=-.375 if name=='shoe_01' else (-.46 if name=='chair_01' else -.28)
  UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(xx,-2.60,.004))
  file=P/'isaacsim/scenes'/('navbot_push_isolated_'+name+'.usda');st.GetRootLayer().Export(str(file));await ctx.open_stage_async(str(file));await frames(40);s=ctx.get_stage()
  if name=='shoe_01':
   for p in list(s.Traverse()):
    if p.IsValid() and str(p.GetPath()).startswith('/World/PushObject/') and ('Left' in p.GetName()):p.SetActive(False)
  obj=s.GetPrimAtPath('/World/PushObject');UsdPhysics.RigidBodyAPI.Apply(obj);UsdPhysics.MassAPI.Apply(obj).CreateMassAttr(mass);pb=PhysxSchema.PhysxRigidBodyAPI.Apply(obj);pb.CreateEnableCCDAttr(True);pb.CreateSleepThresholdAttr(0);pb.CreateStabilizationThresholdAttr(0)
  mat=UsdShade.Material.Define(s,'/World/PushContactMaterial');ma=UsdPhysics.MaterialAPI.Apply(mat.GetPrim());ma.CreateStaticFrictionAttr(.5);ma.CreateDynamicFrictionAttr(.4);ma.CreateRestitutionAttr(0);pa=PhysxSchema.PhysxMaterialAPI.Apply(mat.GetPrim());pa.CreateFrictionCombineModeAttr('average')
  colliders=[p for p in s.Traverse() if str(p.GetPath()).startswith('/World/PushObject/') and p.HasAPI(UsdPhysics.CollisionAPI)]
  for p in colliders:UsdShade.MaterialBindingAPI.Apply(p).Bind(mat,UsdShade.Tokens.strongerThanDescendants,'physics')
  bodies=[str(p.GetPath()) for p in s.Traverse() if str(p.GetPath()).startswith('/World/NavBot/') and p.HasAPI(UsdPhysics.RigidBodyAPI)]
  for path in bodies:
   bp=s.GetPrimAtPath(path);PhysxSchema.PhysxContactReportAPI.Apply(bp).CreateThresholdAttr(0);ba=PhysxSchema.PhysxRigidBodyAPI.Apply(bp);ba.CreateSleepThresholdAttr(0);ba.CreateStabilizationThresholdAttr(0)
  drives=[UsdPhysics.DriveAPI.Get(s.GetPrimAtPath('/World/NavBot/Physics/'+n),'angular') for n in ['wheel_left_joint','wheel_right_joint']]
  for d in drives:d.GetMaxForceAttr().Set(.15);d.GetTargetVelocityAttr().Set(0)
  cam=UsdGeom.Camera.Define(s,'/World/PushCamera');cam.CreateFocalLengthAttr(27);cam.CreateClippingRangeAttr(Gf.Vec2f(.01,100));cx=UsdGeom.Xformable(cam);cx.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(.10,-3.8,1.55),Gf.Vec3d(-.28,-2.65,.15),Gf.Vec3d(0,0,1)).GetInverse());s.GetRootLayer().Save();t.play();t.commit();await frames(90)
  sim=create_simulation_view('numpy',stage_id=ctx.get_stage_id());robot=sim.create_rigid_body_view('/World/NavBot/Geometry/base_footprint/base_link');ob=sim.create_rigid_body_view('/World/PushObject');contact=sim.create_rigid_contact_view(bodies,[[str(p.GetPath()) for p in colliders] for _ in bodies]);start=ob.get_transforms().copy()[0,:3];rstart=robot.get_transforms().copy()[0,:3];begin=t.get_current_time();hist=[];caps=[];nextcap=begin;maxf=0
  vp=get_active_viewport();vp.set_active_camera('/World/PushCamera')
  for d in drives:d.GetTargetVelocityAttr().Set(math.degrees(.06/.033))
  try:
   while t.get_current_time()-begin<12:
    await frames(1);now=t.get_current_time();f=float(np.abs(contact.get_contact_force_matrix(1/60)).max());maxf=max(maxf,f)
    if now>=nextcap:
     po=ob.get_transforms().copy()[0];pr=robot.get_transforms().copy()[0];hist.append({'t':now-begin,'object':po.tolist(),'robot':pr.tolist(),'force_component_n':f});fn=f'{len(caps):05d}.png';await capture_viewport_to_file(vp,str(folder/'frames'/fn)).wait_for_result(completion_frames=0);caps.append({'file':fn,'simulation_time_s':now-begin});nextcap=now+.2
    if not np.isfinite(ob.get_transforms()).all():raise RuntimeError('Nonfinite state')
  finally:
   for d in drives:d.GetTargetVelocityAttr().Set(0)
   await frames(60)
  end=ob.get_transforms().copy()[0,:3];rend=robot.get_transforms().copy()[0,:3];await capture_viewport_to_file(vp,str(folder/'final.png')).wait_for_result();t.pause();t.commit()
  report={'asset':name,'mass_kg':mass,'mass_basis':'user reported; chair lower bound, book approximate','object_contact_friction_assumed':[.5,.4],'wheel_torque_limit_assumed_nm':.15,'command_speed_mps':.06,'duration_s':12,'object_start':start.tolist(),'object_end':end.tolist(),'object_displacement_m':float(np.linalg.norm(end[:2]-start[:2])),'robot_displacement_m':float(np.linalg.norm(rend[:2]-rstart[:2])),'max_contact_force_component_n':maxf,'contact_observed':maxf>.01,'trajectory':hist,'video_frames':caps,'scope':'Rigid-body exploratory model; no foam deformation; no real-world friction or torque calibration'}
  (folder/'report.json').write_text(json.dumps(report,indent=2));print(name,report['object_displacement_m'],maxf,flush=True);sim=None;robot=None;ob=None;contact=None
 

asyncio.ensure_future(main())
