# Revision Policy (리비전 관리 정책)

**대상 독자**: 파이프라인 엔지니어, 데이터 버전 관리자
**목적**: 문서의 이력과 버전을 안전하게 추적 및 보존하는 아키텍처 전략에 대해 학습합니다.
**범위**: `ragprep/core/structure.py` 의 해시 비교와 리비전 롤오버 체계.

---

## 1. Doc_ID 설계 철학

`doc_id`는 파일 시스템의 물리적 이름(예: `01.xml`)과 폴더의 그룹 식별자(`test_group`) 조합, 그리고 간혹 해시를 포함하여 만들어집니다. 파이프라인의 멱등성과 RAG 검색의 단일 진실 공급원(Single Source of Truth)을 유지하기 위해, `doc_id`는 전역적으로 유일해야 합니다. `--merge-group` 이 적용될 경우 폴더 이름인 `test_group-merged`가 식별자가 됩니다.

## 2. Revision 증가 조건 및 트리거 로직

파이프라인은 무작위로 문서를 덮어쓰거나, 불필요한 IO 비용을 지출하지 않습니다.

```mermaid
flowchart LR
    A[정제 완료 텍스트 유입] --> B[SHA256 Hash 계산]
    B --> C{기존 Document.json<br>존재 여부 확인}
    C -- "YES (존재)" --> D{Hash 값 비교}
    C -- "NO (신규)" --> E[Revision = 1 부여]
    
    D -- "Hash 불일치 (변동)" --> F[기존 파일 Revisions/ 하위 이동]
    F --> G[Revision = Old + 1 부여]
    D -- "Hash 일치 (동일)" --> H[Revision 유지 (Skip/Overwrite)]
    
    E --> I((저장))
    G --> I((저장))
    H --> I((저장))
```

문서의 텍스트 콘텐츠(Section들의 글 결합체) 전체의 `SHA256` 체크섬을 떠서 이전 상태(기존 `document.json` 안의 `normalized_sha256`)와 대조합니다.
- 토씨 하나라도 바뀌면 해시는 달라지므로, 이를 기반으로 **스냅샷 백업** 후 신규 버전을 작성합니다.

## 3. 과거 버전 롤백(Rollback) 및 파일 위치 전략

업데이트(Revision + 1)가 트리거될 경우, 덮어쓰기 이전에 원본 문서를 안전하게 아카이브 합니다.
파일은 `data/prepared/documents/revisions/{old_revision}/` 위치로 무브(복사) 됩니다.
이로써 파이프라인 운영 중 데이터가 파괴되거나 잘못 업데이트되더라도 즉시 복원이 가능한 버전 트리가 구축됩니다.
