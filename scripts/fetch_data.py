import os
import datetime
import json
import time
import html
import math
import re
from urllib.parse import quote
import requests

# [CHANGE] 2026-11-11: "오늘"을 한국 시간(KST) 기준으로 계산한다. GitHub Actions 서버는 UTC 라서 예전에는
# 새벽 5시(KST) 실행 때도 "어제" 날짜로 계산되어, 한국 날짜로 이미 끝난 축제가 오전 11시 실행 때까지 지도에 남았다.
KST = datetime.timezone(datetime.timedelta(hours=9))
NOW_KST = datetime.datetime.now(KST)
TODAY = NOW_KST.strftime('%Y%m%d')
# 30일 전부터 검색해서, 이미 시작했지만 아직 안 끝난 축제도 놓치지 않도록 함
SEARCH_FROM = (NOW_KST - datetime.timedelta(days=30)).strftime('%Y%m%d')

# 서울 리전에서 실행되는 Vercel 프록시 함수 주소.
# GitHub Actions(해외 서버)가 apis.data.go.kr에 직접 접속하면 차단당하는 문제를 피하기 위해
# 한국 위치인 이 프록시를 통해 대신 데이터를 받아온다.
PROXY_URL = os.environ.get("FESTIVAL_PROXY_URL", "https://YOUR-PROJECT.vercel.app/api/festivals")

# map.html의 지역 필터(filterRegion)와 반드시 동일하게 맞춰야 하는 지역 구분.
# 순서가 곧 "전국 전체보기"에서 대표 축제가 나열되는 순서.
REGION_KEYWORDS = [
    # [FIX] 2026-10-26: 지역 판정을 "주소에 키워드가 들어있는가(in)"에서 "주소가 키워드로 시작하는가"로 바꿨다.
    # 예전 방식은 서울 종로구 "세종로/세종대로"가 '세종'에, 경기도 "광주시"가 '광주'에 걸려서
    # 서울 행사가 충청 대표로, 경기 광주 행사가 전라 대표로 뽑히는 오류가 있었다.
    # 또 TourAPI 주소가 2026년부터 광주·전남 모두 "전남광주통합특별시 …"로 내려오므로 '전남'(접두)로 잡히게 했다.
    ('seoul', ['서울', '인천', '경기', '수원', '용인', '파주', '화성']),
    ('gangwon', ['강원', '강릉']),
    ('chungcheong', ['세종', '대전', '충북', '충남', '충청', '청주']),
    ('gyeongsang', ['대구', '울산', '부산', '경북', '경남', '경상']),
    ('jeolla', ['광주', '전북', '전남', '전라']),
    ('jeju', ['제주']),
]

REGION_LABELS = {
    'seoul': '서울·인천·경기',
    'gangwon': '강원',
    'chungcheong': '세종·대전·충청',
    'gyeongsang': '경상도',
    'jeolla': '광주·전라도',
    'jeju': '제주',
}


def fetch_all_items(mode='festival', max_retries=3):
    """Vercel 프록시(서울 리전)를 통해 TourAPI 데이터를 한 번에 받아온다.
    mode='nature'면 축제 대신 자연관광지(수목원·공원·자연휴양림)를 가져온다.

    festivals.js는 실패해도 항상 JSON({"error": "진짜 이유..."}) 형태로 응답하도록 짜여있다.
    상태코드와 무관하게 항상 본문을 먼저 파싱해서 진짜 원인을 그대로 로그에 남긴다
    (res.raise_for_status()를 먼저 부르면 502 등에서 본문이 버려져 원인을 알 수 없게 된다)."""
    params = {'mode': mode}
    if mode == 'festival':
        params['from'] = SEARCH_FROM

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(PROXY_URL, params=params, timeout=30)
            try:
                data = res.json()
            except ValueError:
                data = None

            if res.ok and isinstance(data, dict) and 'error' not in data:
                return data.get('items', [])

            if isinstance(data, dict) and 'error' in data:
                last_error = RuntimeError(f"HTTP {res.status_code} - {data['error']}")
            else:
                last_error = RuntimeError(f"HTTP {res.status_code} - {(res.text or '')[:200]}")
        except requests.exceptions.RequestException as e:
            last_error = e

        wait = 5 * attempt
        print(f"프록시 호출 실패({mode}, {attempt}/{max_retries}): {last_error} — {wait}초 후 재시도")
        if attempt < max_retries:
            time.sleep(wait)
    raise last_error


