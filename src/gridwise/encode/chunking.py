from typing import List, Dict, Callable

def window(text: str, max_tokens: int, overlap_tokens: int = 0,
           token_counter: Callable[[str], int] | None = None) -> List[Dict]:
    if token_counter is None:
        def token_counter(s: str) -> int:
            return max(1, len(s) // 4)

    if token_counter(text) <= max_tokens:
        return [{"id": 0, "content": text}]

    lines = text.splitlines()
    chunks: List[Dict] = []
    buf: List[str] = []
    buf_tokens = 0
    idx = 0

    def flush():
        nonlocal buf, buf_tokens, idx
        if buf:
            chunks.append({"id": idx, "content": "\n".join(buf)})
            idx += 1
            buf, buf_tokens = [], 0

    for ln in lines:
        t = token_counter(ln + "\n")
        if buf_tokens + t > max_tokens and buf:
            if overlap_tokens > 0:
                overlap_text = "\n".join(buf)[-overlap_tokens*4 :]
                chunks.append({"id": idx, "content": "\n".join(buf)})
                idx += 1
                buf, buf_tokens = [overlap_text], token_counter(overlap_text)
            else:
                flush()
        buf.append(ln)
        buf_tokens += t
    flush()
    return chunks
