"""Compose aligned D2 exports into one native-player comparison; no simulation."""
import argparse, hashlib, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def compose(a):
    root=Path(a.root); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    provenance=json.loads((root/'data/media-provenance.json').read_text())
    names=['d2-regression-hybrid','d2-regression-logreplay']
    inputs=[provenance[n] for n in names]; renders=[m['render'] for m in inputs]
    assert renders[0]['map_bounds']==renders[1]['map_bounds']
    assert renders[0]['source_start_s']==renders[1]['source_start_s']
    assert [r['t'] for r in renders[0]['timing']]==[r['t'] for r in renders[1]['timing']]
    decoders=[]
    for item in inputs:
        p=root/item['video']; assert digest(p)==item['sha256']
        decoders.append(subprocess.Popen(['ffmpeg','-v','error','-i',str(p),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE))
    enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x900','-r','10','-i','-','-an','-c:v','libx264','-threads','4','-preset','medium','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
    font=lambda n:ImageFont.truetype(FONT,n)
    for i,row in enumerate(renders[0]['timing']):
        image=Image.new('RGB',(1920,900),'#0f1727'); d=ImageDraw.Draw(image)
        for side,decoder in enumerate(decoders):
            raw=decoder.stdout.read(1600*1000*3); assert len(raw)==1600*1000*3
            frame=Image.frombytes('RGB',(1600,1000),raw); x=side*960
            image.paste(frame.crop((16,62,976,482)),(x,56))
            image.paste(frame.crop((16,515,1584,950)).resize((960,266),Image.Resampling.LANCZOS),(x,520))
            d.text((x+16,10),['Hybrid policy','Log replay'][side],font=font(30),fill='white')
            d.text((x+16,490),'Bird’s-eye view',font=font(20),fill='white')
        d.line((960,0,960,786),fill='#8a95a5',width=2)
        for x,label,color in [(16,'Blue: recorded motion','#5ab4f0'),(480,'Orange: simulation','#f0a050'),(940,'Green R: reactive vehicle','#70ed91'),(1450,'Red: deviation > 2 m','#f06060')]:
            d.text((x,800),label,font=font(22),fill=color)
        t=row['t']; phase='Recorded motion' if t<renders[0]['handover_video_s']-1e-6 else 'Driving stack in control'
        if t>=renders[0]['event_video_s']:phase+=' · Recorded intervention time reached'
        d.text((16,850),phase,font=font(25),fill='white')
        d.text((1720,850),f't = {t:.1f} s',font=font(25),fill='white')
        enc.stdin.write(image.tobytes())
        if i==120:image.save(out.with_suffix('.jpg'))
    for decoder in decoders:
        assert not decoder.stdout.read(1); decoder.stdout.close(); assert decoder.wait()==0
    enc.stdin.close(); assert enc.wait()==0
    meta={'video':str(out.name),'sha256':digest(out),'origin':'Synchronized side-by-side composition of the existing D2 regression comparison.',
          'composition':{'frames':len(renders[0]['timing']),'fps':10,'width':1920,'height':900,'left':'Hybrid policy','right':'Log replay','camera_views_per_run':6,'all_actors':True,'source_times_identical':True,'map_bounds_identical':True},
          'inputs':{name:{k:v for k,v in item.items() if k!='video'} for name,item in zip(names,inputs)},'composer_sha256':digest(Path(__file__))}
    out.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--output',required=True);compose(p.parse_args())