def fetch_shelter_page(page_no, num_of_rows=1000, max_retries=3):
    """무더위쉼터 프록시(festivals.js, mode=shelter)에서 딱 한 페이지만 받아온다.
    전국 데이터가 9만3천여 건(2026년 기준)이라, 프록시가 내부에서 전체 페이지를
    다 모아 한 번에 돌려주는 방식은 Vercel 함수 실행시간을 넘겨 타임아웃이 난다
    (실제로 발생함). 그래서 페이지네이션은 여기(파이썬)에서 직접 돌고, 프록시는
    한 페이지 처리만 담당한다 — 왕복 하나하나는 항상 짧게 끝나 안전하다."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(
                PROXY_URL,
                params={'mode': 'shelter', 'pageNo': page_no, 'numOfRows': num_of_rows},
                timeout=30
            )
            try:
                data = res.json()
            except ValueError:
                data = None

            if res.ok and isinstance(data, dict) and 'error' not in data:
                return data.get('items', []), int(data.get('totalCount') or 0)

            if isinstance(data, dict) and 'error' in data:
                last_error = RuntimeError(f"HTTP {res.status_code} - {data['error']}")
            else:
                last_error = RuntimeError(f"HTTP {res.status_code} - {(res.text or '')[:200]}")
        except requests.exceptions.RequestException as e:
            last_error = e

        wait = 3 * attempt
        print(f"무더위쉼터 페이지 호출 실패({page_no}페이지, {attempt}/{max_retries}): {last_error} — {wait}초 후 재시도")
        if attempt < max_retries:
            time.sleep(wait)
    raise last_error


def fetch_all_shelter_items_paginated(num_of_rows=1000, max_pages=150):
    """전국 무더위쉼터(9만 건 이상)를 여러 페이지로 나눠 순차적으로 전부 받아온다.
    max_pages는 totalCount를 잘못 읽는 경우 등에 대비한 안전장치일 뿐이고
    (numOfRows=1000 기준 최대 15만 건까지 커버, 현재 알려진 전국 규모 9만3천여 건보다
    넉넉하게 잡아둔 값), 정상적으로는 totalCount에 도달하면 그 전에 끝난다."""
    all_items = []
    page_no = 1
    while True:
        items, total_count = fetch_shelter_page(page_no, num_of_rows)
        if not items:
            break
        all_items.extend(items)
        if page_no * num_of_rows >= total_count:
            break
        if page_no >= max_pages:
            print(f"무더위쉼터 페이지 수집이 안전 한도({max_pages}페이지)에 도달해 중단합니다. "
                  f"지금까지 {len(all_items)}건 / 전체 {total_count}건")
            break
        page_no += 1
    return all_items


SHELTER_CACHE_PATH = os.path.join('data', 'shelter_raw_cache.json')
SHELTER_CACHE_MAX_AGE_DAYS = 3  # safemap.go.kr 원본 데이터의 갱신주기가 1년이라, 매 실행마다 다시 받을 필요가 없음


def load_shelter_cache():
    """최근에 받아둔 무더위쉼터 원본 데이터가 있으면 재사용한다. 원본 갱신주기가
    1년이라, 실행(하루 3회)마다 9만 건 넘는 데이터를 매번 다시 받는 건 API에
    불필요한 부담을 주고 실행 시간도 늘어난다. 캐시가 없거나 오래됐으면 None을 반환."""
    if not os.path.exists(SHELTER_CACHE_PATH):
        return None
    try:
        with open(SHELTER_CACHE_PATH, 'r', encoding='utf-8') as fp:
            cache = json.load(fp)
        fetched_at = datetime.datetime.strptime(cache.get('fetched_at', ''), '%Y%m%d')
        age_days = (datetime.datetime.now() - fetched_at).days
        if age_days > SHELTER_CACHE_MAX_AGE_DAYS:
            return None
        return cache.get('items', [])
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


def save_shelter_cache(items):
    os.makedirs('data', exist_ok=True)
    with open(SHELTER_CACHE_PATH, 'w', encoding='utf-8') as fp:
        json.dump({'fetched_at': TODAY, 'items': items}, fp, ensure_ascii=False)


def fetch_detail_overview(content_id, max_retries=2):
    """특정 축제의 상세 설명(overview)을 프록시(detail.js / detailCommon2)를 통해 받아온다.

    detail.js는 실패해도 항상 JSON({"error": "진짜 이유..."}) 형태로 응답하도록 짜여있다.
    상태코드와 무관하게 항상 본문을 먼저 파싱해서 진짜 원인을 그대로 로그에 남긴다
    (res.raise_for_status()를 먼저 부르면 502 등에서 본문이 버려져 원인을 알 수 없게 된다).
    실패해도 전체 파이프라인을 막지 않도록 빈 문자열을 돌려준다."""
    if not content_id:
        return ''

    detail_url = PROXY_URL.rsplit('/', 1)[0] + '/detail'
    last_message = ''
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(detail_url, params={'contentId': content_id}, timeout=20)
            try:
                data = res.json()
            except ValueError:
                data = None

            if res.ok and isinstance(data, dict) and 'error' not in data:
                return (data.get('overview') or '').strip()

            if isinstance(data, dict) and 'error' in data:
                last_message = f"HTTP {res.status_code} - {data['error']}"
            else:
                last_message = f"HTTP {res.status_code} - {(res.text or '')[:200]}"
        except requests.exceptions.RequestException as e:
            last_message = str(e)

        if attempt < max_retries:
            time.sleep(3)

    print(f"상세 설명 조회 실패(contentId={content_id}): {last_message}")
    return ''


def fetch_intro_fields(content_id, content_type_id='15', max_retries=2):
    """축제 상세페이지용 부가정보(이용요금·주최/주관·홈페이지 등)를
    프록시(intro.js / detailIntro2)를 통해 받아온다.
    실패해도 전체 파이프라인을 막지 않도록 빈 dict를 돌려준다."""
    if not content_id:
        return {}

    intro_url = PROXY_URL.rsplit('/', 1)[0] + '/intro'
    last_message = ''
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(
                intro_url,
                params={'contentId': content_id, 'contentTypeId': content_type_id or '15'},
                timeout=20
            )
            try:
                data = res.json()
            except ValueError:
                data = None

            if res.ok and isinstance(data, dict) and 'error' not in data:
                return data

            if isinstance(data, dict) and 'error' in data:
                last_message = f"HTTP {res.status_code} - {data['error']}"
            else:
                last_message = f"HTTP {res.status_code} - {(res.text or '')[:200]}"
        except requests.exceptions.RequestException as e:
            last_message = str(e)

        if attempt < max_retries:
            time.sleep(3)

    print(f"부가정보 조회 실패(contentId={content_id}): {last_message}")
    return {}


# [ADD] 2026-11-11: 상세페이지에도 지도 코스 카드와 같은 운영시간·소요시간을 보여준다.
# TourAPI 운영시간(playTime)은 "화요일~일요일 10:30 / 14:00매주 월요일 휴무"처럼 붙어서 내려와 읽기 좋게 나눈다.
# FESTIVAL_EXTRA_INFO: TourAPI에는 없고 공식 안내로만 확인된 소요시간 등(contentid 기준). festival/index.html 의 같은 이름 상수와 맞춘다.
#  - 3113265 APAP 작품투어: 안양문화예술재단 안내 — 소요 약 60~90분
FESTIVAL_EXTRA_INFO = {
    '3113265': {'duration': '약 60~90분'},
}
TIME_ROW_START = '<!--pt:v1-->'
TIME_ROW_END = '<!--/pt:v1-->'


def format_play_time_for_page(raw):
    """playTime 문구를 상세페이지용 한 줄(" · "로 구분)로 정리한다. 읽을 수 없으면 빈 문자열."""
    t = re.sub(r'<[^>]+>', ' ', str(raw or ''))
    t = html.unescape(t)
    t = t.replace('※', ' · ')
    t = re.sub(r'(^|\s)[-•*]\s+', ' · ', t)
    t = re.sub(r'([0-9:)])\s*-\s*(?=[가-힣]|\d{1,2}/\d)', r'\1 · ', t)
    t = re.sub(r'([0-9:)])(?=(?:매주|매월|매일))', r'\1 · ', t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'(?:\s*·\s*){2,}', ' · ', t)
    t = re.sub(r'^\s*·\s*', '', t)
    t = re.sub(r'\s*·\s*$', '', t).strip()
    if not t or '확인되지' in t:
        return ''
    return t[:200]


def build_time_rows_html(play_time, content_id):
    """운영시간·소요시간 행(마커로 감싸 여러 번 실행해도 같은 결과). 보여줄 정보가 없으면 빈 문자열."""
    rows = []
    pt = format_play_time_for_page(play_time)
    if pt:
        rows.append('<div class="detail-row"><div class="detail-label">운영시간</div><div class="detail-value">'
                    + html.escape(pt) + '</div></div>')
    extra = FESTIVAL_EXTRA_INFO.get(str(content_id or '')) or {}
    if extra.get('duration'):
        rows.append('<div class="detail-row"><div class="detail-label">소요시간</div><div class="detail-value">'
                    + html.escape(extra['duration']) + '</div></div>')
    if not rows:
        return ''
    return TIME_ROW_START + '\n    '.join(rows) + TIME_ROW_END + '\n    '


def build_detail_page_html(festival, overview, intro):
    """축제 1건에 대한 독립 상세페이지(festival/detail/{contentid}.html)를 만든다."""
    title = html.escape(festival.get('title') or '')
    addr = html.escape(festival.get('addr') or '')
    start = festival.get('startDate') or ''
    end = festival.get('endDate') or ''
    lat = festival.get('lat') or ''
    lng = festival.get('lng') or ''
    image = festival.get('image') or ''
    tel = html.escape(festival.get('tel') or intro.get('sponsor1tel') or '')

    def fmt_date(raw):
        return f"{raw[:4]}.{raw[4:6]}.{raw[6:8]}" if len(raw) == 8 else raw
    date_label = f"{fmt_date(start)} ~ {fmt_date(end)}"

    overview_html = html.escape(overview) if overview else '설명 정보가 없습니다.'
    fee = html.escape(intro.get('usetimefestival') or '') or '정보 없음'
    sponsor1 = html.escape(intro.get('sponsor1') or '')
    sponsor2 = html.escape(intro.get('sponsor2') or '')
    sponsor_label = ' / '.join([s for s in [sponsor1, sponsor2] if s]) or '정보 없음'
    program = html.escape(intro.get('program') or '')
    eventplace = html.escape(intro.get('eventplace') or '')
    # TourAPI가 <a href="...">...</a> 형태의 HTML 문자열로 그대로 내려주는 경우가 많아 그대로 사용
    homepage_raw = intro.get('eventhomepage') or ''

    time_rows = build_time_rows_html(festival.get('playTime'), festival.get('contentid'))
    map_link_html = ''
    if lat and lng:
        map_url = f"https://map.kakao.com/link/map/{quote(festival.get('title') or '축제')},{lat},{lng}"
        map_link_html = f'<a href="{map_url}" target="_blank" rel="noopener" class="detail-link">지도에서 보기 →</a>'

    image_html = f'<img src="{image}" alt="{title}" class="detail-image">' if image else ''
    program_block = (
        f'<div class="detail-card"><div class="detail-label" style="margin-bottom:8px;">프로그램</div>'
        f'<div class="detail-overview">{program}</div></div>'
        if program else ''
    )

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - 전국 축제 지도</title>
<meta name="description" content="{title} | {date_label} | {addr}">
<!-- [ADD] 애드센스 심사에서 "가치가 별로 없는 콘텐츠"로 지적받음 — 공공데이터
     소개문을 거의 그대로 옮긴 짧은 페이지가 1,000건 넘게 있어 사이트 전체가
     "복사한 페이지 모음"처럼 보인 것. 검색 결과·크롤러 평가에서 이 페이지들을
     주요 콘텐츠로 안 치도록 noindex 처리(링크는 계속 따라가게 follow는 유지).
     지도 자체(사람이 보는 화면)는 그대로다 — 크롤링/색인 신호만 바꾸는 것. -->
<meta name="robots" content="noindex, follow">
<link rel="icon" href="/favicon.svg">
<script src="https://cdn.tailwindcss.com"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, sans-serif; background: #f8fafc; margin: 0; }}
  .detail-wrap {{ max-width: 640px; margin: 0 auto; padding: 24px 20px 60px; }}
  .detail-image {{ display: block; width: 100%; height: auto; border-radius: 14px; margin-bottom: 20px; object-fit: contain; max-height: 480px; background: #f1f5f9; }}
  .detail-card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px; margin-bottom: 16px; }}
  .detail-row {{ display: flex; gap: 8px; padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-size: 14px; }}
  .detail-row:last-child {{ border-bottom: none; }}
  .detail-label {{ flex: 0 0 90px; font-weight: 700; color: #1a73e8; }}
  .detail-value {{ flex: 1; color: #334155; word-break: break-all; }}
  .detail-back {{ display: inline-block; margin-bottom: 16px; color: #1a73e8; font-weight: 700; text-decoration: none; font-size: 14px; }}
  .detail-link {{ color: #1a73e8; font-weight: 700; text-decoration: none; }}
  .detail-link:hover {{ text-decoration: underline; }}
  .detail-overview {{ font-size: 14px; color: #444; line-height: 1.6; white-space: pre-line; }}
</style>
</head>
<body>
<div class="detail-wrap">
  <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">
    <a href="/festival/" class="detail-back" style="margin-bottom:0;">← 지도로 돌아가기</a>
    <a href="/" style="color:#1a73e8; font-weight:700; text-decoration:none; font-size:14px;">🏠 홈</a>
  </div>
  {image_html}
  <h1 style="font-size:22px; font-weight:800; color:#111; margin-bottom:8px;">{title}</h1>
  <p style="font-size:13px; color:#ff5722; font-weight:700; margin-bottom:20px;">📅 {date_label}</p>

  <div class="detail-card">
    <div class="detail-row"><div class="detail-label">장소</div><div class="detail-value">{addr}{(' · ' + eventplace) if eventplace else ''}</div></div>
    {time_rows}<div class="detail-row"><div class="detail-label">이용요금</div><div class="detail-value">{fee}</div></div>
    <div class="detail-row"><div class="detail-label">주최/주관</div><div class="detail-value">{sponsor_label}</div></div>
    <div class="detail-row"><div class="detail-label">대표번호</div><div class="detail-value">{tel or '정보 없음'}</div></div>
    <div class="detail-row"><div class="detail-label">홈페이지</div><div class="detail-value">{homepage_raw or '정보 없음'}</div></div>
  </div>

  <div class="detail-card">
    <div class="detail-overview">{overview_html}</div>
  </div>

  {program_block}

  <div style="margin-top:20px;">{map_link_html}</div>
</div>
<div id="site-footer"></div>
<script>
    fetch('/footer.html')
        .then(res => res.text())
        .then(html => {{
            const footerEl = document.getElementById('site-footer');
            footerEl.innerHTML = html;
            footerEl.querySelectorAll('script').forEach(function (oldScript) {{
                const newScript = document.createElement('script');
                if (oldScript.src) newScript.src = oldScript.src;
                newScript.textContent = oldScript.textContent;
                oldScript.parentNode.replaceChild(newScript, oldScript);
            }});
        }})
        .catch(function () {{ /* 푸터 로드 실패해도 상세페이지 표시엔 영향 없음 */ }});
</script>
</body>
</html>
'''


def generate_detail_pages(festivals):
    """각 축제의 상세페이지(festival/detail/{contentid}.html)를 생성한다.
    이미 만들어진 페이지는 다시 만들지 않고, 새로 나타난 contentid만 생성한다 —
    축제 상세 정보(요금·주최 등)는 한 번 생성되면 바뀔 일이 거의 없고,
    매일 전체를 다시 만들면 TourAPI 호출만 불필요하게 늘어나기 때문.
    [2026-10-27] 예전에는 이미 있는 페이지에 애드센스 코드가 빠져 있으면 자동으로
    끼워넣었지만, 본문이 짧은 자동 생성 페이지라 "가치가 별로 없는 콘텐츠" 지적을
    받아 상세페이지에는 광고 코드를 넣지 않기로 했다(보정 로직도 제거)."""
    detail_dir = os.path.join('festival', 'detail')
    os.makedirs(detail_dir, exist_ok=True)


    new_count = 0
    for f in festivals:
        content_id = f.get('contentid')
        if not content_id:
            continue
        out_path = os.path.join(detail_dir, f'{content_id}.html')
        if os.path.exists(out_path):
            continue  # 이미 생성된 페이지는 건드리지 않음

        overview = f.get('overview')  # 수동 등록 축제는 이미 설명이 주어져 있어 TourAPI를 안 부름
        if overview is None:
            overview = fetch_detail_overview(content_id)
        if f.get('overview') is not None:
            # 수동 등록 축제: TourAPI 부가정보(intro)를 부르지 않는 대신,
            # manual_festivals.json에 적어둔 이용요금/주최주관/프로그램/홈페이지를
            # TourAPI와 같은 모양(intro dict)으로 바꿔서 그대로 사용한다.
            # 비워둔 항목은 build_detail_page_html()이 기존처럼 '정보 없음'으로 보여준다.
            intro = {
                'usetimefestival': f.get('fee', ''),
                'sponsor1': f.get('sponsor1', ''),
                'sponsor2': f.get('sponsor2', ''),
                'program': f.get('program', ''),
                'eventplace': f.get('eventplace', ''),
                'eventhomepage': f.get('homepage', ''),
            }
        else:
            intro = fetch_intro_fields(content_id)
            # [ADD] 2026-11-01: 이미 받아온 부가정보에서 행사 시간대(playtime)도 같이 기억해 둔다(추가 호출 없음).
            # 조회 실패({})일 땐 기록하지 않아 attach_play_times()가 다음 실행에서 다시 시도한다.
            if intro:
                f['playTime'] = clean_play_time(intro.get('playtime'))
        page_html = build_detail_page_html(f, overview, intro)
        with open(out_path, 'w', encoding='utf-8') as fp:
            fp.write(page_html)
        new_count += 1
        time.sleep(0.3)  # TourAPI에 과도하게 연속 호출하지 않도록 약간의 간격

    print(f"상세페이지 신규 생성: {new_count}건 (festival/detail/)")


def clean_play_time(raw):
    """TourAPI playtime(행사 시간대) 문구를 한 줄 텍스트로 정리한다.
    HTML 줄바꿈/태그를 공백으로 바꾸고 연속 공백을 줄이며, 너무 길면 자른다."""
    if not raw:
        return ''
    s = re.sub(r'<br\s*/?>', ' ', str(raw), flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = html.unescape(s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s[:160]


# 한 번 실행에 새로 조회할 최대 건수. 지도의 축제는 150건 안팎이라 처음 며칠에 걸쳐 채워지고,
# 이후엔 새로 생긴 축제만 조회하므로 TourAPI 호출량이 거의 늘지 않는다.
PLAY_TIME_MAX_NEW_PER_RUN = 70


def classify_fee(text):
    """[ADD] 2026-11-11: 상세페이지의 '이용요금' 문구를 무료/일부 유료/유료로 나눈다(판단이 안 되면 '').
      free  = '무료'만 있고 금액·유료 표시가 없음   (예: 무료)
      mixed = 무료로 시작하지만 일부 유료/금액이 함께 있음 (예: 무료(일부 프로그램 유료))
      paid  = 금액(○○원)이나 '유료'가 있고 무료로 시작하지 않음 (예: 성인 12,000원)
    """
    t = re.sub(r'\s+', ' ', text or '').strip()
    has_paid = bool(re.search(r'\d[\d,]*\s*원|유료', t))
    has_free = '무료' in t
    if has_free and not has_paid:
        return 'free'
    if has_paid and not has_free:
        return 'paid'
    if has_paid and has_free:
        return 'mixed' if re.match(r'^[\s\-\[\]※]*(입장료\s*)?무료', t) else 'paid'
    return ''


# 시·군 이름(끝의 '시'·'군' 뺀 것) + 광역시도. 행사명 앞 단어가 지역 이름인지 판단하는 기준.
# '영동'처럼 시·군 이름이면서 권역 이름으로도 쓰여 오해가 생기는 것은 일부러 뺐다.
REGION_STEMS = set((
    "서울 부산 대구 인천 광주 대전 울산 세종 제주 "
    "수원 성남 의정부 안양 부천 광명 평택 동두천 안산 고양 과천 구리 남양주 오산 시흥 군포 의왕 하남 용인 파주 이천 안성 김포 화성 양주 포천 여주 "
    "춘천 원주 강릉 동해 태백 속초 삼척 청주 충주 제천 천안 공주 보령 아산 서산 논산 계룡 당진 전주 군산 익산 정읍 남원 김제 "
    "목포 여수 순천 나주 광양 포항 경주 김천 안동 구미 영주 영천 상주 문경 경산 창원 진주 통영 사천 김해 밀양 거제 양산 서귀포 "
    "가평 양평 연천 강화 옹진 고성 양양 영월 평창 정선 철원 화천 양구 인제 홍천 횡성 보은 옥천 증평 진천 괴산 음성 단양 "
    "금산 부여 서천 청양 홍성 예산 태안 완주 진안 무주 장수 임실 순창 고창 부안 담양 곡성 구례 고흥 보성 화순 장흥 강진 해남 영암 "
    "무안 함평 영광 장성 완도 진도 신안 군위 의성 청송 영양 영덕 청도 고령 성주 칠곡 예천 봉화 울진 울릉 의령 함안 창녕 하동 산청 "
    "함양 거창 합천 남해 기장 달성"
).split())


def build_region_vocab(items):
    """[ADD] 2026-11-11: 주소에서 시·군 이름(예: 영주, 안동)과 시도 이름을 모아 '지역 이름 목록'을 만든다.
    행사명 첫 단어가 지역 이름인데 실제 개최 주소가 다른 지역인 경우를 찾는 데 쓴다."""
    vocab = set(REGION_STEMS)
    for it in items or []:
        a = it.get('addr') or ''
        for w in re.findall(r'([가-힣]{2,4})(?:시|군)(?=\s|$)', a):
            vocab.add(w)
    return vocab


def venue_mismatch_note(item, vocab):
    """[ADD] 2026-11-11: 행사명 앞의 지역(예: '영주 사과축제'의 영주)과 개최 주소의 지역이 다르면 안내 문구를 돌려준다.
    다른 지역 주최 행사가 서울 등에서 열리는 경우(직거래 장터 등)를 방문자가 오류로 오해하지 않게 하는 용도이며,
    데이터를 고치는 것이 아니라 '확인하세요' 안내만 붙인다. 해당 없으면 빈 문자열."""
    title = (item.get('title') or '').strip()
    addr = (item.get('addr') or '').strip()
    if not title or not addr:
        return ''
    title = re.sub(r'^[\[(（]?(?:제?\s*\d+\s*(?:회|th)?|\d{4}\s*년?)[\])）]?\s*', '', title)
    m = re.match(r'([가-힣]{2,4})(?=\s|$)', title)
    if not m:
        return ''
    tok = m.group(1)
    if tok not in vocab or tok in addr:
        return ''
    label = ' '.join(addr.split()[:2])
    return (f"행사명의 지역({tok})과 개최 장소({label})가 달라요. "
            f"다른 지역에서 여는 행사일 수 있으니 방문 전 개최 장소를 확인해 주세요.")


def compute_venue_notes(items):
    """contentid → 안내 문구. 축제 항목만 대상."""
    fest = [i for i in (items or []) if i.get('type', 'festival') == 'festival']
    vocab = build_region_vocab(fest)
    out = {}
    for it in fest:
        n = venue_mismatch_note(it, vocab)
        if n and it.get('contentid'):
            out[str(it['contentid'])] = n
    return out


def attach_fee_types(items, detail_dir=os.path.join('festival', 'detail')):
    """[ADD] 2026-11-11: 축제 포스터 페이지가 '무료/유료'로 걸러 볼 수 있도록, 축제 항목마다 feeType 을 붙인다.
    이미 만들어진 상세페이지(festival/detail/{contentid}.html)의 '이용요금' 값을 읽어 판단하며,
    상세페이지가 없거나 판단이 안 되면 feeType 을 비워 둔다. 실패해도 다른 데이터에는 영향을 주지 않는다."""
    n = 0
    for it in items:
        if it.get('type') != 'festival':
            continue
        it['feeType'] = ''
        cid = it.get('contentid')
        path = os.path.join(detail_dir, f'{cid}.html')
        if not cid or not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as fp:
                page = fp.read()
        except Exception:
            continue
        m = re.search(r'이용요금</div>\s*<div class="detail-value">(.*?)</div>', page, re.S)
        if m:
            it['feeType'] = classify_fee(html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1))))
            n += 1 if it['feeType'] else 0
    print(f"축제 이용요금 구분(feeType) {n}건")


def attach_play_times(festivals, prev_path=os.path.join('data', 'festivals.json')):
    """[ADD] 2026-11-01: 지도 코스에서 "이 행사는 몇 시에 끝나는지"를 계산할 수 있도록
    축제마다 playTime(행사 시간대 문구)을 붙인다.
      - 지난번 festivals.json 에 이미 playTime 키가 있으면(빈 문자열 포함) 그대로 재사용한다.
        → 별도 캐시 파일이 필요 없고(워크플로 git add 목록 변경 불필요), 한 번 조회한 건 다시 안 부른다.
      - 키가 없는 축제만 부가정보(detailIntro2)를 조회하되, 한 번에 PLAY_TIME_MAX_NEW_PER_RUN건까지만.
      - 조회가 실패하면({}) 키를 넣지 않아 다음 실행에서 다시 시도한다.
    실패해도 전체 파이프라인은 멈추지 않는다."""
    prev = {}
    try:
        if os.path.exists(prev_path):
            with open(prev_path, 'r', encoding='utf-8') as fp:
                for x in json.load(fp):
                    if isinstance(x, dict) and x.get('type') == 'festival' and 'playTime' in x and x.get('contentid'):
                        prev[x['contentid']] = x['playTime']
    except Exception as e:
        print(f"이전 festivals.json 읽기 실패(playTime 재사용 생략): {e}")

    reused = fetched = failed = 0
    for f in festivals:
        cid = f.get('contentid')
        if not cid:
            continue
        if 'playTime' in f:
            continue  # 수동 등록 축제 또는 이번 실행에서 상세페이지를 만들며 이미 받은 값
        if cid in prev:
            f['playTime'] = prev[cid]
            reused += 1
            continue
        if fetched >= PLAY_TIME_MAX_NEW_PER_RUN:
            continue
        try:
            intro = fetch_intro_fields(cid)
        except Exception as e:
            print(f"행사시간 조회 중 오류(contentId={cid}): {e}")
            intro = {}
        if intro:
            f['playTime'] = clean_play_time(intro.get('playtime'))
            fetched += 1
        else:
            failed += 1
        time.sleep(0.3)
    filled = sum(1 for f in festivals if f.get('playTime'))
    print(f"행사시간(playTime): 재사용 {reused}건, 신규 조회 {fetched}건, 실패 {failed}건, 값이 있는 축제 {filled}/{len(festivals)}건")


# [ADD] 2026-11-11: 상세페이지의 "← 지도로 돌아가기"가 전국 지도로만 돌아가서, 그 장소 위치로 바로 가도록
# ?id=contentid&lat=&lng= 를 실어 보낸다(festival/index.html 이 이 값을 읽어 그 위치로 이동하고 하단 카드까지 띄운다).
# 아이랑 장소 상세(generate_kids_detail_pages.py)는 이미 같은 형식을 쓴다. 좌표는 페이지 안의 "지도에서 보기" 링크
# (map.kakao.com/link/map/이름,위도,경도)에서 읽고, 없으면 id 만 싣는다. 링크가 정확히 "/festival/" 인 것만 바꾸므로
# 다시 실행해도 결과가 같다.
BACK_LINK_RE = re.compile(r'<a href="/festival/"([^>]*>← (?:나들이 )?지도로 돌아가기</a>)')
MAP_COORD_RE = re.compile(r'map\.kakao\.com/link/map/[^,"\']*,(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)')


def add_focus_to_back_link(content, content_id):
    m = BACK_LINK_RE.search(content)
    if not m or not content_id:
        return content, False
    url = f'/festival/?id={quote(str(content_id))}'
    c = MAP_COORD_RE.search(content)
    if c:
        url += f'&amp;lat={c.group(1)}&amp;lng={c.group(2)}'
    return content[:m.start()] + f'<a href="{url}"' + m.group(1) + content[m.end():], True


def patch_existing_detail_pages(festivals=None):
    """festival/detail/ 폴더 안에 이미 만들어진 상세페이지 전체(누적 수천 건)를
    대상으로, 상단 "🏠 홈" 버튼이 빠진 옛 버전을 찾아 새 버전으로 바꿔치기한다.

    [FIX] 처음엔 generate_detail_pages() 안에서, 이번 실행에서 새로 받아온 festivals
    목록(= 아직 끝나지 않은 "진행중/예정" 축제만 담김, 예: 278건)에 대해서만 보정했다.
    그런데 festival/detail/에는 이미 종료되어 더 이상 그 목록에 없는 과거 축제의
    상세페이지도 수천 건 그대로 남아있어서(디자인상 일부러 안 지움 — SEO/이미 색인된
    페이지 보존 목적), 실제로 돌려보니 3,456건 중 278건만 보정되고 나머지는
    "진행중/예정 목록에 없다"는 이유로 그냥 건너뛰어졌다. 그래서 festivals 목록을
    거치지 않고 festival/detail/ 디렉터리 자체를 직접 훑어서, 종료된 지 오래된
    페이지까지 포함해 전부 빠짐없이 보정하도록 따로 뺐다. TourAPI 재호출은 전혀
    없고 파일 내용 치환만 하는 것이라, 수천 건이어도 몇 초 안에 끝난다."""
    detail_dir = os.path.join('festival', 'detail')
    if not os.path.isdir(detail_dir):
        print(f"{detail_dir} 폴더가 없어 전체 보정을 건너뜁니다.")
        return

    # 축제 상세페이지(build_detail_page_html) 템플릿 — 기존 "지도로 돌아가기"
    # 한 줄을 "지도로 돌아가기 + 홈" 두 줄짜리로 바꿔치기한다.
    OLD_HEADER = '<a href="/festival/" class="detail-back">← 지도로 돌아가기</a>'
    NEW_HEADER = (
        '<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">\n'
        '    <a href="/festival/" class="detail-back" style="margin-bottom:0;">← 지도로 돌아가기</a>\n'
        '    <a href="/" style="color:#1a73e8; font-weight:700; text-decoration:none; font-size:14px;">🏠 홈</a>\n'
        '  </div>'
    )

    # [ADD] 자연관광지/캠핑장/수상레저 상세페이지(build_nature_page_html) 템플릿은
    # 원래 상단에 아무 링크도 없이(바로 사진/제목부터 시작) 맨 아래에만
    # "← 지도에서 보기"(class="back-link")가 있던 구조라, 위 OLD_HEADER 문자열 자체가
    # 없다 — "바꿔치기"가 아니라 <body> 바로 뒤에 새로 "끼워넣기"가 필요하다.
    # class="back-link"는 이 템플릿에서만 쓰는 고유 표식이라 이걸로 "아직 홈 버튼이
    # 없는 자연관광지류 페이지"를 구분한다(이미 끼워넣은 페이지는 "🏠 홈" 문자열로
    # 판별해 건너뛰므로 재실행해도 중복으로 끼워넣지 않는다).
    NATURE_MARKER = 'class="back-link"'
    NATURE_HEADER = (
        '<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">\n'
        '  <a href="/festival/" style="color:#059669; font-weight:700; text-decoration:none; font-size:14px;">← 지도로 돌아가기</a>\n'
        '  <a href="/" style="color:#059669; font-weight:700; text-decoration:none; font-size:14px;">🏠 홈</a>\n'
        '</div>\n'
    )

    # [ADD] 2026-11-11: 대표 사진 모양 보정. 예전 CSS는 사진을 높이 320px로 가운데만 잘라(object-fit: cover)
    # 보여줘서, 세로로 긴 포스터(예: 광주비엔날레 7:10)는 글자가 없는 가운데 빈 부분만 보였다.
    # 사진 전체가 보이게(contain) 바꾸고 높이 상한을 480px로 늘린다. 옛 CSS 문자열이 있는 페이지만 바꾸므로
    # 여러 번 실행해도 결과가 같다(TourAPI 호출 없음, 문자열 치환만).
    IMG_CSS_OLD_NEW = (
        ('.detail-image { width: 100%; border-radius: 14px; margin-bottom: 20px; object-fit: cover; max-height: 320px; }',
         '.detail-image { display: block; width: 100%; height: auto; border-radius: 14px; margin-bottom: 20px; object-fit: contain; max-height: 480px; background: #f1f5f9; }'),
        ('.detail-image{width:100%;border-radius:14px;margin-bottom:16px;object-fit:cover;max-height:320px}',
         '.detail-image{display:block;width:100%;height:auto;border-radius:14px;margin-bottom:16px;object-fit:contain;max-height:480px;background:#f1f5f9}'),
    )

    # [ADD] 2026-11-11: 운영시간·소요시간 행. 이번 실행에서 받은 festivals(playTime 포함)로 이미 만들어진 상세페이지에도 끼워 넣는다.
    # 마커(<!--pt:v1-->)로 감싸 두어 다시 실행하면 같은 자리를 새 값으로 바꿀 뿐 중복되지 않는다(TourAPI 호출 없음).
    # [ADD] 2026-11-11: 이미 끝난 축제의 상세페이지에 "종료" 안내를 보여준다. 페이지 안의 날짜(📅 시작 ~ 끝)를 읽어 한국 날짜로
    # 비교하는 작은 스크립트라 매일 다시 쓰지 않아도 된다. 마커(<!--ended:v1-->)가 있으면 건너뛰어 여러 번 실행해도 중복되지 않는다.
    # 축제 상세페이지(📅 날짜가 있고 kids- 가 아닌 것)에만 넣는다. 아래 출처 안내도 같은 마커 안에 함께 넣는다.
    ENDED_MARK = '<!--ended:v1-->'
    ENDED_BANNER = (ENDED_MARK + '<div id="endedBanner" style="display:none;margin:0 0 14px;padding:10px 14px;border-radius:12px;'
                    'background:#fef2f2;border:1px solid #fecaca;color:#b91c1c;font-size:13px;font-weight:700;line-height:1.6"></div><!--/ended:v1-->\n')
    ENDED_FOOT = (
        '<!--ended-js:v1--><p style="max-width:640px;margin:0 auto;padding:0 20px 8px;font-size:11px;color:#94a3b8;line-height:1.6;text-align:center">'
        '정보 출처: 한국관광공사 TourAPI(공공데이터포털). 일정·요금·운영시간은 바뀔 수 있으니 방문 전 위 홈페이지·전화로 확인해 주세요.</p>\n'
        '<script>(function(){try{var el=document.getElementById("endedBanner");if(!el)return;'
        'var m=(document.body.innerText||"").match(/📅\\s*(\\d{4})\\.(\\d{2})\\.(\\d{2})\\s*~\\s*(\\d{4})\\.(\\d{2})\\.(\\d{2})/);if(!m)return;'
        'var end=m[4]+m[5]+m[6];var t=new Date(Date.now()+9*3600*1000).toISOString().slice(0,10).replace(/-/g,"");'
        'if(end<t){el.innerHTML="⏹ 이 행사는 "+m[4]+"."+m[5]+"."+m[6]+"에 종료되었어요. 지금 진행 중인 행사는 <a href=\\"/festival/\\" style=\\"color:#b91c1c;text-decoration:underline\\">나들이 지도</a>에서 확인하세요.";el.style.display="block";}'
        '}catch(e){}})();</script><!--/ended-js:v1-->\n'
    )
    ended_patched = 0
    # [ADD] 2026-11-11: 행사명 지역과 개최 장소가 다른 축제의 상세페이지 맨 위에 안내를 한 번만 넣고, 이후엔 같은 자리를 새 값으로 바꾼다.
    VENUE_START, VENUE_END = '<!--venue:v1-->', '<!--/venue:v1-->'
    try:
        venue_note_by_cid = compute_venue_notes(festivals)
    except Exception as _e:
        print(f"행사명-개최지 안내 계산 건너뜀: {_e}")
        venue_note_by_cid = {}
    venue_patched = 0
    FEE_ROW_MARK = '<div class="detail-row"><div class="detail-label">이용요금</div>'
    time_block_by_cid = {}
    for _f in (festivals or []):
        _cid = str(_f.get('contentid') or '')
        _blk = build_time_rows_html(_f.get('playTime'), _cid)
        if _cid and _blk:
            time_block_by_cid[_cid] = _blk
    time_rows_patched = 0

    filenames = [fn for fn in os.listdir(detail_dir) if fn.endswith('.html')]
    header_patched = 0
    focus_patched = 0
    nature_header_patched = 0
    image_css_patched = 0
    for fn in filenames:
        path = os.path.join(detail_dir, fn)
        with open(path, 'r', encoding='utf-8') as fp:
            content = fp.read()
        changed = False

        if OLD_HEADER in content:
            content = content.replace(OLD_HEADER, NEW_HEADER)
            changed = True
            header_patched += 1
        elif NATURE_MARKER in content and '🏠 홈' not in content and '<body>' in content:
            content = content.replace('<body>', '<body>\n' + NATURE_HEADER, 1)
            changed = True
            nature_header_patched += 1
        # 둘 다 해당 없으면 이미 보정된 페이지(새 버전)이거나 알 수 없는 템플릿 — 건드리지 않음

        # [ADD] 2026-11-11: 축제 상세페이지에 종료 안내 배너 + 출처 안내를 한 번만 끼워 넣는다.
        if ENDED_MARK not in content and '📅' in content and not fn.startswith('kids-') \
                and '<h1' in content and '<div id="site-footer">' in content:
            content = content.replace('<h1', ENDED_BANNER + '<h1', 1)
            content = content.replace('<div id="site-footer">', ENDED_FOOT + '<div id="site-footer">', 1)
            changed = True
            ended_patched += 1

        _vn_txt = venue_note_by_cid.get(fn[:-5])
        if _vn_txt and '<h1' in content:
            _vn_html = (VENUE_START + '<div style="margin:0 0 14px;padding:10px 14px;border-radius:12px;background:#fffbeb;'
                        'border:1px solid #fde68a;color:#92400e;font-size:13px;font-weight:700;line-height:1.6">📍 '
                        + html.escape(_vn_txt) + '</div>' + VENUE_END + '\n')
            if VENUE_START in content and VENUE_END in content:
                _a = content.index(VENUE_START)
                _b = content.index(VENUE_END) + len(VENUE_END)
                _nc = content[:_a] + _vn_html.rstrip('\n') + content[_b:]
            else:
                _anchor = ENDED_MARK if ENDED_MARK in content else '<h1'
                _nc = content.replace(_anchor, _vn_html + _anchor, 1)
            if _nc != content:
                content = _nc
                changed = True
                venue_patched += 1

        # [ADD] 2026-11-11: "지도로 돌아가기" 링크에 이 장소의 id·좌표를 실어 그 위치로 돌아오게 한다.
        content, _focus_done = add_focus_to_back_link(content, fn[:-5])
        if _focus_done:
            changed = True
            focus_patched += 1

        for _old_css, _new_css in IMG_CSS_OLD_NEW:
            if _old_css in content:
                content = content.replace(_old_css, _new_css)
                changed = True
                image_css_patched += 1
                break

        _blk = time_block_by_cid.get(fn[:-5])
        if _blk and FEE_ROW_MARK in content:
            if TIME_ROW_START in content and TIME_ROW_END in content:
                _a = content.index(TIME_ROW_START)
                _b = content.index(TIME_ROW_END) + len(TIME_ROW_END)
                _new = content[:_a] + _blk.rstrip(' \n').rstrip() + content[_b:]
                _new = _new.replace(TIME_ROW_END + '\n    <div class="detail-row"><div class="detail-label">이용요금', TIME_ROW_END + '\n    <div class="detail-row"><div class="detail-label">이용요금')
            else:
                _new = content.replace(FEE_ROW_MARK, _blk + FEE_ROW_MARK, 1)
            if _new != content:
                content = _new
                changed = True
                time_rows_patched += 1

        if changed:
            with open(path, 'w', encoding='utf-8') as fp:
                fp.write(content)

    print(f"festival/detail/ 전체({len(filenames)}개 파일) 스캔 완료 — "
          f"축제 상단 홈 버튼 보정: {header_patched}건, 자연관광지류 홈 버튼 보정: {nature_header_patched}건, "
          f"대표 사진 모양 보정: {image_css_patched}건, 운영시간·소요시간 행 보정: {time_rows_patched}건, "
          f"지도로 돌아가기 위치 링크: {focus_patched}건, 종료 안내·출처 보정: {ended_patched}건, 행사명-개최지 안내: {venue_patched}건")


def build_nature_page_html(spot, overview, page_label='자연공원·수목원'):
    """수목원·공원·자연휴양림(및 캠핑장·수상레저 등 같은 방식으로 취급하는 상시 개방
    장소) 1건에 대한 독립 상세페이지를 만든다. 축제와 달리 시작/종료일, 주최자,
    이용요금 같은 축제 전용 필드가 없어서, contentTypeId와 무관하게 항상 내려오는
    공통 정보(개요·주소·전화·지도)만으로 구성한다.
    page_label만 종류별로 바꿔주면 자연관광지 외 다른 상시 개방 장소에도 그대로 쓸 수 있다."""
    title = html.escape(spot.get('title') or '')
    addr = html.escape(spot.get('addr') or '')
    lat = spot.get('lat') or ''
    lng = spot.get('lng') or ''
    image = spot.get('image') or ''
    tel = html.escape(spot.get('tel') or '')
    overview_html = html.escape(overview) if overview else '설명 정보가 없습니다.'

    map_link_html = ''
    if lat and lng:
        map_url = f"https://map.kakao.com/link/map/{quote(spot.get('title') or '관광지')},{lat},{lng}"
        map_link_html = f'<a href="{map_url}" target="_blank" rel="noopener" class="detail-link">지도에서 보기 →</a>'

    image_html = f'<img src="{html.escape(image)}" alt="{title}" class="detail-image">' if image else ''
    tel_html = f'<p class="detail-row"><strong>전화</strong> {tel}</p>' if tel else ''

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - 전국 {page_label} 지도</title>
<meta name="description" content="{title} | {addr}">
<!-- [ADD] 애드센스 "가치가 별로 없는 콘텐츠" 지적 대응 — 자연관광지/캠핑장/수상레저
     상세페이지도 축제 상세페이지와 같은 이유로 noindex 처리. -->
<meta name="robots" content="noindex, follow">
<link rel="icon" href="/favicon.svg">
<script src="https://cdn.tailwindcss.com"></script>
<style>
body{{font-family:'Noto Sans KR',sans-serif;max-width:640px;margin:0 auto;padding:20px 16px;color:#1e293b}}
.detail-image{{display:block;width:100%;height:auto;border-radius:14px;margin-bottom:16px;object-fit:contain;max-height:480px;background:#f1f5f9}}
.detail-row{{margin:6px 0;font-size:14px;color:#475569}}
.detail-link{{display:inline-block;margin-top:14px;color:#059669;font-weight:700;text-decoration:underline}}
.back-link{{display:inline-block;margin-top:24px;color:#059669;font-weight:700;text-decoration:none}}
</style>
</head>
<body>
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px;">
  <a href="/festival/" style="color:#059669; font-weight:700; text-decoration:none; font-size:14px;">← 지도로 돌아가기</a>
  <a href="/" style="color:#059669; font-weight:700; text-decoration:none; font-size:14px;">🏠 홈</a>
</div>
{image_html}
<h1 style="font-size:1.4rem;font-weight:900;margin-bottom:6px">{title}</h1>
<p class="detail-row"><strong>주소</strong> {addr}</p>
{tel_html}
{map_link_html}
<div style="margin-top:20px;padding-top:16px;border-top:1px solid #e2e8f0;font-size:14px;line-height:1.8;color:#334155">{overview_html}</div>
<a class="back-link" href="/festival/">← 지도에서 보기</a>
</body>
</html>'''


def generate_nature_detail_pages(spots, max_new=40, page_label='자연공원·수목원', log_label='자연관광지'):
    """상시 개방 장소(자연관광지·캠핑장·수상레저 등)의 상세페이지를 생성한다.
    generate_detail_pages()와 동일한 원칙(이미 있는 페이지는 재생성하지 않음)을 따른다.
    [2026-10-27] 상세페이지에는 애드센스 코드를 넣지 않는다.

    max_new: 이번 실행에서 새로 만들 상세페이지 개수 상한. 축제(searchFestival2)와
    이 함수를 쓰는 모든 종류(areaBasedList2+detailCommon2)가 같은 TourAPI 일일
    할당량을 나눠 쓰기 때문에, 첫 실행처럼 한꺼번에 수백 건을 만들려고 하면
    "일일 서비스 요청제한 초과"로 실패한다. 한 번에 조금씩만 만들고 나머지는
    다음 실행(하루 3회)에서 이어서 만들도록 제한한다."""
    detail_dir = os.path.join('festival', 'detail')
    os.makedirs(detail_dir, exist_ok=True)


    new_count = 0
    skipped_for_quota = 0
    for spot in spots:
        content_id = spot.get('contentid')
        if not content_id:
            continue
        out_path = os.path.join(detail_dir, f'{content_id}.html')
        if os.path.exists(out_path):
            continue

        if new_count >= max_new:
            skipped_for_quota += 1
            continue  # 이번 실행 할당량 소진 — 다음 실행에서 이어서 생성

        overview = fetch_detail_overview(content_id)
        page_html = build_nature_page_html(spot, overview, page_label=page_label)
        with open(out_path, 'w', encoding='utf-8') as fp:
            fp.write(page_html)
        new_count += 1
        time.sleep(0.3)

    remaining_note = f", 다음 실행으로 이월: {skipped_for_quota}건" if skipped_for_quota else ""
    print(f"{log_label} 상세페이지 신규 생성: {new_count}건{remaining_note}")


def _pick_field(item, candidates, default=''):
    """공공데이터 응답의 필드명이 기관마다 조금씩 달라, 후보 이름들을 순서대로
    시도해서 처음 값이 있는 것을 쓴다. 전부 없으면 default를 반환한다."""
    for key in candidates:
        val = item.get(key)
        if val not in (None, ''):
            return val
    return default


def webmercator_to_wgs84(x, y):
    """safemap.go.kr(생활안전지도) 무더위쉼터 API가 x/y로 내려주는 좌표는
    위경도(WGS84)가 아니라 웹 메르카토르(Web Mercator, EPSG:3857) 투영 좌표다.
    이 값을 그대로 지도(Kakao Maps)에 넣으면 엉뚱한 위치(바다 한가운데 등)에
    찍히므로, 반드시 위경도로 변환한 뒤에 써야 한다.
    실제 응답 좌표(예: 신안군 자은면 x=14031309.0658, y=4145007.07747 →
    위도 34.86, 경도 126.05)로 변환식을 검증 완료함."""
    lon = (x / 20037508.34) * 180
    lat_rad = 2 * math.atan(math.exp((y / 20037508.34) * math.pi)) - (math.pi / 2)
    lat = lat_rad * 180 / math.pi
    return lat, lon


def extract_region_label(addr):
    """주소 앞 두 토큰(시/도 + 시/군/구)을 클러스터 묶음 단위로 쓴다.
    예: '경기도 부천시 원미구 ...' → '경기도 부천시', '전라남도 신안군 ...' → '전라남도 신안군'."""
    if not addr:
        return '기타'
    parts = addr.strip().split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    return parts[0]


def build_shelter_clusters(shelter_items):
    """개별 무더위쉼터(전국 9만 건 이상)를 지역(시/군/구) 단위로 묶어서, 지도에는
    지역당 마커 1개('경기도 부천시 무더위쉼터 (87곳)')만 찍히도록 만든다.
    festivals.json에 9만 건을 통째로 넣으면 모든 방문자가 페이지를 열 때마다
    그 용량을 다 받아야 하고 지도에 마커 9만 개를 그리는 것도 무리라 반드시 필요한 처리.
    지역별 개별 목록은 data/shelters/{contentid}.json에 따로 저장해두고, 프론트엔드가
    그 지역 마커를 클릭했을 때만 해당 파일을 불러와 보여준다."""
    groups = {}
    for item in shelter_items:
        title = (item.get('cc_nm') or '').strip()
        addr = (item.get('rn_adres') or item.get('adres') or '').strip()
        raw_x = item.get('x')
        raw_y = item.get('y')
        if not title or not raw_x or not raw_y:
            continue
        try:
            lat, lng = webmercator_to_wgs84(float(raw_x), float(raw_y))
        except (TypeError, ValueError):
            continue

        label = extract_region_label(addr)
        groups.setdefault(label, []).append({'title': title, 'addr': addr, 'lat': lat, 'lng': lng})

    shelter_dir = os.path.join('data', 'shelters')
    os.makedirs(shelter_dir, exist_ok=True)

    clusters = []
    for i, label in enumerate(sorted(groups.keys())):
        members = groups[label]
        content_id = f"shelter-cluster-{i:04d}"
        avg_lat = sum(m['lat'] for m in members) / len(members)
        avg_lng = sum(m['lng'] for m in members) / len(members)

        with open(os.path.join(shelter_dir, f'{content_id}.json'), 'w', encoding='utf-8') as fp:
            json.dump(members, fp, ensure_ascii=False)

        clusters.append({
            'type': 'shelter',
            'title': f"{label} 무더위쉼터 ({len(members)}곳)",
            'lat': avg_lat,
            'lng': avg_lng,
            'startDate': '',
            'endDate': '',
            'addr': label,
            'image': '',
            'tel': '',
            'contentid': content_id,
            'count': len(members)
        })

    print(f"무더위쉼터 {len(shelter_items)}건을 {len(clusters)}개 지역 클러스터로 묶어 data/shelters/에 저장 완료")
    return clusters


def is_heatwave_season(today_str):
    """폭염 대책기간(5.20~9.30) 안인지 판정한다. 이 기간 밖에서는 무더위쉼터를
    아예 수집하지 않는다 — 시즌 지난 정보를 계속 보여주는 것보다, 다음 시즌에
    자동으로 다시 나타나는 편이 안전하다."""
    md = today_str[4:8]  # 'MMDD'
    return '0520' <= md <= '0930'


def addr_matches_region(addr, keywords):
    """주소가 지역 키워드로 '시작'할 때만 그 지역으로 인정한다(festival/index.html의
    addrMatchesRegion과 같은 기준). 도로명·동네 이름에 우연히 들어간 글자는 무시."""
    a = (addr or '').strip()
    return bool(a) and any(a.startswith(kw) for kw in keywords)


def get_region_key(addr):
    """주소로부터 지역 키를 판정한다 (festival/index.html의 필터 로직과 동일한 기준)."""
    for key, keywords in REGION_KEYWORDS:
        if addr_matches_region(addr, keywords):
            return key
    return None


def build_festival_list_page(list_items):
    """지도(JS 마커)는 검색봇이 발견하지 못하는 링크라, 축제·자연관광지 등 상세페이지
    전체를 순수 텍스트 링크 목록으로 모아둔 크롤링 전용 페이지를 만든다.
    지도는 사람용, 이 페이지(festival/list.html)는 검색봇용 목록이다.

    [수정] 예전엔 축제와 자연관광지·캠핑장·수상레저를 지역별로만 묶어서 한 목록에
    섞어놨었는데, 페이지 제목·설명은 "OO월 전국 축제 목록"인데 실제 내용엔 산·계곡·
    캠핑장까지 나와서 "제목과 내용이 안 맞는다"는 지적을 받았다. 이제 카테고리
    (축제 / 자연관광지 / 캠핑장 / 수상레저)로 먼저 나누고, 그 안에서 지역별로
    묶는다. 제목·설명도 실제로 들어있는 카테고리를 다 반영하도록 고쳤다."""
    now = NOW_KST
    month_label = f"{now.year}년 {now.month}월"

    def fmt_date(raw):
        return f"{raw[:4]}.{raw[4:6]}.{raw[6:8]}" if raw and len(raw) == 8 else (raw or '')

    def render_by_region(items):
        by_region = {key: [] for key, _ in REGION_KEYWORDS}
        unclassified = []
        for f in items:
            key = get_region_key(f.get('addr', ''))
            (by_region[key] if key else unclassified).append(f)

        def render_group(label, group_items):
            group_items = sorted(group_items, key=lambda x: x.get('endDate') or '')
            lines = [f'<h3 class="region-heading">{html.escape(label)}</h3>', '<ul class="festival-list">']
            for f in group_items:
                title = html.escape(f.get('title') or '')
                addr = html.escape(f.get('addr') or '')
                start, end = f.get('startDate'), f.get('endDate')
                date_part = f"{fmt_date(start)} ~ {fmt_date(end)} · " if start or end else ''
                content_id = f.get('contentid')
                link = f'/festival/detail/{content_id}.html' if content_id else '#'
                lines.append(f'<li><a href="{link}">{title}</a> — {date_part}{addr}</li>')
            lines.append('</ul>')
            return '\n'.join(lines)

        parts = []
        for key, _ in REGION_KEYWORDS:
            if by_region[key]:
                parts.append(render_group(REGION_LABELS[key], by_region[key]))
        if unclassified:
            parts.append(render_group('기타 지역', unclassified))
        return '\n'.join(parts) if parts else '<p>현재 등록된 정보가 없습니다.</p>'

    # [CHANGE] 2026-11-11: 이 목록은 "진행 중이거나 곧 시작하는" 축제만 보여준다. 예전에는 종료 후 30일(GRACE_DAYS)
    # 지난 축제까지 그대로 담겨 있어 이미 끝난 행사가 노출됐다. 종료일이 오늘(KST)보다 앞이면 목록에서 뺀다.
    festivals = [f for f in list_items
                 if f.get('type') not in ('park', 'camping', 'watersports')
                 and not (f.get('endDate') and str(f.get('endDate')) < TODAY)]
    parks = [f for f in list_items if f.get('type') == 'park']
    campings = [f for f in list_items if f.get('type') == 'camping']
    watersports = [f for f in list_items if f.get('type') == 'watersports']

    sections = ['<h2 class="category-heading">🎪 축제</h2>', render_by_region(festivals)]
    if parks:
        sections += ['<h2 class="category-heading">🌳 자연관광지 (공원·수목원·자연휴양림)</h2>', render_by_region(parks)]
    if campings:
        sections += ['<h2 class="category-heading">🏕️ 캠핑장</h2>', render_by_region(campings)]
    if watersports:
        sections += ['<h2 class="category-heading">🚤 수상레저</h2>', render_by_region(watersports)]
    body = '\n'.join(sections)

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{month_label} 전국 축제·자연관광지 목록 - HOHO PLAY 축제 지도</title>
<meta name="description" content="{month_label} 기준 전국에서 진행 중이거나 예정된 축제, 그리고 상시 이용 가능한 자연관광지·캠핑장·수상레저 정보를 지역별로 모은 전체 목록입니다.">
<link rel="canonical" href="https://hohoplaylab.com/festival/list.html">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7990191075290055" crossorigin="anonymous"></script>
<style>
body{{font-family:'Noto Sans KR',sans-serif;max-width:720px;margin:0 auto;padding:24px 16px;color:#1e293b;line-height:1.7}}
h1{{font-size:1.5rem;font-weight:900}}
.category-heading{{font-size:1.3rem;font-weight:900;margin-top:36px;padding-bottom:8px;border-bottom:3px solid #1e293b}}
.region-heading{{font-size:1.1rem;font-weight:800;margin-top:22px;color:#4f46e5;border-bottom:2px solid #e0e7ff;padding-bottom:6px}}
.festival-list{{list-style:none;padding:0;margin:12px 0}}
.festival-list li{{padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:14px}}
.festival-list a{{color:#1e293b;font-weight:700;text-decoration:none}}
.festival-list a:hover{{color:#4f46e5;text-decoration:underline}}
.back-link{{display:inline-block;margin-top:24px;color:#4f46e5;font-weight:700;text-decoration:none}}
</style>
</head>
<body>
<h1>{month_label} 전국 축제·자연관광지 목록</h1>
<p style="font-size:13px;color:#64748b;margin:4px 0 10px">데이터 기준일 {now.strftime('%Y.%m.%d')} (KST) · 출처: 한국관광공사 TourAPI / 공공데이터포털 · 종료된 행사는 자동으로 빠집니다.</p>
<p>현재 진행 중이거나 곧 시작하는 전국 축제, 그리고 상시 이용 가능한 자연관광지·캠핑장·수상레저 정보를 모았습니다. 지도에서 한눈에 보고 싶다면 <a href="/festival/">축제 지도</a>를 이용해보세요.</p>
{body}
<a class="back-link" href="/festival/">← 지도에서 보기</a>
</body>
</html>"""

    os.makedirs('festival', exist_ok=True)
    with open('festival/list.html', 'w', encoding='utf-8') as fp:
        fp.write(page)
    print(f"festival/list.html 갱신 완료 (축제 {len(festivals)}건 + 자연관광지 {len(parks)}건 + 캠핑장 {len(campings)}건 + 수상레저 {len(watersports)}건)")


