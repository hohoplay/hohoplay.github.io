"""
운세 자동화 - 하루 27개 포스팅
  1개  : 오늘의 명언
 12개  : 별자리 운세
 12개  : 띠 운세
  1개  : 별자리 주간 운세 (12별자리 통합)
  1개  : 띠별 월간 운세 (12띠 통합)
────────────────────────────────
 27개/일 × 30일 = 810개/월
"""

import os, random, time
import pandas as pd
import requests
from datetime import datetime, date, timezone, timedelta

# KST = UTC+9
KST = timezone(timedelta(hours=9))

def now_kst():
    """항상 KST 기준 현재 시각 반환"""
    return datetime.now(KST)

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, '..', 'data')
# GitHub Actions에서 DATA_DIR 환경변수로 경로 오버라이드 가능
if os.environ.get('DATA_DIR'):
    DATA = os.environ['DATA_DIR']

# ─────────────────────────────────────────
# 포스트 타입별 대표 이미지 URL
# GitHub raw URL 형식:
#   https://raw.githubusercontent.com/{유저명}/{저장소명}/main/data/파일명.png
# ※ 아래 _GITHUB_RAW 의 {유저명}/{저장소명} 을 실제 값으로 교체하세요
# ─────────────────────────────────────────
IMG = {
    "zodiac":  "https://i.ibb.co/hFTQc66p/todayhoroscopelaboratory03.png",  # 별자리 오늘 운세
    "chinese": "https://i.ibb.co/ccxKySzq/todayhoroscopelaboratory04.png",  # 띠 오늘 운세
    "weekly":  "https://i.ibb.co/PZyr5FvY/todayhoroscopelaboratory05.png",  # 주간운세 (띠+별자리)
    "monthly": "https://i.ibb.co/Dfqdzbd2/todayhoroscopelaboratory06.png",  # 띠별 월간운세
}

def post_img(key):
    """포스트 상단 히어로 아래 삽입용 이미지 HTML"""
    url = IMG.get(key, "")
    if not url:
        return ""
    return (
        '<div style="text-align:center;margin-bottom:20px">'
        f'<img src="{url}" alt="오늘의운세로그" '
        'style="width:100%;max-width:680px;border-radius:16px;'
        'box-shadow:0 4px 20px rgba(0,0,0,0.12)" '
        "onerror=\"this.style.display='none'\">"
        '</div>'
    )

def csv(name):
    try:
        return pd.read_csv(os.path.join(DATA, name))
    except:
        return pd.DataFrame()

# ─────────────────────────────────────────
# CSV 로드
# ─────────────────────────────────────────
fortune_emotion   = csv("fortune_emotion_5000.csv")
fortune_1000      = csv("fortune_sentences_1000.csv")
fortune_4000      = csv("fortune_sentences_4000.csv")
daily_365         = csv("daily_fortunes_365.csv")
fortune_365       = csv("fortune_365_days.csv")
fortune_quotes    = csv("fortune_quotes_10000.csv")   # ← 오늘의명언용
zodiac_kr         = csv("zodiac_fortune_1000.csv")
fortune_score     = csv("fortune_score.csv")          # ← 운세 지수
lucky_items       = csv("lucky_items_1000.csv")        # ← 행운의 아이템 (별자리용)
chinese_zodiac    = csv("chinese_zodiac_fortunes.csv")
colors_200        = csv("lucky_colors_200.csv")
numbers_500       = csv("lucky_numbers_500.csv")
seo_keywords      = csv("fortune_seo_keywords_3000.csv")
seo_patterns      = csv("seo_patterns.csv")

# 주간/월간 CSV
weekly_500        = csv("weekly_fortune_500.csv")
monthly_500       = csv("monthly_fortune_500.csv")
zodiac_weekly     = csv("zodiac_weekly_1000.csv")
zodiac_monthly    = csv("zodiac_monthly_1000.csv")
chinese_weekly    = csv("chinese_weekly_1000.csv")
chinese_monthly   = csv("chinese_monthly_1000.csv")

# ─────────────────────────────────────────
# 정적 데이터
# ─────────────────────────────────────────
ZODIACS = [
    {"en":"aries",       "kr":"양자리",    "date":"3/21~4/19",  "emoji":"♈"},
    {"en":"taurus",      "kr":"황소자리",  "date":"4/20~5/20",  "emoji":"♉"},
    {"en":"gemini",      "kr":"쌍둥이자리","date":"5/21~6/21",  "emoji":"♊"},
    {"en":"cancer",      "kr":"게자리",    "date":"6/22~7/22",  "emoji":"♋"},
    {"en":"leo",         "kr":"사자자리",  "date":"7/23~8/22",  "emoji":"♌"},
    {"en":"virgo",       "kr":"처녀자리",  "date":"8/23~9/22",  "emoji":"♍"},
    {"en":"libra",       "kr":"천칭자리",  "date":"9/23~10/22", "emoji":"♎"},
    {"en":"scorpio",     "kr":"전갈자리",  "date":"10/23~11/21","emoji":"♏"},
    {"en":"sagittarius", "kr":"사수자리",  "date":"11/22~12/21","emoji":"♐"},
    {"en":"capricorn",   "kr":"염소자리",  "date":"12/22~1/19", "emoji":"♑"},
    {"en":"aquarius",    "kr":"물병자리",  "date":"1/20~2/18",  "emoji":"♒"},
    {"en":"pisces",      "kr":"물고기자리","date":"2/19~3/20",  "emoji":"♓"},
]

def _make_chinese_years(base_year: int) -> str:
    """base_year부터 12년 주기로 1940년 이후 ~ 미래 1주기 연도 생성."""
    START = 1940
    current_year = now_kst().year
    # base_year에서 START 이후 첫 해당 연도 찾기
    y = base_year
    while y < START:
        y += 12
    years = []
    while y <= current_year + 12:
        years.append(str(y))
        y += 12
    return ",".join(years)

# 각 띠의 기준 연도(1900년대 최초 해당 연도)
_CHINESE_BASE = {
    "rat":1900,"ox":1901,"tiger":1902,"rabbit":1903,
    "dragon":1904,"snake":1905,"horse":1906,"sheep":1907,
    "monkey":1908,"rooster":1909,"dog":1910,"pig":1911,
}

CHINESE = [
    {"en":"rat",     "kr":"쥐띠",    "year":_make_chinese_years(_CHINESE_BASE["rat"]),     "emoji":"🐭"},
    {"en":"ox",      "kr":"소띠",    "year":_make_chinese_years(_CHINESE_BASE["ox"]),      "emoji":"🐮"},
    {"en":"tiger",   "kr":"호랑이띠","year":_make_chinese_years(_CHINESE_BASE["tiger"]),   "emoji":"🐯"},
    {"en":"rabbit",  "kr":"토끼띠",  "year":_make_chinese_years(_CHINESE_BASE["rabbit"]),  "emoji":"🐰"},
    {"en":"dragon",  "kr":"용띠",    "year":_make_chinese_years(_CHINESE_BASE["dragon"]),  "emoji":"🐲"},
    {"en":"snake",   "kr":"뱀띠",    "year":_make_chinese_years(_CHINESE_BASE["snake"]),   "emoji":"🐍"},
    {"en":"horse",   "kr":"말띠",    "year":_make_chinese_years(_CHINESE_BASE["horse"]),   "emoji":"🐴"},
    {"en":"sheep",   "kr":"양띠",    "year":_make_chinese_years(_CHINESE_BASE["sheep"]),   "emoji":"🐑"},
    {"en":"monkey",  "kr":"원숭이띠","year":_make_chinese_years(_CHINESE_BASE["monkey"]),  "emoji":"🐵"},
    {"en":"rooster", "kr":"닭띠",    "year":_make_chinese_years(_CHINESE_BASE["rooster"]), "emoji":"🐓"},
    {"en":"dog",     "kr":"개띠",    "year":_make_chinese_years(_CHINESE_BASE["dog"]),     "emoji":"🐶"},
    {"en":"pig",     "kr":"돼지띠",  "year":_make_chinese_years(_CHINESE_BASE["pig"]),     "emoji":"🐷"},
]

RATINGS = ["★★★☆☆","★★★★☆","★★★★★","★★☆☆☆","★★★★☆","★★★☆☆"]

# ═══════════════════════════════════════════════════════════════════
# ① 요일·월 보정값 (수치 계산 근거 제공)
# ═══════════════════════════════════════════════════════════════════
# 요일별 각 운세 보정치 (월=0 ~ 일=6)
# 값의 의미: 기본 CSV 점수에 더하거나 뺄 보정 포인트
_DOW_ADJUST = {
    # (총운, 금전, 건강, 연애)
    0: ( 2, -3,  4,  1),   # 월: 체력 회복 유리, 금전 신중
    1: ( 4,  5,  2,  2),   # 화: 전반적 상승, 금전 특히 활발
    2: (-2,  3, -1,  4),   # 수: 연애 활성, 컨디션 주의
    3: ( 5,  4,  3,  3),   # 목: 주 최고 에너지, 결정에 유리
    4: ( 3,  6,  1,  5),   # 금: 연애·금전 동반 상승
    5: (-3, -4,  5,  3),   # 토: 건강 투자 유리, 충동 소비 주의
    6: (-1, -5,  6, -2),   # 일: 휴식·회복 최적, 금전 보수적
}
# 월별 전체 운세 분위기 보정 (1~12월)
_MON_ADJUST = {
    1:  3,   # 1월: 새해 상승 에너지
    2: -2,   # 2월: 전환기, 소폭 하락
    3:  4,   # 3월: 봄 시작, 활력 상승
    4:  2,   # 4월: 안정적 흐름
    5:  5,   # 5월: 연중 최고 활동기
    6:  1,   # 6월: 소강 상태
    7: -1,   # 7월: 여름 무기력 구간
    8:  0,   # 8월: 중립
    9:  3,   # 9월: 하반기 재도약
    10: 4,   # 10월: 결실의 계절
    11: 2,   # 11월: 마무리 에너지 상승
    12:-3,   # 12월: 연말 소진, 재충전 필요
}
# 시간대 추천 문구 (요일·보정값 기반)
_DOW_GOLDEN_TIME = {
    0: "오전 10시~12시 (주초 집중력이 살아있는 황금 타임)",
    1: "오후 2시~4시 (화요일 오후 업무 추진력 최고조)",
    2: "오전 9시~11시 (수요일 오전 창의력 활성 구간)",
    3: "오전 10시~오후 1시 (목요일 전체 에너지 피크 타임)",
    4: "오후 3시~6시 (금요일 대인관계·마무리 최적 시간)",
    5: "오전 7시~10시 (토요일 이른 아침, 하루 에너지 충전 타임)",
    6: "오후 4시~7시 (일요일 저녁, 내일을 위한 준비 골든타임)",
}

def _apply_adjustments(total, money, health, love):
    """요일·월 보정을 적용해 최종 지수 및 계산 내역을 반환"""
    kst = now_kst()
    dow = kst.weekday()   # 0=월 … 6=일
    mon = kst.month
    dt, dm, dh, dl = _DOW_ADJUST[dow]
    ma = _MON_ADJUST[mon]
    dow_names = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"]
    mon_names = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"]

    # 보정 적용 (0~100 클램프)
    adj_total  = max(1, min(100, total  + dt + ma))
    adj_money  = max(1, min(100, money  + dm + ma))
    adj_health = max(1, min(100, health + dh + ma))
    adj_love   = max(1, min(100, love   + dl + ma))

    golden = _DOW_GOLDEN_TIME[dow]
    dow_sign = "▲" if dt >= 0 else "▼"
    mon_sign = "▲" if ma >= 0 else "▼"

    # 계산 내역 HTML (포스팅에 삽입할 수치 근거 카드)
    calc_html = f'''
<div class="card" style="background:#f8faff;border-left:5px solid #3b82f6">
  <span class="badge" style="background:#dbeafe;color:#1d4ed8">📐 오늘의 운세 지수 계산 방식</span>
  <div style="margin-top:12px;font-size:13px;color:#374151;line-height:1.9">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
      <div style="background:#fff;border-radius:8px;padding:10px;border:1px solid #e5e7eb">
        <div style="font-size:11px;color:#6b7280;margin-bottom:4px">📅 요일 보정 ({dow_names[dow]})</div>
        <div style="font-weight:700;color:#1d4ed8">{dow_sign} 총운 {abs(dt):+d} · 금전 {abs(dm):+d} · 건강 {abs(dh):+d} · 연애 {abs(dl):+d}</div>
      </div>
      <div style="background:#fff;border-radius:8px;padding:10px;border:1px solid #e5e7eb">
        <div style="font-size:11px;color:#6b7280;margin-bottom:4px">🗓 월별 분위기 ({mon_names[mon-1]})</div>
        <div style="font-weight:700;color:#7c3aed">{mon_sign} 전체 지수 {ma:+d}점 조정</div>
      </div>
    </div>
    <div style="background:#eff6ff;border-radius:8px;padding:10px;margin-bottom:10px">
      <div style="font-size:12px;color:#1e40af;font-weight:600;margin-bottom:6px">🔢 최종 보정 지수</div>
      <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:13px">
        <span>🌟 종합 <b>{adj_total}점</b> <span style="font-size:11px;color:#6b7280">(기본 {total} {dt+ma:+d})</span></span>
        <span>💰 금전 <b>{adj_money}점</b> <span style="font-size:11px;color:#6b7280">(기본 {money} {dm+ma:+d})</span></span>
        <span>💪 건강 <b>{adj_health}점</b> <span style="font-size:11px;color:#6b7280">(기본 {health} {dh+ma:+d})</span></span>
        <span>❤️ 연애 <b>{adj_love}점</b> <span style="font-size:11px;color:#6b7280">(기본 {love} {dl+ma:+d})</span></span>
      </div>
    </div>
    <div style="font-size:12px;color:#374151">
      ⏰ <b>오늘의 골든 타임:</b> {golden}
    </div>
  </div>
</div>'''
    return adj_total, adj_money, adj_health, adj_love, calc_html


# ═══════════════════════════════════════════════════════════════════
# ② 색상별·아이템별 효과 매핑 딕셔너리 (VLOOKUP 대체 로직)
# ═══════════════════════════════════════════════════════════════════
# 색상명 → (효과 영역, 운세 타입, 상승 %, 추천 아이템 목록, 착용/활용법)
COLOR_EFFECT = {
    "골드":      ("자신감과 풍요로움", "금전·사업운", 18,
                  "골드 시계·반지·명함케이스·금색 볼펜",
                  "오늘 중요한 미팅이나 협상 자리에 골드 소품을 하나 챙겨보세요. 시선을 끄는 동시에 자신감 있는 인상을 줍니다."),
    "라벤더":    ("차분함과 직관력",   "대인관계·연애운", 15,
                  "라벤더 향수·스카프·쿠션·노트",
                  "오늘 감정 기복이 있을 수 있습니다. 라벤더 계열 소품을 가까이 두면 마음이 안정되고 상대방에게도 편안한 인상을 줍니다."),
    "민트그린":  ("회복력과 신선함",   "건강·활력", 14,
                  "민트 계열 텀블러·수첩·에코백",
                  "점심 먹고 나면 괜히 늘어지는 날이에요. 민트 계열 텀블러나 소품 하나 책상에 두면 오후가 조금 달라집니다."),
    "스카이블루": ("소통과 신뢰감",    "연애·대인관계운", 16,
                  "하늘색 셔츠·파우치·손수건·이어폰케이스",
                  "오늘 말 한마디가 중요한 날입니다. 스카이블루 소품을 착용하면 신뢰감 있는 이미지를 전달하는 데 도움이 됩니다."),
    "코랄":      ("활력과 긍정 에너지","연애·사교운", 20,
                  "코랄 립스틱·귀걸이·가방·파일케이스",
                  "활기찬 분위기를 만들고 싶은 날에 코랄 컬러가 빛을 발합니다. 새로운 만남이 있는 자리에 특히 효과적입니다."),
    "퍼플":      ("창의력과 직관",     "아이디어·예술운", 13,
                  "보라색 다이어리·마스킹테이프·파우치",
                  "오늘 아이디어가 샘솟는 날입니다. 퍼플 계열 소품을 책상에 두면 창의적인 사고를 촉진하는 데 도움이 됩니다."),
    "로즈핑크":  ("사랑과 감수성",     "연애·감성운", 19,
                  "로즈핑크 핸드크림·메모지·파우치·양말",
                  "감수성이 풍부해지는 날입니다. 소중한 사람에게 작은 선물이나 메시지를 전해보세요. 로즈핑크 소품이 따뜻한 분위기를 만들어 줍니다."),
    "버건디":    ("깊이감과 카리스마", "직장·사업운", 17,
                  "버건디 넥타이·머플러·다이어리·케이스",
                  "중요한 프레젠테이션이나 보고가 있는 날 버건디 소품은 신뢰감과 전문성을 높여줍니다."),
    "웜그레이":  ("집중력과 안정감",   "업무 효율·직장운", 12,
                  "회색 계열 노트북 파우치·머그컵·마우스패드",
                  "오늘 집중이 필요한 업무가 있다면 웜그레이 소품으로 데스크를 정리해 보세요. 산만함을 줄이고 집중력을 높여줍니다."),
    "화이트":    ("청결함과 새 시작",  "정신 건강·리셋", 11,
                  "흰색 노트·손수건·텀블러·파우치",
                  "머릿속이 복잡하게 느껴지는 날이에요. 책상 위 물건 하나만 치워보세요. 공간이 정리되면 생각도 따라 정리됩니다."),
    "딥블루":    ("집중과 냉철한 판단","직장·금전 결정운", 15,
                  "네이비 지갑·볼펜·파일·넥타이",
                  "중요한 결정이나 계약이 있는 날이에요. 딥블루 계열을 하나 걸치면 말투가 자연스럽게 차분해지는 효과가 있어요."),
    "오렌지":    ("열정과 도전",       "활동·창업·도전운", 16,
                  "오렌지 계열 파우치·케이스·스티커·양말",
                  "뭔가 시작하고 싶은데 첫 발이 안 떨어지는 날이에요. 오렌지 소품 하나 곁에 두고, 일단 파일부터 열어보세요."),
    "그린":      ("성장과 치유",       "건강·금전 성장운", 13,
                  "초록색 화분·텀블러·노트·에코백",
                  "자연의 기운이 필요한 날입니다. 작은 화분 하나를 책상에 두거나 그린 계열 소품을 활용해 보세요."),
}

# 행운 아이템 → 사용법 매핑 (아이템 키워드 기반 매칭)
ITEM_USAGE = [
    # (키워드 리스트, 사용법 설명)
    (["수정","크리스탈","돌","원석"],
     "오늘 수정은 왼손에 쥐거나 주머니에 넣어 다니세요. 머릿속이 복잡한 날일수록 손에 뭔가 잡히는 게 생각보다 집중에 도움이 돼요."),
    (["동전","코인"],
     "지갑 깊숙이 넣어 두세요. 작은 거지만 '돈 자리를 비워두지 않는다'는 감각이 오늘 지출 습관을 조금 달리 만들어줘요."),
    (["꽃","꽃잎","식물","화분"],
     "오늘 책상이나 창가에 꽃이나 식물 하나 두세요. 눈에 초록이 들어오는 것만으로도 기분이 조금 달라지는 날이에요."),
    (["반지","팔찌","목걸이","귀걸이","주얼리"],
     "오늘 이 아이템 착용할 때 잠깐 거울 한 번만 보세요. '오늘 나 괜찮다'는 생각 하나가 하루 분위기를 바꾸는 경우 있어요."),
    (["향초","향","아로마"],
     "아침에 5분만 켜두세요. 후각이 뇌를 자극하거든요. 향 하나로 오전 집중력이 눈에 띄게 달라지는 사람들 꽤 있어요."),
    (["거울","미러"],
     "외출 전 거울 한 번만 똑바로 보세요. '잘 될 거야'보다 그냥 '오늘도 나 왔네'라는 느낌으로요. 그걸로 충분해요."),
    (["책","노트","수첩","다이어리"],
     "오늘 머릿속에 맴도는 것들 짧게라도 적어보세요. 생각이 글이 되면 무게가 달라져요. 나중에 보면 의외로 도움이 됩니다."),
    (["열쇠","키"],
     "오늘 막혀있던 일의 실마리가 뜻밖의 방향에서 나올 수 있어요. 고집 부리던 방향 한 번만 바꿔보세요. 그게 오늘의 열쇠예요."),
    (["조약돌","돌","스톤"],
     "힘들 때 손으로 쥐어보세요. 이상하게 들리겠지만 손에 뭔가 잡히는 감각이 마음을 차분하게 만들어주는 경우가 있어요."),
]

def get_color_guide(color_name):
    """행운 색상 → 활용 가이드 문자열 반환"""
    info = COLOR_EFFECT.get(color_name)
    if not info:
        # 부분 매칭 시도
        for key, val in COLOR_EFFECT.items():
            if key in color_name or color_name in key:
                info = val
                break
    if info:
        effect_area, fortune_type, boost_pct, items, usage = info
        return (
            f"오늘 행운 색상은 <b>'{color_name}'</b>이에요. "
            f"{items} 중 하나를 오늘 곁에 두거나 착용해보세요. "
            f"{usage}"
        )
    return f"오늘 '{color_name}' 컬러를 소품이나 옷에 하나 곁에 두세요. 묘하게 기분이 달라지는 날이에요."

def get_item_guide(item_name):
    """행운 아이템 → 활용법 문자열 반환"""
    item_lower = str(item_name)
    for keywords, usage in ITEM_USAGE:
        if any(kw in item_lower for kw in keywords):
            return usage
    return f"오늘 '{item_name}' 가방이나 책상 위에 두세요. 작은 거지만 오늘은 그 자리가 의미 있어요."


# ═══════════════════════════════════════════════════════════════════
# ③ 별자리 배경 지식 딕셔너리 (포스팅 하단 고정 카드용)
# ═══════════════════════════════════════════════════════════════════
ZODIAC_INFO = {
    "양자리": {
        "element": "불 (Fire)", "ruling": "화성 (Mars)",
        "trait": "행동력과 추진력이 넘치는 리더형 별자리입니다. 새로운 도전을 두려워하지 않는 용감함이 최대 강점입니다.",
        "strength": "결단력, 열정, 리더십, 개척 정신",
        "weakness": "성급함, 지속력 부족, 충동적 결정",
        "compatible": "사자자리, 사수자리, 쌍둥이자리",
        "tip": "오늘 중요한 결정을 내리기 전에 3초만 멈추는 습관을 만들어 보세요. 딱 10분만 기다려보세요. 충동적으로 결정하고 싶은 순간일수록 잠깐 멈추는 게 오늘은 맞아요.",
        "color": "빨간색, 오렌지", "stone": "다이아몬드, 루비", "number": "1, 9",
    },
    "황소자리": {
        "element": "흙 (Earth)", "ruling": "금성 (Venus)",
        "trait": "안정과 신뢰를 중시하는 현실주의자입니다. 한번 시작한 일은 끝까지 해내는 끈기와 성실함이 빛납니다.",
        "strength": "인내심, 신뢰성, 현실 감각, 심미안",
        "weakness": "고집스러움, 변화 거부, 소유욕",
        "compatible": "처녀자리, 염소자리, 게자리",
        "tip": "오늘 새로운 방식을 한 가지만 시도해 보세요. 변하기 싫어도 딱 한 가지만 다르게 해보세요. 생각보다 안 무너집니다.",
        "color": "초록색, 베이지", "stone": "에메랄드, 로즈쿼츠", "number": "2, 6",
    },
    "쌍둥이자리": {
        "element": "공기 (Air)", "ruling": "수성 (Mercury)",
        "trait": "지적 호기심과 소통 능력이 뛰어난 다재다능한 별자리입니다. 상황에 따라 유연하게 적응하는 능력이 탁월합니다.",
        "strength": "적응력, 커뮤니케이션 능력, 창의성, 유머",
        "weakness": "변덕, 집중력 부족, 우유부단함",
        "compatible": "천칭자리, 물병자리, 양자리",
        "tip": "오늘 여러 가지에 손대기보다 딱 두 가지에만 집중해 보세요. 오늘 할 일 목록 열 개 있으면 두 개만 남기세요. 집중이 성과를 만드는 날이에요.",
        "color": "노란색, 하늘색", "stone": "아게이트, 시트린", "number": "3, 5",
    },
    "게자리": {
        "element": "물 (Water)", "ruling": "달 (Moon)",
        "trait": "감수성과 공감 능력이 풍부한 보살핌의 별자리입니다. 가족과 소중한 사람을 위해 헌신하는 따뜻한 마음이 특징입니다.",
        "strength": "공감력, 직관력, 보살핌, 기억력",
        "weakness": "감정 기복, 소극성, 과도한 집착",
        "compatible": "전갈자리, 물고기자리, 황소자리",
        "tip": "오늘 자신을 돌보는 시간을 꼭 만들어 보세요. 오늘 남 챙기다 본인 밥은 챙겼어요? 본인 먼저 챙기는 게 오늘은 더 중요해요.",
        "color": "은색, 흰색", "stone": "문스톤, 진주", "number": "2, 7",
    },
    "사자자리": {
        "element": "불 (Fire)", "ruling": "태양 (Sun)",
        "trait": "카리스마와 자신감이 넘치는 무대의 주인공 별자리입니다. 타고난 리더십으로 주변을 밝히고 이끄는 힘이 있습니다.",
        "strength": "카리스마, 관대함, 창의력, 자신감",
        "weakness": "자존심, 지나친 인정 욕구, 고집",
        "compatible": "양자리, 사수자리, 쌍둥이자리",
        "tip": "오늘 다른 사람의 의견도 주인공처럼 들어주세요. 오늘 회의나 대화에서 말하기 전에 한 번만 더 들어보세요. 말투가 달라지면 분위기가 달라져요.",
        "color": "금색, 주황색", "stone": "루비, 호박", "number": "1, 4",
    },
    "처녀자리": {
        "element": "흙 (Earth)", "ruling": "수성 (Mercury)",
        "trait": "분석력과 완벽주의적 성향을 지닌 세심한 별자리입니다. 디테일을 놓치지 않는 꼼꼼함이 큰 강점입니다.",
        "strength": "분석력, 성실함, 실용성, 정확성",
        "weakness": "완벽주의, 지나친 비판, 걱정이 많음",
        "compatible": "황소자리, 염소자리, 게자리",
        "tip": "오늘 '80%면 충분하다'는 마음을 가져보세요. 오늘 80%에서 멈추고 내보내세요. 완성이 완벽보다 오늘은 더 낫습니다.",
        "color": "네이비, 회색", "stone": "사파이어, 카넬리안", "number": "5, 6",
    },
    "천칭자리": {
        "element": "공기 (Air)", "ruling": "금성 (Venus)",
        "trait": "균형과 조화를 중시하는 외교적 별자리입니다. 아름다움과 공정함에 대한 감각이 뛰어나며 관계를 소중히 여깁니다.",
        "strength": "균형 감각, 외교력, 심미안, 협력",
        "weakness": "우유부단함, 갈등 회피, 의존성",
        "compatible": "쌍둥이자리, 물병자리, 사수자리",
        "tip": "오늘 결정을 미루고 싶어지는 순간이 오면, '이것이 내가 원하는 것인가'를 먼저 물어보세요. 결정 못 하고 계속 미루고 있는 게 있으면 오늘 안에 하나만 끝내세요. 직감이 맞는 날이에요.",
        "color": "파스텔 핑크, 라벤더", "stone": "오팔, 로즈쿼츠", "number": "6, 9",
    },
    "전갈자리": {
        "element": "물 (Water)", "ruling": "명왕성 (Pluto)",
        "trait": "깊이 있는 통찰력과 강인한 의지를 지닌 신비의 별자리입니다. 한번 목표를 정하면 어떤 어려움도 뚫고 나가는 집중력이 있습니다.",
        "strength": "통찰력, 집중력, 강인함, 변화 적응력",
        "weakness": "집착, 의심, 복수심, 비밀주의",
        "compatible": "게자리, 물고기자리, 염소자리",
        "tip": "오늘 신뢰하는 사람에게 마음을 조금 열어보세요. 오늘 말투가 평소보다 차갑게 나가고 있지는 않은지 확인해보세요. 눈치 빠른 상대는 이미 느끼고 있어요.",
        "color": "검정, 진홍색", "stone": "토파즈, 옵시디언", "number": "8, 11",
    },
    "사수자리": {
        "element": "불 (Fire)", "ruling": "목성 (Jupiter)",
        "trait": "자유와 모험을 사랑하는 낙관주의 별자리입니다. 넓은 시야로 세상을 바라보며 끊임없이 새로운 지식과 경험을 추구합니다.",
        "strength": "낙관성, 철학적 사고, 모험심, 솔직함",
        "weakness": "무책임함, 성급한 약속, 무신경함",
        "compatible": "양자리, 사자자리, 물병자리",
        "tip": "오늘 약속은 지킬 수 있는 것만 하세요. 무리한 부탁이 들어오면 '오늘은 좀 어려워요'라고 짧게 말하세요. 의리보다 솔직함이 관계를 오래 가게 해요.",
        "color": "보라색, 파란색", "stone": "터키석, 라피스라줄리", "number": "3, 9",
    },
    "염소자리": {
        "element": "흙 (Earth)", "ruling": "토성 (Saturn)",
        "trait": "책임감과 인내로 목표를 향해 묵묵히 나아가는 별자리입니다. 시간이 걸리더라도 반드시 정상에 오르는 지구력이 특징입니다.",
        "strength": "책임감, 인내심, 실용성, 야망",
        "weakness": "고집, 지나친 실용주의, 감정 억제",
        "compatible": "황소자리, 처녀자리, 전갈자리",
        "tip": "오늘 일에서 잠시 손을 떼고 쉬어가는 것도 전략입니다. 너무 오래 달려왔다면 오늘만큼은 속도를 줄여도 됩니다. 멈추는 게 아니라 더 오래 가기 위한 거예요.",
        "color": "갈색, 카키", "stone": "가넷, 호안석", "number": "8, 10",
    },
    "물병자리": {
        "element": "공기 (Air)", "ruling": "천왕성 (Uranus)",
        "trait": "독창성과 혁신적 사고를 지닌 미래 지향적 별자리입니다. 기존의 틀을 깨고 새로운 방식으로 세상을 바라보는 능력이 있습니다.",
        "strength": "독창성, 인도주의, 미래 지향, 개방성",
        "weakness": "감정 표현 어려움, 고집, 거리감",
        "compatible": "쌍둥이자리, 천칭자리, 사수자리",
        "tip": "오늘 아이디어가 너무 앞서간다 싶으면 주변 사람이 이해할 수 있게 설명하는 연습을 해보세요. 아이디어가 너무 앞서간다 싶으면, 먼저 메모해두세요. 상대가 따라올 준비가 됐을 때 꺼내는 게 맞아요.",
        "color": "일렉트릭 블루, 청록색", "stone": "아메시스트, 아쿠아마린", "number": "4, 7",
    },
    "물고기자리": {
        "element": "물 (Water)", "ruling": "해왕성 (Neptune)",
        "trait": "공감 능력이 탁월하고 예술적 감수성이 풍부한 별자리입니다. 타인의 감정을 직관적으로 읽어내는 능력이 탁월합니다.",
        "strength": "직관력, 창의성, 공감력, 헌신",
        "weakness": "우유부단함, 현실 도피, 감정 기복",
        "compatible": "게자리, 전갈자리, 황소자리",
        "tip": "오늘 감정에 치우치지 않도록 하루 한 번 '지금 내 감정이 사실인가'를 점검하세요. 오늘 감이 강하게 오는 순간이 있으면 믿되, 확인은 꼭 하세요. 직감과 사실 확인이 같이 갈 때 실수가 줄어요.",
        "color": "바다색, 연보라", "stone": "아쿠아마린, 문스톤", "number": "7, 12",
    },
}

def zodiac_info_card(z_kr, emoji):
    """별자리 배경 지식 카드 HTML 생성"""
    info = ZODIAC_INFO.get(z_kr)
    if not info:
        return ""
    return f'''
<div class="card" style="background:linear-gradient(135deg,#faf5ff,#eff6ff);border-left:5px solid #7c3aed">
  <span class="badge" style="background:#ede9fe;color:#5b21b6">
    {emoji} {z_kr} 기본 정보
  </span>
  <div style="margin-top:14px;display:grid;gap:10px">

    <div style="font-size:14px;color:#374151;line-height:1.85">
      {info["trait"]}
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px">
      <div style="background:#fff;border-radius:8px;padding:10px;border:1px solid #ede9fe">
        <div style="color:#7c3aed;font-weight:700;margin-bottom:4px">🌿 원소 · 지배성</div>
        <div style="color:#374151">{info["element"]}</div>
        <div style="color:#374151">{info["ruling"]}</div>
      </div>
      <div style="background:#fff;border-radius:8px;padding:10px;border:1px solid #dbeafe">
        <div style="color:#1d4ed8;font-weight:700;margin-bottom:4px">💎 행운 스톤 · 숫자</div>
        <div style="color:#374151">{info["stone"]}</div>
        <div style="color:#374151">행운 숫자: {info["number"]}</div>
      </div>
    </div>

    <div style="background:#fff;border-radius:8px;padding:10px;border:1px solid #d1fae5;font-size:13px">
      <div style="color:#065f46;font-weight:700;margin-bottom:4px">✅ 강점</div>
      <div style="color:#374151">{info["strength"]}</div>
    </div>

    <div style="background:#fff;border-radius:8px;padding:10px;border:1px solid #fee2e2;font-size:13px">
      <div style="color:#991b1b;font-weight:700;margin-bottom:4px">⚠️ 주의할 점</div>
      <div style="color:#374151">{info["weakness"]}</div>
    </div>

    <div style="background:#fff;border-radius:8px;padding:10px;border:1px solid #fef3c7;font-size:13px">
      <div style="color:#92400e;font-weight:700;margin-bottom:4px">💑 궁합 좋은 별자리</div>
      <div style="color:#374151">{info["compatible"]}</div>
    </div>

    <div style="background:linear-gradient(135deg,#7c3aed15,#1d4ed815);border-radius:8px;
                padding:12px;border:1px solid #c4b5fd;font-size:13px;line-height:1.8">
      <div style="color:#5b21b6;font-weight:700;margin-bottom:6px">💡 오늘의 {z_kr} 조언</div>
      <div style="color:#374151">{info["tip"]}</div>
    </div>

  </div>
</div>'''


# ─────────────────────────────────────────
# 유틸 함수
# ─────────────────────────────────────────
def sentence():
    pool = []
    for df in [fortune_emotion, fortune_1000, fortune_4000]:
        if not df.empty and 'sentence' in df.columns:
            pool += df['sentence'].dropna().tolist()
    return random.choice(pool) if pool else "오늘도 좋은 하루 되세요."

