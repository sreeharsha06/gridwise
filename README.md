# GridWise

**GridWise — Efficient spreadsheet encoders for LLMs (inspired by [SpreadsheetLLM](https://arxiv.org/abs/2407.09025)).**  

[![CI](https://github.com/sreeharsha06/gridwise/actions/workflows/ci.yml/badge.svg)](https://github.com/sreeharsha06/gridwise/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

Turn spreadsheets into **LLM-friendly text**: compress, chunk, and retrieve with minimal tokens.

---

## ✨ Features
- 📥 Load `.csv`, `.xlsx` into a structured **Sheet** object  
- 📝 **Vanilla encoder** (Markdown-like) with explicit cell addresses  
- 🔒 **Compression strategies**  
  - Anchors (replace repeated headers)  
  - Inverted dictionary (replace repeated strings)  
  - Aggregation (merge values into compact form)  
- 📦 **Chunking** to fit LLM context window limits  
- 🔢 Token counting for **vanilla vs compressed** encodings  
- 🔍 Built-in **BM25 retrieval** for natural language queries  
- 🛠️ **Streaming CSV encoder** (low-memory, handles 100MB+ files)  
- ⚡ Compatible with **RAG pipelines** out-of-the-box  

---

## 📦 Install
```bash
# Local dev
pip install -e ".[tokens]"

# For contributors
pip install -e ".[dev]"



Quickstart (Python)

Encode a spreadsheet and get token-efficient text:

from gridwise.io.loaders import from_csv
from gridwise.encode.best import best_encode

# Load CSV → Sheet
sheet = from_csv("my_dataset.csv")

# Encode sheet with compression
res = best_encode(sheet, output_mode="compressed")

print("Compressed tokens:", res.tokens_compressed, "vs vanilla:", res.tokens_vanilla)

# Save encoded text
with open("encoded_output.txt", "w", encoding="utf-8") as f:
    f.write(res.text)

🔍 End-to-End Example (Encoding + Indexing + Query)
from gridwise.io.loaders import from_csv
from gridwise.encode.best import best_encode
from gridwise.store import (
    save_chunks_jsonl, build_inverted_index, save_index,
    load_chunks_jsonl, load_index, bm25_score
)

# 1. Load
sheet = from_csv("Hearing_wellbeing_Survey_Report.csv")

# 2. Encode
res_c = best_encode(
    sheet,
    output_mode="compressed",
    dict_encode_all_strings=True,
    dict_skip_if_shorter_than=None,
)

print("Compressed tokens:", res_c.tokens_compressed, "vs vanilla:", res_c.tokens_vanilla)

# 3. Save chunks
jsonl_path = "encoded_output.gridwise.jsonl"
save_chunks_jsonl(res_c.chunks, jsonl_path)

# 4. Build & save index
index = build_inverted_index(res_c.chunks)
save_index(index, "encoded_output.index.pkl")

# 5. Query
chunks = load_chunks_jsonl(jsonl_path)
index = load_index("encoded_output.index.pkl")

results = bm25_score("What do people say about hearing tests?", chunks, index, topk=3)
for r in results:
    print(f"Hit {r['id']} | score={r['score']:.3f}")
    print(r["content"][:200], "...\n")