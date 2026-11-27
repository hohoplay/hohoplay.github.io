import re
A=open(WORK+'/course_cards_all.html',encoding='utf-8').read()
B=open(WORK+'/list_all_sample.html',encoding='utf-8').read()
def scripts(t): return re.findall(r'<script>.*?</script>',t,flags=re.S)
styles=''.join(re.findall(r'<style>.*?</style>',B,flags=re.S))
styles=styles.replace('body.near','.vw.near').replace('body.rain','.vw.rain')
# 공통 윗부분
top=A[A.index('<div class="wrap">'):A.index('<div class="sbox">')]
top=top.replace('<div class="wrap">','',1).replace('<span class="badge">디자인 시안 · 실제 데이터 · 전체 43개 코스</span>','<span class="badge">디자인 시안 · 통합본(코스 추천 + 전체목록)</span>')
viewA=A[A.index('<div class="sbox">'):A.index('</div><aside id="pcmap"')]
viewB=B[B.index('<div class="sbox">'):B.index('</div><aside id="pcmap"')]
for v in ('A','B'): pass
viewA=viewA.replace(' for="dpick"','');viewB=viewB.replace(' for="dpick"','')
aside=A[A.index('<aside id="pcmap"'):A.index('</aside>')+8]
RG=[('seoul','서울'),('busan','부산'),('daegu','대구'),('incheon','인천'),('daejeon','대전'),('sejong','세종'),('gyeonggi','경기'),('gangwon','강원'),('chungbuk','충북'),('gyeongbuk','경북'),('gyeongnam','경남'),('chungnam','충남'),('jeonbuk','전북'),('jeonnam','전남'),('gwangju','광주'),('ulsan','울산'),('jeju','제주')]
aside=re.sub(r'<div class="tip">.*?</div>','<div class="mtop"><select id="pcsel" aria-label="지역 선택"><option value="">전국 전체보기</option>'+''.join(f'<option value="{k}">{l}</option>' for k,l in RG)+'</select><div class="tkw" id="tkw"><span id="tki"></span></div></div><div class="tip2">📍 시안용 지도 모형 (실제는 카카오맵)</div>',aside,count=1,flags=re.S)
foot=A[A.index('<div class="wrap" id="pcfoot">'):A.index('<script>')]
foot=re.sub(r'<p class="note">.*?</p>','<p class="note">※ 시안이에요. 코스 추천 43개 · 장소 676곳 · 축제는 실제 데이터를 사용했고, 지도는 모형이에요. (모바일은 탭으로, PC는 오른쪽 지도와 함께 보여요)</p>',foot,flags=re.S)
foot=foot.rstrip()
if foot.endswith('</div>')==False: foot+='</div>'
sa=scripts(A);sb=scripts(B)
def wrap(js,name):
    js=js.replace('<script>','',1).replace('</script>','',1).strip()
    assert js.startswith('(function(){'),js[:40]
    js='(function(document){'+js[len('(function(){'):]
    assert js.rstrip().endswith('})();')
    js=js.rstrip()[:-len('})();')]+'})(SC.'+name+');'
    return js
