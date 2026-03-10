"""
blog_generator.py — Claude API로 블로그 글 자동 생성
역할: sheets_client에서 타겟 ✅ 툴을 읽어 6가지 유형(B/C/D/E) 중 하나를
      랜덤으로 선택해 블로그 초안을 생성하고, 결과를 Google Sheets
      '블로그 콘텐츠' 시트에 저장한다. (A=키워드리서치, F=SEO마무리는 제외)

유형 가중치 (같은 ai_category 동료 툴 수에 따라 동적 조정):
  B(리뷰): 40% / C(비교): 20% / D(대안): 20% / E(순위): 20%
  동료 부족 시 해당 가중치는 B로 귀속

실행: python blog_generator.py
"""

import os
import random
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from sheets_client import SheetsClient

# .env 로드
_SCRIPT_DIR = Path(__file__).parent
load_dotenv(_SCRIPT_DIR / ".env")

# Claude 모델
MODEL = "claude-opus-4-5"
MAX_TOKENS = 4096

# ──────────────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────────────

def _slug(name: str) -> str:
    """툴이름 → URL-safe slug."""
    return name.lower().replace(" ", "-").replace("_", "-")


def _utm(name: str) -> str:
    """UTM 파라미터가 포함된 어필리에이트 URL 반환."""
    s = _slug(name)
    return (
        f"https://{s}.com/"
        f"?ref=ai-itda&utm_source=ai-itda&utm_medium=referral&utm_campaign={s}"
    )


def _price_note(price: str) -> str:
    """가격에 $ 포함 시 원화 환산 힌트 반환."""
    if "$" in price:
        return "(달러 가격은 원화로 환산해서 병기: 예 $29/월 ≈ ₩39,000/월)"
    return ""


def _peers(tool: dict, all_tools: list[dict]) -> list[dict]:
    """같은 ai_category이고 이름이 다른 툴 목록 반환."""
    cat = tool.get("ai_category", "").strip()
    if not cat:
        return []
    return [
        t for t in all_tools
        if t.get("ai_category", "").strip() == cat
        and t.get("name", "").strip() != tool.get("name", "").strip()
    ]


# ──────────────────────────────────────────────────────
# 공통 규칙 (모든 프롬프트에 포함)
# ──────────────────────────────────────────────────────

_COMMON_RULES = """
## 공통 필수 규칙
- **제휴 공개 문구** (글 맨 위): > 이 글에는 제휴 링크가 포함되어 있습니다.
- **모든 외부 링크 형식**: https://도구.com/?ref=ai-itda&utm_source=ai-itda&utm_medium=referral&utm_campaign={{tool-slug}}
- **CTA 버튼 표기**: [CTA 버튼] 텍스트: "{{툴명}} 무료로 시작하기 →"
- **가격 표기**: $12/월 (≈₩16,000/월) — 달러+원화 반드시 병기
- **금지 표현**: "~인 것 같습니다", "아마도", "~인 듯합니다" (단정 표현만 사용)
- **이미지 태그**: [이미지: 설명] 형식으로 3곳 이상 배치
- **1인칭 경험 표현**: "제가 직접 써봤을 때", "테스트해보니" 포함
- **문장 길이**: 2~3줄 이내, 단락 4줄 이내로 끊기
- **SEO 구조**: H1 1개(메인 키워드 포함), H2 4~6개(보조 키워드 포함)
"""


# ──────────────────────────────────────────────────────
# 프롬프트 빌더 — 유형 B (리뷰 글)
# ──────────────────────────────────────────────────────