def pick_quote():
    """fortune_quotes_10000.csv에서 오늘의 명언 랜덤 선택"""
    if not fortune_quotes.empty and 'quote_ko' in fortune_quotes.columns:
        row = fortune_quotes.sample(1).iloc[0]
        quote = row['quote_ko']
        meaning = row.get('meaning', '')
        category = row.get('category', '')
        return quote, meaning, category
    return sentence(), "", ""

def daily_fortune():
    today = now_kst().strftime("%Y-%m-%d")
    for df in [daily_365, fortune_365]:
        if not df.empty and 'date' in df.columns:
            m = df[df['date'] == today]
            if not m.empty:
                return m.iloc[0]['fortune']
    return sentence()

def zodiac_fortune(kr_name):
    if not zodiac_kr.empty and 'zodiac' in zodiac_kr.columns:
        m = zodiac_kr[zodiac_kr['zodiac'] == kr_name]
        if not m.empty:
            text = m.sample(1).iloc[0]['fortune']
            # 줄바꿈을 HTML <br><br>로 변환
            return str(text).replace('\n\n', '<br><br>').replace('\n', '<br>')
    return sentence()

def chinese_fortune(en_name):
    if not chinese_zodiac.empty:
        m = chinese_zodiac[chinese_zodiac['animal_zodiac'] == en_name]
        if not m.empty:
            return m.sample(1).iloc[0]['fortune']
    return sentence()

# ═══════════════════════════════════════════════════════════════════
# 별자리별 고유 성격 기반 현실 디테일 풀 (AI 티 제거 + "헉 맞는데?" 포인트)
# ═══════════════════════════════════════════════════════════════════

# ── 별자리별 구어체 오프닝 (사람이 쓴 느낌, 각 별자리 성격 반영) ──
_ZODIAC_HUMAN_VOICE = {
    "양자리": [
        "솔직히 오늘 아침부터 뭔가 답답한 느낌 들지 않으셨어요?",
        "오늘 유독 참을 성이 없어지는 날이에요. 그거 당신 잘못 아닙니다.",
        "새로 뭔가 시작하고 싶은 충동이 생기는 날이에요. 나쁘지 않아요, 근데 지갑은 닫으세요.",
        "요즘 빨리 결과가 나오길 기다리다 지친 것 같아요. 오늘 한 가지만 실행해 보세요. 작아도 움직이는 것 자체가 흐름을 만듭니다.",
    ],
    "황소자리": [
        "오늘 유독 '이거 꼭 사야 해' 싶은 물건이 눈에 밟힌다면, 내일 다시 보세요.",
        "변하기 싫은 건데 상황이 바뀌려 하면 괜히 짜증나는 날이에요. 자연스러운 거예요.",
        "오늘은 사실 혼자 있는 게 제일 편할 날입니다. 억지로 맞출 필요 없어요.",
        "요즘 혼자 버티는 느낌이 강했을 수 있어요. 오늘 저녁 한 가지 작은 것으로 자신을 챙겨 보세요. 큰 거 아니어도 됩니다.",
    ],
    "쌍둥이자리": [
        "오늘 대화 중에 말이 너무 많아지거나, 반대로 갑자기 하기 싫어지는 순간이 올 수 있어요.",
        "머릿속에서 생각이 10개씩 동시에 돌아가는 날이에요. 그중 딱 2개만 오늘 처리하면 됩니다.",
        "갑자기 옛날 연락처를 열어보고 싶어지는 날이에요. 한 번만 더 생각하고 누르세요.",
        "오늘 여러 가지가 동시에 들어와서 뭐부터 해야 할지 모르는 상태일 수 있어요. 그 중에서 오늘 안에 끝낼 수 있는 것 하나만 먼저 골라보세요.",
    ],
    "게자리": [
        "오늘은 이유 없이 감수성이 올라오는 날이에요. 그냥 느끼게 두세요, 다 이유가 있습니다.",
        "누군가 지나가는 말 한마디가 오늘은 유독 마음에 걸릴 수 있어요. 의도를 먼저 확인해보세요.",
        "오늘 집에서 뭔가 따뜻한 거 먹고 싶은 날이에요. 그 감각, 무시하지 마세요.",
        "남 챙기다 자신은 못 챙긴 날들이 쌓여서 오늘 유독 지친 것 같아요. 오늘만큼은 나 먼저 챙겨도 됩니다.",
    ],
    "사자자리": [
        "오늘 내가 당연히 인정받아야 하는데 그렇지 않으면 유독 속상한 날이에요. 당연한 감정입니다.",
        "솔직히 오늘 약간 빛나고 싶은 날인데, 그 에너지를 잘 쓰면 진짜로 빛납니다.",
        "오늘 혼자 너무 많이 짊어지고 있는 건 아닌지 돌아보세요. 주인공도 쉬어야 합니다.",
        "열심히 했는데 티가 안 나는 것 같아서 답답했을 수 있어요. 오늘 오전에 그게 조금 보이기 시작합니다. 포기하지 말고 조금만 더 보여주세요.",
    ],
    "처녀자리": [
        "오늘 뭔가 찝찝하게 마무리된 일이 계속 머릿속을 맴돌 수 있어요. 완벽주의 모드 잠깐 꺼도 돼요.",
        "남이 대충 한 일이 눈에 밟히는 날이에요. 지적하고 싶은 마음, 오늘만큼은 잠깐 참아보세요.",
        "사실 오늘은 억지로 힘내는 것보다 그냥 조금 쉬어가는 게 더 맞는 날 같아요.",
        "요즘 너무 꼼꼼하게 확인하다 보니 오히려 판단이 늦어지고 있는 건 아닌가요? 오늘 80%에서 한 번 내보내 보세요. 생각보다 괜찮습니다.",
    ],
    "천칭자리": [
        "오늘 결정 못 하고 계속 미루고 있는 게 있지 않으세요? 오늘 안에 하나만 끝내세요.",
        "좋은 게 좋다 싶어서 참았는데 오늘은 괜히 그게 더 억울한 날이에요.",
        "괜히 예민해지는 이유가 있습니다. 오늘은 당신 잘못만은 아닐 수도 있어요.",
        "맞추다 맞추다 지친 날일 수 있어요. 오늘만큼은 솔직하게 '나는 이게 싫어요'라고 말해도 됩니다. 관계가 무너지지 않아요.",
    ],
    "전갈자리": [
        "오늘 누군가의 행동이 뭔가 수상하게 느껴진다면, 그 직감 한 번은 믿어보세요.",
        "겉으로 아무렇지 않은 척하고 있지만 오늘 속으로는 꽤 복잡한 날일 수 있어요.",
        "오늘 말을 꺼내기 전에 한 번 더 생각하는 것만으로 꽤 많은 게 달라집니다.",
        "참아왔던 말이 오늘 터질 것 같은 날이에요. 한 번만 더 참는 게 아니라, 오늘 저녁에 차분하게 꺼내 보세요. 터뜨리는 것과 전달하는 것은 달라요.",
    ],
    "사수자리": [
        "오늘 또 충동적으로 뭔가 계획 세우고 싶어지는 날인데, 이번엔 메모라도 해두세요.",
        "솔직히 오늘 조금 갑갑한 느낌이 드는 날이에요. 잠깐이라도 바깥 바람 쐬면 달라집니다.",
        "오늘은 말 한마디가 생각보다 멀리 퍼지는 날이에요. 농담도 조금 신경 써서 하세요.",
        "뭔가 새로 시작하고 싶은 에너지가 차오르는 날이에요. 그 에너지, 지금 당장 큰 결정에 쓰지 말고 오늘은 아이디어만 정리해 보세요. 실행은 내일부터여도 늦지 않습니다.",
    ],
    "염소자리": [
        "오늘 계획대로 안 풀리는 게 생길 수 있어요. 그래도 당신이 무너질 사람이 아니잖아요.",
        "남들 눈에 안 보이는 데서 열심히 하고 있는 거 알아요. 오늘 그게 조금 보이기 시작합니다.",
        "쉬는 것도 능력이에요. 오늘 하루 무리하지 않는 것 자체가 가장 현명한 선택일 수 있습니다.",
        "너무 오래 달려왔다면 오늘만큼은 속도를 줄여도 됩니다. 멈추는 게 아니에요. 더 오래 가기 위해 페이스를 조절하는 거예요.",
    ],
    "물병자리": [
        "오늘 왜인지 모르게 혼자이고 싶은데 동시에 누군가 알아줬으면 하는 날이에요. 둘 다 자연스러워요.",
        "오늘 아이디어가 갑자기 떠오르면 반드시 메모하세요. 나중에 기억 못 합니다.",
        "남들이 이상하게 볼까봐 못 하고 있는 거 있으면, 오늘 한 번만 그냥 해보세요.",
        "설명하기 피곤한 날이에요. 오늘은 모든 걸 이해시키려 하지 말고, 내 생각을 짧게 메모해두는 것만으로도 오늘은 잘 한 거예요.",
    ],
    "물고기자리": [
        "오늘 감이 유독 잘 맞는 날이에요. 논리보다 직감이 먼저 반응한다면 그쪽을 믿어보세요.",
        "경계가 흐릿해지기 쉬운 날이에요. 내 기분인지 상대 기분인지 헷갈리면 잠깐 혼자 있어보세요.",
        "오늘 유독 감성적인 콘텐츠나 음악이 당기는 날이에요. 그냥 느끼게 두세요.",
        "누군가의 부탁을 또 들어주다 내 것을 못 챙긴 날일 수 있어요. 오늘만큼은 거절해도 됩니다. 상대도 이해합니다.",
    ],
}

# ── "헉 맞는데?" 현실 디테일 블록 (별자리별) ──
_ZODIAC_REAL_DETAIL = {
    "양자리": {
        "contact_time": "오후 1시~3시",
        "money_leak": "충동적으로 '일단 담아놓고 보기'",
        "annoying_person": "말은 맞는데 타이밍이 너무 늦은 사람",
        "regret_tonight": "화가 난 상태에서 보낸 메시지",
    },
    "황소자리": {
        "contact_time": "저녁 7시~9시",
        "money_leak": "할인이라는 이유만으로 사는 물건",
        "annoying_person": "갑자기 계획을 바꾸자는 사람",
        "regret_tonight": "잠들기 전 떠올리는 '그때 그 말 왜 했을까'",
    },
    "쌍둥이자리": {
        "contact_time": "오전 10시~낮 12시",
        "money_leak": "앱에서 '오늘만' 뜨는 세일",
        "annoying_person": "대화 중에 핸드폰 보는 사람",
        "regret_tonight": "너무 많이 말해버린 것",
    },
    "게자리": {
        "contact_time": "저녁 8시~10시",
        "money_leak": "선물 사다가 내 것도 같이 사기",
        "annoying_person": "무심코 던진 말이 칼처럼 박히는 사람",
        "regret_tonight": "말했어야 했는데 못 한 것",
    },
    "사자자리": {
        "contact_time": "오후 2시~4시",
        "money_leak": "분위기상 내가 계산하는 상황",
        "annoying_person": "공은 다 가져가고 실수는 남기는 사람",
        "regret_tonight": "너무 크게 반응한 것",
    },
    "처녀자리": {
        "contact_time": "오전 9시~11시",
        "money_leak": "더 좋은 버전이 있을 것 같아 계속 검색하기",
        "annoying_person": "대충 마무리하고 OK라는 사람",
        "regret_tonight": "완벽하게 못 끝낸 일 목록 떠올리기",
    },
    "천칭자리": {
        "contact_time": "오후 4시~6시",
        "money_leak": "분위기 맞추다가 원하지 않는 걸 같이 구매",
        "annoying_person": "당신한테만 솔직한 척하는 사람",
        "regret_tonight": "확실하게 말하지 못한 것",
    },
    "전갈자리": {
        "contact_time": "밤 9시~11시",
        "money_leak": "감정이 격해진 상태에서의 충동구매",
        "annoying_person": "속 빤히 보이는데 모르는 척하는 사람",
        "regret_tonight": "참을 걸 괜히 말해버린 것",
    },
    "사수자리": {
        "contact_time": "낮 12시~오후 2시",
        "money_leak": "여행·경험·체험 관련 즉흥 결제",
        "annoying_person": "왜 그렇게 해야 하냐고 묻는 사람",
        "regret_tonight": "또 미루기로 한 것",
    },
    "염소자리": {
        "contact_time": "오전 8시~10시",
        "money_leak": "장기적으로 필요하다는 명목의 과소비",
        "annoying_person": "결과 없이 과정만 나열하는 사람",
        "regret_tonight": "쉬지 않고 무리한 것",
    },
    "물병자리": {
        "contact_time": "오후 3시~5시",
        "money_leak": "독특하고 특이해서 사는 물건",
        "annoying_person": "틀에 박힌 방식만 고집하는 사람",
        "regret_tonight": "설명을 생략했더니 오해가 생긴 것",
    },
    "물고기자리": {
        "contact_time": "저녁 6시~8시",
        "money_leak": "누군가를 위한다는 이유로 쓰는 돈",
        "annoying_person": "감정을 숫자로만 판단하는 사람",
        "regret_tonight": "경계를 지키지 못한 것",
    },
}

# ── 띠별 고유 구어체 오프닝 ──
_CHINESE_HUMAN_VOICE = {
    "쥐띠": [
        "오늘 뭔가 기회가 보이는데 타이밍을 못 잡고 있는 느낌 드시나요?",
        "머리가 너무 빠르게 돌아가다 보니 오히려 결정이 늦어지는 날이에요.",
        "오늘은 계산보다 직감이 먼저인 날이에요. 두 번 생각하면 이미 늦습니다.",
        "생각 못 한 사람이 오늘 먼저 연락해 올 수 있어요. 그 연락, 흘려보내지 마세요.",
        "오늘 정보가 하나 들어오면 바로 메모하세요. 머릿속에 두면 오늘 저녁쯤 증발합니다.",
    ],
    "소띠": [
        "오늘 조용히 혼자 처리하고 싶은 일이 생길 수 있어요. 그렇게 해도 됩니다.",
        "변하기 싫은 마음은 이해하는데, 오늘 딱 하나만 새로운 방식으로 해보세요.",
        "당신이 말없이 해온 일들이 오늘 슬며시 빛을 발하기 시작합니다.",
        "오래된 일이 오늘 갑자기 해결 실마리를 보일 수 있어요. 서두르지 말고 잡아두세요.",
        "오늘 약속 하나가 갑자기 바뀔 수 있어요. 짜증나겠지만 결과적으로 나쁘지 않을 수 있습니다.",
    ],
    "호랑이띠": [
        "오늘 에너지가 넘치는 날이에요. 그걸 엉뚱한 곳에 쓰지 않도록 방향을 잡아두세요.",
        "충동적으로 결정 내리고 싶은 날이에요. 딱 10분만 기다려보세요.",
        "솔직히 오늘 이겨야 직성이 풀리는 날인데, 꼭 이겨야 하는 싸움인지 먼저 확인하세요.",
        "오늘 예상 못 한 방향에서 일이 들어올 수 있어요. 처음엔 번거로워 보여도 거절하기 전에 한번 들어보세요.",
        "이번 주 약속이 두 번 바뀔 수 있어요. 미리 여유 있게 계획 잡아두세요.",
    ],
    "토끼띠": [
        "오늘 누군가 상처 주는 말을 할 수 있어요. 그 말이 진심인지 확인하고 받아들이세요.",
        "부드럽게 흘러가는 날이에요. 억지로 뭔가 하려고 하지 않아도 됩니다.",
        "오늘 본인 챙기는 것 잊지 마세요. 남 걱정하다가 정작 자신이 지칩니다.",
        "오늘 오래 연락 안 하던 사람이 갑자기 생각날 수 있어요. 그냥 짧게 안부 넣어도 됩니다.",
        "거절했다가 은근 마음에 걸리는 상황이 생길 수 있어요. 오늘은 그냥 솔직하게 말하는 게 낫습니다.",
    ],
    "용띠": [
        "오늘 크게 한 방 노리고 싶은 날인데, 그 전에 기초가 단단한지 확인하세요.",
        "주목받고 싶은 마음, 오늘은 자연스럽게 드러내도 됩니다. 때가 맞아요.",
        "혼자 다 하려고 하지 마세요. 오늘 도움을 받는 것이 더 빠른 길입니다.",
        "오늘 누군가 뜻밖의 제안을 해올 수 있어요. 즉흥적으로 결정하지 말고 조건 먼저 확인하세요.",
        "막혀있던 일이 오늘 갑자기 뚫리는 느낌이 올 수 있어요. 그 순간 바로 움직이는 게 좋습니다.",
    ],
    "뱀띠": [
        "오늘 직감이 맞는 날이에요. 뭔가 이상하다 싶으면 그냥 이상한 겁니다.",
        "겉으로 말하지 않아도 속으로 다 보이는 날이에요. 표정 관리 약간 필요합니다.",
        "오늘 설명 없이 행동하면 오해가 생겨요. 한마디 더 하는 게 낫습니다.",
        "평소 의심스러웠던 일이 오늘 확인될 수 있어요. 그때 바로 결론 짓지 말고 조금 더 지켜보세요.",
        "오늘 말 한마디가 오래 남는 날이에요. 좋은 쪽으로도 나쁜 쪽으로도요. 신경 써서 하세요.",
    ],
    "말띠": [
        "오늘 움직이고 싶어서 가만있기 힘든 날이에요. 에너지 쓸 곳을 미리 정해두세요.",
        "자유롭게 하고 싶은데 뭔가 발목 잡히는 느낌이 드는 날이에요. 그 이유를 먼저 파악하세요.",
        "오늘 결정이 빠른 날이에요. 그만큼 후회도 빠를 수 있으니 잠깐 숨 고르고 가세요.",
        "오늘 갑자기 연락이 오거나, 아니면 반대로 기다리던 연락이 안 오는 날일 수 있어요. 둘 다 대비해 두세요.",
        "일정이 갑자기 생기거나 없어지는 날이에요. 오전에 메모 하나 해두면 혼란이 줄어듭니다.",
    ],
    "양띠": [
        "오늘 감성이 예민하게 열려있는 날이에요. 나쁜 게 아니라 특별히 잘 느끼는 날입니다.",
        "오늘은 거절을 잘 못하는 날이에요. 미리 '오늘은 힘들어'를 연습해두세요.",
        "혼자 있는 시간이 오늘 특히 필요한 날이에요. 충전하고 나면 달라집니다.",
        "은근히 서운했던 게 오늘 갑자기 생각날 수 있어요. 바로 꺼내기보다 글로 한번 써보는 게 낫습니다.",
        "오늘 별것 아닌 말 한마디가 오래 남는 날이에요. 좋은 말은 흘리지 말고 나쁜 말은 오래 붙들지 마세요.",
    ],
    "원숭이띠": [
        "머리는 잘 돌아가는데 오늘 유독 말이 안 먹히는 상대가 있을 수 있어요.",
        "오늘 꾀를 너무 많이 쓰다가 오히려 꼬이는 경우가 생길 수 있어요. 단순하게 가세요.",
        "재치 있는 말이 오늘은 가끔 역효과가 날 수 있어요. 타이밍을 한 박자 늦추세요.",
        "오늘 예상치 못한 변수가 하나 들어올 수 있어요. 당황하지 말고 그 변수를 활용할 방법을 먼저 찾아보세요.",
        "애매하게 걸리는 사람이 오늘 갑자기 연락해 올 수 있어요. 어떻게 대응할지 미리 생각해두세요.",
    ],
    "닭띠": [
        "오늘 기준이 너무 높아서 내 것도 남의 것도 다 마음에 안 드는 날이에요.",
        "완벽하게 준비되지 않아도 시작할 수 있어요. 오늘이 그 날입니다.",
        "솔직히 오늘은 칭찬 한마디가 유독 당기는 날이에요. 스스로 한마디 해주세요.",
        "미뤄뒀던 일이 오늘 갑자기 처리해야 하는 상황이 될 수 있어요. 오전에 미리 정리해 두세요.",
        "충동구매보다 '원래 사려던 것'을 다시 보는 게 돈을 아끼는 흐름입니다. 오늘 특히요.",
    ],
    "개띠": [
        "오늘 믿었던 사람이 약간 실망스러울 수 있어요. 기대치를 조금 내려두세요.",
        "충성스럽게 다 해줬는데 돌아오는 게 없다면, 오늘 그 관계를 한 번 점검하세요.",
        "오늘 의리 때문에 손해 보는 상황이 생길 수 있어요. 그래도 당신은 할 겁니다. 그게 당신입니다.",
        "오늘 누군가의 작은 배신 같은 느낌이 들 수 있어요. 크게 반응하기 전에 사실인지 확인하세요.",
        "갑자기 도움 요청이 들어올 수 있어요. 거절하고 싶어도 한 번만 더 들어보세요. 나쁘지 않은 인연일 수 있습니다.",
    ],
    "돼지띠": [
        "오늘 너무 좋은 게 많아서 욕심이 생기는 날이에요. 하나씩만 챙기세요.",
        "사람들이 당신을 좋아하는 날이에요. 그 에너지 잘 받아서 오늘 하루 펼쳐보세요.",
        "오늘 지갑이 열리기 쉬운 날이에요. 가격표 먼저 보는 습관을 오늘만큼은 지켜주세요.",
        "생각 못 했던 사람이 오늘 먼저 안부를 물어올 수 있어요. 반갑게 받아도 됩니다.",
        "좋은 흐름이니까 더 욕심 내고 싶어지는 날이에요. 지금 가진 것도 충분하다는 걸 잊지 마세요.",
    ],
}

# ── 띠별 "헉 맞는데?" 현실 디테일 ──
_CHINESE_REAL_DETAIL = {
    "쥐띠":     {
        "contact_time": "오전 11시~오후 1시",
        "money_leak":   "비교하다가 세 군데서 조금씩 다 결제",
        "annoying_person": "아무 준비 없이 '일단 만나자'는 사람",
        "regret_tonight":  "좋은 정보를 메모 안 해서 잊어버린 것",
    },
    "소띠":     {
        "contact_time": "저녁 7시~9시",
        "money_leak":   "천천히 아낀다면서 한 번에 큰 것 사기",
        "annoying_person": "갑자기 계획을 바꾸자는 사람",
        "regret_tonight":  "한마디 더 했으면 달랐을 것 같은 순간",
    },
    "호랑이띠": {
        "contact_time": "낮 12시~오후 2시",
        "money_leak":   "지금 안 사면 후회할 것 같은 기분에 충동 결제",
        "annoying_person": "결론 없이 우물쭈물 계속 미루는 사람",
        "regret_tonight":  "너무 크게 반응해서 분위기 이상해진 것",
    },
    "토끼띠":   {
        "contact_time": "오후 3시~5시",
        "money_leak":   "분위기 맞추다가 사고 싶지 않은 것 구매",
        "annoying_person": "배려해줬더니 당연하게 여기는 사람",
        "regret_tonight":  "거절하지 못하고 그냥 OK한 것",
    },
    "용띠":     {
        "contact_time": "오전 10시~낮 12시",
        "money_leak":   "스케일 크게 시작했다가 유지비가 생각보다 많이 나오는 것",
        "annoying_person": "큰 그림은 없고 디테일만 계속 따지는 사람",
        "regret_tonight":  "혼자 너무 많이 짊어진 것",
    },
    "뱀띠":     {
        "contact_time": "밤 9시~11시",
        "money_leak":   "갖고 싶었던 것 마침 할인이라서 결제",
        "annoying_person": "겉만 보고 다 안다는 듯이 판단하는 사람",
        "regret_tonight":  "직감이 맞았는데 무시했던 것",
    },
    "말띠":     {
        "contact_time": "오후 1시~3시",
        "money_leak":   "에너지 넘칠 때 계획 없이 즉흥 결제",
        "annoying_person": "느리게 진행하면서 이유도 설명 안 하는 사람",
        "regret_tonight":  "또 충동적으로 결정했다는 걸 저녁에 깨달은 것",
    },
    "양띠":     {
        "contact_time": "저녁 6시~8시",
        "money_leak":   "선물·나눔·후원에 감정적으로 쓰는 돈",
        "annoying_person": "내 감정을 이해 못 하는 척하는 사람",
        "regret_tonight":  "No라고 못 했던 것",
    },
    "원숭이띠": {
        "contact_time": "오후 2시~4시",
        "money_leak":   "재미있을 것 같아서 시작한 구독 서비스 여러 개",
        "annoying_person": "융통성 없이 원칙만 내세우는 사람",
        "regret_tonight":  "너무 영리하게 굴려다 오히려 역효과 난 것",
    },
    "닭띠":     {
        "contact_time": "오전 8시~10시",
        "money_leak":   "더 좋은 게 있을 것 같아서 계속 비교하다가 결국 다 구매",
        "annoying_person": "기준도 없이 '그냥 하면 되지'하는 사람",
        "regret_tonight":  "완벽하게 못 끝낸 항목이 머릿속에서 맴도는 것",
    },
    "개띠":     {
        "contact_time": "오후 4시~6시",
        "money_leak":   "의리로 대신 계산했는데 나만 손해인 상황",
        "annoying_person": "말만 하고 행동이 없는 사람",
        "regret_tonight":  "감정은 있었는데 표현하지 못한 것",
    },
    "돼지띠":   {
        "contact_time": "낮 12시~오후 2시",
        "money_leak":   "맛있는 것, 좋아 보이는 것, 일단 사고 나서 생각하기",
        "annoying_person": "부정적인 얘기를 계속 가져다주는 사람",
        "regret_tonight":  "오늘 너무 많이 쓰거나 먹은 것",
    },
}

def _get_zodiac_human_voice(kr_name):
    """별자리별 구어체 오프닝 랜덤 선택"""
    pool = _ZODIAC_HUMAN_VOICE.get(kr_name, [])
    if pool:
        return random.choice(pool)
    return ""

def _get_zodiac_real_detail_html(kr_name, lucky_color):
    """'헉 맞는데?' 현실 디테일 블록 HTML 생성"""
    d = _ZODIAC_REAL_DETAIL.get(kr_name, {})
    if not d:
        return ""
    return f'''
<div class="card" style="background:linear-gradient(135deg,#fefce8,#fff7ed);border-left:5px solid #f59e0b">
  <span class="badge" style="background:#fef3c7;color:#92400e">🔍 오늘의 현실 체크 — {kr_name} 한정</span>
  <div style="margin-top:14px;display:grid;gap:10px">
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #fde68a">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">📱 연락 올 가능성 높은 시간</div>
      <div style="font-size:15px;font-weight:700;color:#92400e">{d["contact_time"]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px">이 시간대에 진동이 울리면 바로 확인하세요.</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #fee2e2">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">💸 오늘 돈 새기 가장 쉬운 행동</div>
      <div style="font-size:14px;font-weight:700;color:#dc2626">{d["money_leak"]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px">결제 전 한 번만 더 생각하세요.</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #e0e7ff">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">😤 오늘 은근히 신경 긁는 사람 유형</div>
      <div style="font-size:14px;font-weight:700;color:#4338ca">{d["annoying_person"]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px">맞닥뜨려도 오늘만큼은 흘려보내세요.</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #d1fae5">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">🌙 오늘 밤 후회할 가능성 높은 행동</div>
      <div style="font-size:14px;font-weight:700;color:#065f46">{d["regret_tonight"]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px">지금 알았으니 피할 수 있습니다.</div>
    </div>
  </div>
</div>'''

def _get_chinese_human_voice(kr_name):
    """띠별 구어체 오프닝 랜덤 선택"""
    pool = _CHINESE_HUMAN_VOICE.get(kr_name, [])
    if pool:
        return random.choice(pool)
    return ""

def _get_chinese_real_detail_html(kr_name):
    """띠별 '헉 맞는데?' 현실 디테일 블록 HTML"""
    d = _CHINESE_REAL_DETAIL.get(kr_name, {})
    if not d:
        return ""
    return f'''
<div class="card" style="background:linear-gradient(135deg,#fefce8,#fff7ed);border-left:5px solid #f59e0b">
  <span class="badge" style="background:#fef3c7;color:#92400e">🔍 오늘의 현실 체크 — {kr_name} 한정</span>
  <div style="margin-top:14px;display:grid;gap:10px">
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #fde68a">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">📱 연락 올 가능성 높은 시간</div>
      <div style="font-size:15px;font-weight:700;color:#92400e">{d["contact_time"]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px">이 시간대에 진동이 울리면 바로 확인하세요.</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #fee2e2">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">💸 오늘 돈 새기 가장 쉬운 행동</div>
      <div style="font-size:14px;font-weight:700;color:#dc2626">{d["money_leak"]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px">결제 전 한 번만 더 생각하세요.</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #e0e7ff">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">😤 오늘 은근히 신경 긁는 사람 유형</div>
      <div style="font-size:14px;font-weight:700;color:#4338ca">{d["annoying_person"]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px">맞닥뜨려도 오늘만큼은 흘려보내세요.</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #d1fae5">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">🌙 오늘 밤 후회할 가능성 높은 행동</div>
      <div style="font-size:14px;font-weight:700;color:#065f46">{d["regret_tonight"]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px">지금 알았으니 피할 수 있습니다.</div>
    </div>
  </div>
</div>'''

def weekly_fortune_general():
    if not weekly_500.empty and 'sentence' in weekly_500.columns:
        row = weekly_500.sample(1).iloc[0]
        return row['sentence'], row.get('advice', '')
    return sentence(), ""

def monthly_fortune_general():
    if not monthly_500.empty and 'sentence' in monthly_500.columns:
        row = monthly_500.sample(1).iloc[0]
        return row['sentence'], row.get('advice', '')
    return sentence(), ""

def pick_score(name):
    """운세 지수 랜덤 선택"""
    if not fortune_score.empty and 'zodiac' in fortune_score.columns:
        m = fortune_score[fortune_score['zodiac'] == name]
        if not m.empty:
            row = m.sample(1).iloc[0]
            return int(row['total']), int(row['money']), int(row['health']), int(row['love'])
    # 백업 랜덤
    return random.randint(60,95), random.randint(45,99), random.randint(50,99), random.randint(40,99)

def score_bar(label, emoji, pct, color):
    """운세 지수 막대 그래프 HTML"""
    filled = round(pct / 10)
    bar = '█' * filled + '░' * (10 - filled)
    return f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px"><span style="min-width:70px;font-size:13px">{emoji} {label}</span><span style="font-family:monospace;color:{color};font-size:14px">{bar}</span><span style="font-size:13px;font-weight:700;color:{color}">{pct}%</span></div>'

def score_card(name):
    """운세 지수 카드 HTML"""
    total, money, health, love = pick_score(name)
    return f'''<div class="card" style="background:#f8f0ff">
    <span class="badge">📊 오늘의 운세 지수</span>
    <div style="margin-top:10px">
        {score_bar("종합운", "🌟", total,  "#6c3483")}
        {score_bar("금전운", "💰", money,  "#d4ac0d")}
        {score_bar("건강운", "💪", health, "#1e8449")}
        {score_bar("애정운", "❤️", love,   "#e74c3c")}
    </div>
</div>'''

def pick_lucky_item(zodiac_name):
    """별자리 행운의 아이템 선택"""
    if not lucky_items.empty and 'zodiac' in lucky_items.columns:
        m = lucky_items[lucky_items['zodiac'] == zodiac_name]
        if not m.empty:
            return m.sample(1).iloc[0]['item']
    return random.choice(['수정 팔찌', '네잎클로버', '파란 돌', '은반지', '향초'])

def pick_color():
    if not colors_200.empty and 'color' in colors_200.columns:
        return colors_200.sample(1).iloc[0]['color']
    return "골드"

def pick_number():
    if not numbers_500.empty and 'number' in numbers_500.columns:
        num = numbers_500.sample(1).iloc[0]['number']
        # 1~99 범위로 제한
        return str(int(num) % 99 + 1)
    return str(random.randint(1, 99))

def seo_title(target):
    if not seo_patterns.empty:
        p = seo_patterns.sample(1).iloc[0]['pattern']
        return p.replace("{대상}", target)
    return f"{target} 오늘의 운세"

def seo_kw(n=8):
    if not seo_keywords.empty and 'keyword' in seo_keywords.columns:
        return ", ".join(seo_keywords.sample(n)['keyword'].tolist())
    return ""

def stars():
    return random.choice(RATINGS)

def get_week_range():
    today = now_kst().date()
    mon_day = today.toordinal() - today.weekday()   # 이번 주 월요일
    mon = date.fromordinal(mon_day).strftime("%m/%d")
    sun = date.fromordinal(mon_day + 6).strftime("%m/%d")
    return f"{mon} ~ {sun}"

def get_month():
    return now_kst().strftime("%Y년 %m월")

def get_next_month_str():
    """
    1일       → 이번달 운세 (당월 발행)
    마지막주 월요일 or FORCE_MONTHLY → 다음달 운세 (미리 발행)
    그 외      → 이번달
    """
    import calendar as _c
    from datetime import date as _date
    t = now_kst()
    _last = _c.monthrange(t.year, t.month)[1]
    _last_mon = max(d for d in range(1, _last+1)
                    if _date(t.year, t.month, d).weekday() == 0)
    force = os.environ.get("FORCE_MONTHLY","false").lower() == "true"
    # 1일이면 당월 발행
    if t.day == 1:
        return t.strftime("%Y년 %m월")
    # 마지막주 월요일 or 강제 → 다음달
    if t.day == _last_mon or force:
        nm = t.month % 12 + 1
        ny = t.year + (1 if t.month == 12 else 0)
        return f"{ny}년 {nm:02d}월"
    return t.strftime("%Y년 %m월")

