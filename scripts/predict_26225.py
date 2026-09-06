#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预测排列五最新一期(26225)并存档"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts'))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'assets', 'data', '排列5历史数据.xlsx')


def main():
    from p5_fusion_complete import Pick5FusionComplete
    fusion = Pick5FusionComplete(data_path=DATA, auto_update=False)
    r = fusion.predict()
    print('\n=====直选Top10=====')
    for i, b in enumerate(r.get('zx_bets', [])[:10], 1):
        print(f"{i}. {''.join(map(str, b.get('digits')))}  score={b.get('final_score', 0):.2f}")
    print('\n=====复式=====')
    cb = r.get('compound_bets', {})
    if cb:
        for k, v in cb.items():
            print(f'{k}: {v}')
    print('\n[Store] 预测已存档')


if __name__ == '__main__':
    main()
