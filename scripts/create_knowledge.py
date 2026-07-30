#!/usr/bin/env python3
"""
create_knowledge.py — '운세상식' 카테고리 정보성 글 자동 생성/발행
=======================================================================
기존 create_post.py(CSV 기반 매일 운세 27개 자동화)와 완전히 독립된 스크립트입니다.

  - create_post.py는 import하지 않습니다. (import하면 CSV 로딩·토큰 발급 등
    create_post.py 최상단 코드가 전부 같이 실행되어 버립니다.)
  - Blogger 인증 코드는 create_post.py의 get_access_token()과 같은 로직을
    여기 복사해서 씁니다.
  - 발행 함수 이름도 post_blogger_scheduled()로 만들어, 기존 post_blogger()와
    이름이 겹치지 않게 했습니다. (같은 파일이 아니라 다른 파일이라 어차피
    충돌은 안 나지만, 나중에 두 파일을 한 곳에서 참고할 때 헷갈리지 않도록.)
  - 기존 CSV(zodiac_fortune_1000.csv 등)는 전혀 읽지도, 쓰지도 않습니다.
    이 스크립트가 새로 만드는 파일은 data/knowledge_state.json 하나뿐이고,
    이건 '어느 주제까지 발행했는지' 기록하는 용도의 신규 파일입니다.

실행:
  python scripts/create_knowledge.py             # 1개 생성/발행 (주간 cron 기본값)
  python scripts/create_knowledge.py --count 5   # 초기 시드 배치용 — 5개 연속 생성/발행

환경변수:
  GEMINI_API_KEY                                  (필수 — Google AI Studio에서 발급)
  BLOG_ID, BLOGGER_REFRESH_TOKEN,
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET           (필수 — 기존 시크릿 재사용)
  DATA_DIR                                        (기본: ./data)
"""

import os
import sys
import json
import csv
import time
import argparse
from datetime import datetime, timezone

import requests
from google import genai

# ─────────────────────────────────────────
# 인증 — create_post.py의 get_access_token()과 동일한 로직을 복사
# (import 아님. create_post.py 파일은 이 스크립트에서 한 번도 열리지 않음)
# ─────────────────────────────────────────
BLOG_ID        = os.environ.get("BLOG_ID", "")
REFRESH_TOKEN  = os.environ.get("BLOGGER_REFRESH_TOKEN", "")
CLIENT_ID      = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET  = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

DATA_DIR   = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
STATE_PATH = os.path.join(DATA_DIR, "knowledge_state.json")
COUPANG_LINKS_PATH = os.path.join(DATA_DIR, "coupang_links.csv")


def get_access_token_for_knowledge():
    """Blogger access token 발급 — create_post.py의 get_access_token()과 같은 로직."""
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


def post_blogger_scheduled(access_token, title, content, labels, published_iso=None):
    """운세상식 전용 발행 함수 — 기존 post_blogger()는 절대 건드리지 않고 별도로 둠.
    published_iso를 주면 예약 발행, 생략하면 즉시 발행 (지금 구조는 즉시 발행만 사용)."""
    if not BLOG_ID or not access_token:
        print(f"(테스트 모드 — BLOG_ID/토큰 없음) {title}")
        return True

    url  = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    body = {"title": title, "content": content, "labels": labels}
    if published_iso:
        body["published"] = published_iso

    for attempt in range(1, 4):  # 최대 3회 재시도 (기존 post_blogger()와 동일한 패턴)
        resp = requests.post(url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=body)
        if resp.status_code in (200, 201):
            print(f"✅ 발행 완료 — {title}")
            return True
        elif resp.status_code == 429:
            wait = 60 * attempt
            print(f"⏳ 429 쿼터 초과 — {wait}초 대기 후 재시도 ({attempt}/3)")
            time.sleep(wait)
        else:
            print(f"❌ 발행 실패 ({resp.status_code}): {resp.text[:150]}")
            return False

    print("❌ 3회 재시도 후 실패")
    return False


