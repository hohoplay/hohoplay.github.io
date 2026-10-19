# -*- coding: utf-8 -*-
"""
kids_places.json 좌표 보정 스크립트 (카카오 로컬 API)

왜 필요한가:
  kids_places.json의 lat/lng 상당수가 실제 장소 좌표가 아니라 구/군 중심 좌표라서,
  같은 구/군 장소 여러 곳이 지도에서 한 점(예: 강화군청)에 겹쳐 있다.
  이 스크립트는 각 장소의 주소(addr)·이름(title)으로 카카오 로컬 API를 조회해
  실제 위치 좌표로 바꾼다.

동작 순서 (장소 하나당):
  1) 캐시(data/geocode_cache.json)에 같은 주소·이름으로 찾아둔 결과가 있으면 그대로 쓴다
     (API를 다시 부르지 않음 — 다시 실행해도 결과가 흔들리지 않고 호출량도 아낌).
  2) 주소가 구체적이면(번지·도로명 등 숫자 포함) 주소 검색 API로 찾는다.
  3) 못 찾으면 장소 이름으로 키워드 검색 API를 부르고, 결과 중 기존 좌표에서
     가장 가까운 곳을 고른다(같은 이름의 다른 지점이 섞여도 걸러지게).
  4) 어떤 결과든 기존 좌표(구/군 중심)에서 MAX_MOVE_KM 넘게 떨어지면 엉뚱한 곳으로
     보고 버린다 — 이 경우 기존 좌표를 그대로 둔다.
  - "coordLock": true 가 붙은 장소는 건드리지 않는다(손으로 맞춘 좌표 보호용).
  - lat/lng 외의 필드, 장소 순서, 파일 형식(indent 2, 한글 그대로)은 바꾸지 않는다.

필요한 환경변수: KAKAO_REST_KEY (GitHub Actions Secrets에 등록된 값)
실행: python scripts/geocode_kids_places.py
"""
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

DATA_PATH = os.path.join('data', 'kids_places.json')
CACHE_PATH = os.path.join('data', 'geocode_cache.json')
ADDRESS_URL = 'https://dapi.kakao.com/v2/local/search/address.json'
KEYWORD_URL = 'https://dapi.kakao.com/v2/local/search/keyword.json'
MAX_MOVE_KM = 40.0      # 기존(구/군 중심) 좌표에서 이보다 멀면 오답으로 본다
REQUEST_GAP_SEC = 0.12  # API 호출 간격


class AuthError(Exception):
    pass


