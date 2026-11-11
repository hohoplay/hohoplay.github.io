#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
나들이 도구 5개 페이지의 공통 상단 메뉴를 '메뉴 동기화(Actions)'로 맞추는 스크립트 (여러 번 실행해도 안전).

  대상: festival/worldcup.html · camping-worldcup.html · pick.html · roulette.html · poster.html

  ① 상단 헤더(HOHO PLAY · 플레이하기 · 소통·정보 · 약관·정책)
       원본 = blog/magazine/index.html(호호 매거진/커뮤니티)의 <nav> 를 그대로 읽어서 대상 페이지의
       <!-- HN_START --> ~ <!-- HN_END --> 구간에 다시 써 넣는다.
       → 메뉴 항목을 추가·변경하는 워크플로(Add ... Menu / Update Nav Menu)가 매거진 메뉴를 고친 뒤
         이 스크립트를 돌리면(자동으로 이어서 실행됨) 5개 페이지의 헤더도 똑같이 바뀐다.
       이 페이지들은 Tailwind 를 쓰지 않으므로, 그 헤더에 쓰인 클래스만 옮긴 CSS 를 <head> 의
       <!-- HN_CSS_START --> ~ <!-- HN_CSS_END --> 구간에 같이 넣는다.
  ② 헤더 아래 도구 탭(월드컵·캠핑장 월드컵·오늘 어디 갈까?·룰렛·축제 포스터)과 「← 아이랑 나들이 지도 / 🏠 홈」 줄
       (<!-- FZ_NAV_START --> ~ <!-- FZ_NAV_END -->). 처음 실행할 때 기존 상단 링크 줄을 이것으로 바꾼다.
  ③ 우하단 리모콘 버튼 지도·포스터·맨 위·홈 (<!-- FZ_REMOTE_START --> ~ <!-- FZ_REMOTE_END -->).
       '오늘 어디 갈까?'(pick.html)에 있던 옛 리모콘은 이것으로 합친다.

  이미 들어간 구간은 새 내용으로 교체하므로 몇 번을 돌려도 결과가 같다.
  원본 메뉴를 못 찾으면 아무 파일도 건드리지 않고 오류로 끝낸다.

사용법:  python3 scripts/sync_festival_nav.py          (실제로 고침)
         python3 scripts/sync_festival_nav.py --dry     (고치지 않고 결과만 보여줌)
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join('blog', 'magazine', 'index.html')
# (파일, 아이콘, 탭 이름, 기존 상단바 종류)
PAGES = [
    ('worldcup.html',         '🏆', '나들이 월드컵',          'topbar'),
    ('camping-worldcup.html', '⛺', '캠핑장 월드컵',          'topbar'),
    ('pick.html',             '🧭', '오늘 어디 갈까?',        'pk'),
    ('roulette.html',         '🎡', '나들이·캠핑장·숲 룰렛', 'topbar'),
    ('poster.html',           '🎪', '축제 포스터',            'pz'),
]
DIR = 'festival'

