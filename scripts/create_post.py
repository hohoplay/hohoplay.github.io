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
     "오늘 책상이나 창가에 꽃이나 식물 하나 두시기 바랍니다. 초록이 눈에 들어오는 것만으로도 기분이 달라지는 날입니다."),
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
            f"오늘 행운 색상은 <b>'{color_name}'</b>입니다. "
            f"{items} 중 하나를 오늘 곁에 두거나 착용해보세요. "
            f"{usage}"
        )
    return f"오늘 '{color_name}' 컬러를 소품이나 옷에 활용해보시기 바랍니다. 미묘하게 기분이 달라지는 날입니다."

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
        "tip": "오늘 중요한 결정을 내리기 전에 잠시 멈추는 습관이 필요합니다. 충동적으로 결정하고 싶은 순간일수록 3분만 기다리는 것이 더 나은 결과를 만들어 냅니다.",
        "color": "빨간색, 오렌지", "stone": "다이아몬드, 루비", "number": "1, 9",
    },
    "황소자리": {
        "element": "흙 (Earth)", "ruling": "금성 (Venus)",
        "trait": "안정과 신뢰를 중시하는 현실주의자입니다. 한번 시작한 일은 끝까지 해내는 끈기와 성실함이 빛납니다.",
        "strength": "인내심, 신뢰성, 현실 감각, 심미안",
        "weakness": "고집스러움, 변화 거부, 소유욕",
        "compatible": "처녀자리, 염소자리, 게자리",
        "tip": "오늘 새로운 방식을 한 가지만 시도해 보시기 바랍니다. 변화를 받아들이기 어려운 상황에서도 단 하나만 다르게 해보면 예상보다 안정적으로 진행됩니다.",
        "color": "초록색, 베이지", "stone": "에메랄드, 로즈쿼츠", "number": "2, 6",
    },
    "쌍둥이자리": {
        "element": "공기 (Air)", "ruling": "수성 (Mercury)",
        "trait": "지적 호기심과 소통 능력이 뛰어난 다재다능한 별자리입니다. 상황에 따라 유연하게 적응하는 능력이 탁월합니다.",
        "strength": "적응력, 커뮤니케이션 능력, 창의성, 유머",
        "weakness": "변덕, 집중력 부족, 우유부단함",
        "compatible": "천칭자리, 물병자리, 양자리",
        "tip": "오늘 여러 가지에 분산하기보다 두 가지에만 집중하는 것이 효과적입니다. 할 일 목록이 많다면 가장 중요한 두 가지만 선택하여 완성하시기 바랍니다.",
        "color": "노란색, 하늘색", "stone": "아게이트, 시트린", "number": "3, 5",
    },
    "게자리": {
        "element": "물 (Water)", "ruling": "달 (Moon)",
        "trait": "감수성과 공감 능력이 풍부한 보살핌의 별자리입니다. 가족과 소중한 사람을 위해 헌신하는 따뜻한 마음이 특징입니다.",
        "strength": "공감력, 직관력, 보살핌, 기억력",
        "weakness": "감정 기복, 소극성, 과도한 집착",
        "compatible": "전갈자리, 물고기자리, 황소자리",
        "tip": "오늘 자신을 돌보는 시간을 반드시 확보하시기 바랍니다. 타인을 챙기는 데 에너지를 쏟기 전에 자신의 상태를 먼저 점검하는 것이 더 중요한 날입니다.",
        "color": "은색, 흰색", "stone": "문스톤, 진주", "number": "2, 7",
    },
    "사자자리": {
        "element": "불 (Fire)", "ruling": "태양 (Sun)",
        "trait": "카리스마와 자신감이 넘치는 무대의 주인공 별자리입니다. 타고난 리더십으로 주변을 밝히고 이끄는 힘이 있습니다.",
        "strength": "카리스마, 관대함, 창의력, 자신감",
        "weakness": "자존심, 지나친 인정 욕구, 고집",
        "compatible": "양자리, 사수자리, 쌍둥이자리",
        "tip": "오늘 다른 사람의 의견을 경청하는 자세가 필요합니다. 대화에서 말하기 전에 상대방의 말을 먼저 충분히 듣는 것이 전체 분위기를 긍정적으로 만듭니다.",
        "color": "금색, 주황색", "stone": "루비, 호박", "number": "1, 4",
    },
    "처녀자리": {
        "element": "흙 (Earth)", "ruling": "수성 (Mercury)",
        "trait": "분석력과 완벽주의적 성향을 지닌 세심한 별자리입니다. 디테일을 놓치지 않는 꼼꼼함이 큰 강점입니다.",
        "strength": "분석력, 성실함, 실용성, 정확성",
        "weakness": "완벽주의, 지나친 비판, 걱정이 많음",
        "compatible": "황소자리, 염소자리, 게자리",
        "tip": "오늘 80% 완성도에서 진행하는 것이 더 나은 선택입니다. 완벽을 추구하다 전달이 늦어지는 것보다 충분한 수준에서 내보내는 것이 오늘은 더 중요합니다.",
        "color": "네이비, 회색", "stone": "사파이어, 카넬리안", "number": "5, 6",
    },
    "천칭자리": {
        "element": "공기 (Air)", "ruling": "금성 (Venus)",
        "trait": "균형과 조화를 중시하는 외교적 별자리입니다. 아름다움과 공정함에 대한 감각이 뛰어나며 관계를 소중히 여깁니다.",
        "strength": "균형 감각, 외교력, 심미안, 협력",
        "weakness": "우유부단함, 갈등 회피, 의존성",
        "compatible": "쌍둥이자리, 물병자리, 사수자리",
        "tip": "오늘 결정을 미루고 싶은 순간이 온다면 자신이 진정으로 원하는 것이 무엇인지 먼저 확인하시기 바랍니다. 계속 미뤄온 결정이 있다면 오늘 안에 하나만 마무리하는 것이 좋습니다.",
        "color": "파스텔 핑크, 라벤더", "stone": "오팔, 로즈쿼츠", "number": "6, 9",
    },
    "전갈자리": {
        "element": "물 (Water)", "ruling": "명왕성 (Pluto)",
        "trait": "깊이 있는 통찰력과 강인한 의지를 지닌 신비의 별자리입니다. 한번 목표를 정하면 어떤 어려움도 뚫고 나가는 집중력이 있습니다.",
        "strength": "통찰력, 집중력, 강인함, 변화 적응력",
        "weakness": "집착, 의심, 복수심, 비밀주의",
        "compatible": "게자리, 물고기자리, 염소자리",
        "tip": "오늘 신뢰하는 사람에게 마음을 조금 열어보시기 바랍니다. 말투가 평소보다 차갑게 전달되고 있지는 않은지 확인하는 것이 관계 유지에 도움이 됩니다.",
        "color": "검정, 진홍색", "stone": "토파즈, 옵시디언", "number": "8, 11",
    },
    "사수자리": {
        "element": "불 (Fire)", "ruling": "목성 (Jupiter)",
        "trait": "자유와 모험을 사랑하는 낙관주의 별자리입니다. 넓은 시야로 세상을 바라보며 끊임없이 새로운 지식과 경험을 추구합니다.",
        "strength": "낙관성, 철학적 사고, 모험심, 솔직함",
        "weakness": "무책임함, 성급한 약속, 무신경함",
        "compatible": "양자리, 사자자리, 물병자리",
        "tip": "오늘 지킬 수 있는 약속만 하시기 바랍니다. 무리한 부탁이 들어온다면 솔직하게 어렵다는 의사를 표현하는 것이 장기적인 관계를 위해 더 좋은 선택입니다.",
        "color": "보라색, 파란색", "stone": "터키석, 라피스라줄리", "number": "3, 9",
    },
    "염소자리": {
        "element": "흙 (Earth)", "ruling": "토성 (Saturn)",
        "trait": "책임감과 인내로 목표를 향해 묵묵히 나아가는 별자리입니다. 시간이 걸리더라도 반드시 정상에 오르는 지구력이 특징입니다.",
        "strength": "책임감, 인내심, 실용성, 야망",
        "weakness": "고집, 지나친 실용주의, 감정 억제",
        "compatible": "황소자리, 처녀자리, 전갈자리",
        "tip": "오늘 잠시 멈추고 쉬어가는 것도 전략입니다. 오래 달려왔다면 속도를 줄이는 것이 멈추는 것이 아니라 더 오래, 더 멀리 가기 위한 준비입니다.",
        "color": "갈색, 카키", "stone": "가넷, 호안석", "number": "8, 10",
    },
    "물병자리": {
        "element": "공기 (Air)", "ruling": "천왕성 (Uranus)",
        "trait": "독창성과 혁신적 사고를 지닌 미래 지향적 별자리입니다. 기존의 틀을 깨고 새로운 방식으로 세상을 바라보는 능력이 있습니다.",
        "strength": "독창성, 인도주의, 미래 지향, 개방성",
        "weakness": "감정 표현 어려움, 고집, 거리감",
        "compatible": "쌍둥이자리, 천칭자리, 사수자리",
        "tip": "오늘 아이디어가 너무 앞서간다 싶다면 먼저 메모해두시기 바랍니다. 상대방이 받아들일 준비가 되었을 때 꺼내는 것이 더 효과적인 전달 방법입니다.",
        "color": "일렉트릭 블루, 청록색", "stone": "아메시스트, 아쿠아마린", "number": "4, 7",
    },
    "물고기자리": {
        "element": "물 (Water)", "ruling": "해왕성 (Neptune)",
        "trait": "공감 능력이 탁월하고 예술적 감수성이 풍부한 별자리입니다. 타인의 감정을 직관적으로 읽어내는 능력이 탁월합니다.",
        "strength": "직관력, 창의성, 공감력, 헌신",
        "weakness": "우유부단함, 현실 도피, 감정 기복",
        "compatible": "게자리, 전갈자리, 황소자리",
        "tip": "오늘 감정에 치우치지 않도록 하루 한 번 현재 감정이 사실에 근거한 것인지 점검하시기 바랍니다. 직감이 강하게 느껴지더라도 반드시 사실 확인을 병행하는 것이 실수를 줄여줍니다.",
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
    """fortune_quotes_real.csv에서 오늘 날짜 기반으로 명언 선택"""
    if not fortune_quotes.empty and 'quote_ko' in fortune_quotes.columns:
        kst = now_kst()
        seed = kst.month * 100 + kst.day
        idx  = seed % len(fortune_quotes)
        row  = fortune_quotes.iloc[idx]
        quote      = str(row.get('quote_ko', ''))
        quote_en   = str(row.get('quote_en', ''))
        author_ko  = str(row.get('author_ko', ''))
        author_en  = str(row.get('author_en', ''))
        birth      = str(row.get('birth_death', ''))
        profession = str(row.get('profession', ''))
        meaning    = str(row.get('meaning', ''))
        background = str(row.get('background', ''))
        apply_     = str(row.get('apply', ''))
        category   = str(row.get('category', ''))
        return quote, quote_en, author_ko, author_en, birth, profession, meaning, background, apply_, category
    return '', '', '', '', '', '', '', '', '', ''

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
        m = zodiac_kr[zodiac_kr['zodiac'] == kr_name].reset_index(drop=True)
        if not m.empty:
            # 날짜(월*100+일)를 시드로 — 같은 날 같은 별자리는 항상 같은 문장
            kst = now_kst()
            seed = kst.month * 100 + kst.day
            idx  = seed % len(m)
            text = m.iloc[idx]['fortune']
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
        "오늘 유독 참기 어려운 날입니다. 그것은 개인의 잘못이 아닙니다.",
        "새로 뭔가 시작하고 싶은 충동이 생기는 날이에요. 나쁘지 않아요, 근데 지갑은 닫으세요.",
        "요즘 빨리 결과가 나오길 기다리다 지친 것 같아요. 오늘 한 가지만 실행해 보세요. 작아도 움직이는 것 자체가 흐름을 만듭니다.",
    ],
    "황소자리": [
        "오늘 유독 '이거 꼭 사야 해' 싶은 물건이 눈에 밟힌다면, 내일 다시 보세요.",
        "변화를 원하지 않는데 상황이 바뀌려 할 때 불편함이 생기는 날입니다. 자연스러운 반응입니다.",
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
    """이미지 저장 버튼 + 별과 띠가 만나는 시간 배너 링크
    - 공유하기(SNS 바텀시트) 제거
    - 이미지 저장 유지
    - 별과 띠가 만나는 시간 라벨 페이지 배너 추가
    """
    OMNIBUS_URL = (
        "https://todayhoroscopelaboratory.blogspot.com/search/label/"
        "%EB%B3%84%EA%B3%BC%EB%9D%A0%EA%B0%80%EB%A7%8C%EB%82%98%EB%8A%94%EC%8B%9C%EA%B0%84"
    )
    return f"""
<button id="savebtn-{card_id}" class="save-btn" onclick="saveFortuneCard('{card_id}', '{filename}')">📸 이미지 저장</button>
<a href="{OMNIBUS_URL}" target="_blank" rel="noopener"
   style="display:flex;align-items:center;gap:12px;text-decoration:none;
          margin-top:10px;padding:16px 18px;border-radius:14px;
          background:linear-gradient(135deg,#1e1b4b,#4c1d95)">
  <span style="font-size:26px;flex-shrink:0">🌙</span>
  <div style="flex:1;min-width:0">
    <div style="font-size:13px;font-weight:700;color:#e9d5ff;
                margin-bottom:3px;word-break:keep-all">별과띠가만나는시간</div>
    <div style="font-size:12px;color:#c4b5fd;line-height:1.6;word-break:keep-all">
      내 별자리와 띠가 오늘 어떻게 연결되는지 보러 가기 →
    </div>
  </div>
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
       stroke="#a78bfa" stroke-width="2.5" style="flex-shrink:0">
    <path d="M9 18l6-6-6-6"/>
  </svg>
</a>"""

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
    "아침이 유독 무겁게 느껴지는 날이 있습니다. 뉴스를 켜면 불안하고, 끄면 또 다른 불안이 찾아옵니다. 열심히 살고 있는데도 점점 좁아지는 느낌이 드는 것은 혼자만의 경험이 아닙니다.",
    "수입은 그대로인데 지출은 늘어나고, 제대로 하고 있는 건지 확신이 서지 않는 날들이 쌓입니다. 그 무게가 어느 순간부터 일상이 되어버린 것이 더 무겁게 느껴집니다.",
    "이렇게 살아도 되는 건지 의문이 드는 날이 있습니다. 주변은 모두 앞으로 나아가는 것처럼 보이는데 자신만 제자리인 것 같은 그 감각이 하루에 한 번씩은 찾아옵니다.",
    "직장에서 힘들어도 귀가 후에는 쉬어야 하는데, 집에 돌아와서도 머릿속은 계속 업무를 떠올립니다. 언제부터 쉬는 시간조차 불안해진 것인지 모르겠습니다.",
    "아무리 해도 풀리지 않는 시기가 있습니다. 특별히 잘못한 것도 없는데 세상이 냉정하게 느껴지는 그런 시기입니다. 지금 그러한 시간을 지나고 있는 분들이 적지 않을 것입니다.",
    "누군가에게 '요즘 어때요?'라는 말을 들으면 '그냥 그렇죠'라고 답하는 날이 늘었습니다. 설명하기도 애매하고, 그렇다고 괜찮은 것도 아닌 상태입니다.",
    "마음이 허전한데 그 이유를 명확히 말하기 어려운 날이 있습니다. 크게 잘못된 것도 없고, 그렇다고 좋은 것도 없는, 모든 것이 흐릿한 날입니다.",
    "열심히 준비하고 참으며 기다렸는데 기대했던 것보다 결과가 나오지 않을 때, 그 실망감은 말로 표현하기 어렵습니다. 겉으로 내보이기도 어려운 감정입니다.",
    "잘하고 싶은 마음은 있는데 몸이 따라주지 않는 날이 있습니다. 의지의 문제가 아니라, 너무 많은 것이 쌓인 것입니다. 자신에게 가장 엄격한 것이 자기 자신인 경우가 많습니다.",
    "연락해야 할 사람이 있는데 계속 미루게 되는 날들이 있습니다. 보고 싶기는 하지만 먼저 연락하기가 어색해진 것입니다. 그 거리감이 언제부터 생긴 것인지 모르겠습니다.",
    "괜찮은 척하는 것이 습관이 되면, 어느 순간부터 자신이 진짜 괜찮은 것인지 아닌지도 알 수 없게 됩니다. 그것이 가장 어려운 상태입니다.",
    "직장에서 왜 이것까지 해야 하는지 의문이 드는 순간이 최근 들어 자주 생깁니다. 해야 한다는 것을 알면서도 그 마음이 자꾸 올라오는 것은 지쳐가고 있다는 신호입니다.",
]

