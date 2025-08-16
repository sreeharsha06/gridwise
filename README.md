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
- 🔢 Token counting for **vanilla vs compressed**
- ⚡ Compatible with **RAG pipelines** out-of-the-box  

---

## 📦 Install
```bash
# Local dev
pip install -e ".[tokens]"

# For contributors
pip install -e ".[dev]"
````

## 🔍 End-to-End Example (Encoding + Indexing + Query)

```python
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

save_to_txt("encoded_output.txt", res_c.text)

# 4. Query
Use the saved files as input to your RAG pipeline or LLM for queries.
```