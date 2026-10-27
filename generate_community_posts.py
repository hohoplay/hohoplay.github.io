# -*- coding: utf-8 -*-
"""
generate_community_posts.py

Cloudflare Worker(D1 DB)에 저장된 커뮤니티 게시글(공지사항/업데이트/게임소개)을
불러와서, 게시글마다 진짜 정적 HTML 페이지(blog/posts/{id}.html)를 생성합니다.

GitHub Pages는 완전한 정적 호스팅이라 서버가 요청마다 새로 렌더링해줄 수 없기
때문에, 이 스크립트를 GitHub Actions로 주기적으로 돌려서 "빌드 타임에 미리
정적 페이지를 만들어두는" 방식으로 크롤러 노출 문제를 해결합니다.

이 스크립트가 하는 일:
1. Worker API에서 전체 게시글 목록 + 각 게시글 상세 내용을 가져온다
2. blog/posts/{id}.html 정적 페이지를 생성한다 (매 실행마다 전체 글을 항상 최신
   템플릿/공통 헤더로 다시 렌더링한다 — 게시글 '내용'은 등록 후 바뀌지 않지만, 상단
   메뉴 같은 공통 헤더나 템플릿은 나중에 바뀔 수 있어서, 그때도 이미 만들어진 과거
   글들이 자동으로 최신 상태를 따라가게 하기 위함. 내용이 실제로 안 바뀐 글은
   렌더링 결과도 바이트 단위로 동일해서 git에는 diff가 안 남는다. 삭제된 글은
   정리 단계에서 함께 제거)
3. blog/index.html 안의 "최근 게시글" 정적 폴백 섹션(HOHO PLAY BBS 패널 내부, BBS 톤으로
   스타일링됨)을 최신 12개로 갱신한다
4. sitemap.xml에 새로 생긴 게시글 URL을 추가한다 (중복 추가하지 않음)

실행 환경: GitHub Actions (Python 3.11+, requests 필요)
"""

import json
import os
import re
import sys
import html as html_lib
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

WORKER_API = "https://old-rain-16f7.lyh0929mm.workers.dev"
SITE_ROOT = "https://hohoplaylab.com"
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(REPO_ROOT, "blog", "posts")
TEMPLATE_PATH = os.path.join(REPO_ROOT, "templates", "community_post_template.html")
BLOG_INDEX_PATH = os.path.join(REPO_ROOT, "blog", "index.html")
# [ADD] 2026-10-19: footer.html에 "최신 소식"(공지사항·업데이트·호호 매거진 최신 3개) 칸을
# 추가하면서 생김. footer.html은 모든 페이지가 fetch('/footer.html')로 받아 그 자리에
# outerHTML로 통째로 갈아끼우는 "공용 조각 파일"이라, 자바스크립트로 그때그때 최신글을
# 불러오는 방식은 쓸 수 없다(outerHTML로 끼워 넣은 <script>는 브라우저가 실행해주지 않음 —
# innerHTML/outerHTML로 삽입된 스크립트는 원래 동작 안 하는 게 표준 동작이라, footer.html
# 맨 아래 있던 기존 footerNav() 스크립트도 사실 지금까지 전 페이지에서 똑같이 실행 안 되고
# 있었던 것으로 보임. 이 스크립트가 이미 매 실행마다 전체 글을 최신순으로 불러오고 있으므로,
# blog/index.html의 COMMUNITY_STATIC_LIST와 완전히 같은 방식 — 마커 사이를 매 실행마다
# 정적 HTML로 다시 채워 넣는 방식 — 으로 footer.html도 같이 최신화한다.
FOOTER_PATH = os.path.join(REPO_ROOT, "footer.html")
SITEMAP_PATH = os.path.join(REPO_ROOT, "sitemap.xml")

# [FIX] 2026-09-21: "호호 매거진" 카테고리가 이 목록에 없어서, 매거진 글들이
# blog/posts/{id}.html 정적 페이지도, sitemap.xml 등록도, blog/index.html
# 정적 폴백 목록 반영도 전혀 안 되고 있었음(Worker API 조회 자체가 카테고리별로
# 이 목록을 순회하는 방식이라, 목록에 없으면 애초에 안 불러와짐). "매거진 글도
# 커뮤니티 전체 목록에 섞여서 노출되는 게 의도"라는 기존 설계와도 어긋나던
# 상태라 추가함.
CATEGORIES = ["공지사항", "업데이트", "게임소개", "호호 매거진"]

# [ADD] 2026-10-06: 공지사항/업데이트는 운영 알림성 글로 보통 분량이 짧고 반복적이라,
# AdSense 품질 심사에서 "얇은 콘텐츠"로 잡히기 쉬움(실제로 blog/posts/2,3,4,6,17,18,19.html
# 7개가 이 문제로 수동으로 noindex 처리된 적 있음). 앞으로는 이 스크립트가 글을 생성하는
# 시점에 카테고리만 보고 자동으로 noindex를 넣어서, 매번 수동으로 찾아 고칠 필요가 없게 한다.
NOINDEX_CATEGORIES = {"공지사항", "업데이트"}

# [ADD] 2026-09-21: 매거진 카테고리 전체 글 목록을, ?board=magazine 같은
# 쿼리스트링이 아니라 실제 정적 파일이 있는 주소로도 제공하기 위해 추가.
# 이 슬러그는 한 번 정해지면 이후 매거진 글이 계속 늘어나도 파일 안의 목록
# 내용만 매 실행마다 최신화될 뿐, 주소(파일 경로) 자체는 절대 바뀌지 않는다.
# 공유 링크나 구글 색인이 계속 유효하게 쌓이도록 하기 위함.
#
# [FIX] 2026-09-21(같은 날 두 번째 수정): 처음엔 슬러그에 "만든 날짜"(260921)를
# 그대로 못박아 board-magazine-260921 로 만들었는데, 이러면 방문자가 사이트
# 메뉴로 "호호 매거진"을 클릭했을 때도 주소창에 이 날짜 붙은 기술적인 문자열이
# 그대로 보이게 된다 — 일반 방문자에게는 부자연스러움. 운영 첫날이라 색인/공유가
# 거의 없는 지금 시점에, 사람이 봐도 자연스러운 슬러그(magazine)로 교체한다.
# (참고: blog/index.html의 라이브 화면에서 쓰는 board slug 매핑도 이미
# BOARD_NAME_TO_SLUG = {'호호 매거진': 'magazine'} 로 되어 있어서 일치시킴.)
# 예전 주소(OLD_MAGAZINE_ARCHIVE_SLUG)로 들어오는 기존 링크/북마크/색인이
# 갑자기 404가 되지 않도록, build_magazine_archive_redirect()가 그 자리에
# 새 주소로 안내하는 정적 리다이렉트 페이지를 남겨둔다.
MAGAZINE_CATEGORY = "호호 매거진"
OLD_MAGAZINE_ARCHIVE_SLUG = "board-magazine-260921"
OLD_MAGAZINE_ARCHIVE_DIR = os.path.join(REPO_ROOT, "blog", OLD_MAGAZINE_ARCHIVE_SLUG)
OLD_MAGAZINE_ARCHIVE_URL = f"{SITE_ROOT}/blog/{OLD_MAGAZINE_ARCHIVE_SLUG}/"

MAGAZINE_ARCHIVE_SLUG = "magazine"
MAGAZINE_ARCHIVE_DIR = os.path.join(REPO_ROOT, "blog", MAGAZINE_ARCHIVE_SLUG)
MAGAZINE_ARCHIVE_URL = f"{SITE_ROOT}/blog/{MAGAZINE_ARCHIVE_SLUG}/"

