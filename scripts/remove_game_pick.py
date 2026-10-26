#!/usr/bin/env python3
"""게임 본 페이지 10개에서 '호호픽(HOHO PICK)' 삽입 코드를 제거하는 일회용 스크립트.

- 대상: 저장소 루트의 게임 10개 페이지 (공략 페이지·미니게임·기타 페이지는 건드리지 않음)
- 제거 내용: <div id="hoho-pick-placeholder" ...></div> 와 그 바로 뒤의
             /hoho-pick.html 을 fetch 하는 <script> 한 덩어리
- 여러 번 실행해도 안전합니다(이미 지워진 파일은 건너뜀).
- 사용: python scripts/remove_game_pick.py        (실제 적용)
        python scripts/remove_game_pick.py --dry  (확인만)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TARGETS = [
    'hoya-typing-rpg.html',
    'hoya-proverb-typing.html',
    'hoho-cherry-blossom-typing.html',
    'hoho-typing-fps.html',
    'hoho-racing.html',
    'hoho-run.html',
    'hoho-tile-match.html',
    'jelly-pop-7.html',
    'hoho-dash.html',
    'word-puzzle-dungeon.html',
]

# 플레이스홀더 div + (그 뒤에 이어지는) hoho-pick.html 을 불러오는 script 한 개.
# script 범위가 다른 </script> 를 넘어가지 않도록 제한한다.
BLOCK = re.compile(
    r'[ \t]*<div id="hoho-pick-placeholder"[^>]*></div>[ \t]*\r?\n'
    r'[ \t]*<script>(?:(?!</script>).)*?hoho-pick\.html(?:(?!</script>).)*?</script>[ \t]*\r?\n?',
    re.S,
)


def remove_pick(text):
    new, n = BLOCK.subn('', text)
    return new, n


def main():
    dry = '--dry' in sys.argv
    changed, already, missing, failed = [], [], [], []
    for name in TARGETS:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            missing.append(name)
            continue
        with open(path, encoding='utf-8', newline='') as fp:
            original = fp.read()
        if 'hoho-pick' not in original:
            already.append(name)
            continue
        new, n = remove_pick(original)
        if n != 1 or 'hoho-pick' in new:
            failed.append((name, '삽입 블록을 1개로 특정하지 못함(%d개 매치)' % n))
            continue
        changed.append(name)
        if not dry:
            with open(path, 'w', encoding='utf-8', newline='') as fp:
                fp.write(new)
    print('호호픽 제거: 고침 %d개 / 이미 없음 %d개 / 파일 없음 %d개 / 확인 필요 %d개'
          % (len(changed), len(already), len(missing), len(failed)))
    for n in changed:
        print('  고침:', n)
    for n in already:
        print('  이미 없음:', n)
    for n in missing:
        print('  파일 없음:', n)
    for n, why in failed:
        print('  확인 필요:', n, '-', why)
    if dry:
        print('(--dry: 실제 파일은 바꾸지 않았습니다)')


if __name__ == '__main__':
    main()
