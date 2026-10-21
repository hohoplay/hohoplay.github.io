#!/usr/bin/env python3
"""
grow_chinese_period_csv.py — 띠별 주간/월간 문장 CSV 자동 확장
=============================================================
대상 파일 (create_post.py가 읽는 풀):
  data/chinese_weekly_1000.csv   — 별과띠가만나는시간 주간판의 '띠 주간 문장'
  data/chinese_monthly_1000.csv  — 띠별 월간운세 통합 글의 '띠 이달 문장'
CSV 열: id, animal_zodiac(영문), kr(한글 띠 이름), fortune

왜 필요한가
  기존 두 파일은 1,008줄이지만 띠 이름을 빼면 서로 다른 문장이 8개뿐이라
  글마다 같은 문장이 반복되었다. 이 스크립트가
    ① 이름만 다른 중복 문장을 정리하고 (기존 문장은 첫 1개씩만 남김)
    ② Claude API로 띠 × 영역(관계/일/돈/건강/마음가짐/생활습관)별 새 문장을 생성해 추가한다.

실행:
  python scripts/grow_chinese_period_csv.py --kind both --count 3     # 주간+월간, 띠×영역당 3개
  python scripts/grow_chinese_period_csv.py --kind weekly --count 5
  python scripts/grow_chinese_period_csv.py --kind monthly --chinese 쥐띠
  python scripts/grow_chinese_period_csv.py --kind both --dry-run     # API 호출 없이 중복 정리 결과만 확인

환경변수:
  ANTHROPIC_API_KEY   (필수, --dry-run 제외 — grow_csv.py와 동일한 키 재사용)
  DATA_DIR            (기본: ./data)
"""

import os, re, sys, json, time, argparse
import pandas as pd

