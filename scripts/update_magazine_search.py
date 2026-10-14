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
- url은 전부 "/blog/magazine/"로 통일한다. 이 BBS 구조(GitHub Issues 기반)는
  글 하나하나로 바로 연결되는 딥링크 URL이 없어서(= 클릭하면 안에서 목록을 보여주고
  글을 다시 눌러야 함) 지금은 "매거진 코너로 보내기"까지만 가능하다. 특정 글로
  바로 펄치는 딥링크를 원하면 /blog/magazine/ 페이지 쪽에 festival/index.html에서
  했던 것과 같은 방식의 URL 파라미터(예: ?post=123) 지원을 별도로 추가해야 한다.

사용법:
    python scripts/update_magazine_search.py
환경변수:
    GITHUB_TOKEN  - GitHub Actions에서 자동 주입되는 토큰(선택). 있으면 API
                    요청 한도가 늘어나고, 비공개 저장소에서도 동작한다.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error
import urllib.parse

GH_OWNER = "hohoplay"
GH_REPO = "hohoplaylab.com"
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
    token = os.environ.get("GITHUB_TOKEN")
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
            "url": "/blog/magazine/",
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
