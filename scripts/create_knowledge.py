#!/usr/bin/env python3
"""
create_knowledge.py — '운세상식' 카테고리 정보성 글 자동 생성/발행 (SEO 프롬프트 v9.5 · 호호매거진 편집 모듈 적용)
=======================================================================
기존 create_post.py(CSV 기반 매일 운세 27개 자동화)와 완전히 독립된 스크립트입니다.
(create_post.py를 import하지 않으며, 새로 만드는 파일은 data/knowledge_state.json 하나뿐입니다.)

[v9.5 방식 — 2026-11 개편]
  · Gemini는 JSON(내용)만 만들고, 코드가 HTML을 조립합니다.
    구조: 도입 → 📌한줄요약 → 📍나만의 포인트 → 📚목차(앵커) → 본문 H2 4~5개(각 📝간단 정리)
          → ✅한 번에 정리 → 표(0~3) → 이 글의 판단 → 🛠실전 팁 → FAQ 5개 → 참고할 수 있는 공식 자료 → 💬마무리 질문 → 해시태그
  · 분량: 박스류·해시태그를 뺀 본문 공백 제외 2,000자 이상 (섹션만 1,300자 이상), 못 채우면 발행하지 않음
  · 글 유형 5종 로테이션(직전 3개와 다른 유형), 직전 10개 글의 제목·H2·FAQ·첫 문장과 중복 방지
  · 주제별 편집자 관점(_META), 절기·보름달·태양 별자리 천문 계산값 주입(ephem, 실패하면 생략)
  · 상황형 제목을 쓰므로 주제 키를 상태 파일과 글의 customMetaData("topic:...")에 저장해 중복 발행을 막음
  · 기존에 올라간 글(구형식)은 건드리지 않음 — 신규 발행분부터 적용

실행:
  python scripts/create_knowledge.py             # 1개 생성/발행 (주간 cron 기본값)
  python scripts/create_knowledge.py --count 5   # 초기 시드 배치용

환경변수:
  GEMINI_API_KEY, BLOG_ID, BLOGGER_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET  (필수)
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
from datetime import datetime, timezone, timedelta

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


def post_blogger_scheduled(access_token, title, content, labels, published_iso=None, slug_number=None, custom_meta=None, is_draft=False):
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
    qs = {"isDraft": "true"} if is_draft else None   # 초안 모드: 공개하지 않고 Blogger 초안함에만 저장

    slug_title = str(slug_number) if slug_number else None
    insert_title = slug_title or title

    body = {"title": insert_title, "content": content, "labels": labels}
    if custom_meta:
        body["customMetaData"] = custom_meta   # 주제 키 저장 — 제목이 상황형이라 제목만으로는 중복 판단이 안 됨
    if published_iso:
        body["published"] = published_iso

    post_id = None
    for attempt in range(1, 4):  # 최대 3회 재시도 (기존 post_blogger()와 동일한 패턴)
        resp = requests.post(url, params=qs,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json=body)
        if resp.status_code in (200, 201):
            post_id = resp.json().get("id")
            break
        elif resp.status_code == 429:
            wait = 60 * attempt
            print(f"⏳ 429 쿼터 초과 — {wait}초 대기 후 재시도 ({attempt}/3)")
            time.sleep(wait)
        elif resp.status_code == 400 and body.get("customMetaData"):
            print(f"⚠️ customMetaData 거부({resp.text[:100]}) — 주제 키 없이 다시 시도")
            body.pop("customMetaData", None)
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

KST = timezone(timedelta(hours=9))


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
    {"topic": "복을 부르는 현관 인테리어와 거울 위치",         "emoji": "🚪", "tags": ["풍수", "현관인테리어", "풍수지리"], "angle": "현관 정리의 실용 포인트(신발 정리, 동선, 조명, 환기)를 먼저 쓰고, 풍수에서 현관과 거울에 대해 전해지는 원칙은 '전통적으로 ~라고 봅니다'로 소개하세요. 복이 들어온다는 결과를 약속하지 마세요.", "slug": "entrance-fengshui"},
    {"topic": "재물운을 높이는 침실 침대 방향과 풍수지리",     "emoji": "🛏️", "tags": ["풍수", "침실풍수", "재물운"], "angle": "수면 환경 상식과 풍수 전통을 함께 다루세요. 조도·소음·온도, 침대와 출입문·창문의 위치가 주는 심리적 안정감 같은 일반적인 내용을 먼저 설명하고, 풍수에서 전해지는 방향·배치 원칙은 '전통적으로 ~라고 봅니다'로 소개하세요. 재물·건강 효과를 단정하거나 의학적 조언을 하지 마세요.", "slug": "bedroom-fengshui"},
    {"topic": "행운의 색이 알려주는 나만의 기운 이야기",       "emoji": "🎨", "tags": ["행운의색", "색채심리", "운세상식"], "angle": "색채가 주는 일반적인 심리적 연상(따뜻함·차분함 등)과 전통 오방색(청·적·황·백·흑)의 방위·오행 대응을 중심으로 설명하세요. '나만의 행운의 색'을 고르는 간단한 방법은 재미로 참고하는 활동으로 소개하고 효과를 단정하지 마세요.", "slug": "lucky-color"},
    {"topic": "태어난 달로 알아보는 탄생석의 의미",           "emoji": "💎", "tags": ["탄생석", "탄생석의미", "보석상식"], "angle": "월별 탄생석 이름을 정확히 정리하되, 나라·문화권·시기에 따라 목록이 다를 수 있음을 밝히세요. 각 보석의 의미는 '전해지는 상징'으로 소개하고, 보석 구매·투자 권유나 효능 주장은 하지 마세요.", "slug": "birthstone-meaning"},
    {"topic": "재물운을 부르는 지갑 색깔과 정리 습관",         "emoji": "🪙", "tags": ["지갑풍수", "재물운", "정리습관"], "angle": "지갑 정리 습관이 중심입니다. 영수증·카드·현금 정리 요령, 지갑 점검 주기를 구체적으로 쓰세요. 색깔에 얽힌 전통적 의미와 색채 연상은 '전해지는 이야기'로 소개하고, 재물이 늘어난다는 식의 효과나 재테크·투자 조언은 쓰지 마세요.", "slug": "wallet-fengshui"},
    {"topic": "별자리별 잘 어울리는 향수 노트 찾기",           "emoji": "🌸", "tags": ["별자리향수", "향수추천", "별자리매칭"], "angle": "향수 지식이 중심입니다. 탑·미들·베이스 노트의 구조와 지속 시간 차이, 시트러스·플로럴·우디·머스크 같은 향 계열의 특징을 먼저 설명하세요. 별자리별 추천은 불·흙·공기·물 원소 이미지에서 연상한 '재미 요소'로만 소개하고 근거를 단정하지 마세요. 특정 브랜드·제품명은 쓰지 마세요.", "slug": "zodiac-perfume"},
    {"topic": "이사할 때 챙기면 좋은 손없는 날과 개운 소품",   "emoji": "🧂", "tags": ["손없는날", "이사풍수", "개운소품"], "angle": "사실 정보가 중심입니다. 음력 날짜 끝자리가 9·0인 날(9·10·19·20·29·30일)이 손 없는 날로 전해진다는 점, 손(損)이 날짜에 따라 방향을 옮겨 다니며 일을 방해한다고 믿던 민간 전승, 음력 날짜를 확인하는 방법을 설명하세요. 이사 날짜 선택의 현실 팁(수요가 몰려 비용·예약이 어려울 수 있음, 최신 상황은 확인 필요)과 이사 전후 점검 목록을 포함하고, 믿음 여부와 상관없이 쓸 수 있게 쓰세요.", "slug": "moving-day-fengshui"},
    {"topic": "수험생 자녀를 둔 부모를 위한 합격운 높이는 방법", "emoji": "📚", "tags": ["합격운", "수험생", "학부모"], "angle": "수험생 부모가 실제로 할 수 있는 지원이 중심입니다. 수면·식사 리듬, 대화 방식, 시험 당일 준비물과 이동 점검, 불안을 다루는 방법을 구체적으로 쓰세요. 엿·찹쌀떡 같은 합격 기원 풍습은 '전해 내려오는 풍습'으로 한 섹션만 소개하고 합격 효과를 단정하지 마세요.", "slug": "exam-luck-guide"},
    {"topic": "이직·취업 준비생을 위한 취업운 체크리스트",     "emoji": "💼", "tags": ["취업운", "이직", "구직"], "angle": "운세 문구가 아니라 실제 취업 준비 점검표가 중심입니다. 이력서·포트폴리오 정리, 지원 현황 기록, 면접 일정과 컨디션 관리, 면접 전날·당일 준비물 점검 등 오늘 바로 해볼 수 있는 행동을 구체적으로 쓰세요. 면접 날 옷 색 같은 전해지는 습속은 '심리적 안정 장치' 정도로 한 문단만 소개하고 효과를 단정하지 마세요.", "slug": "job-luck-checklist"},
    {"topic": "신혼부부를 위한 재물운 부르는 인테리어",         "emoji": "🏠", "tags": ["신혼부부", "재물운", "인테리어풍수"], "angle": "신혼집 정리 요령(수납, 동선, 공용 공간 배치, 둘이 함께 정하는 규칙)을 구체적으로 쓰고, 풍수에서 전해지는 배치 원칙은 '전통적으로 ~라고 봅니다'로 소개하세요. 재물이 늘어난다는 효과나 재테크 조언은 쓰지 마세요.", "slug": "newlywed-fengshui"},
    {"topic": "섬세하고 온화한 토끼띠의 성격과 어울리는 환경", "emoji": "🐰", "tags": ["토끼띠", "띠별성격", "사주"], "slug": ""},
    {"topic": "카리스마 넘치는 용띠의 성격과 특징 4가지", "emoji": "🐲", "tags": ["용띠", "띠별성격", "사주"], "slug": ""},
    {"topic": "신중하고 통찰력 깊은 뱀띠의 성격 분석", "emoji": "🐍", "tags": ["뱀띠", "띠별성격", "사주"], "slug": ""},
    {"topic": "자유롭고 활동적인 말띠의 성격과 특징", "emoji": "🐴", "tags": ["말띠", "띠별성격", "사주"], "slug": ""},
    {"topic": "온순하고 배려심 깊은 양띠의 성격 이야기", "emoji": "🐑", "tags": ["양띠", "띠별성격", "사주"], "slug": ""},
    {"topic": "재치 있고 호기심 많은 원숭이띠의 성격 특징", "emoji": "🐵", "tags": ["원숭이띠", "띠별성격", "사주"], "slug": ""},
    {"topic": "성실하고 꼼꼼한 닭띠의 성격과 장단점", "emoji": "🐔", "tags": ["닭띠", "띠별성격", "사주"], "slug": ""},
    {"topic": "의리 있고 정직한 개띠의 성격 분석", "emoji": "🐶", "tags": ["개띠", "띠별성격", "사주"], "slug": ""},
    {"topic": "복스럽고 낙천적인 돼지띠의 성격과 특징", "emoji": "🐷", "tags": ["돼지띠", "띠별성격", "사주"], "slug": ""},
    {"topic": "개척 정신이 강한 양자리의 유래와 신화", "emoji": "♈", "tags": ["양자리", "별자리유래", "그리스신화"], "slug": ""},
    {"topic": "끈기 있는 황소자리의 유래와 신화 이야기", "emoji": "♉", "tags": ["황소자리", "별자리유래", "그리스신화"], "slug": ""},
    {"topic": "호기심 많은 쌍둥이자리의 유래와 신화", "emoji": "♊", "tags": ["쌍둥이자리", "별자리유래", "그리스신화"], "slug": ""},
    {"topic": "감성이 풍부한 게자리의 유래와 신화 이야기", "emoji": "♋", "tags": ["게자리", "별자리유래", "그리스신화"], "slug": ""},
    {"topic": "분석적인 처녀자리의 유래와 신화 이야기", "emoji": "♍", "tags": ["처녀자리", "별자리유래", "그리스신화"], "slug": ""},
    {"topic": "균형을 중시하는 천칭자리의 유래와 상징", "emoji": "♎", "tags": ["천칭자리", "별자리유래", "별자리상징"], "slug": ""},
    {"topic": "열정적인 전갈자리의 유래와 신화 이야기", "emoji": "♏", "tags": ["전갈자리", "별자리유래", "그리스신화"], "slug": ""},
    {"topic": "모험을 좋아하는 사수자리의 유래와 신화", "emoji": "♐", "tags": ["사수자리", "별자리유래", "그리스신화"], "slug": ""},
    {"topic": "책임감 강한 염소자리의 유래와 신화 이야기", "emoji": "♑", "tags": ["염소자리", "별자리유래", "그리스신화"], "slug": ""},
    {"topic": "상상력 풍부한 물고기자리의 유래와 신화", "emoji": "♓", "tags": ["물고기자리", "별자리유래", "그리스신화"], "slug": ""},
    {"topic": "목·화·토·금·수 오행의 기본 원리와 의미", "emoji": "🌿", "tags": ["오행", "사주기초", "운세상식"], "slug": ""},
    {"topic": "12지지와 하루 12시진, 나는 어느 시간에 태어났을까", "emoji": "🕰️", "tags": ["십이지", "시진", "사주기초"], "slug": ""},
    {"topic": "24절기의 의미와 계절별 생활 풍습", "emoji": "🍃", "tags": ["24절기", "절기풍습", "전통문화"], "slug": ""},
    {"topic": "입춘을 기준으로 띠가 바뀐다는 말의 진짜 의미", "emoji": "🌱", "tags": ["입춘", "띠기준", "사주기초"], "slug": ""},
    {"topic": "사주팔자 네 기둥, 연주·월주·일주·시주 쉽게 이해하기", "emoji": "🧭", "tags": ["사주팔자", "사주기초", "운세상식"], "slug": ""},
    {"topic": "천간 십간이란 무엇인가, 갑을병정 기초 정리", "emoji": "📜", "tags": ["천간", "십간", "사주기초"], "slug": ""},
    {"topic": "윤달의 의미와 윤달에 얽힌 전통 풍습", "emoji": "🌙", "tags": ["윤달", "전통풍습", "음력"], "slug": ""},
    {"topic": "동지 팥죽에 담긴 전통 풍습과 유래", "emoji": "🥣", "tags": ["동지", "팥죽", "전통풍습"], "slug": ""},
    {"topic": "정월대보름에 즐기던 전통 풍습과 그 의미", "emoji": "🌕", "tags": ["정월대보름", "전통풍습", "세시풍속"], "slug": ""},
    {"topic": "거실 소파와 가구 배치로 보는 풍수 기본 원칙", "emoji": "🛋️", "tags": ["거실풍수", "풍수", "인테리어풍수"], "slug": ""},
    {"topic": "주방 풍수의 기본, 가스레인지와 싱크대 위치", "emoji": "🍳", "tags": ["주방풍수", "풍수", "인테리어풍수"], "slug": ""},
    {"topic": "책상 방향과 공부 환경으로 보는 풍수 이야기", "emoji": "📖", "tags": ["책상풍수", "공부방풍수", "풍수"], "slug": ""},
    {"topic": "사무실 책상 배치로 보는 풍수 상식", "emoji": "🖥️", "tags": ["사무실풍수", "풍수", "직장인"], "slug": ""},
    {"topic": "띠별 운세와 사주팔자는 무엇이 다를까", "emoji": "⚖️", "tags": ["띠운세", "사주팔자", "운세상식"], "slug": "", "priority": True, "angle": "교육형 글입니다. 띠 운세는 태어난 해 하나(12지의 해당 동물)만 보는 반면, 사주팔자는 태어난 연·월·일·시 네 기둥(여덟 글자)을 본다는 구조 차이를 비교표나 목록으로 정리하세요. 입력 정보의 양, 해석 범위, 그래서 같은 띠여도 사주는 사람마다 다르다는 점을 설명하고, 두 방식 모두 전통 해석이며 과학적으로 검증된 예측이 아님을 분명히 하세요."},
    {"topic": "별자리 운세는 왜 태양 별자리를 기준으로 할까", "emoji": "☀️", "tags": ["별자리운세", "태양별자리", "점성술기초"], "slug": "", "priority": True, "angle": "교육형 글입니다. 생일에 태양이 지나던 황도 12궁을 '태양 별자리'라 부른다는 정의, 점성술에는 태양 외에 달·상승궁 등 다른 요소도 있다는 점, 대중 매체의 별자리 칼럼에서 태양 별자리가 가장 접근하기 쉬운 기준으로 널리 쓰이게 되었다는 배경을 설명하세요. 천문학상 별자리 경계와 점성술의 12궁 구분이 다르다는 점도 한 문단으로 짚으세요. 구체적인 연도·인물은 확실하지 않으면 쓰지 마세요."},
    {"topic": "명리학의 오행과 십신은 무엇을 뜻할까", "emoji": "🔥", "tags": ["명리학", "오행", "십신"], "slug": "", "priority": True, "angle": "교육형 글입니다. 오행(목·화·토·금·수)의 상생·상극 구조를 쉽게 설명하고, 십신은 사주의 중심 글자인 일간을 기준으로 다른 글자와의 관계를 열 가지 이름(비견, 겁재, 식신, 상관, 편재, 정재, 편관, 정관, 편인, 정인)으로 나눈 것이라고 정의하세요. 해석은 유파와 해석자마다 다를 수 있다는 점을 밝히고, 용어는 처음 나올 때 괄호로 풀어 쓰세요."},
    {"topic": "타로 카드의 기본 구조와 해석 원칙", "emoji": "🃏", "tags": ["타로", "타로카드", "타로기초"], "slug": "", "priority": True, "angle": "교육형 글입니다. 일반적인 타로 덱이 78장이고 메이저 아르카나 22장과 마이너 아르카나 56장(네 가지 수트, 수트당 14장)으로 이뤄진다는 구조를 설명하세요. 정방향·역방향 해석, 질문을 구체적으로 세우는 법, 한 장 뽑기와 세 장 뽑기의 차이를 소개하되, 타로는 미래를 확정하는 도구가 아니라 상황을 정리하고 생각을 돕는 성찰 도구로 쓰는 관점을 제시하세요. 해석은 덱과 사람마다 다를 수 있음을 밝히세요."},
    {"topic": "음력과 양력의 차이, 운세 해석에는 어떤 영향을 줄까", "emoji": "🌙", "tags": ["음력", "양력", "역법"], "slug": "", "priority": True, "angle": "교육형 글입니다. 양력은 태양의 움직임, 음력은 달의 위상 변화를 기준으로 한다는 차이, 음력에는 윤달이 들어가 날짜가 해마다 양력과 어긋난다는 점을 설명하세요. 운세에서는 띠를 보는 기준(설날 또는 입춘)과 사주에서 월을 나누는 기준(절기)이 양력 날짜와 어떻게 다를 수 있는지, 그래서 1~2월 생일은 확인이 필요하다는 점을 안내하세요. 달력 날짜는 한국천문연구원 같은 공공기관 자료로 확인할 수 있다고 안내하되, 구체적인 날짜는 해마다 다르므로 단정하지 마세요."},
    {"topic": "행운의 숫자는 어디에서 왔을까", "emoji": "🔢", "tags": ["행운의숫자", "숫자의미", "운세상식"], "slug": "", "priority": True, "angle": "교육형 글입니다. 숫자에 의미를 부여하는 문화적 배경을 설명하세요. 예를 들어 중국어권에서 8이 발음 때문에 선호되고 4는 죽음을 뜻하는 글자와 발음이 비슷해 꺼린다는 점, 서양에서 7을 행운의 수로 여기는 경향, 피타고라스 학파와 연결되어 전해지는 수비학 전통을 '전해지는 이야기'로 소개하세요. 숫자 자체가 운을 정한다는 과학적 근거는 없으며 문화적 연상이라는 점을 분명히 하고, 확실하지 않은 기원은 단정하지 마세요."},
    {"topic": "흔한 운세 오해 10가지와 바로잡기", "emoji": "🧩", "tags": ["운세오해", "운세상식", "올바른운세활용"], "slug": "", "priority": True, "angle": "교육형 글입니다. 본문 소제목을 오해 유형별(예측 vs 성향 해석, 띠·별자리 기준, 소품과 부적, 좋고 나쁜 운세의 의미 등)로 나누어 흔한 오해 10가지를 짚고 각각 어떻게 이해하면 좋은지 바로잡으세요. 예: 별자리 하나로 성격이 결정되지 않는다, 띠 기준은 양력 1월 1일이 아닐 수 있다, 신문·앱의 일간 운세는 개인 맞춤이 아니다, 좋은 운세라고 노력이 필요 없지 않다, 나쁜 운세가 곧 불행은 아니다. 운세가 과학적으로 검증된 예측이 아님을 분명히 하세요."},
]

# 쿠팡파트너스 필수 고지 문구 (정보통신망법 — 게시물 최상단에 위치해야 함)
_COUPANG_DISCLOSURE = (
    "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
)

# ─────────────────────────────────────────
# 하늘의 움직임(천문 근거) 블록 — 2026-11-02 추가
#  "왜 이번 주/이번 달에 이런 흐름인가"를 보여 주기 위해, 절기·달의 위상·수성 역행·행성의 별자리 이동을
#  천체력(ephem) 계산으로 구해 글에 싣는다. 날짜·위치는 계산값(한국 시간 기준)이고, 풀이 문장은 점성술·전통 해석이다.
#  ephem이 없으면 pip로 설치를 시도하고, 그래도 안 되면 블록만 조용히 생략한다(글 발행은 영향 없음).
# ─────────────────────────────────────────
_EPHEM = None   # None=미확인, False=사용 불가, 모듈=사용 가능

def _sky_lib():
    global _EPHEM
    if _EPHEM is not None:
        return _EPHEM
    try:
        import ephem as _e
        _EPHEM = _e
        return _EPHEM
    except Exception:
        pass
    try:
        import subprocess, sys
        for extra in ([], ["--break-system-packages"]):
            r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ephem"] + extra,
                               capture_output=True, timeout=180)
            if r.returncode == 0:
                break
        import ephem as _e
        _EPHEM = _e
    except Exception as ex:
        print(f"⚠️ 천문 계산 라이브러리(ephem)를 사용할 수 없어 '하늘의 움직임' 블록을 생략합니다: {ex}")
        _EPHEM = False
    return _EPHEM


_SKY_SIGNS = ["양자리", "황소자리", "쌍둥이자리", "게자리", "사자자리", "처녀자리",
              "천칭자리", "전갈자리", "사수자리", "염소자리", "물병자리", "물고기자리"]
_SKY_ELEMENT = {  # 별자리 → 원소
    "양자리": "불", "사자자리": "불", "사수자리": "불",
    "황소자리": "흙", "처녀자리": "흙", "염소자리": "흙",
    "쌍둥이자리": "공기", "천칭자리": "공기", "물병자리": "공기",
    "게자리": "물", "전갈자리": "물", "물고기자리": "물",
}
_SKY_TERMS = {  # 태양 황경 → (절기, 뜻)
    315: ("입춘", "봄이 시작되는 절기"), 330: ("우수", "눈이 비로 바뀌고 얼음이 녹기 시작하는 절기"),
    345: ("경칩", "겨울잠 자던 동물이 깨어난다고 하는 절기"), 0: ("춘분", "낮과 밤의 길이가 거의 같아지는 절기"),
    15: ("청명", "하늘이 맑고 따뜻해지는 절기"), 30: ("곡우", "봄비가 내려 곡식을 키운다는 절기"),
    45: ("입하", "여름이 시작되는 절기"), 60: ("소만", "만물이 점점 자라 가득 찬다는 절기"),
    75: ("망종", "보리를 거두고 모를 심던 시기의 절기"), 90: ("하지", "북반구에서 낮이 가장 긴 절기"),
    105: ("소서", "본격적인 더위가 시작되는 절기"), 120: ("대서", "한여름 더위가 가장 심하다는 절기"),
    135: ("입추", "가을이 시작되는 절기"), 150: ("처서", "더위가 물러가고 일교차가 커지는 절기"),
    165: ("백로", "풀잎에 이슬이 맺히기 시작하는 절기"), 180: ("추분", "낮과 밤의 길이가 거의 같아지는 절기"),
    195: ("한로", "찬 이슬이 맺히는 절기"), 210: ("상강", "서리가 내리기 시작하는 절기"),
    225: ("입동", "겨울이 시작되는 절기"), 240: ("소설", "첫눈이 내릴 무렵이라는 절기"),
    255: ("대설", "눈이 많이 내리는 시기라는 절기"), 270: ("동지", "북반구에서 밤이 가장 긴 절기"),
    285: ("소한", "본격적인 추위가 시작되는 절기"), 300: ("대한", "겨울 추위가 가장 심하다는 절기"),
}
_SKY_PLANET_KR = {"Mercury": "수성", "Venus": "금성", "Mars": "화성", "Jupiter": "목성", "Saturn": "토성"}
_SKY_PLANET_MEAN = {"수성": "소통·이동·계약", "금성": "관계·취향·소비", "화성": "행동력·추진력",
                    "목성": "확장·기회", "토성": "책임·구조"}
_SKY_ELEM_FLAVOR = {
    "불": "솔직하고 적극적인", "흙": "현실적이고 안정을 따지는",
    "공기": "가볍고 대화 중심인", "물": "감성적이고 깊이 헤아리는",
}
_SKY_MOON_NAMES = {"new": "신월(삭)", "first": "상현달", "full": "보름달(만월)", "last": "하현달"}
_SKY_MOON_MEAN = {
    "new":   ["점성술에서는 신월을 새 계획을 세우고 마음을 정리하기 좋은 시점으로 해석합니다.",
              "전통적으로 달이 새로 시작되는 시점이라, 목표를 적어 보기에 알맞은 때로 여겼습니다."],
    "first": ["달이 차오르며 추진력이 붙는 시기로 해석합니다. 미뤄 둔 일을 실행으로 옮기기 좋다고 봅니다.",
              "점성술에서는 상현을 결정과 행동에 힘이 실리는 때로 봅니다."],
    "full":  ["점성술에서는 보름달 무렵 감정과 관계가 선명해지고, 그동안의 일이 결과로 드러난다고 해석합니다.",
              "보름달은 마음이 들뜨기 쉬운 때로 전해져, 큰 결정은 하루 이틀 두고 보는 편이 좋다고 봅니다."],
    "last":  ["점성술에서는 하현을 정리하고 내려놓기 좋은 시기로 해석합니다.",
              "달이 줄어드는 때라 불필요한 것을 덜어내기에 알맞다고 봅니다."],
}


def _sky_deg(x):
    import math
    return math.degrees(x) % 360


def _sky_ecl_lon(body_cls, dt_utc):
    e = _sky_lib()
    b = body_cls()
    b.compute(dt_utc, epoch=dt_utc)
    return _sky_deg(e.Ecliptic(b).lon)


def _sky_kst_noon_utc(d):
    from datetime import datetime as _dt
    return _dt(d.year, d.month, d.day, 3, 0, 0)     # 정오 KST = 03:00 UTC


def _sky_utc_to_kst_date(dt_utc):
    from datetime import timedelta as _td
    return (dt_utc + _td(hours=9)).date()


def sky_events(start, end):
    """start~end(포함, KST 날짜)에 일어나는 천문 이벤트와 기간 초의 상태를 계산해 돌려준다."""
    from datetime import datetime as _dt, timedelta as _td
    e = _sky_lib()
    if not e:
        return None
    ev = {"terms": [], "moon": [], "sun_sign": [], "stations": [], "ingress": [], "retro_start": [], "retro_end": [],
          "moon_sign_start": None}
    t0 = _dt(start.year, start.month, start.day) - _td(hours=9)          # 시작일 00:00 KST (UTC)
    t1 = _dt(end.year, end.month, end.day) + _td(hours=15)               # 종료일 24:00 KST (UTC)

    # 절기 · 태양의 별자리 이동 (1시간 간격 스캔)
    t = t0
    prev = _sky_ecl_lon(e.Sun, t)
    while t < t1:
        nxt = t + _td(hours=1)
        cur = _sky_ecl_lon(e.Sun, nxt)
        for deg in range(0, 360, 15):
            if ((prev - deg + 180) % 360 - 180) < 0 <= ((cur - deg + 180) % 360 - 180):
                d = _sky_utc_to_kst_date(nxt)
                name, mean = _SKY_TERMS[deg]
                ev["terms"].append((d, name, mean))
                if deg % 30 == 0:
                    ev["sun_sign"].append((d, _SKY_SIGNS[(deg // 30) % 12]))
        prev, t = cur, nxt

    # 달의 위상 (+ 그때 달이 머무는 별자리)
    for key, fn in (("new", e.next_new_moon), ("first", e.next_first_quarter_moon),
                    ("full", e.next_full_moon), ("last", e.next_last_quarter_moon)):
        d = e.Date(t0 - _td(days=1))
        while True:
            d = fn(d)
            dt = d.datetime()
            if dt >= t1:
                break
            if dt >= t0:
                sign = _SKY_SIGNS[int(_sky_ecl_lon(e.Moon, dt) // 30) % 12]
                ev["moon"].append((_sky_utc_to_kst_date(dt), key, sign))
            d = e.Date(d + 0.5)
    ev["moon"].sort()

    # 기간 초 달의 별자리
    ev["moon_sign_start"] = _SKY_SIGNS[int(_sky_ecl_lon(e.Moon, _sky_kst_noon_utc(start)) // 30) % 12]

    # 행성: 별자리 이동(입성) · 방향 전환(station) · 기간 초/말 역행 여부 (하루 단위)
    day = start
    prev_sign, prev_dir = {}, {}
    for name in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
        cls = getattr(e, name)
        l0 = _sky_ecl_lon(cls, _sky_kst_noon_utc(start))
        l1 = _sky_ecl_lon(cls, _sky_kst_noon_utc(start) + _td(days=1))
        prev_sign[name] = int(l0 // 30)
        prev_dir[name] = (((l1 - l0) + 180) % 360 - 180) < 0       # True=역행
        if prev_dir[name]:
            ev["retro_start"].append(_SKY_PLANET_KR[name])
    d = start
    while d <= end:
        noon = _sky_kst_noon_utc(d)
        for name in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
            cls = getattr(e, name)
            a = _sky_ecl_lon(cls, noon)
            b = _sky_ecl_lon(cls, noon + _td(days=1))
            retro = (((b - a) + 180) % 360 - 180) < 0
            sign_i = int(a // 30)
            if d > start:
                if sign_i != prev_sign[name] and name in ("Mercury", "Venus", "Mars"):
                    ev["ingress"].append((d, _SKY_PLANET_KR[name], _SKY_SIGNS[sign_i]))
                if retro != prev_dir[name] and name in ("Mercury", "Venus", "Mars"):
                    ev["stations"].append((d, _SKY_PLANET_KR[name], "역행 시작" if retro else "순행 복귀"))
            prev_sign[name], prev_dir[name] = sign_i, retro
        d += _td(days=1)
    for name in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
        if prev_dir[name]:
            ev["retro_end"].append(_SKY_PLANET_KR[name])
    return ev




# ─────────────────────────────────────────
# SEO 프롬프트 v9.5 — 23장(호호매거진 편집 모듈) · 19.5/19.6 박스 규격 적용
#  · Gemini는 JSON(내용)만 만들고, HTML 조립은 코드가 한다 (목차 앵커·박스 위치·글자 수 계산이 틀리지 않게)
#  · 분량: 한줄요약·나만의 포인트·목차·간단 정리·한 번에 정리·해시태그를 뺀 본문 공백 제외 2,000자 이상
#  · 글 유형 5종 로테이션(직전 3개와 다른 유형), 직전 10개 글과 제목·H2·FAQ·첫 문장 중복 금지
# ─────────────────────────────────────────
MIN_CHARS         = 2000   # 본문 합계(공백 제외) 최소 — 박스류 제외, 실전 팁·FAQ 포함 (v9.5 23.7)
MIN_SECTION_CHARS = 1000   # 본문 H2 섹션만의 최소 분량 — FAQ·팁으로 분량을 채우는 것 방지
MAX_CHARS         = 6500
MAX_ATTEMPTS      = 3
FAQ_COUNT         = 5
RECENT_N          = 10
MAX_OUT_TOKENS    = 16384

POST_TYPES = {
    "문제해결형":  "독자가 겪는 문제 하나를 정하고, 원인 → 확인 순서 → 해결 행동의 흐름으로 쓴다.",
    "비교·선택형": "두 가지 이상(방식·기준·유파·종류)을 같은 항목으로 비교하고, 어떤 상황에 무엇을 고르면 되는지 기준을 준다.",
    "체크리스트형": "오늘 바로 점검할 수 있는 항목을 순서대로 제시한다. 항목마다 '왜 보는지'와 확인 방법을 붙인다.",
    "일정·시기형": "달력·절기·월별·단계별 시간 흐름으로 정리한다. 가상의 사례를 실제 사례처럼 쓰지 않는다.",
    "데이터해설형": "표·목록으로 정리된 사실(구조, 이름, 날짜, 계산값)을 풀어 설명하고, 읽는 법을 알려 준다.",
}
INTRO_PATTERNS = {
    "수치형": "첫 문장을 숫자(개수·날짜·시각 등)로 시작한다.",
    "상황형": "독자가 처한 구체적 상황(예: 이사 날짜를 잡는 순간, 생일이 1월인 경우)으로 시작하되 첫 문장에 구체값 1개 이상을 넣는다.",
    "질문형": "독자가 실제로 궁금해할 질문 한 문장으로 시작하되 첫 문장에 구체값 1개 이상을 넣는다.",
}

# 근거 자료 안내처(화이트리스트) — 존재가 확실한 기관·사이트만. 글에는 '발행 시점에 직접 확인한 문서'가 아니라
# '더 확인할 수 있는 공식 안내처'로 표기한다. (v9.5 23.4: 확인하지 않은 자료를 있는 것처럼 꾸미지 않음)
SOURCES = {
    "kasi": ("한국천문연구원", "천문우주지식정보 — 절기·월력·음력 날짜 안내", "https://astro.kasi.re.kr"),
    "iau":  ("국제천문연맹(IAU)", "별자리(Constellations) 공식 안내", "https://www.iau.org/public/themes/constellations/"),
    "folk": ("국립민속박물관", "한국민속대백과사전", "https://folkency.nfm.go.kr"),
    "aks":  ("한국학중앙연구원", "한국민족문화대백과사전", "https://encykorea.aks.ac.kr"),
}

# 주제별 편집자 관점(23.1-③) · 근거 안내처 · 글 유형 힌트 · 천문 계산값 주입 방식
#  (prefix, view, src, type_hint, sky)
_META = [
 ("복을 부르는 현관", "현관은 '풍수 효과'보다 신발 정리·동선·조명·환기 같은 실천 항목을 먼저 제시하고 전통 원칙은 구분해 소개한다 — 믿음과 무관하게 쓸 수 있어야 하기 때문", ["aks"], "체크리스트형", None),
 ("재물운을 높이는 침실", "수면 환경(조도·소음·온도)을 먼저, 풍수 배치 전통은 '전통적으로 ~라고 본다'로 분리한다 — 의학·재물 효과를 단정하지 않기 위해", ["aks"], None, None),
 ("행운의 색", "색채가 주는 심리적 연상과 오방색 전통을 구분하고, 나만의 색 고르기는 3단계 점검 절차로 준다 — 결과를 약속하지 않고 선택 기준을 주기 위해", ["folk"], "체크리스트형", None),
 ("태어난 달로", "탄생석 목록이 나라·시기마다 다르다는 점을 먼저 밝히고 월별 표로 정리한다 — 한 가지 목록을 정답처럼 쓰지 않기 위해", [], "데이터해설형", None),
 ("재물운을 부르는 지갑", "지갑 정리 주기와 방법(영수증·카드·현금)을 구체 습관으로 쓰고 색의 의미는 전해지는 이야기로 한 단락만 둔다 — 재테크 조언으로 번지지 않게", [], "체크리스트형", None),
 ("별자리별 잘 어울리는 향수", "향수 구조(탑·미들·베이스, 지속 시간 차이)를 먼저 설명하고 별자리 매칭은 원소 이미지에서 연상한 재미 요소로 분리한다 — 근거 없는 추천을 단정하지 않기 위해", [], "비교·선택형", None),
 ("이사할 때 챙기면", "손 없는 날의 정의와 음력 확인 방법을 먼저, 날짜 선택의 현실 변수(예약·비용)를 함께 비교한다 — 믿음 여부와 상관없이 쓰는 점검표를 주기 위해", ["kasi"], "문제해결형", None),
 ("수험생 자녀", "부모가 할 수 있는 지원(수면·식사 리듬·시험 당일 준비물)을 시간 순서로 제시하고 합격 기원 풍습은 한 섹션으로 제한한다 — 효과를 단정하지 않기 위해", [], "일정·시기형", None),
 ("이직·취업", "운세 문구 대신 취업 점검표(이력서·지원 기록·면접 일정) 중심으로 쓰고 옷 색 같은 습속은 심리적 안정 장치로만 소개한다 — 실제 행동이 결과를 만들기 때문", [], "체크리스트형", None),
 ("신혼부부", "공용 공간 규칙·수납·동선을 '둘이 합의하는 순서'로 제시하고 풍수 배치는 전통 소개로 분리한다 — 재물 효과를 약속하지 않기 위해", ["aks"], "문제해결형", None),
 ("목·화·토·금·수 오행", "상생·상극을 표 하나로 정리하고 '오행은 성격 판정표가 아니라 분류 체계'라는 관점으로 시작한다 — 흔한 오해를 먼저 걷어내기 위해", ["aks"], "데이터해설형", None),
 ("12지지와 하루 12시진", "12시진 시간표를 먼저 표로 주고 출생 시간이 불확실할 때 확인하는 순서를 제시한다 — 시간이 사주 해석의 입력값이고 유파별 경계 해석이 다를 수 있기 때문", ["aks"], "데이터해설형", None),
 ("24절기", "24절기를 계절 4분기 표로 묶고 가까운 절기 날짜는 천문 계산값(한국시간)으로 제시한다 — 풍습은 '전해지는 것'으로 구분하기 위해", ["kasi", "folk"], "데이터해설형", "term"),
 ("입춘을 기준으로", "띠 기준이 설날이냐 입춘이냐를 비교표로 정리하고 1~2월 생일 확인 절차를 준다 — 유파마다 기준이 달라 생일이 걸리는 독자가 실제로 혼란을 겪기 때문", ["kasi"], "비교·선택형", "term"),
 ("사주팔자 네 기둥", "연·월·일·시 네 기둥이 무엇을 대표하는지 표로 정리하고 월주는 절기 기준이라는 점을 강조한다 — 생일 양력 날짜만으로 사주가 정해지지 않는 이유를 보여 주기 위해", ["aks", "kasi"], "문제해결형", "term"),
 ("천간 십간", "10천간을 오행·음양 표 하나로 정리하고 순서를 외우는 방법을 제시한다 — 이후 사주 글의 기초 용어표로 쓰기 위해", ["aks"], "데이터해설형", None),
 ("윤달", "윤달이 생기는 원리(달 기준 한 해와 태양 기준의 차이)를 먼저 설명하고 풍습은 전해지는 이야기로 구분한다", ["kasi", "folk"], "문제해결형", "moon"),
 ("동지 팥죽", "동지 날짜를 계산값으로 제시하고 팥죽 풍습은 '전해지는 의미'로 구분한다 — 날짜와 풍습의 근거 수준이 다르기 때문", ["folk", "kasi"], "일정·시기형", "term"),
 ("정월대보름", "대보름 풍속(부럼·오곡밥·달맞이 등)을 시간 순으로 정리하고 가까운 보름달 날짜는 계산값으로 제시한다", ["folk", "kasi"], "일정·시기형", "moon"),
 ("거실 소파", "가구 배치는 동선·채광·시선 3가지 실용 기준을 먼저, 풍수 원칙은 전통 소개로 분리한다", ["aks"], "체크리스트형", None),
 ("주방 풍수", "화기와 물(가스레인지·싱크대) 위치의 전통 해석을 소개하되 안전·위생 기준(환기·동선)을 먼저 둔다 — 실생활 판단이 먼저여야 하기 때문", ["aks"], "비교·선택형", None),
 ("책상 방향", "집중 환경(조명·소음·정리)을 먼저 다루고 풍수 방향 설은 전해지는 이야기로 구분한다", ["aks"], None, None),
 ("사무실 책상", "업무 효율 환경(동선·채광·시선) 기준을 먼저 쓰고 풍수 배치는 전통 소개로 분리한다", ["aks"], None, None),
 ("띠별 운세와 사주팔자", "입력 정보량(태어난 해 1개 vs 연·월·일·시 여덟 글자)을 비교표로 대비한다 — 같은 띠여도 사주가 사람마다 다른 이유를 한눈에 보여 주기 위해", ["aks"], "비교·선택형", None),
 ("별자리 운세는 왜 태양", "태양 별자리의 정의, 천문학 별자리 경계와 점성술 12궁의 차이, 올해 태양 별자리 경계일(계산값)을 표로 보여 준다 — 생일이 경계에 걸리는 독자의 혼란을 줄이기 위해", ["iau"], "데이터해설형", "allsigns"),
 ("명리학의 오행과 십신", "십신 열 가지 이름을 '일간 기준 관계' 표로 정리하고 처음 나오는 용어는 괄호로 풀이한다 — 용어 장벽을 낮추기 위해", ["aks"], "데이터해설형", None),
 ("타로 카드", "78장 구조(메이저 22 + 마이너 56)를 표로 정리하고 타로를 '성찰 도구'로 쓰는 관점을 제시한다 — 미래 확정 도구로 오해하지 않게", [], "비교·선택형", None),
 ("음력과 양력", "양력·음력·절기 세 가지 기준을 비교표로 정리하고 가까운 절기·보름달 날짜는 계산값으로 제시한다 — 운세 해석에서 기준이 갈리는 지점을 보여 주기 위해", ["kasi"], "비교·선택형", "term+moon"),
 ("행운의 숫자", "문화권별 숫자 선호(예: 8·4·7)를 표로 정리하고 수비학은 전해지는 이야기로 소개한다 — 숫자가 운을 정한다는 근거는 없고 문화적 연상이라는 점을 분명히 하기 위해", [], None, None),
 ("흔한 운세 오해", "오해 10개를 '오해 → 실제 → 확인 방법' 형식으로 정리한다 — 독자가 자기 믿음을 점검하는 용도로 쓰게 하기 위해", [], "체크리스트형", None),
]


def get_meta(item):
    """주제별 편집자 관점·근거 안내처·유형 힌트·천문 값 방식을 돌려준다."""
    topic = item["topic"]
    tags = item.get("tags", [])
    for prefix, view, src, hint, sky in _META:
        if topic.startswith(prefix):
            return {"view": view, "src": src, "type_hint": hint, "sky": sky}
    if "띠별성격" in tags:
        animal = tags[0]
        return {"view": f"{animal} 성격은 확정된 기질이 아니라 십이지 전통 상징을 읽는 틀로 소개하고, 장점마다 '보완할 점'을 짝지어 독자가 스스로 점검하는 기준으로 쓴다 — 성격 단정은 근거가 없기 때문",
                "src": ["folk"], "type_hint": None, "sky": None}
    if "별자리유래" in tags:
        sign = tags[0]
        return {"view": f"{sign}는 신화 줄거리보다 '밤하늘에서 찾는 법과 관측 시기'를 먼저 쓰고 신화는 전해지는 이야기로 구분한다 — 천문학 사실과 점성술 성격 설명을 섞지 않기 위해",
                "src": ["iau"], "type_hint": None, "sky": f"sign:{sign}"}
    return {"view": "", "src": [], "type_hint": None, "sky": None}


# ─────────────────────────────────────────
# 천문 계산값(고유 데이터) — 절기·보름달·태양 별자리 이동일
# ─────────────────────────────────────────
def sky_facts(mode, today):
    """주제에 맞는 천문 계산값을 '사실 목록' 문자열로 돌려준다. 실패하면 빈 문자열(글은 계산값 없이 진행)."""
    if not mode:
        return ""
    try:
        from datetime import timedelta as _td
        lines = []
        if mode.startswith("sign:") or mode == "allsigns":
            ev = sky_events(today, today + _td(days=370))
            if not ev:
                return ""
            ings = ev["sun_sign"]
            if mode.startswith("sign:"):
                sg = mode.split(":", 1)[1]
                for i, (d, s) in enumerate(ings):
                    if s == sg:
                        nxt = ings[i + 1] if i + 1 < len(ings) else None
                        lines.append(f"태양이 {sg}에 들어가는 날: {d.year}년 {d.month}월 {d.day}일" +
                                     (f" (다음 별자리 {nxt[1]} 진입 {nxt[0].month}월 {nxt[0].day}일)" if nxt else ""))
                        break
            else:
                for d, s in ings:
                    lines.append(f"태양이 {s}에 들어가는 날: {d.year}년 {d.month}월 {d.day}일")
        else:
            ev = sky_events(today, today + _td(days=75))
            if not ev:
                return ""
            if "term" in mode:
                for d, name, mean in ev["terms"]:
                    lines.append(f"절기 {name}: {d.year}년 {d.month}월 {d.day}일 ({mean})")
            if "moon" in mode:
                for d, key, sign in ev["moon"]:
                    if key in ("new", "full"):
                        lines.append(f"{_SKY_MOON_NAMES[key]}: {d.year}년 {d.month}월 {d.day}일")
        if not lines:
            return ""
        head = (f"[천문 계산값 — 기준일 {today.year}.{today.month:02d}.{today.day:02d}, 천체력(ephem) 계산, 한국 표준시. "
                f"아래 날짜는 이 값 그대로 쓰고 기준일을 함께 적을 것. 별자리 경계일은 해마다 하루 안팎 달라질 수 있음]")
        return head + "\n" + "\n".join("- " + l for l in lines[:14])
    except Exception as e:
        print(f"  ⚠️ 천문 계산값 생성 실패(계산값 없이 진행): {e}")
        return ""


# ─────────────────────────────────────────
# 프롬프트
# ─────────────────────────────────────────
_BANNED_HARD = ["최고", "100%", "완치", "효과 보장", "완벽 보장", "단번에 해결", "역대급", "인생 맛집", "호호플레이"]
_BANNED_VOCAB = ["획기적", "완벽한", "극대화", "혁신적", "압도적", "필수불가결", "누구나 한 번쯤", "알아보겠습니다",
                 "결론적으로", "마무리하며", "도움이 되셨으면", "매우 중요합니다", "다양한", "효과적인"]
_EXPERIENCE = ["직접 가봤", "다녀와 보니", "먹어봤", "써 보니", "써보니", "우리 아이가", "제가 경험", "제가 직접",
               "직접 해보니", "직접 써", "직접 사용해", "저도 해봤"]
_BAD_OPENERS = ["누구나 한 번쯤", "아침에 눈을", "주말이 되면", "주말이나 휴일", "어린 자녀를 둔", "를 바탕으로 살펴보면", "최근 몇 년간"]
_REPLACE_MAP = [("매우 중요합니다", "꼭 짚어 볼 부분입니다"), ("다양한", "여러"), ("효과적인", "쓸 만한"), ("무조건", "반드시"),
                ("알아보겠습니다", "정리합니다"), ("결론적으로", "정리하면"), ("마무리하며", "정리하며"),
                ("도움이 되셨으면", "참고가 되길"), ("획기적", "눈에 띄는"), ("혁신적", "새로운"),
                ("극대화", "키우는"), ("압도적", "큰"), ("완벽한", "충분한")]


def build_prompt(item, meta, ptype, intro_pat, recent, sky_text, retry_note=""):
    topic = item["topic"]
    angle = item.get("angle", "")
    src_names = [SOURCES[k][0] for k in meta["src"] if k in SOURCES]

    if recent:
        rl = []
        for i, r in enumerate(recent, 1):
            rl.append(f"{i}. 제목: {r.get('title') or r.get('topic','')} | H2: {' / '.join(r.get('h2', [])[:6])} | "
                      f"FAQ: {' / '.join(r.get('faq', [])[:5])} | 첫 문장 시작: {r.get('intro12','')}")
        recent_block = ("[직전 글 목록 — 제목·H2·FAQ 질문·첫 문장 시작어구가 아래와 겹치지 않게 쓰세요]\n" + "\n".join(rl))
    else:
        recent_block = "[직전 글 목록] 없음"

    src_note = (f"본문에서 기관 이름을 쓸 때는 {', '.join(src_names)}만 쓸 수 있습니다. 자료명·보고서명·통계 수치는 쓰지 마세요. "
                f"도입 2~3번째 문장에 '{src_names[0]}에서 확인할 수 있는 ○○ 정보' 정도로 확인처를 연결하세요."
                if src_names else
                "허용된 근거 기관이 없는 주제입니다. 기관·자료·통계를 언급하지 말고, 도입 2~3번째 문장에는 '이 글의 선정·정리 기준'을 밝히세요.")

    sky_block = ("\n" + sky_text + "\n위 계산값은 본문에 최소 2개 이상 사용하고(표에 넣어도 됨), 계산값과 해석(점성술·전통 풍습)을 문장으로 구분하세요.\n"
                 if sky_text else "")
    angle_block = f"\n[이 주제의 방향]\n{angle}\n" if angle else ""
    retry_block = f"\n[이전 시도 수정 사항 — 반드시 반영]\n{retry_note}\n" if retry_note else ""

    return f"""당신은 한국어 정보 블로그 '오늘운세로그'의 매거진 편집자입니다. 아래 주제로 구글 블로그용 정보 글의 '내용'만 JSON으로 작성하세요. HTML은 쓰지 않습니다(코드가 조립합니다).

