#!/usr/bin/env python3
"""scripts/improve_kids_course_pages.py

[1회성 정리 스크립트] blog/kids-course/*.html (아이랑 나들이 추천 코스 글 33개) 품질 개선.

배경: 코스 글 33개가 모두 같은 소개 2문단 + 같은 마무리 3문단(약 900~1,000자)을 갖고 있어,
장소가 3~4곳뿐인 짧은 글은 본문의 절반 가까이가 공통 문구였다. 또 짧은 자동 생성 페이지에서는
애드센스 코드를 이미 걷어냈는데 코스 글만 로더가 남아 있었다.

하는 일 (글마다):
  1) 애드센스 로더(<script ...adsbygoogle.js> + 앞의 안내 주석) 제거
  2) 공통 소개 2문단 → 지역명·장소 수가 들어간 짧은 소개 1문단
  3) 소개 바로 아래에 "○○ 코스 한눈에 보기" 요약 문단 추가
     (data/kids_places.json 의 값으로 계산: 무료/유료 곳 수, 실내/실외 곳 수,
      비 오는 날 후보·야외 후보 장소 이름, 월요일 휴관 곳 수, 운영시간 미확인 곳 수)
  4) 공통 마무리 3문단 → 짧은 2문단
  5) 운영시간 줄(🕒)이 빠진 장소 보강: kids_places.json 에 실제 운영시간이 있으면 그 값을 채우고,
     값이 없거나 "확인 필요" 같은 자리표시 문구뿐이면 "🕒 운영시간 정보 없음 (방문 전 확인)"으로 통일

바뀌지 않는 것: 장소 목록·주소·요금·전화번호·장소 설명·링크·메타태그·공유/댓글 영역.
멱등: 이미 처리한 글(<!--kc:v1--> 표식이 있는 글)은 다시 실행해도 변하지 않는다.
안전장치: 예상한 문장 패턴이 하나라도 없으면 그 글은 건드리지 않고 경고만 남긴다.

사용법(저장소 루트에서):  python3 scripts/improve_kids_course_pages.py [--dry-run]
"""
import glob
import html as html_lib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if '--root' in sys.argv:  # 테스트용: 다른 폴더를 저장소 루트처럼 사용
    ROOT = os.path.abspath(sys.argv[sys.argv.index('--root') + 1])

MARK = '<!--kc:v1-->'

# ── 원본(기존 글 33개에 공통) 문구 ───────────────────────────────────────────
OLD_INTRO_1 = (
    '<p>호호플레이가 전국 200여 곳의 ‘아이랑 갈만한 곳’ 데이터 가운데, 서로 가까이 모여 있어 하루 코스로 묶기 좋은 지역만 '
    '추려 ‘아이랑 나들이 코스’로 소개합니다. 기간이 정해진 축제는 빼고 언제 가도 운영 중인 상시 장소만 담았기 때문에, '
    '계절이나 날짜에 상관없이 언제든 참고할 수 있습니다.</p>'
)
OLD_INTRO_2 = (
    '<p>아래 목록은 실제 위치 정보를 기준으로 가까운 순서에 가깝게 정리했습니다. 각 장소 이름을 누르면 운영시간·요금·전화번호 등 '
    '자세한 정보를 볼 수 있고, 지도에서 한눈에 보고 싶다면 아래 ‘아이랑 나들이 지도에서 보기’ 버튼을 이용해보세요.</p>'
)
OLD_OUTRO_RE = re.compile(
    r'(<h2 style="[^"]*">이 코스, 이렇게 다녀오세요</h2>)'
    r'(<p>운영시간·요금·휴무일 정보는.*?</p>)'
    r'(<p>하루에 모든 곳을 다 돌기보다는.*?</p>)'
    r'(<p>이 코스에 담긴 장소들은.*?</p>)',
    re.S)

H2_STYLE = 'font-size:20px;font-weight:900;color:#1e293b;margin:24px 0 4px'

NEW_OUTRO_1 = ('<p>운영시간·요금·휴무일은 계절이나 요일에 따라 바뀔 수 있고, 소규모 체험 공간은 예고 없이 쉬는 날도 있습니다. '
               '방문 전에 전화나 홈페이지로 한 번 확인해 보세요.</p>')
