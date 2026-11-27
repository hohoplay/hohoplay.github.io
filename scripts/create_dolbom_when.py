#!/usr/bin/env python3
"""
create_dolbom_when.py — '이럴 땐 이렇게' 시리즈(돌봄상식 블로그) 자동 생성/발행
==========================================================================
부모님 돌봄 상황별 "오늘 할 일 → 선택지 → 상황별 분기 → 진행 순서"를 알려 주는 행동 안내 글을
주 1편 발행한다. 돌봄상식(create_dolbom_knowledge.py)과 달리 AI가 주제를 자유롭게 쓰지 않고,
사람이 확인한 '상황 카드'(data/dolbom_when_cards.json)와 '확정 사실표'(data/dolbom_fact_sheet.json)에
있는 내용만 문장으로 풀어 쓴다. 틀린 행동 지시가 독자에게 실제 손해가 될 수 있기 때문이다.

기존 자동화와의 관계 (건드리지 않음)
  - create_dolbom_knowledge.py, grow_dolbom_knowledge.yml, dolbom_knowledge_state.json 을
    import 하거나 읽거나 쓰지 않는다. Blogger 인증·발행 코드는 복사해서 독립시켰다(한쪽을 고쳐도
    다른 쪽이 깨지지 않게).
  - 같은 시크릿(BLOG_ID, BLOGGER_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    GEMINI_API_KEY)을 그대로 재사용한다.
  - 이 스크립트가 쓰는 파일은 data/dolbom_when_state.json 하나뿐이다. 카드 파일과 사실표는
    읽기만 하며, 사람만 수정한다.

실행
  python scripts/create_dolbom_when.py                      # 1편 발행 (주간 cron 기본값)
  python scripts/create_dolbom_when.py --count 4            # 4편 연속 발행
  python scripts/create_dolbom_when.py --dry-run            # 발행 없이 글만 만들어 data/preview/ 에 저장
  python scripts/create_dolbom_when.py --dry-run --card ID  # 특정 카드(draft 포함)를 미리 보기

환경변수: GEMINI_API_KEY, BLOG_ID, BLOGGER_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
          DATA_DIR(기본 ./data)

발행 대상 카드: status 가 "verified" 이고, 아직 발행하지 않았고, needs_review 로 빠지지 않았고,
  fact_refs 로 연결된 사실표 항목이 모두 존재하며 verified_at 의 연도가 올해인 카드.
  → 매년 수가·제도가 바뀔 때 확인일이 지난 사실을 쓰는 카드는 자동으로 발행에서 빠진다.

발행 전 게이트(하나라도 끝내 통과하지 못하면 그 주는 발행하지 않고 건너뜀 — exit 0):
  1. 숫자 화이트리스트: 글 속 숫자가 카드·연결된 사실표에 없으면 불통과
  2. 기관명 화이트리스트: 카드 agencies 에 없는 기관·단체 이름으로 보이는 표현이 있으면 불통과
  3. 단정 표현·과장 표현 금지, 링크·소제목·표 등 지정 외 마크업 금지
  4. 구조 일치: 오늘 할 일·상황별 분기·진행 순서의 목록 개수가 카드와 같아야 하고,
     선택지 비교 문단에 카드의 모든 선택지 이름이 나와야 함 (비교표는 카드에서 코드가 직접 만듦)
  5. 분량 2,000자 이상(코드가 만드는 부분 제외), FAQ 정확히 5개, FAQ 자리표시자 없음
인프라 오류(Gemini 응답을 한 번도 못 받음, Blogger 발행 실패)는 exit 1 로 알린다.
한 카드가 3회 연속 게이트를 통과하지 못하면 state 의 needs_review 로 옮겨 대상에서 뺀다
(카드 파일은 고치지 않는다 — 사람이 카드를 고친 뒤 state 의 needs_review 에서 해당 id 를 지우면 된다).
"""

import os
import re
import sys
import json
import time
import html
import argparse
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import requests
from google import genai
from google.genai import types

# ─────────────────────────────────────────
# 인증·경로 — 돌봄상식과 같은 시크릿을 재사용 (코드는 복사본)
# ─────────────────────────────────────────
BLOG_ID        = os.environ.get("BLOG_ID", "")
REFRESH_TOKEN  = os.environ.get("BLOGGER_REFRESH_TOKEN", "")
CLIENT_ID      = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET  = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

DATA_DIR    = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
CARDS_PATH  = os.path.join(DATA_DIR, "dolbom_when_cards.json")
FACTS_PATH  = os.path.join(DATA_DIR, "dolbom_fact_sheet.json")
STATE_PATH  = os.path.join(DATA_DIR, "dolbom_when_state.json")
PREVIEW_DIR = os.path.join(DATA_DIR, "preview")

_BLOG_BASE = "https://bumodolbom.blogspot.com"

# 조정 가능한 기준값
MIN_CHARS = 2000            # 코드가 만드는 부분(비교표·확인할 기관·근거 자료)을 뺀 글자 수 기준
MAX_ATTEMPTS = 3            # 글 한 편당 생성 시도 횟수
REVIEW_AFTER_FAILS = 3      # 이 횟수만큼 연속으로 게이트를 못 넘으면 needs_review
SLUG_START = 40001          # 돌봄상식(30001~)과 겹치지 않는 숫자 슬러그 시작값
SITUATION_ORDER = ["퇴원예정", "치매의심", "거동불편", "요양원알아보는중"]
SERIES_LABEL = "이럴땐이렇게"


def _now_kst():
    return datetime.now(timezone(timedelta(hours=9)))


def get_access_token():
    """Blogger access token 발급 — 돌봄상식과 같은 로직."""
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "grant_type":    "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    if resp.status_code == 200:
        print("🔑 Access Token 발급 완료")
        return resp.json().get("access_token", "")
    print(f"❌ Token 발급 실패: {resp.text[:150]}")
    return ""


def post_blogger(access_token, title, content, labels, slug_number):
    """발행 후 (성공 여부, 글 주소)를 돌려준다. 숫자 제목으로 먼저 생성한 뒤 한글 제목으로 고쳐서
    URL이 순차 숫자 슬러그(예: /2026/11/40001.html)로 남게 한다 — 돌봄상식과 같은 방식.
    글 주소는 관련 글 링크에 쓰려고 받아 둔다."""
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    body = {"title": str(slug_number), "content": content, "labels": labels}

    post_id, post_url = None, ""
    for attempt in range(1, 4):
        resp = requests.post(url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=body)
        if resp.status_code in (200, 201):
            data = resp.json()
            post_id = data.get("id")
            post_url = data.get("url", "")
            break
        elif resp.status_code == 429:
            wait = 60 * attempt
            print(f"⏳ 429 쿼터 초과 — {wait}초 대기 후 재시도 ({attempt}/3)")
            time.sleep(wait)
        else:
            print(f"❌ 발행 실패 ({resp.status_code}): {resp.text[:150]}")
            return False, ""

    if post_id is None:
        print("❌ 3회 재시도 후 실패")
        return False, ""

    try:
        patch_resp = requests.patch(f"{url}{post_id}",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"title": title})
        if patch_resp.status_code not in (200, 201):
            print(f"⚠️ 한글 제목으로 수정 실패({patch_resp.status_code}) — URL은 숫자로 정상이나 화면 제목이 숫자로 남았을 수 있음")
    except Exception as e:
        print(f"⚠️ 제목 수정 요청 중 오류: {e}")

    print(f"✅ 발행 완료 — {title}")
    return True, post_url


