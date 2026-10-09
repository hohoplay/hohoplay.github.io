# -*- coding: utf-8 -*-
"""
kids_places.json의 각 장소마다 /festival/detail/{contentid}.html 상세페이지를 생성한다.

사용법:
    python3 scripts/generate_kids_detail_pages.py [kids_places.json 경로] [출력 폴더] [템플릿 경로]
    (저장소 루트에서 실행하는 것을 기준으로 함 — data/, templates/, scripts/, festival/detail/
    가 모두 저장소 루트의 형제 폴더인 구조)

기본값(인자 없이 실행 시, 이 스크립트가 <저장소 루트>/scripts/ 안에 있다고 가정):
    kids_places.json 경로 = <저장소 루트>/data/kids_places.json
    출력 폴더            = <저장소 루트>/festival/detail
    템플릿 경로           = <저장소 루트>/templates/kids_detail_template.html

주의:
    - [FIX 2026-10-09] 예전 버전은 기본 경로가 이 스크립트가 있는 폴더(scripts/) 기준으로
      계산되어 있어서, data/·templates/·festival/ 이 scripts/의 형제 폴더인 실제 배포
      구조에서는 파일을 못 찾는 버그가 있었다. 저장소 루트 기준으로 고쳤다.
    - 축제 상세페이지(fetch_data.py가 생성)와 같은 폴더(festival/detail/)를 공유합니다.
      contentid가 서로 겹치지 않아야 합니다(축제는 TourAPI 숫자 contentid, 여기는 "kids-0001"
      형식이라 자연스럽게 안 겹칩니다).
    - 장소를 새로 추가/수정할 때마다 이 스크립트를 다시 실행하면 전체 상세페이지가 다시
      생성됩니다(이미 있는 파일도 덮어씀 — 내용이 바뀌었을 수 있으니 항상 전체 재생성).
    - templates/kids_detail_template.html 을 수정하면 디자인을 바꿀 수 있습니다.
    - [2026-10-09] 축제 상세페이지(fetch_data.py의 build_detail_page_html)와 같은 레이아웃
      (장소/이용요금/운영시간/전화번호/홈페이지 표 + 긴 설명)으로 맞췄다. kids_places.json에
      fee/hours/homepage/overview 필드가 있으면 그대로 쓰고, 없으면 축제 쪽과 동일하게
      "정보 없음"으로 표시한다 — 데이터가 아직 없는 장소도 페이지 생성 자체는 깨지지 않는다.
    - 광고 영역의 data-ad-slot="REPLACE_WITH_AD_SLOT_ID" 는 실제 AdSense 광고 단위 slot
      번호로 꼭 바꿔주세요. 채우지 않으면 광고가 표시되지 않습니다(에러는 안 남).
    - [2026-10-09] kids_places.json에 image 필드(TourAPI 공식 사진 URL)가 있으면 축제
      상세페이지와 동일하게 상단에 사진을 넣는다. image를 채우려면 scripts/fetch_kids_images.py
      를 먼저 실행해야 한다(이 스크립트 혼자서는 사진을 찾아오지 않음) — 없으면 그냥 사진
      영역 없이 생성된다.
"""
import json
import sys
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# [FIX] 2026-10-09: 이 스크립트가 scripts/ 폴더 안에 있을 때(zip으로 전달하는 실제 배포 구조:
# data/, templates/, scripts/, festival/detail/ 가 모두 저장소 루트의 형제 폴더) 과거에는
# 아래 기본 경로들이 SCRIPT_DIR(=scripts/) 기준으로 계산되어 scripts/kids_places.json,
# scripts/templates/... 처럼 실제로는 존재하지 않는 경로를 가리키는 버그가 있었다.
# REPO_ROOT(=scripts/의 부모 폴더, 즉 저장소 루트)를 기준으로 고쳤다 — 인자 없이 실행해도
# 저장소 루트에서 'python scripts/generate_kids_detail_pages.py'로 실행하면 정상 동작한다.
REPO_ROOT = SCRIPT_DIR.parent


