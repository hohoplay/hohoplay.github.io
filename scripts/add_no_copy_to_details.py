#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/add_no_copy_to_details.py

[1회성 정리 스크립트] 상세페이지 본문 글자를 마우스로 드래그해 선택·복사하지 못하게 한다.
  - 대상: festival/detail/*.html (축제·캠핑장·자연관광지·아이랑 나들이 상세페이지)
  - 방법: </head> 바로 앞에 CSS 한 줄(user-select:none)을 넣는다. 입력칸(댓글 등)과 class="allow-copy" 는 선택 가능.
  - 이미 들어 있으면(id="hp-nocopy") 건너뛴다 → 여러 번 실행해도 결과는 같다.
  - 새로 만드는 페이지는 fetch_data.py(NOCOPY_STYLE)와 templates/kids_detail_template.html 이 같은 CSS를 넣는다.

사용법(저장소 루트에서):  python3 scripts/add_no_copy_to_details.py [--dry-run]
"""
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOCOPY = '''<style id="hp-nocopy">html,body{-webkit-user-select:none;user-select:none}input,textarea,select,[contenteditable="true"],.allow-copy{-webkit-user-select:text;user-select:text}img{-webkit-user-drag:none;user-drag:none}</style>'''


def main():
    dry = '--dry-run' in sys.argv
    files = sorted(glob.glob(os.path.join(ROOT, 'festival', 'detail', '*.html')))
    done = skip = nohead = 0
    for fp in files:
        with open(fp, encoding='utf-8') as f:
            t = f.read()
        if 'id="hp-nocopy"' in t:
            skip += 1
            continue
        if '</head>' not in t:
            nohead += 1
            continue
        t = t.replace('</head>', NOCOPY + '\n</head>', 1)
        if not dry:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(t)
        done += 1
    print(f"상세페이지 {len(files)}개 / 새로 적용 {done}개 / 이미 적용 {skip}개 / </head> 없음 {nohead}개" + (' (dry-run)' if dry else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