# ─────────────────────────────────────────
# 스타일 — 돌봄상식과 같은 세이지그린 톤 + 이 시리즈용 표·행동 문구 스타일
# ─────────────────────────────────────────
def when_style():
    return """<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Noto Sans KR',sans-serif;background:#F7F6F0;color:#333;padding:16px}
.wrap{max-width:720px;margin:auto}
.hero{background:linear-gradient(135deg,#3F5D45,#6B8E6E);color:#fff;border-radius:18px;padding:36px 24px;text-align:center;margin-bottom:22px}
.hero h1{font-size:24px;margin-bottom:8px;line-height:1.4}
.hero p{opacity:.85;font-size:14px}
.card{background:#fff;border-radius:14px;padding:26px 24px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.card h2{font-size:18px;color:#2F4A34;margin:26px 0 10px;padding-left:10px;border-left:4px solid #6B8E6E}
.card h2:first-child{margin-top:0}
.card p{font-size:15px;line-height:1.9;color:#374151;margin-bottom:14px}
.card ul{margin:0 0 14px 20px}
.card ol{margin:0 0 14px 20px}
.card li{font-size:15px;line-height:1.9;color:#374151;margin-bottom:8px}
.act{font-weight:700;color:#2F4A34}
.badge{display:inline-block;background:#DDE6DA;color:#3F5D45;padding:3px 10px;border-radius:20px;font-size:12px;margin-bottom:10px}
.tag-cloud{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.tag{background:#EEF3EC;color:#4C6B52;padding:4px 10px;border-radius:20px;font-size:11px}
.notice{background:#FBF3EF;border:1px solid #E8C9B8;border-radius:10px;padding:12px 16px;font-size:13px;color:#8A5A3D;margin-bottom:16px}
.intro{font-size:15.5px;line-height:1.9;color:#2F4A34;font-weight:500;margin-bottom:18px}
.faq-item{margin-bottom:18px;padding-bottom:16px;border-bottom:1px solid #EEF1EC}
.faq-item:last-child{margin-bottom:0;padding-bottom:0;border-bottom:none}
.faq-q{font-size:15px;color:#2F4A34;margin-bottom:6px;line-height:1.6}
.faq-a{font-size:14px;line-height:1.8;color:#4B5B4E;margin-bottom:0}
.meta{color:#aaa;font-size:12px;text-align:center;padding:20px 0}
.box-label{font-weight:800;color:#2F4A34;font-size:14px;margin-bottom:6px}
.box-summary{background:#F3F6F1;border:1px solid #CFE0CB;border-radius:12px;padding:14px 16px;margin:0 0 14px}
.box-summary p{margin:0;font-size:14.5px;line-height:1.75;color:#374151}
.box-toc{background:#FAFAF7;border:1px solid #E5E7EB;border-radius:12px;padding:14px 16px;margin:0 0 18px}
.box-toc ol{margin:0;padding-left:20px}
.box-toc li{font-size:14px;line-height:1.8;margin-bottom:2px}
.box-toc a{color:#3F5D45;text-decoration:none}
.tbl-wrap{overflow-x:auto;margin:0 0 16px}
.opt-table{width:100%;border-collapse:collapse;min-width:480px}
.opt-table th{background:#EEF3EC;color:#2F4A34;text-align:left;padding:8px 10px;border:1px solid #D5DFD2;font-size:13.5px}
.opt-table td{padding:8px 10px;border:1px solid #E3E8E1;font-size:13.5px;vertical-align:top;line-height:1.7;color:#374151}
.ref-block{font-size:13px;color:#4B5B4E;margin-bottom:14px}
.ref-block ul{margin:4px 0 0;padding-left:18px}
.ref-block li{margin-bottom:4px;font-size:13px;line-height:1.7}
.ref-block a{color:#3F5D45}
.closing-q{font-size:13.5px;color:#4C6B52;font-style:italic;text-align:center;margin:0}
</style>"""


# ─────────────────────────────────────────
# Gemini 호출 — 돌봄상식과 같은 모델 후보·재시도 방식(복사본)
# ─────────────────────────────────────────
GEMINI_MODEL_CANDIDATES = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",   # 서로 다른 모델은 수용량이 따로라, 한쪽이 과부하여도 다른 쪽은 될 수 있음
    "gemini-flash-latest",
    "gemini-3.6-flash",
]
_GEMINI_CONFIG = types.GenerateContentConfig(max_output_tokens=8192)
_RETRYABLE_MARKERS = ("UNAVAILABLE", "RESOURCE_EXHAUSTED", "DEADLINE_EXCEEDED", "INTERNAL",
                      "503", "500", "429")
_MODEL_GONE_MARKERS = ("NOT_FOUND", "404")   # 후보 모델이 없어진 경우 — 그 모델만 건너뛰고 나머지로 계속
GEMINI_ROUNDS = 3                            # 전체 후보를 몇 바퀴 시도할지
GEMINI_ROUND_WAITS = (30, 60)                # 바퀴 사이 대기 초 (과부하는 보통 수 분 안에 풀림)


def _is_retryable(err):
    msg = str(err)
    return any(marker in msg for marker in _RETRYABLE_MARKERS)


def _is_model_gone(err):
    msg = str(err)
    return any(marker in msg for marker in _MODEL_GONE_MARKERS)


def _call_gemini_with_fallback(client, prompt):
    """모델 후보를 순서대로 시도하고, 전원이 '일시적' 오류로만 실패하면 대기 후 전체를 다시 시도(최대 GEMINI_ROUNDS 바퀴)."""
    last_err = None
    for attempt in range(GEMINI_ROUNDS):
        if attempt > 0:
            wait = GEMINI_ROUND_WAITS[min(attempt - 1, len(GEMINI_ROUND_WAITS) - 1)]
            print(f"  ⏳ 모든 모델이 일시적 오류(과부하 등)로 실패 — {wait}초 대기 후 전체 재시도 ({attempt + 1}/{GEMINI_ROUNDS}바퀴)")
            time.sleep(wait)

        all_retryable = True
        for model_name in GEMINI_MODEL_CANDIDATES:
            try:
                resp = client.models.generate_content(
                    model=model_name, contents=prompt, config=_GEMINI_CONFIG)
                text = (resp.text or "").strip()
                if not text:
                    raise ValueError("빈 응답")
                text = text.replace("```html", "").replace("```", "").strip()
                return text
            except Exception as e:
                print(f"  ⚠️ 모델 '{model_name}' 실패: {e} — 다음 후보로 재시도합니다.")
                last_err = e
                if not _is_retryable(e) and not _is_model_gone(e):
                    all_retryable = False

        if not all_retryable:
            break

    raise RuntimeError(f"모든 Gemini 모델 후보가 실패했습니다. 마지막 에러: {last_err}")