HN_CSS = r'''<!-- HN_CSS_START -->
<style>
  /* 호호 매거진 등과 같은 상단 메뉴 마크업이 Tailwind 없이도 똑같이 보이도록, 그 마크업의 클래스만 옮긴 CSS */
  nav.hn-std { font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif; line-height: 1.5; text-align: left; }
  nav.hn-std *, nav.hn-std *::before, nav.hn-std *::after { box-sizing: border-box; border: 0 solid #e5e7eb; }
  nav.hn-std a { color: inherit; text-decoration: none; }
  nav.hn-std button { font-family: inherit; font-size: 100%; background: transparent; border: 0; padding: 0; margin: 0; cursor: pointer; color: inherit; }
  nav.hn-std svg { display: block; vertical-align: middle; }
  nav.hn-std div, nav.hn-std span { margin: 0; }
  nav.hn-std.sticky { position: sticky; } nav.hn-std.top-0 { top: 0; } nav.hn-std.z-50 { z-index: 50; }
  nav.hn-std .z-50 { z-index: 50; }
  nav.hn-std.bg-white\/80 { background-color: rgba(255,255,255,.8); }
  nav.hn-std.backdrop-blur-md { -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px); }
  nav.hn-std.border-b { border-bottom-width: 1px; }
  nav.hn-std.shadow-sm { box-shadow: 0 1px 2px 0 rgba(0,0,0,.05); }
  nav.hn-std .max-w-7xl { max-width: 80rem; } nav.hn-std .mx-auto { margin-left: auto; margin-right: auto; }
  nav.hn-std .px-4 { padding-left: 16px; padding-right: 16px; } nav.hn-std .px-2 { padding-left: 8px; padding-right: 8px; }
  nav.hn-std .py-1 { padding-top: 4px; padding-bottom: 4px; } nav.hn-std .py-2 { padding-top: 8px; padding-bottom: 8px; }
  nav.hn-std .py-2\.5 { padding-top: 10px; padding-bottom: 10px; } nav.hn-std .py-3 { padding-top: 12px; padding-bottom: 12px; }
  nav.hn-std .py-4 { padding-top: 16px; padding-bottom: 16px; } nav.hn-std .pb-1 { padding-bottom: 4px; } nav.hn-std .pt-1 { padding-top: 4px; }
  nav.hn-std .flex { display: flex; } nav.hn-std .flex-col { flex-direction: column; } nav.hn-std .block { display: block; }
  nav.hn-std .hidden { display: none; } nav.hn-std .relative { position: relative; } nav.hn-std .absolute { position: absolute; }
  nav.hn-std .justify-between { justify-content: space-between; } nav.hn-std .justify-center { justify-content: center; } nav.hn-std .items-center { align-items: center; }
  nav.hn-std .gap-1 { gap: 4px; } nav.hn-std .gap-1\.5 { gap: 6px; } nav.hn-std .gap-2 { gap: 8px; } nav.hn-std .gap-3 { gap: 12px; }
  nav.hn-std .space-x-2 > :not([hidden]) ~ :not([hidden]) { margin-left: 8px; }
  nav.hn-std .space-y-1 > :not([hidden]) ~ :not([hidden]) { margin-top: 4px; }
  nav.hn-std .h-20 { height: 80px; } nav.hn-std .h-12 { height: 48px; } nav.hn-std .h-10 { height: 40px; } nav.hn-std .h-0\.5 { height: 2px; }
  nav.hn-std .w-12 { width: 48px; } nav.hn-std .w-10 { width: 40px; } nav.hn-std .w-6 { width: 24px; } nav.hn-std .w-40 { width: 160px; } nav.hn-std .w-44 { width: 176px; } nav.hn-std .w-full { width: 100%; }
  nav.hn-std .left-0 { left: 0; } nav.hn-std .right-0 { right: 0; } nav.hn-std .top-full { top: 100%; } nav.hn-std .mt-2 { margin-top: 8px; } nav.hn-std .my-2 { margin-top: 8px; margin-bottom: 8px; }
  nav.hn-std .bg-white { background-color: #fff; } nav.hn-std .bg-indigo-600 { background-color: #4f46e5; } nav.hn-std .bg-slate-700 { background-color: #334155; } nav.hn-std .bg-indigo-50 { background-color: #eef2ff; }
  nav.hn-std .text-white { color: #fff; } nav.hn-std .text-indigo-600 { color: #4f46e5; } nav.hn-std .text-violet-500 { color: #8b5cf6; }
  nav.hn-std .text-slate-400 { color: #94a3b8; } nav.hn-std .text-slate-500 { color: #64748b; } nav.hn-std .text-slate-600 { color: #475569; } nav.hn-std .text-slate-700 { color: #334155; }
  nav.hn-std .text-2xl { font-size: 24px; line-height: 32px; } nav.hn-std .text-sm { font-size: 14px; line-height: 20px; } nav.hn-std .text-xs { font-size: 12px; line-height: 16px; }
  nav.hn-std .font-black { font-weight: 900; } nav.hn-std .font-bold { font-weight: 700; } nav.hn-std .text-left { text-align: left; }
  nav.hn-std .uppercase { text-transform: uppercase; } nav.hn-std .tracking-tighter { letter-spacing: -.05em; }
  nav.hn-std .rounded-xl { border-radius: 12px; } nav.hn-std .rounded-2xl { border-radius: 16px; }
  nav.hn-std .border { border-width: 1px; } nav.hn-std .border-t { border-top-width: 1px; } nav.hn-std .border-slate-100 { border-color: #f1f5f9; }
  nav.hn-std .shadow-lg { box-shadow: 0 10px 15px -3px rgba(0,0,0,.1), 0 4px 6px -4px rgba(0,0,0,.1); }
  nav.hn-std .shadow-xl { box-shadow: 0 20px 25px -5px rgba(0,0,0,.1), 0 8px 10px -6px rgba(0,0,0,.1); }
  nav.hn-std .shadow-indigo-200 { box-shadow: 0 20px 25px -5px rgba(199,210,254,1), 0 8px 10px -6px rgba(199,210,254,1); }
  nav.hn-std .opacity-0 { opacity: 0; } nav.hn-std .invisible { visibility: hidden; }
  nav.hn-std .transition { transition: color .15s, background-color .15s, border-color .15s, opacity .15s, box-shadow .15s, transform .15s; }
  nav.hn-std .transition-all { transition: all .15s; } nav.hn-std .duration-200 { transition-duration: .2s; } nav.hn-std .duration-300 { transition-duration: .3s; }
  nav.hn-std .hover\:bg-indigo-50:hover { background-color: #eef2ff; } nav.hn-std .hover\:bg-slate-100:hover { background-color: #f1f5f9; } nav.hn-std .hover\:bg-slate-50:hover { background-color: #f8fafc; }
  nav.hn-std .hover\:text-indigo-600:hover { color: #4f46e5; } nav.hn-std .hover\:text-slate-600:hover { color: #475569; }
  nav.hn-std .group:hover .group-hover\:opacity-100 { opacity: 1; } nav.hn-std .group:hover .group-hover\:visible { visibility: visible; }
  @media (min-width: 640px) { nav.hn-std .sm\:gap-3 { gap: 12px; } nav.hn-std .sm\:px-6 { padding-left: 24px; padding-right: 24px; } }
  @media (min-width: 768px) { nav.hn-std .md\:flex { display: flex; } nav.hn-std .md\:hidden { display: none; } }
  @media (min-width: 1024px) { nav.hn-std .lg\:px-8 { padding-left: 32px; padding-right: 32px; } }
</style>
<!-- HN_CSS_END -->
'''

