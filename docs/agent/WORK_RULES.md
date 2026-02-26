# Agent Work Rules (SSOT)

본 문서는 에이전트(antigravity 등)가 **업무 시작 전에 반드시 읽고 준수**해야 하는 규칙입니다.
프로젝트의 유지보수성을 최우선 목표로 합니다.

## 0. 기본 원칙
- 모든 실행/설치는 **uv 기반**으로 수행합니다. (python/pip 직접 호출 금지)
- 변경은 “작게, 자주” 하되, **테스트/문서/린트 게이트**를 항상 통과해야 합니다.
- 정책/규칙의 단일 진실 원천(SSOT)은 아래입니다:
  - `pyproject.toml` (툴 설정/의존성)
  - `uv.lock` (환경 고정)
  - `docs/agent/WORK_RULES.md` / `docs/architecture.md` / `CONTRIBUTING.md`
  - `.github/workflows/ci.yml`

## 1. 작업 시작 전 필수 절차 (매 세션)
1) 현재 브랜치/상태 확인
- `git status`
- `git branch --show-current`

2) 환경 동기화 (lock 기반)
- `uv sync`

3) 품질 게이트 사전 실행 (로컬)
- `make fmt`
- `make lint`
- `make type`
- `make test`

> 위 4개 중 하나라도 실패하면, “우회”하지 말고 원인을 해결 후 진행합니다.

## 2. 절대 금지 사항
- `pip install`, `pip freeze`, `python -m pip ...` 직접 실행
- 테스트 없이 기능 추가/리팩토링 커밋
- ruff 경고를 `# noqa`로 무분별하게 무시
- 설정/비밀키를 코드/로그/리포지토리에 포함

## 3. 변경 유형별 필수 산출물
### 3.1 버그 수정
- 회귀 테스트(최소 1개) 추가가 원칙입니다.
- 재현 절차를 PR/커밋 메시지에 포함합니다.

### 3.2 기능 추가
- 서비스/도메인 경계 준수 (`docs/architecture.md`)
- 최소 단위 테스트 추가
- API 변경이면 요청/응답 스키마와 문서 반영

### 3.3 리팩토링
- “행동 변화 없음”을 테스트로 증명
- 파일/모듈 이동 시 import 경로 정리 + 문서 업데이트

## 4. 커밋/PR 품질 체크리스트 (에이전트용)
- [ ] `uv sync` 성공
- [ ] `make fmt` 통과
- [ ] `make lint` 통과
- [ ] `make type` 통과
- [ ] `make test` 통과
- [ ] 변경에 맞게 README/docs 갱신
- [ ] 민감정보 누출 없음
- [ ] 로그에 PII/토큰 노출 없음

## 5. 에러 발생 시 보고 형식
- 실패한 명령어
- 핵심 에러 로그(상단/하단 20줄)
- 재현 단계
- 원인 추정(가능하면)
- 해결안(수정 diff 요약)