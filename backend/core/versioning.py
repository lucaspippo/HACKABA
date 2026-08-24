from __future__ import annotations

import datetime
import json
import os


class VersionStore:
    """Snapshots inmutables del dato. Cada save crea una versión nueva;
    ninguna versión previa se modifica. Restore devuelve el snapshot tal cual."""

    def __init__(self, base_dir: str):
        self.dir = os.path.join(base_dir, "versions")
        os.makedirs(self.dir, exist_ok=True)
        self.index_path = os.path.join(self.dir, "index.json")

    def _index(self) -> list[dict]:
        if not os.path.exists(self.index_path):
            return []
        with open(self.index_path, encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: dict, motivo: str, autor: str = "sistema") -> dict:
        idx = self._index()
        version_id = (idx[-1]["id"] + 1) if idx else 1
        meta = {
            "id": version_id,
            "motivo": motivo,
            "autor": autor,
            "creado": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        with open(os.path.join(self.dir, f"v{version_id}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        idx.append(meta)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)
        return meta

    def list(self) -> list[dict]:
        return self._index()

    def restore(self, version_id: int) -> dict:
        path = os.path.join(self.dir, f"v{version_id}.json")
        if not os.path.exists(path):
            raise KeyError(f"Versión inexistente: {version_id}")
        with open(path, encoding="utf-8") as f:
            return json.load(f)
