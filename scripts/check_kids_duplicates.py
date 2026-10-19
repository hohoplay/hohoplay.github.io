# -*- coding: utf-8 -*-
"""
data/kids_places.json 중복 장소 검사

왜 필요한가:
  2026-10-14에 부산 47곳·제주 6곳이 기존 항목과 똑같이 한 번 더 입력되어
  52곳이 중복된 적이 있다(이름이 살짝 다르게 들어간 경우 포함). 같은 장소가 두 번
  들어가면 지도에 같은 곳이 "외 1곳"으로 겹쳐 보이고 상세페이지도 둘로 나뉜다.
  이 스크립트는 kids_places.json이 바뀔 때마다 중복 의심 항목을 찾아 알려준다.

판정 기준 (둘 중 하나라도 걸리면 중복 의심):
  1) contentid가 같음
  2) 이름이 같음 — 띄어쓰기·기호, 맨 앞 지역명(부산/부산광역시 등), 맨 뒤 지점명
     (부산점/광안점 등)·'본관'을 떼고 비교
  3) 같은 시/군/구 안에서
     - 한 이름이 다른 이름을 통째로 포함 ("마리앤쥬" ⊂ "마리앤쥬 부산점"), 또는
     - 도로명+번지가 같고 이름도 꽤 비슷함 ("레이저아레나 광안점" ↔ "레이저태그스포츠 광안점")
  ※ 같은 건물에 있는 서로 다른 시설(예: 다이나믹메이즈/런닝맨)은 이름이 달라서 안 걸린다.
  ※ 진짜 서로 다른 곳인데 걸리면, 아래 KNOWN_DIFFERENT에 그 짝을 추가하거나, 둘 중
     한 항목에 "notDuplicateOf": ["kids-0000"]을 넣어두면 그 짝은 더 이상 경고하지 않는다.

결과: 의심 항목이 있으면 목록을 출력하고 종료 코드 1(Actions에 빨간 X 표시)로 끝난다.
     사이트 배포를 막지는 않는다 — 알림 용도.
실행: python scripts/check_kids_duplicates.py [파일경로]
"""
import json
import os
import re
import sys

DATA_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join('data', 'kids_places.json')

SIDO_ALIASES = [
    ('서울특별시', '서울'), ('부산광역시', '부산'), ('대구광역시', '대구'), ('인천광역시', '인천'),
    ('광주광역시', '광주'), ('대전광역시', '대전'), ('울산광역시', '울산'), ('세종특별자치시', '세종'),
    ('경기도', '경기'), ('강원특별자치도', '강원'), ('강원도', '강원'), ('충청북도', '충북'),
    ('충청남도', '충남'), ('전북특별자치도', '전북'), ('전라북도', '전북'), ('전라남도', '전남'),
    ('경상북도', '경북'), ('경상남도', '경남'), ('제주특별자치도', '제주'),
]
SIDO_SHORT = sorted({s for _, s in SIDO_ALIASES}, key=len, reverse=True)
SIDO_LONG = sorted({l for l, _ in SIDO_ALIASES}, key=len, reverse=True)


# 이름이 비슷하지만 실제로 다른 장소로 확인된 짝(데이터 파일을 건드리지 않고 여기서 제외).
KNOWN_DIFFERENT = {
    frozenset(['kids-0036', 'kids-0037']),  # 83타워(전망대) ↔ 이월드 83타워 아이스링크
}

# 이 단어만 남는 이름은 너무 흔해서(부산박물관 → "박물관") 비교 기준으로 쓰지 않는다.
GENERIC_WORDS = {
    '박물관', '미술관', '도서관', '과학관', '체험관', '전시관', '기념관', '문화관', '역사관',
    '공원', '수목원', '식물원', '아쿠아리움', '전망대', '아이스링크', '빙상장', '동물원',
    '어린이박물관', '시립미술관', '시립도서관', '문화회관', '예술회관', '테마파크',
}


