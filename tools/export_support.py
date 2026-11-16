"""Prepare display data from existing map, ambiguity and empty-road evidence.

No new simulation or outcome assessment. Coordinates are translated locally.
Usage: python3 tools/export_support.py --workspace PATH
"""
import argparse, csv, hashlib, json, math, xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
import numpy as np
from pyproj import Transformer

def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(v): return np.asarray(v).round(5).tolist()

def main(w, out):
    cross=w/'mcap2carla_research_evidence/disengagement_behaviour_studies/cross_recording'
    review=cross/'second-opinion-review-20261109'
    amb=review/'real-gaps-d1-d10-20261112/out/ambiguous_links.csv'
    row=next(r for r in csv.DictReader(amb.open()) if r['D']=='D7' and r['source'].startswith('1a5f'))
    ep=cross/'rearcone-handover-matrix-20261108'/row['clip']/'inputs/studies/relaxed_current/base-179dbe/01_source.online/tracklet_evidence.json'
    tracks={a['id']:a for a in read(ep)['tracklets']}
    links=[(row['source'],row['target'],float(row['cost']))]+[tuple(c[:3]) for c in json.loads(row['competitors_full'])]
    source=tracks[row['source']]['samples'];t0=source[-1]['t'];origin=np.array(source[-1]['position'][:2])
    v=np.mean([s['linear_velocity'][:2] for s in source if s['t']>=t0-1],axis=0)
    if np.linalg.norm(v)>=.5: angle=math.atan2(v[1],v[0])
    else:
        x,y,z,q=source[-1]['orientation'];angle=math.atan2(2*(q*z+x*y),1-2*(y*y+z*z))
    rot=np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]])
    ids=[row['source'],row['target']]+[b for a,b,c in links[1:] if a==row['source']]+[a for a,b,c in links[1:] if b==row['target']]
    colors=['#122438','#d55e00','#0072b2','#009e73','#cc79a7']
    fragments=[]
    for ident,color in zip(ids,colors):
        s=tracks[ident]['samples'];end=ident in {a for a,b,c in links}
        s=[p for p in s if p['t']>=s[-1]['t']-3] if end else [p for p in s if p['t']<=s[0]['t']+3]
        fragments.append(dict(id=ident[:4],role='source' if end else 'target',color=color,t=clean([p['t']-t0 for p in s]),xy=clean((np.array([p['position'][:2] for p in s])-origin)@rot)))
    ambiguity=dict(fragments=fragments,links=[dict(source=a[:4],target=b[:4],cost=c,gap=tracks[b]['samples'][0]['t']-tracks[a]['samples'][-1]['t']) for a,b,c in links],margin=float(row['global_margin']),source_sha256=digest(ep))

    run=w/'evaluation-rearcone-handover/results/AWE-20261113-133610'
    hand=read(run/'replay-experiment/handover.json');th=hand['actual_source_s'];org=hand['source_clock_origin_sim_s']
    driftpath=review/'ego-empty-road-20261113/data/b2_ego_deviation_AWE-20261113-133610.csv'
    drift=[r for r in csv.DictReader(l for l in driftpath.open() if not l.startswith('#')) if 9<=float(r['source_s'])<=24]
    command=[]
    for line in (run/'control-decisions.jsonl').open():
        d=json.loads(line)
        if d.get('kind')!='message' or d.get('topic')!='/control/trajectory_follower/control_cmd':continue
        d=d['data'];t=d['stamp']['sec']+d['stamp']['nanosec']*1e-9-org
        if 9<=t<=24:command.append(dict(t=t-th,speed=d['longitudinal']['velocity'],acceleration=d['longitudinal']['acceleration'],steering=d['lateral']['steering_tire_angle']))
    command.sort(key=lambda x:x['t'])
    motion=dict(t=clean([float(r['source_s'])-th for r in drift]),recorded_speed=clean([float(r['v_rec_mps']) for r in drift]),simulated_speed=clean([float(r['v_sim_mps']) for r in drift]),deviation=clean([float(r['dev_xy_m']) for r in drift]),along=clean([float(r['along_m']) for r in drift]),cross=clean([float(r['cross_m']) for r in drift]),commands=command,source_sha256=digest(driftpath),command_sha256=digest(run/'control-decisions.jsonl'))

    # CARLA lane samples are archived in the recording projection. Undo that
    # declared-frame projection to recover native OpenDRIVE XY, without a fit.
    audit=w/'perception-evaluation-audit/results/munich-map-audit'
    prov=read(audit/'provenance_vector.json')
    recording_proj='+proj=tmerc +lat_0=48.127806304395456 +lon_0=11.687878538713091 +k=1 +datum=WGS84 +units=m'
    native_proj='+proj=tmerc +lat_0=48.1399855868253 +lon_0=11.6010261850502 +k=1 +datum=WGS84 +units=m'
    to_native=Transformer.from_crs(recording_proj,native_proj,always_xy=True)
    xd=defaultdict(list)
    samplepath=audit/'tables/samples_xodr_to_l2.csv'
    for r in csv.DictReader(samplepath.open()):
        if r['type']=='Driving':xd[r['lane']].append(to_native.transform(float(r['x']),float(r['y'])))
    map_path=w/'evaluation-rearcone-handover/assets/maps/Munich_Route_1/lanelet2_map.osm'
    tree=ET.parse(map_path).getroot()
    maps=[]
    for case,rid in [('D1','20261116-004752'),('D2','20261111-131623'),('D7','20261110-212645'),('Empty road','20261113-133610')]:
        rp=w/('evaluation-rearcone-handover/results/AWE-'+rid)/'replay-experiment'
        sc=read(rp/'source.json');actor=next(a for a in sc['actors'] if a['id']=='ego')['states']
        project=Transformer.from_crs('EPSG:4326',sc['metadata']['coordinate_frame']['proj_string'],always_xy=True)
        nodes={n.get('id'):project.transform(float(n.get('lon')),float(n.get('lat'))) for n in tree.findall('node')}
        ways={a.get('id'):[nodes[n.get('ref')] for n in a.findall('nd')] for a in tree.findall('way')}
        ids={m.get('ref') for r in tree.findall('relation') if any(t.get('k')=='type' and t.get('v')=='lanelet' for t in r.findall('tag')) for m in r.findall('member') if m.get('type')=='way' and m.get('role') in ('left','right')}
        ref=np.column_stack([actor['x'],actor['y']]);origin=ref[0];lo=ref.min(0)-25;hi=ref.max(0)+25
        def local(lines):
            result=[]
            for line in lines:
                p=np.array(line)
                if len(p)>1 and np.any(np.all((p>=lo)&(p<=hi),axis=1)):result.append(clean(p-origin))
            return result
        execution=[json.loads(l) for l in (rp/'ego-execution.jsonl').open()]
        sim=[[r['xyz_carla'][0],-r['xyz_carla'][1]] for r in execution]
        maps.append(dict(case=case,lanelet=local([ways[i] for i in ids]),carla=local(xd.values()),recording=clean(ref-origin),simulation=clean(np.array(sim)-origin),bounds=clean([lo-origin,hi-origin])))
    result=dict(ambiguity=ambiguity,motion=motion,maps=maps,map_sources=dict(lanelet_sha256=digest(map_path),carla_samples_sha256=digest(samplepath),coordinate_conversion='Archived recording-frame CARLA samples converted back to native OpenDRIVE XY. Lanelet2 and recorded trajectories use the configured corrected simulation projection. CARLA y is negated to right-handed XY. No additional fitted transform.'))
    (out/'support.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n')
    print('Exported ambiguity, empty-road commands/drift and four map views')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);p.add_argument('--output',default='data');a=p.parse_args();main(Path(a.workspace),Path(a.output))
