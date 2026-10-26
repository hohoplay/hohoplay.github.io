#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상단 메뉴 개편 (한 번만 실행하는 일괄 수정 스크립트)

  ① '💬 소통' 이름을 '소통·정보'로 바꾸고, 그 안을 이렇게 묶는다:
       커뮤니티 · 호호 매거진 · 아이랑 나들이 지도 · 게임공략 · 꿈해몽 사전 · 파트너
     (아이랑 나들이 지도 / 게임공략 / 꿈해몽 사전은 '플레이하기'에서 옮겨온다)
  ② '회사' 안의 '고객지원'을 '약관·정책' 맨 아래로 옮긴다.
  ③ (2차) '회사' 메뉴(소개 하나만 남음)를 통째로 없애고, 오른쪽 위 '🔮 오늘의 운세' 버튼/아이콘을 없앤 대신
     '플레이하기'의 상식테스트 아래에 '운세' 항목을 추가한다.

저장소의 모든 .html / .py 파일을 훑어서 메뉴 코드가 있는 곳만 고친다
(생성 스크립트·템플릿 안에 박힌 메뉴도 같이 고쳐야 자동 생성 페이지가 다시 옛 메뉴로 돌아가지 않는다).
데스크톱 메뉴와 모바일 메뉴를 각각 따로 처리하며, 이미 고쳐진 파일은 건드리지 않는다(여러 번 실행해도 안전).
고칠 자리를 정확히 못 찾은 파일은 건드리지 않고 마지막에 목록으로 알려준다.

사용법:  python scripts/update_nav_menu.py          (실제로 고침)
         python scripts/update_nav_menu.py --dry     (고치지 않고 결과만 보여줌)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'.git', 'node_modules', '.github'}
SKIP_FILES = {'update_nav_menu.py'}
NEEDED = (('호호 매거진', '/blog/magazine/'), ('아이랑 나들이 지도', '/festival/'), ('게임공략', '/guides/index.html'), ('꿈해몽 사전', '/dream/'))
# 예전 이름으로 남아 있는 페이지가 있으면 같은 항목으로 보고 이름도 같이 바꾼다
ALIASES = {'아이랑 나들이 지도': ('축제 지도',)}
SUPPORT_RE = re.compile(r'^[^\n]*>고객지원</(?:a|button)>[^\n]*\n', re.M)


def item_line(seg, label):
    """seg 안에서 label 텍스트를 가진 메뉴 항목 한 줄을 찾는다(없으면 None)."""
    m = re.search(r'^[^\n]*>%s</(?:a|button)>[^\n]*\n' % re.escape(label), seg, re.M)
    return m.group(0) if m else None


def line_bounds(text, idx):
    start = text.rfind('\n', 0, idx) + 1
    end = text.find('\n', idx)
    end = len(text) if end == -1 else end + 1
    return start, end


def copy_look(line, ref):
    """line의 모양(class 또는 style 속성)을 ref 줄과 똑같이 맞춘다."""
    for attr in ('class', 'style'):
        r = re.search(r'%s="[^"]*"' % attr, ref)
        if r and re.search(r'%s="[^"]*"' % attr, line):
            line = re.sub(r'%s="[^"]*"' % attr, lambda _m: r.group(0), line, count=1)
    return line