# ── 감정 흐름 파트: 버티는 감정의 솔직한 표현 ──
_EMOTION_POOL = [
    "그렇게 버티고 있다는 것 자체가 이미 대단한 일입니다. 무너지지 않는 것이 얼마나 힘든 일인지는 버텨본 사람이 압니다.",
    "지치는 것은 약해서가 아닙니다. 너무 오래 강했기 때문입니다. 그 차이를 스스로는 인정할 필요가 있습니다.",
    "힘든 것을 힘들다고 말하지 못하는 것이 더 힘든 경우가 있습니다. 이 정도면 괜찮아야 한다는 기준을 너무 높게 설정하고 있는 것은 아닌지 한 번쯤 돌아볼 필요가 있습니다.",
    "잘 살고 싶은 마음이 있기 때문에 지치는 것입니다. 무관심한 사람은 지치지 않습니다. 지금 이 피로감은 열심히 살고 있다는 증거입니다.",
    "오늘 하루가 다 풀리지 않아도 됩니다. 어떤 날은 그냥 지나가는 것만으로 충분한 날이 있습니다. 모든 날이 의미 있어야 하는 것은 아닙니다.",
    "감정을 억누르고 살다 보면 어느 순간 이유도 알 수 없이 힘들어지는 날이 옵니다. 그것은 이상한 것이 아닙니다. 오래 참아온 것이 쌓인 것입니다.",
    "잘못된 것이 아닙니다. 지금 이 시기가 험한 것입니다. 세상도, 상황도, 사람 사이도 모두 함께 어수선한 시기입니다.",
    "모든 것을 혼자 해결하려 하다 보니 부담이 너무 커진 것입니다. 내려놓는 것은 포기가 아닙니다. 숨을 고르는 것입니다.",
    "타인과 비교하게 되는 마음도 이해할 수 있습니다. 그러나 타인의 삶은 좋은 순간만 보이고, 자신의 삶은 전체가 보입니다. 그 차이를 인식하는 것이 중요합니다.",
    "기대했다가 실망하는 것이 반복되면 어느 순간 기대 자체를 하지 않게 됩니다. 그것이 자기 보호이기도 하지만, 한편으로는 안타까운 일입니다.",
    "지금과 같은 세상에서 불안함을 느끼는 것은 당연한 일입니다. 불안을 느끼는 것은 잘못된 것이 아닙니다. 그 불안을 안고 하루를 살아내는 것이 진정한 용기입니다.",
    "무언가를 잘하고 싶은 마음이 있는 한 완전히 포기한 것이 아닙니다. 그 마음이 아직 남아 있다는 것을 기억하시기 바랍니다.",
]

# ── 위로 파트: 구체적이고 따뜻한 위로 ──
_COMFORT_POOL = [
    "오늘 여기까지 왔다는 것, 그것만으로도 이미 충분히 잘한 것입니다. 큰 성공이 아니어도 됩니다. 오늘 무너지지 않은 것, 그것이 진짜 대단한 일입니다.",
    "지금 이 자리에서 계속 살아내고 있다는 것은 쉬운 일이 아닙니다. 누군가 알아주지 않더라도, 그 무게를 아는 사람이 있습니다.",
    "오늘 하루 힘들었다면 충분히 힘들었다고 인정하시기 바랍니다. 스스로에게만큼은 솔직해도 됩니다. 그 정도면 충분히 열심히 살아낸 것입니다.",
    "완벽하게 잘 살지 않아도 됩니다. 조금씩, 자신의 속도대로 가는 것이 오히려 더 멀리 가는 방법입니다. 서두르지 않아도 됩니다.",
    "지금 잘 보이지 않더라도 쌓이고 있는 것이 있습니다. 눈에 보이지 않는 것들이 나중에 가장 단단한 기반이 되는 경우가 많습니다. 지금 하고 있는 것들이 헛된 것이 아닙니다.",
    "힘든 시간을 지나고 있다면, 그것이 끝이 아닙니다. 끝처럼 느껴지는 그 순간이 사실은 방향이 바뀌기 직전인 경우가 많습니다.",
    "오늘 아무것도 못 한 것 같더라도, 오늘을 버텨냈습니다. 그것이 오늘의 성과입니다.",
    "스스로에게 조금 더 너그러워도 됩니다. 타인에게는 이해할 수 있는 것들을 자신에게는 너무 엄격하게 적용하고 있는 것은 아닌지 한 번 돌아보시기 바랍니다.",
    "지치면 쉬어도 됩니다. 쉬는 것은 포기가 아닙니다. 멈추는 것이 아니라, 다시 나아가기 위해 숨을 고르는 것입니다.",
    "지금 버티고 있는 이 시간이 나중에 가장 단단한 토대가 되어줄 것입니다. 지금은 보이지 않더라도 쌓이고 있습니다.",
    "살다 보면 그냥 통과해야 하는 시기가 있습니다. 그 시기를 잘 지나가는 것 자체가 대단한 일입니다. 지금이 그러한 시간일 수 있습니다.",
    "오늘 괜찮지 않아도 됩니다. 모든 날이 잘 흘러가야 하는 것은 아닙니다. 오늘은 그냥 지나가는 것만으로 충분한 날입니다.",
]

# ── SEO 제목 키워드 패턴 ──
_QUOTE_TITLE_PATTERNS = [
    "{today} 오늘의 명언 — 지금 이 순간 필요한 한 마디",
    "{today} 오늘의 위로 명언 | 힘든 하루를 살아낸 분들에게",
    "오늘의 명언 {today} — 지치고 힘들 때 읽으면 좋은 글",
    "{today} 오늘 하루를 살아가는 분들을 위한 명언",
    "오늘의 명언 | {today} 마음에 새길 한 줄",
    "{today} 오늘의 명언 — 무기력한 날에 읽어보시기 바랍니다",
    "지금 지쳐 있는 분들에게 | {today} 오늘의 위로 명언",
    "{today} 오늘의 명언 · 현실 위로형 스토리텔링",
]

