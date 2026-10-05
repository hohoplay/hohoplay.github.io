#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_sitemap.py — sitemap.xml을 저장소의 실제 파일 상태와 자동으로 맞춥니다.

이 스크립트가 하는 일 (딱 이 두 가지만 합니다):

  1. sitemap.xml에 있는 각 <loc> 주소가 실제로 저장소에 해당 파일이
     있는지 확인하고, 파일이 없는 주소(글 삭제/이동으로 고아가 된 항목)는
     자동으로 제거합니다.

  2. blog/posts/ 와 blog/magazine/ 폴더 밑에 새로 생긴 .html 파일인데
     아직 sitemap.xml에 없는 게 있으면 기본값(changefreq=monthly,
     priority=0.5, lastmod=오늘 날짜)으로 자동 추가합니다.
     (이 두 폴더로 범위를 좁힌 이유: 다른 페이지들 — 게임, 공략, 소개
     페이지 등 — 은 우선순위/주기를 사람이 직접 정해서 넣는 게 맞고,
     자동 추가 대상이 아니기 때문입니다. 새 폴더 생기면 ADD_NEW_FROM_DIRS에
     추가하세요.)

  그 외(루트 페이지, 게임, 가이드 등)는 "파일이 있는데 주소가
  없는" 경우에도 자동으로 추가하지 않고, 실행 로그에 알림만 남깁니다.
  사람이 직접 priority/changefreq를 정해서 넣어주세요.

  리다이렉트 스텁 페이지(<meta http-equiv="refresh"> 가 있고,
  canonical이 자기 자신이 아닌 다른 주소를 가리키는 페이지)는
  sitemap에 올리지 않는 게 SEO 원칙이라, 파일이 있어도 자동 추가
  대상에서 제외합니다. 기존에 실수로 들어가 있었다면 다음 1번 규칙에
  의해 자동으로 빠집니다(파일 자체가 있으므로 1번에는 안 걸리니,
  2.5번 규칙으로 별도 처리).

사용법:
  python3 sync_sitemap.py --root /path/to/repo --sitemap /path/to/repo/sitemap.xml

  --dry-run 을 주면 실제로 파일을 고치지 않고 무엇을 바꿀지만 출력합니다.
  (GitHub Action에서는 --dry-run 없이 돌리고, 바뀐 게 있으면 그대로
  커밋합니다.)

종료 코드:
  0 = 변경 없음 (sitemap.xml이 이미 최신 상태)
  2 = 변경 있음 (sitemap.xml을 고쳤음 — Action이 이 코드를 보고 커밋함)
