import asyncio
async def main():
 """Isaac Sim Script Editor: depth-assisted navigation on one fixed scattered layout.
 Open a scene under this project's isaacsim/scenes before running.
 Videos are encoded separately from 5 Hz viewport frames and frame timestamps.
 """
 import asyncio,builtins,json,math,random,heapq
 from scipy.ndimage import distance_transform_edt
 from pathlib import Path
 import numpy as np
 import omni.usd,omni.timeline,omni.kit.app
 from pxr import Usd,UsdGeom,UsdPhysics,PhysxSchema,Gf
 
 CASES={'random_scattered':[]}
 SEED=20260925
 
 async def run_case(name,record=True):
  ctx=omni.usd.get_context();t=omni.timeline.get_timeline_interface();app=omni.kit.app.get_app()
  root=Path(ctx.get_stage().GetRootLayer().identifier).parents[2]
  assert (root/'isaacsim/scenes/navbot_lidar_stop_test.usda').exists(),'Open a project scene first'
  folder=root/'tests/navigation/depth_planner'/str(SEED);folder.mkdir(parents=True,exist_ok=True)
  async def frames(n):
   for _ in range(n):await app.next_update_async()
  t.stop();t.commit();await frames(15)
  if hasattr(builtins,'navbot_lidar_sensor'):
   builtins.navbot_lidar_sensor._invalidate_sensor();del builtins.navbot_lidar_sensor
  st=Usd.Stage.CreateInMemory();st.GetRootLayer().ImportFromString((root/'isaacsim/scenes/navbot_scanned_chair.usda').read_text(encoding='utf-8'));st.OverridePrim('/World/SuiteObstacle_0').SetActive(False)
  rng=random.Random(SEED);names=['chair_01','shoe_01','book_01','dumbbell_01'];rng.shuffle(names);targets=[];layout=[]
  for i,(asset,y) in enumerate(zip(names,[-2.35,-1.55,-.65,.15])):
   width={'chair_01':.45,'shoe_01':.32,'book_01':.15,'dumbbell_01':.10}[asset];x=rng.uniform(-.78+width/2,.20-width/2);y+=rng.uniform(-.06,.06);angle=rng.uniform(-12,12)
   path='/World/Scattered/'+asset;obj=UsdGeom.Xform.Define(st,path);obj.GetPrim().GetReferences().AddReference(str(root.parent.parent/'simforge_assets'/asset/'usd'/(asset+'.usda')));xf=UsdGeom.XformCommonAPI(obj);xf.SetTranslate(Gf.Vec3d(x,y,0));xf.SetRotate(Gf.Vec3f(0,0,angle));targets.append(path);layout.append({'asset':asset,'x':x,'y':y,'yaw_deg':angle})
  CASES[name]=layout
  filename=root/'isaacsim/scenes/navbot_depth_planner.usda';st.GetRootLayer().Export(str(filename));await ctx.open_stage_async(str(filename));await frames(90)
  s=ctx.get_stage();em=app.get_extension_manager()
  for ext in ['isaacsim.sensors.experimental.rtx','isaacsim.sensors.rtx.nodes']:em.set_extension_enabled_immediate(ext,True)
  cp='/World/NavBot/Geometry/base_footprint/base_link/DepthCamera';dc=UsdGeom.Camera.Define(s,cp);dc.CreateFocalLengthAttr(12);dc.CreateHorizontalApertureAttr(20.14);dc.CreateVerticalApertureAttr(15.105);dc.CreateClippingRangeAttr(Gf.Vec2f(.04,4));dx=UsdGeom.Xformable(dc);dx.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(.085,0,.13),Gf.Vec3d(.8,0,-.15),Gf.Vec3d(0,0,1)).GetInverse())
  import omni.replicator.core as rep
  rp=rep.create.render_product(cp,(640,480));da=rep.AnnotatorRegistry.get_annotator('distance_to_image_plane');da.attach([rp]);memory=[];rng=np.random.default_rng(71);depth_counts=[];occupied=set();resolution=.025;origin=np.array([-2.,-5.]);shape=(160,320);depth_fresh=0
  from isaacsim.sensors.experimental.rtx import Lidar,LidarSensor,parse_generic_model_output_data
  from omni.physics.tensors import create_simulation_view
  from omni.kit.viewport.utility import get_active_viewport,capture_viewport_to_file
  sensor=LidarSensor(Lidar('/World/NavBot/Geometry/base_footprint/base_link/base_scan/Lidar',aux_output_level='FULL',reset_xform_op_properties=False),annotators=['generic-model-output'])
  builtins.navbot_lidar_sensor=sensor
  bodies=[str(p.GetPath()) for p in s.Traverse() if str(p.GetPath()).startswith('/World/NavBot/') and p.HasAPI(UsdPhysics.RigidBodyAPI)]
  for path in bodies:PhysxSchema.PhysxContactReportAPI.Apply(s.GetPrimAtPath(path)).CreateThresholdAttr(0)
  filters=[str(p.GetPath()) for p in s.Traverse() if str(p.GetPath()).startswith(tuple(targets)) and p.HasAPI(UsdPhysics.CollisionAPI)]+[str(p.GetPath()) for p in s.Traverse() if str(p.GetPath()).startswith('/World/Corridor/Collision/') and p.HasAPI(UsdPhysics.CollisionAPI) and p.GetName()!='Floor']
  assert len(filters)>0
  drives=[UsdPhysics.DriveAPI.Get(s.GetPrimAtPath('/World/NavBot/Physics/'+n),'angular') for n in ['wheel_left_joint','wheel_right_joint']]
  def command(v,w):
   for d,side in zip(drives,[-1,1]):d.GetTargetVelocityAttr().Set(math.degrees((v+side*w*.16/2)/.033))
  command(0,0);t.play();t.commit();await frames(90)
  sim=create_simulation_view('numpy',stage_id=ctx.get_stage_id())
  body=sim.create_rigid_body_view('/World/NavBot/Geometry/base_footprint/base_link')
  contact=sim.create_rigid_contact_view(bodies,[filters for _ in bodies])
  assert contact.sensor_count==len(bodies) and contact.filter_count==len(filters)
  goal=np.array([-.28,.85]);begin=t.get_current_time();last=None;fresh=begin;previous=0.;history=[];max_force=0.;reason='timeout'
  best=float('inf');progress_time=begin;captures=[];next_capture=begin
  vp=get_active_viewport();cfg=json.loads((root/'tests/navigation/scanned_chair/observation_camera.json').read_text(encoding='utf-8'));cam=UsdGeom.Camera.Define(s,'/World/NavTestCamera');cam.CreateFocalLengthAttr(cfg['focal_length']);cam.CreateClippingRangeAttr(Gf.Vec2f(.01,100));cx=UsdGeom.Xformable(cam);cx.AddTransformOp().Set(Gf.Matrix4d(*[v for row in cfg['world_transform'] for v in row]));vp.set_active_camera('/World/NavTestCamera');s.GetRootLayer().Save()
  if record:(folder/'frames').mkdir(exist_ok=True)
  try:
   while t.get_current_time()-begin<100:
    await frames(1);now=t.get_current_time()
    forces=contact.get_contact_force_matrix(1/60);max_force=max(max_force,float(np.abs(forces).max()))
    if max_force>.1:reason='contact';break
    data,_=sensor.get_data('generic-model-output');g=parse_generic_model_output_data(data)
    if g.numElements and g.scanComplete and g.frameId!=last:
     last=g.frameId;fresh=now;tr=body.get_transforms().copy()[0];pos=tr[:2].astype(float);qx,qy,qz,qw=tr[3:7]
     yaw=math.atan2(2*(qw*qz+qx*qy),1-2*(qy*qy+qz*qz));dist=float(np.linalg.norm(goal-pos))
     if dist<.12:reason='goal_reached';break
     if dist<best-.025:best=dist;progress_time=now
     if now-progress_time>18:reason='blocked_no_progress';break
     a=np.deg2rad(np.array(g.x,copy=True));r=np.array(g.z,copy=True);valid=np.isfinite(r)&(r>=.12)&(r<=3.5)
     points=np.column_stack((r[valid]*np.cos(a[valid])-.032,r[valid]*np.sin(a[valid])))
     d=np.array(da.get_data()).squeeze()
     if d.shape==(480,640):
      yy,xx=np.indices(d.shape);pc=np.stack([(xx-319.5)*d/(640*12/20.14),-(yy-239.5)*d/(480*12/15.105),-d,np.ones_like(d)],axis=-1).reshape(-1,4);valid=np.isfinite(pc).all(1)&(d.ravel()>.04)&(d.ravel()<2.0);world=(pc[valid]@np.array(dc.ComputeLocalToWorldTransform(0)))[:,:3]
      sample=world[rng.choice(len(world),min(2500,len(world)),replace=False)];plane_best=None
      for _ in range(70):
       q=sample[rng.choice(len(sample),3,replace=False)];n=np.cross(q[1]-q[0],q[2]-q[0]);norm=np.linalg.norm(n)
       if norm<1e-8:continue
       n/=norm
       if n[2]<0:n=-n
       if n[2]<.97:continue
       off=-n@q[0];count=int((np.abs(sample@n+off)<.005).sum())
       if plane_best is None or count>plane_best[0]:plane_best=(count,n,off)
      if plane_best is not None:
       _,n,off=plane_best;depth_fresh=now;heights=world@n+off;obstacles=world[(heights>.012)&(heights<.25)];grid=np.unique(np.round(obstacles[:,:2]/.02).astype(int),axis=0)*.02;memory.append((now,grid));depth_counts.append(len(grid))
     memory=[(tm,ps) for tm,ps in memory if now-tm<3.0]
     if memory:
      extra=np.vstack([ps for _,ps in memory]);delta=extra-pos;rot=np.array([[math.cos(yaw),math.sin(yaw)],[-math.sin(yaw),math.cos(yaw)]]);extra=delta@rot.T;extra=extra[np.linalg.norm(extra,axis=1)>.13];points=np.vstack([points,extra])
     if now-depth_fresh>.6:reason='stale_depth';break
     c,ss=math.cos(yaw),math.sin(yaw);rotation=np.array([[c,-ss],[ss,c]])
     wp=points@rotation.T+pos;cells=np.round((wp-origin)/resolution).astype(int)
     occupied.update((int(a),int(b)) for a,b in cells if 0<=a<shape[0] and 0<=b<shape[1])
     grid=np.zeros(shape,dtype=bool)
     for cell in occupied:grid[cell]=True
     clearance=distance_transform_edt(~grid)*resolution;blocked=clearance<.175
     start=tuple(np.round((pos-origin)/resolution).astype(int));finish=tuple(np.round((goal-origin)/resolution).astype(int))
     frontier=[(0.,start)];cost={start:0.};parent={};found=False
     while frontier:
      _,current=heapq.heappop(frontier)
      if current==finish:found=True;break
      for ix,iy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
       nxt=(current[0]+ix,current[1]+iy)
       if not(0<=nxt[0]<shape[0] and 0<=nxt[1]<shape[1]) or blocked[nxt]:continue
       if ix and iy and (blocked[current[0]+ix,current[1]] or blocked[current[0],current[1]+iy]):continue
       nc=cost[current]+math.hypot(ix,iy)*(1+.08/max(.025,clearance[nxt]-.15))
       if nc<cost.get(nxt,float('inf')):
        cost[nxt]=nc;parent[nxt]=current;heapq.heappush(frontier,(nc+math.dist(nxt,finish),nxt))
     if not found:reason='no_map_path';break
     path=[finish]
     while path[-1]!=start:path.append(parent[path[-1]])
     path.reverse();route=np.array(path)*resolution+origin
     target=route[min(6,len(route)-1)];local=rotation.T@(target-pos);angle=math.atan2(local[1],local[0]);previous=angle
     # Rotate before advancing; the inflated map accounts for the circular footprint.
     v=.065*max(0,math.cos(angle)) if abs(angle)<math.radians(35) else 0.;w=float(np.clip(2*angle,-.55,.55));free=float(clearance[start])
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
   passed=(reason=='goal_reached') and max_force<=.1 and drift<.03
   await capture_viewport_to_file(vp,str(folder/'final.png')).wait_for_result()
  finally:
   command(0,0);t.pause();t.commit();da.detach([rp]);rp.destroy()
   report=dict(case=name,passed=locals().get('passed',False),reason=reason,goal=goal.tolist(),obstacles=CASES[name],final=locals().get('final'),duration_s=locals().get('stop_time'),braking_drift_m=locals().get('drift'),max_contact_force_n=max_force,contact_body_count=contact.sensor_count,monitored_colliders=filters,trajectory=history,video_frames=captures,localization='simulator ground truth',depth_obstacle_grid_counts=depth_counts,depth_ground_threshold_m=.012,depth_memory_seconds=3,planner='A-star on accumulated sensor points, 2.5 cm grid, 17.5 cm footprint inflation')
   (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
  print(json.dumps({k:v for k,v in report.items() if k not in ['trajectory','video_frames','monitored_colliders']}))
  return report
 
 async def main():
  for name in CASES:await run_case(name)
 
 await run_case('random_scattered',record=True)

asyncio.ensure_future(main())
