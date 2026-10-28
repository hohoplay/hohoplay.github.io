#!/usr/bin/env python3
"""scripts/update_home_latest.py

홈(index.html)의 "📰 최신 소식" 블록을 정적 HTML로 채워 넣는다.

왜 필요한가
  호호픽(hoho-pick.html)은 자바스크립트가 Worker API에서 글을 받아 그려서, 스크립트를 실행하지
  않는 봇에게는 "불러오는 중..."만 보인다. 이 블록은 HTML에 글 제목·요약이 직접 들어 있게 한다.

동작
  1. blog/magazine/*.html 과 blog/posts/*.html (generate_community_posts.py 가 만든 정적 글)에서
     제목·날짜·요약(meta description)을 읽는다. index.html 같은 목록 페이지는 제외한다.
  2. 날짜(같으면 글 번호) 내림차순으로 5개를 고른다.
  3. index.html 의 <!-- HOME_LATEST_START --> ~ <!-- HOME_LATEST_END --> 사이만 다시 쓴다.
     그 밖의 부분은 한 글자도 바꾸지 않는다. 내용이 같으면 파일을 쓰지 않는다(멱등).

실행 위치
  .github/workflows/sync_community_posts.yml 에서 generate_community_posts.py 바로 다음 단계로 실행한다.
  (같은 커밋으로 올라가므로 index.html 이 사람 손과 따로 커밋될 일이 없다.)

사용법(저장소 루트에서):  python3 scripts/update_home_latest.py [--dry-run] [--root 경로]
종료 코드: 0 = 정상(변경 없음 포함), 1 = 오류(표식 없음 등)
"""
import argparse
import glob
import html
import os
import re
import sys

LATEST_COUNT = 5
EXCERPT_MAX = 240  # 홈 카드에서 3~4줄로 보이는 길이(호호 매거진 카드와 비슷하게)
START = '<!-- HOME_LATEST_START -->'
END = '<!-- HOME_LATEST_END -->'
SOURCES = [
    ('blog/magazine', '호호 매거진', '/blog/magazine/'),
    ('blog/posts', '호호플레이 소식', '/blog/posts/'),
]
TITLE_SUFFIX_RE = re.compile(r'\s*-\s*HOHO PLAY 커뮤니티\s*$')
DATE_RE = re.compile(r'HOHO PLAY\s*·\s*(\d{4})\.(\d{2})\.(\d{2})')
TITLE_RE = re.compile(r'<title>(.*?)</title>', re.S)
DESC_RE = re.compile(r'<meta\s+name="description"\s+content="(.*?)"\s*/?>', re.S)


def clean(text):
    text = text or ''
    for _ in range(3):  # 생성기가 이미 이스케이프된 글자를 한 번 더 이스케이프한 경우(&amp;amp;)까지 풀기
        new = html.unescape(text)
        if new == text:
            break
        text = new
    return re.sub(r'\s+', ' ', text).strip()


CONTENT_RE = re.compile(r'<div class="magazine-content[^>]*>(.*?)</div>', re.S)
FIRST_P_RE = re.compile(r'<p[^>]*>(.*?)</p>', re.S)
TAG_RE = re.compile(r'<[^>]+>')
GREETING_RE = re.compile(r'^안녕하세요[^.!。]*[.!]\s*')


def body_excerpt(src):
    """본문(.magazine-content)에서 인사말을 뺀 첫 번째 '내용 있는' 문단. 없으면 빈 문자열."""
    m = CONTENT_RE.search(src)
    if not m:
        return ''
    for p in FIRST_P_RE.finditer(m.group(1)):
        text = GREETING_RE.sub('', clean(TAG_RE.sub(' ', p.group(1)))).strip()
        # 이모지·기호만 남은 줄은 건너뛴다(글자가 10자 이상인 문단만 사용).
        if len(re.findall(r'[0-9A-Za-z가-힣]', text)) >= 10:
            return text
    return ''


