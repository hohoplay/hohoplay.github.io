#!/usr/bin/env python3
"""목차 리모컨(/festival/toc-remote.js) 스크립트 태그를 기존 페이지에 한 번에 넣는다. 여러 번 실행해도 결과는 같다.

대상: festival/detail/kids-*.html, 본문 목차(pt-toc)가 있는 festival/detail/*.html, blog/kids-course/*.html (index.html 제외)
새로 만들어지는 페이지는 templates/kids_detail_template.html 과 fetch_data.py 템플릿이 같은 태그를 넣는다.
"""
import glob
import os
import sys

TAG = '<script src="/festival/toc-remote.js?v=20261127a" defer></script>'
MARK = 'toc-remote.js'


def targets():
    for p in sorted(glob.glob('festival/detail/*.html')):
        yield p
    for p in sorted(glob.glob('blog/kids-course/*.html')):
        if os.path.basename(p) != 'index.html':
            yield p


def main():
    added = skipped = 0
    for p in targets():
        with open(p, 'r', encoding='utf-8') as f:
            s = f.read()
        if MARK in s:
            continue
        base = os.path.basename(p)
        if p.startswith('festival/detail/') and not base.startswith('kids-') and 'pt-toc' not in s:
            skipped += 1  # 소제목이 없는 단순 페이지
            continue
        i = s.rfind('</body>')
        if i == -1:
            skipped += 1
            continue
        with open(p, 'w', encoding='utf-8') as f:
            f.write(s[:i] + TAG + '\n' + s[i:])
        added += 1
    print(f'목차 리모컨 태그 추가 {added}개, 건너뜀 {skipped}개')
    return 0


if __name__ == '__main__':
    sys.exit(main())