def update_sitemap(list_items):
    """sitemap.xml에서 festival/detail/* 및 festival/list.html 항목만 지우고,
    festival/list.html 하나만 다시 채운다. 다른 페이지(홈, 게임, 약관 등) 항목은
    절대 건드리지 않는다.

    [정책 변경] 예전에는 축제·자연관광지 상세페이지 하나하나를 전부 sitemap.xml에
    등록했었다(1,130건 중 1,069건, 전체의 95%). 그런데 이 상세페이지들이 공공데이터
    소개문을 거의 그대로 옮긴 짧은 페이지들이라, "직접 쓴 콘텐츠 몇 개 + 복사한 짧은
    페이지 천 개"로 보여 애드센스 심사에 오히려 마이너스라는 지적을 받았다.
    상세페이지 자체는 그대로 두고(URL로 직접 접근 가능하고 festival/list.html에서
    링크도 걸려있어 검색봇이 링크를 타고 찾아갈 수 있음), sitemap.xml에는 그 목록
    페이지 하나만 등록해서 제출 URL 대비 색인 품질 비율을 정상적으로 되돌린다."""
    import re
    sitemap_path = 'sitemap.xml'
    if not os.path.exists(sitemap_path):
        print("sitemap.xml이 없어 건너뜁니다.")
        return

    with open(sitemap_path, 'r', encoding='utf-8') as fp:
        content = fp.read()

    content = re.sub(
        r'\s*<url>\s*<loc>https://hohoplaylab\.com/festival/(?:detail/[^<]+|list\.html)</loc>.*?</url>',
        '',
        content,
        flags=re.DOTALL
    )

    insertion = (
        '  <url>\n    <loc>https://hohoplaylab.com/festival/list.html</loc>\n'
        '    <changefreq>daily</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
    )
    content = content.replace('</urlset>', insertion + '</urlset>') if '</urlset>' in content \
        else content.rstrip() + '\n' + insertion

    with open(sitemap_path, 'w', encoding='utf-8') as fp:
        fp.write(content)
    print(f"sitemap.xml 갱신 완료 (상세페이지 {len(list_items)}건은 목록 페이지 링크로만 노출, 사이트맵엔 festival/list.html 1건만 등록)")


