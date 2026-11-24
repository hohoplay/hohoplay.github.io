# -*- coding: utf-8 -*-
"""
기존 글에 남아 있는 '⭐ 오늘의 별자리운세' / '🐉 오늘의 띠운세' 링크 버튼을 제거하는 1회성 스크립트.
- 새 글에는 이미 빠져 있음(_ALL_TYPES). 이 스크립트는 예전에 발행된 글만 정리한다.
- 기본은 미리보기(DRY RUN): 바꿀 글 목록만 출력하고 아무것도 수정하지 않는다.
- APPLY=true 로 실행해야 실제 수정(PATCH)한다. 본문 content만 바꾸고 제목·라벨·발행일은 건드리지 않는다.
- 제거 대상: href가 '별자리운세'/'띠운세' 라벨 검색 주소이면서 버튼 글자가 '오늘의 별자리운세'/'오늘의 띠운세'인 <a> 태그 하나씩.
"""
import os, re, sys, time, json
import urllib.request, urllib.parse, urllib.error

BLOG_ID       = os.environ.get("BLOG_ID", "")
REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN", "")
CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
APPLY = os.environ.get("APPLY", "false").lower() == "true"

# 라벨 주소 끝이 정확히 일치할 때만(별자리주간·띠별월간 등 다른 라벨 버튼은 건드리지 않음)
_LABELS = ["%EB%B3%84%EC%9E%90%EB%A6%AC%EC%9A%B4%EC%84%B8",   # 별자리운세
           "%EB%9D%A0%EC%9A%B4%EC%84%B8"]                     # 띠운세
_TEXTS  = ["오늘의 별자리운세", "오늘의 띠운세"]

_ANCHOR = re.compile(
    r'<a\b[^>]*\bhref="[^"]*/search/label/(?:' + "|".join(re.escape(x) for x in _LABELS) + r')(?:\?[^"]*)?"[^>]*>(.*?)</a>',
    re.S | re.I)

def strip_buttons(html):
    removed = []
    def _sub(m):
        inner = re.sub(r"<[^>]+>", "", m.group(1))
        if any(t in inner for t in _TEXTS):
            removed.append(inner.strip())
            return ""
        return m.group(0)
    return _ANCHOR.sub(_sub, html), removed

def http(url, data=None, method="GET", headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8") or "{}")

def token():
    body = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN,
                                   "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}).encode()
    return http("https://oauth2.googleapis.com/token", data=body, method="POST",
                headers={"Content-Type": "application/x-www-form-urlencoded"})["access_token"]

def main():
    if not (BLOG_ID and REFRESH_TOKEN and CLIENT_ID and CLIENT_SECRET):
        print("❌ BLOG_ID / BLOGGER_REFRESH_TOKEN / GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 필요"); sys.exit(1)
    tk = token()
    auth = {"Authorization": f"Bearer {tk}"}
    print("▶ 모드:", "실제 수정(APPLY)" if APPLY else "미리보기(DRY RUN) — 수정하지 않음")
    page, total, hit, done, fail = None, 0, 0, 0, 0
    while True:
        q = {"fetchBodies": "true", "maxResults": "50", "status": "live",
             "fields": "nextPageToken,items(id,title,url,content)"}
        if page: q["pageToken"] = page
        res = http(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts?" + urllib.parse.urlencode(q), headers=auth)
        for p in res.get("items", []):
            total += 1
            new, removed = strip_buttons(p.get("content", ""))
            if not removed:
                continue
            hit += 1
            print(f"  · {p['title'][:40]} — 제거 {len(removed)}개 ({', '.join(removed)})")
            if APPLY:
                try:
                    http(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/{p['id']}",
                         data=json.dumps({"content": new}).encode("utf-8"), method="PATCH",
                         headers={**auth, "Content-Type": "application/json"})
                    done += 1
                except urllib.error.HTTPError as e:
                    fail += 1
                    print(f"    ❌ 수정 실패 {e.code}: {e.read().decode('utf-8','ignore')[:150]}")
                time.sleep(0.5)
        page = res.get("nextPageToken")
        if not page: break
    print(f"\n✅ 검사 {total}개 글 · 해당 {hit}개" + (f" · 수정 {done}개 · 실패 {fail}개" if APPLY else " (미리보기라 수정 없음)"))
    if fail: sys.exit(1)

if __name__ == "__main__":
    main()
