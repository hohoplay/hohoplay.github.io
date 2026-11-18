#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상단 메뉴 동기화 (Tailwind 없이 단독으로 쓰는 페이지용)

메인 index.html 의 상단 메뉴(PC 드롭다운 + 모바일 햄버거)를 읽어서, 같은 항목·같은 순서의
상단 메뉴를 "인라인 스타일만 쓰는 독립 블록"으로 만들어 아래 페이지에 넣는다.
  - contact/index.html      (문의하기)
  - festival/list.html      (축제 목록 — fetch_data.py 가 매일 새로 만들 때도 이 블록을 같이 넣는다)

메뉴를 바꾸는 방법: index.html 의 메뉴만 고치면 된다. 이 스크립트(워크플로 "Sync Standalone Nav")를
실행하면 위 페이지들이 같은 메뉴로 맞춰진다. 이미 같으면 아무것도 바꾸지 않는다(여러 번 실행해도 안전).

블록은 <!-- HN_NAV_START --> ... <!-- HN_NAV_END --> 로 감싸 있어서, 그 사이만 교체한다.
(아직 마커가 없는 contact/index.html 은 기존 <nav>…</nav> 를 이 블록으로 한 번 교체한다.)

사용법:  python scripts/sync_standalone_nav.py          (실제로 고침)
         python scripts/sync_standalone_nav.py --dry     (고치지 않고 결과만 보여줌)
