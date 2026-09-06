#!/usr/bin/env python3
"""
V1.50.0 验证脚本: 26205期模拟预测 (数据截断到26204, 预测26205)
校验机制性质(非单期运气):
  1. Top10恰好10注
  2. 反垄断: 每位置每数字≤2席
  3. 优先级分层: 每位置覆盖≥1个近端(0-2期)和≥1个短间隔(3-8期)数字(若存在)
  4. 确定性: 固定种子下两次运行结果一致
同时报告对实际开奖 8 0 6 0 8 的覆盖情况(信息性)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from p5_fusion_complete import Pick5FusionComplete, VERSION
from pathlib import Path

actual = [8, 0, 6, 0, 8]
names = ['万', '千', '百', '十', '个']

def run_once():
    fusion = Pick5FusionComplete(auto_update=False)
    assert list(fusion.draws[-1]) == actual, f"最新期应为26205={actual}, 实际{list(fusion.draws[-1])}"
    fusion.draws = fusion.draws[:-1]
    fusion.last_period = '26204'
    fusion.prev_draw = list(fusion.draws[-1])
    return fusion.predict()['bets']

bets = run_once()
print(f"[Verify] 版本={VERSION}")

print("\nTop10:")
for i, b in enumerate(bets, 1):
    print(f"  {i:2d}. {''.join(map(str, b['digits']))}  score={b.get('final_score', 0):.4f}")

# 遗漏表(用于tier判定)
fusion = Pick5FusionComplete(auto_update=False)
fusion.draws = fusion.draws[:-1]
_miss = [{}, {}, {}, {}, {}]
for _pos in range(5):
    _seq = [d[_pos] for d in fusion.draws[-200:]]
    for _d in range(10):
        for _i in range(len(_seq) - 1, -1, -1):
            if _seq[_i] == _d:
                _miss[_pos][_d] = len(_seq) - 1 - _i
                break
        if _d not in _miss[_pos]:
            _miss[_pos][_d] = len(_seq)

def tier(pos, d):
    m = _miss[pos].get(d, 99)
    if m <= 2:
        return 0
    if m <= 8:
        return 1
    if m <= 9:
        return 2
    return 3

ok = True

# 1. 恰好10注
n = len(bets)
print(f"\n[1] Top10注数: {n}", "✅" if n == 10 else "❌")
ok = ok and n == 10

# 2. 反垄断
mono_ok = True
for pos in range(5):
    cnt = {}
    for b in bets:
        cnt[b['digits'][pos]] = cnt.get(b['digits'][pos], 0) + 1
    for d, c in cnt.items():
        if c > 2:
            mono_ok = False
            print(f"  ❌ {names[pos]}位{d}占{c}席 (>2)")
print(f"[2] 反垄断(每位置每数字≤2席):", "✅" if mono_ok else "❌")
ok = ok and mono_ok

# 3. 优先级分层覆盖
tier_ok = True
for pos in range(5):
    for t_need, tname in ((0, '近端0-2'), (1, '短间隔3-8')):
        exists = any(tier(pos, d) == t_need for d in range(10))
        if not exists:
            continue
        covered = any(tier(pos, b['digits'][pos]) == t_need for b in bets)
        if not covered:
            tier_ok = False
            print(f"  ❌ {names[pos]}位缺tier{t_need}({tname})覆盖")
print(f"[3] 优先级分层(每位置覆盖近端+短间隔):", "✅" if tier_ok else "❌")
ok = ok and tier_ok

# 4. 确定性
bets2 = run_once()
same = [tuple(b['digits']) for b in bets] == [tuple(b['digits']) for b in bets2]
print(f"[4] 确定性(两次运行一致):", "✅" if same else "❌")
ok = ok and same

# 5. 信息性: 实际覆盖
hits = []
for pos in range(5):
    cnt = sum(1 for b in bets if b['digits'][pos] == actual[pos])
    hits.append(cnt)
    print(f"  {names[pos]}位实际{actual[pos]}: {cnt}/10")
best = max(sum(1 for p in range(5) if b['digits'][p] == actual[p]) for b in bets)
print(f"  最佳单注命中: {best}/5 | 位置命中率: {sum(hits)}/50 = {sum(hits)/50*100:.0f}%")

print(f"\n{'✅ 全部机制校验通过' if ok else '❌ 存在校验失败'}")
sys.exit(0 if ok else 1)
