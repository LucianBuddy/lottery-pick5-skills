#!/usr/bin/env python3
"""
排列5 (Pick5) 预测技能 — CLI Adapter

输出策略:
- 默认: 调试stdout重定向到 logs/p5_YYYYmmdd_HHMMSS.log, 只打印最终用户输出
- P5_VERBOSE=1: 全量调试输出到stdout(调试用)
"""

import argparse, sys, json, os, contextlib, datetime
from typing import Dict, List, Any
from p5_fusion_complete import Pick5FusionComplete, VERSION

_VERBOSE = os.environ.get('P5_VERBOSE', '0') == '1'


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


def _print_info(info_dict):
    print(f"\n{'='*55}")
    print(f"  {info_dict['skill']}")
    print(f"{'='*55}")
    print(f"  版本:      V{info_dict['version']}")
    print(f"  最新开奖:  [{_fmt(info_dict['last_draw'])}] ({info_dict['data_periods']}期)")
    print()


def _print_report(rep):
    print(f"排列5技能报告 V{rep['version']}")
    print(f"数据: {rep['data_periods']}期")
    for k, v in rep['capabilities'].items():
        print(f"  {k}: {v}")
    print()


def _log_path():
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, f"p5_{datetime.datetime.now():%Y%m%d_%H%M%S}.log")


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

    # —— 执行阶段: 非VERBOSE时调试stdout重定向到日志文件 ——
    log_path = None
    _stdout = sys.stdout
    if not _VERBOSE:
        log_path = _log_path()
        sys.stdout = open(log_path, 'w', encoding='utf-8')

    try:
        fusion = Pick5FusionComplete()
        if args.command == 'predict' or args.command is None:
            result = fusion.predict(top_n=args.top if hasattr(args, 'top') else 10)
        elif args.command == 'info':
            result = fusion.info()
        elif args.command == "backtest":
            result = fusion.backtest(n_periods=args.periods)
        elif args.command == 'benchmark':
            result = fusion.benchmark(n_periods=args.periods)
        elif args.command == 'report':
            result = fusion.report()
        else:
            result = None
    finally:
        if log_path:
            sys.stdout.close()
            sys.stdout = _stdout

    # —— 展示阶段: 仅用户可见输出 ——
    if log_path:
        print(f"[P5] 调试日志: {log_path}")

    if args.command == 'predict' or args.command is None:
        _print_predict(result)
    elif args.command == 'info':
        _print_info(result)
    elif args.command == "backtest":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'benchmark':
        if isinstance(result, dict) and 'error' not in result:
            print(f"[P5-Benchmark] 模型和值命中率 {result.get('model_sum_match_rate_%')}% "
                  f"vs 随机 {result.get('random_sum_match_rate_%')}% "
                  f"(delta {result.get('delta_%')}%, p={result.get('p_value')}, "
                  f"显著={result.get('significant')})")
        elif result:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'report':
        _print_report(result)
        _print_info(fusion.info())


if __name__ == '__main__':
    main()