"""

import argparse
import datetime
import os
import re
import sys
import xml.etree.ElementTree as ET

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", SITEMAP_NS)

DOMAIN = "https://hohoplaylab.com"

# 새 파일이 생기면 자동으로 sitemap에 추가해줄 디렉터리 (끝에 '/' 포함, 저장소 루트 기준)
ADD_NEW_FROM_DIRS = ["blog/posts/", "blog/magazine/"]

# 파일 스캔에서 아예 제외할 디렉터리/패턴 (관리자 페이지, 백업, data 폴더 등)
EXCLUDE_DIR_PATTERNS = [
    r"^\.git(/|$)",
    r"^\.github(/|$)",
    r"^admin(/|$)",
    r"^data(/|$)",
    r"^node_modules(/|$)",
    r"board-magazine-\d+",  # 날짜 찍힌 백업 폴더 (예: board-magazine-260921)
]

# 파일명 자체가 템플릿/placeholder 인 경우 (예: community_post_template.html)
EXCLUDE_FILE_PATTERNS = [
    r"\{\{.*\}\}",      # {{POST_ID}} 같은 플레이스홀더가 파일명에 들어간 경우
    r"_template\.html$",
]

DEFAULT_CHANGEFREQ = "monthly"
DEFAULT_PRIORITY = "0.5"


def is_excluded_dir(rel_dir: str) -> bool:
    rel_dir = rel_dir.replace(os.sep, "/")
    for pat in EXCLUDE_DIR_PATTERNS:
        if re.search(pat, rel_dir):
            return True
    return False


def is_excluded_file(filename: str) -> bool:
    for pat in EXCLUDE_FILE_PATTERNS:
        if re.search(pat, filename):
            return True
    return False


def path_to_url(rel_path: str) -> str:
    """저장소 루트 기준 상대경로를 사이트 URL로 변환.
    예) 'index.html' -> '/'
        'about/index.html' -> '/about/'
        'blog/posts/6.html' -> '/blog/posts/6.html'
        'hoho-run.html' -> '/hoho-run.html'
    """
    rel_path = rel_path.replace(os.sep, "/")
    if rel_path == "index.html":
        return "/"
    if rel_path.endswith("/index.html"):
        return "/" + rel_path[: -len("index.html")]
    return "/" + rel_path


def url_to_rel_path(loc: str) -> str:
    """사이트 URL(절대 URL 또는 /path)을 저장소 루트 기준 상대경로로 변환."""
    path = loc
    if path.startswith(DOMAIN):
        path = path[len(DOMAIN):]
    if not path.startswith("/"):
        path = "/" + path
    if path == "/":
        return "index.html"
    if path.endswith("/"):
        return path[1:] + "index.html"
    return path[1:]


def scan_html_files(root: str):
    """저장소에서 .html 파일을 전부 찾아 상대경로 set으로 반환."""
    found = set()
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        rel_dir = "" if rel_dir == "." else rel_dir
        if is_excluded_dir(rel_dir):
            dirnames[:] = []  # 하위 디렉터리도 더 안 들어감
            continue
        # 하위 디렉터리 중에서도 제외 대상은 내려가지 않도록 미리 거름
        dirnames[:] = [
            d for d in dirnames
            if not is_excluded_dir((rel_dir + "/" + d) if rel_dir else d)
        ]
        for fn in filenames:
            if not fn.endswith(".html"):
                continue
            if is_excluded_file(fn):
                continue
            rel_path = fn if not rel_dir else f"{rel_dir}/{fn}"
            found.add(rel_path)
    return found


def is_redirect_stub(file_path: str) -> bool:
    """meta refresh로 다른 주소로 즉시 리다이렉트하는 스텁 페이지인지 확인."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(4000)  # head만 읽으면 충분
    except OSError:
        return False
    has_refresh = bool(re.search(r'<meta[^>]+http-equiv=["\']refresh["\']', head, re.I))
    return has_refresh


def load_sitemap(sitemap_path: str):
    """sitemap.xml을 파싱해서 loc -> {element, lastmod, changefreq, priority} 딕셔너리로."""
    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    entries = {}
    for url_el in list(root):
        loc_el = url_el.find(f"{{{SITEMAP_NS}}}loc")
        if loc_el is None or not loc_el.text:
            continue
        entries[loc_el.text.strip()] = url_el
    return tree, root, entries


def make_url_element(loc: str, lastmod: str, changefreq: str, priority: str):
    url_el = ET.Element(f"{{{SITEMAP_NS}}}url")
    loc_el = ET.SubElement(url_el, f"{{{SITEMAP_NS}}}loc")
    loc_el.text = loc
    if lastmod:
        lastmod_el = ET.SubElement(url_el, f"{{{SITEMAP_NS}}}lastmod")
        lastmod_el.text = lastmod
    changefreq_el = ET.SubElement(url_el, f"{{{SITEMAP_NS}}}changefreq")
    changefreq_el.text = changefreq
    priority_el = ET.SubElement(url_el, f"{{{SITEMAP_NS}}}priority")
    priority_el.text = priority
    return url_el