"""
import html as _html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START = '<!-- HN_NAV_START (scripts/sync_standalone_nav.py 가 만든 블록입니다. 직접 고치지 말고 index.html 메뉴를 고친 뒤 동기화하세요) -->'
END = '<!-- HN_NAV_END -->'
TARGETS = ['contact/index.html', 'festival/list.html']

# index.html 메뉴의 navigateTo('x') / mobileNav('x') 는 실제 주소로 바꿔서 쓴다
PAGE_URL = {'blog': '/blog/', 'partner': '/partner/', 'terms': '/terms/', 'privacy': '/privacy/',
            'copyright': '/copyright/', 'guide': '/guide/', 'about': '/about/', 'index': '/game/', 'fortune': '/fortune/'}


def _item_href(line):
    m = re.search(r'href="([^"]+)"', line)
    if m:
        return m.group(1)
    m = re.search(r"location\.href\s*=\s*'([^']+)'", line)
    if m:
        return m.group(1)
    m = re.search(r"(?:navigateTo|mobileNav)\('([^']+)'\)", line)
    if m:
        return PAGE_URL.get(m.group(1))
    return None


def parse_index_menu(index_html):
    """index.html 의 PC 드롭다운 메뉴를 [(그룹 이름, [(항목 이름, 주소), ...]), ...] 로 읽는다."""
    s = index_html.index('<div class="hidden md:flex')
    e = index_html.index('<!-- 검색 바로가기', s)
    block = index_html[s:e]
    groups = []
    for part in block.split('<div class="relative group">')[1:]:
        hm = re.search(r'<button[^>]*>([^<]+?)\s*<svg', part)
        if not hm:
            raise ValueError('메뉴 그룹 이름을 못 찾음')
        items = []
        for line in part.split('\n'):
            ls = line.strip()
            if not (ls.startswith('<a ') or ls.startswith('<button onclick')):
                continue
            lm = re.search(r'>([^<>]+)</(?:a|button)>\s*$', ls)
            href = _item_href(ls)
            if not lm or not href:
                raise ValueError('메뉴 항목을 읽지 못함: ' + ls[:80])
            items.append((_html.unescape(lm.group(1)), href))
        groups.append((_html.unescape(hm.group(1)).strip(), items))
    if len(groups) < 3 or any(not g[1] for g in groups):
        raise ValueError('메뉴 그룹 수가 이상함')
    return groups


A_D = 'display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none'
A_M = 'display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none'
A_M2 = 'display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#94a3b8;font-size:14px;text-decoration:none'
HOVER = "this.querySelector('.hn-dd').style.opacity='%s';this.querySelector('.hn-dd').style.visibility='%s'"
CHEV = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>'


def render_nav(groups):
    q = lambda t: _html.escape(t, quote=True)
    last = len(groups) - 1
    desk = ''
    for gi, (name, items) in enumerate(groups):
        small = gi == last                      # 마지막 그룹(약관·정책)은 연한 글씨 + 오른쪽 정렬
        width = 176 if (small or len(name) > 8) else 208 if gi == 0 else 160
        desk += ('<div style="position:relative" onmouseenter="%s" onmouseleave="%s">'
                 '<button type="button" style="color:%s;font-weight:700;font-size:14px;display:flex;align-items:center;gap:4px;padding:4px 8px;background:none;border:none;cursor:pointer;font-family:inherit">%s %s</button>'
                 '<div class="hn-dd" style="position:absolute;%s:0;top:100%%;margin-top:8px;width:%dpx;background:#fff;border-radius:16px;box-shadow:0 20px 25px -5px rgba(0,0,0,.15);border:1px solid #f1f5f9;padding:8px 0;opacity:0;visibility:hidden;transition:opacity .2s,visibility .2s;z-index:50">%s</div></div>'
                 % (HOVER % ('1', 'visible'), HOVER % ('0', 'hidden'), '#94a3b8' if small else '#64748b', q(name), CHEV,
                    'right' if small else 'left', width,
                    ''.join('<a href="%s" style="%s">%s</a>' % (q(h), A_D, q(l)) for l, h in items)))
    mob = '<div style="padding:16px;display:flex;flex-direction:column;gap:4px">'
    for gi, (name, items) in enumerate(groups):
        if gi:
            mob += '<div style="border-top:1px solid #e2e8f0;margin:8px 0"></div>'
        if gi != last:
            mob += '<div style="font-size:12px;font-weight:700;color:#94a3b8;padding:%s">%s</div>' % ('8px 16px 2px' if gi == 0 else '0 16px 2px', q(name))
        mob += ''.join('<a href="%s" style="%s">%s</a>' % (q(h), A_M2 if gi == last else A_M, q(l)) for l, h in items)
    mob += '</div>'
    return (
        START + '\n'
        '<nav id="hn-nav" style="background:rgba(255,255,255,0.92);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid #e2e8f0;position:sticky;top:0;z-index:50;box-shadow:0 1px 4px rgba(0,0,0,0.06);font-family:\'Noto Sans KR\',sans-serif;text-align:left">'
        '<div style="max-width:1280px;margin:0 auto;padding:0 1rem;display:flex;align-items:center;justify-content:space-between;height:56px">'
        '<a href="/" style="display:flex;align-items:center;gap:8px;text-decoration:none">'
        '<span style="width:32px;height:32px;background:#4f46e5;border-radius:12px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:9px;font-weight:900;letter-spacing:-0.5px;line-height:1.1;text-align:center;box-shadow:0 4px 10px rgba(79,70,229,0.3)">HOHO<br>PLAY</span>'
        '<span style="font-size:1.125rem;font-weight:900;letter-spacing:-0.03em;text-transform:uppercase"><span style="color:#4f46e5">HOHO</span><span style="color:#8b5cf6"> PLAY</span></span></a>'
        '<div id="hn-desktop" style="display:none;align-items:center;gap:2px">' + desk + '</div>'
        '<button type="button" id="hn-burger" aria-label="메뉴 열기" onclick="hnToggle()" style="display:flex;flex-direction:column;justify-content:center;align-items:center;width:36px;height:36px;gap:6px;border-radius:12px;background:none;border:none;cursor:pointer">'
        '<span id="hnbar1" style="display:block;width:20px;height:2px;background:#334155;transition:.3s"></span>'
        '<span id="hnbar2" style="display:block;width:20px;height:2px;background:#334155;transition:.3s"></span>'
        '<span id="hnbar3" style="display:block;width:20px;height:2px;background:#334155;transition:.3s"></span></button>'
        '</div>'
        '<div id="hn-mobile" style="display:none;border-top:1px solid #e2e8f0;box-shadow:0 10px 15px -3px rgba(0,0,0,.1);background:#fff;max-height:calc(100vh - 56px);overflow-y:auto">' + mob + '</div>'
        '</nav>\n'
        '<script>\n'
        '(function(){\n'
        '  function hnApply(){\n'
        '    var wide = window.innerWidth >= 768;\n'
        '    var d = document.getElementById("hn-desktop"), b = document.getElementById("hn-burger"), m = document.getElementById("hn-mobile");\n'
        '    if (d) d.style.display = wide ? "flex" : "none";\n'
        '    if (b) b.style.display = wide ? "none" : "flex";\n'
        '    if (wide && m) m.style.display = "none";\n'
        '  }\n'
        '  window.hnToggle = function(){\n'
        '    var m = document.getElementById("hn-mobile"), b1 = document.getElementById("hnbar1"), b2 = document.getElementById("hnbar2"), b3 = document.getElementById("hnbar3");\n'
        '    var open = m.style.display === "block";\n'
        '    m.style.display = open ? "none" : "block";\n'
        '    b1.style.transform = open ? "" : "translateY(6px) rotate(45deg)";\n'
        '    b2.style.opacity = open ? "1" : "0";\n'
        '    b3.style.transform = open ? "" : "translateY(-6px) rotate(-45deg)";\n'
        '  };\n'
        '  hnApply();\n'
        '  window.addEventListener("resize", hnApply);\n'
        '})();\n'
        '</script>\n' + END)


def render_nav_block(root=ROOT):
    """fetch_data.py 가 쓰는 함수. 읽기에 실패하면 빈 문자열을 돌려줘서(메뉴만 빠지고) 매일 도는 작업은 멈추지 않는다."""
    try:
        with open(os.path.join(root, 'index.html'), encoding='utf-8') as fp:
            return render_nav(parse_index_menu(fp.read()))
    except Exception as ex:  # noqa
        print('[sync_standalone_nav] 메뉴 블록 생성 실패(빈 블록 사용): %s' % ex)
        return ''


def apply_block(text, block):
    """text 안의 메뉴 블록을 교체한다. (새 텍스트, 상태) 반환."""
    if START[:20] in text and END in text:
        s = text.index('<!-- HN_NAV_START')
        e = text.index(END, s) + len(END)
        new = text[:s] + block + text[e:]
        return new, ('same' if new == text else 'updated')
    return text, 'nomarker'


def main():
    dry = '--dry' in sys.argv
    block = render_nav_block()
    if not block:
        print('메뉴 블록을 만들지 못했습니다. index.html 의 메뉴 구조를 확인하세요.')
        sys.exit(1)
    for rel in TARGETS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print('없음:', rel)
            continue
        with open(path, encoding='utf-8', newline='') as fp:
            text = fp.read()
        new, st = apply_block(text, block)
        if st == 'nomarker':
            m = re.search(r'<nav\b.*?</nav>\s*', text, re.S)
            if rel == 'contact/index.html' and m:
                new, st = text[:m.start()] + block + '\n\n    ' + text[m.end():], 'inserted'
            else:
                print('건너뜀(마커 없음):', rel)
                continue
        print('%-22s %s' % (rel, st))
        if st != 'same' and not dry:
            with open(path, 'w', encoding='utf-8', newline='') as fp:
                fp.write(new)


if __name__ == '__main__':
    main()
