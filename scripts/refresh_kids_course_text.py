#!/usr/bin/env python3
"""scripts/refresh_kids_course_text.py

blog/kids-course/*.html (아이랑 나들이 추천 코스 글)의 문구를 data/kids_places.json 기준으로 다시 쓴다.

바꾸는 곳 (표식으로 구간을 구분하므로 여러 번 실행해도 같은 결과)
  1) <!--kc:v1-->…<!--/kc:v1-->  소개 + "코스 한눈에 보기"
  2) <!--kr:v1-->…<!--/kr:v1-->  추천 동선과 방문 요령
  3) <!--ko:v1-->…<!--/ko:v1-->  마무리 (처음 실행 때는 옛 "이 코스, 이렇게 다녀오세요" 구간을 찾아 표식으로 감싼다)
  4) <meta name="description"> / og:description / twitter:description 문구

  5) <meta name="robots" content="noindex,follow"> 가 없으면 canonical 아래에 넣는다 (코스 글 전체 검색 제외)

바뀌지 않는 것: 장소 목록·주소·요금·전화번호·장소 설명·링크·메타태그(위 4)·공유/댓글 영역·noindex 설정.
기대한 패턴이 없으면 그 글은 건드리지 않고 경고만 남긴다.

사용법(저장소 루트에서):  python3 scripts/refresh_kids_course_text.py [--dry-run] [--root 경로]
종료 코드: 0 = 정상, 1 = 건드리지 못한 글이 있음
"""
import glob
import html as html_lib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import add_kids_course_route as rte   # noqa: E402
import kids_course_text as kct        # noqa: E402

ROOT = rte.ROOT
KC_RE = re.compile(r'<!--kc:v1-->.*?<!--/kc:v1-->', re.S)
KR_RE = re.compile(re.escape(rte.KR_START) + r'.*?' + re.escape(rte.KR_END), re.S)
KO_RE = re.compile(re.escape(kct.KO_START) + r'.*?' + re.escape(kct.KO_END), re.S)
OLD_OUTRO_RE = re.compile(r'<h2 style="[^"]*">이 코스, 이렇게 다녀오세요</h2>.*?(?=<div style="margin-top:32px;padding-top:20px;border-top:1px solid #f1f5f9)', re.S)
DESC_RES = [re.compile(r'(<meta name="description" content=")[^"]*(">)'),
            re.compile(r'(<meta property="og:description" content=")[^"]*(">)'),
            re.compile(r'(<meta name="twitter:description" content=")[^"]*(">)')]


def transform(page, places):
    region = rte.region_name(page)
    if not region:
        return None, '제목에서 지역명을 찾지 못함'
    entries = []
    for cid, name in rte.RE_PLACE.findall(page):
        p = places.get(cid)
        if p is None or p.get('lat') is None or p.get('lng') is None:
            return None, '장소 데이터/좌표 없음: %s' % cid
        entries.append((cid, html_lib.unescape(name), p))
    if len(entries) < 2:
        return None, '장소 블록이 2개 미만'
    if not KC_RE.search(page) or not KR_RE.search(page):
        return None, '소개(kc)·동선(kr) 표식을 찾지 못함'

    out = KC_RE.sub(lambda m: '<!--kc:v1-->' + kct.build_kc(region, entries) + '<!--/kc:v1-->', page, count=1)
    out = KR_RE.sub(lambda m: rte.KR_START + kct.build_kr(region, entries) + rte.KR_END, out, count=1)
    ko = kct.KO_START + kct.build_outro(region, entries) + kct.KO_END
    if KO_RE.search(out):
        out = KO_RE.sub(lambda m: ko, out, count=1)
    elif OLD_OUTRO_RE.search(out):
        out = OLD_OUTRO_RE.sub(lambda m: ko, out, count=1)
    else:
        return None, '마무리 구간을 찾지 못함'

    desc = html_lib.escape(kct.build_meta_desc(region, entries))
    for rx in DESC_RES:
        out = rx.sub(lambda m: m.group(1) + desc + m.group(2), out, count=1)
    out = kct.ensure_noindex(out)   # 코스 글은 모두 noindex,follow (2026-11-10 결정)
    return out, 'ok'


def main():
    dry = '--dry-run' in sys.argv
    places = rte.load_places()
    files = sorted(p for p in glob.glob(os.path.join(ROOT, 'blog', 'kids-course', '*.html')) if not p.endswith('index.html'))
    changed = same = failed = 0
    for path in files:
        rel = os.path.relpath(path, ROOT)
        with open(path, 'r', encoding='utf-8') as fp:
            before = fp.read()
        after, msg = transform(before, places)
        if after is None:
            failed += 1
            print('⚠️ %s: %s — 건드리지 않음' % (rel, msg), file=sys.stderr)
            continue
        if after == before:
            same += 1
            continue
        changed += 1
        if not dry:
            with open(path, 'w', encoding='utf-8', newline='\n') as fp:
                fp.write(after)
    print('코스 글 %d개 / 수정 %d개 / 변경 없음 %d개 / 실패 %d개%s' % (len(files), changed, same, failed, ' (dry-run)' if dry else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