def pick_region_representatives(today_list):
    """오늘 진행중인 축제 중, 지역별로 마감이 가장 임박한 축제 1개씩을 대표로 뽑는다
    (지역마다 진행중인 축제가 없으면 그 지역은 건너뛰므로 결과는 최대 6개, 보통 5~6개)."""
    reps = []
    for key, keywords in REGION_KEYWORDS:
        in_region = [f for f in today_list if addr_matches_region(f.get('addr'), keywords)]
        if not in_region:
            continue
        in_region.sort(key=lambda f: f['endDate'])
        rep = dict(in_region[0])
        rep['regionKey'] = key
        reps.append(rep)
    return reps


def build_today_html(festivals, today):
    """오늘 진행중인 축제 중 지역별 대표 1곳씩(최대 6곳)을 골라
    festival/index.html의 "전국 전체보기" 기본 화면에 그대로 박아넣을 HTML 텍스트를 만든다.
    (특정 지역을 선택했을 때 보이는 목록은 index.html의 자바스크립트가 festivals.json을
    직접 걸러서 클라이언트에서 렌더링한다 — 여기서는 기본 화면만 담당)"""
    today_list = [
        f for f in festivals
        if f.get('startDate') and f.get('endDate') and f['startDate'] <= today <= f['endDate']
    ]

    top_list = pick_region_representatives(today_list)
    if not top_list:
        # 지역별 대표를 하나도 못 뽑은 경우(데이터가 매우 적을 때)는 마감임박순 상위로 대체
        today_list = sorted(today_list, key=lambda f: f['endDate'])
        top_list = today_list[:5]

    if not top_list:
        return '<li class="today-empty">오늘 진행 중인 축제가 없습니다. 곧 새로운 소식으로 찾아올게요!</li>'

    def fmt_date(raw):
        return f"{raw[:4]}.{raw[4:6]}.{raw[6:8]}" if len(raw) == 8 else raw

    items = []
    for f in top_list:
        title = html.escape(f.get('title') or '')
        addr = html.escape(f.get('addr') or '')
        start = f.get('startDate') or ''
        end = f.get('endDate') or ''
        lat = f.get('lat') or ''
        lng = f.get('lng') or ''
        content_id = f.get('contentid') or ''
        date_label = f"{fmt_date(start)} ~ {fmt_date(end)}"

        overview = fetch_detail_overview(content_id)
        overview = html.escape(overview)
        if len(overview) > 160:
            overview = overview[:160].rstrip() + '…'
        desc_html = f'<p class="today-desc">{overview}</p>' if overview else ''

        region_key = f.get('regionKey')
        region_html = (
            f'<span class="today-region">{html.escape(REGION_LABELS.get(region_key, ""))}</span>'
            if region_key else ''
        )

        link_parts = []
        if content_id:
            link_parts.append(f'<a class="today-map-link" href="/festival/detail/{content_id}.html">상세보기 →</a>')
        if lat and lng:
            map_url = f"https://map.kakao.com/link/map/{quote(f.get('title') or '축제')},{lat},{lng}"
            link_parts.append(
                f'<a class="today-map-link" href="{map_url}" target="_blank" '
                f'rel="noopener" onclick="event.stopPropagation()">지도에서 보기 →</a>'
            )
        links_html = ('<div style="display:flex; gap:12px; margin-top:2px;">' + ''.join(link_parts) + '</div>') if link_parts else ''

        items.append(
            f'<li class="today-item" data-cid="{content_id}" '
            f'onclick="focusFestival({lat}, {lng}); closeTodayPanel();">'
            f'{region_html}'
            f'<strong>{title}</strong>'
            f'<span class="today-date">📅 {date_label}</span>'
            f'<span class="today-addr">📍 {addr}</span>'
            f'{desc_html}'
            f'{links_html}'
            f'</li>'
        )
    return ''.join(items)