# [ADD] 2026-09-21: "매거진 페이지도 상단메뉴·푸터가 있어야 다른 페이지랑 어울려
# 보인다"는 지적을 반영. index.html/footer.html에 있는 실제 헤더·푸터 마크업을
# 그대로 가져오되, 이 페이지는 index.html의 SPA(navigateTo)가 아니라 /blog/magazine/
# 라는 독립된 정적 파일이라는 점만 다르게 처리한다:
#  - about/guide/blog/terms/privacy/copyright/fortune 은 index.html의 navigateTo()에서도
#    이미 "진짜 폴더 주소로 이동"하는 REAL_URL_PAGES라, 그냥 <a href="/xxx/">로 바로 연결.
#  - '파트너'만 index.html 안에서 fetch로 불러오는 SPA 전용 화면이라 실제 폴더 주소가
#    없음 — index.html의 다른 정적 페이지(footer.html 등)에서 쓰는 것과 같은 방식으로,
#    sessionStorage에 표시해두고 루트(index.html)로 보내면 index.html이 열리자마자
#    자동으로 그 화면을 띄워준다(index.html의 renderInitialPage()가 이미 지원).
#  - 문의(Contact)는 index.html의 모달(openInquiryModal)까지 통째로 가져오면 무거워지니,
#    같은 목적지인 메일 링크로 단순화.
#  - 이 페이지는 /blog/<슬러그>/ 처럼 루트에서 한 단계 더 들어간 위치라 상대경로
#    "index.html"이 아니라 반드시 절대경로 "/index.html"로 이동해야 한다(안 그러면
#    /blog/magazine/index.html 자기 자신으로 되돌아가버림).
SITE_HEADER_HTML = """<nav class="bg-white/80 backdrop-blur-md border-b sticky top-0 z-50 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-20 items-center">
            <a href="/" class="flex items-center gap-3">
                <div class="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center text-white font-black shadow-indigo-200 shadow-xl" style="font-size:13px;letter-spacing:-0.5px;line-height:1">HOHO<br>PLAY</div>
                <span class="text-2xl font-black tracking-tighter uppercase"><span class="text-indigo-600">HOHO</span><span class="text-violet-500"> PLAY</span></span>
            </a>
            <div class="hidden md:flex space-x-2 items-center">
                <div class="relative group">
                    <button class="text-slate-600 hover:text-indigo-600 font-bold transition text-sm flex items-center gap-1 px-2 py-1">\U0001F3AE 플레이하기 <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
                    <div class="absolute left-0 top-full mt-2 w-40 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                        <a href="/game/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">전체게임</a>
                        <a href="/vote/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">익명투표</a>
                        <a href="/quiz/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">상식테스트</a>
                        <a href="/fortune/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">운세</a>
                    </div>
                </div>
                <div class="relative group">
                    <button class="text-slate-600 hover:text-indigo-600 font-bold transition text-sm flex items-center gap-1 px-2 py-1">\U0001F4AC 소통·정보 <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
                    <div class="absolute left-0 top-full mt-2 w-44 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                        <a href="/blog/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">커뮤니티</a>
                        <a href="/blog/magazine/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-indigo-600 bg-indigo-50 transition">호호 매거진</a>
                        <a href="/festival/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">아이랑 나들이 지도</a>
                        <a href="/festival/worldcup.html" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">나들이 월드컵</a>
                        <a href="/festival/camping-worldcup.html" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">캠핑장 월드컵</a>
                        <a href="/guides/index.html" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">게임공략</a>
                        <a href="/dream/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">꿈해몽 사전</a>
                        <a href="#" onclick="goPartner();return false;" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">파트너</a>
                    </div>
                </div>
                <div class="relative group">
                    <button class="text-slate-400 hover:text-slate-600 font-bold transition text-sm flex items-center gap-1 px-2 py-1">약관·정책 <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
                    <div class="absolute right-0 top-full mt-2 w-44 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                        <a href="/terms/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">이용약관</a>
                        <a href="/privacy/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">개인정보처리방침</a>
                        <a href="/copyright/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">저작권·콘텐츠 정책</a>
                        <a href="/guide/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">FAQ</a>
                    </div>
                </div>
            </div>
            <div class="flex items-center gap-2 sm:gap-3">
                <button id="menu-btn" onclick="toggleMenu()" class="md:hidden flex flex-col justify-center items-center w-10 h-10 gap-1.5 rounded-xl hover:bg-slate-100 transition">
                    <span id="bar1" class="block w-6 h-0.5 bg-slate-700 transition-all duration-300"></span>
                    <span id="bar2" class="block w-6 h-0.5 bg-slate-700 transition-all duration-300"></span>
                    <span id="bar3" class="block w-6 h-0.5 bg-slate-700 transition-all duration-300"></span>
                </button>
            </div>
        </div>
    </div>
    <div id="mobile-menu" class="hidden md:hidden bg-white border-t shadow-lg">
        <div class="px-4 py-4 space-y-1">
            <div class="text-xs font-bold text-slate-400 px-4 pt-1 pb-1">\U0001F3AE 플레이하기</div>
            <a href="/game/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">전체게임</a>
            <a href="/vote/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">익명투표</a>
            <a href="/quiz/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">상식테스트</a>
            <a href="/fortune/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">운세</a>
            <div class="border-t my-2"></div>
            <div class="text-xs font-bold text-slate-400 px-4 pt-1 pb-1">\U0001F4AC 소통·정보</div>
            <a href="/blog/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">커뮤니티</a>
            <a href="/blog/magazine/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-indigo-600 bg-indigo-50 transition">호호 매거진</a>
            <a href="/festival/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">아이랑 나들이 지도</a>
            <a href="/festival/worldcup.html" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">나들이 월드컵</a>
            <a href="/festival/camping-worldcup.html" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">캠핑장 월드컵</a>
            <a href="/guides/index.html" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">게임공략</a>
            <a href="/dream/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">꿈해몽 사전</a>
            <a href="#" onclick="goPartner();return false;" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">파트너</a>
            <div class="border-t my-2"></div>
            <a href="/terms/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition text-sm">이용약관</a>
            <a href="/privacy/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition text-sm">개인정보처리방침</a>
            <a href="/copyright/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition text-sm">저작권·콘텐츠 정책</a>
            <a href="/guide/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition text-sm">FAQ</a>
        </div>
    </div>
</nav>
<div id="menu-overlay" onclick="toggleMenu()" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;z-index:40;background:rgba(0,0,0,0.3);"></div>"""

SITE_FOOTER_HTML = """<footer class="bg-slate-900 text-slate-400 py-16">
    <div class="max-w-7xl mx-auto px-4 grid grid-cols-1 md:grid-cols-3 gap-12 text-center md:text-left">
        <div class="col-span-1 md:col-span-2">
            <h4 class="font-black text-2xl mb-6 uppercase tracking-wider"><span class="text-indigo-400">HOHO</span><span class="text-violet-400"> PLAY</span></h4>
            <p class="text-lg leading-relaxed mb-6">로그인 없이 즉기는 무한한 즉거움, HOHO PLAY은 웹 표준 기술을 이용한 고성능 브라우저 게임 플랫폼입니다.</p>
            <p class="text-sm text-slate-500 mb-6">개인 운영 서비스 · Since 2026 · 문의: <a href="mailto:lyh0929mm@gmail.com" class="hover:text-white transition">lyh0929mm@gmail.com</a></p>
            <div class="flex justify-center md:justify-start gap-4">
                <a href="https://www.threads.com/@hohoplay.io" target="_blank" rel="noopener noreferrer" aria-label="HOHO PLAY 쓰레드" class="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center hover:bg-slate-600 transition cursor-pointer text-white">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 192 192"><path d="M141.537 88.988a66.667 66.667 0 0 0-2.518-1.143c-1.482-27.307-16.403-42.94-41.457-43.1h-.34c-14.986 0-27.449 6.396-35.12 18.036l13.779 9.452c5.73-8.695 14.724-10.548 21.348-10.548h.229c8.249.053 14.474 2.452 18.503 7.129 2.932 3.405 4.893 8.111 5.864 14.05-7.314-1.243-15.224-1.626-23.68-1.14-23.82 1.371-39.134 15.264-38.105 34.568.522 9.792 5.4 18.216 13.735 23.719 7.047 4.652 16.124 6.927 25.557 6.412 12.458-.683 22.231-5.436 29.049-14.127 5.178-6.6 8.452-15.153 9.899-25.93 5.937 3.583 10.337 8.298 12.767 13.966 4.132 9.635 4.373 25.468-8.546 38.376-11.319 11.308-24.925 16.2-45.488 16.351-22.809-.169-40.06-7.484-51.275-21.741C35.232 139.966 29.522 120.682 29.3 96c.222-24.682 5.932-43.966 16.981-57.317C57.496 24.425 74.747 17.11 97.556 16.94c22.976.17 40.56 7.52 52.256 21.845 5.75 7.09 10.093 16.016 12.94 26.402l16.345-4.363c-3.43-12.682-8.856-23.716-16.232-32.927C147.036 9.972 125.202.195 97.688 0h-.384C69.866.195 48.284 10.012 33.536 29.19 20.395 46.081 13.528 69.513 13.301 95.932L13.3 96v.068c.228 26.419 7.095 49.851 20.236 66.742 14.748 19.178 36.33 28.995 64.112 29.19h.384c24.737-.173 42.135-6.662 56.416-20.931 18.459-18.423 18.131-40.974 11.97-55.049-4.598-10.724-13.263-19.5-25.881-25.032zm-37.45 44.31c-10.458.588-21.286-5.192-21.82-14.121-.392-6.872 4.89-14.536 20.683-15.468 1.807-.104 3.583-.155 5.328-.155 6.195 0 11.988.601 17.286 1.748-1.968 24.48-11.151 27.435-21.477 27.996z"/></svg>
                </a>
                <a href="https://www.instagram.com/hohoplay.io" target="_blank" rel="noopener noreferrer" aria-label="HOHO PLAY 인스타그램" class="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center hover:bg-pink-600 transition cursor-pointer text-white">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 1.366.062 2.633.334 3.608 1.308.975.975 1.246 2.242 1.308 3.608.058 1.266.07 1.646.07 4.851s-.012 3.584-.07 4.85c-.062 1.366-.334 2.633-1.308 3.608-.975.975-2.242 1.246-3.608 1.308-1.266.058-1.646.07-4.85.07s-3.584-.012-4.85-.07c-1.366-.062-2.633-.334-3.608-1.308-.975-.975-1.246-2.242-1.308-3.608C2.175 15.584 2.163 15.204 2.163 12s.012-3.584.07-4.85c.062-1.366.334-2.633 1.308-3.608.975-.975 2.242-1.246 3.608-1.308C8.416 2.175 8.796 2.163 12 2.163zm0-2.163C8.741 0 8.332.014 7.052.072 5.197.157 3.355.673 2.014 2.014.673 3.355.157 5.197.072 7.052.014 8.332 0 8.741 0 12c0 3.259.014 3.668.072 4.948.085 1.855.601 3.697 1.942 5.038 1.341 1.341 3.183 1.857 5.038 1.942C8.332 23.986 8.741 24 12 24s3.668-.014 4.948-.072c1.855-.085 3.697-.601 5.038-1.942 1.341-1.341 1.857-3.183 1.942-5.038.058-1.28.072-1.689.072-4.948s-.014-3.668-.072-4.948c-.085-1.855-.601-3.697-1.942-5.038C20.645.673 18.803.157 16.948.072 15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zm0 10.162a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/></svg>
                </a>
                <a href="https://www.youtube.com/@HOHOPLAY2026" target="_blank" rel="noopener noreferrer" aria-label="HOHO PLAY 유튜브" class="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center hover:bg-red-600 transition cursor-pointer text-white">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>
                </a>
                <a href="https://naver.me/GXFVLneY" target="_blank" rel="noopener noreferrer" aria-label="HOHO PLAY 네이버클립" class="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center hover:bg-green-600 transition cursor-pointer text-white">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7L8 5z"/></svg>
                </a>
                <a href="https://blog.naver.com/hohologtv/" target="_blank" rel="noopener noreferrer" aria-label="HOHO PLAY 네이버블로그" class="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center hover:bg-green-600 transition cursor-pointer text-white">
                    <span style="font-weight:900;font-size:16px;line-height:1">N</span>
                </a>
            </div>
        </div>
        <div>
            <h4 class="text-white font-bold mb-4">고객 센터</h4>
            <p class="text-sm">이메일: <a href="mailto:lyh0929mm@gmail.com" class="hover:text-white transition">lyh0929mm@gmail.com</a></p>
        </div>
    </div>
    <div class="max-w-7xl mx-auto px-4 mt-16 pt-8 border-t border-slate-800 text-center text-sm font-medium tracking-wide">
        <div class="flex flex-wrap justify-center gap-x-6 gap-y-2 mb-4 text-slate-500">
            <a href="/terms/" class="hover:text-white transition">이용약관</a>
            <span>·</span>
            <a href="/about/" class="hover:text-white transition">소개</a>
            <span>·</span>
            <a href="/privacy/" class="hover:text-white transition font-bold text-slate-300">개인정보처리방침</a>
            <span>·</span>
            <a href="/copyright/" class="hover:text-white transition">저작권·콘텐츠 정책</a>
            <span>·</span>
            <a href="mailto:lyh0929mm@gmail.com" class="hover:text-white transition">문의</a>
        </div>
        &copy; 2026 HOHO PLAY. All rights reserved.
    </div>
</footer>
<script>
function toggleMenu() {
    var menu = document.getElementById('mobile-menu');
    var overlay = document.getElementById('menu-overlay');
    var bar1 = document.getElementById('bar1');
    var bar2 = document.getElementById('bar2');
    var bar3 = document.getElementById('bar3');
    var isOpen = !menu.classList.contains('hidden');
    if (isOpen) {
        menu.classList.add('hidden');
        if (overlay) overlay.style.display = 'none';
        bar1.style.transform = '';
        bar2.style.opacity = '1';
        bar3.style.transform = '';
    } else {
        menu.classList.remove('hidden');
        if (overlay) overlay.style.display = 'block';
        bar1.style.transform = 'translateY(8px) rotate(45deg)';
        bar2.style.opacity = '0';
        bar3.style.transform = 'translateY(-8px) rotate(-45deg)';
    }
}
function goPartner() {
    location.href = '/partner/';
}
</script>"""

