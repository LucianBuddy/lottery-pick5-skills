#!/usr/bin/env python3
"""
V1.53.0 快速单元测试: 重建需求tier3(10-15期)保2个数字 (秒级, 不跑全量pipeline)
场景: 26208期归因 — 开奖47186, 存档预测万4 0/10(千7/百1/十8/个6 各1-2/10)
根因: 重建需求每个(位置,档)只取_digs[0] — 万位tier3={5:漏12,4:漏10}按遗漏深
  优先只保万5(漏12), 万4(漏10)被跳过 → 开奖万4全漏(同P3 26208个1型)
修复: [V1.53.0] 重建循环tier3(10-15中冷深)每位置保2个数字(其他档容量有限保1个)
验证:
  场景1 26208复现: 退化输入重建后 万4≥1(开奖) 且 万5≥1(原保) 不退化
  场景2 回归26207: 个4(漏14,tier3)/十4(漏9,tier2)≥1 保持
  场景3 回归26205: 万8(漏3)/千tier1覆盖 保持
"""
import sys, os, random, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import openpyxl
from p5_fusion_complete import Pick5FusionComplete, VERSION

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', 'assets', 'data', '排列5历史数据.xlsx')
wb = openpyxl.load_workbook(DATA, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
draws = []
for _r in rows[1:]:
    if _r[0] >= 26209:
        break
    draws.append(tuple(int(x) for x in _r[1:6]))
assert draws[-1] == (4, 7, 1, 8, 6), draws[-1]
draws = draws[:-1]  # 到26207, 复现26208预测场景
assert draws[-1] == (8, 6, 6, 4, 4), draws[-1]
print(f"[verify-p5-v153] 数据{len(draws)}期(至26207), 版本={VERSION}")

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
names = ['万', '千', '百', '十', '个']

def tier(pos, d):
    m = miss[pos].get(d, 99)
    return 0 if m <= 2 else (1 if m <= 8 else (2 if m <= 9 else (3 if m <= 15 else 4)))

def make_stub(p3_top1=(2, 7, 8)):
    stub = type('Stub', (), {})()
    stub.draws = draws
    stub._p5_protected = set()
    stub._p5_v46_high = set()
    stub.last_period = '26207'
    stub._load_p3_prediction = lambda period, top_n=1: list(p3_top1)
    return stub

random.seed(26208)
pool = []
seen = set()
for _ in range(900):
    d = tuple(random.randint(0, 9) for _ in range(5))
    if d in seen:
        continue
    seen.add(d)
    pool.append({'digits': list(d), 'final_score': random.uniform(-6, 0.5)})
for d in ([5, 1, 8, 2, 3], [4, 0, 8, 4, 6], [4, 7, 2, 5, 1], [8, 6, 5, 0, 5]):
    pool.append({'digits': d, 'final_score': -3.0})
result = {'all': pool, 'top100': pool[:100]}
ok = True

# ===== 场景1: 26208复现 — 退化重建后万4(tier3)≥1 =====
# 模拟26208退化: 前8张万/千/百锁死, 触发构造式重建
deg10 = []
for _ in range(8):
    deg10.append({'digits': [6, 5, 5, 0, 5], 'final_score': 0.3})
deg10.append({'digits': [8, 6, 6, 4, 4], 'final_score': 0.2})
deg10.append({'digits': [2, 7, 8, 2, 3], 'final_score': -3.0})
out1 = Pick5FusionComplete._v50_final_channel(make_stub(), [dict(c) for c in deg10], result, pool)
top1 = out1[:10]
c_w4 = sum(1 for b in top1 if b['digits'][0] == 4)
c_w5 = sum(1 for b in top1 if b['digits'][0] == 5)
c_q7 = sum(1 for b in top1 if b['digits'][1] == 7)
c_g6 = sum(1 for b in top1 if b['digits'][4] == 6)
print(f"\n[场景1 26208复现] 开奖47186")
print(f"  万4(开奖): {c_w4}/10 {'✅' if c_w4>=1 else '❌'}")
print(f"  万5(原保): {c_w5}/10 {'✅' if c_w5>=1 else '❌'}")
print(f"  千7(开奖): {c_q7}/10 {'✅' if c_q7>=1 else '❌'}")
print(f"  个6(开奖): {c_g6}/10 {'✅' if c_g6>=1 else '❌'}")
print(f"  Top10: {[''.join(map(str,b['digits'])) for b in top1]}")
ok1 = c_w4 >= 1 and c_w5 >= 1 and c_q7 >= 1 and c_g6 >= 1
ok = ok and ok1

# ===== 场景2: 回归26207 — 个4(漏14,tier3)/十4(漏9,tier2)≥1 =====
deg2 = []
for _ in range(9):
    deg2.append({'digits': [6, 5, 5, 0, 5], 'final_score': 0.3})
deg2.append({'digits': [2, 7, 8, 0, 3], 'final_score': -3.0})
out2 = Pick5FusionComplete._v50_final_channel(make_stub(), [dict(c) for c in deg2], result, pool)
top2 = out2[:10]
c_ge4_2 = sum(1 for b in top2 if b['digits'][4] == 4)
c_shi4_2 = sum(1 for b in top2 if b['digits'][3] == 4)
print(f"\n[场景2 回归26207] 个4: {c_ge4_2}/10, 十4: {c_shi4_2}/10")
print(f"  Top10: {[''.join(map(str,b['digits'])) for b in top2]}")
ok2 = c_ge4_2 >= 1 and c_shi4_2 >= 1
print(f"  {'✅' if ok2 else '❌'}")
ok = ok and ok2

# ===== 场景3: 回归26205 — 万8(漏3,tier1)/千tier1覆盖 =====
draws3 = draws[:-2]  # 到26205
assert draws3[-1] == (8, 0, 6, 0, 8), draws3[-1]
miss3 = [{}, {}, {}, {}, {}]
for pos in range(5):
    seq = [d[pos] for d in draws3[-200:]]
    for d in range(10):
        for i in range(len(seq) - 1, -1, -1):
            if seq[i] == d:
                miss3[pos][d] = len(seq) - 1 - i
                break
        if d not in miss3[pos]:
            miss3[pos][d] = len(seq)
def tier3f(pos, d):
    m = miss3[pos].get(d, 99)
    return 0 if m <= 2 else (1 if m <= 8 else (2 if m <= 9 else (3 if m <= 15 else 4)))
stub3 = type('Stub', (), {})()
stub3.draws = draws3
stub3._p5_protected = set()
stub3._p5_v46_high = set()
stub3.last_period = '26204'
stub3._load_p3_prediction = lambda period, top_n=1: [2, 7, 8]
deg3 = []
for _ in range(7):
    deg3.append({'digits': [6, 5, 5, 2, 5], 'final_score': 0.3})
for _ in range(3):
    deg3.append({'digits': [6, 5, 8, 2, 5], 'final_score': 0.1})
out3 = Pick5FusionComplete._v50_final_channel(stub3, [dict(c) for c in deg3], result, pool)
top3 = out3[:10]
c_w8 = sum(1 for b in top3 if b['digits'][0] == 8)
q_t1_ok = any(tier3f(1, b['digits'][1]) == 1 for b in top3)
mono3 = all(max([sum(1 for b in top3 if b['digits'][p] == d) for d in range(10)]) <= 2 for p in range(5))
print(f"\n[场景3 回归26205] 万8: {c_w8}/10, 千tier1覆盖: {q_t1_ok}, 注数={len(top3)}, 反垄断={mono3}")
print(f"  Top10: {[''.join(map(str,b['digits'])) for b in top3]}")
ok3 = c_w8 >= 1 and q_t1_ok and len(top3) == 10 and mono3
print(f"  {'✅' if ok3 else '❌'}")
ok = ok and ok3

print(f"\n{'✅ V1.53.0 FAST全部通过' if ok else '❌ FAST有失败'}")
sys.exit(0 if ok else 1)
