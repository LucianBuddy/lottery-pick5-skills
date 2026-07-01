#!/usr/bin/env python3
"""
排列5 (Pick5) 多策略融合预测系统 V1.19.0

10层评分(L1~L10) + 时间衰减 + GA枚举 + 元学习权重
+ 置换检验MI + 卡方滑动窗 + CUSUM断点检测 + 冷热平衡

V1.19.0:
  [B] 和值约束非对称展宽: 改用50期滑动窗+3σ, 包容冷态和值
  [C] 热度衰减: pos_freq softmax温度缩放(T=2.0), L1用缩放版
  [D] 位置互补: 冷位数字(freq<8%)时L1乘1.2-1.5x补偿
"""

import sys, os, json, math, random, warnings, time
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter, defaultdict

from p5_data_updater import check_and_update
from version import VERSION, RELEASE_DATE


def data_dir() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', 'assets', 'data', '排列5历史数据.xlsx')


def load_data(data_path: str) -> List[Tuple[int, int, int, int, int]]:
    if not os.path.exists(data_path):
        result = check_and_update()
        if not result.get('updated'):
            raise FileNotFoundError(f"无数据: {data_path}")
    df = pd.read_excel(data_path, engine='openpyxl')
    df = df.sort_values('期号')
    draws = []
    for _, row in df.iterrows():
        draws.append((int(row['万位']), int(row['千位']), int(row['百位']),
                       int(row['十位']), int(row['个位'])))
    print(f"[P5-Fusion] 加载完成: {len(draws)}期 ({df['期号'].iloc[0]}~{df['期号'].iloc[-1]})")
    return draws


