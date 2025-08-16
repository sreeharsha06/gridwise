from __future__ import annotations
from typing import Tuple, Dict, List
import re

TOTALS_RE = re.compile(r"(?i)\b(total|subtotal|sum|avg|average)\b")

def apply_anchors(text: str, k_keep_between: int = 0) -> Tuple[str, Dict]:
    """
    Mark and preserve anchor lines in encoded spreadsheet text, optionally collapsing 
    large spans between anchors.

    Anchors include:
    - Sheet titles (first line starting with "# Sheet:")
    - Header rows (lines containing "::header")
    - Metadata lines (starting with "[META]")
    - Totals/aggregate rows (matching keywords like total, subtotal, sum, avg)

    Between anchors, long spans of rows can be collapsed, keeping only the first and 
    last `k_keep_between` lines with a summary placeholder.

    Parameters
    ----------
    text : str
        Full encoded spreadsheet text.
    k_keep_between : int, default=0
        Number of lines to keep at the start and end of long spans between anchors.
        If 0, spans are kept verbatim.

    Returns
    -------
    Tuple[str, Dict]
        - Collapsed text with anchors marked as "[ANCHOR]..."
        - Metadata with indices of kept anchor lines and applied rule description
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
