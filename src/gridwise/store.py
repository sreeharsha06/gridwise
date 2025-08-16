from __future__ import annotations
import json, math, re, pickle
from pathlib import Path
from typing import List, Dict
from collections import Counter

# keep codes whole + unicode words
_CODE_RE = re.compile(r"@C\{[A-Z]+\}t\d+")
_WORD_RE = re.compile(r"\w+", re.UNICODE)

def _tokenize(text: str) -> List[str]:
    tokens = []
    # preserve dictionary codes as single tokens
    tokens.extend(m.group(0).lower() for m in _CODE_RE.finditer(text))
    # add regular words
    tokens.extend(t.lower() for t in _WORD_RE.findall(text))
    return tokens

def save_chunks_jsonl(chunks: List[Dict], out_path: str) -> None:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps({"id": ch["id"], "content": ch["content"]}, ensure_ascii=False) + "\n")

def load_chunks_jsonl(path: str) -> List[Dict]:
    chunks: List[Dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            # basic schema assert
            if "id" in obj and "content" in obj:
                chunks.append({"id": obj["id"], "content": obj["content"]})
    return chunks

def build_inverted_index(chunks: List[Dict]) -> Dict:
    df: Dict[str, int] = {}
    postings: Dict[str, Dict[int, int]] = {}
    for ch in chunks:
        doc_id = ch["id"]            # do not force int; keep whatever id you used
        terms = _tokenize(ch["content"])
        tf_local = Counter(terms)
        for t, tf in tf_local.items():
            postings.setdefault(t, {})[doc_id] = tf
            df[t] = df.get(t, 0) + 1
    return {"df": df, "N": len(chunks), "postings": postings}

def save_index(index: Dict, path: str) -> None:
    with open(path, "wb") as f:
        pickle.dump(index, f)

def load_index(path: str) -> Dict:
    with open(path, "rb") as f:
        return pickle.load(f)

def bm25_score(query: str, chunks: List[Dict], index: Dict, k1: float = 1.5, b: float = 0.75, topk: int = 5) -> List[Dict]:
    if not query.strip():
        return []

    N = index["N"]
    df = index["df"]
    postings = index["postings"]

    # document lengths (sum tf per doc)
    doc_len: Dict[int, int] = {}
    for plist in postings.values():
        for doc_id, tf in plist.items():
            doc_len[doc_id] = doc_len.get(doc_id, 0) + tf
    avgdl = (sum(doc_len.values()) / len(doc_len)) if doc_len else 1.0

    q_terms = _tokenize(query)
    scores: Dict[int, float] = {}
    for t in q_terms:
        ft = df.get(t)
        if not ft:
            continue
        idf = math.log(1 + (N - ft + 0.5) / (ft + 0.5))
        for doc_id, tf in postings[t].items():
            dl = doc_len.get(doc_id, 1)
            denom = tf + k1 * (1 - b + b * (dl / avgdl))
            s = idf * (tf * (k1 + 1)) / denom
            scores[doc_id] = scores.get(doc_id, 0.0) + s

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:topk]
    by_id = {ch["id"]: ch for ch in chunks}
    return [{"id": did, "score": sc, "content": by_id[did]["content"]} for did, sc in ranked if did in by_id]