NEW_OUTRO_2 = ("<p>하루에 모두 돌기보다 아이 컨디션에 맞춰 2~3곳만 골라 여유 있게 다니는 것을 권합니다. "
               "위치가 궁금하면 아래 '아이랑 나들이 지도'에서 전체 위치를 먼저 확인해 보세요.</p>")

# 장소 제목 + 메타줄(📍...)을 한 덩어리로 잡는다.
RE_PLACE_META = re.compile(
    r'(<h2 style="font-size:19px[^"]*">\d+\.\s*<a href="/festival/detail/([^"]+?)\.html"[^>]*>[^<]+</a></h2>\s*)'
    r'(<p style="font-size:13px;color:#94a3b8;margin:0 0 8px">)(📍.*?)(</p>)', re.S)
NO_HOURS = ' &nbsp;·&nbsp; 🕒 운영시간 정보 없음 (방문 전 확인)'


def real_hours(p):
    """kids_places.json 의 hours 가 실제 운영시간이면 문자열, 비었거나 '확인 필요' 류 자리표시면 None."""
    h = (p.get('hours') or '').strip()
    if not h or '확인 필요' in h or '확인필요' in h:
        return None
    return h


# 로더 + 앞 안내 주석(들여쓰기·줄바꿈 포함)
RE_ADS_COMMENT = re.compile(r'[ \t]*<!--[^>]*?AdSense[^>]*?-->[ \t]*\n', re.S)
RE_ADS_LOADER = re.compile(
    r'[ \t]*<script\b[^>]*pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js[^>]*>\s*</script>[ \t]*\n?', re.I)

# 장소 블록: <h2 ...>N. <a href="/festival/detail/kids-0107.html" ...>이름</a></h2>
RE_PLACE = re.compile(r'<h2 style="font-size:19px[^"]*">\d+\.\s*<a href="/festival/detail/([^"]+?)\.html"[^>]*>([^<]+)</a></h2>')


def load_places():
    with open(os.path.join(ROOT, 'data', 'kids_places.json'), 'r', encoding='utf-8') as fp:
        return {p['contentid']: p for p in json.load(fp)}


def region_name(page):
    m = re.search(r'<h1[^>]*>(.*?)</h1>', page, re.S)
    if not m:
        return None
    t = html_lib.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
    suffix = ' 아이랑 나들이 추천 코스'
    return t[:-len(suffix)] if t.endswith(suffix) else None


def pick_names(names, k=2):
    return ', '.join(names[:k])


def build_summary(region, entries):
    """entries: [(contentid, name, place_dict)] — 페이지에 실린 순서."""
    n = len(entries)
    free = sum(1 for _, _, p in entries if p.get('costTag') == '완전무료')
    unknown = sum(1 for _, _, p in entries if p.get('costTag') == '확인 필요')
    paid = n - free - unknown
    types = {'실내': [], '실내외': [], '실외': []}
    for _, name, p in entries:
        types.setdefault(p.get('placeType', ''), []).append(name)
    mon = sum(1 for _, _, p in entries
              if real_hours(p) and re.search(r'월요일', real_hours(p)) and re.search(r'휴관|휴무|쉬', real_hours(p)))
    nohours = sum(1 for _, _, p in entries if real_hours(p) is None)

    parts = []
    cost = f'요금은 무료 {free}곳, 유료(일부 무료 조건 포함) {paid}곳'
    if unknown:
        cost += f', 확인이 필요한 곳 {unknown}곳'
    parts.append(f'{region} 코스에는 장소 {n}곳이 담겨 있고, {cost}입니다.')

    kinds = [f'{k} {len(v)}곳' for k, v in (('실내', types['실내']), ('실내외', types['실내외']), ('실외', types['실외'])) if v]
    if kinds:
        parts.append('장소 유형은 ' + ' · '.join(kinds) + '입니다.')

    indoor = types['실내'] + types['실내외']
    if indoor:
        parts.append(f'비 오는 날에는 {pick_names(indoor)} 같은 실내 장소부터 고르면 편합니다.')
    else:
        parts.append('실내 장소가 없어 비 오는 날보다는 날씨 좋은 날에 가기 좋은 코스입니다.')
    if types['실외']:
        parts.append(f'날씨가 좋은 날에는 {pick_names(types["실외"])} 같은 야외 장소를 먼저 들러 보세요.')

    notes = []
    if mon:
        notes.append(f'월요일에 쉬는 곳이 {mon}곳이니 월요일 방문이라면 미리 확인하세요')
    if nohours:
        notes.append(f'운영시간이 확인되지 않은 곳이 {nohours}곳 있어 아래에 별도로 표시했습니다')
    if notes:
        parts.append('주의할 점: ' + ', '.join(notes) + '.')
    return '<p>' + ' '.join(parts) + '</p>'