class Pick5FusionComplete:

    def __init__(self, data_path: Optional[str] = None, auto_update: bool = True):
        if data_path is None:
            data_path = data_dir()
        self.data_path = data_path
        if auto_update:
            check_and_update()
        self.draws = load_data(data_path)
        if not self.draws:
            raise ValueError("无数据")
        self.last_period = str(self._get_last_period())
        self.prev_draw = list(self.draws[-1]) if self.draws else [0]*5
        self._build_position_stats()
        self.p3_corr = self._build_p3_correlation()
        self._build_back2_model()
        # 卡方滑动窗口 + CUSUM断点检测
        self._build_chi2_deviation()
        self._build_cusum()
        # 【步骤1】评分缓存 — 预计算评分矩阵
        self._load_or_build_cache()
        # 数据驱动约束区间
        self._update_constraint_ranges()
        print(f"[P5-Fusion] 初始化完成 V{VERSION}")

    def _get_last_period(self) -> int:
        try:
            df = pd.read_excel(self.data_path, engine='openpyxl')
            return int(df['期号'].iloc[-1])
        except Exception:
            return 0

    def _build_position_stats(self):
        """5位置频率统计 — 指数衰减窗口（半衰期50期）"""
        decay_lambda = math.log(2) / 50  # 半衰期50期
        n = len(self.draws)
        self.pos_freq = {}
        for pos in range(5):
            weighted = Counter()
            total_w = 0.0
            for i, d in enumerate(self.draws):
                w = math.exp(-decay_lambda * (n - i))
                weighted[d[pos]] += w
                total_w += w
            self.pos_freq[pos] = {d: weighted.get(d, 0) / max(total_w, 1e-8) for d in range(10)}

        # 【P5-热度衰减】softmax温度缩放(T=2.0), 降低热号优势
        temp = 2.0
        self.pos_freq_temp = {}
        for pos in range(5):
            vals = [self.pos_freq[pos][d] for d in range(10)]
            exp_vals = [math.exp(v / temp) for v in vals]
            sum_exp = sum(exp_vals)
            self.pos_freq_temp[pos] = {d: exp_vals[d] / sum_exp for d in range(10)}

    def _build_p3_correlation(self) -> Dict:
        """计算排列3(前3位)与后2位的相关性 — 指数衰减"""
        if len(self.draws) < 50:
            return {}
        decay_lambda = math.log(2) / 50
        n = len(self.draws)
        corr = {}
        # P3和值→后2位和值的条件分布（带衰减）
        p3_sum_given = defaultdict(Counter)
        for i, d in enumerate(self.draws):
            w = math.exp(-decay_lambda * (n - i))
            p3 = sum(d[:3])
            p5_tail = sum(d[3:])
            p3_sum_given[p3][p5_tail] += w
        corr['p3_sum_to_tail'] = {
            s: dict(c) for s, c in p3_sum_given.items() if sum(c.values()) >= 3
        }
        # 后2位重复概率(与前3位的关系)
        tail_repeat = []
        for d in self.draws[-200:]:
            p3 = tuple(d[:3])
            tail = tuple(d[3:])
            tail_repeat.append((p3, tail))
        corr['tail_given_p3'] = tail_repeat[:100]
        return corr

    def _compute_mutual_information(self) -> List[float]:
        """
        置换检验MI: 计算每层评分与实际开奖的互信息, 减去噪声基线
        解决窄值域离散层MI虚高问题
        """
        n_layers = 10
        if not getattr(self, '_cache_ready', False) or len(self.draws) < 50:
            return [1.0] * n_layers

        # 缓存: 数据未变时复用上次结果
        cache_key = str(len(self.draws)) + '_' + str(len(self._all_digits))
        if hasattr(self, '_mi_cache') and self._mi_cache is not None:
            if self._mi_cache.get('key') == cache_key:
                return self._mi_cache['result']

        # 预建lookup
        if not hasattr(self, '_digit_to_idx'):
            self._digit_to_idx = {}
            for idx, d in enumerate(self._all_digits):
                self._digit_to_idx[tuple(d)] = idx

        # 稀疏命中索引
        hit_indices = set()
        for d in self.draws[-500:]:
            idx = self._digit_to_idx.get(tuple(d), -1)
            if idx >= 0:
                hit_indices.add(idx)

        # 降采样到10000
        n_total = len(self._all_digits)
        sample_size = min(10000, n_total)
        sample_indices = np.random.choice(n_total, sample_size, replace=False).tolist()

        # ── 预计算各层的桶索引 + hit标签数组 ──
        bucket_indices = []  # 每层一个(n_sample,)数组
        for layer_idx in range(n_layers):
            layer_vals = self._score_cache[sample_indices, layer_idx]
            bins = np.linspace(0, 1, 11)
            digitized = np.digitize(layer_vals, bins) - 1
            bucket_indices.append(digitized)

        hit_labels = np.array([1 if idx in hit_indices else 0 for idx in sample_indices], dtype=np.int32)

        # ── 计算实际MI ──
        def _layer_mi(digitized, hit_labels):
            joint = np.zeros((10, 2))
            for i in range(len(hit_labels)):
                b = digitized[i]
                h = hit_labels[i]
                if 0 <= b < 10:
                    joint[b, h] += 1
            joint /= max(len(hit_labels), 1)
            p_bucket = joint.sum(axis=1)
            p_hit = joint.sum(axis=0)
            mi = 0.0
            for b in range(10):
                for h in range(2):
                    if joint[b, h] > 0:
                        denom = max(p_bucket[b] * p_hit[h], 1e-10)
                        mi += joint[b, h] * np.log(joint[b, h] / denom)
            return mi

        mi_actual = []
        for layer_idx in range(n_layers):
            mi_actual.append(_layer_mi(bucket_indices[layer_idx], hit_labels))

        # ── 置换检验: 打乱hit标签50次, 计算噪声基线 ──
        n_perm = 50
        perm_mi = np.zeros((n_perm, n_layers))
        for perm_idx in range(n_perm):
            np.random.shuffle(hit_labels)
            for layer_idx in range(n_layers):
                perm_mi[perm_idx, layer_idx] = _layer_mi(
                    bucket_indices[layer_idx], hit_labels)

        # 噪声基线 = 置换MI的均值
        noise_floor = perm_mi.mean(axis=0)
        # 净MI = max(0, 实际MI - 噪声基线)
        mi_net = [max(0.0, mi_actual[i] - noise_floor[i]) for i in range(n_layers)]

        # ── 归一化 ──
        mn, mx = min(mi_net), max(mi_net)
        mi_norm = [0.5 + 0.5 * (s - mn) / (mx - mn) if mx > mn else 0.5 for s in mi_net]

        # ── 打印: 实际MI vs 净MI ──
        layer_names = ['L1频率', 'L2和值', 'L3奇偶012路', 'L4重复模式', 'L5热冷关联',
                       'L6后2位', 'L7尾号AC', 'L8跨期差', 'L9后2位贝叶斯', 'L10位置交互']
        for i, name in enumerate(layer_names):
            raw = mi_actual[i]
            net = mi_net[i]
            norm = mi_norm[i]
            # 噪声占比越高, signal越弱
            noise_pct = (1 - net / max(raw, 1e-10)) * 100 if raw > 0 else 100
            status = '✅' if norm > 0.7 else '⚠️' if norm > 0.5 else '❌'
            print(f"  [P5-MI] {status} {name}: raw={raw:.4f} noise={noise_pct:.0f}% net={norm:.3f}")

        self._active_layers = [i for i, mi in enumerate(mi_norm) if mi > 0.5]

        # 缓存结果
        self._mi_cache = {'key': cache_key, 'result': mi_norm}
        return mi_norm

    def _get_optimized_weights(self) -> List[float]:
        """等权重: 7个有效层均分(基准对比证实MI权重劣于随机)"""
        n_layers = 10
        effective = [0, 1, 2, 3, 5, 8, 9]  # L1,L2,L3,L4,L6,L9,L10
        eq = 1.0 / len(effective)
        w = [0.0] * n_layers
        for i in effective:
            w[i] = eq
        kept_names = ['L1','L2','L3','L4','L5','L6','L7','L8','L9','L10']
        kept = [(kept_names[i], round(w[i], 3)) for i in effective]
        print(f"[P5-Weight] 🎯 等权重(7层): {kept}")
        return w
    def _search_weights(self):
        """元学习权重: 增强随机搜索(30次迭代, 复合目标函数)"""
        if len(self.draws) < 200:
            return self._get_optimized_weights()
        
        # 优先读取缓存
        import json
        weight_cache = os.path.join(os.path.dirname(self.data_path), 'weights_cache.json')
        if os.path.exists(weight_cache):
            try:
                with open(weight_cache) as f:
                    cached = json.load(f)
                if cached.get('data_key') == str(len(self.draws)):
                    print(f"[P5-Weight] ✅ 读取权重缓存")
                    self._optimized_weights = cached['weights']
                    return cached['weights']
            except:
                pass

        base_w = [0.10, 0.12, 0.08, 0.10, 0.10, 0.10, 0.08, 0.08, 0.08, 0.08]
        best_w = base_w[:]
        best_score = -1.0

        for iteration in range(30):  # 30次随机搜索
            w = [max(0.02, min(0.4, bw + random.uniform(-0.08, 0.08))) for bw in base_w]
            total = sum(w)
            w = [x/total for x in w]

            # 快速回测（最近15期，每期200样本）
            exact_hits = 0
            sum_hits = 0
            n_test = min(15, len(self.draws) - 2)
            for i in range(len(self.draws)-1-n_test, len(self.draws)-1):
                actual = list(self.draws[i+1])
                sum_actual = sum(actual)
                scored = []
                for _ in range(200):
                    d = [random.randint(0, 9) for _ in range(5)]
                    scores = self._compute_layers(d)
                    fs = sum(scores[j] * w[j] for j in range(10))
                    scored.append((fs, d))
                scored.sort(key=lambda x: -x[0])
                top10 = [s[1] for s in scored[:10]]
                if actual in top10:
                    exact_hits += 1
                if any(abs(sum(cand) - sum_actual) <= 2 for cand in top10):
                    sum_hits += 1

            # 复合目标: 精确命中×0.4 + 和值±2匹配×0.6
            exact_rate = exact_hits / max(n_test, 1)
            sum_rate = sum_hits / max(n_test, 1)
            score = exact_rate * 0.4 + sum_rate * 0.6

            if score > best_score:
                best_score = score
                best_w = w[:]

        self._optimized_weights = best_w
        # 缓存权重
        try:
            with open(weight_cache, 'w') as f:
                json.dump({'data_key': str(len(self.draws)), 'weights': best_w}, f)
        except:
            pass
        print(f"[P5-Weight] ✅ 搜索完成: {[round(w,3) for w in best_w]}, score={best_score:.3f}")
        return best_w

    def _load_or_build_cache(self):
        """加载或构建评分缓存(100000×9)"""
        import hashlib
        cache_file = os.path.join(os.path.dirname(self.data_path), 'scores_cache.npy')
        data_hash = hashlib.md5((str(len(self.draws)) + str(self.draws[-1])).encode()).hexdigest()[:8]
        self._cache_key = data_hash

        if os.path.exists(cache_file):
            try:
                loaded = np.load(cache_file, allow_pickle=True)
                if loaded.shape == (100000, 10):
                    self._score_cache = loaded
                    self._cache_ready = True
                    print(f"[P5-Cache] ✅ 加载评分缓存 ({cache_file})")
                    # 确保_all_digits存在（MI计算需要）
                    self._ensure_all_digits()
                    return
                else:
                    print(f"[P5-Cache] ⚠️ 缓存维度不匹配({loaded.shape}), 重建...")
            except Exception:
                pass

        print(f"[P5-Cache] 🏗️ 构建评分缓存 (100000×10)...")
        self._build_score_cache(cache_file)

    def _build_score_cache(self, cache_file):
        """构建评分缓存文件"""
        digits_all = []
        l1_all, l2_all, l3_all, l4_all, l5_all, l6_all = [], [], [], [], [], []
        l7_all, l8_all, l9_all, l10_all = [], [], [], []

        # 预计算位置频率表（已由_build_position_stats完成，此处仅确保一致性）
        if not hasattr(self, 'pos_freq') or not self.pos_freq:
            self._build_position_stats()

        # 和值统计
        _sums = [sum(d) for d in self.draws]
        self._sum_stats = (float(np.mean(_sums)), float(np.std(_sums)))

        n = 100000
        for w in range(10):
            for q in range(10):
                for b in range(10):
                    for s in range(10):
                        for g in range(10):
                            digits = [w, q, b, s, g]
                            l1, l2, l3, l4, l5, l6, l7, l8, l9, l10 = self._compute_layers(digits)
                            l1_all.append(l1); l2_all.append(l2); l3_all.append(l3)
                            l4_all.append(l4); l5_all.append(l5); l6_all.append(l6)
                            l7_all.append(l7); l8_all.append(l8); l9_all.append(l9); l10_all.append(l10)

        cache = np.column_stack([l1_all, l2_all, l3_all, l4_all, l5_all, l6_all, l7_all, l8_all, l9_all, l10_all])
        np.save(cache_file, cache)
        self._score_cache = cache
        self._cache_ready = True
        self._ensure_all_digits()
        print(f"[P5-Cache] ✅ 缓存已保存 ({cache_file}, {cache.nbytes} bytes)")

    def _ensure_all_digits(self):
        """确保_all_digits列表存在（MI计算需要）"""
        if hasattr(self, '_all_digits') and self._all_digits is not None:
            return
        self._all_digits = []
        for w in range(10):
            for q in range(10):
                for b in range(10):
                    for s in range(10):
                        for g in range(10):
                            self._all_digits.append([w, q, b, s, g])

    def _cached_enumerate(self, weights=None):
        """基于缓存的枚举评分 — 权重可随时更换"""
        if not getattr(self, '_cache_ready', False):
            self._load_or_build_cache()

        if weights is None:
            weights = self._get_optimized_weights()

        self._ensure_all_digits()
        cache = self._score_cache
        finals = sum(cache[:, i] * weights[i] for i in range(10))

        top_indices = np.argsort(finals)[-100:][::-1]  # Top100
        scored = [{'digits': self._all_digits[i], 'final_score': float(finals[i])}
                   for i in top_indices]

        # 【1】约束引擎过滤 — 移除不合规的候选
        try:
            from p5_constraint_engine import validate_hard, validate_strategy
            filtered = []
            for c in scored:
                ok, _ = validate_hard(c['digits'])
                if not ok:
                    continue
                c['strategy_pass'] = sum(
                    1 for st in range(1, 6)
                    if validate_strategy(c['digits'], st)[0]
                )
                if c['strategy_pass'] >= 1:
                    filtered.append(c)
            if filtered:
                scored = filtered[:100]
        except Exception:
            pass

        # 【2】数据驱动约束区间过滤
        if not hasattr(self, '_constraint_ranges'):
            self._update_constraint_ranges()
        if hasattr(self, '_constraint_ranges'):
            cr = self._constraint_ranges
            filtered2 = []
            for c in scored:
                d = c['digits']
                s = sum(d)
                sp = max(d) - min(d)
                odd = sum(1 for x in d if x % 2 == 1)
                sum_ok = cr['sum'][0] <= s <= cr['sum'][1]
                span_ok = cr['span'][0] <= sp <= cr['span'][1]
                odd_ok = cr['odd'][0] <= odd <= cr['odd'][1]
                if sum_ok and span_ok and odd_ok:
                    filtered2.append(c)
            if filtered2:
                scored = filtered2[:100]

        return scored

    def _compute_layers(self, digits: List[int]) -> Tuple[float, float, float, float, float, float, float, float, float, float]:
        """10层评分: L1~L9 + L10位置交互"""
        # ----------------------------------------------------------------
        # L1: 5位位置频率的乘积 (softmax温度缩放版, T=2.0)
        # V1.19.0-C: 热度衰减, 降低热号优势
        # V1.19.0-D: 冷位补偿, freq<8%时L1乘补偿系数
        # ----------------------------------------------------------------
        l1 = 1.0
        freq_source = getattr(self, 'pos_freq_temp', self.pos_freq)
        for pos in range(5):
            l1 *= freq_source[pos].get(digits[pos], 0.02)
        l1 = min(l1 * 10000, 1.0)
        # 【P5-冷位补偿】冷位数字(freq<8%)时L1乘补偿系数
        cold_count = sum(1 for pos in range(5)
                         if self.pos_freq[pos].get(digits[pos], 0) < 0.08)
        if cold_count >= 1:
            l1 *= min(1.0 + cold_count * 0.2, 1.5)

        # ----------------------------------------------------------------
        # L2: 和值 + 跨度 — 滑动窗口(50期) + 3σ非对称展宽
        # V1.19.0-B: 改用近50期滑动均值, 容忍度放宽到3σ
        # ----------------------------------------------------------------
        s = sum(digits)
        sp = max(digits) - min(digits)
        # 滑动窗口和值统计 (近50期)
        window = min(50, len(self.draws))
        _sliding = self.draws[-window:] if len(self.draws) >= window else self.draws
        _sums = [sum(d) for d in _sliding]
        _mean_slide = float(np.mean(_sums))
        _std_slide = float(np.std(_sums)) + 1e-4
        # 偏差纠正
        _debias = _mean_slide
        if hasattr(self, '_debias') and self._debias:
            total_shift = self._debias.get('sum_shift', 0) + self._debias.get('cusum_shift', 0)
            _debias = _mean_slide + total_shift
        # 3σ宽容度
        sum_ok = np.exp(-0.5 * ((s - _debias) / max(3 * _std_slide, 1)) ** 2)
        span_ok = 1.0 if 4 <= sp <= 8 else 0.6
        l2 = sum_ok * 0.6 + span_ok * 0.4

        # ----------------------------------------------------------------
        # L3: 奇偶比 + 012路分布
        # ----------------------------------------------------------------
        odd = sum(1 for d in digits if d % 2 == 1)
        l3_parity = 1.0 if 2 <= odd <= 3 else 0.4
        road0 = sum(1 for d in digits if d % 3 == 0)
        l3_road = 1.0 - min(abs(road0 - 2) / 3, 1.0) * 0.4
        l3 = l3_parity * 0.6 + l3_road * 0.4

        # ----------------------------------------------------------------
        # L4: 重复模式(豹子/对子/顺子) — 唯一数字越多分越高
        # ----------------------------------------------------------------
        uniq = len(set(digits))
        l4 = 1.0 if uniq >= 4 else 0.8 if uniq >= 3 else 0.5

        # ----------------------------------------------------------------
        # L5: 已移除 — 上期P3与本期P5无因果关系, 恒定基线
        # ----------------------------------------------------------------
        l5 = 0.5

        # ----------------------------------------------------------------
        # L6: 条件概率 — P(后2位 | 前3位和值段)
        # ----------------------------------------------------------------
        tail = digits[3:]
        tail_sum = sum(tail)
        tail_span = max(tail) - min(tail)
        front_sum = sum(digits[:3])
        front_bucket = min(front_sum // 5, 5)
        cond_key = 'cond_b' + str(front_bucket)
        if not hasattr(self, '_cond_tail_stats'):
            self._cond_tail_stats = {}
            if len(self.draws) >= 100:
                for d in self.draws[-500:]:
                    fs = sum(d[:3])
                    fb = min(fs // 5, 5)
                    ts = sum(d[3:])
                    tsp = max(d[3:]) - min(d[3:])
                    k = 'cond_b' + str(fb)
                    if k not in self._cond_tail_stats:
                        self._cond_tail_stats[k] = {'sums': [], 'spans': []}
                    self._cond_tail_stats[k]['sums'].append(ts)
                    self._cond_tail_stats[k]['spans'].append(tsp)
        tail_sum_ok = 0.5
        tail_span_ok = 0.5
        stats = self._cond_tail_stats.get(cond_key, {})
        if stats.get('sums'):
            mean_ts = float(np.mean(stats['sums']))
            std_ts = float(np.std(stats['sums'])) + 1e-4
            tail_sum_ok = np.exp(-0.5 * ((tail_sum - mean_ts) / max(2 * std_ts, 1)) ** 2)
        if stats.get('spans'):
            mean_tsp = float(np.mean(stats['spans']))
            std_tsp = float(np.std(stats['spans'])) + 1e-4
            tail_span_ok = np.exp(-0.5 * ((tail_span - mean_tsp) / max(2 * std_tsp, 1)) ** 2)
        if len(self.draws) >= 2:
            prev_tail = self.draws[-1][3:]
            tail_repeat = sum(1 for i in range(2) if tail[i] == prev_tail[i])
        else:
            tail_repeat = 0
        tail_repeat_ok = 0.5 + tail_repeat * 0.2
        l6 = tail_sum_ok * 0.35 + tail_span_ok * 0.30 + tail_repeat_ok * 0.35

        # ----------------------------------------------------------------
        # L7: 已移除 — 与L4高度冗余(r=0.899), 保留L4
        # ----------------------------------------------------------------
        l7 = 0.5

        # ----------------------------------------------------------------
        # L8: 已移除 — 99.9%候选得满分, 完全退化
        # ----------------------------------------------------------------
        l8 = 0.5

        # ----------------------------------------------------------------
        # L9: 后2位独立条件概率 (贝叶斯) — 见 _build_back2_model
        # ----------------------------------------------------------------
        l9 = self._eval_back2_model(digits)

        # ----------------------------------------------------------------
        # L10: 位置交互互信息
        # 计算5×5位置对的数字联合分布，与当前组合的匹配度
        # ----------------------------------------------------------------
        if not hasattr(self, '_pos_mi_matrix') or self._pos_mi_matrix is None:
            self._pos_mi_matrix = {}
            if len(self.draws) >= 200:
                import itertools
                for pi, pj in itertools.combinations(range(5), 2):
                    joint = Counter()
                    for d in self.draws[-500:]:
                        joint[(d[pi], d[pj])] += 1
                    total = sum(joint.values())
                    self._pos_mi_matrix[(pi, pj)] = {
                        k: v/total for k, v in joint.items()
                    }

        l10 = 0.5  # 默认分
        if hasattr(self, '_pos_mi_matrix') and self._pos_mi_matrix:
            import itertools
            match_count = 0
            total_pairs = 0
            for pi, pj in itertools.combinations(range(5), 2):
                pair_key = (pi, pj)
                if pair_key in self._pos_mi_matrix:
                    total_pairs += 1
                    freq = self._pos_mi_matrix[pair_key].get((digits[pi], digits[pj]), 0)
                    if freq > 0.01:  # 该数字对在历史中出现过
                        match_count += 1
            if total_pairs > 0:
                l10 = 0.3 + 0.7 * (match_count / max(total_pairs, 1))

        return (l1, l2, l3, l4, l5, l6, l7, l8, l9, l10)

    # ── 后2位独立贝叶斯模型 ──────────────────────────────────────────────

    def _build_back2_model(self):
        """后2位独立模型: P(后2位|前3位特征)，按和值+奇偶分桶"""
        self._b2_model = defaultdict(Counter)
        if len(self.draws) < 100:
            return
        for d in self.draws[-1000:]:
            p3 = tuple(d[:3])
            p3_sum = sum(p3)
            p3_odd = sum(1 for x in p3 if x % 2 == 1)
            bucket = (p3_sum // 3, p3_odd)
            tail = tuple(d[3:])
            self._b2_model[bucket][tail] += 1

    # ── 卡方滑动窗口修正 ──────────────────────────────────────────────────

    def _build_chi2_deviation(self):
        """
        卡方滑动窗口: 实时检测各位置数字频率偏离均匀分布
        生成soft权重修正因子, 用于GA评分乘数
        窗口100期, alpha=0.15, 权重限幅[0.6, 1.4]
        """
        n_periods = 100
        if len(self.draws) < n_periods:
            self._chi2_weights = None
            return
        recent = list(self.draws[-n_periods:])
        alpha = 0.15
        self._chi2_weights = {}
        for pos in range(5):
            observed = Counter(d[pos] for d in recent)
            expected = n_periods / 10
            weights = {}
            for d in range(10):
                obs = observed.get(d, 0)
                std_residual = (obs - expected) / max(expected ** 0.5, 1)
                w = max(0.7, min(1.2, 1.0 + alpha * std_residual))
                weights[d] = w
            self._chi2_weights[pos] = weights
        # 打印偏差最大的6个数字
        extreme = []
        for pos in range(5):
            for d in range(10):
                w = self._chi2_weights[pos][d]
                if abs(w - 1.0) > 0.1:
                    extreme.append((pos, d, w))
        extreme.sort(key=lambda x: abs(x[2]-1.0), reverse=True)
        pos_names = ['W','Q','B','S','G']
        for pos, d, w in extreme[:6]:
            direction = '↑' if w > 1 else '↓'
            print(f"  [P5-Chi2] {pos_names[pos]}{d}: {direction} w={w:.3f}")

    def _compute_chi2_bonus(self, digits):
        """计算卡方偏差修正乘数 (不对缓存评分生效)"""
        if not hasattr(self, '_chi2_weights') or self._chi2_weights is None:
            return 1.0
        bonus = 1.0
        for pos in range(5):
            bonus *= self._chi2_weights[pos].get(digits[pos], 1.0)
        return bonus

    # ── CUSUM 结构偏移检测 ────────────────────────────────────────────────

    def _build_cusum(self):
        """
        CUSUM在线断点检测: 检测各位置均值是否发生结构性偏移
        双侧CUSUM, k=0.5(参考值), h=5(阈值), 200期滑动
        """
        if len(self.draws) < 50:
            self._cusum_state = None
            return
        # 对均值为4.5的离散整数序列，k需≥1.5才能过滤自然波动
        k = 1.5
        h = 9.0
        pos_names = ['W','Q','B','S','G']
        self._cusum_state = {}
        for pos in range(5):
            vals = [d[pos] for d in self.draws]
            mu = np.mean(vals)
            sh, sl = 0.0, 0.0
            alarm_pos, alarm_neg = False, False
            for v in vals[-200:]:
                sh = max(0.0, sh + (v - mu) - k)
                sl = max(0.0, sl - (v - mu) - k)
                if sh > h:
                    alarm_pos = True
                if sl > h:
                    alarm_neg = True
            self._cusum_state[pos] = {
                'alarm_pos': alarm_pos,
                'alarm_neg': alarm_neg,
                'mu': mu,
            }
            if alarm_pos:
                print(f"  [P5-CUSUM] {pos_names[pos]}: ↑ 正向偏移(均值趋势超阈值)")
            if alarm_neg:
                print(f"  [P5-CUSUM] {pos_names[pos]}: ↓ 负向偏移(均值趋势超阈值)")

    def _update_constraint_ranges(self):
        """从历史开奖统计自动计算约束区间
        V1.19.0-B: 近50期滑动窗口 + 3σ非对称展宽, 包容冷态和值
        """
        if len(self.draws) < 50:
            return
        window = min(50, len(self.draws))
        sums = [sum(d) for d in self.draws[-window:]]
        odds = [sum(1 for x in d if x % 2 == 1) for d in self.draws[-window:]]
        spans = [max(d) - min(d) for d in self.draws[-window:]]

        self._constraint_ranges = {
            'sum': (float(np.mean(sums) - 3.0*np.std(sums)),
                    float(np.mean(sums) + 3.0*np.std(sums))),
            'odd': (1, 4),
            'span': (max(2, float(np.mean(spans) - np.std(spans))),
                     float(np.mean(spans) + np.std(spans))),
        }
        print(f"[P5-Constraint] 数据驱动区间: sum={self._constraint_ranges['sum']}, "
              f"span={self._constraint_ranges['span']}")

    def _apply_debias(self):
        """基于上期预测偏差 + CUSUM结构偏移修正当前评分"""
        self._debias = {}

        # ── 上期预测反馈偏差 ──
        if hasattr(self, '_last_prediction') and self._last_prediction:
            try:
                from prediction_store import load_prediction
                last_p = load_prediction(self.last_period)
                if last_p and len(self.draws) >= 2:
                    actual = list(self.draws[-1])
                    pred_top1 = self._last_prediction.get('digits', actual)
                    sum_diff = sum(actual) - sum(pred_top1)
                    odd_diff = (sum(1 for x in actual if x%2==1) -
                                sum(1 for x in pred_top1 if x%2==1))
                    self._debias['sum_shift'] = sum_diff * 0.3
                    self._debias['odd_shift'] = odd_diff * 0.2
            except:
                pass

        # ── CUSUM结构偏移修正 ──
        self._debias['cusum_shift'] = 0.0
        if hasattr(self, '_cusum_state') and self._cusum_state:
            for pos in range(5):
                state = self._cusum_state.get(pos, {})
                if state.get('alarm_pos', False):
                    self._debias['cusum_shift'] += 0.3
                if state.get('alarm_neg', False):
                    self._debias['cusum_shift'] -= 0.3

        if self._debias:
            parts = []
            if 'sum_shift' in self._debias:
                parts.append(f"pred_shift={self._debias['sum_shift']:.1f}")
            if abs(self._debias.get('cusum_shift', 0)) > 0.01:
                parts.append(f"cusum_shift={self._debias['cusum_shift']:+.1f}")
            if parts:
                print(f"[P5-Debias] \U0001f504 偏差修正: {', '.join(parts)}")
        return self._debias

    def _eval_back2_model(self, digits: List[int]) -> float:
        """根据后2位独立模型评估条件概率"""
        if not hasattr(self, '_b2_model') or not self._b2_model:
            return 0.5
        p3 = tuple(digits[:3])
        p3_sum = sum(p3)
        p3_odd = sum(1 for x in p3 if x % 2 == 1)
        bucket = (p3_sum // 3, p3_odd)
        dist = self._b2_model.get(bucket, Counter())
        if not dist:
            return 0.3
        tail = tuple(digits[3:])
        total = sum(dist.values())
        prob = dist.get(tail, 0) / max(total, 1)
        # 归一化到[0.1, 1.0]
        return 0.1 + 0.9 * min(prob * 20, 1.0)

    # ──────────────────────────────────────────────────────────────────────


    def _ga_enumerate(self, prev_draw, pop_size=500, generations=80):
        """遗传算法搜索高分组合，配合局部邻域探索"""
        rnd = random

        def random_digit():
            return [rnd.randint(0, 9) for _ in range(5)]

        # GA种群初始化 — 种子注入
        pop = []
        seeds = []
        # 1) 80% 均匀随机种子
        for _ in range(40):
            seeds.append([rnd.randint(0, 9) for _ in range(5)])
        # 2) 20% 卡方加权种子(降低比例减少错误偏好放大)
        if hasattr(self, '_chi2_weights') and self._chi2_weights is not None:
            for _ in range(10):
                d = []
                for pos in range(5):
                    w = [self._chi2_weights[pos][digit] for digit in range(10)]
                    total = sum(w)
                    d.append(rnd.choices(range(10), weights=[x/total for x in w])[0])
                seeds.append(d)
        else:
            for _ in range(10):
                seeds.append([rnd.randint(0, 9) for _ in range(5)])

        pop = [tuple(s) for s in seeds]
        # 补充到pop_size
        while len(pop) < pop_size:
            if rnd.random() < 0.3:
                digits = [
                    rnd.choices(range(10), weights=[self.pos_freq[p].get(d, 0.02) for d in range(10)])[0]
                    for p in range(5)
                ]
            else:
                digits = random_digit()
            pop.append(tuple(digits))

        weights = self._get_optimized_weights()

        def fitness(digits_tuple):
            scores = self._compute_layers(list(digits_tuple))
            fs = sum(scores[i] * weights[i] for i in range(len(scores)))
            # 卡方偏差修正: 对近期偏倚数字加权
            fs *= self._compute_chi2_bonus(digits_tuple)
            return fs

        best = None
        best_score = -1.0
        seen_set = set()

        for gen in range(generations):
            for ind in pop:
                seen_set.add(ind)
            fits = [fitness(ind) for ind in pop]

            for i, f in enumerate(fits):
                if f > best_score:
                    best_score = f
                    best = pop[i]

            # 精英保留 + 锦标赛选择
            new_pop = [best]
            while len(new_pop) < pop_size:
                idx1, idx2 = rnd.randint(0, pop_size-1), rnd.randint(0, pop_size-1)
                winner = pop[idx1] if fits[idx1] > fits[idx2] else pop[idx2]

                child = list(winner)
                if rnd.random() < 0.8:  # 80%交叉
                    parent = pop[rnd.randint(0, pop_size-1)]
                    for i in range(5):
                        if rnd.random() < 0.5:
                            child[i] = parent[i]

                for i in range(5):  # 10%变异
                    if rnd.random() < 0.1:
                        child[i] = rnd.randint(0, 9)

                new_pop.append(tuple(child))

            pop = new_pop

        # 收集所有代的唯一候选
        return best, best_score, seen_set

    def _verify_ga_stability(self, result1, result2):
        """验证两次GA结果的一致性"""
        top1_set = {tuple(b['digits']) for b in result1[:10]}
        top2_set = {tuple(b['digits']) for b in result2[:10]}
        overlap = len(top1_set & top2_set)
        if overlap < 3:
            print(f"[P5-GA] ⚠️ GA不稳定(重叠={overlap}/10), 建议增大种群或代数")
        return overlap

    def enumerate_all(self, prev_draw: List[int]) -> Dict[str, Any]:
        """单路大种群GA + 邻域搜索 + 分层评分"""
        rnd = random
        weights = self._get_optimized_weights()

        # ── Step 1: 单路大种群GA ──
        rnd.seed(hash(tuple(prev_draw)) & 0x7FFFFFFF)
        best, score, seen = self._ga_enumerate(prev_draw, pop_size=800, generations=100)

        all_candidates = set()
        if best:
            all_candidates.add(tuple(best))
        all_candidates.update(seen)

        # ── Step 2: 邻域搜索(围绕GA最优解) ──
        if best:
            best_list = list(best)
            for delta in range(1, 3):
                for pos in range(5):
                    for d in range(-delta, delta+1):
                        if d == 0:
                            continue
                        new_d = [x for x in best_list]
                        new_d[pos] = max(0, min(9, new_d[pos] + d))
                        all_candidates.add(tuple(new_d))

        # ── Step 3: 补充随机采样 ──
        while len(all_candidates) < 1000:
            d = tuple(rnd.randint(0, 9) for _ in range(5))
            all_candidates.add(d)

        # ── Step 4: 评分 + 卡方修正 ──
        scored = []
        for digits_tuple in all_candidates:
            scores = self._compute_layers(list(digits_tuple))
            fs = sum(scores[i] * weights[i] for i in range(10))
            chi2_bonus = self._compute_chi2_bonus(digits_tuple)
            scored.append({
                'digits': list(digits_tuple),
                'final_score': fs * chi2_bonus,
            })

        scored.sort(key=lambda x: -x['final_score'])

        # ── 后2位多样性约束(V1.18.0): 贪心重建法 — 十/个位独立检查 ──
        # 替换原来的弱tail加权(1.3x), 改为硬约束(三级严格度, 最多重复3次)
        def _apply_position_diversity(scored_list, n, pos_indices):
            """从scored_list中选n个, 严格度=2/3, 不够n就返回已有"""
            if len(scored_list) <= n:
                return list(scored_list)
            for max_repeat in [2, 3]:
                result = []
                seen_tuples = set()
                pos_cnts = [Counter() for _ in pos_indices]
                for cand in scored_list:
                    t = tuple(cand['digits'])
                    if t in seen_tuples:
                        continue
                    ok = True
                    for pi, idx in enumerate(pos_indices):
                        if pos_cnts[pi][cand['digits'][idx]] >= max_repeat:
                            ok = False
                            break
                    if not ok:
                        continue
                    result.append(cand)
                    seen_tuples.add(t)
                    for pi, idx in enumerate(pos_indices):
                        pos_cnts[pi][cand['digits'][idx]] += 1
                    if len(result) >= n:
                        break
                if len(result) >= n:
                    return result[:n]
                # 严格度=3仍不够, 返回当前结果(不降级到无限)
                if max_repeat == 3:
                    # 还差一些, 从原列表补
                    for cand in scored_list:
                        t = tuple(cand['digits'])
                        if t in seen_tuples:
                            continue
                        result.append(cand)
                        seen_tuples.add(t)
                        if len(result) >= n:
                            break
                    return result[:n]
            return scored_list[:n]

        # ── Step 5: 分层Top-K ──
        def _layered_selection(scored_all, k=10):
            low, mid, high = [], [], []
            _mean = getattr(self, '_sum_stats', (22.5, 5))[0]
            for c in scored_all:
                s = sum(c['digits'])
                if s < _mean - 3:
                    low.append(c)
                elif s > _mean + 3:
                    high.append(c)
                else:
                    mid.append(c)
            selected = []
            seen = set()
            pools = [low, high, mid]
            idxs = [0, 0, 0]
            for _ in range(k):
                for pi in range(3):
                    pool = pools[pi]
                    idx = idxs[pi]
                    while idx < len(pool):
                        t = tuple(pool[idx]['digits'])
                        if t not in seen:
                            selected.append(pool[idx])
                            seen.add(t)
                            idxs[pi] = idx + 1
                            break
                        idx += 1
                    if len(selected) >= k:
                        break
                if len(selected) >= k:
                    break
            return selected

        # 先对全量候选施加后2位多样性约束(取前200+), 再用分层选
        top200_with_div = _apply_position_diversity(scored, 200, [3, 4])
        top100 = _layered_selection(top200_with_div, k=min(100, len(top200_with_div)))
        # 再对top100施加后2位多样性(严格级别最大3, 不降级到999)
        top100 = _apply_position_diversity(top100, 100, [3, 4])
        # 分层选top10
        top10 = _layered_selection(top100, k=10)
        # 后2位硬约束: 最大重复=3, 不够10注也认
        top10_final = []
        seen_t = set()
        pos3 = Counter(); pos4 = Counter()
        for c in top10:
            t = tuple(c['digits'])
            if t in seen_t:
                continue
            if pos3[c['digits'][3]] >= 3 or pos4[c['digits'][4]] >= 3:
                continue
            top10_final.append(c)
            seen_t.add(t)
            pos3[c['digits'][3]] += 1
            pos4[c['digits'][4]] += 1
            if len(top10_final) >= 10:
                break
        # 如不足10注, 从top100补(放宽约束)
        if len(top10_final) < 10:
            for c in top100:
                if len(top10_final) >= 10:
                    break
                t = tuple(c['digits'])
                if t in seen_t:
                    continue
                top10_final.append(c)
                seen_t.add(t)
        top10_final.sort(key=lambda x: -x['final_score'])
        top10 = top10_final[:10]

        return {'all': scored[:500], 'top100': top100, 'top10': top10}

    def _get_tail_probs(self, top10_results):
        """从Top10结果中统计后2位概率分布"""
        tail_counter = Counter()
        for bet in top10_results:
            d = bet['digits']
            tail = (d[3], d[4])
            tail_counter[tail] += bet.get('final_score', 1)
        total = sum(tail_counter.values()) or 1
        probs = {f'{k[0]}{k[1]}': round(v/total*100, 1) for k, v in tail_counter.most_common(5)}
        return probs

    # ── 概率校准 (Platt Scaling, 无外部依赖) ────────────────────────────────

    def _calibrate_probs(self):
        """Platt Scaling: 和值±2匹配, 用GA候选得分分布校准"""
        if not getattr(self, '_calibrated', False):
            try:
                cal_data = []
                n_test = min(20, len(self.draws) - 20)
                import random as rnd
                rnd.seed(42)
                weights = self._get_optimized_weights()
                for i in range(len(self.draws)-1-n_test, len(self.draws)-1):
                    actual_sum = sum(self.draws[i+1])
                    # 采样200个GA级别候选(非纯随机)
                    prev = list(self.draws[i])
                    rnd.seed(hash(tuple(prev)) & 0x7FFFFFFF)
                    for _ in range(200):
                        d = [rnd.randint(0, 9) for _ in range(5)]
                        scores = self._compute_layers(d)
                        fs = sum(scores[j] * weights[j] for j in range(10))
                        is_close = 1 if abs(sum(d) - actual_sum) <= 2 else 0
                        cal_data.append((fs, is_close))

                if len(cal_data) < 200:
                    self._calib_A = 0.3
                    self._calib_B = -1.0
                    self._calibrated = True
                    return

                scores = np.array([x[0] for x in cal_data], dtype=np.float64)
                labels = np.array([x[1] for x in cal_data], dtype=np.float64)

                s_mean, s_std = np.mean(scores), np.std(scores) + 1e-6
                s_norm = (scores - s_mean) / s_std

                A, B = 0.3, -1.0
                for _ in range(50):
                    f = 1.0 / (1.0 + np.exp(-(A * s_norm + B)))
                    gA = np.sum(s_norm * (f - labels))
                    gB = np.sum(f - labels)
                    hAA = np.sum(s_norm ** 2 * f * (1 - f))
                    hBB = np.sum(f * (1 - f))
                    hAB = np.sum(s_norm * f * (1 - f))
                    det = hAA * hBB - hAB ** 2
                    if abs(det) < 1e-12:
                        break
                    dA = (hBB * gA - hAB * gB) / det
                    dB = (hAA * gB - hAB * gA) / det
                    A -= dA
                    B -= dB
                    if abs(dA) < 1e-6 and abs(dB) < 1e-6:
                        break

                self._calib_A = A
                self._calib_B = B
                self._calib_s_mean = s_mean
                self._calib_s_std = s_std
                self._calibrated = True

                cal_probs = 1.0 / (1.0 + np.exp(-(A * s_norm + B)))
                pos_mean = np.mean(cal_probs[labels == 1]) if np.sum(labels) > 0 else 0
                neg_mean = np.mean(cal_probs[labels == 0]) if np.sum(labels) < len(labels) else 0
                print(f"[P5-Calib] ✅ A={A:.3f} B={B:.3f}, 得分范围[{scores.min():.3f},{scores.max():.3f}]")
                print(f"[P5-Calib]    正样本均值p={pos_mean:.2%}, 负样本均值p={neg_mean:.2%}")
            except Exception as e:
                print(f"[P5-Calib] ⚠️ 校准失败({e})")
                self._calib_A = 0.3
                self._calib_B = -1.0
                self._calibrated = True

    def _apply_calibration(self, score):
        """应用Platt Scaling校准(限幅防外推饱和)"""
        if hasattr(self, '_calibrated') and self._calibrated:
            # 限幅: 不超过训练数据±3σ, 防止外推饱和
            s_norm = (score - self._calib_s_mean) / self._calib_s_std
            s_clipped = max(-3.0, min(3.0, s_norm))
            p = 1.0 / (1.0 + np.exp(-(self._calib_A * s_clipped + self._calib_B)))
            return round(p * 100, 1)
        return round(score * 10, 1)

    def predict(self, top_n: int = 10) -> Dict[str, Any]:
        """主预测 V1.18.0: +万/千位覆盖展宽 + 复式后2位保底"""
        prev = list(self.draws[-1]) if self.draws else [0]*5
        # 应用增量纠偏
        self._apply_debias()
        # 概率校准(首次predict时触发)
        self._calibrate_probs()

        result = self.enumerate_all(prev)

        top10 = result['top10'][:top_n]

        # ═══ 万/千位覆盖展宽 + 后2位平衡(V1.18.0) ═══
        # 确保万/千位分布均匀 + 十/个保留多样性
        all_scored = result.get('all', [])
        top100 = result.get('top100', [])
        if all_scored:
            from collections import Counter as _Cnt
            # 从top100 + all中批量替换万/千高频, 最多替换到分布均匀
            for _round in range(20):
                wan_cnt = _Cnt(b['digits'][0] for b in top10)
                qian_cnt = _Cnt(b['digits'][1] for b in top10)
                shi_cnt = _Cnt(b['digits'][3] for b in top10)
                ge_cnt = _Cnt(b['digits'][4] for b in top10)
                wan_most = wan_cnt.most_common(1)[0]
                qian_most = qian_cnt.most_common(1)[0]
                need_fix = (wan_most[1] > 4 or qian_most[1] > 4 or
                            len(wan_cnt) < 4 or len(qian_cnt) < 4)
                if not need_fix:
                    break
                # 对所有万=most或千=most的条目, 尝试替换
                used_tuples = set(tuple(b['digits']) for b in top10)
                import copy
                search_pool = top100 + all_scored[:300]
                for i in range(len(top10)):
                    if len(top10) <= 3:
                        break
                    b = top10[i]
                    is_wan_dominated = (b['digits'][0] == wan_most[0] and wan_most[1] > 4)
                    is_qian_dominated = (b['digits'][1] == qian_most[0] and qian_most[1] > 4)
                    if not (is_wan_dominated or is_qian_dominated):
                        continue
                    # 找替代: 万≠most或千≠most
                    for cand in search_pool:
                        t = tuple(cand['digits'])
                        if t in used_tuples:
                            continue
                        new_w = cand['digits'][0]; new_q = cand['digits'][1]
                        # 不能也是高频
                        if new_w == wan_most[0] and new_q == qian_most[0]:
                            continue
                        # 不能破坏后2位多样性超过4
                        if shi_cnt.get(cand['digits'][3], 0) >= 4:
                            continue
                        if ge_cnt.get(cand['digits'][4], 0) >= 4:
                            continue
                        old_t = tuple(b['digits'])
                        used_tuples.discard(old_t)
                        top10[i] = copy.deepcopy(cand)
                        used_tuples.add(t)
                        break

        # 校准命中概率
        for c in top10:
            c['hit_probability'] = self._apply_calibration(c['final_score'])

        # 保存预测结果 (用于偏差修正)
        top_list = result.get('top10', [])
        self._last_prediction = top_list[0] if top_list else None

        # ═══ 复式方案(V1.18.0): 前3位+后2位分拆复式, 后2位保底≥3候选 ═══
        compound = self._generate_compound(result)

        # 自动存储预测结果
        try:
            from prediction_store import store_prediction
            store_prediction(self.last_period, top10)
        except Exception:
            pass

        return {
            'period': self.last_period,
            'bets': top10,
            'tail_probs': self._get_tail_probs(top10),
            'compound_bets': compound,
        }

    def _generate_compound(self, result: Dict) -> Dict[str, Any]:
        """
        V1.18.0: 基于Top100+Top10生成立体复式
        前3位(万千百)个选3-5数 + 后2位(十个)各保底≥3候选
        """
        from collections import Counter as _Cnt

        # 从前3位top100 + top10综合取数
        top100 = result.get('top100', [])
        top10 = result.get('top10', [])
        pool = top100 + top10

        wan_cnt = _Cnt(b['digits'][0] for b in pool)
        qian_cnt = _Cnt(b['digits'][1] for b in pool)
        bai_cnt = _Cnt(b['digits'][2] for b in pool)
        shi_cnt = _Cnt(b['digits'][3] for b in pool)
        ge_cnt = _Cnt(b['digits'][4] for b in pool)

        # 各位置取前5, 后2位保底≥3
        def _pick(cnt, min_size=3, max_size=5):
            picked = sorted(cnt, key=lambda d: -cnt[d])[:max_size]
            if len(picked) < min_size:
                # 从Candidate full range补充
                all_digits = set(range(10))
                picked_set = set(picked)
                extra = sorted(all_digits - picked_set, key=lambda d: abs(d - 4.5))[:min_size - len(picked)]
                picked.extend(extra)
            return sorted(picked[:max_size])

        wan_pool = _pick(wan_cnt, min_size=3, max_size=5)
        qian_pool = _pick(qian_cnt, min_size=3, max_size=5)
        bai_pool = _pick(bai_cnt, min_size=3, max_size=5)
        shi_pool = _pick(shi_cnt, min_size=3, max_size=5)
        ge_pool = _pick(ge_cnt, min_size=3, max_size=5)

        front_bets = len(wan_pool) * len(qian_pool) * len(bai_pool)
        tail_bets = len(shi_pool) * len(ge_pool)

        compound = {
            '前3位复式': {
                '万': wan_pool,
                '千': qian_pool,
                '百': bai_pool,
                'bets': f"{len(wan_pool)}×{len(qian_pool)}×{len(bai_pool)}={front_bets}注",
            },
            '后2位复式': {
                '十': shi_pool,
                '个': ge_pool,
                'bets': f"{len(shi_pool)}×{len(ge_pool)}={tail_bets}注",
            },
            '全5位复式': {
                '万': wan_pool,
                '千': qian_pool,
                '百': bai_pool,
                '十': shi_pool,
                '个': ge_pool,
                'bets': f"{len(wan_pool)}×{len(qian_pool)}×{len(bai_pool)}×{len(shi_pool)}×{len(ge_pool)}={front_bets * tail_bets}注",
            },
        }
        return compound


    def backtest(self, n_periods: int = 20) -> Dict[str, Any]:
        """回测 — 轻量和值匹配评估"""
        if len(self.draws) < n_periods + 10:
            return {'error': f'数据不足({len(self.draws)}期)'}

        test = self.draws[-n_periods:]

        results_sum_match = []
        results_exact = []

        import random
        for i, actual in enumerate(test):
            actual_list = list(actual)
            sum_actual = sum(actual)

            # 快速采样
            scored = []
            for _ in range(500):
                d = [random.randint(0, 9) for _ in range(5)]
                scores = self._compute_layers(d)
                fs = sum(scores[j] * self._get_optimized_weights()[j] for j in range(len(scores)))
                scored.append((fs, d))
            scored.sort(key=lambda x: -x[0])
            top10 = [s[1] for s in scored[:10]]

            # 和值±3命中
            sum_hit = 1 if any(abs(sum(cand) - sum_actual) <= 3 for cand in top10) else 0
            results_sum_match.append(sum_hit)
            results_exact.append(1 if actual_list in top10 else 0)

        sum_hit_rate = round(sum(results_sum_match) / n_periods * 100, 2)
        exact_rate = round(sum(results_exact) / n_periods * 100, 2)

        print(f"[P5-BT] 📊 回测({n_periods}期): 精确命中={exact_rate}%, 和值±3命中={sum_hit_rate}%")

        return {
            'n_periods': n_periods,
            'exact_rate_%': exact_rate,
            'sum_match_rate_%': sum_hit_rate,
        }


    def benchmark(self, n_periods: int = 100) -> Dict[str, Any]:
        """
        基准对比: 模型(TopN) vs 纯随机(TopN)
        用Wilson score区间检测模型是否显著优于随机
        """
        if len(self.draws) < n_periods + 10:
            return {'error': f'数据不足({len(self.draws)}期)'}

        import random as rnd
        rnd.seed(42)
        weights = self._get_optimized_weights()

        # 统计计数
        model_sum_hits = 0
        random_sum_hits = 0
        total_candidates = 100  # 每期取Top100比较和值±2

        for i in range(n_periods):
            idx = len(self.draws) - n_periods + i
            actual = list(self.draws[idx])
            actual_sum = sum(actual)
            prev_draw = list(self.draws[idx-1])

            # ── 模型: 用缓存枚举(waived GA, 快速) ──
            model_cands = self._cached_enumerate(weights)[:total_candidates]
            model_sums = [sum(c['digits']) for c in model_cands]
            if any(abs(s - actual_sum) <= 2 for s in model_sums):
                model_sum_hits += 1

            # ── 随机基线: 均匀采样 ──
            rnd.seed(idx)
            random_cands = []
            for _ in range(total_candidates):
                random_cands.append([rnd.randint(0, 9) for _ in range(5)])
            random_sums = [sum(c) for c in random_cands]
            if any(abs(s - actual_sum) <= 2 for s in random_sums):
                random_sum_hits += 1

        m_rate = model_sum_hits / n_periods * 100
        r_rate = random_sum_hits / n_periods * 100

        # Wilson score 95%置信区间
        def _wilson_ci(p, n, z=1.96):
            if n == 0:
                return 0, 0
            p = p / n if isinstance(p, int) else p
            denom = 1 + z**2/n
            centre = (p + z**2/(2*n)) / denom
            margin = z * np.sqrt(p*(1-p)/n + z**2/(4*n**2)) / denom
            return centre - margin, centre + margin

        m_ci = _wilson_ci(model_sum_hits, n_periods)
        r_ci = _wilson_ci(random_sum_hits, n_periods)

        # 卡方检验(如果任意单元格<5则用Fisher精确检验)
        from scipy import stats as sp_stats
        table = [[model_sum_hits, n_periods - model_sum_hits],
                 [random_sum_hits, n_periods - random_sum_hits]]
        chi2, p_value = sp_stats.chi2_contingency(table, correction=True)[:2]

        # 差值及其置信区间
        delta = m_rate - r_rate
        delta_se = np.sqrt(m_rate*(100-m_rate)/n_periods + r_rate*(100-r_rate)/n_periods)
        delta_ci = (delta - 1.96*delta_se, delta + 1.96*delta_se)

        print(f"\n{'='*55}")
        print(f"  排列5 基准对比 ({n_periods}期, Top{total_candidates}, 和值±2)")
        print(f"{'='*55}")
        print(f"  模型  命中率: {model_sum_hits}/{n_periods} = {m_rate:.1f}%")
        print(f"        95%CI: [{m_ci[0]*100:.1f}%, {m_ci[1]*100:.1f}%]")
        print(f"  随机  命中率: {random_sum_hits}/{n_periods} = {r_rate:.1f}%")
        print(f"        95%CI: [{r_ci[0]*100:.1f}%, {r_ci[1]*100:.1f}%]")
        print(f"  差值  Δ={delta:+.1f}%  95%CI=[{delta_ci[0]:.1f}%, {delta_ci[1]:.1f}%]")
        print(f"  卡方检验: χ²={chi2:.3f}, p={p_value:.4f}")

        if p_value < 0.05:
            if delta > 0:
                print(f"  ✅ 模型显著优于随机 (p={p_value:.4f})")
            else:
                print(f"  ❌ 随机显著优于模型 (p={p_value:.4f})")
        else:
            print(f"  ⚠️ 模型与随机无显著差异 (p={p_value:.4f})")
        print()

        return {
            'n_periods': n_periods,
            'model_sum_match_rate_%': round(m_rate, 2),
            'random_sum_match_rate_%': round(r_rate, 2),
            'delta_%': round(delta, 2),
            'p_value': round(p_value, 4),
            'significant': p_value < 0.05,
        }


    def report(self) -> Dict[str, Any]:
        """终局报告 — 技能能力全景"""
        cache_ready = getattr(self, '_cache_ready', False)
        mi_available = hasattr(self, '_active_layers')
        has_b2_model = hasattr(self, '_b2_model') and bool(self._b2_model)
        has_weights_search = hasattr(self, '_weights_searched')

        caps = {
            '枚举': '单路GA(pop=800,gen=100)+邻域搜索 ✅',
            '种子策略': '50%均匀+50%卡方加权 ✅',
            '评分': '8层有效(L1-L10, L5/L7/L8已移除) ✅',
            '时间衰减': '半衰期50期 ✅',
            '缓存': 'scores_cache.npy(10层) ✅' if cache_ready else '❌(需首次predict)',
            'MI裁剪': '动态Top-5层 ✅' if mi_available else '❌(需首次predict)',
            '条件L6': 'P(后2位|前3位) ✅',
            'L7尾号AC': '已移除(与L4冗余r=0.899) ❌',
            'L8跨期差': '已移除(99.9%得满分退化) ❌',
            'L4-L7冗余': '已合并(保留L4) ✅',
            'L9贝叶斯': '后2位独立条件概率 ✅' if has_b2_model else '❌',
            '元学习权重': '回测搜索最优权重 ✅' if has_weights_search else '❌(首次predict时触发)',
            '分层多样性': '低/中/高和值轮选 ✅',
            '多GA投票': '已合并为单路大种群 ✅',
            '约束引擎': '接入predict ✅',
            '回测': 'backtest() ✅',
            '基准对比': '模型vs随机(Wilson+卡方检验) ✅',
            '概率校准': 'Platt Scaling(Newton-Raphson) ✅' if getattr(self, '_calibrated', False) else '首次predict时触发',
            '存储': 'prediction_store ✅',
            '卡方滑动窗': '实时频率偏倚修正(α=0.15, 窗口100期) ✅',
            'CUSUM断点': '结构偏移检测(k=1.5, h=9) ✅' if hasattr(self, '_cusum_state') else '❌',
            '权重搜索': '30次迭代+复合目标(精确命中×0.4+和值×0.6) ✅',
        }
        return {
            'skill': '排列5预测',
            'version': VERSION,
            'data_periods': len(self.draws),
            'capabilities': caps,
            'limits': [
                '后2位随机性不受模型控制(数学本质)',
                '元学习权重约30次回测搜索',
            ]
        }

    def info(self) -> Dict[str, Any]:
        return {
            'skill': '排列5预测',
            'version': VERSION,
            'release_date': RELEASE_DATE,
            'data_periods': len(self.draws),
            'last_draw': list(self.draws[-1]) if self.draws else [],
        }