# ─────────────────────────────────────────
# 카드·사실표 읽기와 검증 (읽기 전용)
# ─────────────────────────────────────────
class ContentQualityError(Exception):
    """게이트를 끝내 통과하지 못해 발행을 보류함. 인프라 문제가 아니라 의도된 보류(exit 0)."""
    pass


_CARD_LIST_FIELDS = ("today_actions", "options", "branches", "steps", "agencies", "fact_refs")


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_card(card):
    """카드 한 장의 구조를 검사해 문제 목록을 돌려준다(비어 있으면 정상)."""
    problems = []
    for key in ("id", "situation", "topic", "status"):
        if not isinstance(card.get(key), str) or not card.get(key).strip():
            problems.append(f"'{key}' 누락")
    for key in _CARD_LIST_FIELDS:
        if not isinstance(card.get(key), list) or not card.get(key):
            problems.append(f"'{key}' 목록이 비어 있거나 없음")
    if problems:
        return problems
    if not all(isinstance(x, str) and x.strip() for x in card["today_actions"]):
        problems.append("today_actions 항목은 비어 있지 않은 문장이어야 함")
    if not all(isinstance(x, str) and x.strip() for x in card["steps"]):
        problems.append("steps 항목은 비어 있지 않은 문장이어야 함")
    for o in card["options"]:
        if not isinstance(o, dict) or not all(str(o.get(k, "")).strip() for k in ("name", "fits_when", "pros", "cons")):
            problems.append("options 항목에 name/fits_when/pros/cons 가 모두 필요함")
            break
    for b in card["branches"]:
        if not isinstance(b, dict) or not all(str(b.get(k, "")).strip() for k in ("when", "then")):
            problems.append("branches 항목에 when/then 이 모두 필요함")
            break
    for a in card["agencies"]:
        if not isinstance(a, dict) or not all(str(a.get(k, "")).strip() for k in ("name", "role")):
            problems.append("agencies 항목에 name/role 이 모두 필요함")
            break
    return problems


def load_cards_and_facts():
    """카드 목록과 사실표(키→항목)를 읽는다. 파일 자체가 깨졌으면 예외를 그대로 올려 exit 1 로 알린다."""
    cards_raw = _load_json(CARDS_PATH).get("cards", [])
    facts_raw = _load_json(FACTS_PATH).get("facts", [])
    fact_map = {f["key"]: f for f in facts_raw if isinstance(f, dict) and f.get("key")}

    cards, seen = [], set()
    for c in cards_raw:
        if not isinstance(c, dict):
            continue
        problems = validate_card(c)
        if c.get("id") in seen:
            problems.append("id 중복")
        if problems:
            print(f"⚠️ 카드 '{c.get('id', '(id 없음)')}' 구조 문제로 제외: {' / '.join(problems)}")
            continue
        seen.add(c["id"])
        cards.append(c)
    return cards, fact_map


def facts_fresh(card, fact_map, year):
    """카드의 fact_refs 가 모두 사실표에 있고 확인일 연도가 올해인지. (정상 여부, 문제 설명)"""
    for key in card["fact_refs"]:
        fact = fact_map.get(key)
        if fact is None:
            return False, f"사실표에 '{key}' 없음"
        verified = str(fact.get("verified_at", ""))
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", verified) or int(verified[:4]) != year:
            return False, f"사실 '{key}' 확인일({verified or '없음'})이 {year}년이 아님"
    return True, ""


# ─────────────────────────────────────────
# 상태 파일 (이 스크립트가 쓰는 유일한 파일)
# ─────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_PATH):
        state = _load_json(STATE_PATH)
    else:
        state = {}
    state.setdefault("published", [])          # 발행한 카드 id
    state.setdefault("next_slug_number", SLUG_START)
    state.setdefault("fail_counts", {})        # 카드 id → 연속 게이트 실패 횟수
    state.setdefault("needs_review", [])       # 반복 실패로 대상에서 뺀 카드 id
    state.setdefault("last_situation", "")
    state.setdefault("history", [])
    return state


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def pick_card(cards, fact_map, state, year, forced_id=None, allow_draft=False):
    """발행할 카드 한 장을 고른다. 상황 4개를 번갈아 가며(퇴원 → 치매 → 거동 → 요양원) 고르고,
    해당 상황에 후보가 없으면 다음 상황으로 넘어간다."""
    if forced_id:
        for c in cards:
            if c["id"] == forced_id:
                if c["status"] != "verified" and not allow_draft:
                    print(f"❌ 카드 '{forced_id}' 의 status 가 verified 가 아니라 발행할 수 없습니다(미리 보기는 --dry-run).")
                    return None
                ok, why = facts_fresh(c, fact_map, year)
                if not ok:
                    print(f"❌ 카드 '{forced_id}' 사용 불가: {why}")
                    return None
                return c
        print(f"❌ 카드 '{forced_id}' 를 찾을 수 없습니다.")
        return None

    candidates = []
    for c in cards:
        if c["status"] != "verified":
            continue
        if c["id"] in state["published"] or c["id"] in state["needs_review"]:
            continue
        ok, why = facts_fresh(c, fact_map, year)
        if not ok:
            print(f"  ℹ️ 카드 '{c['id']}' 는 발행 대상에서 제외: {why}")
            continue
        candidates.append(c)
    if not candidates:
        return None

    present = []
    for c in candidates:
        if c["situation"] not in present:
            present.append(c["situation"])
    order = list(SITUATION_ORDER) + sorted(s for s in present if s not in SITUATION_ORDER)
    last = state.get("last_situation", "")
    start = (order.index(last) + 1) if last in order else 0
    for k in range(len(order)):
        sit = order[(start + k) % len(order)]
        for c in candidates:
            if c["situation"] == sit:
                return c
    return candidates[0]


# ─────────────────────────────────────────
# 프롬프트
# ─────────────────────────────────────────
_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _extract_numbers(text):
    return {m.replace(",", "") for m in _NUM_RE.findall(text or "")}


def _card_text_for_numbers(card):
    """카드에서 '글에 들어갈 수 있는' 문장만 모아 숫자 화이트리스트의 재료로 쓴다(id·상태·태그 등은 제외)."""
    parts = [card["topic"]]
    parts += [str(v) for v in (card.get("conditions") or {}).values()]
    parts += card["today_actions"] + card["steps"]
    for o in card["options"]:
        parts += [o["name"], o["fits_when"], o["pros"], o["cons"]]
    for b in card["branches"]:
        parts += [b["when"], b["then"]]
    for a in card["agencies"]:
        parts += [a["name"], a["role"]]
    return "\n".join(parts)


