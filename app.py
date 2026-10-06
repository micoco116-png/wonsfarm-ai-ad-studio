import os, json, textwrap
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

st.set_page_config(page_title='원스팜 AI 광고 스튜디오 v2', page_icon='🍲', layout='wide')

PRODUCTS = {
    '동전육수': {'usp':['간편함','빠른 조리','1인분 활용','자취·캠핑·초보 요리'], 'tone':'친근하고 빠른 숏폼'},
    '스틱육수': {'usp':['계량 편의','깔끔한 사용','보관 편리','일상 요리'], 'tone':'깔끔하고 실용적인 숏폼'},
    '국대육수': {'usp':['진한 국물','프리미엄 이미지','국·찌개 활용','제품 존재감'], 'tone':'강한 제품 중심의 시네마틱 숏폼'},
}

SEEDS = [
 {'name':'선택형·참여형 숏폼','why':'시청자가 선택하거나 댓글을 남기게 만드는 구조','fit':{'동전육수':5,'스틱육수':5,'국대육수':4}},
 {'name':'댓글을 콘텐츠로 확장','why':'질문·댓글을 다음 영상 소재로 이어가는 구조','fit':{'동전육수':5,'스틱육수':5,'국대육수':5}},
 {'name':'POV·생활공감','why':'퇴근·자취·초보요리 같은 실제 상황에서 제품 필요성을 보여주는 구조','fit':{'동전육수':5,'스틱육수':4,'국대육수':4}},
 {'name':'AI 미니어처·불가능한 장면','why':'촬영하기 어려운 장면을 AI로 만들어 제품을 주인공으로 만드는 구조','fit':{'동전육수':5,'스틱육수':4,'국대육수':5}},
 {'name':'제품 히어로·시네마틱','why':'패키지와 제품 질감을 강하게 보여주는 제품 중심 광고','fit':{'동전육수':4,'스틱육수':4,'국대육수':5}},
]

IDEAS = {
 '동전육수': [('오늘 육수 뭐 넣을래?','선택형·참여형','동전육수·스틱육수·국대육수를 빠르게 비교하고 시청자가 자기 취향을 고르게 한다.',94),('퇴근한 사람 vs 육수','POV·생활공감','퇴근 후 요리하기 싫은 순간, 동전육수로 국물을 빠르게 완성한다.',91),('댓글에서 가장 많이 나온 국물','댓글 확장형','댓글로 받은 메뉴를 다음 영상에서 동전육수로 구현한다.',88)],
 '스틱육수': [('육수 계량, 아직도 눈대중?','비교형','눈대중 계량의 번거로움과 스틱형의 깔끔한 사용성을 대비한다.',93),('요리 초보의 첫 육수','생활공감','요리 초보가 실패 없이 한 번에 육수를 만드는 과정을 짧게 보여준다.',90),('한 스틱으로 어디까지?','사용법·댓글형','국·찌개·면 등 활용처를 빠르게 보여주고 다음 메뉴를 댓글로 받는다.',87)],
 '국대육수': [('육수가 일하는 공장','AI 미니어처·판타지','국대육수 내부를 작은 공장처럼 표현해 진한 국물이 만들어지는 느낌을 시각화한다.',95),('냄비가 감탄한 한 팩','시네마틱','끓는 국물과 제품을 영화 예고편처럼 강하게 연출한다.',92),('평범한 국물의 반전','스토리형','평범해 보이던 국물이 국대육수 투입 후 깊은 국물로 변하는 순간을 강조한다.',89)]
}

def local_fallback(product, goal, season):
    return {
      'source':'내장 트렌드 데이터(실시간 검색 연결 전)',
      'checked_period':'최근 14일을 기준으로 설계된 기본 시드',
      'trends': SEEDS,
      'note':'실시간 검색을 사용하려면 운영 서버에 OPENAI_API_KEY 환경변수를 설정하세요.'
    }

def server_ai_available():
    return bool(os.getenv('OPENAI_API_KEY')) and OpenAI is not None

