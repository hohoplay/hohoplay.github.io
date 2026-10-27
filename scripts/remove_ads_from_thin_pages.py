#!/usr/bin/env python3
"""scripts/remove_ads_from_thin_pages.py

[1회성 정리 스크립트] 애드센스 "가치가 별로 없는 콘텐츠" 대응.

본문이 짧은 자동 생성 페이지에서 광고 코드만 제거한다.
  1) festival/detail/*.html  (축제·자연관광지·캠핑장·아이랑 나들이 상세페이지)
  2) blog/posts/*.html 중 noindex 로 표시된 글 (공지사항·업데이트)

제거 대상: adsbygoogle.js 로더 <script>, <ins class="adsbygoogle"> 광고 단위
(감싸는 div·안내 주석·push 스크립트 포함). 본문 글자·링크·메타태그는 건드리지 않는다.
이미 정리된 파일은 다시 실행해도 변하지 않는다(멱등).

사용법(저장소 루트에서):  python3 scripts/remove_ads_from_thin_pages.py [--dry-run]
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1) 로더 스크립트 (앞쪽 들여쓰기와 뒤 줄바꿈까지 같이 지움)
RE_LOADER = re.compile(
    r'[ \t]*<script\b[^>]*pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js[^>]*>\s*</script>[ \t]*\n?',
    re.I)

# 2) 광고 단위: (안내 주석) + 감싸는 div + <ins> + push 스크립트 + </div>
RE_AD_BLOCK = re.compile(
    r'(?:[ \t]*<!--[^>]*?광고[^>]*?-->[ \t]*\n)?'
    r'[ \t]*<div\b[^>]*>\s*'
    r'<ins\b[^>]*class="adsbygoogle"[^>]*>\s*</ins>\s*'
    r'<script>\s*\(adsbygoogle\s*=\s*window\.adsbygoogle\s*\|\|\s*\[\]\)\.push\(\{\}\);?\s*</script>\s*'
    r'</div>[ \t]*\n?',
    re.S)

# 3) 위 모양이 아닌 떠돌이 광고 단위/푸시 스크립트 (안전망)
RE_INS = re.compile(r'[ \t]*<ins\b[^>]*class="adsbygoogle"[^>]*>\s*</ins>[ \t]*\n?', re.S)
RE_PUSH = re.compile(
    r'[ \t]*<script>\s*\(adsbygoogle\s*=\s*window\.adsbygoogle\s*\|\|\s*\[\]\)\.push\(\{\}\);?\s*</script>[ \t]*\n?',
    re.S)


def strip_ads(html):
    out = RE_AD_BLOCK.sub('', html)
    out = RE_INS.sub('', out)
    out = RE_PUSH.sub('', out)
    out = RE_LOADER.sub('', out)
    return out


def targets():
    for p in sorted(glob.glob(os.path.join(ROOT, 'festival', 'detail', '*.html'))):
        yield p
    for p in sorted(glob.glob(os.path.join(ROOT, 'blog', 'posts', '*.html'))):
        with open(p, 'r', encoding='utf-8') as fp:
            head = fp.read()
        # 공지사항/업데이트 글만(생성기가 noindex 메타를 넣은 글). 일반 글은 건드리지 않음.
        if re.search(r'<meta\s+name="robots"\s+content="[^"]*noindex', head, re.I):
            yield p


def main():
    dry = '--dry-run' in sys.argv
    scanned = changed = leftover = 0
    for path in targets():
        scanned += 1
        with open(path, 'r', encoding='utf-8') as fp:
            before = fp.read()
        if 'adsbygoogle' not in before:
            continue
        after = strip_ads(before)
        if 'adsbygoogle' in after:
            leftover += 1
            print(f'⚠️ 광고 코드가 남음(수동 확인 필요): {os.path.relpath(path, ROOT)}', file=sys.stderr)
        if after != before:
            changed += 1
            if not dry:
                with open(path, 'w', encoding='utf-8') as fp:
                    fp.write(after)
    print(f'검사 {scanned}개 / 광고 제거 {changed}개 / 광고 남은 파일 {leftover}개' + (' (dry-run)' if dry else ''))
    return 1 if leftover else 0


if __name__ == '__main__':
    sys.exit(main())