KST = timezone(timedelta(hours=9))


# [ADD] 2026-09-21: "매거진 글 개별 주소도 /blog/posts/{id}.html이 아니라
# /blog/magazine/{id}.html 처럼 매거진 밑에 있어야 하지 않냐"는 요청을 반영.
# 카테고리에 따라 글이 저장되는 폴더·주소가 갈라진다: 매거진 글은
# blog/magazine/{id}.html, 그 외(공지사항/업데이트/게임소개)는 기존과 동일하게
# blog/posts/{id}.html. 한 글의 카테고리가 나중에 바뀔 수도 있으므로(writer.html
# 수정 기능), generate_post_pages()는 "지금 카테고리 기준 정답 위치"에 없으면 새로
# 만들고, "틀린(예전) 위치"에 파일이 남아있으면 정리한다 — 그래야 카테고리를
# 매거진 ↔ 다른 카테고리로 바꿔도 주소가 계속 맞게 따라간다.
def post_output_dir(post):
    return MAGAZINE_ARCHIVE_DIR if post.get("category") == MAGAZINE_CATEGORY else POSTS_DIR


def post_output_rel(post):
    """로그·설명용 상대 경로 문자열 (예: 'blog/magazine/10.html')."""
    slug = MAGAZINE_ARCHIVE_SLUG if post.get("category") == MAGAZINE_CATEGORY else "posts"
    return f"blog/{slug}/{post['id']}.html"


def post_output_url(post):
    """사이트맵·canonical 등에 쓰는 전체 URL."""
    slug = MAGAZINE_ARCHIVE_SLUG if post.get("category") == MAGAZINE_CATEGORY else "posts"
    return f"{SITE_ROOT}/blog/{slug}/{post['id']}.html"


def fetch_json(url):
    import urllib.request
    # Cloudflare가 기본 파이썬 User-Agent(Python-urllib/x.x)를 자동으로 봇 요청으로
    # 인식해 403으로 차단하는 경우가 있어, 일반 브라우저처럼 보이는 User-Agent를 명시함.
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))


def fetch_all_posts():
    """카테고리별로 목록을 가져와 하나로 합친다 (id 기준 중복 제거).

    [FIX] 2026-10-16: "호호 매거진" 카테고리 글(id 35)이 Worker DB엔 정상 저장돼
    있는데도 blog/magazine/35.html이 끝내 생성되지 않고 /blog/magazine/ 목록에도
    안 뜨는 사고가 있었다. 원인을 역산해보니, 이 run의 "전체 게시글 N개 확인" 숫자가
    정확히 공지사항+업데이트+게임소개 카테고리 글 수의 합과 일치했다 — "호호 매거진"
    카테고리만 이 fetch에서 실패했는데도 아래 except가 그냥 ⚠️ 경고만 stderr에 찍고
    조용히 continue해버려서, 그 카테고리 글 전체가 통째로 빠진 채 "신규 0개"로
    정상 종료된 것처럼 보였다(로그를 한 줄 한 줄 다 펼쳐보지 않으면 못 알아챔).
    더 나쁜 건, current_ids에서 그 카테고리 글이 통째로 빠지면 바로 아래
    generate_post_pages()의 "삭제된 글 정리" 로직이 "서버에서 삭제된 글"로 오인해서
    이미 있던 정적 페이지까지 지워버릴 수 있다는 점 — 한 번의 일시적 네트워크
    실패가 멀쩡한 글들을 통째로 날려버릴 수 있는 구조였다.
    그래서: (1) 요청 하나가 실패하면 짧게 몇 번 재시도하고, (2) 그래도 끝내 실패하면
    조용히 넘어가지 않고 Actions를 확실하게 빨간 실패로 띄운다 — 일시적 네트워크
    문제라면 다음 재실행(또는 다음 자동 스케줄)에서 정상적으로 전체가 다시 반영되고,
    "일부만 가져온 채로 계속 진행"하는 일은 없게 한다.
    """
    import time

    seen = {}
    failed_categories = []
    for cat in CATEGORIES:
        url = f"{WORKER_API}/posts?category={quote(cat)}"
        data = None
        last_err = None
        for attempt in range(3):
            try:
                data = fetch_json(url)
                break
            except Exception as e:
                last_err = e
                if attempt < 2:
                    time.sleep(2)
        if data is None:
            print(f"::error::{cat} 목록 조회 실패(3회 재시도 후에도 실패): {last_err}", file=sys.stderr)
            failed_categories.append(cat)
            continue
        for p in data.get("posts", []):
            seen[p["id"]] = p

    if failed_categories:
        print(
            "::error::일부 카테고리 조회가 끝내 실패해 전체 게시글 목록이 불완전합니다 "
            f"({', '.join(failed_categories)}). 이 상태로 계속 진행하면 해당 카테고리의 "
            "기존 정적 페이지가 '삭제된 글'로 오인되어 지워질 위험이 있어 여기서 중단합니다. "
            "— 다시 실행(workflow_dispatch)하거나 다음 자동 스케줄을 기다려주세요."
        )
        sys.exit(1)

    # 최신순 정렬
    return sorted(seen.values(), key=lambda p: p["created_at"], reverse=True)


def fetch_post_detail(post_id):
    url = f"{WORKER_API}/posts/{post_id}"
    data = fetch_json(url)
    return data.get("post")


def format_date(ms_timestamp):
    dt = datetime.fromtimestamp(ms_timestamp / 1000, tz=KST)
    return dt.strftime("%Y.%m.%d")


_TAG_RE = re.compile(r"<[^>]+>")


