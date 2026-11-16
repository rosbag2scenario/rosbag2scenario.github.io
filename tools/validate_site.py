"""Check public assets, data integrity and agreement with the submitted tables."""
import csv,hashlib,json,math,re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1]
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=[];self.rows=[];self.row=None;self.cell=None;self.video_sources=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='source' and a.get('type')=='video/mp4':self.video_sources.append(a['src'])
        if 'id' in a:self.ids.append(a['id'])
        for k in ['src','href','poster']:
            if k in a:self.links.append(a[k])
        if tag=='tr':self.row=[]
        if tag in ['td','th']:self.cell=''
    def handle_data(self,s):
        if self.cell is not None:self.cell+=s
    def handle_endtag(self,tag):
        if tag in ['td','th'] and self.row is not None:self.row.append(self.cell.strip());self.cell=None
        if tag=='tr':self.rows.append(self.row);self.row=None
h=Links();h.feed((ROOT/'index.html').read_text());assert len(h.ids)==len(set(h.ids))
assert len(h.video_sources)==len(set(h.video_sources))==7
assert h.video_sources.count('media/d1-submission.mp4')==1
for link in h.links:
    u=urlsplit(link)
    if u.scheme:assert u.scheme=='data',f'Unexpected external resource: {link}';continue
    if u.path:assert (ROOT/unquote(u.path)).is_file(),link
    elif u.fragment:assert u.fragment in h.ids,link
x=json.loads((ROOT/'data/gaps.json').read_text());bench=[r for r in x['cases'] if r['kind']=='benchmark'];real=[r for r in x['cases'] if r['kind']=='real']
assert len(bench)==111 and len(real)==4
assert sum(r['motion']=='moving' for r in bench)==56
methods={'linear':1.00,'hermite':1.21,'zhu':1.17,'ours':.88};tot={k:[] for k in methods}
for c in x['cases']:
    for s in [*c['observed'],*c['methods'].values()]+([c['truth']] if c['truth'] else []):
        assert len(s['t'])==len(s['xy'])==len(s['speed'])
        assert all(a<b for a,b in zip(s['t'],s['t'][1:]))
        assert all(math.isfinite(v) for p in s['xy'] for v in p)
    if c['kind']=='benchmark':
        for k,s in c['methods'].items():
            assert s['t']==c['truth']['t']
            squared=[sum((a-b)**2 for a,b in zip(p,q)) for p,q in zip(s['xy'],c['truth']['xy'])]
            assert abs(math.sqrt(sum(squared)/len(squared))-c['rmse'][k])<2e-5,(c['id'],k)
            tot[k].extend(squared)
    else:
        assert c['truth'] is None and c['rmse'] is None
        assert 'zhu' in c['methods']
assert len(tot['ours'])==3296
for k,v in methods.items():assert round(math.sqrt(sum(tot[k])/len(tot[k])),2)==v
association=json.loads((ROOT/'data/association.json').read_text())
assert association['population']['all']==111 and association['population']['moving']==56
assert len(association['rows'])==4
for result in association['rows']:
    label=f"Zhu et al., {result['gate_s']:g} s / {result['dist_m']:g} m"
    row=next(r for r in h.rows if r and r[0].replace('\u00a0',' ')==label)
    assert [int(v) for v in row[1:]]==[result['rejoined'],result['moving'],result['links']['wrong']]
with (ROOT/'data/disengagements.csv').open() as f:events=list(csv.DictReader(f))
assert len(events)==9 and sum(r['outcome']=='reproduced' for r in events)==5
for e in events:
    row=next(r for r in h.rows if r and r[0]==e['id'])
    assert [float(v) for v in row[2:6]]==[float(e[k]) for k in ['cone','coverage_percent','within_2m_percent','ego_error_m']]
    assert row[6]==('reproduced' if e['outcome']=='reproduced' else 'diverged')
media=json.loads((ROOT/'data/media-provenance.json').read_text())
for name,m in media.items():
    if 'render' in m:
        assert m['render']['all_actors'] and m['render']['cone_overlay'] is True
        assert m['render']['frames']==len(m['render']['timing'])
    assert hashlib.sha256((ROOT/m['video']).read_bytes()).hexdigest()==m['sha256'],name
