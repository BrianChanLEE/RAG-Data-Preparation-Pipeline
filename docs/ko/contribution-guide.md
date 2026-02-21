# Contribution Guide (기여 가이드라인)

**대상 독자**: 오픈소스 컨트리뷰터, 사내 외부 팀 협업자
**목적**: 프로젝트에 새로운 기능을 제안하거나 버그를 고치고 병합(PR)하기 위한 원칙과 규칙을 정의합니다.

---

## 1. 코드 컨벤션 (Code Convention)

이 파이프라인은 유지보수성과 가독성을 위해 매우 엄격한 룰을 따릅니다.
- **Python 버전**: `3.10` 이상.
- **타입 힌팅 강제**: 모든 함수명, 파라미터 및 반환값에 대해 Type Hint(`-> bool`, `ctx: RunContext`)를 누락 없이 작성해야 합니다.
- **포매터**: `Black` 에 준수하는 라인 브레이크와 들여쓰기 4칸, `flake8` 린트룰 준수.

## 2. 새로운 구조화 파서(Extractor) 추가 절차

파이프라인에 새로운 확장자 지원(ex: `.docx`, `.md`)을 원한다면 다음 아키텍처 규칙을 위배해선 안 됩니다.

1. `ragprep/core/extract_{format}.py` 스크립트를 생성합니다.
2. 타 모듈 의존성을 피하고, 입력은 오직 `FileMeta`와 `RunContext`만 받습니다.
3. 리턴 값은 추출된 순수 원시 텍스트와 디스크 저장 로직이 포함되어야 하며 `True/False`로 성공 여부를 반환합니다.
4. `ragprep/core/router.py` 내의 `process_document` 함수에 해당 파서를 분기(if-elif)로 등록하십시오.

## 3. PR(Pull Request) 병합 조건 (Merge Criteria)

우리는 시스템의 내결함성(Fault tolerance) 붕괴를 원치 않습니다.
PR 제출 시 아래 조건이 선행되어야 합니다.

- `Pydantic` Data 모델 스키마가 변경되었다면 `SCHEMA_VERSION` 상수를 올려야 합니다.
- 기존의 정상 동작하던 추출기를 부수지 않았는지(Regression) 로컬에서 `python -m ragprep.prepare` 를 전체 `--force` 재수행하여 검증 스크린샷 1부를 첨부해야 합니다.
- 외부 라이브러리 추가(`requirements.txt` 변경)는 보안상의 이유로 사전 승인 없이 거절될 수 있습니다. 순수 내장 패키지(Standard Library) 사용을 압도적으로 우선하십시오.
