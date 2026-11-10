#!/usr/bin/env python3
"""scripts/build_kids_course_pages.py

대전 구별 '아이랑 나들이 추천 코스' 글 3개를 data/kids_places.json 으로 (재)생성한다.
  - blog/kids-course/daejeon-yuseong.html (유성구)
  - blog/kids-course/daejeon-jung.html    (중구)
  - blog/kids-course/daejeon-seo.html     (서구)

껍데기(헤더·공유·댓글·푸터)는 기존 코스 글 한 개(daejeon-yuseong.html)의 것을 그대로 쓰고,
본문(소개·한눈에 보기·장소 블록·추천 동선·마무리)만 새로 만든다.
  - 소개·요약·추천 동선·마무리·메타 설명: scripts/kids_course_text.py (장소 데이터에서 문장을 생성)
제외 규칙: EXCLUDE 에 적은 장소, 그리고 overview 에 "확인하지 못했다"가 들어 있는 장소(주소·운영시간·요금을 확인하지 못한 곳)는 글에 싣지 않는다.
멱등: 여러 번 실행해도 같은 결과.  사용법(저장소 루트): python3 scripts/build_kids_course_pages.py [--dry-run]
"""
import html as H
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import improve_kids_course_pages as imp  # noqa: E402
import add_kids_course_route as rte      # noqa: E402
import kids_course_text as kct           # noqa: E402
import kids_images as ki                 # noqa: E402

DATE = '2026.10.15'          # 기존 유성구 글의 게시일을 유지
SHELL_SLUG = 'daejeon-yuseong'
UNVERIFIED = '확인하지 못했다'
H2_BIG = 'font-size:20px;font-weight:900;color:#1e293b;margin:24px 0 4px'
H2_OUT = 'font-size:20px;font-weight:900;color:#1e293b;margin:32px 0 8px'
H2_PLACE = 'font-size:19px;font-weight:900;color:#1e293b;margin:28px 0 6px'

# slug → (지역명, 구 이름, 순서를 고정할 기존 장소들)
COURSES = [
    ('daejeon-yuseong', '대전 유성구', '유성구', ['kids-0066', 'kids-0067', 'kids-0069']),
    ('daejeon-jung', '대전 중구', '중구', []),
    ('daejeon-seo', '대전 서구', '서구', []),
]
# 정보 부족 외에 코스에 어울리지 않아 뺀 곳: 충무체육관(프로배구 경기가 있는 날만 관람 가능)
EXCLUDE = {'kids-0325'}
EMOJI = {'완전무료': '✅', '확인 필요': '❓'}


def e(s):
    return H.escape(s or '', quote=False)


def place_block(i, p):
    cid, title = p['contentid'], p['title']
    meta = ['📍 ' + e(p['addr']), '%s %s' % (EMOJI.get(p.get('costTag'), '💳'), e(p.get('costTag')))]
    h = imp.real_hours(p)
    meta.append('🕒 ' + e(h) if h else '🕒 운영시간 정보 없음 (방문 전 확인)')
    fee = (p.get('fee') or '').strip()
    if fee:
        meta.append('💰 ' + e(fee))
    if (p.get('tel') or '').strip():
        meta.append('☎ ' + e(p['tel']))
    out = ['<h2 style="%s">%d. <a href="/festival/detail/%s.html" style="color:#1e293b;text-decoration:none;border-bottom:2px solid #c7d2fe">%s</a></h2>'
           % (H2_PLACE, i, cid, e(title)) + ki.course_figure(p),   # 공식 사진이 있으면 제목 바로 아래(2026-11-10)
           '<p style="font-size:13px;color:#94a3b8;margin:0 0 8px">' + ' &nbsp;·&nbsp; '.join(meta) + '</p>']
    if (p.get('desc') or '').strip():
        out.append('<p style="margin:0 0 4px;font-weight:700;color:#475569">%s</p>' % e(p['desc']))
    if (p.get('overview') or '').strip():
        out.append('<p style="margin:0 0 4px">%s</p>' % e(p['overview']))
    hp = (p.get('homepage') or '').strip()
    if hp.startswith('http'):
        out.append('<p style="margin:0 0 4px"><a href="%s" target="_blank" rel="noopener" style="font-size:13px;color:#0891b2;font-weight:700;text-decoration:none">🔗 공식 홈페이지</a></p>' % H.escape(hp))
    out.append('<p style="margin:4px 0 0"><a href="/festival/detail/%s.html" style="font-size:13px;color:#4f46e5;font-weight:700;text-decoration:none">자세히 보기 →</a></p>' % cid)
    return '\n'.join(out)


