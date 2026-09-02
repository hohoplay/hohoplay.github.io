#!/usr/bin/env python3
"""
grow_chinese_csv.py — 띠운세 문장 자동 확장
==========================================
grow_csv.py(별자리용)와 완전히 동일한 패턴. 매달 GitHub Actions에서 실행.
Claude API로 각 띠×타입별 새 문장 N개를 생성해 CSV에 추가한다.

기존 grow_csv.py와의 차이점은 대상이 "띠"라는 것 하나뿐이다.
CSV(data/chinese_fortune_1000.csv)가 아직 없으면 헤더만 있는 빈 파일로
자동 생성한 뒤 그 위에 문장을 쌓아올린다 — 최초 실행(시드 배치) 때는
--count를 크게 주면 됨(예: --count 20).

실행:
  python scripts/grow_chinese_csv.py               # 전체 띠 각 5개씩 추가
  python scripts/grow_chinese_csv.py --count 20    # 각 20개씩 (초기 시드 배치용)
  python scripts/grow_chinese_csv.py --chinese 쥐띠 # 특정 띠만

환경변수:
  ANTHROPIC_API_KEY   (필수 — grow_csv.py와 동일한 키 재사용)
  DATA_DIR            (기본: ./data)
"""

import os, sys, json, time, argparse
import pandas as pd
import anthropic