FZ_CSS = '''<!-- FZ_CSS_START -->
<style>
  .fz-nav { margin: 0 0 14px; padding: 12px 0 0; }
  .fz-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 14px; font-weight: 700; }
  .fz-row a { color: #4f46e5; text-decoration: none; }
  .fz-tabs { display: flex; gap: 8px; margin-top: 10px; overflow-x: auto; -webkit-overflow-scrolling: touch; padding-bottom: 4px; scrollbar-width: thin; }
  .fz-tab { flex: 0 0 auto; display: inline-block; white-space: nowrap; padding: 8px 14px; border-radius: 999px; border: 1px solid #e2e8f0; background: #fff; color: #475569; font-size: 13px; font-weight: 800; line-height: 1.2; text-decoration: none; }
  .fz-tab:hover { background: #eef2ff; color: #3730a3; }
  .fz-tab[aria-current="page"] { background: #4338ca; border-color: #4338ca; color: #fff; }
  .fz-remote { position: fixed; right: 16px; bottom: 16px; z-index: 40; display: flex; flex-direction: column; gap: 10px; }
  .fz-rbtn { width: 54px; height: 54px; border-radius: 50%; background: #fff; box-shadow: 0 4px 14px rgba(0,0,0,.2); display: flex; flex-direction: column; align-items: center; justify-content: center; text-decoration: none; color: #333; font-size: 20px; line-height: 1; border: none; padding: 0; cursor: pointer; font-family: inherit; }
  .fz-rbtn .lb { font-size: 9px; font-weight: 700; margin-top: 2px; color: #555; }
  .fz-rbtn:hover { background: #eef2ff; }
  html body { padding-bottom: 120px; }
  @media (max-width: 640px) { .fz-remote { right: 12px; bottom: 12px; gap: 7px; } .fz-rbtn { width: 46px; height: 46px; font-size: 16px; } }
</style>
<!-- FZ_CSS_END -->
'''


