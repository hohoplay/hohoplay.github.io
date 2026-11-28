import json,math,html,re,glob,os
P=[x for x in json.load(open('data/kids_places.json')) if not x.get('hidden')]
byt={}
for p in P: byt.setdefault(p['title'],[]).append(p)
def d(a,b): return math.hypot((float(a['lat'])-float(b['lat']))*111,(float(a['lng'])-float(b['lng']))*88)
# [ADD] 사진 없는 장소는 상세 페이지와 같은 유형별 일러스트(/data/placeholders/*.svg)를 쓴다(규칙은 generate_kids_detail_pages.py 와 동일하게 그 파일을 그대로 불러옴).
import importlib.util as _iu
_sp=_iu.spec_from_file_location('_gkd','scripts/generate_kids_detail_pages.py'); _gkd=_iu.module_from_spec(_sp); _sp.loader.exec_module(_gkd)
def ph_img(p): return '/data/placeholders/'+_gkd.placeholder_category(p)+'.svg'
def img_or_ph(p):
    u=p.get('image') or ''
    return (('https://'+u[7:]) if u.startswith('http://') else u) or ph_img(p)
def img(u): return ('https://'+u[7:]) if (u or '').startswith('http://') else (u or '')
SIDO={'seoul':'서울','busan':'부산','daegu':'대구','incheon':'인천','daejeon':'대전','sejong':'세종','gyeonggi':'경기','gangwon':'강원','chungbuk':'충북','gyeongbuk':'경북','gyeongnam':'경남','chungnam':'충남','jeonbuk':'전북','jeonnam':'전남','gwangju':'광주','ulsan':'울산','jeju':'제주'}
courses={}
for f in sorted(glob.glob('blog/kids-course/*.html')):
    b=os.path.basename(f)
    if b=='index.html': continue
    key=b.split('-')[0]
    s=re.sub(r'<(script|style)[^>]*>.*?</\1>','',open(f,encoding='utf-8').read(),flags=re.S)
    t=re.search(r'<h[12][^>]*>\s*([^<]*?) 코스 한눈에 보기',s)
    area=t.group(1).strip() if t else b
    names=[re.sub('<[^>]+>','',m).strip() for m in re.findall(r'<h[23][^>]*>\s*\d+\.\s*(.*?)</h[23]>',s,flags=re.S)]
    ps=[byt[n][0] for n in names if byt.get(n) and byt[n][0].get('lat')]
    if len(ps)<3: print('SKIP',b,len(names),len(ps)); continue
    courses.setdefault(key,[]).append((b[:-5],key,area,ps,len(names)))
# [ADD] 코스 글에 담기지 않은 장소를 같은 시·군의 가까운 곳끼리 묶어 자동 코스로 채운다(모든 지역에 코스가 나오도록).
_RKS=[('seoul',('서울',)),('daejeon',('대전',)),('daegu',('대구',)),('busan',('부산',)),('incheon',('인천',)),('gyeonggi',('경기',)),('sejong',('세종',)),('gangwon',('강원',)),('chungbuk',('충청북도','충북')),('gyeongbuk',('경상북도','경북')),('gyeongnam',('경상남도','경남')),('chungnam',('충청남도','충남')),('jeonbuk',('전북','전라북도')),('jeonnam',('전라남도','전남')),('gwangju',('광주','전남광주')),('ulsan',('울산',)),('jeju',('제주',))]
def _rk0(a):
    t=(a or ' ').split()[0]
    for k,ps in _RKS:
        if any(t.startswith(x) for x in ps): return k
    return ''
_shown={p['contentid'] for v in courses.values() for x in v for p in x[3][:4]}
_unc={}
for _p in P:
    if _p['contentid'] in _shown or not _p.get('lat') or not _p.get('lng'): continue
    _k=_rk0(_p['addr'])
    if _k: _unc.setdefault(_k,[]).append(_p)
def _sgg(p):
    t=p['addr'].split()
    return t[1] if len(t)>1 else t[0]
for _k,_ps in _unc.items():
    _rem=sorted(_ps,key=lambda p:(_sgg(p),p['title']));_n=0
    while _rem:
        _seed=_rem.pop(0);_grp=[_seed]
        for _lim in (6,12,25):
            _cand=sorted([q for q in _rem if d(_seed,q)<=_lim],key=lambda q:d(_seed,q))
            for q in _cand:
                if len(_grp)>=4: break
                if q not in _grp: _grp.append(q)
            if len(_grp)>=3: break
        if len(_grp)<2:
            continue
        for q in _grp[1:]: _rem.remove(q)
        _n+=1
        courses.setdefault(_k,[]).append((f'auto-{_k}-{_n}',_k,SIDO[_k]+' '+_sgg(_seed),_grp,len(_grp)))
TOPICS=[('mus','🏛️','박물관·전시',('박물관','미술관','전시','기념관','역사관','문화관','아트','뮤지엄','문학관')),
 ('sci','🔬','과학·체험',('과학','천문','체험','로봇','키자니아','우주','생태','교육')),
 ('park','🌳','공원·자연',('공원','수목원','숲','호수','해변','정원','휴양림','산책','저수지','강변','마을','섬')),
 ('lib','📚','도서관·책',('도서관','책','문고')),
 ('play','🎠','놀이·키즈카페',('키즈','놀이','랜드','파크','트램폴린','아이스링크','스케이트','플레이','월드')),
 ('zoo','🐠','동물·수족관',('동물','수족관','아쿠아','아쿠아리움','곤충','펭귄','사파리','해양'))]
