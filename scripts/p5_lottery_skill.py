#!/usr/bin/env python3
"""
排列5 (Pick5) 预测技能 — CLI Adapter
"""

import argparse, sys, json
from typing import Dict, List, Any
from p5_fusion_complete import Pick5FusionComplete, VERSION


def _fmt(digits):
    return ' '.join(str(d) for d in digits)


def _print_predict(result):
    period = result.get('period', '?')
    bets = result.get('bets', [])

    print(f"\n{'='*55}")
    print(f"  排列5 第{period}期 多策略融合预测")
    print(f"{'='*55}")

    if bets:
        print(f"\n🎯 推荐方案 (Top {len(bets)})")
        print(f"{'-'*40}")
        for i, bet in enumerate(bets, 1):
            d = bet.get('digits', [])
            s = bet.get('final_score', 0)
            p = bet.get('hit_probability', 0)
            print(f"  {i:2d}. [{_fmt(d)}]  score={s:.4f}  p={p:.1f}%")

    print(f"\n⚠️  仅供参考娱乐，请理性投注！")


def main():
    parser = argparse.ArgumentParser(description='排列5 (Pick5) 预测')
    sub = parser.add_subparsers(dest='command')

    p_pred = sub.add_parser('predict', help='预测下一期')
    p_pred.add_argument('--top', type=int, default=10)

    p_bt = sub.add_parser('backtest', help='回测模型表现')
    p_bt.add_argument('--periods', type=int, default=30, help='回测期数')

    p_bm = sub.add_parser('benchmark', help='基准对比(模型vs随机)')
    p_bm.add_argument('--periods', type=int, default=100, help='对比期数')

    p_info = sub.add_parser('info', help='技能信息')
    p_rep = sub.add_parser('report', help='技能能力报告')


    args = parser.parse_args()
    fusion = Pick5FusionComplete()

    if args.command == 'predict' or args.command is None:
        result = fusion.predict(top_n=args.top if hasattr(args, 'top') else 10)
        _print_predict(result)
    elif args.command == 'info':
        info_dict = fusion.info()
    elif args.command == "backtest":
        result = fusion.backtest(n_periods=args.periods)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'benchmark':
        fusion.benchmark(n_periods=args.periods)
    elif args.command == 'report':
        rep = fusion.report()
        print(f"排列5技能报告 V{rep['version']}")
        print(f"数据: {rep['data_periods']}期")
        for k, v in rep['capabilities'].items():
            print(f"  {k}: {v}")
        print()
        fusion.benchmark(n_periods=100)
        info_dict = fusion.info()
        print(f"\n{'='*55}")
        print(f"  {info_dict['skill']}")
        print(f"{'='*55}")
        print(f"  版本:      V{info_dict['version']}")
        print(f"  最新开奖:  [{_fmt(info_dict['last_draw'])}] ({info_dict['data_periods']}期)")
        print()


if __name__ == '__main__':
    main()
