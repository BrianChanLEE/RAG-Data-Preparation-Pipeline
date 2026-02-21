import os
from pathlib import Path
from typing import Dict, Any # Added Any for FileMeta placeholder

# Assuming FileMeta is a custom type, for now, we'll use Any or expect it to be defined elsewhere.
# If FileMeta is a TypedDict, it would need to be imported from typing.

def get_file_metadata(file_path: Path) -> Any: # Changed FileMeta to Any as it's not defined in the snippet
    """
    파일의 기본 정보(메타데이터)를 추출하고 파이프라인 전반에서 식별자로 사용할 doc_id를 생성합니다.
    - 파일 시스템 정보: 경로, 크기, 수정시간
    - 고유 식별자(doc_id): 파일 이름과 원본 파일의 SHA256 해시값 12자리를 결합하여 멱등성 식별에 사용
    """
    import datetime # This import should ideally be at the top of the file
    
    stat = file_path.stat()
    # Assuming calculate_sha256 is defined elsewhere or will be added.
    # For this change, we'll assume it's available.
    # If not, this function would cause a NameError.
    sha256 = calculate_sha256(file_path) 
    extension = file_path.suffix.lower().lstrip('.')
    
    import re # This import should ideally be at the top of the file
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', file_path.stem)
    doc_id = f"{safe_name}-{sha256[:12]}" # Corrected line
    
    # The rest of the FileMeta construction would go here.
    # For example:
    # return {
    #     "doc_id": doc_id,
    #     "file_path": str(file_path),
    #     "file_name": file_path.name,
    #     "extension": extension,
    #     "size": stat.st_size,
    #     "created_at": datetime.datetime.fromtimestamp(stat.st_ctime),
    #     "modified_at": datetime.datetime.fromtimestamp(stat.st_mtime),
    #     "sha256": sha256
    # }
    
    # Returning a placeholder for now as the full FileMeta structure is not provided.
    return {"doc_id": doc_id, "file_path": str(file_path), "sha256": sha256}


def init_directories(base_dir: Path) -> Dict[str, Path]:
    """
    Initialize directory structure for the pipeline.
    """
    dirs = {
        'raw': base_dir / 'raw',
        'extracted': base_dir / 'extracted',
        'normalized': base_dir / 'normalized',
        'prepared_docs': base_dir / 'prepared' / 'documents',
        'prepared_chunks': base_dir / 'prepared' / 'chunks',
        'prepared_reports': base_dir / 'prepared' / 'reports',
        'quarantine': base_dir / 'quarantine',
        'review': base_dir / 'review',
        'dlq': base_dir / 'dlq',
        'logs': base_dir.parent / 'logs' if base_dir.name == 'data' else base_dir / 'logs'
    }
    
    for _, path in dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        
    return dirs
