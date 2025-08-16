from __future__ import annotations
from typing import Tuple, Dict, List, Optional
import re
import statistics

CELL_RE = re.compile(r"(?P<addr>([A-Z]+)\d+)=(?P<val>[^|]+?)(?P<fmt>::[^|]+)?(?=$| \| )")
NUM_RE  = re.compile(r"^[\-+]?\d+(\.\d+)?$")

def _is_anchor_line(ln: str) -> bool:
    return ln.startswith("[ANCHOR]") or ln.startswith("[META]") or ln.startswith("[DICT")

def _val_to_float(v: str) -> Optional[float]:
    t = v.strip().strip("'")
    if NUM_RE.match(t):
        try:
            return float(t)
        except Exception:
            return None
    return None

def apply_aggregation(
    text: str,
    sample_head: int = 5,
    sample_tail: int = 5,
    sample_every: int = 50,
    z_outlier: float = 3.0,
) -> Tuple[str, Dict]:
    
    """
    Reduce long blocks of spreadsheet rows by sampling, keeping anomalies, 
    and adding compact numeric summaries.

    - Keeps head/tail rows and periodic samples in the middle.
    - Always retains rows with numeric outliers (z-score ≥ threshold).
    - Appends a compact [AGG ...] line with per-column stats (count, min, max, mean, p10, p90).
    - Leaves short spans unchanged.

    Returns
    -------
    (str, dict)
        Aggregated text and a metadata dict with sampling parameters.
    """

    
    lines = text.splitlines()
    N = len(lines)
    out: List[str] = []
    i = 0

    def _percentile(vals: List[float], p: float) -> float:
        xs = sorted(vals)
        if not xs:
            return float("nan")
        k = max(0, min(len(xs) - 1, int(round((p / 100.0) * (len(xs) - 1)))))
        return xs[k]

    def emit_span(i0: int, i1: int):
        span = lines[i0 : i1 + 1]
        if len(span) <= sample_head + sample_tail:
            out.extend(span)
            return

        # numeric per column letters
        col_vals: Dict[str, List[float]] = {}
        parsed_rows = []
        for ln in span:
            row_cells = []
            for m in CELL_RE.finditer(ln):
                addr = m.group("addr")
                col_letters = re.match(r"([A-Z]+)", addr).group(1)
                val = m.group("val")
                row_cells.append((col_letters, val))
                f = _val_to_float(val)
                if f is not None:
                    col_vals.setdefault(col_letters, []).append(f)
            parsed_rows.append(row_cells)

        stats_per_col: Dict[str, Dict[str, float]] = {}
        for col, vals in col_vals.items():
            if len(vals) >= sample_head + sample_tail + 1:
                mean = statistics.fmean(vals)
                stdev = statistics.pstdev(vals) if len(vals) > 1 else 0.0
                stats_per_col[col] = {
                    "count": float(len(vals)),
                    "min": float(min(vals)),
                    "max": float(max(vals)),
                    "mean": float(mean),
                    "p10": float(_percentile(vals, 10)),
                    "p90": float(_percentile(vals, 90)),
                    "stdev": float(stdev),
                }

        outlier_rows: set[int] = set()
        if stats_per_col:
            for r_i, row_cells in enumerate(parsed_rows):
                for (col_letters, val) in row_cells:
                    f = _val_to_float(val)
                    if f is None or col_letters not in stats_per_col:
                        continue
                    st = stats_per_col[col_letters]
                    if st["stdev"] > 0:
                        z = abs((f - st["mean"]) / st["stdev"])
                        if z >= z_outlier:
                            outlier_rows.add(r_i)

        keep = set(range(0, min(sample_head, len(span))))
        keep.update(range(max(0, len(span) - sample_tail), len(span)))
        for k in range(sample_head, max(0, len(span) - sample_tail), sample_every):
            keep.add(k)
        keep.update(outlier_rows)

        for idx, ln in enumerate(span):
            if idx in keep:
                out.append(ln)

        if stats_per_col:
            stats_parts = []
            for col in sorted(stats_per_col.keys()):
                st = stats_per_col[col]
                stats_parts.append(
                    f"{col}:count={int(st['count'])},min={st['min']:.4g},max={st['max']:.4g},"
                    f"mean={st['mean']:.4g},p10={st['p10']:.4g},p90={st['p90']:.4g}"
                )
            out.append(f"[AGG span={len(span)} kept={len(keep)} stats={' | '.join(stats_parts)}]")

    while i < N:
        if _is_anchor_line(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        j = i
        while j < N and not _is_anchor_line(lines[j]):
            j += 1
        emit_span(i, j - 1)
        i = j

    meta = {"mode": "safe", "sample_head": sample_head, "sample_tail": sample_tail, "sample_every": sample_every}
    return "\n".join(out), meta