def allowed_agency_names(card, fact_map):
    """카드의 agencies 이름 + 카드 문장·연결된 사실 문장에 이미 나오는 기관 표현(예: 사실표에 적힌 '주간보호센터').
    사람이 확인한 문장에 있는 표현은 글에서 써도 되고, 그 밖의 기관 이름은 막는다."""
    names = [a["name"] for a in card["agencies"]]
    source_text = _card_text_for_numbers(card) + "\n" + "\n".join(fact_map[k]["text"] for k in card["fact_refs"])
    for m in _AGENCY_RE.findall(source_text):
        if m not in names:
            names.append(m)
    return names


def allowed_numbers(card, fact_map):
    nums = _extract_numbers(_card_text_for_numbers(card))
    for key in card["fact_refs"]:
        nums |= _extract_numbers(fact_map[key]["text"])
    return nums


def _format_card_brief(card):
    cond = ", ".join(f"{k}: {v}" for k, v in (card.get("conditions") or {}).items()) or "(없음)"
    lines = [f"- 상황: {card['situation']}", f"- 주제: {card['topic']}", f"- 조건: {cond}", "- 오늘 할 일:"]
    lines += [f"  {i + 1}. {t}" for i, t in enumerate(card["today_actions"])]
    lines.append("- 선택지:")
    for i, o in enumerate(card["options"]):
        lines.append(f"  {i + 1}. [{o['name']}] 맞는 경우: {o['fits_when']} / 장점: {o['pros']} / 단점·주의: {o['cons']}")
    lines.append("- 상황별 분기:")
    for i, b in enumerate(card["branches"]):
        lines.append(f"  {i + 1}. {b['when']} → {b['then']}")
    lines.append("- 진행 순서:")
    lines += [f"  {i + 1}. {t}" for i, t in enumerate(card["steps"])]
    lines.append("- 확인할 기관:")
    lines += [f"  - {a['name']}: {a['role']}" for a in card["agencies"]]
    return "\n".join(lines)


