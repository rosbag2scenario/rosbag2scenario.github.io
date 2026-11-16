"""Adapt the usual submission renderer to six SIM cameras; archived inputs only."""
import argparse,hashlib,json,subprocess,xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from pyproj import Transformer
from standard_bev import sample,draw_bev,BG,FONT

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return [json.loads(r) for r in p.read_text().splitlines()]
def render(a):
    run=Path(a.run);rp=run/'replay-experiment';out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    src=json.loads((rp/'source.json').read_text());refs=src['actors'];plan=json.loads((rp/'traffic/plan.json').read_text())
    assert digest(rp/'source.json')==plan['source_sha256']
    frames={f['frame']:f for f in rows(rp/'traffic/frames.jsonl')};cameras=rows(run/'surround-comparison/frames.jsonl')
    audit=json.loads((rp/'handover.json').read_text());released={}
    for f in frames.values():
        for r in f.get('transitions') or []:released.setdefault(r['id'],r['time_s'])
    actor_ids={r['id'] for r in refs};assert all(set(f['states'])<=actor_ids for f in frames.values())
    ego_index=next(i for i,r in enumerate(refs) if r['id']=='ego')
    pair=None
    if a.paired_run:
        pairpath=Path(a.paired_run)/'replay-experiment';assert digest(pairpath/'source.json')==digest(rp/'source.json')
        pairframes=rows(pairpath/'traffic/frames.jsonl');pair={round(f['time'],5):f['states']['ego'] for f in pairframes}
    tree=ET.parse(a.lanelet).getroot();tr=Transformer.from_crs('EPSG:4326',src['metadata']['coordinate_frame']['proj_string'],always_xy=True)
    nodes={n.get('id'):tr.transform(float(n.get('lon')),float(n.get('lat'))) for n in tree.findall('node')}
    ids={m.get('ref') for r in tree.findall('relation') if any(t.get('k')=='type' and t.get('v')=='lanelet' for t in r.findall('tag')) for m in r.findall('member') if m.get('type')=='way' and m.get('role') in ('left','right')}
    roads=[[nodes[n.get('ref')] for n in w.findall('nd')] for w in tree.findall('way') if w.get('id') in ids]
    video=run/'surround-comparison/comparison.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate','-of','json',str(video)]))['streams'][0]
    assert (info['width'],info['height'],info['r_frame_rate'])==(2880,680,'10/1')
    # Extract the actual 300-pixel camera rows separately, excluding the source mosaic's 15-pixel gutter.
    camera_filter='[0:v]split=2[top][bottom];[top]crop=1440:300:1440:45:exact=1[t];[bottom]crop=1440:300:1440:360:exact=1[b];[t][b]vstack=inputs=2,scale=1920:800:flags=lanczos[cameras]'
    dec=subprocess.Popen(['ffmpeg','-v','error','-i',str(video),'-filter_complex',camera_filter,'-map','[cameras]','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1470','-r','10','-i','-','-an','-c:v','libx264','-threads','4','-preset','medium','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
    font=lambda size:ImageFont.truetype(FONT,size)
    times=[];bounds_log=[];start=cameras[0]['source_s'];handover=audit.get('actual_source_s');event=audit['options'].get('event_s')
    event_label=str(Decimal(str(round(event-start,6))).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP)) if event is not None else None
    for index,c in enumerate(cameras):
        raw=dec.stdout.read(1920*800*3);assert len(raw)==1920*800*3
        row=frames[c['frame']];t=row['time'];assert abs(t-c['source_s'])<.001
        f={'r':[],'a':[]}
        for r in refs:
            ref=sample(r,t);state=row['states'].get(r['id']);actual=None
            if state:
                reference=r.get('position_reference');assert reference in ['actor_origin','bounding_box_center']
                prefix='actor_origin_' if reference=='actor_origin' else ''
                actual=[state[prefix+k] for k in ['x','y','yaw']]+[state['length'],state['width']]
                actual.append(float(np.linalg.norm(np.subtract(actual[:2],ref[:2]))) if ref else 0.)
            f['r'].append(ref);f['a'].append(actual)
        centers=[s[:2] for s in [f['r'][ego_index],f['a'][ego_index]] if s]
        if pair is not None:
            state=pair[round(t,5)];prefix='actor_origin_' if refs[ego_index].get('position_reference')=='actor_origin' else ''
            centers.append([state[prefix+'x'],state[prefix+'y']])
        # Usual ego-centered extent. For the D2 pair, both simulated egos contribute symmetrically.
        center=np.mean(centers,axis=0);span=max(130.,float(np.ptp(np.asarray(centers)[:,0]))+70.,(float(np.ptp(np.asarray(centers)[:,1]))+55.)*1400/480)
        bounds=[center[0]-span/2,center[1]-span*480/2800,center[0]+span/2,center[1]+span*480/2800]
        visible=[line for line in roads if any(bounds[0]-20<=x<=bounds[2]+20 and bounds[1]-20<=y<=bounds[3]+20 for x,y in line)]
        image=Image.new('RGB',(1920,1470),BG);image.paste(Image.frombytes('RGB',(1920,800),raw),(0,56));d=ImageDraw.Draw(image)
        d.text((20,12),a.title,font=font(30),fill='white')
        for y,labels in [(56,['Front left','Front center','Front right']),(456,['Rear left','Rear center','Rear right'])]:
            d.rectangle((0,y,1919,y+27),fill=BG)
            for col,label in enumerate(labels):d.text((12+640*col,y),label,font=font(22),fill='white')
        d.text((20,869),'Bird’s-eye view',font=font(24),fill='white')
        active={k for k,v in released.items() if t>=v}
        ego=f['a'][ego_index];cone=None
        if ego and audit['options'].get('traffic_mode')!='kinematic':
            angles=ego[2]+np.pi+np.linspace(-np.pi/4,np.pi/4,61)
            cone=[tuple(ego[:2])]+[(ego[0]+100*np.cos(angle),ego[1]+100*np.sin(angle)) for angle in angles]
        draw_bev(image,dict(bounds=bounds,roads=visible,actors=[dict(id=r['id'],path=[]) for r in refs],road_color='#637588',road_width=2,reactive_ids=active,heading_arrows=True,cone=cone,cone_active=handover is not None and t>=handover),f,(15,905,1400,480))
        for j,(label,color) in enumerate([('Blue: reconstructed recording','#47c7ec'),('Orange: simulation','#ffab54'),('Green R: reactive vehicle','#70ed91'),('Red: position error > 2 m','#ed6470'),('Grey: lane boundaries','#b0b8c8')]):d.text((1440,910+j*34),label,font=font(21),fill=color)
        autonomous=handover is not None and t>=handover
        mode='Autonomous' if autonomous else 'Replay'
        d.rectangle((1440,1088,1904,1138),fill='#15382e' if autonomous else '#243348',outline='#70ed91' if autonomous else '#a6b7ce',width=2)
        bold=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',23)
        d.text((1452,1098),f'Driving mode: {mode}',font=bold,fill='white')
        d.text((1440,1152),f't = {t-start:.1f} s',font=font(27),fill='white')
        if event is not None:d.text((1440,1197),f'Disengagement t_d = {event_label} s',font=font(23),fill='#ffb5b5')
        enc.stdin.write(image.tobytes());times.append({'frame':c['frame'],'t':round(t-start,5),'source_s':t});bounds_log.append(bounds)
        if index==120:image.save(out.with_suffix('.jpg'))
        if index==0:image.save(out.with_name(out.stem+'-before.jpg'))
    assert not dec.stdout.read(1);dec.stdout.close();enc.stdin.close();assert dec.wait()==0 and enc.wait()==0
    meta=dict(case=a.case,run=run.name,frames=len(times),all_actors=True,cone_overlay=audit['options'].get('traffic_mode')!='kinematic',cone_visualization=dict(opening_deg=90,range_m=100,anchor='simulated ego',activation_source_s=handover),camera_rows=dict(source_y=[45,360],source_height=300,output_height=400,gutter_removed=True),status_position=[1440,1088],clock_position=[1440,1152],mode_overlay=dict(modes=['Replay','Autonomous'],handover_source_s=handover,disengagement_source_s=event,disengagement_video_s=event-start if event is not None else None,event_position=[1440,1197],event_callout=False,camera_outline=False),view='Usual ego-centered BEV; all actors considered, no scoring-radius filter',source_start_s=start,timing=times,map_bounds_by_frame=bounds_log,source_video_sha256=digest(video),source_states_sha256=digest(rp/'source.json'),traffic_frames_sha256=digest(rp/'traffic/frames.jsonl'),lanelet_sha256=digest(Path(a.lanelet)),standard_drawing_sha256=digest(Path(__file__).with_name('standard_bev.py')),renderer_sha256=digest(Path(__file__)))
    out.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--lanelet',required=True);p.add_argument('--output',required=True);p.add_argument('--title',required=True);p.add_argument('--case',required=True);p.add_argument('--paired-run');render(p.parse_args())
