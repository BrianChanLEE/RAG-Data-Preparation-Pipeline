import json
import logging
import re
from pathlib import Path
from ragprep.core.models import RunContext, NormalizedSchema, SectionInfo

logger = logging.getLogger("ragprep.normalize")

def normalize(meta, ctx: RunContext) -> bool:
    """
    Normalizes extracted JSON into the common normalization schema.
    """
    if meta.extension == "pdf":
        return _normalize_pdf(meta, ctx)
    elif meta.extension == "jwpub":
        return _normalize_jwpub(meta, ctx)
    elif meta.extension == "xml":
        return _normalize_xml(meta, ctx)
    return False

def _clean_common(text: str, ctx: RunContext = None) -> str:
    """
    모든 문서 타입에 공통으로 적용되는 텍스트 정제(Normalization) 로직.
    - 눈에 보이지 않는 제어문자 및 특수 기호를 제거
    - 불필요하게 반복되는 연속된 공백이나 줄바꿈을 단일 공백/줄바꿈으로 압축
    - PII 마스킹 처리 (선택)
    """
    # 1) 제어문자 제거, 공백 정리, 연속 줄바꿈 정리
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    
    if ctx and getattr(ctx, "pii_mask", False):
        from ragprep.core.pii import mask_pii
        text = mask_pii(text)
        
    return text

