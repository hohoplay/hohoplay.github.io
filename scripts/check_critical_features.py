#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
핵심 기능 마커 가드.

왜 필요한가:
  오래된 로컬 백업 파일을 베이스로 다른 작업(예: 메뉴 추가)을 하다가,
  그 사이에 추가됐던 다른 기능(예: HOHO PICK 로더)이 통째로 같이
  사라지는 사고가 실제로 있었음(2026-10-05, index.html에서 호호픽
  불러오는 코드가 꿈해몽 메뉴 작업 중 사라짐). 파일 자체는 지워지지
  않고 레포에 멀쩡히 있었지만, 그걸 "불러오는 연결고리"만 사라져서
  화면에 안 보였음 — 이런 종류의 사고를 push 시점에 바로 잡기 위한
  스크립트.

하는 일:
  아래 CRITICAL_FEATURES에 등록해둔 (파일, 안에 반드시 있어야 하는
  문자열들, 설명) 목록을 돌면서, 파일이 없거나 문자열이 하나라도
  빠지면 실패(exit 1)하고 어떤 파일의 어떤 마커가 왜 빠졌는지 정확히
  알려준다. GitHub Actions에서 실행되면 ::error:: 형식으로도 찍어서
  Actions 화면에서 바로 보이게 한다.

새 기능을 추가했는데 이 가드에도 등록해두고 싶으면, 아래
CRITICAL_FEATURES 리스트에 항목만 추가하면 된다(코드 수정 불필요).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (파일 경로, [반드시 포함돼야 하는 문자열들], 사람이 읽을 설명)
CRITICAL_FEATURES = [
    (
        "index.html",
        ['id="hoho-pick-placeholder"', "fetch(\"/hoho-pick.html\")"],
        "메인 페이지의 'HOHO PICK' 큐레이션 위젯 로더 "
        "(축제·게임공략·커뮤니티·호호 매거진을 /hoho-pick.html에서 불러옴)",
    ),
    (
        "footer.html",
        None,  # 파일 존재 여부만 확인 (내용 마커는 아직 안 정함)
        "사이트 공용 푸터 (거의 모든 페이지가 fetch로 불러옴)",
    ),
    (
        "hoho-pick.html",
        ['id="hoho-pick-festival"', 'id="hoho-pick-guide"'],
        "HOHO PICK 큐레이션 조각 파일 자체 "
        "(index.html/game*/mgame*가 공통으로 fetch하는 대상)",
    ),
]


def in_github_actions():
    return os.environ.get("GITHUB_ACTIONS") == "true"


def check_one(rel_path, required_markers, description):
    """하나의 파일을 검사한다. (ok: bool, messages: list[str]) 반환."""
    full_path = os.path.join(ROOT, rel_path)
    messages = []

    if not os.path.exists(full_path):
        messages.append(
            f"[누락] {rel_path} 파일 자체가 없습니다 — {description}"
        )
        return False, messages

    if not required_markers:
        return True, messages

    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    missing = [m for m in required_markers if m not in content]
    if missing:
        missing_list = ", ".join(missing)
        messages.append(
            f"[마커 누락] {rel_path} 안에 다음 내용이 없습니다: {missing_list}\n"
            f"  → {description}\n"
            f"  → 이 파일이 최신 버전이 맞는지, 오래된 백업으로 덮어쓴 건 "
            f"아닌지 확인하세요."
        )
        return False, messages

    return True, messages


def main():
    any_fail = False
    for rel_path, required_markers, description in CRITICAL_FEATURES:
        ok, messages = check_one(rel_path, required_markers, description)
        if not ok:
            any_fail = True
            for msg in messages:
                if in_github_actions():
                    # GitHub Actions 주석 형식 (Actions 화면에 바로 노출됨)
                    first_line = msg.split("\n", 1)[0]
                    print(f"::error file={rel_path}::{first_line}")
                print(msg)
        else:
            print(f"[OK] {rel_path} — {description}")

    if any_fail:
        print(
            "\n하나 이상의 핵심 기능 마커가 빠졌습니다. "
            "실수로 예전 파일을 덮어쓴 건 아닌지 확인해주세요."
        )
        return 1

    print("\n모든 핵심 기능 마커 확인 완료 — 이상 없음.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
