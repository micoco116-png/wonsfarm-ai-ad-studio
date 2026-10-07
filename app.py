import os
import json
import base64
from datetime import date

import streamlit as st

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# ------------------------------------------------------------
# App config
# ------------------------------------------------------------
st.set_page_config(
    page_title="원스팜 AI 광고 스튜디오",
    page_icon="🍲",
    layout="wide",
)

# ------------------------------------------------------------
# Product strategy
# ------------------------------------------------------------
PRODUCTS = {
    "동전육수": {
        "usp": ["간편함", "빠른 조리", "1인분 활용", "자취·캠핑·초보 요리"],
        "strategy": "가격 경쟁력, 한닢쿡보다 저렴한 포지션, 선택형·비교형·생활공감형 콘텐츠, 다양한 요리 활용",
        "tone": "친근하고 빠른 숏폼",
    },
    "스틱육수": {
        "usp": ["계량 편의", "깔끔한 사용", "개별 포장", "보관·휴대 편의"],
        "strategy": "이미 스틱육수에 관심 있는 사람을 대상으로 간편함, 깔끔함, 개별 사용성을 강조",
        "tone": "깔끔하고 실용적인 숏폼",
    },
    "국대육수": {
        "usp": ["가성비", "진한 국물", "국·찌개·면 활용", "강한 제품 존재감"],
        "strategy": "가성비 있는 동전육수, 실제 국물요리, 음식 비주얼, 제품 중심 시네마틱 연출",
        "tone": "강한 제품 중심의 시네마틱 숏폼",
    },
}

GOALS = ["제품 인지도", "구매 전환", "댓글 참여", "신제품 관심"]
PLATFORMS = ["Instagram Reels", "TikTok", "YouTube Shorts"]
SEASONS = ["가을", "겨울", "봄", "여름", "명절/기념일", "상시"]

SEEDS = [
    {
        "name": "선택형·참여형 숏폼",
        "why": "시청자가 선택하거나 댓글을 남기게 만드는 구조",
        "fit": {"동전육수": 5, "스틱육수": 5, "국대육수": 4},
    },
    {
        "name": "댓글을 콘텐츠로 확장",
        "why": "질문·댓글을 다음 영상 소재로 이어가는 구조",
        "fit": {"동전육수": 5, "스틱육수": 5, "국대육수": 5},
    },
    {
        "name": "POV·생활공감",
        "why": "퇴근·자취·초보요리 같은 실제 상황에서 제품 필요성을 보여주는 구조",
        "fit": {"동전육수": 5, "스틱육수": 4, "국대육수": 4},
    },
    {
        "name": "AI 미니어처·불가능한 장면",
        "why": "촬영하기 어려운 장면을 AI로 만들어 제품을 주인공으로 만드는 구조",
        "fit": {"동전육수": 5, "스틱육수": 4, "국대육수": 5},
    },
    {
        "name": "제품 히어로·시네마틱",
        "why": "패키지와 제품 질감을 강하게 보여주는 제품 중심 광고",
        "fit": {"동전육수": 4, "스틱육수": 4, "국대육수": 5},
    },
]

IDEAS = {
    "동전육수": [
        ("오늘 육수 뭐 넣을래?", "선택형·참여형", "동전육수·스틱육수·국대육수를 빠르게 비교하고 시청자가 자기 취향을 고르게 한다.", 94),
        ("퇴근한 사람 vs 육수", "POV·생활공감", "퇴근 후 요리하기 싫은 순간, 동전육수로 국물을 빠르게 완성한다.", 91),
        ("댓글에서 가장 많이 나온 국물", "댓글 확장형", "댓글로 받은 메뉴를 다음 영상에서 동전육수로 구현한다.", 88),
    ],
    "스틱육수": [
        ("육수 계량, 아직도 눈대중?", "비교형", "눈대중 계량의 번거로움과 스틱형의 깔끔한 사용성을 대비한다.", 93),
        ("요리 초보의 첫 육수", "생활공감", "요리 초보가 간편하게 육수를 만드는 과정을 짧게 보여준다.", 90),
        ("한 스틱으로 어디까지?", "사용법·댓글형", "국·찌개·면 등 활용처를 빠르게 보여주고 다음 메뉴를 댓글로 받는다.", 87),
    ],
    "국대육수": [
        ("육수가 일하는 공장", "AI 미니어처·판타지", "국대육수를 거대한 국물 공정처럼 연출해 진한 국물이 만들어지는 느낌을 시각화한다.", 95),
        ("냄비가 감탄한 한 팩", "시네마틱", "끓는 국물과 제품을 영화 예고편처럼 강하게 연출한다.", 92),
        ("평범한 국물의 반전", "스토리형", "평범해 보이던 국물이 국대육수 투입 후 깊은 국물로 바뀌는 순간을 강조한다.", 89),
    ],
}


