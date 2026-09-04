import os
import datetime
import json
import time
import html
import requests

TODAY = datetime.datetime.now().strftime('%Y%m%d')
# 30일 전부터 검색해서, 이미 시작했지만 아직 안 끝난 축제도 놓치지 않도록 함
SEARCH_FROM = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

# 주의: 공공데이터포털에서 발급받은 두 키 중 "디코딩(Decoding)" 키를 넣을 것.
# "인코딩(Encoding)" 키를 넣으면 requests가 다시 한 번 인코딩해서 401 오류가 남.
API_KEY = os.environ.get("TOUR_API_KEY", "YOUR_TOUR_API_KEY")
BASE_URL = "https://apis.data.go.kr/B551011/KorService2/searchFestival2"


def fetch_page(page_no, num_of_rows=200, max_retries=3):
    params = {
        'serviceKey': API_KEY,
        'numOfRows': num_of_rows,
        'pageNo': page_no,
        'MobileOS': 'ETC',
        'MobileApp': 'hohoplay',
        '_type': 'json',
        'eventStartDate': SEARCH_FROM,
        'arrange': 'A'
    }

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(BASE_URL, params=params, timeout=20)
            res.raise_for_status()
            break
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError) as e:
            last_error = e
            wait = 5 * attempt
            print(f"연결 실패({attempt}/{max_retries}): {e} — {wait}초 후 재시도")
            if attempt < max_retries:
                time.sleep(wait)
    else:
        raise last_error

    try:
        data = res.json()
    except ValueError:
        # 오류 시 JSON이 아니라 XML 에러 메시지가 오는 경우가 있어 원문을 출력해둠
        print("JSON 파싱 실패. 응답 원문 일부:", res.text[:300])
        raise

    header = data.get('response', {}).get('header', {})
    result_code = header.get('resultCode')
    if result_code not in ('0000', '00'):
        print("API 오류 응답:", header.get('resultMsg'), "| 원문:", res.text[:300])
        return [], 0

    body = data.get('response', {}).get('body', {})
    total_count = int(body.get('totalCount', 0))
    items = body.get('items', {})

    if items == '' or items is None:
        item_list = []
    else:
        item_list = items.get('item', [])
        if isinstance(item_list, dict):  # 결과가 1건뿐이면 dict로 오는 API 특성 대비
            item_list = [item_list]

    return item_list, total_count


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
        date_label = f"{fmt_date(start)} ~ {fmt_date(end)}"
        items.append(
            f'<li class="today-item" onclick="focusFestival({lat}, {lng}); closeTodayPanel();">'
            f'<strong>{title}</strong>'
            f'<span class="today-date">📅 {date_label}</span>'
            f'<span class="today-addr">📍 {addr}</span>'
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
    all_items = []
    page_no = 1
    num_of_rows = 200

    while True:
        item_list, total_count = fetch_page(page_no, num_of_rows)
        all_items.extend(item_list)

        if page_no * num_of_rows >= total_count or not item_list:
            break
        page_no += 1
        time.sleep(0.2)  # 연속 호출 과부하 방지

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
            'tel': item.get('tel', '')
        })

    # repo 루트 기준 data/ 폴더에 저장 (workflow가 repo 루트에서 scripts/fetch_data.py로 실행하는 것을 전제)
    os.makedirs('data', exist_ok=True)
    with open('data/festivals.json', 'w', encoding='utf-8') as f:
        json.dump(festivals, f, ensure_ascii=False, indent=2)

    print(f"총 수신 {len(all_items)}건, 진행중/예정 축제 {len(festivals)}건 data/festivals.json에 저장 완료.")

    update_map_html(festivals, TODAY)


if __name__ == '__main__':
    main()
