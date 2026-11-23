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

2026-11-02 업데이트 (MULTI_PLATFORM_SEO_MASTER v7.6 §22 정보형 블로그 모듈 적용):
  - 제목(28~40자)·도입 요약(150~250자)·본문 H2 4~5개(섹션당 300~450자)·FAQ 5개(답변당
    120~220자)·마무리+안내문구(100~200자)를 구분자로 분리해 받고, 공백 제외 전체 분량이
    2,000자 이상인지, FAQ가 정확히 5개인지, 금지 표현이 없는지를 코드에서 직접 검증한다
    (§22.8). 기준 미달이면 최대 2회 재생성 → 그래도 분량만 부족하면 보강 섹션 1회 추가
    → 끝까지 못 채우면 "발행하지 않고" 건너뛴다(기준 미달 글을 올리는 것보다 한 주 건너뛰는
    편이 낫다는 원칙, §22.8.6).
  - 주제(TOPICS)가 두 바퀴째 순환할 때부터는 관점(기본 개념/생활 활용/흔한 오해 바로잡기/
    상황별 가이드/체크리스트)을 자동으로 바꿔가며 써서, 같은 주제를 다시 다룰 때도 내용이
    겹치지 않게 한다(§22.7, 애드센스 "가치 없는 콘텐츠" 반려 대응).

2026-11-23 업데이트 (MULTI_PLATFORM_SEO_MASTER v9.5 §19.5~19.7·§23 HOHO MAGAZINE
EDITORIAL MODULE 적용 — v9.5는 "호호매거진, 운세상식, 돌봄상식 등 정보형 글"에 §23을
명시적으로 적용 대상으로 지정함):
  - TITLE/INTRO/BODY/FAQ/CLOSING 5개 필수 구분자는 v7.6과 동일하게 유지해 기존에 안정적으로
    검증된 핵심 흐름(재시도·품질 게이트·인프라 오류 구분)을 그대로 보존한다. 그 위에 선택
    구분자 SUMMARY(📌 한줄요약)/MYPOINT(📍 나만의 포인트)/ONESHOT(✅ 한 번에 정리)/
    TIPS(🛠 실전 팁)/CLOSINGQ(💬 마무리 질문)를 추가한다 — 있으면 본문에 넣고 없으면 그
    박스만 생략한 채 발행한다(§19.2 구조 적용 예외와 같은 원칙 — 선택 섹션이 없다고 발행을
    막지 않는다. 반복 가능한 주간 자동화에서 "완벽히 못 채우면 건너뛴다"를 선택 섹션에까지
    적용하면 매주 멈출 위험이 커지므로 핵심 5개 구분자에만 하드 게이트를 둔다).
  - 📚 목차와 "확인하면 좋은 기관"(§23.4 "참고한 자료"에 대응, 실제 출처 인용이 아니라 고정된
    확인 기관 안내로 구현 — 돌봄상식은 호호플레이 같은 자체 집계 데이터가 없어 특정 자료명·
    통계를 지어낼 위험이 있다고 판단해, 사실관계를 지어내지 않는 쪽을 택함)는 AI에게 맡기지
    않고 코드에서 직접 만든다: 목차는 본문 <h2>를 그대로 추출해 id(hh-s1, hh-s2 …)를 부여하고
    앵커로 연결하므로(§19.5-C) 목차와 본문이 어긋나거나 자리표시자가 남는 문제가 구조적으로
    발생하지 않는다.
  - 각 <h2> 섹션 바로 뒤에 📝 간단 정리(class="mini-sum")를 받아 본문에 포함하되, 분량
    (2,000자) 집계에서는 제외한다(§23.7 분량 기준 — 한줄요약·나만의 포인트·목차·간단 정리·
    한 번에 정리는 제외, 실전 팁은 새 정보라서 포함). FAQ에는 "(제도)"·"[대상]"·"OOO" 같은
    분류 라벨·자리표시자가 남지 않았는지(§23.5) 새 하드 게이트로 코드에서 직접 검사한다.
  - 금지 표현 목록에 실제 발행 글에서 반복됐던 상투적 시작 틀과, 이 블로그에는 애초에 해당
    없는 "직접 방문·체험" 표현("가봤더니"·"다녀와 보니" 등, §23.8)을 추가했다 — 돌봄상식은
    운영자가 현장을 방문해 쓰는 글이 아니므로 체험 표현이 섞이면 거짓 경험을 암시하게 된다.
  - 3종 표(§8.9.5)는 이번 적용 범위에서 **제외**했다 — 표 안의 구체적인 수치(요금·기간 등)를
    실제 데이터 없이 AI가 메꾸게 될 위험이, 얻는 정보 가치보다 크다고 판단했다. 제목 3후보·
    썸네일 지시(§19.1/§19.7-C)도 실제 사람이 고르거나 이미지를 붙이는 단계가 이 완전 자동
    파이프라인에는 없어 제외했다(제목은 상황형 1개만 바로 채택).
