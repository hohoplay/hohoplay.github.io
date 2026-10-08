# -*- coding: utf-8 -*-
"""
kids_places.json의 각 장소마다 /festival/detail/{contentid}.html 상세페이지를 생성한다.

사용법:
    python3 generate_kids_detail_pages.py [kids_places.json 경로] [출력 폴더]

기본값:
    kids_places.json 경로 = ./kids_places.json
    출력 폴더            = ./festival/detail

주의:
    - 축제 상세페이지(fetch_data.py가 생성)와 같은 폴더(festival/detail/)를 공유합니다.
      contentid가 서로 겹치지 않아야 합니다(축제는 TourAPI 숫자 contentid, 여기는 "kids-0001"
      형식이라 자연스럽게 안 겹칩니다).
    - 장소를 새로 추가/수정할 때마다 이 스크립트를 다시 실행하면 전체 상세페이지가 다시
      생성됩니다(이미 있는 파일도 덮어씀 — 내용이 바뀌었을 수 있으니 항상 전체 재생성).
    - templates/kids_detail_template.html 을 수정하면 디자인을 바꿀 수 있습니다.
    - 광고 영역의 data-ad-slot="REPLACE_WITH_AD_SLOT_ID" 는 실제 AdSense 광고 단위 slot
      번호로 꼭 바꿔주세요. 채우지 않으면 광고가 표시되지 않습니다(에러는 안 남).
"""
import json
import sys
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def html_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def main():
    data_path = Path(sys.argv[1]) if len(sys.argv) > 1 else SCRIPT_DIR / "kids_places.json"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else SCRIPT_DIR / "festival" / "detail"
    template_path = SCRIPT_DIR / "templates" / "kids_detail_template.html"

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

        if tel:
            tel_block = (
                '<p class="tel">📞 <a href="tel:'
                + html_escape(tel)
                + '">'
                + html_escape(tel)
                + "</a></p>"
            )
        else:
            tel_block = ""

        html_out = (
            template.replace("{{TITLE}}", html_escape(title))
            .replace("{{ADDR}}", html_escape(addr))
            .replace("{{TEL_BLOCK}}", tel_block)
            .replace("{{DESC}}", html_escape(desc))
            .replace("{{CANONICAL_URL}}", canonical_url)
            .replace("{{MAP_URL}}", map_url)
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
