# gridwise/encode/compressor/encode.py
from .anchors import apply_anchors
from .invert_index import apply_inverted_index
from .aggregate import apply_aggregation
from .dict_rebuild import force_rebuild_dict_block

def encode(
    text: str,
    *,
    use_anchors: bool = True,
    use_inverted_index: bool = True,
    use_aggregation: bool = True,
    budget_tokens: int = 8192,
    dict_min_freq: int = 3,
    dict_encode_all_strings: bool = True,
    dict_skip_if_shorter_than: int | None = 3, 
):
    content = text
    meta: dict = {}

    if use_anchors:
        content, m = apply_anchors(content)
        meta["anchors"] = m

    rev_dicts = {}
    if use_inverted_index:
        content, m = apply_inverted_index(
            content,
            min_freq=dict_min_freq,
            encode_all_strings=dict_encode_all_strings,
            skip_if_shorter_than=dict_skip_if_shorter_than,
        )
        meta["dictionary"] = {k: v for k,v in m.items() if k != "rev_dicts"}
        rev_dicts = m["rev_dicts"]

    if use_aggregation:
        content, m = apply_aggregation(content)
        meta["aggregation"] = m

    content = force_rebuild_dict_block(content, rev_dicts)

    return {"kind": "compressed", "content": content, "meta": meta, "budget": budget_tokens}