def build_prompt_B(tool: dict) -> str:
    """유형 B: 단일 툴 심층 리뷰 (2,500~3,000자)."""
    name     = tool.get("name", "")
    tagline  = tool.get("tagline", "")
    ai_cat   = tool.get("ai_category", "")
    price    = tool.get("price", "정보 없음")
    saves    = tool.get("saves", "")
    released = tool.get("released", "")
    utm_url  = _utm(name)
    p_note   = _price_note(price)

    return f"""당신은 AI있다(ai-itda.com) 블로그의 전문 에디터입니다.
아래 AI 툴에 대해 한국 영상/글 크리에이터를 타겟으로 하는 SEO 최적화 리뷰 글을 작성하세요.

## 툴 정보
- 이름: {name}
- 설명: {tagline}
- AI있다 카테고리: {ai_cat}
- 가격: {price} {p_note}
- 저장수(인기 지표): {saves}
- 출시: {released}
- 어필리에이트 URL: {utm_url}
{_COMMON_RULES}
## 글 구조 (순서대로 모두 포함, 목표 2,500~3,000자)

> 이 글에는 제휴 링크가 포함되어 있습니다.

### H1 제목 형식
{name} 리뷰: [tagline 핵심 혜택 한국어 요약], 실제로 써보니 이랬습니다 (2026)

### 3줄 요약 (결론 먼저)
- **이런 분께 추천**: (구체적 타겟 1줄)
- **이런 분께 비추천**: (한계 상황 1줄)
- **한 줄 결론**: (명확한 판단)
[CTA 버튼] 텍스트: "{name} 무료로 시작하기 →" → {utm_url}

### {name}이란? (H2)
200자 이내 간결한 소개.

### 핵심 기능 3가지 (H2)
각 기능: 소제목 + 150자 설명 + 1인칭 경험 + 수치 포함
[이미지: 기능 화면] 태그 삽입
[CTA 버튼] 텍스트: "{name} 기능 확인하기 →" → {utm_url}

### 가격 및 플랜 비교 (H2)
마크다운 표: | 플랜 | 월 비용 | 포함 기능 | 추천 대상 |
USD + KRW 병기, 무료 체험 여부 명시
[CTA 버튼] 텍스트: "{name} 가격 확인하기 →" → {utm_url}

### 솔직한 장단점 (H2)
✅ 장점 3~4개 / ❌ 단점 2~3개 (솔직하게)

### 어떤 사람에게 적합한가? (H2)
한국 크리에이터 맥락의 구체적 사용 시나리오 3가지

### 자주 묻는 질문 FAQ (H2)
5개 Q&A (실제 사용자가 궁금해할 내용)

### 최종 평점 및 결론 (H2)
마크다운 표: | 항목 | 평점 | (기능 완성도/가성비/사용 편의성/한국어 지원/종합)
2~3문장 최종 결론
[CTA 버튼] 텍스트: "{name} 지금 시작하기 →" → {utm_url}

위 구조를 반드시 지켜서 완성된 블로그 글 전문을 작성하세요. H1 제목부터 끊김 없이 출력하세요."""


# ──────────────────────────────────────────────────────
# 프롬프트 빌더 — 유형 C (비교 글)
# ──────────────────────────────────────────────────────

def build_prompt_C(tool_a: dict, tool_b: dict) -> str:
    """유형 C: 두 툴 비교 글 (2,000~2,500자)."""
    na, nb      = tool_a.get("name", ""), tool_b.get("name", "")
    pa, pb      = tool_a.get("price", "정보 없음"), tool_b.get("price", "정보 없음")
    ta, tb      = tool_a.get("tagline", ""), tool_b.get("tagline", "")
    ai_cat      = tool_a.get("ai_category", "")
    utm_a, utm_b = _utm(na), _utm(nb)

    return f"""당신은 AI있다(ai-itda.com) 블로그의 전문 에디터입니다.
한국 영상/글 크리에이터를 타겟으로 아래 두 AI 툴을 비교하는 SEO 최적화 글을 작성하세요.

## 툴 정보
- 툴 A: {na} — {ta} (가격: {pa}) {_price_note(pa)}
  어필리에이트 URL: {utm_a}
- 툴 B: {nb} — {tb} (가격: {pb}) {_price_note(pb)}
  어필리에이트 URL: {utm_b}
- 카테고리: {ai_cat}
{_COMMON_RULES}
## 글 구조 (순서대로 모두 포함, 목표 2,000~2,500자)

> 이 글에는 제휴 링크가 포함되어 있습니다.

### H1 제목 형식
{na} vs {nb}: 2026년 완벽 비교 — 어떤 걸 선택해야 할까?

### 3줄 요약 (결론 먼저) (H2)
**{na}이 나은 경우** (구체적 상황 3가지)
**{nb}이 나은 경우** (구체적 상황 3가지)
[CTA 버튼 A] 텍스트: "{na} 무료 체험 →" → {utm_a}
[CTA 버튼 B] 텍스트: "{nb} 무료 체험 →" → {utm_b}

### 한눈에 보는 비교표 (H2)
마크다운 표: | 항목 | {na} | {nb} |
항목: 시작 가격/무료 플랜/한국어 지원/주요 강점/추천 대상

### {na} 핵심 특징 (H2)
강점 위주 200자, 1인칭 경험 포함
[이미지: {na} 화면]
[CTA 버튼] 텍스트: "{na} 자세히 보기 →" → {utm_a}

### {nb} 핵심 특징 (H2)
강점 위주 200자, 1인칭 경험 포함
[이미지: {nb} 화면]
[CTA 버튼] 텍스트: "{nb} 자세히 보기 →" → {utm_b}

### 기능별 상세 비교 (H2)
하위 항목별 비교 (영상 품질/가격/사용 편의성/한국어 지원/고객 지원)
각 항목 끝에 "**승자**: {{툴명}} — 이유" 명시

### 사용 목적별 최종 추천 (H2)
3가지 사용 시나리오별 추천 + 각 CTA

### 자주 묻는 질문 FAQ (H2)
3개 Q&A

### 최종 결론 (H2)
나라면 이렇게 선택하겠다 (상황별 명확한 결론)
[CTA 버튼 A] 텍스트: "{na} 무료 체험 →" → {utm_a}
[CTA 버튼 B] 텍스트: "{nb} 무료 체험 →" → {utm_b}

위 구조를 반드시 지켜서 완성된 블로그 글 전문을 작성하세요. H1 제목부터 끊김 없이 출력하세요."""


