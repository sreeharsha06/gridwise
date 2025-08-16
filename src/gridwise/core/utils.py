import math

def idx_to_addr(row: int, col: int) -> str:

    def col_to_name(c: int) -> str:
        res = ""; c += 1
        while c > 0:
            c, rem = divmod(c - 1, 26)
            res = chr(65 + rem) + res
        return res
    return f"{col_to_name(col)}{row+1}"

def infer_dtype(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "empty"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str) and any(ch in value for ch in ("-", "/", ":")) and any(ch.isdigit() for ch in value):
        return "date" if len(value) <= 25 else "text"
    return "text"
