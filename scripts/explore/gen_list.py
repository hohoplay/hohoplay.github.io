import json,re,html,datetime
S=ROOT+'/'
base=open(WORK+'/course_cards_all.html',encoding='utf-8').read()
css=re.search(r'<style>.*?</style>',base,flags=re.S).group(0)
top=base[base.index('<div class="wrap">'):base.index('<div class="sbox">')].replace('<span class="badge">디자인 시안 · 실제 데이터 · 전체 43개 코스</span>','<span class="badge">디자인 시안 · 전체목록 · 실제 데이터</span>')
# 날짜 JS 재사용
gs=open(ASSET+'/gen_all.py',encoding='utf-8').read()
datejs=gs[gs.index("(function(){var W=['일'"):gs.index("pick(late?'tom':'today',late);})();")+len("pick(late?'tom':'today',late);})();")]
dtblock=re.search(r'<div class="dt">.*?</p></div>\n',base,flags=re.S).group(0)
TOOLS=base[base.index('<div id="today-tools-s"') if '<div id="today-tools-s"' in base else base.index('<section id="today-tools-s"'):]
TOOLS=TOOLS[:TOOLS.index('</section>')+10]
FOOT=open(WORK+'/regcards.html',encoding='utf-8').read()+base[base.index('<div id="data-notice"'):base.index('<p class="note">')]
# 주제 (gen_all에서 복사)
exec(gs[gs.index('TOPICS=['):gs.index('def fee_of')])
REG=[('seoul','서울','🗼',('서울',)),('daejeon','대전','🔬',('대전',)),('daegu','대구','🍎',('대구',)),('busan','부산','🌉',('부산',)),('incheon','인천','✈️',('인천',)),
('gyeonggi','경기','🏙️',('경기',)),('sejong','세종','🏛️',('세종',)),('gangwon','강원','⛰️',('강원',)),('chungbuk','충북','🌿',('충청북도','충북')),('gyeongbuk','경북','🏯',('경상북도','경북')),('gyeongnam','경남','🌊',('경상남도','경남')),
('chungnam','충남','🌾',('충청남도','충남')),('jeonbuk','전북','🍚',('전북','전라북도')),('jeonnam','전남','🌴',('전라남도','전남')),('gwangju','광주','🎨',('광주','전남광주')),('ulsan','울산','🐋',('울산',)),('jeju','제주','🍊',('제주',))]
def rk(addr):
    a=addr.split()[0] if addr else ''
    for k,_,_,ps in REG:
        if any(a.startswith(p) for p in ps): return k
    return ''
def img(u): return ('https://'+u[7:]) if (u or '').startswith('http://') else (u or '')
items=[]
P=[x for x in json.load(open(S+'data/kids_places.json',encoding='utf-8')) if not x.get('hidden')]
for p in P:
    tg=p.get('costTag') or ''
    c='free' if tg=='완전무료' else ('paid' if tg.startswith('유료') else 'etc')
    sp=(p['addr'].split()+['',''])[1]
    d=(p.get('desc') or '').strip()
    items.append(dict(la=round(float(p['lat']),4),ln=round(float(p['lng']),4),t='p',id=p['contentid'],n=p['title'],r=rk(p['addr']),s=sp,im=img(p.get('image')),pt=p.get('placeType') or '',c=c,tp=topics_of(p['title']),d=d[:64]))
import datetime as _dt
today=(_dt.datetime.utcnow()+_dt.timedelta(hours=9)).strftime('%Y%m%d')
F=[f for f in json.load(open(S+'data/festivals.json',encoding='utf-8')) if f.get('type')=='festival' and f['endDate']>=today]
F.sort(key=lambda f:(f['startDate']>today,f['endDate']))
for f in F:
    ft=f.get('feeType') or ''
    c='free' if ft=='free' else ('paid' if ft in('paid','mixed') else 'etc')
    sp=(f['addr'].split()+['',''])[1]
    items.append(dict(la=round(float(f['lat']),4),ln=round(float(f['lng']),4),t='f',id=f['contentid'],n=f['title'],r=rk(f['addr']),s=sp,im=img(f.get('image')),pt='',c=c,tp=[],d=f['addr'].split(' (')[0][:40],sd=f['startDate'],ed=f['endDate']))
