#!/usr/bin/env python3
"""
delete_old_posts.py — 특정 라벨의 게시물을 날짜 기준으로 정리
==========================================================
목적: 별자리운세·띠운세·별자리주간·띠별월간·별과띠가만나는시간
     5개 타입 중, 지정한 날짜(cutoff) "이전"에 발행된 글을 정리한다.
     (오늘의명언·운세상식은 대상에서 제외 — 절대 건드리지 않음)

안전장치 (중요):
  - 기본은 항상 DRY RUN입니다. 실제로 지우지 않고, 지워질 글 목록만
    콘솔에 출력하고 data/delete_preview.json 파일로도 저장합니다.
  - 실제 삭제는 --confirm DELETE 를 정확히(대소문자까지) 줬을 때만
    실행됩니다. 오타나 실수로 지워지는 사고를 막기 위함입니다.
  - 한 번 지운 글은 복구할 수 없습니다. 반드시 먼저 DRY RUN 목록을
    확인한 뒤 진행하세요.

실행:
  # 1단계 — 목록만 확인 (항상 이걸 먼저)
  python scripts/delete_old_posts.py --cutoff 2026-08-31

  # 2단계 — 실제 삭제 (목록 확인 후에만!)
  python scripts/delete_old_posts.py --cutoff 2026-08-31 --confirm DELETE

환경변수:
  BLOG_ID, BLOGGER_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
  (기존 auto_post.yml / create_post.py와 동일한 secrets 재사용)
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

# 삭제 대상 라벨 — 이 5개만. 오늘의명언·운세상식은 여기 없음(안전).
TARGET_LABELS = ["별자리운세", "띠운세", "별자리주간", "띠별월간", "별과띠가만나는시간"]

DATA_DIR = os.environ.get('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
PREVIEW_PATH = os.path.join(DATA_DIR, 'delete_preview.json')


def get_access_token():
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "grant_type": "refresh_token",
        "refresh_token": os.environ["BLOGGER_REFRESH_TOKEN"],
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_posts_by_label(blog_id, token, label):
    """해당 라벨이 붙은 글 전부를 페이지네이션으로 끝까지 가져온다."""
    posts = []
    url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"
    params = {
        "labels": label,
        "maxResults": 500,
        "fetchBodies": "false",
        "status": "live",
    }
    while True:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
        if r.status_code != 200:
            print(f"  ⚠️ '{label}' 조회 중 오류({r.status_code}): {r.text[:200]}")
            break
        data = r.json()
        posts.extend(data.get("items", []))
        next_token = data.get("nextPageToken")
        if not next_token:
            break
        params["pageToken"] = next_token
    return posts


def main():
    parser = argparse.ArgumentParser(description="지정 라벨 게시물을 날짜 기준으로 삭제")
    parser.add_argument("--cutoff", required=True,
                         help="이 날짜(YYYY-MM-DD) '이전'에 발행된 글만 삭제 대상 (이 날짜 포함 이후는 유지)")
    parser.add_argument("--confirm", default="",
                         help="실제 삭제를 실행하려면 정확히 'DELETE'를 입력. 그 외에는 항상 DRY RUN")
    args = parser.parse_args()

    if "BLOGGER_REFRESH_TOKEN" not in os.environ:
        print("❌ BLOGGER_REFRESH_TOKEN 등 환경변수 필요")
        sys.exit(1)

    cutoff = datetime.strptime(args.cutoff, "%Y-%m-%d").replace(tzinfo=KST)
    blog_id = os.environ["BLOG_ID"]
    token = get_access_token()

    is_dry_run = (args.confirm != "DELETE")
    print(f"{'🔍 DRY RUN (목록만 확인, 실제 삭제 안 함)' if is_dry_run else '🗑️  실제 삭제 모드'}")
    print(f"기준일: {args.cutoff} 이전 발행 글만 대상")
    print(f"대상 라벨: {TARGET_LABELS}\n")

    seen_ids = set()
    to_delete = []

    for label in TARGET_LABELS:
        posts = fetch_posts_by_label(blog_id, token, label)
        print(f"  · '{label}' 라벨 전체 {len(posts)}개 조회됨")
        for p in posts:
            pid = p["id"]
            if pid in seen_ids:
                continue  # 라벨이 겹쳐도 중복 집계 방지
            published_str = p.get("published", "")
            if not published_str:
                continue
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00")).astimezone(KST)
            if published < cutoff:
                seen_ids.add(pid)
                to_delete.append({
                    "id": pid,
                    "title": p.get("title", ""),
                    "url": p.get("url", ""),
                    "published": published.strftime("%Y-%m-%d %H:%M"),
                    "label": label,
                })

    to_delete.sort(key=lambda x: x["published"])

    print(f"\n총 삭제 대상: {len(to_delete)}개\n")
    for item in to_delete:
        print(f"  [{item['published']}] ({item['label']}) {item['title']}")

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PREVIEW_PATH, "w", encoding="utf-8") as f:
        json.dump(to_delete, f, ensure_ascii=False, indent=2)
    print(f"\n📄 전체 목록이 {PREVIEW_PATH} 에도 저장되었습니다.")

    if is_dry_run:
        print("\n✅ DRY RUN 완료 — 아무것도 삭제되지 않았습니다.")
        print("   목록을 확인하신 뒤, 문제없으면 --confirm DELETE 옵션으로 다시 실행해주세요.")
        return

    print(f"\n⚠️  {len(to_delete)}개 게시물을 실제로 삭제합니다...")
    success, fail = 0, 0
    for item in to_delete:
        del_url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{item['id']}"
        r = requests.delete(del_url, headers={"Authorization": f"Bearer {token}"})
        if r.status_code in (200, 204):
            success += 1
            print(f"  ✅ 삭제됨: {item['title']}")
        else:
            fail += 1
            print(f"  ⚠️ 삭제 실패({r.status_code}): {item['title']}")
        time.sleep(0.3)  # API rate limit 방지

    print(f"\n완료: {success}개 삭제 성공, {fail}개 실패")


if __name__ == "__main__":
    main()
