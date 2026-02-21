# Run Manifest & Lineage (매니페스트와 데이터 혈통 추적)

**대상 독자**: 데이터 과학자, 감사팀 (Compliance)
**목적**: AI가 어떤 데이터를 바탕으로, 어떤 파라미터 환경에서 생성된 지식 모델인지 영구적으로 투명하게 추적하는 방안을 설명합니다.
**범위**: `ragprep/prepare.py` 매니페스트 발급 기능과 `chunk.jsonl` 내부의 `ChunkLineage` 모듈.

---

## 1. Run Manifest 구조 (실행 프로파일 박제)

RAG 엔진은 지속적으로 업데이트됩니다. 1년 뒤에 데이터베이스 내 청크의 원인을 스캔할 때 과거 문서가 어떤 설정으로 처리되었는지 알아야 합니다. 파이프라인이 실행을 종료할 때, 시스템은 `data/runs/{run_id}/manifest.json` 을 덤프합니다.

| 분류 (Section) | 제공되는 필드 (Fields) | 설명 |
| :--- | :--- | :--- |
| **운영 컨텍스트** | `run_id`, `started_at`, `finished_at` | 파이프라인이 생성된 고유 ID와 UTC 시작/종료 일시 |
| **런타임 환경** | `git_commit`, `requirements_hash`, `host_info` | 서버의 아키텍처, 패키지들의 무결성 해시 및 파이프라인 저장소 스냅샷 스탬프 |
| **파라미터** | `concurrency`, `pii_mask`, `executor_type` | 파이프라인 커맨드 호출 당시 주입되었던 튜닝 매개변수 설정 목록 |

## 2. Lineage (데이터 계보) 추적 메커니즘

수억 건의 레코드가 쪼개져 생성되는 벡터 DB에서, 답변을 구성한 특정 "청크" 한 단위의 신뢰성을 어떻게 증명할 수 있을까요? 파운더 레이어인 "청크 데이터" 객체 구조 안에는 이를 위한 계보(Lineage) 메타데이터가 설계되어 있습니다.

```json
{
  "chunk_id": "abx-cd-12-c2",
  "text": "태초에 하나님이 천지를 창조하시니라...",
  "lineage": {
    "doc_id": "genesis-1-merged",
    "group_id": "genesis",
    "revision": 3,
    "source_paths": [
      "/absolute/path/to/origin/genesis_1.xml"
    ],
    "stage_versions": {
      "schema": "1.0",
      "chunker": "1.0.0"
    }
  }
}
```

이 `lineage` 블록의 구조를 통해 우리는 역추적이 가능합니다.
- `source_paths`: 어떤 원시 파일을 가져와 변형한 것인지 명문화. 
- `revision`: 해당 파일 내용이 3번째 해시 업데이트를 맞이해 추출된 최신본이라는 것을 데이터베이스 상에서 입증.
- `stage_versions`: 추출 알고리즘 구경에 있어 청킹이나 파이프라인 스키마가 혹시나 치명적 오류 파서(Version 0.9)로 생성되어 리마이그레이션이 필요한지 아닌지를 벡터 DB 차원에서 필터링할 수 있도록 보조.