def update_map_html(festivals, today):
    """festival/index.html 안의 TODAY_FESTIVALS 표시 구간을 오늘 날짜 기준으로 갱신한다."""
    map_path = os.path.join('festival', 'index.html')
    if not os.path.exists(map_path):
        print(f"{map_path} 없음 — 오늘의 축제 패널 갱신 건너뜀")
        return

    with open(map_path, 'r', encoding='utf-8') as f:
        content = f.read()

    start_marker = '<!-- TODAY_FESTIVALS_START -->'
    end_marker = '<!-- TODAY_FESTIVALS_END -->'
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        print("index.html에서 TODAY_FESTIVALS 마커를 찾지 못해 패널 갱신 건너뜀")
        return

    new_html = build_today_html(festivals, today)
    updated = content[:start_idx + len(start_marker)] + '\n' + new_html + '\n' + content[end_idx:]

    with open(map_path, 'w', encoding='utf-8') as f:
        f.write(updated)

    # [ADD] 2026-11-11: 사이드 패널 하단의 "데이터 기준일"을 이번 실행 시각(KST)으로 바꾼다. 마커가 없으면 건너뛴다.
    try:
        with open(map_path, 'r', encoding='utf-8') as f:
            content2 = f.read()
        a = content2.find('<!-- DATA_UPDATED_START -->')
        b = content2.find('<!-- DATA_UPDATED_END -->')
        if a != -1 and b != -1 and a < b:
            label = NOW_KST.strftime('%Y.%m.%d %H:%M')
            content2 = (content2[:a + len('<!-- DATA_UPDATED_START -->')]
                        + f'데이터 기준일: {label} (KST)' + content2[b:])
            with open(map_path, 'w', encoding='utf-8') as f:
                f.write(content2)
    except Exception as e:
        print(f"데이터 기준일 표시 갱신 건너뜀: {e}")

    print("festival/index.html의 '오늘의 축제' 패널 갱신 완료")


