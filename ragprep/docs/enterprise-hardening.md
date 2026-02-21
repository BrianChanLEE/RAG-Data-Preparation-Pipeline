# RAG Data Preparation Pipeline - Enterprise Hardening Guide

본 문서는 RAG 데이터 파이프라인(`ragprep`)의 엔터프라이즈급 강화(Phase 4) 프로젝트 결과를 정리한 기술 안내서입니다. 대규모 배치 환경에서 안정성, 재현성, 그리고 보안을 보장하기 위해 7가지 주요 아키텍처가 도입되었습니다.

## 1. 7가지 강화 사항 기술 아키텍처

### 1) 품질 게이트 (Quality Gate) - `core/quality.py`
청크 품질 저하(예: 지나치게 짧은 청크 다수 발생)를 사전에 차단하기 위한 모듈입니다.
- **역할**: `prepare.py` 결과물의 길이를 분석하여 정상(`PASS`), 리뷰 필요(`REVIEW`), 격리(`QUARANTINE`) 상태로 자동 분류합니다.
- **라우팅**: `router.py`의 `finalize_processing`에서 상태에 따라 `data/review/` 또는 `data/quarantine/` 폴더로 문서를 이동하고 `quality.json` 리포트를 기록합니다.

### 2) 재현 가능한 빌드 (Lineage & Manifest) - `core/models.py`
배치 작업의 추적성을 보장하고 결과물의 출처와 버전을 묶어 관리합니다.
- **역할**: 파이프라인 실행 시 `manifest.json` 을 생성해 실행 환경(`git_commit`, 파라미터 등)을 기록합니다. 단일 청크 역시 생성 규칙의 버전을 담은 `lineage` 속성이 `chunks.jsonl`에 포함됩니다.

### 3) 관측성 (Observability) - `core/logging.py`
문서 처리 시 단계별로 JSON 형식의 표준 규격 로그와 메트릭을 발행합니다.
- **역할**: Splunk, Datadog 같은 중앙 관제 시스템과 연동하기 쉽도록 `run_id`, `duration_ms`, `event` 필드를 가진 로그 기록. 실행 완료 시 `metrics.json` 형태로 p95 요약 통계를 배출합니다.

### 4) 중복 검출 및 버전 관리 (Dedupe & Revision) - `core/dedupe.py`
동일 내용의 청크가 의미 없이 RAG DB에 인덱싱되는 것을 막고, 문서 갱신 여부를 캐치합니다.
- **역할**: n-gram Fingerprinting 및 Jaccard 유사도 분석 알고리즘을 사용해 중복되는 청크(동일 문서 내 혹은 그룹 내)를 건너뜁니다. `structure.py` 단계에서 이전 정제본의 `SHA256` 해시와 비교해 변경시에만 `revision`을 증가하고 백업합니다.

### 5) JWPUB 추출 강화 - `core/extract_jwpub.py`
복합 아카이브 구조인 JWPUB 처리를 대폭 고도화하여 오류율을 개선합니다.
- **역할**: 우선순위를 HTML 추출로 변경하고, 추출간 실패 파일이 생겨도 파이프라인을 멈추는 대신 `extract_warnings` 목록에 실패기록을 달고 계속 진행(부분 성공)합니다. HTML 내부의 불필요한 태그 파싱과 연속 텍스트 병합(`_clean_html`) 정제 스펙이 반영되었습니다.

### 6) 워크큐 / 재시도 / DLQ (Executor) - `core/executor.py`
GIL 차단을 극복하는 멀티 프로세싱과 실패 시 복구를 위한 내결함성 통제 모듈입니다.
- **역할**: ThreadPool 혹은 ProcessPool 실행기를 동적으로 선택할 수 있도록 추상화(`BaseExecutor`)하였습니다. 또한 `RetryWrapper`를 통해 실패 시 지수 백오프(`retry_backoff_ms`)와 재시도를 제어하며, 최종 실패 항목은 `quarantine` 대신 `dlq/`(Dead Letter Queue)로 전달됩니다.

### 7) 보안 및 컴플라이언스 (PII & Zip Bomb) - `core/pii.py`
사용자 개인정보(PII) 유출 및 악의적 압축 파일로부터 시스템을 방어합니다.
- **역할**: 텍스트 정제(`normalize.py`) 시 이메일, 전화번호, 주민번호 등의 민감 데이터를 정규식으로 마스킹(`[EMAIL]`, `[PHONE]`)합니다. JWPUB 추출 시에도 Zip Bomb 방어를 위한 `MAX_FILES`, `MAX_TOTAL_SIZE` 검사가 들어가 있습니다.

---

## 2. 확장된 CLI 옵션 사용법 예시

다음은 새롭게 도입된 CLI 파라미터들을 조합한 종합적인 실행 예시입니다.

```bash
# 그룹화, 품질 분석, DLQ/재시도, 중복제거, 개인정보 마스킹 등 전체 엔터프라이즈 모드 실행
python -m ragprep.prepare \
  --input-dir data/raw \
  --output-dir data/prepared \
  --force \
  --concurrency 4 \
  --merge-group true \
  --quality-gate true \
  --dedupe true \
  --dedupe-scope doc \
  --executor process \
  --max-retries 2 \
  --retry-backoff-ms 1000 \
  --pii-mask
```

### 주요 추가 옵션 설명
* `--executor`: 작업 병렬화 기법 선택 (`process` 권장, I/O 바운드만 있을 경우 `thread`)
* `--max-retries` / `--retry-backoff-ms`: 분석 중 에러가 났을 때 최대 재시도 횟수, 딜레이 대기시간.
* `--pii-mask`: 정칙 표현식 기반을 이용해 PII를 제거해야 할 경우 추가합니다.
* `--dedupe` / `--dedupe-scope`: 데이터베이스화 전 In-Memory 중복 제거 기능 (범위를 `doc` 또는 `group`으로 지정).

---

## 3. 권한 관리 가이드 적용 (Permissions)

생성된 데이터는 매우 높은 보안 등급이 적용된 인프라에서 운용되므로 **Linux/Unix 파일 퍼미션 통제**가 뒤따라야 합니다. 그룹 권한을 초과하는 데이터 접근을 막기 위해 파이프라인의 결과물엔 권한 수준 분리가 필요합니다.

### 1) 파이프라인 레벨 자동 권한 할당
애플리케이션(코드) 관점에서는 파이프라인이 저장하는 마지막 단계에서 `os.chmod()`를 통해 마스크를 제한하는 방식을 추천합니다. 

```python
import os
import stat
from pathlib import Path

def secure_save_document(data: str, out_path: Path):
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(data)
        
    # 소유자와 그룹 소유자만 읽기/쓰기 가능하도록 0640 (rw-r-----) 권한 적용 예시
    # 보안 요구사항에 따라 0600 으로 배타적 통제 가능
    os.chmod(out_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
```

### 2) 시스템 디렉터리 umask 설정
해당 RAG 파이프라인을 구동하는 계정에 시스템 마스크(`umask 027` 또는 `umask 077`)를 설정하여, 기본 생성 리소스에 대해 Everyone(Other) 권한이 자동으로 차단되도록 운영체제 단의 조치를 우선 수행하시기 바랍니다.

```bash
# 구동 환경 (e.g. ~/.bash_profile, systemd service unit)
umask 027
```