jsA=wrap(sa[0],'c')
lb=sb[0].replace('<script>','',1).replace('</script>','',1).strip()
i=lb.index('\n(function(){');itemsline=lb[:i];jsB=wrap('<script>'+lb[i+1:]+'</script>','l')
mp=sa[1].replace('<script>','',1).replace('</script>','',1)
# MP 보정: 두 보기 지원
mp=mp.replace("LIST=!!window.ITEMS;","LIST=false;")
mp=mp.replace("if(LIST){var t=ITEMS.filter(function(x){return x.id===id})[0];if(t)api.focus(id,null,t.la,t.ln,c);}\nelse{","if(c.classList.contains('li')){var t=ITEMS.filter(function(x){return x.id===id})[0];if(t)api.focus(id,null,t.la,t.ln,c);}\nelse{")
mp=mp.replace("if(LIST){var t=ITEMS.filter(function(x){return x.id===id})[0];if(!el&&t){api.focus(id,null,t.la,t.ln,null);return;}}","if(window.__view==='l'){var t=ITEMS.filter(function(x){return x.id===id})[0];if(!el&&t){api.focus(id,null,t.la,t.ln,null);return;}}")
i=mp.index("if(!LIST){var tm=null;");j=mp.rindex("})();")
mp=mp[:i]+"""var tm=null;function syncC(){if(!visible()||window.__view!=='c')return;var a=[];[].forEach.call(document.querySelectorAll('#vc .card'),function(c){if(c.offsetParent===null)return;a.push({id:c.getAttribute('data-id'),la:+c.getAttribute('data-lat'),ln:+c.getAttribute('data-lng'),c:1})});api.set(a);}
new MutationObserver(function(){clearTimeout(tm);tm=setTimeout(syncC,120)}).observe(document.getElementById('vc'),{subtree:true,attributes:true,attributeFilter:['style'],childList:true});window.addEventListener('resize',syncC);
window.PCROWS=function(rows){if(window.__view!=='l')return;api.set(rows.map(function(i){return {id:i.id,la:i.la,ln:i.ln,f:i.t==='f'}}));};
window.PCSYNC={c:function(){syncC()},l:function(){if(window.__rows){window.PCROWS(window.__rows)}}};setTimeout(syncC,50);
"""+mp[j:]
mp=mp.replace("window.PCSYNC=","var BOX={seoul:[37.7,37.4,126.8,127.2],busan:[35.3,35.0,128.9,129.3],daegu:[35.95,35.75,128.45,128.75],incheon:[37.6,37.3,126.4,126.8],daejeon:[36.5,36.2,127.2,127.55],sejong:[36.7,36.4,127.1,127.4],gyeonggi:[38.0,36.9,126.4,127.7],gangwon:[38.4,37.0,127.5,129.3],chungbuk:[37.2,36.0,127.3,128.5],gyeongbuk:[37.0,35.7,128.1,129.5],gyeongnam:[35.7,34.7,127.7,129.2],chungnam:[37.0,36.0,125.9,127.4],jeonbuk:[36.2,35.3,126.4,127.7],jeonnam:[35.4,34.3,126.1,127.5],gwangju:[35.3,35.0,126.7,127.0],ulsan:[35.7,35.4,129.0,129.45],jeju:[33.6,33.15,126.1,126.95]};api.region=function(k){if(!visible())return;clear();if(!k||!BOX[k]){reset();dots();return;}var b=BOX[k];fit(b[1],b[0],b[2],b[3]);dots();};window.PCSYNC=",1)
assert 'LIST' not in mp.replace('LIST=false;','')
SW=r'''
var SC={};
function mkScope(root){return {getElementById:function(id){return root.querySelector('#'+id)||document.getElementById(id)},querySelector:function(s){return root.querySelector(s)||document.querySelector(s)},querySelectorAll:function(s){return root.querySelectorAll(s)},addEventListener:function(t,f,o){root.addEventListener(t,f,o)},get body(){return root},createElement:function(t){return document.createElement(t)},get documentElement(){return document.documentElement}};}
SC.c=mkScope(document.getElementById('vc'));SC.l=mkScope(document.getElementById('vl'));window.__view='c';
'''
TABJS=r'''
(function(){var vc=document.getElementById('vc'),vl=document.getElementById('vl');
function show(v){var seg=(v==='c'?vl:vc).querySelector('.seg'),y0=seg?seg.getBoundingClientRect().top:0;
vc.hidden=v!=='c';vl.hidden=v!=='l';window.__view=v;var ns=(v==='c'?vc:vl).querySelector('.seg');if(ns&&seg){window.scrollBy(0,ns.getBoundingClientRect().top-y0);}
if(window.PCSYNC)window.PCSYNC[v]();}
[].forEach.call(document.querySelectorAll('.seg a'),function(a,i){a.addEventListener('click',function(e){e.preventDefault();var n=a.textContent.trim();if(n==='코스 추천')show('c');else if(n==='전체목록')show('l');else alert('시안: 모바일에서는 기존 지도 화면(/festival/)으로 이동해요.');});});
/* 하단 지역 카드: 지금 보고 있는 보기에서 지역 선택 */
document.addEventListener('click',function(e){var a=e.target.closest('.rc');if(!a)return;var root=window.__view==='c'?vc:vl,b=root.querySelector('.rg[data-k='+a.getAttribute('data-k')+']');if(b){e.preventDefault();b.click();root.scrollIntoView({behavior:'smooth'});}});
})();
'''
REM='''<nav class="rm" aria-label="바로가기"><button type="button" class="up" id="rmup" aria-label="맨 위로">⬆<small>위로</small></button><a href="/" aria-label="홈">🏠<small>홈</small></a></nav>'''
CSSX='''<style>.mtop{position:absolute;left:50%;transform:translateX(-50%);top:12px;width:min(420px,calc(100% - 140px));z-index:3}#pcsel{width:100%;padding:13px 14px;border:2px solid #4f46e5;border-radius:12px;background:#fff;color:#1e293b;font-size:15px;font-weight:800;font-family:inherit;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.tkw{margin-top:6px;height:30px;border-radius:0 0 10px 10px;background:rgba(255,255,255,.92);overflow:hidden;position:relative;box-shadow:0 2px 8px rgba(0,0,0,.1)}.tkw span{position:absolute;left:0;top:0;line-height:30px;white-space:nowrap;font-size:12px;font-weight:700;color:#334155;padding:0 12px;will-change:transform}
.tip2{position:absolute;left:14px;bottom:12px;padding:5px 9px;border-radius:9px;background:rgba(255,255,255,.9);color:#475569;font-size:11px;font-weight:700}
.rm{position:fixed;right:14px;bottom:18px;z-index:40;display:flex;flex-direction:column;gap:10px}.rm a,.rm button{width:52px;height:52px;border-radius:50%;border:1px solid var(--line);background:var(--card);color:var(--ink);box-shadow:0 4px 14px rgba(0,0,0,.2);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;font-size:20px;line-height:1;font-family:inherit;cursor:pointer;text-decoration:none}.rm small{font-size:10px;font-weight:800}.rm .up{opacity:0;pointer-events:none;transition:opacity .2s}.rm .up.on{opacity:1;pointer-events:auto}
[hidden]{display:none!important}@media(min-width:1024px){.seg{grid-template-columns:repeat(2,1fr)!important}.seg a:nth-child(3){display:none}}</style>'''
RMJS=r'''
(function(){var u=document.getElementById('rmup');function t(){u.classList.toggle('on',(window.pageYOffset||0)>300)}window.addEventListener('scroll',t,{passive:true});t();
u.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'})});})();
/* 지도 위 지역 선택 + 안내 티커 */
(function(){var sel=document.getElementById('pcsel');if(!sel)return;
function apply(k,fromSel){sel.value=k||'';if(window.PCMAP&&PCMAP.region)PCMAP.region(k||'');}
sel.addEventListener('change',function(){var k=sel.value,root=document.getElementById(window.__view==='c'?'vc':'vl'),b=k?root.querySelector('.rg[data-k='+k+']'):root.querySelector('.sh-all');if(b)b.click();apply(k);});
document.addEventListener('click',function(e){var b=e.target.closest('.rg[data-k]');if(b&&!b.hasAttribute('data-all')&&!e.__fromSel){apply(b.getAttribute('data-k'));}var s2=e.target.closest('.sh-all');if(s2)apply('');},true);
var M=['📋 전체목록: 지금 열리는 축제를 전부 볼 수 있어요','🗺️ 코스추천: 아이랑 갈만한 곳을 묶어 하루 코스로 보여드려요 (최대 4곳)','⚠️ 코스에 포함된 축제는 성격이 다양할 수 있어요 — 방문 전 한번 더 확인하세요','📍 지역을 먼저 선택하면 그 지역 코스만 바로 볼 수 있어요','💰 이용요금에서 무료만/유료만으로 비용별로 걸러볼 수 있어요'];
var wrap=document.getElementById('tkw'),el=document.getElementById('tki'),i=0,red=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
function play(){if(!wrap||!el)return;el.textContent=M[i%M.length];i++;if(red||wrap.offsetWidth===0){setTimeout(play,8500);return;}
var w=wrap.offsetWidth;el.style.transition='none';el.style.transform='translateX('+w+'px)';void el.offsetWidth;var iw=el.offsetWidth;el.style.transition='transform 8000ms linear';el.style.transform='translateX(-'+iw+'px)';setTimeout(play,8500);}
play();})();
'''
page=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>아이랑 갈만한 곳·축제 통합 시안 - HOHO PLAY</title>{styles}{CSSX}</head><body><div id="pcmain"><div class="wrap">{top}<div class="vw" id="vc">{viewA}</div><div class="vw" id="vl" hidden>{viewB}</div></div>{aside}</div>
{foot}
{REM}
<script>{itemsline}
{SW}
{jsA}
{jsB}
{TABJS}{RMJS}</script><script>{mp}</script></body></html>'''
open(WORK+'/hohoplay_merged_sample.html','w',encoding='utf-8').write(page)
print(len(page)//1024,'KB')
