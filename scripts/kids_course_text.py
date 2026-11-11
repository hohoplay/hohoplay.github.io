#!/usr/bin/env python3
"""scripts/kids_course_text.py

아이랑 나들이 코스 글(blog/kids-course/*.html)의 "소개·한눈에 보기 / 추천 동선 / 마무리" 문구를 만든다.

왜 새로 만들었나
  예전 문구는 글마다 같은 안내 문장(운영시간은 바뀔 수 있다, 2~3곳만 골라라, 거리는 어림값이다 …)이 그대로 들어가
  지역만 바꾼 자동 생성 글처럼 보였다. 이 모듈은 문장 틀을 쓰지 않고, data/kids_places.json 에서 계산한 값
  (장소 이름·요금·아이 요금·운영시간·휴관 요일·이용 연령 제한·장소 사이 거리)만으로 문장을 만든다.
  그래서 지역이 다르면 문장도 다르다. 직접 다녀온 후기처럼 데이터에 없는 사실은 만들지 않는다.

쓰는 곳: scripts/refresh_kids_course_text.py (기존 글 일괄 갱신), scripts/build_kids_course_pages.py (대전 글 생성)
"""
import html as html_lib
import re

import add_kids_course_route as rte

H2_BIG = 'font-size:20px;font-weight:900;color:#1e293b;margin:24px 0 4px'
H2_OUT = 'font-size:20px;font-weight:900;color:#1e293b;margin:32px 0 8px'
UL = 'margin:0 0 12px;padding-left:20px;list-style:disc'
LI = 'margin:0 0 6px'

esc = rte.esc
names_join = rte.names_join

KO_START = '<!--ko:v1-->'
KO_END = '<!--/ko:v1-->'

# ── 조사 ────────────────────────────────────────────────────────────────────
_DIGIT_FINAL = set('013678')      # 영·일·삼·육·칠·팔 — 받침 있음
_LATIN_FINAL = set('lmnrLMNR')    # 엘·엠·엔·알 — 받침 있음


def _has_final(text):
    t = re.sub(r'<[^>]+>', '', html_lib.unescape(text)).strip()
    while t and t[-1] in ')]}」』"\'':
        t = t[:-1]
        # 괄호가 닫힌 이름이면 괄호 안의 마지막 글자를 기준으로 본다
    if not t:
        return False
    c = t[-1]
    if '가' <= c <= '힣':
        return (ord(c) - 0xAC00) % 28 != 0
    if c.isdigit():
        return c in _DIGIT_FINAL
    return c in _LATIN_FINAL


def _rieul(text):
    t = re.sub(r'<[^>]+>', '', html_lib.unescape(text)).strip().rstrip(')]}')
    return bool(t) and '가' <= t[-1] <= '힣' and (ord(t[-1]) - 0xAC00) % 28 == 8


def j(text, kind):
    """text 뒤에 붙일 조사. kind: eul(을/를) eun(은/는) i(이/가) gwa(과/와) euro(으로/로)"""
    f = _has_final(text)
    if kind == 'eul':
        return '을' if f else '를'
    if kind == 'eun':
        return '은' if f else '는'
    if kind == 'i':
        return '이' if f else '가'
    if kind == 'gwa':
        return '과' if f else '와'
    if kind == 'euro':
        return '로' if (not f or _rieul(text)) else '으로'
    raise ValueError(kind)


def dist_phrase(d):
    k = rte.fmt_km(d)
    return '서로 바로 옆' if k == '바로 옆' else '직선 ' + k


# ── 데이터 읽기 ─────────────────────────────────────────────────────────────
_CHILD = [
    re.compile(r'어린이(?:\s*\([^)]{0,14}\))?(?:\s*[·/]\s*청소년)?\s*(?:요금|입장료)?\s*[:：]?\s*(무료|[\d,]{3,}\s*원)'),
    re.compile(r'소인(?:\s*\([^)]{0,16}\))?\s*[:：]?\s*(무료|[\d,]{3,}\s*원)'),
    re.compile(r'초등학생(?:\s*\([^)]{0,14}\))?\s*[:：]?\s*(무료|[\d,]{3,}\s*원)'),
]