# [ADD] 2026-10-17: 매거진 목록 페이지에 글마다 3줄 미리보기를 보여달라는 요청으로
# 추가. render_post_html()이 메타 설명용으로 앞 80자만 쓰던 것과 같은 방식(태그
# 제거 + 공백 정리)이지만, 여기선 화면에 직접 보여주는 미리보기라 더 넉넉히 자른다.
# 실제 "3줄"은 글자 수가 아니라 화면 폭에 따라 달라지므로, 여기서는 3줄을 채우고도
# 남을 만큼만(200자) 잘라서 넘기고 정확히 3줄로 자르는 건 CSS(-webkit-line-clamp:3)에
# 맡긴다.
def plain_text_excerpt(content, length=200):
    plain = re.sub(r"\s+", " ", _TAG_RE.sub("", content or "")).strip()
    return plain[:length]


# ───────────────────────────────────────────────────────────────────────────
# [ADD] 2026-10-27: 호호 매거진 글 하단 "함께 보면 좋은 페이지" 박스.
# 매거진 글 본문에는 게임·운세·나들이로 넘어가는 링크가 없어서(메뉴 제외) 색인되는 페이지끼리
# 서로 이어지지 않았다. 글 주제에 맞는 공략/운세/꿈해몽/나들이/다른 매거진 글 링크를 글 하단에
# 자동으로 붙인다. 이 생성기가 3시간마다 모든 글을 다시 렌더링하므로, 기존 글에도 자동 반영된다.
#  - 글 id별로 직접 정한 목록(MAGAZINE_RELATED_MAP)이 있으면 그걸 쓰고,
#  - 새로 올린 글(목록에 없는 id)은 제목 키워드로 자동 선택(_related_keys_by_title)한다.
#  - "m:숫자"는 다른 매거진 글(이번 실행에 실제로 존재하는 글만 표시, 자기 자신은 제외).
#  - 링크 대상은 전부 색인되는 페이지(공략·운세·꿈해몽·나들이·소개·개인정보)로만 구성.
# ───────────────────────────────────────────────────────────────────────────
RELATED_LINK_CATALOG = {
    "g_rpg":     ("game", "/guides/hoya-typing-rpg-guide.html", "호호타자RPG 공략", "웨이브당 비석 16개와 보스 타수 계산, 성장 카드 우선순위와 코인 사용 기준을 정리한 공략입니다."),
    "g_proverb": ("game", "/guides/hoya-proverb-typing-guide.html", "호호속담 공략", "10라운드 점수식과 길이별 라운드 전략, 연습 루틴을 담은 공략입니다."),
    "g_cherry":  ("game", "/guides/hoho-cherry-blossom-typing-guide.html", "호호벚꽃타자 공략", "SHIELD 3칸을 지키는 방법과 CHAIN 10 피버, 보스 보너스 계산을 다룬 공략입니다."),
    "g_fps":     ("game", "/guides/hoho-typing-fps-guide.html", "호호타자FPS 공략", "CHAIN 배율별 점수표와 보스 등장 점수 일정, 코어 보스 처리 순서를 정리한 공략입니다."),
    "g_racing":  ("game", "/guides/hoho-racing-guide.html", "호호레이싱 공략", "점수 구간별 차선 확장과 트럭 경고 대응, 체력·방패 관리법을 담은 공략입니다."),
    "g_run":     ("game", "/guides/hoho-run-guide.html", "HOHO RUN 공략", "높이 구간별 장애물과 화염구, 상점 비용과 부활 티켓 사용 시점을 정리한 공략입니다."),
    "g_tile":    ("game", "/guides/hoho-tile-match-guide.html", "호호사천성 공략", "AI 단계별 속도와 공격 비용, 통찰·결계재편 사용 기준을 계산한 공략입니다."),
    "g_jelly":   ("game", "/guides/jelly-pop-7-guide.html", "JELLY POP 7 공략", "조합 개수별 젤리당 점수와 CHAIN CAST 사이클, 2인 대결 요령을 다룬 공략입니다."),
    "g_dash":    ("game", "/guides/hoho-dash-guide.html", "HOHO DASH 공략", "거리 구간별 STAGE 변화와 아이템 판단 기준, 상점 업그레이드 순서를 정리한 공략입니다."),
    "g_dungeon": ("game", "/guides/word-puzzle-dungeon-guide.html", "낱말퍼즐 던전 공략", "풀이 5단계 순서와 교차 칸으로 후보를 거르는 법, 힌트를 쓸 위치를 설명한 공략입니다."),
    "hub":       ("game", "/guides/index.html", "게임공략 모음", "호호플레이 게임 10종의 완벽 공략을 한곳에 모은 목록입니다."),
    "mini":      ("game", "/guides/minigames-guide.html", "미니게임 10종 공략", "사다리·동전 던지기부터 두더지 잡기까지 미니게임 10종의 공략을 한 페이지에 모았습니다."),
    "game":      ("game", "/game/", "전체 게임", "설치·가입 없이 무료로 즐기는 호호플레이 게임 모음입니다."),
    "fortune":   ("fortune", "/fortune/", "오늘의 운세 · 타로 · MBTI", "오늘의 운세와 타로, MBTI 조합 풀이를 무료로 볼 수 있습니다."),
    "dream":     ("fortune", "/dream/", "꿈해몽 사전", "키워드로 찾아보는 꿈해몽 사전입니다."),
    "festival":  ("kids", "/festival/", "아이랑 나들이 지도", "전국 축제와 아이랑 가볼 만한 곳을 지도에서 찾아보세요."),
    "about":     ("info", "/about/", "호호플레이 소개", "호호플레이가 어떤 서비스인지 소개합니다."),
    "privacy":   ("info", "/privacy/", "개인정보처리방침", "호호플레이가 어떤 정보를 어떻게 다루는지 확인할 수 있습니다."),
}
RELATED_KIND_LABEL = {
    "game": "🎮 게임", "fortune": "🔮 운세", "kids": "🎪 아이랑 나들이",
    "mag": "📖 호호 매거진", "info": "ℹ️ 안내",
}
MAGAZINE_RELATED_MAP = {
    10: ["hub", "game", "m:35", "m:11"],
    11: ["hub", "game", "m:10", "mini"],
    12: ["g_rpg", "hub", "m:11"],
    13: ["g_rpg", "g_cherry", "g_fps", "g_proverb"],
    14: ["g_racing", "g_dash", "m:21", "game"],
    15: ["g_run", "g_dash", "m:21", "m:10"],
    16: ["g_tile", "g_jelly", "m:20", "hub"],
    20: ["g_jelly", "g_tile", "g_dungeon", "m:22"],
    21: ["g_dash", "g_run", "m:15", "m:14"],
    22: ["g_dungeon", "g_jelly", "m:20", "hub"],
    23: ["g_cherry", "g_fps", "m:13", "game"],
    24: ["g_rpg", "g_dash", "m:15", "game"],
    27: ["fortune", "m:29", "m:28", "dream"],
    28: ["dream", "fortune", "m:31", "m:27"],
    29: ["fortune", "m:27", "m:28", "m:37"],
    30: ["fortune", "m:32", "m:41", "dream"],
    31: ["dream", "fortune", "m:32", "m:28"],
    32: ["fortune", "m:41", "m:30", "m:31"],
    34: ["about", "hub", "fortune", "festival"],
    35: ["game", "hub", "mini", "m:38"],
    36: ["festival", "m:39", "game", "fortune"],
    37: ["fortune", "m:29", "m:28", "m:32"],
    38: ["g_cherry", "g_jelly", "mini", "m:35"],
    39: ["festival", "m:36", "game"],
    40: ["privacy", "about", "m:34", "game"],
    41: ["fortune", "m:32", "m:30", "dream"],
}
RELATED_BOX_MAX = 4


def _related_keys_by_title(title):
    """목록(MAGAZINE_RELATED_MAP)에 없는 새 매거진 글: 제목 키워드로 관련 링크를 고른다."""
    t = title or ""
    keys = []

    def add(*ks):
        for k in ks:
            if k not in keys:
                keys.append(k)

    if "꿈" in t:
        add("dream", "fortune")
    if any(w in t for w in ("운세", "사주", "궁합", "타로", "MBTI", "mbti", "별자리")):
        add("fortune")
    if any(w in t for w in ("나들이", "축제", "아이와", "아이랑", "육아", "체험")):
        add("festival")
    if "레이싱" in t:
        add("g_racing")
    if "사천성" in t or "마작" in t:
        add("g_tile")
    if "타자" in t or "타이핑" in t:
        add("g_rpg", "g_cherry", "g_fps", "g_proverb")
    if "낱말" in t or "십자말" in t:
        add("g_dungeon")
    if any(w in t for w in ("숫자 퍼즐", "2048", "스도쿠")):
        add("g_jelly")
    if any(w in t for w in ("러닝", "달리기", "점프", "플랫폼")):
        add("g_dash", "g_run")
    if any(w in t for w in ("개인정보", "프라이버시", "쿠키")):
        add("privacy")
    if any(w in t for w in ("미니게임", "사다리", "룰렛", "주사위")):
        add("mini")
    # 어떤 키워드도 안 맞으면 사이트 전체를 이어주는 기본 묶음
    if not keys:
        add("hub", "game", "fortune", "festival")
    else:
        add("hub", "game")
    return keys