def build_prompt(card, fact_map, recent_history, feedback=""):
    n_act, n_br, n_st = len(card["today_actions"]), len(card["branches"]), len(card["steps"])
    opt_names = ", ".join(f'"{o["name"]}"' for o in card["options"])
    agency_names = ", ".join(f'"{a["name"]}"' for a in card["agencies"])
    nums = sorted(allowed_numbers(card, fact_map), key=lambda x: (len(x), x))
    nums_text = ", ".join(nums) if nums else "(사용할 수 있는 숫자 없음 — 숫자를 쓰지 마세요)"
    fact_lines = "\n".join(f"- {fact_map[k]['text']}" for k in card["fact_refs"])

    recent_block = ""
    lines = []
    for h in recent_history:
        if h.get("title"):
            lines.append(f"- 제목: {h['title']} / 첫 문장 시작: {h.get('first_words') or '(기록 없음)'}")
    if lines:
        recent_block = ("\n\n[최근 발행한 글 — 제목과 도입 첫 문장 시작 어구가 겹치지 않게 쓰세요]\n"
                        + "\n".join(lines))

    feedback_block = f"\n\n[재작성 지시]\n{feedback}" if feedback else ""

    return f"""당신은 부모님 돌봄 상황에서 "지금 무엇부터 해야 하는지"를 차분하게 안내하는 정보 필자입니다.
이 글을 읽는 사람은 부모님의 돌봄 문제가 갑자기 닥쳐 급하게 검색해서 들어온 자녀입니다.
글 전체에서 "호호플레이"나 특정 서비스·앱 이름을 언급하지 마세요.

아래 [상황 카드]와 [확인된 사실]은 사람이 직접 확인한 내용입니다. 글은 이 두 가지에 적힌 내용만
근거로 쓰고, 문장으로 풀어 설명하는 일만 하세요. 카드와 사실에 없는 제도, 서비스 이름, 기간, 금액,
통계, 기관을 새로 지어내거나 기억에서 덧붙이지 마세요. 분량은 새 사실이 아니라 독자의 상황에 대한
설명, 판단 기준, 준비해 둘 것, 가족과 나눌 이야기처럼 사실이 아닌 설명으로 채우세요.

[상황 카드]
{_format_card_brief(card)}

[확인된 사실]
{fact_lines}

[숫자 규칙 — 반드시 지키세요]
- 글에 쓸 수 있는 숫자는 다음뿐입니다: {nums_text}
- 순번을 숫자로 쓰지 말고(1단계, 2번 등), "먼저/다음으로/마지막으로"나 목록(<ol>)을 쓰세요.
- 위 목록에 없는 숫자(기간, 금액, 비율, 횟수, 나이 등)는 어떤 형태로도 쓰지 마세요.

[기관 이름 규칙]
- 기관·단체 이름은 다음과, [상황 카드]·[확인된 사실]에 이미 적힌 표현만 쓸 수 있습니다: {agency_names}
- 보건복지부, 주민센터, 복지관 등 위에 없는 기관은 언급하지 마세요.

[출력 형식 — 반드시 아래 구분자를 정확히 그대로 포함해서 출력하세요. 인사말이나 설명 문장은 쓰지 마세요.
TITLE/INTRO/ACTIONS/OPTIONS/BRANCHES/STEPS/FAQ/CLOSING은 필수이며, SUMMARY/CLOSINGQ는 구분자는 항상
출력하되 정말 쓸 내용이 없으면 안쪽만 비워도 됩니다. 소제목(<h2>), 표(<table>), 링크(<a>), 주소(http)는
쓰지 마세요 — 소제목과 표는 시스템이 따로 붙입니다]
<!--TITLE_START-->
(28~40자. 독자의 상황이 보이는 제목. 예: "퇴원이 며칠 남았는데 등급이 없을 때, 오늘 할 일 순서"처럼
[상황]+[얻는 것]. 과장 없이 텍스트만)
<!--TITLE_END-->
<!--INTRO_START-->
(<p> 태그, 공백 제외 150~250자, 3문장 이내. 첫 문장은 독자의 구체적인 상황으로 열고, "오늘은 ~에 대해
알아보겠습니다" 같은 예고 문장이나 인사말로 시작하지 마세요. 둘째 문장에서 이 글이 알려 주는 핵심
순서를 말하고, 셋째 문장에서 글의 구성을 짚으세요.)
<!--INTRO_END-->
<!--SUMMARY_START-->
(<p> 태그 1~2문장, 공백 제외 100~200자. 이 글의 결론을 독립된 문장으로. 카드에 있는 내용만 요약하세요.)
<!--SUMMARY_END-->
<!--ACTIONS_START-->
(<ol> 안에 <li>를 정확히 {n_act}개. 카드의 "오늘 할 일" {n_act}개를 같은 순서로, 한 항목에 하나씩 쓰세요.
각 항목은 <li><span class="act">(카드의 행동을 한 문장으로)</span> (왜 필요한지와 어떻게 하면
되는지를 카드와 사실 안에서 2~3문장으로 설명)</li> 형식이며, 항목당 공백 제외 120~220자.)
<!--ACTIONS_END-->
<!--OPTIONS_START-->
(<p> 태그 2~3개, 공백 제외 450~750자. 카드의 선택지 {len(card['options'])}개를 서로 견주는 설명입니다.
선택지 이름을 카드에 적힌 그대로 한 번 이상 쓰세요: {opt_names}. 각 선택지가 어떤 상황에 맞는지,
무엇을 얻고 무엇을 감수하는지를 카드 내용에 근거해 쓰고, 어느 하나를 정답으로 정하지 말고 독자의
상황에 따라 달라진다고 쓰세요. 표는 쓰지 마세요.)
<!--OPTIONS_END-->
<!--BRANCHES_START-->
(<ul> 안에 <li>를 정확히 {n_br}개. 카드의 "상황별 분기" {n_br}개를 같은 순서로 하나씩 쓰세요.
각 항목은 <li><span class="act">(카드의 조건을 "~라면" 형태 한 문장으로)</span> (그때 해야 할 일과
이유를 카드와 사실 안에서 2~3문장으로 설명)</li> 형식이며, 항목당 공백 제외 150~280자.)
<!--BRANCHES_END-->
<!--STEPS_START-->
(<ol> 안에 <li>를 정확히 {n_st}개. 카드의 "진행 순서" {n_st}개를 같은 순서로 하나씩 쓰세요.
각 항목은 <li><span class="act">(카드의 단계를 한 문장으로)</span> (그 단계에서 확인하거나 준비할 것을
카드와 사실 안에서 1~2문장으로 설명)</li> 형식이며, 항목당 공백 제외 90~180자.)
<!--STEPS_END-->
<!--FAQ_START-->
(class="faq-item" 블록 정확히 5개. 각 블록은 다음 형식을 그대로 따르세요:
<div class="faq-item"><h3 class="faq-q">Q. (질문)</h3><p class="faq-a">A. (답변)</p></div>
질문은 이 상황의 독자가 실제로 검색할 법한 완성된 문장으로 쓰고, 답변은 공백 제외 120~220자로 첫 문장에서
바로 답하세요. 답변은 카드와 사실에 있는 내용만 쓰고, 근거가 없는 질문은 만들지 마세요. 5개 질문의 문형과
끝맺는 말을 서로 다르게 쓰세요. 질문에 "(제도)", "[대상]", "OOO", "○○" 같은 분류 라벨이나 자리표시자,
질문 번호를 쓰지 마세요.)
<!--FAQ_END-->
<!--CLOSING_START-->
(<p> 태그 2~3문장, 공백 제외 100~220자. 이 글이 권하는 판단을 한 문장으로 쓰고, 독자가 오늘 바로 할 수 있는
행동 한 가지로 맺으세요. 새로운 사실을 추가하지 마세요. "이 글은 일반적인 정보이며 의료·법률 상담을
대신하지 않는다"는 취지를 자연스럽게 한 번 포함하세요.)
<!--CLOSING_END-->
<!--CLOSINGQ_START-->
(한 줄. 독자의 상황을 묻는 질문 하나. 공감·저장을 구걸하는 문구는 쓰지 마세요.)
<!--CLOSINGQ_END-->

[문장 톤 규칙]
- "~합니다", "~해보세요"체의 다정하고 담백한 존댓말. "~에요", "~죠", "~잖아요" 같은 구어체는 쓰지 마세요.
- 같은 문장 종결 패턴이 두 문장 이상 연속되지 않게 하고, 문단마다 "또한/한편/따라서/결론적으로"로
  시작하지 마세요. 같은 내용을 여러 곳에서 반복해 분량을 채우지 마세요.
- 다음 표현은 쓰지 마세요: "최고", "무조건", "반드시", "절대", "틀림없이", "확실히", "100%", "완치",
  "효과 보장", "단번에 해결", "역대급", "~에 대해 알아보겠습니다", "결론적으로", "마무리하며",
  "도움이 되셨으면 좋겠습니다", "누구나 한 번쯤", "~를 바탕으로 살펴보면", "직접 가봤더니",
  "제가 경험한 바로는". 이 블로그는 직접 방문·체험 콘텐츠가 아닙니다.

[안전 규칙]
- 사실에 적힌 서술의 강도와 범위를 바꾸지 마세요. "마쳐야 한다"는 "~이내에 마치도록 정해져 있습니다"처럼 기한임을 밝히고,
  "이내에 완료됩니다", "이내에 나옵니다"처럼 결과를 보장하는 말로 바꾸지 마세요. 기한이 연장되어 늦어질 수 있는 경우에는
  그 점을 함께 쓰세요. 사실의 자격·조건을 더 넓은 대상에 적용하는 문장도 쓰지 마세요.
- "분기"라는 단어는 글에 쓰지 말고 "상황별"로 쓰세요.
- 의료적 진단이나 처방, 법률 판단으로 읽힐 수 있는 단정은 하지 말고, 최종 확인은 해당 기관에 문의하도록
  안내하세요. 법령이나 제도는 바뀔 수 있다는 점을 자연스럽게 밝히세요.
- 보호자의 죄책감이나 불안을 자극하는 표현("방치하면 큰일 납니다" 등)은 쓰지 마세요.
- 가족 간 의견이 갈릴 수 있는 내용은 정답을 정하지 말고 선택지를 나란히 놓으세요.{recent_block}{feedback_block}"""


# ─────────────────────────────────────────
# 파싱과 게이트
# ─────────────────────────────────────────
_REQUIRED = ("title", "intro", "actions", "options", "branches", "steps", "faq", "closing")
_OPTIONAL = ("summary", "closingq")
_SECTION_RE = {
    key: re.compile(rf"<!--{key.upper()}_START-->(.*?)<!--{key.upper()}_END-->", re.S)
    for key in _REQUIRED + _OPTIONAL
}
_FAQ_ITEM_RE = re.compile(r'class="faq-item"', re.I)
_LI_RE = re.compile(r"<li\b", re.I)
_PLACEHOLDER_RE = re.compile(r'[\(\[][^)\]]{0,24}/[^)\]]{0,24}[\)\]]|○{2,}|[Oo]{3,}|[xX]{3,}')
_FORBIDDEN_MARKUP_RE = re.compile(r"<\s*(?:h1|h2|table|script|style|iframe|form|a)\b|https?://", re.I)

