import re
import logging
from typing import Set, Dict, List

logger = logging.getLogger("ragprep.dedupe")

def _get_ngrams(text: str, n: int = 3) -> Set[str]:
    """텍스트에서 n-gram 핑거프린트를 추출합니다."""
    words = re.findall(r'\w+', text.lower())
    if len(words) < n:
        return set(words)
    return set([' '.join(words[i:i+n]) for i in range(len(words)-n+1)])

def calculate_fingerprint(text: str) -> Set[str]:
    return _get_ngrams(text, n=3)

def jaccard_similarity(fp1: Set[str], fp2: Set[str]) -> float:
    if not fp1 or not fp2: 
        return 0.0
    return len(fp1 & fp2) / len(fp1 | fp2)

class ChunkDeduplicator:
    """
    SimHash 대신 n-gram Jaccard 유사도 기반으로 Near-Duplicate을 차단하는 모듈.
    (의존성 없는 인메모리 방식)
    """
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.fingerprints: Dict[str, List[Set[str]]] = {}
        
    def is_duplicate(self, scope_id: str, text: str) -> bool:
        if not text.strip(): 
            return True
            
        fp = calculate_fingerprint(text)
        if not fp: 
            return True
            
        if scope_id not in self.fingerprints:
            self.fingerprints[scope_id] = []
            
        for existing_fp in self.fingerprints[scope_id]:
            sim = jaccard_similarity(fp, existing_fp)
            if sim >= self.threshold:
                return True
                
        self.fingerprints[scope_id].append(fp)
        return False