[주제] {topic}
[글 유형] {ptype} — {POST_TYPES[ptype]}
[도입 패턴] {intro_pat} — {INTRO_PATTERNS[intro_pat]}
[편집자 관점(이 글이 권하는 판단)] {meta['view'] or '독자가 스스로 판단할 수 있는 기준을 하나 정해 근거와 함께 제시한다.'}
{angle_block}{sky_block}
{recent_block}

[독창성 3요소 — 모두 충족]
1) 고유 데이터 또는 선정 기준: 위 계산값이 있으면 사용하고, 없으면 '이 글이 쓴 선정·정리 기준 3가지 이상'을 본문에 밝힌다.
2) 구체 사실 밀도: 문단 3개마다 확인 가능한 구체값(숫자·날짜·시각·이름·순서)을 1개 이상 넣는다. 새 정보가 없는 문단은 쓰지 않는다.
3) 편집자 관점: 위 관점을 '이 글의 판단' 한 문단으로 쓰고 근거를 붙인다.

[작성 규칙]
- 독자의 문제가 주인공입니다. 재미와 참고를 위한 전통 문화 정보로 쓰되, 운세는 과학적으로 검증된 예측이 아님을 본문 어딘가에 한 번 분명히 밝힙니다.
- 전해 내려오는 해석은 "전통적으로 ~라고 봅니다", "~로 전해집니다"로 쓰고 사실과 구분합니다. 확실하지 않은 연도·인물·기원은 쓰지 마세요.
- {src_note}
- 퍼센트·통계·"연구에 따르면" 같은 출처 없는 수치 표현 금지. 의학·재테크 조언 금지.
- 운영자 경험이 없으므로 "직접 해보니", "써 보니", "우리 아이가" 같은 1인칭 체험 표현 금지. '확인하는 방법·선정 기준' 방식으로 쓴다.
- 금지 표현: {', '.join(_BANNED_HARD)}, {', '.join(_BANNED_VOCAB)}. 금지 도입: "누구나 한 번쯤", "아침에 눈을", "주말이 되면", "최근 몇 년간 ~열풍". 소제목마다 "~가 중요합니다"로 끝내지 않는다.
- "호호플레이"라는 단어를 쓰지 않는다.
- 도입은 3문장 이내: ①구체값으로 시작하는 첫 문장 → ②이 글이 답하는 질문 → ③근거·확인처 연결. 도입 안에서 "알아보겠습니다" 같은 예고 문장 금지.