def pick(places, gu, pinned):
    cand = [p for p in places if p['addr'].startswith('대전광역시 ' + gu) and UNVERIFIED not in (p.get('overview') or '') and p['contentid'] not in EXCLUDE]
    by = {p['contentid']: p for p in cand}
    first = [by[c] for c in pinned if c in by]
    rest = sorted((p for p in cand if p['contentid'] not in pinned), key=lambda p: p['contentid'])
    return first + rest


def build(shell, slug, region, plist):
    entries = [(p['contentid'], p['title'], p) for p in plist]
    n = len(plist)
    # 소개·동선·마무리 문구는 scripts/kids_course_text.py 가 장소 데이터(요금·운영시간·좌표)에서 만든다.
    kc = ('<!--kc:v1-->' + kct.build_kc(region, entries) + '<!--/kc:v1-->')
    kr = rte.KR_START + kct.build_kr(region, entries) + rte.KR_END
    ko = kct.KO_START + kct.build_outro(region, entries) + kct.KO_END
    body = (kc + '\n<h2 style="%s">%s, 아이랑 갈만한 곳 %d곳</h2>\n' % (H2_BIG, region, n)
            + '\n'.join(place_block(i + 1, p) for i, p in enumerate(plist)) + '\n'
            + kr + ko)

    s = shell
    a = s.index('<div class="space-y-4 text-slate-700 leading-relaxed" style="white-space:pre-wrap">')
    a = s.index('>', a) + 1
    b = s.index('<div style="margin-top:32px;padding-top:20px;border-top:1px solid #f1f5f9')
    s = s[:a] + body + s[b:]

    old_region = rte.region_name(shell)
    s = s.replace(SHELL_SLUG, slug)
    s = s.replace('<title>%s 아이랑' % old_region, '<title>%s 아이랑' % region)
    s = s.replace('<h1 class="text-3xl font-black text-slate-900 mb-2 leading-tight">%s ' % old_region,
                  '<h1 class="text-3xl font-black text-slate-900 mb-2 leading-tight">%s ' % region)
    desc = H.escape(kct.build_meta_desc(region, entries))
    for rx in (r'(<meta name="description" content=")[^"]*(">)', r'(<meta property="og:description" content=")[^"]*(">)',
               r'(<meta name="twitter:description" content=")[^"]*(">)'):
        s = re.sub(rx, lambda m: m.group(1) + desc + m.group(2), s, count=1)
    s = kct.ensure_noindex(s)   # 코스 글은 모두 검색 제외(noindex,follow) — 2026-11-10 결정
    s = re.sub(r'(HOHO PLAY · )\d{4}\.\d{2}\.\d{2}', lambda m: m.group(1) + DATE, s, count=1)
    return s


def main():
    dry = '--dry-run' in sys.argv
    with open(os.path.join(ROOT, 'data', 'kids_places.json'), encoding='utf-8') as f:
        places = json.load(f)
    shell_path = os.path.join(ROOT, 'blog', 'kids-course', SHELL_SLUG + '.html')
    with open(shell_path, encoding='utf-8') as f:
        shell = f.read()
    for slug, region, gu, pinned in COURSES:
        plist = pick(places, gu, pinned)
        out = build(shell, slug, region, plist)
        path = os.path.join(ROOT, 'blog', 'kids-course', slug + '.html')
        print('%s: 장소 %d곳' % (slug, len(plist)), ', '.join(p['title'] for p in plist))
        if not dry:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(out)


if __name__ == '__main__':
    main()
