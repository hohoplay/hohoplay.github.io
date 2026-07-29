#!/usr/bin/env python3
"""
announce_meeting_issue.py — "별빛이 오솔길로 내려오는 밤" 신간 오픈 공지 자동 생성
==========================================================
fortune.html의 별자리월간 콘텐츠는 매월 "마지막 주 월요일"에 다음 달 버전으로
조기 전환됨(zodiacCycleMonth() 로직과 동일). "별빛이 오솔길로 내려오는 밤"도
같은 시드를 쓰므로, 이 시점에 새 호가 열리는 셈.

이 스크립트는 그 시점(그 달의 마지막 월요일)에 맞춰 GitHub Issue를 하나
자동으로 생성해 커뮤니티 소식 게시판에 "🌙 OO월호 오픈!" 알림이 자연스럽게
올라오게 함 — 사람이 직접 이슈를 안 올려도 최소 월 1회는 최신 글이 보장됨
(build_community_board.py의 RECENT_DAYS 필터와 맞물려 게시판이 마르지 않게 함).

실행: 매주 월요일 스케줄로 돌리되, 그 달의 마지막 월요일이 아니면 그냥
아무것도 안 하고 넘어감(멱등 — 매주 돌려도 안전).

환경변수:
  GITHUB_TOKEN   (필수 — Issue 생성 권한 필요, Actions 안에서는 자동 제공됨)
"""

import os
import sys
import json
import calendar
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

REPO = "hohoplay/hohoplay.github.io"
SITE_URL = "https://hohoplay.github.io/fortune/"
LABEL = "공지사항"


def kst_now():
    return datetime.now(timezone.utc) + timedelta(hours=9)


def last_monday_of_month(year, month):
    last_day = calendar.monthrange(year, month)[1]
    d = datetime(year, month, last_day)
    offset = d.weekday()  # Monday=0
    return (d - timedelta(days=offset)).date()


def next_issue_ym(now):
    # 조기 전환 — 이번 달 마지막 월요일에 여는 새 호는 "다음 달" 버전
    y, m = now.year, now.month + 1
    if m > 12:
        m = 1
        y += 1
    return y, m


def create_issue(title, body):
    url = f"https://api.github.com/repos/{REPO}/issues"
    payload = json.dumps({"title": title, "body": body, "labels": [LABEL]}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "hohoplay-meeting-issue-bot",
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    now = kst_now()
    today = now.date()
    lm = last_monday_of_month(now.year, now.month)

    if today != lm:
        print(f"오늘({today})은 이번 달 마지막 월요일({lm})이 아니라 건너뜀 — 정상")
        return

    if "GITHUB_TOKEN" not in os.environ:
        print("❌ GITHUB_TOKEN 환경변수 필요")
        sys.exit(1)

    y, m = next_issue_ym(now)
    title = f"🌙 {y}년 {m}월호 오픈! — 별빛이 오솔길로 내려오는 밤"
    body = (
        f"부엉이 마을의 새 이야기, {y}년 {m}월호가 열렸어요.\n\n"
        f"열두 별자리와 열두 띠가 이번 달엔 어떤 이야기를 들려줄지, "
        f"지금 바로 만나보세요.\n\n"
        f"👉 {SITE_URL} 의 '별빛오솔길의 밤' 탭에서 확인하실 수 있어요."
    )

    try:
        issue = create_issue(title, body)
        print(f"✅ 이슈 생성 완료 → {issue.get('html_url')}")
    except urllib.error.HTTPError as e:
        print(f"❌ GitHub API 오류: {e.code} {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 이슈 생성 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
