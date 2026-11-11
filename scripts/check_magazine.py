#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""호호매거진 발행 점검 (MULTI_PLATFORM_SEO_MASTER v9.0 의 23·24장 기준).

blog/magazine/*.html 의 글을 읽어서 아래를 검사하고 결과를 표로 보여준다. 파일은 수정하지 않는다(읽기 전용).
  - 자리표시자 남음: "(시술/메뉴/상품)", "[지역]", "OOO" 같은 템플릿 문구가 소제목·FAQ·본문에 남았는지
  - FAQ 라벨: "1. (방문/이용 전 확인) …", "Q1. [방문/주차] …" 처럼 질문 앞에 붙은 분류 라벨
  - "호호플레이" 언급 횟수(본문 2회 이하) / 도입부(앞 400자) 언급
  - 출처: 공식 기관·자료명 표기 또는 "참고한 자료" 블록이 있는지
  - 구체 수치(요금·시간·인원·연도 등) 밀도
  - 상투적 도입·수식어 (23.2장)
  - 분량(공백 제외 2,000자 이상)
  - 글 간 중복: 같은 H2 / 같은 FAQ 질문이 여러 글에 반복되는지

사용:  python scripts/check_magazine.py                 (저장소 루트에서, blog/magazine 전체)
       python scripts/check_magazine.py blog/magazine/52.html blog/magazine/53.html
       python scripts/check_magazine.py --only-problems   (문제 있는 글만)
표준 라이브러리만 쓰며 종료 코드는 항상 0 이다(Actions 를 막지 않음). 새 글을 올리기 전에 직접 돌려 보는 용도.
"""
import glob
import html as htmllib
import os
import re
import sys
from collections import defaultdict

MIN_CHARS = 2000
MAX_SERVICE_MENTIONS = 2
SERVICE_NAMES = ('호호플레이', 'HOHO PLAY', 'HoHoPlay')

PLACEHOLDER_RES = [
    re.compile(r'[\(\[（]\s*(?:시술|메뉴|상품|지역|업종|상호|매장명|상호명)\s*[/,·][^\)\]）\n]{0,20}[\)\]）]'),
    re.compile(r'[\(\[（]\s*(?:시술|메뉴|상품|지역|업종|상호|매장명|상호명)\s*[\)\]）]'),
    re.compile(r'OOO|○○○|〇〇〇|XXX|\{\{[^}]+\}\}'),
]
FAQ_LABEL_RE = re.compile(r'^\s*(?:Q\s*\d*\s*[\.\):]?|\d+\s*[\.\)])\s*[\(\[（][^\)\]）]{1,16}[\)\]）]')
CLICHES = [
    '누구나 한 번쯤', '이루 말할 수 없', '아련한', '열풍이 불고', '의 중요성', '의 매력과 가치',
    '알아보겠습니다', '살펴보겠습니다', '획기적', '완벽한', '극대화', '혁신적', '압도적', '필수불가결',
]
SOURCE_RE = re.compile(
    r'한국관광공사|문화체육관광부|통계청|보건복지부|교육부|행정안전부|질병관리청|기상청|공공데이터|TourAPI|지자체|'
    r'국민여행조사|참고한 자료|참고 자료|출처|기준일|YYYY|\d{4}[.\-]\d{1,2}[.\-]\d{1,2}\s*기준|\d{4}년\s*\d{1,2}월\s*기준'
)
FACT_RE = re.compile(r'\d[\d,\.]*\s*(?:원|분|시간|명|%|곳|개|세|개월|월|일|년|시|km|m|cm|g|kg|ml)|\d{1,2}:\d{2}')


def strip_tags(s):
    s = re.sub(r'<(script|style)[\s\S]*?</\1>', '', s, flags=re.I)
    s = re.sub(r'<br\s*/?>|</p>|</li>|</tr>|</h[1-6]>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    return htmllib.unescape(s)


def article_html(raw):
    m = re.search(r'<h1[\s\S]*?(?=<aside|<div id="site-footer"|<footer|</article>|</main>|$)', raw)
    return m.group(0) if m else raw


FAQ_HEAD_RE = re.compile(r'FAQ|자주\s*묻는')
FAQ_ITEM_RE = re.compile(r'^\s*(?:Q\s*\d*\s*[\.\):]|\d+\s*[\.\)])\s*(.+)$')


def faq_questions(text):
    """본문 텍스트에서 FAQ 구역을 찾아 질문 줄(‘Q.’, ‘Q1.’, ‘1.’로 시작)을 모은다. 질문 뒤에 답이 한 줄로 붙어 있어도 질문 부분(첫 물음표까지)만 쓴다."""
    lines = text.split('\n')
    start = None
    for i, ln in enumerate(lines):
        if FAQ_HEAD_RE.search(ln) and len(ln.strip()) < 40:
            start = i + 1
    if start is None:
        return []
    out = []
    for ln in lines[start:]:
        if re.match(r'^\s*(?:함께|관련|참고한|해시태그|#)', ln):
            break
        m = FAQ_ITEM_RE.match(ln)
        if m:
            q = ln.strip()
            k = re.search(r'[?？]', q)
            out.append(q[:k.end()] if k else q)
        elif len(ln.strip()) <= 120 and re.search(r'[?？]\s*$', ln):
            # v9.0 규격: 질문이 H3(또는 굵은 한 줄)로 따로 있고 답변이 아래 별도 문단인 경우
            out.append(ln.strip())
    return out


def norm(t):
    t = re.sub(r'^\s*(?:Q\s*\d+\s*[\.\):]\s*(?:\[[^\]]*\]\s*)?|\d+(?:\.\d+)*\s*[\.\):]\s*)', '', t.strip())
    return re.sub(r'\s+', '', t)


