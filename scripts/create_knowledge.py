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

SEO 프롬프트 v7.6(22장 정보형 블로그 모듈) 적용: 공백 제외 2,000자 이상 + FAQ 5개 + 안내 문구를
코드에서 검증하고, 미달이면 재생성/보충하며 끝내 못 채우면 발행하지 않습니다.

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
import re
import html as _html
import time
import argparse
from datetime import datetime, timezone

import requests
from google import genai
from google.genai import types

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


def post_blogger_scheduled(access_token, title, content, labels, published_iso=None, slug_number=None):
    """운세상식 전용 발행 함수 — 기존 post_blogger()는 절대 건드리지 않고 별도로 둠.
    published_iso를 주면 예약 발행, 생략하면 즉시 발행 (지금 구조는 즉시 발행만 사용).
    slug_number를 주면 [숫자만으로 된 제목으로 생성 → 한글 제목으로 수정] 2단계로 발행해서
    URL이 무작위 숫자 코드 대신 순차 숫자 슬러그로 남는다 (예: /2026/08/20001.html).
    2026-08-19부터 기존 영어 단어 슬러그(예: ox-personality) 방식은 폐기했다 — 오늘의명언
    (create_post.py, 1로 시작하는 순차번호)과 앞자리를 다르게(2로 시작) 맞춰 서로 안 겹침."""
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
    for attempt in range(1, 4):  # 최대 3회 재시도 (기존 post_blogger()와 동일한 패턴)
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
                print(f"⚠️ 한글 제목으로 수정 실패({patch_resp.status_code}) — URL은 영어로 정상이나 화면 제목이 영어로 남았을 수 있음")
        except Exception as e:
            print(f"⚠️ 제목 수정 요청 중 오류: {e}")

    print(f"✅ 발행 완료 — {title}")
    return True


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
.card h3{font-size:16px;color:#4c1d95;margin:18px 0 6px;line-height:1.5}
.card ul{margin:0 0 14px 20px;font-size:15px;line-height:1.9;color:#374151}
.faq{background:#faf8ff;border-radius:12px;padding:6px 16px 2px;margin:8px 0 14px}
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
# 하단 관련 콘텐츠 링크 4개 — 현재 발행 중인 카테고리(별자리 주간, 띠별 월간, 별과띠 주간판, 오늘의 명언)로 고정.
# (label, url, gradient) — url은 실제 create_post.py가 붙이는 라벨과 정확히 일치해야 함
# ─────────────────────────────────────────
_RELATED_LINKS = [
    ("📅 별자리 주간운세",
     "https://todayhoroscopelaboratory.blogspot.com/search/label/%EB%B3%84%EC%9E%90%EB%A6%AC%EC%A3%BC%EA%B0%84",
     "#1e3a5f,#2563eb"),
    ("🌙 띠별 월간운세",
     "https://todayhoroscopelaboratory.blogspot.com/search/label/%EC%9B%94%EA%B0%84%EC%9A%B4%EC%84%B8",
     "#7c2d12,#ea580c"),
    ("✨ 별과 띠가 만나는 시간",
     "https://todayhoroscopelaboratory.blogspot.com/search/label/%EB%B3%84%EA%B3%BC%EB%9D%A0%EA%B0%80%EB%A7%8C%EB%82%98%EB%8A%94%EC%8B%9C%EA%B0%84",
     "#4c1d95,#7c3aed"),
    ("💬 오늘의 명언",
     "https://todayhoroscopelaboratory.blogspot.com/search/label/%EC%98%A4%EB%8A%98%EC%9D%98%EB%AA%85%EC%96%B8",
     "#374151,#6b7280"),
]

TOPICS = [
    {"topic": "지혜롭고 부지런한 소띠의 4가지 성격 특징",   "emoji": "🐮", "tags": ["소띠", "띠별성격", "사주"], "slug": "ox-personality"},
    {"topic": "꾀 많고 영리한 쥐띠의 반전 성격과 특징",       "emoji": "🐭", "tags": ["쥐띠", "띠별성격", "사주"], "slug": "rat-personality"},
    {"topic": "용맹하고 열정적인 호랑이띠의 성격 분석",       "emoji": "🐯", "tags": ["호랑이띠", "띠별성격", "사주"], "slug": "tiger-personality"},
    {"topic": "물병자리에 숨겨진 그리스 신화 이야기",         "emoji": "♒", "tags": ["물병자리", "별자리유래", "그리스신화"], "slug": "aquarius-myth"},
    {"topic": "사자자리의 유래와 밤하늘에 얽힌 전설",         "emoji": "♌", "tags": ["사자자리", "별자리유래", "그리스신화"], "slug": "leo-myth"},
    {"topic": "복을 부르는 현관 인테리어와 거울 위치",         "emoji": "🚪", "tags": ["풍수", "현관인테리어", "풍수지리"], "slug": "entrance-fengshui"},
    {"topic": "재물운을 높이는 침실 침대 방향과 풍수지리",     "emoji": "🛏️", "tags": ["풍수", "침실풍수", "재물운"], "slug": "bedroom-fengshui"},
    {"topic": "행운의 색이 알려주는 나만의 기운 이야기",       "emoji": "🎨", "tags": ["행운의색", "색채심리", "운세상식"], "slug": "lucky-color"},
    {"topic": "태어난 달로 알아보는 탄생석의 의미",           "emoji": "💎", "tags": ["탄생석", "탄생석의미", "보석상식"], "slug": "birthstone-meaning"},
    {"topic": "재물운을 부르는 지갑 색깔과 정리 습관",         "emoji": "🪙", "tags": ["지갑풍수", "재물운", "정리습관"], "slug": "wallet-fengshui"},
    {"topic": "별자리별 잘 어울리는 향수 노트 찾기",           "emoji": "🌸", "tags": ["별자리향수", "향수추천", "별자리매칭"], "slug": "zodiac-perfume"},
    {"topic": "이사할 때 챙기면 좋은 손없는 날과 개운 소품",   "emoji": "🧂", "tags": ["손없는날", "이사풍수", "개운소품"], "slug": "moving-day-fengshui"},
    {"topic": "수험생 자녀를 둔 부모를 위한 합격운 높이는 방법", "emoji": "📚", "tags": ["합격운", "수험생", "학부모"], "slug": "exam-luck-guide"},
    {"topic": "이직·취업 준비생을 위한 취업운 체크리스트",     "emoji": "💼", "tags": ["취업운", "이직", "구직"], "slug": "job-luck-checklist"},
    {"topic": "신혼부부를 위한 재물운 부르는 인테리어",         "emoji": "🏠", "tags": ["신혼부부", "재물운", "인테리어풍수"], "slug": "newlywed-fengshui"},
]

# 쿠팡파트너스 필수 고지 문구 (정보통신망법 — 게시물 최상단에 위치해야 함)
_COUPANG_DISCLOSURE = (
    "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
)


# ─────────────────────────────────────────
# SEO 프롬프트 v7.6 (22장 정보형 블로그 모듈 — 운세상식) 기준 상수
# ─────────────────────────────────────────
MIN_CHARS      = 2000   # 공백·HTML 태그 제외, FAQ 포함 최소 글자 수 (v7.6 22.2)
MAX_ATTEMPTS   = 3      # 기준 미달 시 전체 재생성 최대 횟수 (v7.6 22.8-2)
FAQ_COUNT      = 5      # FAQ 정확히 5개 (v7.6 11.4)
MAX_OUT_TOKENS = 16384  # 한국어 3,000자 이상이 잘리지 않도록 넉넉히 (v7.6 22.8-7)

# 글마다 바꿔 쓰는 관점 — 같은 주제가 순환해 다시 나올 때 다른 글이 되도록 (v7.6 22.7)
PERSPECTIVES = [
    "기본 개념 정리",
    "일상 속 활용",
    "흔한 오해 바로잡기",
    "역사와 유래",
    "상황별 가이드",
    "체크리스트",
]

# v7.6 4.1 공통 금지 표현 — 하나라도 있으면 재생성
_BANNED_HARD = ["최고", "무조건", "100%", "완치", "효과 보장", "완벽 보장", "단번에 해결", "역대급", "인생 맛집"]
# v7.6 4.3 AI 문장 표현 — 재시도 여유가 있으면 다시 쓰게 하고, 마지막 시도에서는 허용
_BANNED_SOFT = ["매우 중요합니다", "다양한", "효과적인", "알아보겠습니다", "결론적으로", "마무리하며",
                "도움이 되셨으면"]


def build_prompt(topic, style="info", perspective="기본 개념 정리", recent_topics=None):
    recent_note = ""
    if recent_topics:
        recent_note = "\n최근 발행한 글 제목(도입 문장·소제목이 겹치지 않게 하세요): " + " / ".join(recent_topics)

    base = f"""당신은 사주·별자리·풍수 등 전통·점성 문화를 알기 쉽게 설명하는 정보형 블로그 필자입니다.
검색해서 들어온 독자가 한 가지 질문에 끝까지 답을 얻고 가는 글을 작성하세요.

주제: {topic}
이번 글의 관점: {perspective}{recent_note}

[출력 형식 — 순수 HTML 조각만 출력]
- <html>, <head>, <body>, <h1> 태그나 코드블록(```), 마크다운 기호(##, **)는 절대 쓰지 마세요.
- 아래 순서와 태그를 정확히 지키세요.
  1) 도입: <p> 1~2개 (150~250자). 소제목 없이 시작합니다.
  2) 본문: <h2> 소제목 4~5개. 각 섹션은 <p> 2~3개로 300~450자.
  3) <h2>자주 묻는 질문</h2> 바로 아래에 <div class="faq"> 안에 질문 5개.
     각 질문은 <h3>Q. 질문 문장</h3> 다음 <p>답변</p> 형식입니다.
  4) <h2>마무리</h2> 아래 <p> 1~2개 (100~200자).
- 전체 분량은 공백·HTML 태그를 제외하고 2,000자 이상(FAQ 포함)이어야 하며, 2,300~2,800자를 목표로 하세요.
  분량은 같은 말의 반복이 아니라 새로운 정보와 구체적인 예시로 채우세요. 3,000자를 넘기지 마세요.

[도입 규칙 — 답 먼저]
- 첫 3문장 안에 이 글에서 얻을 수 있는 핵심 답이나 결론을 쓰세요.
- 인사말, "오늘은 ~에 대해 알아보겠습니다" 같은 예고 문장으로 시작하지 마세요. 감정 이모지도 쓰지 마세요.
- 독자의 상황을 한 문장으로 짚고 → 결론 → 이 글에서 다룰 내용 순으로 쓰세요.

[본문 규칙]
- 소제목(<h2>)은 독자가 실제로 검색할 법한 말로 쓰세요. 예: "물병자리는 어떤 성격으로 해석되나요?"
  소제목을 모두 같은 문형으로 만들지 마세요.
- 본문 섹션은 다음 흐름에서 주제에 맞게 4~5개를 고르세요: 기본 개념·정의 / 원리·유래·과정 /
  구체적인 상황 예시 / 생활 속 적용 방법 / 흔한 오해·주의.
- 각 섹션은 "주장 → 설명 → 구체적 예시 또는 적용" 순서로 쓰고, 섹션마다 독자가 새로 알게 되는 정보가 하나 이상 있어야 합니다.
- 구체적 예시는 지어낸 일화나 실존 인물 이야기가 아니라 누구나 겪을 법한 일반적인 상황으로 쓰세요.
- 한 문단은 2~4문장으로 짧게 끊어, 모바일에서 읽기 쉽게 하세요.

[사실과 신뢰 규칙 — 가장 중요]
- 확실하게 쓸 수 있는 사실: 별자리의 날짜 구간, 12띠의 순서와 연도 주기, 십이지·오행 등 전통 체계의 용어와 기본 구조.
- 성격·운명·건강·재물·연애에 대한 내용은 단정하지 말고 "~라고 해석합니다", "전통적으로 ~라고 봅니다", "~라고 알려져 있습니다"로 쓰세요.
- 통계, 연구 결과, 전문가 발언, 책·고서의 구절, 철학자나 실존 인물의 말을 근거로 들지 마세요. 출처를 댈 수 없는 "전문가들은", "연구에 따르면"도 쓰지 마세요.
- 신화·유래·방위·날짜는 통상적으로 널리 알려진 내용만 쓰고, 확신이 없으면 그 내용은 쓰지 않거나 "전해집니다" 정도로 한정하세요.
- 운세 결과로 투자, 계약, 진료 중단 같은 중요한 결정을 하라고 권하지 마세요.
- 효과를 보장하는 표현은 금지입니다.

[문장 규칙]
- 어조는 "~합니다", "~해보세요"체의 담백한 존댓말입니다. "~에요", "~죠", "~잖아요"는 쓰지 마세요.
- 금지 표현: 최고, 무조건, 100%, 완치, 효과 보장, 완벽 보장, 단번에 해결, 역대급, 인생 맛집,
  "~는 매우 중요합니다", 다양한, 효과적인, "~에 대해 알아보겠습니다", 결론적으로, 마무리하며, "도움이 되셨으면 좋겠습니다".
  "새로운 가치를 만듭니다" 같은 막연한 구호도 쓰지 마세요.
- 같은 어미로 세 문장 이상 이어 쓰지 말고, 짧은 문장과 긴 문장을 섞으세요.
- 같은 내용을 도입·본문·마무리에서 되풀이해 분량을 채우지 마세요.

[FAQ 규칙 — 질문 정확히 5개, 질문마다 문형을 다르게]
질문은 주제어를 넣어 독자가 실제로 검색할 문장으로 쓰고, 다음 5가지 유형을 이 순서로 하나씩 다루세요.
  1. 정의·개념: 이 주제가 무엇이며 어떤 의미로 쓰이는가
  2. 원리·방법: 어떻게 정해지거나 어떤 순서로 진행되는가
  3. 생활 적용: 일상에서 어떻게 참고하거나 활용하는가
  4. 대상·상황: 어떤 사람이나 상황에서 특히 참고하기 좋은가
  5. 주의·오해: 흔한 오해나 꼭 알아둘 주의사항은 무엇인가
- 답변은 120~220자로 쓰고, 첫 문장에서 바로 답하세요.
- 답변은 본문 문장을 복사하지 말고 본문과 다른 각도의 보충 설명으로 쓰세요.

[마무리 규칙]
- 2~3문장으로 핵심 한 줄 정리와 독자가 바로 해볼 수 있는 행동 한 가지를 쓰세요.
- 마무리 안에 "재미로 참고하는 운세·풍수 정보이며 실제 결정은 본인의 판단으로 하세요"라는 취지의 안내를 한 문장 넣되,
  표현은 이 글에 맞게 자연스럽게 바꿔 쓰세요."""

    if style == "checklist":
        base += """

[체크리스트 규칙]
- 이 글은 특정 상황(수험생 학부모, 이직 준비생, 신혼부부 등)에 놓인 독자를 위한 실천 가이드입니다.
  본문 소제목 중 하나는 <ul><li> 목록으로 바로 실천할 수 있는 행동 3~5개를 제시하세요.
  목록 앞뒤에 설명 문단을 붙여 도입 → 본문 → FAQ → 마무리 구조는 그대로 유지하세요."""

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


def _clean_model_text(text):
    """코드블록·마크다운 잔여물 제거."""
    text = (text or "").strip()
    text = text.replace("```html", "").replace("```", "").strip()
    return text


def _is_transient(err):
    """503(과부하)·429(쿼터)·5xx·연결 끊김·타임아웃은 잠시 뒤 같은 모델로 다시 시도할 가치가 있다.
    404(모델 없음)·400(요청 오류)은 재시도해도 소용없으니 바로 다음 모델로 넘어간다."""
    code = getattr(err, "code", None)
    if isinstance(code, int):
        return code in (429, 500, 502, 503, 504)
    msg = str(err).lower()
    return any(k in msg for k in ("503", "unavailable", "disconnected", "timed out", "timeout",
                                  "429", "resource_exhausted", "deadline", "connection", "overloaded"))


def _make_client():
    # 응답 없이 오래 매달리는 경우(지난 실행에서 4분 44초 소요)를 막기 위해 호출당 120초 제한.
    try:
        return genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(timeout=120_000))
    except Exception:
        return genai.Client(api_key=GEMINI_API_KEY)


def _discover_models(client, already_tried):
    """고정 후보가 전부 막혔을 때 — 지금 계정에서 실제로 쓸 수 있는 flash 계열 모델을 조회해 대체 후보로 쓴다.
    (모델 이름이 예고 없이 바뀌어 404가 나는 경우 대비)"""
    found = []
    try:
        for m in client.models.list():
            name = (getattr(m, "name", "") or "").replace("models/", "")
            actions = getattr(m, "supported_actions", None) or []
            if "flash" not in name:
                continue
            if any(x in name for x in ("image", "tts", "live", "audio", "embedding", "robotics", "computer", "thinking-exp")):
                continue
            if actions and "generateContent" not in actions:
                continue
            if name in already_tried:
                continue
            found.append(name)
    except Exception as e:
        print(f"  ⚠️ 사용 가능 모델 조회 실패: {e}")
        return []
    # 안정판(preview/exp 아닌 것)을 앞으로, 이름이 긴 순서 대신 단순 정렬
    found.sort(key=lambda n: (("preview" in n) or ("exp" in n), n))
    return found[:3]


def _try_model(client, model_name, prompt, cfg, retries=3):
    """한 모델을 최대 retries번 시도 (일시 오류일 때만 15초→45초 간격으로 재시도). 성공 시 텍스트, 실패 시 예외."""
    last_err = None
    for n in range(1, retries + 1):
        try:
            resp = client.models.generate_content(model=model_name, contents=prompt, config=cfg)
            text = _clean_model_text(resp.text)
            if not text:
                raise ValueError("빈 응답")
            return text
        except Exception as e:
            last_err = e
            if _is_transient(e) and n < retries:
                wait = 15 if n == 1 else 45
                print(f"  ⏳ 모델 '{model_name}' 일시 오류({n}/{retries}): {str(e)[:120]} — {wait}초 뒤 재시도")
                time.sleep(wait)
                continue
            break
    raise last_err


def _call_gemini(prompt):
    """모델 후보를 차례로 시도해 텍스트 한 덩어리를 돌려준다.
    일시 오류(503 등)는 같은 모델로 재시도하고, 고정 후보가 전부 실패하면 사용 가능한 flash 모델을 조회해 추가 시도한다.
    전부 실패하면 RuntimeError."""
    client = _make_client()
    cfg = types.GenerateContentConfig(max_output_tokens=MAX_OUT_TOKENS, temperature=0.8)
    last_err = None
    tried = []

    for model_name in GEMINI_MODEL_CANDIDATES:
        tried.append(model_name)
        try:
            return _try_model(client, model_name, prompt, cfg)
        except Exception as e:
            print(f"  ⚠️ 모델 '{model_name}' 실패: {str(e)[:200]} — 다음 후보로 재시도합니다.")
            last_err = e

    for model_name in _discover_models(client, tried):
        print(f"  🔎 조회로 찾은 대체 모델 시도: {model_name}")
        try:
            return _try_model(client, model_name, prompt, cfg, retries=2)
        except Exception as e:
            print(f"  ⚠️ 모델 '{model_name}' 실패: {str(e)[:200]}")
            last_err = e

    raise RuntimeError(f"모든 Gemini 모델 후보가 실패했습니다. 마지막 에러: {last_err}")


def count_chars(html_text):
    """공백·줄바꿈·HTML 태그·<style> 제외 글자 수 (v7.6 22.2)."""
    t = re.sub(r"<style.*?</style>", "", html_text, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = _html.unescape(t)
    return len(re.sub(r"\s+", "", t))


_DISCLAIMERS = [
    "운세와 풍수는 재미로 참고하는 전통 문화 정보이니, 실제 결정은 본인의 판단으로 내려 주세요.",
    "재미 삼아 참고하는 이야기일 뿐이므로, 중요한 선택은 스스로 판단해 정하시기 바랍니다.",
    "이 글은 재미와 참고를 위한 전통 문화 소개이며, 현실의 결정은 본인의 상황과 판단이 우선입니다.",
    "가볍게 재미로 즐기는 정보로 두고, 실제 결정은 본인의 판단으로 하세요.",
]
_CLOSING_FALLBACKS = [
    "오늘 알게 된 내용 중 마음에 남는 한 가지를 가볍게 생활에 적용해 보세요.",
    "이 글에서 눈에 띈 부분 하나만 골라 오늘 바로 시험해 보세요.",
]
# 모델이 자꾸 쓰는 표현 중 기계적으로 안전하게 바꿀 수 있는 것
_REPLACE_MAP = [
    ("다양한", "여러"),
    ("효과적인", "도움이 되는"),
    ("결론적으로, ", ""),
    ("결론적으로 ", ""),
    ("마무리하며, ", ""),
    ("마무리하며 ", ""),
]


def autofix_html(html_text):
    """모델이 자주 빠뜨리는 부분을 코드로 보정한다 — 다시 생성(1분 이상)하는 것보다 안정적이다.
    1) 피해야 할 표현 치환  2) '마무리' 섹션 없으면 추가  3) 안내 문구('재미…') 없으면 마지막 문단에 덧붙임.
    글이 중간에 잘린 경우(마지막이 태그로 끝나지 않음)에는 보정하지 않고 그대로 둔다(검증에서 걸러짐)."""
    import random
    t = html_text
    if not t.rstrip().endswith(">"):
        return t
    for old, new in _REPLACE_MAP:
        t = t.replace(old, new)

    if not re.search(r"<h2[^>]*>\s*마무리", t):
        t = t.rstrip() + "\n<h2>마무리</h2>\n<p>" + random.choice(_CLOSING_FALLBACKS) + "</p>"

    plain = _html.unescape(re.sub(r"<[^>]+>", "", t))
    if "재미" not in plain:
        k = t.rfind("</p>")
        sentence = " " + random.choice(_DISCLAIMERS)
        if k != -1:
            t = t[:k] + sentence + t[k:]
        else:
            t = t.rstrip() + "<p>" + random.choice(_DISCLAIMERS) + "</p>"
    return t


def validate_html(html_text):
    """(hard, soft) 문제 목록을 돌려준다.
    hard = 이대로는 발행하면 안 되는 문제, soft = 재시도 여유가 있을 때만 고치게 하는 문제."""
    hard, soft = [], []
    chars = count_chars(html_text)
    plain = _html.unescape(re.sub(r"<[^>]+>", "", html_text))

    if chars < MIN_CHARS:
        hard.append(f"글자 수 부족: 현재 {chars}자 (공백·태그 제외, 최소 {MIN_CHARS}자)")

    faq_n = len(re.findall(r"<h3\b", html_text, flags=re.I))
    if faq_n != FAQ_COUNT:
        hard.append(f"FAQ 질문 수가 {faq_n}개입니다 (정확히 {FAQ_COUNT}개여야 함)")

    if not re.search(r"<h2[^>]*>\s*자주 묻는 질문", html_text):
        hard.append("<h2>자주 묻는 질문</h2> 섹션이 없습니다")
    if not re.search(r"<h2[^>]*>\s*마무리", html_text):
        hard.append("<h2>마무리</h2> 섹션이 없습니다")
    elif not html_text.rstrip().endswith(">"):
        hard.append("글이 중간에 잘린 것 같습니다 (마지막이 태그로 끝나지 않음)")

    if "재미" not in plain:
        hard.append("'재미로 참고하는 정보' 취지의 안내 문구가 없습니다")

    if re.search(r"<h1\b|<script|<html|<body", html_text, flags=re.I):
        hard.append("허용되지 않은 태그(h1/script/html/body)가 있습니다")

    found = [w for w in _BANNED_HARD if w in plain]
    if found:
        hard.append("금지 표현 포함: " + ", ".join(found))

    h2_n = len(re.findall(r"<h2\b", html_text, flags=re.I))
    if not (5 <= h2_n <= 8):
        soft.append(f"<h2>가 {h2_n}개입니다 (본문 3~5개 + 자주 묻는 질문 + 마무리)")

    found_soft = [w for w in _BANNED_SOFT if w in plain]
    if found_soft:
        soft.append("피해야 할 표현 포함: " + ", ".join(found_soft))

    if "##" in html_text or "**" in html_text:
        soft.append("마크다운 기호(##, **)가 남아 있습니다")

    if chars > 4200:
        soft.append(f"글이 너무 깁니다 ({chars}자) — 3,000자 안팎으로 줄이세요")

    return hard, soft


def _append_extra_section(topic, html_text, need_chars):
    """그래도 모자랄 때 — 부족한 분량만큼 본문 섹션 1개를 추가 생성해 FAQ 앞에 붙인다 (v7.6 22.8-3)."""
    titles = re.findall(r"<h2[^>]*>(.*?)</h2>", html_text, flags=re.S)
    prompt = f"""블로그 글 '{topic}'에 본문 섹션 1개를 추가하려고 합니다.
이미 있는 소제목: {' / '.join(re.sub('<[^>]+>', '', t) for t in titles)}

규칙:
- 위 소제목과 겹치지 않는 새로운 관점의 <h2> 소제목 1개와 <p> 문단 2~3개만 출력하세요. 다른 태그와 코드블록은 쓰지 마세요.
- 분량은 공백 제외 {need_chars + 150}자 안팎입니다.
- 어조는 "~합니다"체. 통계·연구·전문가 발언·책 구절·실존 인물 인용은 쓰지 말고, 단정하지 않는 표현("~라고 해석합니다", "전통적으로")을 쓰세요.
- 금지: 최고, 무조건, 100%, 완치, 효과 보장, 다양한, 효과적인, 결론적으로.
- 기존 글의 내용을 반복하지 말고, 독자가 새로 알게 되는 정보와 일반적인 상황 예시를 담으세요."""
    extra = _call_gemini(prompt)
    extra = re.sub(r"<h1\b[^>]*>.*?</h1>", "", extra, flags=re.S | re.I)
    m = re.search(r"<h2[^>]*>\s*자주 묻는 질문", html_text)
    if not m:
        return html_text
    return html_text[:m.start()] + extra + "\n" + html_text[m.start():]


def generate_knowledge_html(topic, style="info", perspective="기본 개념 정리", recent_topics=None):
    """v7.6 22.8 규칙: 생성 → 글자 수·구조 검증 → 최대 3회 재생성 → 보충 섹션 → 그래도 안 되면 None."""
    base_prompt = build_prompt(topic, style=style, perspective=perspective, recent_topics=recent_topics)
    prompt = base_prompt
    best = None  # hard 문제는 있어도 가장 글이 긴 후보 (보충 섹션용)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        text = autofix_html(_call_gemini(prompt))
        hard, soft = validate_html(text)
        chars = count_chars(text)
        print(f"  📏 시도 {attempt}/{MAX_ATTEMPTS}: {chars}자 · "
              f"hard {len(hard)} / soft {len(soft)}")

        if not hard:
            # hard 문제가 없으면 발행 가능. 사소한 문체 문제(soft)는 기록만 하고 재생성하지 않는다
            # (재생성은 1분 이상 걸리고 오히려 글이 길어지거나 다른 문제가 생기는 경우가 많았다).
            if soft:
                print("  ℹ️ 사소한 문제는 있지만 발행 가능: " + "; ".join(soft))
            return text

        if best is None or chars > count_chars(best):
            best = text

        for pmsg in hard:
            print(f"     - {pmsg}")
        if attempt < MAX_ATTEMPTS:
            if chars < MIN_CHARS:
                size_note = (f"현재 {chars}자로 부족합니다. 공백·태그 제외 {MIN_CHARS}자 이상(2,300~2,800자 목표)이 되도록 "
                             "H2 섹션과 FAQ 답변에 구체적인 설명을 추가하세요.")
            else:
                size_note = f"분량은 현재 {chars}자입니다. 2,300~2,800자를 유지하고 늘리지 마세요."
            prompt = (base_prompt
                      + "\n\n[직전 결과의 문제점 — 반드시 고쳐서 처음부터 다시 작성하세요]\n- "
                      + "\n- ".join(hard)
                      + "\n\n[직전 결과 (참고용)]\n" + text
                      + "\n\n위 문제를 모두 해결해 전체 글을 다시 출력하세요. " + size_note)
            time.sleep(2)

    # 재생성으로도 기준 미달 — 글자 수만 모자란 경우에 한해 보충 섹션 시도
    if best is not None:
        hard, _soft = validate_html(best)
        only_short = hard and all(h.startswith("글자 수 부족") for h in hard)
        if only_short:
            chars = count_chars(best)
            if chars >= MIN_CHARS - 800:
                print(f"  ➕ 보충 섹션 추가 시도 (현재 {chars}자)")
                for _ in range(2):
                    chars = count_chars(best)
                    if chars >= MIN_CHARS:
                        break
                    try:
                        best = _append_extra_section(topic, best, MIN_CHARS - chars)
                    except Exception as e:
                        print(f"  ⚠️ 보충 섹션 생성 실패: {e}")
                        break
                hard, _soft = validate_html(best)
                if not hard:
                    print(f"  ✅ 보충 후 {count_chars(best)}자로 기준 충족")
                    return best

    print("  ❌ 기준(2,000자·FAQ 5개·안내 문구)을 채우지 못했습니다 — 이 글은 발행하지 않습니다.")
    return None


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {"last_index": -1, "history": []}
    # 숫자 URL 슬러그 순차번호 — 운세상식은 2로 시작(20001~), 오늘의명언(create_post.py, 1로 시작)과
    # 앞자리가 겹치지 않게 분리
    state.setdefault("next_slug_number", 20001)
    return state


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

        # 주제가 한 바퀴 돌아 다시 나올 때는 다른 관점으로 쓰게 한다 (v7.6 22.7)
        cycle_no    = len(state.get("history", [])) // n
        perspective = PERSPECTIVES[(idx + cycle_no) % len(PERSPECTIVES)]
        recent_topics = [h.get("topic", "") for h in state.get("history", [])[-8:] if h.get("topic")]
        print(f"  🎯 관점: {perspective}")

        try:
            body_html = generate_knowledge_html(topic, style=style, perspective=perspective,
                                                recent_topics=recent_topics)
        except Exception as e:
            print(f"  ⚠️ Gemini 생성 실패: {e} — 이 주제는 건너뜁니다.")
            continue

        if not body_html:
            # 2,000자·FAQ 5개 기준 미달 — 기준 미달 글을 올리느니 건너뛴다 (인덱스 미저장 → 다음 실행 때 같은 주제 재시도)
            print("  ⚠️ 품질 기준 미달 — 발행을 건너뜁니다.")
            continue
        print(f"  ✅ 최종 {count_chars(body_html)}자")

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
  <div class="meta"><p>※ 재미와 참고를 위해 정리한 전통 문화 정보이며, 중요한 결정은 본인의 판단으로 하세요</p></div>
</div>"""

        slug_number = state["next_slug_number"]
        ok = post_blogger_scheduled(access_token, topic, content, ["운세상식"], slug_number=slug_number)

        if ok:
            state["last_index"] = idx
            state["next_slug_number"] = slug_number + 1  # 발행 성공 시에만 다음 번호로 갱신
            state["history"].append({
                "index":     idx,
                "topic":     topic,
                "perspective": perspective,
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
