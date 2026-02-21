# Failure Handling (실패/예외 처리 체계)

**대상 독자**: 시스템 운영자, L2/L3 서포트 엔지니어
**목적**: 파이프라인 구동 중 인입되는 비정상 데이터 및 예외 상황에 시스템이 붕괴하지 않고 복원되는 메커니즘을 설명합니다.

---

## 1. 실패 관리 3단계 방어선

대규모의 온프레미스 배치 작업에서는 파서(Parser)의 치명적 결함 하나가 수만 개의 정상 파일 진행마저 롤백시키는 대참사로 이어집니다. 본 시스템은 3가지 안전장치(Safeguard)를 가동합니다.

1. **부분 성공 (Partial Success)**: JWPUB 등 압축 아카이브에서 단일 파일의 HTML을 읽지 못하는 에러가 발생하면 배치를 중단(Raise)하지 않고, 리턴 객체에 `extract_warnings` 메타리스트를 달아 성공 처리 후 넘깁니다.
2. **Exponential Backoff 재시도 (Retries)**: 일시적 I/O 오류나 스레드 락이 발생했다면 `Executor`는 슬립 대기 후 재시도합니다.
3. **격리 (Quarantine & DLQ)**: 모든 재시도에도 죽어버리는 파일은 다른 정상 파일들에 영향을 주지 않기 위해 에러 로그와 함께 `dlq/` 로 이동하고 파이프라인에서 버려집니다. (Skip)

## 2. 장애별 대응 매뉴얼 (Exception Playbook)

| 에러 시그니처 로그 (Log Signature) | 트리거 원인 | 권장 행동 조치 사항 |
| :--- | :--- | :--- |
| `Zip bomb detected: {size} > {MAX}` | JWPUB 용량이 폭발적으로 늘어나는 바이러스나 오염 파일 인입 시. | 악의적 문서이므로 `quarantine/` 이동분 즉시 삭제 권장. |
| `UNHANDLED_ERROR` in `router.py` | 모듈의 버그나 이전에 겪지 못한 인코딩, 포맷 파괴 현상 발생 시. | `data/dlq/`로 이관된 원본 파일을 디버거로 직접 스텝 쓰루. |
| `QualityDecision.REVIEW` & `Too many short chunks` | 성경 데이터 등 극단적으로 짧은 포맷의 정상적인 변형 현상 시. | 내용 확인 후 `review/` 폴더 내 파일을 수동으로 인덱서에 탑재. |

## 3. 재처리 (Retry) 운영 방식

DLQ나 Review 큐에 들어간 문서를 패치 후 다시 태우려면, 해당 파일들을 다시 `data/raw/` 입력 폴더에 삽입한 후, 아래 명령어를 실행하십시오. 
파이프라인의 멱등 메커니즘 덕에, 이미 성공 처리 완료된 전체 문서는 `#success.json`의 존재 유무 확인 덕분에 1초 만에 스킵되고 **오직 재투입된 오류 파일만 핀포인트로 처리됩니다.**

```bash
python -m ragprep.prepare --executor thread
```