def process(text, desktop, active_label=None):
    """한 가지 메뉴(데스크톱 또는 모바일)를 고친다. (새 텍스트, 상태 문구) 반환."""
    if desktop:
        pat_company, pat_play, pat_comm, pat_terms = r'회사 <svg', r'플레이하기 <svg', r'소통(?:·정보)? <svg', r'약관·정책 <svg'
    else:
        pat_company, pat_play, pat_comm, pat_terms = r'회사</div>', r'플레이하기</div>', r'소통(?:·정보)?</div>', r'>이용약관</'

    def find(pat, start):
        m = re.compile(pat).search(text, start)
        return (m.start(), m.end()) if m else (-1, -1)

    iC, _ = find(pat_company, 0)
    if iC == -1:
        return text, 'none'          # 이 파일엔 이 메뉴가 없음
    iP, _ = find(pat_play, iC)
    iS, eS = find(pat_comm, iP) if iP != -1 else (-1, -1)
    iT, _ = find(pat_terms, iS) if iS != -1 else (-1, -1)
    if min(iP, iS, iT) == -1:
        return text, 'fail:마커 순서 불일치'

    seg_play, seg_comm, seg_comp = text[iP:iS], text[iS:iT], text[iC:iP]
    t_end = text.find('</div>', iT)
    t_end = iT + 5000 if t_end == -1 else t_end
    seg_terms = text[iT:t_end]

    # ── 소통·정보에 들어갈 3개: 이미 있으면 그대로, 플레이하기에 있으면 옮기고, 없으면(옛 페이지) 새로 만든다 ──
    to_insert, to_remove_from_play = [], []
    template = item_line(seg_play, '익명투표') or item_line(seg_play, '전체게임')
    for label, href in NEEDED:
        if ('>%s<' % label) in seg_comm:
            continue
        ln = item_line(seg_play, label)
        old_ln = None
        if not ln:
            for alias in ALIASES.get(label, ()):
                old_ln = item_line(seg_play, alias)
                if old_ln:
                    ln = old_ln.replace('>%s<' % alias, '>%s<' % label, 1)
                    break
        if ln:
            to_remove_from_play.append(old_ln or ln)
            to_insert.append(ln)
        elif template:
            ln = re.sub(r'href="[^"]*"', lambda _m: 'href="%s"' % href, template, count=1)
            ln = re.sub(r'onclick="[^"]*"\s*', '', ln, count=1)
            ln = re.sub(r'>(?:익명투표|전체게임)<', '>%s<' % label, ln, count=1)
            to_insert.append(ln)
        else:
            return text, 'fail:새 항목을 만들 기준 줄(익명투표/전체게임)이 없음'

    support = SUPPORT_RE.search(seg_comp)
    support_done = ('>고객지원<' in seg_terms)

    # ── 뒤쪽 위치부터 고쳐야 앞쪽 위치가 안 밀린다: ① 약관·정책 ② 소통 ③ 플레이하기 ④ 회사 ──
    # ① 고객지원 → 약관·정책 맨 아래 ('저작권·콘텐츠 정책' 줄 다음, 그 줄의 모양을 그대로 복사)
    if support and not support_done:
        ref_idx = text.find('저작권·콘텐츠 정책</', iT, t_end)
        if ref_idx == -1:
            ref_idx = text.find('개인정보처리방침</', iT, t_end)
        if ref_idx == -1:
            return text, 'fail:약관·정책 메뉴의 기준 줄을 못 찾음'
        ls, le = line_bounds(text, ref_idx)
        line = copy_look(support.group(0), text[ls:le])
        text = text[:le] + line + text[le:]

    # ② 소통 → 소통·정보 (+ 3개를 호호 매거진 다음, 파트너 앞에 삽입)
    new_comm = seg_comm
    if to_insert:
        p = new_comm.find('>파트너</')
        if p == -1:
            return text, 'fail:소통 메뉴에서 파트너 항목을 못 찾음'
        ps, _ = line_bounds(new_comm, p)
        new_comm = new_comm[:ps] + ''.join(to_insert) + new_comm[ps:]
    # [보정] <a> 링크 항목은 반드시 class에 block이 있어야 한 줄씩 쌓인다. 예전 실행에서 파트너(<button>)의
    # class를 그대로 복사하는 바람에 block이 빠져 "게임공략 꿈해몽 사전"이 한 줄에 붙던 페이지도 여기서 고친다.
    def _fix_block(m):
        cls = m.group(2)
        return m.group(0) if re.search(r'(?<![\w-])block(?![\w-])', cls) else '%sclass="block %s"' % (m.group(1), cls)
    new_comm = re.sub(r'(^[^\n]*?<a\b[^>\n]*?\s)class="([^"]*)"', _fix_block, new_comm, flags=re.M)

    # [보정] 꿈해몽 사전 페이지에서는 그 항목이 "지금 보는 페이지" 색(보라)이어야 한다. 예전 실행으로 풀렸으면 되돌린다.
    if active_label:
        new_comm = re.sub(r'(^[^\n]*>%s</[^\n]*$)' % re.escape(active_label),
                          lambda m: re.sub(r'color:#(?:475569|334155)', 'color:#4f46e5', m.group(1)), new_comm, flags=re.M)

    # 항목 순서를 항상 같게: 커뮤니티 · 호호 매거진 · 아이랑 나들이 지도 · 게임공략 · 꿈해몽 사전 · 파트너
    # (옛 페이지에는 순서가 다르거나 호호 매거진이 빠진 곳이 있다). 모르는 항목이 섞여 있으면 순서는 건드리지 않는다.
    ORDER = ['커뮤니티', '호호 매거진', '아이랑 나들이 지도', '게임공략', '꿈해몽 사전', '파트너']
    lines = new_comm.splitlines(keepends=True)
    slots = [i for i, l in enumerate(lines) if re.search(r'>[^<>]+</(?:a|button)>', l)]
    names = [re.search(r'>([^<>]+)</(?:a|button)>', lines[i]).group(1) for i in slots]
    if names and all(n in ORDER for n in names):
        ordered = [lines[i] for _, i in sorted(zip((ORDER.index(n) for n in names), slots), key=lambda t: t[0])]
        for slot, ln in zip(slots, ordered):
            lines[slot] = ln
        new_comm = ''.join(lines)
    if desktop:
        new_comm = new_comm.replace('소통 <svg', '소통·정보 <svg', 1)
        # 긴 항목 이름이 줄바꿈되지 않도록 드롭다운 폭을 넓힌다(Tailwind w-36 / 인라인 140px)
        new_comm = new_comm.replace('w-36 bg-white', 'w-44 bg-white', 1).replace('width:140px', 'width:176px', 1)
    else:
        new_comm = new_comm.replace('소통</div>', '소통·정보</div>', 1)
    text = text[:iS] + new_comm + text[iT:]

    # ③ 플레이하기에서 옮긴 항목 제거
    if to_remove_from_play:
        new_play = seg_play
        for ln in to_remove_from_play:
            new_play = new_play.replace(ln, '', 1)
        text = text[:iP] + new_play + text[iS:]

    # ④ 회사에서 고객지원 제거
    if support:
        text = text[:iC] + seg_comp.replace(support.group(0), '', 1) + text[iP:]
    return text, 'ok'



