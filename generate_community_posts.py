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
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: 'Noto Sans KR', sans-serif; max-width: 720px; margin: 0 auto; padding: 24px 16px 60px; color: #1e293b; background: #fff; }}
h1 {{ font-size: 1.6rem; font-weight: 900; margin-bottom: 6px; }}
.intro {{ color: #64748b; font-size: 14px; margin-bottom: 24px; }}
.post-list {{ list-style: none; padding: 0; margin: 0; }}
.post-item {{ display: block; padding: 16px 0; border-bottom: 1px solid #f1f5f9; text-decoration: none; color: inherit; }}
.post-title {{ font-size: 16px; font-weight: 800; color: #1e293b; margin-bottom: 6px; }}
.post-meta {{ font-size: 12px; color: #94a3b8; }}
.post-meta span {{ margin-right: 10px; }}
.empty {{ color: #94a3b8; font-size: 14px; padding: 40px 0; text-align: center; list-style: none; }}
.back-link {{ display: inline-block; margin-top: 28px; color: #4f46e5; font-weight: 700; text-decoration: none; font-size: 14px; }}
</style>
</head>
<body>
<h1>📖 호호 매거진</h1>
<p class="intro">호호플레이(HOHO PLAY)의 호호 매거진 게시글을 모아봅니다.</p>
<ul class="post-list">
{items_html}
</ul>
<a class="back-link" href="/blog/">← 커뮤니티 전체로 돌아가기</a>
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
