"""既読履歴（state.json）の読み書き。"""
from __future__ import annotations

import json
import os
from typing import Any

DEFAULT_STATE: dict[str, Any] = {"version": 1, "companies": {}}


def load_state(path: str) -> dict[str, Any]:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(json.dumps(DEFAULT_STATE))  # deep copy


def save_state(path: str, state: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