# ─── 설정 ───────────────────────────────────────────────
DATA_DIR  = os.environ.get('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
CSV_PATH  = os.path.join(DATA_DIR, 'chinese_fortune_1000.csv')
BACKUP_PATH = CSV_PATH.replace('.csv', '_backup.csv')

CSV_COLUMNS = ['chinese', 'type', 'fortune']

CHINESE = [
    "쥐띠", "소띠", "호랑이띠", "토끼띠", "용띠", "뱀띠",
    "말띠", "양띠", "원숭이띠", "닭띠", "개띠", "돼지띠",
]
# create_post.py의 TYPES(grow_csv.py)와 동일한 7개 타입 — 나중에 띠운세
# 일간 포스트에 애정운/금전운/직장운 섹션이 별도로 추가되더라도 바로 쓸 수 있도록
# 별자리와 동일한 구조로 맞춰둔다.
TYPES = ['총운','애정운','금전운','직장운','건강운','대인운','행동운']

# 띠별 핵심 특성 — 프롬프트 품질 유지용 (일반적으로 알려진 12지신 특성 서술)
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

TYPE_CONTEXT = {
    "총운":  "오늘 하루 전체적인 흐름, 에너지, 기회와 주의사항",
    "애정운":"연애·관계·사람 연결에 대한 오늘의 흐름",
    "금전운":"돈·소비·수입·투자에 대한 오늘의 흐름",
    "직장운":"업무·직장·성과·커리어에 대한 오늘의 흐름",
    "건강운":"신체·정신 건강, 에너지 관리에 대한 오늘의 흐름",
    "대인운":"사람 관계·소통·사회적 연결에 대한 오늘의 흐름",
    "행동운":"오늘 실제로 취해야 할 행동, 결정, 실천에 대한 안내",
}


def generate_fortunes(chinese: str, type_: str, count: int, existing: list[str]) -> list[str]:
    """Claude API로 새 띠운세 문장 생성 (grow_csv.py의 generate_fortunes()와 동일한 규칙)"""
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    existing_sample = '\n'.join(f'- {s[:80]}' for s in existing[:5])

    prompt = f"""띠운세 콘텐츠를 작성합니다.

띠: {chinese}
타입: {type_} ({TYPE_CONTEXT[type_]})
띠 특성: {TRAITS[chinese]}

[기존 문장 스타일 참고 — 이 톤과 길이를 유지하세요]
{existing_sample}

위 스타일을 참고해서 {chinese} {type_} 운세 문장을 {count}개 작성하세요.

반드시 지켜야 할 규칙:
1. 격식체 문어체만 사용 ("~합니다", "~입니다", "~됩니다", "~바랍니다", "~있습니다")
   — "~에요", "~거든요", "~봐요", "~네요", "~잖아요" 절대 금지
   — 구글은 한글을 영어로 번역 후 분석하므로 비문법적 표현은 의미가 달라질 수 있습니다
2. 첫 문장은 독자의 감정/상황에 공감하는 문장으로 시작
3. 띠 특성이 자연스럽게 녹아들어야 함
4. 한 문장이 아니라 2~4문장 연결 (100~200자)
5. "골든타임", "X시~X시" 시간대 표현 절대 금지
6. 기존 문장과 겹치지 않는 새로운 상황/관점

JSON 배열로만 응답하세요. 다른 텍스트 없이:
["문장1", "문장2", ...]"""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        if raw.startswith('['):
            result = json.loads(raw)
        else:
            raw = raw.replace('```json','').replace('```','').strip()
            result = json.loads(raw)
        return [str(s).strip() for s in result if len(str(s).strip()) > 20]
    except Exception as e:
        print(f'  ⚠️  API 오류 ({chinese} {type_}): {e}')
        return []


def grow(target_chinese: list[str], count_per: int):
    """CSV 확장 메인 함수"""
    # CSV 로드 — 없으면 헤더만 있는 빈 파일로 새로 시작 (최초 실행 시)
    if not os.path.exists(CSV_PATH):
        print(f'ℹ️  CSV 없음 — 새로 생성합니다: {CSV_PATH}')
        os.makedirs(DATA_DIR, exist_ok=True)
        df = pd.DataFrame(columns=CSV_COLUMNS)
    else:
        df = pd.read_csv(CSV_PATH)
    print(f'현재: {len(df)}개')

    # 백업 (기존 내용이 있을 때만 의미 있지만, 형식 통일을 위해 항상 저장)
    df.to_csv(BACKUP_PATH, index=False, encoding='utf-8')
    print(f'백업: {BACKUP_PATH}')

    new_rows = []
    total = len(target_chinese) * len(TYPES)
    done  = 0

    for chinese in target_chinese:
        for type_ in TYPES:
            done += 1
            existing = df[(df['chinese'] == chinese) & (df['type'] == type_)]['fortune'].tolist() if not df.empty else []
            print(f'[{done:3d}/{total}] {chinese} {type_} (기존 {len(existing)}개) → +{count_per}개 생성 중...')

            new_sents = generate_fortunes(chinese, type_, count_per, existing)
            print(f'  ✅ {len(new_sents)}개 생성')

            for s in new_sents:
                new_rows.append({
                    'chinese': chinese,
                    'type':    type_,
                    'fortune': s,
                })

            time.sleep(1)  # API rate limit 방지

    # 저장
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        result = pd.concat([df, new_df], ignore_index=True)
        result.to_csv(CSV_PATH, index=False, encoding='utf-8')
        print(f'\n✅ 완료: {len(df)}개 → {len(result)}개 (+{len(new_rows)}개)')
        print(f'띠당: {len(result) // 12}개 / 타입당: {len(result) // (12*7)}개')
    else:
        print('\n⚠️  새로 추가된 문장 없음')


def main():
    parser = argparse.ArgumentParser(description='띠운세 CSV 자동 확장')
    parser.add_argument('--chinese', type=str, default=None, help='특정 띠만 (예: 쥐띠)')
    parser.add_argument('--count',   type=int, default=5,   help='띠×타입당 추가할 문장 수 (기본 5, 초기 시드 배치 때는 크게)')
    args = parser.parse_args()

    if 'ANTHROPIC_API_KEY' not in os.environ:
        print('❌ ANTHROPIC_API_KEY 환경변수 필요')
        sys.exit(1)

    target = [args.chinese] if args.chinese else CHINESE
    print(f'대상: {target}')
    print(f'추가량: 띠×타입당 {args.count}개')
    print(f'예상 API 호출: {len(target) * len(TYPES)}회')
    print()

    grow(target, args.count)


if __name__ == '__main__':
    main()
