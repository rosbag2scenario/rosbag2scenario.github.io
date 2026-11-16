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
assert len(h.video_sources)==len(set(h.video_sources))==8
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
with (ROOT/'data/disengagements.csv').open() as f:events=list(csv.DictReader(f))
assert len(events)==9 and sum(r['outcome']=='reproduced' for r in events)==5
for e in events:
    row=next(r for r in h.rows if r and r[0]==e['id'])
    assert [float(v) for v in row[2:6]]==[float(e[k]) for k in ['cone','coverage_percent','within_2m_percent','ego_error_m']]
    assert row[6]==('reproduced' if e['outcome']=='reproduced' else 'diverged')
media=json.loads((ROOT/'data/media-provenance.json').read_text())
for name,m in media.items():
    if 'render' in m:
        assert m['render']['all_actors'] and m['render']['cone_overlay'] is False
        assert m['render']['frames']==len(m['render']['timing'])
    assert hashlib.sha256((ROOT/m['video']).read_bytes()).hexdigest()==m['sha256'],name
assert media['d1-submission']['sha256']==media['d1-submission']['source_sha256']
a,b=[media[n]['render'] for n in ['d2-regression-hybrid','d2-regression-logreplay']]
assert a['frames']==b['frames']==222
assert a['map_bounds']==b['map_bounds'] and a['source_start_s']==b['source_start_s']
assert [r['t'] for r in a['timing']]==[r['t'] for r in b['timing']]
assert all(media[n]['render']['all_actors'] for n in ['d2-regression-hybrid','d2-regression-logreplay','d7-diverged'])
assert all(media[n]['render']['cone_overlay'] is False for n in ['d2-regression-hybrid','d2-regression-logreplay','d7-diverged'])
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
