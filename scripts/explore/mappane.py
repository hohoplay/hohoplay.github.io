CSS=r'''
#pcmap{display:none}
.wrap{padding-bottom:0}#pcfoot{padding-top:0;padding-bottom:16px}
@media(min-width:1024px){
 #pcmain{display:flex;align-items:flex-start}
 #pcmain>.wrap{flex:none;width:480px;max-width:480px;margin:0;padding:16px 14px 0}
 #pcmap{display:block;position:sticky;top:0;flex:1;min-width:0;height:100vh;background:var(--map,#dbeafe);border-left:1px solid var(--line);overflow:hidden;z-index:1}
 .ov{right:auto;width:480px}.sheet{left:0;right:auto;width:480px;max-width:480px;margin:0}
 #pcfoot{max-width:1100px;margin:0 auto;padding:24px 28px 24px;border-top:1px solid var(--line)}#pcfoot .rcg{grid-template-columns:repeat(4,minmax(0,1fr))}
}
@media(min-width:1600px){#pcmain>.wrap{width:560px;max-width:560px}.ov{width:560px}.sheet{width:560px;max-width:560px}}
:root{--map:#dbeafe;--land:#f1f5e9}@media(prefers-color-scheme:dark){:root{--map:#0b2545;--land:#1f2d1f}}
#pcmap svg{width:100%;height:100%;display:block}#pcmap .tip{position:absolute;left:14px;top:12px;padding:6px 10px;border-radius:10px;background:rgba(255,255,255,.92);color:#334155;font-size:12px;font-weight:700;box-shadow:0 2px 8px rgba(0,0,0,.12)}
#pcmap .zb{position:absolute;right:14px;top:12px;display:flex;flex-direction:column;gap:6px}#pcmap .zb button{width:38px;height:38px;border:0;border-radius:10px;background:#fff;color:#334155;font-size:18px;font-weight:800;box-shadow:0 2px 8px rgba(0,0,0,.15);cursor:pointer}
#pclayer{transition:transform .5s cubic-bezier(.2,.8,.2,1);transform-origin:0 0}
.mp{fill:#6366f1;stroke:#fff;stroke-width:1.2;cursor:pointer;vector-effect:non-scaling-stroke}.mp.f{fill:#e11d48}.mp.c{fill:#4f46e5;stroke-width:2}.mp.hl{fill:#f59e0b;stroke:#78350f;stroke-width:2}
.mpath{fill:none;stroke:#4f46e5;stroke-width:3;stroke-dasharray:6 5;stroke-linecap:round;vector-effect:non-scaling-stroke}
.mnum circle{fill:#4f46e5;stroke:#fff;stroke-width:2;vector-effect:non-scaling-stroke}.mnum text.n{fill:#fff;font-weight:800;text-anchor:middle;dominant-baseline:central}
.mnum text.l,.mlbl{font-weight:800;fill:#1e293b;paint-order:stroke;stroke:#fff;stroke-width:3px;vector-effect:non-scaling-stroke;text-anchor:start}
#pcland,#pcjeju{vector-effect:non-scaling-stroke}
.card.mfl,.li.mfl{box-shadow:0 0 0 3px #f59e0b!important;transition:box-shadow .3s}.card.msel,.li.msel{outline:2px solid #4f46e5;outline-offset:2px}
'''
HTML=r'''<aside id="pcmap" aria-hidden="true"><div class="tip">📍 시안용 지도 모형이에요. 실제로는 카카오맵이 들어가요.</div><div class="zb"><button id="pzi" aria-label="확대">＋</button><button id="pzo" aria-label="축소">－</button><button id="pzr" aria-label="전체">⌂</button></div>
<svg id="pcsvg" viewBox="0 0 600 760" preserveAspectRatio="xMidYMid meet"><g id="pclayer"><path id="pcland" fill="var(--land)" stroke="#94a3b8" stroke-width="1.5" d=""/><ellipse id="pcjeju" fill="var(--land)" stroke="#94a3b8" stroke-width="1.5"/><g id="pcpins"></g><g id="pcroute"></g></g></svg></aside>'''
JS=r'''<script>
(function(){var W=600,H=760,X0=125.6,X1=130.0,Y0=38.9,Y1=33.0,layer=document.getElementById('pclayer'),pins=document.getElementById('pcpins'),rt=document.getElementById('pcroute'),map=document.getElementById('pcmap'),view=1,pts=[],selId=null,LIST=!!window.ITEMS;
function px(l){return (l-X0)/(X1-X0)*W}function py(l){return (Y0-l)/(Y0-Y1)*H}
var P=[[126.2,37.8],[126.8,38.1],[127.5,38.5],[128.4,38.6],[129.1,37.8],[129.45,36.9],[129.55,35.9],[129.3,35.2],[128.7,34.9],[128.0,34.85],[127.4,34.55],[126.6,34.3],[126.3,34.9],[126.5,35.7],[126.65,36.5],[126.3,36.85],[126.55,37.35]];
document.getElementById('pcland').setAttribute('d','M'+P.map(function(p){return px(p[0]).toFixed(1)+' '+py(p[1]).toFixed(1)}).join('L')+'Z');
var j=document.getElementById('pcjeju');j.setAttribute('cx',px(126.55));j.setAttribute('cy',py(33.38));j.setAttribute('rx',px(126.95)-px(126.15));j.setAttribute('ry',(py(33.15)-py(33.6))/2);
function visible(){return map.offsetWidth>0}
function size(){var s=document.getElementById('pcsvg').getBoundingClientRect(),k=Math.min(s.width/W,s.height/H);return {k:k,vw:s.width/k,vh:s.height/k}}
function put(s,cx,cy){var z=size(),ox=-(z.vw-W)/2,oy=-(z.vh-H)/2;layer.style.transform='translate('+(ox+z.vw/2-cx*s)+'px,'+(oy+z.vh/2-cy*s)+'px) scale('+s+')';view=s;}
function reset(){layer.style.transform='translate(0,0) scale(1)';view=1;}
function fit(la0,la1,ln0,ln1){var z=size(),x0=px(ln0),x1=px(ln1),y0=py(la1),y1=py(la0);var s=Math.min(z.vw/(Math.max(x1-x0,20)+90),z.vh/(Math.max(y1-y0,20)+90));put(Math.max(1.5,Math.min(s,16)),(x0+x1)/2,(y0+y1)/2);}
function dots(){var h='';pts.forEach(function(p){h+='<circle class="mp'+(p.c?' c':'')+(p.f?' f':'')+(p.id===selId?' hl':'')+'" data-id="'+p.id+'" cx="'+px(p.ln).toFixed(1)+'" cy="'+py(p.la).toFixed(1)+'" r="'+(((p.id===selId?8:(p.c?6:3.4)))/view).toFixed(2)+'"/>'});pins.innerHTML=h;}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function drawRoute(st){var u=1/view,P2=st.map(function(x){return [px(x[1]),py(x[0])]});
rt.innerHTML='<polyline class="mpath" points="'+P2.map(function(p){return p[0].toFixed(1)+','+p[1].toFixed(1)}).join(' ')+'"/>'+st.map(function(x,i){return '<g class="mnum"><circle cx="'+P2[i][0].toFixed(1)+'" cy="'+P2[i][1].toFixed(1)+'" r="'+(11*u).toFixed(2)+'"/><text class="n" style="font-size:'+(11*u).toFixed(2)+'px" x="'+P2[i][0].toFixed(1)+'" y="'+P2[i][1].toFixed(1)+'">'+(i+1)+'</text><text class="l" style="font-size:'+(11*u).toFixed(2)+'px" x="'+(P2[i][0]+14*u).toFixed(1)+'" y="'+(P2[i][1]-12*u).toFixed(1)+'">'+esc(x[2])+'</text></g>'}).join('');}
function clear(){selId=null;rt.innerHTML='';[].forEach.call(document.querySelectorAll('.msel'),function(e){e.classList.remove('msel')});}
var api={set:function(a){pts=a;if(visible())dots();},
 focus:function(id,st,la,ln,el){if(!visible())return;clear();selId=id;if(el)el.classList.add('msel');
  if(st){var a=st.map(function(x){return x[0]}),b=st.map(function(x){return x[1]});fit(Math.min.apply(null,a),Math.max.apply(null,a),Math.min.apply(null,b),Math.max.apply(null,b));drawRoute(st);}
  else{put(6,px(ln),py(la));var u=1/view,t=(window.ITEMS||[]).filter(function(x){return x.id===id})[0];rt.innerHTML='<text class="mlbl" x="'+(px(ln)+9*u)+'" y="'+(py(la)-9*u)+'" style="font-size:'+(12*u).toFixed(2)+'px">'+esc(t?t.n:'')+'</text>';}
  dots();},
 hover:function(id){[].forEach.call(pins.children,function(p){p.classList.toggle('hl',p.getAttribute('data-id')===(id||selId))})}};
window.PCMAP=api;
document.getElementById('pzi').onclick=function(){reZ(1.5)};document.getElementById('pzo').onclick=function(){reZ(1/1.5)};document.getElementById('pzr').onclick=function(){reset();clear();dots()};
function reZ(f){var z=size(),m=/translate\(([-\d.]+)px,([-\d.]+)px\)/.exec(layer.style.transform)||[0,0,0],tx=+m[1],ty=+m[2],ox=-(z.vw-W)/2,oy=-(z.vh-H)/2,cx=((z.vw/2+ox)-tx)/view,cy=((z.vh/2+oy)-ty)/view;var s=Math.max(1,Math.min(16,view*f));put(s,cx,cy);dots();if(selId){var e=document.querySelector('[data-id="'+selId+'"].card,[data-id="'+selId+'"].li');}}
/* 카드 클릭/호버 */
document.addEventListener('click',function(e){var c=e.target.closest('.card,.li');if(!c||e.target.closest('a,button'))return;if(!visible())return;var id=c.getAttribute('data-id');
if(LIST){var t=ITEMS.filter(function(x){return x.id===id})[0];if(t)api.focus(id,null,t.la,t.ln,c);}
else{var st=JSON.parse(c.getAttribute('data-stops')||'[]');api.focus(id,st,0,0,c);}});
document.addEventListener('mouseover',function(e){var c=e.target.closest('.card,.li');if(c&&visible())api.hover(c.getAttribute('data-id'));});
pins.addEventListener('click',function(e){var id=e.target.getAttribute&&e.target.getAttribute('data-id');if(!id)return;var el=document.querySelector('[data-id="'+id+'"].card,[data-id="'+id+'"].li');
if(LIST){var t=ITEMS.filter(function(x){return x.id===id})[0];if(!el&&t){api.focus(id,null,t.la,t.ln,null);return;}}
if(el){el.scrollIntoView({block:'center',behavior:'smooth'});el.classList.add('mfl');setTimeout(function(){el.classList.remove('mfl')},1200);el.click();}});
/* 코스 페이지: 보이는 카드로 점 갱신 */
if(!LIST){var tm=null;function syncC(){if(!visible())return;var a=[];[].forEach.call(document.querySelectorAll('.card'),function(c){if(c.offsetParent===null)return;a.push({id:c.getAttribute('data-id'),la:+c.getAttribute('data-lat'),ln:+c.getAttribute('data-lng'),c:1})});api.set(a);}
new MutationObserver(function(){clearTimeout(tm);tm=setTimeout(syncC,120)}).observe(document.querySelector('.wrap'),{subtree:true,attributes:true,attributeFilter:['style'],childList:true});window.addEventListener('resize',syncC);setTimeout(syncC,50);}
else{window.PCROWS=function(rows){api.set(rows.map(function(i){return {id:i.id,la:i.la,ln:i.ln,f:i.t==='f'}}));};if(window.__rows)window.PCROWS(window.__rows);window.addEventListener('resize',function(){});}
})();
</script>'''