# ------------------------------------------------------------
# Session state
# ------------------------------------------------------------
STATE_DEFAULTS = {
    "generated": False,
    "research": None,
    "reference_analysis": None,
    "reference_image_b64": None,
    "reference_image_mime": None,
    "reference_filename": None,
    "reference_pipeline_complete": False,
    "reference_storyboard": None,
    "reference_prompts": None,
}

for key, value in STATE_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def server_ai_available():
    return bool(os.getenv("OPENAI_API_KEY")) and OpenAI is not None


def local_fallback(product, goal, season):
    return {
        "source": "내장 트렌드 데이터",
        "checked_period": "최근 14일을 기준으로 설계된 기본 시드",
        "trends": SEEDS,
        "note": "실시간 검색을 사용하려면 운영 서버에 OPENAI_API_KEY 환경변수를 설정하세요.",
    }


def call_json_model(prompt, image_data_url=None, model="gpt-6-luna"):
    if not server_ai_available():
        raise RuntimeError("서버 AI가 연결되어 있지 않습니다.")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    content = [{"type": "input_text", "text": prompt}]
    if image_data_url:
        content.append({"type": "input_image", "image_url": image_data_url, "detail": "high"})

    response = client.responses.create(
        model=model,
        input=[{"role": "user", "content": content}],
    )
    text = getattr(response, "output_text", "")
    if not text:
        raise RuntimeError("AI 응답이 비어 있습니다.")

    # 모델이 ```json ... ``` 형태로 반환해도 최대한 복구
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"AI가 올바른 JSON을 반환하지 않았습니다: {exc}") from exc


def research_with_server(product, goal, season, platforms):
    today = date.today()
    prompt = f"""
너는 원스팜의 SNS 광고 전략 담당자다. 오늘 날짜는 {today}이다.
최근 14일 안의 SNS 숏폼 광고/콘텐츠 트렌드를 웹에서 조사하라.
대상 플랫폼: {', '.join(platforms)}
대상 제품: {product}
광고 목표: {goal}
시즌: {season}

조건:
- 실제 확인 가능한 최근 사례를 우선한다.
- 틱톡, 인스타그램 릴스, 유튜브 쇼츠와 F&B뿐 아니라 다른 산업의 사례도 조사한다.
- 수치가 확인되지 않으면 숫자를 만들지 않는다.
- 각 사례의 URL/출처를 남긴다.
- 단순히 '요즘 유행'이라고 말하지 말고 왜 작동할 수 있는지 분석한다.
- 실제 제품 패키지·로고·한글을 AI가 재생성하지 않도록 제작 전략에 반영한다.
- 최종 구매 CTA는 원스팜이 아니라 화니네가게로 연결한다.

다음 JSON 구조로 반환하라.
{{
  "trends": [
    {{
      "name": "",
      "summary": "",
      "why": "",
      "format": "",
      "example": "",
      "source_url": "",
      "source_name": "",
      "freshness": 0,
      "shortform_fit": 0,
      "product_fit": 0,
      "product_visibility": 0,
      "participation": 0,
      "conversion": 0,
      "ai_production": 0
    }}
  ],
  "recommendation": ""
}}
트렌드는 최대 5개. 숫자는 확인 가능한 근거가 있을 때만 사용한다.
"""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.responses.create(
        model="gpt-6-luna",
        tools=[{"type": "web_search"}],
        input=prompt,
    )
    text = getattr(response, "output_text", "")
    try:
        return json.loads(text)
    except Exception:
        return {"source": "서버 AI 검색", "raw": text, "trends": []}


