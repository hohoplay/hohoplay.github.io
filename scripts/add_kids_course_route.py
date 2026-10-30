#!/usr/bin/env python3
"""scripts/add_kids_course_route.py

blog/kids-course/*.html (아이랑 나들이 추천 코스 글)에 "추천 동선과 방문 요령" 구간을 넣는다.

왜 필요한가
  코스 글은 같은 틀(한눈에 보기 → 장소 목록 → 마무리 2문단)로 만들어져 있어, 지역만 바꾼 자동 생성 글처럼 보일 수 있다.
  장소 좌표·유형·운영시간 데이터(data/kids_places.json)로 "그 지역에서만 의미가 있는" 정보를 계산해 넣어 차별화한다.
  (직접 다녀온 후기·사진처럼 사실이 아닌 내용은 만들지 않는다. 계산할 수 있는 값만 쓴다.)

넣는 내용 (모두 kids_places.json 에서 계산)
  1) 가장 짧은 이동 순서와 장소 사이 거리·이동 시간 어림(장소가 많은 지역은 "가까이 모인 묶음"으로 정리)
  2) 이동 수단 안내(걸어서 / 짧은 차량 이동 / 자가용 권장)
  3) 맑은 날·비 오는 날 갈래(장소 유형 실내·실외 기준)
  4) 휴관 요일 정리와 모든 곳이 열려 있는 요일(운영시간 문구에서 명확히 읽히는 경우만)

동작
  - "이 코스, 이렇게 다녀오세요" 제목 바로 앞에 <!--kr:v1--> ~ <!--/kr:v1--> 표식 구간을 넣는다.
  - 이미 표식이 있으면 그 구간만 새 값으로 다시 쓴다(멱등: 데이터가 같으면 파일이 바뀌지 않는다).
  - NOINDEX_FILES 에 적힌 글(장소 3곳 이하이고 본문이 짧은 글)에는 <meta name="robots" content="noindex,follow">를 넣는다.
    (sitemap.xml 에서는 따로 빼 둔다. 글이 보강되면 이 목록에서 지우고 meta 를 제거하면 된다.)
  - 기대한 패턴이 하나라도 없으면 그 글은 건드리지 않고 경고만 남긴다.

사용법(저장소 루트에서):  python3 scripts/add_kids_course_route.py [--dry-run] [--root 경로]
종료 코드: 0 = 정상, 1 = 건드리지 못한 글이 있음
"""
import glob
import html as html_lib
import itertools
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if '--root' in sys.argv:
    ROOT = os.path.abspath(sys.argv[sys.argv.index('--root') + 1])

KR_START = '<!--kr:v1-->'
KR_END = '<!--/kr:v1-->'
H2_STYLE = 'font-size:20px;font-weight:900;color:#1e293b;margin:24px 0 4px'
ANCHOR_RE = re.compile(r'<h2 style="[^"]*">이 코스, 이렇게 다녀오세요</h2>')
RE_PLACE = re.compile(r'<h2 style="font-size:19px[^"]*">\d+\.\s*<a href="/festival/detail/([^"]+?)\.html"[^>]*>([^<]+)</a></h2>')
KR_BLOCK_RE = re.compile(re.escape(KR_START) + r'.*?' + re.escape(KR_END), re.S)
CANONICAL_RE = re.compile(r'(<link rel="canonical" href="[^"]*">)')
ROBOTS = '<meta name="robots" content="noindex,follow">'

# 장소 3곳 이하이고 본문이 2,000자 미만이던 글 (2026-10-28 기준).
NOINDEX_FILES = {'busan-buk.html', 'busan-suyeong.html', 'busan-yeongdo.html'}

DAYS = '월화수목금토일'
DAYS_G = '[월화수목금토일]'
CLUSTER_KM = 1.5        # 묶음의 중심 장소에서 직선으로 이 거리 안쪽에 있는 곳끼리 한 묶음
PATH_MAX_N = 8          # 이 개수 이하면 가장 짧은 순서를 전부 따져서 구한다
ROAD_FACTOR = 1.3       # 직선거리 → 도로 거리 어림 보정
CAR_KMH = 25.0          # 시내 평균 속도 어림
WALK_KMH = 4.0


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


