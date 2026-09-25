import asyncio
async def main():
 import json,math,random
 from pathlib import Path
 import omni.usd,omni.timeline,omni.kit.app
 from pxr import Usd,UsdGeom,UsdPhysics,UsdShade,PhysxSchema,Gf
 P=Path('YOUR_PROJECT_ROOT');F=P/'tests/assets/ball_shower_200';F.mkdir(parents=True,exist_ok=True)
 app=omni.kit.app.get_app();ctx=omni.usd.get_context();t=omni.timeline.get_timeline_interface()
 async def frames(n):
  for _ in range(n): await app.next_update_async()
 t.stop();t.commit();await frames(5)
 ctx.get_stage().Export(str(F/'before_shower.usda'))
 s=Usd.Stage.CreateInMemory();s.GetRootLayer().subLayerPaths=['asset_acceptance.usda'];s.SetTimeCodesPerSecond(60);s.SetStartTimeCode(0);s.SetEndTimeCode(100000)
 scene=P/'isaacsim/scenes/asset_ball_shower_200.usda';s.GetRootLayer().Export(str(scene));await ctx.open_stage_async(str(scene));await frames(40);s=ctx.get_stage()
 s.GetPrimAtPath('/World/Ground').GetAttribute('xformOp:scale').Set(Gf.Vec3f(12,12,.04))
 mat=UsdShade.Material.Define(s,'/World/BallMaterial');pm=UsdPhysics.MaterialAPI.Apply(mat.GetPrim());pm.CreateStaticFrictionAttr(.28);pm.CreateDynamicFrictionAttr(.20);pm.CreateRestitutionAttr(.68)
 px=PhysxSchema.PhysxMaterialAPI.Apply(mat.GetPrim());px.CreateRestitutionCombineModeAttr('max');px.CreateFrictionCombineModeAttr('min')
 sceneapi=PhysxSchema.PhysxSceneAPI.Apply(s.GetPrimAtPath('/World/PhysicsScene'));sceneapi.CreateBounceThresholdAttr(.1);sceneapi.CreateTimeStepsPerSecondAttr(120)
 for prim in list(s.Traverse()):
  path=str(prim.GetPath())
  if '/Assets/shoe_01/Collision/' in path and prim.HasAPI(UsdPhysics.CollisionAPI):UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Set(False)
  if '/Assets/shoe_01/Visual/' in path and prim.IsA(UsdGeom.Mesh):UsdPhysics.CollisionAPI.Apply(prim);UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr('none')
 colors=[(.95,.16,.04),(.02,.42,.95),(.98,.65,.02),(.12,.72,.22),(.65,.10,.85),(.02,.7,.7)]
 rng=random.Random(20260925);spawned=[]
 for group,x in enumerate([-.95,-.4,.2,.9]):
  for j in range(50):
   i=group*50+j;targeted=group==2 and j<12;r=.016 if targeted else .026
   # All balls start separate; varied small lateral velocities give natural trajectories.
   for attempt in range(1000):
    xx=x+rng.uniform(-.22,.22);yy=rng.uniform(-.28,.28);zz=rng.uniform(1.02,1.95)
    if targeted:xx=x+(-.095 if j%2==0 else .095);yy=-.055+(j%3-1)*.012;zz=.24+(j//2)*.11
    if all((xx-a)**2+(yy-b)**2+(zz-c)**2>(2*r+.008)**2 for a,b,c in spawned):break
   else:raise RuntimeError('No nonoverlapping spawn')
   spawned.append((xx,yy,zz))
   b=UsdGeom.Sphere.Define(s,f'/World/Balls/Ball_{i:02d}');b.CreateRadiusAttr(r);b.CreateDisplayColorAttr([colors[rng.randrange(6)]]);UsdGeom.XformCommonAPI(b).SetTranslate(Gf.Vec3d(xx,yy,zz))
   UsdPhysics.CollisionAPI.Apply(b.GetPrim());rb=UsdPhysics.RigidBodyAPI.Apply(b.GetPrim());rb.CreateVelocityAttr(Gf.Vec3f(0 if targeted else rng.uniform(-.45,.45),0 if targeted else rng.uniform(-.5,.3),rng.uniform(-.12,0) if targeted else rng.uniform(-.65,.35)));rb.CreateAngularVelocityAttr(Gf.Vec3f(rng.uniform(-250,250),rng.uniform(-250,250),rng.uniform(-250,250)));UsdPhysics.MassAPI.Apply(b.GetPrim()).CreateMassAttr(.035)
   body=PhysxSchema.PhysxRigidBodyAPI.Apply(b.GetPrim());body.CreateEnableCCDAttr(True);body.CreateSleepThresholdAttr(0);body.CreateStabilizationThresholdAttr(0);body.CreateLinearDampingAttr(.015);body.CreateAngularDampingAttr(.025)
   UsdShade.MaterialBindingAPI.Apply(b.GetPrim()).Bind(mat,UsdShade.Tokens.weakerThanDescendants,'physics')
 cam=UsdGeom.Camera.Define(s,'/World/ShowerCamera');xf=UsdGeom.Xformable(cam);xf.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(3,-4.8,2.8),Gf.Vec3d(0,0,.72),Gf.Vec3d(0,0,1)).GetInverse());cam.CreateFocalLengthAttr(35)
 from omni.kit.viewport.utility import get_active_viewport
 get_active_viewport().set_active_camera('/World/ShowerCamera')
 s.GetRootLayer().Save();await frames(60)
 t.play();t.commit();await frames(3)
 from omni.physics.tensors import create_simulation_view
 sim=create_simulation_view('numpy',stage_id=ctx.get_stage_id());view=sim.create_rigid_body_view('/World/Balls/*');samples=[]
 for i in range(360):
  await frames(1)
  if i%2==0:samples.append({'t':t.get_current_time(),'p':view.get_transforms().copy()[:,:3].tolist(),'v':view.get_velocities().copy()[:,:3].tolist()})
 (F/'motion_check.json').write_text(json.dumps(samples));sim=None;view=None
 t.stop();t.commit();await frames(20)
 print('VALIDATED',len(samples),'samples',samples[-1]['t'],flush=True)
 app.get_extension_manager().set_extension_enabled_immediate('omni.kit.capture.viewport',True);await frames(10)
 from omni.kit.capture.viewport import CaptureOptions,CaptureRangeType,CaptureRenderPreset,CaptureMovieType
 from omni.kit.capture.viewport import extension as ce
 c=ce.capture_instance;o=CaptureOptions();o.capture_every_Nth_frames=1;o.file_name_num_pattern='.####';o.range_type=CaptureRangeType.FRAMES;o.start_frame=0;o.end_frame=359;o.fps=30;o.animation_fps=30;o.res_width=1280;o.res_height=720;o.output_folder=str(F);o.file_name='ball_shower_200';o.file_type='.png';o.movie_type=CaptureMovieType.SEQUENCE;o.render_preset=CaptureRenderPreset.RAY_TRACE;o.camera='/World/ShowerCamera';o.overwrite_existing_frames=True
 c.options=o;c.show_default_progress_window=False;assert c.start()
 while not c.done:await frames(1)
 t.stop();t.commit();await frames(10)
 print('DONE',str(F))
 
 

asyncio.ensure_future(main())