def reference_analysis_prompt(source_url, goal, platform):
    product_context = "\n".join(
        f"- {name}: {info['strategy']} / 핵심 USP: {', '.join(info['usp'])}"
        for name, info in PRODUCTS.items()
    )
    return f"""
너는 원스팜의 SNS 광고 레퍼런스 분석 및 재기획 담당자다.
사용자가 올린 광고 캡처 이미지를 분석하고, 그 광고의 표면적인 표현을 복제하지 않고 핵심 전략과 구조만 추출해 원스팜에 맞는 새로운 광고 아이디어로 변형하라.

[사용자 입력]
원본 SNS 링크: {source_url}
광고 목표: {goal}
플랫폼: {platform}

[원스팜 제품 전략]
{product_context}

[원스팜 공통 제작 원칙]
- 원스팜은 직접 판매처가 아니라, SNS 관심 형성 → 화니네가게 Smart Store 유입 → 구매 전환을 목표로 한다.
- 실제 제품 패키지, 로고, 한글, 제품명은 AI가 재생성하거나 왜곡하지 않는다. 실제 제품 사진을 후반 합성에 사용하는 방향을 우선한다.
- 원본 레퍼런스의 문구, 고유 캐릭터, 고유 디자인, 특정 장면, 브랜드 표현을 그대로 복사하지 않는다.
- 원본에서 '질문형 후킹', '선택형 참여', '문제→해결', '비교', 'POV' 같은 구조적 전략만 추출한다.
- 이미지에 없는 정보는 사실처럼 추측하지 않는다.
- 광고 성과가 실제로 확인되지 않는다면 '효과적이다'라고 단정하지 말고 '효과를 기대할 수 있는 이유'로 표현한다.
- source_url은 사용자가 입력한 값을 문자 하나까지 그대로 유지하고 절대 수정하거나 새 URL을 추측하지 않는다.

[분석 항목]
1. hook: 첫 시선에서 어떤 방식으로 주목을 끄는가
2. format: 콘텐츠 형식/구조
3. product_exposure: 제품이 언제, 어떻게 노출되는가
4. copy_structure: 자막·카피의 구성 방식
5. engagement: 시청자의 참여를 어떻게 유도하는가
6. cta: 마지막 행동 유도
7. strength: 이 구조의 강점

[제품 적합도]
동전육수, 스틱육수, 국대육수 각각을 1~5점으로 평가한다.
5=제품 특성과 레퍼런스 구조가 매우 잘 맞음
4=자연스럽게 적용 가능
3=일부 요소만 활용 가능
2=적용하기 어려움
1=거의 맞지 않음

점수를 먼저 비교하고, 최고 점수 제품을 recommended_product로 선택한다.
동점이면 각 제품의 전략과 광고 목표에 더 잘 맞는 쪽을 선택하고 이유를 쓴다.

[새로운 광고 아이디어]
추천 제품을 기준으로 완전히 새로운 상황과 표현을 만든다.
원본의 문구나 화면을 다시 쓰지 않는다.
반드시 원본에서 추출한 핵심 구조가 무엇인지 adaptation_point에 명시한다.

JSON만 반환하라. 설명 문장은 JSON 바깥에 넣지 마라.

{{
  "source_url": "{source_url}",
  "reference_analysis": {{
    "hook": "",
    "format": "",
    "product_exposure": "",
    "copy_structure": "",
    "engagement": "",
    "cta": "",
    "strength": ""
  }},
  "product_fit": {{
    "동전육수": {{"score": 0, "reason": ""}},
    "스틱육수": {{"score": 0, "reason": ""}},
    "국대육수": {{"score": 0, "reason": ""}}
  }},
  "wonsfarm_application": {{
    "recommended_product": "",
    "recommended_reason": "",
    "idea_title": "",
    "concept": "",
    "hook_copy": "",
    "content_flow": "",
    "product_exposure": "",
    "engagement": "",
    "cta": "",
    "adaptation_point": ""
  }}
}}
"""


def normalize_reference_result(result, source_url):
    # Source URL is always controlled by the user's text input.
    result["source_url"] = source_url

    fit = result.setdefault("product_fit", {})
    for product in PRODUCTS:
        item = fit.setdefault(product, {"score": 0, "reason": ""})
        try:
            item["score"] = max(1, min(5, int(item.get("score", 0))))
        except Exception:
            item["score"] = 0
        item["reason"] = str(item.get("reason", ""))

    app_data = result.setdefault("wonsfarm_application", {})
    top_product = max(PRODUCTS.keys(), key=lambda p: fit[p]["score"])
    app_data["recommended_product"] = top_product
    return result


