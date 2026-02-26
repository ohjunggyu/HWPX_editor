# Architecture Rules

## 1. 목표
- 변경 비용 최소화
- 테스트 용이성
- 경계(레이어) 기반의 책임 분리

## 2. 권장 레이어
- `app/api` : FastAPI 라우터, request/response 변환(얇게)
- `app/service` : 유스케이스(비즈니스 로직)
- `app/domain` : 도메인 모델/규칙(순수)
- `app/repo` : 저장소 접근(인터페이스 + 구현)
- `app/infra` : 외부 시스템(HTTP client, queue, cache)
- `app/core` : 설정, 로깅, 공통 유틸

## 3. 의존성 방향 규칙
- domain은 외부 프레임워크에 의존하지 않습니다.
- api → service 만 호출합니다.
- service는 repo/infra를 **인터페이스**로 의존합니다(의존성 역전).
- repo/infra는 domain 모델을 사용할 수 있습니다.

## 4. DI(Dependency Injection) 원칙
- service는 구체 구현이 아닌 프로토콜/인터페이스를 받습니다.
- 테스트에서는 fake/mock repo를 주입해 unit test를 유지합니다.

## 5. 예외/에러 처리 원칙
- domain/service 레이어에서 가능한 한 의미 있는 예외 타입을 정의합니다.
- api 레이어에서 예외를 HTTP 응답으로 매핑합니다.
- 로그에는 stack trace를 남기되 민감정보는 마스킹합니다.

## 6. 설정(Config) 원칙
- 설정은 `app/core/config.py` 단일 진입점에서 관리합니다.
- 런타임에 필수 설정이 없으면 즉시 fail-fast 합니다.