def build_quote_post(today_str):
    """실존 명언 기반 정보성 스토리텔링 포스트 — 1,000자 이상, 출처·의미·배경·적용 포함"""
    quote, quote_en, author_ko, author_en, birth, profession, meaning, background, apply_, category = pick_quote()

    # 제목 패턴
    kst = now_kst()
    seed = kst.month * 100 + kst.day
    title_patterns = _QUOTE_TITLE_PATTERNS
    title = title_patterns[seed % len(title_patterns)].format(today=today_str)

    # 인물 소개 섹션
    author_intro = f"""
<div class="card" style="border-left:5px solid #7c3aed;background:linear-gradient(135deg,#faf5ff,#f3e8ff)">
  <div style="display:flex;align-items:flex-start;gap:12px">
    <div style="font-size:36px">📖</div>
    <div>
      <div style="font-size:18px;font-weight:900;color:#4c1d95;margin-bottom:4px">{author_ko}</div>
      <div style="font-size:12px;color:#7c3aed;font-weight:600">{author_en} · {birth}</div>
      <div style="font-size:13px;color:#6d28d9;margin-top:4px">{profession}</div>
    </div>
  </div>
</div>"""

    # 명언 원문 섹션
    quote_section = f"""
<div style="background:linear-gradient(135deg,#fdf4ff,#ede9fe);border-radius:18px;
            padding:24px 22px;margin:20px 0;text-align:center;
            box-shadow:0 2px 16px rgba(124,58,237,0.08)">
  <div style="font-size:11px;color:#9ca3af;letter-spacing:0.12em;
              margin-bottom:14px;font-weight:600">오늘의 명언</div>
  <div style="font-size:18px;font-weight:800;color:#4c1d95;
              line-height:1.7;word-break:keep-all;margin-bottom:14px">
    ❝ {quote} ❞
  </div>
  <div style="font-size:12px;color:#9ca3af;font-style:italic;line-height:1.6">
    {quote_en}
  </div>
  <div style="margin-top:12px;font-size:13px;font-weight:700;color:#7c3aed">
    — {author_ko} ({birth})
  </div>
</div>"""

    # 명언의 의미 섹션
    meaning_section = f"""
<div class="card" style="background:#fefce8;border-left:4px solid #eab308">
  <div style="font-size:14px;font-weight:700;color:#92400e;margin-bottom:10px">
    💡 이 명언의 의미
  </div>
  <p style="font-size:15px;line-height:2.0;color:#374151;margin:0;word-break:keep-all">
    {meaning}
  </p>
</div>"""

    # 배경 및 맥락 섹션
    background_section = f"""
<div class="card" style="background:#f0f9ff;border-left:4px solid #0ea5e9">
  <div style="font-size:14px;font-weight:700;color:#0c4a6e;margin-bottom:10px">
    🌍 이 말이 나온 배경
  </div>
  <p style="font-size:15px;line-height:2.0;color:#374151;margin:0;word-break:keep-all">
    {background}
  </p>
</div>"""

    # 오늘 적용 섹션
    apply_section = f"""
<div style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border-radius:14px;
            padding:20px;margin:16px 0;border-left:4px solid #16a34a">
  <div style="font-size:14px;font-weight:700;color:#14532d;margin-bottom:10px">
    ✅ 오늘 이렇게 적용해보시기 바랍니다
  </div>
  <p style="font-size:15px;line-height:2.0;color:#374151;margin:0;word-break:keep-all">
    {apply_}
  </p>
</div>"""

    # 공감·위로 파트
    empathy  = random.choice(_EMPATHY_POOL)
    emotion  = random.choice(_EMOTION_POOL)
    comfort  = random.choice(_COMFORT_POOL)

    # SEO 키워드
    kw_list = [
        "오늘의명언", "위로명언", "현실명언", today_str,
        "힘들때명언", "위로글", "성공명언", "인생명언",
        "동기부여명언", "아침명언", "명언모음", "좋은글",
        author_ko, f"{author_ko}명언",
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
  margin-bottom: 1.0rem;
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
  margin-bottom: 1.6rem;
}}
.qc-rule {{
  text-align: center;
  color: #d1d5db;
  letter-spacing: 0.5em;
  margin: 1.6rem 0;
  font-size: 13px;
}}
.qc-body {{
  font-size: 15px;
  line-height: 2.1;
  color: #374151;
  word-break: keep-all;
}}
.qc-body p {{
  margin: 0 0 1.4em 0;
}}
.qc-footer {{
  margin-top: 2rem;
  padding-top: 1.6rem;
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
    <div class="qc-date">{today_str} · {category}</div>
    <h1 class="qc-title">📖 오늘의 명언</h1>
    <p class="qc-sub">{author_ko}이 오늘 당신에게 건네는 한 줄</p>
    <div class="qc-rule">&middot; &middot; &middot;</div>
    <div class="qc-body">
      <p>{empathy}</p>
    </div>
    <div style="background:linear-gradient(135deg,#fdf4ff,#ede9fe);border-radius:14px;
                padding:18px;text-align:center;margin:12px 0">
      <div style="font-size:16px;font-weight:800;color:#4c1d95;line-height:1.7;
                  word-break:keep-all">❝ {quote} ❞</div>
      <div style="font-size:12px;font-weight:700;color:#7c3aed;margin-top:8px">
        — {author_ko}</div>
    </div>
    <div class="qc-rule">&middot; &middot; &middot;</div>
    <div class="qc-footer">
      오늘 하루도 잘 살아내셨습니다.<br>
      내일도 함께하겠습니다.
    </div>
  </div>

  {share_buttons(card_id, f"오늘의명언_{today_str}")}

  <!-- 인물 소개 -->
  {author_intro}

  <!-- 명언 원문 -->
  {quote_section}

  <!-- 명언의 의미 -->
  {meaning_section}

  <!-- 배경과 맥락 -->
  {background_section}

  <!-- 공감·위로 스토리 -->
  <div class="card" style="background:#fafafa">
    <span class="badge">💭 오늘 당신에게</span>
    <div class="qc-body" style="margin-top:12px">
      <p>{emotion}</p>
      <p>{comfort}</p>
    </div>
  </div>

  <!-- 오늘 적용 -->
  {apply_section}

  <!-- SEO 키워드 -->
  <div class="card">
    <span class="badge">🔍 관련 키워드</span>
    <div class="tag-cloud">{tag_html}</div>
  </div>

  {site_link()}
  <div class="meta">※ 매일 업데이트 · 실존 인물의 명언과 오늘의 이야기</div>
</div>"""

    return title, content, ["오늘의명언", "위로명언", "명언", "운세", category]


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
<div style="display:none" aria-hidden="true">
<div class="card" style="background:#f8f0ff">
  <span class="badge">📊 오늘의 운세 지수 · <strong style="color:#6c3483">{signal_kw}</strong></span>
  <div style="margin-top:12px">
    {_zodiac_score_bar("종합운","🌟",total)}
    {_zodiac_score_bar("금전운","💰",money)}
    {_zodiac_score_bar("건강운","💪",health)}
    {_zodiac_score_bar("애정운","❤️",love)}
  </div>
</div>
</div>'''

    # ── 스토리텔링 섹션별 산문 빌드 ──

    # 오늘의 흐름 레벨 텍스트 (점수% 대신 감성 언어)
    def _flow_level(score):
        if score >= 80: return "오늘 흐름이 잘 열려 있는 날입니다."
        if score >= 65: return "나쁘지 않은 흐름의 날입니다."
        if score >= 50: return "잔잔하게 지나가는 날입니다."
        return "조금 조심스러운 흐름이에요."

    # 공감형 오프닝 (human_voice)
    opening_html = f'''
<div style="padding:1.4rem 1.6rem 1.2rem;background:linear-gradient(135deg,#faf5ff,#f0f9ff);
            border-radius:16px;margin-bottom:16px;border-left:4px solid #a78bfa">
  <p style="font-size:15px;line-height:2.05;color:#374151;font-weight:500;margin:0;word-break:keep-all">
    💭 {human_voice}
  </p>
</div>''' if human_voice else ''

    # 총운 — 스토리 산문
    story_total_html = f'''
<div class="card" style="border-left:5px solid {total_color}">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
    <span style="font-size:22px">🌟</span>
    <div>
      <div style="font-size:16px;font-weight:700;color:{total_color}">오늘의 흐름</div>
      <div style="font-size:12px;color:#9ca3af;margin-top:2px">{_flow_level(total)} · {total_level}</div>
    </div>
  </div>
  <p style="font-size:15px;line-height:2.0;color:#333;font-weight:500;margin:0 0 10px 0">{total_intro}</p>
  <p style="font-size:14px;line-height:1.95;color:#444;margin:0 0 8px 0">{_para(0)}</p>
  <p style="font-size:14px;line-height:1.95;color:#444;margin:0 0 10px 0">{_para(1)}</p>
  <div style="background:#f0fdf4;border-radius:10px;padding:11px 14px;
              font-size:13px;color:#166534;line-height:1.8;border-left:3px solid {total_color}">
    📌 {total_score_c}
  </div>
</div>'''

    # 연애운 — 스토리 산문
    story_love_html = f'''
<div class="card">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
    <span style="font-size:22px">❤️</span>
    <div>
      <div style="font-size:16px;font-weight:700;color:{love_color}">관계·연애</div>
      <div style="font-size:12px;color:#9ca3af;margin-top:2px">{_flow_level(love)}</div>
    </div>
  </div>
  <p style="font-size:15px;line-height:2.0;color:#333;font-weight:500;margin:0 0 10px 0">{love_intro}</p>
  <p style="font-size:14px;line-height:1.95;color:#444;margin:0 0 10px 0">{_para(2)}</p>
  <div style="background:#fff0f3;border-radius:10px;padding:11px 14px;
              font-size:13px;color:#9f1239;line-height:1.8;border-left:3px solid #e11d48">
    💡 {love_detail}
  </div>
  {_love_time_html}
  <p style="margin-top:10px;font-size:13px;line-height:1.85;color:#666;font-style:italic">{love_close}</p>
</div>'''

    # 금전운 — 스토리 산문
    story_money_html = f'''
<div class="card">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
    <span style="font-size:22px">💰</span>
    <div>
      <div style="font-size:16px;font-weight:700;color:{money_color}">돈·재물</div>
      <div style="font-size:12px;color:#9ca3af;margin-top:2px">{_flow_level(money)}</div>
    </div>
  </div>
  <p style="font-size:15px;line-height:2.0;color:#333;font-weight:500;margin:0 0 10px 0">{money_intro}</p>
  <p style="font-size:14px;line-height:1.95;color:#444;margin:0 0 10px 0">{_para(3)}</p>
  <div style="background:#fef9c3;border-radius:10px;padding:11px 14px;
              font-size:13px;color:#78350f;line-height:1.8;border-left:3px solid #d97706">
    💡 {money_detail}
  </div>
  {_money_time_html}
  <p style="margin-top:10px;font-size:13px;line-height:1.85;color:#666;font-style:italic">{money_close}</p>
</div>'''

    # 직장운 — 스토리 산문
    story_work_html = f'''
<div class="card">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
    <span style="font-size:22px">💼</span>
    <div>
      <div style="font-size:16px;font-weight:700;color:{work_color}">일·직장</div>
      <div style="font-size:12px;color:#9ca3af;margin-top:2px">{_flow_level(work_score)}</div>
    </div>
  </div>
  <p style="font-size:15px;line-height:2.0;color:#333;font-weight:500;margin:0 0 10px 0">{work_intro}</p>
  <p style="font-size:14px;line-height:1.95;color:#444;margin:0 0 10px 0">{_para(4)}</p>
  <div style="background:#dbeafe;border-radius:10px;padding:11px 14px;
              font-size:13px;color:#1e3a8a;line-height:1.8;border-left:3px solid #3b82f6">
    💡 {work_detail}
  </div>
  {_work_time_html}
  <p style="margin-top:10px;font-size:13px;line-height:1.85;color:#666;font-style:italic">{work_close}</p>
</div>'''

    # 공통 엔딩 — 별자리 개별 포스트용 (날짜 기반 순환)
    _z_endings = [
        ("오늘 하루가 예상대로 흘러가지 않아도 됩니다.",
         "지금 이 감각은 혼자만 경험하는 것이 아닙니다.",
         "오늘 마음에 걸리는 것 하나만 직면해보시기 바랍니다."),
        ("운세가 모든 상황에 정확히 맞지는 않습니다.",
         "오늘 이 글이 현재 상황을 돌아보는 계기가 되었다면 충분한 역할을 한 것입니다.",
         "오늘도 잘 살아내셨습니다."),
        ("좋은 흐름이 오든, 어려운 흐름이 오든.",
         "결국 오늘을 어떻게 사용하느냐가 내일을 만들어 냅니다.",
         "오늘 가장 마음에 걸리는 것 하나만 실천해보시기 바랍니다."),
        ("오늘 읽으면서 공감이 되거나 위로가 되는 부분이 있었다면.",
         "그 감각이 맞습니다. 결국 오늘 이 이야기는 지금 이 순간의 당신에 관한 것입니다.",
         "내일도 함께하겠습니다."),
        ("힘들었던 날이든, 그냥 지나간 날이든.",
         "오늘 여기까지 온 것만으로 이미 충분히 잘 하고 있는 것입니다.",
         "그 감각은 혼자만 경험하는 것이 아닙니다."),
        ("오늘 하루 수고하셨습니다.",
         "눈에 보이지 않더라도 분명히 쌓이고 있는 것들이 있습니다.",
         "내일도 함께하겠습니다."),
        ("별자리는 오늘 어떤 에너지 위에 있는지 알려주고 있습니다.",
         "그 에너지를 어떻게 사용할지는 스스로 선택하는 것입니다.",
         "오늘 가장 자연스럽게 오는 것을 따라가보시기 바랍니다."),
    ]
    _ze = _z_endings[now_kst().day % len(_z_endings)]
    zodiac_ending_html = f'''
<div style="margin:24px 0 0 0;border-radius:18px;overflow:hidden;
            box-shadow:0 2px 12px rgba(91,33,182,0.07)">
  <div style="background:linear-gradient(90deg,#7c3aed,#a78bfa);
              padding:0.6rem 1.3rem;display:flex;align-items:center;gap:8px">
    <span style="font-size:14px">{z['emoji']}</span>
    <span style="font-size:11px;font-weight:700;color:#ede9fe;letter-spacing:0.1em">
      오늘 {z['kr']}에게 전하는 말
    </span>
  </div>
  <div style="background:linear-gradient(160deg,#faf5ff,#fdf4ff);padding:1.4rem 1.5rem 0.5rem">
    <p style="font-size:15px;line-height:2.0;color:#374151;font-weight:500;
              margin:0 0 0.8rem 0;word-break:keep-all">{_ze[0]}</p>
    <p style="font-size:14px;line-height:1.95;color:#6d28d9;margin:0 0 1.2rem 0;
              font-style:italic;padding-left:0.8rem;border-left:3px solid #c4b5fd;
              word-break:keep-all">{_ze[1]}</p>
  </div>
  <div style="background:#5b21b6;padding:1rem 1.5rem;text-align:center">
    <div style="font-size:11px;color:#c4b5fd;letter-spacing:0.12em;
                margin-bottom:0.4rem;font-weight:600">오늘 하나만 한다면</div>
    <span style="font-size:16px;font-weight:800;color:#fff;
                 word-break:keep-all;line-height:1.6">❝ {_ze[2]} ❞</span>
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

  <!-- 행운 아이템 제거 (애드센스 심사 기준) -->
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
        f"{z['kr']} 조언", f"{z['kr']} 오늘팁",
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

  <!-- 공감형 오프닝 -->
  {opening_html}

  <!-- 1. 오늘의 흐름 (총운 스토리) -->
  {story_total_html}

  <!-- 대표 이미지 -->
  {post_img("zodiac")}

  <!-- 2. 관계·연애 스토리 -->
  {story_love_html}

  <!-- 3. 돈·재물 스토리 -->
  {story_money_html}

  <!-- 4. 일·직장 스토리 -->
  {story_work_html}

  <!-- 5. 오늘 피해야 할 행동 -->
  {avoid_html}

  <!-- 5-1. 현실 디테일 블록 -->
  {real_detail_html}

  <!-- 6. 응원 메시지 -->
  {cheer_html}

  <!-- 이미지 저장 카드 -->
  {image_card_html}
  {share_buttons(card_id, f"별자리운세_{z['kr']}_{today_str}")}

  <!-- 행운 아이템 & 색상 가이드 -->
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
      <!-- 행운 숫자 제거 (애드센스 심사 기준) -->
    </div>
  </div>

  <!-- 계산 내역 제거 (근거 없는 수치 → 애드센스 심사 기준) -->

  <!-- 운세 지수 바 (fortune.html 연동용 — 화면에는 숨김) -->
  {score_html}

  <!-- 별자리 고유 정보 (차별화·정보성 강화) -->
  {zodiac_info_card(z['kr'], z['emoji'])}

  <!-- 공통 엔딩 -->
    <div class="tag-cloud">{tag_html}</div>
  </div>

  {site_link()}
  <div class="meta"><p>{z['kr']} ({z['date']})</p><p>※ 재미로 보는 운세 콘텐츠입니다</p></div>
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

    score_html = f'''<div style="display:none" aria-hidden="true">
<div class="card" style="background:#f8f0ff">
  <span class="badge">📊 오늘의 운세 지수 · <strong style="color:#6c3483">{signal}</strong></span>
  <div style="margin-top:12px">
    {_bar("종합운","🌟",total)}{_bar("금전운","💰",money)}{_bar("건강운","💪",health)}{_bar("애정운","❤️",love)}
  </div>
</div>
</div>'''

    # ── 공감형 오프닝 (human_voice 맨 위) ──
    chinese_opening_html = f'''
<div style="padding:1.4rem 1.6rem 1.2rem;background:linear-gradient(135deg,#fffbeb,#fef3c7);
            border-radius:16px;margin-bottom:16px;border-left:4px solid #f59e0b">
  <p style="font-size:15px;line-height:2.05;color:#374151;font-weight:500;margin:0;word-break:keep-all">
    💭 {chinese_human_voice}
  </p>
</div>''' if chinese_human_voice else ''

    # ── 띠별 공통 엔딩 7종 (날짜 순환) ──
    _c_endings = [
        ("오늘 하루가 예상대로 흘러가지 않아도 됩니다.",
         "지금 이 감각은 혼자만 경험하는 것이 아닙니다.",
         "오늘 마음에 걸리는 것 하나만 직면해보시기 바랍니다."),
        ("운세가 모든 상황에 정확히 맞지는 않습니다.",
         "근데 오늘 이 글이 '나 요즘 이랬는데'가 됐다면, 그걸로 오늘은 잘 읽은 거예요.",
         "오늘도 잘 살아내셨습니다."),
        ("좋은 흐름이 오든, 어려운 흐름이 오든.",
         "결국 오늘을 어떻게 사용하느냐가 내일을 만들어 냅니다.",
         "오늘 딱 하나 — 가장 마음에 걸리는 것, 그거 하나만 해보세요."),
        ("오늘 읽으면서 공감이 되거나 위로가 되는 부분이 있었다면.",
         "그 감각이 맞습니다. 결국 오늘 이 이야기는 지금 이 순간의 당신에 관한 것입니다.",
         "내일도 함께하겠습니다."),
        ("힘들었던 날이든, 그냥 지나간 날이든.",
         "오늘 여기까지 온 것만으로 이미 충분히 잘 하고 있는 것입니다.",
         "그 감각은 혼자만 경험하는 것이 아닙니다."),
        ("오늘 하루 수고하셨습니다.",
         "눈에 보이지 않더라도 분명히 쌓이고 있는 것들이 있습니다.",
         "내일도 함께하겠습니다."),
        ("같은 띠여도 오늘 하루를 어떻게 쓰느냐는 각자 달라요.",
         "오늘 당신이 고른 것들이 쌓여서 당신만의 흐름이 돼요.",
         "오늘 가장 자연스럽게 오는 것을 따라가보시기 바랍니다."),
    ]
    _ce = _c_endings[now_kst().day % len(_c_endings)]
    chinese_ending_html = f'''
<div style="margin:24px 0 0 0;border-radius:18px;overflow:hidden;
            box-shadow:0 2px 12px rgba(245,158,11,0.1)">
  <div style="background:linear-gradient(90deg,#d97706,#f59e0b);
              padding:0.6rem 1.3rem;display:flex;align-items:center;gap:8px">
    <span style="font-size:14px">{c['emoji']}</span>
    <span style="font-size:11px;font-weight:700;color:#fef3c7;letter-spacing:0.1em">
      오늘 {c['kr']}에게 전하는 말
    </span>
  </div>
  <div style="background:linear-gradient(160deg,#fffbeb,#fef9c3);padding:1.4rem 1.5rem 0.5rem">
    <p style="font-size:15px;line-height:2.0;color:#374151;font-weight:500;
              margin:0 0 0.8rem 0;word-break:keep-all">{_ce[0]}</p>
    <p style="font-size:14px;line-height:1.95;color:#92400e;margin:0 0 1.2rem 0;
              font-style:italic;padding-left:0.8rem;border-left:3px solid #fcd34d;
              word-break:keep-all">{_ce[1]}</p>
  </div>
  <div style="background:#92400e;padding:1rem 1.5rem;text-align:center">
    <div style="font-size:11px;color:#fcd34d;letter-spacing:0.12em;
                margin-bottom:0.4rem;font-weight:600">오늘 하나만 한다면</div>
    <span style="font-size:16px;font-weight:800;color:#fff;
                 word-break:keep-all;line-height:1.6">❝ {_ce[2]} ❞</span>
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
    <p>{today_str} · {signal}</p>
  </div>

  <!-- 공감형 오프닝 (맨 위) -->
  {chinese_opening_html}

  <!-- 운세 지수 바 (fortune.html 연동용 — 화면에는 숨김) -->
  {score_html}
  <!-- calc_html 제거 (근거 없는 수치 → 애드센스 심사 기준) -->

  <!-- 시간대별 운세 흐름 -->
  {time_flow_html}

  <!-- 이미지 저장 카드 -->
  <div id="{card_id}" class="fortune-card" style="background:linear-gradient(135deg,#f59e0b,#92400e)">
    <div class="fc-emoji">{c['emoji']}</div>
    <div class="fc-title">{c['kr']}</div>
    <div class="fc-sub">{today_str}</div>
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

  <!-- 출생연도별 맞춤 운세 -->
  {year_section_html}

  <!-- 실전 체크포인트 -->
  {checkpoint_section}

  {caution_html}

  <!-- 현실 디테일 -->
  {chinese_real_detail}

  <!-- 띠별 궁합 -->
  {compat_html}

  <!-- 행운 아이템·색상 가이드 -->
  {lucky_guide_html}

  <!-- 공통 엔딩 -->
  {chinese_ending_html}

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
    """별자리별 주간운세 12개 개별 발행 — 매주 월요일 / 스토리텔링 구조"""
    week_range = get_week_range()
    today_date = now_kst().date()
    mon_date   = date.fromordinal(today_date.toordinal() - today_date.weekday())
    month_str  = mon_date.strftime("%Y년 %m월")

    # 주간 공감형 오프닝 풀
    _W_OPENINGS = [
        "이번 주의 흐름을 점검할 시간입니다. 방향에 대한 의문이 드는 것은 자연스러운 과정입니다.",
        "새로운 한 주가 시작되었습니다. 이번 주를 어떻게 운영할지 함께 살펴보겠습니다.",
        "이번 주 별자리가 전달하는 에너지가 무엇인지 확인할 시간입니다.",
        "한 주를 온전히 살아내는 것은 쉽지 않은 일입니다. 이번 주의 흐름을 미리 파악해 두시기 바랍니다.",
        "새로운 한 주가 시작되었습니다. 이번 주는 지난주와 다른 흐름이 예상됩니다.",
    ]

    # 주간 공통 엔딩 풀
    _W_ENDINGS = [
        ("이번 주 하루하루의 축적이 결국 하나의 흐름을 만들어 냅니다.",
         "현재 올바른 방향으로 나아가고 있습니다. 이러한 감각은 혼자만 경험하는 것이 아닙니다.",
         "이번 주 가장 마음에 걸리는 한 가지에 집중하시기 바랍니다."),
        ("순탄한 주간이든 인내가 필요한 주간이든, 끝까지 완수하는 것이 중요합니다.",
         "이번 주의 흐름을 파악하였으니 보다 안정적으로 움직이실 수 있습니다.",
         "오늘 하루에만 집중하시기 바랍니다. 내일의 흐름은 내일이 결정합니다."),
        ("이번 주 별자리가 전달한 방향을 참고하여 나머지는 스스로 결정하시기 바랍니다.",
         "운세는 방향을 제시하는 도구입니다. 그 방향을 어떻게 걸어가느냐는 본인의 선택입니다.",
         "이번 주도 최선을 다하시기 바랍니다."),
    ]

    results = []
    for z in ZODIACS:
        fortune = zodiac_weekly_fortune(z['kr'])
        rating  = stars()
        card_id = f"zwfc-{z['en']}"
        total, money, health, love = pick_score(z['kr'])

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

        # 주차 계산 (검색 유입 기간 연장)
        week_num = (mon_date.day - 1) // 7 + 1
        week_label = f"{month_str} {week_num}주차"
        title = f"{z['kr']} {week_label} 주간운세 {week_range} | {signal}"

        # ── _flow_level (주간용) ──
        def _w_flow(score):
            if score >= 80: return "이번 주 흐름이 잘 열려 있는 주간입니다."
            if score >= 65: return "안정적인 흐름의 주간입니다."
            if score >= 50: return "잔잔하게 흘러가는 주간입니다."
            return "신중하게 움직여야 하는 주간입니다."

        # ── 공감형 오프닝 ──
        _wi = now_kst().day % len(_W_OPENINGS)
        opening = _W_OPENINGS[_wi]

        # ── 이번 주 흐름 스토리 ──
        weekly_story_html = f'''
<div class="card" style="border-left:5px solid #7c3aed">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
    <span style="font-size:22px">📅</span>
    <div>
      <div style="font-size:16px;font-weight:700;color:#7c3aed">이번 주 흐름</div>
      <div style="font-size:12px;color:#9ca3af;margin-top:2px">{_w_flow(total)} · {week_range}</div>
    </div>
  </div>
  <p style="font-size:15px;line-height:2.0;color:#333;font-weight:500;margin:0 0 10px 0">{fortune}</p>
  <!-- 점수 바 제거 (근거 없는 수치 — 애드센스 심사 기준) -->
</div>'''

        # ── 공통 엔딩 ──
        _we = _W_ENDINGS[now_kst().day % len(_W_ENDINGS)]
        weekly_ending_html = f'''
<div style="margin:24px 0 0 0;border-radius:18px;overflow:hidden;
            box-shadow:0 2px 12px rgba(124,58,237,0.08)">
  <div style="background:linear-gradient(90deg,#7c3aed,#a78bfa);
              padding:0.6rem 1.3rem;display:flex;align-items:center;gap:8px">
    <span style="font-size:14px">{z['emoji']}</span>
    <span style="font-size:11px;font-weight:700;color:#ede9fe;letter-spacing:0.1em">
      이번 주 {z['kr']}에게 전하는 말
    </span>
  </div>
  <div style="background:linear-gradient(160deg,#faf5ff,#fdf4ff);padding:1.4rem 1.5rem 0.5rem">
    <p style="font-size:15px;line-height:2.0;color:#374151;font-weight:500;
              margin:0 0 0.8rem 0;word-break:keep-all">{_we[0]}</p>
    <p style="font-size:14px;line-height:1.95;color:#6d28d9;margin:0 0 1.2rem 0;
              font-style:italic;padding-left:0.8rem;border-left:3px solid #c4b5fd;
              word-break:keep-all">{_we[1]}</p>
  </div>
  <div style="background:#5b21b6;padding:1rem 1.5rem;text-align:center">
    <div style="font-size:11px;color:#c4b5fd;letter-spacing:0.12em;
                margin-bottom:0.4rem;font-weight:600">이번 주 하나만 한다면</div>
    <span style="font-size:16px;font-weight:800;color:#fff;
                 word-break:keep-all;line-height:1.6">❝ {_we[2]} ❞</span>
  </div>
</div>'''

        # 별자리 고유 정보 섹션 (날짜 무관 상시 검색 유입)
        zodiac_info_weekly = zodiac_info_card(z['kr'], z['emoji'])

        kw_list = [
            z['kr'], f"{z['kr']} 주간운세", f"{z['kr']} 이번주운세",
            f"{z['kr']} {week_label}", "별자리 주간운세",
            f"{z['kr']} {month_str}", "주간운세", "별자리운세",
            f"{z['kr']} 특징", f"{z['kr']} 성격", f"{z['kr']} 궁합",
        ]
        tag_html = "".join(f'<span class="tag">{t}</span>' for t in kw_list)

        content_html = f"""{style()}
<div class="wrap">
  <div class="hero">
    <h1>📅 {z['emoji']} {z['kr']} 주간운세</h1>
    <p>{week_range} · {z['date']}</p>
    <div style="margin-top:8px;display:inline-block;background:rgba(255,255,255,0.2);
                padding:3px 12px;border-radius:20px;font-size:12px">{signal}</div>
  </div>

  <!-- 공감형 오프닝 -->
  <div style="padding:1.4rem 1.6rem 1.2rem;background:linear-gradient(135deg,#faf5ff,#f0f9ff);
              border-radius:16px;margin-bottom:16px;border-left:4px solid #a78bfa">
    <p style="font-size:15px;line-height:2.05;color:#374151;font-weight:500;
              margin:0;word-break:keep-all">💭 {opening}</p>
  </div>

  <!-- 이번 주 흐름 -->
  {weekly_story_html}

  <!-- 이미지 저장 카드 -->
  <div id="{card_id}" class="fortune-card">
    <div class="fc-emoji">{z['emoji']}</div>
    <div class="fc-title">{z['kr']} 주간운세</div>
    <div class="fc-sub">{week_range} · {z['date']}</div>
    <div class="fc-stars">{rating}</div>
    <div class="fc-text">{fortune}</div>
    <div class="fc-watermark">todayhoroscopelaboratory.blogspot.com · {week_range}</div>
  </div>
  {share_buttons(card_id, f"{z['kr']}_주간운세")}

  {post_img("weekly")}

  <!-- 공통 엔딩 -->
  {weekly_ending_html}

  <!-- 별자리 고유 정보 (날짜 무관 상시 검색 유입 강화) -->
  {zodiac_info_weekly}

  <div class="card"><span class="badge">🔍 관련 키워드</span>
    <div class="tag-cloud">{tag_html}</div>
  </div>
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

    # ── 띠별 고유 특성 정보 (독창성·정보성 강화) ──
    _CHINESE_INFO = {
        "rat":    {"kr":"쥐띠", "trait":"빠른 판단력과 정보 수집 능력이 뛰어난 타입", "strength":"민첩함·창의성·적응력", "weakness":"과도한 걱정·우유부단", "monthly_tip":"이달 쥐띠는 정보가 곧 기회입니다. 빠르게 움직이되 검증을 먼저 하는 것이 이달 핵심입니다."},
        "ox":     {"kr":"소띠", "trait":"꾸준하고 성실하며 한번 시작한 것은 끝까지 완수하는 타입", "strength":"인내·신뢰감·실행력", "weakness":"변화 거부·고집", "monthly_tip":"이달 소띠는 꾸준함이 가장 강한 무기입니다. 새로 시작하는 것보다 지속하는 것이 이달 더 좋은 결과를 만들어 냅니다."},
        "tiger":  {"kr":"호랑이띠", "trait":"용감하고 카리스마가 강하며 리더십이 자연스럽게 나오는 타입", "strength":"추진력·용기·리더십", "weakness":"충동적·기다림 어려움", "monthly_tip":"이달 호랑이띠는 에너지가 넘치는 시기입니다. 그 에너지를 한 방향으로 집중하는 것이 이달 가장 중요한 전략입니다."},
        "rabbit": {"kr":"토끼띠", "trait":"섬세하고 눈치가 빠르며 조화를 추구하는 타입", "strength":"공감능력·세심함·사교성", "weakness":"우유부단·회피 경향", "monthly_tip":"이달 토끼띠는 관계에서 가장 빛나는 시기입니다. 먼저 다가가는 것이 이달 더 좋은 연결을 만들어 줍니다."},
        "dragon": {"kr":"용띠", "trait":"카리스마가 강하고 이상이 높으며 큰 그림을 보는 타입", "strength":"열정·창의성·카리스마", "weakness":"완벽주의·고집", "monthly_tip":"이달 용띠는 큰 아이디어를 실행으로 옮기기 좋은 시기입니다. 단, 세부 계획도 함께 챙기시기 바랍니다."},
        "snake":  {"kr":"뱀띠", "trait":"직관이 예리하고 신중하며 깊게 생각하는 타입", "strength":"통찰력·신중함·집중력", "weakness":"의심·감정 표현 어려움", "monthly_tip":"이달 뱀띠는 직관이 가장 정확하게 작동하는 시기입니다. 충분히 관찰한 후 움직이는 것이 이달 맞는 방식입니다."},
        "horse":  {"kr":"말띠", "trait":"자유를 사랑하고 활동적이며 변화를 즐기는 타입", "strength":"열정·적응력·사교성", "weakness":"끈기 부족·집중 분산", "monthly_tip":"이달 말띠는 활동적인 에너지가 올라오는 시기입니다. 하나에 집중하는 것이 이달 가장 좋은 결과를 만들어 냅니다."},
        "goat":   {"kr":"양띠", "trait":"온화하고 배려심이 깊으며 예술적 감수성이 풍부한 타입", "strength":"공감능력·창의성·온화함", "weakness":"자기주장 약함·의존적", "monthly_tip":"이달 양띠는 자신의 의견을 먼저 표현하는 연습이 필요한 시기입니다. 배려만큼 자기 자신도 챙기시기 바랍니다."},
        "monkey": {"kr":"원숭이띠", "trait":"재치 있고 영리하며 새로운 것을 빠르게 습득하는 타입", "strength":"지능·유머·적응력", "weakness":"집중력 분산·변덕", "monthly_tip":"이달 원숭이띠는 아이디어가 풍부한 시기입니다. 그 아이디어를 하나 선택해서 완성하는 것이 이달 핵심입니다."},
        "rooster":{"kr":"닭띠", "trait":"성실하고 꼼꼼하며 완벽을 추구하는 타입", "strength":"성실함·책임감·분석력", "weakness":"완벽주의·비판적", "monthly_tip":"이달 닭띠는 꼼꼼함이 빛나는 시기입니다. 완벽하지 않아도 진행하는 연습이 이달 더 좋은 결과를 만들어 냅니다."},
        "dog":    {"kr":"개띠", "trait":"충성스럽고 정직하며 신뢰를 중시하는 타입", "strength":"충성심·정직함·책임감", "weakness":"걱정 많음·융통성 부족", "monthly_tip":"이달 개띠는 신뢰를 쌓는 행동이 가장 빛나는 시기입니다. 말보다 행동으로 보여주는 것이 이달 가장 강한 전략입니다."},
        "pig":    {"kr":"돼지띠", "trait":"낙천적이고 인정이 많으며 베푸는 것을 좋아하는 타입", "strength":"낙천성·인정·성실함", "weakness":"순진함·지나친 관대함", "monthly_tip":"이달 돼지띠는 나눔이 돌아오는 흐름입니다. 베푸는 것도 좋지만 자신의 여유를 먼저 확인하시기 바랍니다."},
    }
    def _chinese_info_card(en_name):
        info = _CHINESE_INFO.get(en_name)
        if not info: return ""
        return f'''
<div class="card" style="background:linear-gradient(135deg,#fffbeb,#fef9c3);border-left:5px solid #f59e0b">
  <span class="badge" style="background:#fef3c7;color:#92400e">🐾 {info["kr"]} 이달의 특성</span>
  <div style="margin-top:12px">
    <div style="font-size:14px;font-weight:700;color:#92400e;margin-bottom:8px">{info["trait"]}</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">
      <div style="background:#fff;border-radius:8px;padding:10px 12px;border:1px solid #fde68a">
        <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;font-weight:600">강점</div>
        <div style="font-size:13px;font-weight:600;color:#374151">{info["strength"]}</div>
      </div>
      <div style="background:#fff;border-radius:8px;padding:10px 12px;border:1px solid #fde68a">
        <div style="font-size:11px;color:#9ca3af;margin-bottom:4px;font-weight:600">주의</div>
        <div style="font-size:13px;font-weight:600;color:#374151">{info["weakness"]}</div>
      </div>
    </div>
    <div style="background:#fef3c7;border-radius:8px;padding:12px;font-size:14px;
                line-height:1.9;color:#374151;word-break:keep-all">{info["monthly_tip"]}</div>
  </div>
</div>'''


    # ── 운세 지수 이유 문구 풀 ──
    _SCORE_REASON = {
        "total_up":   [
            "조용히 쌓아온 것들이 이달 중순쯤 하나씩 드러나기 시작하는 흐름입니다.",
            "기다리던 연락이나 결과가 이달 안에 들어올 가능성이 있습니다.",
            "먼저 움직이는 쪽이 유리한 달입니다. 타이밍을 놓치지 마시기 바랍니다.",
        ],
        "total_warn": [
            "이달은 새로 시작하기보다 유지하는 것이 더 현명한 달입니다.",
            "무리하게 밀어붙일수록 손해가 커지는 흐름입니다. 속도를 줄이시기 바랍니다.",
        ],
        "money_up":   [
            "충동구매를 줄이면 이달 말에 생각보다 금전이 남는 구조입니다.",
            "미루어두었던 환급·정산을 이달 안에 반드시 챙기시기 바랍니다.",
            "쓰는 것보다 지키는 것이 이달 금전 흐름의 핵심입니다.",
        ],
        "money_warn": [
            "이달 큰 지출 결정은 다음 달로 미루는 것이 훨씬 유리합니다.",
            "투자보다 저축이 맞는 달입니다. 이달만큼은 지키는 것이 버는 것입니다.",
        ],
        "health_up":  [
            "체력이 올라오는 달입니다. 새로운 운동 루틴을 시작하기 좋은 타이밍입니다.",
            "몸이 따라주는 달입니다. 미루어두었던 건강검진이나 운동을 이달 안에 실행하시기 바랍니다.",
            "숙면만 지켜도 이달 에너지가 달라지는 흐름입니다.",
        ],
        "health_warn":[
            "이달 중순 이후 과로 누적에 주의가 필요합니다. 지금부터 무리하지 마시기 바랍니다.",
            "소화와 수면 이 두 가지만 챙겨도 이달을 버티는 데 충분한 기반이 됩니다.",
        ],
        "love_up":    [
            "이미 가까운 사람에게서 감정이 발전할 가능성이 더 높은 달입니다.",
            "먼저 연락하거나 먼저 표현하는 쪽이 유리한 흐름입니다.",
            "말 한마디가 관계의 깊이를 바꾸는 달입니다. 솔직하게 표현해보시기 바랍니다.",
        ],
        "love_warn":  [
            "오해가 생기기 쉬운 달입니다. 말하기 전에 한 번 더 생각하시기 바랍니다.",
            "감정적 반응보다 한 박자 여유를 두는 것이 이달 관계를 지켜줍니다.",
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

  <!-- 운세 지수 % 제거 (근거 없는 수치 — 애드센스 심사 기준) -->

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

  <!-- 띠별 고유 특성 정보 (독창성·정보성 강화) -->
  {_chinese_info_card(c['en'])}

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
    """별자리 12개를 한 포스트에 — 공감형 스토리 카드형"""
    title = f"✨ 오늘의 별자리 운세 전체 {today_str} — 12별자리 한눈에"

    kw = ["별자리운세", "오늘운세", "별자리", today_str,
          "양자리", "황소자리", "쌍둥이자리", "게자리", "사자자리", "처녀자리",
          "천칭자리", "전갈자리", "사수자리", "염소자리", "물병자리", "물고기자리",
          "12별자리운세", "별자리운세전체", "오늘의별자리", "별자리총정리",
          "오늘운세보기", "무료운세", "운세2026"]
    labels = ["별자리운세통합", "운세SNS", "운세", "별자리운세"]

    # 별자리별 공감형 한 줄
    _Z_EMPATHY = {
        "양자리": "시작을 원하지만 실행으로 이어지지 않는 날이 있습니다.",
        "황소자리": "꾸준히 노력하고 있으나 방향에 대한 의문이 생기는 날입니다.",
        "쌍둥이자리": "여러 가지에 관심이 분산되어 완성에 어려움을 느끼는 날입니다.",
        "게자리": "표현해도 달라지지 않을 것 같아 감정을 억누르고 있는 날입니다.",
        "사자자리": "최선을 다하고 있으나 주변의 인정이 느껴지지 않는 날입니다.",
        "처녀자리": "완성도에 대한 부담으로 시작을 미루고 있는 날입니다.",
        "천칭자리": "마음에 걸리는 것이 있으나 표현하기 어려운 날입니다.",
        "전갈자리": "상대방을 지나치게 잘 파악하는 것이 오히려 피로로 이어지는 날입니다.",
        "사수자리": "변화를 원하지만 어디서 시작해야 할지 방향을 찾기 어려운 날입니다.",
        "염소자리": "지속적으로 노력하고 있으나 결과가 아직 보이지 않는 날입니다.",
        "물병자리": "기준에 맞추기도, 그렇다고 벗어나기도 어려운 날입니다.",
        "물고기자리": "타인을 챙기는 데 집중하다 스스로를 돌보지 못한 날들이 쌓인 상태입니다.",
    }

    cards_html = ""
    for z in ZODIACS:
        fortune = zodiac_fortune(z['kr'])
        plain = fortune.replace('<br><br>', ' ').replace('<br>', ' ').strip()
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
        if len(short) < 50:
            short = plain[:150] + ('…' if len(plain) > 150 else '')

        empathy = _Z_EMPATHY.get(z['kr'], '오늘 어떤 하루 보내고 있으세요.')

        cards_html += f"""
<div style="background:#fff;border-radius:14px;box-shadow:0 2px 8px rgba(0,0,0,.06);
            border-left:4px solid #7c3aed;padding:14px;margin-bottom:12px">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
    <span style="font-size:28px;line-height:1">{z['emoji']}</span>
    <div>
      <span style="font-weight:900;font-size:15px;color:#4c1d95">{z['kr']}</span>
      <span style="font-size:11px;color:#9ca3af;margin-left:6px">{z['date']}</span>
    </div>
  </div>
  <p style="font-size:12px;color:#7c3aed;font-style:italic;margin:0 0 6px 0;
            line-height:1.6">💭 {empathy}</p>
  <p style="font-size:13px;color:#374151;line-height:1.75;margin:0">{short}</p>
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
  <div style="background:#eef2ff;border-radius:12px;padding:12px;font-size:12px;color:#666;
              text-align:center;margin-bottom:16px">
    🔮 내 별자리 카드를 클릭하면 오늘의 상세 운세를 확인할 수 있어요
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
    """띠 12개를 한 포스트에 — 공감형 스토리 카드형"""
    title = f"🐾 오늘의 띠별 운세 전체 {today_str} — 12띠 한눈에"

    kw = ["띠운세", "오늘운세", "띠별운세", today_str,
          "쥐띠", "소띠", "호랑이띠", "토끼띠", "용띠", "뱀띠",
          "말띠", "양띠", "원숭이띠", "닭띠", "개띠", "돼지띠",
          "12띠운세", "띠운세전체", "오늘의띠운세", "띠운세총정리",
          "오늘운세보기", "무료운세", "운세2026"]
    labels = ["띠운세통합", "운세SNS", "운세", "띠운세"]

    # 띠별 공감형 한 줄
    _C_EMPATHY = {
        "쥐띠": "정보 수집은 빠르지만 실행으로 이어지지 못하는 날입니다.",
        "소띠": "묵묵히 나아가고 있으나 결과가 아직 보이지 않는 날입니다.",
        "호랑이띠": "기준에 맞춰야 한다는 것을 알면서도 받아들이기 어려운 날입니다.",
        "토끼띠": "여러 가지를 동시에 진행하다 완성에 이르지 못한 느낌이 드는 날입니다.",
        "용띠": "에너지는 충분하지만 방향을 정하지 못하고 있는 날입니다.",
        "뱀띠": "흐름이 보이지만 확신을 갖기 어려운 날입니다.",
        "말띠": "전하고 싶은 말이 있으나 적절한 타이밍을 찾지 못하고 있는 날입니다.",
        "양띠": "타인을 배려하는 데 집중하다 스스로가 뒷전이 된 날들이 쌓인 상태입니다.",
        "원숭이띠": "성과를 보여주고 싶지만 타이밍을 잡지 못하고 있는 날입니다.",
        "닭띠": "충분히 준비되지 않았다는 판단으로 실행을 계속 미루고 있는 날입니다.",
        "개띠": "오래 참아온 말이 있으나 꺼내기 어려운 상황인 날입니다.",
        "돼지띠": "예민해진 감각이 부담으로 작용하는 날입니다.",
    }

    cards_html = ""
    for c in CHINESE:
        years_filtered = [y for y in c['year'].split(',') if 1940 <= int(y) <= 2030][:3]
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

        empathy = _C_EMPATHY.get(c['kr'], '오늘 어떤 하루 보내고 있으세요.')
        years_str = "·".join(f"{y}년생" for y in years_filtered)

        cards_html += f"""
<div style="background:#fff;border-radius:14px;box-shadow:0 2px 8px rgba(0,0,0,.06);
            border-left:4px solid #f59e0b;padding:14px;margin-bottom:12px">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
    <span style="font-size:28px;line-height:1">{c['emoji']}</span>
    <div>
      <span style="font-weight:900;font-size:15px;color:#92400e">{c['kr']}</span>
      <span style="font-size:11px;color:#9ca3af;margin-left:6px">{years_str}</span>
    </div>
  </div>
  <p style="font-size:12px;color:#d97706;font-style:italic;margin:0 0 6px 0;
            line-height:1.6">💭 {empathy}</p>
  <p style="font-size:13px;color:#374151;line-height:1.75;margin:0">{short}</p>
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
  <div style="background:#fef3c7;border-radius:12px;padding:12px;font-size:12px;color:#666;
              text-align:center;margin-bottom:16px">
    🐾 내 띠 카드를 클릭하면 출생연도별 상세 운세를 확인할 수 있어요
  </div>
  <div class="card"><span class="badge">🔍 관련 키워드</span>
    <div class="tag-cloud">{''.join(f'<span class="tag">{k}</span>' for k in kw)}</div>
  </div>
  {site_link()}
  <div class="meta">※ 재미로 보는 운세 콘텐츠 · 매일 업데이트</div>
</div>"""

    return title, content_html, labels

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
     "손이 안 가는 날이 있어요. 그게 두려움이 아니에요. "
     "에너지가 너무 커서 어디서 터뜨릴지 못 고른 거거든요. "
     "오늘 용띠의 추진력이 양자리의 그 등을 밀어주는 날입니다."),
    ("황소자리", "뱀띠",    "결실",
     "열심히 하고 있는데 이게 맞는 방향인지 흔들리는 날이 있어요. "
     "뱀띠의 날카로운 직관이 오늘 황소자리의 그 확신을 다시 세워줍니다."),
    ("쌍둥이자리","토끼띠",  "연결",
     "이것도 저것도 신경 쓰이고 결국 아무것도 못 끝낸 느낌. 그 날이에요. "
     "토끼띠가 오늘 쌍둥이자리에게 '그거 하나만 해'라고 조용히 말해줍니다."),
    ("게자리",   "말띠",    "용기",
     "말해봤자 뭐가 달라지나 싶어서 그냥 넘기는 날들이 쌓이고 있지 않으세요. "
     "오늘 말띠의 직진 에너지가 게자리의 그 망설임을 걷어내줍니다."),
    ("사자자리", "원숭이띠", "존재감",
     "열심히 하는 건 나도 아는데 아무도 몰라주는 것 같은 날이에요. "
     "원숭이띠의 타이밍 감각이 오늘 사자자리의 존재감을 드러내는 방법을 알려줍니다."),
    ("처녀자리", "닭띠",    "완성",
     "요즘 뭔가 계속 미루게 되는 것이 있지 않으세요. 완벽하지 않아서. "
     "닭띠의 실행력이 오늘 처녀자리의 완벽주의를 부드럽게 풀어줍니다."),
    ("천칭자리", "개띠",    "관계",
     "말로 꺼내기엔 애매하고 그냥 넘기기엔 걸리는 게 마음에 남아 있지 않으세요. "
     "오늘 개띠의 솔직함이 천칭자리가 참아왔던 말을 꺼낼 수 있는 분위기를 만들어줍니다."),
    ("전갈자리", "돼지띠",  "직관",
     "사람을 너무 잘 읽어서 오히려 지치는 날이 있어요. "
     "돼지띠의 너그러움이 오늘 전갈자리의 날 선 감각을 부드럽게 감싸줍니다."),
    ("사수자리", "쥐띠",    "전환",
     "뭔가 바꾸고 싶은데 어디서 시작해야 할지 모르는 그 답답함이에요. "
     "쥐띠가 오늘 사수자리의 변화 에너지에 방향을 달아줍니다."),
    ("염소자리", "소띠",    "신뢰",
     "결과가 안 보여서 이게 맞나 싶은 날, 주변이 먼저 나아가는 것 같아 조바심 나는 날. "
     "오늘 소띠의 뚝심이 염소자리 옆을 함께 걷습니다. 눈에 안 보여도 분명히 쌓이고 있어요."),
    ("물병자리", "호랑이띠", "다름",
     "맞춰야 할 것 같은데 맞추기가 싫고, 그렇다고 혼자 튀는 것 같아서 눌러두는 아이디어가 있지 않으세요. "
     "호랑이띠의 배짱이 오늘 물병자리에게 '그냥 해도 돼'라는 신호가 됩니다."),
    ("물고기자리","양띠",   "쉬어가기",
     "남 챙기다 정작 나는 못 챙긴 날들이 쌓여서 오늘 유독 무거운 느낌이 드나요. "
     "양띠의 조용한 온기가 오늘 물고기자리에게 쉬어도 된다는 허락이 됩니다."),
]


_OMNIBUS_OPENINGS = [
    "별자리와 띠가 같은 날 위에 놓일 때, 각각의 이야기가 달라집니다. "
    "오늘 두 흐름이 어떻게 교차하는지 살펴보시기 바랍니다. "
    "본인의 별자리와 띠 조합을 찾아 천천히 읽어보시기 바랍니다.",

    "오늘 하루의 흐름을 별자리와 띠가 각각 다른 시각으로 분석하고 있습니다. "
    "두 시각이 겹치는 지점에서 예상치 못한 답이 나오는 날입니다. "
    "읽는 과정에서 공감이 되는 부분이 있다면 그것을 오늘의 기준으로 삼으시기 바랍니다.",

    "운세가 모든 상황에 정확히 들어맞지는 않습니다. "
    "그러나 오늘 이 글이 현재 상황을 돌아보는 계기가 된다면, 그것으로 충분한 역할을 한 것입니다. "
    "별자리와 띠가 오늘을 어떻게 해석하는지 함께 살펴보겠습니다.",

    "오늘 별자리와 띠의 에너지가 교차하는 구간이 존재합니다. "
    "그 구간에서의 행동이 하루 전체의 흐름을 결정하기도 합니다. "
    "본인의 조합을 찾아 오늘의 방향을 확인하시기 바랍니다.",

    "별자리는 감각을 분석하고, 띠는 흐름을 읽습니다. "
    "오늘은 그 두 가지가 교차하는 지점에서 오늘의 방향을 제시합니다. "
    "읽은 후 마음에 남는 것이 있다면 그것이 오늘 가장 필요한 방향입니다.",
]

_OMNIBUS_CLOSINGS = [
    "오늘 읽은 내용 중 한 가지를 선택하여 실천에 옮기시기 바랍니다. "
    "모든 내용을 기억하려 하면 오히려 남는 것이 없습니다. "
    "가장 마음에 남는 한 가지로 오늘 하루를 충실히 마무리하시기 바랍니다.",

    "운세는 미래를 단정 짓는 것이 아닙니다. "
    "현재 느끼고 있는 감각은 개인만의 경험이 아닙니다. "
    "오늘 이 글이 현재 상황을 돌아보는 계기가 되었다면 충분한 역할을 한 것입니다.",

    "끝까지 읽어주신 것에 감사드립니다. "
    "읽은 후 무언가 하나라도 달라진 것이 있다면 오늘 이 글은 제 역할을 다한 것입니다.",

    "좋은 흐름은 파악한 사람에게 먼저 기회로 다가옵니다. "
    "오늘 그 흐름을 확인하였으니 이제 실천할 차례입니다. "
    "크게 시작하지 않아도 됩니다. 작은 한 가지가 오늘의 시작입니다.",

    "오늘 어떤 시간에 무엇을 했는지가 내일의 흐름으로 이어집니다. "
    "이 글이 오늘의 선택에 조금이라도 도움이 되었기를 바랍니다.",

    "순탄한 날이든 힘든 날이든, 오늘 여기까지 온 것 자체가 이미 충분히 잘 해낸 것입니다. "
    "이러한 감각은 혼자만 경험하는 것이 아닙니다. 누구나 이런 과정을 거치며 살아갑니다.",

    "오늘 읽으면서 공감이 되는 부분이 있었다면, 그 감각이 맞습니다. "
    "별자리든 띠든, 결국 오늘 이 이야기는 지금 이 순간의 당신에 관한 것입니다.",
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
     "why": "하루의 흐름이 가장 안정적으로 유지되는 시간대입니다. 오전의 집중력과 오후의 여유가 겹치는 구간입니다.",
     "action": "설득이나 협상이 필요한 대화는 이 시간에 꺼내세요. 상대방도 이 구간이 비교적 열려 있어요.",
     "goal": "오늘 가장 중요한 연락 하나, 이 시간 안에 보내세요."},
    {"label": "오후 1시~3시",
     "why": "점심 후 에너지가 재충전되면서 오후 집중력이 올라오는 시간입니다. 창의적인 판단이 이 시간에 가장 잘 나옵니다.",
     "action": "의외로 여기서 답이 나옵니다. 막혀 있던 문제를 이 시간에 다시 꺼내보세요.",
     "goal": "오후 1시에 오늘 남은 것 중 가장 걸리는 것 하나만 골라 집중하세요."},
    {"label": "오후 2시~4시",
     "why": "업무 추진력이 다시 올라오는 시간대입니다. 사람들의 집중력이 돌아오고 결정이 빠르게 이루어지는 구간입니다.",
     "action": "타이밍이 결과를 바꿉니다. 부탁이나 제안이 필요한 대화는 지금이 적절한 시간입니다.",
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
        "insight": "오늘은 빠르게 움직이는 것보다 타이밍을 파악하는 것이 유리한 하루입니다.",
        "bridge":  "별자리와 띠는 서로 다른 언어를 사용하지만, 오늘은 같은 이야기를 전달하고 있습니다.",
        "action":  "미루어 두었던 것 하나를 시작하시기 바랍니다.",
    },
    # 2일
    {
        "insight": "오늘은 크게 바꾸는 날이 아닙니다. 작은 것 하나를 제대로 선택하는 날입니다.",
        "bridge":  "별자리는 감각으로 읽고, 띠는 흐름으로 읽습니다. 오늘 그 둘이 같은 방향을 가리키고 있습니다.",
        "action":  "현재 마음에 걸리는 것이 오늘 해야 할 것입니다.",
    },
    # 3일
    {
        "insight": "억지로 밀어붙이는 것보다 흐름에 올라타는 것이 더 멀리 갑니다. 오늘이 그러한 날입니다.",
        "bridge":  "별자리와 띠가 오늘 같은 방향을 제시하고 있습니다. 받아들일 준비가 되어 있다면 이미 절반은 된 것입니다.",
        "action":  "오늘 하루, 한 가지를 제대로 완수하시기 바랍니다.",
    },
    # 4일
    {
        "insight": "오늘은 많이 하는 것보다 잘 선택하는 것이 기억에 남는 하루가 될 것입니다.",
        "bridge":  "별자리와 띠가 각각 다른 방향에서 출발하였지만, 오늘은 같은 지점에서 만나고 있습니다.",
        "action":  "오래 묵혀두었던 것 하나를 오늘 꺼내 보시기 바랍니다.",
    },
    # 5일
    {
        "insight": "오늘 주변의 흐름이 조용히 바뀌고 있습니다. 눈에 잘 띄지 않는 방향에서 변화가 시작됩니다.",
        "bridge":  "별자리가 감지한 것을 띠가 확인해주고 있습니다. 오늘의 방향은 하나입니다.",
        "action":  "지금 이 순간, 가장 먼저 떠오른 것을 실행하시기 바랍니다.",
    },
    # 6일
    {
        "insight": "서두르면 놓치는 날이 있습니다. 오늘이 그러한 날일 수 있으므로 한 박자 늦게 움직이시기 바랍니다.",
        "bridge":  "오늘 별자리와 띠가 보내는 신호는 동일합니다. 속도보다 방향이 중요한 날입니다.",
        "action":  "잠시 멈추고, 현재 가장 걸리는 것 하나를 선택하시기 바랍니다.",
    },
    # 7일
    {
        "insight": "오늘은 준비된 사람에게 기회가 열리는 날입니다. 그 기회는 요란하지 않게 찾아옵니다.",
        "bridge":  "별자리와 띠가 오늘 같은 방향의 에너지를 보내고 있습니다. 그 흐름을 활용하시기 바랍니다.",
        "action":  "준비해 두었던 것을 오늘 한 발 내딛어 보시기 바랍니다.",
    },
    # 8일
    {
        "insight": "오늘은 결과보다 방향을 설정하는 날입니다. 방향이 맞으면 속도는 이후에 따라옵니다.",
        "bridge":  "별자리가 오늘 향하는 방향과 띠가 움직이는 방향이 오늘 정확히 일치합니다.",
        "action":  "완성이 아니라 방향 하나만 정하시기 바랍니다.",
    },
    # 9일
    {
        "insight": "오늘은 말보다 행동이 더 멀리 닿는 날입니다. 설명 없이 움직이는 것이 유리합니다.",
        "bridge":  "별자리와 띠, 둘 다 오늘 같은 곳에 에너지를 집중하고 있습니다.",
        "action":  "말하려던 것을 오늘 실행으로 옮겨 보시기 바랍니다.",
    },
    # 10일
    {
        "insight": "오늘은 새로 시작하는 것보다 이어가는 것에 더 큰 힘이 있는 날입니다.",
        "bridge":  "별자리의 감각과 띠의 뚝심이 오늘 같은 리듬으로 움직이고 있습니다.",
        "action":  "어제 하다 멈춘 것을 오늘 다시 꺼내 보시기 바랍니다.",
    },
    # 11일
    {
        "insight": "오늘은 혼자 안고 있던 것을 한 사람에게라도 꺼내는 것이 더 가볍게 만들어 줍니다.",
        "bridge":  "별자리는 감정의 흐름을 읽고, 띠는 관계의 흐름을 읽습니다. 오늘 둘이 같은 방향을 가리키고 있습니다.",
        "action":  "오늘 연락하고 싶었던 사람에게 짧게라도 먼저 연락하시기 바랍니다.",
    },
    # 12일
    {
        "insight": "오늘은 완벽하게 하려다 아무것도 못 하는 것보다, 작게라도 완성하는 것이 훨씬 낫습니다.",
        "bridge":  "별자리와 띠가 오늘 완성을 향해 함께 나아가고 있습니다.",
        "action":  "80% 완성 단계에서 내보내시기 바랍니다. 나머지는 다음 단계에서 보완할 수 있습니다.",
    },
    # 13일
    {
        "insight": "오늘은 기다리는 것보다 먼저 움직이는 쪽에 기회가 있는 날입니다.",
        "bridge":  "별자리와 띠, 둘 다 오늘 먼저 행동할 것을 권하고 있습니다.",
        "action":  "기다리던 것을 오늘 먼저 꺼내 보시기 바랍니다.",
    },
    # 14일
    {
        "insight": "오늘은 감정이 앞서는 날입니다. 판단은 하루 뒤에 해도 늦지 않습니다.",
        "bridge":  "별자리는 오늘 감정을 분석하고, 띠는 그 감정을 어떻게 활용할지 알고 있습니다.",
        "action":  "오늘 느낀 것을 어딘가에 기록해 두시기 바랍니다.",
    },
    # 15일
    {
        "insight": "오늘은 에너지가 고르게 퍼지는 날입니다. 한 곳에 집중하기보다 여러 곳에 적절히 배분하는 것이 효과적입니다.",
        "bridge":  "별자리와 띠가 오늘 같은 템포로 움직이고 있습니다. 무리하지 않아도 되는 날입니다.",
        "action":  "오늘은 나누어서 하시기 바랍니다. 한꺼번에 하지 않아도 됩니다.",
    },
    # 16일
    {
        "insight": "오늘은 결정보다 관찰이 더 유리한 날입니다. 조금 더 살펴본 후 움직이는 것이 맞습니다.",
        "bridge":  "별자리와 띠, 둘 다 오늘 관망하는 것을 권하고 있습니다.",
        "action":  "결정은 내일로 미루고, 오늘은 관찰하는 날로 활용하시기 바랍니다.",
    },
    # 17일
    {
        "insight": "오늘은 자신을 위한 것을 실천하기 좋은 날입니다. 타인을 위한 일은 잠시 내려놓아도 괜찮습니다.",
        "bridge":  "별자리와 띠가 오늘 내면을 향하고 있습니다. 외부가 아닌 내면에 집중할 때입니다.",
        "action":  "오늘 하루, 자신을 위한 것 하나를 먼저 실천하시기 바랍니다.",
    },
    # 18일
    {
        "insight": "오늘은 작은 디테일이 큰 차이를 만드는 날입니다. 사소하다고 지나치지 마시기 바랍니다.",
        "bridge":  "별자리의 예민함과 띠의 꼼꼼함이 오늘 같은 방향을 보고 있습니다.",
        "action":  "오늘 그냥 넘기려던 것을 한 번 더 확인하시기 바랍니다.",
    },
    # 19일
    {
        "insight": "오늘은 혼자 생각하는 것보다 한 사람에게 이야기하는 것이 더 빨리 해결되는 날입니다.",
        "bridge":  "별자리는 오늘 연결을 향하고, 띠는 그 연결을 이어가는 방법을 알고 있습니다.",
        "action":  "지금 머릿속에 있는 것을 한 사람에게 꺼내 보시기 바랍니다.",
    },
    # 20일
    {
        "insight": "오늘은 에너지가 낮은 날일 수 있습니다. 억지로 끌어올리려 하지 말고 자연스러운 흐름에 맡기는 것이 낫습니다.",
        "bridge":  "별자리와 띠, 둘 다 오늘 쉬어도 된다고 말하고 있습니다.",
        "action":  "오늘은 많이 하지 않아도 됩니다. 한 가지만 하고 쉬시기 바랍니다.",
    },
    # 21일
    {
        "insight": "오늘은 계획대로 되지 않는 것처럼 보일 수 있습니다. 그 빈자리에서 예상 밖의 것이 들어옵니다.",
        "bridge":  "별자리와 띠가 오늘 계획 밖의 방향을 가리키고 있습니다. 그쪽이 오늘의 진짜 흐름입니다.",
        "action":  "오늘 계획이 틀어지면, 그 방향을 따라가 보시기 바랍니다.",
    },
    # 22일
    {
        "insight": "오늘은 감사한 것 하나를 기억하는 것만으로 하루 전체의 무게가 달라지는 날입니다.",
        "bridge":  "별자리와 띠가 오늘 현재 가진 것에 집중하라고 말하고 있습니다.",
        "action":  "오늘 잘 된 것 하나를 자기 전에 떠올려 보시기 바랍니다.",
    },
    # 23일
    {
        "insight": "오늘은 설명하지 않아도 되는 날입니다. 감각이 맞다면 그대로 움직여도 됩니다.",
        "bridge":  "별자리의 직관과 띠의 감각이 오늘 같은 방향을 향하고 있습니다.",
        "action":  "설명하지 말고, 오늘은 바로 실행하시기 바랍니다.",
    },
    # 24일
    {
        "insight": "오늘은 오래된 것을 다시 꺼내기 좋은 날입니다. 이전에 포기했던 것이 오늘 다르게 보일 수 있습니다.",
        "bridge":  "별자리와 띠가 오늘 돌아보는 것을 권하고 있습니다. 과거를 돌아보는 것이 앞을 여는 날입니다.",
        "action":  "이전에 포기했던 것을 오늘 다시 한 번 열어 보시기 바랍니다.",
    },
    # 25일
    {
        "insight": "오늘은 에너지가 올라오는 날입니다. 그 에너지를 어디에 사용하느냐가 오늘의 핵심입니다.",
        "bridge":  "별자리와 띠 둘 다 오늘 에너지가 모이고 있습니다. 분산되게 두면 아까운 날입니다.",
        "action":  "오늘 에너지를 한 곳에만 집중하시기 바랍니다. 한 곳에 집중하는 것만으로 오늘 하루를 충실히 쓴 것입니다.",
    },
    # 26일
    {
        "insight": "오늘은 타인에게 인정받으려 하기보다 스스로 인정하는 것이 더 힘이 되는 날입니다.",
        "bridge":  "별자리와 띠가 오늘 내면에서 답을 찾으라고 말하고 있습니다.",
        "action":  "오늘 잘 한 것은 타인이 아닌 스스로가 먼저 인정해도 됩니다.",
    },
    # 27일
    {
        "insight": "오늘은 한 번에 모두 해결하려는 마음을 내려놓을수록 실제로 더 많이 이루어지는 날입니다.",
        "bridge":  "별자리는 오늘 줄이는 것을 말하고, 띠는 집중을 말합니다. 같은 방향입니다.",
        "action":  "오늘 목록에서 하나를 지우시기 바랍니다. 그것이 오늘의 진짜 시작입니다.",
    },
    # 28일
    {
        "insight": "오늘은 누군가의 말 한마디가 예상보다 오래 남는 날입니다. 좋은 방향으로 기억될 말을 먼저 전하시기 바랍니다.",
        "bridge":  "별자리와 띠가 오늘 말의 무게에 대해 같은 이야기를 하고 있습니다.",
        "action":  "오늘 하고 싶었던 말을 생각나는 사람에게 짧게 전하시기 바랍니다.",
    },
    # 29일
    {
        "insight": "오늘은 기대와 다르게 흘러도 그것이 더 나은 방향일 수 있는 날입니다.",
        "bridge":  "별자리가 예상한 것을 띠가 다른 각도로 열어주는 날입니다. 둘이 함께일 때 더 잘 보입니다.",
        "action":  "계획대로 되지 않았다면, 그 방향에서 새로운 것을 찾아보시기 바랍니다.",
    },
    # 30일
    {
        "insight": "오늘은 마무리가 시작보다 중요한 날입니다. 완성하는 것이 다음을 여는 날입니다.",
        "bridge":  "별자리와 띠가 오늘 마무리를 향해 함께 나아가고 있습니다.",
        "action":  "오늘 하나를 완성하시기 바랍니다. 새로운 시작은 내일 해도 됩니다.",
    },
    # 31일
    {
        "insight": "오늘은 흐름을 거스르지 않는 사람이 가장 멀리 나아가는 날입니다.",
        "bridge":  "별자리와 띠가 오늘 같은 물결 위에 있습니다. 그 흐름을 활용하시기 바랍니다.",
        "action":  "억지로 만들려 하지 말고, 오늘 자연스럽게 찾아오는 것을 잡으시기 바랍니다.",
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
    별자리×띠 스토리텔링 브릿지 — 골든타임·연락시간 제거
    별자리 특성 + 띠 특성 + 궁합 + 행동 제안 중심
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
        story = f"{zb}와 {cb}, 오늘 같은 흐름 위에 서 있습니다."

    def hl_warn(t):   return f"<b style='color:#dc2626'>{t}</b>"
    def hl_item(t):   return f"<b style='color:#059669'>{t}</b>"
    def hl_compat(t): return f"<b style='color:#7c3aed'>{t}</b>"

    # 궁합 산문
    compat_prose = (
        f"오늘 {hl_compat(z_compatible)}이나 {hl_compat(c_best)}와 나누는 대화가 "
        f"의외로 좋은 방향을 열어줄 수 있습니다. "
        f"반대로 {hl_warn(c_avoid)}와 감정이 섞인 이야기는 오늘 저녁 이후로 미루는 것이 좋습니다."
    )

    # 행동 제안 산문
    _goal_variants = [
        f"오늘은 이것 하나만 실천해보시기 바랍니다.",
        f"의외로 이 방향에서 답이 나옵니다.",
        f"지금은 선택하는 때입니다.",
        f"오늘 하루 이 하나만 챙기면 충분합니다.",
        f"복잡하게 생각하지 않아도 됩니다.",
        f"오늘의 방향이 여기에 있습니다.",
    ]
    goal_prose = _goal_variants[idx % len(_goal_variants)]

    # 피해야 할 것 산문
    _avoid_variants = [
        (f"오늘 {hl_warn(avoid_action)}은 잠시 멈추는 편이 유리합니다. "
         f"억지로 밀어붙이는 날이 아닙니다."),
        (f"오늘 {hl_warn(avoid_action)}은 내려놓아도 됩니다. "
         f"오늘은 다른 쪽에 에너지를 쓰는 것이 맞습니다."),
        (f"{hl_warn(avoid_action)}은 오늘 굳이 건드리지 않아도 되는 것입니다. "
         f"비워두는 것도 오늘의 선택입니다."),
        (f"오늘 {hl_warn(avoid_action)} 쪽으로 힘을 쏟으면 뒷맛이 남습니다. "
         f"지금은 나머지에 집중할 타이밍입니다."),
    ]
    avoid_prose = _avoid_variants[idx % len(_avoid_variants)]

    # ── 12가지 산문 패턴 (골든타임·연락시간 제거) ──
    patterns = [
        # 0: 스토리 → 별자리 코어 → 행동
        f"{story}<br><br>"
        f"오늘 {zb}의 흐름을 보면, {z_core} "
        f"{goal_prose}",

        # 1: 스토리 → 띠 코어 → 행동
        f"{story}<br><br>"
        f"오늘 {cb}가 전하는 한 마디입니다. {c_core} "
        f"{goal_prose}",

        # 2: 띠 코어 → 별자리 연결 → 궁합
        f"오늘 {cb}의 에너지가 이런 방향을 가리키고 있습니다. {c_core}<br><br>"
        f"{zb}인 분들에게 그 에너지가 닿으면, {story}<br><br>"
        f"{compat_prose}",

        # 3: 테마 → 스토리 → 별자리 코어 → 궁합
        f"오늘의 테마는 {tb}입니다. {zb}와 {cb}가 같은 흐름 위에 서 있는 날입니다.<br><br>"
        f"{story}<br><br>"
        f"오늘 {zb}의 흐름입니다. {z_core} "
        f"{compat_prose}",

        # 4: 스토리 → 피해야 할 것 → 띠 코어
        f"{story}<br><br>"
        f"{avoid_prose}<br><br>"
        f"대신 {cb}가 오늘 이런 방향을 가리키고 있습니다. {c_core}",

        # 5: 스토리 → 별자리↔띠 코어 교차
        f"{story}<br><br>"
        f"오늘 {zb}의 에너지: {z_core}<br><br>"
        f"오늘 {cb}의 에너지: {c_core} "
        f"{goal_prose}",

        # 6: 띠 코어 → 별자리 받는 방식 → 행동
        f"오늘 {cb}의 에너지가 이렇게 흐르고 있습니다. {c_core}<br><br>"
        f"그 에너지를 {zb}는 이렇게 받을 수 있습니다. {z_core}<br><br>"
        f"{goal_prose}",

        # 7: 스토리 → 궁합
        f"{story}<br><br>"
        f"{compat_prose}",

        # 8: 별자리 코어 → 스토리 → 행동
        f"오늘 {zb}의 흐름이 이렇게 보입니다. {z_core}<br><br>"
        f"그 흐름에서 {cb}의 에너지가 이렇게 작용합니다. {story}<br><br>"
        f"{goal_prose}",

        # 9: 스토리 → 띠 코어 → 피해야 할 것
        f"{story}<br><br>"
        f"오늘 {cb}가 건네는 말도 같은 방향입니다. {c_core}<br><br>"
        f"{avoid_prose}",

        # 10: 긍정 선언 → 스토리 → 코어 교차
        f"오늘 {zb}와 {cb}의 흐름이 좋은 방향으로 맞닿아 있습니다.<br><br>"
        f"{story}<br><br>"
        f"{zb}의 오늘: {z_core} {cb}의 오늘: {c_core}",

        # 11: 마무리형 → 스토리 → 궁합
        f"{zb}와 {cb}인 분들께 오늘의 이야기를 전합니다.<br><br>"
        f"{story}<br><br>"
        f"{compat_prose}",
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
        f"🌙 별과띠가만나는시간 {today_str} "
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
            f'<p style="margin:0 0 1.2em 0;text-indent:0">'
            f'<span style="font-size:12px;color:#c4b5fd;margin-right:3px;vertical-align:middle">'
            f'{ZODIACS[[z["kr"] for z in ZODIACS].index(z_kr)]["emoji"] if z_kr in [z["kr"] for z in ZODIACS] else "✦"}'
            f'</span>'
            f'{para}</p>'
        )

    # 6조합씩 2장으로 분할
    paras_1 = paragraphs[0:6]   # 양자리·황소자리·쌍둥이자리·게자리·사자자리·처녀자리
    paras_2 = paragraphs[6:12]  # 천칭자리·전갈자리·사수자리·염소자리·물병자리·물고기자리

    # 각 파트 첫 문단 드롭캡
    for paras in [paras_1, paras_2]:
        paras[0] = paras[0].replace(
            '<p style="margin:0 0 1.9em 0;text-indent:0">',
            '<p style="margin:0 0 1.9em 0;text-indent:0" class="drop-cap-p">',
            1
        )

    story_1 = "\n".join(paras_1)
    story_2 = "\n".join(paras_2)

    # 각 파트 별자리 이름
    z_names = [z['kr'] for z in ZODIACS]
    part_names = [
        "·".join(z_names[0:6]),   # 양자리~처녀자리
        "·".join(z_names[6:12]),  # 천칭자리~물고기자리
    ]
    part_labels = ["첫 번째 이야기", "마지막 이야기"]

    date_slug = today_str.replace(' ','').replace('년','').replace('월','').replace('일','')
    card_ids = [f"omnibus-{i+1}-{date_slug}" for i in range(2)]


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

    def _novel_card(card_id, part_label, part_name, story_html,
                    show_opening=False, show_ending=False):
        opening_html = f'<p class="novel-opening">{opening}</p>' if show_opening else ''
        ending_html = f"""
    <div style="
      margin: 2.8rem 0 0 0;
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 2px 16px rgba(91,33,182,0.08);
    ">
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
      <div style="
        background: linear-gradient(160deg, #faf5ff 0%, #fdf4ff 100%);
        padding: 1.6rem 1.6rem 0.4rem 1.6rem;
      ">
        <p style="
          font-size: 15.5px;
          line-height: 2.05;
          color: #374151;
          margin: 0 0 1.1rem 0;
          word-break: keep-all;
          font-weight: 500;
        ">{ending_insight}</p>
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
    <div class="novel-footer">{closing}</div>
""" if show_ending else ''

        return f"""
  <div class="novel-page" id="{card_id}">
    <div class="novel-date">{today_str} · {season}</div>
    <h1 class="novel-title">🌙 별과띠가만나는시간</h1>
    <p class="novel-subtitle">오늘 하늘이 당신에게 건네는 이야기</p>
    <div class="novel-part">{part_label} · {part_name}</div>
    <div class="novel-rule">&middot; &middot; &middot;</div>
    {opening_html}
    <div class="novel-body">
{story_html}
    </div>
    <div class="novel-rule">&middot; &middot; &middot;</div>
    {ending_html}
  </div>
  <button id="savebtn-{card_id}" class="save-btn" onclick="saveFortuneCard('{card_id}', '별과띠가만나는시간_{part_label}_{today_str}')">📸 이미지 저장</button>
  <div style="margin:24px 0 8px 0;border-top:1px dashed #e5e7eb;padding-top:24px"></div>
"""

    content_html = f"""{style()}
<style>
.novel-page {{
  max-width: 660px;
  margin: 0 auto;
  padding: 0 4px;
  font-family: 'Noto Serif KR', Georgia, serif;
}}
.novel-date {{
  font-size: 11px;
  letter-spacing: 0.12em;
  color: #9ca3af;
  text-align: center;
  margin-bottom: 0.6rem;
}}
.novel-title {{
  font-size: 19px;
  font-weight: 600;
  color: #1f2937;
  text-align: center;
  line-height: 1.45;
  margin-bottom: 0.2rem;
}}
.novel-subtitle {{
  font-size: 12px;
  text-align: center;
  color: #9ca3af;
  margin-bottom: 1.2rem;
}}
.novel-part {{
  font-size: 10px;
  text-align: center;
  color: #c4b5fd;
  letter-spacing: 0.1em;
  margin-bottom: 0.7rem;
  font-weight: 600;
}}
.novel-rule {{
  text-align: center;
  color: #d1d5db;
  letter-spacing: 0.4em;
  margin: 1.1rem 0;
  font-size: 12px;
}}
.novel-body {{
  font-size: 14.5px;
  line-height: 1.95;
  color: #374151;
  word-break: keep-all;
}}
.novel-opening {{
  font-size: 14px;
  line-height: 1.85;
  color: #6b7280;
  margin-bottom: 1rem;
  font-style: italic;
  padding: 0 2px;
  word-break: keep-all;
}}
.novel-footer {{
  margin-top: 1.2rem;
  padding-top: 1.2rem;
  border-top: 1px solid #f3f4f6;
  font-size: 13px;
  color: #9ca3af;
  text-align: center;
  line-height: 1.9;
  font-style: italic;
}}
</style>

<div class="wrap">

{_novel_card(card_ids[0], part_labels[0], part_names[0], story_1, show_opening=True)}
{_novel_card(card_ids[1], part_labels[1], part_names[1], story_2, show_ending=True)}

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