def render_fit_bars(fit):
    ranked = sorted(
        [(p, fit.get(p, {})) for p in PRODUCTS],
        key=lambda x: x[1].get("score", 0),
        reverse=True,
    )
    for rank, (product, data) in enumerate(ranked, 1):
        score = data.get("score", 0)
        reason = data.get("reason", "")
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
        st.markdown(f"### {medal} {product}  ·  **{score} / 5**")
        st.progress(score / 5 if score else 0)
        st.caption(reason)


def build_dynamic_storyboard(ai_data):
    app_data = ai_data["wonsfarm_application"]
    product = app_data["recommended_product"]
    title = app_data.get("idea_title", "새로운 광고 아이디어")
    concept = app_data.get("concept", "")
    hook = app_data.get("hook_copy", "")
    flow = app_data.get("content_flow", "")
    exposure = app_data.get("product_exposure", "")
    engagement = app_data.get("engagement", "")
    cta = app_data.get("cta", "")

    return [
        {"time": "0–2초", "role": "HOOK", "scene": hook or "첫 화면에서 시청자가 멈추게 만드는 질문/상황"},
        {"time": "2–5초", "role": "SETUP", "scene": concept or "광고 상황을 빠르게 제시"},
        {"time": "5–9초", "role": "CORE", "scene": flow or "핵심 행동이나 선택 구조를 보여줌"},
        {"time": "9–14초", "role": "PRODUCT", "scene": f"실제 {product} 제품 사진을 후반 합성하여 노출. {exposure}"},
        {"time": "14–18초", "role": "ENGAGE", "scene": engagement or "댓글/선택 등 참여 행동 유도"},
        {"time": "18–20초", "role": "CTA", "scene": f"{cta or '화니네가게에서 만나보세요.'} → 화니네가게 구매 안내"},
    ]


def build_reference_prompts(ai_data, source_url):
    app_data = ai_data["wonsfarm_application"]
    product = app_data["recommended_product"]
    title = app_data.get("idea_title", "")
    concept = app_data.get("concept", "")
    hook = app_data.get("hook_copy", "")
    exposure = app_data.get("product_exposure", "")

    strategy = PRODUCTS[product]["strategy"]
    usp = ", ".join(PRODUCTS[product]["usp"])

    image = f"""세로형 9:16 프리미엄 한국 식품 광고 이미지.
콘셉트: {title}
상황: {concept}
후킹 카피의 시각적 의도: {hook}
추천 제품: {product}
제품 전략: {strategy}
핵심 USP: {usp}

IMPORTANT PRODUCT RULE:
실제 업로드한 {product} 제품 사진을 원본 레퍼런스로 사용한다.
제품 패키지의 로고, 한글, 제품명, 색상, 형태, 비율, 인쇄 내용을 AI가 새로 그리거나 바꾸지 않는다.
제품 자체는 가능한 한 원본 그대로 후반 합성한다.
AI는 음식, 배경, 조명, 증기, 소품, 카메라 구도만 생성한다.
제품 주변에는 후반 합성을 위한 깨끗한 공간을 남긴다.
이미지 안에 새로운 한글 텍스트를 생성하지 않는다.
photorealistic, cinematic Korean food commercial, realistic food texture, natural steam, realistic liquid physics, shallow depth of field.
출처는 {source_url}이며, 이것은 기획 참고용 메타데이터다.
"""

    video = f"""Vertical 9:16 commercial video.
Title: {title}
Recommended product: {product}
Concept: {concept}
Product exposure direction: {exposure}

Create a completely new scene inspired only by the extracted advertising structure, not by the original ad's literal copy, layout, characters, or branded visuals.
Use natural camera movement, believable cooking motion, realistic steam, and clean composition for captions.
The real uploaded {product} package image must remain unchanged when composited.
Never invent Korean text, logos, package artwork, or product labeling.
Keep the product readable and visually dominant during the product shot.
End with a clear product hero shot and a purchase cue toward 화니네가게.
"""

    premiere = f"""Premiere Pro 20초 편집 가이드 — {product} / {title}

00–02초 | HOOK
{hook}
- 가장 강한 시각 정보를 첫 컷에 배치
- 자막은 제품 패키지를 가리지 않는 빈 공간에 배치

02–05초 | SETUP
{concept}

05–09초 | CORE
{app_data.get('content_flow', '')}

09–14초 | PRODUCT
실제 {product} 제품 사진을 후반 합성.
패키지의 로고/한글/제품명은 그대로 유지.

14–18초 | ENGAGEMENT
{app_data.get('engagement', '')}

18–20초 | CTA
{app_data.get('cta', '')}
최종 구매 안내: 화니네가게

주의: AI가 생성한 패키지를 실제 제품 이미지처럼 사용하지 말고, 실제 제품 사진을 합성 기준으로 사용한다.
"""

    return {"image": image, "video": video, "premiere": premiere}


