#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사이트 전체 상단 메뉴 한 번에 동기화

기준은 메인 index.html 의 상단 메뉴 하나뿐입니다. index.html 에서 메뉴 항목을 추가·삭제·이름변경·순서변경하면,
이 스크립트가 아래 모든 곳의 메뉴(PC 드롭다운 + 모바일 햄버거 + 푸터)를 같은 항목·같은 순서로 맞춥니다.

  ① 인라인 스타일 메뉴(g-nav-desktop / game-mobile-menu) — 약 125개 페이지(코스 글·매거진 글·게임·투표 등)와 템플릿
  ② Tailwind 메뉴(id="mobile-menu") — about·blog·magazine·약관류 등 (현재 보고 있는 페이지의 강조 표시는 그대로 유지)
  ③ fortune-adventure.html (fa- 메뉴)
  ④ 단독 페이지 메뉴 블록(HN_NAV_START~END) — contact/index.html, festival/list.html
  ⑤ footer.html 의 아이랑 / 플레이하기 / 소통·정보 목록(PC 3칸 + 모바일 접이식 3개)

건드리지 않는 곳: index.html(기준), festival/ 도구 5페이지(sync_festival_nav.py 가 따로 맞춤), festival/detail/, 메뉴가 없는 페이지.
이미 같으면 아무것도 바꾸지 않고(커밋 없음), 여러 번 실행해도 결과는 같습니다.

사용법:  python scripts/sync_site_nav.py          (실제로 고침)
         python scripts/sync_site_nav.py --dry     (고치지 않고 어떤 파일이 바뀔지만 보여줌)
         python scripts/sync_site_nav.py --check   (바뀔 파일이 있으면 종료코드 1)