d1=media['d1-submission']
assert d1['source_sha256']=='de98fe3d3ec9b6f275bdf79919630516592a126a35ae3a62e11761215f51d84d'
assert d1['layout_edit']['timing_unchanged'] and d1['layout_edit']['frames']==172
assert float(d1['encoding']['format']['duration'])==17.2
assert (ROOT/d1['layout_edit']['filter']).is_file()
comparison=media['d2-comparison'];a,b=[comparison['inputs'][n]['render'] for n in ['d2-regression-hybrid','d2-regression-logreplay']]
assert comparison['composition']['frames']==222 and comparison['composition']['all_actors']
assert comparison['encoding']['streams'][0]['width']==3840
assert comparison['encoding']['streams'][0]['height']==1470
assert float(comparison['encoding']['format']['duration'])==22.2
assert a['frames']==b['frames']==222
assert a['map_bounds_by_frame']==b['map_bounds_by_frame'] and a['source_start_s']==b['source_start_s']
assert [r['t'] for r in a['timing']]==[r['t'] for r in b['timing']]
assert all(r['all_actors'] for r in [a,b])
assert a['cone_overlay'] is True and b['cone_overlay'] is False
for render in [a,b,*[m['render'] for m in media.values() if 'render' in m]]:
    assert render['camera_rows']['gutter_removed']
    assert render['cone_visualization']['opening_deg']==90 and render['cone_visualization']['range_m']==100
    assert render['status_position'][1]<1300 and render['clock_position'][1]<1300
assert all(k not in h.ids for k in ['gap-time','motion-time','map-zoom','map-position','compare-play','comparison-dialog'])
support=json.loads((ROOT/'data/support.json').read_text())
assert len(support['maps'])==4 and len(support['ambiguity']['fragments'])==5
assert support['ambiguity']['margin']==.7748
motion=support['motion']
for t,value in [(5,.99222),(10,1.78082)]:
    assert motion['deviation'][motion['t'].index(t)]==value
assert all(a['t']<=b['t'] for a,b in zip(motion['commands'],motion['commands'][1:]))
assert 'equal-scale' not in h.ids and 'download-case' not in h.ids
for p in [ROOT/'index.html',ROOT/'site.js',*list((ROOT/'data').iterdir())]:
    if p.is_file():assert not re.search(r'/home/|/media/|/tmp/|file://',p.read_text()),p
print('PASS: local links, 111 benchmark cases, 4 real examples, 3296 timestamps, published RMSEs, all nine event rows, media hashes, public-path scan.')

motion_cases=json.loads((ROOT/'data/encounter-motion.json').read_text())
assert len(motion_cases)==7
assert motion_cases['d3']['run']==media['d3-reproduced']['render']['run']=='AWE-20261111-115708'
assert round(motion_cases['d3']['takeover']['real_speed'],2)==2.52
assert round(motion_cases['d3']['takeover']['sim_speed'],2)==2.51
assert round(motion_cases['d3']['takeover']['along_path_difference'],1)==-3.0
for case,m in motion_cases.items():
    for suffix in ['speed','position','command','achieved']:assert (ROOT/f'fig/motion/{case}-{suffix}.svg').exists()
    assert len(m['series']['t'])==len(m['series']['a_cmd_sim'])==len(m['series']['a_sim'])
    assert m['t_h']<m['t_d']
for case,name in [('d6','d6-reproduced'),('d7','d7-diverged'),('d8','d8-diverged')]:
    assert motion_cases[case]['run']==media[name]['render']['run']
assert motion_cases['d1']['run']=='AWE-20261116-004752'
for case,name in [('d2-hybrid','d2-regression-hybrid'),('d2-replay','d2-regression-logreplay')]:
    assert motion_cases[case]['run']==comparison['inputs'][name]['render']['run']
print('PASS: seven case-matched four-panel plot sets, requested D3 run and screenshot values, usual BEV renderer and aligned D2 frames.')