def research_with_server(product, goal, season, platforms):
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    today = date.today()
    prompt = f'''너는 원스팜의 SNS 광고 전략 담당자다. 오늘 날짜는 {today}이다.
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
- 단순히 '요즘 유행'이라고 말하지 말고 왜 작동하는지 분석한다.
- 원스팜 제품의 실제 패키지·로고·한글을 AI가 재생성하지 않도록 제작 전략에 반영한다.
- 최종 구매 CTA는 원스팜이 아니라 화니네가게로 연결한다.

다음 JSON 구조로 반환하라:
{{"trends":[{{"name":"","summary":"","why":"","format":"","example":"","source_url":"","source_name":"","freshness":0,"shortform_fit":0,"product_fit":0,"product_visibility":0,"participation":0,"conversion":0,"ai_production":0}}],"recommendation":""}}
트렌드는 최대 5개. 각 점수는 0~15 또는 0~20의 정수로 주되, 항목별 기준이 일관되게 유지되게 하라.'''
    r = client.responses.create(model='gpt-6-luna', tools=[{'type':'web_search'}], input=prompt)
    text = getattr(r, 'output_text', '')
    try:
        return json.loads(text)
    except Exception:
        return {'source':'서버 AI 검색','raw':text,'trends':[]}

def build_prompts(product, title, concept):
    usp=', '.join(PRODUCTS[product]['usp'])
    image=f'''세로형 9:16 프리미엄 식품 광고 이미지. 실제 업로드한 {product} 제품 사진을 정확한 제품 레퍼런스로 사용한다. 패키지의 로고, 한글, 색상, 형태, 비율, 인쇄 내용을 AI가 새로 생성하거나 변경하지 않는다. 콘셉트: {concept}. 제품 USP: {usp}. 제품 주변은 후반 합성을 위한 깨끗한 영역을 확보한다. 텍스트는 이미지에 넣지 않는다. photorealistic, cinematic Korean food commercial, realistic steam, realistic liquid physics, shallow depth of field.'''
    video=f'''Vertical 9:16 commercial video. Product: {product}. Concept: {title}. {concept} Camera movement is controlled and physically believable. Natural steam and food motion. The real uploaded product image must remain unchanged when composited; never invent packaging, Korean text, logo, or product artwork. Reserve negative space for Premiere captions. Finish with a strong product hero shot.'''
    premiere=f'''0–2초: 강한 훅. 2–5초: 상황/문제. 5–10초: 실제 {product} 제품 등장 + 핵심 USP. 10–15초: 사용 결과/완성 음식. 15–18초: 댓글 또는 선택 유도. 18–20초: “화니네가게에서 만나보세요.” CTA. 패키지 위에는 자막을 겹치지 않는다.'''
    return image, video, premiere

st.title('🍲 원스팜 AI 광고 스튜디오 v2')
st.caption('사용자 API 키·결제 없이 사용하는 구조 / 서버 AI가 연결되면 최신 트렌드 자동 조사 가능')

with st.sidebar:
    st.header('광고 설정')
    product=st.selectbox('제품',list(PRODUCTS))
    goal=st.selectbox('광고 목표',['제품 인지도','구매 전환','댓글 참여','신제품 관심'])
    season=st.selectbox('시즌',['가을','겨울','봄','여름','명절/기념일','상시'])
    platforms=st.multiselect('플랫폼',['Instagram Reels','TikTok','YouTube Shorts'],default=['Instagram Reels','TikTok'])
    st.divider()
    if server_ai_available(): st.success('서버 AI 연결됨 · 최신 웹 조사 사용 가능')
    else: st.info('현재는 내장 데이터로 실행됩니다. 운영 서버에 OPENAI_API_KEY를 설정하면 사용자에게 키를 요구하지 않고 최신 웹 조사가 활성화됩니다.')