# ─────────────────────────────────────────
# 사이트 톤 유지용 최소 스타일
# (create_post.py의 style() 함수에서 이 글에 필요한 부분만 그대로 복사.
#  share-sheet, html2canvas 등 이미지 저장 기능은 이 콘텐츠 타입에 필요 없어 제외)
# ─────────────────────────────────────────
def knowledge_style():
    return """<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Noto Sans KR',sans-serif;background:#f8f9ff;color:#333;padding:16px}
.wrap{max-width:720px;margin:auto}
.hero{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border-radius:18px;padding:36px 24px;text-align:center;margin-bottom:22px}
.hero h1{font-size:24px;margin-bottom:8px}
.hero p{opacity:.85;font-size:14px}
.card{background:#fff;border-radius:14px;padding:26px 24px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.07)}
.card h2{font-size:18px;color:#4c1d95;margin:22px 0 10px}
.card h2:first-child{margin-top:0}
.card p{font-size:15px;line-height:1.9;color:#374151;margin-bottom:14px}
.badge{display:inline-block;background:#f0eaff;color:#6c3483;padding:3px 10px;border-radius:20px;font-size:12px;margin-bottom:10px}
.tag-cloud{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.tag{background:#eef2ff;color:#5c6bc0;padding:4px 10px;border-radius:20px;font-size:11px}
.meta{color:#aaa;font-size:12px;text-align:center;padding:20px 0}
</style>"""


# ─────────────────────────────────────────
# 운세상식 주제 리스트 — CSV 아니고 여기 파이썬 리스트로 직접 관리.
# 더 추가하고 싶으면 이 리스트에 딕셔너리만 이어서 넣으면 됨.
# ─────────────────────────────────────────
# ─────────────────────────────────────────
# 하단 관련 콘텐츠 링크 3개 — 운세상식은 띠/별자리 양쪽 다 다루는 주제라
# 두 일간 운세 카테고리 + 특별 콘텐츠(별과띠가만나는시간) 조합으로 고정.
# (label, url, gradient) — url은 실제 create_post.py가 붙이는 라벨과 정확히 일치해야 함
# ─────────────────────────────────────────
_RELATED_LINKS = [
    ("🐉 오늘의 띠운세",
     "https://todayhoroscopelaboratory.blogspot.com/search/label/%EB%9D%A0%EC%9A%B4%EC%84%B8",
     "#7c2d12,#ea580c"),
    ("⭐ 오늘의 별자리운세",
     "https://todayhoroscopelaboratory.blogspot.com/search/label/%EB%B3%84%EC%9E%90%EB%A6%AC%EC%9A%B4%EC%84%B8",
     "#1e3a5f,#2563eb"),
    ("✨ 별과 띠가 만나는 시간",
     "https://todayhoroscopelaboratory.blogspot.com/search/label/%EB%B3%84%EA%B3%BC%EB%9D%A0%EA%B0%80%EB%A7%8C%EB%82%98%EB%8A%94%EC%8B%9C%EA%B0%84",
     "#4c1d95,#7c3aed"),
]

TOPICS = [
    {"topic": "지혜롭고 부지런한 소띠의 4가지 성격 특징",   "emoji": "🐮", "tags": ["소띠", "띠별성격", "사주"]},
    {"topic": "꾀 많고 영리한 쥐띠의 반전 성격과 특징",       "emoji": "🐭", "tags": ["쥐띠", "띠별성격", "사주"]},
    {"topic": "용맹하고 열정적인 호랑이띠의 성격 분석",       "emoji": "🐯", "tags": ["호랑이띠", "띠별성격", "사주"]},
    {"topic": "물병자리에 숨겨진 그리스 신화 이야기",         "emoji": "♒", "tags": ["물병자리", "별자리유래", "그리스신화"]},
    {"topic": "사자자리의 유래와 밤하늘에 얽힌 전설",         "emoji": "♌", "tags": ["사자자리", "별자리유래", "그리스신화"]},
    {"topic": "복을 부르는 현관 인테리어와 거울 위치",         "emoji": "🚪", "tags": ["풍수", "현관인테리어", "풍수지리"]},
    {"topic": "재물운을 높이는 침실 침대 방향과 풍수지리",     "emoji": "🛏️", "tags": ["풍수", "침실풍수", "재물운"]},
    {"topic": "행운의 색이 알려주는 나만의 기운 이야기",       "emoji": "🎨", "tags": ["행운의색", "색채심리", "운세상식"]},
    {"topic": "태어난 달로 알아보는 탄생석의 의미",           "emoji": "💎", "tags": ["탄생석", "탄생석의미", "보석상식"]},
    {"topic": "재물운을 부르는 지갑 색깔과 정리 습관",         "emoji": "🪙", "tags": ["지갑풍수", "재물운", "정리습관"]},
    {"topic": "별자리별 잘 어울리는 향수 노트 찾기",           "emoji": "🌸", "tags": ["별자리향수", "향수추천", "별자리매칭"]},
    {"topic": "이사할 때 챙기면 좋은 손없는 날과 개운 소품",   "emoji": "🧂", "tags": ["손없는날", "이사풍수", "개운소품"]},
    {"topic": "수험생 자녀를 둔 부모를 위한 합격운 높이는 방법", "emoji": "📚", "tags": ["합격운", "수험생", "학부모"]},
    {"topic": "이직·취업 준비생을 위한 취업운 체크리스트",     "emoji": "💼", "tags": ["취업운", "이직", "구직"]},
    {"topic": "신혼부부를 위한 재물운 부르는 인테리어",         "emoji": "🏠", "tags": ["신혼부부", "재물운", "인테리어풍수"]},
]

