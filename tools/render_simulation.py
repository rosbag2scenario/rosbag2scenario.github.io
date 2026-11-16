"""Render six simulated cameras and a synchronized BEV from an archived run.

No simulation is executed. Real-camera pixels are discarded before composition.
Inputs are explicit paths; public provenance contains hashes, not local paths.
Dependencies: numpy, Pillow, pyproj; ffmpeg/ffprobe on PATH.
"""
import argparse, hashlib, json, math, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer

BG='#0f1727'; BLUE='#5ab4f0'; ORANGE='#f0a050'; GREEN='#70ed91'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def font(n): return ImageFont.truetype(FONT,n)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def sample(a,t):
    s=a['states']; ts=s['t']
    if t<ts[0] or t>ts[-1]: return None
    return [float(np.interp(t,ts,np.unwrap(s[k]) if k=='yaw' else s[k])) for k in ['x','y','yaw']]+[a['bbox']['length'],a['bbox']['width']]
def render(a):
    run=Path(a.run); root=run/'replay-experiment'; out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    source=json.loads((root/'source.json').read_text()); actors=source['actors']
    plan=json.loads((root/'traffic/plan.json').read_text());assert digest(root/'source.json')==plan['source_sha256']
    frames={r['frame']:r for r in map(json.loads,(root/'traffic/frames.jsonl').read_text().splitlines())}
    cameras=list(map(json.loads,(run/'surround-comparison/frames.jsonl').read_text().splitlines()))
    audit=json.loads((root/'handover.json').read_text()); release=audit.get('actual_source_s'); event=audit['options'].get('event_s')
    released={}
    for f in frames.values():
        for r in f.get('transitions') or []: released.setdefault(r['id'],r['time_s'])
    half=float(audit['options'].get('rear_half_angle_deg') or 90); radius=float(audit['options'].get('rear_range_m') or 100); reactive=bool(released)
    tree=ET.parse(a.lanelet).getroot(); project=Transformer.from_crs('EPSG:4326',source['metadata']['coordinate_frame']['proj_string'],always_xy=True)
    nodes={n.get('id'):project.transform(float(n.get('lon')),float(n.get('lat'))) for n in tree.findall('node')}
    ids={m.get('ref') for r in tree.findall('relation') if any(t.get('k')=='type' and t.get('v')=='lanelet' for t in r.findall('tag')) for m in r.findall('member') if m.get('type')=='way' and m.get('role') in ('left','right')}
    roads=[[nodes[n.get('ref')] for n in w.findall('nd')] for w in tree.findall('way') if w.get('id') in ids]
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',a.video]))['streams'][0]
    w,h=info['width'],info['height'];num,den=map(float,info['r_frame_rate'].split('/'));fps=num/den
    assert abs(fps-10)<1e-6
    assert (w,h)==((1920,1080) if a.layout=='submitted' else (2880,680)), 'Unexpected camera layout'
    # Public comparison: right half contains SIM, x=960..1919, y=95..504.
    # Raw observer mosaic: SIM is the right half, with a 50px header and 2 rows of 315px.
    crop='crop=960:410:960:95' if a.layout=='submitted' else 'crop=1440:630:1440:50,scale=960:420'
    hh=410 if a.layout=='submitted' else 420
    dec=subprocess.Popen(['ffmpeg','-v','error','-i',a.video,'-vf',crop,'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1600x1000','-r','10','-i','-','-an','-c:v','libx264','-threads','4','-preset','medium','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
    # Fixed common map extent includes every recorded and simulated actor in the clip.
    points=[]
    for actor in actors:
        for t,x,y in zip(actor['states']['t'],actor['states']['x'],actor['states']['y']):
            if cameras[0]['source_s']-.1<=t<=cameras[-1]['source_s']+.1:points.append((x,y))
    for f in frames.values():
        for state in f['states'].values():points.append((state['x'],state['y']))
    if a.bounds:
        x0,y0,x1,y1=map(float,a.bounds.split(','))
    else:
        xy=np.asarray(points);x0,y0=xy.min(0)-8;x1,y1=xy.max(0)+8
    origin=cameras[0]['source_s']; checked=[]
    for i,c in enumerate(cameras):
        raw=dec.stdout.read(960*hh*3)
        if len(raw)!=960*hh*3: raise ValueError('Missing camera frame')
        t=c['source_s']; f=frames[c['frame']]
        # The original renderer uses source-relative timestamps from the same exact CARLA frame.
        image=Image.new('RGB',(1600,1000),BG);image.paste(Image.frombytes('RGB',(960,hh),raw),(16,62))
        d=ImageDraw.Draw(image);d.text((16,14),a.title,font=font(26),fill='white')
        d.text((1400,17),f't = {t-origin:.1f} s',font=font(22),fill='white')
        for y,labels in [(62,['Front left','Front center','Front right']),(273,['Rear left','Rear center','Rear right'])]:
            d.rectangle((16,y,975,y+20),fill=BG)
            for col,label in enumerate(labels):d.text((24+320*col,y),label,font=font(16),fill='white')
        x=1005
        d.text((x,80),'SIX SIMULATED CAMERAS',font=font(21),fill='white')
        legend=[('Blue: reconstructed recording',BLUE),('Orange: simulation',ORANGE),('Green R: reactive vehicle',GREEN),('Shaded area: rear release region',GREEN),('Red connector: deviation > 2 m','#f06060'),('Grey: lane boundaries','#b0b8c8')]
        if not a.show_cone:legend=[item for item in legend if not item[0].startswith('Shaded')]
        if not reactive:legend=[item for item in legend if not item[0].startswith('Green R')]
        for j,(label,color) in enumerate(legend):d.text((x,130+j*37),label,font=font(20),fill=color)
        if release is not None:d.text((x,365),f'Handover: {release-origin:.1f} s',font=font(20),fill=ORANGE)
        if event is not None:d.text((x,401),f'Recorded intervention: {event-origin:.1f} s',font=font(20),fill='white')
        states=[]
        actuals=f['states']
        for actor in actors:
            ref=sample(actor,t);s=actuals.get(actor['id']);actual=None
            if s:
                prefix='actor_origin_' if actor.get('position_reference')=='actor_origin' else ''
                actual=[s[prefix+k] for k in ('x','y','yaw')]+[s['length'],s['width']]
            states.append((actor['id'],ref,actual))
        ego=next(s for k,r,s in states if k=='ego'); assert ego is not None
        left,top,bw,bh=16,515,1568,435
        scale=min(bw/(x1-x0),bh/(y1-y0));span=bw/scale;cx,cy=(x0+x1)/2,(y0+y1)/2
        def point(s): return (int(bw/2+(s[0]-cx)*scale),int(bh/2-(s[1]-cy)*scale))
        bev=Image.new('RGB',(bw,bh),BG);bd=ImageDraw.Draw(bev)
        if a.show_cone and reactive and release is not None:
            poly=[point(ego)]+[point((cx+radius*math.cos(ego[2]+math.pi+r),cy+radius*math.sin(ego[2]+math.pi+r))) for r in np.linspace(-math.radians(half),math.radians(half),91)]
            overlay=Image.new('RGBA',(bw,bh));od=ImageDraw.Draw(overlay); active=t>=release
            od.polygon(poly,fill=(112,237,145,30) if active else (150,160,175,18));od.line(poly+[poly[0]],fill=(112,237,145,120) if active else (150,160,175,70),width=2)
            bev=Image.alpha_composite(bev.convert('RGBA'),overlay).convert('RGB');bd=ImageDraw.Draw(bev)
        for road in roads:
            if any(abs(px-cx)<span and abs(py-cy)<span for px,py in road):bd.line([point(p) for p in road],fill='#637588',width=1)
        count=0
        for ident,ref,act in states:
            if ref and act and math.dist(ref[:2],act[:2])>2:bd.line([point(ref),point(act)],fill='#f06060',width=2)
            for state,color in [(ref,BLUE),(act,ORANGE)]:
                if state is None:continue
                px,py=point(state)
                if not(-100<px<bw+100 and -100<py<bh+100):continue
                if ident=='ego':
                    bd.ellipse((px-5,py-5,px+5,py+5),fill=color)
                    if state is act:
                        tip=point((state[0]+4*math.cos(state[2]),state[1]+4*math.sin(state[2])));bd.line([(px,py),tip],fill=color,width=3)
                        ang=math.atan2(tip[1]-py,tip[0]-px)
                        for da in [-2.6,2.6]:bd.line([tip,(tip[0]+8*math.cos(ang+da),tip[1]+8*math.sin(ang+da))],fill=color,width=3)
                    continue
                xx,yy,yaw,length,width=state;co,si=math.cos(yaw),math.sin(yaw)
                box=[point((xx+dx*co-dy*si,yy+dx*si+dy*co)) for dx,dy in [(-length/2,-width/2),(-length/2,width/2),(length/2,width/2),(length/2,-width/2)]]
                bd.line(box+[box[0]],fill=color,width=2)
            if act and released.get(ident,float('inf'))<=t+1e-6:
                px,py=point(act);bd.text((px-7,py-22),'R',font=font(17),fill=GREEN);count+=1
        bd.line((18,bh-15,18+10*scale,bh-15),fill='white',width=3);bd.text((18,bh-42),'10 m / north up',font=font(18),fill='white')
        image.paste(bev,(left,top)); d=ImageDraw.Draw(image)
        d.text((16,479),'BIRD’S-EYE VIEW',font=font(21),fill='white')
        d.text((990,479),'All actors · no scoring-radius filter',font=font(18),fill='white')
        phase='Recorded motion: the ego follows the recording' if release is None or t<release else 'Closed loop: the driving stack controls the ego'
        if event is not None and t>=event:phase+='  |  Recorded intervention time reached'
        d.text((16,963),phase,font=font(22),fill=ORANGE if release is not None and t>=release else 'white')
        enc.stdin.write(image.tobytes());checked.append({'frame':c['frame'],'t':round(t-origin,3),'reactive_count':count})
        if i in [0,80,120]:image.save(out.with_name(out.stem+f'-check-{i}.jpg'))
        if i==80:image.save(out.with_suffix('.jpg'))
    assert not dec.stdout.read(1),'Unindexed video frames'
    dec.stdout.close();enc.stdin.close();assert dec.wait()==0 and enc.wait()==0
    out.with_suffix('.json').write_text(json.dumps({'case':a.case,'illustrative_rerun':a.case=='D1','frames':len(checked),'source_video_sha256':digest(Path(a.video)),'source_states_sha256':digest(root/'source.json'),'traffic_frames_sha256':digest(root/'traffic/frames.jsonl'),'cone_half_angle_deg':half,'cone_range_m':radius,'handover_video_s':None if release is None else release-origin,'event_video_s':None if event is None else event-origin,'all_actors':True,'cone_overlay':bool(a.show_cone and reactive),'map_bounds':[x0,y0,x1,y1],'source_start_s':origin,'camera_pixels':'Simulation half only; real camera half discarded before composition.','timing':checked},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--video',required=True);p.add_argument('--lanelet',required=True);p.add_argument('--output',required=True);p.add_argument('--case',required=True);p.add_argument('--title',required=True);p.add_argument('--show-cone',action='store_true');p.add_argument('--bounds');p.add_argument('--layout',choices=['submitted','raw'],default='submitted');render(p.parse_args())
