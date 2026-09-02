import os
import datetime
import json
import time
import requests

TODAY = datetime.datetime.now().strftime('%Y%m%d')
# 30일 전부터 검색해서, 이미 시작했지만 아직 안 끝난 축제도 놓치지 않도록 함
SEARCH_FROM = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y%m%d')

# 주의: 공공데이터포털에서 발급받은 두 키 중 "디코딩(Decoding)" 키를 넣을 것.
# "인코딩(Encoding)" 키를 넣으면 requests가 다시 한 번 인코딩해서 401 오류가 남.
API_KEY = os.environ.get("TOUR_API_KEY", "YOUR_TOUR_API_KEY")
BASE_URL = "https://apis.data.go.kr/B551011/KorService2/searchFestival2"


def fetch_page(page_no, num_of_rows=200):
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
    res = requests.get(BASE_URL, params=params, timeout=15)
    res.raise_for_status()

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


if __name__ == '__main__':
    main()
