# HWPX 레퍼런스 레포지토리 심층 분석 보고서

본 문서는 HWPX Editor AI Agent 구축을 위해 핵심적으로 참고한 두 오픈소스 프로젝트(`python-hwpx`, `hwpx-mcp-server`)의 디렉토리 구조, 코어 로직, 그리고 우리 프로젝트에 적용할 핵심 차용 코드들을 바닥부터 상세히 분석한 기술 문서입니다.

---

## 1. `python-hwpx` (Low-level HWPX Library)

`python-hwpx`는 한글(HWPX) 문서의 압축(ZIP) 해제부터, 내부의 복잡한 OXML(Open XML) 기반 태그들을 파이썬 객체로 역직렬화(매핑)해주는 저수준 라이브러리입니다.

### 1.1. 핵심 디렉토리 및 파일 구조

```text
hwpx_reference/src/hwpx/
├── core/
├── exceptions.py
├── oxml/
│   ├── document.py     # HWPX 전체 문서 메타데이터 관리
│   ├── body.py         # 실제 본문(섹션, 문단, 표) 엘리먼트 파서
│   └── ...
└── templates.py        # 빈 문서 스켈레톤 압축 바이너리 제공
```

### 1.2. 주요 동작 원리

HWPX 파일은 사실상 `.zip` 파일이며 `Contents/section0.xml` 등에 본문이 들어있습니다.
이 라이브러리는 `xml.etree.ElementTree`나 `lxml`을 래핑하여 `<hp:p>`(문단), `<hp:t>`(텍스트) 등의 노드를 파이썬의 `Paragraph`, `Run` 객체로 매핑합니다.

#### 💡 우리 프로젝트 시사점

이 레포지토리 전체를 의존성으로 가져오면 프로젝트가 너무 무거워집니다. 대신, 우리는 이 라이브러리가 취하는 **"ZIP 압축 해제 -> lxml로 특정 태그 탐색 -> 직렬화"** 라는 핵심 어프로치만 차용하고, 실제 텍스트 조작은 더 가벼운 우리의 커스텀 인프라 코드(`hwpx_tool.py`)로 자체 해결합니다.

---

## 2. `hwpx-mcp-server` (High-level Agent Tool)

Agent(LLM)가 HWPX 파일을 손쉽게 읽고 쓸 수 있도록 MCP(Model Context Protocol) 형태로 고수준 작업을 래핑해놓은 서빙 툴입니다. 우리가 구상한 `HWPX_Editor`의 아키텍처와 가장 맞닿아 있습니다.

### 2.1. 핵심 디렉토리 및 파일 구조

```text
hwpx_mcp_reference/src/hwpx_mcp_server/
├── core/
│   ├── content.py      # 문단/표 추가, 삭제 등 CRUD
│   ├── handles.py      # [🔥핵심] 노드 위치 추적 식별자 (Node ID) 생성
│   ├── locator.py      # 파일 위치 및 시스템 경로 매핑
│   ├── plan.py         # [🔥핵심] 안전한 수정을 위한 트랜잭션 (Plan -> Preview -> Apply)
│   └── search.py       # [🔥핵심] XML 태그 파편화 방지 및 텍스트 교체 알고리즘
├── hwpx_ops.py         # 위 core 로직들을 묶어 HwpxOps 클래스로 노출
└── tools.py            # MCP Client를 위한 JSON Schema 기반 툴 정의
```

---

### 2.2. [핵심 분석 1] 태그 파편화 방지 알고리즘 (`core/search.py`)

한글 HWPX(그리고 워드 문서)의 가장 큰 골칫거리는 `안녕하세요` 라는 단어가, 서식이 중간에 바뀌면 `<hp:t>안녕</hp:t><hp:t>하세요</hp:t>` 로 찢어진다는 점입니다.
당순한 string replace로는 이 텍스트를 찾을 수 없습니다. `hwpx-mcp-server`는 이를 `_distribute_lengths` 라는 알고리즘으로 완벽히 해결했습니다.

**[차용할 핵심 코드 스니펫]**

