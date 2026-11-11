# -*- coding: utf-8 -*-
"""
kids_places.json의 199개 장소 각각을 TourAPI 키워드 검색(api/kids-image-search.js)으로
조회해서, 매칭되는 공식 관광정보가 있으면 그 사진(firstimage)을 "image" 필드로 채워 넣는다.

사용법:
    python3 scripts/fetch_kids_images.py [kids_places.json 경로]

기본값:
    kids_places.json 경로 = ./data/kids_places.json

필요 조건:
    - api/kids-image-search.js 를 Vercel 프로젝트에 배포하고 TOUR_API_KEY 환경변수를
      설정해둔 상태여야 한다(이 스크립트 혼자서는 TourAPI를 호출할 수 없음).
    - KIDS_IMAGE_PROXY_URL 환경변수로 그 배포 주소를 알려줘야 한다. 예:
        export KIDS_IMAGE_PROXY_URL="https://YOUR-PROJECT.vercel.app/api/kids-image-search"
      (기존 FESTIVAL_PROXY_URL과 같은 Vercel 프로젝트라면 "/api/festivals" 부분만
      "/api/kids-image-search"로 바꾼 주소가 된다.)

동작:
    - 각 장소의 title로 키워드 검색 → 반환된 후보 중 addr1에 우리 addr과 겹치는 지역 키워드
      (시/도, 구/군)가 있는 항목을 우선으로 고르고, 없으면 그냥 첫 번째 후보를 쓴다.
      (완전히 다른 동명 장소의 사진이 잘못 붙는 걸 막기 위한 최소한의 안전장치 — 그래도
      틀린 사진이 들어갈 수 있으니, 실행 후 반드시 결과를 한 번 훑어봐야 한다.)
    - firstimage가 없으면(TourAPI에도 사진이 없는 장소) image 필드를 비워 두고 건너뛴다
      (지어내지 않음 — 사진 없는 곳은 그냥 사진 없이 나간다).
    - 매칭/스킵 내역을 콘솔에 출력하고, 마지막에 요약(매칭 N / 사진 없음 N / 결과 없음 N)을 보여준다.
    - kids_places.json을 바로 덮어쓴다(원본 백업이 필요하면 실행 전 직접 복사해둘 것).

주의:
    - TourAPI에는 같은 이름의 장소가 여러 지역에 있을 수 있어(예: "어린이도서관"), 지역
      매칭이 안 맞으면 엉뚱한 사진이 붙을 수 있다. 실행 후 몇 곳을 직접 확인해보는 것을
      권장한다.
    - 요청 사이에 0.3초씩 쉬어서 TourAPI를 과도하게 연속 호출하지 않도록 했다.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROXY_URL = os.environ.get("KIDS_IMAGE_PROXY_URL", "")

# 주소 문자열에서 지역을 비교하기 위한 아주 단순한 토큰 추출 — "경기도 수원시 팔달구 ..."
# 같은 문자열에서 앞쪽 1~2개 의미 있는 토큰(시/도, 시/군/구)만 뽑아 겹치는지 본다.
REGION_TOKEN_RE = re.compile(r"[가-힣]+(?:특별시|광역시|특별자치시|특별자치도|도|시|군|구)")


def region_tokens(addr: str):
    if not addr:
        return set()
    return set(REGION_TOKEN_RE.findall(addr))


# [2026-11-11] 제목에 이런 말이 들어 있는 TourAPI 항목은(우리 장소 이름에 그 말이 없다면) 사진 후보에서 뺀다.
# 예) "동탄호수공원" 검색 → 공원 안의 장애인화장실 사진이 대표 사진으로 붙던 문제.
BAD_TITLE_WORDS = ("화장실", "주차장", "매표소", "안내소", "관리사무소", "휴게소", "편의점")


def _is_bad_candidate(it, our_title):
    t = it.get("title", "") or ""
    return any((w in t) and (w not in our_title) for w in BAD_TITLE_WORDS)


def pick_best_match(items, our_addr, our_title=""):
    """후보 중 우리 장소와 가장 잘 맞는 항목을 고른다.
    점수: 제목 완전일치 +4 / 제목 포함 +2 / 지역(시·군·구) 겹침 +3 / 사진 있음 +1.
    화장실·주차장 같은 부속시설 항목은 아예 제외한다(전부 제외되면 None → 사진 없이 둔다)."""
    if not items:
        return None
    clean = re.sub(r"\s*\([^)]*\)\s*$", "", our_title or "").strip() or (our_title or "")
    cands = [it for it in items if not _is_bad_candidate(it, our_title or "")]
    if not cands:
        return None
    our_tokens = region_tokens(our_addr)

    def score(it):
        sc = 0
        t = (it.get("title", "") or "").strip()
        if clean and t == clean:
            sc += 4
        elif clean and (clean in t or t in clean):
            sc += 2
        if our_tokens and (region_tokens(it.get("addr1", "")) & our_tokens):
            sc += 3
        if it.get("firstimage") or it.get("firstimage2"):
            sc += 1
        return sc

    best = cands[0]
    best_sc = score(best)
    for it in cands[1:]:
        sc = score(it)
        if sc > best_sc:
            best, best_sc = it, sc
    return best


def search_keyword(keyword, max_retries=3):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(PROXY_URL, params={"keyword": keyword}, timeout=15)
            try:
                data = res.json()
            except ValueError:
                data = None
            if res.ok and isinstance(data, dict) and "error" not in data:
                return data.get("items", [])
            last_error = RuntimeError(
                f"HTTP {res.status_code} - {(data or {}).get('error', res.text[:200])}"
            )
        except requests.exceptions.RequestException as e:
            last_error = e
        if attempt < max_retries:
            time.sleep(2 * attempt)
    print(f"  [실패] '{keyword}' 검색 오류: {last_error}")
    return []


def main():
    if not PROXY_URL:
        print(
            "오류: KIDS_IMAGE_PROXY_URL 환경변수가 설정되어 있지 않습니다.\n"
            "  예) export KIDS_IMAGE_PROXY_URL=\"https://YOUR-PROJECT.vercel.app/api/kids-image-search\""
        )
        sys.exit(1)

    data_path = Path(sys.argv[1]) if len(sys.argv) > 1 else SCRIPT_DIR.parent / "data" / "kids_places.json"
    with open(data_path, "r", encoding="utf-8") as f:
        places = json.load(f)

    matched, no_image, not_found = 0, 0, 0

    for i, p in enumerate(places, 1):
        title = p.get("title", "")
        addr = p.get("addr", "")
        if not title:
            continue

        # 이미 사진이 있으면 다시 조회하지 않는다(재실행해도 API 호출이 중복되지 않도록).
        if p.get("image"):
            continue
        # [2026-11-11] imageBlocked: true 인 장소는 사진을 일부러 비워 둔 곳이다(엉뚱한 사진이 붙던 곳).
        # 다시 돌려도 자동으로 채우지 않는다. 올바른 사진 주소를 알게 되면 "image" 에 직접 적고
        # imageBlocked 는 지워도 된다.
        if p.get("imageBlocked"):
            print(f"[{i}/{len(places)}] {title} — imageBlocked, 건너뜀")
            continue

        print(f"[{i}/{len(places)}] {title} 검색 중...")
        # "(세종)" 같은 지역 구분 괄호가 섞여 있으면 검색이 안 될 수 있어 괄호를 뗀 이름으로 검색.
        clean_title = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip() or title
        items = search_keyword(clean_title)

        if not items:
            print(f"  → TourAPI에 매칭되는 장소 없음")
            not_found += 1
            time.sleep(0.3)
            continue

        best = pick_best_match(items, addr, title)
        image = (best or {}).get("firstimage") or (best or {}).get("firstimage2") or ""

        if image:
            p["image"] = image
            matched += 1
            flag = "" if (best.get("title") or "").strip() == clean_title else "  ← 이름이 달라요, 사진 확인 필요"
            print(f"  → 매칭: {best.get('title')} ({best.get('addr1')}) — 사진 있음{flag}")
        else:
            no_image += 1
            print(f"  → 매칭: {best.get('title') if best else '?'} — 사진 없음, 건너뜀")

        time.sleep(0.3)

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        f"\n완료: 사진 매칭 {matched}개 / TourAPI에는 있지만 사진 없음 {no_image}개 / "
        f"TourAPI에 없음 {not_found}개 (전체 {len(places)}개)"
    )
    print(f"'{data_path}' 에 저장했습니다. 이어서 scripts/generate_kids_detail_pages.py 를 다시 실행하세요.")


if __name__ == "__main__":
    main()
