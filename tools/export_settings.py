"""Export the archived real-example recipe without importing or executing it."""
import argparse, ast, hashlib, json, subprocess
from pathlib import Path
import yaml

def digest(data): return hashlib.sha256(data).hexdigest()

def main(workspace, output):
    archive=workspace/'mcap2carla_research_evidence/disengagement_behaviour_studies/cross_recording/rearcone-handover-matrix-20261108'
    cases={'D1':'Fahrt_10_085148_full','D6':'Fahrt_07_083124','D7':'Fahrt_09_115418'}
    configs={};versions={};hashes={}
    for name,case in cases.items():
        raw=(archive/case/'inputs/studies/relaxed_current/base-179dbe/resolved_config.yaml').read_bytes()
        config=yaml.safe_load(raw);hashes[name]=digest(raw);versions[name]=config['code_version'].split('+')[1]
        configs[name]=[s for s in config['steps'] if s['name'] in ('source.online','filter.min_evidence','associate.ours','fill.ours')]
    assert configs['D1']==configs['D6']==configs['D7']
    filenames=['association.py','pipeline.py','motion.py','observation_model.py']
    sources={}
    for version in set(versions.values()):
        sources[version]={f:subprocess.check_output(['git','-C',str(workspace/'mcap2carla-ground-plane'),'show',version+':mcap2carla/reconstruct/'+f]) for f in filenames}
    reference=sources[versions['D7']]
    assert all(source==reference for source in sources.values()),'Inspect version differences before reusing the recipe'
    tree=ast.parse(reference['motion.py'])
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='reconstruct_chain')
    defaults=next(n.value for n in ast.walk(function) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='defaults' for t in n.targets))
    motion={k.arg:ast.literal_eval(k.value) for k in defaults.keywords}
    data=dict(scope='Archived reconstruction recipe used for the D1, D6 and D7 real-gap examples.',code_versions=versions,code_sha256={f:digest(raw) for f,raw in reference.items()},configuration_sha256=hashes,configuration_steps=configs['D7'],motion_defaults=motion)
    output.write_text(json.dumps(data,indent=2)+'\n')
    print('Verified identical recipe and implementation files across D1, D6 and D7')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',required=True);p.add_argument('--output',default='data/reconstruction-settings.json');a=p.parse_args();main(Path(a.workspace),Path(a.output))