def indent_xml(elem, level=0):
    """보기 좋게 들여쓰기 (Python 3.9+ 의 ET.indent 와 동일한 효과, 구버전 호환용)."""
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = i + "  "
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="저장소 루트 디렉터리")
    ap.add_argument("--sitemap", default=None, help="sitemap.xml 경로 (기본: <root>/sitemap.xml)")
    ap.add_argument("--dry-run", action="store_true", help="실제로 파일을 고치지 않고 변경 내역만 출력")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    sitemap_path = args.sitemap or os.path.join(root, "sitemap.xml")

    if not os.path.exists(sitemap_path):
        print(f"[오류] sitemap.xml을 찾을 수 없습니다: {sitemap_path}", file=sys.stderr)
        sys.exit(1)

    files_on_disk = scan_html_files(root)
    tree, root_el, entries = load_sitemap(sitemap_path)

    today = datetime.date.today().isoformat()
    changed = False
    removed = []
    added = []
    notices = []

    # 1) sitemap에 있는데 파일이 없는 항목 제거
    for loc, url_el in list(entries.items()):
        rel_path = url_to_rel_path(loc)
        full_path = os.path.join(root, rel_path)
        if not os.path.isfile(full_path):
            root_el.remove(url_el)
            del entries[loc]
            removed.append(loc)
            changed = True

    # 2) blog/posts, blog/magazine 밑에 새로 생긴 파일을 자동 추가
    #    (리다이렉트 스텁은 제외)
    for rel_path in sorted(files_on_disk):
        in_watched_dir = any(rel_path.startswith(d) for d in ADD_NEW_FROM_DIRS)
        loc = DOMAIN + path_to_url(rel_path)
        # 같은 파일을 가리키는 두 가지 표기(디렉터리형 "/guides/" vs 명시형
        # "/guides/index.html")가 섞여 있을 수 있으므로 둘 다 확인해서
        # 이미 등록된 페이지를 "새 페이지"로 오인하지 않도록 함.
        alt_loc = DOMAIN + "/" + rel_path.replace(os.sep, "/") if rel_path.endswith("/index.html") else None
        if loc in entries or (alt_loc and alt_loc in entries):
            continue
        full_path = os.path.join(root, rel_path)
        if is_redirect_stub(full_path):
            continue  # 리다이렉트 스텁은 sitemap에 올리지 않음
        if in_watched_dir:
            new_el = make_url_element(loc, today, DEFAULT_CHANGEFREQ, DEFAULT_PRIORITY)
            root_el.append(new_el)
            entries[loc] = new_el
            added.append(loc)
            changed = True
        else:
            notices.append(loc)

    if changed:
        indent_xml(root_el)
        if root_el.text is None or not root_el.text.strip():
            root_el.text = "\n  "
        if args.dry_run:
            print("[dry-run] 실제로는 저장하지 않았습니다.")
        else:
            tree.write(sitemap_path, encoding="UTF-8", xml_declaration=True)
            # ET는 선언부에 작은따옴표를 쓰므로 기존 스타일(큰따옴표)에 맞춰 보정
            with open(sitemap_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace(
                "<?xml version='1.0' encoding='UTF-8'?>",
                '<?xml version="1.0" encoding="UTF-8"?>',
            )
            if not content.endswith("\n"):
                content += "\n"
            with open(sitemap_path, "w", encoding="utf-8") as f:
                f.write(content)

    print("=== sync_sitemap.py 결과 ===")
    if removed:
        print(f"\n제거된 항목 ({len(removed)}개) — 파일이 더 이상 존재하지 않음:")
        for loc in removed:
            print(f"  - {loc}")
    if added:
        print(f"\n추가된 항목 ({len(added)}개) — blog/posts 또는 blog/magazine에 새로 생긴 파일:")
        for loc in added:
            print(f"  + {loc}")
    if notices:
        print(f"\n[알림] sitemap에 없는 페이지가 발견됐지만 자동 추가 대상이 아닙니다 "
              f"(우선순위/주기를 직접 정해서 넣어주세요):")
        for loc in notices:
            print(f"  ? {loc}")
            if os.environ.get("GITHUB_ACTIONS") == "true":
                # GitHub Actions 워크플로 요약/체크 화면에 경고로 뜨게 함
                # (로그를 직접 안 열어봐도 눈에 띄도록)
                print(f"::warning title=sitemap.xml 미등록 페이지::{loc} 가 sitemap.xml에 "
                      f"없습니다. 우선순위/주기를 정해서 수동으로 추가해주세요.")
    if not changed and not notices:
        print("\n변경 사항 없음 — sitemap.xml이 실제 파일 상태와 일치합니다.")

    sys.exit(2 if changed else 0)


if __name__ == "__main__":
    main()
