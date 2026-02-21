import argparse
import logging
import os
import sys
import datetime
from pathlib import Path

from ragprep.core.io import init_directories
from ragprep.core.scanner import scan_files
from ragprep.core.router import process_document
from ragprep.core.report import generate_report
from ragprep.core.models import RunContext

def parse_args():
    """
    명령줄 인자를 파싱하여 RAG 파이프라인 실행에 필요한 설정을 가져옵니다.
    """
    parser = argparse.ArgumentParser(description="RAG Data Preparation Pipeline")
    parser.add_argument("--input", type=str, default="data/raw", help="원시 데이터 파일이 있는 디렉토리")
    parser.add_argument("--out", type=str, default="data", help="생성된 결과물이 저장될 최상위 디렉토리")
    parser.add_argument("--force", action="store_true", help="이전 처리 결과를 무시하고 무조건 덮어쓰기 (재실행)")
    parser.add_argument("--concurrency", type=int, default=2, help="병렬 처리에 사용할 최대 워커(프로세스) 수")
    parser.add_argument("--retry-quarantine", action="store_true", help="격리된(Quarantine) 폴더의 실패 항목들을 재시도 대상에 포함")
    parser.add_argument("--min-chars", type=int, default=300, help="정상 문서로 취급할 최소 추출 문자 수")
    parser.add_argument("--merge-group", type=str, default="false", help="하위 폴더(group_id) 단위로 단일 문서 병합 여부 (true/false)")
    parser.add_argument("--quality-gate", type=str, default="true", help="품질 게이트 평가 수행 여부 (true/false)")
    parser.add_argument("--dedupe", type=str, default="true", help="청크 내 Near-Duplicate 중복 제거 수행 여부 (true/false)")
    parser.add_argument("--dedupe-scope", type=str, default="doc", choices=["doc", "group"], help="중복 제거 스코프 (기본: doc)")
    parser.add_argument("--pii-mask", action="store_true", help="정규식을 이용해 개인정보(PII) 마스킹 수행")
    parser.add_argument("--executor", type=str, default="process", choices=["process", "thread"], help="병렬 처리 방식 (process/thread)")
    parser.add_argument("--max-retries", type=int, default=1, help="실패 시 최대 재시도 횟수")
    parser.add_argument("--retry-backoff-ms", type=int, default=2000, help="재시도 간 백오프 대기 시간 (밀리초)")
    return parser.parse_args()

def setup_logging(ctx: RunContext):
    from ragprep.core.logging import setup_observability
    return setup_observability(ctx.run_id, ctx.dirs['logs'])