# ──────────────────────────────────────────────────────
# 프롬프트 빌더 — 유형 D (대안 글)
# ──────────────────────────────────────────────────────

def build_prompt_D(main_tool: dict, alternatives: list[dict]) -> str:
    """유형 D: 유명 툴 대안 소개 글 (2,500~3,000자)."""
    main_name = main_tool.get("name", "")
    ai_cat    = main_tool.get("ai_category", "")
    n         = len(alternatives)

    alt_lines = "\n".join(
        f"  - {t['name']}: {t.get('tagline','')} (가격: {t.get('price','정보 없음')}) {_price_note(t.get('price',''))}\n"
        f"    어필리에이트 URL: {_utm(t['name'])}"
        for t in alternatives
    )

    return f"""당신은 AI있다(ai-itda.com) 블로그의 전문 에디터입니다.
한국 영상/글 크리에이터를 타겟으로 '{main_name}'의 대안 툴을 소개하는 SEO 최적화 글을 작성하세요.

## 툴 정보
- 원본 툴(이탈 대상): {main_name}
- 카테고리: {ai_cat}
- 대안 툴 {n}개:
{alt_lines}
{_COMMON_RULES}
## 글 구조 (순서대로 모두 포함, 목표 2,500~3,000자)

> 이 글에는 제휴 링크가 포함되어 있습니다.

### H1 제목 형식
{main_name} 대안 TOP {n}: 더 저렴하고 쉬운 AI 툴 비교 (2026)
(이탈 이유를 제목에 녹여서 자연스럽게 작성)

### {main_name}을 대신할 이유 (H2)
이탈 이유 3가지 (가격/한국어 미지원/기능 한계 등 현실적으로 추정)

### 한눈에 보는 대안 비교표 (H2)
마크다운 표: | 툴 | 시작 가격 | 무료 플랜 | 주요 강점 | 추천 대상 |
USD + KRW 병기

### 각 대안 툴 상세 소개 (H2, 각 툴마다)
(대안 {n}개를 1위부터 순위 매겨서 각각)
- 한 줄 포지셔닝
- 이런 분에게 추천 (3가지)
- 핵심 기능 3가지
- 원본 툴과 가격 비교
- 단점 1가지 (솔직하게)
- [이미지: 해당 툴 화면]
- [CTA 버튼] 텍스트: "{{툴명}} 무료로 시작하기 →" → {{UTM URL}}

### 나에게 맞는 대안 고르는 방법 (H2)
목적별 / 예산별 / 경험 수준별 추천

### {main_name}이 그래도 나은 경우 (H2)
신뢰도 ↑ — 원본 툴이 더 나은 케이스 솔직하게 언급

### 자주 묻는 질문 FAQ (H2)
4개 Q&A

### 최종 추천 2픽 (H2)
가성비 최우선 / 기능 완성도 기준으로 2개 최종 추천 + CTA

위 구조를 반드시 지켜서 완성된 블로그 글 전문을 작성하세요. H1 제목부터 끊김 없이 출력하세요."""


