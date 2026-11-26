#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
아이랑 나들이 "우리 가족 체크" 초안 자동 작성 v2 — 공식 홈페이지 글을 직접 읽어 Gemini로 추려 쓰기 (검색 연동 불필요)

흐름
  1) draft  : data/kids_places.json 의 homepage 주소를 GitHub Actions 에서 직접 열어(이용안내·주차·오시는 길 같은 하위 페이지 포함)
              글을 가져온 뒤, 그 글에 '실제로 적힌 사실'만 Gemini 에게 뽑게 한다.
              결과는 data/kids_notes_draft.json 에 '초안'으로만 저장된다(사이트 영향 없음).
              사람이 보기 쉽게 data/kids_notes_draft_review.md 도 만든다(근거 문장·출처 링크 포함).
  2) promote: 승인한 contentid 만 data/kids_notes.json 으로 옮긴다. 그 뒤 Fetch Kids Place Images(kids-9999)로 반영.
  3) probe  : 모델이 응답하는지 아주 짧게 점검한다.

안전장치
  - Gemini 가 낸 문장마다 '원문 인용'을 같이 받고, 그 인용이 가져온 글 안에 실제로 있는지 코드가 대조한다. 없으면 그 칸은 버린다.
  - 홈페이지가 없거나(또는 인스타·블로그 등) 글을 못 가져오면 그 장소는 비워 둔다.
  - 사이트의 robots.txt 가 막은 주소는 열지 않는다. 호출 사이에 간격을 둔다.
  - 요금 금액·버스 번호·출구 번호·도보 분이 든 문장은 문장째 버린다.
  - 기존 data/kids_notes.json 은 promote 때만, 이미 적힌 칸은 --force 없이는 덮어쓰지 않는다.

환경변수: GEMINI_API_KEY (draft·probe 때 필수)
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACES = ROOT / "data" / "kids_places.json"
NOTES = ROOT / "data" / "kids_notes.json"
DRAFT = ROOT / "data" / "kids_notes_draft.json"
REVIEW = ROOT / "data" / "kids_notes_draft_review.md"

MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash"]
FIELDS = ("access", "rules", "tip")
LABELS = {"access": "주차·교통", "rules": "이용 규칙", "tip": "관람 팁"}
MAX_LEN = 240
SLEEP_SEC = 5
UA = "Mozilla/5.0 (compatible; HohoplayBot/1.0; +https://hohoplaylab.com)"
MAX_SUBPAGES = 4
PAGE_CHARS = 5000
TOTAL_CHARS = 18000
SKIP_HOSTS = ("instagram.com", "facebook.com", "blog.naver.com", "cafe.naver.com", "m.blog.naver.com",
              "youtube.com", "youtu.be", "naver.me", "map.naver.com", "kakao.com", "twitter.com", "x.com")

KST = timezone(timedelta(hours=9))

BANNED = re.compile(
    r"\d[\d,]*\s*원"
    r"|(?:버스|마을버스|간선|지선)\s*\d"
    r"|\d+\s*번\s*출구"
    r"|\d+\s*번\s*(?:버스|노선)"
    r"|도보\s*(?:약\s*)?\d+\s*분"
    r"|걸어서\s*(?:약\s*)?\d+\s*분"
)


def now_kst():
    return datetime.now(KST).strftime("%Y-%m-%d")


def load_json(path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")


# ---------------------------------------------------------------- 홈페이지 주소·가져오기
def usable_homepage(p):
    """homepage 필드에서 http(s) 주소를 꺼낸다. 인스타·블로그 등은 글을 못 읽으니 제외."""
    m = re.search(r"https?://[^\s,;)\]]+", str(p.get("homepage") or ""))
    if not m:
        return ""
    url = m.group(0).rstrip(".")
    host = urllib.parse.urlparse(url).netloc.lower()
    if any(host == h or host.endswith("." + h) for h in SKIP_HOSTS):
        return ""
    return url


class _TextParser(HTMLParser):
    BLOCK = {"p", "div", "li", "br", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table", "ul", "ol", "dd", "dt", "dl"}
    SKIP = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.links = []
        self._skip = 0
        self._href = None
        self._ltxt = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        if tag in self.BLOCK:
            self.parts.append("\n")
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._ltxt = []

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag in self.BLOCK:
            self.parts.append("\n")
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._ltxt).split())))
            self._href = None

    def handle_data(self, data):
        if self._skip:
            return
        self.parts.append(data)
        if self._href is not None:
            self._ltxt.append(data)