# ─────────────────────────────────────────
# 공통 CSS
# ─────────────────────────────────────────
def style():
    return """<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Noto Sans KR',sans-serif;background:#f8f9ff;color:#333;padding:16px}
.wrap{max-width:720px;margin:auto}
.hero{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border-radius:18px;padding:36px 24px;text-align:center;margin-bottom:22px}
.hero h1{font-size:26px;margin-bottom:8px}
.hero p{opacity:.85;font-size:15px}
.card{background:#fff;border-radius:14px;padding:22px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.07)}
.card p{font-size:15px;line-height:1.85;color:#444}
.badge{display:inline-block;background:#f0eaff;color:#6c3483;padding:3px 10px;border-radius:20px;font-size:12px;margin-bottom:10px}
.lucky{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px}
.lucky-box{flex:1;min-width:120px;background:#f8f0ff;border-radius:10px;padding:14px;text-align:center}
.lucky-box .lbl{font-size:12px;color:#888;margin-bottom:4px}
.lucky-box .val{font-size:20px;font-weight:700;color:#6c3483}
.meta{color:#aaa;font-size:12px;text-align:center;padding:20px 0}
.tag-cloud{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.tag{background:#eef2ff;color:#5c6bc0;padding:4px 10px;border-radius:20px;font-size:11px}
.week-day{background:#fff9e6;border-left:4px solid #f7b731;padding:12px 16px;border-radius:8px;margin-bottom:10px;font-size:14px;line-height:1.7}
.game-link{background:linear-gradient(135deg,#4f46e5,#7c3aed);border-radius:14px;padding:20px;text-align:center;margin-top:20px}
.game-link p{font-size:13px;color:rgba(255,255,255,.8);margin-bottom:10px}
.game-link a{display:inline-block;background:#fff;color:#4f46e5;padding:10px 28px;border-radius:10px;text-decoration:none;font-weight:700;font-size:14px}
.game-link a:hover{background:#f0eaff}
.fortune-card{background:linear-gradient(135deg,#667eea,#764ba2);border-radius:20px;padding:28px;color:#fff;margin-bottom:16px}
.fortune-card .fc-emoji{font-size:48px;text-align:center;margin-bottom:10px}
.fortune-card .fc-title{font-size:22px;font-weight:900;text-align:center;margin-bottom:4px}
.fortune-card .fc-sub{font-size:13px;opacity:.8;text-align:center;margin-bottom:6px}
.fortune-card .fc-stars{color:#fde68a;text-align:center;font-size:14px;margin-bottom:16px}
.fortune-card .fc-text{background:rgba(255,255,255,.15);border-radius:12px;padding:16px;font-size:14px;line-height:1.85;margin-bottom:14px}
.fortune-card .fc-lucky{display:flex;gap:10px}
.fortune-card .fc-lucky-box{flex:1;background:rgba(255,255,255,.2);border-radius:10px;padding:10px;text-align:center}
.fortune-card .fc-lucky-lbl{font-size:11px;opacity:.8;margin-bottom:4px}
.fortune-card .fc-lucky-val{font-size:18px;font-weight:900}
.fortune-card .fc-watermark{font-size:11px;opacity:.5;text-align:center;margin-top:12px}
.save-btn{display:block;width:100%;background:#7c3aed;color:#fff;border:none;padding:14px;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;margin-bottom:16px}
.save-btn:hover{background:#6d28d9}
.share-btn-main{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;background:#f3f4f6;color:#333;border:none;padding:14px;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer;margin-bottom:10px}
.share-btn-main:hover{background:#e5e7eb}
.share-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:9000;align-items:flex-end}
.share-overlay.open{display:flex}
.share-sheet{background:#fff;border-radius:20px 20px 0 0;padding:20px 16px 32px;width:100%;max-width:480px;margin:0 auto;animation:slideUp .25s ease}
@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
.sheet-title{text-align:center;font-size:13px;color:#888;margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid #f0f0f0}
.sheet-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px}
.sheet-item{display:flex;flex-direction:column;align-items:center;gap:6px;cursor:pointer;border:none;background:none;padding:0}
.sheet-icon{width:52px;height:52px;border-radius:16px;display:flex;align-items:center;justify-content:center}
.sheet-item span{font-size:11px;color:#444;font-weight:600}
.sheet-cancel{display:block;width:100%;background:#f3f4f6;border:none;border-radius:12px;padding:13px;font-size:15px;font-weight:700;color:#333;cursor:pointer;margin-top:4px}
.sheet-cancel:hover{background:#e5e7eb}
</style>
<script>
function saveFortuneCard(cardId, filename) {
    var el = document.getElementById(cardId);
    if (!el) { alert('카드를 찾을 수 없습니다'); return; }
    var btn = document.getElementById('savebtn-' + cardId);
    if (btn) { btn.textContent = '⏳ 저장 중...'; btn.disabled = true; }

    var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    var isAndroid = /android/i.test(navigator.userAgent);

    html2canvas(el, {scale:2, backgroundColor:'#ffffff', useCORS:true, logging:false}).then(function(canvas) {

        // ── iOS Safari: Web Share API로 사진첩 저장 ──
        if (isIOS && navigator.share && navigator.canShare) {
            canvas.toBlob(function(blob) {
                var file = new File([blob], filename + '.png', {type:'image/png'});
                if (navigator.canShare({files:[file]})) {
                    navigator.share({files:[file], title:filename})
                    .then(function() {
                        if (btn) { btn.textContent = '📸 이미지 저장'; btn.disabled = false; }
                    })
                    .catch(function(e) {
                        if (e.name !== 'AbortError') { fallbackDownload(canvas, filename); }
                        if (btn) { btn.textContent = '📸 이미지 저장'; btn.disabled = false; }
                    });
                } else {
                    fallbackDownload(canvas, filename);
                    if (btn) { btn.textContent = '📸 이미지 저장'; btn.disabled = false; }
                }
            }, 'image/png');
            return;
        }

        // ── Android / PC: Blob URL로 직접 다운로드 ──
        canvas.toBlob(function(blob) {
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = filename + '.png';
            document.body.appendChild(a);
            a.click();
            setTimeout(function() {
                URL.revokeObjectURL(url);
                document.body.removeChild(a);
            }, 300);
            if (btn) { btn.textContent = '📸 이미지 저장'; btn.disabled = false; }
        }, 'image/png');

    }).catch(function() {
        alert('저장 실패. 스크린샷을 이용해주세요.');
        if (btn) { btn.textContent = '📸 이미지 저장'; btn.disabled = false; }
    });
}

function fallbackDownload(canvas, filename) {
    canvas.toBlob(function(blob) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = filename + '.png';
        document.body.appendChild(a);
        a.click();
        setTimeout(function() { URL.revokeObjectURL(url); document.body.removeChild(a); }, 300);
    }, 'image/png');
}
</script>"""

def share_buttons(card_id, filename):
    """공유하기 버튼 → 바텀시트
    구성: X(트위터) · 페이스북 · 라인 · URL복사(메모) · 문자(SMS)
    - 카카오(서비스 종료) / 네이버밴드 / 쓰레드 / 인스타그램 제거
    - 모두 API 키 불필요한 URL 파라미터 방식
    """
    return f"""
<button class="share-btn-main" onclick="if(window.fortOpenSheet){{window.fortOpenSheet('{card_id}','{filename}')}}else{{alert('잠시 후 다시 시도해주세요');}}" ontouchstart="" style="cursor:pointer;touch-action:manipulation">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>
  공유하기
</button>
<button id="savebtn-{card_id}" class="save-btn" onclick="saveFortuneCard('{card_id}', '{filename}')">📸 이미지 저장</button>
<script>
(function(){{
  /* ── CSS: 최초 1회만 삽입 ── */
  if (!document.getElementById('__fort_css')) {{
    var css = document.createElement('style');
    css.id = '__fort_css';
    css.textContent =
      '.fort-ov{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;' +
      'background:rgba(0,0,0,.52);z-index:2147483647;align-items:flex-end;justify-content:center}}' +
      '.fort-ov.on{{display:flex!important}}' +
      '.fort-sh{{background:#fff;border-radius:20px 20px 0 0;padding:22px 16px 38px;' +
      'width:100%;max-width:480px;box-sizing:border-box;' +
      'animation:fortUp .25s cubic-bezier(.4,0,.2,1)}}' +
      '@keyframes fortUp{{from{{transform:translateY(100%)}}to{{transform:translateY(0)}}}}' +
      '.fort-ttl{{text-align:center;font-size:13px;color:#888;margin-bottom:18px;' +
      'padding-bottom:14px;border-bottom:1px solid #f0f0f0}}' +
      '.fort-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:14px}}' +
      '.fort-btn{{display:flex;flex-direction:column;align-items:center;gap:5px;' +
      'border:none;background:none;cursor:pointer;padding:10px 4px;' +
      '-webkit-tap-highlight-color:rgba(0,0,0,.08);touch-action:manipulation;' +
      'user-select:none;-webkit-user-select:none;min-width:58px}}' +
      '.fort-ico{{width:56px;height:56px;border-radius:16px;display:flex;' +
      'align-items:center;justify-content:center;flex-shrink:0}}' +
      '.fort-btn span{{font-size:10px;color:#444;font-weight:600;text-align:center;line-height:1.3;word-break:keep-all}}' +
      '.fort-cancel{{display:block;width:100%;background:#f3f4f6;border:none;' +
      'border-radius:12px;padding:14px;font-size:15px;font-weight:700;color:#333;' +
      'cursor:pointer;-webkit-tap-highlight-color:transparent}}';
    document.head.appendChild(css);
  }}

  /* ── 바텀시트 DOM: 최초 1회만 생성 ── */
  if (!document.getElementById('__fort_ov')) {{
    var ov = document.createElement('div');
    ov.id = '__fort_ov';
    ov.className = 'fort-ov';
    ov.innerHTML =
      '<div class="fort-sh" id="__fort_sh">' +
        '<div class="fort-ttl">공유하기</div>' +
        '<div class="fort-grid">' +
          /* X (트위터) */
          '<button class="fort-btn" id="__fb_x">' +
            '<div class="fort-ico" style="background:#000">' +
              '<svg width="24" height="24" viewBox="0 0 24 24" fill="#fff">' +
                '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231' +
                '-5.401 6.231H2.744l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.45-6.231z"/>' +
              '</svg>' +
            '</div><span>X 공유</span>' +
          '</button>' +
          /* 페이스북 */
          '<button class="fort-btn" id="__fb_fb">' +
            '<div class="fort-ico" style="background:#1877F2">' +
              '<svg width="26" height="26" viewBox="0 0 24 24" fill="#fff">' +
                '<path d="M24 12.073C24 5.405 18.627 0 12 0S0 5.405 0 12.073' +
                'c0 6.027 4.388 11.024 10.125 11.927V15.563H7.078v-3.49h3.047V9.41' +
                'c0-3.025 1.792-4.697 4.533-4.697 1.312 0 2.686.236 2.686.236v2.97' +
                'h-1.513c-1.491 0-1.956.93-1.956 1.887v2.267h3.328l-.532 3.49' +
                'h-2.796v8.437C19.612 23.097 24 18.1 24 12.073z"/>' +
              '</svg>' +
            '</div><span>페이스북</span>' +
          '</button>' +
          /* 라인 */
          '<button class="fort-btn" id="__fb_ln">' +
            '<div class="fort-ico" style="background:#06C755">' +
              '<svg width="28" height="28" viewBox="0 0 48 48" fill="#fff">' +
                '<path d="M24 4C12.95 4 4 11.86 4 21.5c0 8.3 6.56 15.25 15.5 17.06' +
                '.6.13 1.42.4 1.63.92.19.47.12 1.2.06 1.67l-.26 1.57' +
                'c-.08.47-.37 1.84 1.6.99 1.97-.84 10.63-6.26 14.5-10.72' +
                'C39.9 29.97 44 26.02 44 21.5 44 11.86 35.05 4 24 4z"/>' +
                '<path d="M36 25h-5v-8a1 1 0 00-2 0v9a1 1 0 001 1h6a1 1 0 000-2z" fill="#06C755"/>' +
                '<path d="M19 17a1 1 0 00-1 1v9a1 1 0 002 0v-9a1 1 0 00-1-1z" fill="#06C755"/>' +
                '<path d="M29 17h-4a1 1 0 00-1 1v9a1 1 0 001 1h4a1 1 0 000-2h-3v-2h3a1 1 0 000-2h-3v-2h3a1 1 0 000-2z" fill="#06C755"/>' +
                '<path d="M15 17a1 1 0 00-1 1v9a1 1 0 002 0v-5.29l4.29 5.72A1 1 0 0021 28v-9a1 1 0 00-2 0v5.29l-4.29-5.72A1 1 0 0015 17z" fill="#06C755"/>' +
              '</svg>' +
            '</div><span>라인</span>' +
          '</button>' +
          /* URL 복사 (메모) */
          '<button class="fort-btn" id="__fb_cp">' +
            '<div class="fort-ico" style="background:#6b7280">' +
              '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2">' +
                '<rect x="9" y="9" width="13" height="13" rx="2"/>' +
                '<path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>' +
              '</svg>' +
            '</div><span>URL 복사</span>' +
          '</button>' +
          /* 문자 (SMS) */
          '<button class="fort-btn" id="__fb_sms">' +
            '<div class="fort-ico" style="background:#34C759">' +
              '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2">' +
                '<path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>' +
              '</svg>' +
            '</div><span>문자</span>' +
          '</button>' +
        '</div>' +
        '<button class="fort-cancel" id="__fb_cancel">취소</button>' +
      '</div>';
    document.body.appendChild(ov);

    /* ── 닫기 ── */
    function _close() {{
      ov.classList.remove('on');
      document.body.style.overflow = '';
    }}
    ov.addEventListener('click', function(e){{ if(e.target===ov) _close(); }});
    document.getElementById('__fb_cancel').addEventListener('click', _close);

    /* ── 공유 액션 ── */
    function _open(url, w, h) {{
      window.open(url, '_blank', 'width='+w+',height='+h);
      _close();
    }}

    /* X (트위터) */
    document.getElementById('__fb_x').addEventListener('click', function() {{
      var url = encodeURIComponent(location.href);
      var txt = encodeURIComponent(document.title);
      _open('https://twitter.com/intent/tweet?url='+url+'&text='+txt, 600, 450);
    }});

    /* 페이스북 */
    document.getElementById('__fb_fb').addEventListener('click', function() {{
      var url = encodeURIComponent(location.href);
      _open('https://www.facebook.com/sharer/sharer.php?u='+url, 600, 500);
    }});

    /* 라인 */
    document.getElementById('__fb_ln').addEventListener('click', function() {{
      var url = encodeURIComponent(location.href);
      _open('https://social-plugins.line.me/lineit/share?url='+url, 600, 500);
    }});

    /* URL 복사 (메모) */
    document.getElementById('__fb_cp').addEventListener('click', function() {{
      var url = location.href;
      function done() {{ _close(); alert('✅ URL이 복사되었습니다!\\n메모장이나 원하는 곳에 붙여넣기 하세요.'); }}
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(url).then(done).catch(function() {{ fb(url); done(); }});
      }} else {{ fb(url); done(); }}
      function fb(t) {{
        var x = document.createElement('textarea'); x.value = t;
        x.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0';
        document.body.appendChild(x); x.focus(); x.select();
        document.execCommand('copy'); document.body.removeChild(x);
      }}
    }});

    /* 문자 (SMS) */
    document.getElementById('__fb_sms').addEventListener('click', function() {{
      var txt = encodeURIComponent(document.title + '\\n' + location.href);
      _close();
      /* iOS: sms:&body= / Android: sms:?body= 모두 지원 */
      var isMobile = /android|iphone|ipad|ipod/i.test(navigator.userAgent);
      if (isMobile) {{
        var isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
        window.location.href = isIOS ? 'sms:&body='+txt : 'sms:?body='+txt;
      }} else {{
        /* PC: URL 복사로 대체 */
        if (navigator.clipboard) {{
          navigator.clipboard.writeText(document.title + '\\n' + location.href).then(function() {{
            alert('📋 PC에서는 링크가 복사되었습니다!\\n문자 앱에 붙여넣어 공유하세요.');
          }});
        }} else {{
          alert('공유할 링크:\\n' + location.href);
        }}
      }}
    }});

    /* ── 열기 함수: window에 즉시 등록 ── */
    window.fortOpenSheet = function(cardId, fname) {{
      window.__fort_cid = cardId;
      window.__fort_fn  = fname;
      document.getElementById('__fort_ov').classList.add('on');
      document.body.style.overflow = 'hidden';
    }};
    window.fortCloseSheet = _close;
  }}

  /* ── 이미 DOM이 있어도 fortOpenSheet는 항상 window에 보장 ── */
  if (!window.fortOpenSheet) {{
    window.fortOpenSheet = function(cardId, fname) {{
      window.__fort_cid = cardId;
      window.__fort_fn  = fname;
      var o = document.getElementById('__fort_ov');
      if (o) {{ o.classList.add('on'); document.body.style.overflow = 'hidden'; }}
    }};
  }}
}})();
</script>"""


def site_link():
    _links = [
        ("오늘 운이 따른다면 기록도 한번 남겨보세요 :)", "🎮 호호로그게임 바로가기"),
        ("운세 보고 기분 전환이 필요하다면 여기로!", "🎮 무료 게임 하러 가기"),
        ("오늘 운세가 좋다면, 게임도 잘 풀릴지도요 😄", "🎮 지금 바로 플레이"),
    ]
    msg, btn = random.choice(_links)
    return f"""
<div class="game-link">
    <p>🎮 {msg}</p>
    <a href="https://hohoplay.github.io/">{btn}</a>
</div>"""

# ─────────────────────────────────────────
# HTML 빌더
# ─────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════
# 현실 위로형 스토리텔링 데이터 풀
# 구조: 공감 → 감정 흐름 → 위로 → 마지막 한 줄 (명언 연결)
# 원칙: 구어체, AI 티 제거, 현실 디테일, 반복 패턴 금지
# ═══════════════════════════════════════════════════════════════════

# ── 공감 파트: 요즘 세상 현실 디테일 (직장·관계·돈·피로·사회 불안) ──
_EMPATHY_POOL = [
    "요즘 이상하게 아침이 무거운 날이 많아요. 뉴스 켜면 속상하고, 끄면 불안하고. 열심히 살고 있는데 뭔가 점점 좁아지는 느낌이 드는 거 나만 그런 게 아니에요.",
    "월급은 그대로인데 나가는 건 자꾸 늘어나고, 잘하고 있는 건지 모르겠는 날들이 쌓이죠. 그 무게가 어느 순간부터 그냥 일상이 돼버린 것 같아서 더 무서워요.",
    "요즘 '이렇게 살아도 되나' 싶은 날이 가끔 있지 않아요? 남들은 다 앞으로 가는 것 같은데, 나만 제자리인 것 같고. 그 감각이 하루에 한 번씩은 꼭 찾아와요.",
    "직장에서 힘들어도 집에 가면 쉬어야 하는데, 집에 와도 머릿속은 계속 일 생각이고. 언제부터 쉬는 시간도 불안해진 건지 모르겠어요.",
    "아무리 해도 안 풀리는 시기가 있어요. 딱히 내 탓도 아닌데, 그냥 세상이 나한테 좀 냉정한 느낌이 드는 그런 시기요. 요즘 그런 시간을 지나고 있는 분들 꽤 많을 거예요.",
    "누군가한테 '요즘 어때?' 라는 말을 들으면 '그냥 그렇죠'라고 대답하는 날이 늘었어요. 다 설명하기도 애매하고, 그렇다고 괜찮은 것도 아니고.",
    "마음이 허한데 이유를 딱 집어서 말하기가 어려운 날이 있어요. 크게 잘못된 것도 없고, 그렇다고 좋은 것도 없고. 그냥 다 흐릿한 날요.",
    "열심히 준비하고, 참고, 기다렸는데 생각했던 것보다 결과가 안 나올 때 — 그 실망감이 말로 잘 안 나와요. 티 내기도 뭐하고.",
    "잘하고 싶은 마음은 있는데 몸이 따라주지 않는 날이 있어요. 의지가 없는 게 아니라, 그냥 너무 쌓인 거예요. 자기한테 제일 못 봐주는 게 자기 자신이잖아요.",
    "연락을 해야 할 사람이 있는데 계속 미루게 되는 날들이 있어요. 보고 싶기는 한데, 뭔가 먼저 연락하기가 어색해진 거요. 그 거리감이 언제부터 생긴 건지.",
    "괜찮은 척하는 게 습관이 되면, 어느 순간부터 내가 진짜 괜찮은 건지 아닌 건지도 모르게 되더라고요. 그게 제일 무서운 것 같아요.",
    "회사에서 '내가 왜 이것까지 해야 하지?' 싶은 순간이 요즘 들어 자꾸 많아졌어요. 당연히 해야 하는 건 알겠는데, 그 마음이 자꾸 올라오는 게 지치는 신호인 것 같아요.",
]

# ── 감정 흐름 파트: 버티는 감정의 솔직한 표현 ──
_EMOTION_POOL = [
    "그런데 있잖아요, 그렇게 버티고 있다는 것 자체가 이미 대단한 거예요. 무너지지 않은 게 얼마나 힘든 일인지, 버텨본 사람은 알아요.",
    "지치는 건 약해서가 아니에요. 너무 오래 강했기 때문이에요. 그 차이를 자기 자신한테는 인정해줘야 해요.",
    "힘든 걸 힘들다고 말하지 못하는 게 더 힘든 경우가 있어요. '이 정도면 괜찮아야지'라는 기준을 너무 높게 잡고 있는 건 아닌지, 한 번쯤 내려놔도 돼요.",
    "잘 살고 싶은 마음이 있으니까 지치는 거잖아요. 아무 상관 없는 사람은 지치지도 않아요. 지금 이 피로감이 사실은 열심히 살고 있다는 증거예요.",
    "오늘 하루가 다 풀리지 않아도 괜찮아요. 어떤 날은 그냥 지나가는 것만으로 충분한 날이 있으니까요. 모든 날이 의미 있어야 하는 건 아니에요.",
    "감정을 꽉 누르고 살다 보면, 어느 순간 이유도 모르고 힘들어지는 날이 와요. 그게 이상한 게 아니에요. 그냥 오래 참았던 거예요.",
    "뭔가 잘못된 게 아니에요. 그냥 지금 이 시기가 좀 험한 거예요. 세상도, 상황도, 사람 사이도 다 같이 어수선하니까요.",
    "모든 걸 혼자 해결하려고 하다 보니까 어깨가 너무 무거워진 거예요. 내려놓는 게 포기가 아니에요. 숨 쉬는 거예요.",
    "자꾸 비교하게 되는 마음도 이해해요. 근데 남들 인생은 하이라이트만 보이고, 내 인생은 풀영상이잖아요. 당연히 내 것이 더 많아 보일 수밖에 없어요.",
    "기대했다가 실망하는 게 반복되면, 어느 순간 기대 자체를 안 하게 돼요. 그게 자기 보호이기도 하지만, 한편으로는 참 쓸쓸한 일이에요.",
    "요즘 세상이 이러니까 불안한 게 당연한 거예요. 불안을 느끼는 게 잘못된 게 아니에요. 그 불안을 이고 살면서 하루를 버티는 게 진짜 용기예요.",
    "뭔가를 잘하고 싶은 마음이 있는 한, 완전히 포기한 건 아니에요. 그 마음이 아직 있다는 것, 잊지 마세요.",
]

# ── 위로 파트: 구체적이고 따뜻한 위로 ──
_COMFORT_POOL = [
    "당신이 오늘 여기까지 왔다는 것, 그것만으로도 이미 잘한 거예요. 큰 성공이 아니어도 괜찮아요. 오늘 무너지지 않은 것, 그게 진짜 대단한 일이에요.",
    "지금 이 자리에서 계속 살아내고 있는 것, 그거 쉬운 일이 아니에요. 누군가 알아주지 않아도, 그 무게를 아는 사람이 있어요.",
    "오늘 하루 힘들었으면 충분히 힘들었다고 인정해줘요. 자기한테만큼은 솔직해도 돼요. 그리고 그 정도면 충분히 열심히 산 거예요.",
    "완벽하게 잘 살지 않아도 돼요. 그냥 조금씩, 자기 속도대로 가는 게 오히려 더 멀리 가는 방법이에요. 서두르지 않아도 돼요.",
    "지금 잘 안 보여도, 쌓이고 있는 게 있어요. 눈에 안 보이는 것들이 나중에 가장 단단한 기반이 되는 경우가 많아요. 지금 하고 있는 것들이 헛된 게 아니에요.",
    "힘든 시간을 지나는 중이라면, 그게 끝이 아니에요. 끝처럼 느껴지는 그 순간이 사실은 방향이 바뀌기 직전인 경우가 많거든요.",
    "오늘 아무것도 못 한 것 같아도, 오늘을 버텼잖아요. 그게 오늘의 성과예요. 정말로요.",
    "자기 자신에게 조금 더 너그러워도 돼요. 남한테는 이해해줄 수 있는 것들을, 자기한테는 너무 엄격하게 적용하고 있지는 않은지 한 번만 돌아봐요.",
    "지치면 쉬어도 돼요. 쉬는 게 포기가 아니에요. 멈추는 게 아니라, 다시 가기 위해 숨 고르는 거예요.",
    "당신이 버티고 있는 이 시간이, 나중에 당신을 가장 단단하게 만들어줄 거예요. 지금은 안 보여도, 쌓이고 있어요.",
    "살다 보면 어떤 시기는 그냥 통과해야 하는 시기가 있어요. 그 시기를 잘 지나가는 것 자체가 대단한 일이에요. 지금이 그런 시간일 수도 있어요.",
    "오늘 괜찮지 않아도 괜찮아요. 모든 날이 잘 흘러가야 하는 건 아니니까요. 오늘은 그냥 지나가는 것만으로 충분한 날이에요.",
]

# ── SEO 제목 키워드 패턴 ──
_QUOTE_TITLE_PATTERNS = [
    "{today} 오늘의 명언 — 지금 이 순간 당신에게 필요한 한 마디",
    "{today} 오늘의 위로 명언 | 힘든 하루를 버텨낸 당신에게",
    "오늘의 명언 {today} — 지치고 힘들 때 읽으면 좋은 글",
    "{today} 하루를 버티는 당신을 위한 오늘의 명언",
    "오늘의 명언 | {today} 요즘 같은 때 마음에 새길 한 줄",
    "{today} 오늘의 명언 — 무기력한 날에 읽어보세요",
    "지금 지쳐있는 당신에게 | {today} 오늘의 위로 명언",
    "{today} 오늘의 명언 · 현실 위로형 스토리텔링",
]

def build_quote_post(today_str):
    """현실 위로형 스토리텔링 명언 포스트 — 별과 띠가 만나는 시간과 같은 톤"""
    quote, meaning, category = pick_quote()
    cat_badge = f" · {category}" if category and str(category) != 'nan' else ""

    title_pattern = "{today} 하루를 버티는 당신을 위한 오늘의 명언"
    title = title_pattern.format(today=today_str)

    empathy  = random.choice(_EMPATHY_POOL)
    emotion  = random.choice(_EMOTION_POOL)
    comfort  = random.choice(_COMFORT_POOL)

    # 명언 연결 브릿지 — 설명 없이 자연스럽게 이어지는 문장
    _CLOSING_BRIDGES = [
        f"그래서 오늘 이 말이 더 와닿아요.<br><br>❝ {quote} ❞",
        f"그 마음 그대로, 오늘 이 한 줄 가져가요.<br><br>❝ {quote} ❞",
        f"오늘 하루 이 말 하나, 마음에 담아두세요.<br><br>❝ {quote} ❞",
        f"당신한테 건네고 싶은 말이 딱 이거예요.<br><br>❝ {quote} ❞",
        f"이 한 마디, 오늘 주머니에 넣고 다니세요.<br><br>❝ {quote} ❞",
        f"긴 말 필요 없이, 오늘은 이 한 줄이에요.<br><br>❝ {quote} ❞",
    ]
    closing = random.choice(_CLOSING_BRIDGES)

    kw_list = [
        "오늘의명언", "위로명언", "현실명언", today_str,
        "힘들때명언", "위로글", "오늘명언", "짧은명언",
        "마음에새길말", "감성명언", "하루명언", "좋은글",
    ]
    if category and str(category) != 'nan':
        kw_list.append(category)
    tag_html = "".join(f'<span class="tag">{t}</span>' for t in kw_list)

    card_id = f"qc-{today_str.replace(' ','').replace('년','').replace('월','').replace('일','')}"

    content = f"""{style()}
<style>
.qc-page {{
  max-width: 660px;
  margin: 0 auto;
  padding: 0 4px;
  font-family: 'Noto Serif KR', Georgia, serif;
}}
.qc-date {{
  font-size: 12px;
  letter-spacing: 0.14em;
  color: #9ca3af;
  text-align: center;
  margin-bottom: 1.4rem;
}}
.qc-title {{
  font-size: 21px;
  font-weight: 600;
  color: #1f2937;
  text-align: center;
  line-height: 1.55;
  margin-bottom: 0.3rem;
}}
.qc-sub {{
  font-size: 13px;
  text-align: center;
  color: #9ca3af;
  margin-bottom: 2.2rem;
}}
.qc-rule {{
  text-align: center;
  color: #d1d5db;
  letter-spacing: 0.5em;
  margin: 2rem 0;
  font-size: 13px;
}}
.qc-body {{
  font-size: 15.5px;
  line-height: 2.2;
  color: #374151;
  word-break: keep-all;
}}
.qc-body p {{
  margin: 0 0 1.6em 0;
}}
.qc-quote {{
  font-size: 16px;
  line-height: 1.9;
  color: #4a235a;
  font-weight: 700;
  text-align: center;
  background: linear-gradient(135deg,#fdf4ff,#ede9fe);
  border-radius: 14px;
  padding: 20px 18px;
  margin: 2rem 0;
  word-break: keep-all;
}}
.qc-footer {{
  margin-top: 2.5rem;
  padding-top: 1.8rem;
  border-top: 1px solid #f3f4f6;
  font-size: 14px;
  color: #9ca3af;
  text-align: center;
  line-height: 2.0;
  font-style: italic;
}}
</style>

<div class="wrap">

  <!-- 이미지 저장 카드 -->
  <div id="{card_id}" class="qc-page">
    <div class="qc-date">{today_str}{cat_badge}</div>
    <h1 class="qc-title">📖 오늘의 명언</h1>
    <p class="qc-sub">지금 이 순간 당신에게 건네는 한 줄</p>
    <div class="qc-rule">&middot; &middot; &middot;</div>

    <div class="qc-body">
      <p>{empathy}</p>
      <p>{emotion}</p>
      <p>{comfort}</p>
    </div>

    <div class="qc-quote">{closing}</div>

    <div class="qc-rule">&middot; &middot; &middot;</div>
    <div class="qc-footer">
      오늘도 잘 버텨줘서 고마워요.<br>
      내일 또 이야기 나눠요.
    </div>
  </div>

  {share_buttons(card_id, f"오늘의명언_{today_str}")}

  <!-- SEO 키워드 -->
  <div class="card">
    <span class="badge">🔍 관련 키워드</span>
    <div class="tag-cloud">{tag_html}</div>
  </div>

  {site_link()}
  <div class="meta">※ 매일 업데이트 · 현실 위로형 오늘의 명언</div>
</div>"""
    return title, content, ["오늘의명언", "위로명언", "명언", "운세"]


# ─────────────────────────────────────────
# 별자리운세 SEO·콘텐츠 개선 헬퍼
# ─────────────────────────────────────────

# CTR 신호 키워드 풀 (점수 구간별)
_Z_SIGNAL_MONEY_UP   = ["금전운 상승 타이밍", "재물운 급상승", "수입 기회 포착", "금전 흐름 반전"]
_Z_SIGNAL_LOVE_UP    = ["연애운 급변", "인연 접촉 신호", "애정운 상승 중", "관계 반전 예고"]
_Z_SIGNAL_WARN       = ["오늘 주의 필요", "신중함이 필요한 날", "충동 결정 주의", "조심해야 할 타이밍"]
_Z_SIGNAL_TOTAL_UP   = ["오늘 총운 최고조", "행운 기회 포착", "운세 상승 흐름 확인", "오늘 놓치면 후회"]
_Z_SIGNAL_MID        = ["오늘 균형 잡힌 하루", "안정적 흐름 확인", "차분한 기운의 날"]

def _zodiac_seo_title(z_kr, today_dot, total, money, health, love):
    """지수 기반 CTR 최적화 제목 생성"""
    # 어떤 신호 쓸지 결정 (가장 두드러진 지표 우선)
    scores = {"money": money, "love": love, "total": total, "health": health}
    top_key = max(scores, key=scores.get)
    top_val = scores[top_key]
    avg = (total + money + love) / 3

    if top_key == "money" and money >= 78:
        signal = random.choice(_Z_SIGNAL_MONEY_UP)
    elif top_key == "love" and love >= 78:
        signal = random.choice(_Z_SIGNAL_LOVE_UP)
    elif total >= 82:
        signal = random.choice(_Z_SIGNAL_TOTAL_UP)
    elif avg <= 58:
        signal = random.choice(_Z_SIGNAL_WARN)
    elif abs(money - love) >= 35:
        signal = f"{'금전운' if money > love else '연애운'} 반전 주목"
    else:
        signal = random.choice(_Z_SIGNAL_MID)

    # 제목 패턴 (날짜 포맷: YYYY년 M월 D일)
    patterns = [
        f"{today_dot} {z_kr} 운세 | {signal}",
        f"{z_kr} 오늘운세 ({today_dot}) – {signal} 확인",
        f"[{today_dot}] {z_kr} 별자리 운세 — {signal}",
        f"{z_kr} {today_dot} 오늘의 운세 · {signal}",
    ]
    return random.choice(patterns), signal


# ─────────────────────────────────────────────────────────────────
# 5파트 구조 본문 데이터 풀
# 파트1: 서론(오늘 기운 맥락)  파트2: 지수 해석(수치 근거)
# 파트3: 현실 조언(구체 행동)  파트4: 시간대별 가이드
# 파트5: 마무리(따뜻한 응원)
# ─────────────────────────────────────────────────────────────────

