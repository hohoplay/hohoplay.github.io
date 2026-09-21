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
2. blog/posts/{id}.html 정적 페이지를 생성한다 (없는 것만 새로 생성, 있는 것은 건드리지 않음
   — 게시글 내용은 등록 후 바뀌지 않는다는 전제. 삭제된 글은 정리 단계에서 함께 제거)
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
SITEMAP_PATH = os.path.join(REPO_ROOT, "sitemap.xml")

# [FIX] 2026-09-21: "호호 매거진" 카테고리가 이 목록에 없어서, 매거진 글들이
# blog/posts/{id}.html 정적 페이지도, sitemap.xml 등록도, blog/index.html
# 정적 폴백 목록 반영도 전혀 안 되고 있었음(Worker API 조회 자체가 카테고리별로
# 이 목록을 순회하는 방식이라, 목록에 없으면 애초에 안 불러와짐). "매거진 글도
# 커뮤니티 전체 목록에 섞여서 노출되는 게 의도"라는 기존 설계와도 어긋나던
# 상태라 추가함.
CATEGORIES = ["공지사항", "업데이트", "게임소개", "호호 매거진"]

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
                    <button class="text-slate-600 hover:text-indigo-600 font-bold transition text-sm flex items-center gap-1 px-2 py-1">\U0001F3E2 회사 <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
                    <div class="absolute left-0 top-full mt-2 w-36 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                        <a href="/about/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">소개</a>
                        <a href="/guide/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">고객지원</a>
                    </div>
                </div>
                <div class="relative group">
                    <button class="text-slate-600 hover:text-indigo-600 font-bold transition text-sm flex items-center gap-1 px-2 py-1">\U0001F3AE 플레이하기 <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
                    <div class="absolute left-0 top-full mt-2 w-40 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                        <a href="/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">전체게임</a>
                        <a href="/vote/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">익명투표</a>
                        <a href="/quiz/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">상식테스트</a>
                        <a href="/festival/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">축제 지도</a>
                        <a href="/guides/index.html" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">게임공략</a>
                    </div>
                </div>
                <div class="relative group">
                    <button class="text-slate-600 hover:text-indigo-600 font-bold transition text-sm flex items-center gap-1 px-2 py-1">\U0001F4AC 소통 <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
                    <div class="absolute left-0 top-full mt-2 w-36 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                        <a href="/blog/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">커뮤니티</a>
                        <a href="/blog/magazine/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-indigo-600 bg-indigo-50 transition">호호 매거진</a>
                        <a href="#" onclick="goPartner();return false;" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">파트너</a>
                    </div>
                </div>
                <div class="relative group">
                    <button class="text-slate-400 hover:text-slate-600 font-bold transition text-sm flex items-center gap-1 px-2 py-1">약관·정책 <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg></button>
                    <div class="absolute right-0 top-full mt-2 w-44 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
                        <a href="/terms/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">이용약관</a>
                        <a href="/privacy/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">개인정보처리방침</a>
                        <a href="/copyright/" class="block w-full text-left px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition">저작권·콘텐츠 정책</a>
                    </div>
                </div>
            </div>
            <div class="flex items-center gap-2 sm:gap-3">
                <a href="/fortune/" class="hidden md:flex items-center gap-1.5 bg-purple-100 hover:bg-purple-200 text-purple-700 font-bold text-sm px-4 py-2.5 rounded-full transition">
                    <span>\U0001F52E</span> 오늘의 운세
                </a>
                <a href="/fortune/" aria-label="오늘의 운세" class="md:hidden flex items-center justify-center w-10 h-10 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-full transition text-base">\U0001F52E</a>
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
            <div class="text-xs font-bold text-slate-400 px-4 pt-1 pb-1">\U0001F3E2 회사</div>
            <a href="/about/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">소개</a>
            <a href="/guide/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">고객지원</a>
            <div class="border-t my-2"></div><div class="text-xs font-bold text-slate-400 px-4 pt-1 pb-1">\U0001F3AE 플레이하기</div>
            <a href="/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">전체게임</a>
            <a href="/vote/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">익명투표</a>
            <a href="/quiz/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">상식테스트</a>
            <a href="/festival/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">축제 지도</a>
            <a href="/guides/index.html" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">게임공략</a>
            <div class="border-t my-2"></div>
            <div class="text-xs font-bold text-slate-400 px-4 pt-1 pb-1">\U0001F4AC 소통</div>
            <a href="/blog/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">커뮤니티</a>
            <a href="/blog/magazine/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-indigo-600 bg-indigo-50 transition">호호 매거진</a>
            <a href="#" onclick="goPartner();return false;" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 transition">파트너</a>
            <div class="border-t my-2"></div>
            <a href="/terms/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition text-sm">이용약관</a>
            <a href="/privacy/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition text-sm">개인정보처리방침</a>
            <a href="/copyright/" class="block w-full text-left px-4 py-3 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition text-sm">저작권·콘텐츠 정책</a>
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
    sessionStorage.setItem('page', 'partner');
    location.href = '/index.html';
}
</script>"""

KST = timezone(timedelta(hours=9))


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
    """카테고리별로 목록을 가져와 하나로 합친다 (id 기준 중복 제거)."""
    seen = {}
    for cat in CATEGORIES:
        url = f"{WORKER_API}/posts?category={quote(cat)}"
        try:
            data = fetch_json(url)
        except Exception as e:
            print(f"⚠️ {cat} 목록 조회 실패: {e}", file=sys.stderr)
            continue
        for p in data.get("posts", []):
            seen[p["id"]] = p
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


def render_post_html(template, post):
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
    return html_out


def generate_post_pages(posts):
    os.makedirs(POSTS_DIR, exist_ok=True)
    template = open(TEMPLATE_PATH, encoding="utf-8").read()

    existing_ids = {
        int(f.replace(".html", ""))
        for f in os.listdir(POSTS_DIR)
        if f.endswith(".html")
    }
    current_ids = {p["id"] for p in posts}

    new_count = 0
    for p in posts:
        path = os.path.join(POSTS_DIR, f"{p['id']}.html")
        if os.path.exists(path):
            continue  # 게시글 내용은 불변이므로 이미 있으면 재생성하지 않음
        detail = fetch_post_detail(p["id"])
        if not detail:
            continue
        html_out = render_post_html(template, detail)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_out)
        new_count += 1
        print(f"  + blog/posts/{p['id']}.html 생성 ({detail['title']})")

    # 삭제된 게시글의 정적 파일 정리
    removed_ids = existing_ids - current_ids
    removed_count = 0
    for rid in removed_ids:
        path = os.path.join(POSTS_DIR, f"{rid}.html")
        if os.path.exists(path):
            os.remove(path)
            removed_count += 1
            print(f"  - blog/posts/{rid}.html 삭제 (원본 게시글 삭제됨)")

    return new_count, removed_count


# 커뮤니티 페이지가 처음 열렸을 때 기본으로 보여주는 탭(= window.onload의 switchBoard 기본값과
# 반드시 일치시켜야, 정적 콘텐츠 → 자바스크립트 실시간 콘텐츠로 바뀔 때 내용이 안 튄다).
PAST_LIST_SIZE = 10  # 실시간 화면의 PAST_LIST_SIZE와 동일하게 맞춤


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


def build_magazine_archive_page(posts):
    """호호 매거진 카테고리 글 전체를 모은 정적 목록 페이지(blog/board-magazine-260921/index.html)를
    만든다. blog/posts/{id}.html(개별 글, 내용이 안 바뀌므로 이미 있으면 건드리지 않음)과 달리,
    이 페이지는 "목록"이라 새 매거진 글이 올라올 때마다 내용이 계속 바뀌어야 하므로 매 실행마다
    통째로 다시 써서 덮어쓴다. 파일 경로(=주소)는 MAGAZINE_ARCHIVE_SLUG로 고정되어 있어 안 바뀐다."""
    os.makedirs(MAGAZINE_ARCHIVE_DIR, exist_ok=True)

    magazine_posts = [p for p in posts if p.get("category") == MAGAZINE_CATEGORY]
    magazine_posts.sort(key=lambda p: p["created_at"], reverse=True)

    if not magazine_posts:
        items_html = '<li class="empty">아직 등록된 호호 매거진 글이 없습니다.</li>'
    else:
        rows = []
        for p in magazine_posts:
            title = html_lib.escape(p["title"])
            author = html_lib.escape(p["author"])
            rows.append(
                f'<li><a class="post-item" href="/blog/posts/{p["id"]}.html">'
                f'<div class="post-title">{title}</div>'
                f'<div class="post-meta"><span>{format_date(p["created_at"])}</span>'
                f'<span>👤 {author}</span></div>'
                f'</a></li>'
            )
        items_html = "\n".join(rows)

    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
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
.post-meta {{ font-size: 12px; color: #94a3b8; }}
.post-meta span {{ margin-right: 10px; }}
.empty {{ color: #94a3b8; font-size: 14px; padding: 40px 0; text-align: center; list-style: none; }}
.back-link {{ display: inline-block; margin-top: 28px; color: #4f46e5; font-weight: 700; text-decoration: none; font-size: 14px; }}
</style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen flex flex-col">
{SITE_HEADER_HTML}
<main class="flex-grow max-w-3xl mx-auto w-full px-4 py-10">
<h1 style="font-size:1.6rem;font-weight:900;margin-bottom:6px">📖 호호 매거진</h1>
<p class="intro">호호플레이(HOHO PLAY)의 호호 매거진 게시글을 모아봅니다.</p>
<ul class="post-list">
{items_html}
</ul>
<a class="back-link" href="/blog/">← 커뮤니티 전체로 돌아가기</a>
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


def migrate_magazine_sitemap_entry():
    """[ADD] 2026-09-21: sitemap.xml에 이미 등록돼 있을 수 있는 예전 슬러그
    (board-magazine-260921) 항목을 제거한다. 새 슬러그(magazine) 등록은
    update_sitemap()이 기존 로직 그대로(MAGAZINE_ARCHIVE_URL 기준) 처리한다.
    이미 제거된 상태에서 다시 실행해도(멱등) 아무 일도 하지 않는다."""
    if not os.path.exists(SITEMAP_PATH):
        return
    content = open(SITEMAP_PATH, encoding="utf-8").read()
    if OLD_MAGAZINE_ARCHIVE_URL not in content:
        return
    pattern = re.compile(
        r"[ \t]*<url>\s*<loc>" + re.escape(OLD_MAGAZINE_ARCHIVE_URL) + r"</loc>.*?</url>\n?",
        re.DOTALL,
    )
    new_content, n = pattern.subn("", content)
    if n > 0:
        with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"  ✓ sitemap.xml에서 예전 매거진 주소({OLD_MAGAZINE_ARCHIVE_URL}) 항목 제거")


def update_sitemap(posts):
    if not os.path.exists(SITEMAP_PATH):
        print("⚠️ sitemap.xml을 찾을 수 없어 건너뜁니다.", file=sys.stderr)
        return

    content = open(SITEMAP_PATH, encoding="utf-8").read()
    added = 0

    for p in posts:
        url = f"{SITE_ROOT}/blog/posts/{p['id']}.html"
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

    if added > 0:
        with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✓ sitemap.xml에 {added}개 URL 추가")
    else:
        print("  · sitemap.xml 변경 없음 (신규 게시글 없음)")


def main():
    print("커뮤니티 게시글 동기화 시작...")
    posts = fetch_all_posts()
    print(f"전체 게시글 {len(posts)}개 확인")

    new_count, removed_count = generate_post_pages(posts)
    update_blog_index_static_list(posts)
    build_magazine_archive_page(posts)
    build_magazine_archive_redirect()
    migrate_magazine_sitemap_entry()
    update_sitemap(posts)

    print(f"완료: 신규 {new_count}개, 삭제 {removed_count}개")


if __name__ == "__main__":
    main()