def main():
    args = parse_args()
    input_dir = Path(args.input).resolve()
    base_out_dir = Path(args.out).resolve()
    
    import uuid
    run_id = str(uuid.uuid4())[:8]
    
    dirs = init_directories(base_out_dir)
    
    ctx = RunContext(
        run_id=run_id,
        input_dir=input_dir,
        out_dir=base_out_dir,
        dirs=dirs,
        force=args.force,
        concurrency=args.concurrency,
        retry_quarantine=args.retry_quarantine,
        merge_group=(args.merge_group.lower() == 'true'),
        quality_gate=(args.quality_gate.lower() == 'true'),
        dedupe=(args.dedupe.lower() == 'true'),
        dedupe_scope=args.dedupe_scope,
        pii_mask=args.pii_mask,
        executor_type=args.executor,
        max_retries=args.max_retries,
        retry_backoff_ms=args.retry_backoff_ms,
        min_chars=args.min_chars
    )
    
    logger = setup_logging(ctx)
    logger.info("Starting RAG Prep Pipeline", extra={"cli_args": vars(args)})
    
    try:
        files = scan_files(ctx)
        logger.info(f"Found {len(files)} files to process in {input_dir}")
        
        from ragprep.core.executor import get_executor
        executor = get_executor(ctx.executor_type)
        
        results = []
        if ctx.merge_group:
            from ragprep.core.scanner import get_file_meta
            from ragprep.core.router import process_group
            groups = {}
            for fp in files:
                meta = get_file_meta(fp, ctx.input_dir)
                gid = meta.group_id or "ungrouped"
                if gid not in groups:
                    groups[gid] = []
                groups[gid].append(fp)
                
            for gid in groups:
                groups[gid].sort(key=lambda x: x.name)
                
            items = [(gid, fps) for gid, fps in groups.items()]
            results = executor.execute(items, process_group, ctx)
        else:
            results = executor.execute(files, process_document, ctx)
            
        end_time = datetime.datetime.now()
        # 파이프라인 처리 통계를 담은 최종 리포트 생성
        report_file = generate_report(ctx, results)
    
        # 6. Manifest 생성
        import platform
        from ragprep.core.models import RunManifest, RunConfig, HostInfo, RunStats
        
        stats = RunStats(
            processed=len(results),
            passed=sum(1 for r in results if r.status == "SUCCESS"),
            review=sum(1 for r in results if r.status == "REVIEW"),
            quarantined=sum(1 for r in results if r.status == "QUARANTINE"),
            failed=sum(1 for r in results if r.status == "FAILED")
        )
        host = HostInfo(
            os=platform.system(),
            python_version=platform.python_version(),
            cpu_count=os.cpu_count() or 1
        )
        config = RunConfig(
            concurrency=ctx.concurrency,
            merge_group=ctx.merge_group,
            quality_gate=ctx.quality_gate,
            dedupe=ctx.dedupe,
            dedupe_scope=ctx.dedupe_scope,
            pii_mask=ctx.pii_mask,
            executor_type=ctx.executor_type,
            max_retries=ctx.max_retries,
            retry_backoff_ms=ctx.retry_backoff_ms,
            min_chars=ctx.min_chars,
            retry_quarantine=ctx.retry_quarantine
        )
        manifest = RunManifest(
            run_id=ctx.run_id,
            started_at=ctx.start_time.isoformat(),
            finished_at=end_time.isoformat(),
            config=config,
            host=host,
            stats=stats
        )
        
        runs_dir = ctx.out_dir / "runs" / ctx.run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        with open(runs_dir / "manifest.json", "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))
            
        import pandas as pd
        import json
        
        durations = [r.duration_ms for r in results if getattr(r, 'duration_ms', 0) > 0]
        if durations:
            s = pd.Series(durations)
            p95 = int(s.quantile(0.95))
            mean_dur = int(s.mean())
        else:
            p95 = 0
            mean_dur = 0
            
        metrics = {
            "run_id": ctx.run_id,
            "total_duration_sec": (end_time - ctx.start_time).total_seconds(),
            "docs_processed": stats.processed,
            "quarantine_rate": stats.quarantined / max(stats.processed, 1),
            "duration_p95_ms": p95,
            "duration_mean_ms": mean_dur
        }
        
        with open(runs_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
            
        logger.info(f"Manifest generated: {runs_dir / 'manifest.json'}")

        passed_count = stats.passed + stats.review # Review is also "processed" effectively, but let's count only successes for the green log
        total_expected = len(groups) if ctx.merge_group else len(files)

        if stats.failed == 0 and stats.quarantined == 0 and stats.review == 0:
            print(f"\n\033[92m\033[1m✅ 모든 파일의 처리가 성공적으로 완료되었습니다.\033[0m")
            logger.info("Pipeline completed successfully")
        else:
            print(f"\n\033[91m\033[1m==================================================")
            print(f"⚠️ 경고: {stats.failed + stats.quarantined + stats.review}개의 문서 처리에 문제가 발생했습니다!")
            print(f"==================================================\033[0m")
            for r in results:
                if r.status in ("FAILED", "QUARANTINE", "REVIEW"):
                    print(f"\033[91m  - [{r.status}] {r.filename}: {r.failed_reason}\033[0m")
            print("\n상세한 실패 사유와 원본 파일은 `data/quarantine/` 또는 `data/review/` 격리 폴더 및 리포트를 확인해 주세요.")
            logger.warning(f"Pipeline completed with {stats.failed + stats.quarantined + stats.review} issues out of {len(results)} outputs.")
    except Exception as e:
        logger.exception("Pipeline failed abnormally", extra={"error": str(e)})
        sys.exit(1)

if __name__ == "__main__":
    main()
