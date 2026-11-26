#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/noindex_pages.py

[1회성] 사이트 주제와 무관한 내부·개인용 페이지에 검색 제외(noindex)를 넣는다.
  - HOHO_Holdings_AI_Office_v6.html
  - adsense_guide_v2.html
  - danang_guide/danang_guide.html

하는 일: <head> 안에 <meta name="robots" content="noindex,nofollow"> 를 넣는다.
  - 이미 robots 메타가 있으면 그 줄만 noindex,nofollow 로 바꾼다.
  - 본문·스타일·스크립트는 건드리지 않는다. 여러 번 실행해도 결과는 같다.
  - 파일이 없으면 경고만 남기고 넘어간다.

주의: noindex 는 "검색에 나오지 않게" 하는 것이지 "접속을 막는" 것이 아니다. 주소를 아는 사람은 열 수 있다.

사용법(저장소 루트에서):  python3 scripts/noindex_pages.py [--dry-run] [--root 경로]
"""
import os
import re
import sys

ROOT = os.getcwd()
if '--root' in sys.argv:
    ROOT = os.path.abspath(sys.argv[sys.argv.index('--root') + 1])
DRY = '--dry-run' in sys.argv

TARGETS = [
    'HOHO_Holdings_AI_Office_v6.html',
    'adsense_guide_v2.html',
    'danang_guide/danang_guide.html',
]
META = '<meta name="robots" content="noindex,nofollow">'
ROBOTS_RE = re.compile(r'<meta\s+name=["\']robots["\'][^>]*>', re.I)
HEAD_RE = re.compile(r'<head\b[^>]*>', re.I)


def transform(text):
    if ROBOTS_RE.search(text):
        new = ROBOTS_RE.sub(META, text, count=1)
        return new, ('이미 있음' if new == text else '바꿈')
    m = HEAD_RE.search(text)
    if not m:
        return None, '<head> 를 찾지 못함'
    return text[:m.end()] + '\n' + META + text[m.end():], '넣음'


def main():
    bad = 0
    for rel in TARGETS:
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            print('⚠️ %s: 파일이 없습니다 (경로 확인)' % rel, file=sys.stderr)
            bad += 1
            continue
        with open(path, 'r', encoding='utf-8', errors='strict', newline='') as f:
            before = f.read()
        after, msg = transform(before)
        if after is None:
            print('⚠️ %s: %s — 건드리지 않음' % (rel, msg), file=sys.stderr)
            bad += 1
            continue
        print('%s: noindex %s' % (rel, msg))
        if after != before and not DRY:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(after)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