[JSON 구조 — 키 이름 그대로, 다른 키는 만들지 않는다]
{{
 "titles": ["검색형 제목(핵심 키워드를 앞에, 장식어 없이, 15~38자)", "상황형 제목 1", "상황형 제목 2"],
 "intro": "도입 3문장 이내(문자열 하나)",
 "summary": "한줄요약 1~2문장, 120~220자. 결론 + 핵심 조건 + 구체값 2개 이상. 본문에 나오는 값만. 도입 문장 반복 금지. 독립 완결문",
 "points": ["나만의 포인트 1(40~90자, 이 글만의 선정 기준·확인 순서·놓치기 쉬운 조건)", "포인트 2", "(선택) 포인트 3"],
 "sections": [
   {{"h2": "독자 질문 하나에 답하는 소제목(번호 붙이지 않음, 직전 글과 겹치지 않게)",
     "paragraphs": ["문단 3개, 각 3~4문장", "..."],
     "bullets": ["(선택) 짧은 항목 3~5개, 각각 구체값 포함"],
     "brief": "📝 간단 정리 — 이 소제목의 결론 1줄, 20~90자, 본문에 나온 구체값 1개 이상 인용, 본문 문장 복사 금지"}}
   ],
 "wrapup": "✅ 한 번에 정리 — 3~6줄, 250~450자. ①소제목들을 관통하는 공통 기준 ②어떤 순서로 보면 되는지 ③마지막 한 줄 '결국 …'. 각 간단 정리보다 반드시 길게, 간단 정리를 이어 붙이지 말 것",
 "tables": [{{"caption": "표 제목", "headers": ["열1","열2"], "rows": [["...","..."]]}}],
 "judgement": "이 글의 판단 — 편집자 관점 한 문단(3~5문장): 어떤 기준으로 판단하면 되는지 + 근거. 나만의 포인트와 같은 문장 금지",
 "tips": ["🛠 실전 팁: 오늘 바로 할 행동 1문장(구체값 포함)", "...(2~4개, '이 글의 판단'과 같은 말 반복 금지, '미리 확인하세요'만 쓰지 말고 무엇을 어디서 확인할지 적기)"],
 "faq": [{{"q": "독자가 실제로 물을 법한 완성된 질문", "a": "결론 1문장 → 조건·예외 → 확인 방법, 120~220자"}}],
 "closing_question": "독자의 상황을 묻는 마무리 질문 1줄",
 "hashtags": ["#키워드", "... 8~10개, 띄어쓰기 없이"]
}}

