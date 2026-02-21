# Release Process (배포 프로세스)

**대상 독자**: 릴리즈 매니저, 배포 자동화 파트
**목적**: 코드가 운영(Production) 서버의 온프레미스 장비에 배치되는 파이프라인 릴리즈 규격을 설명합니다.

---

## 1. 버전 관리 정책 (Semantic Versioning)

프로젝트는 `MAJOR.MINOR.PATCH` 룰을 따릅니다.
- **MAJOR**: Pydantic `ChunkSchema` 가 완전히 뒤집어져서 기존 Vector DB 모델과 충돌이 일어날 때 증가.
- **MINOR**: 새로운 Extractor(`.docx`, `.csv` 등) 포맷 지원, `--pii-mask` 같은 대형 피처 옵션 추가.
- **PATCH**: 파서 버그 수정, 텍스트 정제 찌꺼기 Regex 패턴 추가 수정 등.

## 2. 메이저 배포 스텝 (Deployment Steps)

온프레미스 내 `systemd` 기반 실행 환경을 주기로 배포합니다.

1. **저장소 클론 및 브랜치 동기화**
   ```bash
   git pull origin main
   git checkout tags/v1.2.0
   ```
2. **Requirements 무결성 체크**
   배포 환경 내 취약성 해소를 위해 필수 라이브러리 검토 후 가상환경(venv)에 덮어씁니다.
   ```bash
   pip install --upgrade -r requirements.txt
   ```
3. **스키마 버전 롤오버 (Schema Rollover)**
   개발자는 릴리즈 전 `core/models.py` 상단의 `SCHEMA_VERSION = "1.0"` 버전을 일치시킨 뒤 서버에 올려야 합니다. 이 상수는 향후 `manifest.json` 의 `requirements_hash` 와 함께 기록되어 파이프라인 실행 버전을 증명합니다.

## 3. 다운타임 제로 (Zero-Downtime) 지향

배치 스크립트는 24시간 실시간 API와는 결이 다르지만, 만약 크론(Cron) 등에 의해 매시 정각 구동되는 환경이라면 배포 도중 파이프라인 충돌이 발생할 수 있습니다. 

- **조치**: 코드 업데이트가 필요하면 현재 가동 중인 `python -m ragprep.prepare`의 프로세스 ID(PID) 종료를 대기한 뒤 코드를 Swap하는 방식을 채택합니다.
- 코드를 교체하고 난 뒤 중간에 죽은 `group_id` 폴더가 있더라도 재실행 시 스캐너가 자동 복구하므로 스토리지 롤백 시퀀스는 필요하지 않습니다.