# ── 총운 서론 풀 ── (① 감정공감 → ② 긴장/전환 → ③ 구체행동 → ④ 희망반전)
_Z_TOTAL_INTRO_UP = [
    # 공감 → 긴장 → 행동 → 반전
    "요즘 괜히 혼자 다 짊어지는 느낌이 강했을 수 있어요. 그런데 오늘은 조금 달라요. 특히 오전에 누군가 먼저 말 걸어오거나 예상 못한 연락이 오면 흘려보내지 마세요. 그게 오늘 흐름의 시작입니다.",
    "며칠 동안 '이거 맞나?' 하는 의심이 있었을 수 있어요. 오늘 그 답이 조금씩 보이기 시작합니다. 단, 오늘 중반 지나서 갑자기 자신 없어지는 순간이 올 수 있어요. 그 순간에 멈추지 말고 한 발만 더 나가 보세요. 생각보다 빨리 땅이 나옵니다.",
    "오늘은 오래 묵혀둔 연락처를 열어볼 것 같은 날이에요. 미루던 말, 꺼내지 못한 부탁, 보내지 않은 메시지. 그중 하나만 오늘 실행해 보세요. 타이밍이 지금이에요.",
    "사람은 많은데 마음은 더 외로웠을 수 있어요. 오늘 그 외로움을 채워줄 신호가 들어올 수 있습니다. 다만 오늘 저녁까지는 감정보다 행동을 먼저 하는 것이 좋아요. 느끼기 전에 먼저 움직여 보세요. 생각보다 당신 편은 가까이에 있을 수 있습니다.",
    "최근 열심히 했는데 티가 안 나는 것 같아서 지쳤을 수 있어요.\n\n오늘 오전, 누군가의 반응이나 작은 결과 하나가 그 피로를 가볍게 만들어줄 수 있습니다.\n\n보이지 않았던 것이 보이기 시작하는 날입니다.",
    "솔직히 말하면 오늘 꽤 좋은 날이에요.\n\n대단한 일이 생기는 게 아니라, 작은 것들이 자꾸 맞아 떨어지는 날입니다.\n\n오전에 결정이 필요한 일이 있다면 오늘 안에 끝내세요. 내일보다 오늘이 훨씬 유리합니다.",
]
_Z_TOTAL_INTRO_WARN = [
    "요즘 괜히 예민해지는 것 같은 느낌 들지 않으셨나요? 오늘은 그게 더 두드러질 수 있는 날이에요. 특히 오후에 별것 아닌 말 한마디에 감정이 흔들릴 수 있습니다. 그럴 때 바로 반응하지 말고 잠깐 자리를 피해 보세요. 그게 오늘 하루를 지키는 방법이에요.",
    "오늘 계획이 생각대로 안 풀리는 게 생길 수 있어요. 그래도 무너질 사람이 아니잖아요. 오전에 해야 할 일 목록을 딱 세 개로 줄이고, 그 세 개만 끝내는 걸 목표로 잡아 보세요. 욕심을 줄일수록 오늘 하루가 훨씬 가벼워집니다.",
    "요즘 너무 많은 것을 동시에 붙들고 있지는 않으세요? 오늘은 그 무게가 조금 더 느껴지는 날이에요. 억지로 힘내지 않아도 됩니다. 오늘 하나를 내려놓는 것 자체가 내일을 위한 가장 현명한 선택이에요.",
    "뭔가 어긋나는 느낌이 계속 드는 날이에요. 실제로 문제가 있다기보다 감각이 예민해진 날입니다.\n\n오늘은 새로 시작하기보다 기존 것을 점검하는 데 쓰세요.\n\n이런 날일수록 작은 확인 하나가 나중에 큰 실수를 막아줍니다.",
]

# ── 총운 지수 해석 풀 ──
_Z_TOTAL_SCORE_UP = [
    "오늘 오전 10시~오후 2시 사이가 흐름이 가장 잘 타는 시간이에요. 중요한 연락이나 결정이 있다면 그 안에 담아두세요. 미루면 오후로 갈수록 에너지가 분산됩니다.",
    "오늘 이번 주 중에 흐름이 가장 열려있는 날이에요. 오전에 핵심 한 가지만 처리하면 나머지는 자연스럽게 따라옵니다.",
    "오늘 타이밍이 맞는 날이에요. 오전 안에 결정해야 할 게 있다면 망설이지 마세요. 너무 오래 생각하면 오히려 헷갈리는 날입니다.",
]
_Z_TOTAL_SCORE_WARN = [
    "오늘은 새로 시작하기보다 기존 것 마무리에 쓰는 게 맞는 날이에요. 억지로 밀어붙일수록 에너지만 빠지는 흐름입니다. 2~3일 기다리면 흐름이 달라져요.",
    "성과를 억지로 내려 하기보다 오늘 하루 기반을 다지는 작업에 집중하세요. 내일 훨씬 가벼운 상태로 시작할 수 있습니다.",
]

# ── 금전운 지수 해석 풀 ──
_Z_MONEY_SCORE_UP = [
    "오전 10시~오후 1시 사이가 금전 처리하기 가장 유리한 타이밍이에요. 환급금, 포인트 전환, 정산 미룬 것들 오늘 안에 처리해두세요.",
    "놓쳤던 환급금이나 캐시백, 오늘 한 번 확인해보세요. 작은 거라도 오늘은 손에 잡히는 날이에요.",
    "수입 관련 연락이나 제안이 들어오면 오늘 안에 답하세요. 내일로 넘기면 타이밍이 어긋날 수 있어요.",
]
_Z_MONEY_SCORE_WARN = [
    "오늘 지출 결정은 하루 자고 나서 하세요. 지금 급해 보이는 게 내일 보면 안 급한 경우가 많아요.",
    "오늘 카드 내역 한 번 훑어보세요. 쓰는지도 몰랐던 자동결제 하나 끊는 것만으로도 한 달이 달라집니다.",
]

# ── 연애운 서론 풀 ──
_Z_LOVE_INTRO_UP = [
    "답장을 미루던 사람에게 먼저 짧게라도 연락해보세요. 오늘은 그 한 줄이 생각보다 멀리 닿을 수 있는 날이에요. 거창한 말 아니어도 돼요. '요즘 어때요?' 한마디로 시작하면 돼요.",
    "미뤄두던 연락 하나가 이번 주 흐름을 바꿀 수 있어요. 오늘 오후, 핸드폰을 열었을 때 특정 이름이 먼저 떠오른다면 그냥 넘기지 마세요. 그 감각이 맞습니다.",
    "요즘 혼자 감정을 눌러왔다면, 오늘은 그걸 조금 풀어도 괜찮은 날이에요. 상대도 사실 당신의 연락을 기다리고 있었을 수 있습니다.",
]
_Z_LOVE_INTRO_WARN = [
    "오늘 감정이 평소보다 예민하게 올라올 수 있어요. 특히 오후에 상대방 말이나 행동이 유독 크게 느껴지는 순간이 올 수 있습니다. 그 순간 바로 반응하지 말고 숨 한 번 쉬고 넘기세요. 오해로 번지기 전에 잡는 게 훨씬 쉽습니다.",
    "오늘 중요한 감정 대화는 저녁 이후로 미루세요. 낮 동안은 말이 의도와 다르게 나가기 쉬운 흐름이 있어요. 하고 싶은 말이 있다면 먼저 머릿속에서 한 번 정리한 다음 꺼내보세요.",
    "가까운 사람과 사소한 것으로 어긋나기 쉬운 날이에요. 내가 옳다는 확신보다 '이 사람 요즘 어떤 상태일까'를 먼저 생각해 보세요. 그 한 번의 여유가 오늘 관계를 지켜줍니다.",
]

# ── 연애운 상세 조언 풀 ──
_Z_LOVE_DETAIL_UP = [
    "오늘 오후 2시~5시 사이에 예상 못한 연락이 올 수 있어요. 그 연락이 가볍게 느껴지더라도 흘려보내지 마세요. 짧게라도 성의 있게 답하는 것이 오늘 인연의 실을 잇는 방법입니다.",
    "오래 연락이 끊겼던 사람이 갑자기 생각난다면, 먼저 짧은 안부를 넣어 보세요. '요즘 어때요?' 한 줄이 관계를 다시 이어주는 오늘이 될 수 있습니다.",
    "저녁 약속이나 가벼운 만남이 생긴다면 핑계 찾지 말고 나가 보세요. 오늘은 예상치 못한 자리에서 좋은 인연이 시작될 수 있는 날입니다.",
    "오늘 그냥 아무 이유 없이 안부를 묻고 싶은 사람이 있다면,\n\n그냥 연락하세요.\n\n핑계가 필요 없는 날이에요.",
    "오늘 감이 좋은 날이에요. 특히 오후 늦게, 예상하지 못한 쪽에서 연락이 올 수 있습니다.\n\n진동이 울리면 바로 확인하세요.",
    "전에 하려다 멈췄던 고백이나 표현이 있다면, 오늘 가장 가벼운 방식으로 꺼내보세요. 거창하지 않아도 됩니다. 짧은 말 한마디가 오늘은 생각보다 잘 닿습니다.",
]
_Z_LOVE_DETAIL_WARN = [
    "오늘 상대에게 서운한 게 생기더라도, 그 자리에서 바로 꺼내지 마세요. 감정이 가라앉은 저녁 이후에 '그때 그 말이 조금 걸렸어'라고 차분하게 전하는 게 훨씬 효과적입니다.",
    "오늘 문자나 메시지를 보내기 전에 한 번 더 읽어보세요. 내 의도와 다르게 읽힐 수 있는 표현이 있는지 확인한 다음 보내는 게 오늘만큼은 중요합니다.",
    "혼자 있는 시간을 강제로 채우려 하지 마세요. 오늘 억지로 연락하거나 만남을 만들어내는 것보다 잠깐 거리 두는 게 관계에 더 좋은 날입니다.",
    "오늘 상대방이 이상하게 느껴진다면, 상대가 이상한 게 아니라 내 상태가 예민한 것일 수도 있어요.\n\n먼저 내 감정을 확인해 보세요.",
    "상대 말투가 평소보다 조금 차갑게 느껴지는 순간이 올 수 있어요. 그 말투가 진짜 의도인지 지금 그 사람 상태인지 먼저 확인하고 반응하세요. 오해로 번지기 전에 잡는 게 훨씬 쉽습니다.",
    "눈치 보면서 하지 못했던 말이 있다면 오늘 저녁에 짧게라도 꺼내보세요. 타이밍이 지나면 더 꺼내기 어려워지는 말들이 있어요.",
]

# ── 연애운 시간대 가이드 풀 ──
_Z_LOVE_STORY_UP = [
    "💬 마음속에 담아둔 말이 있다면 오늘이 꺼내기 좋은 날이에요. 거창하지 않아도 돼요. 짧은 한 줄이 긴 침묵보다 훨씬 멀리 닿습니다.",
    "💬 오늘 누군가가 먼저 다가오는 느낌이 있을 수 있어요. 그 신호를 흘려보내지 마세요. 작은 반응 하나가 관계의 온도를 바꿔놓을 수 있어요.",
    "💬 말하지 않아도 통하는 사람이 오늘 눈에 띄는 날이에요. 오래 연락 못 한 사람이 떠오른다면 그게 신호일 수 있어요. 짧게라도 먼저 건네보세요.",
    "💬 감정을 설명하려 하기보다 그냥 함께 있는 시간을 만들어 보세요. 오늘은 말보다 온도가 더 잘 전달되는 날이에요.",
]
_Z_LOVE_STORY_WARN = [
    "💬 감정이 예민하게 올라오는 날이에요. 상대의 말 한마디가 평소보다 크게 들릴 수 있어요. 반응하기 전에 한 박자만 쉬어가세요.",
    "💬 오늘은 관계에서 무언가를 해결하려 하기보다 그냥 두는 편이 낫습니다. 억지로 풀려는 날일수록 매듭이 더 단단해지거든요.",
    "💬 기대치를 조금만 낮춰보세요. 오늘은 상대가 내 마음만큼 반응하지 않더라도, 그게 관계의 전부는 아니에요. 조금 더 여유롭게 봐도 됩니다.",
]
# 하위 호환 — 기존 변수명 유지
_Z_LOVE_TIME_UP   = _Z_LOVE_STORY_UP
_Z_LOVE_TIME_WARN = _Z_LOVE_STORY_WARN

# ── 연애운 마무리 풀 ──
_Z_LOVE_CLOSE_UP = [
    "생각보다 당신 편은 가까이에 있을 수 있습니다. 오늘 작은 용기 하나가 내일의 관계를 바꿔놓을 수 있어요. 💕",
    "표현하지 않은 마음은 상대에게 닿지 않아요. 오늘 그 마음, 가장 가벼운 방식으로 한 번만 꺼내 보세요. 🌸",
    "먼저 연락한 사람이 늘 더 많이 얻습니다. 오늘 그 사람이 당신이어도 괜찮습니다. 💞",
]
_Z_LOVE_CLOSE_WARN = [
    "지금 이 관계가 흔들리는 것 같아도, 오늘 하루 잘 버틴 것만으로 이미 충분해요. 관계는 한 번에 완성되는 게 아니니까요. 🌿",
    "감정이 요동치는 날일수록 말보다 침묵이 관계를 지킵니다. 오늘의 여유가 내일의 더 깊은 연결이 됩니다. 🌙",
]

# ── 금전운 서론 풀 ──
_Z_MONEY_INTRO_UP = [
    "요즘 돈 나가는 곳만 보이고 들어오는 건 없는 것 같았을 수 있어요. 오늘은 그 흐름이 살짝 바뀌는 날이에요. 오래 묵혀뒀던 미수금, 환급금, 정산 내역을 오늘 한 번 확인해 보세요. 작은 것이라도 챙겨지는 날입니다.",
    "오늘 금전 관련 연락이나 제안이 들어온다면 내일로 미루지 마세요. 확인하고 결정하기에 오늘이 더 유리한 흐름입니다. 서두르지 않아도 되니까, 오늘 안에 한 번만 열어보세요.",
    "막혀있던 수입 루트가 조금씩 열리는 흐름이에요. 혼자 힘들게 버텨온 시간이 지금 결실로 이어지고 있습니다. 포인트 전환이나 캐시백처럼 작은 것도 오늘 챙겨두면 나중에 쌓입니다.",
]
_Z_MONEY_INTRO_WARN = [
    "오늘 충동적으로 뭔가 사고 싶어지는 순간이 올 수 있어요. 특히 오후에요. 장바구니에 담아두고 내일 아침에 다시 보세요. 80%는 안 사게 됩니다.",
    "오늘은 금전 판단력이 흐려지기 쉬운 날이에요. 큰 결정이나 계약은 오늘 하루만큼은 보류해 두세요. 급한 것처럼 느껴지는 제안일수록 오늘은 신중하게 봐야 합니다.",
]

# ── 금전운 상세 조언 풀 ──
_Z_MONEY_DETAIL_UP = [
    "미뤄두었던 환급금이나 포인트 전환, 캐시백 신청을 오늘 처리하세요. 귀찮아서 미뤘던 것들이 오늘 손에 잡히는 날입니다. 10분만 투자해도 꽤 챙겨집니다.",
    "오후에 수입 관련 메시지나 연락이 올 수 있어요. 조건을 꼼꼼히 읽고 결정하세요. 서두르지 않아도 됩니다. 오늘 안에 판단하면 기회는 놓치지 않습니다.",
    "부업이나 외부 수입에 대해 막연하게만 생각해 왔다면, 오늘 정보를 찾아보는 것만이라도 시작해 보세요. 오늘의 검색 하나가 다음 달 수입의 시작이 될 수 있습니다.",
]
_Z_MONEY_DETAIL_WARN = [
    "오늘 오후 3시 이후에 쇼핑 앱을 열고 싶어진다면 알림을 끄세요. 지금 사고 싶은 게 내일도 사고 싶으면 그때 사세요. 오늘 충동구매는 내일 아침 후회가 됩니다.",
    "오늘 카드 내역을 한 번 훑어보세요. 자동 결제 중에 쓰지 않는 구독 서비스가 있을 수 있어요. 월 몇 천 원이라도 지금 끊어두면 연간으로는 상당히 됩니다.",
    "투자나 새로운 금전 계약은 이틀 뒤로 미루세요. 지금 급해 보이는 제안일수록 오늘은 천천히 보는 것이 맞습니다. 조금 더 생각한 뒤 결정해도 늦지 않아요.",
]

# ── 금전운 시간대 가이드 풀 ──
_Z_MONEY_STORY_UP = [
    "💰 들어올 것이 있다면 오늘 확인해 보세요. 미수금, 포인트, 환급금처럼 챙기지 않으면 그냥 지나치는 것들이 오늘 눈에 들어올 수 있어요.",
    "💰 금전 관련 연락이나 제안이 온다면 오늘은 미루지 말고 확인해 보세요. 판단은 서두르지 않아도 되지만 확인은 오늘 하는 게 맞아요.",
    "💰 수입 루트에 대해 막연하게만 생각해 왔다면, 오늘 10분만 정보를 찾아보세요. 검색 하나가 다음 달을 바꿀 수 있어요.",
]
_Z_MONEY_STORY_WARN = [
    "💰 사고 싶어지는 순간이 올 수 있어요. 장바구니에 담아두고 내일 아침에 다시 열어보세요. 대부분은 그때쯤 안 사게 됩니다.",
    "💰 오늘 금전 결정은 하루만 보류해 두세요. 급해 보이는 제안일수록 오늘은 한 번 더 읽어보는 게 맞아요.",
    "💰 카드 내역 한 번 훑어보세요. 자동 결제 중 쓰지 않는 구독이 하나쯤 있을 거예요. 지금 끊으면 연간으로 꽤 됩니다.",
]
_Z_MONEY_TIME_UP   = _Z_MONEY_STORY_UP
_Z_MONEY_TIME_WARN = _Z_MONEY_STORY_WARN

# ── 금전운 마무리 풀 ──
_Z_MONEY_CLOSE_UP = [
    "오늘 챙긴 작은 것들이 모여서 단단한 기반이 됩니다. 들어오는 흐름일 때 지출도 같이 점검하는 게 진짜 재테크예요. 💛",
    "좋은 흐름일 때 가장 해야 할 건 흥청망청이 아니라 현명한 다음 준비예요. 오늘 그 준비 하나만 해두세요. 🌟",
]
_Z_MONEY_CLOSE_WARN = [
    "오늘 신중한 것 자체가 최고의 금전 전략이에요. 무리하지 않은 날이 나중에 내 편이 됩니다. 💚",
    "지금은 지키는 날이에요. 쌓는 건 내일부터 해도 됩니다. 오늘 버텨낸 것으로 충분합니다. 🌿",
]

# ── 직장운 서론 풀 ──
_Z_WORK_INTRO_UP = [
    "오랫동안 보이지 않는 데서 열심히 해온 것들이 오늘 조금씩 수면 위로 올라오는 날이에요. 특히 오전에 누군가의 반응이 평소와 다르게 느껴진다면 그게 신호입니다. 오늘 한 가지 중요한 일에 집중해 보세요.",
    "오늘 머릿속에서 맴돌던 아이디어가 갑자기 구체화될 수 있어요. 그 순간 메모부터 하세요. 회의나 미팅이 있다면 평소보다 조금 더 적극적으로 발언해 보세요. 오늘 당신 말에 무게가 있는 날입니다.",
    "업무 흐름이 잘 타이는 날이에요. 어렵게 느껴지던 일도 오늘은 생각보다 수월하게 풀릴 수 있어요. 미뤄둔 중요한 과제가 있다면 오늘 시작하는 게 맞습니다.",
]
_Z_WORK_INTRO_WARN = [
    "오늘 업무 중에 예상 못한 변수가 생길 수 있어요. 특히 중반쯤에요. 당황하지 말고 지금 할 수 있는 것만 먼저 처리하세요. 오늘 하루 목록을 세 가지로 줄이면 훨씬 수월해집니다.",
    "집중이 잘 안 되는 날이에요. 억지로 짜내려 하기보다 오늘은 정리와 점검 위주로 움직이세요. 그게 결과적으로 내일의 속도를 높여줍니다.",
]

# ── 직장운 지수 해석 풀 ──
_Z_WORK_SCORE_UP = [
    "오늘 오전이 집중력 제일 좋은 타이밍이에요. 미뤄둔 보고서나 이메일, 오전 안에 처리하면 오후가 훨씬 가벼워집니다.",
    "회의나 발표가 오늘 잡혀있다면 잘 된 거예요. 말이 잘 나오는 날이거든요. 하려다 멈췄던 말 오늘 꺼내보세요.",
    "오늘 동료나 상사 눈치 보느라 못 했던 것들, 오늘은 조금 더 직접적으로 움직여도 괜찮은 흐름이에요.",
]
_Z_WORK_SCORE_WARN = [
    "오늘은 억지로 성과 내려 하기보다 기존에 하던 것 점검하는 날로 쓰세요. 이런 날 무리하면 실수가 나와요.",
    "집중이 잘 안 되는 날이에요. 오늘 할 일 목록을 세 개로 줄이고, 그 세 개만 끝내는 걸 목표로 잡아보세요.",
]

# ── 직장운 상세 조언 풀 ──
_Z_WORK_DETAIL_UP = [
    "오늘 동료나 상사로부터 예상 못한 긍정적인 반응이 올 수 있어요. 그 순간 겸손하게 받되, 다음 목표도 함께 언급해 보세요. 인상이 훨씬 깊어집니다.",
    "오늘 회의에서 말하려다 멈췄던 아이디어가 있다면 꺼내 보세요. 타이밍을 놓치지 않는 것 자체가 오늘 당신의 가장 큰 강점입니다.",
    "오늘 작은 성과가 생기면 팀과 공유하세요. 혼자 안고 가는 것보다 나눌 때 신뢰가 더 쌓이는 날입니다.",
]
_Z_WORK_DETAIL_WARN = [
    "이메일이나 보고서 발송 전에 한 번 더 읽어보세요. 오늘은 작은 오타나 빠진 내용이 생기기 쉬운 날이에요. 2분 확인이 나중의 수습 30분을 아껴줍니다.",
    "동료와 의견이 엇갈리는 순간이 오면, 내 주장을 밀어붙이기 전에 '그 방식은 어떤 이유에서인가요?'를 먼저 물어보세요. 오늘 그 한 마디가 갈등을 만들지 않는 열쇠입니다.",
    "중요한 발표나 보고가 오늘로 잡혀 있다면 준비가 조금 더 필요하다고 느껴질 수 있어요. 그 느낌이 맞습니다. 오늘 오전 안에 한 번 더 점검해 두세요.",
    "오늘 상사나 동료 말투가 유독 날카롭게 느껴지는 순간이 있을 수 있어요. 그 말투가 나를 향한 건지, 그 사람 상태가 안 좋은 건지 구분하고 반응하세요. 불필요한 감정 소모를 줄여줍니다.",
    "눈치 보느라 못 했던 의견이 있다면 오늘은 메일로 짧게라도 남겨두세요. 말로 꺼내기 어려우면 문서가 대신해줍니다.",
]

# ── 직장운 시간대 가이드 풀 ──
_Z_WORK_STORY_UP = [
    "💼 머릿속에서 맴돌던 아이디어가 있다면 오늘 꺼내보세요. 생각이 구체화되기 좋은 날이에요. 말로 꺼내거나 메모로 남기거나, 어떤 방식이든 괜찮아요.",
    "💼 오늘 한 가지 중요한 일에만 집중해 보세요. 여러 개를 동시에 잡으려 할수록 하나도 제대로 안 되는 날이 있거든요. 오늘이 그 날일 수 있어요.",
    "💼 미뤄둔 보고서나 이메일이 있다면 오늘 처리해 두세요. 오늘 해두면 내일 아침이 훨씬 가볍습니다.",
]
_Z_WORK_STORY_WARN = [
    "💼 오늘 집중이 잘 안 된다면 억지로 짜내려 하지 마세요. 정리와 점검 위주로 움직이는 게 결과적으로 내일의 속도를 높여줍니다.",
    "💼 이메일이나 보고서 보내기 전에 한 번 더 읽어보세요. 오늘은 작은 오타나 빠진 내용이 생기기 쉬운 날이에요. 2분 확인이 30분 수습을 아껴줍니다.",
    "💼 의견이 엇갈리는 순간이 오면 먼저 물어보세요. '그 방식은 어떤 이유에서인가요?' 한 마디가 오늘 갈등을 만들지 않는 열쇠예요.",
]
_Z_WORK_TIME_UP   = _Z_WORK_STORY_UP
_Z_WORK_TIME_WARN = _Z_WORK_STORY_WARN

# ── 직장운 마무리 풀 ──
_Z_WORK_CLOSE_UP = [
    "오늘 만들어낸 작은 성과 하나가 나중에 기회의 문을 여는 열쇠가 됩니다. 오늘 하루도 수고 많으셨어요. 🌟",
    "남들 눈에 안 보이는 데서 해온 것들이 오늘 조금씩 보이기 시작합니다. 그게 쌓인 거예요. 💼",
]
_Z_WORK_CLOSE_WARN = [
    "쉽지 않은 날이었을 거예요. 그래도 오늘 하루 버텨낸 것, 정말 잘하셨습니다. 내일은 다를 거예요. 🌿",
    "모든 날이 빛날 수는 없어요. 오늘 같은 날이 있어야 좋은 날의 가치가 더 크게 느껴집니다. 오늘은 충분히 쉬어가세요. 💙",
]
_Z_AVOID_ACTIONS = [
    ["멀티태스킹 강행", "피곤한 상태의 중요 대화", "감정 올라올 때 즉각 반응"],
    ["결론 없는 장시간 회의 참석", "새벽까지 무리한 야근", "억지로 흥미 만들기"],
    ["장바구니 결제 바로 누르기", "중요한 약속 충동 취소", "남 험담에 동조하기"],
    ["수면 부족 강행", "에너지 없을 때 설득 시도", "처음 만난 자리에서 큰 약속하기"],
    ["오전 중 중요 결정 미루기", "불필요한 SNS 논쟁 참여", "피로 상태에서 새 프로젝트 수락"],
    ["빈속에 중요한 대화하기", "충분한 정보 없이 팀 합류", "감정적인 메시지 전송"],
    ["혼자 모든 것 해결하려 하기", "계획 없이 큰 지출 시작", "타이밍 놓친 사과 미루기"],
    ["집중 필요한 작업 중 멀티태스킹", "무리한 약속 수락", "에너지 쏟은 후 바로 판단"],
]
_Z_CHEER = [
    "오늘 쉽지 않다는 거 알아요. 그래도 이미 충분히 잘 해내고 있습니다. 조금씩, 천천히 나아가세요. ✨",
    "완벽하지 않아도 괜찮아요. 지금 하고 있는 것들이 쌓여서 당신만의 길이 됩니다. 그 과정을 믿어보세요. 🌟",
    "힘든 날일수록 자신에게 너그러워져도 돼요. 당신이 생각하는 것보다 훨씬 잘 버티고 있습니다. 오늘도 응원합니다. 💫",
    "작은 걸음이 결국 큰 변화를 만듭니다. 조급해하지 말고 지금 이 순간에 집중해 보세요. 🌙",
    "당신 곁에 좋은 기운이 흐르고 있어요. 눈에 보이지 않아도 분명히 쌓이고 있으니, 오늘도 힘내세요. ⭐",
]

def _split_fortune_sections(fortune_text):
    """운세 원문을 문단으로 분리해 섹션별로 배분"""
    plain = fortune_text.replace('<br><br>', '\n\n').replace('<br>', '\n')
    paras = [p.strip() for p in plain.split('\n\n') if p.strip()]
    # 문단이 부족하면 단일 문장 단위로 보충
    if len(paras) < 2:
        lines = [l.strip() for l in plain.split('\n') if l.strip()]
        paras = lines
    return paras

def _zodiac_score_badge(pct):
    """점수 → 색상·레벨 반환"""
    if pct >= 80: return "#16a34a", "상승 ↑"
    if pct >= 65: return "#d97706", "보통 →"
    return "#dc2626", "주의 ⚠"

def _zodiac_score_bar(label, emoji, pct):
    color, level = _zodiac_score_badge(pct)
    filled = round(pct / 10)
    bar = '█' * filled + '░' * (10 - filled)
    return (f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
            f'<span style="min-width:62px;font-size:12px">{emoji} {label}</span>'
            f'<span style="font-family:monospace;color:{color};font-size:13px;flex:1">{bar}</span>'
            f'<span style="font-size:12px;font-weight:700;color:{color};min-width:30px">{pct}%</span>'
            f'<span style="font-size:11px;color:{color}">{level}</span>'
            f'</div>')


