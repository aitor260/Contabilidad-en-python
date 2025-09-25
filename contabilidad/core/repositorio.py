# libro_diario/storage.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable, Dict, Any

class JsonStorage:
    """
    Persistencia simple en un fichero JSON.
    Almacena la cuentas disponibles.
    """
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")
    
    def load(self) -> Iterable[Dict[str, Any]]:
        return json.loads(self.path.read_text(encoding="utf-8"))
    
    def save_all(self, rows: Iterable[Dict[str, Any]]) -> None:
        data = list(rows)
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )