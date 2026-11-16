"""Export the standard four motion plots from saved stack comparisons."""
import argparse,hashlib,json,math,os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/rosbag-mpl')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BLUE='#1760dc'; ORANGE='#f47700'; GREY='#7c8aa0'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def derivative(t,v):
    # Same five-sample moving average and gradient as build_artifact.py.
    v=np.asarray([np.nan if q is None else q for q in v],float);ok=np.isfinite(v)
    if ok.sum()<7:return np.full(len(v),np.nan)
    vv=np.interp(t,np.asarray(t)[ok],v[ok]);a=np.gradient(np.convolve(vv,np.ones(5)/5,mode='same'),t)
    a[~ok]=np.nan
    # Do not expose zero-padding artifacts at the boundaries of valid support.
    indices=np.flatnonzero(ok);a[indices[:3]]=np.nan;a[indices[-3:]]=np.nan
    return a

def clean(a):return [round(float(v),5) if np.isfinite(v) else None for v in a]
def export(a):
    root=Path(a.compare_dir);site=Path(a.site);dest=site/'fig/motion';dest.mkdir(exist_ok=True)
    specs=[('d1','D1',Path(a.d1_comparison)),('d2-hybrid','D2 · Hybrid traffic',root/'D2_H2v2AL5PLP5SCG_131623.json'),('d2-replay','D2 · Log replay',root/'D2_H2v2AL5PLP5SCKG_132245.json'),('d3','D3',root/'D3_H2v2AL5SSXPG4G_115708.json'),('d6','D6',root/'D6_H2v2ALG_201649.json'),('d7','D7',root/'D7_H2v2AL5G_212645.json'),('d8','D8',root/'D8_H2v2ALG_203002.json')]
    output={}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','svg.hashsalt':'rosbag-motion','axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False})
    for key,title,p in specs:
        c=json.loads(p.read_text());m=c['motion'];t=np.asarray(m['t']);th=c['motion_summary']['t_h'];td=c['motion_summary']['t_d']
        vr=np.asarray(m['v_real'],float);vs=np.asarray(m['v_sim'],float);ds=np.asarray(m['s_sim'],float)-np.asarray(m['s_real'],float)
        ar=np.asarray(c['control']['a_cmd_real'],float);ass=np.asarray(c['control']['a_cmd_sim'],float)
        assert c['control']['t']==m['t']
        dr=derivative(t,vr);dss=derivative(t,vs)
        finite=np.isfinite(vr)&np.isfinite(vs);end=min(c['window'][1],td+10);start=max(c['window'][0],th-4)
        probe=lambda v:float(np.interp(td,t,v))
        rr,ss,dd=probe(vr),probe(vs),probe(ds)
        summary=f'At the recorded takeover: real ego {rr:.2f} m/s; simulated ego {ss:.2f} m/s. The simulated ego is {abs(dd):.1f} m '+('behind' if dd<0 else 'ahead of')+' the recorded ego along its path.'
        charts=[('Speed','Speed [m/s]',[(vr,BLUE),(vs,ORANGE)],'Vehicle speed on both sides.'),('Position along the recorded path','Simulation − recording [m]',[(ds,ORANGE)],'Positive: simulated ego ahead.'),('Commanded acceleration','Acceleration [m/s²]',[(ar,BLUE),(ass,ORANGE)],'Acceleration requested by each stack.'),('Achieved acceleration','Acceleration [m/s²]',[(dr,BLUE),(dss,ORANGE)],'Smoothed rate of change of speed.')]
        fig,axes=plt.subplots(2,2,figsize=(14,8.2),dpi=160)
        for ax,(name,unit,series,caption) in zip(axes.flat,charts):
            for values,color in series:ax.plot(t,values,color=color,lw=1.65)
            ax.set_xlim(start,end);ax.set_xlabel('Time in the recording [s]');ax.set_ylabel(unit)
            ax.set_title(name,loc='left',fontweight='bold',pad=25)
            ax.text(0,1.035,caption,transform=ax.transAxes,color='#57657a',fontsize=10)
            ax.grid(axis='y',color='#e5eaf1');ax.set_axisbelow(True)
            ax.tick_params(axis='both',length=0,pad=6,labelcolor='#526078')
            visible=np.concatenate([v[(t>=start)&(t<=end)] for v,_ in series]);visible=visible[np.isfinite(visible)]
            lo=min(0,float(visible.min()));hi=max(0,float(visible.max()));pad=max(.08,(hi-lo)*.1);ax.set_ylim(lo-pad,hi+pad)
            for when,label in [(th,'handover'),(td,'takeover')]:
                ax.axvline(when,color=GREY,lw=1,ls='--');ax.text(when+.08,.96,label,transform=ax.get_xaxis_transform(),color='#58657b',fontsize=9,va='top')
        fig.legend([plt.Line2D([0],[0],color=BLUE,lw=2),plt.Line2D([0],[0],color=ORANGE,lw=2)],['Real recording','Simulation'],loc='upper center',ncol=2,frameon=False,bbox_to_anchor=(.5,1))
        fig.subplots_adjust(left=.075,right=.985,top=.88,bottom=.08,hspace=.5,wspace=.22)
        fig.canvas.draw()
        for ax,suffix in zip(axes.flat,['speed','position','command','achieved']):
            bbox=ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted()).expanded(1.035,1.06)
            fig.savefig(dest/(key+'-'+suffix+'.svg'),bbox_inches=bbox,metadata={'Date':None,'Creator':'Rosbag2Scenario'})
        if key=='d3':fig.savefig('/tmp/rosbag-standard-render/d3-motion.png')
        plt.close(fig)
        output[key]=dict(title=title,run=c['run'],source_sha256=digest(p),t_h=th,t_d=td,window=[start,end],summary=summary,takeover=dict(real_speed=rr,sim_speed=ss,along_path_difference=dd),series=dict(t=clean(t),v_real=clean(vr),v_sim=clean(vs),ds=clean(ds),a_cmd_real=clean(ar),a_cmd_sim=clean(ass),a_real=clean(dr),a_sim=clean(dss)))
    (site/'data/encounter-motion.json').write_text(json.dumps(output,separators=(',',':'),allow_nan=False)+'\n')
    print('Exported',len(output),'four-panel comparisons; D3:',output['d3']['summary'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--compare-dir',required=True);p.add_argument('--d1-comparison',required=True);p.add_argument('--site',default='.');export(p.parse_args())
