#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
호호 매거진 글 목록을 가져와 data/encyclopedia_index.json 안의
"magazine-<글ID>" 검색 엔트리를 현재 글 목록 기준으로 통째로 다시 생성한다.

[중요] 데이터 소스 정정: 매거진 글은 GitHub Issues가 아니라, 커뮤니티 글쓰기
관리자 페이지(writer.html)가 직접 쓰는 Cloudflare Worker + D1 API
(WORKER_API, old-rain-16f7.lyh0929mm.workers.dev)에 저장된다. 처음엔
index.html의 loadIssues()/GH_OWNER/GH_REPO 코드를 보고 GitHub Issues라고
착각했는데, 그 저장소("hohoplay/hohoplaylab.com", 나중엔 "hohoplay.github.io"로도
시도)엔 "호호 매거진" 라벨 자체가 없었고(GitHub이 "Invalid value" 에러를 냄),
실제로는 저 Worker API가 진짜 데이터 소스였다. 아래 엔드포인트는 writer.html의
JS를 그대로 따라간 것:
  - GET  {WORKER_API}/posts         공개, 목록(아마 content 제외, 인증 불필요)
  - GET  {WORKER_API}/posts/{id}    공개, 글 하나 전체(content 포함, 인증 불필요)
  - POST/PUT/DELETE {WORKER_API}/admin/posts?key=...  관리자 전용(이 스크립트는 안 씀)

- 기존 수동으로 넣은 다른 항목들(festival-* 지역 엔트리, 게임/운세/코너 등)은
  절대 건드리지 않는다. "magazine-"로 시작하는 id만 지우고 새로 채운다.
- id는 글 자체의 id(=/blog/magazine/<id>.html 번호와 동일)라 제목이 수정돼도
  안정적으로 유지된다.
- "호호 매거진" 카테고리인 글만 쓴다 — 공지사항/업데이트/게임소개는 제외.
- searchText는 "글 제목 + 본문 앞부분 일부(최대 EXCERPT_LEN자)"를 쓴다. 본문은
  writer.html에서 이미 HTML로 변환해 저장해두므로, 태그/마크다운 기호를 벗겨내고
  순수 텍스트만 남긴다. 본문 전체를 다 넣지 않는 건, 글이 길어질수록 파일이
  계속 커지고 무관한 단어까지 섞여 검색 정확도가 떨어질 위험이 있어서다.
- url은 "/blog/magazine/<글ID>.html"로 딥링크한다(이 번호가 곧 커뮤니티 글
  자동 정적 페이지 동기화에서 쓰는 그 번호와 동일함을 직접 확인함: id=21 ==
  "슈퍼 마리오부터 쿠키런까지" 글, 공개 API 응답과 실제 페이지 둘 다 일치).
  단, 그 정적 페이지 동기화는 이 스크립트와는 별개의 자동화라서, 글이 막
  올라온 직후 아주 짧은 순간에는 정적 페이지가 아직 안 만들어져 있어 링크가
  404일 수 있다(보통 금방 따라잡힘).

[참고] 공지사항/업데이트/자유게시판 커뮤니티 게시판(index.html의
loadIssues()/openBoard())은 지금도 GitHub Issues API를 바라보고 있는데, 거기
쓰인 저장소 이름이 실제로 존재하는 저장소와 다른 것 같다(둘 다 404). 그쪽은
이 매거진 기능과는 별개의 코드/버그라 이 스크립트로는 안 건드렸다 — 필요하면
별도로 봐드릴 수 있다.

사용법:
    python scripts/update_magazine_search.py
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

WORKER_API = "https://old-rain-16f7.lyh0929mm.workers.dev"
CATEGORY = "호호 매거진"
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "encyclopedia_index.json")
ID_PREFIX = "magazine-"
EXCERPT_LEN = 200


def excerpt_from_body(content):
    """글 본문(HTML)에서 검색에 쓸 짧은 순수 텍스트만 뽑아낸다."""
    if not content:
        return ""
    text = content
    text = re.sub(r"<[^>]+>", " ", text)       # HTML 태그 제거
    text = re.sub(r"[#>*_`~]", " ", text)       # 혹시 남은 마크다운 기호 제거
    text = re.sub(r"&nbsp;|&amp;|&lt;|&gt;|&quot;|&#39;", " ", text)  # 흔한 HTML 엔티티 정리
    text = re.sub(r"\s+", " ", text).strip()
    return text[:EXCERPT_LEN]


def _get_json(url):
    # [FIX] 403 Forbidden 대응: Cloudflare가 Python urllib 기본 User-Agent
    # ("Python-urllib/3.x")를 봇으로 보고 막는 경우가 있어, 실제 브라우저가
    # writer.html에서 호출할 때와 비슷한 헤더(User-Agent/Origin/Referer)를 붙인다.
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Origin": "https://hohoplaylab.com",
        "Referer": "https://hohoplaylab.com/",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_magazine_posts():
    """공개 목록에서 '호호 매거진' 카테고리만 추려서, 각 글의 본문까지 채워 돌려준다."""
    data = _get_json(WORKER_API + "/posts?_=" + str(int(time.time())))
    posts = data.get("posts") or []
    magazine_posts = [p for p in posts if (p.get("category") or "") == CATEGORY]

    full_posts = []
    for p in magazine_posts:
        post_id = p.get("id")
        if post_id is None:
            continue
        try:
            detail = _get_json(WORKER_API + "/posts/" + str(post_id))
            full_posts.append(detail.get("post") or p)
        except Exception as e:
            sys.stderr.write("글 #%s 본문을 못 가져와 제목만 사용: %s\n" % (post_id, e))
            full_posts.append(p)
    return full_posts


def build_magazine_entries(posts):
    entries = []
    for p in posts:
        post_id = p.get("id")
        title = (p.get("title") or "").strip()
        if post_id is None or not title:
            continue
        excerpt = excerpt_from_body(p.get("content"))
        search_text = title if not excerpt else title + " " + excerpt
        entries.append({
            "id": ID_PREFIX + str(post_id),
            "type": "corner",
            "name": title,
            "genre": "매거진",
            "url": "/blog/magazine/%s.html" % post_id,
            "summary": "호호 매거진에 올라온 글이다.",
            "searchText": search_text,
        })
    return entries


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    kept = [item for item in data if not str(item.get("id", "")).startswith(ID_PREFIX)]

    try:
        posts = fetch_magazine_posts()
    except Exception as e:
        sys.stderr.write("매거진 글 목록을 가져오지 못해 기존 magazine-* 항목을 그대로 둔다: %s\n" % e)
        return

    new_entries = build_magazine_entries(posts)

    # 기존 통짜 "magazine" 코너 항목(/blog/magazine/ 전체보기) 바로 뒤에
    # 글별 항목들을 끼워 넣는다. 못 찾으면 맨 끝에 붙인다.
    out = []
    inserted = False
    for item in kept:
        out.append(item)
        if item.get("id") == "magazine":
            out.extend(new_entries)
            inserted = True
    if not inserted:
        out.extend(new_entries)

    if out == data:
        print("변경 없음 (magazine-* %d개, 동일)" % len(new_entries))
        return

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("magazine-* 항목 %d개로 갱신 완료" % len(new_entries))


if __name__ == "__main__":
    main()
