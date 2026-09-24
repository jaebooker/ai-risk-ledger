"use strict";
(function(){
  // Point the footer link at this repo when served from GitHub Pages (user.github.io/repo).
  var a=document.getElementById('repo-link'); if(!a) return;
  var m=location.hostname.match(/^([^.]+)\.github\.io$/); var seg=location.pathname.split('/').filter(Boolean)[0];
  if(m && seg) a.href='https://github.com/'+m[1]+'/'+seg; else a.removeAttribute('href');
})();

function start(D){
  var SRC = {
    metaculus:{name:'Metaculus'}, manifold:{name:'Manifold'}, polymarket:{name:'Polymarket'},
    kalshi:{name:'Kalshi'}, derived:{name:'Implied'}
  };
  var CATS = [
    ['all','All'],['catastrophe','Catastrophe & extinction'],['misuse','Misuse & incidents'],
    ['governance','Governance & labs'],['context','Capability context']
  ];
  var CATNAME = {}; CATS.forEach(function(c){CATNAME[c[0]]=c[1]});
  var state = {cat:'all', off:{}, sort:'group'};
  try{ var s = JSON.parse(localStorage.getItem('ledger-ui')||'null'); if(s){ state.cat=s.cat||'all'; state.sort=s.sort||'group'; state.off=s.off||{}; } }catch(e){}
  function save(){ try{ localStorage.setItem('ledger-ui', JSON.stringify(state)); }catch(e){} }

  var byId = {}; D.items.forEach(function(it){ byId[it.id]=it; });
  var tip = document.getElementById('tip');

  function pct(p){
    if(p==null||isNaN(p)) return '—';
    var v = p*100;
    if(v>=99.95) return (v>=99.99?'99.9+':v.toFixed(1))+'%';
    if(v>=10) return v.toFixed(0)+'%';
    if(v>=1) return v.toFixed(1)+'%';
    if(v>=0.1) return v.toFixed(2)+'%';
    return '<'+'0.1%';
  }
  function part(it){
    if(it.n==null) return '—';
    if(it.nu==='volume'){
      var n=it.n; return '$'+(n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?(n/1e3).toFixed(n>=1e5?0:1)+'k':Math.round(n));
    }
    var s = it.n>=1000?(it.n/1000).toFixed(1)+'k':String(it.n);
    return s+' '+(it.nu==='traders'?'traders':'fcst');
  }
  function esc(s){ return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]}); }
  function chip(src){ return '<span class="chip"><i style="background:var(--s-'+src+')"></i>'+esc(SRC[src]?SRC[src].name:src)+'</span>'; }

  // stamp
  var dt = new Date(D.updated+'T12:00:00Z');
  document.getElementById('stamp').textContent = dt.toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'});

  // tiles
  var st = D.studies;
  var xs = st.filter(function(s){return s.name==='XPT: superforecasters' && /extinction/.test(s.what)})[0];
  var xe = st.filter(function(s){return s.name==='XPT: domain experts' && /extinction/.test(s.what)})[0];
  var airo = st.filter(function(s){return /AIRO/.test(s.name) && /2050/.test(s.what)})[0];
  var T = [
    {lab:'Metaculus, implied', big:pct(byId['mc-implied-cat'].p), cap:'AI kills 10% or more of humanity by 2100', src:'derived'},
    {lab:'Manifold', big:pct(byId['mf-wipe-2100'].p), cap:'AI wipes out humanity by 2100 ('+byId['mf-wipe-2100'].n+' traders)', src:'manifold'},
    {lab:'XPT tournament, 2022', big:pct(xs.p)+' <small>vs</small> '+pct(xe.p), cap:'AI extinction by 2100: superforecasters vs domain experts', src:'expert', srcName:'Tournament'},
    {lab:'FRI AIRO, Sep 2026', big:pct(airo.p), cap:'AI catastrophe by 2050, estimated by an ensemble of frontier models', src:'expert', srcName:'Model ensemble'}
  ];
  document.getElementById('tiles').innerHTML = T.map(function(t){
    return '<div class="tile"><div class="lab">'+esc(t.lab)+'</div><div class="big">'+t.big+'</div><div class="cap">'+esc(t.cap)+'</div><div class="src"><span class="chip"><i style="background:var(--s-'+t.src+')"></i>'+esc(t.srcName||SRC[t.src].name)+'</span></div></div>';
  }).join('');

  // controls
  var catsEl = document.getElementById('cats');
  catsEl.innerHTML = CATS.map(function(c){ return '<button type="button" id="cat-'+c[0]+'" data-cat="'+c[0]+'" aria-pressed="'+(state.cat===c[0])+'">'+esc(c[1])+'</button>'; }).join('');
  catsEl.addEventListener('click', function(e){ var b=e.target.closest('button'); if(!b) return; state.cat=b.dataset.cat; save(); syncControls(); renderTable(); });
  var srcsEl = document.getElementById('srcs');
  srcsEl.innerHTML = Object.keys(SRC).map(function(k){ return '<button type="button" class="src-toggle" id="src-'+k+'" data-src="'+k+'" aria-pressed="'+(!state.off[k])+'"><i style="background:var(--s-'+k+')"></i>'+esc(SRC[k].name)+'</button>'; }).join('');
  srcsEl.addEventListener('click', function(e){ var b=e.target.closest('button'); if(!b) return; var k=b.dataset.src; state.off[k]=!state.off[k]; save(); syncControls(); renderTable(); });
  var sortEl = document.getElementById('sort'); sortEl.value = state.sort;
  sortEl.addEventListener('change', function(){ state.sort=sortEl.value; save(); renderTable(); });
  function syncControls(){
    catsEl.querySelectorAll('button').forEach(function(b){ b.setAttribute('aria-pressed', String(b.dataset.cat===state.cat)); });
    srcsEl.querySelectorAll('button').forEach(function(b){ b.setAttribute('aria-pressed', String(!state.off[b.dataset.src])); });
  }

  function tms(d){ return Date.parse(d+'T00:00:00Z'); }
  var DAY=86400000;
  function valAt(h,t){ var v=null; for(var i=0;i<h.length;i++){ if(tms(h[i][0])<=t) v=h[i][1]; else break; } return v; }
  function change(it,days){
    var h=it.hist; if(!h||h.length<2) return null;
    var tEnd=tms(h[h.length-1][0]), t0=tEnd-days*DAY;
    if(tms(h[0][0])>t0) return null;
    var v0=valAt(h,t0); if(v0==null) return null;
    return it.p - v0;
  }
  function deltaHtml(d){
    if(d==null) return '<span class="delta flat" title="Less than 30 days of history">new</span>';
    var pts=d*100, a=Math.abs(pts);
    if(a<0.5) return '<span class="delta flat">0.0</span>';
    return '<span class="delta '+(pts>0?'up':'down')+'" title="Change over 30 days, percentage points">'+(pts>0?'+':'−')+a.toFixed(a>=10?0:1)+' pts</span>';
  }
  function spark(h){
    if(!h || h.length<2) return '<div class="spark-none">1 reading</div>';
    var w=96,ht=26,pad=3;
    var tEnd=tms(h[h.length-1][0]), t0=Math.max(tms(h[0][0]), tEnd-365*DAY);
    var hh=h.filter(function(x){return tms(x[0])>=t0}); var pre=valAt(h,t0); if(pre!=null && (!hh.length||tms(hh[0][0])>t0)) hh.unshift([new Date(t0).toISOString().slice(0,10),pre]);
    if(hh.length<2) hh=h.slice(-2);
    t0=tms(hh[0][0]);
    var ps=hh.map(function(x){return x[1]});
    var mn=Math.min.apply(null,ps), mx=Math.max.apply(null,ps);
    if(mx-mn<0.04){ var mid=(mx+mn)/2; mn=Math.max(0,mid-0.02); mx=mid+0.02; }
    var span=Math.max(1,tEnd-t0);
    var pts=hh.map(function(x){ var X=pad+(w-2*pad)*(tms(x[0])-t0)/span; var Y=pad+(ht-2*pad)*(1-(x[1]-mn)/(mx-mn)); return [X,Y]; });
    var d='M'+pts.map(function(p){return p[0].toFixed(1)+' '+p[1].toFixed(1)}).join(' L');
    var last=pts[pts.length-1];
    var lbl='Past year: from '+pct(hh[0][1])+' to '+pct(hh[hh.length-1][1]);
    return '<svg class="spark" viewBox="0 0 '+w+' '+ht+'" role="img" aria-label="'+esc(lbl)+'"><title>'+esc(lbl)+'</title><path d="'+d+'"/><circle cx="'+last[0].toFixed(1)+'" cy="'+last[1].toFixed(1)+'" r="2.5"/></svg>';
  }

  // Generic time-series chart. series: [{name,color,dash,h}]
  var MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  function fmtDate(t,long){ var d=new Date(t); return (long?d.getUTCDate()+' ':'')+MON[d.getUTCMonth()]+' '+d.getUTCFullYear(); }
  function lineChart(host, series, rangeDays, H){
    H=H||260;
    var W=Math.max(300, host.clientWidth||640);
    var L=40,R=64,T=12,B=26;
    var tEnd=0,tStart=Infinity;
    series.forEach(function(s){ if(s.h.length){ tEnd=Math.max(tEnd,tms(s.h[s.h.length-1][0])); tStart=Math.min(tStart,tms(s.h[0][0])); } });
    if(rangeDays) tStart=Math.max(tStart,tEnd-rangeDays*DAY);
    var S=series.map(function(s){
      var h=s.h.filter(function(x){return tms(x[0])>=tStart});
      var pre=valAt(s.h,tStart); if(pre!=null && (!h.length||tms(h[0][0])>tStart)) h.unshift([new Date(tStart).toISOString().slice(0,10),pre]);
      return {name:s.name,color:s.color,dash:s.dash,h:h};
    }).filter(function(s){return s.h.length});
    var mx=0; S.forEach(function(s){ s.h.forEach(function(x){ mx=Math.max(mx,x[1]); }); });
    var steps=[0.01,0.02,0.05,0.1,0.2,0.25,0.5,0.6,0.8,1]; var top=1;
    for(var i=0;i<steps.length;i++){ if(mx*1.12<=steps[i]){ top=steps[i]; break; } }
    var tickStep = top<=0.02?0.005: top<=0.05?0.01: top<=0.1?0.02: top<=0.25?0.05: top<=0.6?0.1:0.2;
    function X(t){ return L+(W-L-R)*(t-tStart)/Math.max(1,tEnd-tStart); }
    function Y(p){ return T+(H-T-B)*(1-p/top); }
    var g='<g class="grid">';
    for(var v=0; v<=top+1e-9; v+=tickStep){ var y=Y(v).toFixed(1); g+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+y+'" y2="'+y+'"/><text x="'+(L-6)+'" y="'+(+y+4)+'" text-anchor="end">'+(Math.round(v*1000)/10)+'%</text>'; }
    g+='</g>';
    // x ticks
    var spanD=(tEnd-tStart)/DAY, xs='<g class="xax"><line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(0)+'" y2="'+Y(0)+'"/>';
    var d0=new Date(tStart), yr=d0.getUTCFullYear(), mo=d0.getUTCMonth();
    var every = spanD>1500?12: spanD>700?6: spanD>300?3: spanD>90?1:0;
    if(every){
      var m=Math.ceil((mo+1)/every)*every; var y2=yr; while(m>=12){m-=12;y2++;}
      for(;;){ var t=Date.UTC(y2,m,1); if(t>tEnd) break; if(t>=tStart){ var lx=X(t); var lab= every===12? String(y2) : MON[m]+(m===0||every>=3?' '+String(y2).slice(2):''); xs+='<text x="'+lx.toFixed(1)+'" y="'+(H-6)+'" text-anchor="middle">'+lab+'</text>'; } m+=every; while(m>=12){m-=12;y2++;} }
    } else {
      for(var t2=tStart; t2<=tEnd; t2+=7*DAY){ xs+='<text x="'+X(t2).toFixed(1)+'" y="'+(H-6)+'" text-anchor="middle">'+(new Date(t2).getUTCDate())+' '+MON[new Date(t2).getUTCMonth()]+'</text>'; }
    }
    xs+='</g>';
    var body='';
    var ends=[];
    S.forEach(function(s){
      var d=''; s.h.forEach(function(x,i){ var px=X(tms(x[0])), py=Y(x[1]); if(i===0) d+='M'+px.toFixed(1)+' '+py.toFixed(1); else { var prevY=Y(s.h[i-1][1]); d+=' L'+px.toFixed(1)+' '+prevY.toFixed(1)+' L'+px.toFixed(1)+' '+py.toFixed(1); } });
      var lx=X(tEnd), ly=Y(s.h[s.h.length-1][1]);
      d+=' L'+lx.toFixed(1)+' '+ly.toFixed(1);
      if(S.length===1) body+='<path class="area" style="fill:'+s.color+'" d="'+d+' L'+lx.toFixed(1)+' '+Y(0)+' L'+X(tms(s.h[0][0])).toFixed(1)+' '+Y(0)+' Z"/>';
      body+='<path class="ln" style="stroke:'+s.color+'"'+(s.dash?' stroke-dasharray="6 4"':'')+' d="'+d+'"/>';
      body+='<circle class="hdot" cx="'+lx.toFixed(1)+'" cy="'+ly.toFixed(1)+'" r="4" style="fill:'+s.color+'"/>';
      ends.push({y:ly, txt:pct(s.h[s.h.length-1][1])});
    });
    // end labels, nudged apart
    ends.sort(function(a,b){return a.y-b.y}); for(var k=1;k<ends.length;k++){ if(ends[k].y-ends[k-1].y<14) ends[k].y=ends[k-1].y+14; }
    ends.forEach(function(e){ body+='<text class="endlab" x="'+(W-R+10)+'" y="'+(e.y+4).toFixed(1)+'" fill="var(--ink)">'+e.txt+'</text>'; });
    var svg='<svg viewBox="0 0 '+W+' '+H+'" width="'+W+'" height="'+H+'" role="img" aria-label="'+esc(S.map(function(s){return s.name+' now '+pct(s.h[s.h.length-1][1])}).join('; '))+'">'+g+xs+body+'<g class="hov" style="display:none"><line class="xh" y1="'+T+'" y2="'+Y(0)+'"/></g><rect x="'+L+'" y="'+T+'" width="'+(W-L-R)+'" height="'+(H-T-B)+'" fill="transparent"/></svg>';
    host.innerHTML=svg;
    var el=host.querySelector('svg'), hov=el.querySelector('.hov'), xh=hov.querySelector('line');
    function show(clientX, clientY){
      var r=el.getBoundingClientRect(); var sx=(clientX-r.left)*W/r.width; if(sx<L||sx>W-R){ hide(); return; }
      var t=tStart+(sx-L)/(W-L-R)*(tEnd-tStart);
      xh.setAttribute('x1',sx); xh.setAttribute('x2',sx); hov.style.display='';
      var dots=hov.querySelectorAll('circle'); dots.forEach(function(c){c.remove()});
      var rows=S.map(function(s){ var v=valAt(s.h,t); if(v==null) return ''; var c=document.createElementNS('http://www.w3.org/2000/svg','circle'); c.setAttribute('cx',sx); c.setAttribute('cy',Y(v)); c.setAttribute('r',4); c.setAttribute('class','hdot'); c.style.fill=s.color; hov.appendChild(c); return (S.length>1?'<i style="display:inline-block;width:9px;height:9px;border-radius:2px;background:'+s.color+';margin-right:6px"></i>'+esc(s.name)+': ':'')+'<b>'+pct(v)+'</b>'; }).filter(Boolean);
      tip.innerHTML='<b>'+fmtDate(t,true)+'</b><br>'+rows.join('<br>'); tip.hidden=false;
      tip.style.left=Math.min(window.innerWidth-270, clientX+14)+'px'; tip.style.top=(clientY+14)+'px';
    }
    function hide(){ hov.style.display='none'; tip.hidden=true; }
    el.addEventListener('mousemove',function(e){ show(e.clientX,e.clientY); });
    el.addEventListener('mouseleave',hide);
    el.addEventListener('touchstart',function(e){ var t=e.touches[0]; show(t.clientX,t.clientY); },{passive:true});
    el.addEventListener('touchend',function(){ setTimeout(hide,1500); });
  }
  function rangeButtons(el, cur, onPick){
    var R=[['1y',365],['3y',1095],['all',0]];
    el.innerHTML=R.map(function(r){ return '<button type="button" data-r="'+r[1]+'" aria-pressed="'+(cur===r[1])+'">'+(r[0]==='all'?'All':r[0].toUpperCase())+'</button>'; }).join('');
    el.onclick=function(e){ var b=e.target.closest('button'); if(!b) return; var v=+b.dataset.r; el.querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed',String(x===b))}); onPick(v); };
  }

  var open={};
  function rowHtml(it){
    var w = Math.max(0,Math.min(1,it.p))*100;
    var tags = '';
    if(it.cond) tags += ' <span class="tag" title="Conditional on an earlier event">If</span>';
    var n=(it.hist||[]).length, since=n?fmtDate(tms(it.hist[0][0])):'';
    return '<div class="row" data-id="'+it.id+'">'+
      '<div class="q"><a href="'+esc(it.url)+'" target="_blank" rel="noopener">'+esc(it.q)+'</a>'+tags+
        '<div class="meta">'+chip(it.src)+'<span>'+esc(it.h)+'</span>'+(n>1?'<span>Tracked since '+since+'</span>':'')+'</div>'+
        (it.note?'<div class="note">'+esc(it.note)+'</div>':'')+
        (n>1?'<button type="button" class="xbtn" id="x-'+it.id+'" aria-expanded="'+(!!open[it.id])+'" data-x="'+it.id+'">'+(open[it.id]?'Hide history':'Show history')+'</button>':'')+
      '</div>'+
      '<div class="bar"><span class="v">'+pct(it.p)+'</span><div class="t" role="img" aria-label="'+pct(it.p)+'"><div class="tick" style="left:50%"></div><span style="width:'+w.toFixed(2)+'%"></span></div></div>'+
      '<div class="part">'+part(it)+'</div>'+
      '<div class="trend">'+spark(it.hist)+deltaHtml(change(it,30))+'</div>'+
      (open[it.id]?'<div class="detail"><div class="dh"><span>Full history</span><div class="ranges" data-rg="'+it.id+'"></div></div><div class="chart" data-ch="'+it.id+'"></div></div>':'')+
    '</div>';
  }
  function mountDetails(){
    document.querySelectorAll('[data-ch]').forEach(function(host){
      var it=byId[host.dataset.ch]; var rg=document.querySelector('[data-rg="'+it.id+'"]');
      var col='var(--s-'+it.src+')';
      function draw(r){ lineChart(host,[{name:it.q,color:col,h:it.hist}],r,200); }
      var cur=open[it.id+'_r']||0; rangeButtons(rg,cur,function(r){ open[it.id+'_r']=r; draw(r); }); draw(cur);
    });
  }
  document.getElementById('table').addEventListener('click',function(e){
    var b=e.target.closest('[data-x]'); if(!b) return; var id=b.dataset.x; open[id]=!open[id]; renderTable();
    var nb=document.getElementById('x-'+id); if(nb) nb.focus();
  });
  function partScore(it){ if(it.n==null) return -1; return it.nu==='volume'? it.n/100 : it.n; }
  function renderTable(){
    var list = D.items.filter(function(it){ return (state.cat==='all'||it.cat===state.cat) && !state.off[it.src]; });
    var el = document.getElementById('table');
    var head = '<div class="thead"><span>Question</span><span>Probability</span><span>Participation</span><span>Past year · 30-day change</span></div>';
    if(!list.length){ el.innerHTML = head+'<div class="empty">No questions match. Turn a source back on or pick another category.</div>'; return; }
    var html = head;
    if(state.sort==='group'){
      CATS.slice(1).forEach(function(c){
        var g = list.filter(function(it){return it.cat===c[0]});
        if(!g.length) return;
        if(state.cat==='all') html += '<div class="grp">'+esc(c[1])+'</div>';
        html += g.map(rowHtml).join('');
      });
    } else {
      var l = list.slice();
      if(state.sort==='high') l.sort(function(a,b){return b.p-a.p});
      if(state.sort==='low') l.sort(function(a,b){return a.p-b.p});
      if(state.sort==='part') l.sort(function(a,b){return partScore(b)-partScore(a)});
      if(state.sort==='move') l.sort(function(a,b){return Math.abs(change(b,30)||0)-Math.abs(change(a,30)||0)});
      html += l.map(rowHtml).join('');
    }
    el.innerHTML = html;
    mountDetails();
    document.getElementById('count').textContent = D.items.length+' questions tracked · '+D.people.length+' individual estimates · '+D.studies.length+' structured estimates';
  }

  // legend
  document.getElementById('legend').innerHTML = Object.keys(SRC).map(chip).join('') + '<span class="chip"><i style="background:var(--s-expert)"></i>Expert estimate</span>';

  // studies
  document.getElementById('studies').innerHTML = D.studies.map(function(s){
    return '<div class="study"><div class="v">'+pct(s.p)+'</div><div><div class="w"><a href="'+esc(s.url)+'" target="_blank" rel="noopener">'+esc(s.name)+'</a></div><div class="n">'+esc(s.what)+' · '+esc(s.when)+(s.note?' · '+esc(s.note):'')+'</div></div></div>';
  }).join('');

  // expert dot plot (log scale)
  function drawDots(){
    var P = D.people.slice().sort(function(a,b){ return (b.lo+b.hi)-(a.lo+a.hi); });
    var host = document.getElementById('dots');
    var W = Math.max(520, host.parentNode.clientWidth||600);
    var L = 176, R = 58, rowH = 24, top = 10, bottom = 30;
    var H = top + P.length*rowH + bottom;
    var lo = Math.log10(0.0001), hi = Math.log10(1);
    function x(p){ var v=Math.log10(Math.max(0.0001,Math.min(1,p))); return L + (W-L-R)*(v-lo)/(hi-lo); }
    var ticks=[[0.0001,'0.01%'],[0.001,'0.1%'],[0.01,'1%'],[0.1,'10%'],[1,'100%']];
    var s = '<svg width="'+W+'" height="'+H+'" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Individual p(doom) estimates on a log scale">';
    s += '<g class="ax">';
    ticks.forEach(function(t){ var X=x(t[0]); s+='<line x1="'+X+'" x2="'+X+'" y1="'+top+'" y2="'+(H-bottom)+'"/><text x="'+X+'" y="'+(H-bottom+18)+'" text-anchor="middle">'+t[1]+'</text>'; });
    s += '<line class="base" x1="'+L+'" x2="'+(W-R)+'" y1="'+(H-bottom)+'" y2="'+(H-bottom)+'"/></g>';
    P.forEach(function(p,i){
      var y = top + i*rowH + rowH/2;
      var mid = p.lo===p.hi ? p.lo : Math.sqrt(p.lo*p.hi);
      s += '<g class="p" data-i="'+i+'">';
      s += '<rect class="rowhl" x="0" y="'+(y-rowH/2)+'" width="'+W+'" height="'+rowH+'"/>';
      s += '<text class="pname" x="0" y="'+(y+4)+'">'+esc(p.name)+'</text>';
      if(p.lo!==p.hi) s += '<line class="rng" x1="'+x(p.lo)+'" x2="'+x(p.hi)+'" y1="'+y+'" y2="'+y+'"/>';
      s += '<circle class="dot" cx="'+x(mid)+'" cy="'+y+'" r="5"/>';
      s += '<text class="pval" x="'+(W-R+8)+'" y="'+(y+4)+'">'+esc(p.label)+'</text>';
      s += '<rect class="hit" x="0" y="'+(y-rowH/2)+'" width="'+W+'" height="'+rowH+'"/>';
      s += '</g>';
    });
    s += '</svg>';
    host.innerHTML = s;
    host.querySelectorAll('g.p').forEach(function(g){
      var p = P[+g.dataset.i];
      g.addEventListener('mousemove', function(e){
        tip.innerHTML = '<b>'+esc(p.name)+'</b> · '+esc(p.label)+'<br>'+esc(p.role);
        tip.hidden = false;
        var tx = Math.min(window.innerWidth - 270, e.clientX + 14);
        tip.style.left = tx+'px'; tip.style.top = (e.clientY + 14)+'px';
      });
      g.addEventListener('mouseleave', function(){ tip.hidden = true; });
    });
  }

  // hero chart
  var heroSeries=[
    {name:'Metaculus implied: AI kills 10%+ by 2100', color:'var(--c-blue)', h:byId['mc-implied-cat'].hist},
    {name:'Metaculus implied: AI kills 95%+ by 2100', color:'var(--c-blue)', dash:true, h:byId['mc-implied-ext'].hist},
    {name:'Manifold: AI wipes out humanity by 2100', color:'var(--c-orange)', h:byId['mf-wipe-2100'].hist}
  ];
  document.getElementById('hero-legend').innerHTML=heroSeries.map(function(s){ return '<span><svg width="22" height="8" aria-hidden="true"><line x1="1" x2="21" y1="4" y2="4" stroke="'+s.color+'" stroke-width="2.5"'+(s.dash?' stroke-dasharray="5 3"':'')+'/></svg>'+esc(s.name)+'</span>'; }).join('');
  var heroR=1095; try{ var hv=localStorage.getItem('ledger-hero'); if(hv!=null) heroR=+hv; }catch(e){}
  function drawHero(){ lineChart(document.getElementById('hero-chart'), heroSeries, heroR, 280); }
  rangeButtons(document.getElementById('hero-range'), heroR, function(r){ heroR=r; try{localStorage.setItem('ledger-hero',String(r))}catch(e){} drawHero(); });
  // movers
  var mv=D.items.map(function(it){ return {it:it, d:change(it,30)}; }).filter(function(x){ return x.d!=null && Math.abs(x.d)>=0.005 && x.it.src!=='derived' && x.it.cat!=='context'; })
    .sort(function(a,b){ return Math.abs(b.d)-Math.abs(a.d); }).slice(0,4);
  document.getElementById('movers').innerHTML = mv.map(function(x){
    var pts=x.d*100; return '<div class="mover"><div>'+chip(x.it.src)+'</div><div class="mq">'+esc(x.it.q)+'</div><div class="mv">'+pct(x.it.p)+' <small>'+(pts>0?'▲ +':'▼ −')+Math.abs(pts).toFixed(Math.abs(pts)>=10?0:1)+' pts</small></div></div>';
  }).join('');

  syncControls(); renderTable(); drawDots(); drawHero();
  var rt; window.addEventListener('resize', function(){ clearTimeout(rt); rt=setTimeout(function(){ drawDots(); drawHero(); mountDetails(); },120); });
}

fetch('data.json',{cache:'no-cache'}).then(function(r){ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); }).then(start).catch(function(e){
  document.getElementById('table').innerHTML='<div class="empty">Could not load data.json ('+e.message+'). To preview locally, run: python -m http.server -d site</div>';
});