# ── 거리·시간 ────────────────────────────────────────────────────────────────
def hav(a, b):
    r = 6371.0
    p1, p2 = math.radians(a['lat']), math.radians(b['lat'])
    dphi = p2 - p1
    dl = math.radians(b['lng'] - a['lng'])
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def fmt_km(d):
    if d < 0.1:
        return '바로 옆'
    m50 = int(round(d * 1000 / 50) * 50)
    if m50 < 1000:
        return '약 %dm' % m50
    return '약 %.1fkm' % d


def fmt_move(d):
    """직선거리 d(km) → '(도보 약 N분)' 또는 '(차로 약 N분)' 어림."""
    road = d * ROAD_FACTOR
    if d < 0.1:
        return ''
    if d <= 1.2:
        mins = max(5, int(round(road / WALK_KMH * 60 / 5)) * 5)
        return '(도보 약 %d분)' % mins
    mins = max(5, int(round(road / CAR_KMH * 60 / 5)) * 5)
    return '(차로 약 %d분)' % mins


def best_order(idx, dist):
    """idx 장소들을 모두 지나는 가장 짧은 열린 경로(순서 리스트, 총거리)."""
    n = len(idx)
    if n <= 1:
        return list(idx), 0.0
    if n <= PATH_MAX_N:
        best, bestd = None, None
        for perm in itertools.permutations(idx):
            if perm[0] > perm[-1]:   # 뒤집은 경로는 같은 길이 — 한쪽만 본다
                continue
            d = sum(dist[perm[i]][perm[i + 1]] for i in range(n - 1))
            if bestd is None or d < bestd - 1e-9:
                best, bestd = perm, d
        return list(best), bestd
    # 많은 경우: 가까운 곳으로 이어가기(시작은 다른 곳과 가장 먼 쪽)
    start = max(idx, key=lambda i: max(dist[i][j] for j in idx))
    order, left = [start], set(idx) - {start}
    while left:
        nxt = min(left, key=lambda j: dist[order[-1]][j])
        order.append(nxt)
        left.remove(nxt)
    return order, sum(dist[order[i]][order[i + 1]] for i in range(len(order) - 1))


def clusters(n, dist):
    """중심 장소에서 CLUSTER_KM 안쪽에 있는 곳끼리 묶는다(이어 붙이기식으로 길게 늘어지는 묶음을 막기 위해 중심 기준)."""
    left = set(range(n))
    out = []
    while left:
        seed = max(sorted(left), key=lambda i: sum(1 for j in left if dist[i][j] <= CLUSTER_KM))
        members = sorted(j for j in left if dist[seed][j] <= CLUSTER_KM)
        out.append(members)
        left -= set(members)
    return sorted(out, key=lambda g: (-len(g), g[0]))


# ── 휴관 요일(운영시간 문구에서 명확히 읽히는 것만) ──────────────────────────
# 규칙은 일부러 좁게 잡았다. 애매하면 "판단 불가"로 두고 글에는 쓰지 않는다.
_D = DAYS_G
_DL = _D + r'(?:\s*요일)?(?:\s*[·,/]\s*' + _D + r'(?:\s*요일)?)*'          # 월 / 월·금요일 / 월요일·일요일
# P1: "매주 월요일 ... 휴관" (사이 문구에 시각·운영·개방·~ 가 없을 때)
RE_P1 = re.compile(r'매주\s*(' + _DL + r')(?P<gap>[^/;\n운영개방~]{0,40}?)(?:휴관|휴무|휴일)')
# P2: "(토·일요일 휴무)", "월·화요일 정기휴무", "월·화요일·공휴일 휴관"
RE_P2 = re.compile(r'(?<![가-힣0-9~])(' + _DL + r')\s*(?:[·,]\s*(?:법정)?공휴일)?\s*(?:정기\s*)?(?:휴관|휴무)')
# P3: "월~목요일 휴무" 처럼 범위로 쉬는 경우
RE_P3 = re.compile(r'(?<![가-힣0-9])(' + _D + r')\s*~\s*(' + _D + r')\s*(?:요일)?\s*(?:정기\s*)?(?:휴관|휴무)')
# P4: 문구 전체가 "화~일 09:00~18:00" 한 줄뿐이면 범위 밖 요일은 쉬는 날로 본다
RE_P4 = re.compile(r'^\s*(' + _D + r')\s*~\s*(' + _D + r')\s*(?:요일)?\s*\d{1,2}:\d{2}\s*~\s*\d{1,2}:\d{2}\s*(?:\([^)]*\))?\s*$')


