from __future__ import annotations
from typing import List
from gridwise.core.model import Sheet, Cell

def to_markdown(sheet: Sheet, include_format: bool = True) -> str:
    """
    Row-major textual serialization with cell addresses and optional ::format.
    Preserves structure for SheetCompressor (paper baseline).
    """
    lines: List[str] = [f"# Sheet: {sheet.name} ({sheet.nrows}x{sheet.ncols})"]
    if sheet.frozen:
        fr, fc = sheet.frozen
        lines.append(f"[META] frozen_rows={fr} frozen_cols={fc}")
    if sheet.merged_regions:
        for (r1, c1, r2, c2) in sheet.merged_regions:
            lines.append(f"[META] merged={r1},{c1},{r2},{c2}")

    rows: List[List[Cell]] = [[] for _ in range(sheet.nrows)]
    for c in sheet.cells:
        if 0 <= c.row < sheet.nrows:
            rows[c.row].append(c)

    for r in range(sheet.nrows):
        row = sorted(rows[r], key=lambda c: c.col)
        if not row:
            lines.append("")
            continue
        md_row = []
        for c in row:
            if isinstance(c.value, str):
                val = repr(c.value)
            else:
                val = "NaN" if (isinstance(c.value, float) and c.value != c.value) else repr(c.value)
            base = f"{c.address}={val}"
            if include_format and c.fmt:
                base += f"::{c.fmt}"
            md_row.append(base)
        lines.append(" | ".join(md_row))
    return "\n".join(lines)