# ──────────────────────────────────────────────────────
# 프롬프트 빌더 — 유형 E (순위/리스트 글)
# ──────────────────────────────────────────────────────

def build_prompt_E(tools: list[dict]) -> str:
    """유형 E: 카테고리별 TOP N 순위 글 (3,000~3,500자)."""
    if not tools:
        return ""

    ai_cat = tools[0].get("ai_category", "AI 툴")
    n      = len(tools)

    tool_lines = "\n".join(
        f"  - {t['name']}: {t.get('tagline','')} (가격: {t.get('price','정보 없음')}) {_price_note(t.get('price',''))}\n"
        f"    어필리에이트 URL: {_utm(t['name'])}"
        for t in tools
    )

    return f"""당신은 AI있다(ai-itda.com) 블로그의 전문 에디터입니다.
한국 영상/글 크리에이터를 타겟으로 '{ai_cat}' 카테고리 최고의 툴 순위 글을 작성하세요.

## 툴 정보 ({n}개 — 순위는 AI가 판단해서 배정)
{tool_lines}
{_COMMON_RULES}
## 글 구조 (순서대로 모두 포함, 목표 3,000~3,500자)

> 이 글에는 제휴 링크가 포함되어 있습니다.

### H1 제목 형식
2026년 최고의 {ai_cat} TOP {n}: 직접 써본 솔직 비교

### 이 글을 쓴 이유 + 선정 기준 (H2)
평가 기준: 기능 완성도 / 가성비 / 사용 편의성 / 한국어 지원
1인칭 경험 ("지난 X개월간 N개 이상의 툴을 직접 사용해봤습니다" 형식)

### 빠른 비교표 (H2)
마크다운 표: | 순위 | 툴 | 시작 가격 | 무료 플랜 | 주요 특징 | 평점 |
🥇🥈🥉 이모지 활용, USD + KRW 병기

### 각 순위별 상세 소개 (H2, 각 툴마다)
(1위부터 N위까지 각각)
- ⭐ 평점: X.X/5
- 💰 시작 가격: $X/월 (≈₩X)
- 이런 분에게 추천 (bullet)
- 핵심 기능 3가지
- 장점 2~3개 / 단점 1개 (솔직하게)
- [이미지: 해당 툴 화면]
- [CTA 버튼] 텍스트: "{{툴명}} 무료로 시작하기 →" → {{UTM URL}}

### 목적별 최종 추천 (H2)
유튜브 영상 / 마케팅 광고 / 교육 콘텐츠 / 예산 0원 / 초보자
각 시나리오마다 추천 툴 + CTA

### 자주 묻는 질문 FAQ (H2)
5개 Q&A (한국어 지원, 무료 플랜, 초보자 추천 등)

### 마치며 (H2)
업데이트 날짜 명시, 최종 CTA
[CTA 버튼] 텍스트: "1위 {{툴명}} 무료 체험 →" → {{UTM URL}}

위 구조를 반드시 지켜서 완성된 블로그 글 전문을 작성하세요. H1 제목부터 끊김 없이 출력하세요."""


# ──────────────────────────────────────────────────────
# 유형 선택 로직
# ──────────────────────────────────────────────────────

def select_blog_type(tool: dict, all_tools: list[dict]) -> str:
    """
    같은 ai_category 동료 수에 따라 가중 랜덤으로 블로그 유형 선택.
    B=40% / C=20%(peer≥1) / D=20%(peer≥2) / E=20%(peer≥3)
    부적격 가중치는 B로 귀속.
    반환: "B" | "C" | "D" | "E"
    """
    peer_count = len(_peers(tool, all_tools))

    weights = {"B": 40, "C": 0, "D": 0, "E": 0}

    if peer_count >= 1:
        weights["C"] = 20
    else:
        weights["B"] += 20

    if peer_count >= 2:
        weights["D"] = 20
    else:
        weights["B"] += 20

    if peer_count >= 3:
        weights["E"] = 20
    else:
        weights["B"] += 20

    types  = list(weights.keys())
    probs  = [weights[t] for t in types]
    chosen = random.choices(types, weights=probs, k=1)[0]

    print(f"  📝 블로그 유형 선택: {chosen} (동료 {peer_count}개, 가중치 B:{weights['B']} C:{weights['C']} D:{weights['D']} E:{weights['E']})")
    return chosen


