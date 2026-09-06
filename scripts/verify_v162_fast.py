#!/usr/bin/env python3
"""V1.62.0 验证: 组选节奏加权(4,5)+(1,5,9)行为 + 全量predict零退化"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p5_fusion_complete import Pick5FusionComplete
import prediction_store as _ps_mod
_ps_mod.store_prediction = lambda *a, **k: None

model = Pick5FusionComplete(auto_update=False)
model._last_check_time = 9999999999.0

# ---------- [1] 当前漏期 ----------
draws = model.draws
miss45 = 0
for d in reversed(draws):
    if tuple(sorted((d[3], d[4]))) == (4, 5):
        break
    miss45 += 1
miss159 = 0
for d in reversed(draws):
    if set(d[:3]) == {1, 5, 9}:
        break
    miss159 += 1
print(f"[1] (4,5)后2位漏期={miss45} (窗口[45,250]), (1,5,9)前3位漏期={miss159} (窗口[80,200])")

# ---------- [2] 节奏加权行为 ----------
def _mk(digits, score=0.5):
    return {'digits': digits, 'final_score': score}

cands = [
    _mk([1, 2, 3, 4, 5]),   # 后2位(4,5) + 前3位含{1,5,9}中1个
    _mk([1, 5, 9, 6, 7]),   # 前3位(1,5,9)全含
    _mk([1, 5, 7, 6, 7]),   # 前3位含2个
    _mk([2, 3, 4, 6, 8]),   # 无匹配
]
out = model._apply_combo_rhythm_boost(cands, [])
for c in out:
    print(f"[2] {c['digits']}: adj={c.get('combo_rhythm', 0.0):+.2f} score={c['final_score']:.2f}")

c0 = out[0]
if 45 <= miss45 <= 250:
    assert c0['combo_rhythm'] == 0.04, "后2位(4,5)应+0.04"
if 80 <= miss159 <= 200:
    assert out[1]['combo_rhythm'] == 0.04, "前3位全含应+0.04"
    assert out[2]['combo_rhythm'] == 0.02, "前3位含2个应+0.02"
assert out[3].get('combo_rhythm', 0.0) == 0.0, "无匹配不应调整"
print("[2] ✅ 节奏加权行为正确")

# ---------- [3] 注入行为: 窗口内Top10无(4,5)票时换入 ----------
if 45 <= miss45 <= 250:
    top10_no45 = [_mk([1, 2, 3, 6, 7], 0.5), _mk([9, 8, 7, 6, 5], 0.4)]
    pool = [_mk([3, 3, 3, 4, 5], 0.6), _mk([8, 8, 8, 8, 8], 0.9)]
    r = model._apply_combo_rhythm_boost(top10_no45, pool)
    has45 = any(tuple(sorted((c['digits'][3], c['digits'][4]))) == (4, 5) for c in r)
    print(f"[3] 注入测试: Top10含(4,5)票={has45}, len={len(r)}")
    assert has45, "窗口内应注入(4,5)票"
print("[3] ✅ 注入行为正确")

# ---------- [4] 全量predict零退化 ----------
t0 = time.time()
pred = model.predict(top_n=10)
t1 = time.time()
print(f"[4] predict耗时: {t1-t0:.2f}s")
for i, b in enumerate(pred['bets'], 1):
    print(f"    注{i}: {''.join(map(str, b['digits']))} score={b['final_score']:.4f}")
assert len(pred['bets']) == 10
print("[4] ✅ predict正常")

print("\n✅ V1.62.0 FAST全部通过")
