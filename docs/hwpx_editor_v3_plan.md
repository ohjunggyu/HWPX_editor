# HWPX Editor (AI Agent Tool) v3.0 최종 설계 및 구현 기획서

## 1. 개요 (Overview)

본 문서는 AI Agent가 HWPX 파일을 파괴하지 않고 안전하게 읽고 쓸 수 있도록 지원하는 **HWPX Editor API 서버**의 최종 아키텍처(v3.0) 및 개발 로드맵을 정의합니다.
기존 `python-hwpx` 라이브러리의 무거운 객체 모델 대신, **Native ZIP/XML 파싱 및 Block ID 기반 맵핑** 구조를 채택하여 경량화와 안정성을 극대화합니다.

## 2. 코어 아키텍처 전략 (Core Architecture)

### 2.1. Native XML 파싱 및 Block ID 맵핑

HWPX 파일은 ZIP 아카이브 형태의 OXML 구조를 가집니다. 본 프로젝트는 외부 의존성을 최소화하고 제어력을 높이기 위해 다음과 같은 접근을 취합니다.

* **파일 처리**: `zipfile` 모듈을 이용해 HWPX 파일을 임시 디렉토리에 압축 해제 및 재압축합니다.
* **XML 조작**: `lxml`을 이용하여 문서 본문인 `Contents/section0.xml`을 직접 탐색 및 조작합니다.
* **Block ID 생성**: LLM이 복잡한 XML 트리를 직접 다루지 않도록, 파싱 단계에서 각 문단(`<hp:p>`)과 표 셀(`<hp:tc>`)에 일차원적이고 직관적인 고유 식별자(Block ID)를 부여합니다.
  * 예시: `sec0_p1` (0번 섹션, 1번 문단), `sec0_tbl1_r0_c0` (0번 섹션, 1번 표, 0행 0열 셀)

### 2.2. 태그 파편화 방지 알고리즘 (Fragment Resolution)

HWPX 문서 내에서 동일한 단어라도 서식(글꼴, 색상, 굵기 등)이 다르면 여러 개의 `<hp:t>`(Text Run) 태그로 분할되는 현상(파편화)이 발생합니다. 단순 문자열 치환은 파일 서식을 손상시킬 수 있습니다.

* **Length Distribution (길이 비례 분배) 패턴 적용**:
    1. Block 내의 모든 `<hp:t>` 태그 텍스트를 하나로 병합하여 치환을 수행합니다.
    2. 새롭게 치환된 전체 문자열의 길이를 기존 `<hp:t>` 태그들의 텍스트 길이 비율(Weight)에 맞춰 재분할합니다.
    3. 재분할된 텍스트를 기존 `<hp:t>` 태그에 덮어씀으로써, 기존 서식을 100% 보존하면서 안전하게 텍스트만 치환합니다.

## 3. 모듈별 상세 설계 (Module Specification)

### 3.1. Infrastructure Layer (`app/infra/hwpx_tool.py`)

문서의 압축, 해제 분석 및 치환을 담당하는 시스템의 심장부입니다.

* `extract_hwpx(file_path: str) -> str`: HWPX 파일을 임시 환경에 압축 해제합니다.
* `iter_blocks(section_xml_path: str) -> Iterator[dict]`: XML 트리를 순회하며 `block_id`, `type`, `text` 정보를 추출하여 평탄화(Flatten)된 형태로 반환합니다.
* `apply_modifications(section_xml_path: str, modifications: list[ModificationItem]) -> None`: Agent로부터 전달받은 `block_id`를 기반으로 해당 XML 노드를 찾아, 파편화 방지 알고리즘을 적용하여 텍스트를 안전하게 치환합니다.
* `package_hwpx(temp_dir: str, output_path: str) -> None`: 조작이 완료된 임시 디렉토리를 다시 유효한 HWPX ZIP 파일로 패키징합니다.

### 3.2. Service Layer (`app/service/editor_service.py`)

Infrastructure 모듈을 오케스트레이션하여 비즈니스 트랜잭션을 처리합니다.

* `process_read_request(...)`: 업로드된 파일을 읽고 Block ID 배열을 반환합니다.
* `process_modify_request(...)`: 원본 파일과 수정 사항(JSON)을 입력받아, 백그라운드에서 임시 폴더 생성 -> 압축 해제 -> XML 조작 -> 재압축의 파이프라인을 안전하게 실행하고 최종 결과물의 경로를 반환합니다.

### 3.3. API Layer (`app/api/endpoints.py`)

AI Agent와의 통신을 위한 REST API 엔드포인트를 노출합니다.

* `POST /api/v1/hwpx/read`:
  * **Input**: `file` (UploadFile, .hwpx)
  * **Output**: `JSON Array` (문서 내 모든 텍스트 블록의 ID와 내용)
* `POST /api/v1/hwpx/modify`:
  * **Input**: `file` (UploadFile), `modifications` (JSON string)
  * **Output**: `FileResponse` (수정 완료된 .hwpx 구동 파일)

## 4. 단계별 구현 로드맵 (Execution Plan)

1. **Phase 1: 아키텍처 설계 및 검증 (완료)**
    * 레퍼런스 레포지토리(`python-hwpx`, `hwpx-mcp-server`) 심층 분석 및 파편화 해결 알고리즘 차용 결정.
2. **Phase 2: Core Infrastructure 구현 (현재 진행 대상)**
    * `hwpx_tool.py` 파일 생성 및 `lxml`, `zipfile` 기반의 압축/해제 로직 작성.
    * XML 트리 탐색 및 `Block ID` 부여 로직 구현.
    * 파편화 방지 텍스트 치환 알고리즘 이식 및 검토.
3. **Phase 3: Domain & Service 계층 연동**
    * FastAPI Pydantic 모델(`models.py`) 작성.
    * `editor_service.py` 파이프라인 구성.
4. **Phase 4: API 라우터 개방 및 테스트**
    * `endpoints.py` 연결.
    * Unit Test 및 E2E Test (FastAPI TestClient 연동).
5. **Phase 5: 검수 및 퀄리티 게이트**
    * `make fmt`, `make lint`, `make type` 통과 확인.
    * 수정된 HWPX 파일이 실제 한컴오피스 뷰어에서 정상적으로 열리는지 무결성 검증.