"""

import os
import re
import sys
import json
import csv
import time
import argparse
from datetime import datetime, timezone

import requests
from google import genai
from google.genai import types

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
.intro{font-size:15.5px;line-height:1.9;color:#2F4A34;font-weight:500;margin-bottom:18px}
.faq-item{margin-bottom:18px;padding-bottom:16px;border-bottom:1px solid #EEF1EC}
.faq-item:last-child{margin-bottom:0;padding-bottom:0;border-bottom:none}
.faq-q{font-size:15px;color:#2F4A34;margin-bottom:6px;line-height:1.6}
.faq-a{font-size:14px;line-height:1.8;color:#4B5B4E;margin-bottom:0}
.meta{color:#aaa;font-size:12px;text-align:center;padding:20px 0}
.box-label{font-weight:800;color:#2F4A34;font-size:14px;margin-bottom:6px}
.box-summary{background:#F3F6F1;border:1px solid #CFE0CB;border-radius:12px;padding:14px 16px;margin:0 0 14px}
.box-summary p{margin:0;font-size:14.5px;line-height:1.75;color:#374151}
.box-mypoint{background:#EFF6EE;border:1px solid #CFE0CB;border-radius:12px;padding:14px 16px;margin:0 0 14px}
.box-mypoint ul{margin:0;padding-left:20px}
.box-mypoint li{font-size:14px;line-height:1.7;color:#374151;margin-bottom:4px}
.box-toc{background:#FAFAF7;border:1px solid #E5E7EB;border-radius:12px;padding:14px 16px;margin:0 0 18px}
.box-toc ol{margin:0;padding-left:20px}
.box-toc li{font-size:14px;line-height:1.8}
.box-toc a{color:#3F5D45;text-decoration:none}
.mini-sum{background:#F7F6F0;border-left:3px solid #9DB89F;padding:6px 10px;font-size:13px;color:#4C6B52;margin:0 0 16px;border-radius:0 6px 6px 0}
.box-oneshot{background:#EAF1EC;border:1px solid #BFD4C2;border-radius:12px;padding:14px 16px;margin:16px 0 0}
.box-oneshot p{margin:0;font-size:14.5px;line-height:1.75;color:#2F4A34}
.box-tips{background:#FBF3EF;border:1px solid #E8C9B8;border-radius:12px;padding:14px 16px;margin:14px 0 0}
.box-tips ul{margin:0;padding-left:20px}
.box-tips li{font-size:14px;line-height:1.7;color:#4B3A2E;margin-bottom:4px}
.ref-block{font-size:12.5px;color:#6b7280;margin-bottom:10px}
.ref-block ul{margin:4px 0 0;padding-left:18px}
.ref-block li{margin-bottom:3px}
.closing-q{font-size:13.5px;color:#4C6B52;font-style:italic;text-align:center;margin:0}
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

# v9.5 §23.4 "참고한 자료" 대응 — 돌봄상식은 호호플레이처럼 자체 집계 데이터가 없어 AI에게
# 특정 자료명·통계를 맡기면 지어낼 위험이 있다. 대신 실제로 틀릴 수 없는 고정된 "확인 기관"
# 안내로 코드에서 직접 만든다(기관명·연락처만 쓰고, 특정 발표자료·통계는 인용하지 않음).
_CHECK_ORGS = [
    ("국민건강보험공단 (노인장기요양보험)", "1577-1000", "https://www.nhis.or.kr"),
    ("보건복지부 (보건복지상담센터)", "129", "https://www.mohw.go.kr"),
    ("거주지 주민센터·보건소", "", ""),
]


def _build_checkpoints_html():
    """실제 발표자료를 인용하는 대신, 언제나 맞는 고정된 확인 기관 목록을 코드에서 직접 만든다."""
    items = "".join(
        f"<li><b>{org}</b>" + (f" · {phone}" if phone else "") +
        (f' · <a href="{url}">{url}</a>' if url else "") + "</li>"
        for org, phone, url in _CHECK_ORGS
    )
    return f'<div class="ref-block"><div class="box-label">🔎 확인하면 좋은 기관</div><ul>{items}</ul></div>'


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


def build_prompt(topic, perspective, style, recent_history, feedback=""):
    """MULTI_PLATFORM_SEO_MASTER v9.5 §23(HOHO MAGAZINE EDITORIAL MODULE — "호호매거진, 운세상식,
    돌봄상식 등 정보형 글"에 명시적으로 적용 대상) + §19.5~19.7(한줄요약·목차·나만의 포인트·
    간단 정리·한 번에 정리·실전 팁·홈판 대응 모듈)을 적용한 프롬프트.

    TITLE/INTRO/BODY/FAQ/CLOSING 5개는 v7.6과 동일하게 "필수" 구분자로 유지하고(파싱 실패 시
    재시도 — 기존에 안정적으로 검증된 부분을 건드리지 않는다), SUMMARY/MYPOINT/ONESHOT/TIPS/
    CLOSINGQ는 "선택" 구분자로 추가한다. 📚 목차와 "확인하면 좋은 기관"은 여기서 AI에게 맡기지
    않고 generate_dolbom_post()/run()이 본문 <h2>와 고정 기관 목록에서 직접 만든다."""

    recent_block = ""
    if recent_history:
        lines = []
        for h in recent_history:
            if not h.get("title"):
                continue
            h2_part = ", ".join(h.get("h2") or []) or "(기록 없음)"
            fw_part = h.get("first_words") or "(기록 없음)"
            lines.append(f"- 제목: {h['title']} / 소제목: {h2_part} / 첫 문장 시작: {fw_part}")
        if lines:
            recent_block = (
                "\n\n[최근 발행한 글 — 아래와 제목·소제목(H2)·도입 첫 문장 시작 어구가 겹치지 "
                "않게 쓰세요 (§23.6)]\n" + "\n".join(lines)
            )

    checklist_rule = ""
    if style == "checklist":
        checklist_rule = (
            " 본문 소제목 중 하나는 <ul><li> 목록으로 독자가 지금 바로 확인할 수 있는 체크 항목"
            " 3~5개를 제시하세요. 목록 앞뒤에 설명 문단을 붙여 목록만으로 섹션을 채우지 마세요."
        )

    feedback_block = ""
    if feedback:
        feedback_block = f"\n\n[재작성 지시]\n{feedback}"

    return f"""당신은 고령자 돌봄·복지 제도와 관련 행정 절차를 알기 쉽게 설명하는 정보 전문 필자입니다.
이 글을 읽는 사람은 대부분 부모님을 돌보는 자녀 세대이며, 절차를 몰라 막막해하며 검색해서 들어온 독자입니다.
글 전체에서 "호호플레이"나 특정 서비스 이름을 언급하지 마세요 — 이 블로그는 정보 제공이 유일한 목적입니다.