# 쿠팡파트너스 필수 고지 문구 (정보통신망법 — 게시물 최상단에 위치해야 함)
_COUPANG_DISCLOSURE = (
    "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
)


def build_prompt(topic, style="info"):
    base = f"""당신은 사주·별자리·풍수 등 전통·점성 문화를 알기 쉽게 설명하는 블로그 필자입니다.
아래 주제로 블로그 정보성 글을 작성해 주세요.

주제: {topic}

[구조 규칙 — 검색해서 들어온 독자가 원하는 건 이야기가 아니라 정보입니다]
1. 순수 HTML 조각만 출력하세요. <html>, <head>, <body> 태그나 코드블록(```)은 절대 포함하지 마세요.
2. 소제목은 <h2>, 문단은 <p> 태그를 사용하세요. 마크다운 기호(##, **)는 사용하지 마세요.
3. 전체 분량은 공백 제외 1,500자 이상으로 풍성하게 작성하세요.
4. <h2> 소제목 3개 내외로 구성하세요 (도입 → 본론 2~3개 → 마무리). 소제목만 훑어봐도 글의 핵심이 파악되게 하세요.
5. "💭" 같은 감정 이모지나 "오늘 이야기를 들려드리겠습니다" 식의 이야기체 도입은 쓰지 마세요. 이 글은 매일 바뀌는 개인 운세가 아니라, 검색해서 정보를 찾는 독자를 위한 글입니다.

[문장 톤 규칙 — 정보를 나열하되 사람이 관찰하고 쓴 것처럼]
6. 어조는 "~합니다", "~해보세요"체의 다정하고 담백한 존댓말을 사용하세요. "~에요", "~죠", "~잖아요" 같은 구어체는 쓰지 마세요.
7. 첫 문단은 사전적 정의("○○는 ~한 성격입니다")로 시작하지 말고, 일상에서 마주칠 법한 구체적인 장면이나 관찰로 여세요.
   예시: "회사에서 유독 야근을 마다 않고 묵묵히 일을 끝내는 동료가 있다면, 소띠일 가능성이 높습니다." 처럼
   추상적 설명이 아니라 눈에 그려지는 상황에서 시작하세요. 이런 구체적 장면 열기는 도입부뿐 아니라
   본론의 각 <h2> 섹션 첫 문장에도 최소 1곳 이상 적용하세요.
8. "A는 ~합니다. 또한 B합니다. 그리고 C합니다." 같은 단순 나열식 문장 반복은 피하세요. 문장 길이와 구조를
   문단마다 다르게 가져가세요 (짧은 문장과 긴 문장을 섞고, 이유·비유·예시를 번갈아 사용하세요).
9. 같은 문장 종결 패턴이 두 문장 이상 연속으로 이어지지 않게 하세요.
10. 첫 <p> 문단 안에 이 주제와 어울리는 짧은 격언이나 속담을 자연스럽게 녹여서 함께 배치하세요.
11. 마지막 문단은 독자를 다정하게 응원하는 한두 문장으로 마무리하세요.
12. 사실 관계(신화, 유래, 방위 등)는 무리해서 확신하지 말고 통상적으로 알려진 내용 위주로 서술하세요."""

    if style == "checklist":
        base += """
13. 이 글은 특정 상황(수험생 학부모, 이직 준비생, 신혼부부 등)에 놓인 독자를 위한 실천 가이드입니다.
    본론 소제목 중 최소 하나는 <ul><li> 목록을 사용해 바로 실천할 수 있는 행동 체크리스트 3~5개를
    제시하세요 (예: "오늘부터 해볼 수 있는 것 3가지"). 다만 목록만으로 소제목을 채우지 말고,
    목록 앞뒤에 설명 문단을 붙여 정보성 글의 구조(도입 → 본론 → 마무리)는 그대로 유지하세요."""

    return base


