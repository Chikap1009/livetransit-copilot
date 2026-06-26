"""Train the LightGBM arrival-delay predictor and compare against baselines.

Time-based split (never random) to avoid leakage. Saves the model + metadata to
models/ (git-ignored; in production this goes to R2, not the repo).

CLI:  .venv\\Scripts\\python.exe -m backend.app.ml.train
"""
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
from sklearn.metrics import mean_absolute_error

from backend.app.ml.features import FEATURES, TARGET, build_dataset

MODEL_DIR = Path("models")
SPLIT_FRACTION = 0.8


def main() -> None:
    df = build_dataset().reset_index(drop=True)
    split = int(len(df) * SPLIT_FRACTION)  # df is time-ordered -> this is a time split
    train, test = df.iloc[:split], df.iloc[split:]
    print(f"train={len(train):,}  test={len(test):,}  "
          f"(split at {df['scheduled_ts'].iloc[split]})")

    y = test[TARGET].to_numpy()

    # --- Baselines ---
    mae_schedule = mean_absolute_error(y, np.zeros_like(y))                 # assume on-time
    route_mean = train.groupby("route_id", observed=True)[TARGET].mean()
    hist = test["route_id"].map(route_mean).fillna(train[TARGET].mean()).to_numpy()
    mae_hist = mean_absolute_error(y, hist)
    mae_persist = mean_absolute_error(y, test["current_delay"].to_numpy())  # next = current

    # --- Model ---
    cats = list(train["route_id"].cat.categories)
    Xtr = train[FEATURES].copy()
    Xte = test[FEATURES].copy()
    Xtr["route_id"] = Xtr["route_id"].cat.codes
    Xte["route_id"] = (
        Xte["route_id"].astype("category").cat.set_categories(cats).cat.codes
    )
    model = lgb.LGBMRegressor(
        n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=50, verbose=-1
    )
    model.fit(Xtr, train[TARGET], categorical_feature=["route_id"])
    mae_model = mean_absolute_error(y, model.predict(Xte))

    print("\nMAE (seconds) on the held-out (later) period:")
    print(f"  baseline  schedule (on-time)   : {mae_schedule:7.1f}")
    print(f"  baseline  historical avg/route : {mae_hist:7.1f}")
    print(f"  baseline  persistence          : {mae_persist:7.1f}")
    print(f"  MODEL     LightGBM             : {mae_model:7.1f}")
    print(f"\n  vs schedule : {100*(1-mae_model/mae_schedule):.1f}% better")
    print(f"  vs persist. : {100*(1-mae_model/mae_persist):.1f}% better")

    MODEL_DIR.mkdir(exist_ok=True)
    model.booster_.save_model(str(MODEL_DIR / "eta_model.txt"))
    (MODEL_DIR / "meta.json").write_text(json.dumps({
        "features": FEATURES,
        "route_categories": cats,
        "mae_model_s": round(mae_model, 1),
        "mae_schedule_s": round(mae_schedule, 1),
        "mae_persistence_s": round(mae_persist, 1),
    }, indent=2))
    print(f"\nsaved model -> {MODEL_DIR/'eta_model.txt'}")


if __name__ == "__main__":
    main()
