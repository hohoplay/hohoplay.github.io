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
                  "점심 후 무기력감이 올 수 있습니다. 민트 계열 음료나 소품을 활용해 오후 에너지를 끌어올려 보세요."),
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
                  "오늘 마음을 리셋하고 싶은 날이라면 화이트 소품으로 주변을 정리해 보세요. 깔끔한 환경이 새로운 에너지를 불러옵니다."),
    "딥블루":    ("집중과 냉철한 판단","직장·금전 결정운", 15,
                  "네이비 지갑·볼펜·파일·넥타이",
                  "중요한 결정을 내려야 하는 날 딥블루 계열이 냉철한 판단력을 도와줍니다. 계약이나 협상 자리에 특히 추천합니다."),
    "오렌지":    ("열정과 도전",       "활동·창업·도전운", 16,
                  "오렌지 계열 파우치·케이스·스티커·양말",
                  "새로운 도전을 시작하기에 좋은 날입니다. 오렌지 소품이 행동력과 추진력을 높여주는 에너지를 더해줍니다."),
    "그린":      ("성장과 치유",       "건강·금전 성장운", 13,
                  "초록색 화분·텀블러·노트·에코백",
                  "자연의 기운이 필요한 날입니다. 작은 화분 하나를 책상에 두거나 그린 계열 소품을 활용해 보세요."),
}

# 행운 아이템 → 사용법 매핑 (아이템 키워드 기반 매칭)
ITEM_USAGE = [
    # (키워드 리스트, 사용법 설명)
    (["수정","크리스탈","돌","원석"],
     "오늘 수정은 왼손에 쥐거나 주머니에 넣어 다니세요. 부정적인 에너지를 흡수하고 집중력을 높여주는 효과가 있습니다."),
    (["동전","코인"],
     "오늘 동전을 지갑 깊숙이 넣어 두세요. '돈이 들어오는 자리'를 비워두지 않는다는 상징으로 금전운을 활성화합니다."),
    (["꽃","꽃잎","식물","화분"],
     "오늘 꽃이나 식물을 곁에 두세요. 생명 에너지가 긍정적인 기운을 불러오고 공간의 분위기를 밝게 바꿔줍니다."),
    (["반지","팔찌","목걸이","귀걸이","주얼리"],
     "오늘 이 아이템을 착용할 때 잠깐 눈을 감고 '오늘 하루 좋은 일이 가득하길'이라고 마음속으로 빌어보세요. 의도를 담는 것이 중요합니다."),
    (["향초","향","아로마"],
     "아침 루틴에 5분간 이 향을 사용해 보세요. 후각이 뇌를 자극해 하루 전체의 에너지 흐름을 긍정적으로 세팅하는 효과가 있습니다."),
    (["거울","미러"],
     "오늘 외출 전 거울을 보며 자신에게 긍정적인 말을 한마디 건네보세요. 자기 확신이 오늘 하루의 운세를 실제로 끌어올립니다."),
    (["책","노트","수첩","다이어리"],
     "오늘 떠오르는 아이디어나 감정을 짧게라도 기록해 두세요. 이 아이템이 오늘 당신의 생각을 현실로 연결하는 통로가 됩니다."),
    (["열쇠","키"],
     "열쇠는 '문을 여는 힘'의 상징입니다. 오늘 막혀 있던 문제의 해결책이 의외의 곳에서 나타날 수 있습니다. 열린 마음으로 하루를 시작하세요."),
    (["조약돌","돌","스톤"],
     "주머니나 가방에 넣고 다니다가 힘들 때 손으로 쥐어보세요. 자연의 안정 에너지가 마음을 차분하게 만들어줍니다."),
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
            f"오늘의 행운 색상 <b>'{color_name}'</b>은 {effect_area}을 높여주는 컬러입니다. "
            f"{items}을 착용하거나 곁에 두면 {fortune_type} 지수가 최대 <b>{boost_pct}% 상승</b>하는 효과를 기대할 수 있습니다. "
            f"{usage}"
        )
    return f"오늘의 행운 색상 '{color_name}'을 소품이나 의류에 활용해 보세요. 긍정적인 에너지를 끌어당기는 데 도움이 됩니다."

