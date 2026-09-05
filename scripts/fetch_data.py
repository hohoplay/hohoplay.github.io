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
    """오늘의 축제 카드용으로, 특정 축제의 상세 설명(overview)을 프록시를 통해 받아온다.
    실패해도 전체 파이프라인을 막지 않도록 빈 문자열을 돌려준다."""
    if not content_id:
        return ''

    detail_url = PROXY_URL.rsplit('/', 1)[0] + '/detail'
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(detail_url, params={'contentId': content_id}, timeout=20)
            res.raise_for_status()
            data = res.json()
            if 'error' in data:
                return ''
            return (data.get('overview') or '').strip()
        except Exception as e:
            if attempt < max_retries:
                time.sleep(3)
            else:
                print(f"상세 설명 조회 실패(contentId={content_id}): {e}")
    return ''


def build_today_html(festivals, today):
    """오늘 진행중인 축제 중 5곳을 골라 festival/map.html에 그대로 박아넣을 HTML 텍스트를 만든다."""
    today_list = [
        f for f in festivals
        if f.get('startDate') and f.get('endDate') and f['startDate'] <= today <= f['endDate']
    ]
    today_list.sort(key=lambda f: f['endDate'])  # 마감 임박한 순
    top5 = today_list[:5]

    if not top5:
        return '<li class="today-empty">오늘 진행 중인 축제가 없습니다. 곧 새로운 소식으로 찾아올게요!</li>'

    def fmt_date(raw):
        return f"{raw[:4]}.{raw[4:6]}.{raw[6:8]}" if len(raw) == 8 else raw

    items = []
    for f in top5:
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

        map_link_html = ''
        if lat and lng:
            map_url = f"https://map.kakao.com/link/map/{quote(f.get('title') or '축제')},{lat},{lng}"
            map_link_html = (
                f'<a class="today-map-link" href="{map_url}" target="_blank" '
                f'rel="noopener" onclick="event.stopPropagation()">지도에서 보기 →</a>'
            )

        items.append(
            f'<li class="today-item" onclick="focusFestival({lat}, {lng}); closeTodayPanel();">'
            f'<strong>{title}</strong>'
            f'<span class="today-date">📅 {date_label}</span>'
            f'<span class="today-addr">📍 {addr}</span>'
            f'{desc_html}'
            f'{map_link_html}'
            f'</li>'
        )
    return ''.join(items)


def update_map_html(festivals, today):
    """festival/map.html 안의 TODAY_FESTIVALS 표시 구간을 오늘 날짜 기준으로 갱신한다."""
    map_path = os.path.join('festival', 'map.html')
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
        print("map.html에서 TODAY_FESTIVALS 마커를 찾지 못해 패널 갱신 건너뜀")
        return

    new_html = build_today_html(festivals, today)
    updated = content[:start_idx + len(start_marker)] + '\n' + new_html + '\n' + content[end_idx:]

    with open(map_path, 'w', encoding='utf-8') as f:
        f.write(updated)

    print("festival/map.html의 '오늘의 축제' 패널 갱신 완료")


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

    update_map_html(festivals, TODAY)


if __name__ == '__main__':
    main()