SUPPORT_OR_ABOUT = {'소개', '고객지원'}


def _labels(seg):
    return re.findall(r'>([^<>]+)</(?:a|button)>', seg)


def remove_company_desktop(text):
    """데스크톱 '회사' 드롭다운 그룹 전체를 지운다. 반환: (text, 상태)."""
    lines = text.splitlines(keepends=True)
    k = next((i for i, l in enumerate(lines) if '회사 <svg' in l), None)
    if k is None:
        return text, 'none'
    if k == 0 or not lines[k - 1].lstrip().startswith('<div'):
        return text, 'fail:회사 그룹 시작 줄을 못 찾음'
    indent = len(lines[k - 1]) - len(lines[k - 1].lstrip())
    end = next((i for i in range(k + 1, len(lines))
                if lines[i].strip() == '</div>' and len(lines[i]) - len(lines[i].lstrip()) == indent), None)
    if end is None or end - k > 30:
        return text, 'fail:회사 그룹 끝 줄을 못 찾음'
    block = ''.join(lines[k - 1:end + 1])
    if not set(_labels(block)) <= SUPPORT_OR_ABOUT or block.count('<div') != block.count('</div>'):
        return text, 'fail:회사 그룹 안에 예상 밖 항목이 있음'
    return ''.join(lines[:k - 1] + lines[end + 1:]), 'ok'


MOBILE_COMPANY_RE = re.compile(r'<div[^>]*>[^<>]*회사</div>.*?(?=<div[^>]*>[^<>]*플레이하기</div>)', re.S)


def remove_company_mobile(text):
    m = MOBILE_COMPANY_RE.search(text)
    if not m:
        return text, 'none'
    block = m.group(0)
    if not set(_labels(block)) <= SUPPORT_OR_ABOUT or len(block) > 3000:
        return text, 'fail:모바일 회사 블록 안에 예상 밖 항목이 있음'
    return text[:m.start()] + text[m.end():], 'ok'