def build_related_box_html(post, magazine_titles):
    """호호 매거진 글 하단 '함께 보면 좋은 페이지' 박스 HTML. 매거진이 아니면 빈 문자열."""
    if post.get("category") != MAGAZINE_CATEGORY:
        return ""
    pid = post.get("id")
    keys = MAGAZINE_RELATED_MAP.get(pid)
    if keys is None:
        keys = _related_keys_by_title(post.get("title", ""))
    items = []
    for k in keys:
        if k.startswith("m:"):
            try:
                mid = int(k[2:])
            except ValueError:
                continue
            if mid == pid or mid not in magazine_titles:
                continue  # 자기 자신이거나 이번 실행에 없는(삭제된) 글은 건너뜀
            items.append(("mag", f"/blog/{MAGAZINE_ARCHIVE_SLUG}/{mid}.html",
                          magazine_titles[mid], "호호 매거진의 관련 글입니다."))
        elif k in RELATED_LINK_CATALOG:
            items.append(RELATED_LINK_CATALOG[k])
    items = items[:RELATED_BOX_MAX]
    if not items:
        return ""
    rows = []
    for kind, href, title, desc in items:
        rows.append(
            f'<a href="{html_lib.escape(href)}" style="display:block;padding:12px 14px;border:1px solid #e2e8f0;'
            f'border-radius:12px;background:#f8fafc;text-decoration:none">'
            f'<span style="display:inline-block;font-size:11px;font-weight:800;color:#4f46e5;background:#eef2ff;'
            f'padding:2px 9px;border-radius:999px">{RELATED_KIND_LABEL[kind]}</span>'
            f'<div style="font-size:14px;font-weight:800;color:#1e293b;margin-top:6px;line-height:1.45;word-break:keep-all">{html_lib.escape(title)}</div>'
            f'<div style="font-size:12.5px;color:#64748b;margin-top:2px;line-height:1.55;word-break:keep-all">{html_lib.escape(desc)}</div>'
            f'</a>'
        )
    return (
        '<aside aria-label="함께 보면 좋은 페이지" style="margin-top:36px;padding:18px;border:1px solid #e2e8f0;'
        'border-radius:16px;background:#fff">'
        '<div style="font-size:15px;font-weight:900;color:#1e293b;margin-bottom:12px">🔗 함께 보면 좋은 페이지</div>'
        '<div style="display:grid;gap:10px">' + "".join(rows) + '</div></aside>'
    )


def render_post_html(template, post, magazine_titles=None):
    # [FIX] 2026-09-21: post["content"]를 html_lib.escape()로 감싸고 있었음 — writer.html이
    # 실제 <h1>/<h2>/<p>/<ul><li>/<strong> 등 진짜 HTML 태그로 저장한 본문을 여기서 다시
    # 이스케이프하면, 브라우저에는 제목·문단·목록이 아니라 "<h1>...</h1>" 글자가 그대로
    # 노출된다(실제로 blog/posts/10.html에서 이 증상이 확인됨). blog/index.html의 실시간
    # 화면(viewCommunityPost)은 이미 예전에 같은 이유로 이스케이프를 제거했는데, 정적 페이지를
    # 만드는 이 함수는 그때 같이 안 고쳐져 있었음. writer.html은 관리자 키로 보호된 대표님
    # 전용 도구라 공개 사용자가 임의로 글을 못 올리므로, 여기서도 이스케이프 없이 그대로
    # HTML로 해석해서 넣는다.
    content_html = post["content"]

    # excerpt(메타 설명 등에 쓰임)는 원래 raw content의 첫 줄을 그대로 잘라 썼는데, 그 줄이
    # "<h1>...</h1>" 같은 태그째로 시작하는 경우가 많아 메타 설명에 "&lt;h1&gt;..."이 그대로
    # 노출되는 문제가 있었음 — 태그를 먼저 제거하고, 문단 사이 줄바꿈도 공백 하나로 합친
    # 순수 텍스트에서 잘라낸다(줄바꿈을 안 합치면 자른 80자 안에 실제 개행문자가 섞여
    # <meta ... content="..."> 속성값 한 줄이 깨지는 문제가 있었음).
    plain_text = re.sub(r"\s+", " ", _TAG_RE.sub("", post["content"])).strip()
    excerpt = plain_text[:80] if plain_text else post["title"]

    html_out = template
    html_out = html_out.replace("{{POST_ID}}", str(post["id"]))
    html_out = html_out.replace("{{CATEGORY}}", html_lib.escape(post["category"]))
    html_out = html_out.replace("{{TITLE}}", html_lib.escape(post["title"]))
    html_out = html_out.replace("{{AUTHOR}}", html_lib.escape(post["author"]))
    html_out = html_out.replace("{{DATE}}", format_date(post["created_at"]))
    html_out = html_out.replace("{{EXCERPT}}", html_lib.escape(excerpt))
    html_out = html_out.replace("{{CONTENT_HTML}}", content_html)
    # [ADD] 2026-10-27: 매거진 글 하단 관련 링크 박스(템플릿의 {{RELATED_HTML}} 자리, 매거진 외 카테고리는 빈 문자열)
    html_out = html_out.replace("{{RELATED_HTML}}", build_related_box_html(post, magazine_titles or {}))
    # [ADD] 2026-09-21: 글 카테고리에 따라 실제 파일 위치(주소)가 blog/posts/ 또는
    # blog/magazine/ 로 갈라지게 되어, 템플릿이 canonical/og:url 태그에 쓸 수 있도록
    # 이 글의 "진짜 전체 주소"를 넘겨준다. (템플릿에 {{POST_URL}}이 없으면 그냥
    # 무시되니 안전함 — 아직 실제 템플릿 파일을 못 받아서, 있다면 이걸로 채워질
    # 자리를 미리 준비만 해둔 것.)
    html_out = html_out.replace("{{POST_URL}}", post_output_url(post))

    # [ADD] 2026-10-06: 공지사항/업데이트 글은 생성 시점에 canonical 태그 바로 다음 줄에
    # noindex 메타 태그를 자동으로 끼워넣는다. follow는 유지해서(noindex,follow) 검색엔진이
    # 이 페이지 자체는 색인하지 않지만, 페이지 안의 다른 링크(다른 글, 메뉴 등)는 계속
    # 따라가게 한다. canonical 줄을 못 찾으면(템플릿 변경 등) 조용히 건너뛰지 않고 로그를
    # 남겨서 Actions 화면에서 바로 알 수 있게 한다.
    if post.get("category") in NOINDEX_CATEGORIES:
        # [ADD] 2026-10-27: 색인에서 뺀 짧은 글(공지·업데이트)에는 애드센스 로더도 넣지 않는다
        # ("가치가 별로 없는 콘텐츠" 대응 — 본문이 짧은 페이지에 광고 코드가 있으면 불리).
        html_out = re.sub(
            r'[ \t]*<script\b[^>]*pagead2\.googlesyndication\.com/pagead/js/adsbygoogle\.js[^>]*>\s*</script>[ \t]*\n?',
            "",
            html_out,
        )
        canonical_line = f'<link rel="canonical" href="{post_output_url(post)}">'
        if canonical_line in html_out:
            html_out = html_out.replace(
                canonical_line,
                canonical_line + '\n    <meta name="robots" content="noindex,follow">',
                1,
            )
        else:
            print(
                f"⚠️ {post['id']}: canonical 태그를 못 찾아 noindex를 추가하지 못했습니다 (템플릿 확인 필요).",
                file=sys.stderr,
            )

    return html_out


