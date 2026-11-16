"""Join the two standard SIM/BEV exports without changing their frames or layout."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def compose(a):
    left,right,out=map(Path,[a.left,a.right,a.output]);out.parent.mkdir(parents=True,exist_ok=True)
    l,r=[json.loads(p.with_suffix('.json').read_text()) for p in [left,right]]
    assert l['frames']==r['frames']==222
    assert l['map_bounds_by_frame']==r['map_bounds_by_frame']
    assert [v['source_s'] for v in l['timing']]==[v['source_s'] for v in r['timing']]
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(left),'-i',str(right),'-filter_complex','[0:v][1:v]hstack=inputs=2[v]','-map','[v]','-an','-c:v','libx264','-threads','4','-preset','medium','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-ss','12','-i',str(out),'-frames:v','1',str(out.with_suffix('.jpg'))],check=True)
    data=dict(video=out.name,sha256=digest(out),origin='Standard BEV renderer, simulation cameras only, synchronized D2 comparison',composition=dict(frames=222,fps=10,width=3840,height=1470,left='Hybrid policy',right='Log replay',all_actors=True,camera_views_per_run=6,source_times_identical=True,map_bounds_identical=True),inputs={'d2-regression-hybrid':dict(sha256=digest(left),render=l),'d2-regression-logreplay':dict(sha256=digest(right),render=r)},composer_sha256=digest(Path(__file__)))
    out.with_suffix('.json').write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--left',required=True);p.add_argument('--right',required=True);p.add_argument('--output',required=True);compose(p.parse_args())
