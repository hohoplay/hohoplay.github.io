#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/extend_kids_course_places.py

이미 만들어 둔 코스 글(blog/kids-course/<슬러그>.html)에, 그 뒤 지도에 추가된 같은 구·시 장소를 이어 붙인다.

 - 대상 장소: data/kids_places.json 에서 숨김이 아니고, 설명에 '확인하지 못했다'가 없고(정보 확인됨),
   build_kids_course_pages.EXCLUDE 에 없고, 코스 글에 아직 없는 장소 (같은 구·시)
 - 같은 이름의 중복 장소는 한 곳만 넣고 나머지는 알려 준다.
 - 새 장소 블록은 마지막 장소 뒤(추천 동선 앞)에 이어 붙이고 번호를 이어서 매긴다.
 - 이어서 필요한 마무리(사진 조각, 소개·동선 문구, 목록 숫자)를 같은 스크립트가 처리한다:
     add_kids_images.py → refresh_kids_course_text.py 는 따로 실행(아래 사용법)

사용법(저장소 루트에서):
    python3 scripts/extend_kids_course_places.py [--dry-run] [--skip=kids-0001,kids-0002] 슬러그 [슬러그 ...]
    python3 scripts/add_kids_images.py
    python3 scripts/refresh_kids_course_text.py
(--dry-run 은 어떤 장소가 들어갈지만 보여 준다. 사진·문구 단계는 위 두 줄을 이어서 실행)
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_kids_course_pages as bk   # noqa: E402
import add_kids_course_route as rte    # noqa: E402

ROOT = os.path.dirname(HERE)
UNV = bk.UNVERIFIED
PLACE_H2 = re.compile(r'<h2[^>]*>\s*(\d+)\.\s*<a href="/festival/detail/(kids-\d+)\.html"')


def norm_title(t):
    return re.sub(r'[\s·\-()]', '', t or '')


def sido_gu(addr):
    tk = (addr or '').split()
    return (tk[0][:2] if tk else ''), (tk[1] if len(tk) > 1 else '')


def main():
    dry = '--dry-run' in sys.argv
    slugs = [a for a in sys.argv[1:] if not a.startswith('--')]
    skip = set()
    for a in sys.argv[1:]:
        if a.startswith('--skip='):
            skip |= set(x for x in a[7:].split(',') if x)
    if not slugs:
        print(__doc__); return 1
    with open(os.path.join(ROOT, 'data', 'kids_places.json'), encoding='utf-8') as f:
        allp = json.load(f)
    places = [p for p in allp if not p.get('hidden')]
    byid = {p['contentid']: p for p in places}
    total_added = 0
    for slug in slugs:
        path = os.path.join(ROOT, 'blog', 'kids-course', slug + '.html')
        page = open(path, encoding='utf-8').read()
        ids = [m.group(2) for m in PLACE_H2.finditer(page)]
        if not ids or ids[0] not in byid:
            print('%s: 기존 장소를 읽지 못해 건너뜀' % slug); continue
        sg = sido_gu(byid[ids[0]]['addr'])
        have_titles = {norm_title(byid[i]['title']) for i in ids if i in byid}
        picked, skipped = [], []
        for p in sorted(places, key=lambda x: x['contentid']):
            if p['contentid'] in ids or p['contentid'] in bk.EXCLUDE or sido_gu(p.get('addr')) != sg:
                continue
            if p['contentid'] in skip:
                skipped.append((p, '직접 제외')); continue
            if UNV in (p.get('overview') or ''):
                skipped.append((p, '정보 미확인')); continue
            nt = norm_title(p['title'])
            if nt in have_titles:
                skipped.append((p, '같은 이름이 이미 있음(중복 장소)')); continue
            have_titles.add(nt)
            picked.append(p)
        print('\n## %s (%s %s) 현재 %d곳 → 추가 %d곳' % (slug, sg[0], sg[1], len(ids), len(picked)))
        for p in picked:
            print('   + %s %s' % (p['contentid'], p['title']))
        for p, why in skipped:
            print('   - %s %s  (%s)' % (p['contentid'], p['title'], why))
        if dry or not picked:
            continue
        n0 = len(ids)
        blocks = '\n'.join(bk.place_block(n0 + i + 1, p) for i, p in enumerate(picked)) + '\n'
        if rte.KR_START not in page:
            print('   !! 추천 동선 표식(KR_START)이 없어 건너뜀'); continue
        page = page.replace(rte.KR_START, blocks + rte.KR_START, 1)
        n = n0 + len(picked)
        page, c = re.subn(r'(아이랑 갈만한 곳 )\d+(곳)', lambda m: m.group(1) + str(n) + m.group(2), page, count=1)
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(page)
        total_added += len(picked)
        # 목록 페이지 카드 숫자
        ip = os.path.join(ROOT, 'blog', 'kids-course', 'index.html')
        idx = open(ip, encoding='utf-8').read()
        idx = re.sub(r'(<a class="post-item" href="/blog/kids-course/%s\.html">.*?<span>장소 )\d+(곳</span>)' % re.escape(slug),
                     lambda m: m.group(1) + str(n) + m.group(2), idx, count=1, flags=re.S)
        with open(ip, 'w', encoding='utf-8', newline='') as f:
            f.write(idx)
    print('\n추가한 장소 합계: %d곳' % total_added)
    return 0


if __name__ == '__main__':
    sys.exit(main())
