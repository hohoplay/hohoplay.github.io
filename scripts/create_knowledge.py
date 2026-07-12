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
    {"topic": "숫자에 담긴 동서양의 길흉 상징 이야기",         "emoji": "🔢", "tags": ["숫자의미", "길흉", "운세상식"]},
    {"topic": "사주팔자란 무엇일까, 기초부터 알아보기",       "emoji": "🀄", "tags": ["사주팔자", "동양점술", "기초상식"]},
    {"topic": "별자리 점성술은 어떻게 시작되었을까",           "emoji": "⭐", "tags": ["점성술기원", "서양점성술", "별자리역사"]},
]


def build_prompt(topic):
    return f"""당신은 사주·별자리·풍수 등 전통·점성 문화를 알기 쉽게 설명하는 블로그 필자입니다.
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


def generate_knowledge_html(topic):
    client = genai.Client(api_key=GEMINI_API_KEY)
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_prompt(topic),
    )
    text = (resp.text or "").strip()
    # 혹시 모델이 코드블록으로 감싸서 응답하면 제거
    text = text.replace("```html", "").replace("```", "").strip()
    return text


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_index": -1, "history": []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def run(count=1):
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)

    access_token = get_access_token_for_knowledge()
    if not access_token:
        print("❌ Blogger 인증 실패 — 발행을 진행할 수 없습니다.")
        sys.exit(1)

    state = load_state()
    n = len(TOPICS)

    for i in range(count):
        idx  = (state["last_index"] + 1) % n
        item = TOPICS[idx]
        topic, emoji, tags = item["topic"], item["emoji"], item["tags"]

        cycle_note = " (주제 리스트를 모두 사용해 처음부터 다시 순환합니다)" \
            if idx == 0 and state["last_index"] != -1 else ""
        print(f"[{i+1}/{count}] 주제 #{idx}: {topic}{cycle_note}")

        try:
            body_html = generate_knowledge_html(topic)
        except Exception as e:
            print(f"  ⚠️ Gemini 생성 실패: {e} — 이 주제는 건너뜁니다.")
            continue

        if len(body_html) < 300:
            print(f"  ⚠️ 생성된 글이 너무 짧습니다 ({len(body_html)}자) — 발행을 건너뜁니다.")
            continue

        kw_list  = [topic] + tags + ["운세상식"]
        tag_html = "".join(f'<span class="tag">{t}</span>' for t in kw_list)

        content = f"""{knowledge_style()}
<div class="wrap">
  <div class="hero">
    <h1>{emoji} {topic}</h1>
    <p>운세 상식</p>
  </div>
  <div class="card">
    {body_html}
  </div>
  <div class="card"><span class="badge">🔍 관련 키워드</span>
    <div class="tag-cloud">{tag_html}</div>
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
        else:
            print(f"  ❌ '{topic}' 발행 실패 — 인덱스를 저장하지 않습니다. "
                  f"다음 실행 때 같은 주제부터 다시 시도합니다.")
            break

        if i < count - 1:
            time.sleep(5)  # Gemini + Blogger 쿼터 보호


def main():
    parser = argparse.ArgumentParser(description="운세상식 카테고리 자동 생성/발행")
    parser.add_argument("--count", type=int, default=1,
                         help="이번 실행에서 생성할 글 개수 (기본 1, 초기 시드 배치는 --count 10 처럼 크게)")
    args = parser.parse_args()

    print(f"🚀 운세상식 생성 시작 — {args.count}개")
    run(args.count)
    print("🎉 완료")


if __name__ == "__main__":
    main()