# 돌봄상식과 같은 과장·상투 표현 + 행동 안내 글에서 의료·법률 판단으로 읽힐 수 있는 단정 표현
_BANNED_HARD = [
    "최고의", "무조건", "100% 효과", "완치", "효과 보장", "완벽 보장", "단번에 해결", "역대급",
    "새로운 가치를 만듭니다", "당신의 성공과 함께합니다", "차별화된 서비스", "고객 만족을 최우선으로",
    "정성을 다하겠습니다", "에 대해 알아보겠습니다", "결론적으로", "마무리하며",
    "도움이 되셨으면 좋겠습니다", "누구나 한 번쯤", "아련한 추억", "의 매력과 가치", "를 바탕으로 살펴보면",
    "데이터를 바탕으로 분석한 결과", "직접 가봤더니", "다녀와 보니", "제가 경험한 바로는", "먹어봤는데", "써 보니",
    "반드시", "절대", "틀림없이", "확실히", "100%",
    "분기별", "분기",
]

# 법정 기한을 결과 보장처럼 단정하는 표현(예: "30일 이내에 완료됩니다")
_DEADLINE_ASSERT_RE = re.compile(r"이내에\s*(?:등급\s*판정이\s*|결과가\s*|심사가\s*)?(?:완료|나옵|나오게|끝납|끝나|이뤄|이루어|확정)")

# 기관·단체 이름으로 보이는 표현(앞에 한글 2자 이상 + 기관 접미어)
_AGENCY_RE = re.compile(
    r"[가-힣]{2,}(?:건강보험공단|연금공단|공단|보건복지부|복지부|행정복지센터|주민센터|치매안심센터|"
    r"복지센터|센터|보건소|복지관|심사평가원|구청|시청|군청)"
)


def _visible_text(html_fragment):
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", html_fragment or "")).strip()


def _visible_len(html_fragment):
    return len(_WS_RE.sub("", _TAG_RE.sub("", html_fragment or "")))


def _first_words(text, n=12):
    plain = _visible_text(text)
    return " ".join(plain.split(" ")[:n])


def _find_banned(text):
    return [p for p in _BANNED_HARD if p in text]


def _find_placeholder(text):
    return _PLACEHOLDER_RE.findall(text or "")


def _find_bad_numbers(text, allowed):
    return sorted(n for n in _extract_numbers(text) if n not in allowed)


def _find_unlisted_agencies(text, agency_names):
    bad = []
    for m in _AGENCY_RE.findall(_visible_text(text)):
        if not any(m in name or name in m for name in agency_names):
            if m not in bad:
                bad.append(m)
    return bad


def _parse_sections(raw):
    sections = {}
    for key in _REQUIRED:
        m = _SECTION_RE[key].search(raw)
        if not m:
            return None
        sections[key] = m.group(1).strip()
    return sections


def _parse_optional(raw):
    out = {}
    for key in _OPTIONAL:
        m = _SECTION_RE[key].search(raw)
        out[key] = m.group(1).strip() if m else ""
    return out


def check_gates(card, fact_map, sections, optional):
    """게이트 5종을 모두 검사해 (문제 목록, AI가 쓴 부분의 글자 수)를 돌려준다."""
    allowed = allowed_numbers(card, fact_map)
    agency_names = allowed_agency_names(card, fact_map)
    scan_keys = ("intro", "actions", "options", "branches", "steps", "faq", "closing")
    scan_text = "\n".join(sections[k] for k in scan_keys) + "\n" + "\n".join(optional.get(k, "") for k in _OPTIONAL)

    total_len = sum(_visible_len(sections[k]) for k in scan_keys)
    problems = []

    # 1. 숫자 화이트리스트
    bad_nums = _find_bad_numbers(_visible_text(scan_text) + " " + sections["title"], allowed)
    if bad_nums:
        problems.append(f"카드·사실에 없는 숫자 포함: {', '.join(bad_nums)}")

    # 2. 기관명 화이트리스트
    bad_agencies = _find_unlisted_agencies(scan_text + " " + sections["title"], agency_names)
    if bad_agencies:
        problems.append(f"카드에 없는 기관·단체 이름으로 보이는 표현 포함: {', '.join(bad_agencies)}")

    # 3. 단정·과장 표현, 지정 외 마크업
    banned = _find_banned(_visible_text(scan_text) + " " + sections["title"])
    if banned:
        problems.append(f"금지 표현 포함: {', '.join(banned)}")
    if _FORBIDDEN_MARKUP_RE.search(scan_text):
        problems.append("소제목·표·링크·주소 등 지정하지 않은 마크업 포함")
    if _DEADLINE_ASSERT_RE.search(_visible_text(scan_text)):
        problems.append("법정 기한을 결과 보장처럼 단정함 ('~이내에 완료/나옵니다' 금지 — '~이내에 마치도록 정해져 있고 연장될 수 있다'로)")

    # 4. 구조 일치
    for key, expected, label in (("actions", len(card["today_actions"]), "오늘 할 일"),
                                 ("branches", len(card["branches"]), "상황별 분기"),
                                 ("steps", len(card["steps"]), "진행 순서")):
        got = len(_LI_RE.findall(sections[key]))
        if got != expected:
            problems.append(f"{label} 목록 {got}개(카드는 {expected}개)")
    opt_text = _visible_text(sections["options"])
    missing = [o["name"] for o in card["options"] if o["name"] not in opt_text]
    if missing:
        problems.append(f"선택지 비교 문단에 카드의 선택지 이름이 빠짐: {', '.join(missing)}")

    # 5. 분량·FAQ·자리표시자
    if total_len < MIN_CHARS:
        problems.append(f"글자수 {total_len}자({MIN_CHARS}자 미달)")
    faq_count = len(_FAQ_ITEM_RE.findall(sections["faq"]))
    if faq_count != 5:
        problems.append(f"FAQ {faq_count}개(5개 필요)")
    ph = _find_placeholder(sections["faq"])
    if ph:
        problems.append(f"FAQ에 분류 라벨/자리표시자 포함: {', '.join(ph)}")

    return problems, total_len