def generate_post_pages(posts):
    os.makedirs(POSTS_DIR, exist_ok=True)
    os.makedirs(MAGAZINE_ARCHIVE_DIR, exist_ok=True)
    template = open(TEMPLATE_PATH, encoding="utf-8").read()

    def collect_ids(directory):
        ids = set()
        if not os.path.isdir(directory):
            return ids
        for f in os.listdir(directory):
            if f == "index.html" or not f.endswith(".html"):
                continue  # index.html(아카이브 목록)이나 .html이 아닌 파일은 글 파일이 아니므로 제외
            stem = f[: -len(".html")]
            if stem.isdigit():
                ids.add(int(stem))
        return ids

    existing_posts_ids = collect_ids(POSTS_DIR)
    existing_magazine_ids = collect_ids(MAGAZINE_ARCHIVE_DIR)
    current_ids = {p["id"] for p in posts}

    new_count = 0
    updated_count = 0
    # [ADD] 2026-10-17: 매거진 목록 페이지(build_magazine_archive_page)에 보여줄
    # 3줄 미리보기용 — 어차피 아래에서 글마다 fetch_post_detail()로 본문을 이미
    # 받아오고 있어서, 매거진 목록을 만들 때 같은 본문을 또 fetch하지 않도록
    # 여기서 한 번만 받아온 걸 모아뒀다가 넘겨준다.
    post_excerpts = {}
    # [ADD] 2026-10-27: 매거진 글 하단 관련 링크 박스에서 쓰는 {id: 제목} (이번 실행에 실제 존재하는 매거진 글만)
    magazine_titles = {p["id"]: p["title"] for p in posts if p.get("category") == MAGAZINE_CATEGORY}
    for p in posts:
        target_dir = post_output_dir(p)
        target_path = os.path.join(target_dir, f"{p['id']}.html")
        # [ADD] 카테고리가 바뀐 글 처리: "지금 카테고리 기준으로는 틀린" 예전 위치에
        # 파일이 남아있으면(예: 매거진 → 다른 카테고리로 바뀌었는데 blog/magazine/에
        # 옛 파일이 남아있는 경우, 또는 그 반대) 지워서 주소가 카테고리를 계속
        # 따라가게 한다.
        other_dir = MAGAZINE_ARCHIVE_DIR if target_dir is POSTS_DIR else POSTS_DIR
        other_path = os.path.join(other_dir, f"{p['id']}.html")
        if os.path.exists(other_path):
            os.remove(other_path)
            other_rel = "blog/posts" if other_dir is POSTS_DIR else f"blog/{MAGAZINE_ARCHIVE_SLUG}"
            print(f"  - {other_rel}/{p['id']}.html 삭제 (카테고리 변경으로 주소 이동됨)")

        # [FIX] 2026-10-12: 예전에는 target_path가 이미 있으면 "게시글 내용은 불변"이란
        # 이유로 재생성을 아예 건너뛰었다. 하지만 글 '내용'은 안 바뀌어도 모든 글이
        # 공유하는 상단 메뉴(SITE_HEADER_HTML)나 템플릿 자체는 나중에 바뀔 수 있는데,
        # 그 경우 이미 만들어진 과거 글들은 영원히 그 시점의 옛날 메뉴를 보여주는 채로
        # 멈춰 있었다 — 실제로 상단 메뉴에 "아이랑 나들이 지도"/"꿈해몽 사전" 링크를
        # 나중에 추가했는데, blog/magazine/ 아카이브 목록(매번 다시 그려짐)에는
        # 반영됐지만 그 전에 이미 생성돼 있던 blog/magazine/27.html 같은 개별 글
        # 페이지에는 반영되지 않는 문제로 발견됨. 이제 매번 실행할 때마다 모든 글을
        # 항상 최신 템플릿/헤더로 다시 렌더링한다 — 글 내용이 실제로 그대로면 렌더링
        # 결과도 바이트 단위로 동일하므로 git 커밋에는 변화가 없고, 헤더/템플릿을
        # 고친 뒤 다음 자동 실행(3시간 주기) 때 기존 글들에도 자동으로 반영된다.
        was_existing = os.path.exists(target_path)
        detail = fetch_post_detail(p["id"])
        if not detail:
            continue
        post_excerpts[p["id"]] = plain_text_excerpt(detail.get("content", ""))
        html_out = render_post_html(template, detail, magazine_titles)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(html_out)
        if was_existing:
            updated_count += 1
        else:
            new_count += 1
            print(f"  + {post_output_rel(p)} 생성 ({detail['title']})")

    # 삭제된 게시글의 정적 파일 정리 (두 폴더 다 확인)
    removed_count = 0
    for rid in existing_posts_ids - current_ids:
        path = os.path.join(POSTS_DIR, f"{rid}.html")
        if os.path.exists(path):
            os.remove(path)
            removed_count += 1
            print(f"  - blog/posts/{rid}.html 삭제 (원본 게시글 삭제됨)")
    for rid in existing_magazine_ids - current_ids:
        path = os.path.join(MAGAZINE_ARCHIVE_DIR, f"{rid}.html")
        if os.path.exists(path):
            os.remove(path)
            removed_count += 1
            print(f"  - blog/{MAGAZINE_ARCHIVE_SLUG}/{rid}.html 삭제 (원본 게시글 삭제됨)")

    return new_count, removed_count, updated_count, post_excerpts


# 커뮤니티 페이지가 처음 열렸을 때 기본으로 보여주는 탭(= window.onload의 switchBoard 기본값과
# 반드시 일치시켜야, 정적 콘텐츠 → 자바스크립트 실시간 콘텐츠로 바뀔 때 내용이 안 튄다).
PAST_LIST_SIZE = 10  # 실시간 화면의 PAST_LIST_SIZE와 동일하게 맞춤
FOOTER_LATEST_SIZE = 3  # footer.html "최신 소식" 칸에 보여줄 개수


def update_blog_index_static_list(posts):
    """blog/index.html의 커뮤니티 피드 자리를 정적 텍스트로 채워 넣는다.

    실시간 화면과 완전히 같은 모양(카테고리 배지 → 최신 글 1개는 본문까지 통째로
    → 그 아래 지난 글 목록)으로 렌더링한다. 이건 자바스크립트가 데이터를 불러오기
    '전'에 이미 페이지 소스에 존재하는 정적 텍스트라, 크롤러가 자바스크립트 실행
    없이도 최신 글 본문을 그대로 읽을 수 있다. 자바스크립트가 로드되면 이 자리를
    같은 모양으로 다시 그려 넣으며 공유·댓글 UI를 덧붙인다(내용이 이미 같으므로
    화면이 튀지 않는다).
    """
    if not os.path.exists(BLOG_INDEX_PATH):
        print("⚠️ blog/index.html을 찾을 수 없어 정적 목록 갱신을 건너뜁니다.", file=sys.stderr)
        return

    html_content = open(BLOG_INDEX_PATH, encoding="utf-8").read()

    # [FIX] 2026-09-21: 커뮤니티 정적 목록(크롤러가 보는 첫 화면 + JS 로드 전 화면)에는
    # "호호 매거진" 글을 안 섞는다. 매거진은 /blog/magazine/ 라는 자기 전용 목록
    # 페이지가 따로 있어서, 여기 커뮤니티 목록에도 똑같이 섞여 나오면 같은 글이
    # 두 군데(커뮤니티의 짧은 미리보기 vs 매거진 전용 목록)에 다른 모습으로 중복
    # 노출된다는 지적을 반영. (blog/index.html의 실시간 화면 쪽 getBoardFilteredPosts()도
    # 같은 날 같은 이유로 동일하게 고쳐서, 정적 폴백 → 실시간 전환 시 내용이 안 튄다.)
    posts = [p for p in posts if p.get("category") != MAGAZINE_CATEGORY]

    if not posts:
        items_html = ""
    else:
        latest = posts[0]
        detail = fetch_post_detail(latest["id"])
        if detail:
            # [FIX] 2026-09-21: html_lib.escape()로 감싸고 있었음 — render_post_html()과 같은
            # 이유로, writer.html이 진짜 HTML 태그로 저장한 본문을 여기서 다시 이스케이프하면
            # blog/index.html 정적 폴백(크롤러가 보는 첫 화면)에 "<h1>...</h1>" 글자가 그대로
            # 노출된다. 실시간 화면(viewCommunityPost, blog/index.html 안의 JS)은 이미
            # 이스케이프 없이 post.content.replace(/\n/g,'<br>')만 쓰고 있으므로, 여기서도
            # 그것과 완전히 동일하게 맞춘다(정적 폴백 → JS 렌더링 전환 시 내용이 안 튀어야 함).
            content_html = detail["content"].replace("\n", "<br>")
            title_escaped = html_lib.escape(detail["title"])
            author_escaped = html_lib.escape(detail["author"])
            category_escaped = html_lib.escape(detail["category"])
            latest_html = (
                f'<span style="display:inline-block;background:#eef2ff;color:#4f46e5;'
                f'font-size:11px;font-weight:800;padding:4px 12px;border-radius:9999px;'
                f'margin-bottom:10px">{category_escaped}</span>'
                f'<h2 style="font-size:22px;font-weight:900;color:#1e293b;margin:8px 0 6px">{title_escaped}</h2>'
                f'<p style="color:#94a3b8;font-size:13px;margin-bottom:20px">'
                f'{author_escaped} · {format_date(detail["created_at"])}</p>'
                f'<div style="color:#334155;font-size:14px;line-height:1.9;margin-bottom:24px">'
                f'{content_html}</div>'
            )
        else:
            latest_html = ""

        past = posts[1:1 + PAST_LIST_SIZE]
        past_items = ""
        for p in past:
            p_title = html_lib.escape(p["title"])
            p_author = html_lib.escape(p["author"])
            p_category = html_lib.escape(p["category"])
            past_items += (
                f'<a href="/blog/posts/{p["id"]}.html" class="bbs-post" style="display:block;text-decoration:none">'
                f'<div class="bbs-post-title">{p_title}</div>'
                f'<div class="bbs-post-meta">'
                f'<span>{p_category}</span>'
                f'<span>{format_date(p["created_at"])}</span>'
                f'<span>👤 {p_author}</span>'
                f'</div>'
                f'</a>\n                                '
            )

        past_html = ""
        if past_items:
            past_html = (
                '<div style="margin-top:32px;padding-top:24px;border-top:1px solid #e2e8f0">'
                '<div style="font-size:12px;font-weight:900;color:#94a3b8;letter-spacing:.05em;'
                f'margin-bottom:12px">📋 지난 글</div>'
                f'<div>{past_items}</div>'
                '</div>'
            )

        items_html = latest_html + past_html

    start_marker = "<!-- COMMUNITY_STATIC_LIST_START -->"
    end_marker = "<!-- COMMUNITY_STATIC_LIST_END -->"

    count = html_content.count(start_marker)
    if count == 0:
        print("⚠️ blog/index.html에서 정적 목록 마커를 찾지 못했습니다. 수동 확인이 필요합니다.", file=sys.stderr)
        return

    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    replacement = f"{start_marker}\n                                {items_html}{end_marker}"
    new_html, n_subs = pattern.subn(replacement, html_content)

    with open(BLOG_INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)
    shown_count = (1 if posts else 0) + (len(past) if posts else 0)
    print(f"  ✓ blog/index.html 정적 목록 갱신 완료 (최신글+지난글 {shown_count}개, {n_subs}곳 반영)")


