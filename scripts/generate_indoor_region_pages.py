# -*- coding: utf-8 -*-
"""
data/kids_places.json의 실내/실내외 장소를 시/도 단위로 모아
"비오는날 아이랑 실내 OOO" 검색 유입용 지역별 목록 페이지를 생성한다.

사용법:
    python3 scripts/generate_indoor_region_pages.py [kids_places.json 경로] [출력 폴더] [sitemap.xml 경로]
    (저장소 루트에서 실행하는 것을 기준으로 함 — data/, blog/, scripts/ 가 모두
    저장소 루트의 형제 폴더인 구조)

기본값(인자 없이 실행 시, 이 스크립트가 <저장소 루트>/scripts/ 안에 있다고 가정):
    kids_places.json 경로 = <저장소 루트>/data/kids_places.json
    출력 폴더            = <저장소 루트>/blog/indoor-kids
    sitemap.xml 경로      = <저장소 루트>/sitemap.xml

하는 일:
    1. kids_places.json에서 placeType이 "실내" 또는 "실내외"인 장소만 추려서
       주소 첫 단어(시/도) 기준으로 묶는다. "강원도"/"강원특별자치도", "대구"/"대구광역시"처럼
       표기가 다른 동일 지역은 REGION_ALIASES로 하나로 합친다.
    2. 데이터가 있는 시/도마다 /blog/indoor-kids/{slug}.html 정적 페이지를 생성한다.
       - "비오는날 아이랑 실내 {지역}" 류의 실제 검색어를 타이틀/설명에 반영
       - 각 장소는 기존 상세페이지(festival/detail/{contentid}.html)로 링크
       - 디자인은 festival/detail/kids-0001.html과 같은 카드 스타일을 재사용
       - festival/kids-course/ 지역(구/군 단위) 페이지와 경로가 겹치지 않도록
         blog/indoor-kids/ 라는 새 폴더를 씀(시/도 단위로 더 넓은 검색어를 노림)
    3. 생성된 페이지 URL을 sitemap.xml에 추가한다(이미 있으면 lastmod만 오늘 날짜로 갱신).
       sitemap-check 워크플로가 blog/ 밖 새 파일만 경고하므로, 이 스크립트가 sitemap도
       직접 갱신해야 새 페이지가 누락 경고 없이 바로 반영된다.

주의:
    - 장소가 바뀔 때마다(실내 태그 수정, 신규 추가) 이 스크립트를 다시 실행하면 전체 지역
      페이지가 다시 생성됩니다(이미 있는 파일도 덮어씀 — 내용이 바뀌었을 수 있으니 항상 전체
      재생성).
    - REGION_SLUGS에 없는 시/도(예: 광주광역시·충청남도 — 이번 데이터에는 없음)는 데이터가
      생겨도 자동으로 매핑되므로 별도 수정 없이 바로 페이지가 생성됩니다.
    - 광고 영역의 data-ad-slot="REPLACE_WITH_AD_SLOT_ID" 는 실제 AdSense 광고 단위 slot
      번호로 꼭 바꿔주세요. 채우지 않으면 광고가 표시되지 않습니다(에러는 안 남).
"""
import json
import re
import sys
from pathlib import Path
from datetime import date

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

SITE_BASE = "https://hohoplaylab.com"

# 주소 첫 토큰이 다르게 표기된 동일 지역을 하나로 합친다
REGION_ALIASES = {
    "강원도": "강원특별자치도",
    "대구": "대구광역시",
}

