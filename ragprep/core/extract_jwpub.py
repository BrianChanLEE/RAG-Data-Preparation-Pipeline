import json
import logging
import sqlite3
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

from ragprep.core.models import RunContext, FileMeta

logger = logging.getLogger("ragprep.extract_jwpub")

def extract(meta: FileMeta, ctx: RunContext) -> bool:
    """
    JWPUB 형식(실제로는 ZIP 확장자 호환)의 아카이브를 풀어 HTML 콘텐츠를 추출합니다.
    - `contents/*.html` 파일들을 순회하며 BeautifulSoup을 이용해 텍스트를 파싱합니다.
    - JWPUB 특성상 본문에 있는 불필요한 태그(스크립트, 스타일)는 BeautifulSoup 수준에서 1차 제거합니다.
    - 추출량이 너무 적을 경우(min_chars 달성 실패) 비정상 파일로 간주해 예외 처리합니다.
    """
    import zipfile
    import json
    import sqlite3
    from bs4 import BeautifulSoup
    import datetime
    
    extracted_data = []
    total_chars = 0
    all_warnings = []
    
    out_file = ctx.dirs['extracted'] / f"{meta.doc_id}.jwpub.json"
    paths_to_process = getattr(meta, 'paths', None) or [meta.path]
    global_order = 1
    
    for idx, path in enumerate(paths_to_process):
        unzip_dir = ctx.dirs['extracted'] / meta.doc_id / f"jwpub_unzip_{idx}"
        
        # 1. Unzip
        try:
            unzip_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(path, 'r') as zip_ref:
                MAX_FILES = 5000
                MAX_TOTAL_SIZE = 500 * 1024 * 1024 # 500MB
                MAX_FILE_SIZE = 100 * 1024 * 1024 # 100MB
                
                info_list = zip_ref.infolist()
                if len(info_list) > MAX_FILES:
                    raise ValueError(f"Zip bomb detected: {len(info_list)} files > {MAX_FILES}")
                total_size = sum(info.file_size for info in info_list)
                if total_size > MAX_TOTAL_SIZE:
                    raise ValueError(f"Zip bomb detected: Total uncompressed size {total_size} > {MAX_TOTAL_SIZE}")
                for info in info_list:
                    if info.file_size > MAX_FILE_SIZE:
                        raise ValueError(f"Zip bomb detected: Single file too large {info.file_size} > {MAX_FILE_SIZE}")
                        
                zip_ref.extractall(unzip_dir)
        except Exception as e:
            logger.error(f"Failed to unzip JWPUB {path}: {e}")
            from ragprep.core.router import quarantine_error
            quarantine_error(meta, ctx, "JWPUB_UNZIP_FAIL", f"Failed to unzip {path}: {e}")
            return False
            
        # 2. V2 폼 (내부 압축): `contents` 파일이 ZIP 구조일 확률이 높음
        inner_unzip_dir = unzip_dir / "inner_contents"
        contents_zip = unzip_dir / "contents"
        
        if contents_zip.exists() and zipfile.is_zipfile(contents_zip):
            inner_unzip_dir.mkdir(parents=True, exist_ok=True)
            try:
                with zipfile.ZipFile(contents_zip, 'r') as inner_zf:
                    MAX_FILES = 5000
                    MAX_TOTAL_SIZE = 500 * 1024 * 1024 # 500MB
                    MAX_FILE_SIZE = 100 * 1024 * 1024 # 100MB
                    info_list = inner_zf.infolist()
                    if len(info_list) > MAX_FILES:
                        raise ValueError(f"Zip bomb detected in inner zip: {len(info_list)} files")
                    total_size = sum(info.file_size for info in info_list)
                    if total_size > MAX_TOTAL_SIZE:
                        raise ValueError(f"Zip bomb detected in inner zip: Total uncompressed size {total_size}")
                    for info in info_list:
                        if info.file_size > MAX_FILE_SIZE:
                            raise ValueError(f"Zip bomb detected in inner zip: Single file too large {info.file_size}")
                            
                    inner_zf.extractall(inner_unzip_dir)
            except Exception as e:
                logger.warning(f"Failed to extract inner contents zip: {e}")
                inner_unzip_dir = unzip_dir # fallback
        else:
            inner_unzip_dir = unzip_dir

        # 3. 데이터 추출 (우선순위: HTML 폴더 -> DB 파일)
        contents_dir = inner_unzip_dir / "contents"
        if not contents_dir.exists():
            contents_dir = inner_unzip_dir
            
        file_sections = []
        file_chars = 0
        warnings = []
        
        html_files = list(contents_dir.glob("*.html")) + list(contents_dir.glob("*.xhtml"))
        if html_files:
            engine_used = "jwpub-html"
            file_sections, file_chars, warnings = _extract_from_html(contents_dir, start_order=global_order)
            all_warnings.extend(warnings)
            
        if file_chars == 0:
            db_files = list(inner_unzip_dir.glob("*.db"))
            if db_files:
                db_path = db_files[0]
                logger.info(f"Fallback to SQLite Database: {db_path.name}")
                engine_used = "jwpub-sqlite"
                file_sections, file_chars = _extract_from_db(db_path, start_order=global_order)
            else:
                if not html_files:
                    logger.warning(f"No contents or publication.db found for {path}")
                    from ragprep.core.router import quarantine_error
                    quarantine_error(meta, ctx, "JWPUB_NO_CONTENT", f"Neither contents/ nor publication.db found in {path}")
                    return False
                
        sections.extend(file_sections)
        total_chars += file_chars
        global_order += len(file_sections)
            
        # Cleanup unzip dir to save space
        try:
            shutil.rmtree(unzip_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup unzip dir {unzip_dir}: {e}")
            
    if total_chars < ctx.min_chars:
        logger.warning(f"JWPUB text too short for {meta.doc_id} ({total_chars} chars)")
        from ragprep.core.router import quarantine_error
        quarantine_error(meta, ctx, "TOO_SHORT_TEXT", f"Total chars {total_chars} < {ctx.min_chars}")
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
            "engine": engine_used,
            "engine_version": None,
            "extracted_at": datetime.datetime.now().isoformat(),
            "extract_warnings": all_warnings
        },
        "sections": sections,
        "stats": {
            "section_count": len(sections),
            "total_chars": total_chars
        }
    }
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    return True