def closed_days(hours):
    """(휴관 요일 집합, 판단 가능 여부). 판단 불가면 (set(), False)."""
    h = (hours or '').strip()
    if not h or '확인되지 않' in h or '확인 필요' in h or '확인필요' in h:
        return set(), False
    closed = set()

    def days_of(s):
        return set(re.findall(_D, s.replace('요일', '')))   # '월요일'의 '일'을 요일 '일'로 읽지 않도록 '요일'을 먼저 지운다

    def partial(m):
        # 격주·몇째 주·계절 한정 휴관은 "매주 쉬는 요일"이 아니므로 쓰지 않는다
        return bool(re.search(r'째|마지막\s*주|격주|비수기|성수기|하절기|동절기', h[max(0, m.start() - 12):m.start()]))
    for m in RE_P1.finditer(h):
        if re.search(r'\d{1,2}:\d{2}', m.group('gap')) or partial(m):
            continue
        closed |= days_of(m.group(1))
    for m in RE_P2.finditer(h):
        if partial(m):
            continue
        closed |= days_of(m.group(1))
    for m in RE_P3.finditer(h):
        a, b = DAYS.index(m.group(1)), DAYS.index(m.group(2))
        if a <= b:
            closed |= set(DAYS[a:b + 1])
    m = RE_P4.match(h)
    if m:
        a, b = DAYS.index(m.group(1)), DAYS.index(m.group(2))
        if a <= b:
            closed |= set(DAYS) - set(DAYS[a:b + 1])
    if closed:
        return closed, True
    if re.search(r'연중무휴|매일|상시 개방|상시개방', h):
        return set(), True
    return set(), False


# ── 문장 만들기 ──────────────────────────────────────────────────────────────
def esc(s):
    return html_lib.escape(s, quote=False)


def names_join(names, k=2):
    return ', '.join(names[:k]) + (' 등' if len(names) > k else '')


