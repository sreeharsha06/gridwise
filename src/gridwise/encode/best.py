from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal

from gridwise.encode.vanilla import to_markdown
from gridwise.encode.compressor import encode as compress
from gridwise.encode.chunking import chunk_anchor_and_dict_safe
from gridwise.encode.post import parse_dict_block, expand_text_with_dict
from gridwise.eval.tokens import count_tokens
from gridwise.core.model import Sheet, BestEncodeResult

Mode = Literal["practical", "research"]
OutputMode = Literal["compressed", "expanded", "auto"]

def best_encode(
    sheet: Sheet,
    *,
    include_format: bool = True,
    compress_min_tokens: int = 5_000,
    max_tokens_per_chunk: int = 4_000,
    overlap_tokens: int = 200,
    use_anchors: bool = True,
    use_inverted_index: bool = True,
    use_aggregation: bool = True,
    output_mode: OutputMode = "compressed",
    # NEW — knobs:
    dict_min_freq: int = 3,
    dict_encode_all_strings: bool = False,
    dict_skip_if_shorter_than: int | None = 3,
) -> BestEncodeResult:
    """
    Encode a spreadsheet into a token-efficient text representation with optional
    dictionary compression, formatting markers, and chunking for retrieval.

    Parameters
    ----------
    sheet : Sheet
        Parsed spreadsheet object (e.g., from `from_csv` or `from_xlsx`).
    include_format : bool, default=True
        If True, preserves formatting metadata such as headers, cell markers, and anchors.
    compress_min_tokens : int, default=5000
        Minimum vanilla token length threshold before enabling dictionary compression.
        If the sheet text is shorter than this, compression may be skipped.
    max_tokens_per_chunk : int, default=4000
        Maximum size (in tokens) for each output chunk.
    overlap_tokens : int, default=200
        Number of tokens to overlap between consecutive chunks (to maintain continuity).
    use_anchors : bool, default=True
        Whether to insert `[ANCHOR]` markers for navigation and retrieval alignment.
    use_inverted_index : bool, default=True
        If True, build inverted index metadata for BM25-based retrieval.
    use_aggregation : bool, default=True
        If True, aggregate similar values (e.g., repeating survey answers) to reduce size.
    output_mode : {"compressed", "expanded", "auto"}, default="compressed"
        - "compressed": replaces repeated strings with dictionary codes (@C{X}tN).
        - "expanded": fully expanded plain text.
        - "auto": automatically pick the most efficient mode.
    dict_min_freq : int, default=3
        Minimum frequency of a string before considering it for dictionary compression.
    dict_encode_all_strings : bool, default=False
        If True, all strings are dictionary-encoded regardless of frequency.
    dict_skip_if_shorter_than : int or None, default=3
        Skip dictionary encoding for strings shorter than this many tokens.
        If None, encode all strings regardless of length.

    Returns
    -------
    BestEncodeResult
        A result object containing:
        - text (str): the full encoded representation of the spreadsheet.
        - kind (str): "compressed" or "expanded".
        - tokens_vanilla (int): token count without compression.
        - tokens_compressed (int | None): token count after compression.
        - chunks (List[dict]): list of {"id", "content"} chunks for retrieval.
        - meta (dict): extra metadata (dictionary mappings, anchors, etc.).

    Notes
    -----
    - Use `save_chunks_jsonl(result.chunks, path)` to persist the chunks for RAG.
    - Pair with `bm25_score` for efficient semantic retrieval over spreadsheet data.
    - Dictionary compression replaces repeated values with short codes
      and appends a `[DICT-BEGIN]…[DICT-END]` block at the end.
    """
    # 1) vanilla
    md = to_markdown(sheet, include_format=include_format)
    t_md = count_tokens(md)

    chosen_text = md
    kind = "vanilla"
    comp_meta: Dict = {}
    t_comp: Optional[int] = None

    # 2) compress if useful
    if t_md >= compress_min_tokens:
        enc = compress(
                md,
                budget_tokens=max_tokens_per_chunk,
                use_anchors=use_anchors,
                use_inverted_index=use_inverted_index,
                use_aggregation=use_aggregation,
                dict_min_freq=dict_min_freq,
                dict_encode_all_strings=dict_encode_all_strings,   
                dict_skip_if_shorter_than=dict_skip_if_shorter_than,
            )
        comp_text = enc["content"]
        t_comp = count_tokens(comp_text)
        if t_comp < t_md:
            chosen_text = comp_text
            kind = "compressed"
            comp_meta = enc.get("meta", {})

    mapping = parse_dict_block(chosen_text)
    if output_mode == "expanded" and mapping:
        chosen_text = expand_text_with_dict(chosen_text, mapping)
        kind = f"{kind}+expanded"
    elif output_mode == "auto" and mapping:
        expanded = expand_text_with_dict(chosen_text, mapping)
        if count_tokens(expanded) < count_tokens(chosen_text):
            chosen_text = expanded
            kind = f"{kind}+expanded"

    chunks = chunk_anchor_and_dict_safe(
        chosen_text,
        max_tokens=max_tokens_per_chunk,
        overlap_tokens=overlap_tokens,
        token_counter=count_tokens,
    )

    meta_out: Dict = {"compression_meta": comp_meta} if comp_meta else {}
    return BestEncodeResult(
        text=chosen_text,
        kind=kind,
        tokens_vanilla=t_md,
        tokens_compressed=t_comp,
        chunks=chunks,
        meta=meta_out,
    )