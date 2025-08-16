# gridwise/encode/compressor/invert_index.py
from __future__ import annotations
from typing import Tuple, Dict, List, DefaultDict, Optional
import re
from collections import defaultdict, Counter

CELL_RE = re.compile(
    r"(?P<addr>([A-Z]+)\d+)="
    r"(?P<val>(?:'[^']*')|(?:\"[^\"]*\"))"
    r"(?P<fmt>::[^|]+)?"
)

DICT_BLOCK_GLOBAL_RE = re.compile(r"\[DICT-BEGIN\].*?\[DICT-END\]\s*", re.S)
CODE_RE = re.compile(r"@C\{([A-Z]+)\}t(\d+)\b")

def _col_letters(addr: str) -> str:
    m = re.match(r"([A-Z]+)", addr)
    return m.group(1) if m else addr

def _unquote_keep(s: str) -> tuple[str, str]:
    if len(s) >= 2 and ((s[0] == s[-1] == "'") or (s[0] == s[-1] == '"')):
        raw = s[1:-1]; quoted = s
    else:
        raw = s; quoted = s
    norm = " ".join(raw.split())
    return norm, quoted

def apply_inverted_index(
    text: str,
    *,
    min_freq: int = 3,
    encode_all_strings: bool = True,
    skip_if_shorter_than: Optional[int] = None,
) -> Tuple[str, Dict]:
    
    """
    Replace repeated string values in encoded spreadsheet text with short codes,
    maintaining per-column dictionaries for later expansion.

    This compression pass scans cell values in the encoded text, normalizes them
    (whitespace collapsed, quotes preserved), and assigns deterministic codes of
    the form ``@C{COL}tN`` per column. It is especially effective when many
    repeated strings (e.g. categories, names, survey responses) appear.

    Parameters
    ----------
    text : str
        Encoded spreadsheet text (as produced by GridWise vanilla encoder).
    min_freq : int, default=3
        Minimum frequency for a string (per column) to be encoded if
        ``encode_all_strings`` is False.
    encode_all_strings : bool, default=True
        If True, encode every string value regardless of frequency.
        If False, only encode values with frequency >= ``min_freq``.
    skip_if_shorter_than : int or None, default=None
        If set, string values shorter than this length are not encoded
        (useful to avoid replacing very short labels with codes that may
        actually cost more tokens).

    Returns
    -------
    Tuple[str, Dict]
        - ``new_text`` : str  
          Text with string values replaced by codes like ``@C{A}t4``.  
          Any pre-existing ``[DICT-BEGIN]...[DICT-END]`` blocks are stripped.  
        - ``meta`` : dict  
          Metadata including:
          * ``per_column`` (bool) — dictionaries are built per column
          * ``encode_all_strings`` / ``min_freq`` / ``skip_if_shorter_than`` (settings)
          * ``rev_dicts`` — reverse dictionaries mapping codes → exemplar quoted values

    Notes
    -----
    - Codes are assigned **per column** in descending frequency order, with
      ties broken by first-seen order.
    - Normalization collapses whitespace inside values but preserves quoted form.
    - The reverse dictionaries allow you to later expand codes back into their
      original strings when preparing prompts.

    Example
    -------
    >>> compressed, meta = apply_inverted_index(encoded_text, min_freq=2)
    >>> print(compressed.splitlines()[0])
    A1=@C{A}t1 | B1=@C{B}t2
    >>> print(meta["rev_dicts"]["A"]["@C{A}t1"])
    "'Yes'"
    """
    
    lines = text.splitlines()

    col_freq_norm: DefaultDict[str, Counter] = defaultdict(Counter)
    col_first_seen_norm: DefaultDict[str, Dict[str, int]] = defaultdict(dict)
    col_norm_to_exemplar: DefaultDict[str, Dict[str, str]] = defaultdict(dict)
    matches_per_line: List[List[re.Match]] = []

    ordinal = 0
    for ln in lines:
        ms = list(CELL_RE.finditer(ln))
        matches_per_line.append(ms)
        for m in ms:
            col = _col_letters(m.group("addr"))
            sval = m.group("val")
            norm, quoted = _unquote_keep(sval)
            if skip_if_shorter_than is not None and len(norm) < skip_if_shorter_than:
                continue
            col_freq_norm[col][norm] += 1
            if norm not in col_first_seen_norm[col]:
                col_first_seen_norm[col][norm] = ordinal
                col_norm_to_exemplar[col][norm] = quoted
                ordinal += 1

    col_norm2code: Dict[str, Dict[str, str]] = {}
    rev_dicts: Dict[str, Dict[str, str]] = {}

    for col, freq_ctr in col_freq_norm.items():
        vocab = list(freq_ctr.keys()) if encode_all_strings else [
            v for v,c in freq_ctr.items() if c >= min_freq
        ]
        if not vocab:
            continue
        vocab.sort(key=lambda v: (-freq_ctr[v], col_first_seen_norm[col][v]))
        mapping = {norm: f"@C{{{col}}}t{i+1}" for i, norm in enumerate(vocab)}
        col_norm2code[col] = mapping
        rev_dicts[col] = { mapping[norm]: col_norm_to_exemplar[col][norm] for norm in vocab }

    out_lines: List[str] = []
    for ln, ms in zip(lines, matches_per_line):
        if not ms:
            out_lines.append(ln); continue
        new_ln = ln
        for m in reversed(ms):
            col = _col_letters(m.group("addr"))
            sval = m.group("val")
            norm, _ = _unquote_keep(sval)
            if skip_if_shorter_than is not None and len(norm) < skip_if_shorter_than:
                continue
            code = col_norm2code.get(col, {}).get(norm)
            if code:
                s, e = m.span("val")
                new_ln = new_ln[:s] + code + new_ln[e:]
        out_lines.append(new_ln)

    replaced = "\n".join(out_lines)
    replaced = re.sub(DICT_BLOCK_GLOBAL_RE, "", replaced).rstrip()

    meta = {
        "per_column": True,
        "encode_all_strings": encode_all_strings,
        "min_freq": min_freq,
        "skip_if_shorter_than": skip_if_shorter_than,
        "rev_dicts": {k: dict(v) for k,v in rev_dicts.items()},
    }
    return replaced, meta
