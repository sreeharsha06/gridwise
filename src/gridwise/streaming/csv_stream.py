from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import Counter, defaultdict
import json
import pandas as pd

from gridwise.core.utils import idx_to_addr
from gridwise.eval.tokens import count_tokens

def _render_value(v) -> str:
    import math
    try:
        import numpy as np
        if isinstance(v, np.integer):
            v = int(v)
        elif isinstance(v, np.floating):
            v = float(v)
            if math.isnan(v):
                return "NaN"
    except Exception:
        pass
    if isinstance(v, str):
        return repr(v)
    if isinstance(v, float) and v != v:
        return "NaN"
    return repr(v)

def _lines_to_token_count(lines: List[str]) -> int:
    return count_tokens("\n".join(lines))

def _flush_chunk(chunks_fh, chunk_id: int, lines: List[str]) -> int:
    if not lines:
        return chunk_id
    chunks_fh.write(json.dumps({"id": chunk_id, "content": "\n".join(lines)}, ensure_ascii=False) + "\n")
    return chunk_id + 1

def _col_letters(col_index: int) -> str:
    res = ""
    c = col_index + 1
    while c > 0:
        c, rem = divmod(c - 1, 26)
        res = chr(65 + rem) + res
    return res

def stream_encode_csv_to_jsonl(
    path: str,
    out_jsonl: Optional[str] = None,
    *,
    usecols: Optional[List[str]] = None,
    chunksize: int = 100_000,
    max_tokens_per_chunk: int = 4_000,
    overlap_tokens: int = 200,
    build_dictionary: bool = True,
    include_format: bool = True,
    sheet_name: Optional[str] = None,
    output_mode: str = "compressed",  # "compressed" | "expanded"
) -> Tuple[str, Optional[str]]:
    src = Path(path)
    if out_jsonl is None:
        out_jsonl = str(src.with_suffix("")) + ".gridwise.jsonl"
    jsonl_path = Path(out_jsonl)

    per_col_freq: Dict[int, Counter] = defaultdict(Counter)
    col_names: Optional[List[str]] = None
    reader1 = pd.read_csv(path, usecols=usecols, chunksize=chunksize)
    for df in reader1:
        df = df.reset_index(drop=True)
        if col_names is None:
            col_names = [str(c) for c in df.columns]
        for j, col in enumerate(col_names):
            sv = df[col].dropna()
            if sv.dtype == "object":
                for s in sv:
                    if isinstance(s, str):
                        per_col_freq[j][repr(s)] += 1
    if col_names is None:
        raise ValueError("CSV appears empty or unreadable.")

    col_dicts: Dict[int, Dict[str, str]] = {}
    rev_dicts: Dict[int, Dict[str, str]] = {}

    if build_dictionary and output_mode == "compressed":
        for j, freq in per_col_freq.items():
        # take ALL distinct strings (keys of freq)
            vocab = list(freq.keys())

        # OPTIONAL: skip short strings (e.g., len < 3)
            SKIP_IF_SHORTER_THAN = 3  # set to None to disable
            if SKIP_IF_SHORTER_THAN is not None:
                vocab = [v for v in vocab if len(v[1:-1]) >= SKIP_IF_SHORTER_THAN]

            # order by frequency desc, then lexical to be deterministic
            vocab.sort(key=lambda v: (-freq[v], v))
            if vocab:
                mapping = {v: f"@C{{{_col_letters(j)}}}t{i+1}" for i, v in enumerate(vocab)}
                col_dicts[j] = mapping
                rev_dicts[j] = {code: sval for sval, code in mapping.items()}

    # PASS 2: render + chunk
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    chunk_id = 0
    buffer_lines: List[str] = []

    with jsonl_path.open("w", encoding="utf-8") as out_f:
        sheet_title = sheet_name or src.stem
        header_lines = [f"# Sheet: {sheet_title} (unknownx{len(col_names)})"]
        header_row = []
        for j, col in enumerate(col_names):
            addr = idx_to_addr(0, j)
            cell = f"{addr}={repr(col)}"
            if include_format:
                cell += "::header"
            header_row.append(cell)
        header_lines.append("[ANCHOR]" + " | ".join(header_row))
        buffer_lines.extend(header_lines)

        reader2 = pd.read_csv(path, usecols=usecols, chunksize=chunksize)
        row_base = 0
        for df in reader2:
            df = df.reset_index(drop=True)
            for i in range(df.shape[0]):
                cells = []
                for j, col in enumerate(col_names):
                    val = df.iat[i, j]
                    addr = idx_to_addr(row_base + 1 + i, j)
                    s = _render_value(val)
                    if output_mode == "compressed":
                        if build_dictionary and j in col_dicts and isinstance(val, str):
                            code = col_dicts[j].get(repr(val))
                            if code:
                                s = code
                    cells.append(f"{addr}={s}")
                buffer_lines.append(" | ".join(cells))

                if _lines_to_token_count(buffer_lines) > max_tokens_per_chunk:
                    if overlap_tokens > 0:
                        content = "\n".join(buffer_lines)
                        out_f.write(json.dumps({"id": chunk_id, "content": content}, ensure_ascii=False) + "\n")
                        chunk_id += 1
                        tail = content[-overlap_tokens * 4 :]
                        buffer_lines = [tail]
                    else:
                        chunk_id = _flush_chunk(out_f, chunk_id, buffer_lines)
                        buffer_lines = []
            row_base += df.shape[0]

        if buffer_lines:
            chunk_id = _flush_chunk(out_f, chunk_id, buffer_lines)
            buffer_lines = []

        if output_mode == "compressed" and rev_dicts:
            dict_lines = ["[DICT-BEGIN]"]
            for j in sorted(rev_dicts.keys()):
                dict_lines.append(f"[COL {_col_letters(j)}]")
                for code, sval in rev_dicts[j].items():
                    dict_lines.append(f"{code}={sval}")
            dict_lines.append("[DICT-END]")
            _ = _flush_chunk(out_f, chunk_id, dict_lines)

    return str(jsonl_path), (None)
