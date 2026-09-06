#!/usr/bin/env python3
"""V1.55.0 快速单元测试: P3 TopN保底扩展 (秒级, 不跑全量predict)
场景: 26210期归因 — 开奖 0 9 4 5 1, 存档预测千9 0/10(万0 1/10/百4 1/10/十5 1/10/个1 1/10)
根因: ①P3候选(2,9,6)/(2,9,2)的千9信号在P5池中缺失(万2漏36深冷被GA/多样性
  挤出, 500池集中) — 混合评分无票可改 ②V51保底仅P3 Top1, Top2-Top10信号丢失
  ③V51连续注入共享数字候选(万2×4)时, 后注入票裁剪掉先注入票(只剩最后1个)
修复(V1.55.0):
  [A] V51保底从Top1扩展为TopN(上限8), 遍历P3 Top10注入缺失前3位
  [B] _v51_prot保护集: 已注入保底票不被后续注入/裁剪换出
  [C] _v51_loss后2位唯一覆盖加权(+2): 换出避开十/个唯一载体
  [D] 兼容stub返回(3元素int列表→包装成单元素列表)
验证:
  场景A 26210复现: 千9≥1(开奖), 万0/百4/十5/个1信息性
  场景B v152回归: P3 Top1(278)保底注入且不拆十4唯一载体
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import openpyxl
from p5_fusion_complete import Pick5FusionComplete, VERSION

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', 'assets', 'data', '排列5历史数据.xlsx')
wb = openpyxl.load_workbook(DATA, read_only=True)
rows = list(wb.active.iter_rows(values_only=True))
# 【柔性截断】数据文件随期更新, 按期号截断至26210视角
draws = []
for _r in rows[1:]:
    if int(_r[0]) >= 26211:
        break
    draws.append(tuple(int(x) for x in _r[1:6]))
assert draws[-1] == (0, 9, 4, 5, 1), draws[-1]  # 26210已同步
print(f"[verify-p5-v155] 数据{len(draws)}期(至26210), 版本={VERSION}")

def make_stub(p3_top1=(2, 7, 8), p3_topn=None):
    stub = type('Stub', (), {})()
    stub.draws = draws
    stub._p5_protected = set()
    stub._p5_v46_high = set()
    stub.last_period = '26209'
    if p3_topn is not None:
        stub._load_p3_prediction = lambda period, top_n=1: p3_topn
    else:
        stub._load_p3_prediction = lambda period, top_n=1: list(p3_top1)
    return stub

def count(top, pos, d):
    return sum(1 for c in top if c['digits'][pos] == d)

# ============ 场景A: 26210复现 — P3 TopN保底注入 ============
# 模拟: top10退化(不含千9/百4), P3 Top10含048/296/268/288/245/292/254...
seedA = [
    {'digits': [6, 7, 5, 0, 5], 'final_score': 0.43},
    {'digits': [7, 0, 9, 6, 8], 'final_score': 0.28},
    {'digits': [7, 0, 4, 6, 8], 'final_score': -0.01},
    {'digits': [8, 7, 9, 7, 3], 'final_score': -0.10},
    {'digits': [8, 6, 6, 2, 3], 'final_score': -0.10},
    {'digits': [3, 6, 6, 0, 5], 'final_score': -3.22},
    {'digits': [4, 5, 5, 8, 0], 'final_score': -4.08},
    {'digits': [2, 1, 8, 7, 7], 'final_score': -4.17},
    {'digits': [2, 5, 3, 2, 1], 'final_score': -4.36},
    {'digits': [6, 4, 8, 4, 2], 'final_score': -3.50},
]
poolA = [dict(c) for c in seedA] + [
    {'digits': [0, 4, 8, 8, 5], 'final_score': 0.41},
    {'digits': [2, 9, 6, 8, 5], 'final_score': 0.40},
    {'digits': [2, 9, 2, 2, 1], 'final_score': 0.30},
    {'digits': [2, 5, 4, 8, 5], 'final_score': 0.20},
    {'digits': [2, 6, 8, 7, 3], 'final_score': 0.10},
    {'digits': [2, 8, 8, 7, 3], 'final_score': 0.05},
    {'digits': [2, 4, 5, 7, 5], 'final_score': 0.00},
    {'digits': [6, 4, 8, 7, 3], 'final_score': -0.05},
    {'digits': [8, 1, 8, 7, 3], 'final_score': -0.10},
    {'digits': [9, 4, 8, 7, 3], 'final_score': -0.15},
]
p3_topn = [[0, 4, 8], [2, 9, 6], [2, 6, 8], [2, 8, 8], [2, 4, 5],
           [2, 9, 2], [2, 5, 4], [6, 4, 8], [8, 1, 8], [9, 4, 8]]
resultA = {'all': poolA, 'top100': poolA[:100]}
outA = Pick5FusionComplete._v50_final_channel(make_stub(p3_topn=p3_topn),
                                              [dict(c) for c in seedA], resultA, poolA)
topA = outA[:10]
print(f"\n[场景A 26210复现] 开奖09451 | Top10: {[''.join(map(str,c['digits'])) for c in topA]}")
checksA = [('千9(开奖)', 1, 9, 1), ('百4(开奖)', 2, 4, 1)]
okA = True
for name, pos, d, req in checksA:
    c = count(topA, pos, d)
    ok = c >= req
    okA = okA and ok
    print(f"  {name}: {c}/10 {'✅' if ok else '❌'}")
# 万0(信息性): verify seed为退化合成场景, V50-TIER换出链与真实predict不同,
# 真实repro已验证万0 1/10(04885在Top10)
print(f"  万0(信息性): {count(topA, 0, 0)}/10")
# P3 TopN注入数
p3_cnt = sum(1 for c in topA if tuple(c['digits'][:3]) in set(tuple(x) for x in p3_topn))
print(f"  P3前3位注入数: {p3_cnt}/10 (应≥3) {'✅' if p3_cnt >= 3 else '❌'}")
okA = okA and p3_cnt >= 3

# ============ 场景B: v152回归 — 不拆十4唯一载体 + Top1保底 ============
seedB = [
    {'digits': [6, 7, 5, 0, 5], 'final_score': 0.43},
    {'digits': [7, 0, 9, 6, 8], 'final_score': 0.28},
    {'digits': [7, 0, 4, 6, 8], 'final_score': -0.01},
    {'digits': [8, 7, 9, 7, 3], 'final_score': -0.10},
    {'digits': [8, 6, 6, 2, 3], 'final_score': -0.10},
    {'digits': [3, 6, 6, 0, 5], 'final_score': -3.22},
    {'digits': [4, 5, 5, 8, 0], 'final_score': -4.08},
    {'digits': [2, 1, 8, 7, 7], 'final_score': -4.17},
    {'digits': [2, 5, 3, 2, 1], 'final_score': -4.36},
    {'digits': [6, 4, 8, 4, 2], 'final_score': -3.50},  # 十4唯一载体
]
outB = Pick5FusionComplete._v50_final_channel(make_stub(p3_top1=(2, 7, 8)),
                                              [dict(c) for c in seedB], resultA, poolA)
topB = outB[:10]
c_shi4 = count(topB, 3, 4)
c_p3t = sum(1 for c in topB if tuple(c['digits'][:3]) == (2, 7, 8))
print(f"\n[场景B v152回归] P3Top1(278)保底+十4不拆 | Top10: {[''.join(map(str,c['digits'])) for c in topB]}")
print(f"  十4: {c_shi4}/10 {'✅' if c_shi4 >= 1 else '❌'}")
print(f"  P3Top1前3位278: {c_p3t}/10 {'✅' if c_p3t >= 1 else '❌'}")
okB = c_shi4 >= 1 and c_p3t >= 1

print(f"\n{'✅ V1.55.0 FAST全部通过' if (okA and okB) else '❌ FAST有失败'}")