"""
import html as _html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_standalone_nav import parse_index_menu, render_nav, apply_block, START, END  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'.git', 'node_modules', '.github', 'scripts', os.path.join('festival', 'detail')}
SKIP_FILES = {'index.html', 'festival/worldcup.html', 'festival/camping-worldcup.html',
              'festival/pick.html', 'festival/roulette.html', 'festival/poster.html'}
REV = {'/blog/': 'blog', '/partner/': 'partner'}       # 푸터에서 footerNav() 를 쓰는 항목

q = lambda s: _html.escape(s, quote=True)
def norm(s):
    """비교용: 공백, class 순서, 의미 없는 onclick="return true;" 차이는 무시한다."""
    s = s.replace(' onclick="return true;"', '')
    s = re.sub(r'class="([^"]*)"', lambda m: 'class="' + ' '.join(sorted(m.group(1).split())) + '"', s)
    return re.sub(r'\s+', '', s)

CHEV = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>'


def div_end(t, start):
    """t[start] 에서 시작하는 <div> 와 짝이 맞는 </div> 의 끝 위치."""
    i, d = start, 0
    while True:
        a, b = t.find('<div', i), t.find('</div>', i)
        if b == -1:
            return -1
        if a != -1 and a < b:
            d += 1
            i = a + 4
        else:
            d -= 1
            i = b + 6
            if d == 0:
                return i


# ───────────────────────── ① ③ 인라인 스타일 메뉴 ─────────────────────────
A_D = 'display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none'
A_M = 'display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none'
A_M2 = 'display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#94a3b8;font-size:14px;text-decoration:none'


def render_inline(groups, dd, desk_id, mob_id, widths):
    last = len(groups) - 1
    hov = "this.querySelector('.%s').style.opacity='%%s';this.querySelector('.%s').style.visibility='%%s'" % (dd, dd)
    d = '<div id="%s" style="display:none;align-items:center;gap:2px">\n' % desk_id
    for gi, (name, items) in enumerate(groups):
        d += '                    <div style="position:relative" onmouseenter="%s" onmouseleave="%s">\n' % (hov % ('1', 'visible'), hov % ('0', 'hidden'))
        d += '                        <button style="color:%s;font-weight:700;font-size:14px;display:flex;align-items:center;gap:4px;padding:4px 8px;background:none;border:none;cursor:pointer">%s %s</button>\n' % ('#94a3b8' if gi == last else '#64748b', q(name), CHEV)
        d += '                        <div class="%s" style="position:absolute;%s:0;top:100%%;margin-top:8px;width:%dpx;background:#fff;border-radius:16px;box-shadow:0 20px 25px -5px rgba(0,0,0,.15);border:1px solid #f1f5f9;padding:8px 0;opacity:0;visibility:hidden;transition:opacity .2s,visibility .2s;z-index:50">\n' % (dd, 'right' if gi == last else 'left', widths[min(gi, len(widths) - 1)])
        for l, h in items:
            d += '                            <a href="%s" style="%s">%s</a>\n' % (q(h), A_D, q(l))
        d += '                        </div>\n                    </div>\n'
    d += '                </div>'
    m = '<div id="%s" style="display:none;border-top:1px solid #e2e8f0;box-shadow:0 10px 15px -3px rgba(0,0,0,.1);background:#fff">\n            <div style="padding:16px;display:flex;flex-direction:column;gap:4px">\n' % mob_id
    for gi, (name, items) in enumerate(groups):
        if gi:
            m += '                <div style="border-top:1px solid #e2e8f0;margin:8px 0"></div>\n'
        if gi != last:
            m += '                <div style="font-size:12px;font-weight:700;color:#94a3b8;padding:%s">%s</div>\n' % ('8px 16px 2px' if gi == 0 else '0 16px 2px', q(name))
        for l, h in items:
            m += '                <a href="%s" style="%s">%s</a>\n' % (q(h), A_M2 if gi == last else A_M, q(l))
    m += '            </div>\n        </div>'
    return d, m


def sync_inline(t, groups, desk_id, mob_id, dd, widths):
    """인라인 스타일 메뉴 한 종류를 고친다. (새 텍스트, 상태)"""
    if ('id="%s"' % desk_id) not in t or ('id="%s"' % mob_id) not in t:
        return t, 'none'
    nd, nm = render_inline(groups, dd, desk_id, mob_id, widths)
    changed = False
    for tag, new in (('<div id="%s"' % mob_id, nm), ('<div id="%s"' % desk_id, nd)):     # 뒤쪽 위치부터
        s = t.find(tag)
        e = div_end(t, s)
        if e == -1:
            return t, 'fail'
        if norm(t[s:e]) != norm(new):
            t = t[:s] + new + t[e:]
            changed = True
    return t, 'updated' if changed else 'same'


# ───────────────────────── ② Tailwind 메뉴 ─────────────────────────
def active_labels(seg):
    """이미 '지금 보는 페이지' 강조(보라 글씨 + 연보라 배경)가 걸린 항목 이름들."""
    out = set()
    for m in re.finditer(r'<(?:a|button)\b[^>]*class="([^"]*)"[^>]*>([^<>]+)</(?:a|button)>', seg):
        c = m.group(1)
        if 'bg-indigo-50' in c and 'hover:bg-indigo-50' not in c:
            out.add(m.group(2).strip())
    return out


def sync_tailwind(t, groups, idx_html):
    if 'id="mobile-menu"' not in t or '<div class="hidden md:flex' not in t:
        return t, 'none'
    last = len(groups) - 1
    # PC: index.html 의 그룹 껍데기(버튼·드롭다운 여는 줄)를 그대로 가져오고 항목만 새로 만든다
    s = idx_html.index('<div class="hidden md:flex')
    ie = div_end(idx_html, s)
    chunk = idx_html[s:ie]
    parts = chunk.split('<div class="relative group">')[1:]
    ds = t.index('<div class="hidden md:flex')
    de = div_end(t, ds)
    old_d = t[ds:de]
    act = active_labels(old_d)
    new_d = old_d[:old_d.index('>') + 1] + '\n'
    for gi, part in enumerate(parts):
        k = part.index('<div class="absolute')
        k = part.index('\n', k) + 1
        head = part[:k]
        items = ''
        for l, h in groups[gi][1]:
            cls = ('block w-full text-left px-4 py-2.5 text-sm font-bold text-indigo-600 bg-indigo-50 transition' if l in act
                   else 'block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition')
            items += '                            <a href="%s" class="%s">%s</a>\n' % (q(h), cls, q(l))
        new_d += '                    <div class="relative group">' + head + items + '                        </div>\n                    </div>\n'
    new_d += '                </div>'
    # 모바일
    ms = t.index('<div id="mobile-menu"')
    me = div_end(t, ms)
    old_m = t[ms:me]
    inner_s = old_m.index('<div class="px-4 py-4 space-y-1">')
    inner_e = div_end(old_m, inner_s)
    mact = active_labels(old_m)
    mi = '<div class="px-4 py-4 space-y-1">\n'
    for gi, (name, items) in enumerate(groups):
        if gi:
            mi += '\n                <div class="border-t my-2"></div>\n'
        else:
            mi += '\n'
        if gi != last:
            mi += '                <div class="text-xs font-bold text-slate-400 px-4 pt-1 pb-1">%s</div>\n' % q(name)
        for l, h in items:
            if gi == last:
                cls = 'block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition text-sm'
            elif l in mact:
                cls = 'block w-full text-left px-4 py-3 rounded-xl font-bold text-indigo-600 bg-indigo-50 transition'
            else:
                cls = 'block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition'
            mi += '                <a href="%s" class="%s">%s</a>\n' % (q(h), cls, q(l))
    mi += '            </div>'
    new_m = old_m[:inner_s] + mi + old_m[inner_e:]
    changed = False
    if norm(new_m) != norm(old_m):
        t = t[:ms] + new_m + t[me:]
        changed = True
    if norm(new_d) != norm(old_d):
        t = t[:ds] + new_d + t[de:]
        changed = True
    return t, 'updated' if changed else 'same'


# ───────────────────────── ⑤ footer.html ─────────────────────────
def sync_footer(t, groups):
    def lis(items, ind):
        o = ''
        for l, h in items:
            oc = (' onclick="if(typeof footerNav===\'function\'){footerNav(\'%s\');return false;}"' % REV[h]) if h in REV else ''
            o += '%s<li><a href="%s"%s>%s</a></li>\n' % (ind, q(h), oc, q(l))
        return o
    changed = False
    for name, items in groups[:3]:
        bare = re.sub(r'^[^\w가-힣]+', '', name).strip()
        for pat, ind in ((r'(<h4 class="hpf-h">%s</h4>\s*<ul>\n)(.*?)(\s*</ul>)', ' ' * 20),
                         (r'(<summary>%s</summary>\s*<ul>\n)(.*?)(\s*</ul>)', ' ' * 20)):
            m = re.search(pat % re.escape(bare), t, re.S)
            if not m:
                return t, 'fail:푸터에서 "%s" 목록을 못 찾음' % bare
            new = lis(items, ind).rstrip('\n')
            if norm(m.group(2)) != norm(new):
                t = t[:m.start(2)] + new + t[m.end(2):]
                changed = True
    return t, 'updated' if changed else 'same'


# ───────────────────────── 실행 ─────────────────────────
def iter_files():
    for dp, dns, fns in os.walk(ROOT):
        rel_dp = os.path.relpath(dp, ROOT)
        dns[:] = [d for d in dns if d not in SKIP_DIRS and os.path.normpath(os.path.join(rel_dp, d)) not in SKIP_DIRS]
        for fn in fns:
            if fn.endswith('.html'):
                rel = os.path.normpath(os.path.join(rel_dp, fn)).replace(os.sep, '/')
                if rel not in SKIP_FILES:
                    yield rel


def process(rel, t, groups, idx_html):
    if rel == 'footer.html':
        return sync_footer(t, groups)
    st = []
    for fn in (lambda x: sync_inline(x, groups, 'g-nav-desktop', 'game-mobile-menu', 'g-dd-menu', [176, 160, 176, 176]),
               lambda x: sync_inline(x, groups, 'fa-nav-desktop', 'fa-mobile-menu', 'fa-dd-menu', [208, 160, 176, 176]),
               lambda x: sync_tailwind(x, groups, idx_html),
               lambda x: apply_block(x, render_nav(groups))):
        t, s = fn(t)
        st.append(s)
    st = [s for s in st if s not in ('none', 'nomarker')]
    if not st:
        return t, 'none'
    if any(s.startswith('fail') for s in st):
        return t, 'fail'
    return t, 'updated' if 'updated' in st else 'same'


def main():
    dry = '--dry' in sys.argv or '--check' in sys.argv
    with open(os.path.join(ROOT, 'index.html'), encoding='utf-8') as fp:
        idx_html = fp.read()
    groups = parse_index_menu(idx_html)
    n_up = n_same = n_none = 0
    fails, ups = [], []
    for rel in sorted(iter_files()):
        path = os.path.join(ROOT, rel)
        with open(path, encoding='utf-8', newline='') as fp:
            t = fp.read()
        if '소통·정보' not in t and 'HN_NAV_START' not in t:
            n_none += 1
            continue
        new, st = process(rel, t, groups, idx_html)
        if st == 'fail':
            fails.append(rel)
        elif st == 'updated':
            n_up += 1
            ups.append(rel)
            if not dry:
                with open(path, 'w', encoding='utf-8', newline='') as fp:
                    fp.write(new)
        elif st == 'same':
            n_same += 1
        else:
            n_none += 1
    for r in ups:
        print('  고침:' if not dry else '  고칠 예정:', r)
    print('메뉴 동기화: %d개 %s, %d개 이미 같음, %d개 메뉴 없음/대상 아님' % (n_up, '고침' if not dry else '고칠 예정', n_same, n_none))
    if fails:
        print('※ 고칠 자리를 못 찾아 건드리지 않은 파일:', ', '.join(fails))
    if '--check' in sys.argv and (ups or fails):
        sys.exit(1)


if __name__ == '__main__':
    main()
