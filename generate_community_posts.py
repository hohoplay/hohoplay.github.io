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
3. blog/index.html 안의 "최근 게시글" 정적 폴백 섹션을 최신 12개로 갱신한다
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

CATEGORIES = ["공지사항", "업데이트", "게임소개"]

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


def render_post_html(template, post):
    content_escaped = html_lib.escape(post["content"])
    excerpt = post["content"].strip().splitlines()[0][:80] if post["content"].strip() else post["title"]

    html_out = template
    html_out = html_out.replace("{{POST_ID}}", str(post["id"]))
    html_out = html_out.replace("{{CATEGORY}}", html_lib.escape(post["category"]))
    html_out = html_out.replace("{{TITLE}}", html_lib.escape(post["title"]))
    html_out = html_out.replace("{{AUTHOR}}", html_lib.escape(post["author"]))
    html_out = html_out.replace("{{DATE}}", format_date(post["created_at"]))
    html_out = html_out.replace("{{EXCERPT}}", html_lib.escape(excerpt))
    html_out = html_out.replace("{{CONTENT_HTML}}", content_escaped)
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


CATEGORY_COLORS = {
    "공지사항": ("#fee2e2", "#dc2626"),
    "업데이트": ("#dcfce7", "#16a34a"),
    "게임소개": ("#dbeafe", "#2563eb"),
}


def update_blog_index_static_list(posts):
    """blog/index.html 안의 '최근 게시글' 정적 폴백 섹션을 최신 12개로 갱신."""
    if not os.path.exists(BLOG_INDEX_PATH):
        print("⚠️ blog/index.html을 찾을 수 없어 정적 목록 갱신을 건너뜁니다.", file=sys.stderr)
        return

    html_content = open(BLOG_INDEX_PATH, encoding="utf-8").read()

    recent = posts[:12]
    items_html = ""
    for p in recent:
        bg, fg = CATEGORY_COLORS.get(p["category"], ("#f1f5f9", "#64748b"))
        title_escaped = html_lib.escape(p["title"])
        items_html += (
            f'<a href="/blog/posts/{p["id"]}.html" style="display:block;background:#f8fafc;'
            f'border:1px solid #e2e8f0;border-radius:14px;padding:14px 16px;text-decoration:none;color:inherit">'
            f'<span style="display:inline-block;font-size:11px;font-weight:800;padding:2px 8px;'
            f'border-radius:999px;background:{bg};color:{fg};margin-bottom:6px">{html_lib.escape(p["category"])}</span>'
            f'<div style="font-weight:800;font-size:14px;color:#1e293b">{title_escaped}</div>'
            f'</a>\n                        '
        )

    start_marker = "<!-- COMMUNITY_STATIC_LIST_START -->"
    end_marker = "<!-- COMMUNITY_STATIC_LIST_END -->"

    if start_marker not in html_content or end_marker not in html_content:
        print("⚠️ blog/index.html에서 정적 목록 마커를 찾지 못했습니다. 수동 확인이 필요합니다.", file=sys.stderr)
        return

    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    replacement = f"{start_marker}\n                        {items_html}{end_marker}"
    new_html = pattern.sub(replacement, html_content)

    with open(BLOG_INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"  ✓ blog/index.html 정적 목록 갱신 완료 ({len(recent)}개)")


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
    update_sitemap(posts)

    print(f"완료: 신규 {new_count}개, 삭제 {removed_count}개")


if __name__ == "__main__":
    main()
