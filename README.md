# 대화형 HWPX 공문 작성 에이전트 (HWPX Editor)

**HWPX Editor**는 한글(HWPX) 문서 양식을 기반으로 AI 비서(LLM)가 사용자와 자연스러운 대화를 나누며 필요한 정보를 수집하고, **빈칸을 자동으로 채워 완성된 공문을 생성해 주는 대화형 CLI 프로그램**입니다.

이 프로젝트는 무거운 한글 오브젝트 모델을 메모리에 띄우지 않고, **순수 Python과 XML 제어(LXML)**를 통해 백엔드에서 문서를 직접 조작하므로 리눅스 등 다양한 환경에서 가볍고 빠르게 동작합니다.

---

## ✨ 핵심 기능 (Core Features)

### 1. 🧠 Content-Aware Template Classifier (지능형 양식 분류 및 캐싱)

사용자가 "나 다쳐서 병원 다녀왔는데 뭐 제출해야 해?" 라고 물어보면, AI가 의도를 파악하고 가장 알맞은 양식을 자동 선택합니다.

- 프로그램 최초 구동 시, `templates/` 폴더 내의 모든 HWPX 파일을 읽고 LLM이 각 문서의 **주된 사용 목적**과 **필수 입력 항목**을 요약합니다.
- 이 요약 결과는 `summary.json`으로 캐싱되어, 이후부터는 수백 장의 양식이 있어도 분류 지연 시간 없이 0.1초 만에 문서를 매핑합니다.

### 2. ⚡ Lightweight Native Parsing (경량 HWPX 파싱)

HWPX는 사실 ZIP 압축 포맷입니다. 본 에이전트는 압축을 직접 해제하고 `Contents/section0.xml`을 파싱하여, 문서 내의 모든 단락(`<hp:p>`)과 표 셀(`<hp:tc>`)에 고유한 `block_id`(예: `sec0_tbl0_r1_c0`)를 부여합니다. LLM은 오직 이 ID들을 키(Key) 값으로 삼아 문서를 수정합니다.

### 3. 🧩 Tag Fragmentation Resolution (스타일 파편화 방지 알고리즘)

문서 내 텍스트에 볼드체, 색상 등이 혼합되어 XML 태그(`<hp:t>`)가 쪼개져 있는 언어적 한계를 극복했습니다.

- 단어 길이를 비율로 재분배하는 **Length Distribution Algorithm**을 적용하여, 사용자가 요청한 텍스트로 치환할 때 원본 양식의 서식(폰트, 색상 등)을 완벽하게 유지합니다.
- 원본의 빈칸(`""`)을 채우는 경우에도 동적으로 XML 노드를 생성해 안전하게 텍스트를 주입합니다.

### 4. 📈 Dynamic Table Expansion (동적 표 행 투여)

본문 표의 칸이 1줄밖에 없더라도, 사용자가 10개의 물품을 입력하면 자동으로 표를 확장합니다.

- AI 엔진이 템플릿 마지막 행(`<hp:tr>`)의 XML 구조(테두리, 서식 등)를 Deepcopy하여 표 범위 아래로 끝없이 자동 생성해 줍니다.

---

## 🛠️ 시스템 요구사항 (Requirements)

- **Python 3.10 이상**
- **uv** (초고속 파이썬 패키지 매니저)
- **Ollama** (로컬 LLM 구동용. 기본적으로 `localhost:11435` 포트를 바라보고 통신합니다. `gemma3:12b` 호환)

---

## 🚀 프로젝트 실행 방법 (Getting Started)

### 1. 패키지 설치

이 프로젝트는 `uv` 기반으로 관리됩니다.

```bash
uv sync
```

### 2. 백엔드 서버 실행 (API 엔진)

HWPX 문서를 읽고 쓰는 코어 엔진은 FastAPI로 동작합니다. 새 터미널 창을 열고 아래 명령어로 구동합니다.

```bash
uv run uvicorn src.app.main:app --host 127.0.0.1 --port 8000
```

### 3. 대화형 AI 인터페이스 시작 (사용자 모드)

다른 터미널 창에서 메인 챗봇 비서를 실행합니다.

```bash
uv run interactive_agent.py
```

💡 **예시 답변:** "내일 체육대회 건으로 휴가 쓰고 싶어. 내 이름은 오정규야."

### 4. 양식 추가 방법

새로운 빈칸이 있는 한글 양식을 에이전트에 가르치고 싶다면, 단순히 `templates/` 폴더 안에 새로운 `.hwpx` 파일을 넣고 프로그램을 다시 시작하면 됩니다. AI가 알아서 문서를 분석해 캐싱합니다!

---

## 📂 디렉터리 구조 (Project Structure)

```text
HWPX_editor/
├── interactive_agent.py  # 메인 챗봇 실행 파일 (LLM 통신 및 CLI 로직)
├── .env                  # 환경 변수 및 설정 파일
├── pyproject.toml        # 의존성 정의 (uv)
├── templates/            # 사용자가 넣은 원본 HWPX 양식 파일
├── result/               # 생성 및 작성이 완료된 HWPX 결과물
├── debug/                # (옵션) DEBUG_MODE=True 일 때 파싱된 로그가 남는 폴더
└── src/app/
    ├── main.py           # FastAPI 서버 엔트리포인트 
    ├── api/              # /read, /modify 라우터 연결
    └── infra/            
        └── hwpx_tool.py  # [핵심] XML 노드 복제 및 텍스트 파편화 분배 체계 엔진
```

---

## 🤝 기여하기 (Contributing)

- 레거시 `.hwp` 포맷 지원은 향후 Phase 9 목표로, `olefile`을 통한 OLE 바이너리 직접 제어를 우선순위로 두고 있습니다.
- 버그 제보와 Pull Request는 언제나 환영합니다!
