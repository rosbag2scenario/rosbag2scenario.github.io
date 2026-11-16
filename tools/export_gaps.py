"""Export existing paper-evaluation cases for the static gap explorer.

Re-evaluates only the archived lane-aware baseline to recover its coordinates;
every error must match the saved per-sample errors. No captures or new trials.
Usage: python tools/export_gaps.py --workspace PATH --output data
Requires the local evidence and evaluated implementation, numpy/scipy.
"""
import argparse, ast, csv, gzip, hashlib, json, sys
from copy import deepcopy
from pathlib import Path
import numpy as np

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(a): return np.asarray(a).round(5).tolist()
def series(times,xy,t0,origin,rot):
    times=np.asarray(times); xy=np.asarray(xy); pos=(xy-origin)@rot
    speed=np.linalg.norm(np.gradient(xy,times,axis=0),axis=1) if len(times)>1 else np.zeros(len(times))
    return {'t':clean(times-t0),'xy':clean(pos),'speed':clean(speed)}
def export(args):
    w=Path(args.workspace);o=Path(args.output);o.mkdir(exist_ok=True)
    r=w/'mcap2carla_research_evidence/disengagement_behaviour_studies/cross_recording/second-opinion-review-20261109'
    src=w/'Rosbag2Scenario_Paper-chapter4-review/Evidence/20261110/town10_labels/cases.json.gz'
    saved=r/'town10-gap-checks-20261112/out/fill_cases.json'
    rows=[x for x in json.loads(gzip.decompress(src.read_bytes())) if x.get('kind')=='natural_output_gap' and x['status']=='scored']
    scores={(x['seed'],x['tracklet']):x for x in json.loads(saved.read_text())};assert len(rows)==111
    sys.path.insert(0,str(w/'mcap2carla-ground-plane'))
    from mcap2carla.baselines.zhu2023.objects import objects_from_evidence
    from mcap2carla.baselines.zhu2023.params import Zhu2023Params
    from mcap2carla.baselines.zhu2023.true_positive import smooth
    from mcap2carla.baselines.zhu2023.false_negatives import merge,_state
    from mcap2carla.baselines.zhu2023.pipeline import _actor_entry
    from mcap2carla.reconstruct.road import RoadMap,reconstruct_route_gap
    # Use the exact archived function without importing the script's batch-writing main body.
    original=r/'town10-gap-checks-20261112/scripts/fill.py'
    node=next(n for n in ast.parse(original.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='zhu_map_frame')
    scope=locals()|{'np':np,'deepcopy':deepcopy};exec(compile(ast.Module(body=[node],type_ignores=[]),str(original),'exec'),scope)
    road=RoadMap.from_osm(w/'autoware.maps/lanelets/carla/Town10/lanelet2_map.osm')
    cases=[]; csvrows=[]
    for i,x in enumerate(rows):
        key=(x.get('source_case') or x['case'],x['tracklet']);s=scores[key]
        t0=x['last_retained_s'];tg=np.array(x['times']);truth=np.array(x['reference_xy']);pred=x['predictions']
        zhu,_,_=scope['zhu_map_frame'](deepcopy(x['parts']),tg,road)
        assert np.allclose(np.linalg.norm(zhu-truth,axis=1),s['errors']['zhu_lane'],atol=1e-7),key
        origin=np.array(x['parts'][0]['samples'][-1]['position'][:2]);end=np.array(x['parts'][1]['samples'][0]['position'][:2]);direction=end-origin
        if np.linalg.norm(direction)<0.5:direction=np.array([1.,0.])
        direction/=np.linalg.norm(direction);rot=np.column_stack([direction,[-direction[1],direction[0]]])
        observed=[]
        for part in x['parts']:
            pts=part['samples'];a=series([v['t'] for v in pts],[v['position'][:2] for v in pts],t0,origin,rot)
            a['speed']=clean([np.linalg.norm(v['linear_velocity'][:2]) for v in pts]);observed.append(a)
        methods={k:series(tg,xy,t0,origin,rot) for k,xy in [('linear',pred['linear']),('hermite',pred['raw_hermite']),('zhu',zhu),('ours',pred['joint'])]}
        errors={k:s['rmse'][v] for k,v in [('linear','linear'),('hermite','raw_hermite'),('zhu','zhu_lane'),('ours','joint')]}
        cid=f'T{i+1:03d}'
        cases.append({'id':cid,'kind':'benchmark','drive':key[0],'duration':x['first_return_s']-t0,'motion':s['motion'],'outcome':s['e2_ours'],'observed':observed,'truth':series(tg,truth,t0,origin,rot),'methods':methods,'rmse':errors})
        csvrows.append({'case':cid,'drive':key[0],'gap_s':x['gap_s'],'motion':s['motion'],'association':s['e2_ours'],'samples':s['n'],**{k+'_rmse_m':v for k,v in errors.items()}})
    # Real examples: stored exported reconstructions and observed fragments, no invented ground truth.
    p=r/'real-gaps-d1-d10-20261112/out';mc=json.loads((p/'method_curves.json').read_text());gs=json.loads((p/'gap_series_cache.json').read_text())
    choices=[('D7','1994','Pulling away: the paper’s 3.1 s gap'),('D7','bc25','A longer gap while pulling away'),('D1','3429','A moving vehicle on a curved path'),('D6',None,'Motion across a short tracker gap')]
    for drive,prefix,title in choices:
        row=next(x for x in mc['rows'] if x['D']==drive and (prefix is None or x['source_fragment'].startswith(prefix)) and x['predict_error'] is None)
        key='|'.join([row['D'],row['actor_id'],row['source_fragment'],row['target_fragment']]);cur=mc['curves'][key];s=gs[key]
        fa=s['fragments'][row['source_fragment']];fb=s['fragments'][row['target_fragment']];t0=fa[-1]['t'];t1=fb[0]['t'];origin=np.array([fa[-1]['x'],fa[-1]['y']]);d=np.array([fb[0]['x'],fb[0]['y']])-origin;d/=np.linalg.norm(d);rot=np.column_stack([d,[-d[1],d[0]]])
        obs=[]
        for f in [fa,fb]:
            f=[v for v in f if t0-3<=v['t']<=t1+3];a=series([v['t'] for v in f],[[v['x'],v['y']] for v in f],t0,origin,rot);a['speed']=clean([v['v'] for v in f]);obs.append(a)
        methods={k:series(cur['times'],cur[m],t0,origin,rot) for k,m in [('linear','linear'),('hermite','raw_hermite'),('zhu','zhu_component'),('ours','ours')]}
        cases.append({'id':f'R{len(cases)-110:02d}','kind':'real','drive':drive,'title':title,'duration':t1-t0,'observed':obs,'methods':methods,'truth':None,'rmse':None})
    out={'schema':1,'methods':{'linear':'Constant velocity','hermite':'Hermite','zhu':'Zhu-inspired','ours':'End-aware (ours)'},'cases':cases}
    (o/'gaps.json').write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')
    with (o/'gap-scores.csv').open('w') as f:
        c=csv.DictWriter(f,fieldnames=list(csvrows[0]),lineterminator='\n');c.writeheader();c.writerows(csvrows)
    summary={k:float(np.sqrt(np.mean([e*e for s in scores.values() for e in s['errors'][m]]))) for k,m in [('linear','linear'),('hermite','raw_hermite'),('zhu','zhu_lane'),('ours','joint')]}
    assert [round(v,2) for v in summary.values()]==[1.,1.21,1.17,.88]
    (o/'gap-provenance.json').write_text(json.dumps({'population':'111 scored natural output gaps; correct fragment pairs supplied for completion','benchmark_sources':{'cases_sha256':sha(src),'scores_sha256':sha(saved),'lane_baseline_function_sha256':sha(original)},'real_sources':{'method_curves_sha256':sha(p/'method_curves.json'),'fragment_series_sha256':sha(p/'gap_series_cache.json')},'coordinate_system':'Each gap translated and rotated locally; physical distances preserved.','speed':'Method speed is a finite difference of exported XY samples; observed speed is tracker-reported.','real_examples_note':'Illustrative continuity examples without ground truth; no error ranking. Real examples use the archived Cartesian Zhu-inspired completion; the benchmark uses the lane-aware configuration from Table II.','pooled_rmse_m':summary,'all_cases_included':111,'real_examples':4},indent=2)+'\n')
    print('Exported',len(cases),'cases;',summary)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);p.add_argument('--output',default='data');export(p.parse_args())