def child_fee(p):
    """요금 문구에서 아이(어린이·소인·초등학생) 요금이 분명히 읽히면 '어린이 1,000원' 꼴, 아니면 None."""
    f = (p.get('fee') or '')
    for rx, label in zip(_CHILD, ('어린이', '소인', '초등학생')):
        m = rx.search(f)
        if m:
            return '%s %s' % (label, re.sub(r'\s+', '', m.group(1)))
    return None


_RANGE = re.compile(r'(\d{1,2}):(\d{2})\s*~\s*(\d{1,2}):(\d{2})')


def window(p):
    """운영시간이 '한 가지 시간대'로 읽히면 (여는 분, 닫는 분), 아니면 None (계절·평일/주말 구분이 있으면 쓰지 않는다)."""
    h = (p.get('hours') or '')
    if not h or '확인 필요' in h or '확인되지' in h:
        return None
    r = _RANGE.findall(h)
    if len(r) != 1:
        return None
    if re.search(r'하절기|동절기|평일|주말|토요일|일요일.*:|공연|시즌|성수기|비수기', h):
        return None
    a, b, c, d = map(int, r[0])
    o, cl = a * 60 + b, c * 60 + d
    if cl <= o:
        return None
    return o, cl


def hm(mins):
    return '%02d:%02d' % (mins // 60, mins % 60)


def profile(entries):
    n = len(entries)
    names = [e[1] for e in entries]
    pl = [e[2] for e in entries]
    d = dict(n=n, names=names, pl=pl)
    d['free'] = [i for i, p in enumerate(pl) if p.get('costTag') == '완전무료']
    d['unk_cost'] = [i for i, p in enumerate(pl) if p.get('costTag') == '확인 필요']
    d['paid'] = [i for i in range(n) if i not in d['free'] and i not in d['unk_cost']]
    t = [p.get('placeType', '') for p in pl]
    d['in'] = [i for i, x in enumerate(t) if x == '실내']
    d['out'] = [i for i, x in enumerate(t) if x == '실외']
    d['mixed'] = [i for i, x in enumerate(t) if x == '실내외']
    d['nohours'] = [i for i, p in enumerate(pl) if not rte.closed_days(p.get('hours'))[1] and
                    (not (p.get('hours') or '').strip() or '확인 필요' in (p.get('hours') or '') or '확인되지' in (p.get('hours') or ''))]
    d['closed'] = [rte.closed_days(p.get('hours')) for p in pl]
    d['win'] = [window(p) for p in pl]
    return d


def li(text):
    return '<li style="%s">%s</li>' % (LI, text)


def nlist(d, idx, k):
    return names_join([d['names'][i] for i in idx], k)


# ── 1) 소개 + 한눈에 보기 ───────────────────────────────────────────────────
def build_kc(region, entries):
    d = profile(entries)
    n = d['n']
    nf, np_, nu = len(d['free']), len(d['paid']), len(d['unk_cost'])
    indoor = d['in'] + d['mixed']
    if nf >= max(3, int(n * 0.6 + 0.999)):
        fn = nlist(d, d['free'], 2)
        lead = '%d곳이 입장 무료라 %s%s 먼저 들르면 입장료 부담이 거의 없어요.' % (nf, esc(fn), j(fn, 'eul'))
    elif len(d['in']) >= max(3, int(n * 0.8 + 0.999)):
        lead = '실내 장소가 %d곳(%s)이라 비가 오는 주말에도 일정을 잡기 편한 지역이에요.' % (len(d['in']), esc(nlist(d, d['in'], 2)))
    elif len(d['out']) >= max(2, int(n * 0.5 + 0.999)):
        lead = '야외 장소가 %d곳(%s)으로 많아 날씨 좋은 날에 맞는 코스예요.' % (len(d['out']), esc(nlist(d, d['out'], 2)))
    elif nf and np_:
        lead = '무료 %d곳과 유료 %d곳이 섞여 있어 예산에 맞춰 고르기 좋아요.' % (nf, np_)
    else:
        lead = '요금·실내외·운영시간은 아래에 장소별로 정리했어요.'
    intro = '<p>%s 코스는 모두 %d곳입니다. %s</p>' % (esc(region), n, lead)

    items = []
    fee = '무료 %d곳' % nf
    if nf:
        fee += '(%s)' % esc(nlist(d, d['free'], 4))
    fee += ' · 유료 %d곳' % np_
    if nu:
        fee += ' · 요금 확인 필요 %d곳' % nu
    items.append(li('<b>요금</b> — ' + fee))

    cf = [(i, child_fee(p)) for i, p in enumerate(d['pl']) if d['pl'][i].get('costTag') != '완전무료']
    cf = [(i, c) for i, c in cf if c]
    if cf:
        shown = cf[:4]
        items.append(li('<b>아이 요금이 확인되는 곳</b> — ' + ' · '.join('%s %s' % (esc(d['names'][i]), esc(c)) for i, c in shown)
                        + (' 등' if len(cf) > len(shown) else '')))

    wx = []
    if d['in']:
        wx.append('실내 %d곳(%s)' % (len(d['in']), esc(nlist(d, d['in'], 3))))
    if d['mixed']:
        wx.append('실내외 %d곳(%s)' % (len(d['mixed']), esc(nlist(d, d['mixed'], 2))))
    if d['out']:
        wx.append('실외 %d곳(%s)' % (len(d['out']), esc(nlist(d, d['out'], 3))))
    if wx:
        items.append(li('<b>비 오는 날 · 맑은 날</b> — ' + ' / '.join(wx)))

    w = [(i, x) for i, x in enumerate(d['win']) if x]
    if len(w) >= 2:
        early = min(w, key=lambda t: (t[1][1], t[0]))
        late = max(w, key=lambda t: (t[1][1], -t[0]))
        if early[1][1] != late[1][1]:
            rest = n - len(w)
            if rest == 0:
                items.append(li('<b>문 닫는 시간</b> — 가장 일찍 닫는 곳은 %s(%s), 가장 늦게까지 여는 곳은 %s(%s)입니다.'
                                % (esc(d['names'][early[0]]), hm(early[1][1]), esc(d['names'][late[0]]), hm(late[1][1]))))
            else:
                # 계절·요일별로 시간이 나뉘거나 확인이 안 된 곳은 비교에서 빠지므로, 비교 범위를 밝힌다(다른 곳이 더 늦게까지 열 수 있음).
                items.append(li('<b>문 닫는 시간</b> — 운영시간이 하나로 정해진 %d곳만 비교하면 가장 일찍 닫는 곳은 %s(%s), 가장 늦게 닫는 곳은 %s(%s)예요. '
                                '나머지 %d곳은 시간이 요일·계절별로 나뉘거나 확인되지 않아 장소별 안내를 봐 주세요.'
                                % (len(w), esc(d['names'][early[0]]), hm(early[1][1]), esc(d['names'][late[0]]), hm(late[1][1]), rest)))

    by_day = {}
    for i, (c, ok) in enumerate(d['closed']):
        for day in c:
            by_day.setdefault(day, []).append(d['names'][i])
    if by_day:
        items.append(li('<b>쉬는 요일</b> — ' + ' / '.join('%s요일: %s' % (day, esc(names_join(by_day[day], 4)))
                                                         for day in rte.DAYS if day in by_day)))

    warn = [(i, (p.get('ageWarning') or '').strip()) for i, p in enumerate(d['pl']) if (p.get('ageWarning') or '').strip()]
    for i, wtxt in warn[:3]:
        items.append(li('<b>이용 연령·제한</b> — %s: %s' % (esc(d['names'][i]), esc(wtxt))))

    if d['nohours']:
        items.append(li('<b>운영시간 미확인</b> — ' + esc(nlist(d, d['nohours'], 5))))

    ul = '<ul style="%s">%s</ul>' % (UL, ''.join(items))
    return intro + '<h2 style="%s">%s 코스 한눈에 보기</h2>' % (H2_BIG, esc(region)) + ul


# ── 2) 추천 동선 ────────────────────────────────────────────────────────────
def build_kr(region, entries):
    d = profile(entries)
    n, names, pl = d['n'], d['names'], d['pl']
    dist = [[rte.hav(pl[i], pl[j]) for j in range(n)] for i in range(n)]
    parts = []

    if n <= rte.PATH_MAX_N:
        order, total = rte.best_order(list(range(n)), dist)
        circ = '①②③④⑤⑥⑦⑧'
        chain = ' → '.join('%s%s' % (circ[k], esc(names[i])) for k, i in enumerate(order))
        legs = []
        for k in range(n - 1):
            a, b = order[k], order[k + 1]
            mv = rte.fmt_move(dist[a][b])
            legs.append('%s→%s %s%s' % (esc(names[a]), esc(names[b]), rte.fmt_km(dist[a][b]), (' ' + mv) if mv else ''))
        parts.append('<p>%d곳을 가장 짧게 잇는 순서는 %s입니다. 구간별로는 %s이고, 전부 이으면 직선 %s 정도예요(직선거리 기준).</p>'
                     % (n, chain, ', '.join(legs), rte.fmt_km(total)))
        legd = [(dist[order[k]][order[k + 1]], order[k], order[k + 1]) for k in range(n - 1)]
        walk = [t for t in legd if t[0] <= 1.2]
        drive = [t for t in legd if t[0] > 1.2]
        longest = max(legd)
        spread = max(dist[i][j] for i in range(n) for j in range(n))
        if not drive:
            parts.append('<p>%d개 구간이 모두 걸어서 갈 수 있는 거리이고, 가장 긴 %s→%s도 %s %s예요.</p>'
                         % (len(legd), esc(names[longest[1]]), esc(names[longest[2]]), rte.fmt_km(longest[0]), rte.fmt_move(longest[0])))
        elif not walk:
            parts.append('<p>%d개 구간 모두 차나 버스로 이동하는 거리예요. 가장 긴 구간은 %s에서 %s까지 %s %s입니다.</p>'
                         % (len(drive), esc(names[longest[1]]), esc(names[longest[2]]), rte.fmt_km(longest[0]), rte.fmt_move(longest[0])))
        else:
            parts.append('<p>%d개 구간은 걸어서, %d개 구간은 차나 버스로 이동하는 구성이에요. 차량 구간 중 가장 긴 곳은 %s에서 %s까지 %s %s입니다.</p>'
                         % (len(walk), len(drive), esc(names[longest[1]]), esc(names[longest[2]]), rte.fmt_km(longest[0]), rte.fmt_move(longest[0])))
        if spread > 6:
            far = max(((dist[i][j], i, j) for i in range(n) for j in range(n)))
            parts.append('<p>가장 먼 두 곳은 %s%s %s로 직선 %s 떨어져 있어, 이 둘은 하루에 함께 넣기보다 %s 쪽과 %s 쪽으로 나눠 가는 편이 편해요.</p>'
                         % (esc(names[far[1]]), j(names[far[1]], 'gwa'), esc(names[far[2]]), rte.fmt_km(far[0]), esc(names[far[1]]), esc(names[far[2]])))
    else:
        groups = rte.clusters(n, dist)
        multi = [g for g in groups if len(g) >= 2]
        singles = [g[0] for g in groups if len(g) == 1]
        big = multi[0] if multi else []
        parts.append('<p>%d곳이 있어 하루에 모두 돌기는 어려워요. 중심 장소에서 직선 %skm 안쪽끼리 묶으면 %d개 묶음이 나오고, 가장 큰 묶음은 %d곳입니다. '
                     '가장 큰 묶음 %d곳만 돌아도 하루 일정이 되니, 묶음 하나를 골라 채우면 이동이 크게 줄어요.</p>' % (n, ('%g' % rte.CLUSTER_KM), len(multi), len(big), len(big)))
        shown = multi[:4]
        for gi, g in enumerate(shown, 1):
            order, total = rte.best_order(g, dist)
            parts.append('<p>· 묶음 %d (%d곳, 이동 합계 %s): %s</p>' % (gi, len(g), rte.fmt_km(total), ' → '.join(esc(names[i]) for i in order)))
        tail = []
        if len(multi) > len(shown):
            tail.append('위 묶음 외에도 가까운 곳끼리 이어지는 묶음이 %d개 더 있어요' % (len(multi) - len(shown)))
        if singles:
            tail.append('%s처럼 다른 곳과 떨어진 %d곳은 따로 차로 가는 일정에 넣으세요' % (esc(names_join([names[i] for i in singles], 2)), len(singles)))
        if tail:
            parts.append('<p>' + '. '.join(tail) + '.</p>')

    # 날씨 갈래
    pin, pout, mixed = d['in'], d['out'], d['mixed']
    mixed_txt = (' %s%s 실내외를 함께 써서 그날 날씨에 맞춰 고르면 돼요.' % (esc(nlist(d, mixed, 3)), j(nlist(d, mixed, 3), 'eun'))) if mixed else ''
    if pin and pout:
        po, pi_ = nlist(d, pout, 2), nlist(d, pin, 2)
        s = '<p>맑은 날에는 야외 %s%s 오전에 먼저 들르고 오후에 실내 %s%s 옮기는 흐름이 편해요. ' % (
            esc(po), j(po, 'eul'), esc(pi_), j(pi_, 'euro'))
        if len(pin) == 1:
            s += '비가 오면 실내인 %s 한 곳 중심으로 짜면 됩니다.' % esc(names[pin[0]])
        elif len(pin) <= rte.PATH_MAX_N:
            _, tot_in = rte.best_order(pin, dist)
            s += '비가 오면 실내 %d곳만 이어도 직선 %s 정도예요.' % (len(pin), rte.fmt_km(tot_in))
        else:
            s += '비가 오면 실내 장소가 %d곳으로 많으니 위 묶음 중 실내 위주인 곳을 고르세요.' % len(pin)
        parts.append(s + mixed_txt + '</p>')
    elif pin and not pout:
        if mixed:
            parts.append('<p>야외 전용 장소가 없고 실내 %d곳(%s)이 중심이라 날씨 영향이 적어요.%s</p>' % (len(pin), esc(nlist(d, pin, 2)), mixed_txt))
        else:
            pn = nlist(d, pin, 3)
            parts.append('<p>%s%s 모두 실내라 비나 더위·미세먼지가 심한 날에도 위 순서 그대로 다닐 수 있어요.</p>' % (esc(pn), j(pn, 'i')))
    elif pout and not pin:
        parts.append('<p>%s 등 야외 장소가 중심이라 비나 미세먼지가 심한 날은 일정을 미루는 편이 좋아요.%s</p>' % (esc(nlist(d, pout, 3)).rstrip(' 등'), mixed_txt))
    elif mixed:
        mn = nlist(d, mixed, 3)
        parts.append('<p>%s%s 실내외를 함께 쓰는 곳이라 그날 날씨에 맞춰 코스를 조절하면 돼요.</p>' % (esc(mn), j(mn, 'eun')))

    # 휴관 요일
    known = [i for i, (c, ok) in enumerate(d['closed']) if ok]
    by_day = {}
    for i in known:
        for day in d['closed'][i][0]:
            by_day.setdefault(day, []).append(names[i])
    if known and by_day:
        free_days = [x for x in rte.DAYS if x not in by_day]
        first_closed = next(nm for day in rte.DAYS if day in by_day for nm in by_day[day][:1])
        txt = '쉬는 곳이 요일마다 달라, 방문할 요일을 먼저 정한 뒤 열려 있는 곳 위주로 순서를 바꾸세요.'
        if free_days:
            idx = [rte.DAYS.index(x) for x in free_days]
            span = ('%s~%s' % (free_days[0], free_days[-1])) if (len(idx) >= 3 and idx == list(range(idx[0], idx[0] + len(idx)))) else '·'.join(free_days)
            txt = '%s요일에 가면 %s%s 포함해 운영시간이 확인된 %d곳은 대체로 문을 열어요. 공휴일 휴관과 예약 여부는 방문 전에 따로 확인해 주세요.' % (span, esc(first_closed), j(first_closed, 'eul'), len(known))
        parts.append('<p>%s</p>' % txt)
    elif known and not by_day:
        parts.append('<p>운영시간이 확인된 %d곳 가운데 정해진 휴관 요일이 있는 곳은 없어요.</p>' % len(known))

    return '<h2 style="%s">%s 추천 동선과 방문 요령</h2>%s' % (rte.H2_STYLE, esc(region), ''.join(parts))


# ── 3) 마무리 ───────────────────────────────────────────────────────────────
def build_outro(region, entries):
    d = profile(entries)
    n, names, pl = d['n'], d['names'], d['pl']
    parts = []
    if n >= 2:
        dist = [[rte.hav(pl[i], pl[j]) for j in range(n)] for i in range(n)]
        pair = min(((dist[i][j], i, j) for i in range(n) for j in range(i + 1, n)))
        s = '가장 가까운 두 곳 %s · %s(%s)를 한 묶음으로 잡으면 이동이 가장 적어요.' % (
            esc(names[pair[1]]), esc(names[pair[2]]), dist_phrase(pair[0]))
        w = [(i, x) for i, x in enumerate(d['win']) if x]
        early = [t for t in w if t[1][1] <= 17 * 60 + 30]
        if early:
            e = min(early, key=lambda t: (t[1][1], t[0]))
            s += ' %s%s %s에 문을 닫으니 오전이나 이른 오후에 먼저 넣으세요.' % (esc(names[e[0]]), j(names[e[0]], 'eun'), hm(e[1][1]))
        parts.append('<p>' + s + '</p>')
    if d['nohours']:
        tel = []
        for i in d['nohours'][:4]:
            t = (pl[i].get('tel') or '').strip()
            tel.append('%s%s' % (esc(names[i]), (' (☎ %s)' % esc(t)) if t else ''))
        parts.append('<p>운영시간을 확인하지 못한 %d곳은 가기 전에 전화로 물어보세요: %s%s.</p>'
                     % (len(d['nohours']), ', '.join(tel), ' 등' if len(d['nohours']) > 4 else ''))
    return '<h2 style="%s">%s 하루 일정 잡기</h2>%s' % (H2_OUT, esc(region), ''.join(parts))


def build_meta_desc(region, entries):
    d = profile(entries)
    n = d['n']
    bits = []
    if d['free']:
        bits.append('무료 %d곳' % len(d['free']))
    indoor = len(d['in'])
    if indoor:
        bits.append('실내 %d곳' % indoor)
    tail = ' · '.join(bits)
    return '%s 아이랑 갈 만한 %d곳%s. 요금·운영시간·휴관 요일과 이동 순서를 장소별로 정리했어요.' % (
        region, n, (' (' + tail + ')') if tail else '')


ROBOTS_NOINDEX = '<meta name="robots" content="noindex,follow">'
_CANON_RE = re.compile(r'(\n([ \t]*)<link rel="canonical" href="[^"]*">)')


def ensure_noindex(page):
    """canonical 바로 아래에 noindex,follow 메타를 넣는다(이미 robots 메타가 있으면 그대로 둠)."""
    if 'name="robots"' in page:
        return page
    return _CANON_RE.sub(lambda m: m.group(1) + '\n' + m.group(2) + ROBOTS_NOINDEX, page, count=1)
