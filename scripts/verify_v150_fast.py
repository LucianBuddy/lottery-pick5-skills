#!/usr/bin/env python3
"""
V1.50.0 快速单元测试: 只跑 _v50_final_channel 最终整合通道(秒级, 不跑全量pipeline)
用合成退化top10 + 真实历史数据验证:
  1. 反垄断: 每位置每数字≤2席
  2. 优先级分层: 每位置覆盖近端(0-2期)+短间隔(3-8期)数字(若存在)
  3. 输出恰好10注
执行逻辑优化: 全量验证(verify_v150.py)每轮~3分钟, 本脚本<5秒, 迭代调试用
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import openpyxl
from p5_fusion_complete import Pick5FusionComplete, VERSION

# 1) 真实历史数据(截断到26204, 复现26205预测场景)
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', 'assets', 'data', '排列5历史数据.xlsx')
wb = openpyxl.load_workbook(DATA, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
draws = []
for _r in rows[1:]:
    if _r[0] >= 26206:
        break
    draws.append(tuple(int(x) for x in _r[1:6]))
assert draws[-1] == (8, 0, 6, 0, 8), draws[-1]
draws = draws[:-1]  # 去掉26205

# 2) 合成退化top10: 模拟26205失败态(万6重号垄断7席/千5中冷5席/百8深冷4席)
random.seed(26205)
base_pool = []
for _ in range(800):
    base_pool.append({'digits': [random.randint(0, 9) for _ in range(5)],
                      'final_score': random.uniform(-5, 0.5)})
degenerate_top10 = []
for _ in range(7):
    degenerate_top10.append({'digits': [6, 5, 5, 2, 5], 'final_score': 0.3})
for _ in range(3):
    degenerate_top10.append({'digits': [6, 5, 8, 2, 5], 'final_score': 0.1})

# 3) stub对象: 只提供方法需要的属性
stub = type('Stub', (), {})()
stub.draws = draws
stub._p5_protected = set()
stub.last_period = '26204'
# V1.51.0: P3 Top1(26206场景=558前3位5,5,8) — 验证通道不拆除保底
stub._load_p3_prediction = lambda period, top_n=1: [5, 5, 8] if top_n == 1 else [[5, 5, 8]]
result = {'all': base_pool, 'top100': base_pool[:100]}

out = Pick5FusionComplete._v50_final_channel(stub, degenerate_top10, result, base_pool)

names = ['万', '千', '百', '十', '个']
# 遗漏表
miss = [{}, {}, {}, {}, {}]
for pos in range(5):
    seq = [d[pos] for d in draws[-200:]]
    for d in range(10):
        for i in range(len(seq) - 1, -1, -1):
            if seq[i] == d:
                miss[pos][d] = len(seq) - 1 - i
                break
        if d not in miss[pos]:
            miss[pos][d] = len(seq)

def tier(pos, d):
    m = miss[pos].get(d, 99)
    return 0 if m <= 2 else (1 if m <= 8 else (2 if m <= 9 else 3))

ok = True
# 检查1: 10注
n = len(out)
print(f"[fast][1] 注数={n}", "✅" if n == 10 else "❌")
ok = ok and n == 10
# 检查2: 反垄断
for pos in range(5):
    cnt = {}
    for b in out:
        cnt[b['digits'][pos]] = cnt.get(b['digits'][pos], 0) + 1
    for d, c in cnt.items():
        if c > 2:
            ok = False
            print(f"  ❌ {names[pos]}位{d}占{c}席")
print(f"[fast][2] 反垄断≤2席", "✅" if ok else "❌")
# 检查3: 分层覆盖
for pos in range(5):
    for t_need, tn in ((0, '近端'), (1, '短间隔')):
        exists = any(tier(pos, d) == t_need for d in range(10))
        if not exists:
            continue
        covered = any(tier(pos, b['digits'][pos]) == t_need for b in out)
        if not covered:
            ok = False
            print(f"  ❌ {names[pos]}位缺tier{t_need}({tn})")
print(f"[fast][3] 优先级分层覆盖", "✅" if ok else "❌")

# 检查4: P3 Top1保底(V1.51.0) — 前3位(5,5,8)必须在输出中
p3t_ok = any(tuple(c['digits'][:3]) == (5, 5, 8) for c in out)
print(f"[fast][4] P3 Top1前3位(5,5,8)保底", "✅" if p3t_ok else "❌")
ok = ok and p3t_ok

print(f"\nTop10: {[''.join(map(str,b['digits'])) for b in out]}")
print(f"{'✅ FAST全部通过' if ok else '❌ FAST有失败'}")
sys.exit(0 if ok else 1)
