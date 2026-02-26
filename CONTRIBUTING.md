# Contributing Guide

## 1) 개발 환경
- Python 버전은 `pyproject.toml`의 `requires-python` 기준을 따릅니다.
- 의존성/실행은 **uv로만** 수행합니다.

### 설치/동기화
- `uv sync`

### 실행(예시)
- `uv run python -m app`

## 2) 품질 게이트 (필수)
PR을 올리기 전 아래를 모두 통과해야 합니다.
- `make fmt`
- `make lint`
- `make type`
- `make test`

## 3) PR 규칙
- PR은 가능한 작게 나눕니다(리뷰 가능 크기).
- 버그 수정 PR에는 **회귀 테스트**가 포함되어야 합니다.
- API/동작 변경이 있으면 `docs/` 또는 `README.md`를 갱신합니다.

## 4) 커밋 메시지 권장
- feat: ...
- fix: ...
- refactor: ...
- test: ...
- docs: ...
- chore: ...

## 5) 보안/비밀정보
- 토큰, 키, 개인식별정보(PII)는 절대 커밋하지 않습니다.
- 로그에도 토큰/민감정보가 출력되지 않도록 주의합니다.