```python
# src/hwpx_mcp_server/core/search.py 내의 일부분

def _distribute_lengths(total: int, weights: list[int]) -> list[int]:
    """텍스트가 변경되었을 때, 전체 길이를 기존 서식 태그들의 가중치(비율)에 맞게 재분배합니다."""
    # (코드 중략...) 기존 태그의 길이 비례에 맞춰 새 텍스트를 자를 크기 리스트 반환

def _replace_across_xml_runs(run_elements: list[Any], find_text: str, replace_text: str) -> int:
    """여러 <hp:t>(Run)에 찢어져 있는 텍스트를 찾아 서식을 유지하며 교체합니다."""
    texts = [_xml_run_text(run_element) for run_element in run_elements]
    merged = "".join(texts)
    
    # 1. 일단 문자열을 하나로 합쳐서 찾고자 하는 텍스트가 있는지 검사
    if find_text not in merged:
        return 0

    # 2. 치환된 전체 새 문자열 생성
    new_merged = merged.replace(find_text, replace_text)
    
    # 3. 기존 찢어져 있던 태그들의 텍스트 길이 가중치 계산
    weights = [len(text) for text in texts]
    
    # 4. 새 문자열을 기존 가중치에 맞춰 쪼갬 (핵심)
    redistributed = _distribute_lengths(len(new_merged), weights)

    cursor = 0
    # 5. 기존 XML 엘리먼트(Run)의 텍스트 값만 안전하게 갈아끼움
    for run_element, size in zip(run_elements, redistributed):
        _set_xml_run_text(run_element, new_merged[cursor : cursor + size])
        cursor += size

    return merged.count(find_text)
```

**👉 결론:** 우리가 `modify` 기능을 만들 때, 이 `_replace_across_xml_runs` 로직을 우리식으로 포팅하여 가져와야 문서 서식이 깨지는 것을 막을 수 있습니다.

---

### 2.3. [핵심 분석 2] 안정적인 노드 식별자 (`core/handles.py`)

LLM에게 문서 트리(`XML`)를 냅다 던져주고 특정 노드를 고치라고 하면 100% 에러가 납니다. 이것을 어떻게 일차원적인 ID(`block_id`)로 치환했는지가 중요합니다.

**[차용할 핵심 코드 스니펫]**

```python
# src/hwpx_mcp_server/core/handles.py

import hashlib
from typing import Iterable, Tuple

def stable_node_id(parts: Iterable[str | int]) -> str:
    """제공된 구조적 경로(예: section0_para1)를 기반으로 결정론적(해시) 식별자를 반환합니다."""
    normalized = _normalize_parts(parts)
    joined = "::".join(normalized)
    # 경로를 이어붙인 뒤 SHA256으로 해싱하여 고유 ID(n_xxxx) 생성
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
    return f"n_{digest}"
```

**👉 결론:** 우리가 채택한 **"방법 2: Block ID 기반 맵핑"** 의 완벽한 모범 사례입니다. 다만 SHA256 해시값 `n_3d8f2a...` 은 LLM에게 덜 직관적이므로, 우리는 해싱 대신 인간도 읽을 수 있는 명시적 경로(`sec0_p1_run2`)를 그대로 `block_id`로 서빙하는 방식으로 개선(Upgrade)하여 적용하겠습니다.

---

### 2.4. [핵심 분석 3] 롤백 가능한 변경 트랜잭션 (`core/plan.py`)

Agent의 "우발적 전체 수정"이나 "환각에 의한 엉뚱한 수정"을 막기 위해 3단계 확인 절차를 거칩니다.

```python
# src/hwpx_mcp_server/core/plan.py 구조 리뷰
class ServerResponse(BaseModel):
    # 1. 수정 계획서 (Plan)
    plan: Optional[PlanSummaryData] = None
    # 2. Diff 미리보기 (Preview)
    preview: Optional[PreviewData] = None
    # 3. 실제 적용 여부 (Apply)
    apply: Optional[ApplyData] = None
```

**👉 결론:** 보안상 매우 훌륭한 구조입니다. 하지만 현재 우리의 MVP 목표(FastAPI REST 연동)에는 한 번의 통신으로 수정을 끝내는 것이 효율적입니다. 따라서 이 3단계 트랜잭션 시스템 자체는 보류하되, **수정 전 `Target`과 `match` 문자열이 100% 일치할 때만 교체한다**는 철학만 가져오도록 하겠습니다.

---

## 3. 최종 요약 및 아키텍처 결론

`hwpx-mcp-server`의 심층 분석을 통해 우리의 `HWPX Editor` 아키텍처에 다음 기술들을 결정적으로 도입합니다.

1. **파서 및 라이브러리:** 무거운 `python-hwpx` 라이브러리 객체를 쓰지 않고, 순수 `lxml`과 `zipfile` 만을 이용해 `Contents/section0.xml`을 직접 조작하는 경량화 노선을 유지합니다.
2. **조작 안정성:** `search.py`에 등장한 `_distribute_lengths` 가중치 분배 알고리즘을 도입하여 찢어진 태그(`Run`) 문제를 해결합니다.
3. **LLM 상호작용 (Block ID):** `handles.py` 의 해싱 방식 대신, `sec{N}_tbl{M}_r{R}_c{C}` 형식의 명시적 `semantic ID`를 사용하여 LLM의 참조 능력을 극대화합니다.

이제 이 분석을 바탕으로 실제 `app/infra/hwpx_tool.py` 파일의 개발을 시작할 수 있는 완고한 기반이 마련되었습니다.