def render_pipeline_result(result):
    fit = result.get("product_fit", {})
    app_data = result.get("wonsfarm_application", {})

    st.markdown("## 01 · 레퍼런스 분석")
    analysis = result.get("reference_analysis", {})
    cards = [
        ("HOOK", analysis.get("hook", "")),
        ("FORMAT", analysis.get("format", "")),
        ("PRODUCT", analysis.get("product_exposure", "")),
        ("COPY", analysis.get("copy_structure", "")),
        ("ENGAGEMENT", analysis.get("engagement", "")),
        ("CTA", analysis.get("cta", "")),
    ]
    cols = st.columns(3)
    for idx, (label, value) in enumerate(cards):
        with cols[idx % 3]:
            st.markdown(
                f"<div class='result-card'><div class='eyebrow'>{label}</div><div class='card-value'>{value}</div></div>",
                unsafe_allow_html=True,
            )
    if analysis.get("strength"):
        st.info(f"**이 레퍼런스의 핵심 강점** · {analysis['strength']}")

    st.markdown("## 02 · 원스팜 제품 적합도")
    st.caption("레퍼런스 구조가 각 제품 전략과 얼마나 자연스럽게 연결되는지 AI가 평가합니다.")
    render_fit_bars(fit)

    recommended = app_data.get("recommended_product", "")
    reason = app_data.get("recommended_reason", "")
    st.markdown("## 03 · ★ BEST MATCH")
    st.markdown(
        f"<div class='best-match'><div class='eyebrow'>BEST PRODUCT</div><div class='best-title'>{recommended}</div><div class='best-score'>{fit.get(recommended, {}).get('score', 0)} / 5</div><div class='best-reason'>{reason}</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("## 04 · NEW WONSFARM IDEA")
    with st.container(border=True):
        st.markdown(f"### {app_data.get('idea_title', '새로운 광고 아이디어')}")
        st.write(app_data.get("concept", ""))
        a, b = st.columns(2)
        with a:
            st.markdown("**HOOK COPY**")
            st.write(app_data.get("hook_copy", ""))
            st.markdown("**CONTENT FLOW**")
            st.write(app_data.get("content_flow", ""))
        with b:
            st.markdown("**PRODUCT EXPOSURE**")
            st.write(app_data.get("product_exposure", ""))
            st.markdown("**ENGAGEMENT**")
            st.write(app_data.get("engagement", ""))
        st.markdown("**CTA**")
        st.write(app_data.get("cta", ""))
        st.markdown("**ADAPTATION POINT**")
        st.caption(app_data.get("adaptation_point", ""))

    if st.button("▶ 이 아이디어로 20초 광고 만들기", type="primary", use_container_width=True, key="make_20sec"):
        storyboard = build_dynamic_storyboard(result)
        prompts = build_reference_prompts(result, result.get("source_url", ""))
        st.session_state["reference_storyboard"] = storyboard
        st.session_state["reference_prompts"] = prompts
        st.session_state["reference_pipeline_complete"] = True

    if st.session_state.get("reference_pipeline_complete"):
        st.markdown("## 05 · 20초 스토리보드")
        for scene in st.session_state["reference_storyboard"]:
            with st.container(border=True):
                left, right = st.columns([1, 5])
                with left:
                    st.markdown(f"**{scene['time']}**")
                    st.caption(scene["role"])
                with right:
                    st.write(scene["scene"])

        st.markdown("## 06 · 제작 프롬프트")
        prompts = st.session_state["reference_prompts"]
        t1, t2, t3 = st.tabs(["AI 이미지", "Higgsfield 영상", "Premiere Pro"])
        with t1:
            st.code(prompts["image"], language="text")
        with t2:
            st.code(prompts["video"], language="text")
        with t3:
            st.code(prompts["premiere"], language="text")

        full_report = {
            "date": str(date.today()),
            "workflow": "reference_to_ad_pipeline",
            "source_url": result.get("source_url", ""),
            "reference_analysis": result.get("reference_analysis", {}),
            "product_fit": result.get("product_fit", {}),
            "wonsfarm_application": result.get("wonsfarm_application", {}),
            "storyboard_20sec": st.session_state["reference_storyboard"],
            "prompts": st.session_state["reference_prompts"],
        }
        st.download_button(
            "📥 레퍼런스 → 광고 제작 리포트 JSON 다운로드",
            data=json.dumps(full_report, ensure_ascii=False, indent=2),
            file_name="wonsfarm_reference_to_ad_report.json",
            mime="application/json",
            use_container_width=True,
        )

    st.markdown("## 07 · 출처")
    source_url = result.get("source_url", "")
    if source_url:
        st.markdown(f"[{source_url}]({source_url})")
    else:
        st.caption("사용자가 입력한 원본 SNS 링크가 없습니다.")


# ------------------------------------------------------------
# CSS / Visual language
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --ivory: #f7f4ec;
        --green: #214d3b;
        --green-2: #2f604c;
        --ink: #20231f;
        --muted: #6e756f;
        --line: rgba(33,77,59,.14);
    }
    .stApp { background: linear-gradient(180deg, #fbfaf6 0%, #f5f2e9 100%); }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem; }
    h1, h2, h3 { color: var(--ink); letter-spacing: -0.03em; }
    .hero { padding: 1.4rem 0 1.2rem; border-bottom: 1px solid var(--line); margin-bottom: 1.25rem; }
    .hero-kicker { font-size: .78rem; letter-spacing: .16em; font-weight: 700; color: var(--green-2); }
    .hero-title { font-size: 2.4rem; font-weight: 800; line-height: 1.05; margin-top: .45rem; }
    .hero-sub { color: var(--muted); margin-top: .45rem; }
    .result-card { border: 1px solid var(--line); border-radius: 16px; padding: 16px; min-height: 120px; background: rgba(255,255,255,.66); box-shadow: 0 5px 20px rgba(33,77,59,.05); margin-bottom: 14px; }
    .eyebrow { font-size: .7rem; letter-spacing: .14em; font-weight: 800; color: var(--green-2); }
    .card-value { margin-top: 9px; font-weight: 600; line-height: 1.45; }
    .best-match { border: 1px solid rgba(33,77,59,.3); border-radius: 22px; padding: 26px; background: linear-gradient(135deg, rgba(33,77,59,.10), rgba(255,255,255,.82)); box-shadow: 0 10px 28px rgba(33,77,59,.08); }
    .best-title { font-size: 2rem; font-weight: 850; margin-top: 6px; }
    .best-score { font-size: 1.05rem; font-weight: 750; color: var(--green-2); margin-top: 4px; }
    .best-reason { margin-top: 10px; color: #414741; line-height: 1.6; }
    div[data-testid="stMetricValue"] { color: var(--green); }
    div.stButton > button { border-radius: 12px; font-weight: 750; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
st.markdown(
    """
    <div class='hero'>
      <div class='hero-kicker'>ONE'S FARM · AI AD STUDIO</div>
      <div class='hero-title'>SNS 광고 기획부터 제작 준비까지</div>
      <div class='hero-sub'>레퍼런스를 분석해 원스팜 제품 전략에 맞는 새로운 광고 아이디어와 20초 제작안으로 연결합니다.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("광고 설정")
    product = st.selectbox("제품", list(PRODUCTS))
    goal = st.selectbox("광고 목표", GOALS)
    season = st.selectbox("시즌", SEASONS)
    platforms = st.multiselect("플랫폼", PLATFORMS, default=["Instagram Reels", "TikTok"])
    st.divider()
    if server_ai_available():
        st.success("서버 AI 연결됨 · 최신 웹 조사/이미지 분석 사용 가능")
    else:
        st.info("현재는 내장 데이터 모드입니다. OPENAI_API_KEY를 서버 환경변수에 설정하면 AI 기능을 사용할 수 있습니다.")

main_tab, ref_tab = st.tabs(["🧠 AI 광고 기획", "🔎 내 레퍼런스 분석"])

# ------------------------------------------------------------
# Existing flow
# ------------------------------------------------------------
with main_tab:
    if st.button("🚀 오늘의 광고 만들기", type="primary", use_container_width=True):
        with st.spinner("최근 트렌드와 제품 적합도를 분석하는 중..."):
            if server_ai_available():
                try:
                    research = research_with_server(product, goal, season, platforms)
                except Exception as exc:
                    research = local_fallback(product, goal, season)
                    research["error"] = str(exc)
            else:
                research = local_fallback(product, goal, season)
        st.session_state["research"] = research
        st.session_state["generated"] = True

    if not st.session_state.get("generated"):
        st.markdown("## 버튼 하나로 광고 기획 시작")
        st.markdown("**최신 트렌드 조사 → 제품 매칭 → BEST 아이디어 → 20초 스토리보드 → AI 제작 프롬프트 → Premiere 편집안**")
    else:
        research = st.session_state["research"] or {}
        st.success(f"{product} × {season} × {goal} 기준 분석 완료")
        st.markdown("## 01 · 최근 SNS 트렌드")
        if research.get("source") == "서버 AI 검색":
            st.caption("운영 서버의 AI 웹 검색 결과를 사용했습니다.")
        else:
            st.caption("현재는 내장 트렌드 시드입니다.")
        for idx, trend in enumerate(research.get("trends", [])[:5], 1):
            name = trend.get("name", "트렌드")
            score = trend.get("fit", {}).get(product, 0) if isinstance(trend.get("fit"), dict) else trend.get("product_fit", 0)
            with st.container(border=True):
                a, b, c = st.columns([3, 1, 4])
                a.subheader(f"{idx}. {name}")
                b.metric("제품 적합도", f"{score}/5" if score <= 5 else score)
                c.write(trend.get("why") or trend.get("summary", ""))
                if trend.get("source_url"):
                    st.markdown(f"출처: [{trend.get('source_name', '원문')}]({trend['source_url']})")

        st.markdown("## 02 · 광고 아이디어")
        ideas = sorted(IDEAS[product], key=lambda x: x[3], reverse=True)
        for idx, (title, fmt, desc, score) in enumerate(ideas, 1):
            with st.container(border=True):
                a, b, c = st.columns([3, 2, 1])
                a.subheader(f"{idx}. {title}")
                b.write(f"**{fmt}**\n\n{desc}")
                c.metric("추천 점수", score)

        best = ideas[0]
        st.markdown("## 03 · 🏆 BEST 광고")
        st.markdown(f"### {best[0]}")
        st.write(best[2])
        st.write(f"**형식:** {best[1]} · **추천 점수:** {best[3]}/100")

        st.markdown("## 04 · 20초 스토리보드")
        scenes = [
            ("0–2초", "HOOK", "문제 또는 선택 질문으로 멈춰 세우기"),
            ("2–5초", "SITUATION", f"{product}가 필요한 상황 보여주기"),
            ("5–10초", "PRODUCT", f"실제 {product} 제품 이미지 + USP"),
            ("10–15초", "RESULT", "국물/완성 음식 결과 강조"),
            ("15–18초", "ENGAGE", "댓글 또는 선택 유도"),
            ("18–20초", "CTA", "화니네가게 구매 안내"),
        ]
        for item in scenes:
            with st.container(border=True):
                st.markdown(f"**{item[0]} · {item[1]}** — {item[2]}")

        st.markdown("## 05 · 제작 프롬프트")
        usp = ", ".join(PRODUCTS[product]["usp"])
        image_prompt = f"""세로형 9:16 프리미엄 식품 광고 이미지. 실제 업로드한 {product} 제품 사진을 정확한 제품 레퍼런스로 사용한다. 제품 패키지의 로고, 한글, 색상, 형태, 비율, 인쇄 내용을 AI가 새로 생성하거나 변경하지 않는다. 콘셉트: {best[2]}. 제품 USP: {usp}. 후반 합성을 위해 제품 주변에 깨끗한 영역을 확보한다. 이미지 안에 새로운 텍스트를 넣지 않는다. photorealistic, cinematic Korean food commercial."""
        video_prompt = f"""Vertical 9:16 commercial video. Product: {product}. Concept: {best[0]}. {best[2]} Camera movement is controlled and physically believable. Natural steam and food motion. The real uploaded product image must remain unchanged when composited; never invent packaging, Korean text, logo, or product artwork. Reserve negative space for Premiere captions. Finish with a strong product hero shot."""
        premiere_prompt = f"""0–2초: 강한 훅. 2–5초: 상황/문제. 5–10초: 실제 {product} 제품 등장 + 핵심 USP. 10–15초: 사용 결과/완성 음식. 15–18초: 댓글 또는 선택 유도. 18–20초: 화니네가게 구매 안내. 패키지 위에는 자막을 겹치지 않는다."""
        t1, t2, t3 = st.tabs(["AI 이미지", "Higgsfield 영상", "Premiere Pro"])
        with t1:
            st.code(image_prompt, language="text")
        with t2:
            st.code(video_prompt, language="text")
        with t3:
            st.code(premiere_prompt, language="text")

        report = {
            "date": str(date.today()),
            "product": product,
            "goal": goal,
            "season": season,
            "platforms": platforms,
            "research": research,
            "best_idea": {"title": best[0], "format": best[1], "description": best[2], "score": best[3]},
            "storyboard": scenes,
            "prompts": {"image": image_prompt, "video": video_prompt, "premiere": premiere_prompt},
        }
        st.download_button(
            "📥 광고 기획서 JSON 다운로드",
            data=json.dumps(report, ensure_ascii=False, indent=2),
            file_name=f"wonsfarm_{product}_ad_plan.json",
            mime="application/json",
            use_container_width=True,
        )

# ------------------------------------------------------------
# New reference flow
# ------------------------------------------------------------
with ref_tab:
    st.markdown("## REFERENCE LAB")
    st.caption("좋아하는 SNS 광고를 캡처해서 가져오세요. 원본의 표현을 복제하지 않고 구조만 분석해 원스팜용 아이디어로 재기획합니다.")

    left, right = st.columns([1.1, 1])
    with left:
        uploaded = st.file_uploader(
            "SNS 광고 캡처 업로드",
            type=["png", "jpg", "jpeg", "webp"],
            help="분석할 광고 화면을 올려주세요.",
            key="reference_uploader",
        )
        if uploaded is not None:
            st.image(uploaded, caption=uploaded.name, use_container_width=True)

    with right:
        source_url = st.text_input(
            "원본 SNS 링크",
            placeholder="https://www.instagram.com/reel/...",
            help="출처 표시용으로만 사용합니다. AI가 URL을 추측하거나 수정하지 않습니다.",
            key="reference_url",
        )
        ref_goal = st.selectbox("광고 목표", GOALS, index=0, key="ref_goal")
        ref_platform = st.selectbox("플랫폼", PLATFORMS, index=0, key="ref_platform")
        st.info("V1은 링크 크롤링이 아니라 업로드한 광고 캡처 이미지를 실제 분석 대상으로 사용합니다.")

    if st.button("🔎 레퍼런스 분석하기", type="primary", use_container_width=True, key="analyze_reference"):
        if uploaded is None:
            st.warning("먼저 광고 캡처 이미지를 업로드해주세요.")
        elif not source_url.strip():
            st.warning("원본 SNS 링크를 입력해주세요. 출처는 입력값 그대로 저장됩니다.")
        elif not server_ai_available():
            st.error("레퍼런스 이미지 분석은 서버 AI 연결이 필요합니다. OPENAI_API_KEY를 운영 서버 환경변수에 설정해주세요.")
        else:
            try:
                raw_bytes = uploaded.getvalue()
                mime = uploaded.type or "image/png"
                image_b64 = base64.b64encode(raw_bytes).decode("utf-8")
                image_data_url = f"data:{mime};base64,{image_b64}"
                prompt = reference_analysis_prompt(source_url.strip(), ref_goal, ref_platform)
                with st.spinner("레퍼런스의 구조 → 제품 적합도 → 새로운 광고 아이디어를 분석하는 중..."):
                    result = call_json_model(prompt, image_data_url=image_data_url)
                    result = normalize_reference_result(result, source_url.strip())

                st.session_state["reference_analysis"] = result
                st.session_state["reference_image_b64"] = image_b64
                st.session_state["reference_image_mime"] = mime
                st.session_state["reference_filename"] = uploaded.name
                st.session_state["reference_pipeline_complete"] = False
                st.session_state["reference_storyboard"] = None
                st.session_state["reference_prompts"] = None
            except Exception as exc:
                st.error(f"레퍼런스 분석 중 문제가 발생했습니다: {exc}")

    result = st.session_state.get("reference_analysis")
    if result:
        st.divider()
        render_pipeline_result(result)
