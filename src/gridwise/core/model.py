from dataclasses import dataclass
from typing import Any, Optional, List, Tuple

@dataclass(frozen= True)
class Cell:
    row: int
    col: int
    address: str
    value: Any
    dtype: str
    fmt: Optional[str] = None
    
    
@dataclass
class Sheet:
    name: str
    nrows: int
    ncols: int
    cells: List[Cell]
    merged_regions: Optional[List[Tuple[int, int, int, int]]] = None
    frozen: Optional[Tuple[int, int]] = None