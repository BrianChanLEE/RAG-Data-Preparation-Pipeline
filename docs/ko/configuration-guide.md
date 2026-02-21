# Configuration Guide (설정 가이드)

**대상 독자**: 파이프라인 관리자
**목적**: 하드코딩된 규칙들의 임계치 조정, 시스템 변수 세팅 등 CLI 외부의 설정 제어 방식을 익힙니다.
**범위**: Zip Bomb 용량 한계, 청킹 글자수 타겟, Quality 점수 비율 등.

---

## 1. 내부 상수 (Constants) 설정 튜닝 가이드

파이프라인의 몇몇 보안 임계치 및 통나무 정제 사이즈는 엔터프라이즈 특성상 CLI 파라미터가 아닌 내부 스크립트 상수에 캡슐화되어 있습니다. 커스텀이 필요할 경우 아래의 파일에서 조정하십시오.

### 🛡 Zip Bomb (JWPUB 방어 한계선)
- **파일**: `ragprep/core/extract_jwpub.py`
- JWPUB 내 파일을 열 때, 단일 파일이나 풀린 용량의 최대 허용치를 지정합니다. 메모리가 적은 서버라면 하향 조정하십시오.
  - `MAX_FILES = 5000` (기본 5,000개 파일 개수 방어)
  - `MAX_TOTAL_SIZE = 500 * 1024 * 1024` (압축 해제 총 볼륨 500MB 방어)
  - `MAX_FILE_SIZE = 100 * 1024 * 1024` (압축 내 단일 파일의 거대 팽창 100MB 컷오프)

### ✂️ Semantic Chunk Length (청크 길이)
- **파일**: `ragprep/core/chunk.py`
- LLM 모델 윈도우 한계나 임베딩 모델의 차원에 맞게 이 값을 먼저 조정해야 합니다.
  - `target_len = 1000`: 1,000자 기준으로 의미론적 단절(마침표/엔터) 지점 탐색.
  - `overlap_len = int(target_len * 0.15)`: 앞뒤 청크와 컨텍스트를 이어주기 위해 가져갈 겹침 단어의 비중 제한.

### 💯 Quality Gate Threshold (품질 기준 폭)
- **파일**: `ragprep/core/quality.py`
- `PASS`/`REVIEW`의 합격 기준을 결정하는 비율입니다.
  - `short_ratio > 0.9` -> `REVIEW`: 길이가 극단적으로 짧은 조각들의 비율이 90%가 넘어갈 경우 리뷰 격리 처리 룰.
  - `meaningless_ratio > 0.6` -> `QUARANTINE`: 쓰레기값 특수기호(`<>` 등) 비율이 너무 높은 텍스트 덩어리 파기 룰.

## 2. 외부 환경변수 (Environment Variables)

별도의 환경변수를 필수로 물고 들어가진 않지만 시스템 차원에서 Python 관련 퍼포먼스나 메모리를 할당하기 위한 옵션들은 유효합니다.

```bash
# 멀티 코어 운영 시 Python 해시시드 램덤화 고정 (선택 사항)
export PYTHONHASHSEED=0

# umask: RAG 산출물이 Linux상에서 권한 탈취 당하지 않도록 배치 스크립트 전에 선행되어야 함
umask 027
```
