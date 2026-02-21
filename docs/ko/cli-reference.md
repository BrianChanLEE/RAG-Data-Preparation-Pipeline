# CLI Reference (명령줄 인터페이스 가이드)

**대상 독자**: 배치 시스템 호출 파트, MLOps 크루
**목적**: 파이프라인의 실행 트리거에 쓰이는 아규먼트(Flags) 전반을 설명합니다.
**범위**: `ragprep/prepare.py` 모듈.

---

## 1. 구동 옵션 표 (Full Options Table)

파이프라인은 `argparse`를 통해 옵션을 받습니다. 아래 옵션을 조합해 다양한 엔터프라이즈 목적(속도 최적화, 보안 위주, 복구 등)을 달성할 수 있습니다.

| 인자명 (`Flag`) | 데이터 타입 / 기본값 | 설명 (Description) | 추천 (Usage) |
| :--- | :--- | :--- | :--- |
| `--input-dir` | Path (`data/raw`) | 읽어들일 원본 파일(.pdf, .jwpub, .xml)들의 루트 디렉터리. 하위 경로까지 재귀 스캔됨. | - |
| `--output-dir` | Path (`data/prepared`) | 정제 문서, 쪼개진 청크와 리포트들이 저장될 산출물 디렉터리. | - |
| `--force` | Boolean 플래그 | 만약 이전에 성공한 기록(`#success.json`)이 있더라도 강제 덮어쓰기 하고 리비전을 확인. | 재처리 / 버전 갱신 시 |
| `--concurrency` | Integer (`CPU Core수/2`) | 동시에 병렬로 돌릴 문서 / 그룹의 개수 제한. | I/O 바운드 시 증가 |
| `--merge-group` | String (`false`) | 물리적 하위 폴더 이름(`group_id`)을 바탕으로 다수의 파일을 단일 맥락 문서로 묶음. | 분할된 성경/교재 데이터 |
| `--min-chars` | Integer (`300`) | 문서의 총 텍스트 길이가 해당 수치 미만이면 쓸모없는 파일로 간주해 격리함. | 200~300 사이 |
| `--quality-gate` | String (`true`) | 청크들이 생성된 후 길이 및 쓰레기 값 분석 로직을 거치게 할 것인가? (`true`시 Review, Quarantine 분기 작동) | 엔터프라이즈 환경 시 필수 |
| `--dedupe` | String (`true`) | 똑같거나 85% 이상 일치하는 청크들이 반복 생성되는 것을 막을 것인가? | 필수 (오염 방지용) |
| `--dedupe-scope`| String (`doc`\|`group`) | 스코프를 현재 문서 내부(`doc`)로 할 것인지, 병합 그룹 전체(`group`) 간 비교를 할지 결정. | - |
| `--pii-mask` | Boolean 플래그 | 주민등록번호, 이메일, 휴대전화 등 민감 정보를 `[EMAIL]` 등의 패턴으로 치환함. | 클라우드 DB 연동 전 필수 |
| `--executor` | String (`process`\|`thread`) | 병렬 처리 엔진 지정. 프로세스 풀(속도/CPU 중심) 혹은 스레드 풀(가볍고 네트워크 대기가 긴 경우). | 주로 `process` 권장 |
| `--max-retries` | Integer (`1`) | 알 수 없는 추출 오류 시 파이프라인이 최대 몇 번 재시도할지 결정. (지수 백오프 적용) | 2 |
| `--retry-backoff-ms` | Integer (`2000`) | 재시도 시 첫 대기시간을 밀리초(ms)로 지정. 실패 시 이 시간은 두 배씩 늘어남. | API 연동 시 증가 |

## 2. 사용 사례 커맨드 (Usage Scenarios)

** 캐시 무효화 및 단일 프로세스 집중**  
(디버깅이나 메모리가 부족한 소형 배치 서버에서 돌릴 때)
```bash
python -m ragprep.prepare --force --concurrency 1 --executor thread --pii-mask
```

** 다수의 XML 파편들을 하나의 거대 문서로 압축할 때**  
(예: 수천 개의 개별 장/절 문서를 성경 한 권 컨텍스트에 담고 싶을 때)
```bash
python -m ragprep.prepare --merge-group true --dedupe-scope group
```