def get_item_guide(item_name):
    """행운 아이템 → 활용법 문자열 반환"""
    item_lower = str(item_name)
    for keywords, usage in ITEM_USAGE:
        if any(kw in item_lower for kw in keywords):
            return usage
    return f"오늘 '{item_name}'을 가까이 두거나 몸에 지니세요. 긍정적인 기운이 하루 전체에 흐릅니다."


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
        "tip": "오늘 중요한 결정을 내리기 전에 3초만 멈추는 습관을 만들어 보세요. 당신의 직관은 훌륭하지만 한 박자 여유가 더 좋은 결과를 만듭니다.",
        "color": "빨간색, 오렌지", "stone": "다이아몬드, 루비", "number": "1, 9",
    },
    "황소자리": {
        "element": "흙 (Earth)", "ruling": "금성 (Venus)",
        "trait": "안정과 신뢰를 중시하는 현실주의자입니다. 한번 시작한 일은 끝까지 해내는 끈기와 성실함이 빛납니다.",
        "strength": "인내심, 신뢰성, 현실 감각, 심미안",
        "weakness": "고집스러움, 변화 거부, 소유욕",
        "compatible": "처녀자리, 염소자리, 게자리",
        "tip": "오늘 새로운 방식을 한 가지만 시도해 보세요. 변화가 두렵더라도 작은 실험이 더 큰 안정을 만들어 줍니다.",
        "color": "초록색, 베이지", "stone": "에메랄드, 로즈쿼츠", "number": "2, 6",
    },
    "쌍둥이자리": {
        "element": "공기 (Air)", "ruling": "수성 (Mercury)",
        "trait": "지적 호기심과 소통 능력이 뛰어난 다재다능한 별자리입니다. 상황에 따라 유연하게 적응하는 능력이 탁월합니다.",
        "strength": "적응력, 커뮤니케이션 능력, 창의성, 유머",
        "weakness": "변덕, 집중력 부족, 우유부단함",
        "compatible": "천칭자리, 물병자리, 양자리",
        "tip": "오늘 여러 가지에 손대기보다 딱 두 가지에만 집중해 보세요. 당신의 에너지를 모으면 훨씬 강력한 결과를 만들 수 있습니다.",
        "color": "노란색, 하늘색", "stone": "아게이트, 시트린", "number": "3, 5",
    },
    "게자리": {
        "element": "물 (Water)", "ruling": "달 (Moon)",
        "trait": "감수성과 공감 능력이 풍부한 보살핌의 별자리입니다. 가족과 소중한 사람을 위해 헌신하는 따뜻한 마음이 특징입니다.",
        "strength": "공감력, 직관력, 보살핌, 기억력",
        "weakness": "감정 기복, 소극성, 과도한 집착",
        "compatible": "전갈자리, 물고기자리, 황소자리",
        "tip": "오늘 자신을 돌보는 시간을 꼭 만들어 보세요. 남을 챙기는 것만큼 자신을 챙기는 것도 중요합니다.",
        "color": "은색, 흰색", "stone": "문스톤, 진주", "number": "2, 7",
    },
    "사자자리": {
        "element": "불 (Fire)", "ruling": "태양 (Sun)",
        "trait": "카리스마와 자신감이 넘치는 무대의 주인공 별자리입니다. 타고난 리더십으로 주변을 밝히고 이끄는 힘이 있습니다.",
        "strength": "카리스마, 관대함, 창의력, 자신감",
        "weakness": "자존심, 지나친 인정 욕구, 고집",
        "compatible": "양자리, 사수자리, 쌍둥이자리",
        "tip": "오늘 다른 사람의 의견도 주인공처럼 들어주세요. 경청하는 리더가 더 오래, 더 멀리 갑니다.",
        "color": "금색, 주황색", "stone": "루비, 호박", "number": "1, 4",
    },
    "처녀자리": {
        "element": "흙 (Earth)", "ruling": "수성 (Mercury)",
        "trait": "분석력과 완벽주의적 성향을 지닌 세심한 별자리입니다. 디테일을 놓치지 않는 꼼꼼함이 큰 강점입니다.",
        "strength": "분석력, 성실함, 실용성, 정확성",
        "weakness": "완벽주의, 지나친 비판, 걱정이 많음",
        "compatible": "황소자리, 염소자리, 게자리",
        "tip": "오늘 '80%면 충분하다'는 마음을 가져보세요. 완벽함을 추구하다 정작 중요한 것을 놓치지 않도록 균형이 필요합니다.",
        "color": "네이비, 회색", "stone": "사파이어, 카넬리안", "number": "5, 6",
    },
    "천칭자리": {
        "element": "공기 (Air)", "ruling": "금성 (Venus)",
        "trait": "균형과 조화를 중시하는 외교적 별자리입니다. 아름다움과 공정함에 대한 감각이 뛰어나며 관계를 소중히 여깁니다.",
        "strength": "균형 감각, 외교력, 심미안, 협력",
        "weakness": "우유부단함, 갈등 회피, 의존성",
        "compatible": "쌍둥이자리, 물병자리, 사수자리",
        "tip": "오늘 결정을 미루고 싶어지는 순간이 오면, '이것이 내가 원하는 것인가'를 먼저 물어보세요. 당신의 직관은 생각보다 정확합니다.",
        "color": "파스텔 핑크, 라벤더", "stone": "오팔, 로즈쿼츠", "number": "6, 9",
    },
    "전갈자리": {
        "element": "물 (Water)", "ruling": "명왕성 (Pluto)",
        "trait": "깊이 있는 통찰력과 강인한 의지를 지닌 신비의 별자리입니다. 한번 목표를 정하면 어떤 어려움도 뚫고 나가는 집중력이 있습니다.",
        "strength": "통찰력, 집중력, 강인함, 변화 적응력",
        "weakness": "집착, 의심, 복수심, 비밀주의",
        "compatible": "게자리, 물고기자리, 염소자리",
        "tip": "오늘 신뢰하는 사람에게 마음을 조금 열어보세요. 당신의 강인함 뒤에 숨겨진 따뜻함이 관계를 더 깊게 만들어 줍니다.",
        "color": "검정, 진홍색", "stone": "토파즈, 옵시디언", "number": "8, 11",
    },
    "사수자리": {
        "element": "불 (Fire)", "ruling": "목성 (Jupiter)",
        "trait": "자유와 모험을 사랑하는 낙관주의 별자리입니다. 넓은 시야로 세상을 바라보며 끊임없이 새로운 지식과 경험을 추구합니다.",
        "strength": "낙관성, 철학적 사고, 모험심, 솔직함",
        "weakness": "무책임함, 성급한 약속, 무신경함",
        "compatible": "양자리, 사자자리, 물병자리",
        "tip": "오늘 약속은 지킬 수 있는 것만 하세요. 솔직한 거절 한마디가 신뢰를 더 오래 지킵니다.",
        "color": "보라색, 파란색", "stone": "터키석, 라피스라줄리", "number": "3, 9",
    },
    "염소자리": {
        "element": "흙 (Earth)", "ruling": "토성 (Saturn)",
        "trait": "책임감과 인내로 목표를 향해 묵묵히 나아가는 별자리입니다. 시간이 걸리더라도 반드시 정상에 오르는 지구력이 특징입니다.",
        "strength": "책임감, 인내심, 실용성, 야망",
        "weakness": "고집, 지나친 실용주의, 감정 억제",
        "compatible": "황소자리, 처녀자리, 전갈자리",
        "tip": "오늘 일에서 잠시 손을 떼고 쉬어가는 것도 전략입니다. 꾸준히 달리기 위해서는 페이스를 조절하는 지혜가 필요합니다.",
        "color": "갈색, 카키", "stone": "가넷, 호안석", "number": "8, 10",
    },
    "물병자리": {
        "element": "공기 (Air)", "ruling": "천왕성 (Uranus)",
        "trait": "독창성과 혁신적 사고를 지닌 미래 지향적 별자리입니다. 기존의 틀을 깨고 새로운 방식으로 세상을 바라보는 능력이 있습니다.",
        "strength": "독창성, 인도주의, 미래 지향, 개방성",
        "weakness": "감정 표현 어려움, 고집, 거리감",
        "compatible": "쌍둥이자리, 천칭자리, 사수자리",
        "tip": "오늘 아이디어가 너무 앞서간다 싶으면 주변 사람이 이해할 수 있게 설명하는 연습을 해보세요. 탁월한 생각도 전달되어야 빛납니다.",
        "color": "일렉트릭 블루, 청록색", "stone": "아메시스트, 아쿠아마린", "number": "4, 7",
    },
    "물고기자리": {
        "element": "물 (Water)", "ruling": "해왕성 (Neptune)",
        "trait": "공감 능력이 탁월하고 예술적 감수성이 풍부한 별자리입니다. 타인의 감정을 직관적으로 읽어내는 능력이 탁월합니다.",
        "strength": "직관력, 창의성, 공감력, 헌신",
        "weakness": "우유부단함, 현실 도피, 감정 기복",
        "compatible": "게자리, 전갈자리, 황소자리",
        "tip": "오늘 감정에 치우치지 않도록 하루 한 번 '지금 내 감정이 사실인가'를 점검하세요. 직관은 훌륭하지만 현실 확인이 함께할 때 더 빛납니다.",
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
    return """
<div class="game-link">
    <p>🎮 운세와 함께 즐기는 무료 게임</p>
    <a href="https://hoholog.github.io/hoholog/#index">🎮 호호로그게임 바로가기</a>
</div>"""

# ─────────────────────────────────────────
# HTML 빌더
# ─────────────────────────────────────────

def build_quote_post(today_str):
    quote, meaning, category = pick_quote()
    title = seo_title(f"{today_str} 오늘의 명언")
    cat_badge = f" · {category}" if category and str(category) != 'nan' else ""
    meaning_html = f'<br><p style="font-size:14px;color:#666;line-height:1.8">{meaning}</p>' if meaning and str(meaning) != 'nan' else ""

    content = f"""{style()}
<div class="wrap">
  <div class="hero"><h1>📖 오늘의 명언</h1><p>{today_str}</p></div>
  <div class="card">
    <span class="badge">✨ 오늘의 명언{cat_badge}</span>
    <p style="font-size:17px;font-weight:700;line-height:1.9;color:#4a235a">❝ {quote} ❞</p>
    {meaning_html}
  </div>
  {site_link()}
  <div class="meta">※ 매일 자정 업데이트 · 오늘의 명언</div>
</div>"""
    return title, content, ["오늘의명언", "명언", "운세"]


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

# ── 총운 서론 풀 ──
_Z_TOTAL_INTRO_UP = [
    "오늘 하루 별의 기운이 유독 당신 편입니다. 지금 이 순간, 주변에서 작은 행운의 신호들이 조용히 쌓이고 있다는 것을 느끼셨나요?",
    "오늘은 오랫동안 기다려온 흐름이 비로소 당신 곁으로 돌아오는 날입니다. 그동안 묵묵히 버텨온 시간이 오늘의 좋은 기운을 만들었습니다.",
    "새벽부터 긍정적인 에너지가 흐르기 시작했습니다. 평소보다 발걸음이 가볍게 느껴진다면, 그것이 오늘 기운의 신호입니다.",
    "오늘은 당신이 가진 강점이 특히 도드라지는 날입니다. 자신을 믿고 앞으로 나아가기에 이보다 좋은 타이밍이 없습니다.",
]
_Z_TOTAL_INTRO_WARN = [
    "오늘은 서두르기보다 한 박자 쉬어가는 지혜가 필요한 날입니다. 조급함이 오히려 좋은 기회를 놓치게 만들 수 있습니다.",
    "오늘 하루는 에너지가 다소 분산되어 있습니다. 한 가지에 집중하고, 나머지는 내일로 미루는 전략이 현명합니다.",
    "오늘은 결과보다 과정에 집중하는 날입니다. 눈에 보이는 성과가 없더라도, 묵묵히 자신의 길을 걷는 것이 가장 현명한 선택입니다.",
]

# ── 총운 지수 해석 풀 ──
_Z_TOTAL_SCORE_UP = [
    "오늘의 종합 운세 지수는 상위권을 기록하고 있습니다. 오전 10시~오후 2시 사이에 중요한 결정을 내리거나 대화를 나누면 가장 긍정적인 결과를 기대할 수 있습니다.",
    "현재 측정된 오늘의 에너지 지수는 매우 활성화된 상태입니다. 특히 오전 시간대에 창의적인 작업이나 대인 접촉에서 평소보다 30% 이상 좋은 반응을 얻을 수 있는 흐름입니다.",
    "오늘 당신의 종합 운세는 이번 주 중 가장 높은 흐름을 보이고 있습니다. 주요 활동은 오전 중으로 몰아두고 오후에는 정리와 마무리에 집중하면 효율이 극대화됩니다.",
]
_Z_TOTAL_SCORE_WARN = [
    "오늘의 종합 에너지 지수는 평균 이하 구간에 위치해 있습니다. 이 구간에서 무리한 결정보다는 준비와 계획에 집중하면 2~3일 후 좋은 흐름으로 반전될 가능성이 높습니다.",
    "지수상으로 오늘은 회복과 재충전에 최적화된 날입니다. 새로운 일을 시작하기보다는 기존에 진행 중인 일을 점검하는 데 에너지를 쓰세요.",
]

# ── 연애운 서론 풀 ──
_Z_LOVE_INTRO_UP = [
    "오늘은 마음의 문이 평소보다 조금 더 넓게 열려 있습니다. 좋아하는 사람에게 쉽게 다가가기 어려웠던 날들이 있었다면, 오늘은 그 장벽이 낮아지는 날입니다.",
    "연애운이 따뜻하게 흐르는 날입니다. 혼자 삭이던 감정들을 오늘만큼은 솔직하게 표현해 보세요. 상대도 당신의 진심을 받아들일 준비가 되어 있을 가능성이 높습니다.",
    "오늘은 인연의 실이 조금 더 가까이 당겨지는 날입니다. 평소 스쳐 지나쳤던 만남 속에서 뜻밖의 인연이 시작될 수도 있습니다.",
]
_Z_LOVE_INTRO_WARN = [
    "오늘은 감정의 파도가 다소 높습니다. 사소한 말 한마디가 오해로 이어질 수 있으니, 중요한 대화는 충분히 생각한 뒤 꺼내는 것이 좋습니다.",
    "연애운이 잠시 숨 고르기를 하는 날입니다. 상대에게 기대를 낮추고, 지금 이 관계의 현재를 있는 그대로 바라보는 시간을 가져 보세요.",
    "오늘은 서로 다른 생각이 충돌하기 쉬운 날입니다. 내가 옳다는 확신보다 상대의 입장에서 한 번 더 생각해 보는 여유가 관계를 지켜줍니다.",
]

# ── 연애운 상세 조언 풀 ──
_Z_LOVE_DETAIL_UP = [
    "오늘은 예상 못한 연락이 올 수 있습니다. 특히 오후 2시~5시 사이 인간관계 변화 신호가 강합니다. 내일로 미루지 말고 오늘 답장을 보내세요.",
    "평소 마음에 두고 있던 사람과 자연스러운 대화 기회가 생길 수 있습니다. 먼저 다가가는 용기가 빛을 발합니다. 부담 없는 가벼운 안부 한 마디가 큰 변화를 만들 수 있습니다.",
    "SNS나 메신저에서 뜻밖의 메시지가 도착할 수 있습니다. 가볍게 답하되 진심을 담아 보세요. 오늘의 짧은 대화가 새로운 관계의 시작이 될 수 있습니다.",
    "오늘 저녁 약속이 생긴다면 흘려 넘기지 마세요. 소중한 인연이 이어질 수 있는 자리입니다. 편안한 분위기에서 솔직한 대화를 나눠 보세요.",
]
_Z_LOVE_DETAIL_WARN = [
    "감정적으로 예민해지기 쉬운 날입니다. 중요한 대화는 감정이 가라앉은 저녁 이후로 미루세요. 말하기 전에 '이 말이 필요한 말인가'를 한 번 더 생각해 보세요.",
    "가까운 사람의 말 한마디가 상처로 느껴질 수 있습니다. 오늘은 상대 의도를 먼저 확인해 보세요. 오해에서 시작된 갈등은 빠를수록 해소하기 쉽습니다.",
    "혼자만의 시간이 오히려 관계에 활력을 줄 수 있습니다. 무리해서 연락하기보다 여유를 가져 보세요. 잠시 거리를 두는 것이 더 깊은 연결로 이어지는 법입니다.",
]

# ── 연애운 시간대 가이드 풀 ──
_Z_LOVE_TIME_UP = [
    "💬 오늘의 최적 대화 시간대: 오후 3시~6시 사이가 감수성이 열리는 시간입니다. 이 시간 안에 전하고 싶은 마음을 표현해 보세요.",
    "💬 오늘 저녁 7시 이후에는 편안한 대화 에너지가 흐릅니다. 무거운 주제보다 가벼운 공감 대화부터 시작해 보세요.",
    "💬 오전 중에 연락을 주고받는다면 오늘 하루 관계 에너지가 더 길게 지속됩니다. 짧은 안부 메시지 하나가 하루를 바꿀 수 있습니다.",
]
_Z_LOVE_TIME_WARN = [
    "💬 오후 12시~3시 사이에는 감정 기복이 생기기 쉽습니다. 이 시간대에는 중요한 감정 대화를 피하고 저녁 이후로 미루는 것이 현명합니다.",
    "💬 오늘은 저녁 이후에 오히려 마음이 안정됩니다. 하루 중 가장 솔직한 대화를 나눌 수 있는 시간대이니 참고하세요.",
]

# ── 연애운 마무리 풀 ──
_Z_LOVE_CLOSE_UP = [
    "오늘 하루, 당신의 진심은 분명히 상대에게 전달됩니다. 사랑은 타이밍이 전부가 아닙니다. 오늘 이 순간도 충분히 소중합니다. 💕",
    "연애는 결국 작은 순간들이 쌓이는 과정입니다. 오늘의 작은 용기가 내일의 큰 행복이 되어 돌아옵니다. 자신을 믿어 보세요. 🌸",
    "당신이 먼저 마음을 열면, 세상도 당신을 향해 마음을 엽니다. 오늘의 따뜻한 기운을 주변 사람들과 나눠 보세요. 💞",
]
_Z_LOVE_CLOSE_WARN = [
    "지금 이 순간도 충분히 잘 하고 있습니다. 관계에 있어 완벽한 타이밍은 없습니다. 오늘 하루도 당신만의 속도로 나아가세요. 🌿",
    "사랑은 서두를수록 멀어지는 법입니다. 오늘 하루 여유를 갖고, 상대방을 있는 그대로 바라봐 주세요. 그 여유가 관계를 더 깊게 만듭니다. 🌙",
]

# ── 금전운 서론 풀 ──
_Z_MONEY_INTRO_UP = [
    "오늘은 금전 흐름이 당신에게 유리하게 움직이는 날입니다. 오랫동안 막혀있던 수입의 물꼬가 트일 수 있는 시기입니다.",
    "재물운의 흐름이 상승세를 타고 있습니다. 작은 것이라도 오늘 챙겨두면 나중에 큰 자산이 됩니다. 돈에 관련된 일은 오늘 안으로 처리하세요.",
    "오늘은 경제활동에 있어 생각보다 좋은 하루입니다. 막연하게 기다려온 기회가 구체적인 형태로 나타날 수 있습니다.",
]
_Z_MONEY_INTRO_WARN = [
    "오늘은 금전운이 다소 신중함을 요구하는 날입니다. 충동적인 결정보다는 하루를 관찰하고 내일 행동으로 옮기는 전략이 더 현명합니다.",
    "오늘 금전적인 실수가 생기기 쉬운 흐름입니다. 평소보다 꼼꼼하게 지출을 점검하고, 큰 결정은 보류해 두세요.",
]

# ── 금전운 지수 해석 풀 ──
_Z_MONEY_SCORE_UP = [
    "오늘 경제활동 효율 지수는 높은 수준을 기록하고 있습니다. 오전 10시~오후 1시 사이에 금전 관련 협의나 결정을 내리면 가장 긍정적인 결과를 얻을 수 있습니다.",
    "재물운 지수가 상위 30% 구간에 위치합니다. 놓쳤던 환급금이나 미수금을 오늘 확인해 보세요. 작은 액수라도 오늘의 흐름과 함께라면 의미 있는 수확이 됩니다.",
    "금전운 수치가 이번 주 중 가장 활성화된 날입니다. 새로운 수입 루트나 부업 아이디어를 검토하기에 좋은 타이밍입니다.",
]
_Z_MONEY_SCORE_WARN = [
    "오늘 금전 지수는 평균 이하 구간입니다. 이 구간에서 새로운 투자나 소비보다는 기존 자산을 점검하고 유지하는 것이 장기적으로 유리합니다.",
    "금전운 지수가 낮은 날일수록 충동구매에 취약해집니다. 오늘 하루만큼은 지갑을 닫고 지출 내역을 확인하는 것으로 시작해 보세요.",
]

# ── 금전운 상세 조언 풀 ──
_Z_MONEY_DETAIL_UP = [
    "오늘 소소한 금전 이익이 발생할 수 있습니다. 적은 금액이라도 챙겨두면 나중에 큰 도움이 됩니다. 정기 적금이나 자동 저축 설정을 오늘 검토해 보세요.",
    "미뤄두었던 환급금이나 정산 내역을 오늘 확인해 보세요. 놓친 돈이 있을 수 있습니다. 모바일 앱을 통한 캐시백이나 포인트 전환도 오늘 해두면 좋습니다.",
    "오후 늦게 예상치 못한 수입 관련 연락이 올 수 있습니다. 꼼꼼히 검토하고 결정하세요. 서두르지 않아도 기회는 오늘 하루 안에 있습니다.",
]
_Z_MONEY_DETAIL_WARN = [
    "오늘은 갑작스러운 지출이 생길 수 있습니다. 특히 오후 3시 이후 충동 구매를 주의하세요. 장바구니에 담아 두고 하루 뒤에 다시 확인하는 습관을 들여보세요.",
    "카드 결제·자동이체 내역을 오늘 한 번 점검하세요. 모르는 사이 새어나가는 돈이 있을 수 있습니다. 가계부 앱을 통한 10분 점검이 한 달 지출을 바꿉니다.",
    "투자나 새로운 금전 계약은 오늘보다 2~3일 후로 미루는 것이 유리합니다. 지금의 판단이 흐려지기 쉬운 날이니 문서 서명이나 큰 결제는 신중하게 검토하세요.",
]

# ── 금전운 시간대 가이드 풀 ──
_Z_MONEY_TIME_UP = [
    "💰 오늘의 황금 시간대: 오전 10시~오후 1시 사이에 금전 관련 연락이나 결정을 마무리하세요. 이 시간대에 이루어진 금전 계획은 실행력이 높습니다.",
    "💰 오늘 오후 2시~4시 사이가 수익 관련 아이디어가 가장 활발히 떠오르는 시간입니다. 생각이 떠오르면 바로 메모해 두세요.",
]
_Z_MONEY_TIME_WARN = [
    "💰 오늘 오후 3시 이후에는 지출 충동이 커집니다. 이 시간대에는 쇼핑 앱 알림을 꺼두고, 불필요한 온라인 쇼핑은 내일로 미루세요.",
    "💰 점심 이후부터 금전 판단력이 흐려질 수 있습니다. 중요한 계약이나 결제는 오전 안으로 처리하거나 다음 날로 넘기세요.",
]

# ── 금전운 마무리 풀 ──
_Z_MONEY_CLOSE_UP = [
    "재물은 한 번에 쌓이는 것이 아닙니다. 오늘 챙긴 작은 것들이 모여 당신의 단단한 경제 기반이 됩니다. 오늘 하루도 현명하게 마무리하세요. 💛",
    "돈이 들어오는 흐름을 타고 있을 때, 지출도 함께 점검해야 진짜 부가 쌓입니다. 오늘의 좋은 금전 에너지를 낭비 없이 활용하세요. 🌟",
]
_Z_MONEY_CLOSE_WARN = [
    "오늘의 신중함이 내일의 안정을 만듭니다. 금전 흐름이 좋지 않은 날에 무리하지 않는 것 자체가 최고의 재테크입니다. 💚",
    "지금의 어려움은 일시적입니다. 오늘 하루 지출을 줄이고 내일을 위한 계획을 세워 보세요. 작은 결심 하나가 재정 흐름을 바꿉니다. 🌿",
]

# ── 직장운 서론 풀 ──
_Z_WORK_INTRO_UP = [
    "오늘은 직장에서 당신의 존재감이 빛날 수 있는 날입니다. 그동안 보이지 않는 곳에서 쌓아온 노력이 오늘 드디어 수면 위로 떠오르는 흐름입니다.",
    "업무 흐름이 원활한 하루입니다. 평소 어렵게 느껴지던 일도 오늘은 생각보다 수월하게 풀릴 수 있습니다. 중요한 과제가 있다면 오늘 시작하세요.",
    "오늘은 아이디어와 실행력이 모두 살아있는 날입니다. 머릿속에 맴돌던 계획을 오늘 꺼내 보세요. 생각보다 빠르게 진전될 수 있습니다.",
]
_Z_WORK_INTRO_WARN = [
    "오늘은 직장에서 예상치 못한 변수가 생길 수 있는 날입니다. 계획을 꼼꼼하게 점검하고, 여유 시간을 확보해 두세요.",
    "업무 집중력이 흐트러지기 쉬운 날입니다. 멀티태스킹보다는 한 가지에 집중하는 방식이 결과적으로 더 많은 것을 해냅니다.",
]

# ── 직장운 지수 해석 풀 ──
_Z_WORK_SCORE_UP = [
    "오늘의 업무 효율 지수는 높은 구간을 가리키고 있습니다. 집중력과 판단력이 동시에 살아있는 날이니, 핵심 업무를 오전 중에 처리하면 최상의 결과를 얻을 수 있습니다.",
    "직장 에너지 지수가 이번 주 최고치에 가깝습니다. 팀워크가 필요한 업무나 대외 커뮤니케이션에서 평소보다 좋은 반응을 기대할 수 있습니다.",
    "오늘의 성과 지수는 상위권에 위치합니다. 지금껏 해온 업무의 완성도를 점검하고, 놓친 부분을 보완하는 데 쓰면 큰 성취감을 느낄 수 있습니다.",
]
_Z_WORK_SCORE_WARN = [
    "오늘의 업무 집중 지수는 평균 이하 구간입니다. 성과를 억지로 내려 하기보다 오늘 하루 기반을 다지는 작업에 집중하면 내일 더 좋은 결과로 이어집니다.",
    "직장 에너지가 낮게 측정된 날입니다. 오늘 실수가 나와도 자신을 탓하지 마세요. 쉬면서 회복하는 것도 중요한 업무 능력입니다.",
]

# ── 직장운 상세 조언 풀 ──
_Z_WORK_DETAIL_UP = [
    "오늘 업무에서 작은 성과가 인정받을 수 있습니다. 평소 해온 노력이 드디어 빛을 발하는 시기입니다. 결과가 나왔을 때 겸손하게 팀과 공유하면 더 큰 신뢰를 얻습니다.",
    "동료나 상사로부터 예상치 못한 긍정적인 피드백이 올 수 있습니다. 자신감을 갖고 임해 보세요. 칭찬을 받을 때 다음 목표도 함께 제시하면 인상이 더 깊어집니다.",
    "새로운 아이디어가 떠오르기 쉬운 날입니다. 메모해 두면 나중에 큰 자산이 됩니다. 회의나 미팅에서 적극적으로 발언해 보세요. 오늘 당신의 말에 무게감이 있습니다.",
]
_Z_WORK_DETAIL_WARN = [
    "업무 중 세부 사항을 놓치기 쉬운 날입니다. 서두르지 말고 두 번 확인하는 습관을 발휘하세요. 이메일이나 보고서는 발송 전 반드시 재검토하세요.",
    "동료와의 의견 충돌이 생길 수 있습니다. 내 입장만 고집하기보다 상대 의견도 충분히 들어보세요. 오늘의 양보가 나중에 더 큰 신뢰로 돌아옵니다.",
    "중요한 발표나 보고는 오늘보다 내일 진행하는 것이 더 좋은 결과를 가져올 수 있습니다. 준비가 조금 더 필요하다면 오늘 시간을 그 준비에 투자하세요.",
]

# ── 직장운 시간대 가이드 풀 ──
_Z_WORK_TIME_UP = [
    "💼 오늘의 골든타임: 오전 9시~11시 사이가 집중력이 가장 높은 시간대입니다. 중요한 업무와 핵심 판단을 이 시간 안에 마무리하세요.",
    "💼 오후 2시~4시 사이에는 창의적인 아이디어가 활발히 떠오릅니다. 브레인스토밍이나 기획 작업은 이 시간대를 활용해 보세요.",
    "💼 오전 집중 업무, 오후 협업·소통으로 나누면 오늘 하루 생산성이 극대화됩니다. 오늘은 그 패턴이 특히 잘 맞는 날입니다.",
]
_Z_WORK_TIME_WARN = [
    "💼 오후 1시~3시 사이는 집중력이 가장 떨어지는 시간대입니다. 이 시간에는 단순 반복 업무나 정리 작업 위주로 배치하세요.",
    "💼 오늘 오전 업무 리스트를 미리 작성해 두면 흐트러지는 집중력을 잡을 수 있습니다. 3개 이내로 핵심 과제만 뽑아서 하루를 시작하세요.",
]

# ── 직장운 마무리 풀 ──
_Z_WORK_CLOSE_UP = [
    "오늘 당신이 만들어낸 작은 성과 하나가 미래의 큰 기회를 여는 열쇠가 됩니다. 오늘 하루도 수고 많으셨습니다. 🌟",
    "당신의 능력은 이미 충분합니다. 오늘 하루 그 능력을 마음껏 발휘하고, 저녁에는 스스로를 칭찬해 주세요. 💼",
]
_Z_WORK_CLOSE_WARN = [
    "오늘 하루 버텨낸 것 자체가 대단한 일입니다. 쉽지 않은 날일수록 내일은 더 단단해집니다. 오늘도 정말 잘 하셨습니다. 🌿",
    "모든 날이 빛날 수는 없습니다. 오늘 같은 날이 있기에 좋은 날의 가치가 더 빛납니다. 내일을 위해 오늘은 충분히 쉬어 가세요. 💙",
]
_Z_AVOID_ACTIONS = [
    ["충동적인 큰 결정", "감정적인 메시지 전송", "불필요한 논쟁 시작"],
    ["섣불리 계약서 사인", "새벽 늦게까지 야식 먹기", "검증 없는 투자 참여"],
    ["기분에 따른 충동 구매", "중요한 약속 취소", "남 험담에 동조하기"],
    ["급하게 사람 판단하기", "수면 부족 강행", "처음 보는 사람에게 돈 빌려주기"],
]
_Z_CHEER = [
    "오늘 하루도 쉽지 않다는 거 알아요. 그래도 당신은 이미 충분히 잘 해내고 있습니다. 오늘 하루도 조금씩, 천천히 나아가세요. ✨",
    "완벽하지 않아도 괜찮아요. 오늘의 작은 선택들이 쌓여 당신만의 길이 됩니다. 그 과정을 믿어보세요. 🌟",
    "힘든 날일수록 자신에게 너그러워지세요. 당신이 생각하는 것보다 훨씬 더 잘 버티고 있습니다. 오늘도 응원합니다. 💫",
    "오늘의 작은 걸음이 미래의 큰 변화를 만듭니다. 조급해하지 말고, 지금 이 순간에 집중해 보세요. 🌙",
    "당신 곁에 좋은 기운이 흐르고 있습니다. 눈에 보이지 않아도 분명히 쌓이고 있으니, 오늘도 힘내세요. ⭐",
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

    # ── 1. 총운 (5파트 구조) ──
    total_color, total_level = _zodiac_score_badge(total)
    total_intro    = random.choice(_Z_TOTAL_INTRO_UP   if total >= 65 else _Z_TOTAL_INTRO_WARN)
    total_score_c  = random.choice(_Z_TOTAL_SCORE_UP   if total >= 65 else _Z_TOTAL_SCORE_WARN)
    total_cheer_c  = random.choice(_Z_CHEER)
    summary_html = f'''
<div class="card" style="border-left:5px solid {total_color}">
  <span class="badge" style="background:#f0fdf4;color:{total_color}">🌟 오늘 총운 · {total}% {total_level}</span>
  <p style="margin-top:12px;font-size:15px;line-height:1.95;color:#333;font-weight:500">{total_intro}</p>
  <p style="margin-top:10px;font-size:14px;line-height:1.9;color:#444">{_para(0)}</p>
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
    love_time    = random.choice(_Z_LOVE_TIME_UP     if love_is_up else _Z_LOVE_TIME_WARN)
    love_close   = random.choice(_Z_LOVE_CLOSE_UP    if love_is_up else _Z_LOVE_CLOSE_WARN)
    love_html = f'''
<div class="card">
  <span class="badge" style="background:#fff0f3;color:#e11d48">❤️ 연애운 · {love}% {love_level}</span>
  <p style="margin-top:12px;font-size:15px;line-height:1.95;color:#333;font-weight:500">{love_intro}</p>
  <p style="margin-top:10px;font-size:14px;line-height:1.9;color:#444">{_para(2)}</p>
  <div style="margin-top:12px;background:#fff0f3;border-radius:10px;padding:12px 14px;
              font-size:13px;color:#9f1239;line-height:1.8;border-left:3px solid #e11d48">
    💡 {love_detail}
  </div>
  <p style="margin-top:10px;font-size:13px;line-height:1.8;color:#555">{love_time}</p>
  <p style="margin-top:10px;font-size:13px;line-height:1.85;color:#666;font-style:italic">{love_close}</p>
</div>'''

    # ── 3. 금전운 (5파트 구조) ──
    money_color, money_level = _zodiac_score_badge(money)
    money_is_up   = money >= 70
    money_intro   = random.choice(_Z_MONEY_INTRO_UP   if money_is_up else _Z_MONEY_INTRO_WARN)
    money_score_c = random.choice(_Z_MONEY_SCORE_UP   if money_is_up else _Z_MONEY_SCORE_WARN)
    money_detail  = random.choice(_Z_MONEY_DETAIL_UP  if money_is_up else _Z_MONEY_DETAIL_WARN)
    money_time    = random.choice(_Z_MONEY_TIME_UP    if money_is_up else _Z_MONEY_TIME_WARN)
    money_close   = random.choice(_Z_MONEY_CLOSE_UP   if money_is_up else _Z_MONEY_CLOSE_WARN)
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
  <p style="margin-top:10px;font-size:13px;line-height:1.8;color:#555">{money_time}</p>
  <p style="margin-top:10px;font-size:13px;line-height:1.85;color:#666;font-style:italic">{money_close}</p>
</div>'''

    # ── 4. 직장·사업운 (5파트 구조) ──
    work_score = round((total + health) / 2)
    work_color, work_level = _zodiac_score_badge(work_score)
    work_is_up   = work_score >= 70
    work_intro   = random.choice(_Z_WORK_INTRO_UP    if work_is_up else _Z_WORK_INTRO_WARN)
    work_score_c = random.choice(_Z_WORK_SCORE_UP    if work_is_up else _Z_WORK_SCORE_WARN)
    work_detail  = random.choice(_Z_WORK_DETAIL_UP   if work_is_up else _Z_WORK_DETAIL_WARN)
    work_time    = random.choice(_Z_WORK_TIME_UP     if work_is_up else _Z_WORK_TIME_WARN)
    work_close   = random.choice(_Z_WORK_CLOSE_UP    if work_is_up else _Z_WORK_CLOSE_WARN)
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
  <p style="margin-top:10px;font-size:13px;line-height:1.8;color:#555">{work_time}</p>
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
        range(1940,1950): ("40년대생", "경험과 연륜이 빛나는 시기입니다. 오늘은 주변의 조언을 귀담아 들어보세요.",
                           "된장찌개·두부요리 등 발효식품", "5, 8", "번화한 시장이나 혼잡한 교통"),
        range(1950,1960): ("50년대생", "안정적인 흐름 속에 작은 기회가 숨어 있습니다. 천천히 살피세요.",
                           "제철 나물·현미밥 등 담백한 식단", "3, 6", "급경사 계단이나 미끄러운 바닥"),
        range(1960,1970): ("60년대생", "오랜 경험이 오늘 빛을 발합니다. 자신의 직관을 믿어보세요.",
                           "등푸른 생선·견과류 등 오메가3 식품", "1, 7", "소음이 심한 공사 현장 근처"),
        range(1970,1980): ("70년대생", "균형 잡힌 판단력이 돋보이는 날입니다. 중요한 결정에 자신감을 가져보세요.",
                           "고구마·브로콜리 등 항산화 식품", "2, 9", "밀폐된 실내나 환기가 안 되는 공간"),
        range(1980,1990): ("80년대생", "에너지가 풍부한 시기입니다. 오늘 미루던 일을 하나만 처리해 보세요.",
                           "닭가슴살·달걀 등 고단백 식품", "4, 6", "충동적인 온라인 쇼핑 사이트"),
        range(1990,2000): ("90년대생", "새로운 변화를 받아들이기 좋은 날입니다. 두려움보다 설렘으로 임해보세요.",
                           "아보카도·블루베리 등 슈퍼푸드", "3, 7", "인파가 너무 많은 핫플레이스"),
        range(2000,2010): ("00년대생", "잠재력이 폭발하는 시기입니다. 오늘 아이디어를 바로 실행에 옮겨 보세요.",
                           "바나나·아몬드 등 에너지 식품", "1, 5", "집중이 필요한데 소음이 많은 장소"),
        range(2010,2020): ("10년대생", "호기심과 탐구심이 빛나는 날입니다. 오늘 새로운 것을 한 가지 배워보세요.",
                           "치즈·우유 등 칼슘 풍부한 식품", "2, 8", "불필요한 경쟁 심리가 생기는 장소"),
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
        '쥐띠':    {'best': ('용띠','🐲','창의력과 행동력이 만나 시너지가 폭발합니다'),
                   'avoid':('말띠','🐴','서로 방향이 달라 오해가 생기기 쉽습니다')},
        '소띠':    {'best': ('닭띠','🐓','꼼꼼함과 책임감이 공명해 신뢰가 쌓입니다'),
                   'avoid':('양띠','🐑','속도와 방식이 달라 갈등이 생길 수 있습니다')},
        '호랑이띠':{'best': ('말띠','🐴','두 에너지가 합쳐져 무한한 추진력이 됩니다'),
                   'avoid':('원숭이띠','🐵','주도권 다툼으로 긴장감이 높아집니다')},
        '토끼띠':  {'best': ('양띠','🐑','감성과 공감이 통해 편안한 관계가 됩니다'),
                   'avoid':('닭띠','🐓','논리와 감성이 충돌하기 쉬운 조합입니다')},
        '용띠':    {'best': ('쥐띠','🐭','쥐띠의 지혜가 용띠의 힘을 빛나게 합니다'),
                   'avoid':('개띠','🐶','원칙과 자유로움이 부딪히는 조합입니다')},
        '뱀띠':    {'best': ('닭띠','🐓','지성과 직관이 만나 완벽한 조화를 이룹니다'),
                   'avoid':('돼지띠','🐷','서로 다른 가치관이 충돌하기 쉽습니다')},
        '말띠':    {'best': ('호랑이띠','🐯','열정과 용기가 서로를 끌어올립니다'),
                   'avoid':('쥐띠','🐭','세밀함과 큰 그림이 엇갈리기 쉽습니다')},
        '양띠':    {'best': ('토끼띠','🐰','따뜻한 감성으로 서로를 위로합니다'),
                   'avoid':('소띠','🐮','원칙과 유연함이 마찰을 일으킵니다')},
        '원숭이띠':{'best': ('쥐띠','🐭','재치와 지략이 만나 최강의 팀이 됩니다'),
                   'avoid':('호랑이띠','🐯','리더십 충돌로 긴장감이 생깁니다')},
        '닭띠':    {'best': ('소띠','🐮','성실함과 책임감이 공명합니다'),
                   'avoid':('토끼띠','🐰','속도와 방식의 차이가 스트레스를 줍니다')},
        '개띠':    {'best': ('호랑이띠','🐯','의리와 용기가 함께해 든든합니다'),
                   'avoid':('용띠','🐲','자존심 충돌이 관계를 어렵게 합니다')},
        '돼지띠':  {'best': ('토끼띠','🐰','넉넉함과 온화함이 서로를 행복하게 합니다'),
                   'avoid':('뱀띠','🐍','사소한 의심이 오해로 커질 수 있습니다')},
    }
    compat = _CHINESE_COMPAT.get(c['kr'], {})
    best_compat   = compat.get('best',  ('', '', '오늘 주변 사람들과 좋은 에너지를 나눠보세요'))
    avoid_compat  = compat.get('avoid', ('', '', '감정적인 충돌은 오늘 잠시 보류하세요'))

    compat_html = f'''
<div class="card" style="background:linear-gradient(135deg,#fff7ed,#fef3c7);border-left:5px solid #f59e0b">
  <span class="badge" style="background:#fef3c7;color:#92400e">💑 오늘의 띠별 궁합</span>
  <div style="margin-top:14px;display:grid;gap:10px">
    <div style="background:#fff;border-radius:10px;padding:14px;border:1px solid #d1fae5">
      <div style="font-size:13px;font-weight:700;color:#065f46;margin-bottom:6px">
        🟢 오늘의 찰떡궁합: {best_compat[1]} {best_compat[0]}
      </div>
      <div style="font-size:13px;color:#374151;line-height:1.8">{best_compat[2]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:6px">
        오늘 {best_compat[0]}와 함께하는 시간이 있다면 적극적으로 협력해 보세요.
        두 에너지가 만나 혼자일 때보다 훨씬 좋은 결과를 만들어 낼 수 있습니다.
      </div>
    </div>
    <div style="background:#fff;border-radius:10px;padding:14px;border:1px solid #fee2e2">
      <div style="font-size:13px;font-weight:700;color:#991b1b;margin-bottom:6px">
        🔴 오늘의 거리두기: {avoid_compat[1]} {avoid_compat[0]}
      </div>
      <div style="font-size:13px;color:#374151;line-height:1.8">{avoid_compat[2]}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:6px">
        오늘은 {avoid_compat[0]}와의 중요한 결정이나 논쟁을 피하고,
        감정이 차분해진 내일 이후로 미루는 것이 현명합니다.
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
        if score >= 80: return ("#16a34a", "최적 ★", "적극 활용하세요")
        if score >= 65: return ("#d97706", "보통 ◐", "무난하게 진행 가능")
        return ("#dc2626", "주의 ▼", "중요한 일은 피하세요")

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
          <td style="padding:10px 8px;color:#374151;line-height:1.6">{am_tip}<br><span style="font-size:11px;color:#6b7280">집중력이 필요한 핵심 업무 배치 권장</span></td>
        </tr>
        <tr style="border-bottom:1px solid #e0e7ff">
          <td style="padding:10px 8px;font-weight:700">☀️ 오후<br><span style="font-size:11px;color:#6b7280;font-weight:400">12:00~18:00</span></td>
          <td style="padding:10px 8px;text-align:center;font-weight:900;color:{pm_c};font-size:16px">{pm_score}점</td>
          <td style="padding:10px 8px;text-align:center;color:{pm_c};font-weight:700">{pm_lv}</td>
          <td style="padding:10px 8px;color:#374151;line-height:1.6">{pm_tip}<br><span style="font-size:11px;color:#6b7280">소통·협업·회의 등 대인 활동 배치 권장</span></td>
        </tr>
        <tr>
          <td style="padding:10px 8px;font-weight:700">🌙 저녁<br><span style="font-size:11px;color:#6b7280;font-weight:400">18:00~24:00</span></td>
          <td style="padding:10px 8px;text-align:center;font-weight:900;color:{ev_c};font-size:16px">{ev_score}점</td>
          <td style="padding:10px 8px;text-align:center;color:{ev_c};font-weight:700">{ev_lv}</td>
          <td style="padding:10px 8px;color:#374151;line-height:1.6">{ev_tip}<br><span style="font-size:11px;color:#6b7280">감성적 대화·자기 계발·가족과의 시간 적합</span></td>
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
            f"금전 경보 (지수 {money}점)",
            "오늘은 충동구매 위험이 큽니다. 장바구니에 담아둔 물건은 내일 결제하세요.",
            "카드·현금 지출을 오전 중에 마무리하고, 오후 3시 이후 쇼핑 앱은 잠시 꺼두세요."))
    elif money >= 85:
        checkpoints.append(("💰", "#16a34a",
            f"금전 기회 포착 (지수 {money}점)",
            "오늘 재정 관련 결정에 유리한 흐름입니다. 놓쳤던 환급금·정산을 확인하세요.",
            "오전 10시~오후 1시 사이가 금전 처리의 최적 타임입니다. 적금·투자 계획 검토도 추천합니다."))
    else:
        checkpoints.append(("💰", "#d97706",
            f"금전 안정 관리 (지수 {money}점)",
            "평이한 흐름입니다. 지출 내역을 한 번 점검하고 불필요한 자동결제를 정리해 보세요.",
            "오늘 하루 지출 목표를 아침에 미리 정해두면 충동 소비를 효과적으로 막을 수 있습니다."))

    # 건강운 조건
    if health >= 90:
        checkpoints.append(("💪", "#16a34a",
            f"신체 에너지 최상 (지수 {health}점)",
            "미뤄둔 고강도 운동이나 등산을 추천합니다. 몸이 에너지를 받아들이기 최적인 날입니다.",
            "운동 전 충분한 준비운동과 수분 보충을 잊지 마세요. 새로운 스포츠 도전도 오늘이 적기입니다."))
    elif health < 60:
        checkpoints.append(("💪", "#dc2626",
            f"건강 주의 신호 (지수 {health}점)",
            "무리한 야근·과음·자극적인 식사를 피하세요. 몸이 보내는 신호를 무시하지 마세요.",
            "점심 식사 후 10분 낮잠 또는 가벼운 스트레칭으로 오후 체력을 보충하세요."))
    else:
        checkpoints.append(("💪", "#d97706",
            f"건강 관리 권장 (지수 {health}점)",
            "평소보다 체력 소모가 빠를 수 있습니다. 수분을 충분히 섭취하고 규칙적인 식사를 지켜주세요.",
            "오후 3시경 비타민 C가 풍부한 과일이나 견과류를 간식으로 챙기면 집중력 유지에 도움이 됩니다."))

    # 연애운 조건
    if love >= 80:
        checkpoints.append(("❤️", "#e11d48",
            f"연애 에너지 상승 (지수 {love}점)",
            "소중한 사람에게 먼저 연락해보세요. 오늘 당신의 진심은 분명히 전달됩니다.",
            f"오후 3시~6시 사이가 감성 대화의 최적 타임입니다. 오늘 {lucky_color} 컬러 소품이 연애 에너지를 높여줍니다."))
    elif love < 55:
        checkpoints.append(("❤️", "#6b7280",
            f"감정 정비 필요 (지수 {love}점)",
            "오늘은 중요한 감정 대화를 피하고 서로 여유를 주는 것이 좋습니다.",
            "혼자만의 시간이 오히려 관계에 활력을 줄 수 있습니다. 독서·취미 활동으로 내면을 채워보세요."))

    # 총운 기반 종합 조언
    if total >= 85:
        checkpoints.append(("🌟", "#7c3aed",
            f"오늘의 종합 지수 {total}점 — 행동 적기",
            "오늘은 미루던 중요한 결정을 내리기에 최적입니다. 긍정적인 에너지를 최대한 활용하세요.",
            f"골든 타임 {_DOW_GOLDEN_TIME[dow]}을 활용해 핵심 과제를 처리하면 최상의 결과를 기대할 수 있습니다."))
    elif total < 55:
        checkpoints.append(("🌟", "#6b7280",
            f"오늘의 종합 지수 {total}점 — 신중 모드",
            "오늘은 새로운 시작보다 기존 일을 점검하고 마무리하는 데 집중하세요.",
            "결과에 집착하기보다 과정에 충실한 하루로 삼으면, 2~3일 후 좋은 흐름으로 반전됩니다."))

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
    _SIG_UP   = ["재물운 상승 신호", "금전운 상승 중", "운세 상승 흐름"]
    _SIG_WARN = ["오늘 주의 필요", "신중함이 필요한 날", "주의 신호 감지"]
    _SIG_REV  = ["반전의 하루", "예상 밖 반전 운세", "흐름이 바뀌는 날"]
    _SIG_MID  = ["안정적인 하루", "균형 잡힌 운세", "차분한 에너지의 날"]
    if avg >= 80:                signal = random.choice(_SIG_UP)
    elif avg <= 55:              signal = random.choice(_SIG_WARN)
    elif abs(total-money) >= 30: signal = random.choice(_SIG_REV)
    else:                        signal = random.choice(_SIG_MID)

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
        if scores[top] >= 80:
            signal = f"이번 주 {top} 주목"
        elif min(scores.values()) <= 55:
            signal = "이번 주 주의 필요"
        else:
            signal = "이번 주 흐름 확인"
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
    """띠별 월간운세 12개 개별 발행 — 매월 1일"""
    month_str = get_month()
    results = []
    for c in CHINESE:
        fortune = chinese_monthly_fortune(c['en'])
        rating  = stars()
        card_id = f"cmfc-{c['en']}"
        total, money, health, love = pick_score(c['kr'])

        # 제목 신호 키워드
        scores = {"총운": total, "금전운": money, "건강운": health, "애정운": love}
        top = max(scores, key=scores.get)
        if scores[top] >= 80:
            signal = f"이번 달 {top} 상승"
        elif min(scores.values()) <= 55:
            signal = "이번 달 주의 필요"
        else:
            signal = "이번 달 흐름 확인"
        title = f"{c['kr']} {month_str} 월간운세 | {signal}"

        # 기간별: sentence() 제거 → chinese_monthly_fortune 재사용
        periods = [
            ("상순 (1~10일)", chinese_monthly_fortune(c['en'])),
            ("중순 (11~20일)", chinese_monthly_fortune(c['en'])),
            ("하순 (21~말일)", chinese_monthly_fortune(c['en'])),
        ]
        period_html = "".join(
            f'<div class="week-day"><strong>{p}</strong><br><span style="font-size:13px;color:#555">{s[:80]}{"…" if len(str(s))>80 else ""}</span></div>'
            for p, s in periods
        )

        kw_list = [
            c['kr'], f"{c['kr']} 월간운세", f"{c['kr']} 이달운세",
            "띠별 월간운세", f"{c['kr']} {month_str}", "월간운세", "띠운세"
        ]
        tag_html = "".join(f'<span class="tag">{t}</span>' for t in kw_list)
        score_html = f'''<div class="card" style="background:#fffbeb">
  <span class="badge" style="background:#fef3c7;color:#92400e">📊 이번 달 운세 지수</span>
  <div style="margin-top:10px">
    {_zodiac_score_bar("종합운","🌟",total)}
    {_zodiac_score_bar("금전운","💰",money)}
    {_zodiac_score_bar("건강운","💪",health)}
    {_zodiac_score_bar("애정운","❤️",love)}
  </div>
</div>'''

        content_html = f"""{style()}
<div class="wrap">
  <div class="hero" style="background:linear-gradient(135deg,#f59e0b,#d97706)">
    <h1>🌙 {c['emoji']} {c['kr']} 월간운세</h1>
    <p>{month_str}</p>
    <div style="margin-top:8px;display:inline-block;background:rgba(255,255,255,0.2);padding:3px 12px;border-radius:20px;font-size:12px">{signal}</div>
  </div>
  <div id="{card_id}" class="fortune-card" style="background:linear-gradient(135deg,#f59e0b,#92400e)">
    <div class="fc-emoji">{c['emoji']}</div>
    <div class="fc-title">{c['kr']} 월간운세</div>
    <div class="fc-sub">{month_str}</div>
    <div class="fc-stars">{rating}</div>
    <div class="fc-text">{fortune}</div>
    <div class="fc-watermark">todayhoroscopelaboratory.blogspot.com · {month_str}</div>
  </div>
  {share_buttons(card_id, f"{c['kr']}_월간운세")}

  <!-- 대표 이미지 -->
  {post_img("monthly")}

  {score_html}
  <div class="card">
    <span class="badge">📅 {month_str} 기간별 운세</span>
    <div style="margin-top:8px">{period_html}</div>
  </div>
  <div class="card"><span class="badge">🔍 관련 키워드</span><div class="tag-cloud">{tag_html}</div></div>
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

# 스토리 연결 구조: (별자리, 띠) → (테마, 구어체 내러티브)
_CONNECT_MAP = [
    ("양자리",   "용띠",    "시작",
     "먼저 <b style='color:#5b21b6'>{z}</b>인 분들께. 오늘 아침부터 뭔가 에너지가 들끓는 느낌 받지 않으셨나요? 그 느낌 틀리지 않았어요. 마침 <b style='color:#b45309'>{c}</b>도 오늘 같은 언덕 위에 서 있어요. 두 기운이 만나면 '시작'이라는 말이 자연스럽게 떠오를 수밖에 없어요. 오래 망설였던 일이 있다면, 오늘만큼은 그냥 해보세요. 완벽하지 않아도 돼요. 첫 발이 전부니까요."),

    ("황소자리", "뱀띠",    "결실",
     "그리고 <b style='color:#5b21b6'>{z}</b>인 분들은요 — 있잖아요, 그거 알아요? 당신이 소리 없이 쌓아온 노력들, 오늘 조금씩 빛이 나기 시작해요. <b style='color:#b45309'>{c}</b>도 마찬가지예요. 두 기운 모두 오래 기다린 사람들이 받는 선물을 오늘 건네받을 차례예요. 오후에 잠깐 멈춰 서서 따뜻한 뭔가 한 잔 마시면서 스스로한테 '잘하고 있어'라고 한번만 해줘요. 그 말 한마디가 생각보다 많은 걸 바꿔놓거든요."),

    ("쌍둥이자리","토끼띠",  "아이디어",
     "<b style='color:#5b21b6'>{z}</b>는 오늘 머릿속이 좀 복잡할 수도 있어요. 이것도 하고 싶고, 저것도 하고 싶고. 근데 그게 오늘은 단점이 아니에요. <b style='color:#b45309'>{c}</b>의 유연함이 그 복잡함을 정리해줄 테니까요. 오늘 불쑥 떠오르는 아이디어, 그냥 흘려보내지 마세요. 메모 하나가 나중에 당신 인생의 방향을 바꾸는 경우, 실제로 있어요."),

    ("게자리",   "말띠",    "소통",
     "<b style='color:#5b21b6'>{z}</b>인 분들, 혹시 요즘 하고 싶은 말이 있는데 참고 있는 거 아닌가요? 오늘은 말해도 괜찮아요. <b style='color:#b45309'>{c}</b>의 에너지가 오늘 유독 담이 낮아서요. 짧은 문자 하나, 가벼운 안부 하나가 오해를 풀고 벽을 허무는 날이에요. 먼저 연락하는 사람이 오늘만큼은 이기는 날이에요."),

    ("사자자리", "원숭이띠", "카리스마",
     "<b style='color:#5b21b6'>{z}</b>인 분들은 오늘 자기도 모르게 눈에 띌 거예요. 굳이 애쓰지 않아도요. <b style='color:#b45309'>{c}</b>의 재치가 오늘 그 빛을 더 선명하게 해주거든요. 근데 있잖아요 — 빛나는 사람이 그늘도 품을 줄 알 때, 그게 진짜 카리스마예요. 오늘 그걸 보여줄 날이에요."),

    ("처녀자리", "닭띠",    "성실",
     "<b style='color:#5b21b6'>{z}</b>랑 <b style='color:#b45309'>{c}</b>는 솔직히 말하면요, 오늘 제일 열심히 사는 사람들이에요. 티도 안 내고, 묵묵히. 그 성실함이 오늘은 진짜 빛을 받아요. 완벽하지 않아도 괜찮아요. 오늘만큼은 그냥 시작한 것 자체를 스스로 칭찬해주세요."),

    ("천칭자리", "개띠",    "관계",
     "<b style='color:#5b21b6'>{z}</b>는 오늘 마음속 저울이 기분 좋게 흔들려요. <b style='color:#b45309'>{c}</b>의 따뜻하고 변함없는 기운이 그 균형을 잡아주거든요. 혹시 최근에 오해가 생긴 관계가 있나요? 오늘이 그 이야기를 꺼낼 가장 좋은 날이에요. 진심은 결국 닿아요. 정말로요."),

    ("전갈자리", "돼지띠",  "직관",
     "<b style='color:#5b21b6'>{z}</b>인 분들은 오늘 뭔가 이상하게 감이 잘 맞는 날이에요. 별 생각 없이 느낀 건데, 나중에 보면 맞는 그런 감각이요. <b style='color:#b45309'>{c}</b>의 너그러운 기운이 그 직관에 온기를 더해요. 오늘 첫 번째로 떠오르는 생각, 믿어봐요. 생각보다 정확할 거예요."),

    ("사수자리", "쥐띠",    "도전",
     "<b style='color:#5b21b6'>{z}</b>는 오늘 평소랑 조금 다른 길로 가보고 싶은 마음이 생길 거예요. 그 마음 따라가도 돼요. <b style='color:#b45309'>{c}</b>가 이미 그 길 위에 있어요. 낯선 방향에서 만나는 것들이 오늘의 행운이에요. 우연처럼 보이는 것들이 사실은 오늘 당신한테 준비된 거예요."),

    ("염소자리", "소띠",    "인내",
     "<b style='color:#5b21b6'>{z}</b>랑 <b style='color:#b45309'>{c}</b>는 오늘도 묵묵히 자기 길을 가는 사람들이에요. 결과가 아직 안 보여도, 지금 걷고 있는 방향 맞아요. 그거 알아주는 사람이 없어도 괜찮아요. 오늘 하늘이 알고 있어요. 인내는 절대 배신하지 않으니까요."),

    ("물병자리", "호랑이띠", "독창성",
     "<b style='color:#5b21b6'>{z}</b>는 오늘 '나는 좀 달라'라는 게 강점이 되는 날이에요. <b style='color:#b45309'>{c}</b>의 대담함이 그 다름에 불을 지펴줘요. 남들 다 가는 길 아니어도 돼요. 오늘만큼은 당신이 다르다는 사실이, 진짜 선물이에요."),

    ("물고기자리","양띠",   "평화",
     "그리고 마지막으로, <b style='color:#5b21b6'>{z}</b>인 분들께요. 오늘은 애쓰지 않아도 돼요. 그냥 흘러가도 돼요. <b style='color:#b45309'>{c}</b>의 평화로운 기운이 오늘 당신 곁에서 가만히 같이 있어줄 거예요. 손을 꽉 쥐지 않아도, 오늘의 선물은 손을 펴고 있을 때 조용히 내려앉으니까요."),
]

# 하루 분위기 오프닝 문장 풀 — 사람이 말을 건네는 목소리
_OMNIBUS_OPENINGS = [
    "오늘 아침, 유난히 하늘이 높아 보였다면 그건 당신 기분 탓만은 아닐 거예요. "
    "별들이 오늘따라 제자리를 딱 맞게 찾은 날이거든요. "
    "그래서 오늘은 조금 특별한 이야기를 해드리고 싶어요. "
    "당신의 별자리와 당신의 띠가, 오늘 서로 어떤 말을 주고받고 있는지에 대한 이야기요.",

    "있잖아요, 오늘 하루가 왠지 평소랑 조금 다른 느낌이 든다면요 — "
    "그 감각, 틀리지 않았어요. "
    "별자리와 띠가 오늘은 유독 가까운 거리에서 서로 손을 내밀고 있거든요. "
    "그 이야기를 들려드릴게요.",

    "하루를 시작하면서 문득 이런 생각이 들 때가 있잖아요. "
    "'오늘은 뭔가 다를 것 같다'는 그 느낌. "
    "오늘이 딱 그런 날이에요. "
    "별자리와 띠가 오늘 같은 언어로 이야기하고 있으니까요.",

    "가끔은 별자리 같은 거 믿지 않아도 괜찮아요. "
    "그냥 오늘 하루, 자기 이야기가 여기 있다는 거 알아주는 것만으로도 충분하니까요. "
    "12개의 별자리와 12개의 띠가 오늘 어떤 말을 건네고 싶은지, 같이 들어볼까요?",

    "오늘 하루가 아직 다 열리지 않은 지금, "
    "별자리와 띠가 각자의 자리에서 당신에게 뭔가를 전하려 하고 있어요. "
    "길게 말하지 않을게요. 짧지만 진심을 담아서요.",
]

# 클로징 문장 풀 — 따뜻하게 마무리하는 목소리
_OMNIBUS_CLOSINGS = [
    "별을 믿든 믿지 않든, 오늘 하루 당신이 살아있다는 것만으로도 이미 충분한 기운을 품고 있어요. "
    "오늘도 잘 부탁해요.",

    "운세는 길을 비추는 달빛 같은 거예요. "
    "방향을 알려줄 수는 있지만, 걷는 건 언제나 당신이에요. "
    "오늘 하루, 당신의 발걸음을 응원해요.",

    "별자리가 뭐라고 하든, 결국 오늘 하루를 만들어 가는 건 당신이에요. "
    "작은 것 하나라도 오늘 실천해 보세요. 그걸로 충분해요.",

    "오늘 여기까지 읽어줘서 고마워요. "
    "이 글이 당신의 하루에 작은 온기가 되었으면 좋겠어요. "
    "내일도 또 이야기해요.",

    "좋은 기운은 믿는 사람한테 먼저 와요. "
    "오늘 하루, 조금만 더 자기 자신을 믿어봐요. "
    "충분히 잘하고 있으니까요.",
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


def build_omnibus_post(today_str: str) -> tuple:
    """
    '별과 띠가 만나는 시간' — 소설 목소리 스토리텔링 포스트
    라벨: 별과띠가만나는시간
    """
    kst_dt  = now_kst()
    season  = _season_backdrop(kst_dt)
    opening = random.choice(_OMNIBUS_OPENINGS)
    closing = random.choice(_OMNIBUS_CLOSINGS)

    title = (
        f"🌙 별과 띠가 만나는 시간 {today_str} "
        f"— 오늘 당신의 별자리와 띠가 전하는 이야기"
    )

    # ── 12쌍 문단 생성 ──
    paragraphs = []
    for z_kr, c_kr, theme, tmpl in _CONNECT_MAP:
        para = tmpl.format(z=z_kr, c=c_kr)
        paragraphs.append(
            f'<p style="margin:0 0 1.7em 0;text-indent:0">{para}</p>'
        )

    # 첫 문단 드롭캡
    first_para = paragraphs[0].replace(
        '<p style="margin:0 0 1.7em 0;text-indent:0">',
        '<p style="margin:0 0 1.7em 0;text-indent:0" class="drop-cap-p">',
        1
    )
    paragraphs[0] = first_para
    story_html = "\n".join(paragraphs)

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

    card_id = (
        f"omnibus-"
        f"{today_str.replace(' ','').replace('년','').replace('월','').replace('일','')}"
    )

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
/* drop-cap via inline span — html2canvas 호환 */
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
  <div class="novel-page" id="{card_id}">

    <div class="novel-date">{today_str} · {season}</div>
    <h1 class="novel-title">🌙 별과 띠가 만나는 시간</h1>
    <p class="novel-subtitle">오늘 하늘이 당신에게 건네는 이야기</p>

    <div class="novel-rule">&middot; &middot; &middot;</div>

    <p class="novel-opening">{opening}</p>

    <div class="novel-body">
{story_html}
    </div>

    <div class="novel-rule">&middot; &middot; &middot;</div>

    <div class="novel-footer">
      {closing}
    </div>

  </div>

  {share_buttons(card_id, f"별과띠가만나는시간_{today_str}")}

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

    # 수동 실행 시 강제 포함 옵션
    force_weekly  = os.environ.get("FORCE_WEEKLY",  "false").lower() == "true"
    force_monthly = os.environ.get("FORCE_MONTHLY", "false").lower() == "true"

    # ④ 별자리 주간운세 — 매주 월요일 or 강제 실행
    if kst_now.weekday() == 0 or force_weekly:
        posts.extend(build_zodiac_weekly_post(today_str))
        label = "강제 포함" if force_weekly and kst_now.weekday() != 0 else "월요일"
        print(f"📅 별자리 주간운세 12개 포함 ({label})")
    else:
        print("📅 주간운세 스킵 (월요일 아님)")

    # ⑤ 띠별 월간운세 — 매월 1일 or 강제 실행
    if kst_now.day == 1 or force_monthly:
        posts.extend(build_chinese_monthly_post(today_str))
        label = "강제 포함" if force_monthly and kst_now.day != 1 else "1일"
        print(f"📅 띠별 월간운세 12개 포함 ({label})")
    else:
        print("📅 월간운세 스킵 (1일 아님)")

    total = len(posts)
    weekly  = " + 별자리주간 12" if kst_now.weekday() == 0 else ""
    monthly = " + 띠별월간 12"   if kst_now.day == 1        else ""
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
