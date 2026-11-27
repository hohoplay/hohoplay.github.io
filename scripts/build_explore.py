#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_explore.py — festival/index.html (아이랑 갈만한 곳·축제 : 코스 추천 + 전체목록 통합 페이지) 생성

[ADD] 2026-11-27
데이터(data/kids_places.json, data/festivals.json)와 코스 글(blog/kids-course/*.html)에서
  · 코스 추천 카드(전국 시·도별, 같은 구·군 장소 묶음)
  · 전체목록(아이랑 장소 + 진행 중·예정 축제) 첫 화면 24개 + 전체 JSON
을 읽어 festival/index.html 한 파일로 만든다. 손으로 고치지 말고 이 스크립트로 다시 만들 것.

  사용법:   python3 scripts/build_explore.py            (저장소 루트에서)
            python3 scripts/build_explore.py --root /path/to/repo

  내부 구성: scripts/explore/gen_all.py(코스 보기) → gen_list.py(전체목록 보기) → gen_merge.py(두 보기 합치기)
             → 이 파일의 post()가 실제 서비스용으로 다듬음(머리말·메뉴·푸터·날씨·내 위치·일정표 연결).
  이 스크립트는 다른 자동화(fetch_data.py, check_site_counts.py 등)가 쓰는 파일을 건드리지 않는다.
"""
import argparse, datetime, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.join(HERE, 'explore')
OUT_REL = 'festival/index.html'      # 2026-11-27: 이 통합 페이지가 /festival/ 의 새 첫 화면
MAP_REL = 'festival/map.html'        # 기존 지도 페이지(메뉴·푸터 블록을 여기서 읽는다)
DOMAIN = 'https://hohoplaylab.com'


def run_generators(root, work):
    os.chdir(root)
    for g in ('gen_all.py', 'gen_list.py', 'gen_merge.py'):
        ns = {'ROOT': root, 'ASSET': ASSET, 'WORK': work, '__name__': '__main__'}
        src = open(os.path.join(ASSET, g), encoding='utf-8').read()
        exec(compile(src, g, 'exec'), ns)
    return open(os.path.join(work, 'hohoplay_merged_sample.html'), encoding='utf-8').read()


def between(s, a, b, incl=True):
    i = s.index(a); j = s.index(b, i) + (len(b) if incl else 0)
    return s[i:j]


def sub1(s, old, new, must=True):
    if old not in s:
        if must:
            raise SystemExit('패턴을 찾지 못했어요: ' + old[:80])
        return s
    return s.replace(old, new)


# ───────────────────────── 서비스용 JS (날씨·위치·날짜·일정표·탭 연동) ─────────────────────────
PROD_JS = r'''
(function(){
var API='https://festival-api-proxy.vercel.app/api/weather',TH=60,cache={},seq=0,auto=false;
var C={seoul:[37.56,126.98],busan:[35.18,129.07],daegu:[35.87,128.6],incheon:[37.46,126.7],daejeon:[36.35,127.38],sejong:[36.48,127.29],gyeonggi:[37.4,127.2],gangwon:[37.75,128.3],chungbuk:[36.63,127.49],gyeongbuk:[36.4,128.7],gyeongnam:[35.3,128.3],chungnam:[36.5,126.8],jeonbuk:[35.8,127.1],jeonnam:[34.9,126.9],gwangju:[35.16,126.85],ulsan:[35.54,129.31],jeju:[33.4,126.55]};
var L={seoul:'서울',busan:'부산',daegu:'대구',incheon:'인천',daejeon:'대전',sejong:'세종',gyeonggi:'경기',gangwon:'강원',chungbuk:'충북',gyeongbuk:'경북',gyeongnam:'경남',chungnam:'충남',jeonbuk:'전북',jeonnam:'전남',gwangju:'광주',ulsan:'울산',jeju:'제주'};
function pad(n){return ('0'+n).slice(-2)}
function kst(){return new Date(Date.now()+9*3600000)}
function ymd(d){return ''+d.getUTCFullYear()+pad(d.getUTCMonth()+1)+pad(d.getUTCDate())}
function selDate(){var s=window.__dsel;if(s)return s.replace(/-/g,'');return ymd(kst())}
function rainFor(data,ds){if(!data)return null;var today=ymd(kst())===ds;
if(Array.isArray(data.forecast)&&data.forecast.length){var nh=pad(kst().getUTCHours())+'00',from=today&&nh>'0900'?nh:'0900';
var rows=data.forecast.filter(function(f){return f&&f.date===ds&&String(f.time)>=from&&String(f.time)<='2100'&&isFinite(f.pop)});
if(!rows.length)return null;var m=0;rows.forEach(function(f){if(f.pop>m)m=f.pop});return {rain:m>=TH,pop:m};}
if(today&&typeof data.willRain==='boolean')return {rain:data.willRain,pop:data.maxPop};return null;}
function pt(){if(window.__npos)return {la:window.__npos[0],ln:window.__npos[1],lab:'내 위치'};
var b=document.querySelector('#vc .rg.on[data-k]'),k=b&&b.getAttribute('data-k');if(k&&C[k])return {la:C[k][0],ln:C[k][1],lab:L[k]};return {la:C.seoul[0],ln:C.seoul[1],lab:'서울'};}
function get(p){var key=p.la.toFixed(2)+','+p.ln.toFixed(2),h=cache[key];if(h&&Date.now()-h.at<600000)return Promise.resolve(h.d);
var ct=window.AbortController?new AbortController():null,tm=ct?setTimeout(function(){ct.abort()},4000):null;
return fetch(API+'?lat='+p.la+'&lng='+p.ln,ct?{signal:ct.signal}:undefined).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(d){if(tm)clearTimeout(tm);if(d&&!d.error)cache[key]={at:Date.now(),d:d};return d});}
function apply(on,txt){var r=document.getElementById('rain'),w=document.getElementById('wxn');if(!r||!w)return;
if(on){w.innerHTML=txt;w.style.display='';}else{w.style.display='none';}
if(r.checked!==on){r.checked=on;r.dispatchEvent(new Event('change'));}if(on)w.style.display='';}
function check(){if(window.__view!=='c')return;var p=pt(),ds=selDate(),my=++seq;
get(p).then(function(d){if(my!==seq)return;var i=rainFor(d,ds);
if(i&&i.rain){var t=ds===ymd(kst())?'오늘':(+ds.slice(4,6))+'월 '+(+ds.slice(6,8))+'일';
apply(true,'☔ <b>'+p.lab+' 기준 '+t+' 비 예보'+(isFinite(i.pop)?' (강수확률 '+i.pop+'%)':'')+'</b> — <b>실내 코스를 먼저</b> 보여드려요. 실내 장소가 많은 코스가 위로 올라옵니다.');auto=true;}
else{apply(false);auto=false;}}).catch(function(){});}
var tm2=null;function later(){clearTimeout(tm2);tm2=setTimeout(check,500)}
document.addEventListener('click',later,true);document.addEventListener('change',later,true);
setTimeout(check,300);window.__wx=check;
})();

/* 일정표 만들기: 코스 카드 / 전체목록 장소 */
(function(){
function pad(n){return ('0'+n).slice(-2)}function fmt(m){return pad(Math.floor(m/60)%24)+':'+pad(m%60)}
function modal(cb){if(window.HohoPlanModal){cb(window.HohoPlanModal);return;}var s=document.createElement('script');s.src='/festival/plan-modal.js?v=20261123a';
s.onload=function(){if(window.HohoPlanModal)cb(window.HohoPlanModal)};s.onerror=function(){alert('일정표를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.')};document.head.appendChild(s);}
function course(card){var lis=[].slice.call(card.querySelectorAll('ol > li:not(.mv)')),mv=[].slice.call(card.querySelectorAll('ol > li.mv')),st=[];
try{st=JSON.parse(card.getAttribute('data-stops')||'[]')}catch(e){}
var t=600,rows=[{time:'09:30',title:'집 출발',memo:'',k:'x'}];
lis.forEach(function(l,i){var a=l.querySelector('a'),m=a&&/(kids-[A-Za-z0-9_-]+)/.exec(a.getAttribute('href')||''),memo=[];
if(i>0){var d=/약 ([\d.]+)km/.exec(mv[i-1]?mv[i-1].textContent:'');var km=d?+d[1]:3;memo.push('앞 장소에서 약 '+km+'km');t+=Math.max(15,Math.round(km*4));}
var mm=l.querySelector('.m');if(mm)memo.push(mm.textContent.trim());memo.push('머무는 시간 약 80분(예상)');
rows.push({time:fmt(t),title:'📍 '+(l.querySelector('.t')?l.querySelector('.t').textContent:''),memo:memo.join(' · '),k:'n',pid:m?m[1]:'',lat:st[i]?st[i][0]:0,lng:st[i]?st[i][1]:0});t+=80;});
rows.push({time:fmt(t+20),title:'귀가',memo:'',k:'out'});
var ds=window.__dsel||'';return {title:(card.querySelector('h3')?card.querySelector('h3').textContent:'추천 코스'),dateStr:ds,rows:rows};}
window.__plan={place:function(id){modal(function(M){M.openPlace(id)})}};
document.addEventListener('click',function(e){var b=e.target.closest('.plan[data-course]');
if(b){var c=b.closest('.card');if(!c)return;e.preventDefault();var sp=course(c);modal(function(M){M.openCourse(sp)});return;}
var p=e.target.closest('[data-plan]');if(p){e.preventDefault();var id=p.getAttribute('data-plan');modal(function(M){M.openPlace(id)});}});
})();

/* 지도 열기: 탭·버튼·옛 지도 링크 */
(function(){
function K(){return window.KMAP}
document.addEventListener('click',function(e){
var o=e.target.closest('.openmap');if(o){e.preventDefault();if(K()){if(matchMedia('(min-width:1024px)').matches)window.scrollTo({top:0,behavior:'smooth'});else K().open();}return;}
var bk=e.target.closest('#mback');if(bk){e.preventDefault();if(K())K().close();return;}
var g=e.target.closest('a.go2');if(g&&K()){var cc=g.closest('.card');if(cc){e.preventDefault();K().openCourse(cc.getAttribute('data-id'));return;}var m=/[?&]region=([a-z]+)/.exec(g.getAttribute('href')||'');if(m){e.preventDefault();var k=m[1];K().open(function(){K().region(k)});}return;}
var a2=e.target.closest('.li a.a2');if(a2){var m2=/[?&]id=([^&]+)/.exec(a2.getAttribute('href')||'');if(m2&&K()){e.preventDefault();K().openAt(decodeURIComponent(m2[1]));}}});
var q=new URLSearchParams(location.search),id=q.get('id'),la=+q.get('lat'),ln=+q.get('lng'),rg=q.get('region');
window.addEventListener('load',function(){setTimeout(function(){
if(rg){var b=document.querySelector('#vc .rg[data-k="'+rg+'"]');if(b)b.click();}
if(!K())return;
if(id||(la&&ln))K().openAt(id||'',la,ln);},500);});
})();
'''

MAPMODE_CSS = '''<style>
#mback{display:none}
.maphint{display:none}
@media(max-width:1023px){
 body.mapmode{overflow:hidden}
 body.mapmode #pcmap{display:block;position:fixed;left:0;right:0;top:80px;bottom:0;height:auto;z-index:60;border:0}
 body.mapmode #mback{display:none!important}
 body.mapmode .mtop{width:calc(100% - 24px);left:50%}
 .seg a.mapt{flex:1.1;border:1.5px solid var(--pri);color:var(--pri);background:var(--card)}
 .maphint{display:block;margin:-6px 2px 12px;font-size:12px;color:var(--sub)}
 .rm{bottom:84px}
 body.mapmode .tkw{display:none}
 #mcard{position:absolute;left:10px;right:10px;bottom:14px;z-index:7;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:16px;padding:14px 14px 12px;box-shadow:0 6px 24px rgba(0,0,0,.25)}
 #mcard b{display:block;font-size:15px;padding-right:28px}#mcard span{display:block;margin:2px 0 10px;font-size:12px;color:var(--sub)}
 #mcard .x{position:absolute;right:8px;top:6px;border:0;background:none;color:var(--sub);font-size:16px;padding:6px}
 #mcard .bt{display:flex;gap:8px}#mcard .bt a,#mcard .bt button{flex:1;text-align:center;border:1px solid var(--pri);color:var(--pri);background:var(--card);border-radius:10px;padding:10px 6px;font:800 13px/1.2 inherit;font-family:inherit;text-decoration:none}
 #mcard .bt .p{background:var(--pri);color:#fff}
}
</style>'''

# 탭(코스 추천/전체목록) 사이에서 지역·검색·실내 선택을 같이 가져간다
SYNC_JS = r'''
(function(){
var vc=document.getElementById('vc'),vl=document.getElementById('vl');
window.__syncViews=function(from,to){var y=window.pageYOffset;
var f=from.querySelector('.rg.on[data-k]'),k=f&&!f.hasAttribute('data-all')?f.getAttribute('data-k'):'';
var t=to.querySelector('.rg.on[data-k]'),tk=t&&!t.hasAttribute('data-all')?t.getAttribute('data-k'):'';
if(k!==tk){var b=k?to.querySelector('.rg[data-k="'+k+'"]'):to.querySelector('.sh-all');if(b)b.click();}
var q1=from.querySelector('#q'),q2=to.querySelector('#q');if(q1&&q2&&q1.value!==q2.value){q2.value=q1.value;q2.dispatchEvent(new Event('input'));}
var i1=from.querySelector('#indoor'),i2=to.querySelector('#indoor');if(i1&&i2&&i1.checked!==i2.checked){i2.checked=i1.checked;i2.dispatchEvent(new Event('change'));}
window.scrollTo(0,y);};
})();
'''


def head(root, title, desc, canon):
    idx = open(os.path.join(root, MAP_REL), encoding='utf-8').read()
    hn_css = between(idx, '<!-- HN_CSS_START -->', '<!-- HN_CSS_END -->')
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="website">
<meta property="og:title" content="아이랑 갈만한 곳·축제 코스 추천">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{DOMAIN}/data/festival-og-banner.png">
<meta name="twitter:image" content="{DOMAIN}/data/festival-og-banner.png">
<meta name="twitter:card" content="summary_large_image">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7990191075290055" crossorigin="anonymous"></script>
<link rel="icon" href="/favicon.svg">
{hn_css}
'''


def footer_block(root):
    idx = open(os.path.join(root, MAP_REL), encoding='utf-8').read()
    a = idx.index('<div id="footer-placeholder">')
    b = idx.index('</script>', a) + len('</script>')
    return idx[a:b]


def nav_block(root):
    idx = open(os.path.join(root, MAP_REL), encoding='utf-8').read()
    return between(idx, '<!-- HN_START -->', '<!-- HN_END -->')


def stats(root):
    import json
    P = [x for x in json.load(open(os.path.join(root, 'data/kids_places.json'), encoding='utf-8')) if not x.get('hidden')]
    n = len(P)
    indoor = sum(1 for x in P if x.get('placeType') in ('실내', '실내외'))
    free = sum(1 for x in P if x.get('costTag') == '완전무료')
    return n, indoor, free


def post(s, root, work):
    kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    today_txt = f'{kst.year}.{kst.month:02d}.{kst.day:02d}'
    n, indoor, free = stats(root)
    ncourse = len(re.findall(r'<article class="card"', s))
    nfest = len(re.findall(r'"t":"f"', s))

    # 1) 머리말 교체 ----------------------------------------------------------------------------
    title = '아이랑 갈만한 곳·축제 코스 추천 | HOHO PLAY'
    desc = (f'전국 17개 시·도 아이랑 갈만한 곳 {n}곳과 지금 열리는 축제를 지역·날짜·실내외·이용요금으로 골라 보고, '
            f'같은 동네 장소를 묶은 하루 코스 {ncourse}개를 확인하세요. 비 예보가 있으면 실내 코스를 먼저 보여드려요.')
    i = s.index('<style>')
    css = s[i:s.index('</head>')]
    s = head(root, title, desc, f'{DOMAIN}/festival/') + css + '</head>' + s[s.index('</head>') + 7:]

    # 2) 시안 표시 제거 -------------------------------------------------------------------------
    s = re.sub(r'<span class="badge">.*?</span>\s*', '', s, count=1)
    s = re.sub(r'<div class="tip2">.*?</div>', '', s)
    s = s.replace('<a href="#about-map"', '<a href="#data-notice"')
    s = s.replace('이용 안내 ↓', '데이터 안내 ↓')

    # 3) 날씨 줄: 시안용 스위치 → 실제 날씨(자동) ------------------------------------------------
    s = re.sub(r'<div class="wx">.*?</p></div>',
               '<div class="wx"><input type="checkbox" id="rain" hidden><p class="wxn" id="wxn" role="status" style="display:none"></p></div>',
               s, count=1, flags=re.S)

    # 4) 내 위치: 서울시청 대체값 없이 실제 위치만 ----------------------------------------------------
    fb_old = "var fb=function(){nearOn([37.5665,126.9780],true)};"
    fb_new = ("var fb=function(){var nl=document.getElementById('nlocn');nl.style.display='';"
              "nl.textContent='📍 위치를 가져오지 못했어요. 브라우저의 위치 권한을 허용한 뒤 다시 눌러 주세요.';};")
    assert s.count(fb_old) == 2, s.count(fb_old)
    s = s.replace(fb_old, fb_new)
    s = s.replace("function nearOn(p,fake){pos=p;near=true;", "function nearOn(p,fake){pos=p;window.__npos=p;near=true;")
    s = s.replace("function nearOff(){near=false;pos=null;", "function nearOff(){near=false;pos=null;window.__npos=null;")
    s = s.replace("window.__npos=p;", "window.__npos=p;window.KMAP&&KMAP.me&&KMAP.me(p);")
    s = s.replace("window.__npos=null;", "window.__npos=null;window.KMAP&&KMAP.me&&KMAP.me(null);")
    # 위치 허용 창에서 승인하는 시간까지 기다리도록 제한 시간을 늘린다
    s = s.replace("if(!done){done=true;fb()}},4000)", "if(!done){done=true;fb()}},16000)").replace("{timeout:3500}", "{timeout:15000}")
    s = s.replace("nl.textContent=fake?'📍 시안에서는 위치를 못 가져와 서울시청 기준으로 보여드려요. 실제로는 내 위치 기준이에요.':",
                  "nl.textContent=fake?'':")

    # 5) 날짜 선택 → 전역(__dsel, yyyy-mm-dd) -----------------------------------------------------
    s = s.replace("function pick(k,auto){btns.forEach(",
                  "function pick(k,auto){window.__dsel=iso(k==='tom'?add(1):k==='wk'?sat:now);btns.forEach(")
    s = s.replace("cur=d;btns.forEach(function(b){b.classList.remove('on')});",
                  "cur=d;window.__dsel=iso(d);btns.forEach(function(b){b.classList.remove('on')});")

    # 6) 지도 탭 → 기존 지도 페이지 -----------------------------------------------------------------
    s = s.replace("else alert('시안: 모바일에서는 기존 지도 화면(/festival/)으로 이동해요.');",
                  "else if(window.KMAP)KMAP.open();")
    s = s.replace('<a href="#">지도</a>', '<a href="#map" class="mapt">🗺️ 지도</a>')
    s = s.replace('class="mapt">🗺️ 지도</a></nav>', 'class="mapt">🗺️ 지도</a></nav><p class="maphint">지도를 누르면 지도 페이지로 보여줘요</p>')

    # 7) PC 지도: 메뉴(80px) 아래에 붙이기 + 카카오맵 어댑터 위임 ------------------------------------------
    s = s.replace('</head>', '<style>@media(min-width:1024px){#pcmap{top:80px;height:calc(100vh - 80px)}}'
                  '#pcmain{position:relative}#pcmap #pcsvg,#pcmap .zb{display:none!important}#pcmap{background:#eef2f7}</style></head>', 1)
    d1 = "var api={set:function(a){pts=a;if(visible())dots();},"
    assert d1 in s
    s = s.replace(d1, "var api={set:function(a){pts=a;if(window.KMAP&&KMAP.ready){KMAP.set(a);return}if(visible())dots();},")
    d2 = "focus:function(id,st,la,ln,el){if(!visible())return;"
    assert d2 in s
    s = s.replace(d2, "focus:function(id,st,la,ln,el){if(window.KMAP&&KMAP.ready){KMAP.focus(id,st,la,ln,el);return}if(!visible())return;")
    d3 = "hover:function(id){"
    assert d3 in s
    s = s.replace(d3, "hover:function(id){if(window.KMAP&&KMAP.ready){KMAP.hover(id);return}", 1)
    d4 = "api.region=function(k){if(!visible())return;"
    assert d4 in s
    s = s.replace(d4, "api.region=function(k){if(window.KMAP&&KMAP.ready){KMAP.region(k);return}if(!visible())return;")
    # KMAP이 늦게 준비돼도 지금 보이는 점을 다시 그리게
    s = s.replace("window.PCSYNC={c:function(){syncC()}",
                  "window.__kready=function(){if(window.PCSYNC&&PCSYNC[window.__view])PCSYNC[window.__view]()};window.PCSYNC={c:function(){syncC()}")

    # 8) 탭 이동 시 지역·검색·실내 선택 가져가기 -------------------------------------------------------
    s = s.replace("if(window.PCSYNC)window.PCSYNC[v]();}",
                  "if(window.__syncViews)window.__syncViews(v==='c'?vl:vc,v==='c'?vc:vl);if(window.PCSYNC)window.PCSYNC[v]();}")

    # 9) 푸터: 안내 박스를 새로 씀(festival/index.html 본문 복사 금지) --------------------------------------
    foot_a = s.index('<div class="wrap" id="pcfoot">')
    foot_b = s.index('<nav class="rm"')
    regcards = open(os.path.join(work, 'regcards.html'), encoding='utf-8').read()
    css_note = ('<style>#data-notice{margin:16px 0;padding:14px 16px;border:1px solid var(--line);border-radius:14px;background:var(--card);font-size:13px;line-height:1.75;color:var(--sub)}'
                '#data-notice h2{margin:0 0 6px;font-size:15px;color:var(--ink)}#data-notice p{margin:0 0 6px}#data-notice a{color:var(--pri);font-weight:700}'
                '.xl{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:12px 0 4px}.xl a{display:block;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--ink);text-decoration:none;font-size:13px;font-weight:800}</style>')
    notice = f'''<div id="data-notice" role="note"><h2>📌 이 페이지의 데이터 안내</h2>
<p>축제 정보는 하루 최대 3회 자동으로 확인해 바뀐 내용이 있을 때 업데이트돼요. 데이터 기준일은 <b>{today_txt}</b>(KST)이고, 축제는 한국관광공사 TourAPI·공공데이터포털 정보예요.</p>
<p>아이랑 갈만한 곳 <b>{n}곳</b>은 호호플레이가 직접 조사해 정리했어요. 그중 실내·실내외 장소가 <b>{indoor}곳</b>, 입장료가 없는 곳이 <b>{free}곳</b>이에요. 코스 추천 {ncourse}개는 같은 구·군에 모여 있는 장소를 묶은 거라, 쉬는 날이나 운영시간은 방문 전에 꼭 확인해 주세요.</p>
<p>사용법: 지역·날짜·실내외·이용요금으로 좁히고, 비 예보가 있는 날은 실내 코스가 먼저 나와요. 내 주변 버튼은 누를 때만 위치를 물어봐요. 지도로 한눈에 보려면 <a href="#map" class="openmap">지도 보기</a>를 눌러 보세요. 일정·요금·운영시간은 바뀔 수 있으니 방문 전 상세 페이지와 공식 안내를 꼭 확인해 주세요.</p></div>
<nav class="xl" aria-label="함께 보면 좋은 페이지"><a href="#map" class="openmap">🗺️ 지도 열기</a><a href="/festival/tools.html">🧭 오늘 어디 갈지 정하기</a><a href="/festival/worldcup.html">🏆 나들이 월드컵</a><a href="/blog/kids-course/">🧒 코스 글 모아보기</a></nav>'''
    # 지도 소개·한눈에 보기(표 1~3, 지역별 요약, FAQ): fetch_data.py가 매일 갱신하는 festival/map.html 의 about-map 구간을 그대로 가져온다
    mp = open(os.path.join(root, MAP_REL), encoding='utf-8').read()
    m = re.search(r'<section id="about-map".*?</section>', mp, flags=re.S)
    about = m.group(0) if m else ''
    new_foot = f'{css_note}<div class="wrap" id="pcfoot">{regcards}{notice}{about}</div>\n'
    s = s[:foot_a] + new_foot + s[foot_b:]

    # 지도 화면 위 버튼·아래 카드(모바일 전체화면 지도용)와 스타일
    s = s.replace('</aside>', '<button type="button" id="mback" aria-label="목록으로">← 목록</button><div id="mcard" style="display:none"></div></aside>', 1)
    s = s.replace('</head>', MAPMODE_CSS + '</head>', 1)
    # 10) 메뉴(맨 위) + 공통 푸터 + 스크립트 -------------------------------------------------------------
    s = s.replace('<body><div id="pcmain">', '<body>\n' + nav_block(root) + '\n<div id="pcmain">', 1)
    s = s.replace('<nav class="rm"', footer_block(root) + '\n<nav class="rm"', 1)
    k = s.index('<script>var ITEMS=')
    # 첫 번째 큰 <script> 끝에 서비스용 JS를 붙인다
    end1 = s.index('</script>', k)
    s = s[:end1] + SYNC_JS + PROD_JS + s[end1:]
    # 지도 스크립트 주소에 파일 내용 해시를 붙여, 파일이 바뀌면 브라우저가 옛 캐시를 쓰지 않고 새로 받게 한다
    import hashlib
    mjs = os.path.join(root, 'festival/explore-map.js')
    ver = hashlib.md5(open(mjs, 'rb').read()).hexdigest()[:8] if os.path.exists(mjs) else '1'
    s = s.replace('</body>', '<script src="/festival/detail-sheet.js?v=20261122a" defer></script>\n<script src="/festival/explore-map.js?v=' + ver + '" defer></script>\n</body>')
    # 코스 탭에서도 지도에는 아이랑 장소 전체를 찍는다(지역을 고르면 그 지역만)
    _o = "var a=[];[].forEach.call(document.querySelectorAll('#vc .card'),function(c){if(c.offsetParent===null)return;a.push({id:c.getAttribute('data-id'),la:+c.getAttribute('data-lat'),ln:+c.getAttribute('data-lng'),c:1})});api.set(a);}"
    _n = "var rb=document.querySelector('#vc .rg.on[data-k]'),rk=rb&&!rb.hasAttribute('data-all')?rb.getAttribute('data-k'):'';var a=(window.ITEMS||[]).filter(function(i){return i.t==='p'&&(!rk||i.r===rk)}).map(function(i){return {id:i.id,la:i.la,ln:i.ln}});api.set(a);}"
    assert _o in s
    s = s.replace(_o, _n)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.path.dirname(HERE))
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    with tempfile.TemporaryDirectory() as work:
        merged = run_generators(root, work)
        out = post(merged, root, work)
    path = os.path.join(root, OUT_REL)
    old = open(path, encoding='utf-8').read() if os.path.exists(path) else None
    # 날짜(기준일)만 바뀐 경우를 포함해 내용이 달라졌을 때만 쓴다
    if old != out:
        open(path, 'w', encoding='utf-8').write(out)
        print('wrote', OUT_REL, len(out) // 1024, 'KB')
    else:
        print('no change')


if __name__ == '__main__':
    main()
