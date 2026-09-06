#!/usr/bin/env python3
"""26229存档对比 + 26230视角复现(P5)
场景1: 26229存档预测 vs 26229实际开奖 28054
场景2: 26229视角(数据截至26228) 用当前V1.63.0预测26230 vs 实际 94683
"""
import sys, os, io, contextlib, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import openpyxl, tempfile
import pandas as pd
from p5_fusion_complete import Pick5FusionComplete, VERSION

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', 'assets', 'data', '排列5历史数据.xlsx')
wb = openpyxl.load_workbook(DATA, read_only=True)
rows = list(wb.active.iter_rows(values_only=True))
print(f"[dbg] P5数据{len(rows)-1}期(至{rows[-1][0]}), 版本={VERSION}")


def make_model(until_period):
    draws = []
    periods = []
    for r in rows[1:]:
        if int(r[0]) > until_period:
            break
        draws.append(tuple(int(r[i]) for i in range(1, 6)))
        periods.append(int(r[0]))
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    pd.DataFrame(draws, columns=['万位', '千位', '百位', '十位', '个位']).assign(
        期号=periods).to_excel(tmp.name, index=False, engine='openpyxl')
    return Pick5FusionComplete(data_path=tmp.name, auto_update=False), tmp.name


def hits(preds, actual):
    """位置命中统计: 返回每位置命中数 + 最佳单注命中位置数"""
    pos_hits = [0] * 5
    best = 0
    for b in preds:
        d = b['digits']
        n = sum(1 for i in range(5) if d[i] == actual[i])
        best = max(best, n)
        for i in range(5):
            if d[i] == actual[i]:
                pos_hits[i] += 1
    return pos_hits, best


# ===== 场景1: 26229存档 =====
store = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', 'memory', 'p5_predictions.json')))
preds26229 = None
for p in store['predictions']:
    if p['period'] == '26229':
        preds26229 = p['bets']
actual26229 = (2, 8, 0, 5, 4)
ph, best = hits(preds26229, actual26229)
print(f"\n[S1] 26229存档预测 vs 实际{actual26229}")
print(f"  位置命中: 万{ph[0]}/千{ph[1]}/百{ph[2]}/十{ph[3]}/个{ph[4]} = {sum(ph)}/50, 最佳单注{best}/5")
for b in preds26229[:10]:
    d = b['digits']
    n = sum(1 for i in range(5) if d[i] == actual26229[i])
    print(f"  {d} 命中{n} {'<==' if n>=2 else ''}")

# ===== 场景2: 26229视角预测26230 =====
actual26230 = (9, 4, 6, 8, 3)
model, tmp = make_model(26229)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    r = model.predict(top_n=25)
log = buf.getvalue()
bets = r.get('bets') or r.get('zx_bets') or []
print(f"\n[S2] 26229视角(数据截至26228) 预测26230 vs 实际{actual26230}")
print(f"  预测Top10:")
for i, b in enumerate(bets[:10]):
    d = b['digits']
    n = sum(1 for j in range(5) if d[j] == actual26230[j])
    print(f"  {i+1}. {d} 命中{n} {'<==' if n>=2 else ''}")
ph2, best2 = hits(bets[:10], actual26230)
print(f"  位置命中: 万{ph2[0]}/千{ph2[1]}/百{ph2[2]}/十{ph2[3]}/个{ph2[4]} = {sum(ph2)}/50, 最佳单注{best2}/5")
# 复式
cb = r.get('compound_bets')
if cb:
    print(f"  复式: {str(cb)[:400]}")
os.unlink(tmp)
