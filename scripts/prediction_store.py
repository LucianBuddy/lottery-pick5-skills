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
    # 【V1.60.0】按期号排序再截断: 原append顺序在重存(如26215传导后重跑)
    # 时破坏期号顺序(26214,26215,26211,26213,26216乱序), 且[-50:]按写入
    # 顺序截断会保留旧期号而非最近50期. 排序后截断=期号最近50期
    data["predictions"].sort(key=lambda x: int(x.get("period", 0)))
    data["predictions"] = data["predictions"][-50:]  # 保留最近50期供复盘
    with open(STORE_PATH, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