def html_to_text(html):
    p = _TextParser()
    try:
        p.feed(html)
    except Exception:
        pass
    lines, prev = [], None
    for ln in "".join(p.parts).splitlines():
        ln = " ".join(ln.split())
        if len(ln) < 2 or ln == prev:
            continue
        lines.append(ln)
        prev = ln
    return "\n".join(lines), p.links


def _decode(raw, header_charset):
    cands = []
    if header_charset:
        cands.append(header_charset)
    m = re.search(rb"charset=[\"']?([\w-]+)", raw[:3000], re.I)
    if m:
        cands.append(m.group(1).decode("ascii", "ignore"))
    cands += ["utf-8", "cp949"]
    for enc in cands:
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "ignore")


_ROBOTS = {}


def allowed_by_robots(url):
    u = urllib.parse.urlparse(url)
    base = f"{u.scheme}://{u.netloc}"
    rp = _ROBOTS.get(base)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=10) as r:
                rp.parse(_decode(r.read(200_000), None).splitlines())
        except Exception:
            rp = None  # robots 를 못 읽으면(없음 등) 허용으로 본다
        _ROBOTS[base] = rp if rp else False
        rp = _ROBOTS[base]
    if rp is False:
        return True
    return rp.can_fetch("HohoplayBot", url) and rp.can_fetch("*", url)


def fetch_html(url, timeout=15):
    if not allowed_by_robots(url):
        return None, "robots 차단"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko,en;q=0.5"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            if ctype and "html" not in ctype:
                return None, f"HTML 아님({ctype[:30]})"
            raw = r.read(1_500_000)
            return _decode(raw, r.headers.get_content_charset()), ""
    except Exception as e:
        return None, str(e)[:80]


LINK_WEIGHTS = (
    (("주차", "교통", "오시는", "찾아오", "길찾기", "위치"), 5),
    (("이용안내", "관람안내", "이용 안내", "관람 안내", "이용규칙", "관람규칙", "유의사항", "이용수칙"), 4),
    (("예약", "FAQ", "자주", "Q&A"), 2),
    (("안내", "이용", "편의", "시설", "규정"), 1),
)
BAD_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip", ".hwp", ".doc", ".docx", ".xls", ".xlsx", ".mp4")


def pick_links(base_url, links):
    host = urllib.parse.urlparse(base_url).netloc.lower().replace("www.", "")
    scored = {}
    for href, text in links:
        if not href or href.startswith(("javascript", "mailto", "tel", "#")):
            continue
        full = urllib.parse.urljoin(base_url, href).split("#")[0]
        pu = urllib.parse.urlparse(full)
        if pu.scheme not in ("http", "https") or pu.netloc.lower().replace("www.", "") != host:
            continue
        if pu.path.lower().endswith(BAD_EXT) or full.rstrip("/") == base_url.rstrip("/"):
            continue
        score = 0
        for keys, w in LINK_WEIGHTS:
            if any(k.lower() in text.lower() for k in keys):
                score += w
        if score and (full not in scored or scored[full] < score):
            scored[full] = score
    return [u for u, _ in sorted(scored.items(), key=lambda kv: -kv[1])[:MAX_SUBPAGES]]


def gather_pages(url):
    """홈페이지 + 안내성 하위 페이지의 글을 모은다. [(url, text)]"""
    pages = []
    html, err = fetch_html(url)
    if not html:
        print(f"  ✖ 홈페이지 열기 실패: {err}")
        return pages
    text, links = html_to_text(html)
    pages.append((url, text[:PAGE_CHARS]))
    for sub in pick_links(url, links):
        time.sleep(1.5)
        h, e = fetch_html(sub)
        if not h:
            print(f"  · 건너뜀 {sub[:70]} ({e})")
            continue
        t, _ = html_to_text(h)
        if len(t) > 30:
            pages.append((sub, t[:PAGE_CHARS]))
    total = 0
    out = []
    for u, t in pages:
        if total + len(t) > TOTAL_CHARS:
            t = t[: max(0, TOTAL_CHARS - total)]
        if t:
            out.append((u, t))
            total += len(t)
    return out


# ---------------------------------------------------------------- 대상 고르기
def is_visible(p):
    return bool(p.get("contentid")) and not p.get("hidden")