def build_zodiac_post(z, today_str):
    fortune_raw = zodiac_fortune(z['kr'])
    rating      = stars()
    card_id     = f"fc-{z['en']}"

    # 날짜 포맷
    kst_now    = now_kst()
    today_dot  = kst_now.strftime("%Y년 %-m월 %-d일")   # 예: 2026년 4월 13일 (본문 표시용)
    today_sync = kst_now.strftime("%Y년 %m월 %d일")     # 예: 2026년 04월 13일 (index.html 매칭용 zero-pad)

    # 운세 지수 (CSV 원본)
    raw_total, raw_money, raw_health, raw_love = pick_score(z['kr'])

    # ① 요일·월 보정 적용 → 최종 지수 + 계산 내역 카드
    total, money, health, love, calc_html = _apply_adjustments(
        raw_total, raw_money, raw_health, raw_love
    )

    # SEO 신호 키워드 (제목 표시용)
    _, signal_kw = _zodiac_seo_title(z['kr'], today_dot, total, money, health, love)

    # 제목: index.html fetchFortunePost() 필수 키워드 고정 포함
    # 검색조건: [별자리명, "YYYY년", "MM월", "DD일", "오늘의 운세"] ALL 포함 필수
    title = f"{z['kr']} {today_sync} 오늘의 운세 | {signal_kw}"

    # 행운 아이템·색상·숫자
    lucky_item   = pick_lucky_item(z['kr'])
    lucky_color  = pick_color()
    lucky_number = pick_number()

    # ② 색상·아이템별 조건부 가이드 생성
    color_guide = get_color_guide(lucky_color)
    item_guide  = get_item_guide(lucky_item)

    # 원문 문단 분리 (섹션 배분용)
    paras = _split_fortune_sections(fortune_raw)
    def _para(idx, fallback=""):
        return paras[idx] if idx < len(paras) else (paras[-1] if paras else fallback)

    # ── 별자리별 고유 구어체 오프닝 & 현실 디테일 블록 ──
    human_voice = _get_zodiac_human_voice(z['kr'])
    real_detail_html = _get_zodiac_real_detail_html(z['kr'], lucky_color)

    # ── 1. 총운 (5파트 구조) ──
    total_color, total_level = _zodiac_score_badge(total)
    total_intro    = random.choice(_Z_TOTAL_INTRO_UP   if total >= 65 else _Z_TOTAL_INTRO_WARN)
    total_score_c  = random.choice(_Z_TOTAL_SCORE_UP   if total >= 65 else _Z_TOTAL_SCORE_WARN)
    total_cheer_c  = random.choice(_Z_CHEER)

    # 구어체 오프닝: 별자리마다 다른 사람 말투 삽입 (AI 티 제거)
    human_voice_html = ""
    if human_voice:
        human_voice_html = f'''
  <p style="margin-top:10px;font-size:14px;line-height:1.9;color:#555;
            background:#f9fafb;border-radius:8px;padding:10px 14px;
            font-style:italic;border-left:3px solid #d1d5db">
    💭 {human_voice}
  </p>'''

    summary_html = f'''
<div class="card" style="border-left:5px solid {total_color}">
  <span class="badge" style="background:#f0fdf4;color:{total_color}">🌟 오늘 총운 · {total}% {total_level}</span>
  <p style="margin-top:12px;font-size:15px;line-height:1.95;color:#333;font-weight:500">{total_intro}</p>
  <p style="margin-top:10px;font-size:14px;line-height:1.9;color:#444">{_para(0)}</p>
  {human_voice_html}
  <p style="margin-top:6px;font-size:14px;line-height:1.9;color:#444">{_para(1)}</p>
  <div style="margin-top:12px;background:#f0fdf4;border-radius:10px;padding:12px 14px;
              font-size:13px;color:#166534;line-height:1.8;border-left:3px solid {total_color}">
    📊 {total_score_c}
  </div>
  <p style="margin-top:12px;font-size:13px;line-height:1.85;color:#666;font-style:italic">{total_cheer_c}</p>
</div>'''

    # ── 2. 연애운 (5파트 구조) ──
    love_color, love_level = _zodiac_score_badge(love)
    love_is_up   = love >= 70
    love_intro   = random.choice(_Z_LOVE_INTRO_UP    if love_is_up else _Z_LOVE_INTRO_WARN)
    love_detail  = random.choice(_Z_LOVE_DETAIL_UP   if love_is_up else _Z_LOVE_DETAIL_WARN)
    love_story   = random.choice(_Z_LOVE_STORY_UP    if love_is_up else _Z_LOVE_STORY_WARN)
    love_close   = random.choice(_Z_LOVE_CLOSE_UP    if love_is_up else _Z_LOVE_CLOSE_WARN)

    # ── 3. 금전운 (5파트 구조) ──
    money_color, money_level = _zodiac_score_badge(money)
    money_is_up   = money >= 70
    money_intro   = random.choice(_Z_MONEY_INTRO_UP   if money_is_up else _Z_MONEY_INTRO_WARN)
    money_score_c = random.choice(_Z_MONEY_SCORE_UP   if money_is_up else _Z_MONEY_SCORE_WARN)
    money_detail  = random.choice(_Z_MONEY_DETAIL_UP  if money_is_up else _Z_MONEY_DETAIL_WARN)
    money_story   = random.choice(_Z_MONEY_STORY_UP   if money_is_up else _Z_MONEY_STORY_WARN)
    money_close   = random.choice(_Z_MONEY_CLOSE_UP   if money_is_up else _Z_MONEY_CLOSE_WARN)

    # ── 4. 직장·사업운 (5파트 구조) ──
    work_score = round((total + health) / 2)
    work_color, work_level = _zodiac_score_badge(work_score)
    work_is_up   = work_score >= 70
    work_intro   = random.choice(_Z_WORK_INTRO_UP    if work_is_up else _Z_WORK_INTRO_WARN)
    work_score_c = random.choice(_Z_WORK_SCORE_UP    if work_is_up else _Z_WORK_SCORE_WARN)
    work_detail  = random.choice(_Z_WORK_DETAIL_UP   if work_is_up else _Z_WORK_DETAIL_WARN)
    work_story   = random.choice(_Z_WORK_STORY_UP    if work_is_up else _Z_WORK_STORY_WARN)
    work_close   = random.choice(_Z_WORK_CLOSE_UP    if work_is_up else _Z_WORK_CLOSE_WARN)

    # ── 시간대 문장: 세 카드 중 1개에만 삽입 ──
    # 날짜(일)를 시드로 사용 → 같은 날 12별자리가 각기 다른 카드에 시간대 배정
    _time_card = now_kst().day % 3   # 0=연애, 1=금전, 2=직장
    _love_time_html  = (f'<p style="margin-top:10px;font-size:13px;line-height:1.8;color:#555">{love_story}</p>'
                        if _time_card == 0 else '')
    _money_time_html = (f'<p style="margin-top:10px;font-size:13px;line-height:1.8;color:#555">{money_story}</p>'
                        if _time_card == 1 else '')
    _work_time_html  = (f'<p style="margin-top:10px;font-size:13px;line-height:1.8;color:#555">{work_story}</p>'
                        if _time_card == 2 else '')

    love_html = f'''
<div class="card">
  <span class="badge" style="background:#fff0f3;color:#e11d48">❤️ 연애운 · {love}% {love_level}</span>
  <p style="margin-top:12px;font-size:15px;line-height:1.95;color:#333;font-weight:500">{love_intro}</p>
  <p style="margin-top:10px;font-size:14px;line-height:1.9;color:#444">{_para(2)}</p>
  <div style="margin-top:12px;background:#fff0f3;border-radius:10px;padding:12px 14px;
              font-size:13px;color:#9f1239;line-height:1.8;border-left:3px solid #e11d48">
    💡 {love_detail}
  </div>
  {_love_time_html}
  <p style="margin-top:10px;font-size:13px;line-height:1.85;color:#666;font-style:italic">{love_close}</p>
</div>'''

    money_html = f'''
<div class="card">
  <span class="badge" style="background:#fefce8;color:#a16207">💰 금전운 · {money}% {money_level}</span>
  <p style="margin-top:12px;font-size:15px;line-height:1.95;color:#333;font-weight:500">{money_intro}</p>
  <p style="margin-top:10px;font-size:14px;line-height:1.9;color:#444">{_para(3)}</p>
  <div style="margin-top:12px;background:#fef9c3;border-radius:10px;padding:12px 14px;
              font-size:13px;color:#78350f;line-height:1.8;border-left:3px solid #d97706">
    📊 {money_score_c}
  </div>
  <div style="margin-top:10px;background:#fefce8;border-radius:10px;padding:12px 14px;
              font-size:13px;color:#92400e;line-height:1.8;border-left:3px solid #f59e0b">
    💡 {money_detail}
  </div>
  {_money_time_html}
  <p style="margin-top:10px;font-size:13px;line-height:1.85;color:#666;font-style:italic">{money_close}</p>
</div>'''

    work_html = f'''
<div class="card">
  <span class="badge" style="background:#eff6ff;color:#1d4ed8">💼 직장·사업운 · {work_score}% {work_level}</span>
  <p style="margin-top:12px;font-size:15px;line-height:1.95;color:#333;font-weight:500">{work_intro}</p>
  <p style="margin-top:10px;font-size:14px;line-height:1.9;color:#444">{_para(4)}</p>
  <div style="margin-top:12px;background:#dbeafe;border-radius:10px;padding:12px 14px;
              font-size:13px;color:#1e3a8a;line-height:1.8;border-left:3px solid #3b82f6">
    📊 {work_score_c}
  </div>
  <div style="margin-top:10px;background:#eff6ff;border-radius:10px;padding:12px 14px;
              font-size:13px;color:#1e3a8a;line-height:1.8;border-left:3px solid #1d4ed8">
    💡 {work_detail}
  </div>
  {_work_time_html}
  <p style="margin-top:10px;font-size:13px;line-height:1.85;color:#666;font-style:italic">{work_close}</p>
</div>'''

    # ── 5. 오늘 피해야 할 행동 ──
    avoid_list = random.choice(_Z_AVOID_ACTIONS)
    avoid_items_html = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;padding:7px 0;'
        f'border-bottom:1px solid #fee2e2;font-size:13px;color:#555">'
        f'<span style="color:#dc2626;font-weight:700;flex-shrink:0">✕</span>{item}</div>'
        for item in avoid_list
    )
    avoid_html = f'''
<div class="card" style="border-left:5px solid #dc2626">
  <span class="badge" style="background:#fef2f2;color:#b91c1c">⚠️ 오늘 피해야 할 행동</span>
  <div style="margin-top:10px">{avoid_items_html}</div>
</div>'''

    # ── 6. 응원 토닥 메시지 ──
    cheer_html = f'''
<div style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:16px;
            padding:22px 20px;margin-bottom:16px;text-align:center">
  <div style="font-size:20px;margin-bottom:8px">{z['emoji']}</div>
  <p style="font-size:14px;color:rgba(255,255,255,0.95);line-height:1.85">
    {random.choice(_Z_CHEER)}
  </p>
</div>'''

    # ── 운세 지수 카드 ──
    score_html = f'''
<div class="card" style="background:#f8f0ff">
  <span class="badge">📊 오늘의 운세 지수 · <strong style="color:#6c3483">{signal_kw}</strong></span>
  <div style="margin-top:12px">
    {_zodiac_score_bar("종합운","🌟",total)}
    {_zodiac_score_bar("금전운","💰",money)}
    {_zodiac_score_bar("건강운","💪",health)}
    {_zodiac_score_bar("애정운","❤️",love)}
  </div>
</div>'''

    # ── 이미지 저장 카드 (총운·연애운·금전운·직장운·피해야할행동 포함) ──
    avoid_short = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;font-size:12px;color:rgba(255,255,255,0.85);padding:4px 0">'
        f'<span style="color:#fca5a5;font-weight:700">✕</span>{item}</div>'
        for item in avoid_list
    )
    image_card_html = f'''
<div id="{card_id}" class="fortune-card">
  <div class="fc-emoji">{z['emoji']}</div>
  <div class="fc-title">{z['kr']}</div>
  <div class="fc-sub">{today_str} · {z['date']}</div>
  <div class="fc-stars">{rating}</div>

  <!-- 총운 -->
  <div style="background:rgba(255,255,255,0.12);border-radius:10px;padding:12px;margin-bottom:8px">
    <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-bottom:6px">🌟 오늘 총운 · {total}%</div>
    <div style="font-size:13px;line-height:1.75;color:rgba(255,255,255,0.95)">{_para(0)}</div>
  </div>

  <!-- 연애운 -->
  <div style="background:rgba(255,255,255,0.12);border-radius:10px;padding:12px;margin-bottom:8px">
    <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-bottom:6px">❤️ 연애운 · {love}%</div>
    <div style="font-size:13px;line-height:1.75;color:rgba(255,255,255,0.95)">{_para(2)}</div>
  </div>

  <!-- 금전운 -->
  <div style="background:rgba(255,255,255,0.12);border-radius:10px;padding:12px;margin-bottom:8px">
    <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-bottom:6px">💰 금전운 · {money}%</div>
    <div style="font-size:13px;line-height:1.75;color:rgba(255,255,255,0.95)">{_para(3)}</div>
  </div>

  <!-- 직장·사업운 -->
  <div style="background:rgba(255,255,255,0.12);border-radius:10px;padding:12px;margin-bottom:8px">
    <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-bottom:6px">💼 직장·사업운 · {work_score}%</div>
    <div style="font-size:13px;line-height:1.75;color:rgba(255,255,255,0.95)">{_para(4)}</div>
  </div>

  <!-- 오늘 피해야 할 행동 -->
  <div style="background:rgba(220,38,38,0.2);border-radius:10px;padding:12px;margin-bottom:12px">
    <div style="font-size:11px;color:rgba(255,255,255,0.7);margin-bottom:6px">⚠️ 오늘 피해야 할 행동</div>
    {avoid_short}
  </div>

  <!-- 행운 아이템 -->
  <div class="fc-lucky">
    <div class="fc-lucky-box"><div class="fc-lucky-lbl">행운 아이템</div><div class="fc-lucky-val" style="font-size:13px">{lucky_item}</div></div>
    <div class="fc-lucky-box"><div class="fc-lucky-lbl">행운 색상</div><div class="fc-lucky-val" style="font-size:13px">{lucky_color}</div></div>
    <div class="fc-lucky-box"><div class="fc-lucky-lbl">행운 숫자</div><div class="fc-lucky-val">{lucky_number}</div></div>
  </div>
  <div class="fc-watermark">todayhoroscopelaboratory.blogspot.com · {today_str}</div>
</div>'''

    # ── SEO 키워드 태그 (③ 별자리 정보·색상·보정 키워드 확장) ──
    z_info = ZODIAC_INFO.get(z['kr'], {})
    kw_list = [
        z['kr'], f"{z['kr']} 오늘운세", f"{z['kr']} 운세",
        f"{z['kr']} 오늘의운세", f"{z['kr']} {today_dot}",
        f"{z['kr']} 별자리운세", f"{z['kr']} 금전운", f"{z['kr']} 연애운",
        f"{z['kr']} 직장운", f"{z['date']} 별자리",
        "오늘의운세", "별자리운세", "무료운세", "별자리오늘",
        "금전운 상승", "연애운 급변", "오늘 주의", "운세 반전",
        f"{z['kr']} 특징", f"{z['kr']} 성격", f"{z['kr']} 궁합",
        f"행운 색상 {lucky_color}", f"행운 아이템 {lucky_item}",
        "운세 지수", "오늘 골든타임", f"{z['kr']} 조언",
    ]
    if z_info.get("compatible"):
        for comp in z_info["compatible"].replace(" ","").split(","):
            kw_list.append(f"{z['kr']} {comp} 궁합")
    tag_html = "".join(f'<span class="tag">{t}</span>' for t in kw_list)

    content = f"""{style()}
<div class="wrap">
  <!-- 히어로 -->
  <div class="hero">
    <h1>{z['emoji']} {z['kr']} 오늘의 운세</h1>
    <p>{today_str} · {z['date']}</p>
    <div style="margin-top:10px;display:inline-block;background:rgba(255,255,255,0.2);
                padding:4px 14px;border-radius:20px;font-size:13px;font-weight:700">
      {signal_kw}
    </div>
  </div>

  <!-- 1. 총운 -->
  {summary_html}

  <!-- 대표 이미지 -->
  {post_img("zodiac")}

  <!-- 2. 연애운 -->
  {love_html}

  <!-- 3. 금전운 -->
  {money_html}

  <!-- 4. 직장·사업운 -->
  {work_html}

  <!-- 5. 오늘 피해야 할 행동 -->
  {avoid_html}

  <!-- 5-1. 현실 디테일 블록 (별자리별 고유) -->
  {real_detail_html}

  <!-- 6. 응원 토닥 메시지 -->
  {cheer_html}

  <!-- ① 운세 지수 계산 내역 카드 (요일·월 보정 근거) -->
  {calc_html}

  <!-- 운세 지수 바 -->
  {score_html}

  <!-- ② 행운 색상·아이템 조건부 가이드 카드 -->
  <div class="card" style="background:linear-gradient(135deg,#fffbeb,#fdf4ff);border-left:5px solid #f59e0b">
    <span class="badge" style="background:#fef3c7;color:#92400e">🍀 오늘의 행운 아이템 & 색상 활용 가이드</span>
    <div style="margin-top:14px;display:grid;gap:10px">
      <div style="background:#fff;border-radius:10px;padding:14px;border:1px solid #fde68a;font-size:13px;line-height:1.85;color:#374151">
        <div style="font-weight:700;color:#b45309;margin-bottom:6px">🎨 행운 색상: {lucky_color}</div>
        {color_guide}
      </div>
      <div style="background:#fff;border-radius:10px;padding:14px;border:1px solid #d1fae5;font-size:13px;line-height:1.85;color:#374151">
        <div style="font-weight:700;color:#065f46;margin-bottom:6px">✨ 행운 아이템: {lucky_item}</div>
        {item_guide}
      </div>
      <div style="background:#fff;border-radius:10px;padding:14px;border:1px solid #e0e7ff;font-size:13px;color:#374151">
        <div style="font-weight:700;color:#4338ca;margin-bottom:4px">🔢 오늘의 행운 숫자: {lucky_number}</div>
        <div style="line-height:1.8">오늘 중요한 결정이나 선택의 순간에 이 숫자를 떠올려 보세요. 비밀번호 힌트, 약속 시간, 좌석 번호 등 작은 선택에서도 의미를 찾을 수 있습니다.</div>
      </div>
    </div>
  </div>

  <!-- 이미지 저장 카드 -->
  {image_card_html}

  <!-- 공유·저장 버튼 -->
  {share_buttons(card_id, f"{z['kr']}_운세_{today_dot}")}

  <!-- ③ 별자리 배경 지식 카드 (SEO 고정 콘텐츠) -->
  {zodiac_info_card(z['kr'], z['emoji'])}

  <!-- SEO 키워드 -->
  <div class="card"><span class="badge">🔍 관련 키워드</span><div class="tag-cloud">{tag_html}</div></div>
  <div class="meta"><p>{z['kr']} ({z['date']})</p><p>※ 재미로 보는 운세 콘텐츠입니다</p></div>
  {site_link()}
</div>"""
    return title, content, ["별자리운세", z['kr'], "운세", "오늘운세"]


def build_chinese_post(c, today_str):
    fortune = chinese_fortune(c['en'])
    rating  = stars()
    card_id = f"fc-{c['en']}"

    kst_now    = now_kst()
    today_dot  = kst_now.strftime("%Y년 %-m월 %-d일")
    today_sync = kst_now.strftime("%Y년 %m월 %d일")

    # ── 운세 지수 (요일·월 보정 적용) ──
    raw_total, raw_money, raw_health, raw_love = pick_score(c['kr'])
    total, money, health, love, calc_html = _apply_adjustments(
        raw_total, raw_money, raw_health, raw_love
    )

    # ── 행운 색상·아이템 (② 조건부 가이드 포함) ──
    lucky_color  = pick_color()
    lucky_item   = pick_lucky_item(c['kr']) or random.choice([
        '수정 팔찌','흰 조약돌','파란 볼펜','노란 메모지','향초','작은 수첩'
    ])
    lucky_number = pick_number()
    color_guide  = get_color_guide(lucky_color)
    item_guide   = get_item_guide(lucky_item)

    # ══════════════════════════════════════════════
    # ① 출생연도별 맞춤 키워드 데이터 (엑셀 VLOOKUP 대체)
    # ══════════════════════════════════════════════
    # 연도대별 특성 → 맞춤 조언 매핑 (40년대~20년대)
    _YEAR_PROFILE = {
        range(1940,1950): ("40년대생",
            "오래 쌓아온 경험이 오늘 빛나는 날이에요. 주변에서 조언을 구하는 사람이 있다면 아끼지 말고 나눠주세요. 그 한마디가 누군가의 흐름을 바꿉니다.",
            "된장찌개·두부·나물 등 발효식품", "5, 8", "계단이 많거나 바닥이 미끄러운 장소"),
        range(1950,1960): ("50년대생",
            "천천히 가는 것 같아도 결국 도달하는 분들이에요. 오늘 한 가지 작은 결정을 미루지 말고 끝내보세요. 작게라도 완성하는 것 자체가 오늘의 에너지를 만듭니다.",
            "제철 나물·현미밥 등 담백한 식단", "3, 6", "급경사 계단이나 미끄러운 바닥"),
        range(1960,1970): ("60년대생",
            "오랜 경험에서 나오는 직관이 오늘 유독 맞는 날이에요. 논리보다 감이 먼저 반응한다면 그쪽을 믿어보세요. 틀릴 확률이 낮은 날입니다.",
            "등푸른 생선·견과류 등 오메가3 식품", "1, 7", "소음이 심한 혼잡한 장소"),
        range(1970,1980): ("70년대생",
            "판단력이 살아있는 날이에요. 오늘 결정해야 할 일이 있다면 망설이지 말고 내리세요. 너무 오래 생각하면 오히려 헷갈리는 날입니다.",
            "고구마·브로콜리 등 항산화 식품", "2, 9", "밀폐된 실내나 환기가 안 되는 공간"),
        range(1980,1990): ("80년대생",
            "에너지가 올라오는 날이에요. 미뤄두던 일 하나만 오늘 처리하세요. '나중에'가 쌓이면 짐이 되지만 오늘 하나 처리하면 내일이 가벼워집니다.",
            "닭가슴살·달걀 등 단백질 식품", "4, 6", "충동적인 쇼핑 앱·판매 사이트"),
        range(1990,2000): ("90년대생",
            "뭔가 바꾸고 싶은 충동이 드는 날일 수 있어요. 그 충동 자체는 맞습니다. 다만 오늘은 실행보다 계획 정리에 쓰는 게 더 유리해요. 내일 움직이면 됩니다.",
            "아보카도·블루베리 등 슈퍼푸드", "3, 7", "인파가 너무 많은 핫플레이스"),
        range(2000,2010): ("00년대생",
            "아이디어가 갑자기 떠오르는 날이에요. 그 순간 메모해두지 않으면 저녁에 기억 못 합니다. 떠오른 것은 바로 메모, 실행은 차근차근 해도 됩니다.",
            "바나나·아몬드 등 에너지 식품", "1, 5", "집중이 필요한데 소음이 많은 장소"),
        range(2010,2020): ("10년대생",
            "오늘 새로운 걸 하나 배우면 생각보다 빠르게 흡수되는 날이에요. 학교 수업이든 유튜브든 뭔가 새로 접하기 좋은 날입니다.",
            "치즈·우유 등 칼슘이 풍부한 식품", "2, 8", "불필요한 경쟁심이 생기는 장소"),
    }
    def _get_year_profile(year_int):
        for yr_range, profile in _YEAR_PROFILE.items():
            if year_int in yr_range:
                return profile
        return ("", "오늘 하루도 당신만의 속도로 나아가세요.", "균형 잡힌 식사", "7", "혼잡한 장소")

    # ══════════════════════════════════════════════
    # ④ 띠별 궁합 데이터 (오늘의 찰떡궁합·거리두기)
    # ══════════════════════════════════════════════
    _CHINESE_COMPAT = {
        '쥐띠':    {'best': ('용띠','🐲','말 꺼내기 전에 이미 통하는 날이에요. 오늘 같이 있으면 일이 빠르게 풀립니다'),
                   'avoid':('말띠','🐴','방향이 달라 말투가 튀기 쉬운 날이에요. 중요한 결정은 둘이 같이 하지 마세요')},
        '소띠':    {'best': ('닭띠','🐓','서로 말 안 해도 눈치로 통하는 날이에요. 같이 있으면 신기하게 일이 맞아떨어져요'),
                   'avoid':('양띠','🐑','속도가 달라서 괜히 답답해지는 조합이에요. 오늘은 서로 각자 페이스로 가세요')},
        '호랑이띠':{'best': ('말띠','🐴','오늘 같이 움직이면 혼자 할 때보다 두 배 빠르게 진행돼요'),
                   'avoid':('원숭이띠','🐵','오늘 주도권 얘기 꺼내면 분위기 이상해질 수 있어요. 역할 먼저 정하고 시작하세요')},
        '토끼띠':  {'best': ('양띠','🐑','오늘 같이 있으면 이유 없이 편안해지는 날이에요. 힘든 말 꺼내기 좋은 상대예요'),
                   'avoid':('닭띠','🐓','말투가 엇갈리기 쉬운 날이에요. 오늘 피드백 주고받는 건 다음으로 미루세요')},
        '용띠':    {'best': ('쥐띠','🐭','오늘 아이디어 막힐 때 이 사람한테 물어보세요. 의외의 각도에서 답이 나와요'),
                   'avoid':('개띠','🐶','원칙 얘기 꺼내면 분위기가 굳어지는 조합이에요. 오늘은 가볍게 지나가세요')},
        '뱀띠':    {'best': ('닭띠','🐓','오늘 이 사람과 대화하면 생각이 정리돼요. 복잡한 것 같이 풀기 좋은 날이에요'),
                   'avoid':('돼지띠','🐷','가치관이 달라 은근히 걸리는 말이 나올 수 있어요. 오늘은 깊은 대화 피하세요')},
        '말띠':    {'best': ('호랑이띠','🐯','오늘 이 사람이랑 있으면 괜히 기분이 올라가요. 같이 움직이면 잘 풀리는 날이에요'),
                   'avoid':('쥐띠','🐭','세세한 것과 큰 그림이 자꾸 엇갈려요. 오늘 같이 결정하는 건 보류하세요')},
        '양띠':    {'best': ('토끼띠','🐰','말 안 해도 알아주는 날이에요. 오늘 힘들면 이 사람한테 연락해보세요'),
                   'avoid':('소띠','🐮','원칙과 감성이 부딪히는 날이에요. 오늘은 의견 충돌 없이 각자 하는 게 나아요')},
        '원숭이띠':{'best': ('쥐띠','🐭','오늘 이 사람이랑 브레인스토밍하면 아이디어가 쏟아져요'),
                   'avoid':('호랑이띠','🐯','서로 리드하려다 말투가 강해지는 날이에요. 역할 나누고 시작하세요')},
        '닭띠':    {'best': ('소띠','🐮','오늘 같이 일하면 군더더기 없이 깔끔하게 마무리돼요'),
                   'avoid':('토끼띠','🐰','기준이 달라서 스트레스 받기 쉬운 조합이에요. 오늘은 각자 방식대로 하세요')},
        '개띠':    {'best': ('호랑이띠','🐯','오늘 이 사람이 옆에 있으면 괜히 든든한 날이에요. 믿고 같이 해도 됩니다'),
                   'avoid':('용띠','🐲','자존심이 부딪히기 쉬운 날이에요. 오늘은 먼저 양보하는 쪽이 이기는 날이에요')},
        '돼지띠':  {'best': ('토끼띠','🐰','오늘 이 사람이랑 있으면 기분이 풀려요. 괜히 웃게 되는 조합이에요'),
                   'avoid':('뱀띠','🐍','사소한 말 한마디가 오래 남는 날이에요. 오늘은 가볍게 대화하는 게 좋아요')},
    }
    compat = _CHINESE_COMPAT.get(c['kr'], {})
    best_compat   = compat.get('best',  ('', '', '오늘 주변 사람 중 말 잘 통하는 사람 한 명 찾아보세요'))
    avoid_compat  = compat.get('avoid', ('', '', '감정적으로 걸리는 대화는 오늘 저녁 이후로 미루세요'))

    compat_html = f'''
<div class="card" style="background:linear-gradient(135deg,#fff7ed,#fef3c7);border-left:5px solid #f59e0b">
  <span class="badge" style="background:#fef3c7;color:#92400e">💑 오늘의 띠별 궁합</span>
  <div style="margin-top:14px;display:grid;gap:10px">
    <div style="background:#fff;border-radius:10px;padding:14px;border:1px solid #d1fae5">
      <div style="font-size:13px;font-weight:700;color:#065f46;margin-bottom:6px">
        🟢 오늘 잘 맞는 띠: {best_compat[1]} {best_compat[0]}
      </div>
      <div style="font-size:13px;color:#374151;line-height:1.8">{best_compat[2]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:6px">
        오늘 {best_compat[0]}와 대화하거나 같이 있는 시간이 생기면 놓치지 마세요.
      </div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:14px;border:1px solid #fee2e2">
      <div style="font-size:13px;font-weight:700;color:#991b1b;margin-bottom:6px">
        🔴 오늘 거리두기: {avoid_compat[1]} {avoid_compat[0]}
      </div>
      <div style="font-size:13px;color:#374151;line-height:1.8">{avoid_compat[2]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:6px">
        오늘 {avoid_compat[0]}와 중요한 얘기는 감정이 차분해진 내일 이후로 미루세요.
      </div>
    </div>
  </div>
</div>'''

    # ══════════════════════════════════════════════
    # ② 시간대별 운세 흐름 지수 (수식 기반 자동 계산)
    # ══════════════════════════════════════════════
    def _time_score(base, morning_mod, afternoon_mod, evening_mod):
        clamp = lambda v: max(1, min(100, v))
        return (clamp(base + morning_mod),
                clamp(base + afternoon_mod),
                clamp(base + evening_mod))

    # 총운 기반 시간대별 분배 (요일 특성 반영)
    dow = now_kst().weekday()  # 0=월 … 6=일
    _TIME_MOD = {  # (오전, 오후, 저녁) 모디파이어
        0: ( 8, -12,  4),   # 월: 오전 집중, 오후 하락
        1: ( 5,   3,  7),   # 화: 오후·저녁 고루 좋음
        2: (10,  -8,  6),   # 수: 오전 강세, 오후 주의
        3: ( 7,   5, 10),   # 목: 저녁 최고
        4: ( 3,   8, 12),   # 금: 오후~저녁 상승
        5: (-5,   2, 10),   # 토: 저녁 강세
        6: ( 2,  -5,  8),   # 일: 오전·저녁 무난
    }
    tm, ta, te = _TIME_MOD[dow]
    am_score, pm_score, ev_score = _time_score(total, tm, ta, te)

    def _time_label(score):
        if score >= 80: return ("#16a34a", "최적 ★", "중요한 일, 연락, 결정 — 지금 하세요")
        if score >= 65: return ("#d97706", "보통 ◐", "무난하게 진행 가능, 급한 일 아니면 여유롭게")
        return ("#dc2626", "주의 ▼", "중요 결정·감정 대화는 이 시간대 피하세요")

    am_c, am_lv, am_tip = _time_label(am_score)
    pm_c, pm_lv, pm_tip = _time_label(pm_score)
    ev_c, ev_lv, ev_tip = _time_label(ev_score)

    time_flow_html = f'''
<div class="card" style="background:#f8faff;border-left:5px solid #3b82f6">
  <span class="badge" style="background:#dbeafe;color:#1d4ed8">⏰ 시간대별 운세 흐름</span>
  <div style="margin-top:14px">
    <table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead>
        <tr style="background:#eff6ff">
          <th style="padding:10px 8px;text-align:left;color:#1e40af;font-weight:700;border-radius:8px 0 0 0">시간대</th>
          <th style="padding:10px 8px;text-align:center;color:#1e40af;font-weight:700">지수</th>
          <th style="padding:10px 8px;text-align:center;color:#1e40af;font-weight:700">평가</th>
          <th style="padding:10px 8px;text-align:left;color:#1e40af;font-weight:700;border-radius:0 8px 0 0">추천 행동</th>
        </tr>
      </thead>
      <tbody>
        <tr style="border-bottom:1px solid #e0e7ff">
          <td style="padding:10px 8px;font-weight:700">🌅 오전<br><span style="font-size:11px;color:#6b7280;font-weight:400">06:00~12:00</span></td>
          <td style="padding:10px 8px;text-align:center;font-weight:900;color:{am_c};font-size:16px">{am_score}점</td>
          <td style="padding:10px 8px;text-align:center;color:{am_c};font-weight:700">{am_lv}</td>
          <td style="padding:10px 8px;color:#374151;line-height:1.6">{am_tip}<br><span style="font-size:11px;color:#6b7280">미뤄두던 중요한 일 하나, 오전에 처리하면 오후가 가벼워집니다</span></td>
        </tr>
        <tr style="border-bottom:1px solid #e0e7ff">
          <td style="padding:10px 8px;font-weight:700">☀️ 오후<br><span style="font-size:11px;color:#6b7280;font-weight:400">12:00~18:00</span></td>
          <td style="padding:10px 8px;text-align:center;font-weight:900;color:{pm_c};font-size:16px">{pm_score}점</td>
          <td style="padding:10px 8px;text-align:center;color:{pm_c};font-weight:700">{pm_lv}</td>
          <td style="padding:10px 8px;color:#374151;line-height:1.6">{pm_tip}<br><span style="font-size:11px;color:#6b7280">연락, 답장, 부탁처럼 사람이 필요한 일은 오후에 하세요</span></td>
        </tr>
        <tr>
          <td style="padding:10px 8px;font-weight:700">🌙 저녁<br><span style="font-size:11px;color:#6b7280;font-weight:400">18:00~24:00</span></td>
          <td style="padding:10px 8px;text-align:center;font-weight:900;color:{ev_c};font-size:16px">{ev_score}점</td>
          <td style="padding:10px 8px;text-align:center;color:{ev_c};font-weight:700">{ev_lv}</td>
          <td style="padding:10px 8px;color:#374151;line-height:1.6">{ev_tip}<br><span style="font-size:11px;color:#6b7280">감정 대화, 가까운 사람과의 시간, 오늘 하루 정리에 적합</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</div>'''

    # ══════════════════════════════════════════════
    # ③ 실전 체크포인트 (IF 조건문 기반 정교화)
    # ══════════════════════════════════════════════
    checkpoints = []
    # 금전운 조건
    if money < 60:
        checkpoints.append(("💰", "#dc2626",
            f"오늘 지갑 조심 (지수 {money}점)",
            "오늘 오후에 '이거 하나쯤이야'가 연달아 나올 수 있는 날이에요. 장바구니에 담았다면 내일 아침에 다시 보세요. 80%는 안 사게 됩니다.",
            "쓰지 않는 구독 서비스 하나만 오늘 끊어도 한 달 지출이 달라집니다. 카드 명세서 10분만 훑어보세요."))
    elif money >= 85:
        checkpoints.append(("💰", "#16a34a",
            f"챙길 돈 있는 날 (지수 {money}점)",
            "환급금, 포인트 전환, 캐시백 신청 중 미뤄둔 게 있으면 오늘 처리하세요. 귀찮아서 묵혀둔 것들이 오늘은 손에 잡히는 날입니다.",
            f"오전 10시~오후 1시 사이가 금전 처리에 가장 유리한 타이밍이에요. 작은 것부터 하나씩 처리해 두세요."))
    else:
        checkpoints.append(("💰", "#d97706",
            f"무난한 금전 흐름 (지수 {money}점)",
            "크게 들어오지도 크게 나가지도 않는 날이에요. 오늘은 지출 내역 한 번 훑어보고, 쓰는지도 몰랐던 자동결제 하나 정리해두세요. 작은 것인데 나중에 쌓여요.",
            "충동구매보다 '원래 사려던 것'을 다시 보는 게 오늘 돈을 아끼는 흐름입니다."))

    # 건강운 조건
    if health >= 90:
        checkpoints.append(("💪", "#16a34a",
            f"몸이 따라주는 날 (지수 {health}점)",
            "오늘은 미뤄두던 운동이나 바깥 활동 하기에 딱 좋아요. 몸이 움직이고 싶다는 신호를 보내는 날입니다.",
            "새로운 운동 루틴을 시작하기 좋은 타이밍이에요. 거창하게 시작하지 않아도 됩니다. 20분 걷기부터도 오늘의 시작이에요."))
    elif health < 60:
        checkpoints.append(("💪", "#dc2626",
            f"몸 신호 무시하지 마세요 (지수 {health}점)",
            "오늘 무리하면 내일 모레 더 크게 무너질 수 있어요. 야근, 과음, 잠 줄이기 — 오늘만큼은 셋 다 패스하세요.",
            "점심 먹고 10분 눈 감는 것만으로도 오후가 달라집니다. 몸이 쉬고 싶다는 신호는 진짜입니다."))
    else:
        checkpoints.append(("💪", "#d97706",
            f"체력 관리 챙기는 날 (지수 {health}점)",
            "특별히 아픈 건 아닌데 왠지 기운이 없는 날일 수 있어요. 물 충분히 마시고, 점심은 제시간에 드세요. 작은 것이지만 오늘은 그게 전부입니다.",
            "오후 3시쯤 견과류나 과일 하나 챙겨 먹으면 저녁까지 집중력이 유지됩니다."))

    # 연애운 조건
    if love >= 80:
        checkpoints.append(("❤️", "#e11d48",
            f"연락해도 되는 날 (지수 {love}점)",
            "오래 연락 못 했던 사람, 미루던 답장, 하고 싶었던 말 — 오늘 그 중 하나만 실행해 보세요. 타이밍이 맞는 날입니다.",
            f"오후 3시~6시 사이에 보내는 메시지가 가장 잘 닿아요. 거창한 말 필요 없어요. '요즘 어때요?' 한 줄로 시작해보세요."))
    elif love < 55:
        checkpoints.append(("❤️", "#6b7280",
            f"감정 말고 거리 먼저 (지수 {love}점)",
            "오늘 중요한 감정 대화는 저녁 이후로 미루세요. 낮 동안은 말이 의도와 다르게 나가기 쉬운 흐름이에요.",
            "상대가 이상한 게 아닐 수 있어요. 오늘은 내 컨디션이 예민한 날일 수 있으니 반응하기 전에 한 번 더 생각하세요."))

    # 총운 기반 종합 조언
    if total >= 85:
        checkpoints.append(("🌟", "#7c3aed",
            f"오늘 움직이기 좋은 날 (종합 {total}점)",
            "미뤄두던 결정, 꺼내지 못했던 말, 시작 못 했던 일 — 오늘이 그 날입니다. 완벽하지 않아도 됩니다. 일단 시작하는 것 자체가 오늘의 정답입니다.",
            f"골든 타임은 {_DOW_GOLDEN_TIME[dow]}이에요. 이 시간대에 핵심 한 가지만 처리해도 오늘 하루 흐름이 달라져요."))
    elif total < 55:
        checkpoints.append(("🌟", "#6b7280",
            f"새로 시작보다 점검하는 날 (종합 {total}점)",
            "오늘 새로 벌이는 것보다 기존 것을 마무리하거나 정리하는 게 맞는 날이에요. 쌓인 것 덜어내는 것만으로도 오늘 하루 잘 한 겁니다.",
            "지금 안 되는 게 실력 문제가 아니라 타이밍 문제일 수 있어요. 2~3일만 기다려보세요. 흐름이 바뀝니다."))

    checkpoint_html_rows = ""
    for icon, color, title_cp, main, detail_cp in checkpoints:
        checkpoint_html_rows += f'''
        <tr style="border-bottom:1px solid #f3f0ff">
          <td style="padding:12px 8px;vertical-align:top">
            <span style="font-size:20px">{icon}</span>
          </td>
          <td style="padding:12px 8px">
            <div style="font-size:13px;font-weight:700;color:{color};margin-bottom:4px">{title_cp}</div>
            <div style="font-size:13px;color:#374151;line-height:1.8;margin-bottom:6px">{main}</div>
            <div style="font-size:12px;color:#6b7280;background:#f9fafb;border-radius:6px;
                        padding:8px;line-height:1.7;border-left:3px solid {color}">
              💡 {detail_cp}
            </div>
          </td>
        </tr>'''

    checkpoint_section = f'''
<div class="card">
  <span class="badge">✅ 오늘 실전 체크포인트 (지수 연동 자동 분석)</span>
  <table style="width:100%;border-collapse:collapse;margin-top:12px">
    {checkpoint_html_rows}
  </table>
</div>'''

    # ══════════════════════════════════════════════
    # ① 출생연도별 맞춤 운세 섹션 (본문 카드)
    # ══════════════════════════════════════════════
    current_year = kst_now.year
    years = [y for y in c['year'].split(',') if int(y) <= current_year]

    # 이미지 카드용 (간략)
    year_rows_in_card = ""
    for y in years:
        yr_fortune = chinese_fortune(c['en'])
        plain = str(yr_fortune).replace('\n', ' ').strip()
        short = plain[:80] + ('…' if len(plain) > 80 else '')
        year_rows_in_card += (
            f'<div style="display:flex;align-items:flex-start;gap:10px;padding:9px 0;'
            f'border-bottom:1px solid rgba(255,255,255,0.18)">'
            f'<div style="min-width:62px;background:rgba(255,255,255,0.22);color:#fff;'
            f'border-radius:8px;padding:4px 7px;text-align:center;font-size:11px;'
            f'font-weight:700;flex-shrink:0">{y}년생</div>'
            f'<div style="font-size:12px;color:rgba(255,255,255,0.9);line-height:1.65;flex:1">{short}</div>'
            f'</div>'
        )

    # 본문용 연도별 맞춤 카드
    year_detail_rows = ""
    for y in years:
        yr_int = int(y)
        _, yr_advice, yr_food, yr_num, yr_avoid = _get_year_profile(yr_int)
        yr_fortune_text = chinese_fortune(c['en'])
        plain = str(yr_fortune_text).replace('\n', ' ').strip()
        year_detail_rows += f'''
        <tr style="border-bottom:1px solid #fef3c7">
          <td style="padding:12px 8px;vertical-align:top;min-width:70px">
            <div style="background:#f59e0b;color:#fff;border-radius:8px;padding:5px 8px;
                        text-align:center;font-size:12px;font-weight:700">{y}년생</div>
          </td>
          <td style="padding:12px 8px">
            <div style="font-size:13px;color:#374151;line-height:1.8;margin-bottom:8px">{yr_advice}</div>
            <div style="font-size:12px;background:#fff7ed;border-radius:8px;padding:8px;
                        border-left:3px solid #f59e0b;color:#78350f;line-height:1.7">
              🍽 추천 음식: <b>{yr_food}</b><br>
              🔢 행운의 숫자: <b>{yr_num}</b>&nbsp;&nbsp;
              🚫 조심할 장소: {yr_avoid}
            </div>
          </td>
        </tr>'''

    year_section_html = f'''
<div class="card" style="background:linear-gradient(135deg,#fffbeb,#fff7ed);border-left:5px solid #f59e0b">
  <span class="badge" style="background:#fef3c7;color:#92400e">📅 출생연도별 오늘 맞춤 운세</span>
  <p style="font-size:13px;color:#78350f;margin:10px 0 14px;line-height:1.8">
    같은 {c['kr']}라도 출생연도에 따라 오늘의 기운과 에너지가 미묘하게 다르게 나타납니다.
    아래에서 본인의 출생연도를 찾아 맞춤 운세를 확인해 보세요.
  </p>
  <table style="width:100%;border-collapse:collapse">
    {year_detail_rows}
  </table>
</div>'''

    # ── 주의점 본문 추출 ──
    caution_kws = ["주의", "조심", "피하", "삼가", "무리하지", "충동", "서두르지"]
    plain_fortune = str(fortune).replace('\n', ' ').strip()
    caution_sentence = next(
        (s.strip() for s in plain_fortune.split('. ')
         if any(k in s for k in caution_kws) and len(s.strip()) > 10), ""
    )
    caution_html = f'''
<div style="background:#fff8e1;border-left:4px solid #f59e0b;border-radius:10px;
            padding:14px 16px;margin-bottom:16px">
  <div style="font-size:12px;font-weight:700;color:#d97706;margin-bottom:6px">⚠️ 오늘의 주의점</div>
  <div style="font-size:14px;color:#555;line-height:1.75">{caution_sentence}</div>
</div>''' if caution_sentence else ""

    # ── 운세 지수 바 차트 ──
    def _sc(v): return ("#16a34a","상승 ↑") if v>=80 else (("#d97706","보통") if v>=65 else ("#dc2626","주의 ⚠"))
    def _bar(label, emoji, pct):
        c2, lv = _sc(pct); f2 = round(pct/10)
        return (f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:9px">'
                f'<span style="min-width:65px;font-size:12px">{emoji} {label}</span>'
                f'<span style="font-family:monospace;color:{c2};font-size:13px">{"█"*f2}{"░"*(10-f2)}</span>'
                f'<span style="font-size:12px;font-weight:700;color:{c2};min-width:28px">{pct}%</span>'
                f'<span style="font-size:11px;color:{c2}">{lv}</span></div>')

    # ── 제목: 4가지 패턴 순환 (날짜 홀짝 + 점수 조건 조합) ──
    kst_day  = kst_now.day
    kst_mon  = kst_now.month
    year_abbr = ",".join(y[-2:]+"년" for y in years[:5])  # 예: 47·59·71·83·95년
    # 점수 기반 접두어 (③ IF 로직)
    if money < 60:   score_prefix = f"[금전운 주의] "
    elif total >= 85: score_prefix = f"[오늘 최고의 날] "
    elif health < 60: score_prefix = f"[건강 관리 필요] "
    else:             score_prefix = ""
    # 제목 4종 순환
    _TITLE_PATTERNS = [
        # 패턴1: 종합 지수 노출
        f"{c['kr']} {today_sync} 오늘의 띠운세 | 종합 지수 {total}% {score_prefix.strip()}",
        # 패턴2: 출생연도 타겟팅
        f"오늘의 {c['kr']} 운세 ({year_abbr}생) {kst_mon}월 {kst_day}일 핵심 요약",
        # 패턴3: 액션 가이드형
        f"{score_prefix}{c['kr']} {kst_mon}월 {kst_day}일 반드시 체크할 포인트 | 지수 {total}%",
        # 패턴4: SEO 앞배치형 (띠+운세 먼저)
        f"오늘의 {c['kr']} 운세 {today_sync} | 행운 색상·실전 체크포인트 포함",
    ]
    # index.html 매칭 필수 키워드 보존: 띠명, YYYY년, MM월, DD일, 띠운세
    # → 패턴1·4만 "띠운세" 포함 → 짝수/홀수 날짜로 순환
    # 홀수 날짜: 패턴1(지수 노출) / 짝수 날짜: 패턴4(SEO 앞배치)
    # 단, fetchChinesePost() 매칭을 위해 기본 패턴은 유지하되 suffix 변경
    if kst_day % 4 == 0:   signal_title = _TITLE_PATTERNS[3]
    elif kst_day % 4 == 1: signal_title = _TITLE_PATTERNS[0]
    elif kst_day % 4 == 2: signal_title = _TITLE_PATTERNS[1]
    else:                  signal_title = _TITLE_PATTERNS[2]

    # index.html fetchChinesePost() 매칭 필수: [띠명, YYYY년, MM월, DD일, 띠운세] 포함 보장
    title = f"{c['kr']} {today_sync} 오늘의 띠운세 | {signal_title.split('|')[-1].strip()}"

    # ── 신호 키워드 (score_html·hero용) ──
    avg = (total + money) / 2
    _SIG_UP   = ["오늘 작은 수입 챙길 타이밍", "환급·포인트 확인하기 좋은 날", "들어오는 흐름의 날"]
    _SIG_WARN = ["오늘 충동 결제 특히 주의", "지갑 닫는 게 최선인 날", "신중하게 보는 날"]
    _SIG_REV  = ["예상 밖 연락이 올 수 있는 날", "뒤집히는 흐름의 날", "약속 하나가 바뀔 수 있는 날"]
    _SIG_MID  = ["잔잔하게 흘러가는 날", "무리하지 않으면 괜찮은 날", "차분하게 챙기는 날"]
    if avg >= 80:                signal = random.choice(_SIG_UP)
    elif avg <= 55:              signal = random.choice(_SIG_WARN)
    elif abs(total-money) >= 30: signal = random.choice(_SIG_REV)
    else:                        signal = random.choice(_SIG_MID)

    # ── 띠별 구어체 오프닝 & 현실 디테일 ──
    chinese_human_voice = _get_chinese_human_voice(c['kr'])
    chinese_real_detail = _get_chinese_real_detail_html(c['kr'])
    chinese_human_html = ""
    if chinese_human_voice:
        chinese_human_html = f'''
<div class="card" style="background:#f9fafb;border-left:4px solid #d1d5db">
  <p style="font-size:14px;line-height:1.9;color:#555;font-style:italic;margin:0">
    💭 {chinese_human_voice}
  </p>
</div>'''

    score_html = f'''<div class="card" style="background:#f8f0ff">
  <span class="badge">📊 오늘의 운세 지수 · <strong style="color:#6c3483">{signal}</strong></span>
  <div style="margin-top:12px">
    {_bar("종합운","🌟",total)}{_bar("금전운","💰",money)}{_bar("건강운","💪",health)}{_bar("애정운","❤️",love)}
  </div>
</div>'''

    # ── 행운 가이드 카드 ──
    lucky_guide_html = f'''
<div class="card" style="background:linear-gradient(135deg,#fffbeb,#fdf4ff);border-left:5px solid #f59e0b">
  <span class="badge" style="background:#fef3c7;color:#92400e">🍀 오늘의 행운 아이템 & 색상 활용 가이드</span>
  <div style="margin-top:14px;display:grid;gap:10px">
    <div style="background:#fff;border-radius:10px;padding:14px;border:1px solid #fde68a;
                font-size:13px;line-height:1.85;color:#374151">
      <div style="font-weight:700;color:#b45309;margin-bottom:6px">🎨 행운 색상: {lucky_color}</div>
      {color_guide}
    </div>
    <div style="background:#fff;border-radius:10px;padding:14px;border:1px solid #d1fae5;
                font-size:13px;line-height:1.85;color:#374151">
      <div style="font-weight:700;color:#065f46;margin-bottom:6px">✨ 행운 아이템: {lucky_item}</div>
      {item_guide}
    </div>
    <div style="background:#fff;border-radius:10px;padding:14px;border:1px solid #e0e7ff;font-size:13px;color:#374151">
      <div style="font-weight:700;color:#4338ca;margin-bottom:4px">🔢 행운 숫자: {lucky_number}</div>
      오늘 중요한 선택의 순간에 이 숫자를 떠올려 보세요. 비밀번호, 약속 시간, 좌석 번호 등 작은 선택에서도 의미를 찾을 수 있습니다.
    </div>
  </div>
</div>'''

    # ── SEO 키워드 (확장) ──
    years_tags = [f"{y}년생 {c['kr']}" for y in years]
    kw_list = [
        c['kr'], f"{c['kr']} 오늘운세", f"{c['kr']} 오늘의운세",
        f"{c['kr']} 띠운세", f"{c['kr']} {today_dot}",
        f"{c['kr']} 재물운", f"{c['kr']} 건강운", f"{c['kr']} 애정운",
        "띠운세 오늘", "오늘의운세", "무료운세", f"운세 {today_dot[:4]}",
        "재물운 상승", "오늘 주의", "띠별운세",
        f"{c['kr']} 시간대별 운세", f"{c['kr']} 출생연도별 운세",
        f"{c['kr']} 궁합", f"오늘 찰떡궁합 {best_compat[0]}",
        f"행운 색상 {lucky_color}", f"행운 아이템 {lucky_item}",
        "운세 지수", "오늘 골든타임",
    ] + years_tags
    tag_html = "".join(f'<span class="tag">{t}</span>' for t in kw_list)

    content = f"""{style()}
<div class="wrap">
  <div class="hero" style="background:linear-gradient(135deg,#f59e0b,#d97706)">
    <h1>{c['emoji']} {c['kr']} 오늘의 운세</h1>
    <p>{today_str} · 종합 지수 {total}%</p>
    <div style="margin-top:8px;display:inline-block;background:rgba(0,0,0,0.18);
                padding:3px 14px;border-radius:20px;font-size:12px;font-weight:700">{signal}</div>
  </div>

  <!-- 운세 지수 바 + 계산 내역 -->
  {score_html}
  {calc_html}

  <!-- 띠별 구어체 오프닝 -->
  {chinese_human_html}

  <!-- 시간대별 운세 흐름 표 -->
  {time_flow_html}

  <!-- 이미지 저장 카드 -->
  <div id="{card_id}" class="fortune-card" style="background:linear-gradient(135deg,#f59e0b,#92400e)">
    <div class="fc-emoji">{c['emoji']}</div>
    <div class="fc-title">{c['kr']}</div>
    <div class="fc-sub">{today_str} · 종합 {total}%</div>
    <div class="fc-stars">{rating}</div>
    <div class="fc-text">{fortune}</div>
    <div style="margin-top:14px;border-top:1px solid rgba(255,255,255,0.3);padding-top:12px">
      <div style="font-size:11px;font-weight:700;color:rgba(255,255,255,0.7);margin-bottom:8px">📅 출생연도별 오늘 운세</div>
      {year_rows_in_card}
    </div>
    <div class="fc-watermark" style="margin-top:14px">todayhoroscopelaboratory.blogspot.com · {today_str}</div>
  </div>

  {share_buttons(card_id, f"{c['kr']}_운세_{today_dot}")}

  <!-- 대표 이미지 -->
  {post_img("chinese")}

  <!-- 출생연도별 맞춤 운세 (본문 상세) -->
  {year_section_html}

  <!-- 실전 체크포인트 (지수 연동) -->
  {checkpoint_section}

  {caution_html}

  <!-- 현실 디테일 블록 (띠별 고유) -->
  {chinese_real_detail}

  <!-- 띠별 궁합 -->
  {compat_html}

  <!-- 행운 아이템·색상 가이드 -->
  {lucky_guide_html}

  <div class="card"><span class="badge">🔍 관련 키워드</span><div class="tag-cloud">{tag_html}</div></div>
  <div class="meta"><p>{c['kr']} 출생연도: {c['year']}</p><p>※ 재미로 보는 운세 콘텐츠입니다</p></div>
  {site_link()}
</div>"""
    return title, content, ["띠운세", c['kr'], "운세", "오늘운세"]