[분량·개수]
- sections는 4~5개. 각 섹션 본문(문단+항목)은 공백 제외 450자 이상을 목표로, 문단 3개(각 3~4문장) + 항목 3~5개로 충분히 쓴다(300자 미만이면 다시 쓰게 된다). 전체 본문(도입+섹션+표+판단+팁+FAQ)은 공백 제외 2,400자 이상 4,500자 이하.
- faq는 정확히 5개. 유형을 다르게(정의·방법·조건·비교·주의/예외). 5개 중 2개 이상은 본문에 없는 추가 정보. 같은 어미("~하나요?")가 3개 이상 되지 않게. 질문에 [ ]·( )·OOO 같은 자리표시자 금지.
- tables는 비교·절차·기준이 실제로 있을 때만 0~3개. 억지로 넣지 않는다. 칸이 비면 "확인 필요".
- points 1~3개, tips 2~4개.
{retry_block}
JSON 외의 설명·코드블록 표시는 출력하지 마세요."""


# ─────────────────────────────────────────
# JSON 파싱 · 정리 · 검증
# ─────────────────────────────────────────
def _s(x):
    return re.sub(r"[ \t]+", " ", str(x)).strip() if x is not None else ""


def _nospace_len(s):
    return len(re.sub(r"\s+", "", s or ""))


def _sentences(text):
    return [p for p in re.split(r"(?<=[.!?。])\s+", (text or "").strip()) if p]


def parse_json_text(text):
    text = (text or "").strip().replace("```json", "").replace("```", "").strip()
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("JSON 객체를 찾지 못함")
    return json.loads(text[a:b + 1])


def normalize(d):
    """모델이 돌려준 dict를 기대 구조로 정리(타입 보정·공백 정리). 구조가 어긋나면 비어 있는 값으로 두어 검증에서 걸리게 한다."""
    out = {}
    out["titles"]  = [_s(t) for t in (d.get("titles") or []) if _s(t)] if isinstance(d.get("titles"), list) else []
    out["intro"]   = _s(d.get("intro"))
    out["summary"] = _s(d.get("summary"))
    out["points"]  = [_s(p) for p in (d.get("points") or []) if _s(p)] if isinstance(d.get("points"), list) else []
    secs = []
    for sct in (d.get("sections") or []) if isinstance(d.get("sections"), list) else []:
        if not isinstance(sct, dict):
            continue
        paras = [_s(p) for p in (sct.get("paragraphs") or []) if _s(p)] if isinstance(sct.get("paragraphs"), list) else []
        buls  = [_s(p) for p in (sct.get("bullets") or []) if _s(p)] if isinstance(sct.get("bullets"), list) else []
        secs.append({"h2": _s(sct.get("h2")), "paragraphs": paras, "bullets": buls, "brief": _s(sct.get("brief"))})
    out["sections"] = secs
    out["wrapup"]   = _s(d.get("wrapup"))
    tables = []
    for t in (d.get("tables") or []) if isinstance(d.get("tables"), list) else []:
        if not isinstance(t, dict):
            continue
        hdr  = [_s(h) for h in (t.get("headers") or [])] if isinstance(t.get("headers"), list) else []
        rows = []
        for r in (t.get("rows") or []) if isinstance(t.get("rows"), list) else []:
            if isinstance(r, list):
                rows.append([_s(c) or "확인 필요" for c in r])
        # 모양이 맞지 않는 표는 억지로 쓰지 않고 버린다
        if 2 <= len(hdr) <= 5 and 1 <= len(rows) <= 12 and all(len(r) == len(hdr) for r in rows):
            tables.append({"caption": _s(t.get("caption")), "headers": hdr, "rows": rows})
    out["tables"]    = tables[:3]
    out["judgement"] = _s(d.get("judgement"))
    out["tips"]      = [_s(p) for p in (d.get("tips") or []) if _s(p)] if isinstance(d.get("tips"), list) else []
    faq = []
    for f in (d.get("faq") or []) if isinstance(d.get("faq"), list) else []:
        if isinstance(f, dict) and _s(f.get("q")) and _s(f.get("a")):
            faq.append({"q": _s(f["q"]), "a": _s(f["a"])})
    out["faq"]              = faq
    out["closing_question"] = _s(d.get("closing_question"))
    out["hashtags"]         = [_s(h) for h in (d.get("hashtags") or []) if _s(h)] if isinstance(d.get("hashtags"), list) else []
    return out


def _walk_strings(d, fn):
    """dict 안의 모든 문자열에 fn을 적용한 새 dict."""
    if isinstance(d, dict):
        return {k: _walk_strings(v, fn) for k, v in d.items()}
    if isinstance(d, list):
        return [_walk_strings(v, fn) for v in d]
    if isinstance(d, str):
        return fn(d)
    return d


def autofix(d):
    """기계적으로 고칠 수 있는 것만 고친다: 금지 어휘 치환, 자리표시용 접두 라벨 제거, 제목 따옴표 제거."""
    def fx(s):
        for a, b in _REPLACE_MAP:
            s = s.replace(a, b)
        return s
    d = _walk_strings(d, fx)
    d["titles"] = [t.strip("\"'“”‘’ ") for t in d["titles"]]
    for sct in d["sections"]:
        sct["brief"] = re.sub(r"^(📝\s*)?간단 정리\s*[·:\-—]?\s*", "", sct["brief"]).strip()
    d["wrapup"] = re.sub(r"^(✅\s*)?한 번에 정리\s*[·:\-—]?\s*", "", d["wrapup"]).strip()
    d["tips"]   = [re.sub(r"^(🛠\s*)?실전 팁\s*[·:\-—]?\s*", "", t).strip() for t in d["tips"]]
    return d


def all_text(d):
    parts = [d["intro"], d["summary"], d["wrapup"], d["judgement"], d["closing_question"]] + d["titles"] + d["points"] + d["tips"]
    for s in d["sections"]:
        parts += [s["h2"], s["brief"]] + s["paragraphs"] + s["bullets"]
    for t in d["tables"]:
        parts += [t["caption"]] + t["headers"] + [c for r in t["rows"] for c in r]
    for f in d["faq"]:
        parts += [f["q"], f["a"]]
    return "\n".join(p for p in parts if p)


def section_chars(d):
    return sum(_nospace_len(x) for s in d["sections"] for x in s["paragraphs"] + s["bullets"])


def body_chars(d):
    """v9.5 23.7: 한줄요약·나만의 포인트·목차·간단 정리·한 번에 정리·해시태그를 뺀 본문(실전 팁·FAQ 포함) 공백 제외 글자 수."""
    n = _nospace_len(d["intro"]) + section_chars(d) + _nospace_len(d["judgement"])
    n += sum(_nospace_len(t) for t in d["tips"])
    n += sum(_nospace_len(f["q"]) + _nospace_len(f["a"]) for f in d["faq"])
    for t in d["tables"]:
        n += sum(_nospace_len(c) for r in t["rows"] for c in r) + sum(_nospace_len(h) for h in t["headers"])
    return n


_CONCRETE_WORDS = ["한국천문연구원", "국립민속박물관", "한국학중앙연구원", "국제천문연맹", "띠", "자리", "절기", "입춘", "동지",
                   "음력", "양력", "오행", "사주", "타로", "탄생석", "십이지", "천간", "지지", "시진"]


def validate(d, recent, existing_title_norms):
    """(hard, soft) 문제 목록. hard가 있으면 반드시 다시 쓰고, soft는 재시도 여유가 있을 때만 다시 쓴다."""
    hard, soft = [], []
    txt = all_text(d)

    # ── 구조
    if not d["titles"]:
        hard.append("titles가 비어 있음 — 제목 후보 3개 필요")
    if not d["intro"]:
        hard.append("intro 누락")
    if not d["summary"]:
        hard.append("summary(한줄요약) 누락")
    if not 1 <= len(d["points"]) <= 3:
        hard.append(f"points는 1~3개여야 함(현재 {len(d['points'])}개)")
    if not 2 <= len(d["tips"]) <= 4:
        hard.append(f"tips는 2~4개여야 함(현재 {len(d['tips'])}개)")
    if not d["judgement"]:
        hard.append("judgement(이 글의 판단) 누락")
    if not d["wrapup"]:
        hard.append("wrapup(한 번에 정리) 누락")
    if not d["closing_question"]:
        hard.append("closing_question 누락")

    secs = d["sections"]
    if not 4 <= len(secs) <= 5:
        hard.append(f"sections는 4~5개여야 함(현재 {len(secs)}개)")
    h2s = [s["h2"] for s in secs]
    if any(not h for h in h2s):
        hard.append("h2가 빈 섹션이 있음")
    if len({re.sub(r"\s+", "", h) for h in h2s}) != len(h2s):
        hard.append("같은 h2가 반복됨")
    for i, s in enumerate(secs, 1):
        c = sum(_nospace_len(x) for x in s["paragraphs"] + s["bullets"])
        if c < 220:
            hard.append(f"{i}번 섹션 본문이 {c}자로 짧음 — 450자 안팎으로(문단 1개 추가, 구체값 포함)")

    # ── FAQ
    faq = d["faq"]
    if len(faq) != FAQ_COUNT:
        hard.append(f"faq는 정확히 {FAQ_COUNT}개여야 함(현재 {len(faq)}개)")
    for i, f in enumerate(faq, 1):
        if re.search(r"\[[^\]]{1,14}\]|\((시술|메뉴|상품|지역|업종|주제|대상|상호)[^)]*\)|OOO|○○|XXX", f["q"]):
            hard.append(f"FAQ {i}번 질문에 자리표시자/라벨이 있음")
        if _nospace_len(f["a"]) < 70:
            hard.append(f"FAQ {i}번 답변이 너무 짧음(120자 이상)")
    ends = [re.sub(r"[?\s]+$", "", f["q"])[-3:] for f in faq]
    if ends and max(ends.count(e) for e in set(ends)) >= 3:
        soft.append("FAQ 질문 어미가 3개 이상 같음 — 어미 변주")

    # ── 분량
    bc, sc = body_chars(d), section_chars(d)
    if bc < MIN_CHARS:
        hard.append(f"본문 합계 {bc}자 — 공백 제외 {MIN_CHARS}자 이상 필요(섹션 문단·항목을 늘리고 구체값 추가, {MIN_CHARS - bc}자 이상 부족)")
    if sc < MIN_SECTION_CHARS:
        hard.append(f"섹션 본문만 {sc}자 — {MIN_SECTION_CHARS}자 이상 필요(FAQ·팁으로 채우지 말고 섹션을 보강)")
    if bc > MAX_CHARS:
        hard.append(f"본문 합계 {bc}자로 너무 김 — {MAX_CHARS}자 이하로 줄이기")

    # ── 금지 표현·근거 없는 수치·경험 표현
    for w in _BANNED_HARD:
        if w in txt:
            hard.append(f"금지 표현 '{w}' 사용")
    for w in _EXPERIENCE:
        if w in txt:
            hard.append(f"운영자 경험 표현 '{w}' 사용 금지(경험 메모 없음)")
    if re.search(r"\d+(\.\d+)?\s*%", txt) or re.search(r"(연구|조사|통계|설문)(에|결과)[^.]{0,6}(따르면|의하면|결과)", txt):
        hard.append("출처 없는 퍼센트·통계 표현 금지")
    for w in _BANNED_VOCAB:
        if w in txt:
            soft.append(f"상투어 '{w}' 사용")

    # ── 도입
    intro = d["intro"]
    sents = _sentences(intro)
    if len(sents) > 3:
        soft.append(f"도입이 {len(sents)}문장 — 3문장 이내")
    if sents:
        first = sents[0]
        if not (re.search(r"\d", first) or any(w in first for w in _CONCRETE_WORDS)):
            soft.append("도입 첫 문장에 구체값(숫자·날짜·이름·기관) 1개 이상 필요")
    for w in _BAD_OPENERS:
        if intro.startswith(w) or w in intro[:30]:
            soft.append(f"금지 도입 '{w}'")
    if d["summary"] and intro and d["summary"][:18] == intro[:18]:
        soft.append("한줄요약이 도입 문장을 반복함")
    if not 90 <= len(d["summary"]) <= 300:
        soft.append(f"한줄요약 길이 {len(d['summary'])}자 — 120~220자 권장")

    # ── 박스
    briefs = sum(1 for s in secs if s["brief"])
    if secs and briefs < (len(secs) + 1) // 2:
        soft.append("간단 정리(brief)가 절반 이상의 섹션에 필요")
    longest_brief = max([_nospace_len(s["brief"]) for s in secs] or [0])
    if _nospace_len(d["wrapup"]) < 200 or _nospace_len(d["wrapup"]) <= longest_brief:
        soft.append("한 번에 정리는 250~450자이며 어떤 간단 정리보다 길어야 함")
    if sum(1 for s in secs for x in s["paragraphs"][-1:] if re.search(r"중요합니다\.?$", x)) >= 3:
        soft.append("섹션이 '~가 중요합니다'로 반복 종료됨")

    # ── 직전 글과의 중복
    prev_h2  = {re.sub(r"\s+", "", h) for r in recent for h in r.get("h2", [])}
    prev_faq = {re.sub(r"\s+", "", q) for r in recent for q in r.get("faq", [])}
    dup_h2 = [h for h in h2s if re.sub(r"\s+", "", h) in prev_h2]
    if dup_h2:
        hard.append("직전 글과 같은 소제목: " + " / ".join(dup_h2))
    dup_q = [f["q"] for f in faq if re.sub(r"\s+", "", f["q"]) in prev_faq]
    if dup_q:
        hard.append("직전 글과 같은 FAQ 질문: " + " / ".join(dup_q))
    prev_first = {" ".join(r.get("intro12", "").split()[:5]) for r in recent if r.get("intro12")}
    if intro and " ".join(intro.split()[:5]) in prev_first:
        soft.append("도입 첫 문장 시작이 직전 글과 같음")

    # ── 제목 중복(블로그에 이미 있는 제목)
    if d["titles"] and re.sub(r"\s+", "", d["titles"][0]) in existing_title_norms:
        hard.append("제목이 기존 글과 같음 — 다른 제목으로")
    return hard, soft


def generate_post(item, meta, ptype, intro_pat, recent, sky_text, existing_title_norms):
    """JSON 생성 → 정리 → 검증을 최대 MAX_ATTEMPTS회. hard 문제가 없는 최선의 결과를 돌려주고, 없으면 None(발행 건너뜀)."""
    retry_note, best, best_soft = "", None, None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"  ✍️ Gemini 생성 시도 {attempt}/{MAX_ATTEMPTS}")
        try:
            raw = _call_gemini(build_prompt(item, meta, ptype, intro_pat, recent, sky_text, retry_note), json_mode=True)
            d = autofix(normalize(parse_json_text(raw)))
        except Exception as e:
            print(f"  ⚠️ 생성/파싱 실패: {str(e)[:200]}")
            retry_note = "직전 출력이 올바른 JSON이 아니었습니다. 설명 없이 JSON 객체 하나만, 지정한 키 구조 그대로 출력하세요."
            continue
        hard, soft = validate(d, recent, existing_title_norms)
        print(f"    본문 {body_chars(d)}자(섹션 {section_chars(d)}자) · hard {len(hard)} · soft {len(soft)}")
        if not hard and (best is None or len(soft) < best_soft):
            best, best_soft = d, len(soft)
        if not hard and not soft:
            return d
        if not hard and attempt >= 2:
            break   # 사소한 지적(soft)은 한 번만 다시 쓰게 하고, 그다음엔 현재 결과를 수용 (호출 낭비 방지)
        for p in hard + soft:
            print(f"    - {p}")
        if attempt < MAX_ATTEMPTS:
            retry_note = "\n".join(f"- {p}" for p in hard + soft)
    if best is not None:
        print("  ℹ️ 사소한 지적(soft)이 남았지만 필수 기준(hard)은 통과 — 이 결과로 발행합니다.")
    return best


# ─────────────────────────────────────────
# HTML 조립 (인라인 스타일 — v9.5 19.5/19.6 박스 규격)
# ─────────────────────────────────────────
_E = lambda s: _html.escape(s or "", quote=True)

_H2_STYLE = "font-size:18px;color:#4c1d95;margin:26px 0 10px;line-height:1.5"
_BOX = "margin:{m};padding:{p};background:{bg};border:1px solid {bd};border-radius:12px"


def _box(label, inner, bg, bd, color, m="14px 0 18px", p="14px 16px", lfs="16px"):
    return (f'<div style="{_BOX.format(m=m, p=p, bg=bg, bd=bd)}">'
            f'<div style="font-weight:800;color:{color};font-size:{lfs};margin-bottom:6px">{label}</div>{inner}</div>')


def _ul(items, color="#334155"):
    return ('<ul style="margin:0;padding-left:20px;line-height:1.8;color:%s;font-size:15px">' % color +
            "".join(f"<li>{_E(i)}</li>" for i in items) + "</ul>")


def _table(t):
    th = "".join(f'<th style="border:1px solid #d1d5db;background:#f3f0ff;padding:8px 10px;font-size:14px;text-align:left">{_E(h)}</th>' for h in t["headers"])
    trs = "".join("<tr>" + "".join(f'<td style="border:1px solid #e5e7eb;padding:8px 10px;font-size:14px;line-height:1.6;color:#374151;vertical-align:top">{_E(c)}</td>' for c in r) + "</tr>" for r in t["rows"])
    cap = f'<div style="font-weight:700;color:#4c1d95;font-size:15px;margin:16px 0 6px">{_E(t["caption"])}</div>' if t["caption"] else ""
    return (f'{cap}<div style="overflow-x:auto;margin-bottom:16px"><table style="border-collapse:collapse;width:100%;min-width:320px">'
            f'<thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')


def make_hashtags(d, tags, topic):
    out = []
    for h in d["hashtags"] + tags + ["운세상식", "전통문화", "오늘운세로그", "운세공부", "생활상식", "띠별운세", "별자리운세"]:
        h = re.sub(r"[^0-9A-Za-z가-힣_]", "", str(h).lstrip("#"))
        if h and ("#" + h) not in out:
            out.append("#" + h)
        if len(out) >= 10:
            break
    return out[:10]


def build_body_html(d, meta, today_str, tags, topic):
    secs = d["sections"]
    parts = []

    parts.append(f'<p>{_E(d["intro"])}</p>')
    parts.append(_box("📌 한줄요약", f'<div style="line-height:1.75;color:#334155;font-size:15px">{_E(d["summary"])}</div>',
                      "#fffbeb", "#fcd34d", "#1e293b", m="18px 0 14px"))
    parts.append(_box("📍 나만의 포인트", _ul(d["points"]), "#ecfdf5", "#6ee7b7", "#065f46", m="0 0 14px"))

    toc = [(f"hh-s{i}", s["h2"]) for i, s in enumerate(secs, 1)]
    toc.append(("hh-judge", "이 글의 판단"))
    toc.append(("hh-faq", "자주 묻는 질문"))
    src_keys = [k for k in meta["src"] if k in SOURCES]
    if src_keys:
        toc.append(("hh-ref", "참고할 수 있는 공식 자료"))
    toc_html = ('<ol style="margin:0;padding-left:22px;line-height:1.9;font-size:15px">' +
                "".join(f'<li><a href="#{i}" style="color:#4f46e5;text-decoration:none">{_E(t)}</a></li>' for i, t in toc) + "</ol>")
    parts.append(_box("📚 목차", toc_html, "#eef2ff", "#c7d2fe", "#312e81", m="0 0 22px"))

    for i, s in enumerate(secs, 1):
        parts.append(f'<h2 id="hh-s{i}" style="{_H2_STYLE}">{_E(s["h2"])}</h2>')
        parts += [f"<p>{_E(p)}</p>" for p in s["paragraphs"]]
        if s["bullets"]:
            parts.append(_ul(s["bullets"], "#374151"))
        if s["brief"]:
            parts.append('<div style="margin:10px 0 22px;padding:9px 14px;background:#f8fafc;border-left:4px solid #94a3b8;'
                         'border-radius:6px;line-height:1.7;color:#334155;font-size:14px">📝 <b>간단 정리</b> · %s</div>' % _E(s["brief"]))

    parts.append(_box("✅ 한 번에 정리", f'<div style="line-height:1.75;color:#334155;font-size:15px">{_E(d["wrapup"])}</div>',
                      "#f0f9ff", "#bae6fd", "#0c4a6e", m="14px 0 22px", p="12px 16px", lfs="15px"))
    parts += [_table(t) for t in d["tables"]]

    parts.append(f'<h2 id="hh-judge" style="{_H2_STYLE}">이 글의 판단</h2><p>{_E(d["judgement"])}</p>')
    parts.append(_box("🛠 실전 팁", _ul(d["tips"]), "#fff7ed", "#fdba74", "#9a3412", m="14px 0 22px"))

    faq_html = "".join(f"<h3>Q. {_E(f['q'])}</h3><p>{_E(f['a'])}</p>" for f in d["faq"])
    parts.append(f'<h2 id="hh-faq" style="{_H2_STYLE}">자주 묻는 질문</h2><div class="faq">{faq_html}</div>')

    if src_keys:
        lis = "".join(
            f'<li>{_E(SOURCES[k][0])} · {_E(SOURCES[k][1])} · <a href="{SOURCES[k][2]}" rel="noopener" target="_blank">{_E(SOURCES[k][2])}</a></li>'
            for k in src_keys)
        parts.append(f'<h2 id="hh-ref" style="{_H2_STYLE}">참고할 수 있는 공식 자료</h2>'
                     f'<ul style="margin:0 0 6px 20px;font-size:14px;line-height:1.8;color:#374151">{lis}</ul>'
                     f'<p style="font-size:12px;color:#9ca3af">발행 {today_str} 기준. 위 기관은 더 확인할 수 있는 공식 안내처이며, 날짜·내용은 각 기관 자료에서 직접 확인하세요.</p>')

    parts.append(f'<p style="margin-top:18px;font-weight:700;color:#4c1d95">💬 {_E(d["closing_question"])}</p>')
    parts.append('<p style="font-size:13px;color:#6b7280;line-height:1.9">' + " ".join(make_hashtags(d, tags, topic)) + "</p>")
    return "\n".join(parts)


GEMINI_MODEL_CANDIDATES = [
    "gemini-3.1-flash-lite",
    "gemini-3-flash",
    "gemini-flash-latest",
]


def _clean_model_text(text):
    """코드블록·마크다운 잔여물 제거."""
    text = (text or "").strip()
    text = text.replace("```json", "").replace("```html", "").replace("```", "").strip()
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


def _call_gemini(prompt, json_mode=False):
    """모델 후보를 차례로 시도해 텍스트 한 덩어리를 돌려준다.
    일시 오류(503 등)는 같은 모델로 재시도하고, 고정 후보가 전부 실패하면 사용 가능한 flash 모델을 조회해 추가 시도한다.
    전부 실패하면 RuntimeError."""
    client = _make_client()
    if json_mode:
        try:
            cfg = types.GenerateContentConfig(max_output_tokens=MAX_OUT_TOKENS, temperature=0.8,
                                              response_mime_type="application/json")
        except Exception:
            cfg = types.GenerateContentConfig(max_output_tokens=MAX_OUT_TOKENS, temperature=0.8)
    else:
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

def _norm_title(t):
    return re.sub(r"\s+", "", t or "")


def fetch_existing_titles(access_token):
    """블로그에 실제로 올라가 있는 '운세상식' 글 제목을 모두 가져온다 (중복 발행 방지용).
    상태 파일(knowledge_state.json)이 초기화되거나 날아가도 중복이 생기지 않게 블로그 자체를 기준으로 삼는다.
    조회에 실패하면 None을 돌려주고, 그 경우 상태 파일 기록만으로 중복을 막는다."""
    if not BLOG_ID or not access_token:
        return None
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts"
    titles, metas, page = [], [], None
    try:
        while True:
            params = {"labels": "운세상식", "maxResults": 500, "fetchBodies": "false",
                      "fields": "items(title,customMetaData),nextPageToken"}
            if page:
                params["pageToken"] = page
            resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, params=params, timeout=60)
            if resp.status_code != 200:
                print(f"  ⚠️ 기존 글 제목 조회 실패({resp.status_code}): {resp.text[:120]}")
                return None
            data = resp.json()
            titles += [it.get("title", "") for it in data.get("items", [])]
            metas  += [it.get("customMetaData", "") for it in data.get("items", [])]
            page = data.get("nextPageToken")
            if not page:
                break
    except Exception as e:
        print(f"  ⚠️ 기존 글 제목 조회 중 오류: {e}")
        return None
    return titles, metas


def pick_next_topic_index(state, used_norm):
    """이미 발행된 주제를 건너뛰고 다음에 쓸 주제 인덱스를 고른다. 모두 소진되었으면 None.
    예전처럼 처음부터 다시 순환하지 않는다 — 같은 제목이 두 번 올라가는 문제를 막기 위함."""
    n = len(TOPICS)
    # 교육형 우선 주제(priority)가 남아 있으면 순서와 상관없이 먼저 고른다
    for j, t in enumerate(TOPICS):
        if t.get("priority") and _norm_title(t["topic"]) not in used_norm:
            return j
    start = state["last_index"] + 1
    for k in range(n):
        j = (start + k) % n
        if _norm_title(TOPICS[j]["topic"]) not in used_norm:
            return j
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


def pick_type(history, hint):
    """직전 3개 글과 다른 유형을 고른다(23.6). 주제 힌트가 직전 3개와 겹치지 않으면 힌트 우선."""
    recent_types = [h.get("type") for h in history[-3:]]
    if hint in POST_TYPES and hint not in recent_types:
        return hint
    cands = [t for t in POST_TYPES if t not in recent_types] or list(POST_TYPES)
    return cands[len(history) % len(cands)]


def pick_intro_pattern(history):
    """도입 패턴 3종을 돌려 쓰되 같은 패턴을 연속 2회 쓰지 않는다(23.6)."""
    last = history[-1].get("intro_pat") if history else None
    cands = [p for p in INTRO_PATTERNS if p != last]
    return cands[len(history) % len(cands)]


def run(count=1, draft=False):
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)

    access_token = get_access_token_for_knowledge()
    if not access_token:
        print("❌ Blogger 인증 실패 — 발행을 진행할 수 없습니다.")
        sys.exit(1)

    if draft:
        print("📝 초안 모드 — 블로그에 공개하지 않고 Blogger 초안함에만 저장합니다. 상태 파일(발행 기록)은 바꾸지 않아 주제가 소진되지 않습니다.")
    state = load_state()
    coupang_links = load_coupang_links()
    success_count = 0

    # 이미 발행된 주제 = 블로그 기존 제목(구형 글은 제목=주제) + 글에 저장한 주제 키(신형 글) + 상태 파일 기록
    existing = fetch_existing_titles(access_token)
    used_norm = {_norm_title(h.get("topic", "")) for h in state.get("history", [])}
    title_norms = {_norm_title(h.get("title", "")) for h in state.get("history", []) if h.get("title")}
    if existing is not None:
        titles, metas = existing
        used_norm |= {_norm_title(t) for t in titles}
        used_norm |= {_norm_title(m.split("topic:", 1)[1]) for m in metas if m and m.startswith("topic:")}
        title_norms |= {_norm_title(t) for t in titles}
        seen, dups = set(), []
        for t in titles:
            k = _norm_title(t)
            if k in seen:
                dups.append(t)
            seen.add(k)
        print(f"📚 블로그에 이미 올라간 운세상식 글: {len(titles)}개")
        if dups:
            print("⚠️ 같은 제목이 2번 이상 올라간 글이 있습니다 (직접 삭제 필요): " + " / ".join(sorted(set(dups))))
    else:
        print("ℹ️ 블로그 기존 글 조회 실패 — 상태 파일 기록만으로 중복을 확인합니다.")

    exhausted = False

    for i in range(count):
        idx = pick_next_topic_index(state, used_norm)
        if idx is None:
            print("🛑 TOPICS의 모든 주제가 이미 발행되었습니다. 중복 발행을 막기 위해 새 글을 만들지 않습니다. "
                  "create_knowledge.py의 TOPICS에 새 주제를 추가해 주세요.")
            exhausted = True
            break
        item = TOPICS[idx]
        topic, emoji, tags = item["topic"], item["emoji"], item["tags"]
        meta = get_meta(item)
        _cp = coupang_links.get(idx, {})
        coupang_url     = _cp.get("coupang_url", "")
        product_keyword = _cp.get("product_keyword", "")

        hist    = state.get("history", [])
        recent  = hist[-RECENT_N:]
        ptype   = pick_type(hist, meta["type_hint"])
        intro_p = pick_intro_pattern(hist)
        today   = datetime.now(timezone.utc).astimezone(KST).date()
        print(f"[{i+1}/{count}] 주제 #{idx}: {topic}  (남은 새 주제 {sum(1 for x in TOPICS if _norm_title(x['topic']) not in used_norm)}개)")
        print(f"  🎯 글 유형: {ptype} · 도입: {intro_p} · 근거 안내처: {', '.join(SOURCES[k][0] for k in meta['src']) or '없음'}")

        sky_text = sky_facts(meta["sky"], today)
        if sky_text:
            print(f"  🌌 천문 계산값 {sky_text.count(chr(10))}개 주입")

        try:
            d = generate_post(item, meta, ptype, intro_p, recent, sky_text, title_norms)
        except Exception as e:
            print(f"  ⚠️ Gemini 생성 실패: {e} — 이 주제는 건너뜁니다.")
            continue
        if not d:
            # 품질 기준 미달 — 기준 미달 글을 올리느니 건너뛴다 (인덱스 미저장 → 다음 실행 때 같은 주제 재시도)
            print("  ⚠️ 품질 기준 미달 — 발행을 건너뜁니다.")
            continue

        title = d["titles"][0]
        today_str = f"{today.year}.{today.month:02d}.{today.day:02d}"
        body_html = build_body_html(d, meta, today_str, tags, topic)
        print(f"  ✅ 최종 본문 {body_chars(d)}자 · 제목: {title}")

        kw_list  = [topic] + tags + ["운세상식"]
        tag_html = "".join(f'<span class="tag">{_E(t)}</span>' for t in kw_list)

        related_html = "".join(
            f'<a href="{url}" style="display:inline-block;background:linear-gradient(135deg,{grad});'
            f'color:#fff;padding:8px 16px;border-radius:20px;font-size:12px;font-weight:700;'
            f'text-decoration:none;margin:4px">{label}</a>'
            for label, url, grad in _RELATED_LINKS
        )

        # 쿠팡 링크가 채워진 주제에만 고지문구 + 상품 카드 렌더링.
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
       text-decoration:none">{_E(product_keyword) or '관련 상품'} 보러가기</a>
  </div>"""

        content = f"""{knowledge_style()}
<div class="wrap">
  <div class="hero">
    <h1>{emoji} {_E(title)}</h1>
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
        ok = post_blogger_scheduled(access_token, title, content, ["운세상식"], slug_number=(None if draft else slug_number),
                                    custom_meta=f"topic:{topic}", is_draft=draft)

        if ok and draft:
            print("  📝 초안 저장 완료 — Blogger 관리자 > 게시물 > 초안에서 확인하세요. (공개할 때는 퍼머링크를 숫자로 직접 지정하면 기존 주소 형식과 같아집니다)")
            success_count += 1
            break
        if ok:
            state["last_index"] = idx
            used_norm.add(_norm_title(topic))
            title_norms.add(_norm_title(title))
            state["next_slug_number"] = slug_number + 1  # 발행 성공 시에만 다음 번호로 갱신
            state["history"].append({
                "index":      idx,
                "topic":      topic,
                "title":      title,
                "title_alts": d["titles"][1:],
                "type":       ptype,
                "intro_pat":  intro_p,
                "intro12":    " ".join(d["intro"].split()[:12]),
                "h2":         [s["h2"] for s in d["sections"]],
                "faq":        [f["q"] for f in d["faq"]],
                "chars":      body_chars(d),
                "slug":       str(slug_number),
                "posted_at":  datetime.now(timezone.utc).isoformat(),
            })
            save_state(state)
            success_count += 1
        else:
            print(f"  ❌ '{topic}' 발행 실패 — 인덱스를 저장하지 않습니다. 다음 실행 때 같은 주제부터 다시 시도합니다.")
            break

        if i < count - 1:
            time.sleep(5)  # Gemini + Blogger 쿼터 보호

    return success_count, exhausted


def main():
    parser = argparse.ArgumentParser(description="운세상식 카테고리 자동 생성/발행")
    parser.add_argument("--count", type=int, default=1,
                         help="이번 실행에서 생성할 글 개수 (기본 1, 초기 시드 배치는 --count 10 처럼 크게)")
    parser.add_argument("--draft", action="store_true",
                         help="초안 모드 — 공개하지 않고 Blogger 초안함에만 저장(처음 확인용). 환경변수 KNOWLEDGE_DRAFT=1도 같음")
    args = parser.parse_args()
    draft = args.draft or os.environ.get("KNOWLEDGE_DRAFT", "").strip().lower() in ("1", "true", "yes")

    print(f"🚀 운세상식 생성 시작 — {args.count}개" + (" (초안 모드)" if draft else ""))
    success_count, exhausted = run(1 if draft else args.count, draft=draft)

    if success_count == 0 and exhausted:
        print("ℹ️ 발행할 새 주제가 없어 이번 실행은 아무것도 하지 않고 종료합니다.")
        return

    if success_count == 0:
        print("❌ 이번 실행에서 발행에 성공한 글이 하나도 없습니다.")
        sys.exit(1)

    print(f"🎉 완료 — {success_count}개 발행")


if __name__ == "__main__":
    main()