def add_fortune(text, desktop):
    """플레이하기의 상식테스트 바로 아래에 '운세' 항목을 추가한다(이미 있으면 그대로)."""
    pat_play = r'플레이하기 <svg' if desktop else r'플레이하기</div>'
    pat_next = r'(?:소통(?:·정보)?|약관·정책) <svg' if desktop else r'소통(?:·정보)?</div>'
    mp = re.search(pat_play, text)
    if not mp:
        return text, 'none'
    mn = re.compile(pat_next).search(text, mp.end())
    if not mn:
        return text, 'fail:플레이하기 다음 그룹을 못 찾음'
    seg = text[mp.start():mn.start()]
    if '>운세<' in seg:
        return text, 'ok'
    quiz = item_line(seg, '상식테스트')
    if not quiz:
        return text, 'fail:상식테스트 항목을 못 찾음'
    new = re.sub(r'href="[^"]*"', 'href="/fortune/"', quiz, count=1)
    new = re.sub(r'onclick="[^"]*"\s*', '', new, count=1)
    new = new.replace('>상식테스트<', '>운세<', 1)
    new_seg = seg.replace(quiz, quiz + new, 1)
    return text[:mp.start()] + new_seg + text[mn.start():], 'ok'


CTA_RE = re.compile(
    r'(?:[ \t]*<!--[^\n]*-->[ \t]*\n)?'                       # 위에 붙은 주석(있으면)
    r'[ \t]*<(a|button)\b(?:(?!</\1>).)*?</\1>\s*'              # PC용 '🔮 오늘의 운세' 버튼
    r'<(a|button)\b[^>]*aria-label="오늘의 운세"[^>]*>.*?</\2>[ \t]*\n?',   # 모바일용 🔮 아이콘
    re.S)


def remove_fortune_cta(text):
    def repl(m):
        desktop_el = m.group(0).split('aria-label="오늘의 운세"')[0]
        return '' if ('오늘의 운세' in desktop_el and ('🔮' in desktop_el or 'U0001F52E' in desktop_el)) else m.group(0)
    new = CTA_RE.sub(repl, text)
    return new, ('ok' if new != text or 'aria-label="오늘의 운세"' not in text else 'fail:운세 버튼을 못 찾음')


def process_stage_b(text):
    notes = []
    for fn in (remove_company_desktop, remove_company_mobile):
        text, st = fn(text)
        notes.append(fn.__name__ + ':' + st)
    for desktop in (True, False):
        text, st = add_fortune(text, desktop)
        notes.append(('데스크톱' if desktop else '모바일') + ' 운세:' + st)
    text, st = remove_fortune_cta(text)
    notes.append('운세버튼:' + st)
    return text, notes


def main():
    dry = '--dry' in sys.argv
    changed, skipped, failed, untouched = [], [], [], 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(('.html', '.py')) or fn in SKIP_FILES:
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, ROOT)
            try:
                with open(path, encoding='utf-8', newline='') as fp:
                    original = fp.read()
            except (UnicodeDecodeError, OSError):
                continue
            if '플레이하기' not in original or '소통' not in original:
                untouched += 1
                continue
            text, notes = original, []
            active = '꿈해몽 사전' if rel.replace(os.sep, '/').endswith('dream/index.html') else None
            for desktop in (True, False):
                text, st = process(text, desktop, active)
                notes.append(('데스크톱' if desktop else '모바일') + ':' + st)
            text, notes_b = process_stage_b(text)
            notes += notes_b
            bad = [n for n in notes if 'fail' in n]
            if bad:
                failed.append((rel, bad))
            if text != original:
                changed.append(rel)
                if not dry:
                    with open(path, 'w', encoding='utf-8', newline='') as fp:
                        fp.write(text)
            elif not bad:
                skipped.append(rel)
    print('고친 파일 %d개 / 이미 고쳐져 있거나 해당 없음 %d개 / 확인 필요 %d개' % (len(changed), len(skipped), len(failed)))
    for r in changed:
        print('  고침:', r)
    for r, b in failed:
        print('  확인 필요:', r, b)
    if dry:
        print('(--dry: 실제 파일은 바꾸지 않았습니다)')


if __name__ == '__main__':
    main()
