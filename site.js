/* Local-only interactions for the research supplement. No analytics or remote requests. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const ns = 'http://www.w3.org/2000/svg';
  const colors = {linear:'#d58200', hermite:'#8c4bc4', zhu:'#b44721', ours:'#087f73'};
  const dash = {linear:'',hermite:'8 3',zhu:'3 3',ours:'10 3 2 3'};
  const el = (name, attrs={}, text) => {
    const n=document.createElementNS(ns,name);
    Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));
    if(text!==undefined)n.textContent=text;
    return n;
  };
  const fmt = (n,step) => Math.abs(n)<.0001 ? '0' : n.toFixed(step<1 ? Math.min(3,Math.ceil(-Math.log10(step))) : step<10 ? 1 : 0);
  function plot(svg, series, options) {
    svg.replaceChildren();
    const height=options.height||340, pad={l:58,r:18,t:30,b:48}, w=500-pad.l-pad.r, h=height-pad.t-pad.b;
    const valid=p=>p[1]!==null && p.every(Number.isFinite);
    const points=series.flatMap(s=>s.xy).filter(valid);
    if(!points.length)points.push([options.xrange?.[0]??0,0],[options.xrange?.[1]??1,0]);
    let x0=Math.min(...points.map(p=>p[0])),x1=Math.max(...points.map(p=>p[0]));
    let y0=Math.min(...points.map(p=>p[1])),y1=Math.max(...points.map(p=>p[1]));
    if(options.xrange)[x0,x1]=options.xrange;
    let dx=Math.max(x1-x0,.5),dy=Math.max(y1-y0,.5);x0-=dx*.07;x1+=dx*.07;y0-=dy*.1;y1+=dy*.1;
    if(options.equal){
      const unit=Math.max((x1-x0)/w,(y1-y0)/h),cx=(x0+x1)/2,cy=(y0+y1)/2;
      x0=cx-unit*w/2;x1=cx+unit*w/2;y0=cy-unit*h/2;y1=cy+unit*h/2;
    } else if(options.zero!==false){y0=Math.min(0,y0);}
    if(options.angular){const mid=(y0+y1)/2,span=Math.max(20,y1-y0);y0=Math.max(-180,mid-span/2);y1=Math.min(180,mid+span/2);}
    if(options.yrange)[y0,y1]=options.yrange;
    const X=x=>pad.l+(x-x0)/(x1-x0)*w,Y=y=>pad.t+h-(y-y0)/(y1-y0)*h;
    svg.append(el('title',{},options.title));
    if(options.gap){
      svg.append(el('rect',{x:X(0),y:pad.t,width:X(options.gap)-X(0),height:h,fill:'#eef0f2'}));
      svg.append(el('text',{x:X(options.gap/2),y:20,'text-anchor':'middle','font-size':12,fill:'#626c76'},'tracker gap'));
    }
    for(let i=0;i<=4;i++){
      const x=x0+(x1-x0)*i/4,y=y0+(y1-y0)*i/4;
      svg.append(el('line',{x1:X(x),x2:X(x),y1:pad.t,y2:pad.t+h,stroke:'#edf0f2'}));
      svg.append(el('line',{x1:pad.l,x2:pad.l+w,y1:Y(y),y2:Y(y),stroke:'#edf0f2'}));
      svg.append(el('text',{x:X(x),y:pad.t+h+20,'text-anchor':'middle','font-size':12,fill:'#53606b'},fmt(x,(x1-x0)/4)));
      svg.append(el('text',{x:pad.l-8,y:Y(y)+4,'text-anchor':'end','font-size':12,fill:'#53606b'},fmt(y,(y1-y0)/4)));
    }
    for(const s of series){
      if(!s.show)continue;
      if(s.dots){
        for(const [x,y] of s.xy.filter(valid))svg.append(el('circle',{cx:X(x),cy:Y(y),r:2.5,fill:s.hollow?'white':s.color,stroke:s.color,'stroke-width':1.2}));
      } else {
        let connected=false,previous=null;const path=[];
        for(const p of s.xy){if(!valid(p)){connected=false;continue;}const [x,y]=p;if(options.angular && previous!==null && Math.abs(y-previous)>180)connected=false;path.push((connected?'L':'M')+X(x)+','+Y(y));connected=true;previous=y;}
        svg.append(el('path',{d:path.join(' '),fill:'none',stroke:s.color,'stroke-width':s.id==='ours'?2.6:1.8,'stroke-dasharray':s.dash||''}));
      }
    }
    svg.append(el('text',{x:pad.l+w/2,y:height-8,'text-anchor':'middle','font-size':13,fill:'#243341'},options.xlabel));
    svg.append(el('text',{x:15,y:pad.t+h/2,transform:`rotate(-90 15 ${pad.t+h/2})`,'text-anchor':'middle','font-size':13,fill:'#243341'},options.ylabel));
    const cursor=el('g',{'data-cursor':'true'});svg.append(cursor);
    return {cursor,X,Y,top:pad.t,bottom:pad.t+h};
  }
  function at(s,t,key){
    if(t<s.t[0] || t>s.t.at(-1))return null;
    const j=s.t.findIndex(v=>v>=t);if(j===0 || s.t[j]===t)return s[key][j];
    const q=(t-s.t[j-1])/(s.t[j]-s.t[j-1]),a=s[key][j-1],b=s[key][j];
    if(a===null||b===null || (key==='direction' && Math.abs(b-a)>180))return null;
    return Array.isArray(a)?a.map((v,i)=>v+q*(b[i]-v)):a+q*(b-a);
  }
  // Local path tangent, not a vehicle-box yaw estimate. Do not bridge low-speed gaps.
  function motionHeading(s){
    return s.t.map((t,i)=>{
      const a=Math.max(0,i-1),b=Math.min(s.t.length-1,i+1),dt=s.t[b]-s.t[a];
      if(dt<=0)return null;
      const vx=(s.xy[b][0]-s.xy[a][0])/dt,vy=(s.xy[b][1]-s.xy[a][1])/dt;
      return s.speed[i]<.5 || Math.hypot(vx,vy)<.5 ? null : Math.atan2(vy,vx)*180/Math.PI;
    });
  }
  async function explorer(){
    const response=await fetch('data/gaps.json');if(!response.ok)throw Error('Data unavailable');
    const data=await response.json();let selected,timeRange, filtered=[], visible=12;
    const shown=new Set(Object.keys(data.methods));
    $('gap-methods').hidden=false;
    document.querySelector('#gap-explorer .explorer-controls').hidden=false;
    for(const [key,name] of Object.entries(data.methods)){
      const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.checked=true;input.value=key;
      const swatch=document.createElement('span');swatch.textContent='━';swatch.style.color=colors[key];swatch.setAttribute('aria-hidden','true');
      label.append(input,swatch,document.createTextNode(name));label.dataset.method=key;$('gap-methods').append(label);
      input.addEventListener('change',()=>{input.checked?shown.add(key):shown.delete(key);draw();});
    }
    function chooseList(){
      const kind=$('gap-kind').value,motion=$('gap-motion').value;
      $('motion-label').hidden=kind!=='benchmark';
      const list=data.cases.filter(c=>c.kind===kind && (kind!=='benchmark'||motion==='all'||c.motion===motion));
      $('gap-case').replaceChildren(...list.map(c=>{const o=document.createElement('option');o.value=c.id;o.textContent=c.title || `${c.id} · ${c.drive} · ${c.duration.toFixed(2)} s · ${c.motion.replaceAll('_',' ')}`;return o;}));
      filtered=list;visible=12;gallery();choose();
    }
    function gallery(){
      $('gallery-count').textContent=`${filtered.length} gaps · showing ${Math.min(visible,filtered.length)} · select a path to inspect it`;
      $('gap-gallery').replaceChildren(...filtered.slice(0,visible).map(c=>{
        const b=document.createElement('button');b.type='button';b.className='gap-card';b.dataset.case=c.id;b.setAttribute('aria-pressed',String(c.id===$('gap-case').value));
        const svg=el('svg',{viewBox:'0 0 220 105','aria-hidden':'true'});
        const ss=[...c.observed.map(x=>({xy:x.xy,color:'#2f6bc8'})),{xy:c.methods.ours.xy,color:colors.ours},...(c.truth?[{xy:c.truth.xy,color:'#454d55'}]:[])];
        const pts=ss.flatMap(x=>x.xy),xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);
        const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys),unit=Math.max((x1-x0)/196,(y1-y0)/70,.005),cx=(x0+x1)/2,cy=(y0+y1)/2;
        const X=x=>110+(x-cx)/unit,Y=y=>44-(y-cy)/unit;
        ss.forEach(x=>svg.append(el('path',{d:x.xy.map(([a,b],i)=>(i?'L':'M')+X(a)+','+Y(b)).join(' '),fill:'none',stroke:x.color,'stroke-width':2})));
        const bar=10**Math.floor(Math.log10(unit*50)),label=bar>=1?bar+' m':bar.toFixed(Math.max(1,-Math.floor(Math.log10(bar))))+' m';
        svg.append(el('line',{x1:12,x2:12+bar/unit,y1:96,y2:96,stroke:'#52616b','stroke-width':2}));svg.append(el('text',{x:15+bar/unit,y:99,'font-size':10,fill:'#52616b'},label));
        const title=document.createElement('strong');title.textContent=`${c.id} · ${c.duration.toFixed(2)} s`;
        const note=document.createElement('span');note.textContent=c.kind==='real'?c.drive+' · real recording':c.drive+' · '+c.motion.replaceAll('_',' ');
        b.append(svg,title,note);b.setAttribute('aria-label',`${title.textContent}, ${note.textContent}. Inspect gap`);
        b.addEventListener('click',()=>{$('gap-case').value=c.id;choose();$('gallery-browser').open=false;$('gap-detail').scrollIntoView({behavior:'smooth',block:'start'});$('gap-detail').focus({preventScroll:true});});return b;
      }));
      $('gallery-more').hidden=visible>=filtered.length;
    }
    $('gallery-more').addEventListener('click',()=>{visible+=12;gallery();});
    function choose(){
      selected=data.cases.find(c=>c.id===$('gap-case').value);
      for(const s of [...selected.observed,...Object.values(selected.methods),...(selected.truth?[selected.truth]:[])])s.direction=motionHeading(s);
      $('gap-heading').textContent=selected.title || `${selected.id} · ${selected.duration.toFixed(2)} s tracker gap`;
      document.querySelectorAll('.gap-card').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.case===selected.id)));
      $('gap-description').textContent=selected.kind==='real'?`${selected.drive} · ${selected.duration.toFixed(2)} s without tracker observations. Filled and open blue dots are the two observed fragments.`:`${selected.id} · ${selected.drive} · ${selected.duration.toFixed(2)} s gap · ${selected.motion.replaceAll('_',' ')}. Full-pipeline association: ${selected.outcome.replaceAll('_',' ')}. Correct pairing is supplied for the completion comparison.`;
      for(const label of $('gap-methods').querySelectorAll('label'))label.hidden=!(label.dataset.method in selected.methods);
      const ts=selected.observed.flatMap(s=>s.t);timeRange=[Math.min(...ts),Math.max(...ts)];
      $('gap-context').textContent=selected.kind==='real'?'Compare how the methods connect the observed fragments. The missing motion in this real recording has no ground truth; the benchmark gallery provides the accuracy comparison.':'Compare each completion with simulator ground truth. The errors above describe this gap; the completion table pools errors across all 111 gaps.';
      $('gap-metrics').replaceChildren();
      if(selected.rmse){
        const table=document.createElement('table');const cap=document.createElement('caption');cap.textContent='This gap: XY RMSE against simulator ground truth [m] ↓ (lower is better)';table.append(cap);
        const head=document.createElement('thead'),body=document.createElement('tbody'),hr=document.createElement('tr'),br=document.createElement('tr');
        for(const [k,name] of Object.entries(data.methods)){const th=document.createElement('th'),td=document.createElement('td');th.scope='col';th.textContent=name;td.textContent=selected.rmse[k].toFixed(3);hr.append(th);br.append(td);}
        head.append(hr);body.append(br);table.append(head,body);$('gap-metrics').append(table);
      }
      draw();
    }
    function draw(){
      const series=selected.observed.map((s,i)=>({id:'observed',xy:s.xy,color:'#2f6bc8',dots:true,hollow:i===1,show:true,source:s}));
      if(selected.truth)series.push({id:'truth',xy:selected.truth.xy,color:'#343c44',show:true,source:selected.truth});
      for(const [k,s] of Object.entries(selected.methods))series.push({id:k,xy:s.xy,color:colors[k],dash:dash[k],show:shown.has(k),source:s});
      plot($('gap-xy'),series,{title:'Observed fragments and completed path',xlabel:'Along-gap position [m]',ylabel:'Cross-gap position [m]'});
      plot($('gap-speed'),series.map(s=>({...s,xy:s.source.t.map((t,i)=>[t,s.source.speed[i]])})),{height:220,xrange:timeRange,title:'Speed before, inside and after the gap',gap:selected.duration,xlabel:'Time relative to gap start [s]',ylabel:'Speed [m/s]'});
      plot($('gap-direction'),series.map(s=>({...s,xy:s.source.t.map((t,i)=>[t,s.source.direction[i]])})),{height:220,angular:true,xrange:timeRange,title:'Heading: direction of motion',gap:selected.duration,xlabel:'Time relative to gap start [s]',ylabel:'Motion heading [°]'});
    }
    $('gap-kind').addEventListener('change',chooseList);$('gap-motion').addEventListener('change',chooseList);$('gap-case').addEventListener('change',choose);
    chooseList();
  }
  explorer().catch(()=>{const fallback=document.querySelector('#gap-explorer noscript');if(fallback)$('gap-detail').insertAdjacentHTML('beforeend',fallback.textContent);$('gap-description').textContent='The explorer could not load. Please use the evaluation results and static example.';});

  async function support(){
    const response=await fetch('data/support.json');if(!response.ok)throw Error('Supporting data unavailable');
    const data=await response.json(), amb=data.ambiguity;
    const ts=amb.fragments.flatMap(f=>f.t),lo=Math.min(...ts),hi=Math.max(...ts);
    $('ambiguity-time').min=Math.floor(lo*100)/100;$('ambiguity-time').max=Math.ceil(hi*100)/100;
    const timeline=$('ambiguity-timeline'),tx=t=>95+(t-lo)/(hi-lo)*635,ty=i=>35+i*42;
    timeline.append(el('title',{},'Observation times for the competing D7 fragments'));
    for(let i=0;i<=6;i++){
      const t=lo+(hi-lo)*i/6;
      timeline.append(el('line',{x1:tx(t),x2:tx(t),y1:20,y2:232,stroke:'#e5eaef'}));
      timeline.append(el('text',{x:tx(t),y:251,'font-size':12,'text-anchor':'middle'},t.toFixed(1)));
    }
    timeline.append(el('text',{x:410,y:276,'font-size':13,'text-anchor':'middle'},'Time relative to the end of source 1a5f [s]'));
    const ap=plot($('ambiguity-xy'),amb.fragments.map(f=>({id:f.id,xy:f.xy,color:f.color,dots:true,show:true})),{title:'Observed fragments in the local source frame',equal:true,xlabel:'Along-source position [m]',ylabel:'Cross-source position [m]'});
    amb.fragments.forEach((f,i)=>{
      timeline.append(el('text',{x:87,y:ty(i)+4,'font-size':12,'text-anchor':'end',fill:f.color},f.role+' '+f.id));
      timeline.append(el('line',{x1:tx(f.t[0]),x2:tx(f.t.at(-1)),y1:ty(i),y2:ty(i),stroke:f.color,'stroke-width':7,'stroke-linecap':'round'}));
    });
    for(const link of amb.links){
      const i=amb.fragments.findIndex(f=>f.id===link.source),j=amb.fragments.findIndex(f=>f.id===link.target);
      timeline.append(el('line',{x1:tx(amb.fragments[i].t.at(-1)),x2:tx(amb.fragments[j].t[0]),y1:ty(i),y2:ty(j),stroke:amb.fragments[j].color,'stroke-width':1.5,'stroke-dasharray':'4 4',opacity:.65}));
    }
    const line=el('line',{y1:18,y2:232,stroke:'#313f4b','stroke-width':1.5});timeline.append(line);
    function ambiguityTime(){
      const t=+$('ambiguity-time').value;$('ambiguity-clock').textContent=t.toFixed(2)+' s';line.setAttribute('x1',tx(t));line.setAttribute('x2',tx(t));ap.cursor.replaceChildren();const active=[];
      for(const f of amb.fragments){const p=at(f,t,'xy');if(p){active.push(f.id);ap.cursor.append(el('circle',{cx:ap.X(p[0]),cy:ap.Y(p[1]),r:6,fill:f.color,stroke:'white','stroke-width':1.5}));}}
      $('ambiguity-status').textContent=active.length?'Observed at this time: '+active.join(', ')+'.':'No fragment in this comparison is observed at this time.';
    }
    $('ambiguity-time').addEventListener('input',ambiguityTime);ambiguityTime();
    // A fixed equal-distance map scale; checkbox layers never change the extent.
    function map(){
      const c=data.maps.find(m=>m.case===$('map-case').value),svg=$('alignment-map');svg.replaceChildren();
      const [a,b]=c.bounds,w=650,h=330;
      const unit=Math.max((b[0]-a[0])/w,(b[1]-a[1])/h),cx=(a[0]+b[0])/2,cy=(a[1]+b[1])/2;
      const X=x=>415+(x-cx)/unit,Y=y=>190-(y-cy)/unit;
      svg.append(el('title',{},c.case+' map and ego-path alignment'));
      const defs=el('defs'),clip=el('clipPath',{id:'map-clip'});clip.append(el('rect',{x:90,y:25,width:w,height:h}));defs.append(clip);svg.append(defs);
      const group=el('g',{'clip-path':'url(#map-clip)'});svg.append(group);
      for(let i=0;i<=4;i++){
        const x=cx+(i/4-.5)*w*unit,y=cy+(i/4-.5)*h*unit;
        group.append(el('line',{x1:X(x),x2:X(x),y1:25,y2:355,stroke:'#edf0f2'}));group.append(el('line',{x1:90,x2:740,y1:Y(y),y2:Y(y),stroke:'#edf0f2'}));
        svg.append(el('text',{x:X(x),y:376,'font-size':13,'text-anchor':'middle'},x.toFixed(0)));
        svg.append(el('text',{x:78,y:Y(y)+4,'font-size':13,'text-anchor':'end'},y.toFixed(0)));
      }
      const shown=new Set([...$('map-layers').querySelectorAll('input:checked')].map(i=>i.value));
      const layers=[['lanelet',c.lanelet,'#697687',1,''],['carla',c.carla,'#9473b8',1.3,'5 4'],['recording',[c.recording],'#2f6bc8',3,''],['simulation',[c.simulation],'#da7d16',2,'6 3']];
      for(const [id,lines,color,width,dash] of layers)if(shown.has(id))for(const points of lines)group.append(el('path',{d:points.map(([x,y],i)=>(i?'L':'M')+X(x)+','+Y(y)).join(' '),stroke:color,'stroke-width':width,'stroke-dasharray':dash,fill:'none'}));
      svg.append(el('text',{x:415,y:405,'font-size':14,'text-anchor':'middle'},'East from the first recorded ego pose [m]'));
      svg.append(el('text',{x:20,y:190,transform:'rotate(-90 20 190)','font-size':14,'text-anchor':'middle'},'North [m]'));
    }
    $('map-case').addEventListener('change',map);$('map-layers').addEventListener('change',map);map();
    const m=data.motion;let cp,dp;
    const series=(id,t,v,color)=>({id,xy:t.map((t,i)=>[t,v[i]]),color,show:true});
    const ct=m.commands.map(c=>c.t);
    function commands(){
      const mode=$('motion-view').value;let ss,unit,legend;
      if(mode==='speed'){
        ss=[series('recorded',m.t,m.recorded_speed,'#2f6bc8'),series('simulated',m.t,m.simulated_speed,'#da7d16'),series('command',ct,m.commands.map(c=>c.speed),'#087f73')];unit='Speed [m/s]';legend='Blue: recorded speed · orange: simulated speed · green: target speed requested by the stack.';
      }else if(mode==='components'){
        ss=[series('along',m.t,m.along,'#2f6bc8'),series('cross',m.t,m.cross,'#087f73')];unit='Signed position difference [m]';legend='Blue: along-path difference (negative = simulation behind) · green: lateral difference.';
      }else{
        ss=[series('command',ct,m.commands.map(c=>c[mode]),'#087f73')];unit=mode==='acceleration'?'Commanded acceleration [m/s²]':'Steering tire angle [rad]';legend='Green: command requested by the stack. During replay the recorded motion drives the ego.';
      }
      cp=plot($('motion-command'),ss,{title:unit,zero:false,xlabel:'Time from handover [s]',ylabel:unit});
      dp=plot($('motion-drift'),[series('deviation',m.t,m.deviation,'#da7d16')],{title:'Ego position deviation',xlabel:'Time from handover [s]',ylabel:'XY position deviation [m]'});
      for(const p of [cp,dp]){p.cursor.parentNode.insertBefore(el('line',{x1:p.X(0),x2:p.X(0),y1:p.top,y2:p.bottom,stroke:'#687583','stroke-dasharray':'4 4'}),p.cursor);p.cursor.parentNode.append(el('text',{x:p.X(0)+5,y:23,'font-size':11,fill:'#53606b'},'handover'));}
      $('motion-legend').textContent=legend+' Orange in the right plot: distance from the recorded ego position.';
    }
    $('motion-view').addEventListener('change',commands);commands();
  }
  support().catch(error=>{console.error(error);$('motion-status').textContent='Interactive evidence could not load. The paper figures and descriptions remain available.';});

  const copy=document.querySelector('.copy');if(copy && navigator.clipboard){copy.hidden=false;copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText($('bibtex-entry').textContent);copy.textContent='Copied';}catch{copy.textContent='Select text to copy';}setTimeout(()=>copy.textContent='Copy',2000);});}
  // Pause videos when they leave the viewport; never autoplay on initial load.
  if('IntersectionObserver' in window){const io=new IntersectionObserver(entries=>{for(const e of entries)if(!e.isIntersecting && !document.fullscreenElement)e.target.pause();},{threshold:0});document.querySelectorAll('video').forEach(v=>io.observe(v));}
})();