def zodiac_weekly_fortune(kr_name):
    """주간 운세 CSV에서 가져오기 — zodiac_weekly_1000.csv"""
    if not zodiac_weekly.empty and 'zodiac' in zodiac_weekly.columns:
        m = zodiac_weekly[zodiac_weekly['zodiac'] == kr_name]
        if not m.empty:
            text = m.sample(1).iloc[0]['fortune']
            return str(text).replace('\n\n', '<br><br>').replace('\n', '<br>')
    return sentence()

def zodiac_monthly_fortune(kr_name):
    """월간 운세 CSV에서 가져오기 — zodiac_monthly_1000.csv"""
    if not zodiac_monthly.empty and 'zodiac' in zodiac_monthly.columns:
        m = zodiac_monthly[zodiac_monthly['zodiac'] == kr_name]
        if not m.empty:
            text = m.sample(1).iloc[0]['fortune']
            return str(text).replace('\n\n', '<br><br>').replace('\n', '<br>')
    return sentence()

def chinese_weekly_fortune(en_name):
    """띠 주간 운세 CSV에서 가져오기 — chinese_weekly_1000.csv"""
    if not chinese_weekly.empty and 'animal_zodiac' in chinese_weekly.columns:
        m = chinese_weekly[chinese_weekly['animal_zodiac'] == en_name]
        if not m.empty:
            return m.sample(1).iloc[0]['fortune']
    return sentence()

def chinese_monthly_fortune(en_name):
    """띠 월간 운세 CSV에서 가져오기 — chinese_monthly_1000.csv"""
    if not chinese_monthly.empty and 'animal_zodiac' in chinese_monthly.columns:
        m = chinese_monthly[chinese_monthly['animal_zodiac'] == en_name]
        if not m.empty:
            return m.sample(1).iloc[0]['fortune']
    return sentence()

def build_zodiac_weekly_post(today_str):
    """별자리별 주간운세 12개 개별 발행 — 매주 월요일"""
    week_range = get_week_range()
    today_date = now_kst().date()
    mon_date   = date.fromordinal(today_date.toordinal() - today_date.weekday())
    month_str  = mon_date.strftime("%Y년 %m월")
    results = []
    for z in ZODIACS:
        fortune = zodiac_weekly_fortune(z['kr'])
        rating  = stars()
        card_id = f"zwfc-{z['en']}"
        total, money, health, love = pick_score(z['kr'])

        # 제목 신호 키워드 (간단히)
        scores = {"총운": total, "금전운": money, "건강운": health, "애정운": love}
        top = max(scores, key=scores.get)
        low = min(scores, key=scores.get)
        if scores[top] >= 80:
            signal_map = {
                "총운":  "이번 주 움직이기 좋은 흐름",
                "금전운": "이번 주 환급·포인트 챙길 타이밍",
                "건강운": "이번 주 새 운동 루틴 시작하기 좋은 날",
                "애정운": "이번 주 먼저 연락해도 되는 흐름",
            }
            signal = signal_map.get(top, f"이번 주 {top} 주목")
        elif scores[low] <= 55:
            signal_map_warn = {
                "총운":  "이번 주 버티는 게 전략인 흐름",
                "금전운": "이번 주 충동 결제 특히 주의",
                "건강운": "이번 주 무리하지 않는 게 핵심",
                "애정운": "이번 주 감정 대화 타이밍 조심",
            }
            signal = signal_map_warn.get(low, f"이번 주 {low} 주의")
        else:
            signal = "이번 주 잔잔하게 챙기는 흐름"
        # 제목: index.html fetchWeeklyPost() 필수 키워드 고정 포함
        # 검색조건: [별자리명, "YYYY년", "MM월", "주간운세"] ALL 포함 필수
        title = f"{z['kr']} {month_str} 주간운세 {week_range} | {signal}"

        kw_list = [
            z['kr'], f"{z['kr']} 주간운세", f"{z['kr']} 이번주운세",
            "별자리 주간운세", f"{z['kr']} {month_str}", "주간운세", "별자리운세"
        ]
        tag_html = "".join(f'<span class="tag">{t}</span>' for t in kw_list)
        score_html = f'''<div class="card" style="background:#f8f0ff">
  <span class="badge">📊 이번 주 운세 지수</span>
  <div style="margin-top:10px">
    {_zodiac_score_bar("종합운","🌟",total)}
    {_zodiac_score_bar("금전운","💰",money)}
    {_zodiac_score_bar("건강운","💪",health)}
    {_zodiac_score_bar("애정운","❤️",love)}
  </div>
</div>'''

        content_html = f"""{style()}
<div class="wrap">
  <div class="hero">
    <h1>📅 {z['emoji']} {z['kr']} 주간운세</h1>
    <p>{week_range} · {z['date']}</p>
    <div style="margin-top:8px;display:inline-block;background:rgba(255,255,255,0.2);padding:3px 12px;border-radius:20px;font-size:12px">{signal}</div>
  </div>
  <div id="{card_id}" class="fortune-card">
    <div class="fc-emoji">{z['emoji']}</div>
    <div class="fc-title">{z['kr']} 주간운세</div>
    <div class="fc-sub">{week_range} · {z['date']}</div>
    <div class="fc-stars">{rating}</div>
    <div class="fc-text">{fortune}</div>
    <div class="fc-watermark">todayhoroscopelaboratory.blogspot.com · {week_range}</div>
  </div>
  {share_buttons(card_id, f"{z['kr']}_주간운세")}

  <!-- 대표 이미지 -->
  {post_img("weekly")}

  {score_html}
  <div class="card"><span class="badge">🔍 관련 키워드</span><div class="tag-cloud">{tag_html}</div></div>
  {site_link()}
  <div class="meta">※ 재미로 보는 운세 콘텐츠입니다 · 매주 업데이트</div>
</div>"""
        results.append((title, content_html, ["별자리주간", z['kr'], "주간운세"]))
    return results


def build_chinese_monthly_post(today_str):
    """띠별 월간운세 12개 개별 발행 — 매월 1일 / v2 구조"""
    month_str = get_next_month_str()
    results   = []

    # ── v2 CSV 로드 ──
    v2_path = os.path.join(DATA, "chinese_monthly_v2.csv")
    v2_df   = pd.DataFrame()
    if os.path.exists(v2_path):
        v2_df = pd.read_csv(v2_path, encoding="utf-8")

    def _v2_row(en_name):
        """띠별 v2 데이터 랜덤 1행 반환. 없으면 None."""
        if v2_df.empty:
            return None
        m = v2_df[v2_df['animal_zodiac'] == en_name]
        return m.sample(1).iloc[0] if not m.empty else None

    # ── 운세 지수 이유 문구 풀 ──
    _SCORE_REASON = {
        "total_up":   [
            "조용히 쌓아온 것들이 이달 중순쯤 하나씩 보이기 시작하는 흐름",
            "기다리던 연락이나 결과가 이달 안에 들어올 가능성 있음",
            "먼저 움직이는 쪽이 유리한 달 — 타이밍 놓치지 마세요",
        ],
        "total_warn": [
            "이달은 새로 벌이기보다 버티는 게 더 현명한 달",
            "무리하게 밀어붙일수록 손해가 커지는 흐름 — 속도 줄이세요",
        ],
        "money_up":   [
            "충동구매만 줄이면 이달 말에 생각보다 돈이 남는 구조",
            "미뤄둔 환급·정산 이달 안에 꼭 챙기세요. 안 챙기면 그냥 사라집니다",
            "쓰는 것보다 지키는 것이 이달 금전운의 핵심",
        ],
        "money_warn": [
            "이달 큰 지출 결정은 다음 달로 미루는 게 훨씬 유리합니다",
            "투자보다 저축 — 이달만큼은 지키는 게 버는 것입니다",
        ],
        "health_up":  [
            "체력이 올라오는 달 — 새 운동 루틴 시작하기 딱 좋은 타이밍",
            "몸이 따라주는 달이에요. 미뤄뒀던 건강검진이나 운동, 이달 안에 해두세요",
            "숙면만 지켜도 이달 에너지가 확 달라지는 흐름",
        ],
        "health_warn":[
            "이달 중순 이후 과로 누적 주의 — 지금부터 무리하지 마세요",
            "소화·수면 이 두 가지만 챙기면 이달 버티는 데 든든한 기반이 돼요",
        ],
        "love_up":    [
            "썸보다 이미 가까운 사람에게서 감정 발전 가능성이 더 높은 달",
            "먼저 연락하거나 먼저 표현하는 쪽이 유리한 흐름입니다",
            "말 한마디가 관계 깊이를 바꾸는 달 — 솔직하게 꺼내보세요",
        ],
        "love_warn":  [
            "오해가 생기기 쉬운 달 — 말하기 전에 한 번 더 생각하세요",
            "감정적 반응보다 한 박자 여유가 이달 관계를 지킵니다",
        ],
    }

    def _score_reason(label, val):
        if label == "total":
            pool = _SCORE_REASON["total_up"] if val >= 65 else _SCORE_REASON["total_warn"]
        elif label == "money":
            pool = _SCORE_REASON["money_up"] if val >= 65 else _SCORE_REASON["money_warn"]
        elif label == "health":
            pool = _SCORE_REASON["health_up"] if val >= 65 else _SCORE_REASON["health_warn"]
        else:
            pool = _SCORE_REASON["love_up"] if val >= 65 else _SCORE_REASON["love_warn"]
        return random.choice(pool)

    def _bar(pct):
        filled = round(pct / 10)
        return "█" * filled + "░" * (10 - filled)

    for c in CHINESE:
        v2  = _v2_row(c['en'])
        rating  = stars()
        card_id = f"cmfc-{c['en']}"
        total, money, health, love = pick_score(c['kr'])

        # ── 제목 신호 ──
        scores = {"총운": total, "금전운": money, "건강운": health, "애정운": love}
        top = max(scores, key=scores.get)
        low = min(scores, key=scores.get)
        if scores[top] >= 80:
            signal_map = {
                "총운":  "이달 움직이기 좋은 흐름",
                "금전운": "이달 환급·포인트 챙길 타이밍",
                "건강운": "이달 새 운동 루틴 시작하기 딱",
                "애정운": "이달 먼저 연락해도 되는 흐름",
            }
            signal = signal_map.get(top, f"이달 {top} 상승")
        elif scores[low] <= 55:
            signal_map_warn = {
                "총운":  "이달 버티는 게 전략인 흐름",
                "금전운": "이달 충동 결제 주의",
                "건강운": "이달 무리하지 않는 게 핵심",
                "애정운": "이달 감정 대화 타이밍 조심",
            }
            signal = signal_map_warn.get(low, f"이달 {low} 주의")
        else:
            signal = "이달 잔잔하게 챙기는 흐름"
        title = f"{c['kr']} {month_str} 월간운세 | {signal}"

        # ── v2 데이터 추출 ──
        headline    = v2['headline']    if v2 is not None else chinese_monthly_fortune(c['en'])
        upper_txt   = v2['upper']       if v2 is not None else chinese_monthly_fortune(c['en'])
        mid_txt     = v2['mid']         if v2 is not None else chinese_monthly_fortune(c['en'])
        lower_txt   = v2['lower']       if v2 is not None else chinese_monthly_fortune(c['en'])
        lucky_color  = v2['lucky_color']  if v2 is not None else "골드"
        lucky_number = v2['lucky_number'] if v2 is not None else "3"
        lucky_place  = v2['lucky_place']  if v2 is not None else "카페"
        avoid_kw     = v2['avoid']        if v2 is not None else "즉흥적인 결정"
        sympathy     = v2['sympathy']     if v2 is not None else ""

        # ── 모바일 최적화: \n → <br> ──
        def _mb(text):
            return str(text).replace('\n', '<br>')

        # ── 1. 핵심 한줄 운세 블록 ──
        headline_html = f'''
<div class="card" style="background:linear-gradient(135deg,#fffbeb,#fef9c3);
     border-left:5px solid #f59e0b;padding:18px 16px">
  <p style="font-size:17px;font-weight:900;color:#92400e;
            line-height:1.7;margin:0">{_mb(headline)}</p>
</div>'''

        # ── 2. 운세 지수 (이유 포함) ──
        score_html = f'''
<div class="card" style="background:#fffbeb">
  <span class="badge" style="background:#fef3c7;color:#92400e">📊 이번 달 운세 지수</span>
  <div style="margin-top:14px;display:grid;gap:10px">
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #fde68a">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <span style="font-size:13px;font-weight:700">🌟 종합운</span>
        <span style="font-size:13px;font-weight:900;color:#d97706">{total}%</span>
      </div>
      <div style="font-family:monospace;font-size:13px;color:#f59e0b;letter-spacing:1px">{_bar(total)}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:5px">→ {_score_reason("total",total)}</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #fee2e2">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <span style="font-size:13px;font-weight:700">💰 금전운</span>
        <span style="font-size:13px;font-weight:900;color:#dc2626">{money}%</span>
      </div>
      <div style="font-family:monospace;font-size:13px;color:#f87171;letter-spacing:1px">{_bar(money)}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:5px">→ {_score_reason("money",money)}</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #d1fae5">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <span style="font-size:13px;font-weight:700">💪 건강운</span>
        <span style="font-size:13px;font-weight:900;color:#059669">{health}%</span>
      </div>
      <div style="font-family:monospace;font-size:13px;color:#34d399;letter-spacing:1px">{_bar(health)}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:5px">→ {_score_reason("health",health)}</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #fce7f3">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
        <span style="font-size:13px;font-weight:700">❤️ 애정운</span>
        <span style="font-size:13px;font-weight:900;color:#db2777">{love}%</span>
      </div>
      <div style="font-family:monospace;font-size:13px;color:#f472b6;letter-spacing:1px">{_bar(love)}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:5px">→ {_score_reason("love",love)}</div>
    </div>
  </div>
</div>'''

        # ── 3. 기간별 운세 (사건형, 모바일 최적화) ──
        def _period_card(emoji, label, dates, text, grad_from, grad_to, border_color):
            return f'''
<div class="card" style="background:linear-gradient(135deg,{grad_from},{grad_to});
     border-left:5px solid {border_color};padding:16px">
  <div style="font-size:13px;font-weight:900;color:#374151;margin-bottom:10px">
    {emoji} <span style="color:{border_color}">{label}</span>
    <span style="font-size:11px;color:#9ca3af;margin-left:6px">{dates}</span>
  </div>
  <p style="font-size:14px;line-height:2;color:#374151;margin:0;
            white-space:pre-line">{text}</p>
</div>'''

        period_html = (
            _period_card("🌱","상순","1~10일",  upper_txt, "#f0fdf4","#ecfdf5","#10b981") +
            _period_card("🌿","중순","11~20일", mid_txt,   "#eff6ff","#f0f9ff","#3b82f6") +
            _period_card("🍂","하순","21~말일", lower_txt, "#faf5ff","#fdf4ff","#8b5cf6")
        )

        # ── 4. 행운 키워드 블록 ──
        lucky_html = f'''
<div class="card" style="background:linear-gradient(135deg,#fffbeb,#fdf4ff);
     border-left:5px solid #f59e0b">
  <span class="badge" style="background:#fef3c7;color:#92400e">🍀 이달의 행운 키워드</span>
  <div style="margin-top:14px;display:grid;grid-template-columns:1fr 1fr;gap:8px">
    <div style="background:#fff;border-radius:10px;padding:12px;
                border:1px solid #fde68a;text-align:center">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">행운의 색</div>
      <div style="font-size:14px;font-weight:700;color:#92400e">{lucky_color}</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px;
                border:1px solid #dbeafe;text-align:center">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">행운의 숫자</div>
      <div style="font-size:14px;font-weight:700;color:#1d4ed8">{lucky_number}</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px;
                border:1px solid #d1fae5;text-align:center">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">행운의 장소</div>
      <div style="font-size:13px;font-weight:700;color:#065f46">{lucky_place}</div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:12px;
                border:1px solid #fee2e2;text-align:center">
      <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">이달 피할 것</div>
      <div style="font-size:13px;font-weight:700;color:#dc2626">{avoid_kw}</div>
    </div>
  </div>
</div>'''

        # ── 5. 현실 공감 문장 ──
        sympathy_html = ""
        if sympathy:
            sympathy_html = f'''
<div class="card" style="background:#f9fafb;border-left:4px solid #d1d5db">
  <span class="badge" style="background:#f3f4f6;color:#374151">💬 지금 이런 느낌이라면</span>
  <p style="margin-top:12px;font-size:14px;line-height:2;color:#374151;
            font-style:italic;white-space:pre-line">{sympathy}</p>
</div>'''

        # ── 이미지 저장 카드 (게임링크 없음) ──
        card_html = f'''
<div id="{card_id}" class="fortune-card"
     style="background:linear-gradient(135deg,#f59e0b,#92400e)">
  <div class="fc-emoji">{c['emoji']}</div>
  <div class="fc-title">{c['kr']} 월간운세</div>
  <div class="fc-sub">{month_str}</div>
  <div class="fc-stars">{rating}</div>
  <div class="fc-text" style="white-space:pre-line">{_mb(headline)}</div>
  <div class="fc-watermark">
    todayhoroscopelaboratory.blogspot.com · {month_str}
  </div>
</div>'''

        # ── 관련 키워드 ──
        kw_list  = [c['kr'], f"{c['kr']} 월간운세", f"{c['kr']} 이달운세",
                    "띠별 월간운세", f"{c['kr']} {month_str}", "월간운세", "띠운세"]
        tag_html = "".join(f'<span class="tag">{t}</span>' for t in kw_list)

        content_html = f"""{style()}
<div class="wrap">

  <!-- 히어로 -->
  <div class="hero" style="background:linear-gradient(135deg,#f59e0b,#d97706)">
    <h1>🌙 {c['emoji']} {c['kr']} 월간운세</h1>
    <p>{month_str}</p>
    <div style="margin-top:8px;display:inline-block;background:rgba(255,255,255,0.2);
                padding:3px 12px;border-radius:20px;font-size:12px">{signal}</div>
  </div>

  <!-- 1. 핵심 한줄 운세 -->
  {headline_html}

  <!-- 2. 이미지 저장 카드 -->
  {card_html}
  {share_buttons(card_id, f"{c['kr']}_월간운세")}

  <!-- 대표 이미지 -->
  {post_img("monthly")}

  <!-- 3. 운세 지수 (이유 포함) -->
  {score_html}

  <!-- 4. 기간별 운세 (사건형) -->
  <div style="margin:6px 0 4px;font-size:13px;font-weight:700;
              color:#374151;padding:0 4px">📅 {month_str} 기간별 흐름</div>
  {period_html}

  <!-- 5. 행운 키워드 -->
  {lucky_html}

  <!-- 6. 현실 공감 문장 -->
  {sympathy_html}

  <!-- 관련 키워드 -->
  <div class="card">
    <span class="badge">🔍 관련 키워드</span>
    <div class="tag-cloud">{tag_html}</div>
  </div>

  {site_link()}
  <div class="meta">※ 재미로 보는 운세 콘텐츠입니다 · 매월 업데이트</div>
</div>"""

        results.append((title, content_html, ["띠별월간", c['kr'], "월간운세"]))
    return results


# ─────────────────────────────────────────
# Refresh Token으로 Access Token 자동 발급
# ─────────────────────────────────────────
BLOG_ID       = os.environ.get("BLOG_ID","")
REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN","")
CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID","")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET","")

def get_access_token():
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "grant_type":    "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    if resp.status_code == 200:
        print("🔑 Access Token 자동 갱신 완료")
        return resp.json().get("access_token","")
    else:
        print(f"❌ Token 갱신 실패: {resp.text[:120]}")
        return os.environ.get("BLOGGER_TOKEN","")

ACCESS_TOKEN = get_access_token() if REFRESH_TOKEN else os.environ.get("BLOGGER_TOKEN","")

def post_blogger(title, content, labels, idx, total):
    if not BLOG_ID or not ACCESS_TOKEN:
        print(f"[{idx:02d}/{total}] (테스트) {title[:50]}")
        return True

    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    
    for attempt in range(1, 4):  # 최대 3회 재시도
        resp = requests.post(url,
            headers={"Authorization":f"Bearer {ACCESS_TOKEN}","Content-Type":"application/json"},
            json={"title":title,"content":content,"labels":labels}
        )
        if resp.status_code == 200:
            print(f"[{idx:02d}/{total}] ✅ {title[:45]}  →  200")
            time.sleep(3)   # 분당 쿼터 보호: 3초 간격
            return True
        elif resp.status_code == 429:
            wait = 60 * attempt  # 1분, 2분, 3분
            print(f"[{idx:02d}/{total}] ⏳ 429 쿼터 초과 — {wait}초 대기 후 재시도 ({attempt}/3)...")
            time.sleep(wait)
        else:
            print(f"[{idx:02d}/{total}] ❌ {title[:45]}  →  {resp.status_code}")
            print(f"        오류: {resp.text[:120]}")
            time.sleep(3)
            return False

    print(f"[{idx:02d}/{total}] ❌ {title[:45]}  →  3회 재시도 후 실패")
    return False


# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────