def topics_of(title):
    return [k for k,_,_,kw in TOPICS if any(w in title for w in kw)]
# 주차 가능 확인 장소: 한국관광공사 TourAPI 공식 부가정보(주차시설)가 "가능"인 곳만 (AI가 쓴 글·후기는 쓰지 않는다)
def _pk_load():
    try:
        d=json.load(open('data/kids_notes_draft.json',encoding='utf-8'))
    except Exception:
        return set()
    out=set()
    for k,v in d.items():
        if v.get('model')!='tourapi': continue
        for ek,ev in (v.get('evidence') or {}).items():
            if ek.startswith('parking') and not ek.startswith('parkingfee') and '가능' in str(ev) and '불가' not in str(ev):
                out.add(k)
    return out
PKSET=_pk_load()
def fee_of(ps):
    tags=[p.get('costTag') or '' for p in ps]
    if all(t=='완전무료' for t in tags): return 'free'
    if any(t.startswith('유료') for t in tags): return 'paid'
    return 'etc'
def card(slug,key,area,allp,n_all):
    top=allp[:4]
    stops=[top[0]]; rest=top[1:]
    while rest:
        n=min(rest,key=lambda p:d(stops[-1],p)); rest.remove(n); stops.append(n)
    km=[d(stops[i],stops[i+1]) for i in range(len(stops)-1)]
    free=sum(1 for p in allp if p.get('costTag')=='완전무료')
    li=''
    for i,x in enumerate(stops):
        tag={'실내':'🏠 실내','실외':'🌳 실외','실내외':'🔀 실내외'}.get(x.get('placeType'),'')
        cost={'완전무료':'무료','유료':'유료'}.get(x.get('costTag'),'')
        li+=f'<li><a href="/festival/detail/{x["contentid"]}.html"><span class="n">{i+1}</span><span class="t">{html.escape(x["title"])}</span><span class="m">{tag}{" · "+cost if cost else ""}</span></a></li>'
        if i<len(km): li+=f'<li class="mv">↓ 약 {km[i]:.1f}km</li>'
    th=''.join(f'<i style="background-image:url(\'{img_or_ph(x)}\')"></i>' for x in (stops+stops)[:3])
    area_short=area.split(' ',1)[1] if ' ' in area else area
    tps=sorted({t for x in stops for t in topics_of(x['title'])}); fee=fee_of(stops)
    return f'''<article class="card" data-id="{slug}" data-stops="{html.escape(json.dumps([[float(x['lat']),float(x['lng']),x['title']] for x in stops],ensure_ascii=False))}" data-lat="{sum(float(x['lat']) for x in stops)/len(stops):.5f}" data-lng="{sum(float(x['lng']) for x in stops)/len(stops):.5f}" data-in="{sum(1 for x in stops if x.get('placeType')=='실내')}" data-ar="{html.escape(area_short)}" data-tp="{' '.join(tps)}" data-fee="{fee}" data-pk="{sum(1 for x in stops if x['contentid'] in PKSET)}"><div class="thumbs">{th}</div><div class="body"><div class="reg">{html.escape(area)}{" · 자동 추천" if slug.startswith("auto-") else ""}</div><h3>{html.escape(area_short)} 하루 코스</h3>
<p class="dist"></p><p class="inb">🏠 이 코스 {len(stops)}곳 중 실내 {sum(1 for x in stops if x.get('placeType')=='실내')}곳 · 실내외 {sum(1 for x in stops if x.get('placeType')=='실내외')}곳</p><p class="sub">등록 {n_all}곳 중 대표 {len(stops)}곳 · 무료 {free}곳</p><ol>{li}</ol>
<button type="button" class="go plan" data-course="{slug}">📅 이 코스로 일정표 만들기</button><a class="go2" href="/festival/?region={key}">🗺️ 지도로 보기</a>{"" if slug.startswith("auto-") else f'<a class="more" href="/blog/kids-course/{slug}.html">코스 전체 {n_all}곳 보기 →</a>'}</div></article>'''
ICON={'seoul': '🗼', 'daejeon': '🔬', 'daegu': '🍎', 'busan': '🌉', 'incheon': '✈️', 'gyeonggi': '🏙️', 'sejong': '🏛️', 'gangwon': '⛰️', 'chungbuk': '🌿', 'gyeongbuk': '🏯', 'gyeongnam': '🌊', 'chungnam': '🌾', 'jeonbuk': '🍚', 'jeonnam': '🌴', 'gwangju': '🎨', 'ulsan': '🐋', 'jeju': '🍊'}
TOP5=['seoul','daejeon','daegu','busan','incheon']
ROW=TOP5+['gyeonggi','sejong','gangwon','chungbuk','gyeongbuk','gyeongnam','chungnam','jeonbuk','jeonnam','gwangju','ulsan','jeju']
secs='';chips='';tot=0;rbtn={};subrows=''
for key,lab in SIDO.items():
    v=courses.get(key)
    if not v: continue
    tot+=len(v)
    rbtn[key]=f'<button type="button" class="rg" data-k="{key}"><span class="ic">{ICON[key]}<em>{len(v)}</em></span><span class="lb">{lab}</span></button>'
    if len(v)>1:
        _ac={}
        for x in v:
            _n=x[2].split(" ",1)[1] if " " in x[2] else x[2]
            _ac[_n]=_ac.get(_n,0)+1
        _it=sorted(_ac.items(),key=lambda t:-t[1]); _fold=len(_it)>6
        subrows+=f'<div class="subr fc{" xf fold" if _fold else ""}" data-g="ar"><button type="button" class="on" data-a="">{SIDO[key]} 전체 <span class="cn">{len(v)}</span></button>'+''.join(f'<button type="button" class="{"xh" if (_fold and i>=5) else ""}" data-a="{html.escape(n)}">{html.escape(n)} <span class="cn">{c}</span></button>' for i,(n,c) in enumerate(_it))+(f'<button type="button" class="xmore" data-x="1" data-n="{len(_it)-5}">+ {len(_it)-5}곳 전체 보기 ▾</button>' if _fold else '')+'</div>'
    sub=subrows; subrows=''
    shown={p['contentid'] for x in v for p in x[3][:4]}
    tot_k=sum(1 for p in P if _rk0(p['addr'])==key)
    cov=f'<p class="nt cov">🗺 이 지역 아이랑 장소 <b>{tot_k}곳</b> 중 <b>{len(shown)}곳</b>이 코스에 담겨 보여요. 나머지는 코스에 못 담았거나 그날 쉬는 곳이에요. <a href="/festival/?region={key}">전체 목록으로 보기</a></p>'
    secs+=f'<section id="r-{key}"><h2>{lab} <small>코스 {len(v)}개</small></h2>{sub}{cov}<div class="grid">'+''.join(card(*x) for x in v)+'</div></section>'