주제: {topic}
이번 글의 관점: {perspective} — 본문의 초점과 소제목을 이 관점에 맞춰 구성하세요.
  (예: "체크리스트" 관점이면 실천 목록 중심, "흔한 오해 바로잡기" 관점이면 잘못 알려진 내용을
  바로잡는 구성, "상황별 가이드" 관점이면 상황별 분기로 구성){recent_block}

[출력 형식 — 반드시 아래 구분자를 정확히 그대로 포함해서 출력하세요. 인사말이나 설명 문장은
쓰지 마세요. TITLE/INTRO/BODY/FAQ/CLOSING은 필수이며, SUMMARY/MYPOINT/ONESHOT/TIPS/CLOSINGQ는
가능하면 채우되 구분자 자체는 항상 출력하세요(정말 보탤 내용이 없으면 안쪽만 비워도 됩니다)]
<!--TITLE_START-->
(28~40자. [대상·상황]+[무엇을]+[얻는 것]이 드러나는 제목. 예: "장기요양등급 신청, 서류부터
순서까지 한눈에 정리"처럼 검색하는 사람의 상황이 보이게 쓰세요. 과장 표현 없이. 태그 없이 텍스트만)
<!--TITLE_END-->
<!--INTRO_START-->
(<p> 태그, 공백 제외 150~250자, 3문장 이내. 첫 문장은 독자의 구체적인 상황이나 조건으로 열고
("부모님이 갑자기 거동이 불편해지셨는데 장기요양등급이 뭔지부터 막막하다면,"처럼), 인사말이나
"오늘은 ~에 대해 알아보겠습니다" 같은 예고 문장으로 시작하지 마세요. "아침에 눈을 떠서", "주말이
다가오면", "~를 바탕으로 살펴보면" 같은 뻔한 시작 틀도 쓰지 마세요. 둘째 문장에서 이 글이 바로
답하는 결론을 제시하고, 셋째 문장에서 이 글이 다룰 내용을 간단히 짚으세요. 구체적인 통계나 발표
자료를 지어내지 말고, 필요하면 "국민건강보험공단·보건복지부 기준으로" 정도만 자연스럽게 언급하세요.)
<!--INTRO_END-->
<!--SUMMARY_START-->
(📌 한줄요약 — <p> 태그 1~2문장, 공백 제외 100~200자. 이 글의 결론을 독립된 문장만 읽어도
이해되게 쓰세요. 도입부 문장을 그대로 옮기지 말고, 본문에 실제로 나오는 조건·기준만 요약하세요.
확인하지 못한 구체 수치는 "확인 필요"로 쓰거나 아예 쓰지 마세요. "~에 대해 정리했습니다" 같은
예고형 문장은 쓰지 마세요.)
<!--SUMMARY_END-->
<!--MYPOINT_START-->
(📍 나만의 포인트 — <ul><li> 1~3개, 항목당 한 문장(약 40~90자). 이 글이 다른 글과 다르게 짚는
확인 순서·선정 기준·놓치기 쉬운 조건을 쓰세요. "방문 전 확인이 중요합니다" 같은 일반론은 쓰지
말고, 본문에 실제로 나오는 내용에 근거해서 쓰세요. 한줄요약과 같은 말을 반복하지 마세요.)
<!--MYPOINT_END-->
<!--BODY_START-->
(<h2> 소제목 4~5개, 각 섹션은 <h2> 다음 <p> 1~2개(섹션당 공백 제외 300~450자), 그리고 그 섹션의
맨 마지막에 <p class="mini-sum">📝 간단 정리 — (그 섹션에서 독자가 가져갈 결론 한 줄, 공백 포함
20~90자. 새 사실을 추가하지 말고 섹션 안의 내용만 한 줄로 정리하세요)</p>를 반드시 붙이세요.
다음 흐름 중 이번 관점({perspective})에 맞는 것을 골라 구성하세요: 기본 개념/정의, 원리·과정,
구체적 예시(지어낸 일화가 아닌 일반적인 상황), 생활 속 적용 방법(단계 또는 체크리스트), 흔한
오해·비교·주의. 모든 글에 같은 구조를 쓰지 마세요. 각 섹션은 주장 → 설명 → 구체적 예시/적용
순서로 쓰고, 섹션마다 독자가 새로 알게 되는 정보가 하나 이상 있어야 합니다. 소제목은 독자가
실제로 검색할 만한 말로 쓰세요(예: "장기요양등급은 어떻게 신청하나요?"). 첫 문단은 사전적
정의로 시작하지 말고 독자가 겪을 법한 구체적 상황으로 여세요.{checklist_rule})
<!--BODY_END-->
<!--ONESHOT_START-->
(✅ 한 번에 정리 — <p> 태그, 3~6문장(공백 포함 약 250~450자). 위 본문 소제목들을 관통하는 공통
기준 → 그래서 어떤 순서로 보면 되는지 → 마지막 한 줄 결론("결국 …")의 순서로 쓰세요. 각 섹션의
간단 정리를 그대로 이어 붙이지 말고 섹션들 사이의 관계와 우선순위를 새로 묶어서 쓰세요.)
<!--ONESHOT_END-->
<!--FAQ_START-->
(아래 5가지 유형에 각각 답하는 FAQ를 class="faq-item" 블록 정확히 5개로 작성하세요. 각 블록은
다음 형식을 그대로 따르세요:
<div class="faq-item"><h3 class="faq-q">Q. (질문)</h3><p class="faq-a">A. (답변)</p></div>
질문 유형(주제 '{topic}'을 넣어 독자가 실제로 검색할 문장처럼 쓰세요):
1. [정의·개념] {topic}란 무엇이며 어떤 의미인가요?
2. [원리·방법] 어떤 순서나 기준으로 진행되나요?
3. [생활 적용] 일상에서 어떻게 활용하거나 준비하면 되나요?
4. [대상·상황] 특히 해당되거나 필요한 사람·상황은 어떤 경우인가요?
5. [주의·오해] 흔히 하는 오해나 꼭 알아둘 주의사항은 무엇인가요?
답변은 각각 공백 제외 120~220자, 첫 문장에서 바로 답하세요. 본문 내용을 그대로 요약하지 말고
본문과 다른 각도의 보충 설명으로 쓰세요. 5개 중 최소 2개는 본문에 없는 새로운 정보(관련 제도,
놓치기 쉬운 예외, 추가 확인처 등)를 담으세요. 5개 질문의 문형과 끝맺는 말을 서로 다르게 쓰세요.
질문에 "(제도)", "[대상]", "OOO", "○○" 같은 분류 라벨이나 자리표시자를 절대 쓰지 말고, 완성된
문장으로만 쓰세요.)
<!--FAQ_END-->
<!--CLOSING_START-->
(마무리 — <p> 태그 2~4문장, 공백 제외 100~220자. 먼저 편집자 관점에서 이 글이 권하는 판단을
한 문장으로 쓰세요(예: "결국 장기요양등급은 신청 시점보다 등급 판정 기준을 먼저 아는 쪽이 유리
합니다"처럼 근거가 붙는 한 문장). 그다음 핵심 한 줄 정리와 독자가 바로 해볼 수 있는 행동 한
가지를 덧붙이고, "정확한 최신 기준은 국민건강보험공단(1577-1000)·보건복지부·지자체(주민센터·
보건소)에서 다시 확인하시길 바랍니다"라는 취지와 "이 글은 일반적인 정보이며 의료·법률 상담을
대신하지 않습니다"라는 취지를 자연스럽게 포함하되, 매번 같은 문장을 복사하지 말고 표현을
조금씩 바꿔서 쓰세요.)
<!--CLOSING_END-->
<!--TIPS_START-->
(🛠 실전 팁 — <ul><li> 2~4개, 항목당 한 문장. "오늘 바로 확인하세요", "~부터 준비하세요" 같은
행동형 문장으로 쓰고, 가능하면 확인 순서나 확인처를 함께 쓰세요. 바로 위 CLOSING의 판단 문장을
그대로 반복하지 마세요. "미리 확인하세요"처럼 무엇을 확인하는지 없는 빈 팁은 쓰지 마세요.)
<!--TIPS_END-->
<!--CLOSINGQ_START-->
(💬 마무리 질문 — 한 줄. 독자의 상황을 묻는 질문 하나로 쓰세요. 예: "부모님 장기요양등급을
이미 신청해 보신 분들은 어느 단계에서 가장 막막하셨나요?" 공감·저장을 구걸하는 문구를 쓰지
마세요.)
<!--CLOSINGQ_END-->

[문장 톤 규칙]
- 어조는 "~합니다", "~해보세요"체의 다정하고 담백한 존댓말을 사용하세요. "~에요", "~죠",
  "~잖아요" 같은 구어체는 쓰지 마세요.
- "A는 ~합니다. 또한 B합니다. 그리고 C합니다." 같은 단순 나열식 문장 반복은 피하고, 문장 길이와
  구조를 문단마다 다르게 가져가세요. 같은 문장 종결 패턴이 두 문장 이상 연속으로 이어지지 않게
  하세요. 모든 소제목을 같은 문형으로 만들지 마세요. 문단마다 "또한/한편/따라서/결론적으로"로
  시작하지 마세요.
- 같은 내용을 도입·본문·마무리에서 반복해 분량을 채우지 마세요. 분량은 새로운 정보와 구체적인
  예시로 채우세요.
- 다음 표현은 쓰지 마세요: "최고", "무조건", "100%", "완치", "효과 보장", "완벽 보장",
  "단번에 해결", "역대급", "~에 대해 알아보겠습니다", "결론적으로", "마무리하며", "도움이
  되셨으면 좋겠습니다", "누구나 한 번쯤", "아련한 추억", "~의 매력과 가치", "~를 바탕으로
  살펴보면", "직접 가봤더니", "다녀와 보니", "제가 경험한 바로는"(이 블로그는 직접 방문·경험
  콘텐츠가 아니므로 체험 표현은 절대 쓰지 마세요). "매우 중요합니다"·"다양한"·"효과적인" 같은
  표현도 반복해서 쓰지 마세요.