# 지역 버튼
cnt={}
for i in items: cnt[i['r']]=cnt.get(i['r'],0)+1
cnt['']=len(items)
TOP5=['seoul','daejeon','daegu','busan','incheon']; ROW=TOP5+['gyeonggi','sejong','gangwon','chungbuk','gyeongbuk','gyeongnam']
RM={k:(l,ic) for k,l,ic,_ in REG}
def rb(k): return f'<button type="button" class="rg" data-k="{k}"><span class="ic">{RM[k][1]}<em>{cnt.get(k,0)}</em></span><span class="lb">{RM[k][0]}</span></button>'
nP=sum(1 for i in items if i['t']=='p'); nF=len(items)-nP
tpc=''.join(f'<button type="button" data-v="{k}">{ic} {lb}</button>' for k,ic,lb,_ in TOPICS)
feec='<button type="button" class="on" data-v="">전체</button><button type="button" data-v="free">🆓 무료</button><button type="button" data-v="paid">💳 유료</button><button type="button" data-v="etc">❔ 요금 확인 필요</button>'
sheet=f'''<div class="ov" id="ov"></div><div class="sheet" id="sheet" role="dialog" aria-label="전체 지역"><div class="sh-h"><b>📍 전체 지역</b><button type="button" class="sh-x" id="shx" aria-label="닫기">✕</button></div><div class="shf"><div class="fr"><p class="rgt">주제 <small style="font-weight:600">(장소에만 적용)</small></p><div class="fc" data-g="tp"><button type="button" class="on" data-v="">전체</button>{tpc}</div></div><div class="fr"><p class="rgt">이용요금</p><div class="fc" data-g="fee">{feec}</div></div></div><p class="rgt">지역</p><div class="rgrid sh" id="shgrid">{''.join(rb(k) for k,_,_,_ in REG)}</div><button type="button" class="sh-all" data-k="">🗺️ 전국 전체 보기 ({len(items)})</button></div>'''
EXTRA_CSS='''<style>
.kd{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.li{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;display:flex;flex-direction:column}
.li .ph{position:relative;aspect-ratio:4/3;background:#c7d2fe center/cover no-repeat}.li .bd{position:absolute;left:8px;top:8px;padding:3px 8px;border-radius:999px;font-size:11px;font-weight:800;color:#fff}.bd.p{background:#4f46e5}.bd.f{background:#e11d48}
.li .bx{padding:10px 10px 12px;display:flex;flex-direction:column;gap:5px;flex:1}.li h3{margin:0;font-size:14px;line-height:1.35;word-break:keep-all}.li .mt{font-size:11px;font-weight:700;color:var(--sub);display:flex;gap:4px;flex-wrap:wrap}
.li .mt i{font-style:normal;padding:2px 6px;border-radius:6px;background:var(--soft);color:var(--pri)}.li .mt i.fr0{background:#dcfce7;color:#166534}.li .mt i.pd{background:#fef3c7;color:#92400e}.li p{margin:0;font-size:12px;color:var(--sub);line-height:1.5}
.li .ac{margin-top:auto;display:flex;flex-direction:column;gap:6px;padding-top:6px}.li .ac a,.li .ac button{display:block;text-align:center;border-radius:9px;padding:8px;font-size:12px;font-weight:800;font-family:inherit;text-decoration:none;cursor:pointer}.li .ac .a1{background:#4f46e5;color:#fff;border:0}.li .ac .a2{border:1px solid var(--pri);color:var(--pri);background:none}
.kt{display:flex;gap:6px;margin:0 0 12px}.kt button{flex:1;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:12px;padding:10px 4px;font-family:inherit;font-weight:800;font-size:13px;cursor:pointer}.kt button.on{background:#1e293b;border-color:#1e293b;color:#fff}.kt em{font-style:normal;opacity:.7;margin-left:3px;font-size:12px}
#more{display:block;width:100%;margin:16px 0 4px;padding:13px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:12px;font-weight:800;font-family:inherit;cursor:pointer}#cnt{margin:0 0 10px;font-size:13px;font-weight:800;color:var(--sub)}.empty{padding:30px 10px;text-align:center;color:var(--sub);font-size:14px}
.nb{margin-left:auto;border:1px solid #4f46e5;background:#fff;color:#4f46e5;border-radius:999px;padding:8px 14px;font-size:13px;font-weight:800;font-family:inherit;cursor:pointer;white-space:nowrap}.nb.on{background:#4f46e5;color:#fff}
.rad{display:none;margin:0 0 10px}.rad p{margin:0 0 6px}.dist{display:none;margin:0 0 6px;font-size:12px;font-weight:800;color:#be185d}body.near .dist{display:block}.nlocn{margin:0 0 8px}
.subr.fc{flex-wrap:wrap;overflow:visible;gap:8px}.subr.fc button{flex:0 0 auto}.subr .xmore{display:none}.subr.fold button.xh{display:none}.subr.fold .xmore{display:inline-block;border-style:dashed}.upd{display:block;margin:-4px 0 12px;font-size:12px;color:var(--sub);text-decoration:none;font-weight:700}.upd u{color:var(--pri)}html{scroll-behavior:smooth}#data-notice{scroll-margin-top:16px}#data-notice.fl p{animation:fl 1.6s ease}@keyframes fl{0%,60%{background:#fef9c3;border-color:#facc15}100%{background:#f8fafc}}
.sb2{display:none;margin:0 0 10px}.li .ph .fb{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:44px;background:linear-gradient(135deg,#e0e7ff,#fce7f3)}
</style>'''
JS=r'''<script>
var ITEMS=__DATA__;
(function(){var q=document.getElementById('q'),ind=document.getElementById('indoor'),res=document.getElementById('sres'),list=document.getElementById('kd'),cnt=document.getElementById('cnt'),more=document.getElementById('more');
var st='',sub='',tp='',fee='',kind='',shown=0,PAGE=24,rows=[],W=['일','월','화','수','목','금','토'];
var sh=document.getElementById('sheet'),ov=document.getElementById('ov'),bs=[].slice.call(document.querySelectorAll('.rg[data-k]'));
var dsel=null,near=false,pos=null,rad=0,nbtn=document.getElementById('nearbtn');
function hav(a,b,c,d){var R=6371,t=Math.PI/180,x=(c-a)*t,y=(d-b)*t,h=Math.sin(x/2)*Math.sin(x/2)+Math.cos(a*t)*Math.cos(c*t)*Math.sin(y/2)*Math.sin(y/2);return 2*R*Math.asin(Math.sqrt(h));} /* 선택한 날짜 범위 [from,to] yyyymmdd */
ITEMS.forEach(function(i){i._t=(i.n+i.s+(i.d||'')).replace(/\s+/g,'').toLowerCase();});
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function fd(s){return (+s.slice(4,6))+'.'+(+s.slice(6,8))}
function card(i){var dk=(near&&i._km!=null)?'<p class="dist" style="display:block">📍 내 위치에서 약 '+i._km.toFixed(i._km<10?1:0)+'km</p>':'';var m='',a='',ph='<div class="ph" style="'+(i.im?'background-image:url('+i.im+')':'')+'" role="img" aria-label="'+esc(i.n)+'">'+(i.im?'':'<span class="fb">'+(i.t==='f'?'🎪':({mus:'🏛️',sci:'🔬',park:'🌳',lib:'📚',play:'🎠',zoo:'🐠'}[i.tp[0]]||'📍'))+'</span>')+'<span class="bd '+i.t+'">'+(i.t==='p'?'📍 장소':'🎪 축제')+'</span></div>';
if(i.t==='p'){m=(i.pt?'<i>'+({'실내':'🏠 실내','실외':'🌳 실외','실내외':'🔀 실내외'}[i.pt]||i.pt)+'</i>':'')+'<i class="'+(i.c==='free'?'fr0':i.c==='paid'?'pd':'')+'">'+({free:'무료',paid:'유료',etc:'요금 확인'}[i.c])+'</i>'+(i.s?'<i>'+esc(i.s)+'</i>':'');
a='<a class="a1" href="/festival/detail/'+i.id+'.html">상세 보기</a><button type="button" class="a2" data-plan="'+i.id+'">📅 일정표 만들기</button>';}
else{m='<i>📅 '+fd(i.sd)+' ~ '+fd(i.ed)+'</i><i class="'+(i.c==='free'?'fr0':i.c==='paid'?'pd':'')+'">'+({free:'무료',paid:'유료',etc:'요금 확인'}[i.c])+'</i>';
a='<a class="a1" href="/festival/detail/'+i.id+'.html">상세 보기</a><a class="a2" href="/festival/?id='+i.id+'">🗺️ 지도로 보기</a>';}
return '<article class="li" data-id="'+i.id+'">'+ph+'<div class="bx"><div class="mt">'+m+'</div><h3>'+esc(i.n)+'</h3>'+dk+'<p>'+esc(i.d||'')+'</p><div class="ac">'+a+'</div></div></article>';}
function filt(){var w=q.value.replace(/\s+/g,'').toLowerCase();
rows=ITEMS.filter(function(i){if(kind&&i.t!==kind)return false;if(st&&i.r!==st)return false;if(sub&&i.s!==sub)return false;if(fee&&i.c!==fee)return false;
if(tp&&(i.t!=='p'||i.tp.indexOf(tp)<0))return false;if(ind.checked&&!(i.t==='p'&&i.pt!=='실외'))return false;
if(w&&i._t.indexOf(w)<0)return false;if(near){i._km=hav(pos[0],pos[1],i.la,i.ln);if(rad&&i._km>rad)return false;}
if(dsel&&i.t==='f'&&!(i.sd<=dsel[1]&&i.ed>=dsel[0]))return false;return true;});if(near)rows.sort(function(a,b){return a._km-b._km});}
function counts(){var base=ITEMS.filter(function(i){return (!st||i.r===st)&&(!sub||i.s===sub)&&(!fee||i.c===fee)&&(!(tp&&i.t==='p')||i.tp.indexOf(tp)>=0)&&(!tp||i.t==='p'||kind==='f')&&(!dsel||i.t!=='f'||(i.sd<=dsel[1]&&i.ed>=dsel[0]))});
var np=base.filter(function(i){return i.t==='p'}).length;document.querySelector('#kt [data-v=""] em').textContent=base.length;document.querySelector('#kt [data-v=p] em').textContent=np;document.querySelector('#kt [data-v=f] em').textContent=base.length-np;}
function draw(reset){window.__rows=rows;if(window.PCROWS)PCROWS(rows);if(reset){shown=0;list.innerHTML='';}var next=rows.slice(shown,shown+PAGE);list.insertAdjacentHTML('beforeend',next.map(card).join(''));shown+=next.length;
more.style.display=shown<rows.length?'':'none';more.textContent='더 보기 ('+(rows.length-shown)+'개 남음)';
cnt.textContent=rows.length?('총 '+rows.length+'곳'+(kind===''&&!st&&!sub&&!tp&&!fee&&!ind.checked&&!q.value?' · 열리는 축제 먼저':'')):'';
if(!rows.length)list.innerHTML='<div class="empty" style="grid-column:1/-1">맞는 곳이 없어요. 조건을 바꿔 보세요.</div>';}
function subs(){var w=document.getElementById('subw'),el=document.getElementById('subc');if(!st){w.style.display='none';return;}
var m={};ITEMS.forEach(function(i){if(i.r===st&&i.s)m[i.s]=(m[i.s]||0)+1});var k=Object.keys(m).sort(function(a,b){return m[b]-m[a]});
if(k.length<2){w.style.display='none';return;}
el.innerHTML='<button type="button" class="on" data-a="">'+document.querySelector('.rg[data-k='+st+'] .lb').textContent+' 전체</button>'+k.map(function(x,n){return '<button type="button" class="'+(n>=9?'xh':'')+'" data-a="'+esc(x)+'">'+esc(x)+' '+m[x]+'</button>'}).join('')+(k.length>9?'<button type="button" class="xmore" data-x="1">+ '+(k.length-9)+'곳 더보기 ▾</button>':'');el.classList.toggle('fold',k.length>9);w.style.display='block';}
function run(){filt();counts();draw(true);var on=q.value||ind.checked||st||tp||fee||kind;res.style.display='none';
bs.forEach(function(b){var k=b.getAttribute('data-k');b.classList.toggle('on',b.hasAttribute('data-all')?st==='':k===st)});}
function sheetT(on){sh.classList.toggle('on',on);ov.classList.toggle('on',on);}
bs.forEach(function(b){b.addEventListener('click',function(){if(b.hasAttribute('data-all')){sheetT(true);return;}st=b.getAttribute('data-k');sub='';sheetT(false);subs();run();});});
document.querySelector('.sh-all').addEventListener('click',function(){st='';sub='';sheetT(false);subs();run();window.scrollTo({top:0,behavior:'smooth'});});
document.getElementById('shx').addEventListener('click',function(){sheetT(false)});ov.addEventListener('click',function(){sheetT(false)});
document.addEventListener('click',function(e){var b=e.target.closest('.fc button,#kt button');if(!b)return;
if(b.hasAttribute('data-x')){b.parentNode.classList.remove('fold');return;}
if(b.closest('#subc')){sub=b.getAttribute('data-a');[].forEach.call(b.parentNode.children,function(x){x.classList.toggle('on',x===b)});run();return;}
if(b.closest('#kt')){kind=b.getAttribute('data-v');[].forEach.call(b.parentNode.children,function(x){x.classList.toggle('on',x===b)});run();return;}
var g=b.parentNode.getAttribute('data-g'),v=b.getAttribute('data-v');if(g==='tp')tp=v;else if(g==='fee')fee=v;else if(g==='rad')rad=+v||0;else return;
[].forEach.call(document.querySelectorAll('.fc[data-g='+g+']'),function(el){[].forEach.call(el.children,function(x){x.classList.toggle('on',x.getAttribute('data-v')===v)})});run();});

function nearOn(p,fake){pos=p;near=true;nbtn.classList.add('on');nbtn.textContent='📍 내 주변 ✕';var nl=document.getElementById('nlocn');nl.style.display='';nl.textContent=fake?'📍 시안에서는 위치를 못 가져와 서울시청 기준으로 보여드려요. 실제로는 내 위치 기준이에요.':'📍 내 위치 기준 가까운 순서예요. (위치는 이 기기에서만 쓰고 저장하지 않아요)';document.getElementById('rad').style.display='block';run();}
function nearOff(){near=false;pos=null;rad=0;nbtn.classList.remove('on');nbtn.textContent='📍 내 주변';document.getElementById('rad').style.display='none';document.getElementById('nlocn').style.display='none';[].forEach.call(document.querySelectorAll('#rad .fc button'),function(x){x.classList.toggle('on',!x.getAttribute('data-v'))});run();}
nbtn.addEventListener('click',function(){if(near){nearOff();return;}var fb=function(){nearOn([37.5665,126.9780],true)};if(!navigator.geolocation){fb();return;}var done=false;var t=setTimeout(function(){if(!done){done=true;fb()}},4000);
navigator.geolocation.getCurrentPosition(function(p){if(done)return;done=true;clearTimeout(t);nearOn([p.coords.latitude,p.coords.longitude],false)},function(){if(done)return;done=true;clearTimeout(t);fb()},{timeout:3500});});
document.addEventListener('click',function(e){var a=e.target.closest('.rc');if(!a)return;var b=document.querySelector('.rg[data-k='+a.getAttribute('data-k')+']');if(b){e.preventDefault();b.click();window.scrollTo({top:0,behavior:'smooth'});}});
document.getElementById('upd').addEventListener('click',function(e){e.preventDefault();var t=document.getElementById('data-notice');t.scrollIntoView({behavior:'smooth',block:'center'});t.classList.remove('fl');void t.offsetWidth;t.classList.add('fl');});
more.addEventListener('click',function(){draw(false)});q.addEventListener('input',run);ind.addEventListener('change',run);
/* 날짜 → 축제 필터 */
window.__setRange=function(a,b){dsel=[a,b];run();};
__DATEJS__
run();})();
</script>'''
# 날짜 JS에서 선택 변화를 축제 필터에 연결: pick/setDate 후 범위 통보
datejs2=datejs.replace("note.textContent=t;}","note.textContent=t;rng(k);}",1)
datejs2=datejs2.replace("note.textContent='📅 '+f(d)+' 운영시간","rng2(d);note.textContent='📅 '+f(d)+' 운영시간",1)
datejs2=datejs2.replace("function pick(k,auto){","function ymd(d){return iso(d).replace(/-/g,'')}function rng(k){var a,b;if(k==='today'){a=b=ymd(now)}else if(k==='tom'){a=b=ymd(add(1))}else{a=ymd(sat);b=ymd(sun)}window.__setRange(a,b)}function rng2(d){window.__setRange(ymd(d),ymd(d))}\nfunction pick(k,auto){",1)
datejs2=datejs2.replace("📅 '+f(now)+' 운영시간 기준으로 보여드려요.","📅 '+f(now)+' 열리는 축제만 보여드려요.").replace("'📅 '+f(add(1))+' 운영시간 기준이에요.'","'📅 '+f(add(1))+' 열리는 축제만 보여드려요.'").replace("운영시간 기준이에요. 주말에만 여는 곳·휴관일은 방문 전 확인하세요.","열리는 축제만 보여드려요. 장소는 휴관일을 방문 전 확인하세요.").replace("' 운영시간 기준이에요.'+(wk?","' 열리는 축제만 보여드려요.'+(wk?")
datejs2=datejs2.replace('내일 코스를 먼저 보여드려요. ','내일 날짜로 먼저 보여드려요. ')
JS=JS.replace('__DATA__',json.dumps(items,ensure_ascii=False,separators=(',',':'))).replace('__DATEJS__',datejs2)
import re as _r
m=_r.search(r'데이터 기준일: ([0-9.]+ [0-9:]+)',FOOT)
ST=('기준 '+m.group(1)) if m else '기준일 확인'
MPNS={}
exec(open(ASSET+'/mappane.py',encoding='utf-8').read(),MPNS)
page=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>전체목록 시안 - HOHO PLAY</title>{css}{EXTRA_CSS}<style>{MPNS['CSS']}</style></head><body><div id="pcmain">{top}
<div class="sbox"><input id="q" type="search" placeholder="지역·장소·축제 검색 (예: 진천, 해운대, 박물관)" aria-label="검색" autocomplete="off">
<div class="srow"><label class="in"><input type="checkbox" id="indoor"> 🏠 실내 있는 장소만</label><button type="button" id="nearbtn" class="nb">📍 내 주변</button></div><p id="sres" class="nt" style="display:none"></p></div>
<nav class="seg" aria-label="보기 방식"><a href="#">코스 추천</a><a href="#" class="on">전체목록</a><a href="#">지도</a></nav>
<div class="kt" id="kt"><button type="button" class="on" data-v="">전체<em>{len(items)}</em></button><button type="button" data-v="p">📍 장소<em>{nP}</em></button><button type="button" data-v="f">🎪 축제<em>{nF}</em></button></div>
<div class="rgwrap"><p class="rgt">지역</p><div class="rgrid" id="rgrid"><button type="button" class="rg on" data-k="" data-all="1"><span class="ic">🗺️<em>{len(items)}</em></span><span class="lb">전체 ▾</span></button>{''.join(rb(k) for k in ROW)}</div></div>
<div class="fr sb2" id="subw"><p class="rgt">세부 지역</p><div class="subr fc" id="subc"></div></div>
<div class="fr"><p class="rgt">이용요금</p><div class="fc" data-g="fee">{feec}</div></div>
<div class="fr rad" id="rad"><p class="rgt">📍 내 주변 반경</p><div class="fc" data-g="rad"><button type="button" class="on" data-v="">전체</button><button type="button" data-v="3">3km</button><button type="button" data-v="5">5km</button><button type="button" data-v="10">10km</button><button type="button" data-v="30">30km</button></div></div>
<div class="nt nlocn" id="nlocn" style="display:none"></div>
{sheet}
{dtblock}
<div class="nt">🎪 날짜는 <b>축제</b>에만 적용돼요(그 날 열리는 축제만 표시). 장소는 날짜와 상관없이 모두 보여드려요.</div>
<p id="cnt"></p><a class="upd" id="upd" href="#data-notice">🎪 축제 정보는 하루 최대 3회 갱신 · __ST__ <u>자세히 ↓</u></a><div class="kd" id="kd"></div><button type="button" id="more">더 보기</button>
</div>{MPNS['HTML']}</div>
<div class="wrap" id="pcfoot">{FOOT}
<p class="note">※ 시안이라 버튼 일부는 동작하지 않아요. 장소 {nP}곳(숨김 제외)과 현재 진행·예정 축제 {nF}개를 그대로 사용했어요.</p></div>
{JS}{MPNS['JS']}</body></html>'''
json.dump(items,open(WORK+'/items.json','w',encoding='utf-8'),ensure_ascii=False)
page=page.replace('__ST__',ST)
open(WORK+'/list_all_sample.html','w',encoding='utf-8').write(page)
print(len(items),nP,nF,len(page)//1024,'KB',{k:cnt[k] for k in cnt})
