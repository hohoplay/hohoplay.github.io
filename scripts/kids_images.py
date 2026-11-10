# -*- coding: utf-8 -*-
"""scripts/kids_images.py

아이랑 코스 글(blog/kids-course/)과 실내 놀이 지역 글(blog/indoor-kids/)에 넣는 장소 사진 조각을 만든다.

사진은 data/kids_places.json 의 "image"(한국관광공사 TourAPI 공식 사진 URL)만 쓴다.
 - image 가 없는 장소는 사진을 넣지 않는다(지어내거나 다른 곳 사진을 쓰지 않음).
 - http:// 주소는 https:// 로 바꾼다(HTTPS 페이지의 혼합 콘텐츠 방지).
 - 사진이 안 열리면 그 자리가 통째로 사라지도록 onerror 처리(깨진 이미지 아이콘이 보이지 않게).
 - aspect-ratio 로 자리를 미리 잡아 늦게 뜨는 사진이 글을 밀어내지 않게 한다. loading="lazy".
 - 조각은 <!--kp:v1-->…<!--/kp:v1--> 표식으로 감싸 여러 번 실행해도 같은 결과가 나온다.
 - 코스 글 본문 컨테이너가 white-space:pre-wrap 이라 조각 안에 줄바꿈을 넣지 않는다.
"""
import html as H
import re

KP_START = '<!--kp:v1-->'
KP_END = '<!--/kp:v1-->'
KP_RE = re.compile(re.escape(KP_START) + r'.*?' + re.escape(KP_END), re.S)
CREDIT = '사진: 한국관광공사'

# 실내 놀이 지역 글(.place-card)용 CSS. 지역 글 <style> 안에 한 번만 들어간다.
THUMB_CSS = ('  .place-thumb { display:block; width:100%; aspect-ratio:16/9; object-fit:cover; border-radius:10px; '
             'background:#f1f5f9; margin:0 0 10px; }\n')
THUMB_CSS_MARK = '.place-thumb {'


def img_url(p):
    u = (p.get('image') or '').strip()
    if not u:
        return None
    if u.startswith('http://'):
        u = 'https://' + u[len('http://'):]
    return u if u.startswith('https://') else None


def course_figure(p):
    """코스 글: 장소 제목 바로 아래 큰 사진 + 출처 한 줄."""
    u = img_url(p)
    if not u:
        return ''
    return (KP_START
            + '<figure style="margin:0 0 10px"><img src="%s" alt="%s 사진" loading="lazy" decoding="async" referrerpolicy="no-referrer" '
              'onerror="this.parentNode.style.display=\'none\'" '
              'style="display:block;width:100%%;aspect-ratio:16/9;object-fit:cover;border-radius:12px;background:#f1f5f9">'
              '<figcaption style="font-size:11px;color:#94a3b8;margin:4px 0 0">%s</figcaption></figure>'
            % (H.escape(u, quote=True), H.escape(p.get('title', ''), quote=True), CREDIT)
            + KP_END)


def card_thumb(p):
    """실내 놀이 지역 글: 카드 맨 위 사진."""
    u = img_url(p)
    if not u:
        return ''
    return (KP_START
            + '<img class="place-thumb" src="%s" alt="%s 사진" loading="lazy" decoding="async" referrerpolicy="no-referrer" '
              'onerror="this.style.display=\'none\'">'
            % (H.escape(u, quote=True), H.escape(p.get('title', ''), quote=True))
            + KP_END)