def _clean_html(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "iframe", "meta", "link"]):
        tag.decompose()
        
    from bs4 import Comment
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
        
    for img in soup.find_all('img'):
        alt = img.get('alt', '')
        if alt: img.replace_with(f" [IMG: {alt}] ")
        
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if href and not href.startswith('#'):
            a.append(f" ({href}) ")
            
    text = soup.get_text(separator=' ', strip=True)
    import re
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def _extract_from_html(contents_dir: Path, start_order: int = 1):
    sections = []
    total_chars = 0
    order = start_order
    warnings = []
    
    html_files = sorted(contents_dir.glob("*.html")) + sorted(contents_dir.glob("*.xhtml"))
    for hf in html_files:
        try:
            with open(hf, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), "lxml")
                text = _clean_html(soup)
                
                if text:
                    chars = len(text)
                    sections.append({
                        "section_id": f"s{order}",
                        "heading": Path(hf).stem,
                        "content": text,
                        "order": order
                    })
                    total_chars += chars
                    order += 1
        except Exception as e:
            logger.error(f"Error parsing HTML {hf}: {e}")
            warnings.append(f"Failed to parse {hf.name}: {str(e)}")
            
    return sections, total_chars, warnings

def _extract_from_db(db_path: Path, start_order: int = 1):
    sections = []
    total_chars = 0
    order = start_order
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # JWPUB 스키마 탐색: Document 테이블 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Document'")
        if cursor.fetchone():
            cursor.execute("SELECT Title, Content FROM Document WHERE Content IS NOT NULL")
            rows = cursor.fetchall()
            
            for row in rows:
                title = row[0]
                content = row[1]
                
                if content:
                    if isinstance(content, bytes):
                        # JWPUB SQLite blobs are usually compressed (LZ4/ZLIB) or encrypted.
                        # Since we cannot easily decode proprietary formats here, we skip.
                        pass
                    elif isinstance(content, str):
                        soup = BeautifulSoup(content, "lxml")
                        text = soup.get_text(separator='\n', strip=True)
                        if text:
                            chars = len(text)
                            sections.append({
                                "section_id": f"s{order}",
                                "heading": title,
                                "content": text,
                                "order": order
                            })
                            total_chars += chars
                            order += 1
        else:
            # Document table missing, fallback to raw Document or Bible extraction if needed
            logger.warning(f"No 'Document' table in {db_path.name}")
    except Exception as e:
        logger.error(f"Error parsing SQLite DB {db_path}: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            
    return sections, total_chars