tpl=open(ASSET+'/course_cards_sample.html',encoding='utf-8').read()
css=re.search(r'<style>.*?</style>',tpl,flags=re.S).group(0).replace('</style>','''.chips{position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:5}.chip{text-decoration:none}
section{scroll-margin-top:56px}h2{font-size:19px;margin:22px 0 10px}h2 small{font-size:13px;color:var(--sub);font-weight:700;margin-left:6px}
.go.plan{width:100%;border:0;font-family:inherit;cursor:pointer}.go2{display:block;text-align:center;margin-top:6px;border:1px solid var(--pri);color:var(--pri);text-decoration:none;border-radius:10px;padding:9px;font-size:13px;font-weight:800}
.rgwrap{margin:0 0 12px}.rgt{margin:0 0 8px;font-size:13px;font-weight:800;color:var(--sub)}
.rgrid{display:grid;grid-template-columns:repeat(9,20%);gap:12px 0;overflow-x:auto;overflow-y:hidden;padding:8px 0 4px;max-width:640px;scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch;scrollbar-width:none}.rgrid::-webkit-scrollbar{display:none}.rgrid>.rg{scroll-snap-align:start}#rgrid .ic{width:42px;height:42px;font-size:21px}#rgrid .ic em{right:-8px;top:-6px;min-width:17px;height:17px;padding:0 3px;font-size:10px}#rgrid .lb{font-size:12px;white-space:nowrap}.rgh{margin-left:6px;font-size:11px;font-weight:600;color:var(--sub);opacity:.85}.rg{border:0;background:none;padding:0;font-family:inherit;color:var(--ink);cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:4px}
.rg .ic{position:relative;width:46px;height:46px;border-radius:50%;background:var(--card);border:2px solid var(--line);display:flex;align-items:center;justify-content:center;font-size:22px}
.rg .ic em{position:absolute;right:-6px;top:-6px;min-width:18px;height:18px;padding:0 4px;border-radius:9px;background:#94a3b8;color:#fff;font-size:11px;font-style:normal;font-weight:800;display:flex;align-items:center;justify-content:center}
.rg .lb{font-size:12px;font-weight:700}.rg.on .ic{border-color:#e11d48;background:#fff1f2}.rg.on .ic em{background:#e11d48}.rg.on .lb{color:#e11d48}
.rgrid.sh{grid-template-columns:repeat(4,minmax(0,1fr));gap:14px 6px;overflow:visible;max-width:none;padding:0}
.ov{position:fixed;inset:0;background:rgba(0,0,0,.45);opacity:0;pointer-events:none;transition:opacity .25s;z-index:50}.ov.on{opacity:1;pointer-events:auto}
.sheet{position:fixed;left:0;right:0;bottom:0;max-width:640px;margin:0 auto;background:var(--bg);border-radius:20px 20px 0 0;padding:14px 16px 24px;transform:translateY(105%);transition:transform .3s cubic-bezier(.2,.8,.2,1);z-index:51;max-height:80vh;overflow:auto;box-shadow:0 -8px 30px rgba(0,0,0,.25)}.sheet.on{transform:translateY(0)}
.sh-h{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}.sh-h b{font-size:16px}.sh-x{border:0;background:var(--soft);color:var(--ink);width:32px;height:32px;border-radius:50%;font-size:16px;cursor:pointer}
.sh-all{width:100%;margin-top:16px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:12px;padding:12px;font-weight:800;font-family:inherit;cursor:pointer}
.wx{margin:0 0 12px}.sw{display:flex;align-items:center;gap:10px;font-size:13px;font-weight:800;cursor:pointer}.sw small{font-weight:600;color:var(--sub)}.sw input{display:none}
.tg{width:42px;height:24px;border-radius:12px;background:#cbd5e1;position:relative;flex:none;transition:.2s}.tg:after{content:"";position:absolute;left:3px;top:3px;width:18px;height:18px;border-radius:50%;background:#fff;transition:.2s}.sw input:checked+.tg{background:#2563eb}.sw input:checked+.tg:after{left:21px}
.wxn{margin:8px 0 0;padding:10px 12px;border-radius:10px;background:#dbeafe;color:#1e3a8a;font-size:13px;line-height:1.6}.inb{display:none;margin:0 0 6px;font-size:12px;font-weight:800;color:#1d4ed8}body.rain .inb{display:block}
.dt{margin:0 0 12px}.dbtn{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.dbtn button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:12px;padding:9px 4px;font-family:inherit;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:2px}.dbtn button b{font-size:15px}.dbtn button span{font-size:11px;color:var(--sub);font-weight:700}.dbtn button.on{background:#4f46e5;border-color:#4f46e5;color:#fff}.dbtn button.on span{color:#e0e7ff}#dnote{margin:8px 0 0}
.cal{display:flex;gap:8px;margin-top:8px}.cal button{flex:none;width:44px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:12px;font-size:14px;cursor:pointer}
.cin{position:relative;flex:1;border:1px solid var(--line);background:var(--card);border-radius:12px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px;min-height:42px;cursor:pointer}.cin input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer}.cin.on{border-color:#4f46e5;color:#4f46e5;background:#eef2ff}
.nb{margin-left:auto;border:1px solid #4f46e5;background:#fff;color:#4f46e5;border-radius:999px;padding:8px 14px;font-size:13px;font-weight:800;font-family:inherit;cursor:pointer;white-space:nowrap}.nb.on{background:#4f46e5;color:#fff}
.rad{display:none;margin:0 0 10px}.rad p{margin:0 0 6px}.dist{display:none;margin:0 0 6px;font-size:12px;font-weight:800;color:#be185d}body.near .dist{display:block}.nlocn{margin:0 0 8px}
.rch{font-size:19px;margin:26px 0 4px}.rcs{margin:0 0 12px;font-size:13px;color:var(--sub);line-height:1.6}.rcg{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-bottom:6px}
.rc{display:flex;flex-direction:column;gap:3px;padding:14px;background:var(--card);border:1px solid var(--line);border-radius:14px;text-decoration:none;color:var(--ink)}.rc b{font-size:15px}.rc span{font-size:12px;color:var(--sub)}.rc:active{background:var(--soft)}
.rg.z,.fc button.z{opacity:.4}.pkn{margin:4px 0 0;font-size:11px;color:var(--sub)}.subr{padding:2px 0 8px}.subr.fc{flex-wrap:wrap;overflow:visible;gap:8px}.subr.fc button{flex:0 0 auto}.subr .xmore{display:none}.subr.fold button.xh{display:none}.subr.xf .xmore{display:inline-block;border-style:dashed}.shf{margin-bottom:6px}.fr{margin:0 0 10px}.fr .rgt{margin:0 0 6px}.fc{display:flex;gap:6px;overflow-x:auto;padding-bottom:4px;scrollbar-width:none}.fc::-webkit-scrollbar{display:none}
.fc button{flex:0 0 auto;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:7px 12px;font-size:13px;font-weight:700;font-family:inherit;cursor:pointer;white-space:nowrap}.fc button.on{background:#e11d48;border-color:#e11d48;color:#fff}
.sbox{margin:0 0 12px}.sbox input[type=search]{width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--ink);font-size:15px;font-family:inherit}
.srow{display:flex;gap:8px;margin-top:8px;align-items:center}.srow select{flex:1;padding:10px;border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--ink);font-size:14px;font-family:inherit}.in{font-size:13px;font-weight:700;white-space:nowrap}
.wc{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:0 0 12px;padding:12px 14px;border-radius:12px;background:#fef3c7;color:#92400e;font-size:14px;font-weight:800;text-decoration:none}.wc b{color:#be185d;white-space:nowrap}
.nt{margin:0 0 8px;padding:8px 10px;border-radius:8px;background:var(--soft);color:var(--pri);font-size:12px;line-height:1.6}.nt a{color:var(--pri);font-weight:800}.cov{background:#ecfdf5;color:#065f46;margin:0 0 10px}.cov a{color:#047857}
.more{display:block;text-align:center;margin-top:8px;font-size:12px;font-weight:700;color:var(--pri);text-decoration:none}
</style>''')
JS=r'''<script>
(function(){var q=document.getElementById('q'),ind=document.getElementById('indoor'),res=document.getElementById('sres'),st='',tp='',fee='',pk='';
var cards=[].slice.call(document.querySelectorAll('.card')),secs=[].slice.call(document.querySelectorAll('section[id^=r-]'));
var bs=[].slice.call(document.querySelectorAll('.rg[data-k]')),sh=document.getElementById('sheet'),ov=document.getElementById('ov');
cards.forEach(function(c){c._t=(c.textContent||'').replace(/\s+/g,'').toLowerCase();c._in=/실내/.test(c.textContent);c._tp=' '+(c.getAttribute('data-tp')||'')+' ';c._fee=c.getAttribute('data-fee');c._pk=+c.getAttribute('data-pk')||0;});
secs.forEach(function(s){s._ar='';});
function sheet(on){sh.classList.toggle('on',on);ov.classList.toggle('on',on);}
function run(){var w=q.value.replace(/\s+/g,'').toLowerCase(),n=0,sub=false;
var tot0=0;secs.forEach(function(sec){var vis=0,c0=0,hc=0,am={},fo=sec.querySelector('.subr.fold'),hs={};if(fo)[].forEach.call(fo.querySelectorAll('button.xh'),function(x){hs[x.getAttribute('data-a')]=1});[].forEach.call(sec.querySelectorAll('.card'),function(c){var b0=(!w||c._t.indexOf(w)>-1)&&(!ind.checked||c._in)&&(!near||!rad||c._km<=rad)&&(!tp||c._tp.indexOf(' '+tp+' ')>-1)&&(!fee||c._fee===fee)&&(!pk||c._pk>0);var hid=!!(fo&&!sec._ar&&hs[c.getAttribute('data-ar')]);var ok=b0&&!hid&&(!sec._ar||c.getAttribute('data-ar')===sec._ar);if(b0&&hid)hc++;if(b0){c0++;var a0=c.getAttribute('data-ar');am[a0]=(am[a0]||0)+1}c.style.display=ok?'':'none';if(ok){vis++;n++}});sec.style.display=(vis||sec._ar)?'':'none';if(sec._ar)sub=true;
[].forEach.call(sec.querySelectorAll('.subr button'),function(b){if(b.hasAttribute('data-x'))return;var a=b.getAttribute('data-a'),n=a?(am[a]||0):c0,e=b.querySelector('.cn');if(e)e.textContent=n;if(a)b.classList.toggle('z',!n)});
var xm=sec.querySelector('.xmore');if(xm)xm.textContent=fo?('+ '+xm.getAttribute('data-n')+'곳'+(hc?' · 코스 '+hc+'개':'')+' 전체 보기 ▾'):'접기 ▴';
tot0+=c0;[].forEach.call(document.querySelectorAll('.rg[data-k="'+sec.id.slice(2)+'"]'),function(b){var e=b.querySelector('em');if(e)e.textContent=c0;b.classList.toggle('z',!c0)});});
[].forEach.call(document.querySelectorAll('.rg[data-all] em'),function(e){e.textContent=tot0});
if(w||tp||fee||pk||ind.checked||sub){res.style.display='';res.innerHTML=n?('검색 결과 <b>'+n+'개</b> 코스'):'맞는 코스가 없어요. 조건을 바꿔 보세요.';}else res.style.display='none';
bs.forEach(function(b){var k=b.getAttribute('data-k');b.classList.toggle('on',b.hasAttribute('data-all')?st==='':k===st);});}
bs.forEach(function(b){b.addEventListener('click',function(){var k=b.getAttribute('data-k');
if(b.hasAttribute('data-all')){sheet(true);return;}
st=k;sheet(false);run();var s=document.getElementById('r-'+k);if(s)s.scrollIntoView({behavior:'smooth'});});});
document.querySelector('.sh-all').addEventListener('click',function(){st='';sheet(false);run();window.scrollTo({top:0,behavior:'smooth'});});
document.getElementById('shx').addEventListener('click',function(){sheet(false)});ov.addEventListener('click',function(){sheet(false)});
document.addEventListener('click',function(e){var b=e.target.closest('.fc button');if(!b)return;
if(b.hasAttribute('data-x')){var sr=b.parentNode,sc=b.closest('section');if(sr.classList.contains('fold')){sr.classList.remove('fold');}else{sr.classList.add('fold');var ob=sr.querySelector('button.on');if(ob&&ob.classList.contains('xh')){sc._ar='';[].forEach.call(sr.children,function(x){x.classList.toggle('on',x===sr.children[0])});}}run();return;}
if(b.parentNode.classList.contains('subr')){var sec=b.closest('section');sec._ar=b.getAttribute('data-a');[].forEach.call(b.parentNode.children,function(x){x.classList.toggle('on',x===b)});run();return;}
var g=b.parentNode.getAttribute('data-g'),v=b.getAttribute('data-v');
if(g==='rad'){rad=+v||0}else if(g==='tp')tp=v;else if(g==='pk')pk=v;else fee=v;[].forEach.call(document.querySelectorAll('.fc[data-g='+g+']'),function(el){[].forEach.call(el.children,function(x){x.classList.toggle('on',x.getAttribute('data-v')===v)})});run();});
secs.forEach(function(sec){var g=sec.querySelector('.grid');g._o=[].slice.call(g.children);});
document.getElementById('rain').addEventListener('change',function(){var on=this.checked;document.body.classList.toggle('rain',on);document.getElementById('wxn').style.display=on?'':'none';
secs.forEach(function(sec){var g=sec.querySelector('.grid'),a=g._o.slice();if(on)a.sort(function(x,y){return (+y.getAttribute('data-in'))-(+x.getAttribute('data-in'))||g._o.indexOf(x)-g._o.indexOf(y)});a.forEach(function(c){g.appendChild(c)});});});
(function(){var W=['일','월','화','수','목','금','토'],now=new Date(),late=(now.getHours()*60+now.getMinutes())>=1110;
function add(n,base){var d=new Date(base||now);d.setDate(d.getDate()+n);return d}
function f(d){return (d.getMonth()+1)+'월 '+d.getDate()+'일('+W[d.getDay()]+')'}
function iso(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
var sat=add((6-now.getDay()+7)%7),sun=add((6-now.getDay()+7)%7+1);if(now.getDay()===0){sat=add(-1);sun=add(0)}
var lab={today:f(now),tom:f(add(1)),wk:(sat.getMonth()+1)+'/'+sat.getDate()+'·'+sun.getDate()+' 토·일'};
var btns=[].slice.call(document.querySelectorAll('#dbtn button')),note=document.getElementById('dnote'),pk=document.getElementById('dpick'),dl=document.getElementById('dlab'),cin=document.querySelector('.cin'),cur=null;
pk.min=iso(now);pk.max=iso(add(60));
btns.forEach(function(b){b.querySelector('span').textContent=lab[b.getAttribute('data-d')]});
function pick(k,auto){btns.forEach(function(b){b.classList.toggle('on',b.getAttribute('data-d')===k)});cin.classList.remove('on');dl.textContent='📆 날짜 직접 선택';pk.value='';cur=null;
var t={today:late?'🌙 저녁 6시 반이 지나 오늘 갈 수 있는 시간이 짧아요. 운영시간을 꼭 확인하세요. ('+f(now)+' 기준)':'📅 '+f(now)+' 운영시간 기준으로 보여드려요.',
tom:(auto?'🌙 저녁 6시 반이 지나 내일 코스를 먼저 보여드려요. ':'')+'📅 '+f(add(1))+' 운영시간 기준이에요.',
wk:'📅 주말('+f(sat)+'·'+f(sun)+') 운영시간 기준이에요. 주말에만 여는 곳·휴관일은 방문 전 확인하세요.'}[k];note.textContent=t;}
function setDate(d){var z=new Date(now.getFullYear(),now.getMonth(),now.getDate());if(d<z)d=z;var mx=add(60);if(d>mx)d=mx;cur=d;btns.forEach(function(b){b.classList.remove('on')});cin.classList.add('on');dl.textContent='📆 '+f(d);pk.value=iso(d);
var wk=d.getDay()===0||d.getDay()===6;note.textContent='📅 '+f(d)+' 운영시간 기준이에요.'+(wk?' 주말이라 평일과 운영시간이 다른 곳이 있어요.':' 평일엔 월요일 휴관인 곳이 많으니 방문 전 확인하세요.');}
btns.forEach(function(b){b.addEventListener('click',function(){pick(b.getAttribute('data-d'),false)})});
pk.addEventListener('change',function(){if(pk.value){var p=pk.value.split('-');setDate(new Date(+p[0],+p[1]-1,+p[2]))}});
document.getElementById('dprev').addEventListener('click',function(){var base=cur||(function(){var a=btns.filter(function(b){return b.classList.contains('on')})[0];var k=a&&a.getAttribute('data-d');return k==='tom'?add(1):k==='wk'?sat:now})();setDate(add(-1,base))});
document.getElementById('dnext').addEventListener('click',function(){var base=cur||(function(){var a=btns.filter(function(b){return b.classList.contains('on')})[0];var k=a&&a.getAttribute('data-d');return k==='tom'?add(1):k==='wk'?sat:now})();setDate(add(1,base))});
pick(late?'tom':'today',late);})();

/* 내 주변 */
var near=false,pos=null,rad=0,nearSec=null,nbtn=document.getElementById('nearbtn');
cards.forEach(function(c,i){c._home=c.parentNode;c._i=i;c._la=+c.getAttribute('data-lat');c._ln=+c.getAttribute('data-lng');});
function hav(a,b,c,d){var R=6371,t=Math.PI/180,x=(c-a)*t,y=(d-b)*t,h=Math.sin(x/2)*Math.sin(x/2)+Math.cos(a*t)*Math.cos(c*t)*Math.sin(y/2)*Math.sin(y/2);return 2*R*Math.asin(Math.sqrt(h));}
function nearOn(p,fake){pos=p;near=true;document.body.classList.add('near');nbtn.classList.add('on');nbtn.textContent='📍 내 주변 ✕';
var nl=document.getElementById('nlocn');nl.style.display='';nl.textContent=fake?'📍 시안에서는 위치를 못 가져와 서울시청 기준으로 보여드려요. 실제로는 내 위치 기준이에요.':'📍 내 위치 기준 가까운 코스 순서예요. (위치는 이 기기에서만 쓰고 저장하지 않아요)';
document.getElementById('rad').style.display='block';
if(!nearSec){nearSec=document.createElement('section');nearSec.id='r-near';nearSec.innerHTML='<h2>📍 내 주변 코스</h2><div class="grid"></div>';secs[0].parentNode.insertBefore(nearSec,secs[0]);secs.unshift(nearSec);nearSec._ar='';}
var g=nearSec.querySelector('.grid');cards.slice().forEach(function(c){c._km=hav(pos[0],pos[1],c._la,c._ln);c.querySelector('.dist').textContent='📍 내 위치에서 약 '+c._km.toFixed(c._km<10?1:0)+'km';});
cards.slice().sort(function(a,b){return a._km-b._km}).forEach(function(c){g.appendChild(c)});run();window.scrollTo({top:document.getElementById('r-near').getBoundingClientRect().top+scrollY-60,behavior:'smooth'});}
function nearOff(){near=false;pos=null;rad=0;document.body.classList.remove('near');nbtn.classList.remove('on');nbtn.textContent='📍 내 주변';document.getElementById('rad').style.display='none';document.getElementById('nlocn').style.display='none';
cards.slice().sort(function(a,b){return a._i-b._i}).forEach(function(c){c._home.appendChild(c)});if(nearSec){nearSec.parentNode.removeChild(nearSec);secs.shift();nearSec=null;}
[].forEach.call(document.querySelectorAll('#rad .fc button'),function(x){x.classList.toggle('on',!x.getAttribute('data-v'))});run();}
nbtn.addEventListener('click',function(){if(near){nearOff();return;}var fb=function(){nearOn([37.5665,126.9780],true)};
if(!navigator.geolocation){fb();return;}var done=false;var t=setTimeout(function(){if(!done){done=true;fb()}},4000);
navigator.geolocation.getCurrentPosition(function(p){if(done)return;done=true;clearTimeout(t);nearOn([p.coords.latitude,p.coords.longitude],false)},function(){if(done)return;done=true;clearTimeout(t);fb()},{timeout:3500});});
document.addEventListener('click',function(e){var a=e.target.closest('.rc');if(!a)return;var b=document.querySelector('.rg[data-k='+a.getAttribute('data-k')+']');if(b){e.preventDefault();b.click();}});
q.addEventListener('input',run);ind.addEventListener('change',run);run();})();
</script>'''
TOOLS=open(ASSET+'/tools_part.html',encoding='utf-8').read()
FOOT=open(ASSET+'/footer_part.html',encoding='utf-8').read()

