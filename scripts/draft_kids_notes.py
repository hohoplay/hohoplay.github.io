#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
아이랑 나들이 "우리 가족 체크" 초안 자동 작성 (Gemini + 구글 검색 연동)

흐름
  1) draft  : data/kids_places.json 에서 아직 카드가 없는 장소를 골라 Gemini(구글 검색 연동)에 물어보고
              data/kids_notes_draft.json 에 '초안'으로만 저장한다. 사이트에는 아무 영향이 없다.
              같은 내용을 사람이 훑어볼 수 있게 data/kids_notes_draft_review.md 도 만든다.
  2) promote: 대표님이 골라 승인한 contentid 만 data/kids_notes.json 으로 옮긴다(주차·교통 / 이용 규칙 / 관람 팁).
              그 뒤 Fetch Kids Place Images(kids-9999)를 돌리면 사이트에 반영된다.

안전장치
  - 구글 검색에서 실제로 가져온 출처(URL)가 하나도 없으면 그 장소는 내용을 비워 'no_source'로 둔다.
  - 요금 금액, 버스 번호, 출구 번호, 도보 몇 분 같은 자주 바뀌는 수치는 문장째 버린다.
  - 확인 안 된 항목은 모델이 비워 두도록 하고, 비어 있으면 카드에 그 행이 나오지 않는다.
  - 기존 data/kids_notes.json 은 promote 때만, 그리고 이미 적힌 칸은 덮어쓰지 않고(--force 없이는) 건드리지 않는다.

환경변수: GEMINI_API_KEY (필수, draft 때만)
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACES = ROOT / "data" / "kids_places.json"
NOTES = ROOT / "data" / "kids_notes.json"
DRAFT = ROOT / "data" / "kids_notes_draft.json"
REVIEW = ROOT / "data" / "kids_notes_draft_review.md"

MODELS = ["gemini-3.1-flash-lite", "gemini-3-flash", "gemini-flash-latest"]
FIELDS = ("access", "rules", "tip")
LABELS = {"access": "주차·교통", "rules": "이용 규칙", "tip": "관람 팁"}
MAX_LEN = 240
SLEEP_SEC = 6  # 호출 사이 간격(쿼터 보호)

KST = timezone(timedelta(hours=9))