def generate_post(card, fact_map, recent_history):
    """카드 한 장으로 글을 생성하고 게이트를 검사한다. 최대 MAX_ATTEMPTS 회 재생성하며, 끝내 통과하지 못하면
    ContentQualityError(의도된 보류), 파싱 가능한 응답을 한 번도 못 받았으면 RuntimeError(인프라 문제)."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    feedback = ""
    ever_parsed = False

    for attempt in range(MAX_ATTEMPTS):
        prompt = build_prompt(card, fact_map, recent_history, feedback=feedback)
        try:
            raw = _call_gemini_with_fallback(client, prompt)
        except Exception as e:
            # 이미 여러 바퀴 재시도한 뒤의 실패 — 서버 문제이므로 더 두드리지 않고 인프라 오류로 알린다
            # (게이트 미달이 아니므로 카드의 연속 실패 횟수에는 들어가지 않는다)
            print(f"  ⚠️ Gemini 생성 실패({attempt + 1}/{MAX_ATTEMPTS}): {e}")
            raise RuntimeError(f"Gemini 응답을 받지 못했습니다. 마지막 에러: {e}")

        sections = _parse_sections(raw)
        if sections is None:
            print(f"  ⚠️ 응답 형식 오류({attempt + 1}/{MAX_ATTEMPTS}) — 구분자 누락")
            feedback = ("직전 응답이 지정된 구분자(<!--TITLE_START--> 등) 형식을 지키지 않았습니다. "
                        "다른 설명 없이 지정된 구분자 형식 그대로만 출력하세요.")
            continue

        ever_parsed = True
        optional = _parse_optional(raw)
        problems, total_len = check_gates(card, fact_map, sections, optional)
        if not problems:
            return sections, optional, total_len

        print(f"  ⚠️ 게이트 미달({attempt + 1}/{MAX_ATTEMPTS}): {' / '.join(problems)}")
        feedback = ("직전 결과가 다음 기준을 충족하지 못했습니다 — " + " / ".join(problems) +
                    ". 카드와 확인된 사실 안의 내용만 사용하고, 숫자와 기관 이름은 허용된 것만 쓰세요. "
                    "목록 개수는 카드와 정확히 같게 하고, 분량은 새 사실이 아니라 독자의 상황에 대한 설명으로 "
                    "보강해서 다시 작성하세요.")

    if not ever_parsed:
        raise RuntimeError("Gemini 응답이 매번 지정한 구분자 형식을 지키지 않아 파싱하지 못했습니다.")
    print("  ❌ 게이트를 끝내 통과하지 못해 이번 카드는 발행을 보류합니다(인프라 문제 아님).")
    raise ContentQualityError(card["id"])


# ─────────────────────────────────────────
# 글 조립 — 소제목·비교표·확인할 기관·근거 자료는 코드가 카드/사실표에서 직접 만든다
# ─────────────────────────────────────────
_H2_TITLES = [
    "오늘 먼저 할 일",
    "선택지 한눈에 비교",
    "이럴 땐 이렇게 — 상황별로 달라지는 점",
    "선택 후 밟는 순서",
    "확인할 기관",
]


def _e(text):
    return html.escape(str(text), quote=True)


def _build_toc():
    items = "".join(f'<li><a href="#wh-s{i + 1}">{_e(t)}</a></li>' for i, t in enumerate(_H2_TITLES))
    return f'<div class="box-toc"><div class="box-label">📚 목차</div><ol>{items}</ol></div>'


def _build_options_table(card):
    head = "<thead><tr><th>선택지</th><th>이럴 때 맞습니다</th><th>장점</th><th>단점·주의</th></tr></thead>"
    rows = "".join(
        f"<tr><td><span class=\"act\">{_e(o['name'])}</span></td><td>{_e(o['fits_when'])}</td>"
        f"<td>{_e(o['pros'])}</td><td>{_e(o['cons'])}</td></tr>"
        for o in card["options"]
    )
    return f'<div class="tbl-wrap"><table class="opt-table">{head}<tbody>{rows}</tbody></table></div>'


def _build_agencies(card):
    items = "".join(f"<li><span class=\"act\">{_e(a['name'])}</span> — {_e(a['role'])}</li>" for a in card["agencies"])
    return f"<ul>{items}</ul>"


def _korean_date(iso):
    y, m, d = iso.split("-")
    return f"{int(y)}년 {int(m)}월 {int(d)}일"


def _build_sources(card, fact_map):
    """같은 주소는 한 줄로 묶는다. 법령 조문은 '노인장기요양보험법 제12조·제13조…' 형태로 합친다."""
    groups = {}                      # 주소 → 출처 문자열 목록 (입력 순서 유지)
    for key in card["fact_refs"]:
        f = fact_map[key]
        src = f.get("source", "")
        if not src:
            continue
        groups.setdefault(f.get("source_url", ""), []).append(src)

    items = []
    for url, srcs in groups.items():
        law_nums, others = [], []
        for src in srcs:
            for part in (p.strip() for p in src.split(",")):
                if not part:
                    continue
                if part.startswith("노인장기요양보험법") or re.match(r"^제\d+조", part):   # "법 제2조, 제12조"의 뒤쪽 조문도 법령으로 묶음
                    for n in re.findall(r"제(\d+)조", part):
                        if n not in law_nums:
                            law_nums.append(n)
                elif part not in others:
                    others.append(part)
        label_parts = []
        if law_nums:
            label_parts.append("노인장기요양보험법 " + "·".join(f"제{n}조" for n in sorted(law_nums, key=int)))
        label_parts += others
        label = ", ".join(label_parts)
        link = f' (<a href="{_e(url)}">원문 보기</a>)' if url else ""
        items.append(f"<li>{_e(label)}{link}</li>")
    return ('<div class="ref-block"><div class="box-label">📎 이 글의 근거 자료</div><ul>'
            + "".join(items) + "</ul></div>") if items else ""


def _build_related(card, state_history):
    by_id = {h.get("card_id"): h for h in state_history if h.get("card_id") and h.get("url")}
    items = []
    for rid in card.get("related_ids") or []:
        h = by_id.get(rid)
        if h:
            items.append(f'<li><a href="{_e(h["url"])}">{_e(h["title"])}</a></li>')
    if not items:
        return ""
    return ('<div class="card"><span class="badge">📖 같은 상황의 다른 글</span><ul>'
            + "".join(items) + "</ul></div>")


def assemble_html(card, fact_map, title, sections, optional, state_history):
    verified = max(fact_map[k]["verified_at"] for k in card["fact_refs"])
    notice = (f'<div class="notice">정보 기준일: {_korean_date(verified)} · 이 글은 일반적인 정보이며 '
              f'법령과 제도는 바뀔 수 있으므로 최종 확인은 해당 기관에서 하시기 바랍니다.</div>')

    summary_html = (f'<div class="box-summary"><div class="box-label">📌 한줄요약</div>{optional["summary"]}</div>'
                    if optional.get("summary") else "")
    closingq_html = f'<p class="closing-q">💬 {_e(_visible_text(optional["closingq"]))}</p>' if optional.get("closingq") else ""

    tags = [card["topic"]] + list(card.get("tags") or []) + [card["situation"], "돌봄상식", "이럴 땐 이렇게"]
    tag_html = "".join(f'<span class="tag">{_e(t)}</span>' for t in tags)

    series_url = f"{_BLOG_BASE}/search/label/{quote(SERIES_LABEL)}"
    know_url = f"{_BLOG_BASE}/search/label/{quote('돌봄상식')}"
    link_style = ("display:inline-block;background:linear-gradient(135deg,{g});color:#fff;padding:8px 16px;"
                  "border-radius:20px;font-size:12px;font-weight:700;text-decoration:none;margin:4px")
    related_links = (
        f'<a href="{series_url}" style="{link_style.format(g="#3F5D45,#6B8E6E")}">🧭 이럴 땐 이렇게 모아보기</a>'
        f'<a href="{know_url}" style="{link_style.format(g="#2563A6,#4C8FD1")}">📋 돌봄상식 모아보기</a>'
    )

    return f"""{when_style()}