# 우선순위 순서 — 맨 앞이 실패하면 다음 것을 자동으로 시도.
# gemini-2.5-flash가 2026-07-09부터 예고 없이 404를 반환하기 시작한 사례가 있어서
# (공식 종료 예정일은 2026-10-16이었는데 그보다 훨씬 앞서 막힘), 모델 하나에만
# 의존하지 않도록 대체 모델을 같이 둠.
GEMINI_MODEL_CANDIDATES = [
    "gemini-3.1-flash-lite",
    "gemini-3-flash",
    "gemini-flash-latest",
]


def generate_knowledge_html(topic, style="info"):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = build_prompt(topic, style=style)
    last_err = None

    for model_name in GEMINI_MODEL_CANDIDATES:
        try:
            resp = client.models.generate_content(model=model_name, contents=prompt)
            text = (resp.text or "").strip()
            if not text:
                raise ValueError("빈 응답")
            # 혹시 모델이 코드블록으로 감싸서 응답하면 제거
            text = text.replace("```html", "").replace("```", "").strip()
            return text
        except Exception as e:
            print(f"  ⚠️ 모델 '{model_name}' 실패: {e} — 다음 후보로 재시도합니다.")
            last_err = e

    raise RuntimeError(f"모든 Gemini 모델 후보가 실패했습니다. 마지막 에러: {last_err}")


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_index": -1, "history": []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_coupang_links():
    """coupang_links.csv를 인덱스 기준으로 읽어온다. (index, product_keyword, coupang_url)
    파일이 없거나 특정 인덱스 행이 없어도 에러 없이 빈 값으로 처리 — coupang_url이 비어있으면
    광고 카드 없이 평소처럼 발행된다. 이 파일은 코드 수정 없이 GitHub에서 직접 편집하는 용도.

    인코딩은 여러 개를 순서대로 시도한다 — 엑셀(특히 한글 윈도우)에서 저장하면 UTF-8이 아니라
    CP949로 저장되는 경우가 흔해서, 사람이 매번 인코딩을 신경 쓰지 않아도 되게 방어적으로 처리."""
    links = {}
    if not os.path.exists(COUPANG_LINKS_PATH):
        return links

    raw = None
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            with open(COUPANG_LINKS_PATH, "r", encoding=enc) as f:
                raw = f.read()
            break
        except UnicodeDecodeError:
            continue

    if raw is None:
        print(f"  ⚠️ {COUPANG_LINKS_PATH} 인코딩을 인식할 수 없습니다 — 쿠팡 링크 없이 진행합니다.")
        return links

    for row in csv.DictReader(raw.splitlines()):
        try:
            idx = int((row.get("index") or "").strip())
        except (ValueError, AttributeError):
            continue
        links[idx] = {
            "product_keyword": (row.get("product_keyword") or "").strip(),
            "coupang_url":     (row.get("coupang_url") or "").strip(),
        }
    return links


