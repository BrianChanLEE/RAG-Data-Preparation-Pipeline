import json
import logging
import re
from pathlib import Path
from typing import Dict, Any

from ragprep.core.models import RunContext, QualityMetrics, QualityDecision, FileMeta

logger = logging.getLogger("ragprep.quality")

def evaluate_quality(meta: FileMeta, ctx: RunContext, outputs: Dict[str, str]) -> QualityMetrics:
    """
    품질 스코어를 계산하고 리뷰, 격리, 통과 여부를 결정합니다.
    """
    metrics = QualityMetrics(
        doc_id=meta.doc_id,
        group_id=meta.group_id,
        source_type=meta.extension
    )
    
    reasons = []
    
    # 추출/정제/청크 파일을 읽어 품질을 평가합니다.
    doc_file = Path(outputs.get("document", ""))
    chunk_file = Path(outputs.get("chunks", ""))
    
    if not doc_file.exists() or not chunk_file.exists():
        metrics.decision = QualityDecision.QUARANTINE
        metrics.reasons.append("Missing required output files")
        return metrics

    # 1. 계산 - Document 분석
    total_chars = 0
    valid_chars = 0
    section_count = 0
    with open(doc_file, 'r', encoding='utf-8') as f:
        doc_data = json.load(f)
        sections = doc_data.get("sections", [])
        section_count = len(sections)
        for s in sections:
            content = s.get("content", "")
            total_chars += len(content)
            # 영어, 한글, 숫자, 일반 문장 부호 등 일반적인 텍스트 개수 파악
            valid_chars += len(re.findall(r'[가-힣a-zA-Z0-9\s.,!?\'"()-]', content))

    metrics.total_chars = total_chars
    metrics.valid_chars = valid_chars
    
    if total_chars > 0:
        invalid_ratio = (total_chars - valid_chars) / total_chars
        metrics.replacement_char_ratio = invalid_ratio
        if invalid_ratio > 0.3:
            reasons.append(f"High replacement char ratio: {invalid_ratio:.2f}")
            
    # XML/JWPUB은 기본 섹셔닝이 있지만 PDF는 추론이므로 섹션 검출률 확인
    if meta.extension == "pdf" and section_count <= 1 and total_chars > 5000:
        metrics.section_detect_rate = 0.0
        reasons.append("Low section detect rate (only 1 section for large PDF)")
    else:
        metrics.section_detect_rate = 1.0
        
    # 2. 계산 - Chunk 분석
    chunk_count = 0
    short_chunks = 0
    with open(chunk_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            chunk_count += 1
            chunk_data = json.loads(line)
            text = chunk_data.get("text", "")
            if len(text) < 100:
                short_chunks += 1
                
    metrics.chunk_count = chunk_count
    if chunk_count > 0:
        metrics.short_chunk_ratio = short_chunks / chunk_count
        if metrics.short_chunk_ratio > 0.5:
            reasons.append(f"Too many short chunks: {metrics.short_chunk_ratio:.2f}")
            
    # 3. 점수 계산 (단순 선형 결합)
    score = 100.0
    score -= (metrics.replacement_char_ratio * 50)
    if metrics.section_detect_rate == 0.0:
        score -= 20
    score -= (metrics.short_chunk_ratio * 30)
    
    metrics.quality_score = max(0.0, min(100.0, score))
    
    # 4. 결정 트리 (Decision Tree)
    if metrics.replacement_char_ratio > 0.4 or metrics.total_chars < ctx.min_chars:
        # 텍스트가 너무 깨졌거나 최소 글자수에 미달 (Min chars는 XML 예외 제외 여기서 엄격적용)
        # XML 예외 처리는 이미 이전에 통과했으므로 여기서는 텍스트 자체가 깨진 경우만 격리
        if metrics.replacement_char_ratio > 0.4:
            metrics.decision = QualityDecision.QUARANTINE
            reasons.append("Critical quality failure: Too much broken text")
    elif metrics.quality_score < 60.0 or len(reasons) > 0:
        metrics.decision = QualityDecision.REVIEW
        
    metrics.reasons = reasons
    return metrics