# 자주 바뀌거나 단정하기 어려운 수치가 든 문장은 버린다.
BANNED = re.compile(
    r"\d[\d,]*\s*원"            # 요금 금액
    r"|(?:버스|마을버스|간선|지선)\s*\d"  # 버스 번호
    r"|\d+\s*번\s*출구"          # 출구 번호
    r"|\d+\s*번\s*(?:버스|노선)"
    r"|도보\s*(?:약\s*)?\d+\s*분"  # 도보 분
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


# ---------------------------------------------------------------- 대상 고르기
def is_visible(p):
    return bool(p.get("contentid")) and not p.get("hidden")


def priority(p):
    s = 0
    if p.get("homepage"):
        s += 2
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
        if cid in notes:
            continue
        if cid in draft and not redo:
            continue
        cand.append(p)
    cand.sort(key=priority, reverse=True)
    return cand[:count]


# ---------------------------------------------------------------- 프롬프트
def build_prompt(p):
    known = []
    for label, key in (("이용요금", "fee"), ("운영시간", "hours"), ("전화", "tel"), ("홈페이지", "homepage")):
        v = str(p.get(key) or "").strip()
        if v:
            known.append(f"- {label}: {v[:200]}")
    known_txt = "\n".join(known) if known else "- (없음)"
    return f"""너는 아이 동반 가족을 위한 방문 정보 정리자다. 감상·추천 문구 없이 확인된 사실만 정리한다.

[장소]
이름: {p.get('title')}
주소: {p.get('addr')}

[이미 사이트에 있는 정보 — 다시 쓰지 말 것]
{known_txt}

[할 일]
구글 검색으로 공식 안내(공식 홈페이지·지자체·공공기관·네이버 플레이스 공지)와 최근 방문 후기를 찾아 아래 3가지만 정리해라.
1) access (주차·교통): 가까운 지하철역 이름, 주차 가능 여부, 주차가 혼잡했다는 후기, 행사 때 주차 제한
2) rules (이용 규칙): 재입장, 음식물 반입, 예약 필요 여부, 연령 제한, 반려동물, 유모차
3) tip (관람 팁): 아이 동반 시 추천 동선과 순서, 쉬어 갈 곳, 비 오는 날·더운 날 활용

[규칙]
- 검색에서 확인된 것만 쓴다. 확인되지 않으면 그 항목은 빈 문자열("")로 둔다. 추측하지 않는다.
- 버스 번호, 주차 요금 금액, 지하철 출구 번호, 도보 몇 분은 쓰지 않는다.
- 요금·운영시간은 쓰지 않는다.
- 후기 한두 건에서만 나온 내용은 "~했다는 후기가 있어요"처럼 근거 수준이 드러나게 쓴다.
- 출처끼리 내용이 다르면 단정하지 말고 "자료마다 달라 방문 당일 확인이 필요해요"라고 쓴다.
- 항목마다 1~2문장, 존댓말(~요), 이모지·마크다운 금지.
- 확인하지 못한 항목 이름은 unverified 목록에 넣는다.

[출력] 아래 JSON 한 개만 출력해라. 다른 글은 쓰지 마라.
{{"access": "", "rules": "", "tip": "", "unverified": ["access", "rules", "tip" 중 확인 못 한 것]}}
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
    """수치 문장 제거, 길이 제한. 결과가 비면 ''."""
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


def grounding_sources(resp):
    out, seen = [], set()
    try:
        for cand in (resp.candidates or [])[:1]:
            gm = getattr(cand, "grounding_metadata", None)
            for ch in (getattr(gm, "grounding_chunks", None) or []):
                web = getattr(ch, "web", None)
                uri = getattr(web, "uri", None)
                if uri and uri not in seen:
                    seen.add(uri)
                    out.append({"title": getattr(web, "title", "") or "", "url": uri})
    except Exception:
        pass
    return out[:8]


def is_transient(err):
    code = getattr(err, "code", None)
    if isinstance(code, int):
        return code in (429, 500, 502, 503, 504)
    msg = str(err).lower()
    return any(k in msg for k in ("503", "unavailable", "timed out", "timeout", "429", "resource_exhausted", "overloaded", "connection"))


def call_gemini(client, types, prompt):
    cfg = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=1500,
        tools=[types.Tool(google_search=types.GoogleSearch())],
    )
    last = None
    for model in MODELS:
        for n in range(1, 4):
            try:
                resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
                if not (resp.text or "").strip():
                    raise ValueError("빈 응답")
                return model, resp
            except Exception as e:
                last = e
                if is_transient(e) and n < 3:
                    time.sleep(15 if n == 1 else 45)
                    continue
                print(f"  ⚠️ 모델 {model} 실패: {str(e)[:160]}")
                break
    raise RuntimeError(f"모든 모델 실패: {last}")


def make_entry(p, model, resp):
    sources = grounding_sources(resp)
    data = extract_json(resp.text) or {}
    fields = {k: sanitize(data.get(k)) for k in FIELDS}
    unverified = [k for k in FIELDS if not fields[k]]
    status = "draft"
    if not sources:
        fields = {k: "" for k in FIELDS}
        unverified = list(FIELDS)
        status = "no_source"
    elif not any(fields.values()):
        status = "empty"
    return {
        "title": p.get("title"),
        **fields,
        "unverified": unverified,
        "sources": sources,
        "model": model,
        "draftedAt": now_kst(),
        "status": status,
    }


# ---------------------------------------------------------------- 검토용 md
def write_review(draft):
    lines = ["# 우리 가족 체크 초안 (자동 작성 — 승인 전)", "",
             "승인할 장소의 contentid 를 Actions `promote` 입력에 넣으면 kids_notes.json 으로 옮겨져요.",
             "출처 링크를 열어 확인한 뒤 승인하세요. 문장이 이상하면 승인하지 말고 알려 주세요.", ""]
    for cid in sorted(draft):
        d = draft[cid]
        if d.get("status") == "promoted":
            continue
        lines.append(f"## {cid} {d.get('title')}  `{d.get('status')}`")
        for k in FIELDS:
            v = d.get(k)
            lines.append(f"- **{LABELS[k]}**: {v if v else '(확인 못 함 — 비워 둠)'}")
        if d.get("sources"):
            lines.append("- 출처: " + " · ".join(f"[{(s.get('title') or '링크')[:30]}]({s['url']})" for s in d["sources"]))
        lines.append("")
    REVIEW.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- draft / promote
def run_draft(args):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("❌ GEMINI_API_KEY 환경변수가 없습니다.")
        return 1
    from google import genai
    from google.genai import types
    try:
        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=120_000))
    except Exception:
        client = genai.Client(api_key=api_key)

    places = load_json(PLACES, [])
    notes = load_json(NOTES, {})
    draft = load_json(DRAFT, {})
    ids = [x.strip() for x in (args.ids or "").split(",") if x.strip()]
    targets = pick_targets(places, notes, draft, ids, args.count, redo=args.redo)
    print(f"대상 {len(targets)}곳")
    ok = 0
    for i, p in enumerate(targets, 1):
        cid = p["contentid"]
        print(f"[{i}/{len(targets)}] {cid} {p.get('title')}")
        try:
            model, resp = call_gemini(client, types, build_prompt(p))
            entry = make_entry(p, model, resp)
        except Exception as e:
            print(f"  ❌ 건너뜀: {str(e)[:160]}")
            continue
        draft[cid] = entry
        ok += 1
        print(f"  → {entry['status']} (출처 {len(entry['sources'])}개, 미확인 {entry['unverified']})")
        save_json(DRAFT, draft)  # 중간 저장
        if i < len(targets):
            time.sleep(SLEEP_SEC)
    write_review(draft)
    print(f"완료: {ok}/{len(targets)}곳 초안 저장")
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
    ap.add_argument("mode", choices=["draft", "promote"])
    ap.add_argument("--ids", default="")
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    return run_draft(args) if args.mode == "draft" else run_promote(args)


if __name__ == "__main__":
    sys.exit(main())