# ──────────────────────────────────────────────────────
# 블로그 생성 (Claude API 호출)
# ──────────────────────────────────────────────────────

def generate_blog(
    tool: dict,
    blog_type: str,
    all_tools: list[dict],
) -> tuple[str, str]:
    """
    Claude API를 호출해 블로그 글 생성.
    반환: (제목, 본문 내용)
    """
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    name   = tool["name"]
    peers  = _peers(tool, all_tools)

    # 방어적 폴백: 동료 부족 시 B로 강제
    if blog_type == "C" and len(peers) < 1:
        print(f"  ⚠️ 유형 C → 동료 부족 → B로 폴백")
        blog_type = "B"
    if blog_type == "D" and len(peers) < 2:
        print(f"  ⚠️ 유형 D → 동료 부족 → B로 폴백")
        blog_type = "B"
    if blog_type == "E" and len(peers) < 3:
        print(f"  ⚠️ 유형 E → 동료 부족 → B로 폴백")
        blog_type = "B"

    # 유형별 프롬프트 빌드
    if blog_type == "C":
        tool_b = peers[0]
        prompt = build_prompt_C(tool, tool_b)
        display = f"{name} vs {tool_b['name']}"
    elif blog_type == "D":
        alts   = peers[:4]
        prompt = build_prompt_D(tool, alts)
        display = f"{name} 대안 TOP {len(alts)}"
    elif blog_type == "E":
        group  = [tool] + peers
        prompt = build_prompt_E(group)
        display = f"{tool.get('ai_category','AI 툴')} TOP {len(group)}"
    else:  # B
        prompt = build_prompt_B(tool)
        display = f"{name} 리뷰"

    print(f"  🤖 Claude API 호출 중: [{blog_type}] {display}...")
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    content = message.content[0].text.strip()

    # 첫 번째 H1 라인을 제목으로 추출
    title = f"{display}"
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            break

    print(f"  ✅ 생성 완료 ({len(content)}자): {title[:50]}...")
    return title, content


# ──────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────

def main():
    """타겟 ✅ + 미작성 툴을 순차적으로 블로그 생성 후 Sheets에 저장."""
    print("=" * 55)
    print("blog_generator.py — 블로그 자동 생성 시작")
    print("=" * 55)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "sk-ant-여기에입력":
        print("❌ ANTHROPIC_API_KEY가 .env에 설정되지 않았습니다.")
        print("   apps/scripts/.env 파일을 열어 키를 입력하세요.")
        return

    sheets = SheetsClient()
    tools  = sheets.get_target_tools()

    if not tools:
        print("✅ 생성할 블로그가 없습니다 (타겟 + 미작성 툴 없음).")
        return

    success_count = 0
    fail_count    = 0

    for i, tool in enumerate(tools, 1):
        name = tool["name"]
        print(f"\n[{i}/{len(tools)}] {name}")

        # 유형 선택
        blog_type = select_blog_type(tool, tools)

        # 상태: 생성 중
        sheets.update_blog_status(name, "생성중")

        try:
            title, content = generate_blog(tool, blog_type, tools)

            # 블로그 콘텐츠 시트에 저장 (blog_type 포함)
            saved = sheets.save_blog_content(name, title, content, blog_type)
            if saved:
                sheets.update_blog_status(name, "글완성")
                success_count += 1
            else:
                sheets.update_blog_status(name, "생성오류")
                fail_count += 1

        except anthropic.APIError as e:
            print(f"  ❌ API 오류: {e}")
            sheets.update_blog_status(name, "생성오류")
            fail_count += 1

        except Exception as e:
            print(f"  ❌ 예외 발생: {e}")
            sheets.update_blog_status(name, "생성오류")
            fail_count += 1

        # API 요청 간격 (rate limit 방지)
        if i < len(tools):
            print("  ⏳ 3초 대기...")
            time.sleep(3)

    print("\n" + "=" * 55)
    print(f"✅ 완료 — 성공: {success_count}개 | 실패: {fail_count}개")
    print("스프레드시트 '블로그 콘텐츠' 시트에서 결과를 확인하세요.")
    print("=" * 55)


if __name__ == "__main__":
    main()