def parse_post(path, badge, url_dir):
    with open(path, 'r', encoding='utf-8') as fp:
        src = fp.read()
    m = TITLE_RE.search(src)
    d = DATE_RE.search(src)
    if not m or not d:
        return None
    title = TITLE_SUFFIX_RE.sub('', clean(m.group(1)))
    if not title:
        return None
    desc = body_excerpt(src)
    if not desc:
        dm = DESC_RE.search(src)
        if dm:
            desc = clean(dm.group(1))
            # 설명이 제목으로 시작하면 제목 부분을 걷어낸다.
            if desc.startswith(title):
                desc = desc[len(title):].strip()
            desc = re.sub(r'^[\s:：\-–—]+', '', desc)
    if len(desc) > EXCERPT_MAX:
        cut = desc[:EXCERPT_MAX]
        sp = cut.rfind(' ')
        if sp >= EXCERPT_MAX - 25:  # 단어 중간에서 끊기지 않게 마지막 공백에서 자른다
            cut = cut[:sp]
        desc = cut.rstrip(' ,.·') + '…'
    stem = os.path.splitext(os.path.basename(path))[0]
    sort_id = int(stem) if stem.isdigit() else 0
    return {
        'title': title,
        'desc': desc,
        'date': '%s.%s.%s' % d.groups(),
        'sort': (d.group(1) + d.group(2) + d.group(3), sort_id),
        'badge': badge,
        'url': '%s%s.html' % (url_dir, stem),
    }


def collect(root):
    posts = []
    for folder, badge, url_dir in SOURCES:
        for path in sorted(glob.glob(os.path.join(root, folder, '*.html'))):
            if os.path.basename(path) == 'index.html':
                continue
            p = parse_post(path, badge, url_dir)
            if p:
                posts.append(p)
    posts.sort(key=lambda p: p['sort'], reverse=True)
    return posts[:LATEST_COUNT]


def render(posts):
    e = html.escape
    lines = [START,
             '        <section class="home-latest" aria-label="최신 소식">',
             '            <div class="home-latest-head"><h2>📰 최신 소식</h2><a href="/blog/">전체 글 보기 →</a></div>',
             '            <ul class="home-latest-list">']
    for p in posts:
        desc = ('<span class="hl-desc">%s</span>' % e(p['desc'])) if p['desc'] else ''
        lines.append(
            '                <li><a href="%s"><span class="hl-badge">%s</span>'
            '<span class="hl-title">%s</span>%s<span class="hl-date">%s</span></a></li>'
            % (e(p['url'], quote=True), e(p['badge']), e(p['title']), desc, e(p['date'])))
    lines += ['            </ul>', '        </section>', '        ' + END]
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    index_path = os.path.join(args.root, 'index.html')
    with open(index_path, 'r', encoding='utf-8') as fp:
        page = fp.read()
    if page.count(START) != 1 or page.count(END) != 1 or page.index(START) > page.index(END):
        print('오류: index.html 에서 HOME_LATEST 표식(START/END)을 한 쌍으로 찾지 못했습니다.', file=sys.stderr)
        return 1

    posts = collect(args.root)
    if not posts:
        print('정적 글을 하나도 읽지 못해 홈 최신 소식을 그대로 둡니다.', file=sys.stderr)
        return 0

    # START~END 사이만 교체한다(START 앞의 들여쓰기는 그대로 유지).
    i = page.index(START)
    j = page.index(END) + len(END)
    new_page = page[:i] + render(posts) + page[j:]
    if new_page == page:
        print('변경 없음 (최신 %d개 동일)' % len(posts))
        return 0
    for p in posts:
        print('  - [%s] %s  %s' % (p['date'], p['title'], p['url']))
    if args.dry_run:
        print('[dry-run] 저장하지 않았습니다.')
        return 0
    with open(index_path, 'w', encoding='utf-8') as fp:
        fp.write(new_page)
    print('index.html 최신 소식 %d개로 갱신 완료' % len(posts))
    return 0


if __name__ == '__main__':
    sys.exit(main())
