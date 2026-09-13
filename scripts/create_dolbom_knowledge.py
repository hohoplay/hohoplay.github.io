#!/usr/bin/env python3
"""
create_dolbom_knowledge.py — '돌봄상식' 카테고리 정보성 글 자동 생성/발행
=======================================================================
운세상식(create_knowledge.py)과 완전히 같은 구조·같은 인증 방식을 그대로
복제해서, 대상 블로그만 bumodolbom.blogspot.com(돌봄상식)으로 바꾼 스크립트입니다.

  - create_post.py, create_knowledge.py 어느 쪽도 import하지 않습니다.
    (import하면 그 파일 최상단 코드가 전부 같이 실행됨)
  - Blogger 인증(get_access_token) 로직은 두 기존 스크립트와 동일하게 복사해서 씁니다.
    BLOG_ID, BLOGGER_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET는
    "이 계정이 가진 모든 블로그"에 걸리는 권한이라 새로 발급할 필요 없이 그대로
    재사용합니다. 실제로 바뀌는 값은 BLOG_ID 딱 하나(이 블로그의 ID)뿐입니다.
  - 다른 스크립트가 쓰는 어떤 CSV·상태파일도 읽거나 쓰지 않습니다. 이 스크립트가
    새로 만드는 파일은 data/dolbom_knowledge_state.json 하나뿐입니다.

실행:
  python scripts/create_dolbom_knowledge.py             # 1개 생성/발행 (주간 cron 기본값)
  python scripts/create_dolbom_knowledge.py --count 5   # 초기 시드 배치용 — 5개 연속 생성/발행

환경변수:
  GEMINI_API_KEY                                  (필수 — 운세상식과 동일한 키 재사용)
  BLOG_ID                                         (필수 — ★이 블로그 전용 ID로 반드시 교체★
                                                    bumodolbom.blogspot.com의 blogId)
  BLOGGER_REFRESH_TOKEN,
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET           (필수 — 기존 시크릿 그대로 재사용)
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
# 인증 — create_post.py / create_knowledge.py의 get_access_token()과 동일한 로직.
# 이 넷(BLOG_ID 제외)은 계정 단위 권한이라 그대로 재사용, BLOG_ID만 이 블로그 것으로.
# ─────────────────────────────────────────
BLOG_ID        = os.environ.get("BLOG_ID", "")          # ← bumodolbom.blogspot.com의 blogId로 설정
REFRESH_TOKEN  = os.environ.get("BLOGGER_REFRESH_TOKEN", "")
CLIENT_ID      = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET  = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

DATA_DIR   = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
STATE_PATH = os.path.join(DATA_DIR, "dolbom_knowledge_state.json")
COUPANG_LINKS_PATH = os.path.join(DATA_DIR, "dolbom_coupang_links.csv")


def get_access_token_for_knowledge():
    """Blogger access token 발급 — create_post.py/create_knowledge.py와 같은 로직."""
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


def post_blogger_scheduled(access_token, title, content, labels, published_iso=None, slug_number=None):
    """돌봄상식 전용 발행 함수. slug_number를 주면 [숫자 제목으로 생성 → 한글 제목으로 수정]
    2단계로 발행해서 URL이 순차 숫자 슬러그로 남는다 (예: /2026/09/30001.html).
    30000번대를 써서 오늘의명언(1만번대)·운세상식(2만번대)과 겹치지 않게 함."""
    if not BLOG_ID or not access_token:
        print(f"(테스트 모드 — BLOG_ID/토큰 없음) {title}")
        return True

    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"

    slug_title = str(slug_number) if slug_number else None
    insert_title = slug_title or title

    body = {"title": insert_title, "content": content, "labels": labels}
    if published_iso:
        body["published"] = published_iso

    post_id = None
    for attempt in range(1, 4):
        resp = requests.post(url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=body)
        if resp.status_code in (200, 201):
            post_id = resp.json().get("id")
            break
        elif resp.status_code == 429:
            wait = 60 * attempt
            print(f"⏳ 429 쿼터 초과 — {wait}초 대기 후 재시도 ({attempt}/3)")
            time.sleep(wait)
        else:
            print(f"❌ 발행 실패 ({resp.status_code}): {resp.text[:150]}")
            return False

    if post_id is None:
        print("❌ 3회 재시도 후 실패")
        return False

    if slug_title:
        try:
            patch_resp = requests.patch(f"{url}{post_id}",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"title": title})
            if patch_resp.status_code not in (200, 201):
                print(f"⚠️ 한글 제목으로 수정 실패({patch_resp.status_code}) — URL은 숫자로 정상이나 화면 제목이 숫자로 남았을 수 있음")
        except Exception as e:
            print(f"⚠️ 제목 수정 요청 중 오류: {e}")

    print(f"✅ 발행 완료 — {title}")
    return True


# ─────────────────────────────────────────
# 사이트 톤 — 운세상식의 보라색 계열 대신, 부모돌봄길잡이 앱과 맞춘
# 차분한 세이지그린·아이보리 계열로 새로 구성(브랜드 일관성)
# ─────────────────────────────────────────
def knowledge_style():
    return """<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Noto Sans KR',sans-serif;background:#F7F6F0;color:#333;padding:16px}
