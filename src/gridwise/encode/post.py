from __future__ import annotations
import re
from typing import Dict, List

_DICT_BLOCK_RE = re.compile(r"\[DICT-BEGIN\](.*?)\[DICT-END\]", re.S)
_DICT_LINE_RE  = re.compile(r"^(@C\{[A-Z]+\}t\d+)=(.+)$")
_CODE_RE       = re.compile(r"@C\{[A-Z]+\}t\d+")

def parse_dict_block(text: str) -> Dict[str, str]:
    """Return mapping like {'@C{N}t1': `'No'`, ...}. Keeps quotes in values."""
    m = _DICT_BLOCK_RE.search(text)
    if not m:
        return {}
    block = m.group(1)
    mapping: Dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        mm = _DICT_LINE_RE.match(line)
        if mm:
            mapping[mm.group(1)] = mm.group(2)
    return mapping

def expand_text_with_dict(text: str, mapping: Dict[str, str]) -> str:
    """Replace @C{X}tN codes with original values, but do NOT modify the DICT block."""
    if not mapping:
        return text
    # Split around the first DICT block (if present)
    m = _DICT_BLOCK_RE.search(text)
    if not m:
        return _CODE_RE.sub(lambda mm: mapping.get(mm.group(0), mm.group(0)), text)

    prefix = text[:m.start()]            # content before DICT
    dict_block = text[m.start():m.end()] # the DICT block itself
    suffix = text[m.end():]              # anything after the DICT block

    expanded_prefix = _CODE_RE.sub(lambda mm: mapping.get(mm.group(0), mm.group(0)), prefix)
    # leave dict_block untouched
    expanded_suffix = _CODE_RE.sub(lambda mm: mapping.get(mm.group(0), mm.group(0)), suffix)
    return expanded_prefix + dict_block + expanded_suffix

def expand_chunks_with_dict(chunks: List[dict]) -> List[dict]:
    """Find dict block in any chunk; expand codes in non-dict regions only."""
    # Build mapping from the last chunk that contains a DICT (common pattern)
    mapping: Dict[str, str] = {}
    for ch in reversed(chunks):
        if "[DICT-BEGIN]" in ch["content"]:
            mapping = parse_dict_block(ch["content"])
            if mapping:
                break
    if not mapping:
        return chunks[:]

    out: List[dict] = []
    for ch in chunks:
        content = ch["content"]
        if "[DICT-BEGIN]" in content:
            # expand only outside the dict block within this chunk
            out.append({"id": ch["id"], "content": expand_text_with_dict(content, mapping)})
        else:
            # no dict in this chunk → safe to expand all
            out.append({"id": ch["id"], "content": _CODE_RE.sub(lambda mm: mapping.get(mm.group(0), mm.group(0)), content)})
    return out