def build_block(region, entries):
    """entries: [(contentid, name, place_dict)] — 페이지에 실린 순서."""
    n = len(entries)
    names = [e[1] for e in entries]
    pl = [e[2] for e in entries]
    dist = [[hav(pl[i], pl[j]) for j in range(n)] for i in range(n)]
    parts = []

    # 1) 동선
    if n <= PATH_MAX_N:
        order, total = best_order(list(range(n)), dist)
        circ = '①②③④⑤⑥⑦⑧'
        chain = ' → '.join('%s%s' % (circ[k], esc(names[i])) for k, i in enumerate(order))
        legs = []
        for k in range(n - 1):
            a, b = order[k], order[k + 1]
            legs.append('%s에서 %s까지 %s%s' % (esc(names[a]), esc(names[b]), fmt_km(dist[a][b]),
                                               (' ' + fmt_move(dist[a][b])) if fmt_move(dist[a][b]) else ''))
        parts.append('<p>%s에 담긴 %d곳을 가장 짧게 잇는 순서는 %s입니다. %s로 이동하며, 모두 더하면 직선으로 %s 정도입니다.</p>'
                     % (esc(region), n, chain, ', '.join(legs), fmt_km(total)))
        spread = max(dist[i][j] for i in range(n) for j in range(n))
        if total <= 1.5:
            parts.append('<p>장소끼리 가까워서 아이 걸음으로 천천히 걸어 이동해도 부담이 적은 코스입니다. 유모차를 쓴다면 길 상태만 미리 확인해 보세요.</p>')
        elif spread <= 6:
            parts.append('<p>장소 사이가 걸어 다니기에는 조금 멀어서, 자가용이나 택시·버스로 짧게 이동하는 일정이 편합니다. 주차 가능 여부는 방문 전에 각 장소에 확인하세요.</p>')
        else:
            parts.append('<p>가장 먼 두 곳이 직선으로 %s 떨어져 있어, 자가용 이동을 기본으로 하고 하루에 2~3곳만 고르는 편이 좋습니다.</p>' % fmt_km(spread))
    else:
        groups = clusters(n, dist)
        multi = [g for g in groups if len(g) >= 2]
        singles = [g[0] for g in groups if len(g) == 1]
        parts.append('<p>%s에는 %d곳이 있어 하루에 다 돌기는 어렵습니다. 중심이 되는 장소에서 직선 %skm 안쪽에 있는 곳끼리 묶어 보았습니다. 묶음 하나를 골라 하루를 채우면 이동이 크게 줄어듭니다.</p>'
                     % (esc(region), n, ('%g' % CLUSTER_KM)))
        shown = multi[:4]
        for gi, g in enumerate(shown, 1):
            order, total = best_order(g, dist)
            chain = ' → '.join(esc(names[i]) for i in order)
            parts.append('<p>%s묶음 %d (%d곳, 이동 합계 %s): %s</p>' % ('· ', gi, len(g), fmt_km(total), chain))
        rest = len(multi) - len(shown)
        tail = []
        if rest > 0:
            tail.append('위 묶음 외에도 가까운 곳끼리 이어지는 묶음이 %d개 더 있습니다' % rest)
        if singles:
            tail.append('%s처럼 다른 곳과 떨어진 장소 %d곳은 따로 차로 이동하는 일정에 넣는 편이 좋습니다' % (esc(names_join([names[i] for i in singles], 2)), len(singles)))
        if tail:
            parts.append('<p>' + '. '.join(tail) + '.</p>')

    # 2) 날씨 갈래 (실내외 겸용 장소는 "실내"로 세지 않는다)
    types = [p.get('placeType', '') for p in pl]
    pure_in = [i for i, t in enumerate(types) if t == '실내']
    pure_out = [i for i, t in enumerate(types) if t == '실외']
    mixed = [i for i, t in enumerate(types) if t == '실내외']
    mixed_txt = (' 실내외를 함께 쓰는 %d곳은 그날 날씨에 맞춰 고르면 됩니다.' % len(mixed)) if mixed else ''
    if pure_in and pure_out:
        s = ('<p>날씨가 좋은 날에는 야외 장소(%s)를 오전에 먼저 들르고, 오후에는 실내 장소(%s)로 옮기는 흐름이 편합니다. '
             % (esc(names_join([names[i] for i in pure_out], 2)), esc(names_join([names[i] for i in pure_in], 2))))
        if len(pure_in) == 1:
            s += '비가 오는 날에는 실내 장소인 %s 한 곳을 중심으로 일정을 짜면 됩니다.' % esc(names[pure_in[0]])
        elif len(pure_in) <= PATH_MAX_N:
            _, tot_in = best_order(pure_in, dist)
            s += '비가 오는 날에는 실내 장소 %d곳만 이으면 이동 거리가 직선으로 %s 정도입니다.' % (len(pure_in), fmt_km(tot_in))
        else:
            s += '비가 오는 날에는 실내 장소가 %d곳으로 많으니, 위 묶음 가운데 실내 위주인 곳을 골라 다니면 됩니다.' % len(pure_in)
        parts.append(s + mixed_txt + '</p>')
    elif pure_in and not pure_out:
        if mixed:
            parts.append('<p>야외 전용 장소가 없고 실내 장소가 %d곳이라 날씨 영향이 적은 편입니다.%s</p>' % (len(pure_in), mixed_txt))
        else:
            parts.append('<p>장소가 모두 실내라 비가 오거나 덥고 미세먼지가 심한 날에도 일정을 크게 바꿀 필요가 없습니다.</p>')
    elif pure_out and not pure_in:
        parts.append('<p>야외 장소 위주의 코스라 비가 오거나 미세먼지가 심한 날에는 일정을 미루거나, 지도에서 실내 장소를 따로 찾아보는 편이 좋습니다.%s</p>' % mixed_txt)

    # 3) 휴관 요일
    info = [closed_days(p.get('hours')) for p in pl]
    known = [i for i, (c, ok) in enumerate(info) if ok]
    if known:
        by_day = {}
        for i in known:
            for d in info[i][0]:
                by_day.setdefault(d, []).append(names[i])
        unknown = n - len(known)
        sentences = []
        if by_day:
            days_txt = ' / '.join('%s요일 %s' % (d, esc(names_join(by_day[d], 3))) for d in DAYS if d in by_day)
            sentences.append('운영시간 문구에서 확인되는 휴관 요일은 %s입니다.' % days_txt)
            free_days = [d for d in DAYS if d not in by_day]
            if free_days:
                sentences.append('이 정보만 보면 %s요일에는 확인된 곳이 모두 문을 엽니다.' % '·'.join(free_days))
            else:
                sentences.append('요일마다 쉬는 곳이 하나씩은 있어 방문할 요일에 맞춰 순서를 바꿔야 합니다.')
        else:
            sentences.append('운영시간 문구상 확인된 곳은 정기 휴관 요일이 따로 없습니다.')
        if unknown:
            sentences.append('운영시간이 확인되지 않은 %d곳은 방문 전에 전화나 홈페이지로 꼭 확인하세요.' % unknown)
        parts.append('<p>' + ' '.join(sentences) + '</p>')

    parts.append('<p style="font-size:13px;color:#94a3b8">거리와 이동 시간은 장소 좌표를 바탕으로 계산한 어림값이라 실제 도로·교통 상황에 따라 달라질 수 있습니다.</p>')
    return '<h2 style="%s">%s 추천 동선과 방문 요령</h2>%s' % (H2_STYLE, esc(region), ''.join(parts))


