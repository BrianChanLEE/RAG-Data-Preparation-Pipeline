import re

# 기본적인 개인정보 정규식 패턴: 이메일, 휴대전화, KOR 주민등록번호 형식
PII_PATTERNS = [
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),
    (re.compile(r'\b010-\d{3,4}-\d{4}\b'), '[PHONE]'),
    (re.compile(r'\b\d{6}-[1-4]\d{6}\b'), '[RRN]')
]

def mask_pii(text: str) -> str:
    """정규식을 이용해 텍스트 내의 개인정보를 마스킹합니다."""
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text