# ─────────────────────────────────────────
# ⑥ 운세SNS — 별자리 12개 통합 (간결 카드형)
# ─────────────────────────────────────────
def build_sns_zodiac_post(today_str):
    """별자리 12개를 한 포스트에 SNS 카드형으로"""
    title = f"✨ 오늘의 별자리 운세 전체 {today_str} — 12별자리 한눈에"

    # kw를 HTML 생성 전에 먼저 정의
    kw = ["별자리운세", "오늘운세", "별자리", today_str,
          "양자리", "황소자리", "쌍둥이자리", "게자리", "사자자리", "처녀자리",
          "천칭자리", "전갈자리", "사수자리", "염소자리", "물병자리", "물고기자리",
          "12별자리운세", "별자리운세전체", "오늘의별자리", "별자리총정리",
          "오늘운세보기", "무료운세", "운세2026"]
    labels = ["별자리운세통합", "운세SNS", "운세", "별자리운세"]

    cards_html = ""
    for z in ZODIACS:
        fortune = zodiac_fortune(z['kr'])
        # 100~200자 범위로 자르기 (이모지 점수바 없음)
        plain = fortune.replace('<br><br>', ' ').replace('<br>', ' ').strip()
        sentences = plain.split('. ')
        short = ''
        for s in sentences:
            candidate = (short + s + '. ').strip()
            if len(candidate) >= 100:
                short = candidate
                break
            short = candidate
        if len(short) > 200:
            short = short[:197] + '…'
        if len(short) < 60:
            short = plain[:150] + ('…' if len(plain) > 150 else '')
        cards_html += f"""
<div style="display:flex;align-items:flex-start;gap:12px;padding:14px;margin-bottom:10px;
            background:#fff;border-radius:14px;box-shadow:0 2px 8px rgba(0,0,0,.06);
            border-left:4px solid #667eea">
  <div style="font-size:32px;line-height:1">{z['emoji']}</div>
  <div style="flex:1;min-width:0">
    <div style="font-weight:900;font-size:14px;color:#4c1d95">{z['kr']}
      <span style="font-size:11px;color:#888;font-weight:400"> {z['date']}</span>
    </div>
    <div style="font-size:13px;color:#444;line-height:1.7;margin:4px 0">{short}</div>
  </div>
</div>"""

    card_id = f"sns-zodiac-{today_str.replace(' ','').replace('년','').replace('월','').replace('일','')}"
    content_html = f"""{style()}
<div class="wrap">
  <div class="hero" style="background:linear-gradient(135deg,#667eea,#764ba2)">
    <h1>✨ 오늘의 별자리 운세</h1>
    <p>{today_str} · 12별자리 전체</p>
  </div>
  <div id="{card_id}" style="background:#f8f7ff;border-radius:16px;padding:16px;margin-bottom:16px">
    {cards_html}
    <div style="text-align:center;margin-top:8px;font-size:11px;color:#aaa">✨ todayhoroscopelaboratory.blogspot.com · {today_str}</div>
  </div>
  {share_buttons(card_id, f"별자리운세전체_{today_str}")}
  <div style="background:#eef2ff;border-radius:12px;padding:12px;font-size:12px;color:#666;text-align:center;margin-bottom:16px">
    🔮 각 별자리를 클릭하면 상세 운세를 확인할 수 있어요
  </div>
  <div class="card"><span class="badge">🔍 관련 키워드</span>
    <div class="tag-cloud">{''.join(f'<span class="tag">{k}</span>' for k in kw)}</div>
  </div>
  {site_link()}
  <div class="meta">※ 재미로 보는 운세 콘텐츠 · 매일 업데이트</div>
</div>"""

    return title, content_html, labels


# ─────────────────────────────────────────
# ⑦ 운세SNS — 띠 12개 통합 (간결 카드형)
# ─────────────────────────────────────────
def build_sns_chinese_post(today_str):
    """띠 12개를 한 포스트에 SNS 카드형으로"""
    title = f"🐾 오늘의 띠별 운세 전체 {today_str} — 12띠 한눈에"

    # kw를 HTML 생성 전에 먼저 정의
    kw = ["띠운세", "오늘운세", "띠별운세", today_str,
          "쥐띠", "소띠", "호랑이띠", "토끼띠", "용띠", "뱀띠",
          "말띠", "양띠", "원숭이띠", "닭띠", "개띠", "돼지띠",
          "12띠운세", "띠운세전체", "오늘의띠운세", "띠운세총정리",
          "오늘운세보기", "무료운세", "운세2026"]
    labels = ["띠운세통합", "운세SNS", "운세", "띠운세"]

    cards_html = ""
    for c in CHINESE:
        # 1940년 이상, 2030년 이하 연도만, 최대 4개
        years_filtered = [y for y in c['year'].split(',') if 1940 <= int(y) <= 2030][:4]

        year_rows_html = ""
        for y in years_filtered:
            yr_fortune = chinese_fortune(c['en'])
            plain = str(yr_fortune).strip()
            sentences = plain.split('. ')
            short = ''
            for s in sentences:
                candidate = (short + s + '. ').strip()
                if len(candidate) >= 80:
                    short = candidate
                    break
                short = candidate
            if len(short) > 180:
                short = short[:177] + '…'
            if len(short) < 40:
                short = plain[:120] + ('…' if len(plain) > 120 else '')
            year_rows_html += f"""
<div style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;border-bottom:1px solid #fde68a">
  <div style="min-width:64px;background:#f59e0b;color:#fff;border-radius:8px;padding:4px 8px;
              text-align:center;font-size:12px;font-weight:700;flex-shrink:0">{y}년생</div>
  <div style="font-size:13px;color:#444;line-height:1.7">{short}</div>
</div>"""

        cards_html += f"""
<div style="background:#fff;border-radius:14px;box-shadow:0 2px 8px rgba(0,0,0,.06);
            border-left:4px solid #f59e0b;padding:14px;margin-bottom:12px">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
    <span style="font-size:28px;line-height:1">{c['emoji']}</span>
    <span style="font-weight:900;font-size:15px;color:#92400e">{c['kr']}</span>
  </div>
  {year_rows_html}
</div>"""

    card_id = f"sns-chinese-{today_str.replace(' ','').replace('년','').replace('월','').replace('일','')}"
    content_html = f"""{style()}
<div class="wrap">
  <div class="hero" style="background:linear-gradient(135deg,#f59e0b,#d97706)">
    <h1>🐾 오늘의 띠별 운세</h1>
    <p>{today_str} · 12띠 전체</p>
  </div>
  <div id="{card_id}" style="background:#fffbeb;border-radius:16px;padding:16px;margin-bottom:16px">
    {cards_html}
    <div style="text-align:center;margin-top:8px;font-size:11px;color:#aaa">🐾 todayhoroscopelaboratory.blogspot.com · {today_str}</div>
  </div>
  {share_buttons(card_id, f"띠별운세전체_{today_str}")}
  <div style="background:#fef3c7;border-radius:12px;padding:12px;font-size:12px;color:#666;text-align:center;margin-bottom:16px">
    🐾 각 띠를 클릭하면 출생연도별 상세 운세를 확인할 수 있어요
  </div>
  <div class="card"><span class="badge">🔍 관련 키워드</span>
    <div class="tag-cloud">{''.join(f'<span class="tag">{k}</span>' for k in kw)}</div>
  </div>
  {site_link()}
  <div class="meta">※ 재미로 보는 운세 콘텐츠 · 매일 업데이트</div>
</div>"""

    return title, content_html, labels


# ─────────────────────────────────────────
# ⑧  별자리가 만나는 시간 — 옴니버스 스토리텔링 (매일 1개)
# 라벨: 별과띠가만나는시간
# URL: /search/label/별과띠가만나는시간
# ─────────────────────────────────────────

# 스토리 연결 구조: (별자리, 띠) → (테마, 별자리↔띠 인과 연결형 내러티브)
# 원칙: 별자리의 감정·상황 → 띠의 에너지가 그것을 어떻게 밀거나 잡아주는지 서사로 연결
_CONNECT_MAP = [
    ("양자리",   "용띠",    "시작",
     "뭔가 시작하고 싶은데 이상하게 손이 안 가는 날이 있어요. "
     "그게 두려움이 아니에요. 에너지가 너무 커서 어디서 터뜨릴지 아직 못 고른 거거든요. "
     "오늘 용띠의 추진력이 그 등을 밀어주는 날이에요. "
     "양자리는 아이디어가 넘치는데 첫 발이 의외로 무거운 타입이거든요. "
     "그 공백을 용띠의 '일단 해보자' 에너지가 채워주는 날이에요. "
     "<br><br>"
     "오늘 완성이 목표가 아니에요. 파일 하나 열거나, 메시지 초안 하나 쓰거나. "
     "용띠가 문을 여는 날이고, 양자리가 그 문으로 달려 들어가는 날입니다. "
     "그 한 발이 오늘의 전부예요."),
    ("황소자리", "뱀띠",    "결실",
     "열심히 하고 있는 건 알겠는데, 이게 맞는 방향인지 요즘 자꾸 흔들리는 느낌이 드나요. "
     "황소자리인 당신은 오래 기다리는 걸 잘하는 편이에요. "
     "근데 그 기다림이 너무 길어지면 '내가 맞게 가고 있는 건가' 싶어지죠. "
     "오늘 뱀띠의 날카로운 직관이 그 확신을 다시 세워줍니다. "
     "뱀띠는 흐름을 읽는 눈이 있어요. 그 눈이 오늘 황소자리의 방향이 맞다고 가리키고 있어요. "
     "<br><br>"
     "오늘 오후에 작은 피드백 하나, 반응 하나가 그 신호로 들어올 수 있어요. "
     "흘려보내지 마세요. 황소자리가 쌓아온 것들이 뱀띠의 감각과 만나서 오늘 드디어 보이기 시작합니다."),
    ("쌍둥이자리","토끼띠",  "연결",
     "이것도 해야 하고, 저것도 신경 쓰이고, 결국 아무것도 못 끝낸 느낌. 그 날 있잖아요. "
     "쌍둥이자리인 당신의 머릿속엔 오늘도 생각이 열 개쯤 동시에 돌아가고 있을 거예요. "
     "그런데 토끼띠는 그 중에서 가장 중요한 것만 골라내는 감각이 있어요. "
     "말 많은 쌍둥이자리 옆에서 토끼띠가 '그거 하나만 해'라고 조용히 말해주는 날이에요. "
     "<br><br>"
     "오늘 할 것 목록이 열 개라면 딱 두 개만 남기세요. "
     "쌍둥이자리의 속도와 토끼띠의 선택력이 합쳐지면, 오늘 그 두 개가 생각보다 빠르게 끝납니다."),
    ("게자리",   "말띠",    "용기",
     "말해봤자 뭐가 달라지나 싶어서, 그냥 넘기는 날들이 쌓이고 있지 않으세요. "
     "게자리인 당신은 하고 싶은 말을 속으로 참는 날이 꽤 많아요. "
     "상대가 상처받을까봐, 분위기가 이상해질까봐. "
     "오늘 말띠의 직진 에너지가 그 망설임을 걷어내줍니다. "
     "말띠는 생각보다 말이 먼저 나오는 타입이에요. 그 솔직함이 오늘 게자리에게 필요한 바람이 되는 날이에요. "
     "<br><br>"
     "거창하게 말할 필요 없어요. 문자 하나, 짧은 안부 하나. "
     "게자리의 따뜻함과 말띠의 추진력이 만나면, 오늘 그 말이 생각보다 잘 닿습니다."),
    ("사자자리", "원숭이띠", "존재감",
     "열심히 하는 건 나도 아는데, 아무도 몰라주는 것 같은 날 있잖아요. 그 억울함이요. "
     "사자자리인 당신은 인정받을 때 빛나는 타입이에요. "
     "오늘 원숭이띠의 재치가 그 존재감을 드러내는 방법을 알려줘요. "
     "원숭이띠는 타이밍을 아는 타입이에요. 언제 어떻게 보여줘야 하는지를요. "
     "<br><br>"
     "오늘 오전 안에 하나만 완성해서 공유하세요. "
     "사자자리의 열정과 원숭이띠의 센스가 합쳐지면, 오늘 그 공유가 생각보다 멀리 닿습니다."),
    ("처녀자리", "닭띠",    "완성",
     "요즘 뭔가 계속 미루게 되는 것이 있지 않으세요. 완벽하지 않아서, 아직 아닌 것 같아서. "
     "처녀자리인 당신은 100%가 아니면 내보내기 싫은 타입이에요. "
     "그 꼼꼼함이 강점인데, 오늘은 그게 발목을 잡을 수 있어요. "
     "닭띠는 기준을 높이 세우면서도 실행을 미루지 않는 타입이에요. "
     "그 실행력이 오늘 처녀자리의 완벽주의를 부드럽게 풀어줍니다. "
     "<br><br>"
     "오늘 80%에서 내보내세요. 처녀자리가 다듬고, 닭띠가 밀어내는 날이에요. "
     "나머지 20%는 다음 버전에서 하면 됩니다. 완성이 완벽보다 오늘은 훨씬 중요해요."),
    ("천칭자리", "개띠",    "관계",
     "말로 꺼내기엔 애매하고, 그냥 넘기기엔 뭔가 걸리는 그게 마음에 남아 있지 않으세요. "
     "천칭자리인 당신은 관계에서 좋은 게 좋다는 쪽을 택하는 경우가 많아요. "
     "근데 그게 쌓이면 어느 날 갑자기 서운함이 터지죠. "
     "개띠는 의리와 솔직함을 동시에 갖고 있어요. "
     "그 솔직함이 오늘 천칭자리가 참아왔던 말을 꺼낼 수 있는 분위기를 만들어줍니다. "
     "<br><br>"
     "거창하게 말할 필요 없어요. '그때 그 말이 조금 걸렸어'라고 짧게만 해도 돼요. "
     "천칭자리의 배려와 개띠의 진심이 만나면, 오늘 그 대화가 관계를 오히려 더 단단하게 만들 수 있습니다."),
    ("전갈자리", "돼지띠",  "직관",
     "사람을 너무 잘 읽어서 오히려 지치는 날이 있어요. 그 예민함이 짐이 되는 날이요. "
     "전갈자리인 당신은 사람을 읽는 눈이 날카로워요. "
     "그런데 그 예민함이 때로는 너무 많은 걸 보이게 해서 지치기도 하죠. "
     "돼지띠는 오늘 그 긴장을 풀어주는 역할을 해요. "
     "돼지띠의 너그러움이 전갈자리의 날 선 감각을 부드럽게 감싸줍니다. "
     "<br><br>"
     "오늘 첫 번째로 떠오르는 판단을 믿되, 그 판단에 여유를 하나 더 얹어보세요. "
     "전갈자리의 통찰과 돼지띠의 온기가 만나면, 오늘 관계에서 생각보다 좋은 결과가 나옵니다."),
    ("사수자리", "쥐띠",    "전환",
     "뭔가 바꾸고 싶은데 어디서 시작해야 할지 모르는 그 답답함, 요즘 느끼고 있지 않으세요. "
     "사수자리인 당신은 변화를 좋아하지만, 정작 어디서 시작할지 모를 때가 있어요. "
     "쥐띠는 그 시작점을 빠르게 찾아내는 타입이에요. "
     "정보를 먼저 캐치하고, 기회를 먼저 알아채는 감각이 있거든요. "
     "그 감각이 오늘 사수자리의 변화 에너지에 방향을 달아줍니다. "
     "<br><br>"
     "오늘 딱 하나만 바꿔보세요. 사수자리가 '바꾸고 싶다'는 에너지를 내면, "
     "쥐띠가 '여기서 시작해'라고 답해주는 날이에요. 그 작은 전환이 오늘 흐름을 엽니다."),
    ("염소자리", "소띠",    "신뢰",
     "결과가 아직 안 보여서 이게 맞나 싶은 날, 주변이 먼저 나아가는 것 같아서 조바심 나는 날. "
     "염소자리인 당신은 묵묵히 쌓아가는 타입이에요. "
     "결과가 안 보여도 멈추지 않는 거, 그게 염소자리의 진짜 강점이에요. "
     "오늘 소띠의 뚝심이 그 옆을 함께 걷습니다. "
     "두 에너지가 만나는 오늘은 '지금 잘 가고 있다'는 확신이 생기는 날이에요. "
     "<br><br>"
     "오늘 오전에 지금까지 해온 것들을 짧게 메모해보세요. "
     "눈에 안 보여도 분명히 쌓이고 있어요. 그게 오늘 확인되는 날입니다."),
    ("물병자리", "호랑이띠", "다름",
     "남들이랑 다른 방향이 자꾸 떠오르는데, 혼자 튀는 것 같아서 눌러두고 있지 않으세요. "
     "물병자리인 당신은 남들이 안 가는 방향이 자꾸 떠오르는 타입이에요. "
     "맞춰야 할 것 같은 압박과, 그냥 내 길 가고 싶은 마음 사이에서 흔들릴 수 있어요. "
     "오늘 호랑이띠의 배짱이 그 망설임을 끊어줍니다. "
     "그 배짱이 오늘 물병자리에게 '그냥 해도 돼'라는 신호가 됩니다. "
     "<br><br>"
     "오늘 그 아이디어를 일단 메모해두세요. "
     "물병자리의 독창성과 호랑이띠의 결단력이 만나면, 오늘 그 메모가 내일의 시작이 됩니다."),
    ("물고기자리","양띠",   "쉬어가기",
     "남 챙기다 정작 나는 못 챙긴 날들이 쌓여서, 오늘 유독 무거운 느낌이 드나요. "
     "물고기자리인 당신은 주변 사람의 감정을 다 흡수하는 타입이에요. "
     "공감이 강점인데, 그게 어느 순간 짐이 돼서 정작 본인이 제일 지쳐 있는 날이 있어요. "
     "오늘 양띠의 부드러운 에너지가 그 짐을 내려놓게 해줍니다. "
     "양띠는 강요하지 않아요. 그냥 옆에 있어주는 타입이에요. "
     "그 조용한 존재감이 오늘 물고기자리에게 쉬어도 된다는 허락이 됩니다. "
     "<br><br>"
     "오늘 저녁은 진짜 오프 타임으로 지켜보세요. "
     "물고기자리가 손을 펴고 있을 때, 양띠의 온기가 그 자리를 채워줍니다."),
]


_OMNIBUS_OPENINGS = [
    "별자리와 띠가 같은 날 위에 놓이면, 이야기가 조금 달라져요. "
    "오늘은 그 두 흐름이 어떻게 맞닿는지 읽어보세요. "
    "본인 별자리와 띠를 찾아서 천천히 읽어보면 돼요.",

    "오늘 하루가 어떻게 흘러갈지, 별자리와 띠가 각자 다른 각도로 보고 있어요. "
    "두 시선이 겹치는 자리에서 의외로 답이 나오는 날이거든요. "
    "읽다가 '아, 이거' 싶은 순간이 오면 그때 움직이세요.",

    "운세가 다 맞지는 않아요. "
    "근데 오늘 이 글이 '나 요즘 이랬는데'가 되거나 '이거 해봐야겠다'가 되면, "
    "그걸로 충분히 쓸모 있어요. 별자리와 띠가 오늘을 어떻게 읽는지 같이 봐요.",

    "오늘 별자리와 띠의 에너지가 겹치는 구간이 있어요. "
    "그 구간에서 뭘 하느냐가 하루 전체 흐름을 바꾸기도 하거든요. "
    "본인 조합 찾아서 읽어보세요.",

    "별자리는 감각을 읽고, 띠는 흐름을 읽어요. "
    "오늘은 그 두 가지가 만나는 지점에서 힌트를 꺼내봤어요. "
    "읽고 나서 마음에 걸리는 게 있으면, 그게 오늘 당신한테 필요한 거예요.",
]

_OMNIBUS_CLOSINGS = [
    "오늘 읽은 것 중에 한 가지만 골라서 써보세요. "
    "전부 기억하려 하면 아무것도 안 남아요. "
    "지금 제일 마음에 걸린 것, 그거 하나면 오늘 하루 잘 쓴 거예요.",

    "운세는 '이렇게 될 거야'가 아니에요. "
    "지금 이 감각, 당신만 느끼는 게 아니에요. "
    "요즘 이런 기분이었어가 되는 것만으로도 오늘 이 글은 제 역할을 한 거예요. "
    "내일도 이야기 나눠요.",

    "오늘 여기까지 읽어줘서 고마워요. "
    "읽고 나서 뭔가 하나라도 달라졌으면, 그걸로 오늘 이 글은 제 몫을 한 거예요. "
    "내일 또 봐요.",

    "좋은 흐름은 아는 사람한테 먼저 보여요. "
    "오늘 그 흐름을 봤으니, 이제 움직일 차례예요. "
    "크게 안 해도 돼요. 작은 것 하나, 그게 오늘의 시작이에요.",

    "오늘 어떤 시간에 뭘 했는지가 내일로 이어져요. "
    "이 글이 그 선택에 조금이라도 도움이 됐으면 좋겠어요. "
    "오늘도 수고했어요.",

    "힘들었던 날이든, 그냥 지나간 날이든. "
    "오늘 여기까지 온 것만으로 이미 잘 하고 있는 거예요. "
    "그 감각, 당신만 느끼는 게 아니에요. 다들 이러면서 살아가고 있어요.",

    "오늘 읽으면서 어딘가 찔리거나, 어딘가 위로가 됐다면. "
    "그 느낌이 맞아요. 별자리든 띠든, 결국은 지금 당신 이야기를 하고 싶었던 거니까요. "
    "내일도 잘 부탁해요.",
]

# 날씨·계절 배경 텍스트 (날짜 기반)
def _season_backdrop(kst_dt):
    m = kst_dt.month
    if m in (3, 4, 5):
        return "봄의 기운이 가득한 오늘,"
    elif m in (6, 7, 8):
        return "여름의 열기 속 오늘,"
    elif m in (9, 10, 11):
        return "가을 바람이 살랑이는 오늘,"
    else:
        return "겨울의 고요함이 내려앉은 오늘,"

def _plain(text: str, max_len: int = 90) -> str:
    """HTML 태그·줄바꿈 제거 후 max_len자 이내 반환"""
    import re
    t = re.sub(r'<[^>]+>', '', str(text))
    t = t.replace('\n', ' ').strip()
    return t[:max_len] + ('…' if len(t) > max_len else '')


