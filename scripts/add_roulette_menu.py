#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상단 메뉴·푸터에 '나들이·캠핑장·숲 룰렛' 항목을 추가하는 일괄 수정 스크립트 (여러 번 실행해도 안전).

'캠핑장 월드컵' 메뉴 항목(한 줄짜리 <a href="/festival/camping-worldcup.html" …>캠핑장 월드컵</a>) 바로 아래에
같은 모양의 '나들이·캠핑장·숲 룰렛' 항목(/festival/roulette.html)을 한 줄 복사해 넣는다.
  - 데스크톱 드롭다운, 모바일 햄버거 메뉴, footer.html 의 목록(<li> 한 줄짜리)을 모두 처리한다.
  - 문장 속에 들어간 링크, 카드형 링크, FAQ 탭처럼 '메뉴 항목 한 줄'이 아닌 것은 건드리지 않는다.
  - 생성 스크립트(generate_community_posts.py 등)와 템플릿 안의 메뉴도 같이 고쳐서,
    자동 생성 페이지가 다시 옛 메뉴로 돌아가지 않게 한다.
  - 바로 아래 줄에 이미 roulette.html 항목이 있으면 건너뛴다.
  - 먼저 add_camping_menu.py 로 '캠핑장 월드컵' 항목이 들어가 있어야 한다(그 항목을 기준으로 삼는다).

사용법:  python scripts/add_roulette_menu.py          (실제로 고침)
         python scripts/add_roulette_menu.py --dry     (고치지 않고 결과만 보여줌)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'.git', 'node_modules', '.github', os.path.join('festival', 'detail')}
SKIP_FILES = {'add_worldcup_menu.py', 'add_camping_menu.py', 'add_roulette_menu.py', 'update_nav_menu.py'}
EXTS = ('.html', '.py')
OLD_LABEL = '캠핑장 월드컵'
OLD_HREF = '/festival/camping-worldcup.html'
NEW_LABEL = '나들이·캠핑장·숲 룰렛'
NEW_HREF = '/festival/roulette.html'
# 줄 전체가 메뉴 항목 하나인 경우만: 선택적 <li>, <a href="/festival/camping-worldcup.html" …>캠핑장 월드컵</a>, 선택적 </li>
ITEM_RE = re.compile(r'^(?P<ind>\s*)(?P<li>(?:<li[^>]*>)?)<a href="' + re.escape(OLD_HREF) + r'"(?P<attrs>(?: [^>]*)?)>' + OLD_LABEL + r'</a>(?P<end>(?:</li>)?)\s*$')


def convert(line):
    m = ITEM_RE.match(line)
    if not m or line.count('<a ') != 1:
        return None
    return '%s%s<a href="%s"%s>%s</a>%s' % (m.group('ind'), m.group('li'), NEW_HREF, m.group('attrs'), NEW_LABEL, m.group('end'))


def process(text):
    lines = text.split('\n')
    out, added = [], 0
    for i, ln in enumerate(lines):
        out.append(ln)
        new = convert(ln.rstrip('\r'))
        if new is None:
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ''
        if NEW_HREF in nxt:
            continue
        out.append(new + ('\r' if ln.endswith('\r') else ''))
        added += 1
    return '\n'.join(out), added


def main():
    dry = '--dry' in sys.argv
    files = changed = total = 0
    for dp, dns, fns in os.walk(ROOT):
        rel_dp = os.path.relpath(dp, ROOT)
        dns[:] = [d for d in dns if d not in SKIP_DIRS and os.path.join(rel_dp, d) not in SKIP_DIRS]
        for fn in fns:
            if not fn.endswith(EXTS) or fn in SKIP_FILES:
                continue
            path = os.path.join(dp, fn)
            try:
                with open(path, encoding='utf-8', newline='') as fp:
                    text = fp.read()
            except (UnicodeDecodeError, OSError):
                continue
            if OLD_LABEL not in text:
                continue
            files += 1
            new_text, added = process(text)
            if added:
                changed += 1
                total += added
                print('  %s: 항목 %d개 추가' % (os.path.relpath(path, ROOT), added))
                if not dry:
                    with open(path, 'w', encoding='utf-8', newline='') as fp:
                        fp.write(new_text)
    print('검사한 파일 %d개 중 %d개 수정, 메뉴 항목 %d개 추가%s' % (files, changed, total, ' (dry-run: 실제로는 고치지 않음)' if dry else ''))


if __name__ == '__main__':
    main()