def priority(p):
    s = 0
    if usable_homepage(p):
        s += 3
    if p.get("tel"):
        s += 1
    if p.get("hasDetail"):
        s += 1
    s += min(len(p.get("overview") or "") / 300.0, 2)
    return s


def pick_targets(places, notes, draft, ids, count, redo=False):
    by_id = {p["contentid"]: p for p in places if is_visible(p)}
    if ids:
        return [by_id[i] for i in ids if i in by_id]
    cand = []
    for p in by_id.values():
        cid = p["contentid"]
        if cid in notes or not usable_homepage(p):
            continue
        if cid in draft and not redo:
            continue
        cand.append(p)
    cand.sort(key=priority, reverse=True)
    return cand[:count]


# ---------------------------------------------------------------- 프롬프트
def build_prompt(p, pages):
    blocks = "\n\n".join(f"=== 페이지 {i}: {u} ===\n{t}" for i, (u, t) in enumerate(pages, 1))
    return f"""너는 아이 동반 가족을 위한 방문 정보 정리자다. 아래 [가져온 글]에 실제로 적힌 사실만 정리한다.

[장소] {p.get('title')} ({p.get('addr')})

[가져온 글]
{blocks}

[할 일] 아래 3가지를 [가져온 글]에서만 찾아 정리해라.
1) access (주차·교통): 가까운 지하철역 이름, 주차 가능 여부·주차장 이용 안내
2) rules (이용 규칙): 재입장, 음식물 반입, 예약 필요 여부, 연령 제한, 반려동물, 유모차·휠체어
3) tip (관람 팁): 글에 적힌 추천 관람 순서·동선, 소요시간, 쉬어 갈 곳

[규칙]
- 글에 없는 내용은 절대 쓰지 말고 그 항목은 빈 문자열("")로 둔다. 상식이나 추측으로 채우지 않는다.
- 항목마다 근거가 된 원문을 {{항목}}_quote 에 글에서 그대로(고쳐 쓰지 말고) 40~80자 복사해 넣는다. 근거가 없으면 비워 둔다.
- 버스 번호, 주차 요금 금액, 지하철 출구 번호, 도보 몇 분, 입장료, 운영시간은 쓰지 않는다.
- 항목마다 1~2문장, 존댓말(~요), 이모지·마크다운 금지. 글을 베끼지 말고 쉬운 말로 다시 쓴다.
- 글이 오래됐거나 방문 전 확인이 필요해 보이면 문장 끝에 "방문 전 공식 안내 확인이 필요해요"를 붙인다.

[출력] 아래 JSON 한 개만 출력해라.
{{"access": "", "access_quote": "", "rules": "", "rules_quote": "", "tip": "", "tip_quote": ""}}
"""


# ---------------------------------------------------------------- 응답 처리
def extract_json(text):
    t = (text or "").strip().replace("```json", "").replace("```", "").strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except Exception:
        return None


def sanitize(text):
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    if not t:
        return ""
    t = re.sub(r"\*\*|__|`|#+\s", "", t)
    sents = re.split(r"(?<=[.!?요다])\s+", t)
    kept = [s for s in sents if s and not BANNED.search(s)]
    out = " ".join(kept).strip()
    if len(out) > MAX_LEN:
        cut = out[:MAX_LEN]
        k = max(cut.rfind(". "), cut.rfind("요 "), cut.rfind("다 "))
        out = cut[:k + 1].strip() if k > 60 else ""
    return out


def _squash(s):
    return re.sub(r"[\s​·ㆍ…\-–—~,.:;!?\"'“”‘’()\[\]{}<>/|]+", "", str(s or ""))


def quote_in_pages(quote, pages):
    q = _squash(quote)
    if len(q) < 8:
        return False
    return any(q in _squash(t) for _, t in pages)


def is_transient(err):
    msg = str(err).lower()
    if "perday" in msg.replace(" ", "").replace("_", "") or "limit: 0" in msg:
        return False
    code = getattr(err, "code", None)
    if isinstance(code, int):
        return code in (429, 500, 502, 503, 504)
    return any(k in msg for k in ("503", "unavailable", "timed out", "timeout", "429", "resource_exhausted", "overloaded", "connection", "deadline"))


_ERR_SHOWN = set()


def show_err(model, e):
    key = (model, str(getattr(e, "code", "")))
    limit = 600 if key not in _ERR_SHOWN else 120
    _ERR_SHOWN.add(key)
    print(f"  ⚠️ 모델 {model} 실패: {str(e)[:limit]}")


