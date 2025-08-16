import re
from typing import List, Dict, Callable, Optional

_DICT_RE = re.compile(r"\[DICT-BEGIN\](?:.|\n)*?\[DICT-END\]\s*$", re.MULTILINE)
_ANCHOR_RE = re.compile(r"(?=^\[ANCHOR\].*$)", re.MULTILINE)

def chunk_anchor_and_dict_safe(
    text: str,
    max_tokens: int,
    overlap_tokens: int = 0,
    token_counter: Optional[Callable[[str], int]] = None,
) -> List[Dict]:
    """
    Chunk `text` without splitting inside the trailing DICT block.
    Prefer to split on [ANCHOR] boundaries. If an anchor segment
    exceeds `max_tokens`, fall back to line-packing within that segment.
    The DICT block (if present) is emitted as the final chunk.
    """
    if token_counter is None:
        def token_counter(s: str) -> int:
            return max(1, len(s) // 4)

    chunks: List[Dict] = []
    next_id = 0

    dict_match = _DICT_RE.search(text)
    dict_block = ""
    body = text
    if dict_match:
        dict_block = dict_match.group(0)
        body = text[: dict_match.start()].rstrip()

    anchor_positions = [m.start() for m in _ANCHOR_RE.finditer(body)]
    segments: List[str] = []
    if anchor_positions:
        anchor_positions.append(len(body))
        for a, b in zip(anchor_positions[:-1], anchor_positions[1:]):
            seg = body[a:b].lstrip("\n")
            if seg:
                segments.append(seg)
    else:
        if body:
            segments.append(body)

    def pack_lines(lines: List[str]) -> List[str]:
        out: List[str] = []
        buf: List[str] = []
        buf_tokens = 0

        def flush():
            nonlocal buf, buf_tokens
            if buf:
                out.append("\n".join(buf))
                buf, buf_tokens = [], 0

        for ln in lines:
            t = token_counter(ln + "\n")
            if t > max_tokens and not buf:
                s = ln
                while s:
                    approx_chars = max_tokens * 4
                    piece = s[:approx_chars]
                    out.append(piece)
                    s = s[approx_chars:]
                continue

            if buf_tokens + t > max_tokens and buf:
                flush()
            buf.append(ln)
            buf_tokens += t
        flush()
        return out

    buf: List[str] = []
    buf_tokens = 0

    def flush_buf():
        nonlocal buf, buf_tokens, next_id
        if not buf:
            return
        content = "\n".join(buf).rstrip()
        chunks.append({"id": next_id, "content": content})
        next_id += 1
        if overlap_tokens > 0:
            tail = content[-overlap_tokens * 4 :]
            buf[:] = [tail] if tail else []
            buf_tokens = token_counter(tail) if tail else 0
        else:
            buf[:] = []
            buf_tokens = 0

    for seg in segments:
        seg_tokens = token_counter(seg + "\n")
        if seg_tokens <= max_tokens:
            if buf_tokens + seg_tokens > max_tokens and buf:
                flush_buf()
            buf.append(seg)
            buf_tokens += seg_tokens
        else:
            seg_lines = seg.splitlines()
            packed = pack_lines(seg_lines)
            for piece in packed:
                t = token_counter(piece + "\n")
                if buf_tokens + t > max_tokens and buf:
                    flush_buf()
                buf.append(piece)
                buf_tokens += t
    flush_buf()

    if dict_block.strip():
        chunks.append({"id": next_id, "content": dict_block.rstrip()})

    return chunks
