import json
import logging
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

from ragprep.core.models import RunContext, FileMeta

logger = logging.getLogger("ragprep.extract_xml")

def extract(meta: FileMeta, ctx: RunContext) -> bool:
    """
    XML 파일에서 태그(HTML/XML 구조)를 모두 제거하고 순수 텍스트(문자 및 숫자)만 추출합니다.
    """
    extracted_data = []
    total_chars = 0
    
    out_file = ctx.dirs['extracted'] / f"{meta.doc_id}.xml.json"
    
    paths_to_process = getattr(meta, 'paths', None) or [meta.path]
    
    for path in paths_to_process:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # lxml-xml 파서를 사용하여 XML 태그를 완전히 제거하고 텍스트만 추출
            soup = BeautifulSoup(content, 'xml')
            
            # 스크립트나 스타일 태그가 섞여있을 수 있으므로 제거 (SVG 등 대비)
            for tag in soup(["script", "style"]):
                tag.decompose()
                
            # 특별 처리: 성경 dtbook 포맷 (창세기 등) 등인지 확인
            is_dtbook = soup.find('dtbook') is not None
            
            if is_dtbook:
                book_title = soup.find('doctitle').get_text(strip=True) if soup.find('doctitle') else "Unknown Book"
                
                # level1 태그가 보통 한 '장(Chapter)'을 의미
                for level in soup.find_all('level1'):
                    chapter_heading = level.find('h1').get_text(strip=True) if level.find('h1') else "Chapter"
                    
                    # 문장(절) 단위 파싱
                    sentences = level.find_all('span', class_='sentence')
                    if not sentences:
                        # span 구분이 없으면 단락 통째로
                        sentences = level.find_all('p')
                        
                    for s in sentences:
                        verse_text = s.get_text(strip=True)
                        if verse_text:
                            extracted_data.append({
                                "blocks": [{
                                    "text": verse_text,
                                    "context": f"{book_title} {chapter_heading}"
                                }]
                            })
                            total_chars += len(verse_text)
            else:
                # 일반 XML 폴백 로직
                clean_text = soup.get_text(separator='\n\n', strip=True)
                if clean_text:
                    extracted_data.append({
                        "blocks": [{"text": clean_text}]
                    })
                    total_chars += len(clean_text)
                
        except Exception as e:
            logger.error(f"Failed to read or parse XML {path}: {e}")
            from ragprep.core.router import quarantine_error
            quarantine_error(meta, ctx, "XML_PARSE_FAIL", f"Error in {path}: {str(e)}")
            return False
            
    # XML 문서는 특히 성경의 아주 짧은 구절(장)인 경우 극단적으로 짧을 수 있으므로 예외 허용
    if total_chars < ctx.min_chars and total_chars < 10:
        logger.warning(f"XML text too short for {meta.doc_id} ({total_chars} chars)")
        from ragprep.core.router import quarantine_error
        quarantine_error(meta, ctx, "TOO_SHORT_TEXT", f"Total chars {total_chars} < 10")
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
            "engine": "beautifulsoup-xml",
            "engine_version": None,
            "extracted_at": datetime.now().isoformat()
        },
        "pages": extracted_data, # Use pages to hold blocks for normalize step
        "stats": {
            "page_count": 1,
            "total_chars": total_chars
        }
    }
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    return True
