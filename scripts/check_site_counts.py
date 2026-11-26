#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사이트 수치 일관성 점검 (읽기 전용 — 파일을 고치지 않는다)

실제 데이터(data/kids_places.json, data/festivals.json)에서 "정답 숫자"를 계산하고,
페이지 본문에 글자로 적힌 숫자와 비교해서 어긋난 곳만 목록으로 뽑는다.

사용법 (저장소 루트에서):  python3 scripts/check_site_counts.py [저장소경로]
- 어긋남이 있으면 종료 코드 1, 없으면 0
- 결과는 화면과 data/site_count_report.md 에 같이 남긴다 (--no-report 로 끌 수 있음)
"""
import json
import re
import sys
import collections
from pathlib import Path

ROOT = Path([a for a in sys.argv[1:] if not a.startswith("--")][0]) if [a for a in sys.argv[1:] if not a.startswith("--")] else Path(__file__).resolve().parent.parent
WRITE_REPORT = "--no-report" not in sys.argv

SIDO = {
    "서울특별시": "서울", "서울": "서울", "경기도": "경기", "인천광역시": "인천", "인천": "인천",
    "강원특별자치도": "강원", "강원도": "강원", "대전광역시": "대전", "대전": "대전",
    "세종특별자치시": "세종", "충청북도": "충북", "충청남도": "충남", "대구광역시": "대구", "대구": "대구",
    "경상북도": "경북", "경상남도": "경남", "광주광역시": "광주", "부산광역시": "부산", "부산": "부산",
    "울산광역시": "울산", "제주특별자치도": "제주", "전북특별자치도": "전북", "전라북도": "전북",
    "전라남도": "전남", "전남광주통합특별시": "전남",
}
# 페이지에 쓰인 지역 이름 → 데이터 시·도 이름
PAGE_NAME = {
    "경기도": "경기", "경상북도": "경북", "인천": "인천", "서울": "서울", "부산": "부산", "대구": "대구",
    "충청북도": "충북", "경상남도": "경남", "충청남도": "충남", "대전": "대전", "전라북도": "전북",
    "전라남도": "전남", "강원": "강원", "울산": "울산", "광주": "광주", "세종": "세종", "제주": "제주",
    "경북": "경북", "경기": "경기", "충북": "충북", "충남": "충남", "경남": "경남", "전북": "전북", "전남": "전남", "강원도": "강원",
}

issues = []   # (구분, 파일, 내용)
oks = 0
infos = []


def bad(kind, f, msg):
    issues.append((kind, f, msg))


def ok():
    global oks
    oks += 1


def cmp(kind, f, label, claimed, actual):
    if claimed == actual:
        ok()
    else:
        bad(kind, f, f"{label}: 페이지 {claimed} ↔ 실제 {actual}")


def read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else None


def text_of(html):
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html.replace("&nbsp;", " "))


def sido_of(addr):
    first = (addr or "").split()[0] if (addr or "").split() else ""
    return SIDO.get(first, "?" + first)


# ───────────────────────── 1. 정답 숫자 ─────────────────────────
places_all = json.loads(read("data/kids_places.json"))
places = [p for p in places_all if not p.get("hidden")]
fests = json.loads(read("data/festivals.json"))

N = len(places)
HID = len(places_all) - N
TYPE = collections.Counter(p.get("placeType") for p in places)
COST = collections.Counter(p.get("costTag") if not isinstance(p.get("costTag"), list) else "/".join(p.get("costTag")) for p in places)
BY_SIDO = collections.Counter(sido_of(p.get("addr")) for p in places)
BY_SIDO_TYPE = collections.defaultdict(collections.Counter)
for p in places:
    BY_SIDO_TYPE[sido_of(p.get("addr"))][p.get("placeType")] += 1
camp = [f for f in fests if f.get("type") == "camping"]
CAMP_N = len(camp)
CAMP_IMG = sum(1 for c in camp if c.get("image"))
CAMP_BY = collections.Counter(sido_of(c.get("addr")) for c in camp)

infos.append(f"장소 전체 {len(places_all)}곳, 숨김 {HID}곳, 노출 {N}곳 / 유형 {dict(TYPE)} / 비용태그 {dict(COST)}")
infos.append(f"캠핑장 {CAMP_N}곳(사진 {CAMP_IMG}곳), 전체 축제·공원 등 데이터 {len(fests)}건")
unmapped = [k for k in BY_SIDO if k.startswith("?")]
if any((p.get("addr") or "").startswith("전남광주통합특별시") for p in places):
    infos.append("주소가 '전남광주통합특별시'인 장소는 전남으로 합산해 비교함 (페이지도 전남으로 집계)")
if unmapped:
    infos.append(f"주소 앞머리가 표준 시·도가 아닌 장소 있음: {unmapped} → 지역별 집계에서 따로 세지거나 빠질 수 있음")

# ───────────────────────── 2. 총합 문구 (672곳 / 실내·실외·실내외) ─────────────────────────
for rel in ("festival/index.html", "festival/roulette.html", "festival/worldcup.html", "index.html"):
    h = read(rel)
    if h is None:
        bad("파일", rel, "파일 없음"); continue
    t = text_of(h)
    for m in re.finditer(r"(\d[\d,]*)\s?곳", t):
        pass
    m = re.search(r"장소(?:는)?\s*(\d[\d,]*)\s?곳", t)
    tot = [int(x.replace(",", "")) for x in re.findall(r"나들이 장소(?:는)?\s*(\d[\d,]*)\s?곳", t)]
    for v in tot:
        cmp("총합", rel, "아이랑 나들이 장소 총수", v, N)
    m = re.search(r"실내\s*(\d+)곳,\s*실외\s*(\d+)곳,\s*실내외\s*(\d+)곳", t)
    if m:
        cmp("총합", rel, "실내", int(m.group(1)), TYPE["실내"])
        cmp("총합", rel, "실외", int(m.group(2)), TYPE["실외"])
        cmp("총합", rel, "실내외", int(m.group(3)), TYPE["실내외"])

# worldcup 비용 구성
h = read("festival/worldcup.html")
if h:
    t = text_of(h)
    m = re.search(r"완전무료\s*(\d+)곳,\s*일부 무료[^0-9]*(\d+)곳,\s*유료\s*(\d+)곳,\s*비용 확인이 필요한 곳\s*(\d+)곳", t)
    if m:
        claimed = [int(x) for x in m.groups()]
        if sum(claimed) != N:
            bad("총합", "festival/worldcup.html", f"비용 구성 합계 {sum(claimed)} ≠ 장소 {N} (완전무료 {claimed[0]}, 일부 무료 {claimed[1]}, 유료 {claimed[2]}, 확인필요 {claimed[3]})")
        else:
            ok()
    # 지역별 상위 (서울/부산/인천 ... 순)
    m = re.search(r"지역별로는\s*(.+?)순으로 많", t)
    if m:
        for name, cnt in re.findall(r"([가-힣]+)\s*(\d+)곳", m.group(1)):
            key = PAGE_NAME.get(name)
            if key:
                cmp("지역별", "festival/worldcup.html", f"{name}", int(cnt), BY_SIDO[key])

# tools.html "N곳 넘게" 문구는 하한선이므로 실제가 그 이상인지만 본다
h = read("festival/tools.html")
if h:
    t = text_of(h)
    for label, pat, actual in (
        ("실내 장소", r"실내 장소가\s*(\d+)곳 넘게", TYPE["실내"]),
        ("나들이 장소", r"나들이 장소\s*(\d+)곳 넘게", N),
    ):
        m = re.search(pat, t)
        if m:
            if actual >= int(m.group(1)):
                ok()
            else:
                bad("총합", "festival/tools.html", f"{label} '{m.group(1)}곳 넘게'인데 실제 {actual}곳")
    m = re.search(r"입장료가 없는 곳이\s*(\d+)곳 넘게", t)
    if m:
        free = sum(1 for p in places if p.get("costTag") == "완전무료" or (isinstance(p.get("costTag"), list) and "완전무료" in p.get("costTag")))
        infos.append(f"tools.html '입장료 없는 곳 {m.group(1)}곳 넘게' — 데이터 costTag 완전무료 = {free}곳 (확인용)")

# ───────────────────────── 3. festival/index.html 지역별 한눈에 보기 ─────────────────────────
h = read("festival/index.html")
if h:
    t = text_of(h)
    for name, cnt, a, b, c in re.findall(r"([가-힣]+)\s*\((\d+)곳\)\s*실내\s*(\d+)곳\s*·\s*실외\s*(\d+)곳\s*·\s*실내외\s*(\d+)곳", t):
        key = PAGE_NAME.get(name)
        if not key:
            bad("지역별", "festival/index.html", f"알 수 없는 지역 이름 '{name}'"); continue
        cmp("지역별", "festival/index.html", f"{name} 합계", int(cnt), BY_SIDO[key])
        cmp("지역별", "festival/index.html", f"{name} 실내", int(a), BY_SIDO_TYPE[key]["실내"])
        cmp("지역별", "festival/index.html", f"{name} 실외", int(b), BY_SIDO_TYPE[key]["실외"])
        cmp("지역별", "festival/index.html", f"{name} 실내외", int(c), BY_SIDO_TYPE[key]["실내외"])

# ───────────────────────── 4. 캠핑·숲 숫자 (roulette / camping-worldcup) ─────────────────────────
for rel in ("festival/roulette.html", "festival/camping-worldcup.html"):
    h = read(rel)
    if not h:
        continue
    t = text_of(h)
    m = re.search(r"캠핑장은\s*(\d+)곳\s*이고", t) or re.search(r"캠핑장\s*(\d+)곳\s*\(오토", t)
    if m:
        cmp("캠핑", rel, "캠핑장 총수", int(m.group(1)), CAMP_N)
    m = re.search(r"그중\s*(\d+)곳에 사진", t)
    if m:
        cmp("캠핑", rel, "사진 있는 캠핑장", int(m.group(1)), CAMP_IMG)
    def ctype(c):
        return c.get("title", "")
    tcount = {
        "오토캠핑": sum(1 for c in camp if "오토캠핑" in ctype(c)),
        "글램핑": sum(1 for c in camp if "글램핑" in ctype(c)),
        "카라반": sum(1 for c in camp if "카라반" in ctype(c)),
    }
    for k, v in tcount.items():
        m = re.search(k + r"\s*(\d+)곳", t)
        if m and int(m.group(1)) != v:
            bad("캠핑", rel, f"{k}: 페이지 {m.group(1)} ↔ 데이터(제목에 '{k}' 포함) {v}")
        elif m:
            ok()
    m = re.search(r"지역별로는\s*(.+?)순으로 많", t)
    if m and rel.endswith("camping-worldcup.html"):
        for name, cnt in re.findall(r"([가-힣·]+)\s*(\d+)곳", m.group(1)):
            key = PAGE_NAME.get(name)
            if key:
                cmp("캠핑", rel, f"{name} 캠핑장", int(cnt), CAMP_BY[key])
            elif name == "전남·광주":
                cmp("캠핑", rel, "전남·광주 캠핑장", int(cnt), CAMP_BY["전남"] + CAMP_BY["광주"] + CAMP_BY["광주전남통합"])

# ───────────────────────── 5. 시·도별 실내 장소 페이지 (blog/indoor-kids) ─────────────────────────
REGION_SLUG = {"seoul": "서울", "gyeonggi": "경기", "incheon": "인천", "gangwon": "강원", "daejeon": "대전", "sejong": "세종",
               "chungbuk": "충북", "chungnam": "충남", "daegu": "대구", "gyeongbuk": "경북", "gyeongnam": "경남",
               "gwangju": "광주", "busan": "부산", "ulsan": "울산", "jeju": "제주", "jeonbuk": "전북", "jeonnam": "전남"}
indoor_by = collections.Counter(sido_of(p.get("addr")) for p in places if p.get("placeType") in ("실내", "실내외"))
indoor_by_all = collections.Counter(sido_of(p.get("addr")) for p in places_all if p.get("placeType") in ("실내", "실내외"))
page_total = {}
d = ROOT / "blog/indoor-kids"
if d.exists():
    for f in sorted(d.glob("*.html")):
        slug = f.stem
        if slug == "index":
            continue
        h = f.read_text(encoding="utf-8")
        t = text_of(h)
        m = re.search(r"총\s*(\d+)곳", t)
        key = REGION_SLUG.get(slug)
        if not (m and key):
            continue
        claimed = int(m.group(1))
        page_total[key] = claimed
        rel = f"blog/indoor-kids/{f.name}"
        cards = len(re.findall(r'href="/festival/detail/kids-\d+\.html"', h))
        # 생성 스크립트는 숨김 장소를 거르지 않으므로(노출/숨김 모두 후보) 둘 다 허용
        if claimed not in (indoor_by[key], indoor_by_all[key]):
            bad("실내페이지", rel, f"총 {claimed}곳 ↔ 데이터의 실내·실내외 장소 {indoor_by[key]}곳(숨김 포함 {indoor_by_all[key]}곳) — 페이지 재생성 필요")
        else:
            ok()
        if claimed != indoor_by_all[key] and claimed == indoor_by[key] and HID:
            pass
        if claimed == indoor_by_all[key] and indoor_by_all[key] != indoor_by[key]:
            bad("실내페이지", rel, f"숨김 처리된 장소가 목록에 섞여 있음 (노출 {indoor_by[key]}곳, 페이지 {claimed}곳)")
        # '이용 팁 — N곳 중 M곳 무료' 문구
        m2 = re.search(r"이용 팁\s*—\s*(\d+)\s*곳 중", t)
        if m2 and int(m2.group(1)) != claimed:
            bad("실내페이지", rel, f"이용 팁의 전체 곳수 {m2.group(1)} ≠ 총 {claimed}곳")
h = read("blog/indoor-kids/index.html")
if h:
    t = text_of(h)
    m = re.search(r"전국\s*(\d+)개 시·도,\s*총\s*(\d+)곳", t)
    link_count = len(re.findall(r'href="[^"]*indoor-kids/[a-z]+\.html"', h)) or len(re.findall(r"실내 나들이 장소\s*\d+곳", t))
    cards = re.findall(r"([가-힣]+)\s*실내 나들이 장소\s*(\d+)곳", t)
    if m:
        cmp("실내페이지", "blog/indoor-kids/index.html", "시·도 개수", int(m.group(1)), len(cards))
        cmp("실내페이지", "blog/indoor-kids/index.html", "총 장소 수", int(m.group(2)), sum(indoor_by.values()))
        cmp("실내페이지", "blog/indoor-kids/index.html", "카드 숫자 합계 ↔ 안내 총계", sum(int(c) for _, c in cards), int(m.group(2)))
    for name, c in cards:
        key = PAGE_NAME.get(name)
        if key:
            cmp("실내페이지", "blog/indoor-kids/index.html", f"{name} 카드 숫자", int(c), indoor_by[key])
            if key in page_total and page_total[key] != int(c):
                bad("실내페이지", "blog/indoor-kids/index.html", f"{name}: 목록 카드 {c}곳 ↔ 그 지역 페이지 '총 {page_total[key]}곳'")

# ───────────────────────── 6. 코스 글 (blog/kids-course) ─────────────────────────
course_dir = ROOT / "blog/kids-course"
actual_places = {}
if course_dir.exists():
    for f in sorted(course_dir.glob("*.html")):
        if f.stem == "index":
            continue
        h = f.read_text(encoding="utf-8")
        rel = f"blog/kids-course/{f.name}"
        heads = re.findall(r"<h2[^>]*>\s*(\d+)\.\s*<a href=\"/festival/detail/(kids-\d+)\.html", h)
        n = len(heads)
        actual_places[f.stem] = n
        t = text_of(h)
        m = re.search(r"코스는 모두\s*(\d+)곳", t)
        if m:
            cmp("코스글", rel, "'모두 N곳' ↔ 번호 붙은 장소 수", int(m.group(1)), n)
        m = re.search(r"아이랑 갈만한 곳\s*(\d+)곳", t)
        if m:
            cmp("코스글", rel, "'갈만한 곳 N곳' ↔ 장소 수", int(m.group(1)), n)
        # 번호가 1..n 로 이어지는지
        nums = [int(a) for a, _ in heads]
        if nums and nums != list(range(1, n + 1)):
            bad("코스글", rel, f"장소 번호가 1부터 이어지지 않음: {nums}")
        # 링크된 장소가 실제 존재/숨김 아님
        ids = {p["contentid"] for p in places}
        for _, cid in heads:
            if cid not in ids:
                exists = (ROOT / "festival/detail" / f"{cid}.html").exists()
                why = "숨김 처리된 장소" if cid in {p["contentid"] for p in places_all} else "데이터에서 사라진 장소"
                bad("코스글", rel, f"{cid}: {why}인데 코스 글에 남아 있음 (상세 페이지 파일 {'있음' if exists else '없음 → 링크가 404'})")
    h = read("blog/kids-course/index.html")
    if h:
        t = text_of(h)
        cards = re.findall(r'href="(/blog/kids-course/([a-z\-]+)\.html)"[^>]*>(?:(?!</a>).)*?장소\s*(\d+)곳', h, flags=re.S)
        for _, slug, cnt in cards:
            if slug in actual_places:
                cmp("코스글", "blog/kids-course/index.html", f"{slug} 카드 장소 수", int(cnt), actual_places[slug])
        m = re.search(r"지역\s*(\d+)곳을 소개", t)
        files = len(actual_places)
        if m:
            cmp("코스글", "blog/kids-course/index.html", "'지역 N곳을 소개' ↔ 코스 글 파일 수", int(m.group(1)), files)
        listed = {s for _, s, _ in cards}
        missing = sorted(set(actual_places) - listed)
        if missing:
            bad("코스글", "blog/kids-course/index.html", f"목록에 없는 코스 글: {missing}")
    # 얇은 코스 글: 장소 수가 적은 것
    thin = [f"{k}({v}곳)" for k, v in actual_places.items() if v <= 4]
    if thin:
        infos.append("장소가 4곳 이하인 코스 글(내용이 얇을 수 있음): " + ", ".join(thin))

# ───────────────────────── 7. 상세 페이지 ↔ 장소 데이터 ─────────────────────────
det = ROOT / "festival/detail"
if det.exists():
    kids_files = {f.stem for f in det.glob("kids-*.html") if re.fullmatch(r"kids-\d+", f.stem)}
    ids_vis = {p["contentid"] for p in places}
    ids_all = {p["contentid"] for p in places_all}
    miss = sorted(ids_vis - kids_files)
    extra = sorted(kids_files - ids_all)
    if miss:
        bad("상세페이지", "festival/detail", f"노출 중인데 상세 페이지 없음 {len(miss)}곳: {miss[:8]}")
    else:
        ok()
    if extra:
        sm = read("sitemap.xml") or ""
        noidx = [e for e in extra if "noindex" in (det / f"{e}.html").read_text(encoding="utf-8")[:6000]]
        insm = [e for e in extra if f"{e}.html" in sm]
        msg = f"데이터에 없는 kids 상세 페이지 {len(extra)}개(고아 파일): 사이트맵 포함 {len(insm)}개, noindex {len(noidx)}개 — 예: {extra[:6]}"
        if len(noidx) == len(extra) and not insm:
            infos.append(msg + " (모두 noindex·사이트맵 제외라 문제 없음)")
        else:
            bad("상세페이지", "festival/detail", msg)
    hidden_ids = ids_all - ids_vis
    hid_exist = sorted(hidden_ids & kids_files)
    if hid_exist:
        noidx = [e for e in hid_exist if "noindex" in (det / f"{e}.html").read_text(encoding="utf-8")[:6000]]
        infos.append(f"숨김 장소인데 상세 페이지 파일이 남아 있음 {len(hid_exist)}개: {hid_exist} (noindex {len(noidx)}개)")
    non_kids = [f for f in det.glob("*.html") if not f.stem.startswith("kids-")]
    infos.append(f"상세 페이지 파일: kids {len(kids_files)}개, 축제 등 {len(non_kids)}개 (festivals.json {len(fests)}건)")

# ───────────────────────── 보고서 ─────────────────────────
lines = [f"# 사이트 수치 일관성 점검", "", f"- 일치 확인 {oks}건 / 어긋남 {len(issues)}건", ""]
for s in infos:
    lines.append(f"- ℹ️ {s}")
lines.append("")
by = collections.defaultdict(list)
for k, f, m in issues:
    by[k].append((f, m))
for k in by:
    lines.append(f"## {k} ({len(by[k])})")
    for f, m in by[k]:
        lines.append(f"- `{f}` — {m}")
    lines.append("")
if not issues:
    lines.append("어긋난 숫자가 없습니다.")
out = "\n".join(lines)
print(out)
if WRITE_REPORT:
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data/site_count_report.md").write_text(out + "\n", encoding="utf-8")
sys.exit(1 if issues else 0)
