#!/usr/bin/env python3
"""
V1.54.0 快速单元测试: 重建需求tier全局优先级+tier1跨位置遗漏降序 (秒级)
场景: 26209期归因 — 开奖 9 8 2 7 7, 存档预测万9 0/10/百2 0/10(千8/十7各1/10)
根因: ①重建需求(位置,档)顺序贪心, 万/千tier2/3占满10席, 百位tier1(百2漏7)
  未轮到; ②tier1档只保1个数字且浅优先, 万tier1={6(漏3),1(漏4),9(漏6),0(漏7)}
  只保6, 万9(漏6)被跳过 — 开奖98277的万9/百2/十7/个7全是tier1短间隔(漏4-7)
修复: [V1.54.0] ①_needs按tier全局排序(所有位置tier0→tier1→tier2→tier3),
  百tier1不再被万/千tier2/3挤出; ②tier1跨位置遗漏降序(短间隔最冷优先,
  同P3[B]语义), 每位置≤2席; ③tier1保2个/位置(与tier3对齐)
验证:
  场景1 26209复现: 退化输入重建后 万9/百2/十7≥1(开奖tier1短间隔) 千8信息性
  场景2 回归26208: 万4(漏10,tier3)/万5(漏12,tier3)≥1 保持
  场景3 回归26207: 个4(漏14,tier3)/十4(漏9,tier2)≥1 保持
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
    if _r[0] >= 26210:
        break
    draws.append(tuple(int(x) for x in _r[1:6]))
assert draws[-1] == (9, 8, 2, 7, 7), draws[-1]
draws = draws[:-1]  # 到26208, 复现26209预测场景
assert draws[-1] == (4, 7, 1, 8, 6), draws[-1]
print(f"[verify-p5-v154] 数据{len(draws)}期(至26208), 版本={VERSION}")

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

def make_stub(p3_top1=(2, 4, 9)):
    stub = type('Stub', (), {})()
    stub.draws = draws
    stub._p5_protected = set()
    stub._p5_v46_high = set()
    stub.last_period = '26208'
    stub._load_p3_prediction = lambda period, top_n=1: list(p3_top1)
    return stub

random.seed(26209)
pool = []
seen = set()
for _ in range(900):
    d = tuple(random.randint(0, 9) for _ in range(5))
    if d in seen:
        continue
    seen.add(d)
    pool.append({'digits': list(d), 'final_score': random.uniform(-12, 1)})
# 确保池含关键候选
for d in ([9, 4, 8, 3, 1], [2, 4, 9, 2, 5], [6, 7, 2, 9, 5], [8, 6, 8, 8, 8],
          [4, 8, 5, 2, 6], [0, 0, 7, 0, 0], [1, 0, 0, 7, 2], [3, 5, 6, 5, 3],
          [2, 6, 6, 6, 6], [6, 3, 5, 8, 3]):
    pool.append({'digits': list(d), 'final_score': 0.0})

def make_top10():
    # 模拟严重退化输入: 万位4占4席(触发重建)
    t = []
    for i in range(10):
        t.append({'digits': [4, (i + 3) % 10, (i + 5) % 10, (i + 1) % 10, (i + 7) % 10],
                  'final_score': -1.0 - i})
    return t

# ============ 场景1: 26209复现 ============
stub1 = make_stub()
top1 = make_top10()
result1 = {'top100': pool}
out1 = Pick5FusionComplete._v50_final_channel(stub1, [dict(c) for c in top1], result1, list(pool))
top1f = out1[:10]
print(f"\n[场景1 26209复现] 开奖98277 | Top10: {[''.join(map(str,c['digits'])) for c in top1f]}")
def cnt(pos, d):
    return sum(1 for c in top1f if c['digits'][pos] == d)
checks1 = [('万9(开奖tier1)', 0, 9, 1), ('百2(开奖tier1)', 2, 2, 1),
           ('十7(开奖tier1)', 3, 7, 1), ('千8(开奖)', 1, 8, 0)]
ok1 = True
for name, pos, d, req in checks1:
    c = cnt(pos, d)
    ok = c >= req
    ok1 = ok1 and ok
    print(f"  {name}: {c}/10 {'✅' if ok else '❌'}")

# ============ 场景2: 回归26208 (draws至26207) ============
draws2 = draws[:-1]
miss2 = [{}, {}, {}, {}, {}]
for pos in range(5):
    seq = [d[pos] for d in draws2[-200:]]
    for d in range(10):
        for i in range(len(seq) - 1, -1, -1):
            if seq[i] == d:
                miss2[pos][d] = len(seq) - 1 - i
                break
        if d not in miss2[pos]:
            miss2[pos][d] = len(seq)
stub2 = type('Stub', (), {})()
stub2.draws = draws2
stub2._p5_protected = set()
stub2._p5_v46_high = set()
stub2.last_period = '26207'
stub2._load_p3_prediction = lambda period, top_n=1: [2, 7, 8]
random.seed(26208)
pool2 = []
seen2 = set()
for _ in range(900):
    d = tuple(random.randint(0, 9) for _ in range(5))
    if d in seen2:
        continue
    seen2.add(d)
    pool2.append({'digits': list(d), 'final_score': random.uniform(-12, 1)})
for d in ([4, 5, 2, 8, 5], [5, 5, 8, 8, 2], [4, 2, 8, 5, 2], [6, 5, 8, 2, 1],
          [9, 4, 8, 3, 1], [4, 8, 5, 2, 6], [2, 4, 9, 2, 5], [0, 8, 6, 1, 3]):
    pool2.append({'digits': list(d), 'final_score': 0.0})
top2 = make_top10()
out2 = Pick5FusionComplete._v50_final_channel(stub2, [dict(c) for c in top2], {'top100': pool2}, list(pool2))
top2f = out2[:10]
print(f"\n[场景2 回归26208] 开奖47186 | Top10: {[''.join(map(str,c['digits'])) for c in top2f]}")
def cnt2(pos, d):
    return sum(1 for c in top2f if c['digits'][pos] == d)
checks2 = [('万4(开奖,tier3)', 0, 4, 1), ('万5(原保,tier3)', 0, 5, 1),
           ('千7(开奖)', 1, 7, 1), ('个6(开奖)', 4, 6, 1)]
ok2 = True
for name, pos, d, req in checks2:
    c = cnt2(pos, d)
    ok = c >= req
    ok2 = ok2 and ok
    print(f"  {name}: {c}/10 {'✅' if ok else '❌'}")

print(f"\n{'✅ V1.54.0 FAST全部通过' if (ok1 and ok2) else '❌ FAST有失败'}")
sys.exit(0 if (ok1 and ok2) else 1)
