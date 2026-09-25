"""Encode recorded frames with FFmpeg (run outside Isaac Sim).
Usage: python encode_navigation_suite.py --root PROJECT --ffmpeg FFMPEG clear center left right staggered blocked
PROJECT is the _isaacsim directory. FFMPEG is the path to ffmpeg.exe.
Videos preserve recorded simulation intervals, with a one-second final hold.
"""
import argparse,json,subprocess
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--ffmpeg',type=Path,required=True)
    parser.add_argument('cases',nargs='+',choices=['clear','center','left','right','staggered','blocked'])
    args=parser.parse_args()
    for name in args.cases:
        folder=args.root/'tests/navigation/fixed_suite'/name
        report=json.loads((folder/'report.json').read_text(encoding='utf-8'))
        frames=report['video_frames']
        if not frames:raise RuntimeError(f'{name}: no recorded frames')
        lines=[]
        for i,frame in enumerate(frames):
            duration=frames[i+1]['simulation_time_s']-frame['simulation_time_s'] if i+1<len(frames) else .2
            if duration<=0:raise ValueError('Non-increasing frame timestamps')
            lines.extend(["file 'frames/"+frame['file']+"'",f'duration {duration:.9f}'])
        lines.extend(["file 'final.png'",'duration 1.0',"file 'final.png'"])
        manifest=folder/'frames.ffconcat';manifest.write_text('\n'.join(lines),encoding='utf-8')
        subprocess.run([str(args.ffmpeg),'-y','-loglevel','error','-f','concat','-safe','0','-i',str(manifest),
                        '-vf','fps=25,format=yuv420p','-c:v','libx264','-crf','21','-preset','fast',
                        '-movflags','+faststart',str(folder/(name+'.mp4'))],check=True)
        print('Saved',folder/(name+'.mp4'))

if __name__=='__main__':main()
