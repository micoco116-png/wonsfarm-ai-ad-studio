# 원스팜 AI 광고 스튜디오 v2

사용자에게 API 키나 결제를 요구하지 않는 원스팜 전용 광고 기획 MVP입니다.

## 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 실시간 웹 조사 활성화
사용자에게 키를 보여주지 않고 **운영 서버 환경변수**에만 설정합니다.

Windows PowerShell:
```powershell
$env:OPENAI_API_KEY="회사에서 관리하는 키"
streamlit run app.py
```

키가 없으면 내장 트렌드 데이터로도 프로그램이 실행됩니다.

## 현재 흐름
최신 트렌드 조사(서버 키가 있을 때) → 제품 매칭 → 아이디어 3개 → BEST → 20초 스토리보드 → AI 이미지/Higgsfield/Premiere 프롬프트 → JSON 다운로드

## 주의
API 키를 app.py나 GitHub에 직접 넣지 마세요. 실제 배포에서는 서버의 secrets/environment variables로 관리하는 것을 권장합니다.