def read(path):
    with open(path, encoding='utf-8', newline='') as fp:
        return fp.read()


def write(path, text):
    with open(path, 'w', encoding='utf-8', newline='') as fp:
        fp.write(text)


def load_source():
    """매거진 페이지에서 상단 메뉴(<nav>)·오버레이·열고 닫기 스크립트를 읽어 HN 블록을 만든다."""
    p = os.path.join(ROOT, SOURCE)
    if not os.path.exists(p):
        sys.exit('원본 메뉴 페이지가 없습니다: %s' % SOURCE)
    ref = read(p).replace('\r\n', '\n')
    try:
        a = ref.index('<nav class="bg-white/80')
        b = ref.index('</nav>', a) + len('</nav>')
        nav = ref[a:b]
        ov = re.search(r'<div id="menu-overlay"[^\n]*</div>', ref).group(0)
        f0 = ref.index('function toggleMenu()')
        f1 = ref.index('</script>', f0)
        js = ref[f0:f1].strip()
    except (ValueError, AttributeError):
        sys.exit('매거진 페이지에서 상단 메뉴를 찾지 못했습니다(구조가 바뀐 듯). 아무것도 고치지 않았습니다.')
    if 'goPartner' not in js or 'id="mobile-menu"' not in nav:
        sys.exit('매거진 상단 메뉴 구조가 예상과 다릅니다. 아무것도 고치지 않았습니다.')
    # '현재 페이지(호호 매거진)'로 칠해진 줄은 일반 항목 모양으로 되돌린다(이웃 '커뮤니티' 줄의 class 사용)
    lines = nav.split('\n')
    for i, ln in enumerate(lines):
        if '>호호 매거진</a>' in ln and 'hover:bg-indigo-50' not in ln:
            ref_ln = next((l for l in lines if '>커뮤니티</a>' in l and l.count('<a ') == 1 and ('py-3' in l) == ('py-3' in ln)), None)
            if ref_ln is None:
                sys.exit('매거진 메뉴의 커뮤니티 항목을 찾지 못했습니다. 아무것도 고치지 않았습니다.')
            lines[i] = re.sub(r'class="[^"]*"', lambda m: re.search(r'class="[^"]*"', ref_ln).group(0), ln, count=1)
    nav = '\n'.join(lines).replace('<nav class="bg-white/80', '<nav class="hn-std bg-white/80', 1)
    return '<!-- HN_START -->\n' + nav + '\n' + ov + '\n<script>\n' + js + '\n</script>\n<!-- HN_END -->'


def fz_nav(cur):
    t = []
    for f, ic, nm, _ in PAGES:
        a = ' aria-current="page"' if f == cur else ''
        t.append('<a class="fz-tab" href="/festival/%s"%s>%s %s</a>' % (f, a, ic, html.escape(nm)))
    return ('<!-- FZ_NAV_START -->\n<nav class="fz-nav" aria-label="나들이 도구 메뉴">\n'
            '  <div class="fz-row"><a href="/festival/">← 아이랑 나들이 지도</a><a href="/">🏠 홈</a></div>\n'
            '  <div class="fz-tabs">' + ''.join(t) + '</div>\n</nav>\n'
            '<script>(function(){try{var a=document.querySelector(".fz-tab[aria-current]");if(a&&a.parentNode){a.parentNode.scrollLeft=Math.max(0,a.offsetLeft-16);}}catch(e){}})();</script>\n'
            '<!-- FZ_NAV_END -->')


