import logging
from pathlib import Path
from ragprep.core.models import RunContext, ProcessingResult
from ragprep.core.scanner import get_file_meta
import json

logger = logging.getLogger("ragprep.router")

def is_already_processed(doc_id: str, ctx: RunContext) -> bool:
    if ctx.force:
        return False
    success_marker = ctx.dirs['prepared_docs'] / f"{doc_id}.success.json"
    return success_marker.exists()

def process_document(filepath: Path, ctx: RunContext) -> ProcessingResult:
    import time
    start_t = time.time()
    try:
        meta = get_file_meta(filepath, ctx.input_dir)
    except Exception as e:
        logger.error(f"Failed to get file meta for {filepath}: {e}")
        return ProcessingResult(
            doc_id="unknown",
            filename=filepath.name,
            type="unknown",
            sha256="unknown",
            status="FAILED",
            failed_reason="META_FAIL"
        )
        
    # 2. 멱등성 검사 (이미 처리된 성공 항목은 건너뜀)
    success_file = ctx.dirs['prepared_docs'] / f"{meta.doc_id}.success.json"
    if success_file.exists() and not ctx.force:
        logger.info(f"Skipping {meta.doc_id}, already successfully processed.")
        # Load from success file
        with open(success_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return ProcessingResult(**data)
            
    # 3. 라우팅 로직: 파일 타입(확장자)에 따라 각각의 처리 모듈로 분기
    try:
        if meta.extension == "pdf":
            res = process_pdf(meta, ctx)
        elif meta.extension == "jwpub":
            res = process_jwpub(meta, ctx)
        elif meta.extension == "xml":
            res = process_xml(meta, ctx)
        else:
            # 지원하지 않는 파일 형식은 Quarantine(격리) 폴더로 이관
            logger.warning(f"Unsupported file type: {meta.extension} for {meta.doc_id}")
            res = quarantine_error(meta, ctx, "UNSUPPORTED_TYPE", f"Unsupported extension: {meta.extension}")
            
        res.duration_ms = int((time.time() - start_t) * 1000)
        logger.info("Document processing finished", extra={"doc_id": res.doc_id, "group_id": meta.group_id, "event": "stage_end", "stage": "process_document", "duration_ms": res.duration_ms})
        return res
    except Exception as e:
        logger.exception(f"Unhandled error processing")
        return ProcessingResult(doc_id="unknown", filename=filepath.name, type="unknown", sha256="unknown", status="FAILED", failed_reason=str(e), duration_ms=int((time.time() - start_t) * 1000))

def process_pdf(meta, ctx: RunContext) -> ProcessingResult:
    """
    PDF 전용 파이프라인 수행 단계:
    추출(Extract) -> 정제(Normalize) -> 구조화(Structure) -> 청킹(Chunk) 순차 실행.
    어느 단계에서든 실패하면 즉시 실패 결과(FAILED)를 반환하며, 성공 시 상태 객체를 작성합니다.
    """
    from ragprep.core.extract_pdf import extract
    from ragprep.core.normalize import normalize
    from ragprep.core.structure import structure
    from ragprep.core.chunk import chunk
    from ragprep.core.models import FileMeta
    
    if not extract(meta, ctx):
        return ProcessingResult(doc_id=meta.doc_id, filename=meta.filename, type="pdf", sha256=meta.sha256, status="FAILED", failed_reason="EXTRACT_FAIL", total_chars=0, chunks=0)
        
    if not normalize(meta, ctx):
        return quarantine_error(meta, ctx, "NORMALIZE_FAIL", "Failed to normalize")
        
    if not structure(meta, ctx):
        return quarantine_error(meta, ctx, "STRUCTURE_FAIL", "Failed to structure")
        
    chunks_count = chunk(meta, ctx)
    if chunks_count <= 0:
        return quarantine_error(meta, ctx, "CHUNK_FAIL", "No chunks generated")
        
    # 성공 마커 마킹
    # 경로 계산
    doc_out = ctx.dirs['prepared_docs']
    chunk_out = ctx.dirs['prepared_chunks']
    if meta.group_id:
        doc_out = doc_out / meta.group_id
        chunk_out = chunk_out / meta.group_id
        
    res = ProcessingResult(
        doc_id=meta.doc_id, filename=meta.filename, type="pdf", sha256=meta.sha256, 
        status="SUCCESS", failed_reason=None, 
        outputs={
            "extracted": str(ctx.dirs['extracted'] / f"{meta.doc_id}.pages.json"),
            "normalized": str(ctx.dirs['normalized'] / f"{meta.doc_id}.normalized.json"),
            "document": str(doc_out / f"{meta.doc_id}.document.json"),
            "chunks": str(chunk_out / f"{meta.doc_id}.chunks.jsonl")
        },
        total_chars=0, chunks=chunks_count)
    return finalize_processing(meta, ctx, res)

def process_jwpub(meta, ctx: RunContext) -> ProcessingResult:
    from ragprep.core.extract_jwpub import extract
    from ragprep.core.normalize import normalize
    from ragprep.core.structure import structure
    from ragprep.core.chunk import chunk
    
    if not extract(meta, ctx):
        return ProcessingResult(doc_id=meta.doc_id, filename=meta.filename, type="jwpub", sha256=meta.sha256, status="FAILED", failed_reason="EXTRACT_FAIL")
        
    if not normalize(meta, ctx):
        return quarantine_error(meta, ctx, "NORMALIZE_FAIL", "Failed to normalize")
        
    if not structure(meta, ctx):
        return quarantine_error(meta, ctx, "STRUCTURE_FAIL", "Failed to structure")
        
    chunks_count = chunk(meta, ctx)
    if chunks_count <= 0:
        return quarantine_error(meta, ctx, "CHUNK_FAIL", "No chunks generated")
        
    doc_out = ctx.dirs['prepared_docs']
    chunk_out = ctx.dirs['prepared_chunks']
    if meta.group_id:
        doc_out = doc_out / meta.group_id
        chunk_out = chunk_out / meta.group_id
        
    outputs = {
        "extracted": str(ctx.dirs['extracted'] / f"{meta.doc_id}.jwpub.json"),
        "normalized": str(ctx.dirs['normalized'] / f"{meta.doc_id}.normalized.json"),
        "document": str(doc_out / f"{meta.doc_id}.document.json"),
        "chunks": str(chunk_out / f"{meta.doc_id}.chunks.jsonl")
    }
    res = ProcessingResult(doc_id=meta.doc_id, filename=meta.filename, type="jwpub", sha256=meta.sha256, status="SUCCESS", chunks=chunks_count, outputs=outputs)
    return finalize_processing(meta, ctx, res)

def process_xml(meta, ctx: RunContext) -> ProcessingResult:
    from ragprep.core.extract_xml import extract
    from ragprep.core.normalize import normalize
    from ragprep.core.structure import structure
    from ragprep.core.chunk import chunk
    
    if not extract(meta, ctx):
        return ProcessingResult(doc_id=meta.doc_id, filename=meta.filename, type="xml", sha256=meta.sha256, status="FAILED", failed_reason="EXTRACT_FAIL")
        
    if not normalize(meta, ctx):
        return quarantine_error(meta, ctx, "NORMALIZE_FAIL", "Failed to normalize")
        
    if not structure(meta, ctx):
        return quarantine_error(meta, ctx, "STRUCTURE_FAIL", "Failed to structure")
        
    chunks_count = chunk(meta, ctx)
    if chunks_count <= 0:
        return quarantine_error(meta, ctx, "CHUNK_FAIL", "No chunks generated")
        
    doc_out = ctx.dirs['prepared_docs']
    chunk_out = ctx.dirs['prepared_chunks']
    if meta.group_id:
        doc_out = doc_out / meta.group_id
        chunk_out = chunk_out / meta.group_id
        
    outputs = {
        "extracted": str(ctx.dirs['extracted'] / f"{meta.doc_id}.xml.json"),
        "normalized": str(ctx.dirs['normalized'] / f"{meta.doc_id}.normalized.json"),
        "document": str(doc_out / f"{meta.doc_id}.document.json"),
        "chunks": str(chunk_out / f"{meta.doc_id}.chunks.jsonl")
    }
    res = ProcessingResult(doc_id=meta.doc_id, filename=meta.filename, type="xml", sha256=meta.sha256, status="SUCCESS", chunks=chunks_count, outputs=outputs)
    return finalize_processing(meta, ctx, res)

def quarantine_unsupported(meta, ctx: RunContext) -> ProcessingResult:
    logger.warning(f"Unsupported file type: {meta.extension} for {meta.doc_id}")
    return quarantine_error(meta, ctx, "UNSUPPORTED_TYPE", f"Extension '{meta.extension}' is not supported")

def quarantine_error(meta, ctx: RunContext, step: str, reason: str, stack: str = None) -> ProcessingResult:
    import shutil
    from datetime import datetime
    
    q_dir = ctx.dirs['quarantine'] / meta.doc_id
    q_dir.mkdir(parents=True, exist_ok=True)
    
    src_path = Path(meta.path)
    if src_path.exists():
        dest = q_dir / meta.filename
        if str(src_path) != str(dest):
            shutil.copy2(src_path, dest)
            
    fail_data = {
        "doc_id": meta.doc_id,
        "filename": meta.filename,
        "sha256": meta.sha256,
        "type": meta.extension,
        "step": step,
        "reason": reason,
        "stack": stack,
        "created_at": datetime.now().isoformat()
    }
    
    with open(q_dir / "fail.json", "w", encoding="utf-8") as f:
        json.dump(fail_data, f, ensure_ascii=False, indent=2)
        
    return ProcessingResult(
        doc_id=meta.doc_id,
        filename=meta.filename,
        type=meta.extension,
        sha256=meta.sha256,
        status="FAILED",
        failed_reason=step
    )

def process_group(group_id: str, files: list[Path], ctx: RunContext) -> ProcessingResult:
    import time
    start_t = time.time()
    
    if not files:
        return ProcessingResult(doc_id=f"{group_id}-merged", filename=group_id, type="unknown", sha256="", status="FAILED", failed_reason="EMPTY_GROUP")
        
    first_meta = get_file_meta(files[0], ctx.input_dir)
    ext = first_meta.extension
    doc_id = f"{group_id}-merged"
    
    success_file = ctx.dirs['prepared_docs'] / f"{doc_id}.success.json"
    if success_file.exists() and not ctx.force:
        logger.info(f"Skipping group {group_id}, already successfully processed.")
        with open(success_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return ProcessingResult(**data)
            
    from ragprep.core.models import FileMeta
    merged_meta = FileMeta(
        path=first_meta.path,
        paths=[str(f.resolve()) for f in files],
        filename=f"{group_id}_merged.{ext}",
        extension=ext,
        sha256=first_meta.sha256,
        filesize=sum(f.stat().st_size for f in files),
        mtime=first_meta.mtime,
        doc_id=doc_id,
        group_id=group_id
    )
    
    try:
        if ext == "pdf":
            res = process_pdf(merged_meta, ctx)
        elif ext == "jwpub":
            res = process_jwpub(merged_meta, ctx)
        elif ext == "xml":
            res = process_xml(merged_meta, ctx)
        else:
            res = quarantine_error(merged_meta, ctx, "UNSUPPORTED_TYPE", f"Unsupported extension: {ext}")
            
        res.duration_ms = int((time.time() - start_t) * 1000)
        logger.info("Group processing finished", extra={"doc_id": res.doc_id, "group_id": group_id, "event": "stage_end", "stage": "process_group", "duration_ms": res.duration_ms})
        return res
        
    except Exception as e:
        logger.exception(f"Unhandled error processing group {group_id}")
        return quarantine_error(merged_meta, ctx, "UNHANDLED_ERROR", str(e))

def finalize_processing(meta, ctx: RunContext, res: ProcessingResult) -> ProcessingResult:
    if not getattr(ctx, 'quality_gate', True):
        # 품질 평가 미적용 시 기존 SUCCESS 마커만 작성
        with open(ctx.dirs['prepared_docs'] / f"{meta.doc_id}.success.json", 'w', encoding='utf-8') as f:
            f.write(res.model_dump_json(indent=2))
        return res
        
    from ragprep.core.quality import evaluate_quality
    from ragprep.core.models import QualityDecision
    import shutil
    
    metrics = evaluate_quality(meta, ctx, res.outputs)
    
    doc_path = Path(res.outputs.get("document", ""))
    chunk_path = Path(res.outputs.get("chunks", ""))
    
    if metrics.decision == QualityDecision.PASS:
        with open(ctx.dirs['prepared_docs'] / f"{meta.doc_id}.success.json", 'w', encoding='utf-8') as f:
            f.write(res.model_dump_json(indent=2))
            
        target_dir = doc_path.parent
        if target_dir.exists():
            with open(target_dir / f"{meta.doc_id}.quality.json", 'w', encoding='utf-8') as f:
                f.write(metrics.model_dump_json(indent=2))
                
    elif metrics.decision == QualityDecision.REVIEW:
        review_dir = ctx.dirs['review'] / meta.doc_id
        review_dir.mkdir(parents=True, exist_ok=True)
        
        if doc_path.exists():
            shutil.move(str(doc_path), review_dir / doc_path.name)
        if chunk_path.exists():
            shutil.move(str(chunk_path), review_dir / chunk_path.name)
            
        with open(review_dir / "quality.json", 'w', encoding='utf-8') as f:
            f.write(metrics.model_dump_json(indent=2))
            
        res.status = "REVIEW"
        res.failed_reason = " | ".join(metrics.reasons)
        
    else: # QUARANTINE
        q_dir = ctx.dirs['quarantine'] / meta.doc_id
        q_dir.mkdir(parents=True, exist_ok=True)
        
        if doc_path.exists():
            shutil.move(str(doc_path), q_dir / doc_path.name)
        if chunk_path.exists():
            shutil.move(str(chunk_path), q_dir / chunk_path.name)
            
        with open(q_dir / "quality.json", 'w', encoding='utf-8') as f:
            f.write(metrics.model_dump_json(indent=2))
            
        res.status = "QUARANTINE"
        res.failed_reason = " | ".join(metrics.reasons)
        
    return res
