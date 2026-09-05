import os
import datetime
import json
import time
import html
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


def fetch_all_items(max_retries=3):
    """Vercel 프록시(서울 리전)를 통해 TourAPI 데이터를 한 번에 받아온다."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(PROXY_URL, params={'from': SEARCH_FROM}, timeout=30)
            res.raise_for_status()
            data = res.json()

            if 'error' in data:
                raise RuntimeError(f"프록시 오류 응답: {data['error']}")

            return data.get('items', [])
        except (requests.exceptions.RequestException, RuntimeError, ValueError) as e:
            last_error = e
            wait = 5 * attempt
            print(f"프록시 호출 실패({attempt}/{max_retries}): {e} — {wait}초 후 재시도")
            if attempt < max_retries:
                time.sleep(wait)
    raise last_error


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
<title>{title} - 실시간 전국 축제 지도</title>
<meta name="description" content="{title} | {date_label} | {addr}">
<link rel="icon" href="/favicon.svg">
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
    매일 전체를 다시 만들면 TourAPI 호출만 불필요하게 늘어나기 때문."""
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

        overview = fetch_detail_overview(content_id)
        intro = fetch_intro_fields(content_id)
        page_html = build_detail_page_html(f, overview, intro)
        with open(out_path, 'w', encoding='utf-8') as fp:
            fp.write(page_html)
        new_count += 1
        time.sleep(0.3)  # TourAPI에 과도하게 연속 호출하지 않도록 약간의 간격

    print(f"상세페이지 신규 생성: {new_count}건 (festival/detail/)")


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
    all_items = fetch_all_items()

    festivals = []
    for item in all_items:
        end_date = item.get('eventenddate', '')
        if end_date and end_date < TODAY:
            continue  # 이미 종료된 축제는 제외

        festivals.append({
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

    # repo 루트 기준 data/ 폴더에 저장 (workflow가 repo 루트에서 scripts/fetch_data.py로 실행하는 것을 전제)
    os.makedirs('data', exist_ok=True)
    with open('data/festivals.json', 'w', encoding='utf-8') as f:
        json.dump(festivals, f, ensure_ascii=False, indent=2)

    print(f"총 수신 {len(all_items)}건, 진행중/예정 축제 {len(festivals)}건 data/festivals.json에 저장 완료.")

    generate_detail_pages(festivals)

    update_map_html(festivals, TODAY)


if __name__ == '__main__':
    main()