def analyze(path):
    raw = open(path, encoding='utf-8').read()
    body_html = article_html(raw)
    h1 = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', body_html)
    title = strip_tags(h1.group(1)).strip() if h1 else os.path.basename(path)
    text = strip_tags(body_html)
    flat = re.sub(r'\s+', '', text)
    heads = [strip_tags(x).strip() for x in re.findall(r'<h[23][^>]*>([\s\S]*?)</h[23]>', body_html)]
    h2s = [strip_tags(x).strip() for x in re.findall(r'<h2[^>]*>([\s\S]*?)</h2>', body_html)]
    h3s = [strip_tags(x).strip() for x in re.findall(r'<h3[^>]*>([\s\S]*?)</h3>', body_html)]
    faq_qs = faq_questions(text)
    paras = [p.strip() for p in text.split('\n') if len(p.strip()) >= 40]

    issues = []
    ph = []
    for h in heads + paras:
        for rx in PLACEHOLDER_RES:
            m = rx.search(h)
            if m:
                ph.append(m.group(0))
    if ph:
        issues.append(('자리표시자', f'{len(ph)}건 ({", ".join(sorted(set(ph))[:3])})'))
    labels = [q for q in faq_qs if FAQ_LABEL_RE.search(q)]
    if labels:
        issues.append(('FAQ 라벨', f'질문 앞 분류 라벨 {len(labels)}개 (예: {labels[0][:22]}…)'))

    # 서비스 언급 — 제목·작성자 줄은 제외하고 본문에서 센다
    body_only = text
    if h1:
        body_only = body_only.replace(strip_tags(h1.group(1)), '', 1)
    svc = sum(body_only.count(n) for n in SERVICE_NAMES)
    svc -= body_only.count('HOHO PLAY ·')  # 작성자·날짜 줄
    if svc > MAX_SERVICE_MENTIONS:
        issues.append(('서비스 언급', f'{svc}회 (상한 {MAX_SERVICE_MENTIONS}회)'))
    intro = re.sub(r'\s+', '', body_only.replace('HOHO PLAY ·', ''))[:400]
    if any(n.replace(' ', '') in intro for n in SERVICE_NAMES):
        issues.append(('도입부 서비스 언급', '앞 400자 안에 서비스명 있음'))

    if not SOURCE_RE.search(text):
        issues.append(('출처', '공식 기관·자료명·기준일 표기가 보이지 않음'))
    elif not re.search(r'참고한 자료|참고 자료', text):
        issues.append(('출처 블록', '"참고한 자료" 블록 없음'))

    facts = len(FACT_RE.findall(text))
    need = max(1, len(paras) // 3)
    if facts < need:
        issues.append(('구체 수치', f'수치 {facts}개 (문단 {len(paras)}개 기준 {need}개 이상 권장)'))

    found = [c for c in CLICHES if c in text]
    if found:
        issues.append(('상투어', ', '.join(found[:4]) + (' 외' if len(found) > 4 else '')))
    if len(flat) < MIN_CHARS:
        issues.append(('분량', f'공백 제외 {len(flat)}자 (최소 {MIN_CHARS}자)'))
    if len(faq_qs) != 5:
        issues.append(('FAQ 개수', f'{len(faq_qs)}개로 인식됨 (5개 권장)'))
    return {'path': path, 'title': title, 'chars': len(flat), 'svc': svc, 'issues': issues,
            'h2': [norm(h) for h in h2s], 'faq': [norm(q) for q in faq_qs]}


def main(argv):
    only = '--only-problems' in argv
    paths = [a for a in argv if not a.startswith('--')]
    if not paths:
        paths = sorted(glob.glob(os.path.join('blog', 'magazine', '[0-9]*.html')),
                       key=lambda p: int(re.findall(r'\d+', os.path.basename(p))[0]))
    if not paths:
        print('검사할 글이 없습니다. 저장소 루트에서 실행하거나 파일 경로를 적어 주세요.')
        return 0
    results = [analyze(p) for p in paths]

    by_h2, by_faq = defaultdict(set), defaultdict(set)
    for r in results:
        for h in set(r['h2']):
            if len(h) >= 8:
                by_h2[h].add(os.path.basename(r['path']))
        for q in set(r['faq']):
            by_faq[q].add(os.path.basename(r['path']))
    dup_h2 = {h: v for h, v in by_h2.items() if len(v) >= 2}
    dup_faq = {q: v for q, v in by_faq.items() if len(v) >= 2}

    total_issue_files = 0
    for r in results:
        if r['issues']:
            total_issue_files += 1
        if only and not r['issues']:
            continue
        mark = '⚠' if r['issues'] else '✓'
        print(f"{mark} {os.path.basename(r['path'])}  {r['chars']}자 · 서비스 {r['svc']}회  {r['title'][:40]}")
        for k, v in r['issues']:
            print(f'     - {k}: {v}')
    print('\n── 요약 ──')
    print(f'검사 {len(results)}개 중 문제 있는 글 {total_issue_files}개')
    kinds = defaultdict(int)
    for r in results:
        for k, _ in r['issues']:
            kinds[k] += 1
    for k, n in sorted(kinds.items(), key=lambda x: -x[1]):
        print(f'  {k}: {n}개 글')
    if dup_h2:
        print(f'\n같은 소제목(H2)이 여러 글에 반복: {len(dup_h2)}개')
        for h, v in list(dup_h2.items())[:8]:
            print(f'  · {h[:36]}…  → {", ".join(sorted(v))}')
    if dup_faq:
        print(f'\n같은 FAQ 질문이 여러 글에 반복: {len(dup_faq)}개')
        for q, v in list(dup_faq.items())[:8]:
            print(f'  · {q[:36]}…  → {", ".join(sorted(v))}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
