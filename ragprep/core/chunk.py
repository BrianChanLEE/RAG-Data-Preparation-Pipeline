import json
import logging
from pathlib import Path
from ragprep.core.models import RunContext, DocumentSchema, ChunkSchema, ChunkMeta

logger = logging.getLogger("ragprep.chunk")

import re

def _split_text_generator(text: str, target_len: int, overlap_len: int):
    """
    Phase 2: 의미론적 지능형 청킹(Semantic Chunking)
    - 주어진 텍스트를 마침표(`.!?`)나 개행(`\n`) 기준으로 문장 단위로 분할합니다.
    - 목표 길이(target_len)에 도달할 때까지 문장들을 조합하며,
    - 메모리 효율성을 위해 리스트에 담아 반환하지 않고 제너레이터(`yield`) 패턴을 사용합니다.
    - 앞뒤 파편 간의 문맥 유실을 막기 위해 겹침(overlap_len) 로직도 문장 단위로 수행합니다.
    """
    sentence_pattern = re.compile(r'(?<=[.!?])\s+(?=[가-힣A-Z])|(?<=[.!?])\n+')
    sentences = sentence_pattern.split(text)
    
    current_sentences = []
    current_len = 0
    
    for s in sentences:
        s = s.strip()
        if not s:
            continue
            
        s_len = len(s)
        
        if current_len + s_len <= target_len:
            current_sentences.append(s)
            current_len += s_len + 1
        else:
            if current_sentences:
                yield " ".join(current_sentences)
                
                overlap_sentences = []
                overlap_curr_len = 0
                for os_sent in reversed(current_sentences):
                    if overlap_curr_len + len(os_sent) <= overlap_len:
                        overlap_sentences.insert(0, os_sent)
                        overlap_curr_len += len(os_sent) + 1
                    else:
                        break
                        
                current_sentences = overlap_sentences + [s]
                current_len = overlap_curr_len + s_len + 1
            else:
                yield s
                current_sentences = []
                current_len = 0
                
    if current_sentences:
        yield " ".join(current_sentences)

def get_grouped_chunk_path(base_dir: Path, filename: str, doc_id: str, group_id: str = None) -> Path:
    """
    파일명 또는 group_id를 분석하여 적절한 하위 폴더 경로를 생성합니다.
    """
    if group_id:
        return base_dir / group_id / f"{doc_id}.chunks.jsonl"
        
    import re
    # Rule 1: g_KO 시리즈 (연도월 기반)
    date_series_match = re.search(r'^([a-zA-Z_]+)_(\d{4}\d{2})_', filename)
    if date_series_match:
        prefix = date_series_match.group(1).upper()
        sub_folder = f"{date_series_match.group(1)}_{date_series_match.group(2)}"
        return base_dir / prefix / sub_folder / f"{doc_id}.chunks.jsonl"
        
    # Rule 2: 문자+숫자 결합 시리즈
    num_series_match = re.search(r'^([a-zA-Z_가-힣]+)\d+', filename)
    if num_series_match:
        series_name = num_series_match.group(1)
        return base_dir / series_name / f"{doc_id}.chunks.jsonl"
        
    # Rule 3: 예외
    return base_dir / "etc" / f"{doc_id}.chunks.jsonl"

def chunk(meta, ctx: RunContext) -> int:
    """
    파이프라인의 핵심: 최종 RAG 벡터 DB 인덱싱을 위한 청크(Chunk) 생성 단계.
    구조화가 끝난 문서의 섹션별 본문 데이터를 가져와 의미론적 길이 목표치(기본 ~1000자)에 맞게 쪼갭니다.
    최종 결과물은 스트리밍 친화적인 JSONL 형식으로 `data/prepared/chunks/{그룹}/{시리즈}/` 에 라인 단위로 바로 쓰입니다.
    """
    in_dir = ctx.dirs['prepared_docs']
    if getattr(meta, 'group_id', None):
        in_dir = in_dir / meta.group_id
    
    in_file = in_dir / f"{meta.doc_id}.document.json"
    if not in_file.exists():
        logger.error(f"Document file not found: {in_file}")
        return 0
        
    with open(in_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    doc = DocumentSchema(**data)
    
    from ragprep.core.dedupe import ChunkDeduplicator
    from ragprep.core.models import ChunkLineage, SCHEMA_VERSION
    
    target_len = 1000
    overlap_len = int(target_len * 0.15)
    
    revision = data.get("revision", 1)
    deduplicator = ChunkDeduplicator() if getattr(ctx, 'dedupe', True) else None
    
    doc_id = meta.doc_id
    source_paths = getattr(meta, 'paths', None) or [meta.path]
    
    lineage = ChunkLineage(
        doc_id=doc_id,
        group_id=getattr(meta, 'group_id', None),
        revision=revision,
        source_paths=source_paths,
        stage_versions={"schema": SCHEMA_VERSION, "chunker": "1.0.0"}
    )
    
    out_file = get_grouped_chunk_path(ctx.dirs['prepared_chunks'], meta.filename, meta.doc_id, getattr(meta, 'group_id', None))
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    chunks_generated = 0
    
    with open(out_file, 'w', encoding='utf-8') as f:
        for s in doc.sections:
            c_idx = 0
            for segment in _split_text_generator(s.content, target_len, overlap_len):
                if doc.type != "xml" and len(segment.strip()) < 50:
                    continue
                
                if deduplicator:
                    scope = meta.group_id if getattr(ctx, 'dedupe_scope', 'doc') == 'group' and getattr(meta, 'group_id', None) else doc.doc_id
                    if deduplicator.is_duplicate(scope, segment):
                        logger.debug(f"Skipping duplicate chunk for doc_id {doc.doc_id}: {segment[:50]}...")
                        continue
                    
                chunk_id_suffix = f"s{s.section_id.replace('s', '')}#c{c_idx+1}"
                chunk_id = f"{doc.doc_id}#{chunk_id_suffix}"
                
                c = ChunkSchema(
                    chunk_id=chunk_id,
                    doc_id=doc.doc_id,
                    type=doc.type,
                    title=doc.title,
                    section=s.heading,
                    text=segment.strip(),
                    metadata=ChunkMeta(
                        source_path=meta.path,
                        sha256=meta.sha256
                    ),
                    lineage=lineage
                )
                
                f.write(c.model_dump_json() + "\n")
                chunks_generated += 1
                c_idx += 1
                
    return chunks_generated
