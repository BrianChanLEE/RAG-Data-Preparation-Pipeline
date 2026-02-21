import json
import logging
from pathlib import Path
from typing import List
from ragprep.core.models import RunContext, ProcessingResult

logger = logging.getLogger("ragprep.report")

def generate_report(ctx: RunContext, results: List[ProcessingResult]):
    """
    모든 문서의 파이프라인 처리가 끝난 후, 전체 통계 요약 리포트를 생성합니다.
    - 처리 건수(성공, 스킵, 실패별) 집계
    - 에러 발생 건에 대한 사유별 통계 추출
    - 최종 산출물을 JSON과 CSV 포맷 두 가지로 저장하여 대시보드나 후속 프로세스가 
      쉽게 파이프라인 가동 결과를 분석할 수 있게 돕습니다.
    """
    import pandas as pd
    from datetime import datetime
    
    end_time = datetime.now()
    
    fail_reasons = {}
    for r in results:
        if r.status == "FAILED":
            reason = r.failed_reason or "UNKNOWN_ERROR"
            fail_reasons[reason] = fail_reasons.get(reason, 0) + 1
            
    report = {
        "run_id": ctx.run_id,
        "started_at": ctx.start_time.isoformat(),
        "ended_at": end_time.isoformat(),
        "input_count": len(results),
        "success_count": sum(1 for r in results if r.status == "SUCCESS"),
        "skipped_count": sum(1 for r in results if r.status == "SKIPPED"),
        "failed_count": sum(1 for r in results if r.status == "FAILED"),
        "fail_reasons": fail_reasons,
        "docs": [r.model_dump() for r in results]
    }
    
    json_path = ctx.dirs['prepared_reports'] / f"run-summary-{ctx.run_id}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        
    df = pd.DataFrame(report['docs'])
    if not df.empty:
        # flatten outputs
        def flatten_outputs(row):
            outs = row.get('outputs', {})
            for k, v in outs.items():
                row[f'out_{k}'] = v
            return row
            
        df = df.apply(flatten_outputs, axis=1)
        if 'outputs' in df.columns:
            df = df.drop(columns=['outputs'])
            
    csv_path = ctx.dirs['prepared_reports'] / f"run-summary-{ctx.run_id}.csv"
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    logger.info(f"Report generated: {json_path}")
