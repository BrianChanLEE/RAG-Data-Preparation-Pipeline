import hashlib
import os
import re
from pathlib import Path
from typing import List
from datetime import datetime

from ragprep.core.models import RunContext, FileMeta

def calculate_sha256(file_path: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def normalize_filename(filename: str) -> str:
    # Remove extension
    name = Path(filename).stem
    # Replace non alphanumeric with underscore
    name = re.sub(r'[^a-zA-Z0-9가-힣]+', '_', name)
    return name.strip('_')

def create_doc_id(filepath: Path, sha256_hash: str) -> str:
    norm_name = normalize_filename(filepath.name)
    return f"{norm_name}-{sha256_hash[:12]}"

def get_file_meta(filepath: Path, input_dir: Path = None) -> FileMeta:
    stat = filepath.stat()
    sha = calculate_sha256(filepath)
    doc_id = create_doc_id(filepath, sha)
    
    mtime_str = datetime.fromtimestamp(stat.st_mtime).isoformat()
    
    group_id = None
    if input_dir and input_dir in filepath.parents:
        rel_parts = filepath.relative_to(input_dir).parts
        if len(rel_parts) > 1:
            group_id = rel_parts[0]
            
    return FileMeta(
        path=str(filepath.resolve()),
        filename=filepath.name,
        extension=filepath.suffix.lower().strip('.'),
        sha256=sha,
        filesize=stat.st_size,
        mtime=mtime_str,
        doc_id=doc_id,
        group_id=group_id
    )

def scan_files(ctx: RunContext) -> List[Path]:
    """
    처리할 대상 파일들을 스캔하고 수집합니다.
    입력 디렉토리(--input)를 탐색하여 파일 목록을 반환합니다.
    """
    files = []
    
    # 설정된 경우, 이전에 실패하여 격리 폴더(quarantine)에 있는 파일들도 대상에 포함시킵니다.
    if ctx.retry_quarantine and ctx.dirs['quarantine'].exists():
        for f in ctx.dirs['quarantine'].rglob('*'):
            if f.is_file() and f.name != 'fail.json':
                files.append(f)
                        
    # 입력 디렉토리에서 모든 원시 파일을 스캔합니다 (재귀 탐색).
    input_dir = ctx.input_dir
    if input_dir.exists() and input_dir.is_dir():
        for f in input_dir.rglob('*'):
            if f.is_file() and not f.name.startswith('.'):
                files.append(f)
                
    # 중복 파일 제거를 위해 Set으로 형변환 후 오름차순 정렬하여 반환합니다.
    return sorted(list(set(files)))