DATA_DIR = os.environ.get('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))

KINDS = {
    'weekly':  {'file': 'chinese_weekly_1000.csv',  'period': '이번 주', 'other': '이번 달'},
    'monthly': {'file': 'chinese_monthly_1000.csv', 'period': '이번 달', 'other': '이번 주'},
}

CHINESE = [
    ("rat", "쥐띠"), ("ox", "소띠"), ("tiger", "호랑이띠"), ("rabbit", "토끼띠"),
    ("dragon", "용띠"), ("snake", "뱀띠"), ("horse", "말띠"), ("sheep", "양띠"),
    ("monkey", "원숭이띠"), ("rooster", "닭띠"), ("dog", "개띠"), ("pig", "돼지띠"),
]
# 주의: create_post.py·기존 CSV 모두 양띠의 영문 이름이 'sheep'이다 (goat 아님)

AREAS = {
    "관계":     "가까운 사람과의 대화, 오해, 거리감, 새로운 인연에 대한 흐름",
    "일":       "업무 방식, 성과, 협업, 우선순위에 대한 흐름",
    "돈":       "지출 습관, 저축, 큰 결정 앞에서의 태도에 대한 흐름",
    "건강":     "컨디션, 수면, 식사, 몸이 보내는 신호에 대한 흐름",
    "마음가짐": "감정의 기복, 스스로를 대하는 태도, 불안과 자신감에 대한 흐름",
    "생활습관": "정리, 루틴, 작은 실천, 일상에서 바꿔볼 만한 습관에 대한 흐름",
}

TRAITS = {
    "쥐띠":     "영리하고 기민하며 정보 수집에 능함. 순발력, 재치, 임기응변, 계산적으로 보일 수 있음",
    "소띠":     "성실하고 묵묵하며 끈기가 강함. 인내심, 근면함, 우직함, 융통성 부족",
    "호랑이띠": "용맹하고 추진력이 강하며 독립심이 강함. 결단력, 카리스마, 자존심, 성급함",
    "토끼띠":   "온화하고 섬세하며 평화를 중시함. 배려심, 눈치, 사교성, 우유부단",
    "용띠":     "포부가 크고 자신감이 넘치며 카리스마가 강함. 리더십, 열정, 자존심, 과시욕",
    "뱀띠":     "직관이 예리하고 신중하며 통찰력이 깊음. 분석력, 침착함, 경계심, 속내를 잘 안 보임",
    "말띠":     "자유롭고 활동적이며 사교성이 좋음. 열정, 추진력, 변덕, 인내심 부족",
    "양띠":     "온순하고 예술적 감성이 풍부하며 배려심이 깊음. 공감능력, 섬세함, 소심함, 의존적",
    "원숭이띠": "재치 있고 영리하며 융통성이 뛰어남. 순발력, 창의력, 잔꾀, 산만함",
    "닭띠":     "정확하고 부지런하며 자기관리가 철저함. 계획성, 완벽주의, 잔소리, 고집",
    "개띠":     "충성심이 강하고 정의감이 있으며 책임감이 강함. 신뢰, 의리, 걱정이 많음, 고지식함",
    "돼지띠":   "너그럽고 낙천적이며 포용력이 큼. 관대함, 성실함, 순진함, 우유부단",
}

BAD_ENDINGS = ("에요", "예요", "거든요", "네요", "잖아요", "봐요", "해요", "세요", "어요", "아요")
BAD_WORDS = re.compile(r"오늘|내일|어제|오전|오후|아침|저녁|점심|새벽|골든타임|\d{1,2}\s*시")


def _norm(text: str, kr: str) -> str:
    """띠 이름과 공백만 다른 같은 문장을 같은 것으로 보기 위한 정규화"""
    t = str(text).replace(kr, "X")
    return re.sub(r"\s+", "", t)


def is_valid(sentence: str, period: str, other: str) -> bool:
    s = sentence.strip()
    if not (40 <= len(s) <= 260):
        return False
    if not s.endswith(("다.", "다!", "다")):
        return False
    if BAD_WORDS.search(s):
        return False
    if other in s:                         # 주간 문장에 '이번 달', 월간 문장에 '이번 주'가 섞이면 제외
        return False
    if period not in s:                    # 기간 표현이 없으면 주간/월간 글에 맞지 않음
        return False
    for sent in re.split(r"(?<=[.!?])\s+", s):
        body = sent.strip().rstrip(".!?")
        if body.endswith(BAD_ENDINGS):
            return False
    return True


def generate(kr: str, area: str, kind: str, count: int, samples: list) -> list:
    """Claude API로 새 문장 생성 — 실패하면 빈 목록"""
    import anthropic
    cfg = KINDS[kind]
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    sample_txt = '\n'.join(f'- {s[:90]}' for s in samples[:4])
    prompt = f"""띠별 {'주간' if kind == 'weekly' else '월간'} 운세 문장을 작성합니다.

띠: {kr}
영역: {area} ({AREAS[area]})
띠 특성: {TRAITS[kr]}
기간 표현: 반드시 "{cfg['period']}"을(를) 문장 안에 한 번 이상 사용

[기존 문장 참고 — 이 톤과 길이를 유지하되 내용은 겹치지 않게]
{sample_txt}

{kr} {area} 문장을 {count}개 작성하세요.

반드시 지켜야 할 규칙:
1. 격식체 문어체만 사용 ("~합니다", "~입니다", "~됩니다", "~바랍니다", "~있습니다")
   — "~에요", "~거든요", "~네요", "~잖아요", "~세요" 절대 금지
2. 문장은 띠 이름으로 시작하지 마세요 (앞에 띠 이름이 따로 붙습니다). 상황이나 기간 표현으로 시작하세요.
3. 2문장, 70~150자. 첫 문장은 상황을 짚고 둘째 문장은 구체적인 실천을 제안합니다.
4. 띠 특성이 자연스럽게 드러나야 하고, {count}개가 서로 다른 상황·관점이어야 합니다.
5. "오늘", "내일", "오전", "오후", "아침", "저녁", "X시" 같은 하루·시간대 표현 절대 금지.
6. "{cfg['other']}" 표현 금지.
7. 과도한 단정이나 불안을 부추기는 표현 금지 (재미로 보는 운세).

JSON 배열로만 응답하세요. 다른 텍스트 없이:
["문장1", "문장2", ...]"""
    try:
        max_tokens = min(8000, max(1500, count * 300 + 600))
        msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=max_tokens,
                                     messages=[{"role": "user", "content": prompt}])
        raw = msg.content[0].text.strip().replace('```json', '').replace('```', '').strip()
        return [str(x).strip() for x in json.loads(raw)]
    except Exception as e:
        print(f'  ⚠️  API 오류 ({kr} {area}): {e}')
        return []


def load_and_dedupe(path: str) -> pd.DataFrame:
    """CSV 로드 후 '이름만 다른 같은 문장'을 정리 — 띠마다 서로 다른 문장만 1개씩 남긴다"""
    cols = ['id', 'animal_zodiac', 'kr', 'fortune']
    if not os.path.exists(path):
        print(f'ℹ️  CSV 없음 — 새로 만듭니다: {path}')
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(path)
    before = len(df)
    keep = []
    seen = set()
    for _, r in df.iterrows():
        key = (r['kr'], _norm(r['fortune'], r['kr']))
        if key in seen:
            continue
        seen.add(key)
        keep.append(r)
    out = pd.DataFrame(keep, columns=df.columns)
    print(f'  기존 {before}줄 → 중복 정리 후 {len(out)}줄')
    return out


def grow_one(kind: str, targets: list, count: int, dry_run: bool):
    cfg = KINDS[kind]
    path = os.path.join(DATA_DIR, cfg['file'])
    print(f"\n=== {kind} ({cfg['file']}) ===")
    df = load_and_dedupe(path)
    backup = path.replace('.csv', '_backup.csv')
    if os.path.exists(path):
        pd.read_csv(path).to_csv(backup, index=False, encoding='utf-8')
        print(f'  백업: {backup}')
    if dry_run:
        print('  (dry-run) API 호출·저장 없이 종료')
        return

    en_of = dict((kr, en) for en, kr in CHINESE)
    new_rows, total, done = [], len(targets) * len(AREAS), 0
    for kr in targets:
        for area in AREAS:
            done += 1
            pool = df[df['kr'] == kr]['fortune'].tolist() + [r['fortune'] for r in new_rows if r['kr'] == kr]
            seen = {_norm(x, kr) for x in pool}
            print(f'  [{done:3d}/{total}] {kr} {area} (기존 {len(pool)}개) → +{count}개 생성 중...')
            made = generate(kr, area, kind, count, pool[-4:] if pool else [])
            ok = 0
            for s in made:
                if is_valid(s, cfg['period'], cfg['other']) and _norm(s, kr) not in seen:
                    seen.add(_norm(s, kr))
                    new_rows.append({'animal_zodiac': en_of[kr], 'kr': kr, 'fortune': s})
                    ok += 1
            print(f'    ✅ {ok}/{len(made)}개 통과')
            time.sleep(1)

    if not new_rows:
        print('⚠️  새로 추가된 문장 없음 — 위 "API 오류" 로그를 확인하세요.')
        if df.empty:
            print('❌ 기존 데이터도 없는 상태에서 전부 실패 — 중단합니다.')
            sys.exit(1)
    result = pd.concat([df.drop(columns=['id'], errors='ignore'), pd.DataFrame(new_rows)], ignore_index=True)
    result = result.sort_values(by='kr', key=lambda s: s.map({kr: i for i, (_, kr) in enumerate(CHINESE)}), kind='stable')
    result.insert(0, 'id', range(1, len(result) + 1))
    result.to_csv(path, index=False, encoding='utf-8')
    print(f'  ✅ 저장: {len(result)}줄 (띠당 약 {len(result) // 12}개)')


def main():
    ap = argparse.ArgumentParser(description='띠별 주간/월간 문장 CSV 중복 정리 + 자동 확장')
    ap.add_argument('--kind', choices=['weekly', 'monthly', 'both'], default='both')
    ap.add_argument('--chinese', type=str, default=None, help='특정 띠만 (예: 쥐띠)')
    ap.add_argument('--count', type=int, default=3, help='띠×영역당 추가할 문장 수 (영역 6개 → 띠당 6×count개)')
    ap.add_argument('--dry-run', action='store_true', help='API 호출 없이 중복 정리 결과만 확인')
    a = ap.parse_args()
    if not a.dry_run and 'ANTHROPIC_API_KEY' not in os.environ:
        print('❌ ANTHROPIC_API_KEY 환경변수 필요')
        sys.exit(1)
    targets = [a.chinese] if a.chinese else [kr for _, kr in CHINESE]
    for kind in (['weekly', 'monthly'] if a.kind == 'both' else [a.kind]):
        grow_one(kind, targets, a.count, a.dry_run)


if __name__ == '__main__':
    main()
