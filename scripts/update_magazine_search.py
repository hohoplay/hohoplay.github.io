#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
호호 매거진(GitHub Issues, label="호호 매거진") 글 목록을 가져와
data/encyclopedia_index.json 안의 "magazine-<이슈번호>" 검색 엔트리를
현재 공개된(open) 글 목록 기준으로 통째로 다시 생성한다.

- 기존 수동으로 넣은 다른 항목들(festival-* 지역 엔트리, 게임/운세/코너 등)은
  절대 건드리지 않는다. "magazine-"로 시작하는 id만 지우고 새로 채운다.
- id는 이슈 번호 기반이라 제목이 수정돼도 안정적으로 유지된다.
- searchText는 "글 제목 + 본문 앞부분 일부(최대 EXCERPT_LEN자)"를 쓴다. 제목에
  없는 단어라도 본문 도입부에 나온 핵심 단어로 찾아지게 하기 위함이다(예:
  제목엔 "십자말풀이"가 없어도 본문 첫 문단에 나오면 그 단어로도 검색됨).
  본문 전체를 다 넣지 않는 건, 글이 길어질수록 파일이 계속 커지고 전혀
  무관한 단어까지 섞여 검색 정확도가 떨어질 위험이 있어서다.
- url은 "/blog/magazine/<이슈번호>.html"로 딥링크한다. 이 사이트엔 커뮤니티 글을
  이슈번호.html 정적 페이지로 자동 동기화해주는 별도 자동화가 이미 있어서
  (예: 이슈 #21 -> /blog/magazine/21.html = "슈퍼 마리오부터 쿠키런까지" 글),
  검색 결과를 누르면 목록이 아니라 그 글이 바로 뜬다. 단, 그 정적 페이지 동기화가
  이 스크립트와는 별개의 자동화라서, 이슈가 막 올라온 직후 아주 짧은 순간에는
  정적 페이지가 아직 안 만들어져 있어 링크가 404일 수 있다(보통 금방 따라잡힘).

사용법:
    python scripts/update_magazine_search.py
환경변수:
    MAGAZINE_REPO_TOKEN  - (선택) 이슈를 읽을 때 쓸 개인 액세스 토큰(PAT).
                           저장소가 공개(public)라 없어도 동작하며, 분당 요청
                           한도를 늘리고 싶을 때만 레포 Secrets에 추가해서 쓰면 된다.

※ GH_OWNER/GH_REPO 값에 대한 메모: 사이트 자체 JS(index.html)에는
GH_OWNER='hohoplay', GH_REPO='hohoplaylab.com'으로 박혀 있는데, 실제로 이
저장소 이름으로 GitHub API(repos/hohoplay/hohoplaylab.com/issues)를 호출하면
(인증 유무와 상관없이) 404가 난다 — 실제 커밋/정적 페이지 동기화가 일어나는
저장소는 GitHub 파일 탐색기 주소에 찍히는 "hohoplay.github.io"였다. 그래서
여기서는 GH_REPO를 "hohoplay.github.io"로 맞췄다. (참고: 그렇다면 사이트
자체 JS의 loadIssues()/openBoard() — 공지사항·업데이트·자유게시판을 눌렀을 때
뜨는 실시간 게시판 — 도 같은 이유로 조용히 실패하고 있을 가능성이 있다.
별개 사이트 버그라 이 스크립트로는 못 고치고, 확인해보려면 index.html의
GH_REPO 상수를 "hohoplay.github.io"로 바꿔야 할 수 있다.)

GitHub Actions가 자동으로 주입하는 기본 GITHUB_TOKEN은 "이 워크플로우가 돌고
있는 저장소"에만 쓸 수 있는 권한이라, 혹시라도 이슈가 다른 저장소에 있을
경우를 대비해 이슈를 읽을 때는 인증 헤더를 아예 안 보낸다(공개 저장소라
문제없음). 레포 자체에 커밋·푸시하는 쪽만 Actions가 주는 기본 토큰(별도
코드 없이 git push가 알아서 사용)을 쓴다.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
import urllib.parse

GH_OWNER = "hohoplay"
GH_REPO = "hohoplay.github.io"
LABEL = "호호 매거진"
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "encyclopedia_index.json")
ID_PREFIX = "magazine-"
EXCERPT_LEN = 200


def excerpt_from_body(body):
    """이슈 본문(마크다운)에서 검색에 쓸 짧은 텍스트만 뽑아낸다."""
    if not body:
        return ""
    text = body
    text = re.sub(r"```[\s\S]*?```", " ", text)          # 코드블록 제거
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)     # 마크다운 이미지 제거
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # 마크다운 링크 -> 글자만
    text = re.sub(r"<[^>]+>", " ", text)                   # HTML 태그 제거
    text = re.sub(r"[#>*_`~-]", " ", text)                 # 마크다운 기호 제거
    text = re.sub(r"\s+", " ", text).strip()
    return text[:EXCERPT_LEN]


def fetch_all_issues():
    # 주의: 여기서는 일부러 Actions의 GITHUB_TOKEN을 쓰지 않는다(위 docstring 참고).
    # 이슈가 있는 저장소를 읽을 전용 토큰이 따로 있을 때만 MAGAZINE_REPO_TOKEN으로 넣는다.
    token = os.environ.get("MAGAZINE_REPO_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = "Bearer " + token

    issues = []
    page = 1
    while True:
        qs = urllib.parse.urlencode({
            "labels": LABEL,
            "state": "open",
            "per_page": 100,
            "page": page,
            "sort": "created",
            "direction": "desc",
        })
        url = "https://api.github.com/repos/%s/%s/issues?%s" % (GH_OWNER, GH_REPO, qs)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            sys.stderr.write("GitHub API 요청 실패(HTTP %s): %s\n" % (e.code, e.read().decode("utf-8", "replace")))
            raise
        if not batch:
            break
        # Pull Request도 /issues 엔드포인트에 섞여 나올 수 있어 제외
        issues.extend([it for it in batch if "pull_request" not in it])
        if len(batch) < 100:
            break
        page += 1
    return issues


def build_magazine_entries(issues):
    entries = []
    for it in issues:
        number = it.get("number")
        title = (it.get("title") or "").strip()
        if not number or not title:
            continue
        excerpt = excerpt_from_body(it.get("body"))
        search_text = title if not excerpt else title + " " + excerpt
        entries.append({
            "id": ID_PREFIX + str(number),
            "type": "corner",
            "name": title,
            "genre": "매거진",
            "url": "/blog/magazine/%d.html" % number,
            "summary": "호호 매거진에 올라온 글이다.",
            "searchText": search_text,
        })
    return entries


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    kept = [item for item in data if not str(item.get("id", "")).startswith(ID_PREFIX)]

    try:
        issues = fetch_all_issues()
    except Exception as e:
        sys.stderr.write("매거진 글 목록을 가져오지 못해 기존 magazine-* 항목을 그대로 둔다: %s\n" % e)
        return

    new_entries = build_magazine_entries(issues)

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
