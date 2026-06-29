#!/usr/bin/env python3
"""排列5 预测结果存储模块"""
import json, os
from pathlib import Path

STORE_PATH = Path(__file__).resolve().parent.parent / 'memory' / 'p5_predictions.json'

def _ensure():
    os.makedirs(STORE_PATH.parent, exist_ok=True)
    if not STORE_PATH.exists():
        with open(STORE_PATH, 'w') as f:
            json.dump({"predictions": []}, f)

def load_prediction(period):
    _ensure()
    try:
        with open(STORE_PATH) as f:
            data = json.load(f)
        for p in data.get("predictions", []):
            if p.get("period") == period:
                return p
    except Exception:
        pass
    return None

def store_prediction(period, bets):
    _ensure()
    try:
        with open(STORE_PATH) as f:
            data = json.load(f)
    except Exception:
        data = {"predictions": []}
    data["predictions"] = [p for p in data.get("predictions", []) if p.get("period") != period]
    data["predictions"].append({"period": period, "bets": bets[:10]})
    data["predictions"] = data["predictions"][-2:]  # keep last 2
    with open(STORE_PATH, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