def discover_models(client, tried):
    found = []
    try:
        for m in client.models.list():
            name = (getattr(m, "name", "") or "").replace("models/", "")
            actions = getattr(m, "supported_actions", None) or []
            if "flash" not in name or name in tried or re.match(r"gemini-2\.", name):
                continue
            if any(x in name for x in ("image", "tts", "live", "audio", "embedding", "robotics", "computer", "thinking-exp", "omni")):
                continue
            if actions and "generateContent" not in actions:
                continue
            found.append(name)
    except Exception as e:
        print(f"  ⚠️ 사용 가능 모델 조회 실패: {str(e)[:200]}")
        return []

    def _ver(n):
        m = re.match(r"gemini-(\d+)(?:\.(\d+))?", n)
        return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)
    found.sort(key=lambda n: (("preview" in n) or ("exp" in n), tuple(-x for x in _ver(n)), n))
    return found[:4]


def call_gemini(client, types, prompt):
    cfg = types.GenerateContentConfig(temperature=0.1, max_output_tokens=1500)
    last = None
    models = list(MODELS)
    tried = []
    extra_done = False
    while models:
        model = models.pop(0)
        tried.append(model)
        for n in range(1, 4):
            try:
                resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
                if not (resp.text or "").strip():
                    raise ValueError("빈 응답")
                return model, resp
            except Exception as e:
                last = e
                if is_transient(e) and n < 3:
                    time.sleep(10 if n == 1 else 30)
                    continue
                show_err(model, e)
                break
        if not models and not extra_done:
            extra_done = True
            models = discover_models(client, tried)
    raise RuntimeError(f"모든 모델 실패: {str(last)[:300]}")


def make_entry(p, model, resp, pages):
    data = extract_json(resp.text) or {}
    fields, evidence = {}, {}
    for k in FIELDS:
        txt = sanitize(data.get(k))
        quote = str(data.get(k + "_quote") or "").strip()
        if txt and quote_in_pages(quote, pages):
            fields[k] = txt
            evidence[k] = quote[:160]
        else:
            fields[k] = ""
            if txt:
                print(f"  ✂️ {LABELS[k]}: 원문 인용이 글에서 확인되지 않아 버림")
    unverified = [k for k in FIELDS if not fields[k]]
    return {
        "title": p.get("title"),
        **fields,
        "evidence": evidence,
        "unverified": unverified,
        "sources": [{"title": urllib.parse.urlparse(u).netloc, "url": u} for u, _ in pages],
        "model": model,
        "draftedAt": now_kst(),
        "status": "draft" if any(fields.values()) else "empty",
    }


def empty_entry(p, status, why=""):
    return {"title": p.get("title"), "access": "", "rules": "", "tip": "", "evidence": {}, "unverified": list(FIELDS),
            "sources": [], "model": "", "draftedAt": now_kst(), "status": status, "note": why}


# ---------------------------------------------------------------- 검토용 md
def write_review(draft):
    lines = ["# 우리 가족 체크 초안 (자동 작성 — 승인 전)", "",
             "승인할 장소의 contentid 를 Actions `promote` 입력에 넣으면 kids_notes.json 으로 옮겨져요.",
             "각 문장 아래 '근거'는 공식 홈페이지 원문이에요. 출처 링크를 열어 확인한 뒤 승인하세요.", ""]
    for cid in sorted(draft):
        d = draft[cid]
        if d.get("status") == "promoted":
            continue
        lines.append(f"## {cid} {d.get('title')}  `{d.get('status')}`")
        for k in FIELDS:
            v = d.get(k)
            lines.append(f"- **{LABELS[k]}**: {v if v else '(확인 못 함 — 비워 둠)'}")
            ev = (d.get("evidence") or {}).get(k)
            if v and ev:
                lines.append(f"  - 근거: “{ev}”")
        if d.get("sources"):
            lines.append("- 출처: " + " · ".join(f"[{(s.get('title') or '링크')[:30]}]({s['url']})" for s in d["sources"]))
        if d.get("note"):
            lines.append(f"- 메모: {d['note']}")
        lines.append("")
    REVIEW.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- draft / promote / probe
def make_client(api_key, timeout_ms=120_000):
    from google import genai
    from google.genai import types
    try:
        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version="v1beta", timeout=timeout_ms))
    except Exception:
        client = genai.Client(api_key=api_key)
    return client, types


