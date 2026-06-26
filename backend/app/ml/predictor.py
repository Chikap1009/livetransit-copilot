"""Load the trained LightGBM model and predict arrival delays (inference only).

Uses lightgbm.Booster + numpy (NOT pandas) so the API image stays lean. The feature
order here must match training (see features.FEATURES).
"""
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np

MODEL_DIR = Path("models")
# Must match backend.app.ml.features.FEATURES order.
FEATURE_ORDER = ["current_delay", "hour", "dow", "stop_sequence", "route_id"]

_model: lgb.Booster | None = None
_route_code: dict[str, int] = {}
_meta: dict = {}


def load() -> dict:
    """Load the model + metadata at startup. Returns meta (for the accuracy panel)."""
    global _model, _route_code, _meta
    _model = lgb.Booster(model_file=str(MODEL_DIR / "eta_model.txt"))
    _meta = json.loads((MODEL_DIR / "meta.json").read_text())
    _route_code = {route: i for i, route in enumerate(_meta["route_categories"])}
    return _meta


def is_loaded() -> bool:
    return _model is not None


def meta() -> dict:
    return _meta


def predict_delays(rows: list[dict]) -> list[float]:
    """rows: dicts w/ current_delay, hour, dow, stop_sequence, route_id -> predicted delay (s)."""
    if not rows or _model is None:
        return []
    X = np.array(
        [
            [
                r["current_delay"], r["hour"], r["dow"], r["stop_sequence"],
                _route_code.get(r["route_id"], -1),  # unknown route -> -1
            ]
            for r in rows
        ],
        dtype=float,
    )
    return _model.predict(X).tolist()
