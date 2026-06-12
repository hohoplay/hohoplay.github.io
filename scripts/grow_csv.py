#!/usr/bin/env python3
"""
grow_csv.py — 별자리 운세 문장 자동 확장
==========================================
매달 GitHub Actions에서 실행.
Claude API로 각 별자리×타입별 새 문장 N개를 생성해 CSV에 추가.

실행:
  python scripts/grow_csv.py              # 전체 별자리 각 5개씩 추가
  python scripts/grow_csv.py --count 10  # 각 10개씩
  python scripts/grow_csv.py --zodiac 양자리  # 특정 별자리만

환경변수:
  ANTHROPIC_API_KEY   (필수)
  DATA_DIR            (기본: ./data)
"""

import os, sys, json, time, argparse
import pandas as pd
import anthropic

# ─── 설정 ───────────────────────────────────────────────
DATA_DIR  = os.environ.get('DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
CSV_PATH  = os.path.join(DATA_DIR, 'zodiac_fortune_1000.csv')
BACKUP_PATH = CSV_PATH.replace('.csv', '_backup.csv')

ZODIACS = [
    "양자리","황소자리","쌍둥이자리","게자리","사자자리","처녀자리",
    "천칭자리","전갈자리","사수자리","염소자리","물병자리","물고기자리"
]
TYPES = ['총운','애정운','금전운','직장운','건강운','대인운','행동운']

# 별자리별 핵심 특성 — 프롬프트 품질 유지용
TRAITS = {
    "양자리":    "시작은 빠르고 에너지가 넘치지만 중간에 흥미를 잃거나 여러 개를 동시에 시작하는 패턴. 직감, 추진력, 충동적 결정, 기다리기 힘들어함",
    "황소자리":  "천천히 움직이지만 한번 시작하면 끝까지 가는 타입. 안정·편안함 추구, 꾸준함, 고집, 변화 거부",
    "쌍둥이자리":"호기심 많고 말이 빠르며 동시에 여러 생각이 돌아감. 소통 능력, 적응력, 집중력 분산, 변덕",
    "게자리":    "감정이 풍부하고 가족·친밀한 관계를 중시. 공감능력, 배려, 감정 기복, 상처를 오래 안고 있음",
    "사자자리":  "존재감이 강하고 인정받고 싶어하며 무대 위에서 빛나는 타입. 카리스마, 리더십, 인정 욕구, 자존심",
    "처녀자리":  "꼼꼼하고 분석적이며 완벽을 추구. 분석력, 성실함, 완벽주의로 인한 지연, 과도한 자기비판",
    "천칭자리":  "균형과 조화를 추구하며 관계를 소중히 여김. 사교성, 공정함, 우유부단, 갈등 회피",
    "전갈자리":  "깊고 강렬하며 직관이 예리함. 통찰력, 집중력, 집착, 의심, 감정 표현 어려움",
    "사수자리":  "자유와 모험을 사랑하고 낙관적. 낙관성, 철학적 사고, 모험심, 약속 잊음, 집중 부족",
    "염소자리":  "목표 지향적이고 성실하며 인내심이 강함. 인내, 책임감, 일 중독, 융통성 부족",
    "물병자리":  "독창적이고 혁신적이며 틀에 박히는 걸 싫어함. 독창성, 분석력, 감정 표현 어색함, 고집스러운 자기 논리",
    "물고기자리":"감수성이 풍부하고 공감 능력이 높음. 공감, 창의성, 직관, 현실 도피, 경계 설정 어려움",
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


def generate_fortunes(zodiac: str, type_: str, count: int, existing: list[str]) -> list[str]:
    """Claude API로 새 운세 문장 생성"""
    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

    existing_sample = '\n'.join(f'- {s[:80]}' for s in existing[:5])

    prompt = f"""별자리 운세 콘텐츠를 작성합니다.

별자리: {zodiac}
타입: {type_} ({TYPE_CONTEXT[type_]})
별자리 특성: {TRAITS[zodiac]}

[기존 문장 스타일 참고 — 이 톤과 길이를 유지하세요]
{existing_sample}

위 스타일을 참고해서 {zodiac} {type_} 운세 문장을 {count}개 작성하세요.

반드시 지켜야 할 규칙:
1. 격식체 문어체만 사용 ("~합니다", "~입니다", "~됩니다", "~바랍니다", "~있습니다")
   — "~에요", "~거든요", "~봐요", "~네요", "~잖아요" 절대 금지
   — 구글은 한글을 영어로 번역 후 분석하므로 비문법적 표현은 의미가 달라질 수 있습니다
2. 첫 문장은 독자의 감정/상황에 공감하는 문장으로 시작
3. 별자리 특성이 자연스럽게 녹아들어야 함
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
        # JSON 파싱
        if raw.startswith('['):
            result = json.loads(raw)
        else:
            # 백틱 제거
            raw = raw.replace('```json','').replace('```','').strip()
            result = json.loads(raw)
        return [str(s).strip() for s in result if len(str(s).strip()) > 20]
    except Exception as e:
        print(f'  ⚠️  API 오류 ({zodiac} {type_}): {e}')
        return []


def grow(target_zodiacs: list[str], count_per: int):
    """CSV 확장 메인 함수"""
    # CSV 로드
    if not os.path.exists(CSV_PATH):
        print(f'❌ CSV 없음: {CSV_PATH}')
        sys.exit(1)

    df = pd.read_csv(CSV_PATH)
    print(f'현재: {len(df)}개')

    # 백업
    df.to_csv(BACKUP_PATH, index=False, encoding='utf-8')
    print(f'백업: {BACKUP_PATH}')

    new_rows = []
    total = len(target_zodiacs) * len(TYPES)
    done  = 0

    for zodiac in target_zodiacs:
        ct_row = df[df['zodiac'] == zodiac].iloc[0] if not df[df['zodiac'] == zodiac].empty else None
        contact_time   = ct_row['contact_time']   if ct_row is not None else ''
        contact_reason = ct_row['contact_reason'] if ct_row is not None else ''

        for type_ in TYPES:
            done += 1
            existing = df[(df['zodiac'] == zodiac) & (df['type'] == type_)]['fortune'].tolist()
            print(f'[{done:3d}/{total}] {zodiac} {type_} (기존 {len(existing)}개) → +{count_per}개 생성 중...')

            new_sents = generate_fortunes(zodiac, type_, count_per, existing)
            print(f'  ✅ {len(new_sents)}개 생성')

            for s in new_sents:
                new_rows.append({
                    'zodiac':         zodiac,
                    'type':           type_,
                    'fortune':        s,
                    'contact_time':   contact_time,
                    'contact_reason': contact_reason,
                })

            time.sleep(1)  # API rate limit 방지

    # 저장
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        result = pd.concat([df, new_df], ignore_index=True)
        result.to_csv(CSV_PATH, index=False, encoding='utf-8')
        print(f'\n✅ 완료: {len(df)}개 → {len(result)}개 (+{len(new_rows)}개)')
        print(f'별자리당: {len(result) // 12}개 / 타입당: {len(result) // (12*7)}개')
    else:
        print('\n⚠️  새로 추가된 문장 없음')


def main():
    parser = argparse.ArgumentParser(description='별자리 운세 CSV 자동 확장')
    parser.add_argument('--zodiac', type=str, default=None, help='특정 별자리만 (예: 양자리)')
    parser.add_argument('--count',  type=int, default=5,   help='별자리×타입당 추가할 문장 수 (기본 5)')
    args = parser.parse_args()

    if 'ANTHROPIC_API_KEY' not in os.environ:
        print('❌ ANTHROPIC_API_KEY 환경변수 필요')
        sys.exit(1)

    target = [args.zodiac] if args.zodiac else ZODIACS
    print(f'대상: {target}')
    print(f'추가량: 별자리×타입당 {args.count}개')
    print(f'예상 API 호출: {len(target) * len(TYPES)}회')
    print()

    grow(target, args.count)


if __name__ == '__main__':
    main()
