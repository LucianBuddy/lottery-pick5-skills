#!/usr/bin/env python3
"""26213期归因复现: 开奖 7 4 0 7 1, 存档预测万7 0/10
用26212视角(截断数据)复跑predict, 分析万7缺失根因.
P5规则: 万/千/百 = 同期P3百/十/个 100%一致 → 万7=P3百7
"""
import sys, os
sys.path.insert(0, '/home/admin/.openclaw/workspace-lottery/skills/lottery-pick5-skills/scripts')
sys.path.insert(0, '/home/admin/.openclaw/workspace-lottery/skills/lottery-pick5-skills')

import pandas as pd
import p5_fusion_complete as p5m
from p5_fusion_complete import Pick5FusionComplete, VERSION

print(f"[repro-26213] 版本={VERSION}")

# 截断数据到26212
src = '/home/admin/.openclaw/workspace-lottery/skills/lottery-pick5-skills/assets/data/排列5历史数据.xlsx'
df = pd.read_excel(src, engine='openpyxl')
df = df[df['期号'] <= 26212]
df.to_excel('/tmp/p5_trunc_26212.xlsx', index=False, engine='openpyxl')
print(f"截断: {len(df)}期, 至{df['期号'].iloc[-1]}")

p5m.check_and_update = lambda *a, **k: {'updated': False, 'last_period': 26212}
model = Pick5FusionComplete(data_path='/tmp/p5_trunc_26212.xlsx', auto_update=False)
pred = model.predict()
bets = pred.get('single_bets') or pred.get('bets') or []
top = [b['digits'] for b in bets[:10]]
print(f"\n[26213视角] 开奖74071:")
for i, t in enumerate(top, 1):
    hits = sum(1 for j in range(5) if t[j] == [7,4,0,7,1][j])
    print(f"  {i}. {t} 位置命中={hits}")
for pos, name, d in [(0,'万',7),(1,'千',4),(2,'百',0),(3,'十',7),(4,'个',1)]:
    cnt = sum(1 for c in top if c[pos] == d)
    print(f"  {name}{d}: {cnt}/10 {'✅' if cnt>0 else '❌'}")
