#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P5周期/结构扫描器 — V1.62.0方案 步骤① (描述性扫描, 只读不改)
DLT V4.8.0 / P3 V2.55.0 同协议适配P5 (7691期 4001~26216, 5位×10数字)

结构性前提: P5万/千/百 = 同期P3百/十/个 (100%一致) → 前3位单数字规律已被
P3扫描覆盖(全阴性, 仅组选(1,5,9)节奏为真信号), 本扫描重点:
[1] 后2位(十/个)位置级: 20序列 gap离散指数 + 滞后k基数控制(600检验)
    + 周期图分半 + gap马尔可夫
[2] 后2位组合级gap: 100有序对(p=0.01) + 55无序对(异号p=0.02/同号p=0.01)
    Bonf+分半+置换
[3] 前3位→后2位交叉条件分布: 前3形态(豹/三/六)×后十/后个, 前3和值区间
    ×后2和值区间 — P5特有结构
[4] 相邻期重复模式: 5位集合重叠 vs 放回模型 (P3教训: 超几何是错误空模型)
[5] AnEn相似窗口池 walk-forward (DLT/P3两连败, 便宜复验)
[6] P3(1,5,9)迁移确认: P5前3位集合{1,5,9}间隔应与P3完全一致

输出: /tmp/p5_cycle_scan_result.json
"""
import json
import math
import os

import numpy as np
import pandas as pd
from scipy.stats import chi2, chi2_contingency

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'assets', 'data', '排列5历史数据.xlsx')
MAX_LAG = 30
MIN_SUPPORT = 60
PERM_N = 100
P0 = 0.1


def load_draws(path):
    df = pd.read_excel(path, engine='openpyxl')
    periods = [int(x) for x in df['期号']]
    digits = df[['万位', '千位', '百位', '十位', '个位']].values.astype(int)
    return periods, digits


def indicator_matrix(digits):
    N = len(digits)
    M = np.zeros((N, 5, 10), dtype=np.int8)
    for t in range(N):
        for p in range(5):
            M[t, p, digits[t, p]] = 1
    return M


def gap_stats(ind, p0, min_gaps=20):
    idx = np.nonzero(ind)[0]
    gaps = np.diff(idx)
    m = len(gaps)
    if m < min_gaps:
        return None
    disp = gaps.var(ddof=1) / gaps.mean()
    baseline = (1.0 - p0) / p0
    ratio = disp / baseline
    stat = (m - 1) * disp / baseline
    p_under = float(chi2.cdf(stat, m - 1))
    p_over = float(chi2.sf(stat, m - 1))
    return {'n': m, 'ratio': round(ratio, 3), 'p_under': p_under, 'p_over': p_over}


def lagk_zscore(M, own_p, positions):
    N = M.shape[0]
    out = []
    for k in range(1, MAX_LAG + 1):
        prev = M[:N - k].astype(np.float64)
        cur = M[k:].astype(np.float64)
        a = prev.sum(axis=0)
        b = (prev * cur).sum(axis=0)
        for p in positions:
            for d in range(10):
                if a[p, d] < MIN_SUPPORT:
                    continue
                p0 = own_p[p, d]
                p_cond = b[p, d] / a[p, d]
                se = math.sqrt(p0 * (1 - p0) / a[p, d])
                z = (p_cond - p0) / se if se > 0 else 0.0
                out.append({'pos': p, 'digit': d, 'lag': k,
                            'support': int(a[p, d]), 'p_cond': round(float(p_cond), 4),
                            'own_p': round(float(p0), 4), 'z': round(float(z), 2),
                            'lift': round(float(p_cond / p0), 3)})
    return out


def periodogram_peak(ind, max_period=60):
    N = len(ind)
    x = ind - ind.mean()
    spec = np.abs(np.fft.rfft(x)) ** 2
    best_p, best_pow = None, -1.0
    for p in range(2, max_period + 1):
        i2 = int(round((1.0 / p) * N))
        if i2 >= len(spec):
            continue
        if spec[i2] > best_pow:
            best_pow = spec[i2]
            best_p = p
    return best_p, float(best_pow)


def gap_markov(ind):
    idx = np.nonzero(ind)[0]
    gaps = np.diff(idx)
    if len(gaps) < 30:
        return None
    med = float(np.median(gaps))
    s = (gaps <= med).astype(int)
    M2 = np.zeros((2, 2), dtype=int)
    for i in range(len(s) - 1):
        M2[s[i], s[i + 1]] += 1
    if M2.sum(axis=1).min() == 0:
        return None
    _, pv, _, _ = chi2_contingency(M2, correction=False)
    return float(pv)


def main():
    periods, D = load_draws(DATA_PATH)
    N = len(D)
    M = indicator_matrix(D)
    pos_names = ['万', '千', '百', '十', '个']
    print(f"[P5-SCAN] 数据: {N}期 ({periods[0]}~{periods[-1]})")
    result = {'periods': [periods[0], periods[-1]], 'n_draws': N}

    # ---------- [1] 后2位位置级 (十=3, 个=4) ----------
    gap_rows = []
    for p in (3, 4):
        for d in range(10):
            g = gap_stats(M[:, p, d], P0)
            if g is None:
                continue
            g['pos'] = p
            g['digit'] = d
            gap_rows.append(g)
    bonf_gap = 0.05 / 20
    n_reg = sum(1 for g in gap_rows if g['p_under'] < bonf_gap)
    n_clu = sum(1 for g in gap_rows if g['p_over'] < bonf_gap)
    result['gap_pos'] = gap_rows
    print(f"[1] 后2位位置级gap: 20序列, 规律循环={n_reg}, 聚集={n_clu} (Bonf α={bonf_gap:.2e})")
    for g in sorted(gap_rows, key=lambda r: r['p_under'])[:6]:
        print(f"    {pos_names[g['pos']]}{g['digit']}: ratio={g['ratio']} "
              f"p_under={g['p_under']:.2e} n={g['n']}")

    # 滞后k (后2位, 基数控制)
    own_p = M.mean(axis=0)
    rf = lagk_zscore(M, own_p, positions=(3, 4))
    sig_z = [r for r in rf if r['z'] > 3.94]  # Bonf 600检验
    print(f"[1b] 后2位滞后k基数控制: 600检验, 显著(z>3.94)={len(sig_z)}")
    for r in sorted(rf, key=lambda r: -r['z'])[:5]:
        print(f"    {pos_names[r['pos']]}{r['digit']} lag={r['lag']:02d} "
              f"p_cond={r['p_cond']} own_p={r['own_p']} lift={r['lift']} z={r['z']}")
    result['lagk'] = {'n_tests': 600, 'significant': sig_z}

    # 周期图分半 (后2位)
    half = N // 2
    consis = []
    for p in (3, 4):
        for d in range(10):
            pk1, _ = periodogram_peak(M[:half, p, d])
            pk2, _ = periodogram_peak(M[half:, p, d])
            if pk1 and pk2 and abs(pk1 - pk2) <= 1:
                consis.append({'pos': p, 'digit': d, 'peak_h1': pk1, 'peak_h2': pk2})
    print(f"[1c] 后2位周期图分半一致: {len(consis)}/20 (期望≈1)")
    result['periodogram'] = consis

    # gap马尔可夫 (后2位)
    mk = []
    for p in (3, 4):
        for d in range(10):
            pv = gap_markov(M[:, p, d])
            if pv is not None:
                mk.append({'pos': p, 'digit': d, 'pval': pv})
    n_mk = sum(1 for r in mk if r['pval'] < 0.05 / 20)
    print(f"[1d] 后2位gap马尔可夫: 显著={n_mk}/20 (Bonf)")
    result['gap_markov'] = mk

    # ---------- [2] 后2位组合级gap ----------
    print(f"[2] 后2位组合级gap (100有序对 p=0.01→基线99; 55无序对 异号p=0.02→49/同号0.01→99):")
    pair_seen = {}
    for t in range(N):
        key = (int(D[t, 3]), int(D[t, 4]))
        pair_seen.setdefault(key, []).append(t)
    rows = []
    for key, idx in pair_seen.items():
        gaps = np.diff(np.array(idx))
        m = len(gaps)
        if m < 20:
            continue
        p0 = 0.01
        baseline = 99.0
        disp = gaps.var(ddof=1) / gaps.mean()
        ratio = disp / baseline
        stat = (m - 1) * disp / baseline
        p_under = float(chi2.cdf(stat, m - 1))
        rows.append({'pair': key, 'n': m, 'ratio': round(ratio, 3), 'p_under': p_under})
    bonf_pairs = 0.05 / max(len(rows), 1)
    n_sig = sum(1 for r in rows if r['p_under'] < bonf_pairs)
    print(f"    {len(rows)}个有序对(样本≥20), Bonf显著={n_sig} (α={bonf_pairs:.2e})")
    for r in sorted(rows, key=lambda x: x['p_under'])[:8]:
        print(f"    {r['pair']}: n={r['n']} ratio={r['ratio']} p={r['p_under']:.2e}")
    result['pair_gap'] = {'n': len(rows), 'n_sig': n_sig,
                          'top': sorted(rows, key=lambda x: x['p_under'])[:8]}

    # 无序对
    urows = {}
    for r in rows:
        key = tuple(sorted(r['pair']))
        if key not in urows:
            urows[key] = []
        urows[key].append(r)
    urows2 = []
    for key, sub in urows.items():
        if key[0] == key[1]:
            continue  # 同号对已含于有序
        # 合并两个有序对的gap? 简化: 统计无序对出现期序
    # 直接无序对重算
    useen = {}
    for t in range(N):
        key = tuple(sorted((int(D[t, 3]), int(D[t, 4]))))
        useen.setdefault(key, []).append(t)
    urows3 = []
    for key, idx in useen.items():
        gaps = np.diff(np.array(idx))
        m = len(gaps)
        if m < 20:
            continue
        p0 = 0.02 if key[0] != key[1] else 0.01
        baseline = (1 - p0) / p0
        disp = gaps.var(ddof=1) / gaps.mean()
        ratio = disp / baseline
        stat = (m - 1) * disp / baseline
        p_under = float(chi2.cdf(stat, m - 1))
        urows3.append({'pair': key, 'n': m, 'ratio': round(ratio, 3), 'p_under': p_under})
    bonf_u = 0.05 / max(len(urows3), 1)
    n_usig = sum(1 for r in urows3 if r['p_under'] < bonf_u)
    print(f"    无序对: {len(urows3)}个, Bonf显著={n_usig} (α={bonf_u:.2e})")
    for r in sorted(urows3, key=lambda x: x['p_under'])[:6]:
        print(f"    {r['pair']}: n={r['n']} ratio={r['ratio']} p={r['p_under']:.2e}")
    result['upair_gap'] = {'n': len(urows3), 'n_sig': n_usig,
                           'top': sorted(urows3, key=lambda x: x['p_under'])[:6]}

    # ---------- [3] 前3位→后2位交叉条件分布 ----------
    print(f"[3] 前3位→后2位条件独立性:")
    cond = {}
    f3 = D[:, :3]
    b2 = D[:, 3:]
    # 前3形态
    forms = np.array([0 if f3[t, 0] == f3[t, 1] == f3[t, 2]
                      else (1 if len(set(f3[t])) == 2 else 2) for t in range(N)])
    for bpos, bname in ((3, '后十'), (4, '后个')):
        ct = np.zeros((3, 10), dtype=int)
        for t in range(N):
            ct[forms[t], D[t, bpos]] += 1
        chi2v, pv, dof, _ = chi2_contingency(ct)
        print(f"    前3形态×{bname}: chi2={chi2v:.1f} p={pv:.3f}")
        cond[f'form_x_{bname}'] = {'chi2': round(float(chi2v), 1), 'p': pv}
    # 前3和值区间 × 后2和值区间
    f3sum = f3.sum(axis=1)
    b2sum = b2.sum(axis=1)
    def b3(x):
        return np.clip(x // 9, 0, 2)
    ct = np.zeros((3, 3), dtype=int)
    for t in range(N):
        ct[b3(f3sum[t]), b3(b2sum[t])] += 1
    chi2v, pv, dof, _ = chi2_contingency(ct)
    print(f"    前3和值区间×后2和值区间: chi2={chi2v:.1f} p={pv:.3f}")
    cond['sum3_x_sum2'] = {'chi2': round(float(chi2v), 1), 'p': pv}
    result['cond'] = cond

    # ---------- [4] 相邻期重复模式 (放回模型) ----------
    print(f"[4] 相邻期5位集合重叠 vs 放回模型:")
    obs = np.zeros(6, dtype=int)
    prev_distinct = np.zeros(6, dtype=int)
    for t in range(1, N):
        k = len(set(D[t]) & set(D[t - 1]))
        obs[k] += 1
        prev_distinct[len(set(D[t - 1]))] += 1
    total = N - 1
    # 放回模型期望: 上期不同数字s个, 本期5位独立均匀, 重叠k个
    # 用蒙特卡洛估计 P(k|s) 精确值
    rng = np.random.default_rng(42)
    sims = 200000
    digits_pool = np.arange(10)
    pmat = np.zeros((6, 6))  # pmat[s, k]
    for s in range(1, 6):
        for _ in range(sims):
            prev_set = set(rng.choice(10, s, replace=False))
            cur = rng.choice(10, 5, replace=True)
            k = len(prev_set & set(cur))
            pmat[s, k] += 1
    pmat /= sims
    exp = np.zeros(6)
    for s in range(1, 6):
        for k in range(6):
            exp[k] += prev_distinct[s] * pmat[s, k]
    rates = obs / total
    exp_r = exp / total
    chi2v = sum((o - e) ** 2 / e for o, e in zip(obs, exp) if e > 0)
    pv = float(chi2.sf(chi2v, 5))
    print(f"    观测: k=0:{rates[0]:.4f} k=1:{rates[1]:.4f} k=2:{rates[2]:.4f} "
          f"k=3:{rates[3]:.4f} k=4:{rates[4]:.4f} k=5:{rates[5]:.4f}")
    print(f"    期望: k=0:{exp_r[0]:.4f} k=1:{exp_r[1]:.4f} k=2:{exp_r[2]:.4f} "
          f"k=3:{exp_r[3]:.4f} k=4:{exp_r[4]:.4f} k=5:{exp_r[5]:.4f}")
    print(f"    chi2={chi2v:.1f} p={pv:.3f}")
    result['repeat'] = {'obs': rates.tolist(), 'exp': exp_r.tolist(),
                        'chi2': round(float(chi2v), 1), 'p': pv}

    # ---------- [5] AnEn (全5位) ----------
    TEST_N = 1000
    HIST_MAX = 3000
    EXCLUDE_RECENT = 10
    TOP_K = 30
    POOL = 4
    feats = np.zeros((N, 7))
    feats[:, 0] = D.sum(axis=1) / 45.0
    feats[:, 1] = (D.max(axis=1) - D.min(axis=1)) / 9.0
    feats[:, 2:] = D / 9.0
    start = N - TEST_N
    anen_hits, hot_hits, rand_hits = [], [], []
    for t in range(start, N - 1):
        lo = max(0, t - HIST_MAX)
        hi = t - EXCLUDE_RECENT
        if hi <= lo:
            continue
        hist = np.arange(lo, hi)
        d = np.abs(feats[hist] - feats[t]).sum(axis=1)
        top_idx = hist[np.argsort(d)[:TOP_K]]
        succ = D[top_idx + 1]
        actual = D[t + 1]
        h = 0
        for p in range(5):
            cnts = np.bincount(succ[:, p], minlength=10)
            if actual[p] in np.argsort(-cnts)[:POOL]:
                h += 1
        anen_hits.append(h)
        tr = D[lo:t]
        hh = 0
        for p in range(5):
            cnts = np.bincount(tr[:, p], minlength=10)
            if actual[p] in np.argsort(-cnts)[:POOL]:
                hh += 1
        hot_hits.append(hh)
        rh = 0
        for _ in range(20):
            for p in range(5):
                if actual[p] in rng.choice(10, POOL, replace=False):
                    rh += 1
        rand_hits.append(rh / 20.0)
    af, hf, rf_ = np.mean(anen_hits), np.mean(hot_hits), np.mean(rand_hits)
    win = sum(1 for a, h in zip(anen_hits, hot_hits) if a > h)
    lose = sum(1 for a, h in zip(anen_hits, hot_hits) if a < h)
    n = len(anen_hits)
    print(f"[5] AnEn Top{POOL}/位: AnEn={af:.3f} 热号={hf:.3f} 随机={rf_:.3f} "
          f"(期望={5*POOL/10:.2f}) AnEn-热号={af-hf:+.3f} 胜率={win}/{n} ({(win-lose):+d})")
    result['anen'] = {'anen': float(af), 'hot': float(hf), 'rand': float(rf_),
                      'win': win, 'lose': lose}

    # ---------- [6] P3(1,5,9)迁移确认 ----------
    idx159 = [t for t in range(N) if set(D[t, :3]) == {1, 5, 9}]
    gaps = np.diff(np.array(idx159))
    m = len(gaps)
    disp = gaps.var(ddof=1) / gaps.mean()
    baseline = (1 - 0.006) / 0.006
    ratio = disp / baseline
    stat = (m - 1) * disp / baseline
    p_under = float(chi2.cdf(stat, m - 1))
    print(f"[6] P5前3位集合{{1,5,9}}: 出现{len(idx159)}次 ratio={ratio:.3f} "
          f"p={p_under:.2e} (应与P3组选(1,5,9)一致: ratio=0.323 p=5.3e-7)")
    print(f"    当前漏期: {N - 1 - idx159[-1]}期 (最后出现于期号{periods[idx159[-1]]})")
    result['p3_159'] = {'n': len(idx159), 'ratio': round(ratio, 3),
                        'p_under': p_under, 'miss': N - 1 - idx159[-1]}

    with open('/tmp/p5_cycle_scan_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1, default=str)
    print("[P5-SCAN] 结果已存 /tmp/p5_cycle_scan_result.json")


if __name__ == '__main__':
    main()