def html_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main():
    data_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "data" / "kids_places.json"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO_ROOT / "festival" / "detail"
    template_path = Path(sys.argv[3]) if len(sys.argv) > 3 else REPO_ROOT / "templates" / "kids_detail_template.html"

    with open(data_path, "r", encoding="utf-8") as f:
        places = json.load(f)

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    out_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = []
    for p in places:
        cid = p.get("contentid")
        title = p.get("title", "")
        addr = p.get("addr", "")
        desc = p.get("desc", "")
        tel = p.get("tel")
        fee = p.get("fee")
        hours = p.get("hours")
        homepage = p.get("homepage")
        overview = p.get("overview")
        image = p.get("image")
        lat = p.get("lat")
        lng = p.get("lng")

        if not cid or not title:
            skipped.append(p)
            continue

        canonical_url = f"https://hohoplaylab.com/festival/detail/{cid}.html"
        map_url = (
            "https://map.kakao.com/link/map/"
            + urllib.parse.quote(title)
            + f",{lat},{lng}"
            if lat is not None and lng is not None
            else "https://map.kakao.com/link/search/" + urllib.parse.quote(f"{addr} {title}")
        )
        map_link = (
            f'<a href="{map_url}" target="_blank" rel="noopener" class="detail-link">지도에서 보기 →</a>'
        )

        tel_value = html_escape(tel) if tel else "정보 없음"
        if tel:
            tel_value = f'<a href="tel:{html_escape(tel)}" class="detail-link">{html_escape(tel)}</a>'

        if homepage:
            # TourAPI 쪽(eventhomepage)은 <a href="...">...</a> HTML 문자열을 그대로 내려주는
            # 경우가 많아 그 모양을 맞춘다 — 순수 URL 문자열이면 링크로 감싸고, 이미 <a>가
            # 포함된 문자열(사용자가 그렇게 입력한 경우)이면 그대로 둔다.
            if "<a " in homepage.lower():
                homepage_value = homepage
            else:
                safe_href = html_escape(homepage)
                homepage_value = f'<a href="{safe_href}" target="_blank" rel="noopener" class="detail-link">{safe_href}</a>'
        else:
            homepage_value = "정보 없음"

        overview_text = overview or desc
        overview_html = html_escape(overview_text) if overview_text else "설명 정보가 없습니다."

        # [ADD] TourAPI 키워드 검색(scripts/fetch_kids_images.py)으로 받아온 공식 사진이
        # 있으면 축제 상세페이지와 똑같은 모양(.detail-image)으로 넣고, 없으면 그 자리를
        # 통째로 비워 레이아웃이 깨지지 않게 한다 — fetch_data.py의 image_html 처리와 동일한 방식.
        image_html = (
            f'<img src="{html_escape(image)}" alt="{html_escape(title)}" class="detail-image">'
            if image
            else ""
        )

        html_out = (
            template.replace("{{TITLE}}", html_escape(title))
            .replace("{{ADDR}}", html_escape(addr))
            .replace("{{FEE}}", html_escape(fee) if fee else "정보 없음")
            .replace("{{HOURS}}", html_escape(hours) if hours else "정보 없음")
            .replace("{{TEL_VALUE}}", tel_value)
            .replace("{{HOMEPAGE_VALUE}}", homepage_value)
            .replace("{{OVERVIEW}}", overview_html)
            .replace("{{MAP_LINK}}", map_link)
            .replace("{{DESC}}", html_escape(desc))
            .replace("{{CANONICAL_URL}}", canonical_url)
            .replace("{{IMAGE_HTML}}", image_html)
        )

        out_path = out_dir / f"{cid}.html"
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            f.write(html_out)
        written += 1

    print(f"생성 완료: {written}개")
    if skipped:
        print(f"건너뜀(contentid/title 누락): {len(skipped)}개")


if __name__ == "__main__":
    main()