_REG=[('seoul','서울',('서울',)),('daejeon','대전',('대전',)),('daegu','대구',('대구',)),('busan','부산',('부산',)),('incheon','인천',('인천',)),('gyeonggi','경기',('경기',)),('sejong','세종',('세종',)),('gangwon','강원',('강원',)),('chungbuk','충북',('충청북도','충북')),('gyeongbuk','경북',('경상북도','경북')),('gyeongnam','경남',('경상남도','경남')),('chungnam','충남',('충청남도','충남')),('jeonbuk','전북',('전북','전라북도')),('jeonnam','전남',('전라남도','전남')),('gwangju','광주',('광주','전남광주')),('ulsan','울산',('울산',)),('jeju','제주',('제주',))]
def _rk(a):
    t=(a or ' ').split()[0]
    for k,_,ps in _REG:
        if any(t.startswith(p) for p in ps): return k
    return ''
_pc={}
for _p in P: _pc[_rk(_p['addr'])]=_pc.get(_rk(_p['addr']),0)+1
_cards=''.join(f'<a class="rc" href="/festival/?region={k}" data-k="{k}"><b>{lab} 아이랑 나들이</b><span>장소 {_pc.get(k,0)}곳'+(f' · 코스 {len(courses[k])}개' if k in courses else '')+'</span></a>' for k,lab,_ in _REG)
REGCARDS=f'<section id="region-cards" aria-label="지역별 아이랑 갈만한 곳 모음"><h2 class="rch">🗺️ 지역별 아이랑 갈만한 곳 모음</h2><p class="rcs">전국 17개 시·도, 장소 {len(P)}곳. 지역을 누르면 그 지역 코스·장소로 이동해요.</p><div class="rcg">{_cards}</div></section>\n'
open(WORK+'/regcards.html','w',encoding='utf-8').write(REGCARDS)
RCCSS=''
FOOT=REGCARDS+FOOT
MPNS={}
exec(open(ASSET+'/mappane.py',encoding='utf-8').read(),MPNS)
page=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>코스 카드 시안(전체 지역) - HOHO PLAY</title>{css}<style>{MPNS['CSS']}</style></head><body><div id="pcmain"><div class="wrap">
<span class="badge">디자인 시안 · 실제 데이터 · 전체 {tot}개 코스</span>
<h1>🧒🎪 아이랑 나들이 지도</h1>
<p class="lead">서울·대전·대구·부산·광주를 비롯한 전국 어디서나, 아이랑 가볼만한 곳과 지금 열리는 축제를 한 지도에서 찾아보세요. <a href="#about-map" style="color:var(--pri);font-weight:700;white-space:nowrap">이용 안내 ↓</a></p>
{TOOLS}
<div class="sbox"><input id="q" type="search" placeholder="지역·장소 검색 (예: 진천, 해운대, 박물관)" aria-label="지역·장소 검색" autocomplete="off">
<div class="srow"><label class="in"><input type="checkbox" id="indoor"> 🏠 실내 있는 코스만</label><button type="button" id="nearbtn" class="nb">📍 내 주변</button></div>
<p id="sres" class="nt" style="display:none"></p></div>
<div class="wx"><label class="sw"><input type="checkbox" id="rain"><span class="tg"></span><span>☔ 날씨 궂은 날 미리보기 <small>(시안용 스위치)</small></span></label><p class="wxn" id="wxn" style="display:none">☔ 오늘 비 예보 <b>(강수확률 70%)</b> — <b>실내 코스를 먼저</b> 보여드려요. 각 지역에서 실내 장소가 많은 코스가 위로 올라옵니다. <small style="display:block;margin-top:4px;color:#475569">※ 70%는 시안용 예시 숫자예요. 실제로는 선택한 날짜 낮(9~21시) 최대 강수확률이 들어가요.</small></p></div>
<nav class="seg" aria-label="보기 방식"><a href="#" class="on">코스 추천</a><a href="#">전체목록</a><a href="#">지도</a></nav>
<div class="rgwrap"><p class="rgt">지역<small class="rgh">옆으로 밀어서 더 보기 →</small></p><div class="rgrid" id="rgrid"><button type="button" class="rg on" data-k="" data-all="1"><span class="ic">🗺️<em>{tot}</em></span><span class="lb">전체 ▾</span></button>{''.join(rbtn[k] for k in ROW if k in rbtn)}</div></div>
<div class="fr"><p class="rgt">이용요금</p><div class="fc" data-g="fee"><button type="button" class="on" data-v="">전체</button><button type="button" data-v="free">🆓 전부 무료</button><button type="button" data-v="paid">💳 유료 장소 포함</button><button type="button" data-v="etc">❔ 요금 확인 필요</button></div></div><div class="fr"><p class="rgt">주차</p><div class="fc" data-g="pk"><button type="button" class="on" data-v="">전체</button><button type="button" data-v="1">🅿️ 주차 가능한 곳 포함</button></div><p class="pkn">공식 자료에서 주차 가능으로 확인된 곳만 걸러요. 자료가 없는 곳은 빠질 수 있어요.</p></div>
<div class="ov" id="ov"></div><div class="sheet" id="sheet" role="dialog" aria-label="전체 지역"><div class="sh-h"><b>📍 전체 지역</b><button type="button" class="sh-x" id="shx" aria-label="닫기">✕</button></div><div class="shf"><div class="fr"><p class="rgt">주제</p><div class="fc" data-g="tp"><button type="button" class="on" data-v="">전체</button>{''.join(f'<button type="button" data-v="{k}">{ic} {lb}</button>' for k,ic,lb,_ in TOPICS)}</div></div>
<div class="fr"><p class="rgt">이용요금</p><div class="fc" data-g="fee"><button type="button" class="on" data-v="">전체</button><button type="button" data-v="free">🆓 전부 무료</button><button type="button" data-v="paid">💳 유료 장소 포함</button><button type="button" data-v="etc">❔ 요금 확인 필요</button></div></div><div class="fr"><p class="rgt">주차</p><div class="fc" data-g="pk"><button type="button" class="on" data-v="">전체</button><button type="button" data-v="1">🅿️ 주차 가능한 곳 포함</button></div><p class="pkn">공식 자료에서 주차 가능으로 확인된 곳만 걸러요. 자료가 없는 곳은 빠질 수 있어요.</p></div>
</div><p class="rgt">지역</p><div class="rgrid sh" id="shgrid">{''.join(rbtn[k] for k in rbtn)}</div><button type="button" class="sh-all" data-k="">🗺️ 전국 전체 코스 보기 ({tot})</button></div>
<div class="fr rad" id="rad"><p class="rgt">📍 내 주변 반경</p><div class="fc" data-g="rad"><button type="button" class="on" data-v="">전체</button><button type="button" data-v="5">5km</button><button type="button" data-v="10">10km</button><button type="button" data-v="30">30km</button><button type="button" data-v="60">60km</button></div></div>
<div class="nt nlocn" id="nlocn" style="display:none"></div>
<div class="dt"><p class="rgt">언제 가나요?</p><div class="dbtn" id="dbtn"><button type="button" data-d="today"><b>오늘</b><span></span></button><button type="button" data-d="tom"><b>내일</b><span></span></button><button type="button" data-d="wk"><b>주말</b><span></span></button></div><div class="cal"><button type="button" id="dprev" aria-label="전날">◀</button><label class="cin" for="dpick"><span id="dlab">📆 날짜 직접 선택</span><input type="date" id="dpick"></label><button type="button" id="dnext" aria-label="다음날">▶</button></div><p class="nt nt-late" id="dnote"></p></div>
<div class="nt">⏱ 예상 시간은 운영시간과 이동시간(직선거리 기준)으로 계산한 대략치예요. 방문 전 공식 운영시간을 꼭 확인하세요.</div>
<div class="nt">📷 사진은 직접 퍼오지 않고 공공데이터(한국관광공사 TourAPI)에 등록된 사진만 불러와요. "사진 준비 중"인 곳은 자료에 사진이 올라오면 하루 3번 자동 갱신 때 채워져요.</div>
{secs}
</div>{MPNS['HTML']}</div>
<div class="wrap" id="pcfoot">{FOOT}
<p class="note">※ 시안이라 탭은 아직 동작하지 않아요. 코스 묶음은 지금 사이트의 구·군별 코스 글 {tot}개를 그대로 쓰고, 카드에는 각 코스의 대표 4곳(코스 글에 등록된 순서 앞쪽)을 가까운 순서로 다시 배열했어요. 거리는 직선거리예요.</p>
</div>
{JS}{MPNS['JS']}</body></html>'''

_out=[]
for _k,_v in courses.items():
    for (_slug,_key,_area,_ps,_n) in _v:
        _top=_ps[:4]; _st=[_top[0]]; _rest=_top[1:]
        while _rest:
            _x=min(_rest,key=lambda p:d(_st[-1],p)); _rest.remove(_x); _st.append(_x)
        _out.append(dict(slug=_slug,k=_key,area=_area,n=_n,st=[dict(id=x['contentid'],t=x['title'],la=float(x['lat']),ln=float(x['lng']),pt=x.get('placeType') or '',c=x.get('costTag') or '',im=img(x.get('image'))) for x in _st]))
json.dump(_out,open(WORK+'/courses.json','w',encoding='utf-8'),ensure_ascii=False)
open(WORK+'/course_cards_all.html','w',encoding='utf-8').write(page)
print(tot,page.count('<article'),len(page)//1024,'KB',{k:len(v) for k,v in courses.items()})
