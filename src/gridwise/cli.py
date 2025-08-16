from __future__ import annotations
import argparse, sys
from pathlib import Path

from gridwise.io.loaders import from_csv, from_xlsx
from gridwise.encode.best import best_encode
from gridwise.store import (
    save_chunks_jsonl, build_inverted_index, save_index,
    load_chunks_jsonl, load_index, bm25_score
)
from gridwise.streaming.csv_stream import stream_encode_csv_to_jsonl

def cmd_encode(args):
    path = Path(args.path)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr); sys.exit(1)

    if path.suffix.lower() == ".csv":
        sheet = from_csv(str(path))
    elif path.suffix.lower() in (".xlsx", ".xls"):
        sheet = from_xlsx(str(path), sheet_name=args.sheet)
    else:
        print("Only .csv and .xlsx are supported", file=sys.stderr); sys.exit(2)

    res = best_encode(
        sheet,
        include_format=True,
        compress_min_tokens=args.compress_min_tokens,
        max_tokens_per_chunk=args.max_tokens,
        overlap_tokens=args.overlap,
        use_anchors=not args.no_anchors,
        use_inverted_index=not args.no_inverted_index,
        use_aggregation=args.use_aggregation,
        output_mode=args.mode,
    )

    out_jsonl = args.store or (str(path.with_suffix("")) + ".gridwise.jsonl")
    save_chunks_jsonl(res.chunks, out_jsonl)
    print(f"Saved {len(res.chunks)} chunks → {out_jsonl}")

    if args.index:
        idx_path = args.index if isinstance(args.index, str) else out_jsonl + ".pkl"
        index = build_inverted_index(res.chunks)
        save_index(index, idx_path)
        print(f"Saved index → {idx_path}")

def cmd_stream_encode(args):
    jsonl_path, _ = stream_encode_csv_to_jsonl(
        args.path,
        out_jsonl=args.store,
        usecols=(args.usecols.split(",") if args.usecols else None),
        chunksize=args.chunksize,
        max_tokens_per_chunk=args.max_tokens,
        overlap_tokens=args.overlap,
        build_dictionary=(not args.no_dictionary),
        min_freq=args.min_freq,
        include_format=True,
        sheet_name=args.sheet,
        output_mode=args.mode,
    )
    print(f"Saved chunks → {jsonl_path}")

    if args.index:
        chunks = load_chunks_jsonl(jsonl_path)
        index_path = args.index if isinstance(args.index, str) else jsonl_path + ".pkl"
        save_index(build_inverted_index(chunks), index_path)
        print(f"Saved index → {index_path}")

def cmd_query(args):
    chunks = load_chunks_jsonl(args.store)
    idx_path = args.index or (args.store + ".pkl")
    index = load_index(idx_path)

    results = bm25_score(args.question, chunks, index, topk=args.topk)
    print(f"# Retrieved top-{args.topk} chunks for: {args.question!r}\n")
    for i, r in enumerate(results, 1):
        print(f"=== Hit {i} | chunk {r['id']} | score={r['score']:.3f} ===")
        print(r["content"])
        print()
    if args.concat_out:
        with open(args.concat_out, "w", encoding="utf-8") as f:
            for r in results:
                f.write(f"### CHUNK {r['id']}\n{r['content']}\n\n")
        print(f"Concatenated {len(results)} chunks → {args.concat_out}")

def main():
    p = argparse.ArgumentParser(prog="gridwise", description="GridWise CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    enc = sub.add_parser("encode", help="Encode + chunk a spreadsheet (in-memory) and store JSONL; optional index")
    enc.add_argument("path", help="Path to .csv or .xlsx")
    enc.add_argument("--sheet", help="Worksheet name (for .xlsx)")
    enc.add_argument("--store", help="Output JSONL path (default: <file>.gridwise.jsonl)")
    enc.add_argument("--index", nargs="?", const=True, help="Also build & save index (optional path or default <store>.pkl)")
    enc.add_argument("--max-tokens", type=int, default=4000)
    enc.add_argument("--overlap", type=int, default=200)
    enc.add_argument("--compress-min-tokens", type=int, default=10_000)
    enc.add_argument("--no-anchors", action="store_true")
    enc.add_argument("--no-inverted-index", action="store_true")
    enc.add_argument("--use-aggregation", action="store_true")
    enc.add_argument("--research", action="store_true", help="Enable research preset (aggregation on)")
    enc.add_argument("--mode", choices=["compressed", "expanded", "auto"], default="compressed")
    enc.set_defaults(func=cmd_encode)

    se = sub.add_parser("stream-encode", help="Stream a large CSV into JSONL chunks (two-pass, low memory)")
    se.add_argument("path", help="Path to .csv")
    se.add_argument("--store", help="Output JSONL path (default: <file>.gridwise.jsonl)")
    se.add_argument("--sheet", help="Sheet name for metadata/title")
    se.add_argument("--usecols", help="Comma-separated columns to include (e.g., Date,Region,Sales)")
    se.add_argument("--chunksize", type=int, default=100_000)
    se.add_argument("--max-tokens", type=int, default=4_000)
    se.add_argument("--overlap", type=int, default=200)
    se.add_argument("--no-dictionary", action="store_true")
    se.add_argument("--min-freq", type=int, default=3)
    se.add_argument("--mode", choices=["compressed", "expanded"], default="compressed")
    se.add_argument("--index", nargs="?", const=True, help="Also build index (optional path or default <store>.pkl)")
    se.set_defaults(func=cmd_stream_encode)

    qry = sub.add_parser("query", help="Query stored JSONL with BM25-like retrieval")
    qry.add_argument("store", help="Path to JSONL produced by 'gridwise encode' or 'stream-encode'")
    qry.add_argument("question", help="Natural language query")
    qry.add_argument("--index", help="Path to index .pkl (default: <store>.pkl)")
    qry.add_argument("--topk", type=int, default=5)
    qry.add_argument("--concat-out", help="Write concatenated hits to this file")
    qry.set_defaults(func=cmd_query)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