def transform(page, places):
    """(새 HTML, 메시지). 처리 불가면 (None, 사유)."""
    if MARK in page:
        return page, 'skip(이미 처리됨)'
    if OLD_INTRO_1 not in page or OLD_INTRO_2 not in page:
        return None, '소개 문단 패턴 불일치'
    if not OLD_OUTRO_RE.search(page):
        return None, '마무리 문단 패턴 불일치'
    region = region_name(page)
    if not region:
        return None, '제목에서 지역명을 찾지 못함'

    entries = []
    for cid, name in RE_PLACE.findall(page):
        p = places.get(cid)
        if p is None:
            return None, f'장소 데이터 없음: {cid}'
        entries.append((cid, html_lib.unescape(name), p))
    if not entries:
        return None, '장소 블록을 찾지 못함'

    n = len(entries)
    intro = (f'<p>{region}에서 아이와 함께 가볼 만한 상시 운영 장소 {n}곳을 모았습니다. 축제처럼 기간이 정해진 곳은 빼서 '
             f'언제든 참고할 수 있고, 장소 이름을 누르면 운영시간·요금·전화번호 등 자세한 정보를 볼 수 있습니다.</p>')
    summary = f'<h2 style="{H2_STYLE}">{region} 코스 한눈에 보기</h2>' + build_summary(region, entries)

    out = page.replace(OLD_INTRO_1 + OLD_INTRO_2, MARK + intro + summary + '<!--/kc:v1-->', 1)
    if out == page:
        # 두 문단이 붙어 있지 않은 경우(줄바꿈 등)
        out = page.replace(OLD_INTRO_1, MARK + intro + summary + '<!--/kc:v1-->', 1).replace(OLD_INTRO_2, '', 1)
    out = OLD_OUTRO_RE.sub(lambda m: m.group(1) + NEW_OUTRO_1 + NEW_OUTRO_2, out, count=1)

    # 운영시간 줄이 빠진 장소 보강(실제 값이 있으면 채우고, 없으면 '정보 없음')
    def fix_meta(m):
        body = m.group(4)
        if '🕒' in body:
            return m.group(0)
        p = places.get(m.group(2)) or {}
        h = real_hours(p)
        add = (' &nbsp;·&nbsp; 🕒 ' + html_lib.escape(h, quote=False)) if h else NO_HOURS
        return m.group(1) + m.group(3) + body + add + m.group(5)
    out = RE_PLACE_META.sub(fix_meta, out)

    # 광고 로더 제거
    out = RE_ADS_COMMENT.sub('', out, count=1)
    out = RE_ADS_LOADER.sub('', out)
    if 'adsbygoogle' in out:
        return None, '광고 코드가 남음'
    return out, 'ok'


def main():
    dry = '--dry-run' in sys.argv
    places = load_places()
    files = sorted(p for p in glob.glob(os.path.join(ROOT, 'blog', 'kids-course', '*.html'))
                   if not p.endswith('index.html'))
    changed = skipped = failed = 0
    for path in files:
        rel = os.path.relpath(path, ROOT)
        with open(path, 'r', encoding='utf-8') as fp:
            before = fp.read()
        after, msg = transform(before, places)
        if after is None:
            failed += 1
            print(f'⚠️ {rel}: {msg} — 건드리지 않음', file=sys.stderr)
            continue
        if msg.startswith('skip'):
            skipped += 1
            continue
        changed += 1
        if not dry:
            with open(path, 'w', encoding='utf-8') as fp:
                fp.write(after)
    print(f'코스 글 {len(files)}개 / 수정 {changed}개 / 이미 처리됨 {skipped}개 / 실패 {failed}개' + (' (dry-run)' if dry else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