def _extract_core_sentence(fortune_raw: str) -> str:
    """
    zodiac_fortune / chinese_fortune 원문에서 핵심 문장 1~2개 추출.
    - HTML 태그 제거 → 첫 번째 완전한 문장(마침표/요/죠/다 로 끝나는 것) 반환
    - 너무 짧으면(<20자) 두 번째 문장도 합침
    """
    import re
    text = re.sub(r'<[^>]+>', '', str(fortune_raw))
    text = text.replace('\n', ' ').strip()
    # 문장 분리: 마침표·물음표·느낌표 기준
    sentences = re.split(r'(?<=[다요죠])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    if not sentences:
        return text[:80]
    core = sentences[0]
    if len(core) < 20 and len(sentences) > 1:
        core = core + ' ' + sentences[1]
    return core[:120]


# ── 개선된 시간대별 골든타임 가이드 (왜 + 무엇을) ──
# ── 시간대 풀 (12개) — 별자리×띠 조합마다 다르게 배정
# 요일 고정 → 반복 문제 해결: 조합 idx로 풀에서 선택
_TIME_POOL = [
    {"label": "오전 9시~11시",
     "why": "하루 중 집중력이 가장 높은 시간대예요. 외부 방해가 적고 뇌가 아직 피로를 덜 쌓은 상태라 판단이 빠르게 나와요.",
     "action": "오래 묵혀두던 결정이나 작업을 이 시간에 꺼내세요. 오후로 넘기면 에너지가 분산돼요.",
     "goal": "오전 9시에 오늘 끝내야 할 것 하나를 먼저 정해두세요. 고르는 데 5분이면 돼요."},
    {"label": "오전 10시~낮 12시",
     "why": "뇌가 워밍업을 마치고 최고 속도로 돌아가는 시간대예요. 분석이 필요한 일, 글쓰기, 기획이 이 시간에 가장 잘 풀려요.",
     "action": "밀어붙일 때보다 고르는 때예요. 여러 선택지 중 하나를 이 시간에 결정하세요.",
     "goal": "빈 문서 하나 열고 떠오르는 것부터 적어보세요. 완성이 아니라 꺼내는 게 목표예요."},
    {"label": "오전 11시~오후 1시",
     "why": "하루의 흐름이 가장 안정적으로 유지되는 시간대예요. 오전의 집중력과 오후의 여유가 겹치는 구간이거든요.",
     "action": "설득이나 협상이 필요한 대화는 이 시간에 꺼내세요. 상대방도 이 구간이 비교적 열려 있어요.",
     "goal": "오늘 가장 중요한 연락 하나, 이 시간 안에 보내세요."},
    {"label": "오후 1시~3시",
     "why": "점심 후 에너지가 재충전되면서 오후 집중력이 올라오는 시간이에요. 창의적인 판단이 이 시간에 가장 잘 나와요.",
     "action": "의외로 여기서 답이 나옵니다. 막혀 있던 문제를 이 시간에 다시 꺼내보세요.",
     "goal": "오후 1시에 오늘 남은 것 중 가장 걸리는 것 하나만 골라 집중하세요."},
    {"label": "오후 2시~4시",
     "why": "업무 추진력이 다시 올라오는 시간대예요. 사람들의 집중력이 돌아오고 결정이 빠르게 이뤄지는 구간이거든요.",
     "action": "타이밍이 결과를 바꿔요. 부탁이나 제안이 필요한 대화는 지금이 들어가기 좋은 시간이에요.",
     "goal": "오늘 핵심 연락 하나, 오후 2시 전에 보내세요."},
    {"label": "오후 3시~5시",
     "why": "하루의 피로가 아직 덜 쌓인 상태에서 대인관계 에너지가 올라오는 시간이에요. 대화가 자연스럽게 열리는 구간이거든요.",
     "action": "저녁으로 넘기면 타이밍을 놓쳐요. 마무리 연락이나 짧은 감사 메시지는 지금 보내세요.",
     "goal": "연락하고 싶었던 사람 한 명, 짧은 안부 하나 지금 보내세요."},
    {"label": "오후 4시~6시",
     "why": "하루를 마무리하면서 감정과 생각이 정리되는 시간이에요. 중요한 것들이 선명해지는 구간이거든요.",
     "action": "잠시 멈추는 편이 유리합니다. 오늘 한 일을 짧게 정리하고, 내일 할 것 3개만 적어두세요.",
     "goal": "오늘 가장 잘 한 것 하나를 메모해두세요. 작은 기록이 내일을 만들어요."},
    {"label": "오후 5시~7시",
     "why": "퇴근 후 첫 두 시간은 하루 중 가장 자유로운 시간이에요. 억압 없이 자신이 원하는 것에 집중할 수 있는 구간이거든요.",
     "action": "오늘 하고 싶었는데 못 한 것, 이 시간에 꺼내세요. 작은 것 하나라도 자신을 위해 쓰는 게 맞아요.",
     "goal": "오후 5시 이후 30분, 오늘 자신을 위한 것 하나에만 써보세요."},
    {"label": "저녁 7시~9시",
     "why": "하루의 긴장이 풀리면서 진짜 하고 싶은 말이 나오는 시간이에요. 감정이 안정되면서 대화가 깊어지는 구간이거든요.",
     "action": "낮에 못 꺼낸 말이 있다면 지금이에요. 저녁은 그 말이 가장 자연스럽게 닿는 시간이에요.",
     "goal": "오늘 하고 싶었던 말 하나, 저녁 7시 이후에 꺼내보세요."},
    {"label": "오전 7시~9시",
     "why": "하루를 여는 첫 두 시간이 그날의 흐름을 결정해요. 외부 방해가 없는 이른 시간에 집중하면 오전 전체가 달라지거든요.",
     "action": "오늘 가장 걸리는 것 하나를 오전에 먼저 꺼내세요. 나중으로 미루면 하루 내내 머릿속에 남아요.",
     "goal": "일어나서 오늘 할 것 하나만 정해두세요. 커피 한 잔 마시기 전에 그것만 결정하면 돼요."},
    {"label": "낮 12시~오후 2시",
     "why": "점심 시간은 하루의 피로를 리셋하는 구간이에요. 이 시간을 제대로 쓰면 오후가 완전히 달라지거든요.",
     "action": "오늘 점심은 제대로 먹고, 10분 걸어보세요. 오후 집중력이 눈에 띄게 달라져요.",
     "goal": "핸드폰 내려두고 진짜 쉬는 점심 30분을 만들어보세요."},
    {"label": "오전 6시~8시",
     "why": "세상이 아직 조용한 이 시간, 자신만을 위한 공간이 생겨요. 이 시간에 한 가지를 시작하면 하루 전체가 달라지거든요.",
     "action": "오늘 아침 이른 시간에 시작하고 싶었던 것 하나를 꺼내보세요. 짧아도 괜찮아요.",
     "goal": "조용한 아침 5분, 오늘 하루를 어떻게 보낼지 생각해보세요."},
]

# ── 공통 엔딩 풀 (날짜 기반 순환, 3파트 구조) ──
# insight: 오늘 하루를 꿰뚫는 통찰 문장
# bridge:  별과 띠가 같은 이야기를 한다는 연결 문장
# action:  독자에게 건네는 단 하나의 행동 제안 (인용구 형태)
_COMMON_ENDINGS = [
    # 1일
    {
        "insight": "오늘은 빠르게 움직이는 사람보다, 타이밍을 아는 사람이 유리한 하루입니다.",
        "bridge":  "별과 띠는 서로 다른 언어를 쓰지만, 오늘은 같은 이야기를 하고 있어요.",
        "action":  "미루던 것 하나만 시작해 보세요.",
    },
    # 2일
    {
        "insight": "오늘은 크게 바꾸려는 날이 아니에요. 작은 것 하나를 제대로 고르는 날이에요.",
        "bridge":  "별자리는 감각으로 읽고, 띠는 흐름으로 읽어요. 오늘 그 둘이 같은 곳을 가리키고 있어요.",
        "action":  "지금 마음에 걸리는 것, 그게 오늘 해야 할 것입니다.",
    },
    # 3일
    {
        "insight": "억지로 밀어붙이는 날보다 흐름에 올라타는 날이 더 멀리 가요. 오늘이 그런 날이에요.",
        "bridge":  "별자리와 띠가 오늘 한목소리를 내고 있어요. 들을 준비가 됐다면 이미 반은 된 거예요.",
        "action":  "오늘 하루, 한 가지만 제대로 해보세요.",
    },
    # 4일
    {
        "insight": "오늘은 많이 하는 것보다 잘 고르는 것이 기억에 남는 하루가 될 수 있어요.",
        "bridge":  "별과 띠가 각자 다른 방향에서 출발했지만, 오늘은 같은 지점에서 만나고 있어요.",
        "action":  "오래 묵혀둔 것 하나, 오늘 꺼내 보세요.",
    },
    # 5일
    {
        "insight": "오늘 당신 주변의 흐름이 조용히 바뀌고 있어요. 눈에 잘 띄지 않는 방향에서요.",
        "bridge":  "별자리가 감지한 것을 띠가 확인해주고 있어요. 오늘의 방향은 하나예요.",
        "action":  "지금 이 순간, 가장 먼저 떠오른 것을 해보세요.",
    },
    # 6일
    {
        "insight": "서두르면 놓치는 날이 있어요. 오늘이 그 날일 수 있으니, 한 박자 늦게 움직여 보세요.",
        "bridge":  "오늘 별자리와 띠가 내는 신호는 같아요. 속도보다 방향이 중요한 날이에요.",
        "action":  "잠깐 멈추고, 지금 가장 걸리는 것 하나를 골라보세요.",
    },
    # 7일
    {
        "insight": "오늘은 준비된 사람에게 문이 열리는 날이에요. 그 문은 요란하지 않게 열려요.",
        "bridge":  "별자리와 띠가 오늘 같은 방향의 바람을 불고 있어요. 그 바람을 등에 맞으면 돼요.",
        "action":  "준비해 뒀던 것, 오늘 한 발 내밀어 보세요.",
    },
    # 8일
    {
        "insight": "오늘은 결과보다 방향을 잡는 날이에요. 방향이 맞으면 속도는 나중에 붙어요.",
        "bridge":  "별자리가 오늘 어디를 보고 있는지, 띠가 어떻게 움직이는지가 오늘 딱 겹쳐요.",
        "action":  "완성이 아니라 방향 하나만 정해보세요.",
    },
    # 9일
    {
        "insight": "오늘은 말보다 행동이 더 멀리 닿는 날이에요. 설명 없이 움직이는 쪽이 유리해요.",
        "bridge":  "별과 띠, 둘 다 오늘 같은 곳에 에너지를 모으고 있어요.",
        "action":  "말하려던 것, 오늘은 그냥 해보세요.",
    },
    # 10일
    {
        "insight": "오늘은 새로 시작하는 것보다 이어가는 것에 힘이 있는 날이에요.",
        "bridge":  "별자리의 감각과 띠의 뚝심이 오늘 같은 리듬으로 움직이고 있어요.",
        "action":  "어제 하다 멈춘 것, 오늘 다시 꺼내보세요.",
    },
    # 11일
    {
        "insight": "오늘은 혼자 안고 있던 것을 한 사람에게라도 꺼내는 날이 더 가벼워져요.",
        "bridge":  "별자리는 감정의 흐름을 읽고, 띠는 관계의 흐름을 읽어요. 오늘 둘이 같은 사람을 가리키고 있어요.",
        "action":  "오늘 연락하고 싶었던 사람, 짧게라도 먼저 연락해보세요.",
    },
    # 12일
    {
        "insight": "오늘은 완벽하게 하려다 아무것도 못 하는 날보다, 작게라도 끝내는 날이 훨씬 나아요.",
        "bridge":  "별자리와 띠가 오늘 '완성'을 향해 같이 밀고 있어요.",
        "action":  "80%에서 내보내세요. 나머지는 다음 버전에서 해요.",
    },
    # 13일
    {
        "insight": "오늘은 기다리는 쪽보다 먼저 움직이는 쪽에 기회가 있는 날이에요.",
        "bridge":  "별자리와 띠, 둘 다 오늘 '먼저'를 권하고 있어요.",
        "action":  "기다리던 것, 오늘 먼저 꺼내보세요.",
    },
    # 14일
    {
        "insight": "오늘은 감정이 앞서는 날이에요. 판단은 하루 뒤에 해도 늦지 않아요.",
        "bridge":  "별자리는 오늘 감정을 읽고, 띠는 그 감정을 어떻게 쓸지 알고 있어요.",
        "action":  "오늘 느낀 것, 일단 어딘가에 적어두세요.",
    },
    # 15일
    {
        "insight": "오늘은 에너지가 고르게 퍼지는 날이에요. 한 곳에 몰아넣기보다 여러 곳에 조금씩 쓰는 게 잘 맞아요.",
        "bridge":  "별자리와 띠가 오늘 같은 템포로 움직이고 있어요. 무리하지 않아도 되는 날이에요.",
        "action":  "오늘은 나눠서 하세요. 한꺼번에 안 해도 돼요.",
    },
    # 16일
    {
        "insight": "오늘은 결정보다 관찰이 더 유리한 날이에요. 조금 더 보고 움직이는 쪽이 맞아요.",
        "bridge":  "별과 띠, 둘 다 오늘 '지켜보기'를 권하고 있어요.",
        "action":  "결정은 내일, 오늘은 보는 날로 써보세요.",
    },
    # 17일
    {
        "insight": "오늘은 나를 위해 뭔가를 하기 좋은 날이에요. 남을 위한 일은 잠깐 내려놔도 괜찮아요.",
        "bridge":  "별자리와 띠가 오늘 당신 안을 향하고 있어요. 바깥이 아니라 안쪽이에요.",
        "action":  "오늘 하루, 자신을 위한 것 하나만 먼저 하세요.",
    },
    # 18일
    {
        "insight": "오늘은 작은 디테일이 큰 차이를 만드는 날이에요. 사소하다고 넘기지 마세요.",
        "bridge":  "별자리의 예민함과 띠의 꼼꼼함이 오늘 같은 방향을 보고 있어요.",
        "action":  "오늘 그냥 넘기려던 것, 한 번 더 확인해보세요.",
    },
    # 19일
    {
        "insight": "오늘은 혼자 생각하는 것보다 한 사람한테 말하는 쪽이 더 빨리 풀리는 날이에요.",
        "bridge":  "별자리는 오늘 연결을 향하고, 띠는 그 연결을 잇는 방법을 알고 있어요.",
        "action":  "지금 머릿속에 있는 것, 한 사람한테 꺼내보세요.",
    },
    # 20일
    {
        "insight": "오늘은 에너지가 저점인 날일 수 있어요. 억지로 올리려 하지 말고 흐르는 대로 두는 게 나아요.",
        "bridge":  "별과 띠, 둘 다 오늘 '쉬어도 된다'고 말하고 있어요.",
        "action":  "오늘은 많이 안 해도 돼요. 한 가지만 하고 쉬세요.",
    },
    # 21일
    {
        "insight": "오늘은 계획대로 안 되는 날처럼 보일 수 있어요. 그 빈자리에서 예상 밖의 것이 들어와요.",
        "bridge":  "별자리와 띠가 오늘 '계획 밖'을 가리키고 있어요. 그쪽이 오늘의 진짜 흐름이에요.",
        "action":  "오늘 계획이 틀어지면, 그 방향으로 가보세요.",
    },
    # 22일
    {
        "insight": "오늘은 감사한 것 하나를 기억하는 것만으로 하루 전체 무게가 달라지는 날이에요.",
        "bridge":  "별자리와 띠가 오늘 '있는 것'을 보라고 말하고 있어요.",
        "action":  "오늘 잘 된 것 하나, 자기 전에 떠올려보세요.",
    },
    # 23일
    {
        "insight": "오늘은 설명하지 않아도 되는 날이에요. 느낌이 맞다면 그냥 움직여도 돼요.",
        "bridge":  "별자리의 직관과 띠의 감각이 오늘 같은 곳을 향하고 있어요.",
        "action":  "설명하지 말고, 오늘은 그냥 해보세요.",
    },
    # 24일
    {
        "insight": "오늘은 오래된 것을 다시 꺼내기 좋은 날이에요. 예전에 포기했던 것이 오늘 다르게 보일 수 있어요.",
        "bridge":  "별자리와 띠가 오늘 '돌아보기'를 권하고 있어요. 뒤를 보는 게 앞을 여는 날이에요.",
        "action":  "예전에 접었던 것, 오늘 다시 한 번 열어보세요.",
    },
    # 25일
    {
        "insight": "오늘은 에너지가 올라오는 날이에요. 그 에너지를 어디에 쓰느냐가 오늘의 핵심이에요.",
        "bridge":  "별자리와 띠 둘 다 오늘 힘이 모이고 있어요. 흩어지게 두면 아까운 날이에요.",
        "action":  "오늘 에너지를 한 곳에만 써보세요. 한 군데면 오늘 하루 다 쓴 거예요.",
    },
    # 26일
    {
        "insight": "오늘은 인정받으려 하기보다 스스로 인정하는 쪽이 더 힘이 되는 날이에요.",
        "bridge":  "별자리와 띠가 오늘 '내 안에서' 답을 찾으라고 말하고 있어요.",
        "action":  "오늘 잘 한 것, 남이 아닌 내가 먼저 알아줘도 돼요.",
    },
    # 27일
    {
        "insight": "오늘은 한 번에 다 해결하려는 마음을 내려놓을수록 실제로 더 많이 되는 날이에요.",
        "bridge":  "별자리는 오늘 '줄이기'를 말하고, 띠는 '집중'을 말해요. 같은 방향이에요.",
        "action":  "오늘 목록에서 하나를 지우세요. 그게 오늘의 진짜 시작이에요.",
    },
    # 28일
    {
        "insight": "오늘은 누군가의 말 한마디가 예상보다 오래 남는 날이에요. 좋은 쪽으로 기억될 말을 먼저 건네보세요.",
        "bridge":  "별자리와 띠가 오늘 '말의 무게'에 대해 같은 이야기를 하고 있어요.",
        "action":  "오늘 하고 싶었던 말, 생각나는 사람한테 짧게 전해보세요.",
    },
    # 29일
    {
        "insight": "오늘은 기대와 다르게 흘러도 그게 더 나은 방향일 수 있는 날이에요.",
        "bridge":  "별자리가 예상한 것을 띠가 다른 각도로 열어주는 날이에요. 둘이 함께일 때 더 잘 보여요.",
        "action":  "계획대로 안 됐다면, 그 방향에서 뭔가를 찾아보세요.",
    },
    # 30일
    {
        "insight": "오늘은 마무리가 시작보다 중요한 날이에요. 끝내는 것이 다음을 여는 날이에요.",
        "bridge":  "별자리와 띠가 오늘 '마무리'를 향해 같이 밀고 있어요.",
        "action":  "오늘 하나를 끝내세요. 시작은 내일 해도 돼요.",
    },
    # 31일
    {
        "insight": "오늘은 흐름을 거스르지 않는 사람이 가장 멀리 가는 날이에요.",
        "bridge":  "별자리와 띠가 오늘 같은 물결 위에 있어요. 그 흐름을 타기만 하면 돼요.",
        "action":  "억지로 만들려 하지 말고, 오늘 자연스럽게 오는 것을 잡아보세요.",
    },
]




def _omnibus_bridge(
    z_kr, z_core, c_kr, c_core, theme, idx,
    z_item, z_color, z_lucky_num,
    z_compatible, c_best, c_avoid,
    best_time_label, avoid_action, z_signal,
    z_contact_time='', z_contact_reason='',
    c_peak_time='', c_peak_tip='', c_low_time='', c_low_tip=''
) -> str:
    """
    소설처럼 흐르는 브릿지 — 카드박스/이모지 없이 산문으로 자연스럽게 연결
    시간 정보는 골든타임(_TIME_POOL) 1회만 노출.
    peak/low/contact는 시간 표기 없이 행동 조언 텍스트(tip/reason)만 사용.
    """
    zb = f"<b style='color:#5b21b6'>{z_kr}</b>"
    cb = f"<b style='color:#b45309'>{c_kr}</b>"
    tb = f"<b style='color:#0369a1'>{theme}</b>"

    # _CONNECT_MAP 스토리
    story = ""
    for row in _CONNECT_MAP:
        if row[0] == z_kr and row[2] == theme:
            story = row[3]
            break
    if not story:
        story = f"{zb}와 {cb}, 오늘 같은 흐름 위에 서 있어요."

    # 조합별 시간 가이드 — 요일 고정 반복 방지
    tg = _TIME_POOL[idx % len(_TIME_POOL)]
    time_label  = tg["label"]
    time_why    = tg["why"]
    time_action = tg["action"]
    time_goal   = tg["goal"]

    # ── 인라인 하이라이트 스타일 (반드시 prose 생성 전에 정의) ──
    def hl_time(t):   return f"<b style='color:#2563eb'>{t}</b>"
    def hl_warn(t):   return f"<b style='color:#dc2626'>{t}</b>"
    def hl_item(t):   return f"<b style='color:#059669'>{t}</b>"
    def hl_compat(t): return f"<b style='color:#7c3aed'>{t}</b>"

    # ── 시간 정보 1회 노출 원칙 ──
    # 골든타임(_TIME_POOL)만 시간 표기, peak/low/contact는 조언 텍스트만 사용

    # 띠별 행동 조언 (시간 표기 없이 tip만)
    peak_tip_only = str(c_peak_tip).strip() if c_peak_tip else ""
    low_tip_only  = str(c_low_tip).strip()  if c_low_tip  else ""

    # 별자리 연락 조언 (시간 표기 없이 reason만)
    contact_tip_only = str(z_contact_reason).strip() if z_contact_reason else ""

    # 띠+별자리 행동 조언 산문 — 시간 없이 흐름에 녹임
    behavior_parts = []
    if peak_tip_only:
        behavior_parts.append(f"{cb}는 오늘 {peak_tip_only}")
    if low_tip_only:
        behavior_parts.append(f"에너지가 처지는 시간대엔 {low_tip_only}")
    if contact_tip_only:
        behavior_parts.append(contact_tip_only)
    behavior_prose = " ".join(behavior_parts)

    # 시간대를 산문 안에 녹인 문장들 — 골든타임 1회만
    time_prose_a = (
        f"오늘의 골든타임은 {hl_time(time_label)}이에요. "
        f"{time_why} "
        f"{time_action}"
    )
    time_prose_b = (
        f"오늘은 {hl_time(time_label)}을 어떻게 쓰느냐가 갈려요. "
        f"{time_action}"
    )
    time_prose_c = (
        f"시간 얘기를 하나 할게요. {hl_time(time_label)}, 이 구간을 잘 보세요. "
        f"{time_why}"
    )

    # 목표 문장 — 조합 idx로 다르게
    _goal_variants = [
        f"오늘은 이것만 해보세요. {time_goal}",
        f"의외로 여기서 답이 나옵니다. {time_goal}",
        f"지금은 고르는 때예요. {time_goal}",
        f"오늘 하루, 이 하나만 챙기면 돼요. {time_goal}",
        f"이거 하나면 오늘 하루 다 쓴 거예요. {time_goal}",
        f"복잡하게 생각할 필요 없어요. {time_goal}",
    ]
    goal_prose = _goal_variants[idx % len(_goal_variants)]

    # 행동 조언이 있을 때만 추가하는 보조 산문
    tf = (f"<br><br>{behavior_prose}" if behavior_prose else "")

    # 궁합 산문
    compat_prose = (
        f"오늘 {hl_compat(z_compatible)}이나 {hl_compat(c_best)}와 나누는 대화가 "
        f"의외로 좋은 방향을 열어줄 수 있어요. "
        f"반대로 {hl_warn(c_avoid)}와 감정이 섞인 이야기는 오늘 저녁 이후로 미뤄두는 게 나아요."
    )

    # 행운 산문
    item_prose = (
        f"오늘 {hl_item(z_item)}을 가까이 두거나 "
        f"{hl_item(z_color)} 소품 하나를 챙겨보세요. "
        f"작은 것인데 하루가 조금 달라지거든요."
    )

    # 피해야 할 것 산문 — idx 기반 변형
    _avoid_variants = [
        (f"오늘 {hl_warn(avoid_action)}은 잠시 멈추는 편이 유리해요. "
         f"억지로 밀어붙이는 날이 아니에요."),
        (f"오늘 {hl_warn(avoid_action)}은 내려놓아도 돼요. "
         f"오늘은 그 방향보다 다른 쪽에 에너지를 쓰는 게 맞아요."),
        (f"{hl_warn(avoid_action)}은 오늘 굳이 건드리지 않아도 되는 것들이에요. "
         f"비워두는 것도 오늘의 선택이에요."),
        (f"오늘 {hl_warn(avoid_action)} 쪽으로 힘을 쏟으면 뒷맛이 남아요. "
         f"지금은 그쪽보다 나머지에 집중할 타이밍이에요."),
    ]
    avoid_prose = _avoid_variants[idx % len(_avoid_variants)]

    # ── 12가지 산문 패턴 ──
    # z_core(별자리 오늘 운세 핵심문), c_core(띠 오늘 운세 핵심문)를
    # 스토리 안에 인과적으로 녹여 "별자리가 이러니까 띠가 이렇게 작용한다"는 흐름을 만듦
    patterns = [
        # 0: 스토리 → 실시간 별자리 코어 → 골든타임
        f"{story}<br><br>"
        f"오늘 {zb}의 흐름을 보면, {z_core} "
        f"그 흐름 위에서 {time_prose_a} "
        f"{goal_prose}"
        + tf,

        # 1: 골든타임 먼저 → 스토리 → 띠 코어로 마무리
        f"{time_prose_c}<br><br>"
        f"{story}<br><br>"
        f"오늘 {cb}가 전하는 한 마디는 이거예요. {c_core} "
        f"{goal_prose}"
        + tf,

        # 2: 띠 코어 → 별자리와 연결 → 행동
        f"오늘 {cb}의 에너지가 이런 말을 하고 있어요. {c_core}<br><br>"
        f"{zb}인 당신에게 그 에너지가 닿으면 어떻게 되냐면, {story}<br><br>"
        f"{time_prose_b} {goal_prose}"
        + tf,

        # 3: 테마 선언 → 스토리 → 별자리 코어 → 궁합
        f"오늘의 테마는 {tb}이에요. {zb}와 {cb}가 같은 흐름 위에 서 있는 날이거든요.<br><br>"
        f"{story}<br><br>"
        f"오늘 {zb}의 흐름은 이래요. {z_core} "
        f"{compat_prose}"
        + tf,

        # 4: 스토리 → 피해야 할 것 → 띠 코어로 방향 제시
        f"{story}<br><br>"
        f"{avoid_prose}<br><br>"
        f"대신 {cb}가 오늘 이런 방향을 가리키고 있어요. {c_core} "
        f"{time_prose_b}"
        + tf,

        # 5: 행운 팁 → 별자리↔띠 연결 스토리 → 골든타임
        f"오늘 {zb}와 {cb}에게 먼저 작은 팁 하나. {item_prose}<br><br>"
        f"{story}<br><br>"
        f"{time_prose_a} {goal_prose}"
        + tf,

        # 6: 띠 코어 → 별자리가 받는 방식 → 행동
        f"오늘 {cb}의 에너지가 이렇게 흐르고 있어요. {c_core}<br><br>"
        f"그 에너지를 {zb}는 이렇게 받을 수 있어요. {z_core}<br><br>"
        f"둘이 만나는 지점에서 오늘 가장 잘 되는 것: {time_prose_c} {goal_prose}"
        + tf,

        # 7: 스토리 → 행동 조언 → 골든타임 → 궁합
        f"{story}<br><br>"
        f"{time_prose_a}<br><br>"
        + (f"{behavior_prose}<br><br>" if behavior_prose else "")
        + f"{compat_prose} {goal_prose}",

        # 8: 공감 오프닝 → 별자리 코어 → 스토리 → 골든타임
        f"오늘 {zb}인 분들, 잠깐 이야기 들어보실게요?<br><br>"
        f"오늘 당신의 흐름이 이렇게 보여요. {z_core}<br><br>"
        f"그 흐름에서 {cb}의 에너지가 이렇게 작용해요. {story}<br><br>"
        f"{time_prose_b} {goal_prose}"
        + tf,

        # 9: 스토리 → 행운 → 띠 코어 → 골든타임
        f"{story}<br><br>"
        f"{item_prose}<br><br>"
        f"오늘 {cb}가 건네는 말도 같은 방향이에요. {c_core} "
        f"그리고 {time_prose_a}"
        + tf,

        # 10: 긍정 선언 → 스토리 → 별자리↔띠 코어 교차 → 피해야 할 것
        f"오늘 {zb}와 {cb}의 흐름이 생각보다 좋은 방향으로 맞닿아 있어요.<br><br>"
        f"{story}<br><br>"
        f"{zb}의 오늘: {z_core} {cb}의 오늘: {c_core}<br><br>"
        f"{avoid_prose}"
        + tf,

        # 11: 마무리형 → 스토리 → 골든타임 → 궁합
        f"마지막으로 {zb}와 {cb}인 분들께.<br><br>"
        f"{story}<br><br>"
        f"{time_prose_a}<br><br>"
        f"{compat_prose}"
        + tf,
    ]
    return patterns[idx % len(patterns)]


def build_omnibus_post(today_str: str) -> tuple:
    """
    '별과 띠가 만나는 시간' — 오늘 발행된 별자리·띠 운세 원문을 실시간 조합
    - 별자리 12개 + 띠 12개 → 그날 실제 운세 문장 추출 → 브릿지로 연결
    - 날짜가 달라지면 내용이 자동으로 달라짐 (CSV 데이터 기반)
    라벨: 별과띠가만나는시간
    """
    kst_dt  = now_kst()
    season  = _season_backdrop(kst_dt)
    opening = random.choice(_OMNIBUS_OPENINGS)
    closing = random.choice(_OMNIBUS_CLOSINGS)

    # 공통 엔딩 — 날짜(일)로 순환, 매일 다른 조합
    _day_idx   = kst_dt.day % len(_COMMON_ENDINGS)
    _ending    = _COMMON_ENDINGS[_day_idx]
    ending_insight = _ending["insight"]
    ending_bridge  = _ending["bridge"]
    ending_action  = _ending["action"]

    title = (
        f"🌙 별과 띠가 만나는 시간 {today_str} "
        f"— 오늘 당신의 별자리와 띠가 전하는 이야기"
    )

    # ── 오늘 실시간 데이터 수집 ──────────────────────────────────
    # 띠 궁합 테이블 (chinese_post 와 동일)
    _CHINESE_COMPAT = {
        '쥐띠':    {'best':'용띠',   'avoid':'말띠'},
        '소띠':    {'best':'닭띠',   'avoid':'양띠'},
        '호랑이띠':{'best':'말띠',   'avoid':'원숭이띠'},
        '토끼띠':  {'best':'양띠',   'avoid':'닭띠'},
        '용띠':    {'best':'쥐띠',   'avoid':'개띠'},
        '뱀띠':    {'best':'닭띠',   'avoid':'돼지띠'},
        '말띠':    {'best':'호랑이띠','avoid':'쥐띠'},
        '양띠':    {'best':'토끼띠', 'avoid':'소띠'},
        '원숭이띠':{'best':'쥐띠',   'avoid':'호랑이띠'},
        '닭띠':    {'best':'소띠',   'avoid':'토끼띠'},
        '개띠':    {'best':'호랑이띠','avoid':'용띠'},
        '돼지띠':  {'best':'토끼띠', 'avoid':'뱀띠'},
    }

    # 요일 기반 최고 시간대 레이블
    dow = kst_dt.weekday()
    _TIME_LABELS = {
        0: "오전 시간대",   # 월: 오전 강세
        1: "저녁 시간대",   # 화: 저녁 좋음
        2: "오전 시간대",   # 수: 오전 강세
        3: "저녁 시간대",   # 목: 저녁 최고
        4: "오후~저녁",     # 금: 오후 이후
        5: "저녁 시간대",   # 토: 저녁 강세
        6: "오전 시간대",   # 일: 오전 무난
    }
    best_time_label = _TIME_LABELS[dow]

    # 별자리별 데이터 수집
    z_data = {}
    for z in ZODIACS:
        raw          = zodiac_fortune(z['kr'])
        z_item       = pick_lucky_item(z['kr'])
        z_color      = pick_color()
        z_lucky_num  = pick_number()
        z_compatible = ZODIAC_INFO.get(z['kr'], {}).get('compatible', '').split(',')[0].strip()
        _, z_signal  = _zodiac_seo_title(z['kr'], kst_dt.strftime("%Y년 %-m월 %-d일"),
                                          *pick_score(z['kr']))
        # 📱 연락 시간대 데이터
        _z_ct_row = zodiac_kr[zodiac_kr['zodiac'] == z['kr']]
        _z_contact_time   = _z_ct_row['contact_time'].iloc[0]   if not _z_ct_row.empty and 'contact_time'   in _z_ct_row.columns else ''
        _z_contact_reason = _z_ct_row['contact_reason'].iloc[0] if not _z_ct_row.empty and 'contact_reason' in _z_ct_row.columns else ''
        z_data[z['kr']] = {
            'core':           _extract_core_sentence(raw),
            'item':           z_item,
            'color':          z_color,
            'lucky_num':      z_lucky_num,
            'compatible':     z_compatible,
            'signal':         z_signal,
            'contact_time':   str(_z_contact_time),
            'contact_reason': str(_z_contact_reason),
        }

    # 띠별 데이터 수집
    c_data = {}
    for c in CHINESE:
        raw    = chinese_fortune(c['en'])
        compat = _CHINESE_COMPAT.get(c['kr'], {})
        # ⏰ 시간대 흐름 데이터
        _c_row = chinese_zodiac[chinese_zodiac['animal_zodiac'] == c['en']]
        _peak_time = _c_row['peak_time'].iloc[0] if not _c_row.empty and 'peak_time' in _c_row.columns else ''
        _peak_tip  = _c_row['peak_tip'].iloc[0]  if not _c_row.empty and 'peak_tip'  in _c_row.columns else ''
        _low_time  = _c_row['low_time'].iloc[0]  if not _c_row.empty and 'low_time'  in _c_row.columns else ''
        _low_tip   = _c_row['low_tip'].iloc[0]   if not _c_row.empty and 'low_tip'   in _c_row.columns else ''
        c_data[c['kr']] = {
            'core':      _extract_core_sentence(raw),
            'best':      compat.get('best',  ''),
            'avoid':     compat.get('avoid', ''),
            'peak_time': str(_peak_time),
            'peak_tip':  str(_peak_tip),
            'low_time':  str(_low_time),
            'low_tip':   str(_low_tip),
        }

    # ── 12쌍 문단 생성 (모든 실시간 데이터 → 브릿지로 전달) ──
    paragraphs = []
    for idx, (z_kr, c_kr, theme, _) in enumerate(_CONNECT_MAP):
        zd = z_data.get(z_kr, {})
        cd = c_data.get(c_kr, {})
        para = _omnibus_bridge(
            z_kr            = z_kr,
            z_core          = zd.get('core', ''),
            c_kr            = c_kr,
            c_core          = cd.get('core', ''),
            z_contact_time   = zd.get('contact_time', ''),
            z_contact_reason = zd.get('contact_reason', ''),
            c_peak_time      = cd.get('peak_time', ''),
            c_peak_tip       = cd.get('peak_tip', ''),
            c_low_time       = cd.get('low_time', ''),
            c_low_tip        = cd.get('low_tip', ''),
            theme       = theme,
            idx         = idx,
            z_item      = zd.get('item', ''),
            z_color     = zd.get('color', ''),
            z_lucky_num = zd.get('lucky_num', ''),
            z_compatible= zd.get('compatible', ''),
            c_best      = cd.get('best', ''),
            c_avoid     = cd.get('avoid', ''),
            best_time_label = best_time_label,
            avoid_action= random.choice(_Z_AVOID_ACTIONS)[0],
            z_signal    = zd.get('signal', theme),
        )
        paragraphs.append(
            f'<p style="margin:0 0 1.7em 0;text-indent:0">{para}</p>'
        )

    # 상(0~5) / 하(6~11) 분리
    paras_top = paragraphs[:6]
    paras_bot = paragraphs[6:]

    # 각각 첫 문단 드롭캡
    paras_top[0] = paras_top[0].replace(
        '<p style="margin:0 0 1.7em 0;text-indent:0">',
        '<p style="margin:0 0 1.7em 0;text-indent:0" class="drop-cap-p">',
        1
    )
    paras_bot[0] = paras_bot[0].replace(
        '<p style="margin:0 0 1.7em 0;text-indent:0">',
        '<p style="margin:0 0 1.7em 0;text-indent:0" class="drop-cap-p">',
        1
    )
    story_top = "\n".join(paras_top)
    story_bot = "\n".join(paras_bot)

    # ── 오늘의 명언 ──
    quote_text, _, _ = pick_quote()
    quote_clean = _plain(str(quote_text), 120)

    # ── SEO 키워드 태그 ──
    kw_tags = (
        ["별과띠가만나는시간", "오늘운세", "별자리운세", "띠운세", today_str,
         "별자리와띠", "운세에세이", "오늘의운세", "무료운세", "운세2026"]
        + [z['kr'] for z in ZODIACS]
        + [c['kr'] for c in CHINESE]
    )
    tag_html = "".join(f'<span class="tag">{t}</span>' for t in kw_tags)

    date_slug = today_str.replace(' ','').replace('년','').replace('월','').replace('일','')
    card_id_top = f"omnibus-top-{date_slug}"
    card_id_bot = f"omnibus-bot-{date_slug}"

    # 별자리 12개 이름 — 상/하 구분 표시용
    z_names_top = "·".join(z['kr'] for z in ZODIACS[:6])   # 양자리~처녀자리
    z_names_bot = "·".join(z['kr'] for z in ZODIACS[6:])   # 천칭자리~물고기자리

    content_html = f"""{style()}
<style>
.novel-page {{
  max-width: 660px;
  margin: 0 auto;
  padding: 0 4px;
  font-family: 'Noto Serif KR', Georgia, serif;
}}
.novel-date {{
  font-size: 12px;
  letter-spacing: 0.14em;
  color: #9ca3af;
  text-align: center;
  margin-bottom: 1.6rem;
}}
.novel-title {{
  font-size: 22px;
  font-weight: 600;
  color: #1f2937;
  text-align: center;
  line-height: 1.55;
  margin-bottom: 0.35rem;
}}
.novel-subtitle {{
  font-size: 13px;
  text-align: center;
  color: #9ca3af;
  margin-bottom: 2.6rem;
}}
.novel-part {{
  font-size: 11px;
  text-align: center;
  color: #c4b5fd;
  letter-spacing: 0.12em;
  margin-bottom: 1.2rem;
  font-weight: 600;
}}
.novel-rule {{
  text-align: center;
  color: #d1d5db;
  letter-spacing: 0.5em;
  margin: 2.4rem 0;
  font-size: 13px;
}}
.novel-body {{
  font-size: 15.5px;
  line-height: 2.2;
  color: #374151;
  word-break: keep-all;
}}
.novel-body p b {{
  font-style: normal;
}}
.novel-opening {{
  font-size: 15px;
  line-height: 2.1;
  color: #6b7280;
  margin-bottom: 2rem;
  font-style: italic;
  padding: 0 2px;
  word-break: keep-all;
}}
.novel-footer {{
  margin-top: 3rem;
  padding-top: 2rem;
  border-top: 1px solid #f3f4f6;
  font-size: 14px;
  color: #9ca3af;
  text-align: center;
  line-height: 2.2;
  font-style: italic;
}}
</style>

<div class="wrap">

  <!-- ★ 1번 카드 (상) : 양자리~처녀자리 -->
  <div class="novel-page" id="{card_id_top}">
    <div class="novel-date">{today_str} · {season}</div>
    <h1 class="novel-title">🌙 별과 띠가 만나는 시간</h1>
    <p class="novel-subtitle">오늘 하늘이 당신에게 건네는 이야기</p>
    <div class="novel-part">상 · {z_names_top}</div>
    <div class="novel-rule">&middot; &middot; &middot;</div>
    <p class="novel-opening">{opening}</p>
    <div class="novel-body">
{story_top}
    </div>
    <div class="novel-rule">&middot; &middot; &middot;</div>
  </div>

  <!-- 1번 저장 버튼 -->
  {share_buttons(card_id_top, f"별과띠가만나는시간_상_{today_str}")}

  <div style="margin:32px 0 8px 0;border-top:2px dashed #e5e7eb;padding-top:32px"></div>

  <!-- ★ 2번 카드 (하) : 천칭자리~물고기자리 -->
  <div class="novel-page" id="{card_id_bot}">
    <div class="novel-date">{today_str} · {season}</div>
    <h1 class="novel-title">🌙 별과 띠가 만나는 시간</h1>
    <p class="novel-subtitle">오늘 하늘이 당신에게 건네는 이야기</p>
    <div class="novel-part">하 · {z_names_bot}</div>
    <div class="novel-rule">&middot; &middot; &middot;</div>
    <div class="novel-body">
{story_bot}
    </div>
    <div class="novel-rule">&middot; &middot; &middot;</div>

    <!-- ★ 공통 엔딩 -->
    <!-- ── 공통 엔딩 블록 ── -->
    <div style="
      margin: 2.8rem 0 0 0;
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 2px 16px rgba(91,33,182,0.08);
    ">
      <!-- 헤더 라벨 -->
      <div style="
        background: linear-gradient(90deg, #7c3aed 0%, #a78bfa 100%);
        padding: 0.7rem 1.4rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
      ">
        <span style="font-size:15px">🌙</span>
        <span style="
          font-size: 12px;
          font-weight: 700;
          color: #ede9fe;
          letter-spacing: 0.12em;
        ">오늘 별과 띠가 함께 전하는 말</span>
      </div>

      <!-- 본문 -->
      <div style="
        background: linear-gradient(160deg, #faf5ff 0%, #fdf4ff 100%);
        padding: 1.6rem 1.6rem 0.4rem 1.6rem;
      ">
        <!-- 오늘의 통찰 -->
        <p style="
          font-size: 15.5px;
          line-height: 2.05;
          color: #374151;
          margin: 0 0 1.1rem 0;
          word-break: keep-all;
          font-weight: 500;
        ">{ending_insight}</p>

        <!-- 별·띠 연결 문장 -->
        <p style="
          font-size: 14px;
          line-height: 1.95;
          color: #6d28d9;
          margin: 0 0 1.5rem 0;
          word-break: keep-all;
          font-style: italic;
          padding-left: 0.9rem;
          border-left: 3px solid #c4b5fd;
        ">{ending_bridge}</p>
      </div>

      <!-- 오늘의 한 문장 행동 -->
      <div style="
        background: #5b21b6;
        padding: 1.2rem 1.6rem;
        text-align: center;
      ">
        <div style="
          font-size: 11px;
          color: #c4b5fd;
          letter-spacing: 0.14em;
          margin-bottom: 0.5rem;
          font-weight: 600;
        ">오늘 단 하나만 한다면</div>
        <span style="
          display: inline-block;
          font-size: 17px;
          font-weight: 800;
          color: #ffffff;
          letter-spacing: -0.01em;
          word-break: keep-all;
          line-height: 1.6;
        ">❝ {ending_action} ❞</span>
      </div>
    </div>

    <div class="novel-footer">
      {closing}
    </div>
  </div>

  <!-- 2번 저장 버튼 -->
  {share_buttons(card_id_bot, f"별과띠가만나는시간_하_{today_str}")}

  <!-- 오늘의 한 마디 -->
  <div class="card" style="margin-top:12px">
    <span class="badge">💬 오늘의 한 마디</span>
    <p style="font-size:14px;line-height:1.85;color:#6b7280;font-style:italic;margin-top:8px">{quote_clean}</p>
  </div>

  <!-- SEO 키워드 -->
  <div class="card">
    <span class="badge">🔍 관련 키워드</span>
    <div class="tag-cloud">{tag_html}</div>
  </div>

  {site_link()}
  <div class="meta">※ 재미로 보는 운세 콘텐츠입니다 · 매일 업데이트</div>
</div>"""

    labels = ["별과띠가만나는시간", "별자리운세", "띠운세", "운세", "오늘운세"]
    return title, content_html, labels


def main():
    today_str = now_kst().strftime("%Y년 %m월 %d일")
    kst_now   = now_kst()
    posts = []

    # 수동 실행 시 강제 포함 옵션
    force_weekly  = os.environ.get("FORCE_WEEKLY",  "false").lower() == "true"
    force_monthly = os.environ.get("FORCE_MONTHLY", "false").lower() == "true"
    # MONTHLY_ONLY=true 이면 띠별 월간운세 12개만 발행하고 종료
    monthly_only  = os.environ.get("MONTHLY_ONLY",  "false").lower() == "true"

    if monthly_only:
        print(f"🌙 MONTHLY_ONLY 모드 — 띠별 월간운세 12개만 발행")
        posts.extend(build_chinese_monthly_post(today_str))
        total = len(posts)
        print(f"\n🌟 {today_str} 띠별 월간운세 단독 포스팅 시작 — 총 {total}개\n")
        success = 0
        for i, (title, content, labels) in enumerate(posts, 1):
            if post_blogger(title, content, labels, i, total):
                success += 1
        print(f"\n✅ 완료: {success}/{total}개 게시 성공")
        return

    # ① 오늘의 명언 1개
    posts.append(build_quote_post(today_str))

    # ② 별자리 운세 12개
    for z in ZODIACS:
        posts.append(build_zodiac_post(z, today_str))

    # ③ 띠 운세 12개
    for c in CHINESE:
        posts.append(build_chinese_post(c, today_str))

    # ⑥ 운세SNS — 별자리 통합 1개 (매일)
    posts.append(build_sns_zodiac_post(today_str))

    # ⑦ 운세SNS — 띠 통합 1개 (매일)
    posts.append(build_sns_chinese_post(today_str))

    # ⑧ 별자리가 만나는 시간 — 옴니버스 스토리텔링 1개 (매일)
    posts.append(build_omnibus_post(today_str))

    # 매월 마지막주 월요일 계산 (다음 달 띠별월간 미리 발행)
    import calendar as _cal
    from datetime import date as _date2
    _last_day   = _cal.monthrange(kst_now.year, kst_now.month)[1]
    _last_monday = max(
        d for d in range(1, _last_day + 1)
        if _date2(kst_now.year, kst_now.month, d).weekday() == 0
    )
    is_last_monday = (kst_now.day == _last_monday)

    # ④ 별자리 주간운세 — 매주 월요일 or 강제 실행
    if kst_now.weekday() == 0 or force_weekly:
        posts.extend(build_zodiac_weekly_post(today_str))
        label = "강제 포함" if force_weekly and kst_now.weekday() != 0 else "월요일"
        print(f"📅 별자리 주간운세 12개 포함 ({label})")
    else:
        print("📅 주간운세 스킵 (월요일 아님)")

    # ⑤ 띠별 월간운세
    # - 매월 1일: 당월 운세 발행 (6월1일→6월 운세)
    # - 매월 마지막주 월요일: 다음달 운세 미리 발행
    # - FORCE_MONTHLY=true: 강제 발행
    is_first_day = (kst_now.day == 1)
    if is_first_day or is_last_monday or force_monthly:
        posts.extend(build_chinese_monthly_post(today_str))
        if force_monthly and not is_first_day and not is_last_monday:
            label = "강제 포함"
        elif is_first_day:
            label = "1일 당월 발행"
        else:
            label = "마지막주 월요일 다음달 발행"
        print(f"📅 띠별 월간운세 12개 포함 ({label})")
    else:
        print("📅 월간운세 스킵")

    total = len(posts)
    weekly  = " + 별자리주간 12" if kst_now.weekday() == 0 else ""
    monthly = " + 띠별월간 12"   if (is_last_monday or force_monthly) else ""
    count   = 28 + (12 if kst_now.weekday() == 0 else 0) + (12 if kst_now.day == 1 else 0)
    print(f"\n🌟 {today_str} 운세 포스팅 시작 — 총 {total}개\n")
    print(f"구성: 오늘의명언 1 + 별자리 12 + 띠 12 + SNS통합 2 + 별과띠가만나는시간 1{weekly}{monthly} = {count}개\n")

    success = 0
    for i, (title, content, labels) in enumerate(posts, 1):
        if post_blogger(title, content, labels, i, total):
            success += 1

    print(f"\n✅ 완료: {success}/{total}개 게시 성공")

if __name__ == "__main__":
    main()