# ── 아이랑 나들이 장소 "지역별 요약" (festival/index.html 안내 글 구간, 크롤러용 정적 텍스트) ──
# [ADD] 2026-10-27: 지도·필터 UI만 있으면 검색봇이 읽을 본문이 부족하다는 지적에 따라, data/kids_places.json 을
# 지역별로 묶어 festival/index.html 의 KIDS_REGION_SUMMARY 마커 사이에 정적 HTML 로 넣는다.
# 장소가 충분한 지역(KIDS_SUMMARY_MIN 곳 이상)은 대표 장소 몇 곳을, 적은 지역은 한 줄로 요약한다.
KIDS_SUMMARY_MIN = 5       # 이 수 이상이면 지역별 상자로 자세히 보여줌
KIDS_SUMMARY_PICK = 4      # 상자당 대표 장소 수
KIDS_REGION_LABELS = [
    # (주소 앞부분 → 표시 이름). 같은 지역의 옛/새 행정명은 한 이름으로 합친다.
    (('서울',), '서울'), (('경기',), '경기도'), (('인천',), '인천'), (('부산',), '부산'), (('대구',), '대구'),
    (('대전',), '대전'), (('울산',), '울산'), (('광주',), '광주'), (('세종',), '세종'), (('강원',), '강원'),
    (('충청북', '충북'), '충청북도'), (('충청남', '충남'), '충청남도'), (('전라북', '전북'), '전라북도'),
    (('전라남', '전남'), '전라남도'), (('경상북', '경북'), '경상북도'), (('경상남', '경남'), '경상남도'), (('제주',), '제주'),
]
KIDS_COST_SHORT = {'완전무료': '무료', '유료(일부 무료 조건 있음)': '일부 무료', '유료': '유료', '확인 필요': '비용 확인 필요'}


def _kids_region_of(addr):
    first = (addr or '').split(' ')[0]
    for prefixes, label in KIDS_REGION_LABELS:
        if any(first.startswith(pf) for pf in prefixes):
            return label
    return None


def build_kids_region_summary_html(places):
    groups = {}
    for pl in places:
        label = _kids_region_of(pl.get('addr', ''))
        if label:
            groups.setdefault(label, []).append(pl)
    total = sum(len(v) for v in groups.values())

    def pick(lst):
        # 소개글이 충실한 장소를 우선하되, 실외 장소가 있으면 한 곳은 꼭 포함해서 실내 일색이 되지 않게 한다.
        ranked = sorted(lst, key=lambda x: (not x.get('hasDetail'), -len(x.get('overview', '') or '')))
        chosen = ranked[:KIDS_SUMMARY_PICK]
        if chosen and not any(c.get('placeType') == '실외' for c in chosen):
            outdoor = [x for x in ranked if x.get('placeType') == '실외']
            if outdoor:
                chosen[-1] = outdoor[0]
        return chosen

    def tag(pl):
        t = KIDS_COST_SHORT.get(pl.get('costTag', ''), '비용 확인 필요')
        return f"{pl.get('placeType', '')} · {t}".strip(' ·')

    def link(pl):
        cid = html.escape(str(pl.get('contentid', '')))
        return f'<a href="/festival/detail/{cid}.html" style="color:#4f46e5; font-weight:700;">{html.escape(pl.get("title", ""))}</a>'

    big = sorted([(k, v) for k, v in groups.items() if len(v) >= KIDS_SUMMARY_MIN], key=lambda kv: -len(kv[1]))
    small = sorted([(k, v) for k, v in groups.items() if len(v) < KIDS_SUMMARY_MIN], key=lambda kv: -len(kv[1]))

    out = []
    out.append(f'<p style="margin:0 0 14px;">운영자가 직접 골라 정리한 아이랑 나들이 장소 {total}곳을 지역별로 묶었습니다. '
               f'지역 이름 옆 숫자는 등록된 장소 수이고, 장소 이름을 누르면 운영시간·요금·위치가 담긴 상세 정보를 볼 수 있습니다. '
               f'장소가 많은 지역은 대표 장소를, 적은 지역은 한 줄로 소개합니다.</p>')
    for label, lst in big:
        indoor = sum(1 for x in lst if x.get('placeType') == '실내')
        outdoor = sum(1 for x in lst if x.get('placeType') == '실외')
        both = sum(1 for x in lst if x.get('placeType') == '실내외')
        free = sum(1 for x in lst if x.get('costTag') == '완전무료')
        out.append('<div style="margin:0 0 12px; padding:14px 16px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px;">')
        out.append(f'<p style="margin:0 0 6px; font-weight:800; color:#1e293b;">{html.escape(label)} ({len(lst)}곳)</p>')
        out.append(f'<p style="margin:0 0 8px; font-size:13px; color:#64748b;">실내 {indoor}곳 · 실외 {outdoor}곳 · 실내외 {both}곳, 완전무료 {free}곳</p>')
        out.append('<ul style="margin:0; padding-left:20px;">')
        for pl in pick(lst):
            desc = (pl.get('desc') or '').strip()
            tail = f' — {html.escape(desc)}' if len(desc) >= 15 else ''   # "무료" 같은 한두 단어짜리 설명은 생략
            out.append(f'<li style="margin-bottom:4px;">{link(pl)} <span style="font-size:13px; color:#64748b;">({html.escape(tag(pl))})</span>{tail}</li>')
        out.append('</ul></div>')
    if small:
        parts = []
        for label, lst in small:
            names = ', '.join(link(x) for x in sorted(lst, key=lambda x: -len(x.get('overview', '') or ''))[:3])
            parts.append(f'<strong>{html.escape(label)}</strong>({len(lst)}곳): {names}')
        out.append('<p style="margin:0 0 14px;"><strong>그 밖의 지역</strong> — 등록된 장소가 아직 많지 않은 지역입니다. ' + ' / '.join(parts) + '</p>')
    return '\n'.join(out)


def update_kids_region_summary():
    """festival/index.html 의 KIDS_REGION_SUMMARY 마커 사이를 data/kids_places.json 기준으로 갱신한다."""
    kids_path = os.path.join('data', 'kids_places.json')
    map_path = os.path.join('festival', 'index.html')
    if not (os.path.exists(kids_path) and os.path.exists(map_path)):
        print('kids_places.json 또는 festival/index.html 없음 — 지역별 요약 갱신 건너뜀')
        return
    with open(kids_path, 'r', encoding='utf-8') as f:
        places = json.load(f)
    with open(map_path, 'r', encoding='utf-8') as f:
        content = f.read()
    start_marker = '<!-- KIDS_REGION_SUMMARY_START -->'
    end_marker = '<!-- KIDS_REGION_SUMMARY_END -->'
    si, ei = content.find(start_marker), content.find(end_marker)
    if si == -1 or ei == -1:
        print('KIDS_REGION_SUMMARY 마커를 찾지 못해 지역별 요약 갱신 건너뜀')
        return
    new_html = build_kids_region_summary_html(places)
    updated = content[:si + len(start_marker)] + '\n' + new_html + '\n' + content[ei:]
    if updated != content:
        with open(map_path, 'w', encoding='utf-8') as f:
            f.write(updated)
    print(f"festival/index.html 지역별 아이랑 장소 요약 갱신 완료 (전체 {len(places)}곳)")


# ── 월드컵 두 페이지의 "후보 현황" (festival/worldcup.html, festival/camping-worldcup.html 안내 글 구간) ──
# [ADD] 2026-10-27: 나들이 월드컵·캠핑장 월드컵 안내 글 안의 후보 수치(장소 수, 유형별, 지역별, 16강 가능 지역)가
# 데이터가 바뀌어도 낡지 않도록, 아래 마커 사이를 data/kids_places.json / data/festivals.json 기준으로 다시 쓴다.
# 마커가 없거나 데이터가 비정상적으로 적으면(수신 실패 등) 건드리지 않고 건너뛴다.
WC_KIDS_START = '<!-- WC_KIDS_STATS_START -->'
WC_KIDS_END = '<!-- WC_KIDS_STATS_END -->'
WC_CAMP_START = '<!-- WC_CAMP_STATS_START -->'
WC_CAMP_END = '<!-- WC_CAMP_STATS_END -->'
CAMP_REGION_LABELS = [
    # camping-worldcup.html 의 REGIONS 와 같은 기준(주소 첫 단어 앞부분 → 표시 이름). 전남·광주는 한 이름으로 묶는다.
    (('경기',), '경기도'), (('강원',), '강원'), (('충청남', '충남'), '충청남도'), (('경상남', '경남'), '경상남도'),
    (('전라북', '전북'), '전라북도'), (('충청북', '충북'), '충청북도'), (('경상북', '경북'), '경상북도'),
    (('전남광주', '전라남', '전남', '광주'), '전남·광주'),
    (('인천',), '인천'), (('대구',), '대구'), (('부산',), '부산'), (('울산',), '울산'), (('제주',), '제주'),
    (('대전',), '대전'), (('서울',), '서울'), (('세종',), '세종'),
]
CAMP_TYPE_WORDS = ('오토캠핑', '글램핑', '카라반')