<div class="wrap">
  <div class="hero">
    <h1>🧭 {_e(title)}</h1>
    <p>이럴 땐 이렇게 · {_e(card['situation'])}</p>
  </div>
  {notice}
  <div class="card">
    <div class="intro">{sections['intro']}</div>
    {summary_html}
    {_build_toc()}
    <h2 id="wh-s1">{_H2_TITLES[0]}</h2>
    {sections['actions']}
    <h2 id="wh-s2">{_H2_TITLES[1]}</h2>
    {_build_options_table(card)}
    {sections['options']}
    <h2 id="wh-s3">{_H2_TITLES[2]}</h2>
    {sections['branches']}
    <h2 id="wh-s4">{_H2_TITLES[3]}</h2>
    {sections['steps']}
  </div>
  <div class="card">
    {sections['closing']}
  </div>
  <div class="card"><span class="badge">🙋 자주 묻는 질문</span>
    {sections['faq']}
  </div>
  <div class="card">
    <h2 id="wh-s5">{_H2_TITLES[4]}</h2>
    {_build_agencies(card)}
    {_build_sources(card, fact_map)}
    {closingq_html}
  </div>
  {_build_related(card, state_history)}
  <div class="card"><span class="badge">🔍 관련 키워드</span>
    <div class="tag-cloud">{tag_html}</div>
  </div>
  <div class="card" style="text-align:center;padding:16px">
    <p style="font-size:12px;color:#9ca3af;margin:0 0 12px">🔗 더 궁금하시다면</p>
    {related_links}
  </div>
  <div class="meta"><p>※ 참고용으로 정리한 정보성 콘텐츠이며 의료·법률 상담을 대신하지 않습니다. 정확한 최신 기준은 관련 기관에 별도로 확인하시기 바랍니다</p></div>
</div>"""


# ─────────────────────────────────────────
# 실행
# ─────────────────────────────────────────
def run(count=1, dry_run=False, forced_id=None):
    """(발행 성공 수, 인프라 실패 여부)를 돌려준다."""
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)
    if not dry_run and not BLOG_ID:
        print("❌ BLOG_ID 환경변수가 없습니다 — bumodolbom.blogspot.com 의 blogId 를 설정하세요.")
        sys.exit(1)

    cards, fact_map = load_cards_and_facts()
    state = load_state()
    year = _now_kst().year

    access_token = ""
    if not dry_run:
        access_token = get_access_token()
        if not access_token:
            print("❌ Blogger 인증 실패 — 발행을 진행할 수 없습니다.")
            sys.exit(1)

    success_count = 0
    hard_failure = False
    if dry_run:
        count = 1

    for i in range(count):
        card = pick_card(cards, fact_map, state, year, forced_id=forced_id, allow_draft=dry_run)
        if card is None:
            if forced_id:
                hard_failure = True
            else:
                print("ℹ️ 발행할 수 있는 verified 카드가 없습니다 (카드 status 와 사실표 확인일을 확인하세요).")
            break

        print(f"[{i + 1}/{count}] 카드 '{card['id']}' / 상황: {card['situation']} / 주제: {card['topic']}")
        recent_history = [
            {"title": h.get("title"), "first_words": h.get("first_words")}
            for h in state["history"][-8:] if h.get("title")
        ]

        try:
            sections, optional, total_len = generate_post(card, fact_map, recent_history)
        except ContentQualityError:
            if not dry_run:
                fails = state["fail_counts"].get(card["id"], 0) + 1
                state["fail_counts"][card["id"]] = fails
                state["last_situation"] = card["situation"]  # 같은 카드에 계속 멈추지 않도록 다음 상황으로 넘김
                if fails >= REVIEW_AFTER_FAILS and card["id"] not in state["needs_review"]:
                    state["needs_review"].append(card["id"])
                    print(f"  🔎 카드 '{card['id']}' 가 {fails}회 연속 게이트를 넘지 못해 needs_review 로 뺍니다. "
                          f"카드 내용을 고친 뒤 state 의 needs_review 에서 이 id 를 지우면 다시 대상이 됩니다.")
                save_state(state)
            continue
        except Exception as e:
            print(f"  ⚠️ 카드 '{card['id']}' 생성 중 인프라 오류: {e} — 이번 카드는 건너뜁니다.")
            hard_failure = True
            continue

        post_title = _visible_text(sections["title"]) or card["topic"]
        content = assemble_html(card, fact_map, post_title, sections, optional, state["history"])

        if dry_run:
            os.makedirs(PREVIEW_DIR, exist_ok=True)
            out_path = os.path.join(PREVIEW_DIR, f"{card['id']}.html")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  📝 미리 보기 저장: {out_path} (글자수 {total_len}자, 발행하지 않음)")
            success_count += 1
            break

        slug_number = state["next_slug_number"]
        ok, post_url = post_blogger(access_token, post_title, content, [SERIES_LABEL, card["situation"]], slug_number)
        if ok:
            state["published"].append(card["id"])
            state["next_slug_number"] = slug_number + 1
            state["last_situation"] = card["situation"]
            state["fail_counts"].pop(card["id"], None)
            state["history"].append({
                "card_id":     card["id"],
                "situation":   card["situation"],
                "title":       post_title,
                "url":         post_url,
                "slug":        str(slug_number),
                "char_count":  total_len,
                "posted_at":   datetime.now(timezone.utc).isoformat(),
                "first_words": _first_words(sections["intro"]),
            })
            save_state(state)
            success_count += 1
        else:
            print(f"  ❌ '{post_title}' 발행 실패 — 상태를 저장하지 않습니다. 다음 실행 때 같은 카드부터 다시 시도합니다.")
            hard_failure = True
            break

        if i < count - 1:
            time.sleep(5)

    return success_count, hard_failure


def main():
    parser = argparse.ArgumentParser(description="'이럴 땐 이렇게' 시리즈 자동 생성/발행")
    parser.add_argument("--count", type=int, default=1, help="이번 실행에서 발행할 글 개수 (기본 1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="발행하지 않고 글만 만들어 data/preview/ 에 저장 (상태 파일도 바꾸지 않음)")
    parser.add_argument("--card", default=None, help="특정 카드 id 로 실행 (draft 카드는 --dry-run 에서만 가능)")
    args = parser.parse_args()

    print(f"🚀 이럴 땐 이렇게 시작 — {'미리 보기' if args.dry_run else str(args.count) + '개'}")
    success_count, hard_failure = run(args.count, dry_run=args.dry_run, forced_id=args.card)

    if success_count == 0:
        if hard_failure:
            print("❌ 이번 실행에서 성공한 글이 하나도 없습니다 (Gemini/Blogger 인프라 오류 또는 잘못된 카드 지정).")
            sys.exit(1)
        print("ℹ️ 이번 실행은 발행하지 않았습니다 (대상 카드 없음 또는 게이트 미달 보류). 정상 종료합니다.")
        return

    print(f"🎉 완료 — {success_count}개 {'미리 보기 생성' if args.dry_run else '발행'}")


if __name__ == "__main__":
    main()
