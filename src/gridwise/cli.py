from __future__ import annotations
import argparse, sys
from pathlib import Path

from gridwise.io.loaders import from_csv, from_xlsx
from gridwise.encode.best import best_encode
from gridwise.store import save_chunks_jsonl, save_to_txt
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

    skip = None if args.dict_skip_if_shorter_than == 0 else args.dict_skip_if_shorter_than

    res = best_encode(
        sheet,
        include_format=True,
        compress_min_tokens=args.compress_min_tokens,
        max_tokens_per_chunk=args.max_tokens,
        overlap_tokens=args.overlap,
        use_anchors=not args.no_anchors,
        use_inverted_index=not args.no_inverted_index,
        output_mode=args.mode,  
        dict_encode_all_strings=not args.no_dict_encode_all,  
        dict_skip_if_shorter_than=skip,
    )

    if args.text:
        save_to_txt(args.text, res.text)
        print(f"Saved raw encoded text → {args.text}")

    # Save chunks as JSONL
    out_jsonl = args.store or (str(path.with_suffix("")) + ".gridwise.jsonl")
    save_chunks_jsonl(res.chunks, out_jsonl)
    print(f"Saved {len(res.chunks)} chunks → {out_jsonl}")

def main():
    p = argparse.ArgumentParser(prog="gridwise", description="GridWise CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    enc = sub.add_parser(
        "encode",
        help="Encode + chunk a spreadsheet in memory and save .jsonl (and optionally .txt)",
    )
    enc.add_argument("path", help="Path to .csv or .xlsx")
    enc.add_argument("--sheet", help="Worksheet name (for .xlsx)")
    enc.add_argument("--text", help="Also save raw encoded text to this file")
    enc.add_argument("--store", help="Output JSONL path (default: <file>.gridwise.jsonl)")
    enc.add_argument("--max-tokens", type=int, default=4000)
    enc.add_argument("--overlap", type=int, default=200)
    enc.add_argument("--compress-min-tokens", type=int, default=10_000)
    enc.add_argument("--no-anchors", action="store_true")
    enc.add_argument("--no-inverted-index", action="store_true")
    enc.add_argument("--use-aggregation", action="store_true")
    enc.add_argument("--mode", choices=["compressed", "expanded", "auto"], default="compressed")
    enc.add_argument("--dict-encode-all", action="store_true", help="Encode all quoted strings")
    enc.add_argument("--no-dict-encode-all", action="store_true",
                    help="Disable encoding all quoted strings (fallback to min-freq)")
    enc.add_argument("--dict-skip-if-shorter-than", type=int, default=0,
                 help="Skip strings shorter than N chars (0 = encode all)")


    enc.set_defaults(func=cmd_encode)

    # stream-encode
    se = sub.add_parser(
        "stream-encode",
        help="Stream a large CSV into JSONL chunks (two-pass, low memory)",
    )
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

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