def _normalize_pdf(meta, ctx: RunContext) -> bool:
    """
    PDF 추출 결과물(`pages.json`)을 읽어들여 정제(Normalization)를 수행합니다.
    - Phase 2 도입: 텍스트의 반복 등장 여부가 아닌, Y축 물리적 좌표(BBox)를 기준으로 머리말(Header)과 꼬리말(Footer)을 안전하게 잘라냅니다.
    - 단어 끝에 걸려 끊어진 하이픈(-) 하드 랩핑을 원래 한 단어로 복원합니다.
    - 이후 구조화 단계에서 폰트 크기를 활용하기 위해, 정제된 블록(cleaned_blocks) 데이터를 통계 객체에 같이 넘겨 보존합니다.
    """
    extracted_file = ctx.dirs['extracted'] / f"{meta.doc_id}.pages.json"
    if not extracted_file.exists():
        logger.error(f"Extracted file not found: {extracted_file}")
        return False
        
    with open(extracted_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    pages = data.get("pages", [])
    
    # 특수 페이지 번호(예: Page 3, - 3 -) 패턴
    page_num_pattern = re.compile(r'^(page\s*\d+|-\s*\d+\s*-|\d+\s*/\s*\d+|페이지\s*\d+)$', re.IGNORECASE)
    
    sections = []
    current_content = []
    
    # In Phase 2, we have blocks with bboxes: [x0, y0, x1, y1]
    # We define header/footer margins as top/bottom 7% of page height
    MARGIN_RATIO = 0.07
    
    for p in pages:
        page_height = p.get("height", 842.0) # Default A4 height fallback
        header_y_threshold = page_height * MARGIN_RATIO
        footer_y_threshold = page_height * (1.0 - MARGIN_RATIO)
        
        blocks = p.get("blocks", [])
        
        # Sort blocks by Y coordinate (top to bottom) to ensure natural reading order
        blocks.sort(key=lambda b: b.get("bbox", [0,0,0,0])[1])
        
        cleaned_blocks = []
        for b in blocks:
            bbox = b.get("bbox", [0, 0, 0, 0])
            y0, y1 = bbox[1], bbox[3]
            text = b.get("text", "").strip()
            
            if not text:
                continue
                
            # Header filter
            if y1 < header_y_threshold:
                continue
                
            # Footer filter
            if y0 > footer_y_threshold:
                continue
                
            if page_num_pattern.match(text):
                continue
                
            # Here we preserve the original dict for structure.py to use
            # But we also build a combined text for the fallback logic
            cleaned_blocks.append({
                "text": text,
                "font": b.get("font"),
                "size": b.get("size"),
                "bbox": b.get("bbox")
            })
            
            # Text aggregation for simple structure
            lines = text.split('\n')
            for line in lines:
                if line.strip():
                    current_content.append(line.strip())
                    
    # 하이픈 줄바꿈 복원
    page_text = "\n".join(current_content)
    page_text = re.sub(r'([a-zA-Z가-힣])-\n([a-zA-Z가-힣])', r'\1\2', page_text)
    page_text = _clean_common(page_text, ctx)
    
    if page_text:
        sections.append(SectionInfo(
            section_id="s1",
            heading=None,
            content=page_text
        ))
        
    # We pass the cleaned blocks in the stats so structure.py can use them for Phase 2 styling logic
    norm = NormalizedSchema(
        doc_id=meta.doc_id,
        title_guess=meta.filename,
        type="pdf",
        sections=sections,  # Simple text form
        stats={
            "char_count": len(page_text),
            "cleaned_blocks": [b for p in pages for b in p.get("blocks", [])] # Pass raw blocks down
        }
    )
    
    # Overwrite the blocks with cleaned blocks for Phase 2 structure
    # Actually, we need to pass the cleaned ones:
    all_cleaned_blocks = []
    for p in pages:
        page_height = p.get("height", 842.0)
        h_y = page_height * MARGIN_RATIO
        f_y = page_height * (1.0 - MARGIN_RATIO)
        for b in p.get("blocks", []):
            y0, y1 = b.get("bbox", [0,0,0,0])[1], b.get("bbox", [0,0,0,0])[3]
            txt = b.get("text", "").strip()
            if txt and y1 >= h_y and y0 <= f_y and not page_num_pattern.match(txt):
                all_cleaned_blocks.append(b)
                
    norm.stats["cleaned_blocks"] = all_cleaned_blocks
    
    out_file = ctx.dirs['normalized'] / f"{meta.doc_id}.normalized.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(norm.model_dump_json(indent=2))
        
    return True

def _normalize_jwpub(meta, ctx: RunContext) -> bool:
    extracted_file = ctx.dirs['extracted'] / f"{meta.doc_id}.jwpub.json"
    if not extracted_file.exists():
        logger.error(f"Extracted file not found: {extracted_file}")
        return False
        
    with open(extracted_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    sections_raw = data.get("sections", [])
    sections = []
    
    for s in sections_raw:
        content = _clean_common(s.get("content", ""), ctx)
        if content:
            sections.append(SectionInfo(
                section_id=s.get("section_id", ""),
                heading=s.get("heading"),
                content=content
            ))
            
    norm = NormalizedSchema(
        doc_id=meta.doc_id,
        title_guess=meta.filename,
        type="jwpub",
        sections=sections,
        stats={"section_count": len(sections)}
    )
    
    out_file = ctx.dirs['normalized'] / f"{meta.doc_id}.normalized.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(norm.model_dump_json(indent=2))
        
    return True

def _normalize_xml(meta, ctx: RunContext) -> bool:
    extracted_file = ctx.dirs['extracted'] / f"{meta.doc_id}.xml.json"
    if not extracted_file.exists():
        logger.error(f"Extracted file not found: {extracted_file}")
        return False
        
    with open(extracted_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    pages = data.get("pages", [])
    sections = []
    
    for i, p in enumerate(pages):
        blocks = p.get("blocks", [])
        for b in blocks:
            text = b.get("text", "")
            context = b.get("context", None)
            content = _clean_common(text, ctx)
            if content:
                sections.append(SectionInfo(
                    section_id=f"s{len(sections)+1}",
                    heading=context,
                    content=content
                ))
                
    norm = NormalizedSchema(
        doc_id=meta.doc_id,
        title_guess=meta.filename,
        type="xml",
        sections=sections,
        stats={"section_count": len(sections)}
    )
    
    out_file = ctx.dirs['normalized'] / f"{meta.doc_id}.normalized.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(norm.model_dump_json(indent=2))
        
    return True
