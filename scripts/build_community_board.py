#!/usr/bin/env python3
"""
build_community_board.py — 커뮤니티 소식(GitHub Issues) 정적 캐시 생성
==========================================================
index.html의 "커뮤니티 소식" 섹션이 브라우저에서 GitHub API를 직접 호출하면
비로그인 요청 기준 시간당 60회 제한에 걸릴 수 있음. 그래서 이 스크립트가
GitHub Actions 안에서(레포 기본 GITHUB_TOKEN 사용 — 인증 시 시간당 5000회라
사실상 제한 없음) 대신 한 번 불러와 data/community_board.json에 고정 저장하고,
index.html은 이 정적 파일만 같은 사이트 안에서 읽음.

2026-07-29 수정 (제안 1):
  카드 개수를 3개 → 최대 6개로 늘리되, 억지로 6개를 채우지 않음.
  최근 RECENT_DAYS일 이내에 올라온 이슈만 후보로 삼고, 그중 최신순으로
  최대 MAX_ITEMS개까지만 보여줌 — 글이 뜸한 시기엔 3~4개만 나오고,
  활발한 시기엔 6개가 자연스럽게 꽉 차는 구조. 오래된 글로 억지로 채워서
  "최근에 안 올라오네"라는 역효과가 나는 걸 방지하기 위함.
  (제안 2: "별빛이 오솔길로 내려오는 밤" 매달 신간 발행 시 이슈 자동 생성과
   맞물리면, 최소 월 1개는 항상 이 RECENT_DAYS 윈도우 안에 들어오게 됨)

실행:
  python scripts/build_community_board.py

환경변수:
  GITHUB_TOKEN   (선택 — Actions 안에서는 자동 제공됨. 없어도 비로그인으로 시도)
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

REPO = "hohoplay/hohoplay.github.io"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'community_board.json')

FETCH_PAGE = 20     # 날짜 필터링 전에 넉넉히 후보를 가져올 개수
MAX_ITEMS = 6        # 최종적으로 보여줄 최대 개수
RECENT_DAYS = 30     # 이 기간(일) 이내에 올라온 것만 후보로 인정


def fetch_issues():
    url = (
        f"https://api.github.com/repos/{REPO}/issues"
        f"?state=open&sort=created&direction=desc&per_page={FETCH_PAGE}"
    )
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "hohoplay-community-board-bot",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    try:
        raw_issues = fetch_issues()
    except urllib.error.HTTPError as e:
        print(f"❌ GitHub API 오류: {e.code} {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 이슈 가져오기 실패: {e}")
        sys.exit(1)

    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)

    items = []
    for issue in raw_issues:
        if "pull_request" in issue:
            # GitHub Issues API에는 PR도 섞여서 나오므로 제외
            continue

        created_at_str = issue.get("created_at")
        if not created_at_str:
            continue
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        if created_at < cutoff:
            # 최신순 정렬로 가져오므로, 여기서부터는 전부 기준보다 오래된 것 — 더 볼 필요 없음
            break

        label = issue["labels"][0]["name"] if issue.get("labels") else ""
        items.append({
            "title": issue["title"],
            "url": issue["html_url"],
            "label": label,
        })

        if len(items) >= MAX_ITEMS:
            break

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "issues": items,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(items)}개 이슈 저장 완료(최근 {RECENT_DAYS}일 이내, 최대 {MAX_ITEMS}개) → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