.wrap{max-width:720px;margin:auto}
.hero{background:linear-gradient(135deg,#3F5D45,#6B8E6E);color:#fff;border-radius:18px;padding:36px 24px;text-align:center;margin-bottom:22px}
.hero h1{font-size:24px;margin-bottom:8px}
.hero p{opacity:.85;font-size:14px}
.card{background:#fff;border-radius:14px;padding:26px 24px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.card h2{font-size:18px;color:#2F4A34;margin:22px 0 10px}
.card h2:first-child{margin-top:0}
.card p{font-size:15px;line-height:1.9;color:#374151;margin-bottom:14px}
.card ul{margin:0 0 14px 20px}
.card li{font-size:15px;line-height:1.9;color:#374151;margin-bottom:6px}
.badge{display:inline-block;background:#DDE6DA;color:#3F5D45;padding:3px 10px;border-radius:20px;font-size:12px;margin-bottom:10px}
.tag-cloud{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.tag{background:#EEF3EC;color:#4C6B52;padding:4px 10px;border-radius:20px;font-size:11px}
.notice{background:#FBF3EF;border:1px solid #E8C9B8;border-radius:10px;padding:12px 16px;font-size:13px;color:#8A5A3D;margin-bottom:16px}
.meta{color:#aaa;font-size:12px;text-align:center;padding:20px 0}
</style>"""


# ─────────────────────────────────────────
# 하단 관련 콘텐츠 링크 — 이 블로그(bumodolbom.blogspot.com) 안의 다른
# 카테고리 라벨로 서로 연결(운세상식이 띠/별자리 라벨을 서로 링크하던 것과 동일한 패턴)
# ─────────────────────────────────────────
_BLOG_BASE = "https://bumodolbom.blogspot.com"
_RELATED_LINKS = [
    ("📋 절차·제도", f"{_BLOG_BASE}/search/label/%EC%A0%88%EC%B0%A8%EC%A0%9C%EB%8F%84", "#3F5D45,#6B8E6E"),
    ("🏥 기관 비교", f"{_BLOG_BASE}/search/label/%EA%B8%B0%EA%B4%80%EB%B9%84%EA%B5%90", "#2563A6,#4C8FD1"),
    ("💛 건강·안전", f"{_BLOG_BASE}/search/label/%EA%B1%B4%EA%B0%95%EC%95%88%EC%A0%84", "#B5762C,#D99A4E"),
]

# 쿠팡파트너스 필수 고지 문구 (정보통신망법 — 게시물 최상단에 위치해야 함)
_COUPANG_DISCLOSURE = (
    "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
)


# ─────────────────────────────────────────
# 돌봄상식 주제 리스트 — 5개 카테고리 × 3개, 운세상식(15개)과 같은 규모로 시작.
# 카테고리: 절차제도 / 기관비교 / 건강안전 / 지원제도 / 사후행정
# slug는 사람이 참고용으로 남기는 값일 뿐, 실제 URL은 숫자 슬러그(30001~)를 씀.
# ─────────────────────────────────────────
TOPICS = [
    {"topic": "장기요양등급 신청 방법과 절차 총정리",       "emoji": "📝", "tags": ["장기요양등급", "신청방법", "절차제도"], "slug": "ltc-grade-apply"},
    {"topic": "장기요양등급 1~5등급, 무엇이 다를까",         "emoji": "🔢", "tags": ["장기요양등급", "등급기준", "절차제도"], "slug": "ltc-grade-levels"},
    {"topic": "장기요양보험료는 어떻게 계산될까",             "emoji": "💳", "tags": ["장기요양보험료", "보험료계산", "절차제도"], "slug": "ltc-premium-calc"},
    {"topic": "요양원·요양병원·재가복지센터, 무엇이 다를까",  "emoji": "🏥", "tags": ["요양원", "요양병원", "기관비교"], "slug": "facility-comparison"},
    {"topic": "방문요양 서비스, 어떻게 이용할 수 있을까",     "emoji": "🚪", "tags": ["방문요양", "재가서비스", "기관비교"], "slug": "home-care-guide"},
    {"topic": "복지용구 대여, 어떤 품목을 얼마에 빌릴 수 있을까", "emoji": "🦽", "tags": ["복지용구", "대여품목", "기관비교"], "slug": "welfare-equipment"},
    {"topic": "치매 초기증상, 이렇게 체크해보세요",           "emoji": "🧠", "tags": ["치매초기증상", "치매체크리스트", "건강안전"], "slug": "dementia-signs"},
    {"topic": "어르신 낙상 예방을 위한 생활 속 안전수칙",     "emoji": "🦴", "tags": ["낙상예방", "어르신안전", "건강안전"], "slug": "fall-prevention"},
    {"topic": "어르신을 위한 균형 잡힌 영양관리 방법",         "emoji": "🥣", "tags": ["어르신영양", "식단관리", "건강안전"], "slug": "senior-nutrition"},
    {"topic": "노인맞춤돌봄서비스, 누가 어떻게 신청할까",     "emoji": "🤝", "tags": ["노인맞춤돌봄서비스", "신청대상", "지원제도"], "slug": "senior-care-service"},
    {"topic": "치매안심센터에서 받을 수 있는 도움들",         "emoji": "🏛️", "tags": ["치매안심센터", "무료검진", "지원제도"], "slug": "dementia-center"},
    {"topic": "요양보호사 자격증, 어떻게 취득할까",           "emoji": "🎓", "tags": ["요양보호사", "자격증취득", "지원제도"], "slug": "caregiver-license"},
    {"topic": "사망신고, 언제까지 어떻게 해야 할까",           "emoji": "📮", "tags": ["사망신고", "행정처리", "사후행정"], "slug": "death-report"},
    {"topic": "상속포기와 한정승인, 기한과 절차",             "emoji": "⚖️", "tags": ["상속포기", "한정승인", "사후행정"], "slug": "inheritance-waiver"},
    {"topic": "유족연금과 사망일시금, 신청 방법",             "emoji": "💰", "tags": ["유족연금", "사망일시금", "사후행정"], "slug": "survivor-pension"},
]

# 실천 체크리스트형으로 쓰면 좋은 주제(건강·행정처럼 "지금 바로 해볼 것"이 뚜렷한 주제)
_CHECKLIST_TAGS = {"치매체크리스트", "낙상예방", "행정처리", "신청대상"}


def build_prompt(topic, style="info"):
    base = f"""당신은 고령자 돌봄·복지 제도와 관련 행정 절차를 알기 쉽게 설명하는 정보 전문 필자입니다.
아래 주제로 블로그 정보성 글을 작성해 주세요. 이 글을 읽는 사람은 대부분 부모님을 돌보는
자녀 세대이며, 절차를 몰라 막막해하며 검색해서 들어온 독자입니다.

주제: {topic}

[구조 규칙 — 검색해서 들어온 독자가 원하는 건 이야기가 아니라 정보입니다]
1. 순수 HTML 조각만 출력하세요. <html>, <head>, <body> 태그나 코드블록(```)은 절대 포함하지 마세요.
2. 소제목은 <h2>, 문단은 <p> 태그를 사용하세요. 마크다운 기호(##, **)는 사용하지 마세요.
3. 전체 분량은 공백 제외 1,500자 이상으로 풍성하게 작성하세요.
4. <h2> 소제목 3개 내외로 구성하세요 (도입 → 본론 2~3개 → 마무리). 소제목만 훑어봐도 글의 핵심이 파악되게 하세요.
5. 감정적인 이야기체 도입("오늘은 ~한 이야기를 들려드리겠습니다")은 쓰지 마세요. 검색해서 정보를 찾는 독자를 위한 글입니다.

[문장 톤 규칙]
6. 어조는 "~합니다", "~해보세요"체의 다정하고 담백한 존댓말을 사용하세요. "~에요", "~죠", "~잖아요" 같은 구어체는 쓰지 마세요.
7. 첫 문단은 사전적 정의로 시작하지 말고, 이 문제를 마주한 독자가 겪을 법한 구체적인 상황으로 여세요.
   예시: "부모님이 갑자기 거동이 불편해지셨는데 장기요양등급이 뭔지부터 막막하다면," 처럼
   추상적 설명이 아니라 실제 상황에서 시작하세요. 본론의 각 <h2> 섹션 첫 문장에도 이런 구체적 상황
   제시를 최소 1곳 이상 적용하세요.
8. "A는 ~합니다. 또한 B합니다. 그리고 C합니다." 같은 단순 나열식 문장 반복은 피하세요. 문장 길이와 구조를
   문단마다 다르게 가져가세요.
9. 같은 문장 종결 패턴이 두 문장 이상 연속으로 이어지지 않게 하세요.
10. 마지막 문단은 독자를 다정하게 응원하는 한두 문장으로 마무리하세요.

[사실관계 정확성 규칙 — 반드시 지켜야 함]
11. 신청기한·금액·등급기준 등 구체적인 수치는 일반적으로 널리 알려진 내용 위주로 서술하고,
    법령이나 세부 기준은 개정될 수 있으므로 절대 확정적으로 단언하지 마세요.
12. 글 어딘가(본론 또는 마무리)에 "정확한 최신 기준은 국민건강보험공단(1577-1000) 등 관련
    기관에 반드시 다시 확인하시길 바랍니다"라는 취지의 안내 문장을 자연스럽게 포함하세요.
13. 의료적 진단이나 법률 자문으로 오인될 수 있는 단정적 표현("이러면 틀림없이 ~병입니다",
    "무조건 ~하면 됩니다")은 쓰지 말고, 안내·참고 정보라는 톤을 유지하세요."""

    if style == "checklist":
        base += """
14. 이 글은 독자가 지금 바로 확인·실천할 수 있는 체크리스트가 필요한 주제입니다.
    본론 소제목 중 최소 하나는 <ul><li> 목록을 사용해 바로 확인할 수 있는 체크 항목
    3~5개를 제시하세요. 다만 목록만으로 소제목을 채우지 말고, 목록 앞뒤에 설명 문단을
    붙여 정보성 글의 구조(도입 → 본론 → 마무리)는 그대로 유지하세요."""

    return base


# 우선순위 순서 — 맨 앞이 실패하면 다음 것을 자동으로 시도 (create_knowledge.py와 동일한 이유)
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
            text = text.replace("```html", "").replace("```", "").strip()
            return text
        except Exception as e:
            print(f"  ⚠️ 모델 '{model_name}' 실패: {e} — 다음 후보로 재시도합니다.")
            last_err = e

    raise RuntimeError(f"모든 Gemini 모델 후보가 실패했습니다. 마지막 에러: {last_err}")


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {"last_index": -1, "history": []}
    # 숫자 URL 슬러그 순차번호 — 오늘의명언(1만번대)·운세상식(2만번대)과 안 겹치게 3만번대 사용
    state.setdefault("next_slug_number", 30001)
    return state


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_coupang_links():
    """dolbom_coupang_links.csv를 인덱스 기준으로 읽어온다. (운세상식과 동일한 방어적 인코딩 처리)
    파일이 없거나 특정 인덱스 행이 없어도 에러 없이 빈 값으로 처리."""
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
    if not BLOG_ID:
        print("❌ BLOG_ID 환경변수가 없습니다 — bumodolbom.blogspot.com의 blogId를 설정하세요.")
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

        style = "checklist" if any(t in _CHECKLIST_TAGS for t in tags) else "info"

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

        kw_list  = [topic] + tags + ["돌봄상식"]
        tag_html = "".join(f'<span class="tag">{t}</span>' for t in kw_list)

        related_html = "".join(
            f'<a href="{url}" style="display:inline-block;background:linear-gradient(135deg,{grad});'
            f'color:#fff;padding:8px 16px;border-radius:20px;font-size:12px;font-weight:700;'
            f'text-decoration:none;margin:4px">{label}</a>'
            for label, url, grad in _RELATED_LINKS
        )

        disclosure_html = ""
        product_html = ""
        if coupang_url:
            disclosure_html = (
                f'<div class="notice">{_COUPANG_DISCLOSURE}</div>'
            )
            product_html = f"""
  <div class="card" style="text-align:center;padding:20px">
    <p style="font-size:12px;color:#9ca3af;margin:0 0 10px">🛒 이런 상품은 어떠세요</p>
    <a href="{coupang_url}" style="display:inline-block;background:linear-gradient(135deg,#B5762C,#D99A4E);
       color:#fff;padding:10px 22px;border-radius:20px;font-size:13px;font-weight:700;
       text-decoration:none">{product_keyword or '관련 상품'} 보러가기</a>
  </div>"""

        content = f"""{knowledge_style()}
<div class="wrap">
  <div class="hero">
    <h1>{emoji} {topic}</h1>
    <p>돌봄 상식</p>
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
  <div class="meta"><p>※ 참고용으로 정리한 정보성 콘텐츠이며, 정확한 최신 기준은 관련 기관에 별도로 확인하시기 바랍니다</p></div>
</div>"""

        slug_number = state["next_slug_number"]
        ok = post_blogger_scheduled(access_token, topic, content, ["돌봄상식"], slug_number=slug_number)

        if ok:
            state["last_index"] = idx
            state["next_slug_number"] = slug_number + 1
            state["history"].append({
                "index":     idx,
                "topic":     topic,
                "slug":      str(slug_number),
                "posted_at": datetime.now(timezone.utc).isoformat(),
            })
            save_state(state)
            success_count += 1
        else:
            print(f"  ❌ '{topic}' 발행 실패 — 인덱스를 저장하지 않습니다. "
                  f"다음 실행 때 같은 주제부터 다시 시도합니다.")
            break

        if i < count - 1:
            time.sleep(5)

    return success_count


def main():
    parser = argparse.ArgumentParser(description="돌봄상식 카테고리 자동 생성/발행")
    parser.add_argument("--count", type=int, default=1,
                         help="이번 실행에서 생성할 글 개수 (기본 1, 초기 시드 배치는 --count 10 처럼 크게)")
    args = parser.parse_args()

    print(f"🚀 돌봄상식 생성 시작 — {args.count}개")
    success_count = run(args.count)

    if success_count == 0:
        print("❌ 이번 실행에서 발행에 성공한 글이 하나도 없습니다.")
        sys.exit(1)

    print(f"🎉 완료 — {success_count}개 발행")


if __name__ == "__main__":
    main()