def run_draft(args):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("❌ GEMINI_API_KEY 환경변수가 없습니다.")
        return 1
    client, types = make_client(api_key)
    places = load_json(PLACES, [])
    notes = load_json(NOTES, {})
    draft = load_json(DRAFT, {})
    ids = [x.strip() for x in (args.ids or "").split(",") if x.strip()]
    targets = pick_targets(places, notes, draft, ids, args.count, redo=args.redo)
    print(f"대상 {len(targets)}곳")
    ok = 0
    gem_fail = 0
    for i, p in enumerate(targets, 1):
        cid = p["contentid"]
        print(f"[{i}/{len(targets)}] {cid} {p.get('title')}")
        url = usable_homepage(p)
        if not url:
            print("  → 글을 읽을 홈페이지가 없어 건너뜀")
            draft[cid] = empty_entry(p, "no_homepage", "홈페이지 없음 또는 SNS·블로그")
            save_json(DRAFT, draft)
            continue
        pages = gather_pages(url)
        if not pages:
            draft[cid] = empty_entry(p, "no_source", "홈페이지 글을 가져오지 못함")
            save_json(DRAFT, draft)
            continue
        print(f"  · 가져온 페이지 {len(pages)}개, 글자 {sum(len(t) for _, t in pages)}")
        try:
            model, resp = call_gemini(client, types, build_prompt(p, pages))
            entry = make_entry(p, model, resp, pages)
        except Exception as e:
            print(f"  ❌ 건너뜀: {str(e)[:160]}")
            gem_fail += 1
            continue
        draft[cid] = entry
        ok += 1
        print(f"  → {entry['status']} (미확인 {entry['unverified']})")
        save_json(DRAFT, draft)
        if i < len(targets):
            time.sleep(SLEEP_SEC)
    save_json(DRAFT, draft)
    write_review(draft)
    print(f"완료: 초안 {ok}곳 / 전체 {len(targets)}곳 (모델 실패 {gem_fail})")
    if targets and ok == 0 and gem_fail:
        print("❌ 모델 호출이 모두 실패했습니다. 위쪽 로그를 확인하세요.")
        return 1
    return 0


def run_probe(args):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("❌ GEMINI_API_KEY 환경변수가 없습니다.")
        return 1
    client, types = make_client(api_key, 60_000)
    names = list(MODELS) + discover_models(client, list(MODELS))
    seen = set()
    for model in names:
        if model in seen:
            continue
        seen.add(model)
        try:
            r = client.models.generate_content(model=model, contents="한국의 수도는? 한 단어로 답해.",
                                               config=types.GenerateContentConfig(temperature=0, max_output_tokens=60))
            print(f"✅ {model}: 성공 → {(r.text or '').strip()[:30]}")
        except Exception as e:
            print(f"❌ {model}: {str(e)[:160]}")
        time.sleep(2)
    return 0


def run_promote(args):
    ids = [x.strip() for x in (args.ids or "").split(",") if x.strip()]
    if not ids:
        print("❌ promote 에는 --ids 가 필요합니다.")
        return 1
    draft = load_json(DRAFT, {})
    notes = load_json(NOTES, {})
    moved = 0
    for cid in ids:
        d = draft.get(cid)
        if not d:
            print(f"  ⚠️ {cid}: 초안 없음")
            continue
        if d.get("status") != "draft":
            print(f"  ⚠️ {cid}: 상태가 {d.get('status')} 라 건너뜀")
            continue
        entry = notes.get(cid, {})
        changed = False
        for k in FIELDS:
            v = (d.get(k) or "").strip()
            if v and (args.force or not str(entry.get(k) or "").strip()):
                entry[k] = v
                changed = True
        if not changed:
            print(f"  ⚠️ {cid}: 옮길 내용 없음")
            continue
        order = ["fitFor", "access", "rules", "tip", "caution", "familyCost"]
        notes[cid] = {k: entry[k] for k in order if k in entry} | {k: v for k, v in entry.items() if k not in order}
        d["status"] = "promoted"
        moved += 1
        print(f"  ✅ {cid} {d.get('title')}")
    save_json(NOTES, notes)
    save_json(DRAFT, draft)
    write_review(draft)
    print(f"완료: {moved}곳 kids_notes.json 반영")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["draft", "promote", "probe"])
    ap.add_argument("--ids", default="")
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.mode == "probe":
        return run_probe(args)
    return run_draft(args) if args.mode == "draft" else run_promote(args)


if __name__ == "__main__":
    sys.exit(main())