[사실관계 정확성 규칙 — 반드시 지켜야 함]
- 신청기한·금액·등급기준 등 구체적인 수치는 일반적으로 널리 알려진 내용 위주로 서술하고,
  법령이나 제도는 개정될 수 있으므로 절대 확정적으로 단언하지 마세요.
- 존재 여부가 불확실한 인물, 책, 논문, 통계, 연구 결과, 기관 발표를 지어내지 말고, "전문가들은",
  "연구에 따르면" 같은 출처 없는 권위 표현도 쓰지 마세요. 출처를 댈 수 없으면 "일반적으로",
  "전통적으로"처럼 범위를 한정해 쓰세요.
- 의료적 진단이나 처방으로 오인될 수 있는 단정적 표현("이러면 틀림없이 ~병입니다", "무조건
  ~하면 됩니다")은 쓰지 말고, 증상 관련 내용은 의료진 상담을 권하는 톤을 유지하세요.
- 법률·세금·재산 관련은 일반적인 설명에 그치고, 구체적인 사안은 전문가 확인이 필요하다고
  안내하세요.
- 보호자의 죄책감이나 불안을 자극하는 표현("방치하면 큰일 납니다" 등)은 쓰지 마세요.{feedback_block}"""


# 우선순위 순서 — 맨 앞이 실패하면 다음 것을 자동으로 시도 (create_knowledge.py와 동일한 이유)
# 2026-11-02: 'gemini-3-flash'가 v1beta generateContent에서 404 NOT_FOUND로 확인되어 제거함
#             (gemini-2.5-flash가 2026-07-09부터 예고 없이 404를 반환하기 시작했던 것과 같은 유형의
#             문제 — Gemini 쪽에서 모델명을 조용히 폐기/교체하는 경우가 있어 주기적으로 재확인 필요)
GEMINI_MODEL_CANDIDATES = [
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
]

# 모델 출력이 한국어 3,000자 이상이어도 잘리지 않도록 넉넉히 설정 (v7.6 §22.8.7)
_GEMINI_CONFIG = types.GenerateContentConfig(max_output_tokens=8192)

# 503(UNAVAILABLE)·429(RESOURCE_EXHAUSTED) 등은 "지금 혼잡하니 나중에 다시 시도하라"는
# 일시적 오류 — 404(모델 자체가 없음) 같은 영구적 오류와는 구분해서 재시도할 가치가 있다.
_RETRYABLE_MARKERS = ("UNAVAILABLE", "RESOURCE_EXHAUSTED", "DEADLINE_EXCEEDED", "503", "429")


def _is_retryable(err):
    msg = str(err)
    return any(marker in msg for marker in _RETRYABLE_MARKERS)


def _call_gemini_with_fallback(client, prompt):
    """모델 후보를 순서대로 시도하고, 전원이 '일시적' 오류로만 실패하면 30초 뒤 전체를
    한 번 더 재시도한다 (2026-11-01 — 주 1회뿐인 실행에서 전 후보가 503으로 실패해 그 주
    발행이 통째로 날아간 사례의 재발 방지). generate_dolbom_post()의 최초 생성·재생성·
    보강 생성이 모두 이 함수 하나를 공유한다."""
    last_err = None
    for attempt in range(2):
        if attempt > 0:
            print("  ⏳ 모든 모델이 일시적 오류(과부하 등)로 실패 — 30초 대기 후 전체 재시도")
            time.sleep(30)

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
                if not _is_retryable(e):
                    all_retryable = False

        if not all_retryable:
            break

    raise RuntimeError(f"모든 Gemini 모델 후보가 실패했습니다. 마지막 에러: {last_err}")


# ─────────────────────────────────────────
# v7.6 §22 정보형 블로그 모듈 — 돌봄상식(§22.5-B) 적용
# ─────────────────────────────────────────

# §22.7 관점 로테이션 — 주제가 두 바퀴째 돌 때부터는 다른 관점으로 써서 중복 콘텐츠를 피한다.
PERSPECTIVES = ["기본 개념", "생활 활용", "흔한 오해 바로잡기", "상황별 가이드", "체크리스트"]

# §4.1/4.2 — 객관적 근거 없는 과장·슬로건형 표현. 흔한 일반 단어("다양한" 등 §4.3)는
# 정상적인 글에서도 자연스럽게 쓰일 수 있어 코드 단계의 강제 재생성 대상에서 제외하고
# (아래 build_prompt의 문장 톤 규칙으로만 안내), 아래 목록은 실제로 발생 시 재생성할
# 가치가 있는 과장 표현만 추렸다.
# v9.5 §23.2(실제 발행 글에서 반복된 상투적 시작 틀)·§23.8(이 블로그에는 없는 "직접 방문·체험"
# 표현)에서 정밀하게 추린 문구를 추가했다 — 둘 다 평범한 글에서 우연히 나올 가능성이 낮은
# 멀티워드 문구만 골라서, 과하게 걸려 매주 재생성/건너뛰기가 늘어나는 부작용을 피했다.
_BANNED_HARD = [
    "최고의", "무조건", "100% 효과", "완치", "효과 보장", "완벽 보장", "단번에 해결", "역대급",
    "새로운 가치를 만듭니다", "당신의 성공과 함께합니다", "차별화된 서비스", "고객 만족을 최우선으로",
    "정성을 다하겠습니다", "에 대해 알아보겠습니다", "결론적으로", "마무리하며",
    "도움이 되셨으면 좋겠습니다",
    "누구나 한 번쯤", "아련한 추억", "의 매력과 가치", "를 바탕으로 살펴보면",
    "데이터를 바탕으로 분석한 결과",
    "직접 가봤더니", "다녀와 보니", "제가 경험한 바로는", "먹어봤는데", "써 보니",
]


def _find_banned(text):
    return [p for p in _BANNED_HARD if p in text]


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _visible_len(html_fragment):
    """HTML 태그와 공백·줄바꿈을 뺀 글자 수 (§22.2/§22.8 분량 기준)."""
    text = _TAG_RE.sub("", html_fragment or "")
    text = _WS_RE.sub("", text)
    return len(text)


def _first_words(text, n=12):
    """첫 문장 앞 n어절만 뽑아 중복 방지용 기록에 쓴다 (§23.6)."""
    plain = _TAG_RE.sub(" ", text or "")
    plain = _WS_RE.sub(" ", plain).strip()
    return " ".join(plain.split(" ")[:n])


_SECTION_PATTERNS = {
    "title":   re.compile(r"<!--TITLE_START-->(.*?)<!--TITLE_END-->", re.S),
    "intro":   re.compile(r"<!--INTRO_START-->(.*?)<!--INTRO_END-->", re.S),
    "body":    re.compile(r"<!--BODY_START-->(.*?)<!--BODY_END-->", re.S),
    "faq":     re.compile(r"<!--FAQ_START-->(.*?)<!--FAQ_END-->", re.S),
    "closing": re.compile(r"<!--CLOSING_START-->(.*?)<!--CLOSING_END-->", re.S),
}
_FAQ_ITEM_RE = re.compile(r'class="faq-item"', re.I)

# v9.5 선택 섹션 — 있으면 쓰고 없으면 그 박스만 생략한다(필수 5개 구분자와 달리 파싱 실패로
# 재시도를 유발하지 않는다). §19.5(한줄요약·목차)·§19.6(나만의 포인트·간단 정리·한 번에
# 정리·실전 팁)·§19.7-F(마무리 질문).
_OPTIONAL_SECTION_PATTERNS = {
    "summary":  re.compile(r"<!--SUMMARY_START-->(.*?)<!--SUMMARY_END-->", re.S),
    "mypoint":  re.compile(r"<!--MYPOINT_START-->(.*?)<!--MYPOINT_END-->", re.S),
    "oneshot":  re.compile(r"<!--ONESHOT_START-->(.*?)<!--ONESHOT_END-->", re.S),
    "tips":     re.compile(r"<!--TIPS_START-->(.*?)<!--TIPS_END-->", re.S),
    "closingq": re.compile(r"<!--CLOSINGQ_START-->(.*?)<!--CLOSINGQ_END-->", re.S),
}

# §23.5 — FAQ 질문에 분류 라벨·자리표시자가 남으면(예: "(제도)", "[대상]", "OOO", "○○")
# 발행된 글에 템플릿 조각이 그대로 노출되는 것이므로 길이·FAQ 개수와 동급의 하드 게이트로 검사한다.
_PLACEHOLDER_RE = re.compile(r'[\(\[][^)\]]{0,24}/[^)\]]{0,24}[\)\]]|○{2,}|[Oo]{3,}|[xX]{3,}')

# §19.6-B — 각 <h2> 섹션 뒤의 "📝 간단 정리"는 분량(2,000자) 집계에서 뺀다(§23.7).
_MINI_SUM_RE = re.compile(r'<p[^>]*class="mini-sum"[^>]*>.*?</p>', re.S | re.I)
_H2_RE = re.compile(r'<h2[^>]*>(.*?)</h2>', re.S | re.I)


def _find_placeholder(text):
    return _PLACEHOLDER_RE.findall(text or "")


def _strip_mini_sum(body_html):
    return _MINI_SUM_RE.sub("", body_html or "")


def _extract_h2_titles(body_html):
    titles = []
    for m in _H2_RE.finditer(body_html or ""):
        t = _TAG_RE.sub("", m.group(1)).strip()
        if t:
            titles.append(t)
    return titles


def _inject_h2_ids(body_html):
    """<h2>마다 고유 id(hh-s1, hh-s2 …)를 코드에서 직접 부여해 목차 앵커와 정확히 대응시킨다
    (§19.5-C/§23.10-B) — AI에게 id를 맡기면 누락·중복 위험이 있다."""
    counter = {"n": 0}

    def _add_id(m):
        counter["n"] += 1
        return f'<h2 id="hh-s{counter["n"]}">{m.group(1)}</h2>'

    return _H2_RE.sub(_add_id, body_html or "")


def _build_toc_html(h2_titles):
    """📚 목차는 AI에게 맡기지 않고 실제 본문 <h2>에서 그대로 뽑아 만든다 — 목차와 본문이
    어긋날 위험을 구조적으로 없앤다 (§19.5-C)."""
    if not h2_titles:
        return ""
    items = "".join(f'<li><a href="#hh-s{i + 1}">{t}</a></li>' for i, t in enumerate(h2_titles))
    return f'<div class="box-toc"><div class="box-label">📚 목차</div><ol>{items}</ol></div>'


def _parse_sections(raw):
    sections = {}
    for key, rx in _SECTION_PATTERNS.items():
        m = rx.search(raw)
        if not m:
            return None
        sections[key] = m.group(1).strip()
    return sections


def _parse_optional_sections(raw):
    out = {}
    for key, rx in _OPTIONAL_SECTION_PATTERNS.items():
        m = rx.search(raw)
        out[key] = m.group(1).strip() if m else ""
    return out


def pick_perspective(state, idx):
    """주제 idx를 몇 번째로 다루는지에 따라 관점을 순환시킨다. (첫 바퀴=기본 개념, 둘째 바퀴=생활 활용, …)"""
    visits = state.setdefault("topic_visit_count", {})
    key = str(idx)
    n = visits.get(key, 0)
    return PERSPECTIVES[n % len(PERSPECTIVES)], key, n


class ContentQualityError(Exception):
    """분량·FAQ 개수·금지 표현·FAQ 자리표시자 기준을 끝내 충족하지 못해 발행을 보류함.
    인프라(Gemini API·인증 등) 문제가 아니라 콘텐츠 품질 기준에 의한 의도된 보류이므로,
    run()/main()에서 '정상 종료(exit 0)'로 처리해야 할 신호로 구분해서 쓴다."""
    pass


def generate_dolbom_post(topic, perspective, style, recent_history):
    """제목·도입·본문·FAQ·마무리(필수 5개, v7.6과 동일)와 한줄요약·나만의 포인트·한 번에 정리·
    실전 팁·마무리 질문(선택 5개, v9.5 신설)을 생성하고, 분량(2,000자 이상 — 한줄요약·나만의
    포인트·목차·간단 정리·한 번에 정리는 제외, 실전 팁은 포함 §23.7)·FAQ 개수(5개)·금지 표현·
    FAQ 자리표시자 여부를 코드에서 직접 검증한다. 기준 미달이면 최대 2회 재생성하고, 분량만
    부족하면 보강 섹션을 한 번 더 추가해본다. 끝까지 기준을 못 채우면 ContentQualityError를
    던져 발행을 보류한다 — 이는 인프라 문제가 아니라 의도된 품질 게이트이므로 run()이 구분해서
    처리한다 (기준 미달 글을 올리는 것보다 한 주 건너뛰는 편이 낫다는 §22.8.6/§23.7 원칙).
    반면 Gemini 호출 자체가 매 시도 다 실패해 파싱 가능한 응답을 한 번도 못 받았다면
    이는 인프라 문제이므로 RuntimeError를 그대로 위로 전파한다(이 경우 run()은 종전처럼
    경고 후 건너뛰고, 결국 success_count==0이면 main()이 exit(1)로 알린다).

    선택 섹션(한줄요약 등)은 파싱 실패로 재시도를 유발하지 않는다 — 반복되는 주간 자동화에서
    "완벽히 못 채우면 건너뛴다"를 선택 섹션에까지 적용하면 매주 멈출 위험이 커지기 때문이다."""
    client = genai.Client(api_key=GEMINI_API_KEY)
    feedback = ""
    last_sections, last_optional, last_total = None, None, 0
    last_faq_count, last_banned, last_placeholder = 0, [], []
    ever_parsed = False
    last_infra_err = None

    for attempt in range(3):
        prompt = build_prompt(topic, perspective, style, recent_history, feedback=feedback)
        try:
            raw = _call_gemini_with_fallback(client, prompt)
        except Exception as e:
            print(f"  ⚠️ Gemini 생성 실패({attempt + 1}/3): {e}")
            last_infra_err = e
            feedback = ""
            continue

        sections = _parse_sections(raw)
        if sections is None:
            print(f"  ⚠️ 응답 형식 오류({attempt + 1}/3) — 구분자 누락")
            feedback = ("직전 응답이 지정된 구분자(<!--TITLE_START--> 등) 형식을 지키지 않았습니다. "
                        "다른 설명 없이 지정된 구분자 형식 그대로만 출력하세요.")
            continue

        ever_parsed = True
        optional = _parse_optional_sections(raw)
        body_for_count = _strip_mini_sum(sections["body"])
        total_len = (_visible_len(sections["intro"]) + _visible_len(body_for_count) +
                     _visible_len(sections["faq"]) + _visible_len(sections["closing"]) +
                     _visible_len(optional.get("tips", "")))
        faq_count = len(_FAQ_ITEM_RE.findall(sections["faq"]))
        banned_scan = "".join([
            sections["intro"], sections["body"], sections["closing"],
            optional.get("summary", ""), optional.get("mypoint", ""),
            optional.get("oneshot", ""), optional.get("tips", ""),
        ])
        banned_hits = _find_banned(banned_scan)
        placeholder_hits = _find_placeholder(sections["faq"])
        last_sections, last_optional, last_total = sections, optional, total_len
        last_faq_count, last_banned, last_placeholder = faq_count, banned_hits, placeholder_hits

        problems = []
        if total_len < 2000:
            problems.append(f"전체 글자수 {total_len}자(2,000자 미달)")
        if faq_count != 5:
            problems.append(f"FAQ {faq_count}개(5개 필요)")
        if banned_hits:
            problems.append(f"금지 표현 포함: {', '.join(banned_hits)}")
        if placeholder_hits:
            problems.append(f"FAQ에 분류 라벨/자리표시자 포함: {', '.join(placeholder_hits)}")

        if not problems:
            return sections, optional, total_len

        print(f"  ⚠️ 품질 기준 미달({attempt + 1}/3): {' / '.join(problems)}")
        feedback = ("직전 결과가 다음 기준을 충족하지 못했습니다 — " + " / ".join(problems) +
                    ". 같은 주제와 관점을 유지한 채 본문 섹션과 FAQ 답변에 구체적인 설명을 "
                    "보강해서 다시 작성하세요. FAQ 질문에는 분류 라벨이나 자리표시자를 쓰지 말고 "
                    "완성된 문장으로만 쓰세요.")

    # 분량만 부족하고 나머지는 정상이면, 겹치지 않는 섹션 하나를 추가로 생성해 붙여본다.
    if (last_sections and last_faq_count == 5 and not last_banned and not last_placeholder
            and last_total < 2000):
        try:
            supplement_prompt = (
                f"주제 '{topic}'에 대한 블로그 글을 쓰고 있습니다. 아래는 지금까지 작성된 본문입니다.\n\n"
                f"{last_sections['body']}\n\n"
                "위 내용과 겹치지 않는 새로운 소제목(<h2>)과 본문(<p>, 공백 제외 300~450자)을 "
                "하나만 순수 HTML 조각으로 추가 작성하세요. 코드블록이나 다른 설명 문구 없이 "
                "<h2>...</h2><p>...</p> 형식으로만 출력하세요."
            )
            extra_raw = _call_gemini_with_fallback(client, supplement_prompt)
            if _visible_len(extra_raw) > 50:
                last_sections["body"] += "\n" + extra_raw
                last_total = (_visible_len(last_sections["intro"]) +
                              _visible_len(_strip_mini_sum(last_sections["body"])) +
                              _visible_len(last_sections["faq"]) +
                              _visible_len(last_sections["closing"]) +
                              _visible_len(last_optional.get("tips", "")))
        except Exception as e:
            print(f"  ⚠️ 보강 생성 실패: {e}")

    if (last_sections and last_faq_count == 5 and not last_banned and not last_placeholder
            and last_total >= 2000):
        print(f"  ✅ 보강 후 기준 충족 ({last_total}자)")
        return last_sections, last_optional, last_total

    if not ever_parsed:
        # 3번 다 Gemini 호출/형식 단계에서 막혀 내용을 한 번도 못 받음 — 품질 문제가 아니라 인프라 문제.
        raise RuntimeError(f"Gemini 응답을 한 번도 정상적으로 받지 못했습니다. 마지막 에러: {last_infra_err}")

    print("  ❌ 품질 기준을 끝내 충족하지 못해 이번 주제는 발행을 보류합니다(인프라 문제 아님).")
    raise ContentQualityError(topic)


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {"last_index": -1, "history": []}
    # 숫자 URL 슬러그 순차번호 — 오늘의명언(1만번대)·운세상식(2만번대)과 안 겹치게 3만번대 사용
    state.setdefault("next_slug_number", 30001)
    # 주제별로 몇 바퀴째 다뤘는지 — 관점(perspective) 로테이션에 사용 (§22.7)
    state.setdefault("topic_visit_count", {})
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
    hard_failure = False  # Gemini/Blogger 인프라 문제로 한 건도 못 올렸는지 (품질 게이트 보류와는 구분)

    for i in range(count):
        idx  = (state["last_index"] + 1) % n
        item = TOPICS[idx]
        topic, emoji, tags = item["topic"], item["emoji"], item["tags"]
        perspective, visit_key, visit_n = pick_perspective(state, idx)
        _cp = coupang_links.get(idx, {})
        coupang_url     = _cp.get("coupang_url", "")
        product_keyword = _cp.get("product_keyword", "")

        style = "checklist" if (any(t in _CHECKLIST_TAGS for t in tags) or perspective == "체크리스트") else "info"

        cycle_note = " (주제 리스트를 모두 사용해 처음부터 다시 순환합니다)" \
            if idx == 0 and state["last_index"] != -1 else ""
        print(f"[{i+1}/{count}] 주제 #{idx}: {topic} / 관점: {perspective}{cycle_note}")

        recent_history = [
            {"title": h.get("title"), "h2": h.get("h2") or [], "first_words": h.get("first_words")}
            for h in state.get("history", [])[-8:] if h.get("title")
        ]

        try:
            sections, optional, total_len = generate_dolbom_post(topic, perspective, style, recent_history)
        except ContentQualityError:
            # 품질 기준(분량/FAQ/금지표현/자리표시자) 미달로 의도적으로 보류 — 인프라 문제 아님.
            # 이 주제에 계속 멈춰 있지 않도록 인덱스만 전진시켜 저장한다(관점 카운트·history는 그대로 —
            # 다음 바퀴에 이 주제를 다시 만나면 같은 관점으로 한 번 더 시도).
            state["last_index"] = idx
            save_state(state)
            continue
        except Exception as e:
            print(f"  ⚠️ '{topic}' 생성 중 인프라 오류: {e} — 이 주제는 건너뜁니다.")
            hard_failure = True
            continue

        # §19.5-C/§23.10-B — 목차 앵커는 AI에게 맡기지 않고 본문 <h2>에서 직접 뽑아 id를 부여한다.
        h2_titles = _extract_h2_titles(sections["body"])
        body_html = _inject_h2_ids(sections["body"])
        toc_html = _build_toc_html(h2_titles)

        def _box(label, inner_html, css_class):
            return (f'<div class="{css_class}"><div class="box-label">{label}</div>{inner_html}</div>'
                    if inner_html else "")

        summary_html  = _box("📌 한줄요약", optional.get("summary", ""), "box-summary")
        mypoint_html  = _box("📍 나만의 포인트", optional.get("mypoint", ""), "box-mypoint")
        oneshot_html  = _box("✅ 한 번에 정리", optional.get("oneshot", ""), "box-oneshot")
        tips_html     = _box("🛠 실전 팁", optional.get("tips", ""), "box-tips")
        closingq_html = (f'<p class="closing-q">💬 {optional["closingq"]}</p>'
                          if optional.get("closingq") else "")
        checkpoints_html = _build_checkpoints_html()

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

        post_title = sections["title"] or topic

        content = f"""{knowledge_style()}
<div class="wrap">
  <div class="hero">
    <h1>{emoji} {post_title}</h1>
    <p>돌봄 상식</p>
  </div>
  {disclosure_html}
  <div class="card">
    <p class="intro">{sections['intro']}</p>
    {summary_html}
    {mypoint_html}
    {toc_html}
    {body_html}
    {oneshot_html}
  </div>
  {product_html}
  <div class="card">
    {sections['closing']}
    {tips_html}
  </div>
  <div class="card"><span class="badge">🙋 자주 묻는 질문</span>
    {sections['faq']}
  </div>
  <div class="card">
    {checkpoints_html}
    {closingq_html}
  </div>
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
        ok = post_blogger_scheduled(access_token, post_title, content, ["돌봄상식"], slug_number=slug_number)

        if ok:
            state["last_index"] = idx
            state["next_slug_number"] = slug_number + 1
            state.setdefault("topic_visit_count", {})[visit_key] = visit_n + 1
            state["history"].append({
                "index":       idx,
                "topic":       topic,
                "title":       post_title,
                "perspective": perspective,
                "char_count":  total_len,
                "slug":        str(slug_number),
                "posted_at":   datetime.now(timezone.utc).isoformat(),
                "h2":          h2_titles,
                "first_words": _first_words(sections["intro"]),
            })
            save_state(state)
            success_count += 1
        else:
            print(f"  ❌ '{post_title}' 발행 실패 — 인덱스를 저장하지 않습니다. "
                  f"다음 실행 때 같은 주제부터 다시 시도합니다.")
            hard_failure = True
            break

        if i < count - 1:
            time.sleep(5)

    return success_count, hard_failure


def main():
    parser = argparse.ArgumentParser(description="돌봄상식 카테고리 자동 생성/발행")
    parser.add_argument("--count", type=int, default=1,
                         help="이번 실행에서 생성할 글 개수 (기본 1, 초기 시드 배치는 --count 10 처럼 크게)")
    args = parser.parse_args()

    print(f"🚀 돌봄상식 생성 시작 — {args.count}개")
    success_count, hard_failure = run(args.count)

    if success_count == 0:
        if hard_failure:
            print("❌ 이번 실행에서 발행에 성공한 글이 하나도 없습니다 (Gemini/Blogger 인프라 오류).")
            sys.exit(1)
        else:
            # 품질 기준 미달로만 보류된 경우 — 인프라는 정상이었으므로 Actions를 실패로 표시하지 않는다.
            # (§22.8.6: 기준 미달 글을 올리는 것보다 건너뛰는 편이 낫다는 원칙에 따른 "의도된 건너뜀")
            print("ℹ️ 이번 실행은 품질 기준 미달로 발행을 건너뛰었습니다 (인프라 문제 아님, 다음 실행은 "
                  "다음 주제로 자동 이동). 정상 종료합니다.")
            return

    print(f"🎉 완료 — {success_count}개 발행")


if __name__ == "__main__":
    main()