def transform(page, places, fname):
    region = region_name(page)
    if not region:
        return None, '제목에서 지역명을 찾지 못함'
    entries = []
    for cid, name in RE_PLACE.findall(page):
        p = places.get(cid)
        if p is None or p.get('lat') is None or p.get('lng') is None:
            return None, '장소 데이터/좌표 없음: %s' % cid
        entries.append((cid, html_lib.unescape(name), p))
    if len(entries) < 2:
        return None, '장소 블록이 2개 미만'
    block = KR_START + build_block(region, entries) + KR_END

    if KR_START in page and KR_END in page:
        out = KR_BLOCK_RE.sub(lambda m: block, page, count=1)
    else:
        m = ANCHOR_RE.search(page)
        if not m:
            return None, '마무리 제목("이 코스, 이렇게 다녀오세요")을 찾지 못함'
        out = page[:m.start()] + block + page[m.start():]

    if fname in NOINDEX_FILES and 'name="robots"' not in out:
        if not CANONICAL_RE.search(out):
            return None, 'canonical 링크를 찾지 못해 noindex 를 넣지 못함'
        out = CANONICAL_RE.sub(lambda m: m.group(1) + '\n    ' + ROBOTS, out, count=1)
    return out, 'ok'


def main():
    dry = '--dry-run' in sys.argv
    places = load_places()
    files = sorted(p for p in glob.glob(os.path.join(ROOT, 'blog', 'kids-course', '*.html'))
                   if not p.endswith('index.html'))
    changed = same = failed = 0
    for path in files:
        rel = os.path.relpath(path, ROOT)
        with open(path, 'r', encoding='utf-8') as fp:
            before = fp.read()
        after, msg = transform(before, places, os.path.basename(path))
        if after is None:
            failed += 1
            print('⚠️ %s: %s — 건드리지 않음' % (rel, msg), file=sys.stderr)
            continue
        if after == before:
            same += 1
            continue
        changed += 1
        if not dry:
            with open(path, 'w', encoding='utf-8') as fp:
                fp.write(after)
    print('코스 글 %d개 / 수정 %d개 / 변경 없음 %d개 / 실패 %d개%s' % (len(files), changed, same, failed, ' (dry-run)' if dry else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
