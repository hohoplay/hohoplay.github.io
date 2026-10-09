# -*- coding: utf-8 -*-
"""
사이트 전체 페이지의 "플레이하기" 드롭다운/모바일 메뉴에 있는 "축제 지도" 글자를
"아이랑 나들이 지도"로 바꾸는 1회성 작업 스크립트입니다.

배경: /festival/ 페이지가 원래는 축제 정보만 보여줬는데, 이제 "아이랑 나들이 지도"
탭(아이랑 갈만한 곳 199곳)도 같이 보여주는 페이지로 바뀌어서 메뉴 이름도 그에 맞게
바꾸는 작업입니다. href(링크 주소)는 그대로 "/festival/" 입니다 — 바뀌는 건 화면에
보이는 글자뿐입니다.

중요 — 왜 느슨한 문자열 치환을 쓰지 않았는지:
    이 사이트는 네비게이션 메뉴가 공통 헤더 파일 하나로 관리되는 게 아니라, 페이지마다
    똑같은 메뉴 코드가 각자 복사되어 들어있는 구조입니다(100개 넘는 페이지). 그런데
    "축제 지도"라는 글자는 메뉴뿐 아니라 일부 페이지의 FAQ/소개 문구
    (예: "전국의 다양한 축제 정보를 지도에서 쉽게 찾아볼 수 있습니다" 같은 설명 옆
    링크)에도 똑같이 등장합니다. 이런 본문 설명은 실제로 축제 기능을 가리키는 말이라
    틀린 게 아니므로 건드리면 안 됩니다. 그래서 "축제 지도"라는 글자만 보고 바꾸지
    않고, 실제 메뉴에서만 쓰이는 걸로 확인된 정확한 전체 <a> 태그 모양(스타일/클래스
    속성까지 포함)만 정확히 찾아서 바꿉니다.

    아래 NAV_TAG_TEMPLATES 7가지는 저장소의 모든 *.html 파일(사이트 전체)을 미리
    스캔해서 "href=\"/festival/\" + 글자가 정확히 '축제 지도'인 <a> 태그" 10가지
    변형을 전부 찾아낸 뒤, 그중 메뉴 스타일(패딩/hover 효과 등)을 가진 7가지만
    추린 것입니다. 나머지 3가지(BODY_TEXT_TAGS)는 FAQ/소개 문구용으로 확인되어
    일부러 포함하지 않았습니다.

안전장치:
    - 이미 "아이랑 나들이 지도"로 바뀐 파일은 old 패턴이 더 이상 없으므로 자동으로
      건너뜁니다 — 여러 번 실행해도 안전합니다(멱등적).
    - 실행 후, 알려진 7가지 메뉴 모양도 아니고 알려진 3가지 본문 모양도 아닌데
      "축제 지도"라는 글자가 남아있는 <a href="/festival/"> 태그가 있으면(= 이
      스크립트가 모르는 새로운 메뉴 디자인일 가능성) "검토 필요" 목록으로 따로
      보여줍니다. 이 스크립트는 그런 경우를 자동으로 고치지 않습니다(잘못 고치는
      것보다 사람이 확인하는 게 안전해서).

사용법:
    python3 scripts/rename_festival_nav_label.py [저장소 루트 경로(기본값: 현재 폴더)]
"""
import glob
import os
import re
import sys

OLD_LABEL = "축제 지도"
NEW_LABEL = "아이랑 나들이 지도"

