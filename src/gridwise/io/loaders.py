from __future__ import annotations
import pandas as pd
from typing import List
from gridwise.core.model import Sheet, Cell
from gridwise.core.utils import idx_to_addr, infer_dtype

def from_dataframe(df: pd.DataFrame, name: str = "Sheet1") -> Sheet:
    cells: List[Cell] = []
    df_reset = df.reset_index(drop=True)
    df_reset.columns = [str(c) for c in df_reset.columns]
    nrows, ncols = df_reset.shape
    # header
    for j, col in enumerate(df_reset.columns):
        addr = idx_to_addr(0, j)
        cells.append(Cell(row=0, col=j, address=addr, value=col, dtype="text", fmt="header"))
    # data
    for i in range(nrows):
        for j in range(ncols):
            val = df_reset.iat[i, j]
            addr = idx_to_addr(i + 1, j)
            cells.append(Cell(row=i + 1, col=j, address=addr, value=val, dtype=infer_dtype(val)))
    return Sheet(name=name, nrows=nrows + 1, ncols=ncols, cells=cells)

def from_csv(path: str, name: str | None = None, **read_csv_kwargs) -> Sheet:
    df = pd.read_csv(path, **read_csv_kwargs)
    return from_dataframe(df, name=name or (path.split("/")[-1].split(".")[0]))

def from_xlsx(path: str, sheet_name: str | None = None) -> Sheet:
    df = pd.read_excel(path, sheet_name=sheet_name or 0, engine="openpyxl")
    name = sheet_name if isinstance(sheet_name, str) else "Sheet1"
    return from_dataframe(df, name=name)