def norm_title(title):
    t = re.sub(r'\([^)]*\)', ' ', title or '').split()
    # 맨 뒤 지점명('부산점', '광안점')이나 '본관'은 띄어쓰기로 떨어져 있을 때만 뗀다
    if len(t) > 1 and ((t[-1].endswith('점') and len(t[-1]) <= 5) or t[-1] == '본관'):
        t = t[:-1]
    t = re.sub(r'[\s·\-_,.\'"]', '', ''.join(t))
    for prefix in SIDO_LONG + SIDO_SHORT:
        rest = t[len(prefix):]
        if t.startswith(prefix) and len(rest) >= 3 and rest not in GENERIC_WORDS:
            t = rest
            break
    return t


def common_prefix_len(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


def district(addr):
    """'부산광역시 해운대구 ...' → ('부산', '해운대구'). 시/도가 빠진 주소('수원 영통구')도 처리."""
    toks = (addr or '').split()
    if not toks:
        return ('', '')
    sido = toks[0]
    for long_name, short in SIDO_ALIASES:
        if sido == long_name or sido == short:
            sido = short
            break
    return (sido, toks[1] if len(toks) > 1 else '')


def road_key(addr):
    a = re.sub(r'\([^)]*\)', ' ', addr or '')
    m = re.search(r'(\S+(?:로|길))\s*(\d+(?:-\d+)?)(?!\d)', a)
    return (m.group(1) + ' ' + m.group(2)) if m else ''


def main():
    with open(DATA_PATH, encoding='utf-8') as f:
        places = json.load(f)

    problems = []
    seen_ids = {}
    for p in places:
        cid = p.get('contentid')
        if cid in seen_ids:
            problems.append(('같은 번호', cid, p.get('title'), cid, seen_ids[cid]))
        else:
            seen_ids[cid] = p.get('title')

    info = []
    for p in places:
        info.append({
            'id': p.get('contentid'), 'title': p.get('title', ''),
            'n': norm_title(p.get('title', '')), 'd': district(p.get('addr', '')),
            'r': road_key(p.get('addr', '')),
            'ok': set(p.get('notDuplicateOf') or []),
        })

    for i in range(len(info)):
        a = info[i]
        for j in range(i + 1, len(info)):
            b = info[j]
            if (a['id'] == b['id'] or b['id'] in a['ok'] or a['id'] in b['ok']
                    or frozenset([a['id'], b['id']]) in KNOWN_DIFFERENT):
                continue
            reason = None
            same_sido = a['d'][0] == b['d'][0]
            same_district = same_sido and a['d'][1] and a['d'][1] == b['d'][1]
            if a['n'] and a['n'] == b['n'] and same_sido:
                reason = '같은 이름'
            elif same_district:
                short, long_ = sorted([a['n'], b['n']], key=len)
                if len(short) >= 3 and short not in GENERIC_WORDS and short in long_:
                    reason = '이름 포함'
                elif a['r'] and a['r'] == b['r'] and common_prefix_len(a['n'], b['n']) >= 3:
                    reason = '같은 주소+비슷한 이름'
            if reason:
                problems.append((reason, a['id'], a['title'], b['id'], b['title']))

    lines = ['## 아이랑 장소 중복 검사', '', '- 검사한 장소: %d곳' % len(places)]
    if problems:
        lines += ['- 중복 의심: **%d쌍**' % len(problems), '',
                  '| 이유 | 앞 항목 | 뒤 항목 |', '|---|---|---|']
        lines += ['| %s | %s %s | %s %s |' % pr for pr in problems]
        lines += ['', '진짜 다른 장소라면 한쪽 항목에 `"notDuplicateOf": ["상대 번호"]`를 넣으면 다음부터 경고하지 않아요.']
    else:
        lines += ['- 중복 의심: 없음 ✅']
    report = '\n'.join(lines)
    print(report)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(report + '\n')
    for pr in problems:
        print('::warning title=중복 의심 장소::%s — %s %s / %s %s' % pr)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