def haversine_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def kakao_get(url, params, key):
    full = url + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={
        'Authorization': 'KakaoAK ' + key,
        'User-Agent': 'Mozilla/5.0 (hohoplaylab geocoder)',
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')[:300]
        if e.code in (401, 403):
            raise AuthError('HTTP %d: %s' % (e.code, body))
        print('  ! HTTP %d (%s): %s' % (e.code, params, body))
        return None
    except Exception as e:  # 네트워크 일시 오류 등 — 이 장소만 건너뛴다
        print('  ! 요청 실패 (%s): %s' % (params, e))
        return None
    finally:
        time.sleep(REQUEST_GAP_SEC)


def clean_addr(addr):
    """괄호 안 보충설명('(테크노파크 내)', '(두류동)')과 층·호수 표기를 떼어낸다."""
    a = re.sub(r'\([^)]*\)', ' ', addr or '')
    a = re.sub(r'\s(지하\s?\d+층|\d+층|\d+호|[A-Z]동|\d+동\s?\d+호).*$', '', a)
    return re.sub(r'\s+', ' ', a).strip()


def addr_is_specific(addr):
    # 번지·도로명 번호 같은 숫자가 있어야 "구체적 주소"로 본다. "대구 중구"처럼
    # 구/군까지만 있는 주소는 주소 검색으로 찾으면 그냥 구 중심이 나오므로 건너뛴다.
    return bool(re.search(r'\d', clean_addr(addr)))


def road_addr_only(addr):
    """'센텀4로 15 센텀시티몰 4~6층'처럼 도로명+건물번호 뒤에 붙은 건물명·층수를 떼어낸다."""
    m = re.match(r'^(.*?(?:로|길)\s+\d+(?:-\d+)?)(?!\d)', clean_addr(addr))
    return m.group(1) if m else ''


def search_address(addr, key):
    # 도로명+번호만 남긴 주소 → 괄호·층수만 정리한 주소 → 원문 순서로 시도
    for q in dict.fromkeys([road_addr_only(addr), clean_addr(addr), addr]):
        if not q:
            continue
        data = kakao_get(ADDRESS_URL, {'query': q, 'size': 1}, key)
        docs = (data or {}).get('documents') or []
        if docs and docs[0].get('address_type') in ('ROAD_ADDR', 'REGION_ADDR'):
            return float(docs[0]['y']), float(docs[0]['x']), 'address'
    return None


def search_keyword(title, addr, ref_lat, ref_lng, key):
    # 이름만으로 먼저, 안 되면 "시/군/구 + 이름"으로 한 번 더.
    # 이름에 괄호가 있으면("금강보행교(이응다리)") 괄호째로는 검색이 안 되는 경우가 있어서,
    # 괄호 앞 이름("금강보행교")과 괄호 안 이름("이응다리")도 각각 따로 시도한다.
    names = [title]
    outer = re.sub(r'\([^)]*\)', ' ', title or '').strip()
    inner = re.findall(r'\(([^)]*)\)', title or '')
    for n in [outer] + [i.replace('옛 ', '').strip() for i in inner]:
        if n and n not in names:
            names.append(n)
    region = ' '.join(clean_addr(addr).split()[:2])
    queries = list(names)
    if region:
        queries += [region + ' ' + n for n in names]
    for q in queries:
        data = kakao_get(KEYWORD_URL, {'query': q, 'size': 15}, key)
        docs = (data or {}).get('documents') or []
        best = None
        for d in docs:
            lat, lng = float(d['y']), float(d['x'])
            dist = haversine_km(ref_lat, ref_lng, lat, lng)
            if best is None or dist < best[2]:
                best = (lat, lng, dist)
        if best and best[2] <= MAX_MOVE_KM:
            return best[0], best[1], 'keyword'
    return None


def main():
    key = os.environ.get('KAKAO_REST_KEY', '').strip()
    if not key:
        print('KAKAO_REST_KEY 환경변수가 없습니다. GitHub Secrets 등록을 확인하세요.')
        sys.exit(1)

    with open(DATA_PATH, encoding='utf-8') as f:
        raw = f.read()
    places = json.loads(raw)
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding='utf-8') as f:
            cache = json.load(f)

    stats = {'moved': 0, 'same': 0, 'locked': 0, 'failed': 0, 'cached': 0}
    failed, far_moves = [], []

    try:
        for p in places:
            cid, title, addr = p.get('contentid'), p.get('title', ''), p.get('addr', '')
            if p.get('coordLock'):
                stats['locked'] += 1
                continue
            try:
                ref_lat, ref_lng = float(p['lat']), float(p['lng'])
            except (KeyError, TypeError, ValueError):
                failed.append((cid, title, '기존 좌표 없음'))
                stats['failed'] += 1
                continue

            c = cache.get(cid)
            if c and c.get('addr') == addr and c.get('title') == title:
                result = (c['lat'], c['lng'], c['source'])
                stats['cached'] += 1
            else:
                result = None
                if addr_is_specific(addr):
                    result = search_address(addr, key)
                if result is None:
                    result = search_keyword(title, addr, ref_lat, ref_lng, key)

            if result is None:
                failed.append((cid, title, '검색 결과 없음'))
                stats['failed'] += 1
                continue

            lat, lng, source = round(result[0], 7), round(result[1], 7), result[2]
            dist = haversine_km(ref_lat, ref_lng, lat, lng)
            if dist > MAX_MOVE_KM:
                failed.append((cid, title, '결과가 기존 좌표에서 %.0fkm 떨어져 버림' % dist))
                stats['failed'] += 1
                cache.pop(cid, None)
                continue

            cache[cid] = {'addr': addr, 'title': title, 'lat': lat, 'lng': lng, 'source': source}
            if abs(lat - ref_lat) < 1e-7 and abs(lng - ref_lng) < 1e-7:
                stats['same'] += 1
                continue
            p['lat'], p['lng'] = lat, lng
            stats['moved'] += 1
            if dist >= 15:
                far_moves.append((cid, title, dist, source))
    except AuthError as e:
        print('카카오 API 인증 실패 — 파일을 하나도 바꾸지 않고 중단합니다.')
        print('KAKAO_REST_KEY 값이 "REST API 키"인지, 카카오 개발자 콘솔에서 카카오맵(로컬) 사용 설정이 켜져 있는지 확인하세요.')
        print(e)
        sys.exit(1)

    new_raw = json.dumps(places, ensure_ascii=False, indent=2)
    if new_raw != raw.rstrip('\n'):
        with open(DATA_PATH, 'w', encoding='utf-8') as f:
            f.write(new_raw)
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)

    lines = [
        '## 아이랑 장소 좌표 보정 결과',
        '',
        '| 항목 | 개수 |', '|---|---|',
        '| 좌표 바뀜 | %d |' % stats['moved'],
        '| 이미 정확함(변화 없음) | %d |' % stats['same'],
        '| 캐시 재사용 | %d |' % stats['cached'],
        '| 잠금(coordLock) | %d |' % stats['locked'],
        '| 못 찾음(기존 좌표 유지) | %d |' % stats['failed'],
        '',
    ]
    if failed:
        lines += ['### 못 찾은 장소 (기존 좌표 그대로)', '']
        lines += ['- %s %s — %s' % f for f in failed]
        lines.append('')
    if far_moves:
        lines += ['### 15km 이상 이동한 장소 (한 번 확인 권장)', '']
        lines += ['- %s %s — %.1fkm (%s)' % m for m in far_moves]
        lines.append('')
    report = '\n'.join(lines)
    print(report)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(report + '\n')


if __name__ == '__main__':
    main()
