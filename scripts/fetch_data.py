import os
import datetime
import json
import time
import html
import math
from urllib.parse import quote
import requests

TODAY = datetime.datetime.now().strftime('%Y%m%d')
# 30일 전부터 검색해서, 이미 시작했지만 아직 안 끝난 축제도 놓치지 않도록 함
SEARCH_FROM = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

# 서울 리전에서 실행되는 Vercel 프록시 함수 주소.
# GitHub Actions(해외 서버)가 apis.data.go.kr에 직접 접속하면 차단당하는 문제를 피하기 위해
# 한국 위치인 이 프록시를 통해 대신 데이터를 받아온다.
PROXY_URL = os.environ.get("FESTIVAL_PROXY_URL", "https://YOUR-PROJECT.vercel.app/api/festivals")

# map.html의 지역 필터(filterRegion)와 반드시 동일하게 맞춰야 하는 지역 구분.
# 순서가 곧 "전국 전체보기"에서 대표 축제가 나열되는 순서.
REGION_KEYWORDS = [
    ('seoul', ['서울', '인천', '경기']),
    ('gangwon', ['강원']),
    ('chungcheong', ['세종', '대전', '충북', '충남', '충청']),
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
<link rel="icon" href="/favicon.svg">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7990191075290055" crossorigin="anonymous"></script>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, sans-serif; background: #f8fafc; margin: 0; }}
  .detail-wrap {{ max-width: 640px; margin: 0 auto; padding: 24px 20px 60px; }}
  .detail-image {{ width: 100%; border-radius: 14px; margin-bottom: 20px; object-fit: cover; max-height: 320px; }}
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
  <a href="/festival/" class="detail-back">← 지도로 돌아가기</a>
  {image_html}
  <h1 style="font-size:22px; font-weight:800; color:#111; margin-bottom:8px;">{title}</h1>
  <p style="font-size:13px; color:#ff5722; font-weight:700; margin-bottom:20px;">📅 {date_label}</p>

  <div class="detail-card">
    <div class="detail-row"><div class="detail-label">장소</div><div class="detail-value">{addr}{(' · ' + eventplace) if eventplace else ''}</div></div>
    <div class="detail-row"><div class="detail-label">이용요금</div><div class="detail-value">{fee}</div></div>
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
    다만 애드센스 코드처럼 "이미 있는 페이지에도 나중에 새로 추가된 태그"가
    빠져있는 경우, TourAPI를 다시 부르지 않고 그 자리에서 코드만 삽입해 보정한다."""
    detail_dir = os.path.join('festival', 'detail')
    os.makedirs(detail_dir, exist_ok=True)

    ADSENSE_TAG = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7990191075290055" crossorigin="anonymous"></script>'

    new_count = 0
    patched_count = 0
    for f in festivals:
        content_id = f.get('contentid')
        if not content_id:
            continue
        out_path = os.path.join(detail_dir, f'{content_id}.html')
        if os.path.exists(out_path):
            with open(out_path, 'r', encoding='utf-8') as fp:
                existing = fp.read()
            if ADSENSE_TAG not in existing and '</head>' in existing:
                existing = existing.replace('</head>', f'{ADSENSE_TAG}\n</head>')
                with open(out_path, 'w', encoding='utf-8') as fp:
                    fp.write(existing)
                patched_count += 1
            continue  # 애드센스 보정 외에는 이미 생성된 페이지를 건드리지 않음

        overview = f.get('overview')  # 수동 등록 축제는 이미 설명이 주어져 있어 TourAPI를 안 부름
        if overview is None:
            overview = fetch_detail_overview(content_id)
        intro = {} if f.get('overview') is not None else fetch_intro_fields(content_id)
        page_html = build_detail_page_html(f, overview, intro)
        with open(out_path, 'w', encoding='utf-8') as fp:
            fp.write(page_html)
        new_count += 1
        time.sleep(0.3)  # TourAPI에 과도하게 연속 호출하지 않도록 약간의 간격

    print(f"상세페이지 신규 생성: {new_count}건, 애드센스 코드 보정: {patched_count}건 (festival/detail/)")


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
<link rel="icon" href="/favicon.svg">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7990191075290055" crossorigin="anonymous"></script>
<script src="https://cdn.tailwindcss.com"></script>
<style>
body{{font-family:'Noto Sans KR',sans-serif;max-width:640px;margin:0 auto;padding:20px 16px;color:#1e293b}}
.detail-image{{width:100%;border-radius:14px;margin-bottom:16px;object-fit:cover;max-height:320px}}
.detail-row{{margin:6px 0;font-size:14px;color:#475569}}
.detail-link{{display:inline-block;margin-top:14px;color:#059669;font-weight:700;text-decoration:underline}}
.back-link{{display:inline-block;margin-top:24px;color:#059669;font-weight:700;text-decoration:none}}
</style>
</head>
<body>
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
    generate_detail_pages()와 동일한 원칙(이미 있는 페이지는 재생성하지 않고,
    애드센스 코드 누락만 보정)을 따른다.

    max_new: 이번 실행에서 새로 만들 상세페이지 개수 상한. 축제(searchFestival2)와
    이 함수를 쓰는 모든 종류(areaBasedList2+detailCommon2)가 같은 TourAPI 일일
    할당량을 나눠 쓰기 때문에, 첫 실행처럼 한꺼번에 수백 건을 만들려고 하면
    "일일 서비스 요청제한 초과"로 실패한다. 한 번에 조금씩만 만들고 나머지는
    다음 실행(하루 3회)에서 이어서 만들도록 제한한다."""
    detail_dir = os.path.join('festival', 'detail')
    os.makedirs(detail_dir, exist_ok=True)

    ADSENSE_TAG = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7990191075290055" crossorigin="anonymous"></script>'

    new_count = 0
    patched_count = 0
    skipped_for_quota = 0
    for spot in spots:
        content_id = spot.get('contentid')
        if not content_id:
            continue
        out_path = os.path.join(detail_dir, f'{content_id}.html')
        if os.path.exists(out_path):
            with open(out_path, 'r', encoding='utf-8') as fp:
                existing = fp.read()
            if ADSENSE_TAG not in existing and '</head>' in existing:
                existing = existing.replace('</head>', f'{ADSENSE_TAG}\n</head>')
                with open(out_path, 'w', encoding='utf-8') as fp:
                    fp.write(existing)
                patched_count += 1
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
    print(f"{log_label} 상세페이지 신규 생성: {new_count}건, 애드센스 코드 보정: {patched_count}건{remaining_note}")


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


def get_region_key(addr):
    """주소로부터 지역 키를 판정한다 (map.html의 필터 로직과 동일한 기준)."""
    for key, keywords in REGION_KEYWORDS:
        if addr and any(kw in addr for kw in keywords):
            return key
    return None


def build_festival_list_page(list_items):
    """지도(JS 마커)는 검색봇이 발견하지 못하는 링크라, 축제 상세페이지 전체를
    순수 텍스트 링크 목록으로 모아둔 크롤링 전용 페이지를 만든다.
    지도는 사람용, 이 페이지(festival/list.html)는 검색봇용 목록이다."""
    now = datetime.datetime.now()
    month_label = f"{now.year}년 {now.month}월"

    def fmt_date(raw):
        return f"{raw[:4]}.{raw[4:6]}.{raw[6:8]}" if raw and len(raw) == 8 else (raw or '')

    by_region = {key: [] for key, _ in REGION_KEYWORDS}
    unclassified = []
    for f in list_items:
        key = get_region_key(f.get('addr', ''))
        (by_region[key] if key else unclassified).append(f)

    def render_group(label, items):
        items = sorted(items, key=lambda x: x.get('endDate') or '')
        lines = [f'<h2 class="region-heading">{html.escape(label)}</h2>', '<ul class="festival-list">']
        for f in items:
            title = html.escape(f.get('title') or '')
            addr = html.escape(f.get('addr') or '')
            start, end = f.get('startDate'), f.get('endDate')
            date_part = f"{fmt_date(start)} ~ {fmt_date(end)} · " if start or end else ''
            content_id = f.get('contentid')
            link = f'/festival/detail/{content_id}.html' if content_id else '#'
            lines.append(f'<li><a href="{link}">{title}</a> — {date_part}{addr}</li>')
        lines.append('</ul>')
        return '\n'.join(lines)

    sections = []
    for key, _ in REGION_KEYWORDS:
        if by_region[key]:
            sections.append(render_group(REGION_LABELS[key], by_region[key]))
    if unclassified:
        sections.append(render_group('기타 지역', unclassified))
    body = '\n'.join(sections) if sections else '<p>현재 등록된 축제 정보가 없습니다.</p>'

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{month_label} 전국 축제 목록 - HOHO PLAY 축제 지도</title>
<meta name="description" content="{month_label} 기준 전국에서 진행 중이거나 예정된 축제를 지역별로 모은 전체 목록입니다.">
<link rel="canonical" href="https://hohoplaylab.com/festival/list.html">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7990191075290055" crossorigin="anonymous"></script>
<style>
body{{font-family:'Noto Sans KR',sans-serif;max-width:720px;margin:0 auto;padding:24px 16px;color:#1e293b;line-height:1.7}}
h1{{font-size:1.5rem;font-weight:900}}
.region-heading{{font-size:1.1rem;font-weight:800;margin-top:28px;color:#4f46e5;border-bottom:2px solid #e0e7ff;padding-bottom:6px}}
.festival-list{{list-style:none;padding:0;margin:12px 0}}
.festival-list li{{padding:8px 0;border-bottom:1px solid #f1f5f9;font-size:14px}}
.festival-list a{{color:#1e293b;font-weight:700;text-decoration:none}}
.festival-list a:hover{{color:#4f46e5;text-decoration:underline}}
.back-link{{display:inline-block;margin-top:24px;color:#4f46e5;font-weight:700;text-decoration:none}}
</style>
</head>
<body>
<h1>{month_label} 전국 축제 목록</h1>
<p>현재 진행 중이거나 곧 시작하는 전국 축제를 지역별로 모았습니다. 지도에서 한눈에 보고 싶다면 <a href="/festival/">축제 지도</a>를 이용해보세요.</p>
{body}
<a class="back-link" href="/festival/">← 지도에서 보기</a>
</body>
</html>"""

    os.makedirs('festival', exist_ok=True)
    with open('festival/list.html', 'w', encoding='utf-8') as fp:
        fp.write(page)
    print(f"festival/list.html 갱신 완료 (총 {len(list_items)}건 링크)")


def update_sitemap(list_items):
    """sitemap.xml에서 festival/detail/* 및 festival/list.html 항목만 지우고,
    현재 유효한(종료 후 유예기간 이내 포함) 주소로 새로 채운다.
    다른 페이지(홈, 게임, 약관 등) 항목은 절대 건드리지 않는다."""
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

    new_blocks = [
        f'  <url>\n    <loc>https://hohoplaylab.com/festival/detail/{f["contentid"]}.html</loc>\n'
        f'    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>\n'
        for f in list_items if f.get('contentid')
    ]
    new_blocks.append(
        '  <url>\n    <loc>https://hohoplaylab.com/festival/list.html</loc>\n'
        '    <changefreq>daily</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
    )

    insertion = ''.join(new_blocks)
    content = content.replace('</urlset>', insertion + '</urlset>') if '</urlset>' in content \
        else content.rstrip() + '\n' + insertion

    with open(sitemap_path, 'w', encoding='utf-8') as fp:
        fp.write(content)
    print(f"sitemap.xml 갱신 완료 (축제 상세 {len(new_blocks) - 1}건 + 목록페이지 1건)")


def pick_region_representatives(today_list):
    """오늘 진행중인 축제 중, 지역별로 마감이 가장 임박한 축제 1개씩을 대표로 뽑는다
    (지역마다 진행중인 축제가 없으면 그 지역은 건너뛰므로 결과는 최대 6개, 보통 5~6개)."""
    reps = []
    for key, keywords in REGION_KEYWORDS:
        in_region = [f for f in today_list if f.get('addr') and any(kw in f['addr'] for kw in keywords)]
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

    print("festival/index.html의 '오늘의 축제' 패널 갱신 완료")


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
                'overview': m.get('overview', '')
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
    generate_nature_detail_pages(nature_spots)
    generate_nature_detail_pages(camping_spots, page_label='캠핑장', log_label='캠핑장')
    generate_nature_detail_pages(watersports_spots, page_label='수상레저', log_label='수상레저')

    detail_dir = os.path.join('festival', 'detail')
    for it in all_map_items:
        cid = it.get('contentid')
        it['hasDetail'] = bool(cid) and os.path.exists(os.path.join(detail_dir, f'{cid}.html'))

    # repo 루트 기준 data/ 폴더에 저장 (workflow가 repo 루트에서 scripts/fetch_data.py로 실행하는 것을 전제)
    os.makedirs('data', exist_ok=True)
    with open('data/festivals.json', 'w', encoding='utf-8') as f:
        json.dump(all_map_items, f, ensure_ascii=False, indent=2)

    print(f"총 수신 {len(all_items)}건, 진행중/예정 축제 {len(festivals)}건 + 자연관광지 {len(nature_spots)}건 + 캠핑장 {len(camping_spots)}건 + 수상레저 {len(watersports_spots)}건 + 무더위쉼터 {len(shelters)}건 data/festivals.json에 저장 완료.")

    update_map_html(all_map_items, TODAY)

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
            })

    # 무더위쉼터는 지역 클러스터라 개별 상세페이지가 없어 사이트맵/크롤러용 목록에는
    # 넣지 않는다(검색엔진이 색인할 개별 페이지 자체가 존재하지 않음).

    build_festival_list_page(sitemap_items)
    update_sitemap(sitemap_items)


if __name__ == '__main__':
    main()