# 실제로 메뉴(네비게이션)에서만 쓰이는 걸로 확인된 정확한 전체 태그 7가지.
NAV_TAG_TEMPLATES = [
    # 1) PC 드롭다운 — 인라인 style 버전 (구형 게임/가이드 페이지들)
    '<a href="/festival/" style="display:block;width:100%;box-sizing:border-box;'
    'text-align:left;padding:10px 16px;font-size:14px;font-weight:700;'
    'color:#475569;text-decoration:none">{label}</a>',
    # 2) 모바일 메뉴 — 인라인 style 버전
    '<a href="/festival/" style="display:block;padding:12px 16px;border-radius:12px;'
    'font-weight:700;color:#334155;text-decoration:none">{label}</a>',
    # 3) PC 드롭다운 — Tailwind class 버전 (index.html 계열 신형 페이지들)
    '<a href="/festival/" class="block w-full text-left px-4 py-2.5 text-sm '
    'font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 '
    'transition">{label}</a>',
    # 4) PC 드롭다운 — 인라인 style + 게임오디오 정지 onclick 버전 (게임 페이지들)
    '<a href="/festival/" onclick="stopAllGameAudio();return true;" '
    'style="display:block;width:100%;box-sizing:border-box;text-align:left;'
    'padding:10px 16px;font-size:14px;font-weight:700;color:#475569;'
    'text-decoration:none">{label}</a>',
    # 5) 모바일 메뉴 — 인라인 style + 게임오디오 정지 onclick 버전
    '<a href="/festival/" onclick="stopAllGameAudio();return true;" '
    'style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;'
    'color:#334155;text-decoration:none">{label}</a>',
    # 6) 모바일 메뉴 — Tailwind class 버전 (class 끝에 block 없는 형태)
    '<a href="/festival/" class="block w-full text-left px-4 py-3 rounded-xl '
    'font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 '
    'transition">{label}</a>',
    # 7) 모바일 메뉴 — Tailwind class 버전 (class 끝에 block 있는 형태, index.html 등)
    '<a href="/festival/" class="w-full text-left px-4 py-3 rounded-xl '
    'font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 '
    'transition block">{label}</a>',
]

# 일부러 바꾸지 않는 것 — 메뉴가 아니라 본문/FAQ 설명 문구에 쓰이는 링크들.
BODY_TEXT_TAGS = [
    '<a href="/festival/" style="color:#4f46e5;text-decoration:underline">{label}</a>',
    '<a href="/festival/" style="color:#4f46e5;text-decoration:underline">'
    '<strong>{label}</strong></a>',
    '<a href="/festival/">{label}</a>',
]

# 교체 후에도 "축제 지도"가 남아있는 <a href="/festival/">...</a> 태그를 찾아서,
# 그게 알려진 본문 패턴인지 아닌지 구분하기 위한 느슨한 탐지용 정규식(수정에는 안 씀).
REMAINING_TAG_RE = re.compile(
    r'<a\s+href="/festival/"[^>]*>(?:<strong>)?' + re.escape(OLD_LABEL) + r'(?:</strong>)?</a>'
)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    html_files = sorted(glob.glob(os.path.join(root, "**", "*.html"), recursive=True))

    changed_files = []
    total_replacements = 0

    for path in html_files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        file_replacements = 0
        for template in NAV_TAG_TEMPLATES:
            old_tag = template.format(label=OLD_LABEL)
            new_tag = template.format(label=NEW_LABEL)
            count = content.count(old_tag)
            if count:
                content = content.replace(old_tag, new_tag)
                file_replacements += count

        if content != original:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            changed_files.append((path, file_replacements))
            total_replacements += file_replacements

    print(f"바뀐 파일: {len(changed_files)}개 / 바뀐 메뉴 항목: {total_replacements}개")
    for path, cnt in changed_files:
        print(f"  - {path} ({cnt}곳)")

    # 알려진 본문 패턴(의도적으로 안 바꾼 것)과, 알려지지 않은 새로운 모양을 구분해서 보고.
    known_body_tags = {t.format(label=OLD_LABEL) for t in BODY_TEXT_TAGS}
    expected_body_count = 0
    unexpected = []

    for path in html_files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        for m in REMAINING_TAG_RE.finditer(content):
            tag = m.group(0)
            if tag in known_body_tags:
                expected_body_count += 1
            else:
                unexpected.append((path, tag))

    print()
    print(f"의도적으로 남겨둔 본문/FAQ 문구: {expected_body_count}곳 (정상 — 메뉴가 아님)")
    if unexpected:
        print(f"\n=== 검토 필요: 알려지지 않은 메뉴 모양 {len(unexpected)}곳 ===")
        for path, tag in unexpected:
            print(f"  - {path}")
            print(f"      {tag}")
    else:
        print("검토가 필요한 알 수 없는 메뉴 모양: 없음")


if __name__ == "__main__":
    main()
