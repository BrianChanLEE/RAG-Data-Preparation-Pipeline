import json
import logging
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF

from ragprep.core.models import RunContext

logger = logging.getLogger("ragprep.extract_pdf")

def extract(meta, ctx: RunContext) -> bool:
    """
    Extracts text from PDF page by page.
    Returns True if successful, False if extraction failed or text is too short.
    """
    out_file = ctx.dirs['extracted'] / f"{meta.doc_id}.pages.json"
    
    paths_to_process = getattr(meta, 'paths', None) or [meta.path]
    pages_data = []
    total_chars = 0
    total_lines = 0
    global_page_num = 1
    
    for path in paths_to_process:
        try:
            doc = fitz.open(path)
        except Exception as e:
            logger.error(f"Failed to open PDF {path}: {e}")
            from ragprep.core.router import quarantine_error
            quarantine_error(meta, ctx, "EXTRACT_FAIL", f"PyMuPDF failed to open {path}: {e}")
            return False
            
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract as dictionary to get bounding boxes and font info
                page_dict = page.get_text("dict")
                blocks = []
                
                page_char_count = 0
                page_line_count = 0
                
                for b in page_dict.get("blocks", []):
                    if b.get("type") != 0: # Not text
                        continue
                    
                    block_text = ""
                    primary_font = None
                    primary_size = 0.0
                    
                    for line in b.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            text = span.get("text", "")
                            line_text += text
                            
                            # Infer dominant font by taking the largest size in this block
                            size = span.get("size", 0)
                            if size > primary_size:
                                primary_size = size
                                primary_font = span.get("font", "")
                                
                        block_text += line_text + "\n"
                        page_line_count += 1
                    
                    block_text = block_text.strip()
                    if block_text:
                        page_char_count += len(block_text)
                        blocks.append({
                            "bbox": b.get("bbox"),  # [x0, y0, x1, y1]
                            "text": block_text,
                            "font": primary_font,
                            "size": round(primary_size, 2)
                        })
                        
                total_chars += page_char_count
                total_lines += page_line_count
                
                pages_data.append({
                    "page": global_page_num,
                    "width": page_dict.get("width"),
                    "height": page_dict.get("height"),
                    "blocks": blocks,
                    "char_count": page_char_count,
                    "line_count": page_line_count
                })
                global_page_num += 1
        finally:
            doc.close()
        
    if total_chars < ctx.min_chars:
        logger.warning(f"PDF text too short for {meta.doc_id} ({total_chars} chars)")
        from ragprep.core.router import quarantine_error
        quarantine_error(meta, ctx, "TOO_SHORT_TEXT", f"Total chars {total_chars} < {ctx.min_chars}. Possible scanned PDF.")
        return False
        
    output_data = {
        "doc_id": meta.doc_id,
        "source": {
            "path": meta.path,
            "sha256": meta.sha256,
            "filename": meta.filename,
            "filesize": meta.filesize,
            "mtime": meta.mtime
        },
        "extract": {
            "engine": "pymupdf",
            "engine_version": fitz.VersionBind,
            "extracted_at": datetime.now().isoformat()
        },
        "pages": pages_data
    }
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    return True
