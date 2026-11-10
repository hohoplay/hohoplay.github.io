#!/usr/bin/env python3
"""scripts/add_kids_images.py

blog/kids-course/*.html (코스 글)과 blog/indoor-kids/<지역>.html (실내 놀이 지역 글)의 각 장소에
data/kids_places.json 의 공식 사진(image 필드)을 넣는다. 만드는 방식은 scripts/kids_images.py 참고.

 - 코스 글:   각 장소 제목(<h2>N. <a …>장소</a></h2>) 바로 아래에 <figure>(사진 + "사진: 한국관광공사")
 - 지역 글:   각 .place-card 맨 위에 <img class="place-thumb"> (+ <style>에 .place-thumb 규칙이 없으면 추가)
 - 사진(image)이 없는 장소는 그대로 둔다. 표식(<!--kp:v1-->)으로 구간을 구분하므로 여러 번 실행해도 같은 결과.
 - 목록 페이지(index.html)는 장소 카드가 없어 건드리지 않는다.

사용법(저장소 루트에서):  python3 scripts/add_kids_images.py [--dry-run] [--root 경로]
종료 코드: 0 = 정상, 1 = 건드리지 못한 글이 있음
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kids_images as ki  # noqa: E402

ROOT = os.path.dirname(HERE)
for i, a in enumerate(sys.argv):
    if a == '--root' and i + 1 < len(sys.argv):
        ROOT = os.path.abspath(sys.argv[i + 1])

COURSE_H2 = re.compile(r'(<h2 style="[^"]*">\d+\. <a href="/festival/detail/(kids-\d+)\.html"[^>]*>[^<]*</a></h2>)')
CARD_OPEN = re.compile(r'(  <a href="/festival/detail/(kids-\d+)\.html" class="place-card">\n)')


def apply_course(page, places):
    page = ki.KP_RE.sub('', page)
    n = [0, 0]

    def rep(m):
        p = places.get(m.group(2))
        n[0] += 1
        fig = ki.course_figure(p) if p else ''
        n[1] += bool(fig)
        return m.group(1) + fig
    out = COURSE_H2.sub(rep, page)
    return out, n


REGION_OLD_THUMB = re.compile(r'    ' + re.escape(ki.KP_START) + r'.*?' + re.escape(ki.KP_END) + r'\n', re.S)


def apply_region(page, places):
    page = REGION_OLD_THUMB.sub('', page)
    n = [0, 0]

    def rep(m):
        p = places.get(m.group(2))
        n[0] += 1
        th = ki.card_thumb(p) if p else ''
        n[1] += bool(th)
        return m.group(1) + (('    ' + th + '\n') if th else '')
    out = CARD_OPEN.sub(rep, page)
    if n[1] and ki.THUMB_CSS_MARK not in out:
        anchor = '  .place-name {'
        if anchor not in out:
            return None, n
        out = out.replace(anchor, ki.THUMB_CSS + anchor, 1)
    return out, n


def main():
    dry = '--dry-run' in sys.argv
    with open(os.path.join(ROOT, 'data', 'kids_places.json'), encoding='utf-8') as f:
        places = {p['contentid']: p for p in json.load(f)}
    jobs = [(p, apply_course) for p in sorted(glob.glob(os.path.join(ROOT, 'blog', 'kids-course', '*.html'))) if not p.endswith('index.html')]
    jobs += [(p, apply_region) for p in sorted(glob.glob(os.path.join(ROOT, 'blog', 'indoor-kids', '*.html'))) if not p.endswith('index.html')]
    fails = changed = same = tot = withimg = 0
    for path, fn in jobs:
        with open(path, encoding='utf-8') as f:
            page = f.read()
        out, n = fn(page, places)
        name = os.path.relpath(path, ROOT)
        if out is None or n[0] == 0:
            print('건드리지 못함:', name)
            fails += 1
            continue
        tot += n[0]
        withimg += n[1]
        if out == page:
            same += 1
            continue
        changed += 1
        if not dry:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(out)
    print('글 %d개 / 수정 %d개 / 변경 없음 %d개 / 실패 %d개 — 장소 %d곳 중 사진 %d곳' % (len(jobs), changed, same, fails, tot, withimg))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
