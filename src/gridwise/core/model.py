from dataclasses import dataclass
from typing import Any, Optional, List, Tuple, Dict

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
    
    

@dataclass
class BestEncodeResult:
    """
    Result of best_encode():
      - text: the final serialized sheet text chosen (vanilla or compressed, possibly expanded)
      - kind: "vanilla" or "compressed" (with optional "+expanded" suffix if expansion won)
      - tokens_vanilla: token count of the vanilla serialization (for reference)
      - tokens_compressed: token count of the compressed serialization if computed; otherwise None
      - chunks: list of {"id": int, "content": str} windows suitable to send to an LLM
      - meta: optional stage metadata (e.g., anchors/dictionary/aggregation details)
    """
    text: str
    kind: str
    tokens_vanilla: int
    tokens_compressed: Optional[int]
    chunks: List[Dict]
    meta: Dict