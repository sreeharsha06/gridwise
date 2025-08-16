import math

def idx_to_addr(row: int, col: int) -> str:
    
    """
    Convert a zero-based (row, col) index into an Excel-style cell address.

    Parameters
    ----------
    row : int
        Zero-based row index (0 = first row).
    col : int
        Zero-based column index (0 = column 'A').

    Returns
    -------
    str
        Cell address in "A1" notation, e.g. (0, 0) -> "A1", (4, 27) -> "AB5".

    Examples
    --------
    >>> idx_to_addr(0, 0)
    'A1'
    >>> idx_to_addr(4, 27)
    'AB5'
    """

    def col_to_name(c: int) -> str:
        res = ""; c += 1
        while c > 0:
            c, rem = divmod(c - 1, 26)
            res = chr(65 + rem) + res
        return res
    return f"{col_to_name(col)}{row+1}"

def infer_dtype(value) -> str:
    """
    Infer a coarse data type label for a spreadsheet cell value.

    Parameters
    ----------
    value : Any
        Cell value to classify (may be None, number, string, etc.).

    Returns
    -------
    str
        One of:
        - "empty" : None or NaN
        - "bool"  : Boolean values
        - "number": Integers or floats
        - "date"  : Strings containing digits and date-like symbols
        - "text"  : All other strings

    Notes
    -----
    - Strings are labeled as "date" if they contain both digits and 
      characters like '-', '/', ':' and are reasonably short (<= 25 chars).
    - Longer strings with such characters are treated as free text.

    Examples
    --------
    >>> infer_dtype(None)
    'empty'
    >>> infer_dtype(3.14)
    'number'
    >>> infer_dtype(True)
    'bool'
    >>> infer_dtype("2024-07-15")
    'date'
    >>> infer_dtype("Meeting notes: July 15, 2024")
    'text'
    """
    
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "empty"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str) and any(ch in value for ch in ("-", "/", ":")) and any(ch.isdigit() for ch in value):
        return "date" if len(value) <= 25 else "text"
    return "text"
