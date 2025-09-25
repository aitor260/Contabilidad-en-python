# libro_diario/services.py
from dataclasses import dataclass
from datetime import date
from typing import Protocol, Iterable, Dict, Any, List

@dataclass
class Entry:
    fecha: date
    concepto: str
    debe: float
    haber: float

class Storage(Protocol):
    def load(self) -> Iterable[Dict[str, Any]]: ...
    def save_all(self, rows: Iterable[Dict[str, Any]]) -> None: ...

def serialize(e: Entry) -> Dict[str, Any]:
    return {
        "fecha": e.fecha.isoformat(),
        "concepto": e.concepto,
        "debe": float(e.debe),
        "haber": float(e.haber)
    }

def deserialize(row: Dict[str,Any]) -> Entry:
    return Entry(
        fecha = date.fromisoformat(row["fecha"]),
        concepto = row["concepto"],
        debe = float(row["debe"]),
        haber = float(row["haber"])
    )

def add_entry(storage: Storage, e: Entry) -> None:
    rows = list(storage.load())
    rows.append(serialize(e))
    storage.save_all(rows)

def list_entries(storage: Storage) -> List[Entry]:
    return [deserialize(r) for r in storage.load()]