# [ADD] 2026-10-19: footer.html "최신 소식" 칸 — 공지사항/업데이트/호호 매거진을 합쳐서
# 최신 생성일순 3개만(게임소개는 제외) 보여준다. posts는 fetch_all_posts()가 이미
# created_at 기준 내림차순으로 정렬해서 넘겨주므로 필터링 후 앞에서 3개만 자르면 된다.
FOOTER_LATEST_CATEGORIES = {"공지사항", "업데이트", MAGAZINE_CATEGORY}

_CATEGORY_BADGE_COLOR = {
    "공지사항": "#f59e0b",
    "업데이트": "#4f46e5",
    MAGAZINE_CATEGORY: "#ec4899",
}


def update_footer_latest(posts):
    """footer.html의 FOOTER_LATEST_START~END 마커 사이를 최신글 3개로 갱신한다."""
    if not os.path.exists(FOOTER_PATH):
        print("⚠️ footer.html을 찾을 수 없어 최신 소식 갱신을 건너뜁니다.", file=sys.stderr)
        return

    html_content = open(FOOTER_PATH, encoding="utf-8").read()

    latest = [p for p in posts if p.get("category") in FOOTER_LATEST_CATEGORIES][:FOOTER_LATEST_SIZE]

    if not latest:
        items_html = '<li style="color:#64748b">아직 소식이 없습니다.</li>'
    else:
        items = []
        for p in latest:
            title = html_lib.escape(p["title"])
            category = html_lib.escape(p["category"])
            color = _CATEGORY_BADGE_COLOR.get(p["category"], "#94a3b8")
            url = post_output_url(p)
            items.append(
                '<li><a href="' + url + '" style="display:flex;align-items:baseline;gap:8px;'
                'text-decoration:none;overflow:hidden" class="hover:text-white transition">'
                '<span style="flex:none;font-size:11px;font-weight:800;color:' + color + '">'
                + category + '</span>'
                '<span style="font-size:13px;overflow:hidden;text-overflow:ellipsis;'
                'white-space:nowrap">' + title + '</span>'
                '</a></li>'
            )
        items_html = "".join(items)

    start_marker = "<!-- FOOTER_LATEST_START -->"
    end_marker = "<!-- FOOTER_LATEST_END -->"

    if start_marker not in html_content:
        print("⚠️ footer.html에서 최신 소식 마커를 찾지 못했습니다. 수동 확인이 필요합니다.", file=sys.stderr)
        return

    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    replacement = f"{start_marker}{items_html}{end_marker}"
    new_html, n_subs = pattern.subn(replacement, html_content)

    with open(FOOTER_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"  ✓ footer.html 최신 소식 갱신 완료 ({len(latest)}개, {n_subs}곳 반영)")


# [ADD] 2026-10-27: 매거진 "목록" 페이지(build_magazine_archive_page)는 /footer.html 을 불러오지 않아,
# footer.html 에 들어있는 모바일 햄버거 2열(compact) 스타일이 적용되지 않았다. update_nav_menu.py 가
# 이 파일에 직접 끼워 넣어도 이 페이지는 3시간마다 통째로 다시 써지기 때문에 매번 사라졌다
# (그래서 "호호 매거진 햄버거 메뉴만 안 바뀜"). 근본 해결로 이 생성기가 매번 같은 블록을 넣는다.
# footer.html 의 <style id="mm-compact"> 와 규칙이 같다(767px 이하에서만 적용). f-string 밖의 일반
# 문자열이라 CSS 중괄호를 그대로 쓴다.
MM_COMPACT_STYLE = """<style id="mm-compact">
  @media (max-width: 767px) {
    #mobile-menu > div, #game-mobile-menu > div { display: grid !important; grid-template-columns: 1fr 1fr; gap: 2px 8px !important; padding: 6px 14px 10px !important; }
    #mobile-menu > div > *, #game-mobile-menu > div > * { margin: 0 !important; min-width: 0; }
    #mobile-menu > div > div, #game-mobile-menu > div > div { grid-column: 1 / -1; }
    #mobile-menu > div > div.border-t, #game-mobile-menu > div > div[style*="border-top"] { margin: 4px 0 !important; }
    #mobile-menu a, #mobile-menu button, #game-mobile-menu a { padding: 9px 12px !important; line-height: 1.3 !important; font-size: 14px !important; }
  }
</style>
"""


def build_magazine_archive_page(posts, post_excerpts=None):
    """호호 매거진 카테고리 글 전체를 모은 정적 목록 페이지(blog/board-magazine-260921/index.html)를
    만든다. blog/posts/{id}.html(개별 글, 내용이 안 바뀌므로 이미 있으면 건드리지 않음)과 달리,
    이 페이지는 "목록"이라 새 매거진 글이 올라올 때마다 내용이 계속 바뀌어야 하므로 매 실행마다
    통째로 다시 써서 덮어쓴다. 파일 경로(=주소)는 MAGAZINE_ARCHIVE_SLUG로 고정되어 있어 안 바뀐다.

    post_excerpts: {post_id: 3줄 미리보기용 평문 일부} — generate_post_pages()가 각 글
    본문을 fetch하는 김에 함께 뽑아둔 걸 그대로 받는다(여기서 다시 fetch하지 않음).
    """
    os.makedirs(MAGAZINE_ARCHIVE_DIR, exist_ok=True)
    post_excerpts = post_excerpts or {}

    magazine_posts = [p for p in posts if p.get("category") == MAGAZINE_CATEGORY]
    magazine_posts.sort(key=lambda p: p["created_at"], reverse=True)

    if not magazine_posts:
        items_html = '<li class="empty">아직 등록된 호호 매거진 글이 없습니다.</li>'
    else:
        rows = []
        for p in magazine_posts:
            title = html_lib.escape(p["title"])
            author = html_lib.escape(p["author"])
            excerpt = html_lib.escape(post_excerpts.get(p["id"], ""))
            excerpt_html = f'<p class="post-excerpt">{excerpt}</p>' if excerpt else ""
            rows.append(
                f'<li><a class="post-item" href="/blog/{MAGAZINE_ARCHIVE_SLUG}/{p["id"]}.html">'
                f'<div class="post-title">{title}</div>'
                f'{excerpt_html}'
                f'<div class="post-meta"><span>{format_date(p["created_at"])}</span>'
                f'<span>👤 {author}</span></div>'
                f'</a></li>'
            )
        items_html = "\n".join(rows)

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<!-- [ADD] 2026-10-10: 애드센스 광고 코드가 개별 글(community_post_template.html)에는
     있는데 이 매거진 "목록" 페이지에는 빠져있었음 — 애드센스 품질 심사에서
     "광고 코드가 누락되었거나 불완전한 경우"로 잡힐 수 있어 개별 글과 동일하게 추가. -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-VGTXTM4R91"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-VGTXTM4R91');
