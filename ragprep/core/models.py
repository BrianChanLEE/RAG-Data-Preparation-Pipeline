"""
Core data models for RAG Pipeline
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime
from enum import Enum

SCHEMA_VERSION = "1.0.0"

class RunContext(BaseModel):
    """
    파이프라인 실행 시의 전역 환경 변수들을 보유하는 객체입니다.
    데이터 입출력 경로, 병렬 처리 워커 수, 실행 ID, 격리 재시도 등의 플래그를 담습니다.
    """
    input_dir: Path
    out_dir: Path
    force: bool
    concurrency: int
    retry_quarantine: bool
    merge_group: bool
    quality_gate: bool = True
    dedupe: bool = True
    dedupe_scope: str = "doc"
    pii_mask: bool = False
    executor_type: str = "process"
    max_retries: int = 1
    retry_backoff_ms: int = 2000
    min_chars: int
    run_id: str
    start_time: datetime = Field(default_factory=datetime.now)
    dirs: dict[str, Path]
    
class FileMeta(BaseModel):
    path: str
    paths: Optional[List[str]] = None
    filename: str
    extension: str
    sha256: str
    filesize: int
    mtime: str
    doc_id: str
    group_id: Optional[str] = None

class SectionInfo(BaseModel):
    """
    구조화 단계에서 생성되는 문서의 단락(Section) 정보입니다.
    """
    section_id: str
    heading: Optional[str] = None
    content: str
    
class NormalizedSchema(BaseModel):
    """
    추출 단계 이후, 모든 문서가 통일되게 갖는 구조 규격(Schema)입니다.
    알아볼 수 없는 제어문자나 공백이 정제된 텍스트와, 통계 데이터를 가지고 있습니다.
    """
    doc_id: str
    title_guess: str
    type: str # pdf, jwpub 등
    sections: List[SectionInfo] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)

class DocumentSection(BaseModel):
    """
    최종 구조화(Structuring)가 완료된 계층 문서 조각 객체입니다.
    """
    section_id: str
    heading: Optional[str]
    order: int
    content: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None

class DocumentSchema(BaseModel):
    doc_id: str
    type: str
    revision: int = 1
    normalized_sha256: Optional[str] = None
    title: Optional[str] = None
    source: Dict[str, Any] = Field(default_factory=dict)
    sections: List[DocumentSection]

class ChunkMeta(BaseModel):
    source_path: str
    sha256: str
    version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class ChunkLineage(BaseModel):
    doc_id: str
    group_id: Optional[str] = None
    revision: int = 1
    source_paths: List[str]
    stage_versions: Dict[str, str]

class ChunkSchema(BaseModel):
    chunk_id: str
    doc_id: str
    type: str
    title: Optional[str] = None
    section: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    text: str
    metadata: ChunkMeta
    lineage: Optional[ChunkLineage] = None
    
class ProcessingResult(BaseModel):
    doc_id: str
    filename: str
    type: str
    sha256: str
    status: str # SUCCESS, SKIPPED, FAILED
    failed_reason: Optional[str] = None
    pages: Optional[int] = None
    sections: Optional[int] = None
    total_chars: int = 0
    chunks: int = 0
    duration_ms: int = 0
    outputs: Dict[str, Optional[str]] = Field(default_factory=lambda: {"extracted": None, "normalized": None, "document": None, "chunks": None})

class QualityDecision(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    QUARANTINE = "QUARANTINE"

class QualityMetrics(BaseModel):
    doc_id: str
    group_id: Optional[str] = None
    source_type: str
    total_chars: int = 0
    valid_chars: int = 0
    replacement_char_ratio: float = 0.0
    header_footer_repeat_ratio: float = 0.0
    section_detect_rate: float = 0.0
    chunk_count: int = 0
    short_chunk_ratio: float = 0.0
    overlap_ok_ratio: float = 0.0
    sentence_boundary_ok_ratio: float = 0.0
    quality_score: float = 0.0
    decision: QualityDecision = QualityDecision.PASS
    reasons: List[str] = Field(default_factory=list)

class RunStats(BaseModel):
    processed: int = 0
    passed: int = 0
    review: int = 0
    quarantined: int = 0
    failed: int = 0

class HostInfo(BaseModel):
    os: str
    python_version: str
    cpu_count: int

class RunConfig(BaseModel):
    concurrency: int
    merge_group: bool
    quality_gate: bool
    dedupe: bool = True
    dedupe_scope: str = "doc"
    pii_mask: bool = False
    executor_type: str = "process"
    max_retries: int = 1
    retry_backoff_ms: int = 2000
    min_chars: int
    retry_quarantine: bool

class RunManifest(BaseModel):
    run_id: str
    schema_version: str = SCHEMA_VERSION
    started_at: str
    finished_at: str
    git_commit: Optional[str] = None
    requirements_hash: Optional[str] = None
    config: RunConfig
    host: HostInfo
    stats: RunStats