# 정규화된 지역명 -> (URL 슬러그, 표시용 짧은 이름)
# 기존 /blog/kids-course/ 페이지들의 슬러그(gyeonggi, incheon, busan, sejong, daegu,
# chungbuk, seoul, gangwon, gyeongbuk, daejeon, jeju 등)와 동일한 표기를 그대로 쓴다.
REGION_SLUGS = {
    "서울특별시": ("seoul", "서울"),
    "부산광역시": ("busan", "부산"),
    "대구광역시": ("daegu", "대구"),
    "인천광역시": ("incheon", "인천"),
    "광주광역시": ("gwangju", "광주"),
    "대전광역시": ("daejeon", "대전"),
    "울산광역시": ("ulsan", "울산"),
    "세종특별자치시": ("sejong", "세종"),
    "경기도": ("gyeonggi", "경기"),
    "강원특별자치도": ("gangwon", "강원"),
    "충청북도": ("chungbuk", "충북"),
    "충청남도": ("chungnam", "충남"),
    "전라북도": ("jeonbuk", "전북"),
    "전라남도": ("jeonnam", "전남"),
    "경상북도": ("gyeongbuk", "경북"),
    "경상남도": ("gyeongnam", "경남"),
    "제주특별자치도": ("jeju", "제주"),
}

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="https://hohoplaylab.com/data/banner.png">
<meta name="twitter:card" content="summary">
<link rel="icon" href="/favicon.svg">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7990191075290055" crossorigin="anonymous"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, sans-serif; background: #f8fafc; margin: 0; }}
  .wrap {{ max-width: 640px; margin: 0 auto; padding: 24px 20px 60px; }}
  .back-row {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }}
  .back-link {{ color:#1a73e8; font-weight:700; text-decoration:none; font-size:14px; }}
  .home-link {{ color:#1a73e8; font-weight:700; text-decoration:none; font-size:14px; }}
  .badge {{ display:inline-block; font-size:11px; font-weight:800; color:#1a73e8; background:#eef2ff; padding:4px 10px; border-radius:999px; margin-bottom:10px; }}
  h1 {{ font-size:22px; font-weight:800; color:#111; margin: 0 0 8px; }}
  .intro {{ font-size:14px; color:#475569; line-height:1.7; margin-bottom:20px; }}
  .count-note {{ font-size:13px; color:#94a3b8; margin-bottom:20px; }}
  .place-card {{ background:#fff; border:1px solid #e2e8f0; border-radius:14px; padding:16px 18px; margin-bottom:12px; text-decoration:none; display:block; }}
  .place-name {{ font-size:16px; font-weight:800; color:#111; margin-bottom:6px; }}
  .place-type {{ display:inline-block; font-size:11px; font-weight:700; color:#0ea5e9; background:#f0f9ff; padding:2px 8px; border-radius:999px; margin-bottom:8px; }}
  .place-row {{ font-size:13px; color:#64748b; line-height:1.6; }}
  .place-row b {{ color:#334155; }}
  .place-desc {{ font-size:13px; color:#475569; line-height:1.6; margin-top:8px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="back-row">
    <a href="/festival/" class="back-link">← 나들이 지도로 돌아가기</a>
    <a href="/" class="home-link">🏠 홈</a>
  </div>
  <span class="badge">☔ 비 오는 날에도 OK</span>
  <h1>{h1}</h1>
  <div class="intro">{intro}</div>
  <div class="count-note">총 {count}곳</div>

{place_cards}
  <div style="margin:24px 0; text-align:center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-7990191075290055"
         data-ad-slot="REPLACE_WITH_AD_SLOT_ID"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
  </div>

  <p style="font-size:11px; color:#94a3b8; text-align:center; margin-top:24px; line-height:1.6;">
    위치 정보는 지역 중심 좌표를 기준으로 안내되며, 실제 방문 전 정확한 주소와 운영시간을 확인해주세요.<br>
    정보 출처: 이용자 제보
  </p>
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
        .catch(function () {{ /* 푸터 로드 실패해도 목록페이지 표시엔 영향 없음 */ }});
</script>
</body>
</html>
"""

PLACE_CARD_TEMPLATE = """  <a href="/festival/detail/{contentid}.html" class="place-card">
    <div class="place-name">{title}</div>
    <span class="place-type">{type_label}</span>
    <div class="place-row"><b>장소</b>&nbsp; {addr}</div>
{fee_row}{hours_row}    <div class="place-desc">{desc}</div>
  </a>
"""


def html_escape(s):
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def region_of(addr):
    token = (addr or "").split()[0] if addr else ""
    return REGION_ALIASES.get(token, token)


def type_label_of(place_type):
    return "☔ 실내+야외" if place_type == "실내외" else "☔ 실내"


def build_place_card(p):
    fee = p.get("fee")
    hours = p.get("hours")
    fee_row = (
        f'    <div class="place-row"><b>이용요금</b>&nbsp; {html_escape(fee)}</div>\n' if fee else ""
    )
    hours_row = (
        f'    <div class="place-row"><b>운영시간</b>&nbsp; {html_escape(hours)}</div>\n' if hours else ""
    )
    desc = p.get("desc") or ""
    return PLACE_CARD_TEMPLATE.format(
        contentid=p["contentid"],
        title=html_escape(p.get("title", "")),
        type_label=type_label_of(p.get("placeType")),
        addr=html_escape(p.get("addr", "")),
        fee_row=fee_row,
        hours_row=hours_row,
        desc=html_escape(desc),
    )


def build_page(region_name, places):
    slug, short_name = REGION_SLUGS[region_name]
    places_sorted = sorted(places, key=lambda p: p.get("title", ""))
    cards_html = "".join(build_place_card(p) for p in places_sorted)
    title = f"비오는날 아이랑 실내 {short_name} - 아이랑 나들이 지도 | HOHO PLAY"
    description = (
        f"{short_name} 지역 비 오는 날에도 갈 수 있는 아이랑 실내 나들이 장소 "
        f"{len(places_sorted)}곳을 모았습니다. 주소, 이용요금, 운영시간을 한눈에 확인하세요."
    )
    h1 = f"{short_name} 아이랑 갈만한 실내 나들이 장소"
    intro = (
        f"비 오는 날이나 미세먼지가 심한 날에도 걱정 없이 아이와 함께 갈 수 있는 {short_name}의 "
        f"실내(또는 실내+야외) 나들이 장소를 모았어요. 장소를 누르면 요금·운영시간 등 자세한 정보를 "
        f"볼 수 있습니다."
    )
    canonical = f"{SITE_BASE}/blog/indoor-kids/{slug}.html"
    return canonical, PAGE_TEMPLATE.format(
        title=html_escape(title),
        description=html_escape(description),
        canonical=canonical,
        og_title=html_escape(title),
        h1=html_escape(h1),
        intro=html_escape(intro),
        count=len(places_sorted),
        place_cards=cards_html,
    )


def update_sitemap(sitemap_path, new_urls, today_str):
    if not sitemap_path.exists():
        print(f"경고: {sitemap_path} 가 없어서 sitemap 갱신을 건너뜁니다.")
        return
    content = sitemap_path.read_text(encoding="utf-8")
    for url in new_urls:
        block_pattern = re.compile(
            r"  <url>\s*<loc>" + re.escape(url) + r"</loc>.*?</url>\n",
            re.DOTALL,
        )
        new_block = (
            "  <url>\n"
            f"    <loc>{url}</loc>\n"
            f"    <lastmod>{today_str}</lastmod>\n"
            "    <changefreq>weekly</changefreq>\n"
            "    <priority>0.6</priority>\n"
            "  </url>\n"
        )
        if block_pattern.search(content):
            content = block_pattern.sub(new_block, content)
        else:
            content = content.replace("</urlset>", new_block + "</urlset>")
    sitemap_path.write_text(content, encoding="utf-8", newline="")


def main():
    data_path = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "data" / "kids_places.json"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else REPO_ROOT / "blog" / "indoor-kids"
    sitemap_path = Path(sys.argv[3]) if len(sys.argv) > 3 else REPO_ROOT / "sitemap.xml"

    with open(data_path, "r", encoding="utf-8") as f:
        places = json.load(f)

    grouped = {}
    unmapped_regions = set()
    for p in places:
        if p.get("placeType") not in ("실내", "실내외"):
            continue
        region = region_of(p.get("addr", ""))
        if region not in REGION_SLUGS:
            unmapped_regions.add(region)
            continue
        grouped.setdefault(region, []).append(p)

    out_dir.mkdir(parents=True, exist_ok=True)
    today_str = date.today().isoformat()
    new_urls = []
    written = []
    for region_name, region_places in sorted(grouped.items()):
        canonical, html_out = build_page(region_name, region_places)
        slug = REGION_SLUGS[region_name][0]
        out_path = out_dir / f"{slug}.html"
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            f.write(html_out)
        new_urls.append(canonical)
        written.append((region_name, slug, len(region_places)))

    update_sitemap(sitemap_path, new_urls, today_str)

    print(f"생성 완료: {len(written)}개 지역 페이지")
    for region_name, slug, cnt in written:
        print(f"  - {region_name} -> blog/indoor-kids/{slug}.html ({cnt}곳)")
    if unmapped_regions:
        print(f"매핑 안 된 지역(건너뜀): {sorted(unmapped_regions)}")


if __name__ == "__main__":
    main()