</script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7990191075290055" crossorigin="anonymous"></script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>호호 매거진 - 호호플레이(HOHO PLAY) 커뮤니티</title>
<meta name="description" content="호호플레이(HOHO PLAY) 호호 매거진 게시글을 모아봅니다.">
<link rel="canonical" href="{MAGAZINE_ARCHIVE_URL}">
<meta property="og:title" content="호호 매거진 - 호호플레이(HOHO PLAY) 커뮤니티">
<meta property="og:description" content="호호플레이(HOHO PLAY) 호호 매거진 게시글을 모아봅니다.">
<meta property="og:url" content="{MAGAZINE_ARCHIVE_URL}">
<link rel="icon" href="/favicon.svg">
<script src="https://cdn.tailwindcss.com"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
body {{ font-family: 'Noto Sans KR', sans-serif; }}
.post-list {{ list-style: none; padding: 0; margin: 0; }}
.post-item {{ display: block; padding: 16px 0; border-bottom: 1px solid #f1f5f9; text-decoration: none; color: inherit; }}
.post-title {{ font-size: 16px; font-weight: 800; color: #1e293b; margin-bottom: 6px; }}
.post-excerpt {{
    font-size: 13px; color: #64748b; line-height: 1.5; margin: 0 0 8px;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}}
.post-meta {{ font-size: 12px; color: #94a3b8; }}
.post-meta span {{ margin-right: 10px; }}
.empty {{ color: #94a3b8; font-size: 14px; padding: 40px 0; text-align: center; list-style: none; }}
.back-link {{ display: inline-block; margin-top: 28px; color: #4f46e5; font-weight: 700; text-decoration: none; font-size: 14px; }}
</style>
{MM_COMPACT_STYLE}</head>
<body class="bg-slate-50 text-slate-900 min-h-screen flex flex-col">
{SITE_HEADER_HTML}
<main class="flex-grow max-w-3xl mx-auto w-full px-4 py-10">
<h1 style="font-size:1.6rem;font-weight:900;margin-bottom:6px">📖 호호 매거진</h1>
<p class="intro">호호플레이(HOHO PLAY)의 호호 매거진 게시글을 모아봅니다.</p>
<ul class="post-list">
{items_html}
</ul>
<a class="back-link" href="/blog/">← 커뮤니티 전체로 돌아가기</a>

<!-- [ADD] 2026-10-17: 게임공략 페이지 하단과 같은 방식으로 HOHO PICK을 붙인다.
     data-exclude="magazine"은 hoho-pick.html 쪽에서 "이 페이지가 이미 다루는
     섹션(호호 매거진)은 추천 목록에서 또 보여주지 않는다"는 뜻으로 읽는 값이다
     (게임공략 페이지가 data-exclude="guide"를 쓰는 것과 같은 패턴). -->
<div id="hoho-pick-placeholder" data-exclude="magazine" style="margin-top:24px;"></div>
<script>
(function(){{
    var ph = document.getElementById('hoho-pick-placeholder');
    if (!ph) return;
    fetch('/hoho-pick.html').then(function(r){{ return r.text(); }}).then(function(html){{
        ph.innerHTML = html;
        var scripts = ph.querySelectorAll('script');
        for (var i = 0; i < scripts.length; i++) {{
            var old = scripts[i];
            var s = document.createElement('script');
            for (var j = 0; j < old.attributes.length; j++) {{
                s.setAttribute(old.attributes[j].name, old.attributes[j].value);
            }}
            s.textContent = old.textContent;
            old.parentNode.replaceChild(s, old);
        }}
    }}).catch(function(){{}});
}})();
</script>
</main>
{SITE_FOOTER_HTML}
</body>
</html>"""

    out_path = os.path.join(MAGAZINE_ARCHIVE_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"  ✓ blog/{MAGAZINE_ARCHIVE_SLUG}/index.html 갱신 완료 (매거진 글 {len(magazine_posts)}개)")


def build_magazine_archive_redirect():
    """[ADD] 2026-09-21: 매거진 아카이브 슬러그를 board-magazine-260921 → magazine 으로
    바꾸면서, 예전 주소로 들어오는 기존 링크/북마크/검색 색인이 갑자기 404가 되지
    않도록 옛 주소 자리에 정적 리다이렉트 페이지를 남겨둔다. GitHub Pages는 정적
    호스팅이라 서버 단에서 진짜 301 리다이렉트를 걸 방법이 없으므로, 대신
    meta refresh(방문자용)와 canonical 태그(검색엔진용)로 "진짜 주소는 여기"라고
    알려주는 방식을 쓴다."""
    os.makedirs(OLD_MAGAZINE_ARCHIVE_DIR, exist_ok=True)
    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>호호 매거진 - 호호플레이(HOHO PLAY) 커뮤니티</title>
<link rel="canonical" href="{MAGAZINE_ARCHIVE_URL}">
<meta http-equiv="refresh" content="0; url={MAGAZINE_ARCHIVE_URL}">
<meta name="robots" content="noindex">
</head>
<body>
<p>이 페이지는 <a href="{MAGAZINE_ARCHIVE_URL}">{MAGAZINE_ARCHIVE_URL}</a>(으)로 주소가 바뀌었습니다.</p>
</body>
</html>"""
    out_path = os.path.join(OLD_MAGAZINE_ARCHIVE_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"  ✓ blog/{OLD_MAGAZINE_ARCHIVE_SLUG}/index.html → {MAGAZINE_ARCHIVE_URL} 리다이렉트 페이지 생성")


def _remove_sitemap_url(content, url):
    """sitemap.xml 문자열(content)에서 <loc>이 url인 <url>...</url> 블록 하나를 제거한다.
    없으면 그대로(변경 없음, removed=False) 돌려준다. 여러 마이그레이션(슬러그 변경,
    카테고리 변경에 따른 개별 글 주소 이동)에서 공통으로 쓰는 헬퍼."""
    if url not in content:
        return content, False
    pattern = re.compile(
        r"[ \t]*<url>\s*<loc>" + re.escape(url) + r"</loc>.*?</url>\n?",
        re.DOTALL,
    )
    new_content, n = pattern.subn("", content)
    return new_content, n > 0


def migrate_magazine_sitemap_entry():
    """[ADD] 2026-09-21: sitemap.xml에 이미 등록돼 있을 수 있는 예전 슬러그
    (board-magazine-260921) 항목을 제거한다. 새 슬러그(magazine) 등록은
    update_sitemap()이 기존 로직 그대로(MAGAZINE_ARCHIVE_URL 기준) 처리한다.
    이미 제거된 상태에서 다시 실행해도(멱등) 아무 일도 하지 않는다."""
    if not os.path.exists(SITEMAP_PATH):
        return
    content = open(SITEMAP_PATH, encoding="utf-8").read()
    new_content, removed = _remove_sitemap_url(content, OLD_MAGAZINE_ARCHIVE_URL)
    if removed:
        with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  ✓ sitemap.xml에서 예전 매거진 주소({OLD_MAGAZINE_ARCHIVE_URL}) 항목 제거")


def update_sitemap(posts):
    if not os.path.exists(SITEMAP_PATH):
        print("⚠️ sitemap.xml을 찾을 수 없어 건너뜁니다.", file=sys.stderr)
        return

    content = open(SITEMAP_PATH, encoding="utf-8").read()
    added = 0
    removed = 0

    for p in posts:
        url = post_output_url(p)
        # [ADD] 2026-09-21: 이 글이 예전엔(카테고리가 지금과 달라서) 다른 주소로
        # sitemap에 등록돼 있었을 수 있다 — 특히 매거진 글은 이번에 /blog/posts/{id}.html
        # → /blog/magazine/{id}.html 로 주소가 바뀌었으므로, 그 예전 주소가 남아있으면
        # 지운다. 카테고리가 안 바뀐 대다수 글은 old_url == url 이라 그냥 아무 일도 없다.
        old_url = f"{SITE_ROOT}/blog/posts/{p['id']}.html" if post_output_dir(p) is MAGAZINE_ARCHIVE_DIR else f"{SITE_ROOT}/blog/{MAGAZINE_ARCHIVE_SLUG}/{p['id']}.html"
        if old_url != url:
            content, did_remove = _remove_sitemap_url(content, old_url)
            if did_remove:
                removed += 1
                print(f"  ✓ sitemap.xml에서 예전 글 주소({old_url}) 항목 제거 → {url}")

        # [ADD] 2026-10-06: 공지사항/업데이트(noindex 대상)는 sitemap에 올리지 않는다.
        # 이미 올라가 있던 과거 항목(blog/posts/2,3,4,6,17,18,19.html 등 수동으로 noindex만
        # 처리하고 sitemap 정리는 미처 못했던 글들)도 다음 실행 때 자동으로 제거되어, 더
        # 이상 수동으로 sitemap을 손볼 필요가 없어진다.
        if p.get("category") in NOINDEX_CATEGORIES:
            content, did_remove = _remove_sitemap_url(content, url)
            if did_remove:
                removed += 1
                print(f"  ✓ sitemap.xml에서 비색인 대상 글 주소({url}) 제거 (category={p['category']})")
            continue

        if url in content:
            continue
        entry = (
            f"  <url>\n"
            f"    <loc>{url}</loc>\n"
            f"    <changefreq>monthly</changefreq>\n"
            f"    <priority>0.5</priority>\n"
            f"  </url>\n"
        )
        content = content.replace("</urlset>", entry + "</urlset>")
        added += 1

    # [ADD] 2026-09-21: 호호 매거진 목록 페이지(고정 주소) 등록. 이미 등록돼 있으면
    # (재실행 시) 위 게시글 URL과 동일한 패턴으로 중복 추가하지 않는다.
    if MAGAZINE_ARCHIVE_URL not in content:
        entry = (
            f"  <url>\n"
            f"    <loc>{MAGAZINE_ARCHIVE_URL}</loc>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>0.6</priority>\n"
            f"  </url>\n"
        )
        content = content.replace("</urlset>", entry + "</urlset>")
        added += 1

    if added > 0 or removed > 0:
        with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✓ sitemap.xml 갱신: {added}개 추가, {removed}개 예전 주소 제거")
    else:
        print("  · sitemap.xml 변경 없음 (신규 게시글 없음)")


def main():
    print("커뮤니티 게시글 동기화 시작...")
    posts = fetch_all_posts()
    print(f"전체 게시글 {len(posts)}개 확인")

    new_count, removed_count, updated_count, post_excerpts = generate_post_pages(posts)
    update_blog_index_static_list(posts)
    update_footer_latest(posts)
    build_magazine_archive_page(posts, post_excerpts)
    build_magazine_archive_redirect()
    migrate_magazine_sitemap_entry()
    update_sitemap(posts)

    print(f"완료: 신규 {new_count}개, 재렌더링 {updated_count}개(내용 그대로면 git diff 없음), 삭제 {removed_count}개")


if __name__ == "__main__":
    main()
