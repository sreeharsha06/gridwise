# gridwise/encode/compressor/dict_rebuild.py
from __future__ import annotations
import re
from typing import Dict, List
from collections import defaultdict

_CODE_RE = re.compile(r"@C\{([A-Z]+)\}t(\d+)\b")
_ALL_DICTS_RE = re.compile(r"\[DICT-BEGIN\].*?\[DICT-END\]\s*", re.S)

def force_rebuild_dict_block(text: str, rev_dicts: Dict[str, Dict[str, str]]) -> str:
    base = re.sub(_ALL_DICTS_RE, "", text).rstrip()

    used = defaultdict(set)  # col -> {t}
    for col, num in _CODE_RE.findall(base):
        used[col].add(int(num))

    if not any(used.values()):
        return base

    lines: List[str] = ["[DICT-BEGIN]"]
    for col in sorted(used.keys()):
        tnums = sorted(used[col])
        if not tnums:
            continue
        lines.append(f"[COL {col}]")
        rev = rev_dicts.get(col, {})
        for t in tnums:
            code = f"@C{{{col}}}t{t}"
            raw = rev.get(code)
            # Always print a line; mark missing to surface wiring issues
            lines.append(f"{code}={raw if raw is not None else '<MISSING>'}")
    lines.append("[DICT-END]")
    return base + "\n" + "\n".join(lines) + "\n"