def run(count=1):
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)

    access_token = get_access_token_for_knowledge()
    if not access_token:
        print("❌ Blogger 인증 실패 — 발행을 진행할 수 없습니다.")
        sys.exit(1)

    state = load_state()
    coupang_links = load_coupang_links()
    n = len(TOPICS)
    success_count = 0

    for i in range(count):
        idx  = (state["last_index"] + 1) % n
        item = TOPICS[idx]
        topic, emoji, tags = item["topic"], item["emoji"], item["tags"]
        _cp = coupang_links.get(idx, {})
        coupang_url     = _cp.get("coupang_url", "")
        product_keyword = _cp.get("product_keyword", "")

        # 특정 상황(수험생 학부모/이직/신혼부부) 타겟 주제는 체크리스트형 프롬프트로
        style = "checklist" if any(t in {"합격운", "취업운", "신혼부부"} for t in tags) else "info"

        cycle_note = " (주제 리스트를 모두 사용해 처음부터 다시 순환합니다)" \
            if idx == 0 and state["last_index"] != -1 else ""
        print(f"[{i+1}/{count}] 주제 #{idx}: {topic}{cycle_note}")

        try:
            body_html = generate_knowledge_html(topic, style=style)
        except Exception as e:
            print(f"  ⚠️ Gemini 생성 실패: {e} — 이 주제는 건너뜁니다.")
            continue

        if len(body_html) < 300:
            print(f"  ⚠️ 생성된 글이 너무 짧습니다 ({len(body_html)}자) — 발행을 건너뜁니다.")
            continue

        kw_list  = [topic] + tags + ["운세상식"]
        tag_html = "".join(f'<span class="tag">{t}</span>' for t in kw_list)

        related_html = "".join(
            f'<a href="{url}" style="display:inline-block;background:linear-gradient(135deg,{grad});'
            f'color:#fff;padding:8px 16px;border-radius:20px;font-size:12px;font-weight:700;'
            f'text-decoration:none;margin:4px">{label}</a>'
            for label, url, grad in _RELATED_LINKS
        )

        # 쿠팡 링크가 채워진 주제에만 고지문구 + 상품 카드 렌더링.
        # coupang_url이 비어있으면(아직 링크 안 만든 주제) 평소처럼 이 두 블록 없이 발행됨.
        disclosure_html = ""
        product_html = ""
        if coupang_url:
            disclosure_html = (
                f'<div class="card" style="background:#fffbeb;border:1px solid #fde68a;'
                f'padding:12px 16px;font-size:12px;color:#92400e;margin-bottom:16px">'
                f'{_COUPANG_DISCLOSURE}</div>'
            )
            product_html = f"""
  <div class="card" style="text-align:center;padding:20px">
    <p style="font-size:12px;color:#9ca3af;margin:0 0 10px">🛒 이런 상품은 어떠세요</p>
    <a href="{coupang_url}" style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#ea580c);
       color:#fff;padding:10px 22px;border-radius:20px;font-size:13px;font-weight:700;
       text-decoration:none">{product_keyword or '관련 상품'} 보러가기</a>
  </div>"""

        content = f"""{knowledge_style()}
<div class="wrap">
  <div class="hero">
    <h1>{emoji} {topic}</h1>
    <p>운세 상식</p>
  </div>
  {disclosure_html}
  <div class="card">
    {body_html}
  </div>
  {product_html}
  <div class="card"><span class="badge">🔍 관련 키워드</span>
    <div class="tag-cloud">{tag_html}</div>
  </div>
  <div class="card" style="text-align:center;padding:16px">
    <p style="font-size:12px;color:#9ca3af;margin:0 0 12px">🔗 더 궁금하시다면</p>
    {related_html}
  </div>
  <div class="meta"><p>※ 참고용으로 정리한 정보성 콘텐츠입니다</p></div>
</div>"""

        ok = post_blogger_scheduled(access_token, topic, content, ["운세상식"])

        if ok:
            state["last_index"] = idx
            state["history"].append({
                "index":     idx,
                "topic":     topic,
                "posted_at": datetime.now(timezone.utc).isoformat(),
            })
            save_state(state)
            success_count += 1
        else:
            print(f"  ❌ '{topic}' 발행 실패 — 인덱스를 저장하지 않습니다. "
                  f"다음 실행 때 같은 주제부터 다시 시도합니다.")
            break

        if i < count - 1:
            time.sleep(5)  # Gemini + Blogger 쿼터 보호

    return success_count


def main():
    parser = argparse.ArgumentParser(description="운세상식 카테고리 자동 생성/발행")
    parser.add_argument("--count", type=int, default=1,
                         help="이번 실행에서 생성할 글 개수 (기본 1, 초기 시드 배치는 --count 10 처럼 크게)")
    args = parser.parse_args()

    print(f"🚀 운세상식 생성 시작 — {args.count}개")
    success_count = run(args.count)

    if success_count == 0:
        # 한 개도 성공 못 했으면 실패로 종료 — 이후 git commit 단계가 애매하게
        # "커밋할 파일 없음"으로 죽는 대신, 여기서 원인이 명확한 실패로 끝나야 함
        print("❌ 이번 실행에서 발행에 성공한 글이 하나도 없습니다.")
        sys.exit(1)

    print(f"🎉 완료 — {success_count}개 발행")


if __name__ == "__main__":
    main()
