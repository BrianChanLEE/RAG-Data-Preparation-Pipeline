# Observability (관측성)

**대상 독자**: SRE 엔지니어, 운영팀
**목적**: 중앙 집중식 로깅 인프라 플랫폼(Splunk, Datadog, ELK)과 파이프라인의 시스템 연동 및 분석 지표 수집 방식을 설명합니다.
**범위**: `ragprep/core/logging.py` 및 파이프라인의 `metrics.json` 생성.

---

## 1. 구조화 JSON 로깅 (Structured JSON Logging)

배치 프로세스에서 출력되는 단순 문자열 텍스트 로그는 필터링과 모니터링 경보(Alerting)를 구축하는 데 한계가 있습니다. 이 파이프라인에서는 `python-json-logger` 라이브러리를 통합해 모든 로그 스펙을 기계가 읽을 수 있는(machine-readable) JSON 페이로드로 정밀하게 표준화했습니다.

### 로그 표준 필드 명세

| 로그 필드 명 (`Key`) | 타입 (`Type`) | 설명 (`Description`) |
| :--- | :--- | :--- |
| `timestamp` | String | ISO-8601 포맷 타임스탬프 (UTC/Local) |
| `level` | Enum | `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `name` | String | 로거 이름 (예: `ragprep.router`) |
| `run_id` | String | UUID (v4) - 동일한 배치 시도를 단일 세션으로 묶음 |
| `doc_id` | String | 로그 발송의 주체가 되는 고유 문서명 |
| `group_id` | String | 다중 문서를 병합했을 때 부여되는 폴더 스코프 명 |
| `stage` | String | 파이프라인의 생명주기 위치 (`extractor`, `normalizer`) |
| `event` | String | 특정 라이프사이클 훅 타이틀 (`stage_start`, `stage_end`) |
| `duration_ms` | Integer | 이전 이벤트 대비 소요 시간 (밀리초) - Slow 쿼리 탐색용 |
| `message` | String | 개발자가 남긴 자유 텍스트 로그 요약본 |

## 2. 간소화 메트릭 구조 (Metrics Payload)

배치가 파이프라인 전체를 한 바퀴 정상 종료할 때 커맨드의 성공 지표를 단일 객체 통계치로 만들어 `data/runs/{run_id}/metrics.json` 에 생성합니다. 이는 사후 장애 분석 및 배포 파이프라인 성능 체크(Regression)에 활용됩니다.

```json
{
  "run_id": "8b3401fa",
  "total_duration_sec": 34.12,
  "docs_processed": 542,
  "quarantine_rate": 0.05,
  "duration_p95_ms": 120,
  "duration_mean_ms": 45
}
```

## 3. 장애 분석(Troubleshooting) 방법론

- **특정 에러 문서의 흐름 파악하기**: Elasticsearch/Kibana와 같은 도구에 로그가 탑재되었다면, 검색창에 `doc_id: "xyz123"` 쿼리를 질의하여 해당 문서가 언제 스캔되었고 어느 단계에서 Quarantine으로 격리되었는지 단 한 번에 알 수 있습니다.
- **병목 구간 추적**: 로그의 `duration_ms` 필드를 백분위수로 조회해 어느 `stage`에서 문서 처리가 지연되고 있는지 즉각적인 CPU 프로파일링 힌트를 획득할 수 있습니다.
