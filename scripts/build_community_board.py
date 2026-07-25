#!/usr/bin/env python3
"""
build_community_board.py — 커뮤니티 소식(GitHub Issues) 정적 캐시 생성
==========================================================
index.html의 "커뮤니티 소식" 섹션이 브라우저에서 GitHub API를 직접 호출하면
비로그인 요청 기준 시간당 60회 제한에 걸릴 수 있음. 그래서 이 스크립트가
GitHub Actions 안에서(레포 기본 GITHUB_TOKEN 사용 — 인증 시 시간당 5000회라
사실상 제한 없음) 대신 한 번 불러와 data/community_board.json에 고정 저장하고,
index.html은 이 정적 파일만 같은 사이트 안에서 읽음.

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
from datetime import datetime, timezone

REPO = "hohoplay/hohoplay.github.io"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'community_board.json')
PER_PAGE = 3


def fetch_issues():
    url = (
        f"https://api.github.com/repos/{REPO}/issues"
        f"?state=open&sort=created&direction=desc&per_page={PER_PAGE}"
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

    items = []
    for issue in raw_issues:
        if "pull_request" in issue:
            # GitHub Issues API에는 PR도 섞여서 나오므로 제외
            continue
        label = issue["labels"][0]["name"] if issue.get("labels") else ""
        items.append({
            "title": issue["title"],
            "url": issue["html_url"],
            "label": label,
        })

    data = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "issues": items,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(items)}개 이슈 저장 완료 → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