if st.button('🚀 오늘의 광고 만들기',type='primary',use_container_width=True):
    with st.spinner('최근 트렌드와 제품 적합도를 분석하는 중...'):
        if server_ai_available():
            try: research=research_with_server(product,goal,season,platforms)
            except Exception as e: research=local_fallback(product,goal,season); research['error']=str(e)
        else: research=local_fallback(product,goal,season)
    st.session_state['research']=research
    st.session_state['generated']=True

if not st.session_state.get('generated'):
    st.markdown('## 버튼 하나로 광고 기획 시작')
    st.markdown('**최신 트렌드 조사 → 제품 매칭 → BEST 아이디어 → 스토리보드 → AI 제작 프롬프트 → Premiere 편집안**')
    st.stop()

research=st.session_state['research']
st.success(f'{product} × {season} × {goal} 기준 분석 완료')

st.header('1. 최근 SNS 트렌드')
if research.get('source') == '서버 AI 검색':
    st.caption('운영 서버의 AI 웹 검색 결과를 사용했습니다.')
else:
    st.caption('현재는 내장 트렌드 시드입니다. 서버 키를 연결하면 실시간 조사 결과로 자동 교체됩니다.')

for i,t in enumerate(research.get('trends',[])[:5],1):
    name=t.get('name','트렌드')
    score=t.get('fit',{}).get(product,0) if isinstance(t.get('fit'),dict) else t.get('product_fit',0)
    with st.container(border=True):
        a,b,c=st.columns([3,1,4])
        a.subheader(f'{i}. {name}')
        b.metric('제품 적합도',f'{score}/5' if score<=5 else f'{score}')
        c.write(t.get('why') or t.get('summary',''))
        if t.get('source_url'): st.markdown(f"출처: [{t.get('source_name','원문')}]({t['source_url']})")

st.header('2. 광고 아이디어')
ideas=sorted(IDEAS[product],key=lambda x:x[3],reverse=True)
for i,(title,fmt,desc,score) in enumerate(ideas,1):
    with st.container(border=True):
        a,b,c=st.columns([3,2,1])
        a.subheader(f'{i}. {title}')
        b.write(f'**{fmt}**\n\n{desc}')
        c.metric('추천 점수',score)

best=ideas[0]
st.header('3. 🏆 BEST 광고')
st.markdown(f'### {best[0]}')
st.write(best[2])
st.write(f'**형식:** {best[1]} · **추천 점수:** {best[3]}/100')

st.header('4. 20초 스토리보드')
scenes=[('0–2초','HOOK','문제 또는 선택 질문으로 멈춰 세우기'),('2–5초','SITUATION',f'{product}가 필요한 상황 보여주기'),('5–10초','PRODUCT',f'실제 {product} 제품 이미지 + USP'),('10–15초','RESULT','국물/완성 음식 결과 강조'),('15–18초','ENGAGE','댓글 또는 선택 유도'),('18–20초','CTA','화니네가게 구매 안내')]
for x in scenes: st.markdown(f'**{x[0]} · {x[1]}** — {x[2]}')

st.header('5. 제작 프롬프트')
img,vid,pre=build_prompts(product,best[0],best[2])
t1,t2,t3=st.tabs(['AI 이미지','Higgsfield 영상','Premiere Pro'])
with t1: st.code(img,language='text')
with t2: st.code(vid,language='text')
with t3: st.code(pre,language='text')

report={'date':str(date.today()),'product':product,'goal':goal,'season':season,'platforms':platforms,'research':research,'best_idea':{'title':best[0],'format':best[1],'description':best[2],'score':best[3]},'storyboard':scenes,'prompts':{'image':img,'video':vid,'premiere':pre}}
st.download_button('📥 광고 기획서 JSON 다운로드',json.dumps(report,ensure_ascii=False,indent=2),file_name=f'wonsfarm_{product}_ad_plan_v2.json',mime='application/json')

st.divider()
st.caption('운영 구조: 사용자 화면에는 API 키가 없음 → 서버 환경변수에서 AI 키를 관리 → 최신 웹 조사 결과를 사용자에게 전달')
