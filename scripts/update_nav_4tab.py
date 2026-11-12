#!/usr/bin/env python3
"""
네비게이션 4탭 구조로 일괄 변경
  Before: 플레이하기 / 소통·정보 / 약관·정책
  After : 아이랑 / 플레이하기 / 소통·정보 / 약관·정책

전략: g-nav-desktop 블록 전체와 game-mobile-menu 블록 전체를
      미리 만들어둔 완성본으로 통째 교체한다.
"""
import os, re, glob

# ── 완성된 데스크톱 nav 블록 ──────────────────────────────────────────────────
# <div id="g-nav-desktop" ...> ... </div> 전체

NEW_DESKTOP = '''\
<div id="g-nav-desktop" style="display:none;align-items:center;gap:2px">
                    <div style="position:relative" onmouseenter="this.querySelector('.g-dd-menu').style.opacity='1';this.querySelector('.g-dd-menu').style.visibility='visible'" onmouseleave="this.querySelector('.g-dd-menu').style.opacity='0';this.querySelector('.g-dd-menu').style.visibility='hidden'">
                        <button style="color:#64748b;font-weight:700;font-size:14px;display:flex;align-items:center;gap:4px;padding:4px 8px;background:none;border:none;cursor:pointer">🗺️ 아이랑 <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
                        <div class="g-dd-menu" style="position:absolute;left:0;top:100%;margin-top:8px;width:176px;background:#fff;border-radius:16px;box-shadow:0 20px 25px -5px rgba(0,0,0,.15);border:1px solid #f1f5f9;padding:8px 0;opacity:0;visibility:hidden;transition:opacity .2s,visibility .2s;z-index:50">
                            <a href="/festival/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">아이랑 나들이 지도</a>
                            <a href="/festival/worldcup.html" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">나들이 월드컵</a>
                            <a href="/festival/camping-worldcup.html" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">캠핑장 월드컵</a>
                            <a href="/festival/pick.html" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">오늘 어디 갈까?</a>
                            <a href="/festival/roulette.html" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">나들이·캠핑장·숲 룰렛</a>
                            <a href="/festival/poster.html" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">축제 포스터</a>
                        </div>
                    </div>
                    <div style="position:relative" onmouseenter="this.querySelector('.g-dd-menu').style.opacity='1';this.querySelector('.g-dd-menu').style.visibility='visible'" onmouseleave="this.querySelector('.g-dd-menu').style.opacity='0';this.querySelector('.g-dd-menu').style.visibility='hidden'">
                        <button style="color:#64748b;font-weight:700;font-size:14px;display:flex;align-items:center;gap:4px;padding:4px 8px;background:none;border:none;cursor:pointer">🎮 플레이하기 <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
                        <div class="g-dd-menu" style="position:absolute;left:0;top:100%;margin-top:8px;width:160px;background:#fff;border-radius:16px;box-shadow:0 20px 25px -5px rgba(0,0,0,.15);border:1px solid #f1f5f9;padding:8px 0;opacity:0;visibility:hidden;transition:opacity .2s,visibility .2s;z-index:50">
                            <a href="/game/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">전체게임</a>
                            <a href="/vote/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">익명투표</a>
                            <a href="/quiz/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">상식테스트</a>
                            <a href="/fortune/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">운세</a>
                        </div>
                    </div>
                    <div style="position:relative" onmouseenter="this.querySelector('.g-dd-menu').style.opacity='1';this.querySelector('.g-dd-menu').style.visibility='visible'" onmouseleave="this.querySelector('.g-dd-menu').style.opacity='0';this.querySelector('.g-dd-menu').style.visibility='hidden'">
                        <button style="color:#64748b;font-weight:700;font-size:14px;display:flex;align-items:center;gap:4px;padding:4px 8px;background:none;border:none;cursor:pointer">💬 소통·정보 <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
                        <div class="g-dd-menu" style="position:absolute;left:0;top:100%;margin-top:8px;width:176px;background:#fff;border-radius:16px;box-shadow:0 20px 25px -5px rgba(0,0,0,.15);border:1px solid #f1f5f9;padding:8px 0;opacity:0;visibility:hidden;transition:opacity .2s,visibility .2s;z-index:50">
                            <a href="/blog/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">커뮤니티</a>
                            <a href="/blog/magazine/" onclick="return true;" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">호호 매거진</a>
                            <a href="/guides/index.html" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">게임공략</a>
                            <a href="/dream/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">꿈해몽 사전</a>
                            <a href="/partner/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">파트너</a>
                        </div>
                    </div>
                    <div style="position:relative" onmouseenter="this.querySelector('.g-dd-menu').style.opacity='1';this.querySelector('.g-dd-menu').style.visibility='visible'" onmouseleave="this.querySelector('.g-dd-menu').style.opacity='0';this.querySelector('.g-dd-menu').style.visibility='hidden'">
                        <button style="color:#94a3b8;font-weight:700;font-size:14px;display:flex;align-items:center;gap:4px;padding:4px 8px;background:none;border:none;cursor:pointer">약관·정책 <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
                        <div class="g-dd-menu" style="position:absolute;right:0;top:100%;margin-top:8px;width:176px;background:#fff;border-radius:16px;box-shadow:0 20px 25px -5px rgba(0,0,0,.15);border:1px solid #f1f5f9;padding:8px 0;opacity:0;visibility:hidden;transition:opacity .2s,visibility .2s;z-index:50">
                            <a href="/terms/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">이용약관</a>
                            <a href="/privacy/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">개인정보처리방침</a>
                            <a href="/copyright/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">저작권·콘텐츠 정책</a>
                            <a href="/guide/" style="display:block;width:100%;box-sizing:border-box;text-align:left;padding:10px 16px;font-size:14px;font-weight:700;color:#475569;text-decoration:none">FAQ</a>
                        </div>
                    </div>
                </div>'''

