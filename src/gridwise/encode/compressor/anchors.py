from __future__ import annotations
from typing import Tuple, Dict, List
import re

TOTALS_RE = re.compile(r"(?i)\b(total|subtotal|sum|avg|average)\b")

def apply_anchors(text: str, k_keep_between: int = 0) -> Tuple[str, Dict]:
    """
    Mark structural anchors and (optionally) collapse long spans between anchors.
    Anchors: "# Sheet:", '::header', [META] lines, totals-like rows.
    """
    lines = text.splitlines()
    N = len(lines)
    is_anchor = [False] * N

    for i, ln in enumerate(lines):
        if i == 0 and ln.startswith("# Sheet:"):
            is_anchor[i] = True
        if "::header" in ln:
            is_anchor[i] = True
        if ln.startswith("[META]"):
            is_anchor[i] = True
        if TOTALS_RE.search(ln):
            is_anchor[i] = True

    out: List[str] = []
    kept_idxs: List[int] = []
    i = 0
    while i < N:
        if is_anchor[i]:
            out.append(f"[ANCHOR]{lines[i]}")
            kept_idxs.append(i)
            i += 1
            continue
        j = i
        while j < N and not is_anchor[j]:
            j += 1
        span_len = j - i
        if k_keep_between > 0 and span_len > 2 * k_keep_between:
            head = lines[i : i + k_keep_between]
            tail = lines[j - k_keep_between : j]
            out.extend(head)
            out.append(f"[COLLAPSED span={span_len - 2 * k_keep_between}]")
            out.extend(tail)
        else:
            out.extend(lines[i:j])
        i = j

    meta = {"anchors": kept_idxs, "rule": "sheet/header/meta/totals; optional collapse"}
    return "\n".join(out), meta