def fz_remote(cur):
    b = ['<!-- FZ_REMOTE_START -->\n<div class="fz-remote" id="fzRemote">',
         '  <a class="fz-rbtn" href="/festival/" aria-label="아이랑 나들이 지도로 가기"><span>🗺️</span><span class="lb">지도</span></a>']
    if cur != 'poster.html':
        b.append('  <a class="fz-rbtn" href="/festival/poster.html" aria-label="축제 포스터로 가기"><span>🎪</span><span class="lb">포스터</span></a>')
    b.append('  <button type="button" class="fz-rbtn" id="fzTopBtn" aria-label="맨 위로 올라가기" onclick="try{window.scrollTo({top:0,behavior:\'smooth\'})}catch(e){window.scrollTo(0,0)}"><span>⬆️</span><span class="lb">맨 위</span></button>')
    b.append('  <a class="fz-rbtn" href="/" aria-label="홈으로 가기"><span>🏠</span><span class="lb">홈</span></a>')
    b.append('</div>\n<!-- FZ_REMOTE_END -->')
    return '\n'.join(b)


def strip(s, keys):
    for k in keys:
        s = re.sub(r'\s*<!-- %s_START -->[\s\S]*?<!-- %s_END -->' % (k, k), '', s)
    return s


def process(s, fname, kind, hn_block):
    """한 페이지의 새 텍스트를 만든다. 못 고치면 (None, 이유)."""
    if s.count('</head>') != 1 or s.count('<body>') != 1:
        return None, '</head> 또는 <body> 위치가 예상과 다름'
    # ② 도구 탭: 이미 있으면 그 자리를 교체, 없으면 기존 상단 링크 줄을 이것으로 바꾼다
    pat_mark = re.compile(r'<!-- FZ_NAV_START -->[\s\S]*?<!-- FZ_NAV_END -->')
    if pat_mark.search(s):
        s = pat_mark.sub(lambda m: fz_nav(fname), s, count=1)
    else:
        pat = {'topbar': r'<div class="topbar">[\s\S]*?</div>', 'pk': r'<div class="pk-top">[\s\S]*?</div>', 'pz': r'<div class="pz-top">[\s\S]*?</div>'}[kind]
        found = re.findall(pat, s)
        if len(found) != 1:
            return None, '기존 상단 링크 줄을 찾지 못함'
        s = re.sub(pat, lambda m: fz_nav(fname), s, count=1)
    # 옛 pick 리모콘은 공통 리모콘으로 합친다
    if kind == 'pk':
        s = re.sub(r'<div class="pk-remote" id="pkRemote">[\s\S]*?</div>\s*', '', s, count=1)
    # ①③ 헤더·리모콘·CSS 는 지우고 새로 넣는다
    s = strip(s, ('HN_CSS', 'HN', 'FZ_CSS', 'FZ_REMOTE'))
    s = s.replace('</head>', HN_CSS + FZ_CSS + '</head>', 1)
    s = s.replace('<body>', '<body>\n' + hn_block + '\n' + fz_remote(fname), 1)
    return s, None


def main():
    dry = '--dry' in sys.argv
    hn_block = load_source()
    changed = skipped = 0
    for fname, _ic, _nm, kind in PAGES:
        path = os.path.join(ROOT, DIR, fname)
        if not os.path.exists(path):
            print('  %s: 파일이 없어 건너뜀' % fname)
            skipped += 1
            continue
        old = read(path)
        new, why = process(old, fname, kind, hn_block)
        if new is None:
            print('  %s: 건드리지 않음 (%s)' % (fname, why))
            skipped += 1
            continue
        if new != old:
            changed += 1
            print('  %s: 헤더·도구 탭·리모콘 동기화' % fname)
            if not dry:
                write(path, new)
        else:
            print('  %s: 이미 최신' % fname)
    print('대상 %d개 중 %d개 수정, %d개 건너뜀%s' % (len(PAGES), changed, skipped, ' (dry-run: 실제로는 고치지 않음)' if dry else ''))


if __name__ == '__main__':
    main()