# ── 완성된 모바일 메뉴 블록 ───────────────────────────────────────────────────
# <div id="game-mobile-menu" ...> ... </div> 전체

NEW_MOBILE = '''\
<div id="game-mobile-menu" style="display:none;border-top:1px solid #e2e8f0;box-shadow:0 10px 15px -3px rgba(0,0,0,.1);background:#fff">
            <div style="padding:16px;display:flex;flex-direction:column;gap:4px">
                <div style="font-size:12px;font-weight:700;color:#94a3b8;padding:8px 16px 2px">🗺️ 아이랑</div>
                <a href="/festival/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">아이랑 나들이 지도</a>
                <a href="/festival/worldcup.html" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">나들이 월드컵</a>
                <a href="/festival/camping-worldcup.html" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">캠핑장 월드컵</a>
                <a href="/festival/pick.html" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">오늘 어디 갈까?</a>
                <a href="/festival/roulette.html" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">나들이·캠핑장·숲 룰렛</a>
                <a href="/festival/poster.html" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">축제 포스터</a>
                <div style="border-top:1px solid #e2e8f0;margin:8px 0"></div>
                <div style="font-size:12px;font-weight:700;color:#94a3b8;padding:0 16px 2px">🎮 플레이하기</div>
                <a href="/game/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">전체게임</a>
                <a href="/vote/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">익명투표</a>
                <a href="/quiz/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">상식테스트</a>
                <a href="/fortune/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">운세</a>
                <div style="border-top:1px solid #e2e8f0;margin:8px 0"></div>
                <div style="font-size:12px;font-weight:700;color:#94a3b8;padding:0 16px 2px">💬 소통·정보</div>
                <a href="/blog/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">커뮤니티</a>
                <a href="/blog/magazine/" onclick="return true;" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">호호 매거진</a>
                <a href="/guides/index.html" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">게임공략</a>
                <a href="/dream/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">꿈해몽 사전</a>
                <a href="/partner/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#334155;text-decoration:none">파트너</a>
                <div style="border-top:1px solid #e2e8f0;margin:8px 0"></div>
                <a href="/terms/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#94a3b8;font-size:14px;text-decoration:none">이용약관</a>
                <a href="/privacy/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#94a3b8;font-size:14px;text-decoration:none">개인정보처리방침</a>
                <a href="/copyright/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#94a3b8;font-size:14px;text-decoration:none">저작권·콘텐츠 정책</a>
                <a href="/guide/" style="display:block;padding:12px 16px;border-radius:12px;font-weight:700;color:#94a3b8;font-size:14px;text-decoration:none">FAQ</a>
            </div>
        </div>'''

# ── 헬퍼: 중첩 div 끝 위치 찾기 ─────────────────────────────────────────────

def find_closing_div(html, start):
    """start 위치의 <div ...>에 대응하는 </div> 의 끝 인덱스를 반환"""
    depth = 0
    i = start
    while i < len(html):
        if html[i:i+4] == '<div':
            depth += 1
            i += 4
        elif html[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                return i + 6
            i += 6
        else:
            i += 1
    return -1

# ── 파일 순회 ─────────────────────────────────────────────────────────────────

SKIP_DIRS = {'.git', 'scripts', 'node_modules'}

def should_process(path):
    parts = set(path.replace('\\', '/').split('/'))
    return not parts & SKIP_DIRS

changed = 0
skipped = 0

for path in glob.glob('**/*.html', recursive=True):
    if not should_process(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        original = f.read()

    if 'id="g-nav-desktop"' not in original:
        skipped += 1
        continue

    updated = original

    # 1) 데스크톱 블록 교체
    desktop_start = updated.find('<div id="g-nav-desktop"')
    if desktop_start != -1:
        desktop_end = find_closing_div(updated, desktop_start)
        if desktop_end != -1:
            updated = updated[:desktop_start] + NEW_DESKTOP + updated[desktop_end:]

    # 2) 모바일 블록 교체
    mobile_start = updated.find('<div id="game-mobile-menu"')
    if mobile_start != -1:
        mobile_end = find_closing_div(updated, mobile_start)
        if mobile_end != -1:
            updated = updated[:mobile_start] + NEW_MOBILE + updated[mobile_end:]

    if updated != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(updated)
        print(f'  updated: {path}')
        changed += 1
    else:
        skipped += 1

print(f'\n완료: {changed}개 수정, {skipped}개 변경 없음')
