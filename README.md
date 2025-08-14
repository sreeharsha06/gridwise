# GridWise

**GridWise — Efficient spreadsheet encoders for LLMs (SpreadsheetLLM-inspired).**

[![CI](https://github.com/sreeharsha06/gridwise/actions/workflows/ci.yml/badge.svg)](https://github.com/sreeharsha06/gridwise/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

<!--:
[![PyPI version](https://img.shields.io/pypi/v/gridwise.svg)](https://pypi.org/project/gridwise/)
-->

Turn spreadsheets into **LLM-friendly text**, apply **compression**, and **chunk** into token-bounded slices you can pass directly to any LLM.

## Features
- Load `.csv`, `.xlsx` → structured in-memory model
- **Vanilla encoder** (Markdown-like) with cell addresses
- Modular **compression**: anchors, inverted index, aggregation
- **Chunking** to fit model context limits
- Token counting & basic compression metrics

## Install
```bash
pip install -e ".[tokens]"   # local dev; add [dev] for contributors
