from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Step:
    action: str
    template: Optional[str] = None
    timeout: int = 10
    threshold: float = 0.82
    text: Optional[str] = None
    key: Optional[str] = None
    keys: Optional[List[str]] = field(default_factory=list)
    clicks: int = 1
    dx: int = 0
    dy: int = 0
    duration: float = 0.5
    seconds: float = 1.0
    amount: int = 0
    move_anchor_template: Optional[str] = None
    target_template: Optional[str] = None
    max_scrolls: int = 10
    scroll_amount: int = 500
    note: str = ""