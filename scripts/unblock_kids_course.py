#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/unblock_kids_course.py

[1회성] blog/kids-course/*.html (아이랑 나들이 코스 글 43편 + 목록 index.html)의
<meta name="robots" content="noindex,follow"> 를 지운다. (2026-11-10 "코스 글 전체 noindex" 결정을 번복)

  - 애드센스 안내 "핵심 서비스의 글이 검색에서 빠져 있습니다" 대응.
  - 얇은 글(add_kids_course_route.THIN_NOINDEX_SLUGS)은 보강하기 전까지 noindex 를 유지한다.
  - noindex 만 지운다. 그 외 robots 지시(예: max-image-preview)와 본문은 건드리지 않는다.
  - canonical 이 없거나 자기 자신이 아닌 글은 검색 허용 전에 사람이 보도록 경고를 남긴다.
  - 여러 번 실행해도 결과는 같다.

사용법(저장소 루트에서):  python3 scripts/unblock_kids_course.py [--dry-run] [--root 경로]
종료 코드: 0 = 정상, 1 = 경고가 있는 글이 있음(파일은 그대로 처리됨)
"""
import glob
import os
import re
import sys

ROOT = os.getcwd()
if '--root' in sys.argv:
    ROOT = os.path.abspath(sys.argv[sys.argv.index('--root') + 1])
DRY = '--dry-run' in sys.argv

# add_kids_course_route.THIN_NOINDEX_SLUGS 와 같은 값으로 유지할 것
THIN_NOINDEX_SLUGS = set()  # 2026-11-26: 4편 보강 완료(5곳 이상)로 noindex 해제
NOINDEX_RE = re.compile(r'[ \t]*<meta name="robots" content="[^"]*noindex[^"]*">[ \t]*\n?')
CANON_RE = re.compile(r'<link rel="canonical" href="([^"]*)">')


def main():
    files = sorted(glob.glob(os.path.join(ROOT, 'blog', 'kids-course', '*.html')))
    if not files:
        print('blog/kids-course/*.html 를 찾지 못했습니다 (--root 확인).', file=sys.stderr)
        return 1
    seen = {os.path.basename(f)[:-5] for f in files}
    for s in sorted(THIN_NOINDEX_SLUGS - seen):
        print('⚠️ 얇은 글 목록의 %s 파일이 없습니다 (이름 확인).' % s, file=sys.stderr)

    unblocked = kept = same = warn = 0
    for path in files:
        slug = os.path.basename(path)[:-5]
        rel = os.path.relpath(path, ROOT)
        with open(path, 'r', encoding='utf-8') as fp:
            before = fp.read()
        if slug in THIN_NOINDEX_SLUGS:
            kept += 1
            print('유지(얇은 글): %s — noindex %s' % (rel, '있음' if 'noindex' in before else '없음 ⚠️'))
            if 'noindex' not in before:
                warn += 1
            continue
        after = NOINDEX_RE.sub('', before)
        m = CANON_RE.search(after)
        if not m:
            warn += 1
            print('⚠️ %s: canonical 링크가 없습니다 — 확인 필요' % rel, file=sys.stderr)
        elif not m.group(1).rstrip('/').endswith(('/blog/kids-course/' + slug + '.html', '/blog/kids-course')) and slug != 'index':
            warn += 1
            print('⚠️ %s: canonical 이 자기 주소가 아닙니다 → %s' % (rel, m.group(1)), file=sys.stderr)
        if re.search(r'name="robots"[^>]*noindex', after):
            warn += 1
            print('⚠️ %s: noindex 가 다른 형태로 남아 있습니다 — 직접 확인' % rel, file=sys.stderr)
        if after == before:
            same += 1
            continue
        unblocked += 1
        print('해제: %s' % rel)
        if not DRY:
            with open(path, 'w', encoding='utf-8', newline='\n') as fp:
                fp.write(after)

    print('\n=== 결과 ===  해제 %d · 이미 해제됨 %d · 얇은 글 유지 %d · 경고 %d%s' %
          (unblocked, same, kept, warn, '  (dry-run: 저장 안 함)' if DRY else ''))
    return 1 if warn else 0


if __name__ == '__main__':
    sys.exit(main())