def _camp_region_of(addr):
    first = (addr or '').split(' ')[0]
    for prefixes, label in CAMP_REGION_LABELS:
        if any(first.startswith(pf) for pf in prefixes):
            return label
    return None


def _wc_region_tiers(counts):
    """지역별 장소 수 → (많은 순 목록, 16강 가능 목록, 8강 가능 목록, 8곳 미만 목록). 동수는 이름순."""
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    t16 = [kv for kv in ordered if kv[1] >= 16]
    t8 = [kv for kv in ordered if 8 <= kv[1] < 16]
    low = [kv for kv in ordered if kv[1] < 8]
    return ordered, t16, t8, low


def _wc_fmt(items, with_count=True):
    if with_count:
        return ', '.join(f'{html.escape(k)} {v}곳' for k, v in items)
    return ', '.join(html.escape(k) for k, _ in items)


def _wc_tier_sentence(t16, t8, low):
    parts = []
    if t16:
        parts.append(f'16강까지 가능한 지역은 {_wc_fmt(t16, False)}')
    if t8:
        parts.append(f'8강까지 가능한 지역은 {_wc_fmt(t8, False)}')
    s = ' '.join(p + '입니다.' for p in parts)
    if low:
        s += (' ' if s else '') + f'{_wc_fmt(low, False)}처럼 후보가 8곳보다 적은 지역은 4강으로 줄거나 대진표를 만들 수 없으니, 그럴 땐 "전국"으로 넓혀 주세요.'
    return s


def build_wc_kids_stats_html(places):
    total = len(places)
    pt, ct, counts = {}, {}, {}
    for pl in places:
        pt[pl.get('placeType', '')] = pt.get(pl.get('placeType', ''), 0) + 1
        ct[pl.get('costTag', '')] = ct.get(pl.get('costTag', ''), 0) + 1
        lb = _kids_region_of(pl.get('addr', ''))
        if lb:
            counts[lb] = counts.get(lb, 0) + 1
    ordered, t16, t8, low = _wc_region_tiers(counts)
    top = ordered[:6]
    p1 = (f'<p>현재 후보로 등록된 아이랑 나들이 장소는 <strong>{total}곳</strong>입니다. 장소 유형은 실내 {pt.get("실내", 0)}곳, '
          f'실외 {pt.get("실외", 0)}곳, 실내외 {pt.get("실내외", 0)}곳이고, 비용은 완전무료 {ct.get("완전무료", 0)}곳, '
          f'일부 무료 조건이 있는 곳 {ct.get("유료(일부 무료 조건 있음)", 0)}곳, 유료 {ct.get("유료", 0)}곳, '
          f'비용 확인이 필요한 곳 {ct.get("확인 필요", 0)}곳입니다. 장소는 운영자가 추가·정리하는 대로 늘어나며, 이 숫자도 함께 갱신됩니다.</p>')
    p2 = (f'<p>지역별로는 {_wc_fmt(top)} 순으로 많습니다. 실내·실외와 비용 조건을 따로 두지 않았을 때 {_wc_tier_sentence(t16, t8, low)} '
          f'조건을 함께 고르면 후보가 더 줄어드니, 대진표가 만들어지지 않는다면 조건부터 넓혀 보세요.</p>')
    return p1 + '\n' + p2


def build_wc_camping_stats_html(camps):
    total = len(camps)
    with_img = sum(1 for c in camps if c.get('image'))
    tc = {w: 0 for w in CAMP_TYPE_WORDS}
    plain = 0
    counts = {}
    for c in camps:
        title = c.get('title', '')
        hit = [w for w in CAMP_TYPE_WORDS if w in title]
        for w in hit:
            tc[w] += 1
        if not hit:
            plain += 1
        lb = _camp_region_of(c.get('addr', ''))
        if lb:
            counts[lb] = counts.get(lb, 0) + 1
    ordered, t16, t8, low = _wc_region_tiers(counts)
    top = ordered[:8]
    p1 = (f'<p>현재 후보로 등록된 캠핑장은 <strong>{total}곳</strong>이고, 그중 {with_img}곳에 사진이 등록돼 있습니다. '
          f'이름 기준 유형은 오토캠핑 {tc["오토캠핑"]}곳, 글램핑 {tc["글램핑"]}곳, 카라반 {tc["카라반"]}곳이고, '
          f'이름에 유형 표시가 없는 일반 캠핑장·야영장이 {plain}곳입니다. 이름에 두 가지 이상이 들어간 곳은 각 유형에 모두 셉니다. '
          f'이 숫자는 데이터가 갱신될 때 함께 바뀝니다.</p>')
    p2 = (f'<p>지역별로는 {_wc_fmt(top)} 순으로 많습니다. 유형을 따로 고르지 않았을 때 {_wc_tier_sentence(t16, t8, low)} '
          f'유형까지 고르면 후보가 줄어듭니다. 예를 들어 카라반은 전국 {tc["카라반"]}곳이라 지역을 좁히면 8강이나 4강으로 줄 수 있어요.</p>')
    return p1 + '\n' + p2


def _replace_between_markers(path, start_marker, end_marker, new_html, label):
    if not os.path.exists(path):
        print(f'{path} 없음 — {label} 갱신 건너뜀')
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    si, ei = content.find(start_marker), content.find(end_marker)
    if si == -1 or ei == -1 or ei < si:
        print(f'{path} 에서 {label} 마커를 찾지 못해 갱신 건너뜀')
        return
    updated = content[:si + len(start_marker)] + '\n' + new_html + '\n' + content[ei:]
    if updated != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(updated)
    print(f'{path} {label} 갱신 완료')


