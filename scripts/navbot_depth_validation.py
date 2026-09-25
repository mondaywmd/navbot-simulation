import asyncio
async def main():
 import omni.usd,omni.kit.app,omni.timeline,builtins,json,numpy as np
 from pxr import Usd,UsdGeom,UsdPhysics,Gf
 from pathlib import Path
 P=Path('C:/Users/User/Documents/navbot/_isaacsim');F=P/'tests/sensors/depth_low_obstacles';F.mkdir(parents=True,exist_ok=True);ctx=omni.usd.get_context();app=omni.kit.app.get_app();t=omni.timeline.get_timeline_interface()
 async def frames(n):
  for _ in range(n):await app.next_update_async()
 t.stop();t.commit();await frames(10)
 if hasattr(builtins,'navbot_lidar_sensor'):builtins.navbot_lidar_sensor._invalidate_sensor();del builtins.navbot_lidar_sensor
 st=Usd.Stage.CreateInMemory();st.GetRootLayer().ImportFromString((P/'isaacsim/scenes/navbot_scanned_chair.usda').read_text(encoding='utf-8'));st.OverridePrim('/World/SuiteObstacle_0').SetActive(False);file=P/'isaacsim/scenes/navbot_depth_validation.usda';st.GetRootLayer().Export(str(file));await ctx.open_stage_async(str(file));await frames(40);s=ctx.get_stage()
 base='/World/NavBot/Geometry/base_footprint/base_link';cp=base+'/DepthCamera';c=UsdGeom.Camera.Define(s,cp);c.CreateFocalLengthAttr(12);c.CreateHorizontalApertureAttr(20.14);c.CreateVerticalApertureAttr(15.105);c.CreateClippingRangeAttr(Gf.Vec2f(.04,4));x=UsdGeom.Xformable(c);x.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(.085,0,.13),Gf.Vec3d(.8,0,-.15),Gf.Vec3d(0,0,1)).GetInverse())
 for name in ['shoe_01','book_01','dumbbell_01']:
  o=UsdGeom.Xform.Define(s,'/World/DepthTarget/'+name);o.GetPrim().GetReferences().AddReference(str(P.parent.parent/'simforge_assets'/name/'usd'/(name+'.usda')));UsdGeom.XformCommonAPI(o).SetTranslate(Gf.Vec3d(-.28,-2.3,0));o.GetPrim().SetActive(False)
 s.GetRootLayer().Save()
 import omni.replicator.core as rep
 rp=rep.create.render_product(cp,(640,480));depth=rep.AnnotatorRegistry.get_annotator('distance_to_image_plane');depth.attach([rp]);rgb=rep.AnnotatorRegistry.get_annotator('rgb');rgb.attach([rp]);builtins.navbot_depth_test=(rp,depth,rgb)
 t.play();t.commit();await frames(90)
 from PIL import Image
 results={};rng=np.random.default_rng(17)
 for case in ['empty','shoe_01','book_01','dumbbell_01']:
  for name in ['shoe_01','book_01','dumbbell_01']:s.GetPrimAtPath('/World/DepthTarget/'+name).SetActive(name==case)
  await frames(60);d=np.array(depth.get_data()).squeeze();im=np.array(rgb.get_data());print(case,'depth',d.shape,'rgb',im.shape,flush=True);assert d.shape==(480,640)
  Image.fromarray(im[:,:,:3]).save(str(F/(case+'_rgb.png')))
  yy,xx=np.indices(d.shape);fx=640*12/20.14;fy=480*12/15.105
  pc=np.stack([(xx-319.5)*d/fx,-(yy-239.5)*d/fy,-d,np.ones_like(d)],axis=-1).reshape(-1,4);valid=np.isfinite(pc).all(1)&(d.ravel()>.04)&(d.ravel()<3)
  mat=np.array(c.ComputeLocalToWorldTransform(0));world=(pc[valid]@mat)[:,:3]
  # Camera pose from simulated robot; plane estimated from depth, not known floor geometry.
  roi=world[(world[:,0]>-.75)&(world[:,0]<.20)&(world[:,1]>-2.9)&(world[:,1]<-1.5)]
  sample=roi[rng.choice(len(roi),min(5000,len(roi)),replace=False)];best=None
  for _ in range(180):
   pts=sample[rng.choice(len(sample),3,replace=False)];n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);norm=np.linalg.norm(n)
   if norm<1e-8:continue
   n/=norm
   if n[2]<0:n=-n
   if n[2]<.97:continue
   off=-n@pts[0];mask=np.abs(sample@n+off)<.005;count=int(mask.sum())
   if best is None or count>best[0]:best=(count,n,off)
  assert best is not None
  _,n,off=best;h=world@n+off;obs=world[(h>.012)&(h<.16)]
  box=(obs[:,0]>-.46)&(obs[:,0]<-.10)&(obs[:,1]>-2.47)&(obs[:,1]<-2.13);hits=obs[box]
  results[case]={'plane_normal':n.tolist(),'plane_offset':float(off),'target_roi_obstacle_points':len(hits),'detected':len(hits)>20,'expected':case!='empty','passed':(len(hits)>20)==(case!='empty')}
  np.savez_compressed(str(F/(case+'_depth.npz')),depth=d,obstacles=obs,plane=np.r_[n,off]);print(results[case],flush=True)
 t.stop();t.commit();depth.detach([rp]);rgb.detach([rp]);rp.destroy();del builtins.navbot_depth_test
 (F/'report.json').write_text(json.dumps(results,indent=2));print('DONE',json.dumps(results))

asyncio.ensure_future(main())
