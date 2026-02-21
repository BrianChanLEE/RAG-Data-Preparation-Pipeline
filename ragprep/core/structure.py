import json
import logging
import re
from pathlib import Path

from ragprep.core.models import RunContext, NormalizedSchema, DocumentSchema, DocumentSection

logger = logging.getLogger("ragprep.structure")

def structure(meta, ctx: RunContext) -> bool:
    """
    정제된 텍스트 데이터(`normalized.json`)를 읽어, 문서의 목차나 계층 구조(Sections)를 추론합니다.
    - PDF: 추출된 텍스트 블록들의 폰트 크기를 통계적으로 분석합니다.
           본문 기본 크기보다 설정값 이상으로 큰 폰트를 제목(Heading)으로 식별하여 문서를 분할합니다.
    - JWPUB: 추출 과정에서 이미 구성된 HTML 클래스나 구조에 따라 생성된 섹션 정보를 그대로 유지합니다.
    """
    in_file = ctx.dirs['normalized'] / f"{meta.doc_id}.normalized.json"
    if not in_file.exists():
        logger.error(f"Normalized file not found: {in_file}")
        return False
        
    with open(in_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    norm = NormalizedSchema(**data)
    
    sections = []
    
    if norm.type in ("jwpub", "xml"):
        # JWPUB and XML are already sectioned mostly correctly
        for i, s in enumerate(norm.sections):
            sections.append(DocumentSection(
                section_id=s.section_id,
                heading=s.heading,
                order=i+1,
                content=s.content
            ))
    elif norm.type == "pdf":
        # Phase 2: PDF structural inference using font size and positioning
        blocks = norm.stats.get("cleaned_blocks", [])
        if not blocks:
            # Fallback to pure regex if block data is missing
            if not norm.sections:
                return False
                
            full_text = norm.sections[0].content
            lines = full_text.split('\n')
            
            sections.append(DocumentSection(
                section_id="s1",
                heading=None,
                order=1,
                content=full_text,
                page_start=1,
                page_end=1
            ))
        else:
            # Calculate standard body text size (most common size)
            from collections import Counter
            sizes = [b.get("size", 10.0) for b in blocks if b.get("text", "").strip()]
            if not sizes:
                return False
                
            size_counts = Counter(sizes)
            body_size = size_counts.most_common(1)[0][0]
            
            # Group blocks into sections
            current_heading = None
            current_content = []
            section_idx = 1
            
            for b in blocks:
                text = b.get("text", "").strip()
                if not text:
                    continue
                    
                font_size = b.get("size", body_size)
                
                # If font size is noticeably larger than body text (e.g. > 1pt larger), treat as heading
                if font_size > body_size + 0.5:
                    if current_content:
                        sections.append(DocumentSection(
                            section_id=f"s{section_idx}",
                            heading=current_heading,
                            order=section_idx,
                            content="\n\n".join(current_content).strip()
                        ))
                        section_idx += 1
                        current_content = []
                    current_heading = text
                else:
                    current_content.append(text)
                    
            if current_content or current_heading:
                sections.append(DocumentSection(
                    section_id=f"s{section_idx}",
                    heading=current_heading,
                    order=section_idx,
                    content="\n\n".join(current_content).strip()
                ))
            
    out_dir = ctx.dirs['prepared_docs']
    if getattr(meta, 'group_id', None):
        out_dir = out_dir / meta.group_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_file = out_dir / f"{meta.doc_id}.document.json"
    
    import hashlib
    import shutil
    
    combined_content = "".join([s.content for s in norm.sections])
    norm_sha256 = hashlib.sha256(combined_content.encode('utf-8')).hexdigest()
    
    revision = 1
    if out_file.exists():
        try:
            with open(out_file, 'r', encoding='utf-8') as pf:
                prev_doc = json.load(pf)
                prev_rev = prev_doc.get("revision", 1)
                prev_hash = prev_doc.get("normalized_sha256")
                
            if prev_hash == norm_sha256:
                revision = prev_rev
            else:
                revision = prev_rev + 1
                rev_dir = out_dir / "revisions" / str(prev_rev)
                rev_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(out_file), str(rev_dir / f"{meta.doc_id}.document.json"))
        except Exception as e:
            logger.warning(f"Failed to read previous document {meta.doc_id} to determine revision: {e}")
            
    doc = DocumentSchema(
        doc_id=norm.doc_id,
        type=norm.type,
        revision=revision,
        normalized_sha256=norm_sha256,
        title=norm.title_guess,
        source={"filename": meta.filename},
        sections=sections
    )
    
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(doc.model_dump_json(indent=2))
        
    return True
