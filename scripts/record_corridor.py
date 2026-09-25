import json, math
from pathlib import Path
import carb, omni.usd, omni.timeline, omni.kit.app
from pxr import UsdPhysics
import isaacsim.core.experimental.utils.app as app_utils
from omni.physics.tensors import create_simulation_view
root=Path('C:/Users/User/Documents/navbot/_isaacsim')
folder=root/'tests/physics/videos'
folder.mkdir(exist_ok=True)
ctx=omni.usd.get_context();stage=ctx.get_stage()
t=omni.timeline.get_timeline_interface();app=omni.kit.app.get_app()
assert stage.GetRootLayer().identifier.endswith('navbot_corridor_test.usda')
assert t.is_stopped() and carb.settings.get_settings().get('/app/asyncRendering') is False
app_utils.enable_extension('omni.videoencoding')
app_utils.enable_extension('omni.kit.capture.viewport')
for _ in range(20): await app.next_update_async()
from omni.kit.capture.viewport import CaptureOptions,CaptureRangeType,CaptureRenderPreset,CaptureMovieType
from omni.kit.capture.viewport import extension as capture_ext
capture=capture_ext.capture_instance
drives=[UsdPhysics.DriveAPI.Get(stage.GetPrimAtPath('/World/NavBot/Physics/'+n),'angular') for n in ['wheel_left_joint','wheel_right_joint']]
rotation=stage.GetPrimAtPath('/World/NavBot').GetAttribute('xformOp:rotateZ')
def speed(v):
    for d in drives:d.GetTargetVelocityAttr().Set(math.degrees(v))
reports=[]
try:
    for name,yaw,duration,stop_at in [('forward',90,8,5),('wall_contact',0,12,10)]:
        filename='2026-09-24_navbot_corridor_'+name
        assert not (folder/(filename+'.mp4')).exists(), 'Existing recording'
        rotation.Set(yaw);speed(0)
        opts=CaptureOptions()
        opts.range_type=CaptureRangeType.FRAMES
        opts.start_frame=0;opts.end_frame=duration*30-1
        opts.fps=30;opts.animation_fps=30
        opts.res_width=1280;opts.res_height=720
        opts.output_folder=str(folder);opts.file_name=filename;opts.file_type='.mp4'
        opts.movie_type=CaptureMovieType.SEQUENCE
        opts.render_preset=CaptureRenderPreset.RAY_TRACE
        opts.camera='/World/Camera';opts.overwrite_existing_frames=False
        capture.options=opts;capture.show_default_progress_window=False
        last_v=None
        def control(event):
            global_unused=None
            now=t.get_current_time()
            v=3 if 1<=now<stop_at else 0
            for d in drives:
                if d.GetTargetVelocityAttr().Get()!=math.degrees(v):d.GetTargetVelocityAttr().Set(math.degrees(v))
        sub=app.get_update_event_stream().create_subscription_to_pop(control,name='NavBot recording control')
        assert capture.start()
        while not capture.done: await app.next_update_async()
        sub=None
        speed(0);t.stop();t.commit()
        for _ in range(60):await app.next_update_async()
        p=folder/(filename+'.mp4')
        reports.append({'file':str(p),'bytes':p.stat().st_size if p.exists() else 0,'fps':30,'seconds':duration,'drive_start_s':1,'drive_stop_s':stop_at})
finally:
    speed(0);t.stop();t.commit()
    for _ in range(30): await app.next_update_async()
    rotation.Set(90)
print(json.dumps(reports))
