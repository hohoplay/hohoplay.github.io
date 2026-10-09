#!/usr/bin/env python3
"""scripts/check_critical_features.py

과거 백업 파일로 특정 페이지(특히 index.html)를 덮어쓰다가, 그 안에 있던
다른 핵심 기능(예: HOHO PICK 로더)까지 같이 지워지는 사고가 있었다. 이
스크립트는 그런 사고를 push 시점에 바로 잡기 위해, 각 파일 안에 "반드시
있어야 하는 마커 문자열"이 실제로 있는지만 확인한다.

자동으로 고치지는 않는다(잘못 고치면 더 위험하므로) — 대신 어떤 파일의
어떤 기능이 빠졌는지 명확하게 보여주고, 하나라도 빠지면 CI를 실패시킨다.

새로 추가한 핵심 기능도 여기서 지켜지길 원하면, 아래 CHECKS에 한 줄
추가하면 된다(파일이 실제로 배포된 뒤에 추가할 것 — 아직 안 올라간 기능을
먼저 넣으면 다음 푸시 때 바로 실패한다).
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (파일 경로, 마커 문자열, 설명) — 마커가 파일에 없으면 실패 처리된다.
CHECKS = [
    ("index.html", 'id="hoho-pick-placeholder"', "HOHO PICK 섹션 로더"),
    ("index.html", 'href="/dream/"', "꿈해몽 사전 메뉴 링크"),
    ("index.html", 'href="/vote/"', "익명투표 메뉴 링크"),
    ("index.html", 'href="/quiz/"', "상식테스트 메뉴 링크"),
    ("index.html", 'href="/festival/"', "아이랑 나들이 지도 메뉴 링크"),
    ("index.html", 'id="content"', "메인 콘텐츠(크롤러용 정적 폴백) 컨테이너"),
    ("festival/index.html", 'id="courseModeBtn"', "지역별 추천 코스 보기 버튼"),
]


def iter_game_files():
    """game*.html / mgame*.html은 전부 같은 댓글 시스템(old-rain-16f7 Worker)을
    쓴다 — 파일 하나하나 나열하는 대신 존재하는 파일을 훑어서 확인한다."""
    for pattern in ("game*.html", "mgame*.html"):
        for path in sorted(glob.glob(os.path.join(ROOT, pattern))):
            yield os.path.relpath(path, ROOT)


def main():
    failures = []

    for rel_path, marker, desc in CHECKS:
        full_path = os.path.join(ROOT, rel_path)
        if not os.path.exists(full_path):
            failures.append(f"{rel_path}: 파일 자체가 없음 ({desc})")
            continue
        with open(full_path, encoding="utf-8") as f:
            content = f.read()
        if marker not in content:
            failures.append(f"{rel_path}: '{desc}' 마커가 없음 (찾던 문자열: {marker})")

    for rel_path in iter_game_files():
        full_path = os.path.join(ROOT, rel_path)
        with open(full_path, encoding="utf-8") as f:
            content = f.read()
        if "old-rain-16f7" not in content:
            failures.append(f"{rel_path}: 댓글 위젯(old-rain-16f7 Worker 연동)이 없음")

    if failures:
        print("::error::핵심 기능 마커 확인 실패 — 아래 항목을 확인해주세요")
        for msg in failures:
            print(f"::error::{msg}")
        print()
        print(f"총 {len(failures)}건 누락됨. 백업 파일로 덮어썼거나 실수로 코드가 지워졌을 가능성이 있습니다.")
        sys.exit(1)

    total_checked = len(CHECKS) + len(list(iter_game_files()))
    print(f"핵심 기능 마커 확인 완료 — {total_checked}개 파일 체크, 이상 없음.")


if __name__ == "__main__":
    main()
