# Enterprise Hardening (엔터프라이즈 운영 가이드)

**대상 독자**: 운영팀 (DevOps, SecOps), 안정화 배포 담당자
**목적**: RAG 파이프라인을 운영 도중 발생할 수 있는 장애 상황 대응, 복구 전략 및 시스템 권한 설정을 위한 체크리스트.

---

## 1. 운영 체크리스트 (Operations Checklist)

| 구분 | 검증 항목 | 담당 조치 내역 | 상태 |
| :--- | :--- | :--- | :---: |
| **보안** | `PII Masking` 적용 여부 검토 | 데이터가 민감한 식별자(`주민번호`, `전화번호`)가 평문으로 돌아다니지 않도록 CLI 파라미터 점검 방지. | [ ] |
| **권한** | umask 시스템 변수 제어 | Linux 환경 내 파이프라인 실행 유저의 배치 유저 소유권 0640 `r--` 등 보장 조치 (Other Account 차단). | [ ] |
| **로깅** | 중앙 관제 인프라 적재 연동 | JSON 포맷 로그(`rag-prepare-{run_id}.log`)를 Datadog/Splunk의 데몬 리더와 매핑 및 인덱싱. | [ ] |
| **성능** | Process/Thread Executor 점검 | I/O, CPU 병목에 따른 알맞은 `--executor` 전략 변경 및 튜닝(Concurrency Core 확보). | [ ] |

## 2. 장애 발생 시 DLQ (Dead Letter Queue) 사용 방법론

파이프라인이 재시도 한계를 넘겨 실패(Failed)한 문서는 영원히 버려지지 않고, 디버깅을 위해 온전한 상태 그대로 `data/dlq/{doc_id}/` 디렉터리에 복제됩니다. 

```mermaid
flowchart TD
    Error{Exception 발생} --> Retry[Retry Exponential Backoff]
    Retry --> Error
    Error -- "Max Retries 초과" --> Move[복사물 이동]
    Move --> DLQ>data/dlq/{doc_id}/원본.pdf]
    Move --> Log>data/dlq/{doc_id}/error.log]
```

**[장애 대응 시나리오]**
1. 모니터링 경보(Alert)가 파이프라인 실패 문서 누적을 알립니다.
2. 운영자는 `data/dlq` 폴더 안에 쌓인 파일들의 `error.log` 를 열어 스택 트레이스(`UNHANDLED_ERROR` 등)를 식별합니다.
3. 원인(데이터 손상, 파싱 불가)을 파악하고 파서 코드를 수정한 뒤 패치 버전을 릴리즈합니다.

## 3. 재처리 (Reprocessing) 전략

코드 패치가 끝나거나 `reasons` 가 해결되었다면 문서를 시스템에 재인입시켜야 합니다.

- **파이프라인 재실행**: 파이프라인은 멱등성이 있으므로 전체 파이프라인을 그대로 다시 돌려도 무방합니다 (`#success.json` 식별 메커니즘 작동). 하지만 처리 속도를 비약적으로 늘리려면 `data/dlq`에 방치된 문서를 바로 잡아 다시 `data/raw/` 폴더에 넣고 스캐너에 태우십시오.
- **캐시 초기화**: 특정 단계나 문서를 완전 무효화하고 처음부터 로직(예: 청킹 룰 교체)을 돌리고 싶을 때는 해당 디렉토리의 데이터 로그만 지우거나 과감하게 커맨드 인수 `--force` 플래그를 넣고 전체 배치 명령어를 호출하십시오. 이 경우에는 `revisions` 리비전도 증분 생성되며 이력을 안전하게 덮어쓸 것입니다.