def update_worldcup_stats():
    """나들이 월드컵·캠핑장 월드컵 안내 글의 '후보 현황' 구간을 데이터 기준으로 갱신한다."""
    kids_path = os.path.join('data', 'kids_places.json')
    fest_path = os.path.join('data', 'festivals.json')
    if os.path.exists(kids_path):
        with open(kids_path, 'r', encoding='utf-8') as f:
            places = json.load(f)
        if len(places) >= 20:
            _replace_between_markers(os.path.join('festival', 'worldcup.html'), WC_KIDS_START, WC_KIDS_END,
                                     build_wc_kids_stats_html(places), '나들이 월드컵 후보 현황')
        else:
            print('kids_places.json 장소가 너무 적어 나들이 월드컵 후보 현황 갱신 건너뜀')
    if os.path.exists(fest_path):
        with open(fest_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        camps = [it for it in items if it.get('type') == 'camping' and it.get('title') and it.get('contentid')]
        if len(camps) >= 50:
            _replace_between_markers(os.path.join('festival', 'camping-worldcup.html'), WC_CAMP_START, WC_CAMP_END,
                                     build_wc_camping_stats_html(camps), '캠핑장 월드컵 후보 현황')
        else:
            print('캠핑장 데이터가 너무 적어(수신 실패 의심) 캠핑장 월드컵 후보 현황 갱신 건너뜀')


RL_START = '<!-- RL_STATS_START -->'
RL_END = '<!-- RL_STATS_END -->'


def _forest_kinds(title):
    """roulette.html 의 forestKindsOf 와 같은 기준: 이름에 들어간 말로 숲·수목원·휴양림을 나눈다(해변·해수욕장은 제외)."""
    t = title or ''
    if '해수욕장' in t or '해변' in t:
        return []
    kinds = []
    if '휴양림' in t:
        kinds.append('휴양림')
    if any(w in t for w in ('수목원', '식물원', '정원')):
        kinds.append('수목원·정원')
    if any(w in t for w in ('숲', '산림')):
        kinds.append('숲·산림')
    return kinds


def _rl_region_counts(items):
    counts = {}
    for it in items:
        lb = _camp_region_of(it.get('addr', ''))
        if lb:
            counts[lb] = counts.get(lb, 0) + 1
    return counts


def _rl_tier_paragraph(label, counts):
    """룰렛 칸 수 기준(최대 10칸, 최소 4칸)으로 지역을 나눠 한 문단으로 쓴다."""
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    t10 = [kv for kv in ordered if kv[1] >= 10]
    t8 = [kv for kv in ordered if 8 <= kv[1] < 10]
    t4 = [kv for kv in ordered if 4 <= kv[1] < 8]
    low = [kv for kv in ordered if kv[1] < 4]
    parts = []
    if t10:
        parts.append(f'10칸까지 돌릴 수 있는 지역은 {_wc_fmt(t10, False)}입니다.')
    if t8:
        parts.append(f'후보가 8~9곳이라 칸이 8~9개까지인 지역은 {_wc_fmt(t8, False)}입니다.')
    if t4:
        parts.append(f'후보가 4~7곳이라 칸이 그만큼 줄어드는 지역은 {_wc_fmt(t4, False)}입니다.')
    if low:
        parts.append(f'후보가 4곳보다 적어 룰렛을 만들 수 없는 지역은 {_wc_fmt(low, False)}입니다. 이럴 땐 "전국"으로 넓혀 주세요.')
    return f'<p><strong>{html.escape(label)}</strong> — ' + ' '.join(parts) + '</p>'


def build_roulette_stats_html(kids, camps, forests):
    pt, ct = {}, {}
    for pl in kids:
        pt[pl.get('placeType', '')] = pt.get(pl.get('placeType', ''), 0) + 1
    tc = {w: 0 for w in CAMP_TYPE_WORDS}
    plain = 0
    for c in camps:
        hit = [w for w in CAMP_TYPE_WORDS if w in c.get('title', '')]
        for w in hit:
            tc[w] += 1
        if not hit:
            plain += 1
    kc = {'휴양림': 0, '수목원·정원': 0, '숲·산림': 0}
    for f in forests:
        for k in _forest_kinds(f.get('title', '')):
            kc[k] += 1
    p1 = (f'<p>현재 룰렛 후보는 아이랑 나들이 장소 <strong>{len(kids)}곳</strong>(실내 {pt.get("실내", 0)}곳, 실외 {pt.get("실외", 0)}곳, '
          f'실내외 {pt.get("실내외", 0)}곳), 캠핑장 <strong>{len(camps)}곳</strong>(오토캠핑 {tc["오토캠핑"]}곳, 글램핑 {tc["글램핑"]}곳, '
          f'카라반 {tc["카라반"]}곳, 일반 캠핑장·야영장 {plain}곳), 숲·수목원·휴양림 <strong>{len(forests)}곳</strong>'
          f'(자연휴양림 {kc["휴양림"]}곳, 수목원·식물원·정원 {kc["수목원·정원"]}곳, 숲·산림욕장 {kc["숲·산림"]}곳)입니다. '
          f'이름에 두 가지 이상이 들어간 곳은 각 유형에 모두 세기 때문에 유형별 합이 전체보다 클 수 있고, 이 숫자는 데이터가 갱신될 때 함께 바뀝니다.</p>')
    p2 = _rl_tier_paragraph('아이랑 나들이', _rl_region_counts(kids))
    p3 = _rl_tier_paragraph('캠핑장', _rl_region_counts(camps))
    p4 = _rl_tier_paragraph('숲·수목원·휴양림', _rl_region_counts(forests))
    p5 = '<p>위는 지역만 고르고 다른 조건은 "상관없어요"로 둔 경우입니다. 유형이나 비용, 실내·실외 같은 조건을 더하면 후보가 줄어들고, 비 소식이 있는 지역에서 실외를 뺀 경우에도 줄어듭니다.</p>'
    return '\n'.join([p1, p2, p3, p4, p5])


def update_roulette_stats():
    """룰렛 안내 글의 '후보 현황' 구간을 데이터 기준으로 갱신한다."""
    kids_path = os.path.join('data', 'kids_places.json')
    fest_path = os.path.join('data', 'festivals.json')
    if not (os.path.exists(kids_path) and os.path.exists(fest_path)):
        print('룰렛 후보 현황: 데이터 파일이 없어 갱신 건너뜀')
        return
    with open(kids_path, 'r', encoding='utf-8') as f:
        kids = json.load(f)
    with open(fest_path, 'r', encoding='utf-8') as f:
        items = json.load(f)
    camps = [it for it in items if it.get('type') == 'camping' and it.get('title') and it.get('contentid')]
    forests = [it for it in items if it.get('type') == 'park' and it.get('title') and it.get('contentid') and _forest_kinds(it.get('title', ''))]
    if len(kids) < 20 or len(camps) < 50 or len(forests) < 20:
        print('룰렛 후보 현황: 데이터가 너무 적어(수신 실패 의심) 갱신 건너뜀')
        return
    _replace_between_markers(os.path.join('festival', 'roulette.html'), RL_START, RL_END,
                             build_roulette_stats_html(kids, camps, forests), '룰렛 후보 현황')


def main():
    all_items = fetch_all_items('festival')

    festivals = []
    for item in all_items:
        end_date = item.get('eventenddate', '')
        if end_date and end_date < TODAY:
            continue  # 이미 종료된 축제는 제외

        festivals.append({
            'type': 'festival',
            'title': item.get('title'),
            'lat': item.get('mapy'),
            'lng': item.get('mapx'),
            'startDate': item.get('eventstartdate'),
            'endDate': end_date,
            'addr': item.get('addr1', ''),
            'image': item.get('firstimage', ''),
            'tel': item.get('tel', ''),
            'contentid': item.get('contentid', '')
        })

    # ── 수동 등록 축제 (TourAPI에 없는 것을 직접 추가) ──
    # data/manual_festivals.json에 넣어두면, 자동 수집된 축제와 완전히 동일한 방식으로
    # 지도·목록·상세페이지·사이트맵에 반영된다. endDate가 지나면 다른 축제와 똑같이
    # 자동으로 빠지므로, 한번 등록해두면 따로 지우지 않아도 된다.
    manual_path = os.path.join('data', 'manual_festivals.json')
    if os.path.exists(manual_path):
        with open(manual_path, 'r', encoding='utf-8') as fp:
            manual_list = json.load(fp)
        for m in manual_list:
            end_date = m.get('endDate', '')
            if end_date and end_date < TODAY:
                continue  # 종료된 수동 축제도 자동으로 제외
            entry = {
                'type': 'festival',
                'title': m.get('title'),
                'lat': m.get('lat'),
                'lng': m.get('lng'),
                'startDate': m.get('startDate'),
                'endDate': end_date,
                'addr': m.get('addr', ''),
                'image': m.get('image', ''),
                'tel': m.get('tel', ''),
                'contentid': m.get('contentid'),
                'overview': m.get('overview', ''),
                # 이용요금/주최·주관/프로그램/행사장/홈페이지 — 적어두면 상세페이지에
                # 그대로 표시되고, 비워두면 TourAPI 축제처럼 '정보 없음'으로 나온다.
                'fee': m.get('fee', ''),
                'sponsor1': m.get('sponsor1', ''),
                'sponsor2': m.get('sponsor2', ''),
                'program': m.get('program', ''),
                'eventplace': m.get('eventplace', ''),
                'homepage': m.get('homepage', ''),
                # [ADD] 2026-11-01: 행사 시간대(예: "10:00~17:00"). 적어두면 지도 코스에서 시간 계산에 쓰고, 비우면 "시간 확인 필요"로 표시된다.
                'playTime': m.get('playTime', '')
            }
            festivals.append(entry)
        print(f"수동 등록 축제 {len(manual_list)}건 확인, 이 중 유효 기간 내: {sum(1 for m in manual_list if not m.get('endDate') or m.get('endDate') >= TODAY)}건 반영")

    # ── 자연관광지(수목원·공원·자연휴양림) — 날짜가 없는 상시 개방 장소라
    # startDate/endDate를 비워두고, type:'park'로 표시해 map.html이 기간 필터를
    # 건너뛰고 항상 노출하도록 한다.
    nature_spots = []
    try:
        nature_items = fetch_all_items('nature')
        for item in nature_items:
            nature_spots.append({
                'type': 'park',
                'title': item.get('title'),
                'lat': item.get('mapy'),
                'lng': item.get('mapx'),
                'startDate': '',
                'endDate': '',
                'addr': item.get('addr1', ''),
                'image': item.get('firstimage', ''),
                'tel': item.get('tel', ''),
                'contentid': item.get('contentid', '')
            })
    except Exception as e:
        print(f"자연관광지 수집 실패, 이번 실행에서는 건너뜁니다: {e}")

    # ── 캠핑장(야영장·오토캠핑장) — 자연관광지와 동일하게 상시 개방 장소로 취급.
    # TourAPI contentTypeId=28(레포츠), cat2=A0302(육상레포츠) 중 cat3=A03021700만
    # 콕 집어서, 같은 cat2 안의 골프연습장·스키장·서바이벌게임장 등은 걸러낸다.
    camping_spots = []
    try:
        camping_items = fetch_all_items('camping')
        for item in camping_items:
            camping_spots.append({
                'type': 'camping',
                'title': item.get('title'),
                'lat': item.get('mapy'),
                'lng': item.get('mapx'),
                'startDate': '',
                'endDate': '',
                'addr': item.get('addr1', ''),
                'image': item.get('firstimage', ''),
                'tel': item.get('tel', ''),
                'contentid': item.get('contentid', '')
            })
    except Exception as e:
        print(f"캠핑장 수집 실패, 이번 실행에서는 건너뜁니다: {e}")

    # ── 수상레저(수상스키·래프팅·보트 등) — 위와 동일한 방식.
    # cat2=A0301(수상레포츠) 하나로 충분히 좁혀져서 cat3까지는 지정하지 않았다.
    watersports_spots = []
    try:
        watersports_items = fetch_all_items('watersports')
        for item in watersports_items:
            watersports_spots.append({
                'type': 'watersports',
                'title': item.get('title'),
                'lat': item.get('mapy'),
                'lng': item.get('mapx'),
                'startDate': '',
                'endDate': '',
                'addr': item.get('addr1', ''),
                'image': item.get('firstimage', ''),
                'tel': item.get('tel', ''),
                'contentid': item.get('contentid', '')
            })
    except Exception as e:
        print(f"수상레저 수집 실패, 이번 실행에서는 건너뜁니다: {e}")

    # ── 무더위쉼터 — 폭염 대책기간(5.20~9.30)에만 수집한다.
    # 전국 규모가 9만3천여 곳(2026년 기준)이라 개별 항목을 festivals.json에 그대로
    # 넣을 수 없어(모든 방문자가 페이지 열 때마다 통째로 받아야 함), 지역(시/군/구)
    # 단위로 묶어서 지도에는 클러스터 마커만 찍고 개별 목록은 클릭 시에만
    # data/shelters/{contentid}.json으로 따로 불러오게 한다.
    # 원본 데이터 자체의 갱신주기가 1년이라, 최근에 받아둔 캐시가 있으면 재사용해서
    # 실행 시간과 API 호출량을 아낀다.
    shelters = []
    if is_heatwave_season(TODAY):
        try:
            shelter_items = load_shelter_cache()
            if shelter_items is not None:
                print(f"무더위쉼터 캐시 재사용 ({len(shelter_items)}건, 최근 {SHELTER_CACHE_MAX_AGE_DAYS}일 이내 수집분이라 재수집 생략)")
            else:
                shelter_items = fetch_all_shelter_items_paginated()
                save_shelter_cache(shelter_items)
                print(f"무더위쉼터 신규 수집 완료: {len(shelter_items)}건")
            shelters = build_shelter_clusters(shelter_items)
        except Exception as e:
            print(f"무더위쉼터 수집 실패, 이번 실행에서는 건너뜁니다: {e}")
    else:
        print("폭염 대책기간(5.20~9.30) 밖이라 무더위쉼터는 수집하지 않습니다.")

    all_map_items = festivals + nature_spots + camping_spots + watersports_spots + shelters

    # ── 상세페이지 생성을 JSON 저장보다 먼저 한다 ──
    # 자연관광지·캠핑장·수상레저는 하루 40건씩만 새로 만들어지므로(API 할당량 보호),
    # 아직 상세페이지가 없는 곳도 지도에는 항상 나온다. 그런 곳까지 "상세보기" 버튼을
    # 보여주면 클릭 시 404가 나므로, 실제로 파일이 존재하는지 확인해서 hasDetail로
    # 표시해둔다.
    # 무더위쉼터는 지역 클러스터라 개별 상세페이지 자체가 없음(클릭 시 지역 목록을
    # data/shelters/에서 바로 불러오는 방식이라 hasDetail은 항상 False로 계산됨 — 정상).
    generate_detail_pages(festivals)
    attach_play_times(festivals)  # [ADD] 2026-11-01: 행사 시간대(지도 코스 시간 계산용)
    generate_nature_detail_pages(nature_spots)
    generate_nature_detail_pages(camping_spots, page_label='캠핑장', log_label='캠핑장')
    generate_nature_detail_pages(watersports_spots, page_label='수상레저', log_label='수상레저')
    # [ADD] 위 generate_* 호출들의 "애드센스 코드 보정"은 이번 실행에서 받아온 활성
    # 목록(festivals/nature_spots 등)에 있는 것만 훑는다. 상단 홈 버튼 보정은 이미
    # 종료된 과거 페이지까지 포함해 festival/detail/ 전체를 빠짐없이 훑어야 해서
    # 별도 함수로 한 번 더 돈다 — 1회성 보정이 끝나면(모든 파일이 새 버전이 되면)
    # 이후 실행부터는 OLD_HEADER가 안 남아있어 금방 끝난다.
    patch_existing_detail_pages(festivals)

    detail_dir = os.path.join('festival', 'detail')
    for it in all_map_items:
        cid = it.get('contentid')
        it['hasDetail'] = bool(cid) and os.path.exists(os.path.join(detail_dir, f'{cid}.html'))

    try:
        attach_fee_types(all_map_items)  # [ADD] 2026-11-11: 축제 포스터의 무료/유료 구분용
    except Exception as e:
        print(f"축제 이용요금 구분(feeType) 건너뜀: {e}")

    try:
        # [ADD] 2026-11-11: 행사명의 지역과 개최 주소 지역이 다른 축제에 안내(venueNote)를 붙인다. 지도 카드에 표시됨.
        _vn = compute_venue_notes(all_map_items)
        for it in all_map_items:
            if it.get('type') == 'festival':
                n = _vn.get(str(it.get('contentid')))
                if n:
                    it['venueNote'] = n
                else:
                    it.pop('venueNote', None)
        print(f"행사명-개최지 불일치 안내: {len(_vn)}건")
    except Exception as e:
        print(f"행사명-개최지 불일치 안내 건너뜀: {e}")

    # repo 루트 기준 data/ 폴더에 저장 (workflow가 repo 루트에서 scripts/fetch_data.py로 실행하는 것을 전제)
    os.makedirs('data', exist_ok=True)
    with open('data/festivals.json', 'w', encoding='utf-8') as f:
        json.dump(all_map_items, f, ensure_ascii=False, indent=2)

    print(f"총 수신 {len(all_items)}건, 진행중/예정 축제 {len(festivals)}건 + 자연관광지 {len(nature_spots)}건 + 캠핑장 {len(camping_spots)}건 + 수상레저 {len(watersports_spots)}건 + 무더위쉼터 {len(shelters)}건 data/festivals.json에 저장 완료.")

    update_map_html(all_map_items, TODAY)
    update_kids_region_summary()
    update_worldcup_stats()
    update_roulette_stats()

    # ── 사이트맵 / 크롤러용 목록 페이지 ──────────────────────────────
    # 지도 마커 안의 상세 링크는 JS로 그려져 검색봇이 발견하지 못하므로,
    # 상세페이지 주소를 sitemap.xml에 직접 등록하고 순수 텍스트 목록 페이지도 만든다.
    # 종료된 축제도 곧바로 빼지 않고 GRACE_DAYS일간은 남겨둬서, 이미 색인된 페이지가
    # 갑자기 사라진 것으로 오인되지 않게 한다.
    GRACE_DAYS = 30
    grace_cutoff = (datetime.datetime.now() - datetime.timedelta(days=GRACE_DAYS)).strftime('%Y%m%d')
    sitemap_items = []
    for item in all_items:
        content_id = item.get('contentid', '')
        end_date = item.get('eventenddate', '')
        if not content_id:
            continue
        if end_date and end_date < grace_cutoff:
            continue
        if not os.path.exists(os.path.join('festival', 'detail', f'{content_id}.html')):
            continue  # 상세페이지가 실제로 존재하는 것만 등록
        sitemap_items.append({
            'title': item.get('title'),
            'addr': item.get('addr1', ''),
            'startDate': item.get('eventstartdate'),
            'endDate': end_date,
            'contentid': content_id,
            'type': 'festival',
        })

    # 자연관광지·캠핑장·수상레저는 상시 개방 장소라 기간 제한 없이 상세페이지가
    # 존재하는 것만 그대로 포함 (셋 다 같은 방식으로 처리되어 한 루프로 묶음)
    for spot in nature_spots + camping_spots + watersports_spots:
        content_id = spot.get('contentid', '')
        if not content_id:
            continue
        if not os.path.exists(os.path.join('festival', 'detail', f'{content_id}.html')):
            continue
        sitemap_items.append({
            'title': spot.get('title'),
            'addr': spot.get('addr', ''),
            'startDate': '',
            'endDate': '',
            'contentid': content_id,
            'type': spot.get('type'),  # 'park' / 'camping' / 'watersports' — 목록 페이지에서 카테고리 구분에 씀
        })

    # 수동 등록 축제도 다른 축제와 동일한 유예기간 규칙으로 포함
    if os.path.exists(manual_path):
        for m in manual_list:
            content_id = m.get('contentid', '')
            end_date = m.get('endDate', '')
            if not content_id:
                continue
            if end_date and end_date < grace_cutoff:
                continue
            if not os.path.exists(os.path.join('festival', 'detail', f'{content_id}.html')):
                continue
            sitemap_items.append({
                'title': m.get('title'),
                'addr': m.get('addr', ''),
                'startDate': m.get('startDate'),
                'endDate': end_date,
                'contentid': content_id,
                'type': 'festival',
            })

    # 무더위쉼터는 지역 클러스터라 개별 상세페이지가 없어 사이트맵/크롤러용 목록에는
    # 넣지 않는다(검색엔진이 색인할 개별 페이지 자체가 존재하지 않음).

    build_festival_list_page(sitemap_items)
    update_sitemap(sitemap_items)


if __name__ == '__main__':
    main()
