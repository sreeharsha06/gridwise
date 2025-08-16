from typing import Dict
from .tokens import count_tokens

def compression_ratio(original_tokens: int, compressed_tokens: int) -> float:
    return 1.0 if original_tokens == 0 else compressed_tokens / original_tokens

def report(original_text: str, compressed_text: str) -> Dict[str, float]:
    o = count_tokens(original_text); c = count_tokens(compressed_text)
    return {"orig_tokens": o, "compressed_tokens": c, "ratio": compression_ratio(o, c)}
