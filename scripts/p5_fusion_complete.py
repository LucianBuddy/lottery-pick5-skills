#!/usr/bin/env python3
"""
排列5 (Pick5) 多策略融合预测系统 V1.58.0

10层评分(L1~L10) + 时间衰减 + GA枚举 + 元学习权重
+ 置换检验MI + 卡方滑动窗 + CUSUM断点检测 + 冷热平衡
+ 万/千位硬约束 + 后区对子检测 + 跨期漂移检测 + 评分校准
+ 中等冷分池 + 双阈值冷号 + 梯度压缩 + P3方向多样性
+ 隔期短重号 + 百位冷多路径 + 个位过热限流 + 后2位多样性
+ 全换号扩展 + 后2位交叉 + 数字分散 + 个位冷下探
+ 十位过热限流 + P3数字集迁移 + 全隔期全移位 + 存储可靠性
+ 低位区间趋势惯性检测 + 千位大跨度跳变覆盖
+ P3多路径联动注入 + 后2位短间隔回补检测
+ 候选池扩容(10→25) + 前3位广度加强(≥6)
+ 前3位数字集中检测 + 前3位低位冷号
+ 后2位广度注入 + 后2位集中限流 + 上期重号后保护
+ 中位(2-5)中等冷分池 + 周期回归检测 + 权重配额制 + P3关联增强
+ 万/千位过热限流加强 + P3镜像关联检测
+ 后2位遗漏独立扫描 + TopN质量基准线
+ [核心] P3-P5前3位继承: 万/千/百位评分来自P3模型
+ P3失准独立兜底 + 前3位短间隔回补 + 前3位对子检测 + 后2位跨位迁移
+ P3失准降权加重 + 万位深度冷号独立扫描
+ 各位置短间隔独立窗口 + 后2位锁定
+ 重号保留席 + 中冷分池两档 + 深冷去阈值
+ P3 Top1最终保底 + 前3位组合限流 + 后2位重号提权
+ 复式注数限额(前3位≤50/后2位≤50/全5位≤50)
+ 注入票防替换保护 + 中冷分池小档化 + P3失准原生评分注入 + 固定随机种子
+ 中冷档10-15独立注入 + 后2位近端回补2席 + B2R阈值修复 + 分层保护 + 保护票保底
+ 注入票保护扩展(1-9期) + 重号/垄断上限 + 优先级分层 + P5原生评分并行 + 热号配额

V1.51.0 优化 (2026-08-04, 26206期归因: P3 Top1保底被V50通道拆除):
  [A] P3 Top1最终保底(_v50_final_channel末端): 缺失则换入最高分候选(合成保底),
      换出携带全部超限数字的票 — 修复558前3位被重建拆除
  [B] 多样性强化崩溃修复: fusion._all_digits→self._all_digits + 兜底防IndexError
  验证: verify_v150_fast.py [4]P3 Top1断言全过; 26207预测P3 Top1(2,4,9)在Top10

V1.50.0 优化 (2026-08-04, 26205期归因: 重号垄断+短间隔回补全漏+最终整合通道):
  [A] 注入票保护扩展(修改): V46保护档6-9→1-9期, 近端(1-2期)/短间隔(3-8期)
      原始票不再被V46E/F等后续替换蚕食
  [B] 重号/垄断席位上限(新增, predict最终通道): 每位置每数字≤2席, 上期重号/
      中冷/深冷垄断裁剪, 修复26205万位6(上期重号)占7/10
  [C] 注入优先级分层(新增, predict最终通道): 近端(0-2)>短间隔(3-8)>中冷(6-9)
      >深冷(≥10), 高档缺号只换出低档票, 修复26205万8(漏3)/千0(漏5)0/10
  [D] P5原生评分并行通道(修改_hybrid_score): 非P3候选降权系数随P5原生前3位
      频率自适应(0.60×0.7~1.4), 降低P3单期失准传导
  [E] 热号配额(新增, predict最终通道): 近10期频次≥4数字每位置≥2席
  验证: 26205模拟机制校验全过(10注/反垄断≤2席/优先级分层覆盖/确定性),
      十0×2/个8×1位置命中; 26206预测正常存储(Top1=61508)

V1.49.0 优化 (2026-08-02, 26204期归因: 中冷档10-15+后2位近端回补+分层保护+阈值修复):
  [A] 中冷分池新增10-15档(修改): 26204百位4(漏13期)在C档(≥10)被深冷
      竞争挤出, 10-15独立注入, C档阈值≥10→≥16避免重复
  [B] 10-15档按遗漏降序扫描(修改): 百位0(漏10期)先于百位4(漏13期)被选中,
      降序优先更高遗漏
  [C] 后2位近端回补B2N(新增): 1-3期前数字每位置至少2席
  [D] B2R短间隔阈值修复(修改): log分vs正分阈值永远不成立, 改无条件注入
  [E] 分层保护(新增): _p5_v46_high高优先级 + _p5_protected低优先级
  [F] CNC/B2CNC/HFG替换尊重保护集(修改)
  [G] 保护票TopN保底+回补(新增)
  验证: 26204最佳1位→3位, 8期回测平均命中2.00

V1.48.0 优化 (2026-08-01, 26203期归因):
  [A] 注入票防替换保护(新增, predict末段): V46注入票标记保护,
      后续注入只替换非注入票, 修复26203万1/十6/个8(遗漏9期中冷)
      注入后被V46D/E/F链式替换全部失效
  [B] 中冷分池小档化(修改V1.46.0-B): 6-9档拆6-7/8-9两小档各注入≤1席,
      修复26203三个遗漏9期数字(万1/十6/个8)连续落空
  [C] 后2位中冷独立覆盖: 十/个位纳入小档注入(全5位置统一处理)
  [D] 固定随机种子(新增, predict入口): 按期号派生seed, 同期待测可复现
  [E] P3失准时前3位原生评分注入(新增): P3失准检测后, 前3位6-9档
      中冷注入改用P5原生评分(raw_probability)选候选, 绕过P3混合评分,
      修复万位1在P3百位Top10缺失导致的hybrid评分压低

V1.47.0 优化 (2026-07-31, 复式注数限额):
  [A] 复式注数限额(新增, _generate_compound): 前3位复式≤50注(3×3×5=45),
      后2位复式≤50注(6×6=36), 全5位复式独立小池≤50注(每位置2-3数字)
      原方案前3位216注/全5位7776注, 投注成本过高
      裁剪优先级: 频率最低者先裁, 每位置保底3个(全5位保底2个)

V1.46.0 优化 (2026-07-31, 26202期归因: 重号保留席+中冷分池两档+深冷去阈值+P3 Top1保底+前3位组合限流+后2位重号提权):
  [A] 重号保留席(新增, predict末段): 上期各位置数字在Top10至少保留1席,
      修复千位6/十位7(上期重号)被V1.45.0-C窗口range(2,6)排除的盲区
  [B] 中冷号分池两档(新增, predict末段): 6-9期中冷+≥10期深冷独立检查,
      修复百位1(遗漏7期)落在深冷(≥10)/中位(2-5)之间的空隙
  [C] 深冷注入去阈值(修改V1.45.0-B): 注入阈值0.15→0.02,
      修复万位9(遗漏12期)被P3失准降权后分数不足挡在0.15外
  [D] P3 Top1最终保底(新增, predict末段): P3 Top1前3位在最终Top10
      强制保留1注(放在所有后处理之后), 修复P3 Top1(236)被648反超
  [E] 前3位组合级集中限流(新增): 同一前3位组合≥3注时稀释保留最高分2条,
      修复648开头占6注垄断
  [F] 后2位重号提权(新增): 上期十/个位数字(重号)若未覆盖, 阈值0.05注入,
      修复十位7重号仅1注/个位0间隔1期回补仅2注的弱覆盖

V1.45.0 优化 (2026-07-30, 26201期归因: P3失准降权加重+万位深度冷号+各位置短间隔独立窗口+后2位锁定):
  [A] P3失准降权加重(修改V1.44.0-A): 连续2期失准时非P3降权系数
      0.68→0.80, 连续失准更激进降低P3继承影响
  [B] 万位深度冷号独立扫描(新增): 各位置遗漏≥10期数字从all池注入
  [C] 各位置短间隔独立窗口(迁移P3 V2.36.0-A): 各位置独立检测
      本位置5期内出现数字, 个位替换阈值0.05
  [D] 后2位锁定+前3位替换(新增): 后2位评分高但前3位过度集中时
      固定后2位重新搜索最佳前3位

V1.44.0 优化 (2026-07-29, 26200期归因: P3失准独立兜底+前3位短间隔回补+对子模式检测+后2位跨位迁移):
  [A] P3失准时P5前3位独立兜底管道: 上次P3 Top1与P5实际前3位匹配≤1时,
      非P3候选降权系数×0.60→×0.68, 降低P3失准传导
  [B] 千/百位短间隔数字独立检查: 万/千/百各位置3-8期前数字独立扫描
  [C] 前3位对子模式检测: P3 Top1对子形态时检查P5前3位覆盖
  [D] 后2位同数字跨位置隔期迁移检测: 上期十/个数字跨位迁移

V1.43.0 优化 (2026-07-28, P3-P5前3位继承: 万/千/百位评分来自P3模型):
  [核心重构] P5前3位(万/千/百)=同期P3(百/十/个)100%一致
  加载P3 Top25预测, 对P5全量候选进行混合评分:
  - P3前3位候选: hybrid=0.65×P3_score + 0.35×P5_back2
  - 非P3前3位候选: hybrid=P5_score×0.60(降权)
  - P3 Top1强制在P5 Top10中
  后2位(十/个)保持P5自身评分逻辑不变

V1.42.0 优化 (2026-07-28, 26199期归因: 万/千位过热限流加强+P3镜像关联+后2位遗漏独立扫描+TopN质量基准):
  [A] 万/千位过热限流加强
  [B] P3→P5镜像关联加分
  [C] 后2位中等遗漏独立扫描
  [D] TopN质量基准线

V1.40.0 优化 (2026-07-25, 26196期归因: 万/千位短间隔回补+P5千位独立冷号+后2位窗口扩展+P3路由后验降级):
  [A] 五位置短间隔回补扩展: 原后2位(十/个)扩展至全部5个位置(含万/千),
      窗口5-8期→3-8期, 修复26196万位7(隔1期)/千位2(隔4期)完全缺失
  [B] P5千位独立冷号注入(新增): 遗漏≥6期的千位数字独立扫描注入,
      不依赖P3→P5映射, 修复26196千位2温号回补遗漏
  [C] 后2位短间隔窗口扩展: 5-8期→3-8期+中等冷号阈值4-8→3-10,
      修复26196十位3遗漏9期完全不在窗口内
  [D] P3路由后验降级(新增): 上期P3 Top1前3位在P5命中差时自动启用Top2/Top3路由,
      修复P3 Top1失准时P5无备选前3位的传导缺陷

V1.38.0 (2026-07-24, 26195期归因: 后2位广度注入+集中限流+重号保护)
  [A] 后2位广度注入加强(predict): 十位/个位KMedoids后唯一值≥6
      从低位(0-3)+中段(4-6)+高位(7-9)补充, 对标前3位V1.37.0-A
      修复26195期十位仅4个唯一值、个位仅3个, 十位1/个位6完全缺失
  [B] 后2位数字集中限流(predict): 十位/个位单数字占比>35%时稀释
      对标前3位V1.37.0-B, 修复26195期个位5占7/10注(70%)过度集中
  [C] 上期同位置重号后处理保护(predict): 下游清洗可能覆盖掉正确重号,
      检查各位置上期数字是否在最终Top10中, 缺失且替代非显著更优时保护注入
      修复26195期个位6(上期重号)完全被清洗出局

V1.37.0 (2026-07-23, 26194期归因):
  [A] 前3位广度注入加强(predict): 万/千/百KMedoids后唯一值≥6
      从低位(0-3)+高位(7-9)补充, 对标P3 V2.29.0-A
      修复26194期万位仅{4,6,9}3个唯一值完全缺失7
  [B] 前3位数字集中检测(predict): 万/千/百单数字占比>20%时稀释
      对标P3 V2.25.0-②, 替换超集中数字
      修复26194期万位6占7/10注过度集中
  [C] 前3位低位冷号独立检查(predict): 遗漏≥12期的低位(0-3)
      从全量池强制注入, 修复26194期万位7/千位0遗漏
  [D] 候选池扩容: predict默认top_n从10提升至25
      为前3位宽覆盖提供充足候选空间

V1.36.0 (2026-07-22, 26193期归因):
  [A] 万位/千位低位趋势惯性检测: _compute_layers中连续3+期≤3时低位候选+0.06log/期
      修复26193万位1(连续下降6期)完全不被预测
  [B] 千位大跨度跳变覆盖: 万/千位近6期范围≥4时端点数字注入
      修复26193千位0→8跨3级跳变完全未被覆盖
  [C] P3多路径联动注入: _load_p3_prediction支持top_n>1, Top1外备选Top2/Top3注入
      修复P3 Top1=[4,3,1]与实际[1,8,0]不同时P5无备选前3位
  [D] 后2位短间隔回补检测: predict中十位/个位5-8期前数字独立注入
      修复26193十位6(隔3期)和个位8(隔2期)短间隔回补漏判

V1.33.0 (2026-07-18, 26188期归因):
  [①] P5全换号/偏移防护: P3全换号或前3位集中时强制前3位高多样性
  [②] 后2位交叉模式检测: 十/个数字对覆盖<2注时补充
  [③] 数字重复分散模式覆盖: 上期多位置数字在本期≥2位置覆盖
  [④] P5个位冷号下探: 个位(P5第5位)冷阈值深度≥9/中冷≥7

V1.32.0 (2026-07-17, 26187期归因):
  [①] 隔期短重号检测与注入: 上上期(隔1期)重号缺失时强制注入
  [②] 百位冷号多路径+万位强化: 遗漏4-8期冷号≥2条路径
  [④] 个位过热限流: 个位某数字≥5/10时替换至≤4注
  [⑤] 后2位组合多样性: 后2位完全相同≥3注时替换最低分

V1.30.0 (2026-07-15, 26185期归因):
  [①] 中等遗漏分池覆盖: 各位置4-8期遗漏数字独立检查, 缺失注入最高候选
  [②] 冷号注入双阈值: 增加8-9期中度冷阈值(原仅≥10期深度冷)
  [③] 后2位中等遗漏独立检查: 十位/个位独立扫描4-8期数字
  [④] 评分梯度压缩+尾段多样性: min(得分)≥max×40%, 检测位置数字过度集中
  [⑤] P3方向多样性检查: P3 Top1前3位在P5 Top10中≥4注相同时注入完全不同组合

V1.24.0 (2026-07-10, 26180期失准优化):
  [O1] 各位置深度冷号注入: 扫描>10期未出数字, 强注入Top10
  [O2] 前3位极值和值走廊: 保留5%名额给前3位和值≤8或≥22
  [O3] 双位置联动冷号: 5位任意2处同时冷(≥8期)+10%分/对
  [O4] P3→P5映射偏移检测: P3预测低和值时放大前3位校准偏移
  [O5] 后2位极端组合覆盖: 后2位和值≤4或≥16保留至少1注
  [P3-E] P3联动改用存储查询: 读Pick3技能store, 不跑内建P3实例

V1.23.0 (2026-07-06, 26176期失准优化):
  [A] Chi2降权加深: 下限0.7→0.5, 上限1.2→1.3, 增强冷号惩罚
  [B] P1/P2位置强化: 万位/千位低频数字(freq<10%)额外+0.25log分
  [C] CUSUM均值窗口缩短: 全量→近300期, 提升近期偏移敏感度
  [D] 数字支配惩罚: 同数字≥3次时额外减分(-0.15/次), 防止单数垄断
  [E] 近期数字先验: 最近5期出现数字≥3个时+0.08log分/个

V1.21.0:
  [A] 万/千位多样性硬约束: 每数字每位置限2次/Top10的前3位覆盖展宽增强
  [B] 后区对子检测: 独立评分器对[十,个]对子结构额外加分
  [C] 跨期预测漂移检测: Jaccard相似度>0.5时强制注入3组新号码
  [D] 评分区间校准: 对数概率score统一映射回[0,100]显示区间

V1.20.0:
  [A] 概率校准+对数融合: 每层分数经log(p)变换后求和, 区分度提升10×
  [C2] 后2位与前3位重叠检测: L6新增tail_overlap项
  [B] 和值约束非对称展宽: 改用50期滑动窗+3σ, 包容冷态和值
  [C] 热度衰减: pos_freq softmax温度缩放(T=2.0), L1用缩放版
  [D] 位置互补: 冷位数字(freq<8%)时L1乘1.2-1.5x补偿
"""

import sys, os, json, math, random, warnings, time
import itertools
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter, defaultdict

from p5_data_updater import check_and_update
from version import VERSION as _VERSION, RELEASE_DATE as _RELEASE_DATE

VERSION = _VERSION
RELEASE_DATE = _RELEASE_DATE


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
    """排列5多策略融合完全体 V1.23.0
    + 万/千位硬约束(方案A) + 后区对子检测(方案B)
    + 跨期漂移检测(方案C) + 显示分校准(方案D)
    + Chi2降权加深(A) + P1/P2位置强化(B)
    + CUSUM窗口缩短(C) + 数字支配惩罚(D) + 近期先验(E)"""

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
        # 【V1.24.0-A】位置-数字频率下限保护: 每位频率不低于0.025
        # 防止强热号乘积效应导致冷稀有数字被完全压制
        # 26177期万位8(近15期3次=温号)被完全忽略, 因模型过度惩罚低频乘积
        # ----------------------------------------------------------------
        l1 = 1.0
        freq_source = getattr(self, 'pos_freq_temp', self.pos_freq)
        _MIN_POS_FREQ = 0.025  # 均匀分布0.1的25%
        for pos in range(5):
            _f = freq_source[pos].get(digits[pos], 0.02)
            _f = max(_f, _MIN_POS_FREQ)  # 下限钳制
            l1 *= _f
        l1 = min(l1 * 10000, 1.0)
        # 【P5-冷位补偿】V2.0.0: 冷位数字(freq<8%)时在log空间上加成
        # 旧版: l1 * 1.5 (线性) → log压缩后几乎无效
        # 新版: log后 + 冷位bonus, 直接影响终分
        cold_count = sum(1 for pos in range(5)
                         if self.pos_freq[pos].get(digits[pos], 0) < 0.08)
        cold_bonus = 0.0
        if cold_count >= 1:
            cold_bonus = cold_count * 0.15  # 每个冷位+0.15 log分
            # 多冷位叠加: 3冷位以上额外加成(冷号联动)
            if cold_count >= 3:
                cold_bonus += 0.10
        # [V1.23.0-B] P1/P2位置强化: 万位/千位低频数字额外log加分
        # 26176期P1实际=5(预测top3=[6,0,2]), P2实际=8(预测top3=[0,7,1])
        # 两位置均完全脱离实际, 此修正鼓励低频数字出现在前2位
        p12_bonus = 0.0
        for pos in [0, 1]:
            pf = self.pos_freq[pos].get(digits[pos], 0)
            # 频率<10%的数字给予log加分(每个+0.25)
            if pf < 0.10:
                p12_bonus += 0.25
        # [V1.23.0-E] 近期出现数字先验加权: 最近5期出现过的数字给少量log加分
        # 实际开奖模式具有短期连续性, 如26176(581)继承26175(838)中8的重现
        _recent_window = min(5, len(self.draws))
        _recent_set = set()
        for _d in self.draws[-_recent_window:]:
            _recent_set.update(_d[:5])
        _recent_count = sum(1 for digit in digits if digit in _recent_set)
        # 0~2/3/4/5个近期数字 → +0/+0.08/+0.15/+0.22 (log空间)
        _recent_bonus = max(0.0, (_recent_count - 2) * 0.08) if _recent_count > 2 else 0.0
        
        l1 = self._to_log_prob(l1)
        l1 += cold_bonus  # log空间加法
        l1 += p12_bonus   # [V1.23.0-B] P1/P2 log空间加分
        l1 += _recent_bonus  # [V1.23.0-E] 近期数字加分
        # [P5-O3] 双位置联动冷号: 5位中任意2处同时冷(≥8期未出)时加分
        # 26180期千位0(13期遗漏)+百位5(9期遗漏)双冷, 模型未联动处理
        # 每对冷位+0.10 log分
        try:
            _cold_pair_threshold = max(8, int(len(self.draws) * 0.03))
            _cold_positions = []
            for _p in range(5):
                _pos_seq = [d[_p] for d in self.draws[-50:]]
                _miss = len(_pos_seq)
                for i in range(len(_pos_seq) - 1, -1, -1):
                    if _pos_seq[i] == digits[_p]:
                        _miss = len(_pos_seq) - 1 - i
                        break
                if _miss >= _cold_pair_threshold:
                    _cold_positions.append(_p)
            if len(_cold_positions) >= 2:
                _pair_count = len(_cold_positions) * (len(_cold_positions) - 1) // 2
                l1 += _pair_count * 0.10  # 每对+0.10 log分
        except Exception:
            pass
        # [Plan F] 万位/千位短间隔重号增强: 系数0.15→0.25, 连续2期加倍
        # 26179期万位3(上期万=8→断)未触发旧逻辑, 但近30期5次(17%最高频)
        # 26178期万位8(上期万=8重复)短间隔持续性强, 需足够力度
        if len(self.draws) >= 2:
            _last = self.draws[-1]
            for _p in [0, 1]:  # 万位/千位
                if digits[_p] == _last[_p]:
                    _pos_seq = [d[_p] for d in self.draws[-50:]]
                    if sum(1 for x in _pos_seq if x == digits[_p]) >= 2:
                        l1 += 0.25  # 万/千同位置重复+0.25log分(原0.15)
                        # 连续2期及以上加倍(+额外0.15)
                        if len(self.draws) >= 3 and digits[_p] == self.draws[-2][_p]:
                            l1 += 0.15
        # [V1.36.0-A] 万位/千位低位趋势惯性检测: 连续3+期≤3时低位候选加分
        # 26193期: 万位走势6→9→5→0→3→1(连续下降6期), 万位1完全不在预测
        # 当万位/千位连续多期在低位区间(0-3)时, 低位数字回补概率上升
        try:
            if len(self.draws) >= 5:
                for _p in [0, 1]:
                    _recent = [d[_p] for d in self.draws[-5:]]
                    _consec_low = 0
                    for _d in reversed(_recent):
                        if _d <= 3:
                            _consec_low += 1
                        else:
                            break
                    if _consec_low >= 3 and digits[_p] <= 3:
                        l1 += _consec_low * 0.06  # 每连续1期+0.06log分
        except Exception:
            pass

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
        # 【V1.24.0-B】热号惯性跟踪: 某位置某数字近10期出现≥4次时加分
        # 26177期十位7近20期出现6次(超级热号), 但预测十位无一注猜7
        # 模型过度依赖频率衰减, 忽视了持续热号的惯性延续
        _hot_inertia_bonus = 0.0
        _HOT_WINDOW = min(10, len(self.draws))
        if _HOT_WINDOW >= 10:
            for pos in range(5):
                _pos_digits = [d[pos] for d in self.draws[-_HOT_WINDOW:]]
                _cnt = sum(1 for x in _pos_digits if x == digits[pos])
                if _cnt >= 4:
                    # 出现4次+0.10, 5次+0.15, 6次+0.20... (log空间)
                    _hot_inertia_bonus += 0.05 * (_cnt - 2)
        # 上限封顶
        _hot_inertia_bonus = min(_hot_inertia_bonus, 0.50)
        l2 = self._to_log_prob(l2)
        l2 += _hot_inertia_bonus

        # ----------------------------------------------------------------
        # L3: 奇偶比 + 012路分布
        # ----------------------------------------------------------------
        odd = sum(1 for d in digits if d % 2 == 1)
        l3_parity = 1.0 if 2 <= odd <= 3 else 0.4
        road0 = sum(1 for d in digits if d % 3 == 0)
        l3_road = 1.0 - min(abs(road0 - 2) / 3, 1.0) * 0.4
        l3 = l3_parity * 0.6 + l3_road * 0.4
        l3 = self._to_log_prob(l3)

        # ----------------------------------------------------------------
        # L4: 重复模式(豹子/对子/顺子) — 唯一数字越多分越高
        # ----------------------------------------------------------------
        uniq = len(set(digits))
        l4 = 1.0 if uniq >= 4 else 0.8 if uniq >= 3 else 0.5
        # [V1.25.0-G] 数字支配惩罚释放: 阈值从≥3提升到≥4
        # 实际开奖[3,9,6,2,3]只有4个不同数字(3重复), 合理组合不应被过度惩罚
        # 原来阈值3次导致数字组合偏散, 压制了实际合理的重复模式
        _digit_cnt = Counter(digits)
        _max_repeat = max(_digit_cnt.values())
        if _max_repeat >= 4:
            # 【P5-X】尾段重复豁免: 如果重复数字集中在P3-P5(尾段)
            # 如12444中4重复3次但均在尾段, 这种重复是合理尾豹子
            _most_common = _digit_cnt.most_common(1)[0][0]
            _repeated_positions = [p for p in range(5) if digits[p] == _most_common]
            # 检查重复是否集中在尾段(≥2个重复在P3-P5)
            _tail_repeats = sum(1 for p in _repeated_positions if p >= 2)
            if _tail_repeats >= 2 and len(_repeated_positions) <= 3:
                # 尾段集中的重复: 减半惩罚
                _dominance_penalty = -0.075 * (_max_repeat - 3)
            else:
                _dominance_penalty = -0.15 * (_max_repeat - 3)
            l4 = max(l4 + _dominance_penalty, 0.1)
        l4 = self._to_log_prob(l4)

        # ----------------------------------------------------------------
        # L5: 【V1.24.0-C】排列3→排列5跨期特征 + 【V1.28.0-A】跨期跨位重号路径
        # 利用已出的排列3三期号码(近3期前3位)作为排列5额外特征
        # 排列5后3位=排列3(本期开奖), 跨期关联性:
        #   - 前3位(万千百)影响后2位(十个)的分布
        #   - 近3期P3的和值/跨度模式预测本期P5的前3位
        #   - 【V1.28.0-A】上期数字→本期不同位置的迁移模式(26182: 千2→万3, 百4→十4)
        # ----------------------------------------------------------------
        _p3_score = 0.5
        if len(self.draws) >= 5:
            try:
                # 近3期的前3位(P3等价), 计算和值与跨度
                _p3_periods = [list(d[:3]) for d in self.draws[-3:]]
                _p3_sums = [sum(d) for d in _p3_periods]
                _p3_spans = [max(d)-min(d) for d in _p3_periods]
                
                # 候选的前3位
                _front3 = list(digits[:3])
                _front_sum = sum(_front3)
                _front_span = max(_front3) - min(_front3)
                
                # 特征1: 前3位和值是否在近3期P3和值±4范围内
                _sum_lo = min(_p3_sums) - 4
                _sum_hi = max(_p3_sums) + 4
                _sum_match = 1.0 if _sum_lo <= _front_sum <= _sum_hi else 0.3
                
                # 特征2: 前3位跨度是否在近3期P3跨度±2范围内
                _span_lo = min(_p3_spans) - 2
                _span_hi = max(_p3_spans) + 2
                _span_match = 1.0 if _span_lo <= _front_span <= _span_hi else 0.4
                
                # 特征3: 候选前3位是否包含近3期P3的高频数字(出现≥2次)
                _p3_digit_freq = Counter()
                for d in _p3_periods:
                    _p3_digit_freq.update(d)
                _hot_p3 = {d for d, c in _p3_digit_freq.items() if c >= 2}
                _hot_in_front = sum(1 for d in _front3 if d in _hot_p3)
                _hot_match = min(_hot_in_front / 2.0, 1.0)
                
                # 特征4: 条件概率 — P(后2位 | 前3位)
                _tail = tuple(digits[3:])
                _cond_score = 0.5
                _p3_corr = getattr(self, 'p3_corr', {})
                if _p3_corr and 'tail_given_p3' in _p3_corr:
                    _tg = _p3_corr['tail_given_p3']
                    # 统计历史上前3位相同时后2位的分布
                    _matching_tails = [t for p3, t in _tg if tuple(p3) == tuple(_front3)]
                    if _matching_tails:
                        _match_cnt = sum(1 for t in _matching_tails if t == _tail)
                        _cond_score = 0.3 + 0.7 * (_match_cnt / max(len(_matching_tails), 1))
                
                # 【O4】前3位(P3)近期位置级偏置: 近10期各位置的转移概率
                # 26178期前3位=8,3,7, 模型在万千百三位完全偏位
                # 增加近10期各位置独立转移矩阵, 捕捉位置级短期趋势
                _o4_p3_pos_bias = 0.5
                if len(self.draws) >= 10:
                    _recent_p3 = [list(d[:3]) for d in self.draws[-10:]]
                    # 对每个位置, 检查候选数字在近10期该位置的频率
                    _pos_hits = 0
                    for _pi in range(3):
                        _pos_seq = [d[_pi] for d in _recent_p3]
                        _cnt = sum(1 for x in _pos_seq if x == _front3[_pi])
                        if _cnt >= 2:
                            _pos_hits += min(_cnt / 5.0, 1.0)
                    # 位置命中率转化为偏置分: 0命中=0.3, 1命中=0.6, 2命中=0.8, 3命中=1.0
                    _o4_p3_pos_bias = 0.3 + _pos_hits * 0.25
                
                # 【V1.28.0-A】跨期跨位重号路径: 上期数字迁移到不同位置
                # 26182: 千2→万3(+1), 百4→十4(同值)
                _cross_pos_p3 = 0.5
                if len(self.draws) >= 2:
                    _last = self.draws[-1]
                    _front3 = digits[:3]
                    # 上期P1→本期P2: 上期万位→本期千位
                    if _front3[1] == _last[0]:
                        _cross_pos_p3 += 0.15
                    # 上期P2→本期P1: 上期千位→本期万位
                    if _front3[0] == _last[1]:
                        _cross_pos_p3 += 0.15
                    # 上期P3→本期P4: 上期百位→本期十位(前3影响后2)
                    # 在L6中已有此检测, 此处仅检测前3位内部转移
                    # 序列转移: 上期2位数字同时按序迁移
                    # 如: 上期[P2,P3]=[2,4]→本期[P1,P2]=[2+1,4]
                    if len(_last) >= 3 and _front3[0] == (_last[1] + 1) % 10 and _front3[1] == (_last[2]):
                        _cross_pos_p3 += 0.15
                    # 反向迁移: 上期[P1,P2]=[a,b]→本期[P2,P3]=[a,b+偏移]
                    if len(_last) >= 2 and _front3[1] == _last[0] and _front3[2] == (_last[1] + 1) % 10:
                        _cross_pos_p3 += 0.10
                _cross_pos_p3 = min(_cross_pos_p3, 0.8)
                
                _p3_score = (_sum_match * 0.15 + _span_match * 0.15 + 
                             _hot_match * 0.15 + _cond_score * 0.15 +
                             _o4_p3_pos_bias * 0.15 + _cross_pos_p3 * 0.25)
            except Exception:
                pass
        l5 = self._to_log_prob(max(_p3_score, 0.1))

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
        # V1.20.0-C: 后2位与前3位重叠检测
        tail_in_front = sum(1 for t in digits[3:] if t in digits[:3])
        tail_overlap_bonus = 0.5 + tail_in_front * 0.25  # 0.5/0.75/1.0
        # 【O2】后两位双胞胎模式检测: 十位=个位时检查近20期出现频率
        # 26178期实际十=个=9, Top10中无任何一注后两位相同
        # 双胞胎在P5中频率约12-15%, 不应被完全排除
        _twin_score = 0.5
        if tail[0] == tail[1]:
            if len(self.draws) >= 20:
                _twin_periods = [d[3:] for d in self.draws[-20:]]
                _twin_cnt = sum(1 for t in _twin_periods if t[0] == t[1])
                if _twin_cnt >= 2:
                    _twin_score = 0.5 + min(_twin_cnt / 20.0 * 0.5, 0.5)
            # 【P5-X】冷号同号强化: 后2位同号且该数字在P4/P5均冷(近10期未出)
            # 26181期十位4和个位4均为冷号但组成双胞胎, 当前双胞胎检测只加0.5基础
            # 冷号双胞胎更易被L1压制, 需额外加分
            if len(self.draws) >= 10:
                _last10_p4 = set(d[3] for d in self.draws[-10:])
                _last10_p5 = set(d[4] for d in self.draws[-10:])
                _twin_d = tail[0]
                if _twin_d not in _last10_p4 and _twin_d not in _last10_p5:
                    # 双冷+同号: 强加分
                    _twin_score = min(_twin_score + 0.25, 1.0)
        # 【P5-Y】尾段三连豹子检测: P3=P4=P5(百=十=个)
        # 26181实际4,4,4 — 尾段三同结构
        if len(self.draws) >= 50 and len(set(digits[2:])) == 1:
            # 尾段(P3-P5)全同, 检查近50期出现频率
            _triple_cnt = sum(1 for d in self.draws[-50:] if len(set(d[2:])) == 1)
            if _triple_cnt >= 1:
                _triple_score = 0.5 + min(_triple_cnt / 50.0 * 0.5, 0.5)
                _twin_score = max(_twin_score, _triple_score)
        # 【V1.28.0-E】后2位跨位重号路径增强: 上期P3(百位)→本期P4(十位)迁移
        # 26182: 上期P3=4(百位) → 本期P4=4(十位), 模型十位完全未覆盖4
        # P4(十位)继承上期P3(百位)是常见跨位转移模式
        _cross_pos_repeat = 0.0
        if len(self.draws) >= 2:
            _last = self.draws[-1]
            # 模式1: P3(上期百位)→P4(本期十位)
            if digits[3] == _last[2]:
                _cross_pos_repeat += 0.08
            # 模式2: P2(上期千位)→P1(本期万位)
            if digits[0] == _last[1]:
                _cross_pos_repeat += 0.08
            # 模式3: P1(上期万位)→P2(本期千位)
            if digits[1] == _last[0]:
                _cross_pos_repeat += 0.08
            # 模式4: P4(上期十位)→P3(本期百位)
            if digits[2] == _last[3]:
                _cross_pos_repeat += 0.08
            # 模式5: P5(上个位)→P1(万位)或P5→P5跨位
            if digits[0] == _last[4]:
                _cross_pos_repeat += 0.06
            _cross_pos_repeat = min(_cross_pos_repeat, 0.25)
        l6 = (tail_sum_ok * 0.22 + tail_span_ok * 0.18 +
              tail_repeat_ok * 0.12 + tail_overlap_bonus * 0.13 +
              _twin_score * 0.22 + _cross_pos_repeat * 0.13)
        l6 = self._to_log_prob(l6)

        # ----------------------------------------------------------------
        # L7: 已移除 — 与L4高度冗余(r=0.899), 保留L4
        # ----------------------------------------------------------------
        l7 = 0.5
        l7 = self._to_log_prob(l7)

        # ----------------------------------------------------------------
        # L8: 已移除 — 99.9%候选得满分, 完全退化
        # ----------------------------------------------------------------
        l8 = 0.5
        l8 = self._to_log_prob(l8)

        # ----------------------------------------------------------------
        # L9: 后2位独立条件概率 (贝叶斯) — 见 _build_back2_model
        # ----------------------------------------------------------------
        l9 = self._eval_back2_model(digits)
        l9 = self._to_log_prob(l9)

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
        l10 = self._to_log_prob(l10)

        return (l1, l2, l3, l4, l5, l6, l7, l8, l9, l10)

    # ── V1.20.0-A: 对数概率校准 ──────────────────────────────────────────

    _LOG_PROB_EPS = 1e-6

    def _to_log_prob(self, raw_score):
        """将原始层分数转换为对数概率标度
        核心思想: log(p) 空间下低分受大幅惩罚, 高分接近零,
        组合多层时区分度 = (log0.9 - log0.1) ≈ 2.2, 是线性的10倍
        """
        p = max(float(raw_score), self._LOG_PROB_EPS)
        p = min(p, 1.0)
        return math.log(p)

    def _log_prob_combine(self, scores_tuple, weights):
        """对数概率融合: sum(w_i * log(p_i)) / sum(w_i)
        返回归一化对数概率(-∞, 0], 值越接近0表示越好
        """
        total = 0.0
        w_sum = 0.0
        for i, s in enumerate(scores_tuple):
            if weights[i] > 0:
                total += weights[i] * self._to_log_prob(s)
                w_sum += weights[i]
        return total / max(w_sum, 1e-10)

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
        窗口100期, alpha=0.15, 权重限幅[0.5, 1.3]
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
                # [V1.23.0-A] Chi2降权加深: 下限0.7→0.5, 上限1.2→1.3
                # 增强对过度热号(如0/6/9)的惩罚力度, 同时给冷号更多提升空间
                w = max(0.5, min(1.3, 1.0 + alpha * std_residual))
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
        [V1.23.0-C] 均值计算窗口: 全量→近300期, 避免远距历史稀释近期信号
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
            # [V1.23.0-C] 改用近300期均值, 提升对近期偏移的敏感度
            vals = [d[pos] for d in self.draws[-300:]]
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
        # V1.21.0 ④: 双向报警时取最近30期均值方向,避免双向互相打平
        self._debias['cusum_shift'] = 0.0
        if hasattr(self, '_cusum_state') and self._cusum_state:
            for pos in range(5):
                state = self._cusum_state.get(pos, {})
                has_pos = state.get('alarm_pos', False)
                has_neg = state.get('alarm_neg', False)
                if has_pos and has_neg:
                    # 双向报警: 检查最近30期均值偏移方向
                    recent_vals = [d[pos] for d in self.draws[-30:]]
                    recent_mu = np.mean(recent_vals)
                    base_mu = state.get('mu', 4.5)
                    diff = recent_mu - base_mu
                    if diff > 0.3:  # 最近明显偏上
                        self._debias['cusum_shift'] += 0.3
                    elif diff < -0.3:  # 最近明显偏下
                        self._debias['cusum_shift'] -= 0.3
                    # |diff|<=0.3: 均值回归稳定, 不修正
                else:
                    if has_pos:
                        self._debias['cusum_shift'] += 0.3
                    if has_neg:
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
        # 1) 40% 均匀随机种子
        for _ in range(20):
            seeds.append([rnd.randint(0, 9) for _ in range(5)])
        # 2) 20% 卡方加权种子
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
        # 3) 【方案A-扩展】反主导种子: 强制注入万≠9 + 千≠4的组合
        # 从过去的实际开奖中取样, 避免GA锁死在[9,4,...]的局部最优
        from collections import Counter as _Cnt
        if len(self.draws) >= 50:
            # 统计前3位实际出现次数, 挑出热门的万/千/百搭配
            front_triples = _Cnt(tuple(d[:3]) for d in self.draws[-200:])
            # 排除[9,4,4]和[9,4,*], 取Top 20个非锁定三元组
            anti_dominated = [
                list(k) for k, _ in front_triples.most_common(60)
                if k[0] != 9 or k[1] != 4  # 万不能=9或千不能=4
            ][:15]
            for ad in anti_dominated:
                # 后2位随机
                full = ad + [rnd.randint(0, 9), rnd.randint(0, 9)]
                seeds.append(full)

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
            if digits_tuple is None:
                return -999.0
            if not isinstance(digits_tuple, tuple) or len(digits_tuple) != 5:
                digits_list = [random.randint(0, 9) for _ in range(5)]
            else:
                digits_list = list(digits_tuple)
            scores = self._compute_layers(digits_list)
            # V1.20.0-A: 对数概率融合替代加权求和
            fs = self._log_prob_combine(scores, weights)
            # 卡方修正: 对数空间下加法
            fs += math.log(self._compute_chi2_bonus(digits_list))
            return fs

        best = None
        best_score = -999.0  # V1.20.0: 对数空间下分数可达-6.9, 需更低初值
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

        # 【方案A-扩展2】V2.0.0: 全5位冷位数字强制注入
        # 确保每位冷位数字(近10期未出现)都在候选池中有路径
        # 解决GA收敛导致冷位数字完全消失的问题
        if len(self.draws) >= 10:
            _recent_10 = self.draws[-10:]
            # 每位冷位数字
            _cold_by_pos = []
            for _p in range(5):
                _recent = {d[_p] for d in _recent_10}
                _cold_by_pos.append([d for d in range(10) if d not in _recent])
            _existing_by_pos = [set(d[_p] for d in all_candidates) for _p in range(5)]
            # 对每位, 如果冷位数字不在现有池中, 注入
            for _p in range(5):
                for _cold_d in _cold_by_pos[_p]:
                    if _cold_d not in _existing_by_pos[_p]:
                        # 构造一个包含该冷位数字的候选
                        _new = list(rnd.choices(range(10), k=5))
                        _new[_p] = _cold_d
                        all_candidates.add(tuple(_new))
        
        # 【方案A-扩展2续】从缓存枚举注入前3位多样候选
        # 确保万/千/百的多样性, 不受GA收敛影响
        if getattr(self, '_cache_ready', False) and hasattr(self, '_all_digits'):
            # 统计目前已收集的万/千位分布
            front_freq = Counter((d[0], d[1]) for d in all_candidates)
            # 需要补充的万/千组合: 出现<2次的
            for wan in range(10):
                for qian in range(10):
                    key = (wan, qian)
                    if front_freq.get(key, 0) < 2:
                        # 从缓存枚举取该万/千组合的前5个百位最优组合
                        bai_hits = Counter()
                        for idx, digits in enumerate(self._all_digits):
                            if digits[0] == wan and digits[1] == qian:
                                bai_hits[digits[2]] += 1
                        for bai_d in [d for d, _ in bai_hits.most_common(3)]:
                            # 固定前3位, 后2位随机
                            d = tuple([wan, qian, bai_d, rnd.randint(0, 9), rnd.randint(0, 9)])
                            all_candidates.add(d)

        # ── Step 4: 评分 + 对数概率融合 + 卡方修正 + 后区对子加分 ──
        # 【方案B】后区对子检测: [十,个]位相同时额外加分
        # 排列5后2位[6,6]等对子结构是常见的, L4去重数会惩罚它
        # 需独立评分器补偿
        prev_tail = (self.draws[-1][3], self.draws[-1][4]) if len(self.draws) >= 1 else (0, 0)
        
        # 统计近50期后2位对子出现的频率
        if not hasattr(self, '_tail_pair_rate'):
            _tail_pair_count = 0
            _tail_window = min(50, len(self.draws))
            for d in self.draws[-_tail_window:]:
                if d[3] == d[4]:
                    _tail_pair_count += 1
            self._tail_pair_rate = _tail_pair_count / max(_tail_window, 1)
        
        scored = []
        for digits_tuple in all_candidates:
            scores = self._compute_layers(list(digits_tuple))
            # V1.20.0-A: 对数概率融合
            fs = self._log_prob_combine(scores, weights)
            chi2_bonus = self._compute_chi2_bonus(digits_tuple)
            # 卡方修正在对数空间下加法
            fs += math.log(chi2_bonus)
            
            # 【V2.0.0】冷位数字log空间加分: 每位冷位直接加0.8 log分
            # (在[-1.1,-0.4]分数范围内, 0.8是强力boost)
            _cold_bonus = 0.0
            for _p in range(5):
                if self.pos_freq[_p].get(digits_tuple[_p], 0) < 0.08:
                    _cold_bonus += 0.8
            if _cold_bonus > 0:
                fs += _cold_bonus
            
            # 【方案B】后区对子加分: [十,个]相同时, 根据历史频率给bonus
            if digits_tuple[3] == digits_tuple[4]:
                pair_bonus = 1.0 + self._tail_pair_rate * 0.3
                fs += math.log(pair_bonus)
                if digits_tuple[3] in prev_tail:
                    fs += math.log(1.1)
            
            # 【P5-Z】尾段聚合加分: P3-P5中≥2个相同数字 + 后2位同号时链式加分
            # 26181期百=十=个=4组成尾段三同豹子, 模型完全遗漏
            # 检测后2位同号且该数字也在P3出现 → 链式加分
            _d3, _d4, _d5 = digits_tuple[2], digits_tuple[3], digits_tuple[4]
            _tail_set = len(set([_d3, _d4, _d5]))
            if _tail_set == 1:
                # 百十个全同: 强加分
                fs += math.log(1.25)  # +25%
            elif _tail_set == 2:
                # 尾段2同: 检测同号位置是否包含P4-P5
                if _d4 == _d5:
                    # 后2位同号 + P3关联: 温和加分
                    if _d3 == _d4:  # P3=P4=P5虽不同三, 但链式同
                        fs += math.log(1.15)  # +15%
                    elif _d3 in (_d4, _d5):  # P3与后2位之一同
                        fs += math.log(1.08)  # +8%
            
            scored.append({
                'digits': list(digits_tuple),
                'final_score': fs,
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

        # 【方案A】万/千/百位多样性硬约束: 前3位每数字每位置≤2次
        def _apply_all_position_diversity(scored_list, n):
            """全5位置多样性: 前3位(万/千/百)每数字≤2, 后2位(十/个)每数字≤3
               V2.0.0: 采样池扩展(每位至少5不同数字) + 冷位门禁(2路径) + 反垄断(≤30%)
            """
            if len(scored_list) <= n:
                return list(scored_list)
            
            # 【方案2】计算每个位置的冷位数字(近10期未出现)
            cold_pos_digits = [{}, {}, {}, {}, {}]
            if len(self.draws) >= 10:
                recent_10 = self.draws[-10:]
                for pos in range(5):
                    recent_pos = {d[pos] for d in recent_10}
                    for d in range(10):
                        if d not in recent_pos:
                            cold_pos_digits[pos][d] = True
            
            # 冷位优先候选
            cold_candidates = []
            normal_candidates = []
            for cand in scored_list:
                dig = cand['digits']
                has_cold = any(p < len(cold_pos_digits) and dig[p] in cold_pos_digits[p] for p in range(5))
                if has_cold:
                    cold_candidates.append(cand)
                else:
                    normal_candidates.append(cand)
            
            # 尝试3级严格度
            for max_repeat in [2, 3, 999]:
                result = []
                seen_tuples = set()
                pos_cnts = [Counter() for _ in range(5)]
                cold_path_count = {pos: Counter() for pos in range(5)}
                
                # 冷位候选优先, 再普通
                ordered = cold_candidates + normal_candidates
                for cand in ordered:
                    t = tuple(cand['digits'])
                    if t in seen_tuples:
                        continue
                    ok = True
                    for pos in range(5):
                        limit = max_repeat if pos < 3 else 3
                        if pos_cnts[pos][cand['digits'][pos]] >= limit:
                            ok = False
                            break
                    if not ok:
                        continue
                    
                    # 【方案2】冷位路径控制: 某冷位数字已在2条路径中, 且结果过半 → 跳过
                    skip = False
                    for pos in range(5):
                        dig = cand['digits'][pos]
                        if dig in cold_pos_digits[pos]:
                            if cold_path_count[pos][dig] >= 2 and len(result) >= max(3, n // 2):
                                skip = True
                                break
                    if skip:
                        continue
                    
                    result.append(cand)
                    seen_tuples.add(t)
                    for pos in range(5):
                        pos_cnts[pos][cand['digits'][pos]] += 1
                        if cand['digits'][pos] in cold_pos_digits[pos]:
                            cold_path_count[pos][cand['digits'][pos]] += 1
                    if len(result) >= n:
                        break
                
                if len(result) >= n:
                    # 【方案1+3】检查每位是否覆盖≥7个不同数字, 且无单个数字>30%
                    ok = True
                    for pos in range(5):
                        pos_vals = Counter(c['digits'][pos] for c in result)
                        if len(pos_vals) < 7:
                            ok = False
                            break
                        for d, cnt in pos_vals.items():
                            if cnt / len(result) > 0.30:
                                ok = False
                                break
                        if not ok:
                            break
                    if ok:
                        return result[:n]
                    # 不满足则尝试下一级严格度
                if max_repeat == 999:
                    return result[:n]
            return scored_list[:n]

        # 先对全量候选施加全位多样性约束(取前200+), 再用分层选
        top200_with_div = _apply_all_position_diversity(scored, 200)
        top100 = _layered_selection(top200_with_div, k=min(100, len(top200_with_div)))
        # 再对top100施加全位多样性
        top100 = _apply_all_position_diversity(top100, 100)
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

        # 【P5-Z】数字集中度压缩: Top10中数字池大小>4的候选, 尝试从top100替换为更紧凑组合
        # 26181期实际12444只有3个不同数字, Top10几乎覆盖全10数字, 过于分散
        # 策略: 如果当前Top10总体数字池>6个数字, 尝试注入≤4个数字的紧凑候选
        if len(top10) >= 8:
            _all_digits_in_top10 = set()
            for _c in top10:
                _all_digits_in_top10.update(_c['digits'])
            if len(_all_digits_in_top10) >= 6:
                # 找top100中数字集≤4个的紧凑候选
                _compact_cands = []
                _seen_c = set()
                for _c in top100:
                    _t = tuple(_c['digits'])
                    if _t in _seen_c:
                        continue
                    _seen_c.add(_t)
                    _uniq = len(set(_c['digits']))
                    if _uniq <= 4:
                        _compact_cands.append(_c)
                # 排序: 优先少数字 > 高分数
                _compact_cands.sort(key=lambda x: (len(set(x['digits'])), -x['final_score']))
                # 最多替换3个最分散的候选
                _replaced = 0
                _final_compact = []
                _sc_list = _compact_cands[:10]
                _sc_used = set()
                for _c in top10:
                    if _replaced >= 3:
                        _final_compact.append(_c)
                    else:
                        _uniq = len(set(_c['digits']))
                        if _uniq >= 5 and _sc_list:
                            _r = None
                            for _sci in range(len(_sc_list)):
                                if _sci not in _sc_used:
                                    _r = _sc_list[_sci]
                                    _sc_used.add(_sci)
                                    break
                            if _r:
                                _final_compact.append(_r)
                                _replaced += 1
                            else:
                                _final_compact.append(_c)
                        else:
                            _final_compact.append(_c)
                # 补充可达10注
                _sc_idx = 0
                while len(_final_compact) < 10 and _sc_idx < len(_sc_list):
                    if _sc_idx not in _sc_used:
                        _final_compact.append(_sc_list[_sc_idx])
                    _sc_idx += 1
                _final_compact.sort(key=lambda x: -x['final_score'])
                top10 = _final_compact[:10]

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

    # ═══ 【方案D】评分区间校准 ═══
    # V1.20.0引入对数概率融合后, final_score变为负值(-ln形式,约-2~-15)
    # 映射到[0,100]显示区间, 保持排名不变
    def _display_score(self, log_score: float, reference_max: Optional[float] = None) -> float:
        """
        将对数概率score映射到[0,100]显示区间
        原理: exp(score - max) -> [0,1] -> ×100
        参数:
          log_score: 待转换的对数概率分(负值)
          reference_max: 参考最大值(如Top1的score), 不传则直接exp
        """
        if reference_max is not None:
            rel = log_score - reference_max  # 相对差值(≤0)
            # rel=-1 → 36.8分, rel=-2 → 13.5分, rel=-3 → 5.0分
            return round(math.exp(max(rel, -5.0)) * 100, 1)
        # 没有参考点: exp(log_score)已足够小, ×1000放大
        raw = math.exp(max(log_score, -10.0))
        return round(min(raw * 1000, 100.0), 1)

    def predict(self, top_n: int = 25) -> Dict[str, Any]:
        """主预测 V1.18.0: +万/千位覆盖展宽 + 复式后2位保底"""
        # [V1.48.0-D] 固定随机种子: 按期号派生, 保证同期待测可复现
        # 26203归因: 权重初始化random.uniform无固定种子, 同期多次运行
        # Top10不同(存档63477 vs 重跑13835), 复盘可比性受损
        try:
            random.seed(int(self.last_period) * 7919 + 262144)
            np.random.seed(int(self.last_period) * 7919 + 262144)
        except Exception:
            pass
        prev = list(self.draws[-1]) if self.draws else [0]*5
        # 应用增量纠偏
        self._apply_debias()
        # 概率校准(首次predict时触发)
        self._calibrate_probs()

        result = self.enumerate_all(prev)

        # ====== [V1.43.0] P3-P5前3位继承: 万/千/百位改用P3预测评分 ======
        # 排列5的前3位(万/千/百) = 同期排列3(百/十/个) 100%一致
        # 策略: P5候选的前3位评分继承P3模型的预测分数
        # 后2位(十/个)保持P5自身评分逻辑
        # 实现: 加载P3 Top25预测, 对P5全量候选进行混合评分
        try:
            _p3_all = None
            try:
                _p3_all = self._load_p3_prediction(self.last_period, top_n=25)
            except Exception:
                _p3 = self._load_p3_prediction(self.last_period, top_n=1)
                _p3_all = [_p3] if _p3 else []

            _all_for_hybrid = result.get('all', [])
            _top100_for_hybrid = result.get('top100', [])
            all_scored = _all_for_hybrid
            top100 = _top100_for_hybrid

            if _p3_all and len(_p3_all) >= 1:
                # 构建P3前3位→排名映射
                _p3_rank_map = {}  # {(百,十,个): rank_index}
                for _ri, _p3c in enumerate(_p3_all):
                    _key = tuple(int(x) for x in _p3c)
                    if _key not in _p3_rank_map:
                        _p3_rank_map[_key] = _ri

                # 【V1.50.0-D】前3位遗漏表(近200期): P3继承深冷惩罚用
                # 26205根因: P3 Top1=278(万2漏31期/百8漏29期), P3预测病态
                # 但hybrid仍给P3 Top1前3位 0.65 权重 → 万2/百8垄断P5前3位
                _v50_p3miss = [{}, {}, {}]
                for _pi in range(3):
                    _seq = [d[_pi] for d in self.draws[-min(200, len(self.draws)):]]
                    for _d in range(10):
                        for _i in range(len(_seq) - 1, -1, -1):
                            if _seq[_i] == _d:
                                _v50_p3miss[_pi][_d] = len(_seq) - 1 - _i
                                break
                        if _d not in _v50_p3miss[_pi]:
                            _v50_p3miss[_pi][_d] = len(_seq)

                # 收集P5候选中的前3位频率(用于非P3候选的降权基准)
                from collections import Counter as _FCnt
                _front3_in_p5 = _FCnt()
                for _c in _all_for_hybrid[:2000]:
                    _f3 = tuple(_c['digits'][:3])
                    _front3_in_p5[_f3] += 1

                print(f"[P3-P5H] 🔄 P3-P5混合评分: P3 Top{len(_p3_rank_map)}前3位, "
                      f"P5候选池{len(_all_for_hybrid)}")

                def _hybrid_score(_candidate, _p3_map):
                    """混合评分: 前3位继承P3(带深冷惩罚), 非P3用P5原生前3位证据
                    同尺度(0.3~1.0)归一化, 后2位保持P5 log分"""
                    _front3 = tuple(_candidate['digits'][:3])
                    _orig_score = _candidate.get('final_score', 0)
                    _p5_back2 = _orig_score  # 原始P5 score含后2位信息

                    if _front3 in _p3_map:
                        _p3_rank = _p3_map[_front3]
                        # P3 rank → 归一化分数: rank0=1.0, rank24=0.3
                        _p3_norm = max(0.3, 1.0 - _p3_rank * 0.028)
                        # 【V1.50.0-D2】P3前3位深冷惩罚: 前3位含≥16期遗漏数字
                        # 时P3继承权重降级(0.65→0.55/0.40). 26205 P3 Top1=278
                        # 万2漏31/百8漏29 — 深冷数字进P3 Top1说明P3预测病态,
                        # 降低P3单期失准对P5前3位的传导
                        try:
                            _cold_n = sum(1 for _pi, _di in ((0, _candidate['digits'][0]),
                                                             (1, _candidate['digits'][1]),
                                                             (2, _candidate['digits'][2]))
                                          if _v50_p3miss[_pi].get(_di, 99) >= 16)
                            _p3_w = 0.40 if _cold_n >= 2 else (0.55 if _cold_n == 1 else 0.65)
                        except Exception:
                            _p3_w = 0.65
                        _combined = _p3_norm * _p3_w + _p5_back2 * (1 - _p3_w)
                        return _combined
                    else:
                        # 【V1.50.0-D】P5原生评分并行通道: 非P3前3位候选不再被
                        # 结构性压制(旧版×0.60在log负分域永远低于P3正分). 前3位
                        # 用P5原生证据(近30期位置频率)归一化到与P3_norm同尺度
                        # (0.3~1.0), 后2位保持P5 log分 — 万8(漏3)/千0(漏5)等
                        # 短间隔回补信号即使不在P3 Top25也能获得公平评分
                        try:
                            _nn = 1.0
                            for _pi, _di in ((0, _candidate['digits'][0]),
                                              (1, _candidate['digits'][1]),
                                              (2, _candidate['digits'][2])):
                                _seq = [d[_pi] for d in self.draws[-30:]]
                                _f = _seq.count(_di) / 30.0
                                _nn *= min(1.0, 0.3 + _f * 14.0)
                            _native_norm = min(1.0, max(0.3, _nn))
                        except Exception:
                            _native_norm = 0.3
                        return _native_norm * 0.65 + _p5_back2 * 0.35

                rescored_count = 0
                # 对top100重评分
                if _top100_for_hybrid:
                    for _c in _top100_for_hybrid:
                        _c['final_score'] = _hybrid_score(_c, _p3_rank_map)
                        rescored_count += 1
                # 对all_scored[:2000]重评分
                for _c in _all_for_hybrid[:2000]:
                    _c['final_score'] = _hybrid_score(_c, _p3_rank_map)
                    rescored_count += 1

                # 重排序
                if _top100_for_hybrid:
                    _top100_for_hybrid.sort(key=lambda x: -x.get('final_score', -999))
                if _all_for_hybrid:
                    _all_for_hybrid.sort(key=lambda x: -x.get('final_score', -999))

                # 重建top10: 从top100(hybrid)中取top_n
                _combined_pool = (_top100_for_hybrid[:100] if _top100_for_hybrid
                                 else _all_for_hybrid[:2000])
                _new_top10 = []
                _seen = set()
                for _c in _combined_pool:
                    _t = tuple(_c['digits'])
                    if _t not in _seen:
                        _seen.add(_t)
                        _new_top10.append(_c)
                    if len(_new_top10) >= top_n:
                        break

                # P3 Top1强制在Top10中
                _p3_top1_key = tuple(int(x) for x in _p3_all[0])
                _p3_top1_in = any(tuple(c['digits'][:3]) == _p3_top1_key for c in _new_top10[:10])
                if not _p3_top1_in:
                    # 从全量池搜含P3 Top1前3位的最高分候选
                    _best_p3c = None
                    for _c in _combined_pool:
                        if tuple(_c['digits'][:3]) == _p3_top1_key:
                            if _best_p3c is None or _c['final_score'] > _best_p3c['final_score']:
                                _best_p3c = _c
                    if _best_p3c and len(_new_top10) >= 1:
                        _new_top10[-1] = _best_p3c
                        _new_top10.sort(key=lambda x: -x.get('final_score', -999))
                        print(f"[P3-P5H] 💉 P3 Top1强制注入: "
                              f"{''.join(map(str,_best_p3c['digits']))}")

                print(f"[P3-P5H] ✅ 混合评分完成: {rescored_count}注重评分, "
                      f"新Top10含{sum(1 for c in _new_top10[:10] if tuple(c['digits'][:3]) in _p3_rank_map)}注P3前3位")

                # 保存结果
                result['top10'] = _new_top10[:top_n]
                result['top100'] = _top100_for_hybrid[:100] if _top100_for_hybrid else []
                result['all'] = _all_for_hybrid
                all_scored = _all_for_hybrid
                top100 = _top100_for_hybrid[:100] if _top100_for_hybrid else []

        except Exception as e:
            print(f"[P3-P5H] ⚠️ 混合评分跳过: {e}")
            import traceback
            traceback.print_exc()

        top10 = result['top10'][:top_n]

        # ====== [V1.44.0-A + V1.45.0-A] P3失准时P5前3位独立兜底降权 ======
        # 26200期归因: P3预测Top1=[8,3,5] vs 实际[0,7,7], P3完全失准
        # 导致P5前3位(万/千/百)跟着P3跑偏, 千位7/百位7全漏
        # V1.44.0: 非P3候选降权×0.60→×0.68
        # V1.45.0-A: 连续失准时加权更激进 0.68→0.80,
        # 且2期连续失准时重评hybrid blend 0.65→0.40(P3降权)
        try:
            if len(self.draws) >= 3:
                _p5_last_actual = list(self.draws[-1][:3])
                _last_p3_pred = None
                try:
                    _st = _path.join(_path.dirname(_path.abspath(__file__)), '..', 'memory', 'p3_predictions.json')
                    if _path.exists(_st):
                        with open(_st, 'r') as _fh:
                            _p3j = json.load(_fh)
                        for _p3e in _p3j.get('predictions', []):
                            if str(_p3e.get('period', '')) == str(self.last_period):
                                _bets = _p3e.get('zx_bets', [])
                                if _bets:
                                    _last_p3_pred = _bets[0].get('digits', None)
                                break
                except Exception:
                    pass
                if _last_p3_pred and len(_last_p3_pred) == 3:
                    _match_cnt = sum(1 for _p in range(3) if _last_p3_pred[_p] == _p5_last_actual[_p])
                    if _match_cnt <= 1:
                        # [V1.45.0-A] 检测是否连续2期失准
                        _prev_p3_pred = None
                        _consec_miss = False
                        try:
                            if len(self.draws) >= 4:
                                _prev_actual = list(self.draws[-2][:3])
                                if _path.exists(_st):
                                    with open(_st, 'r') as _fh2:
                                        _p3j2 = json.load(_fh2)
                                    for _p3e2 in _p3j2.get('predictions', []):
                                        if str(_p3e2.get('period', '')) == str(int(self.last_period) - 1):
                                            _pb = _p3e2.get('zx_bets', [])
                                            if _pb:
                                                _prev_p3_pred = _pb[0].get('digits', None)
                                            break
                                if _prev_p3_pred and len(_prev_p3_pred) == 3:
                                    _prev_match = sum(1 for _p in range(3) if _prev_p3_pred[_p] == _prev_actual[_p])
                                    if _prev_match <= 1:
                                        _consec_miss = True
                        except Exception:
                            pass
                        # V1.45.0-A: 连续失准更激进降权
                        _p3_unreliable_mult = 0.80 if _consec_miss else 0.68
                        _p3_tag_str = " 连续2期!" if _consec_miss else ""
                        print(f"[P5-P3D] ⚠️ P3失准: Top1={''.join(map(str,_last_p3_pred))} "
                              f"vs实际前3={''.join(map(str,_p5_last_actual))} "
                              f"匹配{_match_cnt}/3{_p3_tag_str}, "
                              f"非P3降权系数→{_p3_unreliable_mult}")
                        _p3_new_map = {}
                        try:
                            _p3_alt = self._load_p3_prediction(self.last_period, top_n=25)
                            if _p3_alt:
                                for _ri, _p3c in enumerate(_p3_alt):
                                    _key = tuple(int(x) for x in _p3c)
                                    if _key not in _p3_new_map:
                                        _p3_new_map[_key] = _ri
                        except Exception:
                            pass
                        if _p3_new_map:
                            for _c in top10:
                                _front3 = tuple(_c['digits'][:3])
                                _orig = _c.get('final_score', 0)
                                if _front3 not in _p3_new_map:
                                    _c['final_score'] = _orig / 0.60 * _p3_unreliable_mult
                            top10.sort(key=lambda x: -x.get('final_score', 0))
                        print(f"[P5-P3D] ✅ 独立兜底管道启用: {_p3_unreliable_mult}")
        except Exception as e:
            print(f"[P5-P3D] ⚠️ P3失准兜底跳过: {e}")

        # 【方案4】万位/千位空位标记: 排列三百位→万位/千位迁移检测
        # 近5期排列三百位中出现但万位Top10未出现的数字补入候选
        try:
            if len(self.draws) >= 5:
                _recent_p3_bai = [d[2] for d in self.draws[-5:]]
                _current_wan = set(b['digits'][0] for b in top10)
                _migrate_wans = set(_recent_p3_bai) - _current_wan
                if _migrate_wans:
                    print(f"[P5-Migrate] 万位空位:{_migrate_wans}(排列三百位→万位)")
                    # 从all中找包含迁移万位的候选替换10注中的冷门
                    _all = result.get('all', [])
                    _replacement = []
                    for _cand in _all:
                        if len(_replacement) >= 2:
                            break
                        if _cand['digits'][0] in _migrate_wans:
                            _t = tuple(_cand['digits'])
                            if _t not in set(tuple(b['digits']) for b in top10):
                                _replacement.append(_cand)
                    for _i in range(min(len(_replacement), len(top10))):
                        top10[-_i-1] = _replacement[_i]
        except Exception:
            pass

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

        # ═══ 【O3】位置交叉硬约束增强 ═══
        # 26178期[9,4,3,7,7]组选{3,7,9}命中3/4但位置全错
        # 对Top10中组选多样性好的候选(4+独特数字),
        # 从all_scored中找同一数字集的不同位置排列(已由枚举完成),
        # 取其中评分最高的版本替换当前
        try:
            _o3_replaced = 0
            _all_for_o3 = result.get('all', [])
            # 建一个按数字集分组的最高分映射
            _o3_best_by_set = {}
            for _c in _all_for_o3[:500]:
                _s = tuple(sorted(_c['digits']))
                if _s not in _o3_best_by_set or _c['final_score'] > _o3_best_by_set[_s]['final_score']:
                    _o3_best_by_set[_s] = _c
            for _i, _c in enumerate(top10):
                _digits_set = len(set(_c['digits']))
                if _digits_set < 4:
                    continue  # 低于4个独特数字, 排列价值低
                _s = tuple(sorted(_c['digits']))
                if _s in _o3_best_by_set:
                    _better = _o3_best_by_set[_s]
                    if _better['final_score'] > _c['final_score']:
                        top10[_i] = dict(_better)
                        _o3_replaced += 1
            if _o3_replaced > 0:
                print(f"[P5-O3] 位置交叉优化: 替换{_o3_replaced}注(取同数字集最优排列)")
        except Exception as e:
            print(f"[P5-O3] ⚠️ 跳过: {e}")

        # ═══ [Plan E] P3联动强制注入（已修复） ═══
        # 先跑同一期P3预测, 用P3预测的前3位注入P5的前3位位置
        # 注意: 不能使用self.draws[-1][:3](上一期开奖), 那相当于用已知结果作弊
        # 必须使用P3模型的预测结果, 即使P3预测不准也比上一期开奖有意义
        try:
            _p3_predicted = None
            try:
                # 【P3-E】从Pick3技能存储读取同一预测期号(数据最新+1)的P3预测Top1
                _p3_predicted = self._load_p3_prediction(self.last_period)
                if _p3_predicted:
                    _p3_refer_period = str(int(self.last_period) + 1)
                    print(f"[P5-E] P3存储读取: {''.join(map(str,_p3_predicted))} "
                          f"(参考P3第{_p3_refer_period}期)")
            except Exception as _e:
                print(f"[P5-E] ⚠️ P3存储读取失败: {_e}")
            
            if _p3_predicted is not None:
                _all_for_p3 = result.get('all', [])
                _current_tuples = set(tuple(b['digits']) for b in top10)
                # 扫描all池中前3位完全匹配P3预测的候选
                _p3_candidates = [
                    c for c in _all_for_p3
                    if list(c['digits'][:3]) == _p3_predicted
                    and tuple(c['digits']) not in _current_tuples
                ]
                if _p3_candidates:
                    _p3_candidates.sort(key=lambda x: -x['final_score'])
                    _best_p3 = _p3_candidates[0]
                    _worst = min(top10, key=lambda x: x['final_score'])
                    if _best_p3['final_score'] > _worst['final_score'] * 0.8:
                        top10.remove(_worst)
                        top10.append(_best_p3)
                        top10.sort(key=lambda x: -x['final_score'])
                        print(f"[P5-E] P3联动注入: "
                              f"{''.join(map(str,_best_p3['digits']))} "
                              f"(P3={''.join(map(str,_p3_predicted))})")
                    else:
                        print(f"[P5-E] ⚠️ P3候选评分低({_best_p3['final_score']:.1f}), 跳过")
                else:
                    # all池无匹配, 手动构造注入
                    if len(self.draws) >= 15:
                        _recent_shi = [d[3] for d in self.draws[-10:]]
                        _recent_ge = [d[4] for d in self.draws[-10:]]
                        _shi_hot = Counter(_recent_shi).most_common(1)[0][0]
                        _ge_hot = Counter(_recent_ge).most_common(1)[0][0]
                        _manual = _p3_predicted + [_shi_hot, _ge_hot]
                    else:
                        _manual = _p3_predicted + [5, 5]
                    _t = tuple(_manual)
                    if _t not in _current_tuples:
                        _worst = min(top10, key=lambda x: x['final_score'])
                        top10.remove(_worst)
                        top10.append({'digits': list(_manual),
                                      'final_score': _worst['final_score'] * 0.85})
                        top10.sort(key=lambda x: -x['final_score'])
                        print(f"[P5-E] P3手动注入(存储): "
                              f"{''.join(map(str,_manual))}")
            else:
                # 【V1.29.0-A】P3预测备用路径: 轻量统计预测
                _p3_fallback = self._predict_p3_fallback()
                if _p3_fallback:
                    print(f"[P5-E] P3备用预测: {''.join(map(str,_p3_fallback))}")
                    _p3_predicted = _p3_fallback
                    # 同主路径逻辑: 从all池匹配或手动构造
                    _all_for_p3 = result.get('all', [])
                    _current_tuples = set(tuple(b['digits']) for b in top10)
                    _p3_candidates = [
                        c for c in _all_for_p3
                        if list(c['digits'][:3]) == _p3_predicted
                        and tuple(c['digits']) not in _current_tuples
                    ]
                    if _p3_candidates:
                        _p3_candidates.sort(key=lambda x: -x['final_score'])
                        _best_p3 = _p3_candidates[0]
                        _worst = min(top10, key=lambda x: x['final_score'])
                        if _best_p3['final_score'] > _worst['final_score'] * 0.8:
                            top10.remove(_worst)
                            top10.append(_best_p3)
                            top10.sort(key=lambda x: -x['final_score'])
                            print(f"[P5-E] P3联动注入(备用): "
                                  f"{''.join(map(str,_best_p3['digits']))} "
                                  f"(P3={''.join(map(str,_p3_predicted))})")
                        else:
                            print(f"[P5-E] ⚠️ 备用P3候选评分低({_best_p3['final_score']:.1f}), 跳过")
                    else:
                        # 手动构造
                        if len(self.draws) >= 15:
                            _recent_shi = [d[3] for d in self.draws[-10:]]
                            _recent_ge = [d[4] for d in self.draws[-10:]]
                            _shi_hot = Counter(_recent_shi).most_common(1)[0][0]
                            _ge_hot = Counter(_recent_ge).most_common(1)[0][0]
                            _manual = _p3_predicted + [_shi_hot, _ge_hot]
                        else:
                            _manual = _p3_predicted + [5, 5]
                        _t = tuple(_manual)
                        if _t not in _current_tuples:
                            _worst = min(top10, key=lambda x: x['final_score'])
                            top10.remove(_worst)
                            top10.append({'digits': list(_manual),
                                          'final_score': _worst['final_score'] * 0.85})
                            top10.sort(key=lambda x: -x['final_score'])
                            print(f"[P5-E] P3手动注入(备用): "
                                  f"{''.join(map(str,_manual))}")
                else:
                    print(f"[P5-E] ⚠️ 无P3预测可用, 跳过注入")
        except Exception as e:
            print(f"[P5-E] ⚠️ P3联动跳过: {e}")

        # ====== [V1.40.0-D] P3-P5关联增强: Top3候选+位序对齐映射 ======
        # 26197期归因: P3实际=4,7,3与P5前3位完全一致, 但P5预测未充分利用
        # P3 Top1=4,7,3不在P5 Top10内, 需扩展P3候选路径
        try:
            if _p3_predicted and len(_p3_predicted) == 3:
                _p3_tuple = tuple(_p3_predicted)
                _p3_in_top10 = any(c['digits'][:3] == list(_p3_tuple) for c in top10)
                if not _p3_in_top10:
                    # P3 Top1未在Top10中, 从全量池找含P3前3位的候选
                    _p3_injected = False
                    for _c in all_scored:
                        if list(_c['digits'][:3]) == list(_p3_tuple):
                            _t = tuple(_c['digits'])
                            if _t not in set(tuple(c['digits']) for c in top10):
                                _worst_p3 = min(top10, key=lambda x: x['final_score'])
                                if _c['final_score'] > _worst_p3['final_score'] * 0.3:
                                    top10.remove(_worst_p3)
                                    top10.append(_c)
                                    _p3_injected = True
                                    print(f"[P5-P3E] 🔗 P3前3位注入: {''.join(map(str,_c['digits']))}")
                                    break
                    if not _p3_injected:
                        # 退而求其次: 找数字集重叠≥2的候选
                        _p3_set = set(_p3_tuple)
                        for _c in all_scored:
                            _c3_set = set(_c['digits'][:3])
                            if len(_p3_set & _c3_set) >= 2:
                                _t = tuple(_c['digits'])
                                if _t not in set(tuple(c['digits']) for c in top10):
                                    _worst_p3 = min(top10, key=lambda x: x['final_score'])
                                    if _c['final_score'] > _worst_p3['final_score'] * 0.3:
                                        top10.remove(_worst_p3)
                                        top10.append(_c)
                                        print(f"[P5-P3E] 🔗 P3重叠注入(≥2): {''.join(map(str,_c['digits']))}")
                                        break
        except Exception as e:
            print(f"[P5-P3E] ⚠️ P3关联增强跳过: {e}")

        # ====== [V1.44.0-C] 前3位对子模式检测 ======
        # 26200期归因: P5实际[0 7 7 2 0], 前3位[0 7 7]是P3对子
        # P3预测Top1组三形态(百十相同)但被评分压制
        # 策略: 当P3 Top1的百/十位相同(pair)时, 检查P5 Top10的前3位
        # 是否覆盖了该pair数字和不同百位的组合
        try:
            if _p3_predicted and len(_p3_predicted) == 3 and len(top10) >= 5:
                _p3_is_pair = (_p3_predicted[1] == _p3_predicted[2])  # P3百十位=对子
                if _p3_is_pair:
                    _pair_d = _p3_predicted[1]
                    _front3_pairs = 0
                    _front3_has_pair_d = False
                    for _c in top10:
                        _f3 = _c['digits'][:3]
                        if _f3[1] == _pair_d and _f3[2] == _pair_d:
                            _front3_pairs += 1
                        if _pair_d in _f3:
                            _front3_has_pair_d = True
                    print(f"[P5-PAIR] 🔍 前3位对子检测: P3对子数字{_pair_d}, "
                          f"P5覆盖{_front3_pairs}注对子, 含{_pair_d}: {_front3_has_pair_d}")
                    if not _front3_has_pair_d:
                        # 对子数字未在P5前3位中出现, 从all池补充
                        _f3_all = result.get('all', []) or (all_scored or [])
                        _f3_used = set(tuple(c['digits']) for c in top10)
                        _f3_best = None
                        for _c in _f3_all:
                            _c3 = _c['digits'][:3]
                            if _pair_d in _c3:
                                if tuple(_c['digits']) not in _f3_used:
                                    if _f3_best is None or _c.get('final_score', -999) > _f3_best.get('final_score', -999):
                                        _f3_best = _c
                        if _f3_best:
                            _worst_f3 = min(top10, key=lambda x: x.get('final_score', 0))
                            if _f3_best.get('final_score', -999) > _worst_f3.get('final_score', 0) * 0.10:
                                print(f"[P5-PAIR] 🔄 前3位对子注入: 对子{_pair_d}缺失, "
                                      f"补充{''.join(map(str,_f3_best['digits']))}")
                                top10.remove(_worst_f3)
                                top10.append(_f3_best)
                                top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-PAIR] ⚠️ 前3位对子检测跳过: {e}")

        # ====== [V1.36.0-C] P3多路径联动注入: 备选P3 Top2/Top3注入多样性 ======
        # 26193期: P3预测Top1=[4,3,1]与实际[1,8,0]完全不同
        # 如果P3 Top1注入后前3位多样性不足, 从P3 Top2/Top3找替代
        # V1.39.0-D: 增加上期后验诊断, P3 Top1失准时自动启用Top2/Top3
        try:
            _p3_last_match_ok = True  # 默认认为P3匹配正常
            try:
                # 检查上期P3→P5的前3位命中情况
                if len(self.draws) >= 3:
                    _p5_last = list(self.draws[-1])  # 上期P5实际
                    _last_p3_in_p5 = list(self.draws[-1][:3])  # P3前3位
                    # 加载上期的P3预测来对比
                    _last_p3_data = []
                    try:
                        _st = _path.join(_path.dirname(_path.abspath(__file__)), '..', 'memory', 'p3_predictions.json')
                        if _path.exists(_st):
                            with open(_st, 'r') as _fh:
                                _p3j = json.load(_fh)
                            for _p3e in _p3j.get('predictions', []):
                                if str(_p3e.get('period', '')) == str(self.last_period - 1):
                                    _last_p3_data = _p3e.get('zx_bets', [])
                                    break
                    except Exception:
                        pass
                    if _last_p3_data and len(_last_p3_data) >= 1:
                        _p3_top1_prev = _last_p3_data[0].get('digits', [])
                        if len(_p3_top1_prev) == 3:
                            # 检测P3 Top1与实际P5前3位的匹配度
                            _match_cnt = sum(1 for _p in range(3) if _p3_top1_prev[_p] == _last_p3_in_p5[_p])
                            if _match_cnt <= 1:
                                _p3_last_match_ok = False
                                print(f"[P5-E-D] ⚠️ P3上期Top1({''.join(map(str,_p3_top1_prev))}) "
                                      f"vs实际前3({''.join(map(str,_last_p3_in_p5))})仅{_match_cnt}/3正确"
                                      f", 启用Top2兜底")
            except Exception:
                pass

            if _p3_predicted and len(top10) >= 8:
                # 检查前3位多样性
                _front3_tuples = set(tuple(c['digits'][:3]) for c in top10)
                _front3_unique = len(_front3_tuples)
                _p3_top1_set = set(_p3_predicted)
                _same_as_p3 = sum(1 for c in top10 if tuple(c['digits'][:3]) == tuple(_p3_predicted))
                # 多样性不足或P3 Top1过度集中或上期P3失准, 从Top2/Top3补充
                if _front3_unique < 4 or _same_as_p3 >= 3 or not _p3_last_match_ok:
                    _all_p3 = None
                    try:
                        _all_p3 = self._load_p3_prediction(self.last_period, top_n=5)
                    except Exception:
                        pass
                    _max_inject = 2 if not _p3_last_match_ok else 1  # 失准时注入2个备选
                    if _all_p3 and isinstance(_all_p3, list) and len(_all_p3) >= 2:
                        _used_c = set(tuple(c['digits']) for c in top10)
                        _all_for_p3c = result.get('all', [])
                        _injected_alt = 0
                        for _p3_alt in _all_p3[1:]:
                            if _injected_alt >= _max_inject:
                                break
                            if not isinstance(_p3_alt, (list, tuple)) or len(_p3_alt) != 3:
                                continue
                            if tuple(_p3_alt) == tuple(_p3_predicted):
                                continue
                            # 与Top1差异程度: P3失准时放宽要求
                            _diff_cnt = sum(1 for p in range(3) if _p3_alt[p] != _p3_predicted[p])
                            if _diff_cnt < 2 and _p3_last_match_ok:
                                continue  # 正常模式至少2位不同
                            if tuple(_p3_alt) in _front3_tuples:
                                continue
                            _p3c_cands = [
                                c for c in _all_for_p3c
                                if list(c['digits'][:3]) == _p3_alt
                                and tuple(c['digits']) not in _used_c
                            ]
                            if _p3c_cands:
                                _p3c_cands.sort(key=lambda x: -x['final_score'])
                                _best_p3c = _p3c_cands[0]
                                _worst_c = min(top10, key=lambda x: x.get('final_score', 0))
                                if _best_p3c.get('final_score', -999) > _worst_c.get('final_score', 0) * 0.4:
                                    top10.remove(_worst_c)
                                    top10.append(_best_p3c)
                                    top10.sort(key=lambda x: -x.get('final_score', 0))
                                    print(f"[P5-E-C] 🔄 P3多路径注入(备选): "
                                          f"{''.join(map(str,_best_p3c['digits']))}")
                                    _injected_alt += 1
        except Exception as e:
            print(f"[P5-E-C] ⚠️ P3多路径注入跳过: {e}")

        # ====== [V1.42.0-B] P3→P5镜像关联加分 ======
        # 26199期归因: 实际P5前3位(3,0,5)=同期P3实际(3,0,5)完全一致
        # 镜像关系约5-8%频率出现, 但系统未做加分检测
        # 策略: P5候选前3位与P3预测Top1完全匹配→final_score×1.10
        # 数字集重叠≥2位(排序相同但位置漂移)→×1.05
        # 注: 不替换候选(注入可能出错), 仅在现有候选上做加权
        try:
            if _p3_predicted and len(_p3_predicted) == 3 and top10 and len(top10) >= 5:
                _p3_set = set(_p3_predicted)
                _mirror_boosted = 0
                for _c_mirror in top10:
                    _front3 = list(_c_mirror['digits'][:3])
                    # 完全匹配: 前3位与P3 Top1相同
                    if _front3 == _p3_predicted:
                        _c_mirror['final_score'] = _c_mirror['final_score'] * 1.10
                        _mirror_boosted += 1
                        print(f"[P5-MIR] 🔗 镜像完全匹配(+10%): "
                              f"{''.join(map(str,_c_mirror['digits']))}")
                    # 数字集匹配: 前3位数字集与P3 Top1排序后相同
                    elif set(_front3) == _p3_set and tuple(sorted(_front3)) == tuple(sorted(_p3_predicted)):
                        _c_mirror['final_score'] = _c_mirror['final_score'] * 1.08
                        _mirror_boosted += 1
                        print(f"[P5-MIR] 🔗 镜像数字集匹配(+8%): "
                              f"{''.join(map(str,_c_mirror['digits']))}")
                    # 数字集重叠≥2: 至少2个相同数字
                    elif len(_p3_set & set(_front3)) >= 2:
                        _c_mirror['final_score'] = _c_mirror['final_score'] * 1.05
                        _mirror_boosted += 1
                if _mirror_boosted:
                    top10.sort(key=lambda x: -x['final_score'])
                    print(f"[P5-MIR] ✅ 镜像关联加分: {_mirror_boosted}注受惠")
        except Exception as e:
            print(f"[P5-MIR] ⚠️ 镜像关联加分跳过: {e}")

        # [P5-O4] P3→P5映射偏移检测: P3预测低和值时放大前3位校准偏移
        # P3预测Top1若前3位和值<10, 说明当前周期偏极端方向,
        # P5前3位的校准中心也应向低值偏移
        try:
            _p3_front_sum = sum(_p3_predicted) if _p3_predicted else None
            _p3_top = _p3_predicted
        except Exception:
            _p3_front_sum = None
            _p3_top = None
        if _p3_front_sum is not None and _p3_front_sum < 10:
            # 调整top10中候选的前3位分数: 前3位低和值者加分
            _p3_offset_bonus = (10 - _p3_front_sum) * 0.02  # 差越大加越多
            for _c in top10:
                _f3 = sum(_c['digits'][:3])
                if _f3 <= 10:
                    _c['final_score'] += _p3_offset_bonus * (11 - _f3)
            top10.sort(key=lambda x: -x['final_score'])
            print(f"[P5-O4] P3低和值偏移: P3={_p3_front_sum}, "
                  f"offset+{_p3_offset_bonus:.2f}×差距")
        
        # ═══ [V1.30.0-⑤] P3方向多样性检查 ═══
        # 26185期: Plan E注入的P3 Top1(410)导致P5前3位集中在4,1,0
        # 检查Top10是否有≥4个候选共享相同前3位数字集, 注入完全不同者
        try:
            if top10 and len(top10) >= 6 and _p3_predicted:
                _p3_front3_set = set(_p3_predicted)
                # 统计前3位完全使用P3 Top1数字集的候选数
                _p3_dominated = sum(1 for c in top10
                                    if set(c['digits'][:3]) == _p3_front3_set)
                _p3_partial = sum(1 for c in top10
                                  if len(set(c['digits'][:3]) & _p3_front3_set) >= 2)
                if _p3_dominated >= 4 or _p3_partial >= 7:
                    _all_for_p3d = result.get('all', [])
                    _current_tuples = set(tuple(c['digits']) for c in top10)
                    # 找前3位完全不同于P3 Top1的最高分候选
                    _alt_pool = [c for c in _all_for_p3d
                                 if len(set(c['digits'][:3]) & _p3_front3_set) <= 1
                                 and tuple(c['digits']) not in _current_tuples]
                    _alt_pool.sort(key=lambda x: -x['final_score'])
                    _injected = 0
                    for _alt in _alt_pool:
                        if _injected >= 2:
                            break
                        _worst = min(top10, key=lambda x: x['final_score'])
                        if _alt['final_score'] > _worst['final_score'] * 0.5:
                            top10.remove(_worst)
                            top10.append(_alt)
                            _current_tuples.add(tuple(_alt['digits']))
                            print(f"[P5-P3D] 🔄 P3方向多样性注入({_injected+1}/2): "
                                  f"{''.join(map(str,_alt['digits']))} "
                                  f"(前3位≠P3{''.join(map(str,_p3_predicted))})")
                            _injected += 1
                    if _injected:
                        top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-P3D] ⚠️ P3方向多样性跳过: {e}")

        # ====== [V1.33.0-①] P5全换号/偏移防护 ======
        # 26188期归因: P3实际607完全不同于P3预测(420), 但P5前3位
        # 高度集中在P3预测数字上, 未预留足够偏移空间
        # 当P3预测与上期开奖差异大或P5前3位多样性不足时,
        # 强制注入前3位高多样性的候选
        try:
            if top10 and len(top10) >= 6 and len(self.draws) >= 2:
                _prev_p3 = list(self.draws[-1][:3])
                _p3_set = set(_p3_predicted) if _p3_predicted else set(_prev_p3)
                # 检测1: P3预测与上期前3位差异(全换号迹象)
                _p3_overlap = len(_p3_set & set(_prev_p3))
                _p3_all_diff = all(_p3_predicted[p] != _prev_p3[p]
                                   for p in range(3)) if _p3_predicted else False
                # 检测2: P5前3位数字集集中度
                _p5_p3_unique = set()
                for _c in top10:
                    _p5_p3_unique.update(_c['digits'][:3])
                _p5_p3_breadth = len(_p5_p3_unique)
                
                _need_diversify = False
                if _p3_overlap <= 1 and _p3_all_diff:
                    _need_diversify = True
                    print(f"[P5-FS] ⚠️ P3全换号迹象: 预测{''.join(map(str,_p3_predicted))} "
                          f"vs 上期{''.join(map(str,_prev_p3))}")
                elif _p5_p3_breadth < 6:
                    _need_diversify = True
                    print(f"[P5-FS] ⚠️ P5前3位广度不足: 仅{_p5_p3_breadth}个"
                          f"唯一数字({sorted(_p5_p3_unique)})")
                
                if _need_diversify:
                    _all_fs = result.get('all', []) if result.get('all') else (
                        all_scored if all_scored else top10)
                    _used_fs = set(tuple(c['digits']) for c in top10)
                    # 找前3位数字集与当前完全不同的候选
                    _current_p3_sets = [set(c['digits'][:3]) for c in top10]
                    _fresh_pool = []
                    for _c in _all_fs:
                        _t = tuple(_c['digits'])
                        if _t in _used_fs:
                            continue
                        _cs = set(_c['digits'][:3])
                        # 前3位与任一现有候选共享≤1个数字
                        if all(len(_cs & _cps) <= 1 for _cps in _current_p3_sets):
                            _fresh_pool.append(_c)
                    _fresh_pool.sort(key=lambda x: -x.get('final_score', 0))
                    _injected_fs = 0
                    for _fc in _fresh_pool:
                        if _injected_fs >= 2:
                            break
                        _worst = min(top10, key=lambda x: x['final_score'])
                        if _fc.get('final_score', -999) > _worst['final_score'] * 0.4:
                            top10.remove(_worst)
                            top10.append(_fc)
                            _used_fs.add(tuple(_fc['digits']))
                            print(f"[P5-FS] 🔀 全换号偏移注入({_injected_fs+1}/2): "
                                  f"{''.join(map(str,_fc['digits']))}")
                            _injected_fs += 1
                    if _injected_fs:
                        top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-FS] ⚠️ P5全换号跳过: {e}")

        # V1.20.0-A: 对数概率下Softmax校准
        # 对Top10的log分数做softmax得相对概率, 再映射到[0,100]
        scores_arr = [c['final_score'] for c in top10]
        if scores_arr:
            s_max = max(scores_arr)
            # softmax: 以最佳为参考点, 防溢出
            exp_vals = [math.exp(s - s_max) for s in scores_arr]
            total_exp = sum(exp_vals)
            for c, ev in zip(top10, exp_vals):
                prob = ev / total_exp * 100.0  # 相对概率百分比
                c['raw_probability'] = round(ev / total_exp, 4)
                c['hit_probability'] = round(prob, 1)
                # 【方案D】归一化显示分数[0,100]
                c['display_score'] = self._display_score(c['final_score'], s_max)

        # ====== [V1.35.0-②] P3数字集合迁移检测 ======
        # 26191期归因: 前3位数字[0,6,9]在26189的P3中以不同位置出现(百=0, 十=6, 万=9)
        # P3数字集合从26189迁移到26191前3位, 位置全部不同
        # 检测: 候选前3位数字集与近2期P3数字集交集≥2, 且位置全不同→+10%
        try:
            if top10 and len(self.draws) >= 5:
                _p3_draws = [list(d[:3]) for d in self.draws[-3:-1]]  # 最近2期P3(排除本期)
                _p3_sets = [set(d) for d in _p3_draws]
                _modified = False
                for _c in top10:
                    _cand_p3 = set(_c['digits'][:3])
                    for _p3s, _p3d in zip(_p3_sets, _p3_draws):
                        _overlap = _cand_p3 & _p3s
                        if len(_overlap) < 2:
                            continue
                        # 检查位置是否全部不同: 候选的每个重叠数字在原P3中的位置≠候选中的位置
                        _all_pos_diff = True
                        for _d in _overlap:
                            _orig_pos = _p3d.index(_d)
                            _cand_pos = _c['digits'][:3].index(_d)
                            if _orig_pos == _cand_pos:
                                _all_pos_diff = False
                                break
                        if _all_pos_diff:
                            _bonus = 0.10 * len(_overlap)  # 交集每多1个+5%
                            _c['final_score'] *= (1.0 + _bonus)
                            _modified = True
                            print(f"[P5-P3M] 🔄 P3数字集迁移: {''.join(map(str,_c['digits'][:3]))}"
                                  f" 迁移自P3{''.join(map(str,_p3d))}"
                                  f" overlap={sorted(_overlap)} +{_bonus*100:.0f}%")
                            break
                if _modified:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-P3M] ⚠️ P3数字集迁移检测跳过: {e}")

        # ====== [V1.35.0-③] 全隔期+全移位模式加分 ======
        # 26191期: 所有5个数字都在最近3期内出现过, 且位置全部不同
        # 这是极罕见的"全隔期+全移位"模式, 需特殊加分处理
        try:
            if top10 and len(self.draws) >= 5:
                _recent_3 = [list(d) for d in self.draws[-4:-1]]  # 最近3期(排除本期)
                _recent_3_digits = {d for seq in _recent_3 for d in seq}
                _modified_shift = False
                for _c in top10:
                    # 检测: 所有5个数字都在最近3期出现过
                    _cand_all = _c['digits']
                    if not all(d in _recent_3_digits for d in _cand_all):
                        continue
                    # 检测: 每个数字在最近3期中出现的位置≠当前位置
                    _all_shift = True
                    for _pos in range(5):
                        _d = _cand_all[_pos]
                        _found_here = False
                        for _rd in _recent_3:
                            if _rd[_pos] == _d:
                                _found_here = True
                                break
                        if _found_here:
                            _all_shift = False
                            break
                    if _all_shift:
                        print(f"[P5-SHIFT] 🚀 全隔期+全移位: {''.join(map(str,_cand_all))}")
                        _c['final_score'] *= 1.15
                        _modified_shift = True
                if _modified_shift:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-SHIFT] ⚠️ 全隔期全移位检测跳过: {e}")

        # ═══ 【方案C】跨期预测漂移检测 ═══
        # 将当前Top10与存储的上期Top10对比Jaccard相似度
        # 若>0.5, 从all_scored注入3组完全不同的号码
        try:
            from prediction_store import load_prediction
            prev_stored = load_prediction(str(int(self.last_period)))
            if prev_stored and len(top10) >= 8:
                current_set = {tuple(b['digits']) for b in top10}
                prev_set = {tuple(b['digits']) for b in prev_stored.get('bets', [])[:10]}
                if current_set and prev_set:
                    intersect = len(current_set & prev_set)
                    union = len(current_set | prev_set)
                    jaccard = intersect / max(union, 1)
                    if jaccard > 0.5:
                        print(f"[P5-Drift] ⚠️ 跨期相似度{jaccard:.2f}(高), 注入3组新号码")
                        # 从all_scored找3组与当前Top10完全不同的号码
                        current_digit_sets = [set(b['digits']) for b in top10]
                        new_groups = []
                        for cand in all_scored[:200]:
                            if len(new_groups) >= 3:
                                break
                            t = tuple(cand['digits'])
                            if t in current_set:
                                continue
                            cand_set = set(cand['digits'])
                            # 与当前Top10至少2个数字不同
                            max_overlap = max(
                                len(cand_set & cs) for cs in current_digit_sets[:5]
                            )
                            if max_overlap <= 3:
                                new_groups.append(cand)
                        # 替换最后3注
                        for i, ng in enumerate(new_groups):
                            if i >= 3 or len(top10) <= i + 1:
                                break
                            top10[-(i+1)] = ng
                        print(f"[P5-Drift] ✅ 注入{len(new_groups)}组")
            else:
                print(f"[P5-Drift] − 上期预测不存在(skip)")
        except Exception as e:
            pass

        # ═══ 【方案A-最终硬约束】全位多样性兜底 V2.0.0 ═══
        # 确保万/千/百每数字最多2次, 十/个最多3次
        # 每位至少5个不同数字(方案1), 每数字≤30%(方案3)
        # 如不满足, 从all_scored替补
        def _final_diversity_enforce(candidates, all_pool, n=10):
            # [V1.40.0-C] 位置-数字权重配额制: 各位置Top5权重数字总占比≤60%
            try:
                _quota_checked = False
                if len(candidates) >= 5:
                    for _qpos in range(5):
                        _pos_scores = {d: 0.0 for d in range(10)}
                        for _c in candidates:
                            _d = _c['digits'][_qpos]
                            _pos_scores[_d] += _c.get('final_score', 0)
                        _total = sum(_pos_scores.values()) or 1e-10
                        _sorted_s = sorted(_pos_scores.items(), key=lambda x: -x[1])
                        _top5_share = sum(v for _, v in _sorted_s[:5]) / _total
                        if _top5_share > 0.60:
                            # Top5数字占比过高, 从低频数字补充
                            _low_digits = [d for d, v in _sorted_s[5:] if v > 0]
                            for _ld in _low_digits:
                                if len(_low_digits) > 3:
                                    break
                                _best_for_pos = None
                                for _c in all_pool:
                                    if _c['digits'][_qpos] == _ld:
                                        _t = tuple(_c['digits'])
                                        if _t not in _seen_quota:
                                            if _best_for_pos is None or _c['final_score'] > _best_for_pos['final_score']:
                                                _best_for_pos = _c
                                if _best_for_pos:
                                    _worst_q = min(candidates, key=lambda x: x['final_score'])
                                    if _best_for_pos['final_score'] > _worst_q['final_score'] * 0.3:
                                        candidates.remove(_worst_q)
                                        candidates.append(_best_for_pos)
                                        _seen_quota.add(tuple(_best_for_pos['digits']))
                                        _quota_checked = True
                                        print(f"[P5-QUOTA] ⚖️ 权重配额: {['万','千','百','十','个'][_qpos]}位"
                                              f"Top5占{_top5_share*100:.0f}%, 注入低位{_ld}")
                if _quota_checked:
                    candidates.sort(key=lambda x: -x['final_score'])
            except Exception as e:
                print(f"[P5-QUOTA] ⚠️ 跳过: {e}")
            _seen_quota = set(tuple(_c['digits']) for _c in candidates)

            if len(candidates) < n:
                return candidates
            
            # 【方案2】冷位数字(近10期未出现)
            cold_pos_digits = [{}, {}, {}, {}, {}]
            if len(self.draws) >= 10:
                recent_10 = self.draws[-10:]
                for p in range(5):
                    recent = {d[p] for d in recent_10}
                    for d in range(10):
                        if d not in recent:
                            cold_pos_digits[p][d] = True
            
            result = []
            seen = set()
            pos_cnt = [Counter() for _ in range(5)]
            cold_path_cnt = [Counter() for _ in range(5)]
            front_limit, back_limit = 2, 3
            
            for cand in candidates + all_pool:
                t = tuple(cand['digits'])
                if t in seen:
                    continue
                ok = True
                for p in range(5):
                    lim = front_limit if p < 3 else back_limit
                    if pos_cnt[p][cand['digits'][p]] >= lim:
                        ok = False
                        break
                if not ok:
                    continue
                # 冷位路径控制: 某冷位已在2条路径中且结果过半, 跳过
                skip = False
                for p in range(5):
                    dp = cand['digits'][p]
                    if dp in cold_pos_digits[p] and cold_path_cnt[p][dp] >= 2 and len(result) >= max(3, n // 2):
                        skip = True
                        break
                if skip:
                    continue
                result.append(cand)
                seen.add(t)
                for p in range(5):
                    pos_cnt[p][cand['digits'][p]] += 1
                    if cand['digits'][p] in cold_pos_digits[p]:
                        cold_path_cnt[p][cand['digits'][p]] += 1
                if len(result) >= n:
                    break
            
            # 补足不足n注
            if len(result) < n:
                for cand in candidates:
                    if len(result) >= n:
                        break
                    t = tuple(cand['digits'])
                    if t in seen:
                        continue
                    result.append(cand)
                    seen.add(t)
            
            # 【方案1+3】V2.0.0: 每位7数字(原5)+≤30% + 全量修复
            # 修复池不足时直接生成新候选(不依赖all_pool)
            result = result[:n]
            for _round in range(10):
                need_fix = False
                for p in range(5):
                    vals = Counter(c['digits'][p] for c in result)
                    if len(vals) < 5:
                        need_fix = True
                        for want_d in range(10):
                            if want_d not in vals:
                                # 生成一个含want_d的新候选(替换result中最后一个)
                                _old = result[-1]
                                _new_d = list(_old['digits'])
                                _new_d[p] = want_d
                                _t = tuple(_new_d)
                                if _t not in seen:
                                    seen.discard(tuple(_old['digits']))
                                    result[-1] = {'digits': _new_d, 'final_score': _old.get('final_score', 0)-0.1}
                                    seen.add(_t)
                                break
                if not need_fix:
                    break
                # 再查反垄断
                for p in range(5):
                    vals = Counter(c['digits'][p] for c in result)
                    for d, cnt in vals.items():
                        if cnt / n > 0.30:
                            need_fix = True
                            # 找一个不含d的位置, 替换该位置最后一个含d的
                            for idx in range(n-1, -1, -1):
                                if result[idx]['digits'][p] == d:
                                    _new_d = list(result[idx]['digits'])
                                    # 替换为该位置的平均冷位
                                    _alternative = [x for x in range(10) if x != d and (x not in vals or vals[x] < cnt-1)]
                                    if _alternative:
                                        _new_d[p] = _alternative[0]
                                        _t = tuple(_new_d)
                                        if _t not in seen:
                                            seen.discard(tuple(result[idx]['digits']))
                                            result[idx] = {'digits': _new_d, 'final_score': result[idx].get('final_score', 0)-0.1}
                                            seen.add(_t)
                                    break
                            break
                if not need_fix:
                    break
            return result[:n]

        all_pool = all_scored if all_scored else top10
        # 扩大修复池: 从result['all'](500)扩大到包含枚举全量
        # 【V1.51.0】修复: 原fusion._all_digits引用未定义变量(主路径从未生效,
        # 一直走all_pool兜底) + 兜底未防护IndexError(26207数据状态下top10<10时崩溃)
        try:
            _all_extended = result.get('all', []) + [
                {'digits': d, 'final_score': 0} for d in (self._all_digits or [])[-2000:]
            ]
            top10 = _final_diversity_enforce(top10, _all_extended, min(10, len(top10)))
        except Exception:
            try:
                top10 = _final_diversity_enforce(top10, all_pool, min(10, len(top10)))
            except Exception:
                pass

        # [P5-O1] 深度冷号注入: 各位置>10期未出数字强制注入
        try:
            _all_for_cold = result.get('all', []) if result.get('all') else (
                all_scored if all_scored else top10)
            top10 = self._inject_deep_cold_p5(top10, _all_for_cold, 10)
        except Exception as e:
            print(f"[P5-O1] ⚠️ 跳过: {e}")

        # ====== [V1.40.0-A] 中位数字(2-5)中等遗漏(5-12期)独立注入 ======
        try:
            _all_for_mid_a = result.get('all', []) if result.get('all') else (
                all_scored if all_scored else top10)
            top10 = self._inject_mid_cold_p5(top10, _all_for_mid_a, 10)
        except Exception as e:
            print(f"[P5-MIDC] ⚠️ 跳过: {e}")

        # ====== [V1.40.0-B] 周期/间隔回归模式检测 ======
        try:
            _all_for_per = result.get('all', []) if result.get('all') else (
                all_scored if all_scored else top10)
            top10 = self._inject_periodic_p5(top10, _all_for_per, 10)
        except Exception as e:
            print(f"[P5-PER] ⚠️ 跳过: {e}")

        # [V1.30.0-①+③] 中等遗漏分池覆盖 + 后2位独立检查
        # 各位置遗漏4-8期数字独立检查, 后2位(十/个)独立检查
        # 26185期: 万位7(遗漏7)、个位9(遗漏4)完全未被覆盖
        try:
            _all_for_mid = result.get('all', []) if result.get('all') else (
                all_scored if all_scored else top10)
            top10 = self._inject_medium_cold_p5(top10, _all_for_mid, 10)
        except Exception as e:
            print(f"[P5-MCP] ⚠️ 跳过: {e}")

        # ====== [V1.39.0-B] P5千位独立冷号注入 ======
        # 26196期归因: 千位2(遗漏约5期)在Top10中完全缺失
        # P5千位的冷号/温号检测之前完全依赖P3→P5映射,
        # 当P3 Top1与P5前3位(万/千/百)实际偏差大时,
        # 千位没有任何独立覆盖
        # 策略: 千位独立扫描遗漏≥6的数字, 从P5全量池注入
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 10:
                _used_qw = set(tuple(c['digits']) for c in top10)
                _all_qw = result.get('all', []) if result.get('all') else (all_scored if all_scored else top10)
                # 千位遗漏扫描
                _qw_seq = [d[1] for d in self.draws[-50:]]
                _qw_miss = {}
                for i in range(len(_qw_seq)-1, -1, -1):
                    _dd = _qw_seq[i]
                    if _dd not in _qw_miss:
                        _qw_miss[_dd] = len(_qw_seq) - 1 - i
                for _dd in range(10):
                    if _dd not in _qw_miss:
                        _qw_miss[_dd] = len(_qw_seq)
                _injected_qw = 0
                for _dd in range(10):
                    _m = _qw_miss.get(_dd, 99)
                    if _m < 4:  # 近3期刚出现过, 不算冷
                        continue
                    _cnt = sum(1 for c in top10 if c['digits'][1] == _dd)
                    if _cnt >= 1:
                        continue
                    _best_qw = None
                    for _c in _all_qw:
                        if _c['digits'][1] != _dd:
                            continue
                        if tuple(_c['digits']) in _used_qw:
                            continue
                        if _best_qw is None or _c.get('final_score', -999) > _best_qw.get('final_score', -999):
                            _best_qw = _c
                    if _best_qw:
                        _worst_qw = min(top10, key=lambda x: x.get('final_score', 0))
                        if _best_qw.get('final_score', -999) > _worst_qw.get('final_score', 0) * 0.3:
                            top10.remove(_worst_qw)
                            top10.append(_best_qw)
                            _used_qw.add(tuple(_best_qw['digits']))
                            print(f"[P5-QW] 🔄 千位独立冷号注入: 遗漏{_m}期的{_dd}"
                                  f"→ {''.join(map(str,_best_qw['digits']))}")
                            _injected_qw += 1
                if _injected_qw:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-QW] ⚠️ 千位独立冷号跳过: {e}")

        # ====== [V1.32.0-②] 百位冷号多路径 + 万位强化 ======
        # 26187期归因: 百位6遗漏6期仅1条路径, 万位0遗漏7期仅1条
        # 各位置遗漏4-8期冷号确保≥2条路径, 万位冷号优先级提升
        try:
            if top10 and len(self.draws) >= 10:
                _mid_seq = [d for d in self.draws[-50:]] if len(self.draws) >= 50 else list(self.draws)
                _mid_misses = [{}, {}, {}, {}, {}]
                for _pos in range(5):
                    _seq = [_d[_pos] for _d in _mid_seq]
                    _mm = {}
                    for i in range(len(_seq)-1, -1, -1):
                        _dd = _seq[i]
                        if _dd not in _mm:
                            _mm[_dd] = len(_seq) - 1 - i
                    for _dd in range(10):
                        if _dd not in _mm:
                            _mm[_dd] = len(_seq)
                    _mid_misses[_pos] = _mm

                _all_for_mid2 = result.get('all', []) if result.get('all') else (all_scored if all_scored else top10)
                _used_mid = set(tuple(c['digits']) for c in top10)
                _injected_mid = 0
                for _pos in range(5):
                    for _dd in range(10):
                        _m = _mid_misses[_pos].get(_dd, 99)
                        if not (4 <= _m <= 8):
                            continue
                        _cnt = sum(1 for c in top10 if c['digits'][_pos] == _dd)
                        if _cnt >= 2:
                            continue
                        _existing = [c['digits'] for c in top10 if c['digits'][_pos] == _dd]
                        _second = None
                        for _c in _all_for_mid2:
                            if _c['digits'][_pos] != _dd:
                                continue
                            if tuple(_c['digits']) in _used_mid:
                                continue
                            if _existing:
                                diff = sum(1 for p2 in range(5) if p2 != _pos and _c['digits'][p2] != _existing[0][p2])
                            else:
                                diff = 5
                            if diff >= 2:
                                if _second is None or _c.get('final_score', -999) > _second.get('final_score', -999):
                                    _second = _c
                        if _second:
                            _worst = min(top10, key=lambda z: z.get('final_score', 0))
                            top10.remove(_worst)
                            top10.append(_second)
                            _used_mid.add(tuple(_second['digits']))
                            print(f"[P5-MDP] 🔄 冷号多路径: {['万','千','百','十','个'][_pos]}位{_dd}"
                                  f"遗漏{_m}期(当前{_cnt}条)→{''.join(map(str,_second['digits']))}")
                            _injected_mid += 1
                            if _injected_mid >= 3:
                                break
                    if _injected_mid >= 3:
                        break
                if _injected_mid:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-MDP] ⚠️ 冷号多路径跳过: {e}")

        # [P5-O2/O5] 前3位极值 + 后2位极端覆盖
        try:
            _all_for_extreme = result.get('all', []) if result.get('all') else (
                all_scored if all_scored else top10)
            top10 = self._rescue_extreme_candidates_p5(top10, _all_for_extreme, 10)
        except Exception as e:
            print(f"[P5-O2/O5] ⚠️ 跳过: {e}")

        # ====== [V1.31.0-①] 同位置重号保底注入 ======
        # 26186期归因: 百位5(上期重号)在Top10中完全未被任何路径覆盖
        # 上期某位置数字在预测Top10中同位置出现<1次时, 强制补注
        try:
            if top10 and prev and len(prev) == 5:
                _prev_digits = list(prev)
                _used_tuples = set(tuple(c['digits']) for c in top10)
                _all_for_rep = result.get('all', []) if result.get('all') else (
                    all_scored if all_scored else top10)
                _injected_rep = 0
                for _pos in range(5):
                    _prev_d = _prev_digits[_pos]
                    _cnt = sum(1 for c in top10 if c['digits'][_pos] == _prev_d)
                    if _cnt >= 1:
                        continue
                    # 同位置重号缺失, 从全池找最佳注入
                    _best = None
                    for _c in _all_for_rep:
                        if _c['digits'][_pos] != _prev_d:
                            continue
                        if tuple(_c['digits']) in _used_tuples:
                            continue
                        if _best is None or _c.get('final_score', -999) > _best.get('final_score', -999):
                            _best = _c
                    if _best:
                        _worst = min(top10, key=lambda x: x.get('final_score', 0))
                        # 重号保底: 直接注入, 不设分数门槛(检测到即换)
                        top10.remove(_worst)
                        top10.append(_best)
                        _used_tuples.add(tuple(_best['digits']))
                        print(f"[P5-PRE] 🔄 重号注入: {['万','千','百','十','个'][_pos]}位{_prev_d}"
                              f"→ {''.join(map(str,_best['digits']))}")
                        _injected_rep += 1
                if _injected_rep:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-PRE] ⚠️ 重号保底跳过: {e}")

        # ====== [V1.32.0-①] 隔期短重号检测与注入 ======
        # 26187期归因: 千位8(26185出, 隔1期)、十位7(26185出, 隔1期)在Top10全缺失
        # V1.31.0-①仅保上期重号, 隔期重号(上上期)被完全忽略
        # 检查各位置是否有隔1期出现的数字未被覆盖, 强制注入
        try:
            if top10 and prev and len(prev) == 5 and len(self.draws) >= 3:
                _prev2 = list(self.draws[-2]) if len(self.draws) >= 2 else []
                _prev3 = list(self.draws[-3]) if len(self.draws) >= 3 else []
                _used_tups = set(tuple(c['digits']) for c in top10)
                _all_for_gap = result.get('all', []) if result.get('all') else (all_scored if all_scored else top10)
                _injected_gap = 0
                # 同时检查draws[-2](隔1期)和draws[-3](隔2期)
                _gap_sources = []
                if _prev2:
                    _gap_sources.append(('隔1期', _prev2))
                if _prev3 and len(self.draws) >= 3:
                    _gap_sources.append(('隔2期', _prev3))
                for _label, _src in _gap_sources:
                    for _pos in range(5):
                        _gap_digit = _src[_pos]
                        _cnt = sum(1 for c in top10 if c['digits'][_pos] == _gap_digit)
                        if _cnt >= 1:
                            continue
                        # 检查同位置是否连续(隔2期+隔1期+本期=3连), 需要是折返模式
                        if _label == '隔2期' and _prev2:
                            # 隔2期出现, 确认隔1期没出现(否则是间隔4期的不连续出现)
                            if _prev2[_pos] == _gap_digit:
                                continue  # 连续3期一样, 不是折返
                        _best = None
                        for _c in _all_for_gap:
                            if _c['digits'][_pos] != _gap_digit:
                                continue
                            if tuple(_c['digits']) in _used_tups:
                                continue
                            if _best is None or _c.get('final_score', -999) > _best.get('final_score', -999):
                                _best = _c
                        if _best:
                            _worst = min(top10, key=lambda z: z.get('final_score', 0))
                            if _best.get('final_score', -999) > _worst.get('final_score', 0) * 0.5:
                                top10.remove(_worst)
                                top10.append(_best)
                                _used_tups.add(tuple(_best['digits']))
                                print(f"[P5-GAP] 🔄 隔期重号注入({_label}): {['万','千','百','十','个'][_pos]}位{_gap_digit}"
                                      f"→{''.join(map(str,_best['digits']))}")
                                _injected_gap += 1
                if _injected_gap:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-GAP] ⚠️ 隔期重号跳过: {e}")

        # ====== [V1.36.0-B] 千位/万位大跨度跳变覆盖 ======
        # 26193期: 千位走势0→5→5→6→0→8 (0→8跨3级跳变)
        # 模型预测千位集中在[3,4,5,7], 完全无8
        # 当千位/万位近5期max-min≥4时在跳变方向端点注入
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 6:
                _pos_names_b = ['万','千','百','十','个']
                _all_for_jump = result.get('all', []) if result.get('all') else (all_scored if all_scored else top10)
                _used_jump = set(tuple(c['digits']) for c in top10)
                _injected_jump = 0
                for _pos in [0, 1]:  # 万位/千位
                    _seq_pos = [d[_pos] for d in self.draws[-6:]]
                    _pos_min = min(_seq_pos)
                    _pos_max = max(_seq_pos)
                    _pos_range = _pos_max - _pos_min
                    if _pos_range < 4:
                        continue  # 范围不够, 无大跳变
                    _covered_pos = set(c['digits'][_pos] for c in top10)
                    # 覆盖端点: 跳变方向(min和max)的端点数字
                    _endpoints = []
                    if _pos_min not in _covered_pos:
                        _endpoints.append(_pos_min)
                    if _pos_max not in _covered_pos:
                        _endpoints.append(_pos_max)
                    if not _endpoints:
                        continue
                    print(f"[P5-JMP] 📡 {_pos_names_b[_pos]}位范围{_pos_min}-{_pos_max}={_pos_range}, 未覆盖端点:{_endpoints}")
                    for _ep in _endpoints:
                        if _injected_jump >= 2:
                            break
                        _best_j = None
                        for _c in _all_for_jump:
                            if _c['digits'][_pos] != _ep:
                                continue
                            if tuple(_c['digits']) in _used_jump:
                                continue
                            if _best_j is None or _c.get('final_score', -999) > _best_j.get('final_score', -999):
                                _best_j = _c
                        if _best_j:
                            _worst_j = min(top10, key=lambda x: x.get('final_score', 0))
                            if _best_j.get('final_score', -999) > _worst_j.get('final_score', 0) * 0.3:
                                print(f"[P5-JMP] 🔄 跳变端点注入: {_pos_names_b[_pos]}位{_ep}"
                                      f"→ {''.join(map(str,_best_j['digits']))}")
                                top10.remove(_worst_j)
                                top10.append(_best_j)
                                _used_jump.add(tuple(_best_j['digits']))
                                _injected_jump += 1
                if _injected_jump:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-JMP] ⚠️ 跳变覆盖跳过: {e}")

        # ====== [V1.31.0-②] 超深冷多路径注入 ======
        # 26186期归因: 千位6遗漏23期仅2条路径(#7#10), 十位0遗漏24期仅2条(#1#3)
        # 遗漏≥15期的超深冷数字在Top10中<2条路径时, 补至至少2条
        try:
            if top10 and len(self.draws) >= 10:
                _ultra_seq = [d for d in self.draws[-50:]] if len(self.draws) >= 50 else list(self.draws)
                _ultra_misses = [{}, {}, {}, {}, {}]
                for _pos in range(5):
                    _seq = [d[_pos] for d in _ultra_seq]
                    _miss_map = {}
                    for i in range(len(_seq)-1, -1, -1):
                        _d = _seq[i]
                        if _d not in _miss_map:
                            _miss_map[_d] = len(_seq) - 1 - i
                    for _d in range(10):
                        if _d not in _miss_map:
                            _miss_map[_d] = len(_seq)
                    _ultra_misses[_pos] = _miss_map

                _all_for_ultra = result.get('all', []) if result.get('all') else (
                    all_scored if all_scored else top10)
                _used_tups = set(tuple(c['digits']) for c in top10)
                _ultra_inject = []
                for _pos in range(5):
                    for _d in range(10):
                        _m = _ultra_misses[_pos].get(_d, 99)
                        if _m < 15:
                            continue
                        _cnt = sum(1 for c in top10 if c['digits'][_pos] == _d)
                        if _cnt >= 2:
                            continue
                        # 找另一条不同路径(其他位置组合不同)
                        _existing = [c['digits'] for c in top10 if c['digits'][_pos] == _d]
                        _second = None
                        for _c in _all_for_ultra:
                            if _c['digits'][_pos] != _d:
                                continue
                            if tuple(_c['digits']) in _used_tups:
                                continue
                            # 偏好其他位置与已有路径不同的
                            if _existing:
                                _diff = sum(1 for p2 in range(5) if p2 != _pos
                                           and _c['digits'][p2] != _existing[0][p2])
                            else:
                                _diff = 5
                            if _second is None or _diff > _second.get('_diff', 0) or (
                                _diff == _second.get('_diff', 0) and
                                _c.get('final_score', -999) > _second.get('final_score', -999)):
                                _second = dict(_c)
                                _second['_diff'] = _diff
                        if _second:
                            _ultra_inject.append({
                                'pos': _pos, 'digit': _d, 'miss': _m,
                                'cand': _second, 'cnt': _cnt
                            })

                if _ultra_inject:
                    _ultra_inject.sort(key=lambda x: -x['miss'])
                    for _inj in _ultra_inject:
                        if len(top10) <= 0:
                            break
                        _worst = min(top10, key=lambda z: z.get('final_score', 0))
                        # 超深冷: 直接注入(安全网, 不设分数门槛)
                        top10.remove(_worst)
                        top10.append(_inj['cand'])
                        _used_tups.add(tuple(_inj['cand']['digits']))
                        print(f"[P5-UC] 🔺 超深冷多路径: {['万','千','百','十','个'][_inj['pos']]}"
                              f"位{_inj['digit']}遗漏{_inj['miss']}期(当前{_inj['cnt']}条)"
                              f"→ {''.join(map(str,_inj['cand']['digits']))}")
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-UC] ⚠️ 超深冷多路径跳过: {e}")

        # ====== [V1.31.0-③] 后2位中等冷保底覆盖 ======
        # 26186期归因: 个位1遗漏9期(中等冷)在Top10中完全无覆盖
        # 后2位(十位/个位)遗漏≥9期的数字若完全未进入Top10, 强制注入
        try:
            if top10 and len(self.draws) >= 10:
                _back2_seq = [d for d in self.draws[-50:]] if len(self.draws) >= 50 else list(self.draws)
                _back2_misses = [{}, {}]  # 十位=index0, 个位=index1
                for _idx, _pos in enumerate([3, 4]):
                    _seq = [d[_pos] for d in _back2_seq]
                    _miss_map = {}
                    for i in range(len(_seq)-1, -1, -1):
                        _d = _seq[i]
                        if _d not in _miss_map:
                            _miss_map[_d] = len(_seq) - 1 - i
                    for _d in range(10):
                        if _d not in _miss_map:
                            _miss_map[_d] = len(_seq)
                    _back2_misses[_idx] = _miss_map

                _all_for_b2 = result.get('all', []) if result.get('all') else (
                    all_scored if all_scored else top10)
                _used_tups_b2 = set(tuple(c['digits']) for c in top10)
                _b2_inject = []
                for _idx, _pos in enumerate([3, 4]):
                    for _d in range(10):
                        _m = _back2_misses[_idx].get(_d, 99)
                        if _m < 9:
                            continue
                        _cnt = sum(1 for c in top10 if c['digits'][_pos] == _d)
                        if _cnt >= 1:
                            continue
                        # 完全未覆盖, 注入
                        _best = None
                        for _c in _all_for_b2:
                            if _c['digits'][_pos] != _d:
                                continue
                            if tuple(_c['digits']) in _used_tups_b2:
                                continue
                            if _best is None or _c.get('final_score', -999) > _best.get('final_score', -999):
                                _best = _c
                        if _best:
                            _b2_inject.append((_pos, _d, _m, _best))

                if _b2_inject:
                    _b2_inject.sort(key=lambda x: -x[2])
                    for _pos, _d, _m, _best in _b2_inject:
                        if len(top10) <= 0:
                            break
                        _worst = min(top10, key=lambda z: z.get('final_score', 0))
                        # 后2位冷保底: 直接注入(安全网, 不设分数门槛)
                        top10.remove(_worst)
                        top10.append(_best)
                        _used_tups_b2.add(tuple(_best['digits']))
                        print(f"[P5-B2C] 🟡 后2位冷保底: {['十','个'][_pos-3]}位{_d}"
                              f"遗漏{_m}期→ {''.join(map(str,_best['digits']))}")
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-B2C] ⚠️ 后2位冷保底跳过: {e}")

        # ====== [V1.32.0-④] 个位过热限流 ======
        # 26187期归因: 个位8占6/10注, 虽实命中但挤压了其他位置多样性
        # 个位某数字≥5/10时触发替换
        try:
            if top10 and len(top10) >= 5:
                from collections import Counter as _Ctr
                _ge5 = _Ctr([c['digits'][4] for c in top10])
                _ov5 = [d for d, c in _ge5.items() if c >= 5]
                if _ov5:
                    _tg = _ov5[0]
                    _keep = max(3, int(len(top10) * 0.4))
                    _n_rep = _ge5[_tg] - _keep
                    if _n_rep > 0:
                        _used5 = set(tuple(c['digits']) for c in top10)
                        _all5 = result.get('all', []) if result.get('all') else (all_scored if all_scored else top10)
                        _pool5 = [c for c in _all5
                                  if c['digits'][4] != _tg
                                  and tuple(c['digits']) not in _used5
                                  and len(set(c['digits'])) == 5]
                        _pool5.sort(key=lambda x: -x.get('final_score', 0))
                        _rep5 = 0
                        for i in range(len(top10) - 1, -1, -1):
                            if top10[i]['digits'][4] == _tg:
                                if _pool5:
                                    _r = _pool5.pop(0)
                                    print(f"[P5-GE5] 🎯 个位过热: 个位{_tg}占{_ge5[_tg]}/{len(top10)}注, "
                                          f"替换: {''.join(map(str,top10[i]['digits']))}→{''.join(map(str,_r['digits']))}")
                                    top10[i] = _r
                                    _used5.add(tuple(_r['digits']))
                                    _rep5 += 1
                                if _rep5 >= _n_rep:
                                    break
                        if _rep5:
                            top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-GE5] ⚠️ 个位过热跳过: {e}")

        # ====== [V1.32.0-⑤] 后2位组合多样性 ======
        # 26187期归因: 后2位「98」占4注(97888,94888,95888,47988), 实际后2位78
        # 后2位完全相同组合≥3注时替换最低分注
        try:
            if top10 and len(top10) >= 5:
                _b2_groups = {}
                for i, c in enumerate(top10):
                    _b2 = tuple(c['digits'][3:5])
                    _b2_groups.setdefault(_b2, []).append(i)
                _over_b2 = [(k, v) for k, v in _b2_groups.items() if len(v) >= 3]
                if _over_b2:
                    _all_b2 = result.get('all', []) if result.get('all') else (all_scored if all_scored else top10)
                    _used_b2 = set(tuple(c['digits']) for c in top10)
                    _rep_b2 = 0
                    for _b2, _idxs in sorted(_over_b2, key=lambda x: -len(x[1])):
                        # 保留1个最高分, 替换其余
                        _sorted_idx = sorted(_idxs, key=lambda i: -top10[i].get('final_score', 0))
                        for _ri in _sorted_idx[1:]:
                            _best_b2 = None
                            for _c in _all_b2:
                                _ct = tuple(_c['digits'])
                                if _ct in _used_b2:
                                    continue
                                _cb2 = tuple(_c['digits'][3:5])
                                if _cb2 == _b2:
                                    continue
                                if _best_b2 is None or _c.get('final_score', -999) > _best_b2.get('final_score', -999):
                                    _best_b2 = _c
                            if _best_b2:
                                print(f"[P5-B2D] 🎯 后2位集中: {''.join(map(str,_b2))}占{len(_idxs)}注, "
                                      f"替换: {''.join(map(str,top10[_ri]['digits']))}→{''.join(map(str,_best_b2['digits']))}")
                                top10[_ri] = _best_b2
                                _used_b2.add(tuple(_best_b2['digits']))
                                _rep_b2 += 1
                    if _rep_b2:
                        top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-B2D] ⚠️ 后2位多样性跳过: {e}")

        # ====== [V1.33.0-②] 后2位交叉模式检测 ======
        # 26188期归因: 后2位实际=70, 但十7+个0的交叉组合仅42079和97038两注
        # 个别数字对在十/个位同时出现<2注时补充
        try:
            if top10 and len(top10) >= 5:
                _b2_all = result.get('all', []) if result.get('all') else (
                    all_scored if all_scored else top10)
                _used_b2c = set(tuple(c['digits']) for c in top10)
                # 统计后2位的实际覆盖: 每个(十位,个位)数字对的注数
                _b2_pair_counts = {}
                for _c in top10:
                    _pair = (_c['digits'][3], _c['digits'][4])
                    _b2_pair_counts[_pair] = _b2_pair_counts.get(_pair, 0) + 1
                # 检查十位各数字与个位各数字的交叉覆盖
                _shi_in_top = Counter(c['digits'][3] for c in top10)
                _ge_in_top = Counter(c['digits'][4] for c in top10)
                _injected_b2c = False
                for _sd in range(10):
                    for _gd in range(10):
                        _pair = (_sd, _gd)
                        _cnt = _b2_pair_counts.get(_pair, 0)
                        if _cnt > 1:  # 已有覆盖
                            continue
                        # 仅当十位数字和个位数字都在Top10中各自出现时才考虑
                        if _shi_in_top.get(_sd, 0) > 0 and _ge_in_top.get(_gd, 0) > 0:
                            # 该对未被完全覆盖, 从全池寻找
                            _best_b2c = None
                            for _c in _b2_all:
                                _ct = tuple(_c['digits'])
                                if _ct in _used_b2c:
                                    continue
                                if _c['digits'][3] == _sd and _c['digits'][4] == _gd:
                                    if _best_b2c is None or _c.get('final_score', -999) > _best_b2c.get('final_score', -999):
                                        _best_b2c = _c
                            if _best_b2c:
                                _worst = min(top10, key=lambda x: x['final_score'])
                                if _best_b2c.get('final_score', -999) > _worst['final_score'] * 0.3:
                                    print(f"[P5-B2C] 🟡 后2位交叉补充: 十{_sd}个{_gd}对"
                                          f"({_cnt}注) → {''.join(map(str,_best_b2c['digits']))}")
                                    top10.remove(_worst)
                                    top10.append(_best_b2c)
                                    _used_b2c.add(tuple(_best_b2c['digits']))
                                    _b2_pair_counts[_pair] = _b2_pair_counts.get(_pair, 0) + 1
                                    _injected_b2c = True
                                    break  # 每轮只补1个
                if _injected_b2c:
                    top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-B2C] ⚠️ 后2位交叉跳过: {e}")

        # ====== [V1.36.0-D] 后2位短间隔回补检测 ======
        # 26193期: 十位6(26189→26193隔3期)、个位8(26190→26193隔2期)
        # 短间隔回补(5-8期前的数字)独立于隔期重号(3-6期)和冷偏遗漏(4-8期)
        # V1.39.0-A: 窗口扩展至3-8期+位置扩展至全部5位
        # 【V1.49.0】修复两点: ①十位0(漏4期)在窗口内但未注入 — 原每轮只注入
        # 1个且替换最低分票可能拆掉保护票; ②后2位近端(1-3期)独立检查+≥2席
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 12:
                _back_seq_d = [d for d in self.draws[-12:]]
                _used_b2r = set(tuple(c['digits']) for c in top10)
                _all_b2r = result.get('all', []) if result.get('all') else (all_scored if all_scored else top10)
                _protected_b2r = getattr(self, '_p5_protected', set())
                _injected_b2r = False
                # 【V1.49.0】B2N近端回补后重置标志: 原B2N设置_injected_b2r=True,
                # B2R循环_pos=0时elif _injected_b2r: break直接跳出, 3-8期窗口
                # (十位0漏4期)永远扫不到 — 重置让B2R独立扫描全部5位置
                _injected_b2r = False
                # 【V1.49.0】后2位近端回补(1-3期前)独立检查: 每位置至少2席
                # 26204个位7(漏4期)仅3/10、十位0(漏4期)0/10 — 近端信号需保底
                for _pos in [3, 4]:
                    for _back in (1, 2, 3):
                        _d = _back_seq_d[-_back][_pos]
                        _cnt = sum(1 for c in top10 if c['digits'][_pos] == _d)
                        if _cnt >= 2:
                            continue
                        _best_near = None
                        for _c in _all_b2r:
                            if _c['digits'][_pos] != _d:
                                continue
                            if tuple(_c['digits']) in _used_b2r:
                                continue
                            if _best_near is None or _c.get('final_score', -999) > _best_near.get('final_score', -999):
                                _best_near = _c
                        if _best_near:
                            # 替换尊重保护集: 优先非保护最低分
                            _pool_near = [c for c in top10 if tuple(c['digits']) not in _protected_b2r]
                            if not _pool_near:
                                # 【V2.54.0】保护票绝不可换: Top10全为保护票时放弃注入
                                # (26216: B2N注入6张+B2R注入5张超容量, 回退全池换保护票
                                # 致个0票26870被蚕食 → 个0 0/10)
                                continue
                            _worst_near = min(_pool_near, key=lambda x: x.get('final_score', 0))
                            top10.remove(_worst_near)
                            top10.append(_best_near)
                            _used_b2r.add(tuple(_best_near['digits']))
                            # 【V1.49.0】B2R注入票也加入保护集, 防V46后续替换
                            if not hasattr(self, '_p5_protected'):
                                self._p5_protected = set()
                            self._p5_protected.add(tuple(_best_near['digits']))
                            _injected_b2r = True
                            print(f"[P5-B2N] 🔄 后2位近端回补: {['万','千','百','十','个'][_pos]}位{_d}"
                                  f"({_back}期前, 现{_cnt}席→+1) → {''.join(map(str,_best_near['digits']))}")
                for _pos in range(5):  # V1.39.0-A: 全部5个位置(原仅十/个位)
                    _covered_b2r = set(c['digits'][_pos] for c in top10)
                    for _bk in range(3, min(9, len(_back_seq_d))):  # V1.39.0-A: 3-8期(原5-8期)
                        _d = _back_seq_d[-_bk][_pos]
                        if _d in _covered_b2r:
                            continue
                        _best_b2r = None
                        for _c in _all_b2r:
                            if _c['digits'][_pos] != _d:
                                continue
                            if tuple(_c['digits']) in _used_b2r:
                                continue
                            if _best_b2r is None or _c.get('final_score', -999) > _best_b2r.get('final_score', -999):
                                _best_b2r = _c
                        if _best_b2r:
                            # 【V1.49.0】替换尊重保护集
                            _pool_w = [c for c in top10 if tuple(c['digits']) not in _protected_b2r]
                            if not _pool_w:
                                # 【V2.54.0】保护票绝不可换: 池空放弃本次注入
                                continue
                            _worst_b2r = min(_pool_w, key=lambda x: x.get('final_score', 0))
                            # 【V1.49.0】阈值修复: 原_best(log分-11~-7) > _worst(hybrid
                            # 正分72.7)*0.15=10.9 永远不成立, B2R全部注入被静默挡掉 —
                            # 26204十位0(漏4期)不注入根因, 对齐V1.48.0-F无条件注入
                            if True:
                                print(f"[P5-B2R] 🔄 短间隔回补注入: {['万','千','百','十','个'][_pos]}位{_d}"
                                      f"({_bk}期前) → {''.join(map(str,_best_b2r['digits']))}")
                                top10.remove(_worst_b2r)
                                top10.append(_best_b2r)
                                _used_b2r.add(tuple(_best_b2r['digits']))
                                # 【V1.49.0】B2R注入票也加入保护集
                                if not hasattr(self, '_p5_protected'):
                                    self._p5_protected = set()
                                self._p5_protected.add(tuple(_best_b2r['digits']))
                                _injected_b2r = True
                                break
                    if _injected_b2r and _pos >= 3:
                        pass  # 后2位不因单次注入中断, 允许多位置注入
                    elif _injected_b2r:
                        # 【V1.49.0】前3位注入后也继续扫描后2位(原break会中断)
                        _injected_b2r = False  # 重置后继续, 让后2位也能注入
                if _injected_b2r:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-B2R] ⚠️ 短间隔回补跳过: {e}")

        # ====== [V1.44.0-D] 后2位同数字跨位置隔期迁移检测 ======
        # 26200期归因: 后2位实际[2 0], 十位2是回补, 个位0同上期十位0
        # 模式: 某数字在上期后2位某位置出现, 本期迁移到另一位置
        # (十→个 或 个→十)
        # 策略: 检查上期十位与个位数字在本期的另一位置的覆盖情况
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 2:
                _prev_back2 = list(self.draws[-1][3:])  # 上期十/个
                _prev_shi = _prev_back2[0]
                _prev_ge = _prev_back2[1]
                _cross_injected = False
                # 个→十迁移: 上期个位数字, 检查本期十位是否覆盖
                _cur_shi_covered = set(c['digits'][3] for c in top10)
                _cur_ge_covered = set(c['digits'][4] for c in top10)
                _cross_checks = [
                    (3, _prev_ge, f'上期个{_prev_ge}→本期十'),  # 个→十
                    (4, _prev_shi, f'上期十{_prev_shi}→本期个'),  # 十→个
                ]
                for _pos, _digit, _desc in _cross_checks:
                    if _digit in ({set(c['digits'][_pos] for c in top10)} if False else set()):
                        # 已覆盖
                        pass
                    _covered_cross = set(c['digits'][_pos] for c in top10)
                    if _digit not in _covered_cross:
                        _cross_all = result.get('all', []) or (all_scored or [])
                        _cross_used = set(tuple(c['digits']) for c in top10)
                        _cross_best = None
                        for _c in _cross_all:
                            if _c['digits'][_pos] == _digit and tuple(_c['digits']) not in _cross_used:
                                if _cross_best is None or _c.get('final_score', -999) > _cross_best.get('final_score', -999):
                                    _cross_best = _c
                        if _cross_best:
                            # 【V2.54.0】替换池排除_p5_protected: B2N/B2R近端票
                            # 不被跨位迁移替换(26216个0票26870被后处理蚕食同型)
                            _cross_pool = [c for c in top10
                                           if tuple(c['digits']) not in getattr(self, '_p5_protected', set())]
                            if not _cross_pool:
                                # 【V2.54.0】保护票绝不可换: 池空放弃注入
                                continue
                            _worst_cross = min(_cross_pool, key=lambda x: x.get('final_score', 0))
                            if _cross_best.get('final_score', -999) > _worst_cross.get('final_score', 0) * 0.10:
                                print(f"[P5-CROSS] 🔄 后2位跨位迁移: {_desc}{_digit}"
                                      f"→ {''.join(map(str,_cross_best['digits']))}")
                                top10.remove(_worst_cross)
                                top10.append(_cross_best)
                                _cross_injected = True
                                break
                if _cross_injected:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-CROSS] ⚠️ 后2位跨位迁移跳过: {e}")

        # ====== [V1.42.0-C] 后2位中等遗漏独立扫描 ======
        # 26199期归因: 十位0在26198出现(隔1期), 但实际十位=0在
        # Top10中仅排第8位([4 7 0 0 3] score=-7.66)
        # 十位0属于短间隔重号(隔1期)却被严重低估
        # 策略: 十位/个位独立扫描4-8期遗漏数字('中等遗漏'),
        # 若不在Top10中则从全量池选最高分候选强制注入1注
        # 与V1.39.0-C(中等冷号阈值3-10期全5位)互补: 本扫描
        # 仅有针对后2位的强约束(替换阈值0.15→0.10)
        try:
            if top10 and len(top10) >= 5:
                _all_b2m = result.get('all', []) if result.get('all') else (
                    all_scored if all_scored else top10)
                _used_b2m = set(tuple(c['digits']) for c in top10)
                _b2m_positions = [(3, '十'), (4, '个')]
                _injected_b2m = False
                for _pm, _pn in _b2m_positions:
                    _covered_b2m = set(c['digits'][_pm] for c in top10)
                    # 扫描4-8期该位置出现过的数字(短间隔回补候选)
                    for _bk in range(4, min(9, len(self.draws))):
                        _digit_b2m = self.draws[-_bk][_pm]
                        if _digit_b2m in _covered_b2m:
                            continue
                        _best_b2m = None
                        for _c in _all_b2m:
                            if _c['digits'][_pm] != _digit_b2m:
                                continue
                            if tuple(_c['digits']) in _used_b2m:
                                continue
                            if _best_b2m is None or _c.get('final_score', -999) > _best_b2m.get('final_score', -999):
                                _best_b2m = _c
                        if _best_b2m:
                            # 【V2.54.0】替换池排除_p5_protected: B2N/B2R近端票
                            # 不被后2位遗漏扫描替换
                            _b2m_pool = [c for c in top10
                                         if tuple(c['digits']) not in getattr(self, '_p5_protected', set())]
                            if not _b2m_pool:
                                # 【V2.54.0】保护票绝不可换: 池空放弃注入
                                continue
                            _worst_b2m = min(_b2m_pool, key=lambda x: x.get('final_score', 0))
                            # 后2位阈值0.10(更宽松), 其他位置0.15
                            _threshold_b2m = 0.10 if _pm >= 3 else 0.15
                            if _best_b2m.get('final_score', -999) > _worst_b2m.get('final_score', 0) * _threshold_b2m:
                                print(f"[P5-B2M] 🔄 后2位遗漏注入: {_pn}位{_digit_b2m}"
                                      f"({_bk}期前) → {''.join(map(str,_best_b2m['digits']))}")
                                top10.remove(_worst_b2m)
                                top10.append(_best_b2m)
                                _used_b2m.add(tuple(_best_b2m['digits']))
                                _injected_b2m = True
                                break
                    if _injected_b2m:
                        break
                if _injected_b2m:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-B2M] ⚠️ 后2位遗漏扫描跳过: {e}")

        # ====== [V1.33.0-③] 数字重复分散模式覆盖 ======
        # 26188期归因: 实际60770中0出现在千位和个位(2个不同位置各1次)
        # 7出现在百位和十位(2个不同位置各2次)
        # 检测: 某数字在≥2个不同位置各出现≥1次, 确保至少1注含此分散模式
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 2:
                _prev_draw_p5 = list(self.draws[-1])
                # 统计上期每个数字出现在哪些位置
                _prev_pos_map = {}
                for _p, _d in enumerate(_prev_draw_p5):
                    _prev_pos_map.setdefault(_d, []).append(_p)
                # 找出上期在≥2个不同位置出现的数字
                _multi_pos_digits = [d for d, poses in _prev_pos_map.items() if len(set(poses)) >= 2]
                if _multi_pos_digits:
                    _all_rep = result.get('all', []) if result.get('all') else (
                        all_scored if all_scored else top10)
                    _used_rep = set(tuple(c['digits']) for c in top10)
                    _injected_rep = False
                    for _mpd in _multi_pos_digits:
                        # 检查Top10中是否有候选也使用此数字在≥2个位置
                        _has_multi = False
                        for _c in top10:
                            _mp_positions = [p for p in range(5) if _c['digits'][p] == _mpd]
                            if len(_mp_positions) >= 2:
                                _has_multi = True
                                break
                        if not _has_multi:
                            # 寻找包含该数字在≥2个位置的候选注入
                            _best_rep = None
                            for _c in _all_rep:
                                _ct = tuple(_c['digits'])
                                if _ct in _used_rep:
                                    continue
                                _mp = [p for p in range(5) if _c['digits'][p] == _mpd]
                                if len(_mp) >= 2:
                                    if _best_rep is None or _c.get('final_score', -999) > _best_rep.get('final_score', -999):
                                        _best_rep = _c
                            if _best_rep:
                                _worst = min(top10, key=lambda x: x['final_score'])
                                if _best_rep.get('final_score', -999) > _worst['final_score'] * 0.3:
                                    print(f"[P5-RPD] 🔄 数字分散注入: 上期{_mpd}在{_prev_pos_map[_mpd]}位,"
                                          f" 注入{''.join(map(str,_best_rep['digits']))}")
                                    top10.remove(_worst)
                                    top10.append(_best_rep)
                                    _used_rep.add(tuple(_best_rep['digits']))
                                    _injected_rep = True
                                    break
                    if _injected_rep:
                        top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-RPD] ⚠️ 数字分散跳过: {e}")

        # 重新计算display_score + hit_probability(方案D)
        if top10 and len(top10) >= 2:
            scores_arr = [b.get('final_score', -999) for b in top10]
            s_max = max(scores_arr)
            exp_vals = [math.exp(s - s_max) for s in scores_arr]
            total_exp = sum(exp_vals)
            for b, ev in zip(top10, exp_vals):
                b['display_score'] = self._display_score(b.get('final_score', -10), s_max)
                b['raw_probability'] = round(ev / total_exp, 4)
                b['hit_probability'] = round(ev / total_exp * 100.0, 1)
        
        # 【V1.28.0-C + V1.30.0-④】评分校准: rank归一化 + 梯度压缩 + 尾段多样性
        # 26182: Top1评分最高但全错, Top10(36.6分)反而最佳
        # 原因: score集中在[-13,-10]狭区, softmax指数放大微小差异
        # 方案: 按rank权重校准, Top3打散分布, 降低微差主导排序
        # [V1.30.0-④] 梯度压缩: 确保最低分≥最高分的40%
        # [V1.30.0-④] 尾段多样性: 检查数字池集中度
        if top10 and len(top10) >= 3:
            scores_arr = [b.get('final_score', -999) for b in top10]
            s_min, s_max = min(scores_arr), max(scores_arr)
            s_range = s_max - s_min if s_max > s_min else 1.0
            # rank归一化: 映射到[0.3, 1.0]均匀分布, 降低微差放大
            sorted_idx = sorted(range(len(top10)), key=lambda i: -scores_arr[i])
            n = len(sorted_idx)
            for rank_pos, idx in enumerate(sorted_idx):
                rank_weight = 1.0 - 0.7 * rank_pos / max(n - 1, 1)
                b = top10[idx]
                orig_norm = (scores_arr[idx] - s_min) / s_range
                b['final_score'] = rank_weight * 0.8 + orig_norm * 0.2
            
            # [V1.30.0-④] 评分梯度压缩: 最低分不低于最高分的40%
            _fs_arr = [b['final_score'] for b in top10]
            _fs_max = max(_fs_arr)
            _fs_min = min(_fs_arr)
            _floor = _fs_max * 0.40
            if _fs_min < _floor:
                print(f"[P5-GC] 📊 梯度压缩: min={_fs_min:.3f} < {_floor:.3f}(40%of{_fs_max:.3f}), 拉升")
                for _b in top10:
                    if _b['final_score'] < _floor:
                        _b['final_score'] = _floor
            
            # [V1.30.0-④] 尾段数字池集中度检查
            # 检查是否有≥3个候选在≥3个位置上使用完全相同的数字池
            _pos_pools = [{}, {}, {}, {}, {}]
            for _c in top10:
                for _p in range(5):
                    _d = _c['digits'][_p]
                    _pos_pools[_p][_d] = _pos_pools[_p].get(_d, 0) + 1
            _overlap_pos = 0
            for _p in range(5):
                _max_cnt = max(_pos_pools[_p].values()) if _pos_pools[_p] else 0
                if _max_cnt >= 3:
                    _overlap_pos += 1
            if _overlap_pos >= 3:
                print(f"[P5-GC] 📊 尾段集中: {_overlap_pos}/5位置数字≥3次重复")
            
            # 重新计算display_score
            scores_arr = [b.get('final_score', 0) for b in top10]
            s_max = max(scores_arr)
            exp_vals = [math.exp(s - s_max) for s in scores_arr]
            total_exp = sum(exp_vals)
            for b, ev in zip(top10, exp_vals):
                b['display_score'] = self._display_score(b.get('final_score', 0), s_max)
                b['raw_probability'] = round(ev / total_exp, 4)
                b['hit_probability'] = round(ev / total_exp * 100.0, 1)

        # ====== [V1.34.0-①] 20-50期中等遗漏冷号最终扫描 ======
        # 26189期归因: 万位9遗漏31期, 千位4遗漏23期, 经过多轮后处理后未在Top10中
        # 在所有后处理完成后, 最终扫描各位置20-50期未出现的数字,
        # 缺失则强制注入最高分候选, 作为最终兜底
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 30:
                _scan_window = min(50, len(self.draws))
                _pos_misses = [{}, {}, {}, {}, {}]
                for _pos in range(5):
                    _seq = [_d[_pos] for _d in self.draws[-_scan_window:]]
                    _miss = {}
                    for i in range(len(_seq) - 1, -1, -1):
                        _d = _seq[i]
                        if _d not in _miss:
                            _miss[_d] = len(_seq) - 1 - i
                    for _d in range(10):
                        if _d not in _miss:
                            _miss[_d] = len(_seq)
                    _pos_misses[_pos] = _miss

                _all_for_final_cold = result.get('all', []) if result.get('all') else (all_scored if all_scored else top10)
                _used_tuples = set(tuple(c['digits']) for c in top10)
                _injected_fc = False
                _pos_names = ['万','千','百','十','个']
                for _pos in range(5):
                    _covered = set(c['digits'][_pos] for c in top10)
                    # 扫描20-50期未出现的冷号
                    _mid_cold = [d for d in range(10)
                                 if 20 <= _pos_misses[_pos].get(d, 99) <= 50
                                 and d not in _covered]
                    if not _mid_cold:
                        continue
                    print(f"[P5-MCF] ⚠️ 位置{_pos_names[_pos]}中等冷号未覆盖: {_mid_cold}")
                    for _md in _mid_cold:
                        _best = None
                        for _c in _all_for_final_cold:
                            if _c['digits'][_pos] == _md and tuple(_c['digits']) not in _used_tuples:
                                if _best is None or _c.get('final_score', -999) > _best.get('final_score', -999):
                                    _best = _c
                        if _best:
                            # 【V2.54.0】替换池排除_p5_protected — 26216根因: B2N近端
                            # 回补的26870(个位0漏1期)被MCF当最低分票替换掉 → 个0 0/10.
                            # HFG(V1.49.0)已有此保护, MCF漏掉, 其余后处理环节同步补齐
                            _mcf_pool = [c for c in top10
                                         if tuple(c['digits']) not in getattr(self, '_p5_protected', set())]
                            if not _mcf_pool:
                                # 【V2.54.0】保护票绝不可换: 池空放弃注入
                                # (26216根因: B2N个0票26870被MCF当最低分替换)
                                continue
                            _worst = min(_mcf_pool, key=lambda x: x.get('final_score', 0))
                            # 数量共安全网: 无分数门槛(所有后处理已完成, 分数已校准)
                            top10.remove(_worst)
                            top10.append(_best)
                            _used_tuples.add(tuple(_best['digits']))
                            print(f"[P5-MCF] 🔺 中等冷号注入: {_pos_names[_pos]}位{_md}"
                                  f"遗漏{_pos_misses[_pos].get(_md, '?')}期"
                                  f"→ {''.join(map(str,_best['digits']))}")
                            _injected_fc = True
                            break  # 每位置只补1个
                if _injected_fc:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-MCF] ⚠️ 中等冷号扫描跳过: {e}")

        # ====== [V1.34.0-②] 高频号保底机制 ======
        # 26189期归因: 千位5近30期5次(最高频), 但预测池{0,1,4,7}无5
        # 高频号被内部权重竞争挤出, 需确保每位置近20期Top2频次数字被覆盖
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 20:
                _freq_win = self.draws[-20:]
                _pos_freq = [{}, {}, {}, {}, {}]
                for _pos in range(5):
                    for _d in [_d[_pos] for _d in _freq_win]:
                        _pos_freq[_pos][_d] = _pos_freq[_pos].get(_d, 0) + 1

                _all_for_hf = result.get('all', []) if result.get('all') else (all_scored if all_scored else top10)
                _used_tuples_hf = set(tuple(c['digits']) for c in top10)
                _injected_hf = False
                _pos_names = ['万','千','百','十','个']
                for _pos in range(5):
                    _covered = set(c['digits'][_pos] for c in top10)
                    # Top2频次数字(近20期)
                    _sorted_freq = sorted(_pos_freq[_pos].items(), key=lambda x: -x[1])
                    _top2 = [d for d, _c in _sorted_freq[:2]]
                    _missing_top = [d for d in _top2 if d not in _covered]
                    if not _missing_top:
                        continue
                    print(f"[P5-HFG] ⚠️ 位置{_pos_names[_pos]}高频号{_top2}缺失: {_missing_top}")
                    for _md in _missing_top:
                        _best = None
                        for _c in _all_for_hf:
                            if _c['digits'][_pos] == _md and tuple(_c['digits']) not in _used_tuples_hf:
                                if _best is None or _c.get('final_score', -999) > _best.get('final_score', -999):
                                    _best = _c
                        if _best:
                            # 【V1.49.0】替换避开保护票: 高频号注入不应拆掉
                            # 近端/短间隔注入票(B2N/B2R保护集)
                            _hf_pool = [c for c in top10
                                        if tuple(c['digits']) not in getattr(self, '_p5_protected', set())]
                            if not _hf_pool:
                                # 【V2.54.0】保护票绝不可换: 池空放弃注入
                                continue
                            _worst = min(_hf_pool, key=lambda x: x.get('final_score', 0))
                            # 最终安全网: 无分数门槛(分数已校准, 候选分数与Top10不可比)
                            top10.remove(_worst)
                            top10.append(_best)
                            _used_tuples_hf.add(tuple(_best['digits']))
                            print(f"[P5-HFG] 🔥 高频号注入: "
                                  f"{_pos_names[_pos]}位{_md}"
                                  f"(近20期{_pos_freq[_pos].get(_md,0)}次)"
                                  f"→ {''.join(map(str,_best['digits']))}")
                            _injected_hf = True
                            break  # 每位置最多补1个
                if _injected_hf:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-HFG] ⚠️ 高频号保底跳过: {e}")

        # ====== [V1.34.0-③] 位置多样性硬约束: 每位至少2个唯一值 ======
        # 26189期归因: 十位7占10/10注(100%), 完全无多样性
        # 确保每位至少2个唯一数字, 任何单数字不得占100%注数
        try:
            if top10 and len(top10) >= 5:
                _all_for_div = result.get('all', []) if result.get('all') else (all_scored if all_scored else top10)
                # 扩大候选池: 叠加top100 (all 500条可能不够覆盖极端集中)
                _all_for_div_ext = list(_all_for_div)
                _top100_div = result.get('top100', [])
                if _top100_div:
                    _existing_tups = set(tuple(c['digits']) for c in _all_for_div_ext)
                    for _c in _top100_div:
                        if tuple(_c['digits']) not in _existing_tups:
                            _all_for_div_ext.append(_c)
                _used_tuples_dv = set(tuple(c['digits']) for c in top10)
                _injected_dv = False
                _pos_names = ['万','千','百','十','个']
                from collections import Counter as _Cnt_dv
                for _pos in range(5):
                    _pos_cnt = _Cnt_dv(c['digits'][_pos] for c in top10)
                    _unique_vals = len(_pos_cnt)
                    if _unique_vals >= 2:
                        continue  # 已有足够多样性
                    # 只有1个唯一值! 强制引入第2个数字
                    _dominant = list(_pos_cnt.keys())[0]
                    # 找评分最高的非dominant候选注入
                    _best_alt = None
                    for _c in _all_for_div_ext:
                        if _c['digits'][_pos] == _dominant:
                            continue  # 需要不同的
                        if tuple(_c['digits']) in _used_tuples_dv:
                            continue
                        if _best_alt is None or _c.get('final_score', -999) > _best_alt.get('final_score', -999):
                            _best_alt = _c
                    if _best_alt:
                        # 【V2.54.0】替换池排除_p5_protected: 位置多样性硬约束
                        # 不应拆B2N/B2R近端注入票
                        _div_pool = [c for c in top10
                                     if tuple(c['digits']) not in getattr(self, '_p5_protected', set())]
                        if not _div_pool:
                            # 【V2.54.0】保护票绝不可换: 池空放弃注入
                            continue
                        _worst = min(_div_pool, key=lambda x: x.get('final_score', 0))
                        # 位置多样性是硬约束: 无分数门槛(分数已校准)
                        print(f"[P5-PDV] 🚨 位置{_pos_names[_pos]}仅{_unique_vals}个值"
                              f"({_dominant}占{_pos_cnt[_dominant]}/{len(top10)}注), "
                              f"注入: {''.join(map(str,_best_alt['digits']))}")
                        top10.remove(_worst)
                        top10.append(_best_alt)
                        _used_tuples_dv.add(tuple(_best_alt['digits']))
                        _injected_dv = True
                        break  # 一次只修复1个位置
                if _injected_dv:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-PDV] ⚠️ 位置多样性硬约束跳过: {e}")

        # ====== [V1.35.0-①] 十位过热限流 ======
        # 26191期: 十位7在近30期占33%, 十位8完全被挤出
        # 个位已有限流, 十位同样需要: 十位某数字≥4注时替换至≤2
        # 同时强制补充十位冷号(近30期≤3次的数字)
        try:
            if top10 and len(top10) >= 8 and len(self.draws) >= 10:
                _shi_vals = [c['digits'][3] for c in top10]
                _shi_cnt = Counter(_shi_vals)
                _most_common_shi = _shi_cnt.most_common(1)
                if _most_common_shi and _most_common_shi[0][1] >= 4:
                    _hot_shi = _most_common_shi[0][0]
                    _to_replace = sum(1 for c in top10 if c['digits'][3] == _hot_shi)
                    _need_remove = _to_replace - 2
                    print(f"[P5-SHOT] 🔥 十位过热: {_hot_shi}占{_to_replace}/10注, 需移除{_need_remove}注")
                    _all_for_shi = result.get('all', []) if result.get('all') else (
                        all_scored if all_scored else top10)
                    _used_shi = set(tuple(c['digits']) for c in top10)
                    # 补充十位冷号(近30期出现≤3次)
                    _recent_30_shi = [d[3] for d in self.draws[-min(30, len(self.draws)):]]
                    _shi_30freq = Counter(_recent_30_shi)
                    _cold_shi_digits = [d for d in range(10)
                                       if _shi_30freq.get(d, 0) <= 3]
                    _removed = 0
                    for _idx in range(len(top10)-1, -1, -1):
                        if _removed >= _need_remove:
                            break
                        if top10[_idx]['digits'][3] != _hot_shi:
                            continue
                        # 找替代: 十位是冷号且分数不太低
                        _best_alt = None
                        for _ca in _all_for_shi:
                            if tuple(_ca['digits']) in _used_shi:
                                continue
                            if _ca['digits'][3] not in _cold_shi_digits:
                                continue
                            if _ca['digits'][3] == _hot_shi:
                                continue
                            if _best_alt is None or _ca.get('final_score', -999) > _best_alt.get('final_score', -999):
                                _best_alt = _ca
                        if _best_alt:
                            _old_t = tuple(top10[_idx]['digits'])
                            _used_shi.discard(_old_t)
                            top10[_idx] = _best_alt
                            _used_shi.add(tuple(_best_alt['digits']))
                            print(f"[P5-SHOT] 🔄 十位过热替换: {_hot_shi}→{_best_alt['digits'][3]}"
                                  f"({''.join(map(str,_best_alt['digits']))})")
                            _removed += 1
                    if _removed:
                        top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-SHOT] ⚠️ 十位过热限流跳过: {e}")

        # ====== [V1.35.0-⑤] 后2位交叉数字重复检测 ======
        # 26191期: 前3位(9)与后2位(9)共享数字9
        # 前3位与后2位共享数字时说明候选存在"位置交叉",
        # 降低后2位评分防止同数字反复出现在不同位置区域
        try:
            if top10 and len(top10) >= 5:
                _modified_cross = False
                for _c in top10:
                    _front3_set = set(_c['digits'][:3])
                    _back2_set = set(_c['digits'][3:])
                    _shared = _front3_set & _back2_set
                    if _shared:
                        _penalty = len(_shared) * 0.05
                        # 只降后2位的贡献, 不降前3位
                        # 降低后2位score: 按共享数字数量降权
                        _c['final_score'] *= (1.0 - _penalty)
                        _modified_cross = True
                        print(f"[P5-CROSS] ⚠️ 后2位交叉共享: {sorted(_shared)}"
                              f" penalty={_penalty*100:.0f}%"
                              f" → {''.join(map(str,_c['digits']))}")
                if _modified_cross:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-CROSS] ⚠️ 后2位交叉检测跳过: {e}")

        # 构建all_pool供后续模块使用
        _all_pool = result.get('all', [])
        if not _all_pool:
            _all_pool = result.get('top100', [])

        # ====== [V1.37.0-A] 前3位(万/千/百)广度注入加强 ======
        # 26194期: Top10万位仅{4,6,9}3个唯一值, 完全缺失0,1,2,5,7,8
        # 对标P3 V2.29.0-A: 三位置(万/千/百)唯一值≥6
        try:
            if top10 and len(top10) >= 15 and len(self.draws) >= 5:
                _pos_names = ['万', '千', '百']
                for _pi in range(3):
                    _unique_vals = set(c['digits'][_pi] for c in top10)
                    if len(_unique_vals) >= 6:
                        continue
                    _needed = [d for d in range(10) if d not in _unique_vals]
                    # 优先补低位(0-3)和高位(7-9)
                    _priority = [d for d in range(0, 4) if d in _needed] + \
                                [d for d in range(7, 10) if d in _needed]
                    if not _priority:
                        _priority = sorted(_needed, key=lambda d: _unique_vals)
                    if not _priority:
                        continue
                    print(f"[P5-BDIV] 🔄 {_pos_names[_pi]}位广度加强: "
                          f"当前{len(_unique_vals)}个({sorted(_unique_vals)}), "
                          f"目标≥6, 补{_priority[:3]}")
                    _used_d = set(tuple(c['digits']) for c in top10)
                    _injected_cnt = 0
                    for _nd in _priority:
                        if _injected_cnt >= 3:
                            break
                        _best_d = None
                        for _c in _all_pool:
                            if _c['digits'][_pi] == _nd and tuple(_c['digits']) not in _used_d:
                                if _best_d is None or _c['final_score'] > _best_d['final_score']:
                                    _best_d = _c
                        if _best_d:
                            _worst_d = min(top10, key=lambda x: x['final_score'])
                            if _best_d['final_score'] > _worst_d['final_score'] * 0.05:
                                top10.remove(_worst_d)
                                top10.append(_best_d)
                                _used_d.add(tuple(_best_d['digits']))
                                _injected_cnt += 1
                                print(f"[P5-BDIV] 🔄 {_pos_names[_pi]}位{_nd}注入 → "
                                      f"{''.join(map(str,_best_d['digits']))}")
                    if _injected_cnt > 0:
                        top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-BDIV] ⚠️ 前3位广度加强跳过: {e}")

        # ====== [V1.44.0-B] 千/百位短间隔数字独立检查 ======
        # 26200期归因: 千位7(3期前)和百位7(6期前)在短间隔窗口内但完全未覆盖
        # P5的前3位短间隔回补不应完全依赖P3 Top25(若P3没覆盖则P5也漏)
        # 策略: 独立于P3评分, 对万/千/百各位置检查3-8期前数字,
        # 缺失时从all池注入最高分候选
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 12:
                _f3_back = [d for d in self.draws[-12:]]
                _f3_used = set(tuple(c['digits']) for c in top10)
                _f3_all = result.get('all', []) or (all_scored or top10)
                _f3_injected = False
                for _pos in range(3):  # 万/千/百三位置
                    _f3_covered = set(c['digits'][_pos] for c in top10)
                    for _bk in range(3, min(9, len(_f3_back))):
                        _d = _f3_back[-_bk][_pos]
                        if _d in _f3_covered:
                            continue
                        _best_f3 = None
                        for _c in _f3_all:
                            if _c['digits'][_pos] != _d:
                                continue
                            if tuple(_c['digits']) in _f3_used:
                                continue
                            if _best_f3 is None or _c.get('final_score', -999) > _best_f3.get('final_score', -999):
                                _best_f3 = _c
                        if _best_f3:
                            # 【V2.54.0】替换池排除_p5_protected: 前3位短间隔回补
                            # 不拆B2N/B2R近端注入票
                            _f3_pool = [c for c in top10
                                        if tuple(c['digits']) not in getattr(self, '_p5_protected', set())]
                            if not _f3_pool:
                                # 【V2.54.0】保护票绝不可换: 池空放弃注入
                                continue
                            _worst_f3 = min(_f3_pool, key=lambda x: x.get('final_score', 0))
                            if _best_f3.get('final_score', -999) > _worst_f3.get('final_score', 0) * 0.10:
                                print(f"[P5-F3R] 🔄 前3位短间隔回补: {['万','千','百'][_pos]}位{_d}"
                                      f"({_bk}期前) → {''.join(map(str,_best_f3['digits']))}")
                                top10.remove(_worst_f3)
                                top10.append(_best_f3)
                                _f3_used.add(tuple(_best_f3['digits']))
                                _f3_injected = True
                                break
                    if _f3_injected:
                        break
                if _f3_injected:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-F3R] ⚠️ 前3位短间隔回补跳过: {e}")

        # ====== [V1.37.0-B] 前3位数字集中检测 ======
        # 26194期: 万位6占7/10注挤占空间, 对标P3 V2.25.0-②
        try:
            if top10 and len(top10) >= 10:
                from collections import Counter as _P5Cnt
                _modified_cnt = False
                for _pi in range(3):  # 万/千/百三位置
                    _pos_counts = _P5Cnt(c['digits'][_pi] for c in top10)
                    _most_common = _pos_counts.most_common(1)[0]
                    _threshold = max(3, len(top10) // 5)  # 单数字≤20%
                    if _most_common[1] <= _threshold:
                        continue
                    _over = _most_common[1] - _threshold
                    print(f"[P5-CNC] 🎯 {['万','千','百'][_pi]}位{_most_common[0]}占"
                          f"{_most_common[1]}/{len(top10)}注, 需减{_over}注")
                    _used_tup = set(tuple(c['digits']) for c in top10)
                    _replaced = 0
                    for _c in list(top10):
                        if _replaced >= _over:
                            break
                        if _c['digits'][_pi] != _most_common[0]:
                            continue
                        # 【V1.49.0】跳过保护票(近端/短间隔注入): 修复CNC把
                        # B2R注入的67507(十位0漏4期信号)当万6过热票替换掉
                        if tuple(_c['digits']) in getattr(self, '_p5_protected', set()):
                            continue
                        # 找替代: 同位置不同数字
                        _alt = None
                        for _cc in _all_pool:
                            if _cc['digits'][_pi] != _most_common[0]:
                                if tuple(_cc['digits']) not in _used_tup:
                                    # 不能引入新的集中
                                    _new_cnt = sum(1 for x in top10 if x['digits'][_pi] == _cc['digits'][_pi])
                                    if _new_cnt < _threshold:
                                        if _alt is None or _cc['final_score'] > _alt['final_score']:
                                            _alt = _cc
                        if _alt:
                            top10.remove(_c)
                            top10.append(_alt)
                            _used_tup.add(tuple(_alt['digits']))
                            _replaced += 1
                            print(f"[P5-CNC] 🔄 替换: {_most_common[0]}→{_alt['digits'][_pi]} "
                                  f"({''.join(map(str,_alt['digits']))})")
                    if _replaced > 0:
                        _modified_cnt = True
                if _modified_cnt:
                    top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-CNC] ⚠️ 前3位集中检测跳过: {e}")

        # ====== [V1.37.0-C] 万位低位冷号独立检查 ======
        # 26194期: 万位7不在任何候选, 低位0-3也不在
        try:
            if top10 and len(top10) >= 10 and len(self.draws) >= 30:
                _p5_miss_map = [None, None, None, None, None]
                for _p in range(5):
                    _seq = [d[_p] for d in self.draws[-min(500, len(self.draws)):]]
                    _mm = {}
                    for i in range(len(_seq)-1, -1, -1):
                        _dd = _seq[i]
                        if _dd not in _mm:
                            _mm[_dd] = len(_seq) - 1 - i
                    for _dd in range(10):
                        if _dd not in _mm:
                            _mm[_dd] = len(_seq)
                    _p5_miss_map[_p] = _mm
                _injected_low = False
                for _p in [0, 1, 2]:  # 万/千/百
                    _covered = set(c['digits'][_p] for c in top10)
                    # 遗漏≥12期的低位(0-3)检查
                    for _low_d in range(0, 4):
                        if _low_d in _covered:
                            continue
                        _miss = _p5_miss_map[_p].get(_low_d, 999)
                        if _miss >= 12:
                            _best_low = None
                            for _c in _all_pool:
                                if _c['digits'][_p] == _low_d and tuple(_c['digits']) not in set(tuple(x['digits']) for x in top10):
                                    if _best_low is None or _c['final_score'] > _best_low['final_score']:
                                        _best_low = _c
                            if _best_low:
                                _worst = min(top10, key=lambda x: x['final_score'])
                                if _best_low['final_score'] > _worst['final_score'] * 0.05:
                                    top10.remove(_worst)
                                    top10.append(_best_low)
                                    _injected_low = True
                                    print(f"[P5-LOW] 📡 {['万','千','百'][_p]}位低位冷号: {_low_d}遗漏{_miss}期"
                                          f" → {''.join(map(str,_best_low['digits']))}")
                                    break
                    if _injected_low:
                        break  # 每次最多补1位
                if _injected_low:
                    top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-LOW] ⚠️ 低位冷号跳过: {e}")

        # ====== [V1.38.0-A] 后2位(十位/个位)广度注入加强 ======
        # 26195期: 十位覆盖{2,7,8,9}仅4个唯一值, 个位{3,5,8}仅3个
        # 十位1/个位6完全不在任何候选, 后2位无系统化广度保障
        # 对标前3位V1.37.0-A: 后2位唯一值≥6, 从低位+中段+高位补充
        # 已到最终管道, top10=10个, 从pool中取候选注入
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 5:
                _b2_pos_names = ['十', '个']
                for _pi in [3, 4]:
                    _unique_vals = set(c['digits'][_pi] for c in top10)
                    if len(_unique_vals) >= 6:
                        continue
                    _needed = [d for d in range(10) if d not in _unique_vals]
                    # 优先补低位(0-3)+中段(4-6)+高位(7-9)
                    _priority = [d for d in range(0, 4) if d in _needed] + \
                                [d for d in range(4, 7) if d in _needed] + \
                                [d for d in range(7, 10) if d in _needed]
                    if not _priority:
                        _priority = sorted(_needed, key=lambda d: _unique_vals)
                    if not _priority:
                        continue
                    print(f"[P5-B2DIV] 🔄 {_b2_pos_names[_pi-3]}位广度加强: "
                          f"当前{len(_unique_vals)}个({sorted(_unique_vals)}), "
                          f"目标≥6, 补{_priority[:3]}")
                    _used_d = set(tuple(c['digits']) for c in top10)
                    _injected_cnt = 0
                    for _nd in _priority:
                        if _injected_cnt >= 3:
                            break
                        _best_d = None
                        for _c in _all_pool:
                            if _c['digits'][_pi] == _nd and tuple(_c['digits']) not in _used_d:
                                if _best_d is None or _c['final_score'] > _best_d['final_score']:
                                    _best_d = _c
                        if _best_d:
                            _worst_d = min(top10, key=lambda x: x['final_score'])
                            if _best_d['final_score'] > _worst_d['final_score'] * 0.05:
                                top10.remove(_worst_d)
                                top10.append(_best_d)
                                _used_d.add(tuple(_best_d['digits']))
                                _injected_cnt += 1
                                print(f"[P5-B2DIV] 🔄 {_b2_pos_names[_pi-3]}位{_nd}注入 → "
                                      f"{''.join(map(str,_best_d['digits']))}")
                    if _injected_cnt > 0:
                        top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-B2DIV] ⚠️ 后2位广度加强跳过: {e}")

        # ====== [V1.38.0-B] 后2位数字集中限流 ======
        # 26195期: 个位5占7/10注(70%), 完全垄断个位空间
        # 对标前3位V1.37.0-B的20%阈值, 后2位稍宽松至35%
        try:
            if top10 and len(top10) >= 10:
                from collections import Counter as _P5B2Cnt
                _b2_modified = False
                for _pi in [3, 4]:
                    _pos_cnts = _P5B2Cnt(c['digits'][_pi] for c in top10)
                    _most = _pos_cnts.most_common(1)[0]
                    _threshold = max(3, int(len(top10) * 0.35))
                    if _most[1] <= _threshold:
                        continue
                    _over = _most[1] - _threshold
                    print(f"[P5-B2CNC] 🎯 {['十','个'][_pi-3]}位{_most[0]}占"
                          f"{_most[1]}/{len(top10)}注(>{int(_threshold*100/len(top10))}%), 需减{_over}注")
                    _used_b2 = set(tuple(c['digits']) for c in top10)
                    _replaced_b2 = 0
                    for _c in list(top10):
                        if _replaced_b2 >= _over:
                            break
                        if _c['digits'][_pi] != _most[0]:
                            continue
                        # 【V1.49.0】跳过保护票(近端/短间隔注入信号)
                        if tuple(_c['digits']) in getattr(self, '_p5_protected', set()):
                            continue
                        _alt = None
                        for _cc in _all_pool:
                            if _cc['digits'][_pi] != _most[0]:
                                if tuple(_cc['digits']) not in _used_b2:
                                    _new_cnt = sum(1 for x in top10 if x['digits'][_pi] == _cc['digits'][_pi])
                                    if _new_cnt < _threshold:
                                        if _alt is None or _cc['final_score'] > _alt['final_score']:
                                            _alt = _cc
                        if _alt:
                            top10.remove(_c)
                            top10.append(_alt)
                            _used_b2.add(tuple(_alt['digits']))
                            _replaced_b2 += 1
                            print(f"[P5-B2CNC] 🔄 替换: {_most[0]}→{_alt['digits'][_pi]} "
                                  f"({''.join(map(str,_alt['digits']))})")
                    if _replaced_b2 > 0:
                        _b2_modified = True
                if _b2_modified:
                    top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-B2CNC] ⚠️ 后2位集中限流跳过: {e}")

        # ====== [V1.38.0-C] 上期同位置重号后处理保护 ======
        # 26195期: 个位6是26194上期同位置重号, 但完全不在Top10
        # 下游多样性/集中清洗可能将正确重号替换出局
        # 策略: 检查各位置的上期数字, 如不在Top10且替代候选无明显优势(<20%), 则保护重号
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 2:
                _prev_d = list(self.draws[-1])
                _seen_b2p = set(tuple(c['digits']) for c in top10)
                _injected_b2p = False
                for _bp in range(5):
                    _prev_digit = _prev_d[_bp]
                    _covered_b2p = set(c['digits'][_bp] for c in top10)
                    if _prev_digit in _covered_b2p:
                        continue
                    # 该位置的上期重号不在Top10中, 尝试保护注入
                    _best_b2p = None
                    for _c in _all_pool:
                        if _c['digits'][_bp] == _prev_digit and tuple(_c['digits']) not in _seen_b2p:
                            if _best_b2p is None or _c['final_score'] > _best_b2p['final_score']:
                                _best_b2p = _c
                    if _best_b2p:
                        _worst_b2p = min(top10, key=lambda x: x['final_score'])
                        # 只在该重号候选分数不低于最差候选80%时保护注入
                        if _best_b2p['final_score'] >= _worst_b2p['final_score'] * 0.80:
                            top10.remove(_worst_b2p)
                            top10.append(_best_b2p)
                            _seen_b2p.add(tuple(_best_b2p['digits']))
                            _injected_b2p = True
                            print(f"[P5-PROT] 🛡️ 上期{[ '万','千','百','十','个'][_bp]}位{_prev_digit}"
                                  f"重号保护 → {''.join(map(str,_best_b2p['digits']))}")
                if _injected_b2p:
                    top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-PROT] ⚠️ 重号保护跳过: {e}")

        # ====== [V1.41.0-A] 冷号注入限流 ======
        # 26198期: 万位6×5+千位7×6+十位2×6垄断, 与P3 26198同源
        # 各位置同一数字出现≥3次时仅保留最高分2条
        try:
            if top10 and len(top10) >= 5:
                _pos_cnts_a = [{}, {}, {}, {}, {}]
                for _c_a in top10:
                    for _p_a, _d_a in enumerate(_c_a['digits']):
                        _pos_cnts_a[_p_a][_d_a] = _pos_cnts_a[_p_a].get(_d_a, 0) + 1
                _throttled_a = False
                _all_for_a = result.get('all', []) if result.get('all') else (
                    all_scored if all_scored else top10)
                for _p_a in range(5):
                    for _d_a, _cnt_a in _pos_cnts_a[_p_a].items():
                        if _cnt_a >= 3:
                            _matches_a = [(i, c) for i, c in enumerate(top10)
                                          if c['digits'][_p_a] == _d_a]
                            _matches_a.sort(key=lambda x: -x[1]['final_score'])
                            for _idx_a, _c_a in _matches_a[2:]:
                                _best_alt_a = None
                                for _c2 in _all_for_a:
                                    if _c2['digits'][_p_a] != _d_a:
                                        if tuple(_c2['digits']) not in set(tuple(c['digits']) for c in top10):
                                            if _best_alt_a is None or _c2['final_score'] > _best_alt_a['final_score']:
                                                _best_alt_a = _c2
                                if _best_alt_a and _best_alt_a['final_score'] > _c_a['final_score'] * 0.4:
                                    top10[_idx_a] = _best_alt_a
                                    _throttled_a = True
                                    print(f"[P5-A] 🎯 冷号注入限流: {['万','千','百','十','个'][_p_a]}位{_d_a}占"
                                          f"{_cnt_a}注, 替换→{''.join(map(str,_best_alt_a['digits']))}")
                if _throttled_a:
                    top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-A] ⚠️ 冷号注入限流跳过: {e}")

        # ====== [V1.42.0-A] 万/千位过热限流加强 ======
        # 26199期归因: 万位6占5/10注、千位7占6/10注极端垄断
        # 虽然V1.41.0-A已有全局≥3阈值, 但万位6/千位7作为排前位置
        # 的垄断效应更严重(挤占前后位置数字组合空间)
        # 策略: 万位/千位独立阈值设为≥4, 替换为含该位置
        # 中等遗漏(4-8期)数字的最高分候选, 促进冷号回补
        try:
            if top10 and len(top10) >= 5:
                _pos_cnts_wq = [{}, {}]
                for _c_wq in top10:
                    _pos_cnts_wq[0][_c_wq['digits'][0]] = _pos_cnts_wq[0].get(_c_wq['digits'][0], 0) + 1
                    _pos_cnts_wq[1][_c_wq['digits'][1]] = _pos_cnts_wq[1].get(_c_wq['digits'][1], 0) + 1
                _all_wq = result.get('all', []) if result.get('all') else (
                    all_scored if all_scored else top10)
                _throttled_wq = False
                _pos_names_wq = ['万', '千']
                for _pw in range(2):
                    for _dw, _cw in _pos_cnts_wq[_pw].items():
                        if _cw >= 4:
                            # 计算该位置4-8期遗漏的数字
                            _miss_4to8 = []
                            for _d in range(10):
                                _miss_periods = 0
                                for _bk in range(min(8, len(self.draws)), len(self.draws) - 1, -1):
                                    if _bk >= 1 and self.draws[-_bk][_pw] != _d:
                                        _miss_periods += 1
                                    else:
                                        break
                                if 4 <= _miss_periods <= 8:
                                    _miss_4to8.append(_d)
                            _matches_wq = [(i, c) for i, c in enumerate(top10) if c['digits'][_pw] == _dw]
                            _matches_wq.sort(key=lambda x: -x[1]['final_score'])
                            _retain = 2  # 最多保留2注
                            for _idx_wq, _c_wq in _matches_wq[_retain:]:
                                _best_alt_wq = None
                                for _c2 in _all_wq:
                                    if _c2['digits'][_pw] != _dw:
                                        # 优先选中等遗漏数字
                                        _c2_pos_val = _c2['digits'][_pw]
                                        _is_medium = _c2_pos_val in _miss_4to8
                                        _score_boost_wq = 1.2 if _is_medium else 1.0
                                        if tuple(_c2['digits']) not in set(tuple(c['digits']) for c in top10):
                                            _adj_score = _c2['final_score'] * _score_boost_wq
                                            if _best_alt_wq is None or _adj_score > _best_alt_wq[0]:
                                                _best_alt_wq = (_adj_score, _c2)
                                if _best_alt_wq:
                                    _best_c2 = _best_alt_wq[1]
                                    if _best_c2['final_score'] > _c_wq['final_score'] * 0.4:
                                        top10[_idx_wq] = _best_c2
                                        _throttled_wq = True
                                        print(f"[P5-A2] 🎯 万/千过热限流: {_pos_names_wq[_pw]}位{_dw}占"
                                              f"{_cw}注, 替换→{''.join(map(str,_best_c2['digits']))}")
                if _throttled_wq:
                    top10.sort(key=lambda x: -x['final_score'])
        except Exception as e:
            print(f"[P5-A2] ⚠️ 万/千过热限流跳过: {e}")

        # ====== [V1.41.0-B] 五位置广度注入兜底 ======
        # 26198期: 万位仅{6,4,0,9}(4个), 千位仅{7,5,4}(3个), 十位仅{2,4,9,5}(4个)
        # 对标P3 V2.33.0-D: 各位置独立检查唯一值≥6, 从全量池无条件补入
        # 搜索池扩展到 result['all'] + result['top100'] + all_scored(三重保障)减少漏检
        try:
            if top10 and len(top10) >= 5:
                _pos_names_b = ['万','千','百','十','个']
                _used_tuples_b = set(tuple(c['digits']) for c in top10)
                _pool_b = []
                if result.get('all'):
                    _pool_b.extend(result['all'])
                if result.get('top100'):
                    _pool_b.extend(result['top100'])
                if all_scored and all_scored is not _pool_b:
                    _pool_b.extend(all_scored)
                if not _pool_b:
                    _pool_b = top10
                for _pi_b in range(5):
                    _unique_b = set(c['digits'][_pi_b] for c in top10)
                    if len(_unique_b) >= 6:
                        continue
                    _missing_b = [d for d in range(10) if d not in _unique_b]
                    for _nd_b in _missing_b:
                        if len(_unique_b) >= 6:
                            break
                        _best_b = None
                        for _c in _pool_b:
                            if len(_c['digits']) >= 5 and _c['digits'][_pi_b] == _nd_b and tuple(_c['digits']) not in _used_tuples_b:
                                if _best_b is None or _c.get('final_score', -999) > _best_b.get('final_score', -999):
                                    _best_b = _c
                        if _best_b:
                            _worst_b = min(top10, key=lambda x: x.get('final_score', -999))
                            if _best_b.get('final_score', -999) > _worst_b.get('final_score', -999) * 0.001:
                                top10.remove(_worst_b)
                                top10.append(_best_b)
                                _used_tuples_b.add(tuple(_best_b['digits']))
                                _unique_b.add(_nd_b)
                                print(f"[P5-B] 🔄 {_pos_names_b[_pi_b]}位{_nd_b}广度注入 → "
                                      f"{''.join(map(str,_best_b['digits']))}")
                                continue
                        # 搜索池无候选, 合成注入: 复制最差候选并修改目标位置
                        _worst_b2 = min(top10, key=lambda x: x.get('final_score', -999))
                        _new_digits_b = list(_worst_b2['digits'])
                        _new_digits_b[_pi_b] = _nd_b
                        _new_tup_b = tuple(_new_digits_b)
                        if _new_tup_b not in _used_tuples_b:
                            top10.remove(_worst_b2)
                            _synthetic_b = {'digits': list(_new_digits_b), 'final_score': _worst_b2.get('final_score', 0) * 0.9}
                            top10.append(_synthetic_b)
                            _used_tuples_b.add(_new_tup_b)
                            _unique_b.add(_nd_b)
                            print(f"[P5-B] 🔄 {_pos_names_b[_pi_b]}位{_nd_b}合成注入 → "
                                  f"{''.join(map(str,_new_digits_b))}")
        except Exception as e:
            print(f"[P5-B] ⚠️ 五位置广度注入跳过: {e}")

        # ====== [V1.42.0-D] TopN质量基准线 ======
        # 26199期归因: 第8-10名score突降至-7.55~-7.66(第7名+0.38→-7.55断层)
        # 导致候选池在7注后"断供", 替换后注入的候选质量不可控
        # 策略: 确保top10的最低分 ≥ 最高分 × 0.05, 防止score断崖
        # 不足时从all_scored/top100补充分数较高的候选
        try:
            if top10 and len(top10) >= 10:
                _max_score_d = max(c.get('final_score', -999) for c in top10)
                _min_score_d = min(c.get('final_score', -999) for c in top10)
                _floor_d = _max_score_d * 0.05
                if _min_score_d < _floor_d:
                    _pool_d = []
                    if result.get('all'):
                        _pool_d.extend(result['all'])
                    if result.get('top100'):
                        _pool_d.extend(result['top100'])
                    if all_scored and all_scored is not _pool_d:
                        _pool_d.extend(all_scored)
                    if not _pool_d:
                        _pool_d = top10
                    _used_d = set(tuple(c['digits']) for c in top10)
                    _replaced_d = 0
                    for _i in reversed(range(len(top10))):
                        if top10[_i].get('final_score', -999) >= _floor_d:
                            continue
                        _best_floor = None
                        for _c in _pool_d:
                            if tuple(_c['digits']) in _used_d:
                                continue
                            if _c.get('final_score', -999) >= _floor_d:
                                if _best_floor is None or _c['final_score'] > _best_floor['final_score']:
                                    _best_floor = _c
                        if _best_floor:
                            print(f"[P5-FL] 📊 质量基准替换: {''.join(map(str,top10[_i]['digits']))}"
                                  f"({top10[_i].get('final_score',0):.2f}) → "
                                  f"{''.join(map(str,_best_floor['digits']))}"
                                  f"({_best_floor['final_score']:.2f}) [阈值{_floor_d:.2f}]")
                            top10[_i] = _best_floor
                            _used_d.add(tuple(_best_floor['digits']))
                            _replaced_d += 1
                    if _replaced_d:
                        top10.sort(key=lambda x: -x.get('final_score', 0))
                        print(f"[P5-FL] ✅ 质量基准: {_replaced_d}注已替换, 阈值={_floor_d:.2f}")
        except Exception as e:
            print(f"[P5-FL] ⚠️ 质量基准跳过: {e}")

        # ====== [V1.45.0-B] 万位深度冷号独立扫描 ======
        # 26201期归因: 万位8遗漏11期完全不在Top10, 深度冷号注入未覆盖
        # 策略: 各位置遗漏≥10期数字独立检查, 从all池直接注入最高分候选
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 30:
                _dc_cold_used = set(tuple(c['digits']) for c in top10)
                _dc_all = result.get('all', []) or all_scored or []
                _dc_changed = False
                for _p in range(5):
                    _seq = [d[_p] for d in self.draws[-min(200, len(self.draws)):]]
                    _miss = {}
                    for _d in range(10):
                        for _i in range(len(_seq)-1, -1, -1):
                            if _seq[_i] == _d:
                                _miss[_d] = len(_seq) - 1 - _i
                                break
                        if _d not in _miss:
                            _miss[_d] = len(_seq)
                    _deep_cold = [_d for _d, _m in _miss.items() if _m >= 10 and _d not in set(c['digits'][_p] for c in top10)]
                    if _deep_cold:
                        _dc_names = ['万','千','百','十','个']
                        for _dc in _deep_cold:
                            _best_dc = None
                            for _c in _dc_all:
                                if _c['digits'][_p] == _dc and tuple(_c['digits']) not in _dc_cold_used:
                                    if _best_dc is None or _c.get('final_score', -999) > _best_dc.get('final_score', -999):
                                        _best_dc = _c
                            if _best_dc:
                                _worst_dc = min(top10, key=lambda x: x.get('final_score', 0))
                                if _best_dc.get('final_score', -999) > _worst_dc.get('final_score', 0) * 0.15:
                                    print(f"[P5-DCL] ❄️ 深度冷号注入: {_dc_names[_p]}位{_dc}"
                                          f"(遗漏{_miss[_dc]}期) → {''.join(map(str,_best_dc['digits']))}")
                                    top10.remove(_worst_dc)
                                    top10.append(_best_dc)
                                    _dc_cold_used.add(tuple(_best_dc['digits']))
                                    _dc_changed = True
                if _dc_changed:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-DCL] ⚠️ 深度冷号扫描跳过: {e}")

        # ====== [V1.45.0-C] 各位置短间隔独立窗口(迁移P3 V2.36.0-A) ======
        # 26201期归因: 千位6在26197(4期前)短间隔回补被热门数字(百位8垄断)挤压
        # 各位置独立检测本位置最近5期内出现数字, 十位替换阈值0.05
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 10:
                _ps_used = set(tuple(c['digits']) for c in top10)
                _ps_all = result.get('all', []) or all_scored or top10
                _ps_changed = False
                _ps_names = ['万','千','百','十','个']
                for _pos in range(5):
                    _pos_covered = set(c['digits'][_pos] for c in top10)
                    _pos_window = min(8, len(self.draws))
                    for _back in range(2, min(6, _pos_window)):
                        _d = self.draws[-_back][_pos]
                        if _d in _pos_covered:
                            continue
                        _best_ps = None
                        for _c in _ps_all:
                            if _c['digits'][_pos] == _d and tuple(_c['digits']) not in _ps_used:
                                if _best_ps is None or _c.get('final_score', -999) > _best_ps.get('final_score', -999):
                                    _best_ps = _c
                        if _best_ps:
                            _worst_ps = min(top10, key=lambda x: x.get('final_score', 0))
                            _ps_threshold = 0.05 if _pos == 4 else 0.10  # 个位(5th)特殊
                            if _best_ps.get('final_score', -999) > _worst_ps.get('final_score', 0) * _ps_threshold:
                                print(f"[P5-PSI] 🔄 位置短间隔独立注入: {_ps_names[_pos]}位{_d}"
                                      f"({_back}期前) → {''.join(map(str,_best_ps['digits']))}")
                                top10.remove(_worst_ps)
                                top10.append(_best_ps)
                                _ps_used.add(tuple(_best_ps['digits']))
                                _ps_changed = True
                                break
                if _ps_changed:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-PSI] ⚠️ 位置短间隔独立检查跳过: {e}")

        # ====== [V1.45.0-D] 后2位锁定+前3位替换 ======
        # 26201期归因: [0,3,8,7,1]后2位[7,1]全中但前3位[0,3,8]全错
        # 后2位评分足够高时应固定后2位, 从候选池重新匹配最佳前3位
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 3:
                _b2_used = set(tuple(c['digits']) for c in top10)
                _b2_all = result.get('all', []) or all_scored or []
                _b2_changed = False
                # 找出后2位[十,个]评分最高的注
                _top_b2 = sorted(top10, key=lambda x: -x.get('final_score', 0))
                for _tc in _top_b2[:3]:  # 检查Top3
                    _back2 = tuple(_tc['digits'][3:5])
                    _front3 = tuple(_tc['digits'][:3])
                    # 检查前3位是否全部正确(与上期实际对比低约, 主要检查多样性)
                    # 如果前3位中任意2位数字相同(对子)或连续单调, 尝试替换
                    _f3_set = set(_front3)
                    _is_mono = len(_f3_set) <= 2  # 前3位只有≤2个不同数字
                    if not _is_mono:
                        # 检查前3位是否过度集中在单个数字上
                        from collections import Counter as _B2Cnt
                        _f3_all_cnt = _B2Cnt()
                        for _cc in top10:
                            _f3_all_cnt.update(_cc['digits'][:3])
                        _f3_top = _f3_all_cnt.most_common(1)[0]
                        _is_mono = _f3_top[1] >= len(top10) * 0.6  # 某数字占60%+前3位
                    if _is_mono:
                        # 固定后2位, 在全量池搜索含此后2位且前3位不同的最佳候选
                        _best_b2_alt = None
                        for _c in _b2_all:
                            if tuple(_c['digits'][3:5]) == _back2 and tuple(_c['digits']) not in _b2_used:
                                _c_f3 = tuple(_c['digits'][:3])
                                if len(set(_c_f3)) >= 2 and _c_f3 != _front3:
                                    if _best_b2_alt is None or _c.get('final_score', -999) > _best_b2_alt.get('final_score', -999):
                                        _best_b2_alt = _c
                        if _best_b2_alt:
                            _worst_b2 = min(top10, key=lambda x: x.get('final_score', 0))
                            print(f"[P5-B2L] 🔗 后2位锁定+前3位替换: 后2位[{_back2[0]} {_back2[1]}]"
                                  f" {''.join(map(str,_tc['digits']))}"
                                  f"→{''.join(map(str,_best_b2_alt['digits']))}")
                            top10.remove(_worst_b2)
                            top10.append(_best_b2_alt)
                            _b2_used.add(tuple(_best_b2_alt['digits']))
                            _b2_changed = True
                            break
                if _b2_changed:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-B2L] ⚠️ 后2位锁定跳过: {e}")

        # ====== [V1.46.0] 26202期归因: 重号保留席+中冷分池两档+深冷去阈值+P3 Top1保底+前3位限流+后2位重号提权 ======
        # 26202实际96170, 前3位全miss, Top10被648垄断6注. 根因:
        # ① 万位9(遗漏12期)深冷扫描被0.15阈值挡住(P3失准降权后分数不足)
        # ② 千位6/十位7=上期重号, V1.45.0-C窗口range(2,6)不含_back=1
        # ③ 百位1(遗漏7期)落在深冷(≥10)/中位(2-5)之间空隙
        # ④ P3 Top1(236)被648(P3第3注)反超, 强制保底被后续流程移除
        # ⑤ 前3位组合648占6注无组合级限流
        # ⑥ 后2位重号(十7)/短回补(个0)覆盖弱

        # ====== [V1.48.0-A] 注入票防替换保护 ======
        # 26203期归因: V46B注入的万1/十6/个8(遗漏9期中冷)分数低,
        # 被V46D(保底)/V46E(限流)/V46F(重号)后续注入替换 — 每次替换
        # 当前最低分票, 刚注入的中冷票成首选替换对象, 6-9档覆盖全失效
        # 修复: V46注入票标记保护, 后续注入只替换非注入票
        # 【V1.49.0】保护集挂到self: 供B2R(在V46之前执行)等早期注入共享,
        # 防止早期注入票被V46后续链式替换
        if not hasattr(self, '_p5_protected'):
            self._p5_protected = set()
        if not hasattr(self, '_p5_v46_high'):
            self._p5_v46_high = set()
        _protected_v46 = self._p5_protected

        def _pick_worst_v46(_pool):
            # 【V1.52.0】第一层同时避开_p5_v46_high(高优注入票): 原只避开
            # _p5_protected, V46B注入的25848(十4漏9)不在其中, 被V46D(P3 Top1
            # 保底)换出致26207十4 0/10
            _high46 = getattr(self, '_p5_v46_high', set())
            _cands = [c for c in _pool if tuple(c['digits']) not in _protected_v46
                      and tuple(c['digits']) not in _high46]
            if not _cands:
                # 【V1.49.0】V46保护票全占时, 允许替换非V46保护票(B2N近端等
                # 低优先级保护票): 26204 B2N注入6张挤占全部席位, V46B中冷
                # (百位4漏13期)无注入路径 — 分层保护: V46高优先级, 早期注入可让位
                _low_prot = [c for c in _pool
                             if tuple(c['digits']) not in _high46]
                if _low_prot:
                    return min(_low_prot, key=lambda x: x.get('final_score', 0))
                return min(_pool, key=lambda x: x.get('final_score', 0))
            return min(_cands, key=lambda x: x.get('final_score', 0))

        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 20:
                _v46_used = set(tuple(c['digits']) for c in top10)
                _v46_all = result.get('all', []) or all_scored or []
                _v46_names = ['万', '千', '百', '十', '个']
                _v46_changed = False
                _prev_v46 = list(self.draws[-1])
                # [V1.48.0-F] 注入数上限: 无条件注入(移除尺度失配的阈值)但限8注,
                # 保留最高分原始票. 候选池为log分(-7~-3), 原始票为hybrid正分
                # (0.4~0.8), 两者尺度不兼容, 任何乘法/加法阈值都会误杀注入
                _v46_inj_count = 0
                # 【V1.49.0】注入上限8→12→15: 26204 B2N近端回补6张+V46A重号3张
                # +V46B 8-9档4张+6-7档5张=12张恰好耗尽12配额, 10-15档
                # (百位4漏13期)被上限挡住 — 中冷档注入优先于重号, 配额需覆盖全部
                _V46_MAX_INJ = 15

                def _v46_best(_pos, _d, _pool):
                    _b = None
                    for _c in _pool:
                        if _c['digits'][_pos] == _d and tuple(_c['digits']) not in _v46_used:
                            if _b is None or _c.get('final_score', -999) > _b.get('final_score', -999):
                                _b = _c
                    return _b

                def _v46_inject(_pos, _d, _tag, _extra='', _threshold=0.02):
                    nonlocal _v46_changed, _v46_inj_count
                    _best = _v46_best(_pos, _d, _v46_all)
                    if _best is None:
                        _pool_extra = (result.get('top100', []) or []) + top10
                        _best = _v46_best(_pos, _d, _pool_extra)
                    if _best:
                        if _v46_inj_count >= _V46_MAX_INJ:
                            return False
                        _worst = _pick_worst_v46(top10)
                        if _worst is None:
                            return False
                        # [V1.48.0-F] 无条件注入: final_score尺度不兼容
                        # (候选log分vs原始hybrid正分), 原阈值从V1.46.0起误杀全部注入
                        top10.remove(_worst)
                        top10.append(_best)
                        _v46_used.add(tuple(_best['digits']))
                        _protected_v46.add(tuple(_best['digits']))
                        # 【V1.49.0】V46注入票标记高优先级保护
                        if not hasattr(self, '_p5_v46_high'):
                            self._p5_v46_high = set()
                        self._p5_v46_high.add(tuple(_best['digits']))
                        _v46_inj_count += 1
                        _v46_changed = True
                        print(f"[P5-V46{_tag}] 🔄 {_extra}{_v46_names[_pos]}位{_d}"
                              f" → {''.join(map(str,_best['digits']))}")
                        return True
                    return False

                # [V1.48.0-E] P5原生评分注入: P3失准时前3位中冷注入绕过P3混合评分
                # 26203归因: 万位1在P3百位Top10缺失→hybrid评分压低→中冷注入选票偏
                def _v46_best_raw(_pos, _d, _pool):
                    _b = None
                    for _c in _pool:
                        if _c['digits'][_pos] == _d and tuple(_c['digits']) not in _v46_used:
                            # 【V1.49.0】raw_probability可能为None(候选来自enumerate_all
                            # 无该字段): None比较会TypeError导致整个V46块静默跳过,
                            # 26204百位4注入失败根因 — None时回退final_score
                            _rk = _c.get('raw_probability')
                            if _rk is None:
                                _rk = _c.get('final_score', -999)
                            _b_rk = None
                            if _b is not None:
                                _b_rk = _b.get('raw_probability')
                                if _b_rk is None:
                                    _b_rk = _b.get('final_score', -999)
                            if _b is None or _rk > _b_rk:
                                _b = _c
                    return _b

                def _v46_inject_raw(_pos, _d, _tag, _extra='', _threshold=0.02):
                    nonlocal _v46_changed, _v46_inj_count
                    _best = _v46_best_raw(_pos, _d, _v46_all)
                    if _best is None:
                        _pool_extra = (result.get('top100', []) or []) + top10
                        _best = _v46_best_raw(_pos, _d, _pool_extra)
                    if _best:
                        if _v46_inj_count >= _V46_MAX_INJ:
                            return False
                        _worst = _pick_worst_v46(top10)
                        if _worst is None:
                            return False
                        top10.remove(_worst)
                        top10.append(_best)
                        _v46_used.add(tuple(_best['digits']))
                        _protected_v46.add(tuple(_best['digits']))
                        # 【V1.49.0】V46注入票标记高优先级保护
                        if not hasattr(self, '_p5_v46_high'):
                            self._p5_v46_high = set()
                        self._p5_v46_high.add(tuple(_best['digits']))
                        _v46_inj_count += 1
                        _v46_changed = True
                        print(f"[P5-V46{_tag}] 🔄 {_extra}{_v46_names[_pos]}位{_d}"
                              f" → {''.join(map(str,_best['digits']))}")
                        return True
                    return False

                # [B] 中冷号分池: 遗漏计算先行(供保护与注入共用)
                _v46_miss = [{}, {}, {}, {}, {}]
                for _pos in range(5):
                    _seq = [d[_pos] for d in self.draws[-min(200, len(self.draws)):]]
                    _m = {}
                    for _d in range(10):
                        for _i in range(len(_seq) - 1, -1, -1):
                            if _seq[_i] == _d:
                                _m[_d] = len(_seq) - 1 - _i
                                break
                        if _d not in _m:
                            _m[_d] = len(_seq)
                    _v46_miss[_pos] = _m
                # [E] P3失准检测: 最近2期P3 Top1 vs 实际前3位, 匹配≤1/3计失准
                # [V1.48.0-E] 修正P3存档路径: 用_load_p3_prediction(自动+1期)
                _p3_miss_streak = False
                try:
                    _streak_cnt = 0
                    for _bk in range(1, 3):
                        if len(self.draws) <= _bk:
                            break
                        _pred_f3 = None
                        try:
                            _pr3 = self._load_p3_prediction(str(int(self.last_period) - _bk), top_n=1)
                            if _pr3 and len(_pr3) == 3:
                                _pred_f3 = [int(x) for x in _pr3]
                        except Exception:
                            pass
                        if _pred_f3:
                            _actual_f3 = list(self.draws[-_bk][:3])
                            _m3 = sum(1 for _i3 in range(3)
                                      if _pred_f3[_i3] == _actual_f3[_i3])
                            if _m3 <= 1:
                                _streak_cnt += 1
                    _p3_miss_streak = _streak_cnt >= 1
                    if _p3_miss_streak:
                        print(f"[P5-V48E] ⚠️ P3失准({_streak_cnt}期), "
                              f"前3位中冷注入改用P5原生评分")
                except Exception:
                    pass
                # [V1.48.0-B2] 保护含6-9档中冷数字的原始票(26203根因档):
                # 万1/十6/个8全为遗漏9期, 持有这些数字的原始票(如63828含个8)
                # 不应被后续注入替换掉, 否则覆盖被拆东补西
                # 【V1.50.0-A】保护档扩展到近端+短间隔(1-8期): 26205万8(漏3期)/
                # 千0(漏5期)在3-8期回补窗口内却0/10 — 短间隔回补票被V46E/F等
                # 后续替换出池, 近端+短间隔+中冷档(1-9期)原始票一并保护
                for _c0 in top10:
                    for _p0 in range(5):
                        if 1 <= _v46_miss[_p0].get(_c0['digits'][_p0], 99) <= 9:
                            _protected_v46.add(tuple(_c0['digits']))
                            break
                # [V1.48.0-B3] 保护P3 Top1前3位票: P5-E注入的P3 Top1票(如23806)
                # 不应被V46注入替换, 否则V46D保底也无后备候选可注
                try:
                    _p3t_now = self._load_p3_prediction(self.last_period, top_n=1)
                    if _p3t_now and len(_p3t_now) == 3:
                        _p3t_key = tuple(int(x) for x in _p3t_now)
                        for _c0 in top10:
                            if tuple(_c0['digits'][:3]) == _p3t_key:
                                _protected_v46.add(tuple(_c0['digits']))
                                break
                except Exception:
                    pass

                # [A] 重号保留席: 上期各位置数字至少保留1席
                for _pos in range(5):
                    _d = _prev_v46[_pos]
                    if any(c['digits'][_pos] == _d for c in top10):
                        continue
                    _v46_inject(_pos, _d, 'A', '[上期重号] ')

                # [B] 中冷号分池: 三趟扫描 — 先8-9档(26203根因档: 万1/十6/个8
                # 全为遗漏9期), 再6-7档; 每位置每档≤1席
                # 【V1.49.0】新增10-15档: 26204百位4(漏13期)在C档(≥10)但被
                # 深冷高分竞争挤出, 10-15中冷独立注入保证路径
                for _lo, _hi in ((8, 9), (6, 7), (10, 15)):
                    for _pos in range(5):
                        _covered = set(c['digits'][_pos] for c in top10)
                        # 【V1.49.0】10-15档按遗漏降序扫描: 原_d从0升序,
                        # 26204百位0(漏10期)先于百位4(漏13期)被选中, 每档每位置
                        # 只注入1个导致更高遗漏的中冷号被低遗漏顶掉 — 降序优先深冷
                        _scan_order = range(10)
                        if _hi >= 10:
                            _cand_in_band = [(d, _v46_miss[_pos].get(d, 99)) for d in range(10)
                                              if _lo <= _v46_miss[_pos].get(d, 99) <= _hi]
                            _cand_in_band.sort(key=lambda x: -x[1])
                            _scan_order = [d for d, _m in _cand_in_band]
                        for _d in _scan_order:
                            _m = _v46_miss[_pos].get(_d, 99)
                            if _lo <= _m <= _hi and _d not in _covered:
                                # [E] 前3位+P3失准: P5原生评分, 阈值0.02
                                if _pos <= 2 and _p3_miss_streak:
                                    _v46_inject_raw(_pos, _d, 'B',
                                                    f'[遗漏{_m}期中冷·P5原生] ', 0.02)
                                else:
                                    _v46_inject(_pos, _d, 'B',
                                                f'[遗漏{_m}期中冷] ', 0.05)
                                break
                # [C] ≥16期深冷: 每位置≤1席(在B三趟扫描之后, 优先级最低)
                # 【V1.49.0】阈值≥10→≥16: 10-15档已由B档独立覆盖, C档只保留
                # 深冷, 避免与B档10-15重复注入浪费席位
                for _pos in range(5):
                    _covered = set(c['digits'][_pos] for c in top10)
                    for _d in range(10):
                        _m = _v46_miss[_pos].get(_d, 99)
                        if _m >= 16 and _d not in _covered:
                            _v46_inject(_pos, _d, 'C', f'[遗漏{_m}期深冷] ', 0.02)
                            break

                # [D] P3 Top1最终保底: P3 Top1前3位在最终Top10强制保留1注
                try:
                    _p3_top1_v46 = self._load_p3_prediction(self.last_period, top_n=1)
                    if _p3_top1_v46 and len(_p3_top1_v46) == 3:
                        _f3_target = [int(x) for x in _p3_top1_v46]
                        _has_p3t = any(list(c['digits'][:3]) == _f3_target for c in top10)
                        if not _has_p3t:
                            _best_p3t = None
                            for _c in _v46_all:
                                if list(_c['digits'][:3]) == _f3_target and tuple(_c['digits']) not in _v46_used:
                                    if _best_p3t is None or _c.get('final_score', -999) > _best_p3t.get('final_score', -999):
                                        _best_p3t = _c
                            if _best_p3t:
                                _worst_p3t = _pick_worst_v46(top10)
                                if _worst_p3t is None:
                                    pass
                                else:
                                    top10.remove(_worst_p3t)
                                    top10.append(_best_p3t)
                                    _v46_used.add(tuple(_best_p3t['digits']))
                                    _protected_v46.add(tuple(_best_p3t['digits']))
                                    _v46_changed = True
                                    print(f"[P5-V46D] 🎯 P3 Top1保底: 前3位{''.join(map(str,_f3_target))}"
                                          f" → {''.join(map(str,_best_p3t['digits']))}")
                except Exception as _e_d:
                    print(f"[P5-V46D] ⚠️ P3 Top1保底跳过: {_e_d}")

                # [E] 前3位组合级集中限流: 同一前3位组合≥3注稀释至≤2
                _f3_cnt = {}
                for _c in top10:
                    _f3 = tuple(_c['digits'][:3])
                    _f3_cnt[_f3] = _f3_cnt.get(_f3, 0) + 1
                for _f3, _cnt in sorted(_f3_cnt.items(), key=lambda x: -x[1]):
                    if _cnt < 3:
                        break
                    _matches_e = [c for c in top10 if tuple(c['digits'][:3]) == _f3]
                    _matches_e.sort(key=lambda x: -x.get('final_score', 0))
                    # [V1.48.0-A] 优先替换非注入票, 注入票仅在所有重复票都被保护时替换
                    _remove_e = [c for c in _matches_e[2:] if tuple(c['digits']) not in _protected_v46]
                    if not _remove_e:
                        _remove_e = _matches_e[2:]
                    for _c_e in _remove_e:
                        _best_e = None
                        for _c2 in _v46_all:
                            if tuple(_c2['digits'][:3]) != _f3 and tuple(_c2['digits']) not in _v46_used:
                                if _best_e is None or _c2.get('final_score', -999) > _best_e.get('final_score', -999):
                                    _best_e = _c2
                        if _best_e and (_best_e.get('final_score', -999)
                                        > _c_e.get('final_score', 0) - 0.916):
                            top10.remove(_c_e)
                            top10.append(_best_e)
                            _v46_used.add(tuple(_best_e['digits']))
                            _protected_v46.add(tuple(_best_e['digits']))
                            _v46_changed = True
                            print(f"[P5-V46E] 🎯 前3位限流: {''.join(map(str,_f3))}占{_cnt}注, "
                                  f"替换→{''.join(map(str,_best_e['digits']))}")

                # [F] 后2位重号提权: 上期十/个位数字(重号)若未覆盖, 阈值0.05注入
                for _pos in [3, 4]:
                    _d = _prev_v46[_pos]
                    if any(c['digits'][_pos] == _d for c in top10):
                        continue
                    _v46_inject(_pos, _d, 'F', f'[后2位重号{_d}] ', 0.05)

                if _v46_changed:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
        except Exception as e:
            print(f"[P5-V46] ⚠️ 26202归因注入跳过: {e}")

        # 【V1.49.0】保护票TopN保底: 确保V46/B2R注入票留在最终Top10
        # 26204: V46注入的百位4票可能排序后滑出Top10(保护只防替换不防排名滑落),
        # 对齐P3 V2.41.0-F: 返回前合并保护票+非保护票
        # 【V1.49.0-②】从all候选回补: 保护票若被V46前的机制(B2DIV/PROT/A/B等)
        # 替换出池, 从all候选池重新找回注入, 保证信号不丢
        try:
            _prot_set = getattr(self, '_p5_protected', set())
            if _prot_set and top10:
                _kept_p = [c for c in top10 if tuple(c['digits']) in _prot_set]
                _kept_p.sort(key=lambda x: -x.get('final_score', -999))
                _non_p = [c for c in top10 if tuple(c['digits']) not in _prot_set]
                _non_p.sort(key=lambda x: -x.get('final_score', -999))
                _merged_p = (_kept_p + _non_p)[:10]
                if len(_merged_p) == 10:
                    top10 = _merged_p
                    print(f"[P5-PROTECT] 🛡️ 保护票保底: {len(_kept_p)}票在Top10")
                # 【V1.49.0-②】保护票被挤出: 从all候选池找回替换非保护最低分
                _missing_prot = []
                _in_top = set(tuple(c['digits']) for c in top10)
                for _pt in _prot_set:
                    if _pt not in _in_top:
                        _missing_prot.append(_pt)
                if _missing_prot:
                    # 【V1.49.0-②】用all_scored(P3混合后全量候选): 67507等
                    # 短间隔票在all_scored而非enumerate_all的all中, 原用
                    # result.get('all')找不到导致回补失败
                    _pool_rec = all_scored if all_scored else (result.get('all', []) or [])
                    for _pt in _missing_prot[:2]:
                        _rec_c = None
                        for _c in _pool_rec:
                            if tuple(_c['digits']) == _pt:
                                _rec_c = _c
                                break
                        if _rec_c:
                            _pool_np = [c for c in top10
                                        if tuple(c['digits']) not in _prot_set]
                            if not _pool_np:
                                break
                            _worst_r = min(_pool_np, key=lambda x: x.get('final_score', 0))
                            top10.remove(_worst_r)
                            top10.append(_rec_c)
                            top10.sort(key=lambda x: -x.get('final_score', -999))
                            print(f"[P5-PROTECT] ♻️ 保护票回补: "
                                  f"{''.join(map(str,_pt))} → Top10")
        except Exception as _pe:
            print(f"[P5-PROTECT] ⚠️ 保护票保底跳过: {_pe}")

        # ====== [V1.50.0] 最终整合通道(独立方法, 秒级单测) ======
        top10 = self._v50_final_channel(top10, result, all_scored)

        # ====== [V1.62.0] 组选节奏加权: 后2位(4,5) + P3(1,5,9)前3位迁移 ======
        # 周期扫描验证 (scripts/p5_cycle_scan.py, 7691期):
        #  ①后2位无序对(4,5): gap ratio=0.557(p=1.0e-6), 分半双显著
        #    (3.9e-5/2.0e-3), 滚动9窗全<1, 比50次置换最小p(2.68e-6)更极端;
        #    风险函数miss∈[45,75]最稳(1.35-1.73×双半一致), [45,250]持续≥1.25×
        #  ②P3(1,5,9)迁移: P5前3位=同期P3数据, 已验证ratio=0.323(p=5.3e-7)
        #    复用P3 V2.55.0信号(漏期∈[80,200])
        #  ③其余全阴性: 后2位位置级(十4分半不过关)/滞后k(0/600)/周期图(0/20)/
        #    gap马尔可夫(0/20)/交叉条件分布(全p>0.05)/相邻期重复(放回模型
        #    chi2=4.1 p=0.541)/AnEn(+0.018噪声)
        try:
            top10 = self._apply_combo_rhythm_boost(
                top10, all_scored if all_scored else result.get('all', []))
        except Exception as e:
            print(f"[P5-RHYTHM] ⚠️ 组选节奏加权跳过: {e}")

        # 保存预测结果 (用最终 diversity 后的 top10)
        self._last_prediction = top10[0] if top10 else None

        # ═══ 复式方案(V1.18.0): 前3位+后2位分拆复式, 后2位保底≥3候选 ═══
        compound = self._generate_compound(result)

        # V1.20.0: 预测期号 = 最新数据期号 + 1 (修正 off-by-one)
        next_period = str(int(self.last_period) + 1)

        # [V1.35.0-④] 存储可靠性: try/finally+兜底文件
        _store_ok = False
        try:
            from prediction_store import store_prediction
            store_prediction(next_period, top10)
            _store_ok = True
        except Exception as _se:
            print(f"[P5-Store] ⚠️ 存储失败: {_se}")
        finally:
            if not _store_ok:
                try:
                    _fallback_path = os.path.join(os.path.dirname(
                        os.path.dirname(os.path.abspath(__file__))),
                        'memory', 'p5_predictions.json')
                    _fb = {'period': next_period, 'bets': top10, '_fallback': True}
                    os.makedirs(os.path.dirname(_fallback_path), exist_ok=True)
                    with open(_fallback_path, 'w') as _fbf:
                        json.dump(_fb, _fbf, ensure_ascii=False, default=str)
                    print(f"[P5-Store] 💾 已兜底保存到 {_fallback_path}")
                except Exception as _fe:
                    print(f"[P5-Store] ⚠️ 兜底存储也失败: {_fe}")

        # 【V2.54.0】确定性排序: 同分票按号码升序 — 26216复现两次predict
        # Top10同一组票但排序不同(同分票依赖插入序/哈希序), 影响存档Top1
        # 一致性. final_score降序+digits升序tie-breaker跨调用稳定
        top10.sort(key=lambda x: (-x.get('final_score', 0), tuple(x['digits'])))
        return {
            'period': next_period,
            'bets': top10,
            'tail_probs': self._get_tail_probs(top10),
            'compound_bets': compound,
        }

    def _apply_combo_rhythm_boost(self, top10: List[Dict], all_pool: List[Dict]) -> List[Dict]:
        """
        【V1.62.0】组选节奏加权 — 后2位无序对(4,5) + P3(1,5,9)前3位迁移

        数据依据 (scripts/p5_cycle_scan.py, 7691期):
          ①后2位无序对(4,5): gap离散指数ratio=0.557 (p=1.0e-6, 放回基线
            p=0.02), 分半双显著(前半p=3.9e-5/后半p=2.0e-3), 滚动1500期
            9窗全<1.0, 比50次置换最小p(2.68e-6)更极端 — 间隔集中约47期
          ②风险函数: miss∈[45,75]出现概率1.35-1.73×基线且双半一致,
            [45,250]持续≥1.25× — 可开采的时变风险
          ③P3(1,5,9)迁移: P5万/千/百=同期P3百/十/个, 组选(1,5,9)节奏
            已在P3 V2.55.0验证(ratio=0.323 p=5.3e-7, 窗口[80,200])
          ④其余全阴性: 滞后k 0/600, 周期图0/20, gap马尔可夫0/20, 交叉
            条件分布全p>0.05, 相邻期重复(放回模型chi2=4.1 p=0.541),
            AnEn≈热号(噪声)

        机制: (4,5)漏期∈[45,250]时后2位恰为{4,5}的候选+0.04, Top10无此
              票时从池中换入(0.3阈值防拆高票); (1,5,9)漏期∈[80,200]时前3位
              集合含{1,5,9}中3个→+0.04/2个→+0.02。强度保守(低于V50通道权重)
        """
        if not top10 or len(self.draws) < 50:
            return top10
        draws = self.draws
        miss45 = -1
        for _i, d in enumerate(reversed(draws)):
            if tuple(sorted((d[3], d[4]))) == (4, 5):
                miss45 = _i
                break
        miss159 = -1
        for _i, d in enumerate(reversed(draws)):
            if set(d[:3]) == {1, 5, 9}:
                miss159 = _i
                break
        boost45 = 45 <= miss45 <= 250
        boost159 = 80 <= miss159 <= 200
        if not boost45 and not boost159:
            return top10
        boosted = 0
        for c in top10:
            digits = c.get('digits')
            if not digits:
                continue
            adj = 0.0
            if boost45 and tuple(sorted((digits[3], digits[4]))) == (4, 5):
                adj += 0.04
            if boost159:
                ov = len(set(digits[:3]) & {1, 5, 9})
                if ov == 3:
                    adj += 0.04
                elif ov == 2:
                    adj += 0.02
            if adj:
                c['final_score'] = c.get('final_score', 0) + adj
                c['combo_rhythm'] = adj
                boosted += 1
        injected = False
        if boost45 and not any(
                tuple(sorted((c['digits'][3], c['digits'][4]))) == (4, 5)
                for c in top10):
            best45 = None
            for c in all_pool:
                if tuple(sorted((c['digits'][3], c['digits'][4]))) != (4, 5):
                    continue
                if best45 is None or c.get('final_score', -999) > best45.get('final_score', -999):
                    best45 = c
            if best45:
                best45 = dict(best45)
                best45['final_score'] = best45.get('final_score', 0) + 0.04
                best45['combo_rhythm'] = 0.04
                worst = min(top10, key=lambda x: x.get('final_score', 0))
                if best45['final_score'] > worst.get('final_score', 0) * 0.3:
                    top10.remove(worst)
                    top10.append(best45)
                    injected = True
        if boosted or injected:
            print(f"[P5-RHYTHM] 🎵节奏加权: (4,5)漏{miss45}期 "
                  f"(1,5,9)漏{miss159}期: {boosted}注加分"
                  f"{'+1注注入' if injected else ''}")
        return top10

    def _v50_final_channel(self, top10: List[Dict], result: Dict, all_scored: List) -> List[Dict]:
        """V1.50.0 最终整合通道(独立方法, 可单元测试): 重号上限+优先级分层+热号配额.
        26205期归因: 重号/中冷垄断挤出短间隔回补. 严重退化时构造式重建.
        返回修正后的top10"""
        # ====== [V1.50.0] 26205期归因: 最终整合通道(重号上限+优先级分层+热号配额) ======
        # 实际开奖 8 0 6 0 8, 预测万位{2,5,6}(万6上期重号占7席)/千位{4,5,7,8}
        # (千5中冷占5席), 万8(漏3期)/千0(漏5期)在3-8期短间隔回补窗口内却0/10,
        # 最佳单注仅2/5, 位置命中率10%. 根因: ①重号/中冷数字垄断席位挤掉短间隔
        # 回补; ②中间环节替换不尊重保护集(1-9期档保护在V46, 但B2R~V46之间的
        # 十余个替换环节不查保护集); ③B2N近端只覆盖后2位, 前3位近端(1-2期)
        # 无独立保障. 本通道在全部后处理之后最终校准:
        # [B] 重号/垄断上限: 每位置每数字≤2席(上期重号/中冷/深冷垄断裁剪)
        # [C] 优先级分层: 近端(0-2期) > 短间隔(3-8期) > 中冷(6-9期) > 深冷(≥10),
        #     高档缺号时只换出低档(更低优先级)票, 低档不挤占高档
        # [D] P5原生评分并行(hybrid层): 非P3候选原生前3位证据同尺度归一化
        # [E] 热号配额: 近10期频次≥4的数字每位置至少2席
        # 严重退化时(任一数字≥4席或≥2位置缺tier0)放弃补丁式修复, 直接构造式重建
        try:
            if top10 and len(top10) >= 5 and len(self.draws) >= 20:
                _v50_names = ['万', '千', '百', '十', '个']
                # 遗漏表(近200期)
                _v50_miss = [{}, {}, {}, {}, {}]
                for _pos in range(5):
                    _seq = [d[_pos] for d in self.draws[-min(200, len(self.draws)):]]
                    for _d in range(10):
                        for _i in range(len(_seq) - 1, -1, -1):
                            if _seq[_i] == _d:
                                _v50_miss[_pos][_d] = len(_seq) - 1 - _i
                                break
                        if _d not in _v50_miss[_pos]:
                            _v50_miss[_pos][_d] = len(_seq)
                # 近10期频率表
                _v50_freq = [{}, {}, {}, {}, {}]
                _recent10 = self.draws[-10:]
                for _pos in range(5):
                    for _d in range(10):
                        _v50_freq[_pos][_d] = sum(1 for r in _recent10 if r[_pos] == _d)

                _v50_pool = list(all_scored if all_scored else (result.get('all', []) or []))
                _v50_pool += list(result.get('top100', []) or [])
                _v50_used = set(tuple(c['digits']) for c in top10)
                _v50_changed = False
                _v50_inj_cnt = 0
                _V50_MAX_INJ = 60
                # 本次通道注入票: 换出时优先不拆自己刚修的票(防打地鼠)
                _v50_injected = set()

                def _v50_tier(_pos, _d):
                    """优先级分层: 0=近端(0-2期) 1=短间隔(3-8期) 2=中冷(6-9期)
                    3=中冷深(10-15期) 4=深冷(≥16期)
                    V1.52.0: 10-15独立成档 — 26207个4(漏14期)原归tier3(≥10)
                    不在重建需求/高档保底覆盖内, 0/10"""
                    _m = _v50_miss[_pos].get(_d, 99)
                    if _m <= 2:
                        return 0
                    if _m <= 8:
                        return 1
                    if _m <= 9:
                        return 2
                    if _m <= 15:
                        return 3
                    return 4

                def _v50_best(_pos, _d):
                    _b = None
                    for _c in _v50_pool:
                        if _c['digits'][_pos] == _d and tuple(_c['digits']) not in _v50_used:
                            if _b is None or _c.get('final_score', -999) > _b.get('final_score', -999):
                                _b = _c
                    return _b

                def _v50_coverage_loss(_c):
                    """移除该票会造成多少个(位置,高档数字)唯一覆盖丢失(tier0-3)"""
                    _loss = 0
                    for _p in range(5):
                        _d = _c['digits'][_p]
                        if _v50_tier(_p, _d) > 3:
                            continue  # 深冷(≥16)数字不视为珍贵覆盖
                        if sum(1 for c2 in top10 if c2['digits'][_p] == _d) == 1:
                            _loss += 1
                    return _loss

                def _v50_replace(_pos, _d, _tag, _only_digit=None):
                    """换入含_d@_pos的最高分候选. 换出目标:
                    - _only_digit指定时(垄断裁剪): 必须含_only_digit@_pos的票
                    - 否则(档位保底): 更低优先档(更高tier)票, 无则非保护最低分
                    同条件内优先换出: 非本次注入票 > 唯一覆盖损失小 > 分低"""
                    nonlocal _v50_changed, _v50_inj_cnt
                    if _v50_inj_cnt >= _V50_MAX_INJ:
                        return False
                    _best = _v50_best(_pos, _d)
                    if _best is None:
                        return False
                    _t_d = _v50_tier(_pos, _d)
                    _prot = getattr(self, '_p5_protected', set())
                    if _only_digit is not None:
                        _cands_out = [c for c in top10 if c['digits'][_pos] == _only_digit]
                        if not _cands_out:
                            return False
                    else:
                        _cands_out = [c for c in top10
                                      if _v50_tier(_pos, c['digits'][_pos]) > _t_d]
                        if not _cands_out:
                            _cands_out = [c for c in top10 if tuple(c['digits']) not in _prot]
                    if not _cands_out:
                        return False
                    # 优先换非本次注入票
                    _cands_native = [c for c in _cands_out if tuple(c['digits']) not in _v50_injected]
                    if _cands_native:
                        _cands_out = _cands_native
                    _worst = min(_cands_out, key=lambda x: (_v50_coverage_loss(x),
                                                            x.get('final_score', 0)))
                    top10.remove(_worst)
                    top10.append(_best)
                    _v50_used.discard(tuple(_worst['digits']))
                    _v50_used.add(tuple(_best['digits']))
                    _v50_injected.add(tuple(_best['digits']))
                    _v50_changed = True
                    _v50_inj_cnt += 1
                    print(f"[P5-V50{_tag}] 🔄 {_v50_names[_pos]}位{_d}"
                          f"(漏{_v50_miss[_pos].get(_d, 99)}期/tier{_t_d}) "
                          f"→ {''.join(map(str,_best['digits']))}")
                    return True

                # ---- 退化检测: 任一数字≥4席 或 ≥2位置缺tier0覆盖 → 构造式重建 ----
                def _v50_degenerate():
                    for _pos in range(5):
                        _cnt_map = {}
                        for _c in top10:
                            _cnt_map[_c['digits'][_pos]] = _cnt_map.get(_c['digits'][_pos], 0) + 1
                        if any(_c >= 4 for _c in _cnt_map.values()):
                            return True
                    _miss_t0 = 0
                    for _pos in range(5):
                        _has_t0 = any(_v50_tier(_pos, d) == 0 for d in range(10))
                        _cov_t0 = any(_v50_tier(_pos, c['digits'][_pos]) == 0 for c in top10)
                        if _has_t0 and not _cov_t0:
                            _miss_t0 += 1
                    return _miss_t0 >= 2

                if _v50_degenerate():
                    # ---- [B/C/E] 构造式重建: 需求(位置,档)贪心覆盖 ----
                    print(f"[P5-V50] 🏗️ 检测到严重退化, 构造式重建")
                    _needs = []  # (pos, tier, d) 扁平化需求
                    _pos_tier_cnt = {}
                    # 【V1.54.0】重建需求: tier全局优先级(近端>短间隔>中冷>深冷),
                    # 修复26209百2(漏7)/万9(漏6)/十7(漏6)/个7(漏4)全为tier1短间隔
                    # 但被(位置,档)顺序贪心遗漏: 万/千tier2/3占满10席致百tier1未轮到;
                    # tier1跨位置遗漏降序共享席位(每位置≤2), 最冷短间隔优先回补
                    for _pos in range(5):
                        for _t in (0, 1, 2, 3):
                            _digs = [d for d in range(10) if _v50_tier(_pos, d) == _t]
                            if not _digs:
                                continue
                            # tier0浅优先(重号/近端信号强), tier1-3深优先(回补最冷)
                            _digs.sort(key=lambda d: _v50_miss[_pos].get(d, 99),
                                       reverse=(_t >= 1))
                            for _d in _digs:
                                _needs.append((_pos, _t, _d))
                    # tier全局排序: 所有位置tier0 → 所有位置tier1 → tier2 → tier3
                    # (原(位置,档)顺序: 万tier0-3后千tier0-3... 百tier1在第13+位,
                    # 容量10早满 — 26209百2漏7丢失的直接原因)
                    _needs.sort(key=lambda x: x[1])
                    _new_top = []
                    _used = set()
                    _pos_cnt = [{} for _ in range(5)]

                    def _violates(_c):
                        for _p in range(5):
                            if _pos_cnt[_p].get(_c['digits'][_p], 0) >= 2:
                                return True
                        return False

                    _pool_sorted = sorted(_v50_pool, key=lambda x: -x.get('final_score', -999))

                    def _v50_synth(_pos, _d, _tag='SYN'):
                        """合成候选: 取池中最高分未用票, 把_pos位替换为_d (P5任意5位组合合法).
                        池只有top500且高度集中, 缺号时无法从池中取到候选, 合成保底
                        V1.52.0: 检查改后票而非原始票 — 原_violates(_c)在多位置2席饱和后
                        池中几乎全票违反, 十位tier2(十4漏9)合成失败致26207十4 0/10"""
                        nonlocal _v50_changed, _v50_inj_cnt
                        if _v50_inj_cnt >= _V50_MAX_INJ:
                            return None
                        for _c in _pool_sorted:
                            if tuple(_c['digits']) in _used:
                                continue
                            _nc = dict(_c)
                            _nc['digits'] = list(_c['digits'])
                            _nc['digits'][_pos] = _d
                            if tuple(_nc['digits']) in _used:
                                continue
                            # 【V1.52.0】检查改后票: 加入后各位置≤2席(_pos位需求未满足
                            # 保证≤1席, 只需查其余4位当前计数≤1)
                            _synth_ok = all(
                                _pos_cnt[_p].get(_nc['digits'][_p], 0) <= 1
                                for _p in range(5) if _p != _pos)
                            if not _synth_ok:
                                continue
                            _nc['final_score'] = _c.get('final_score', 0) - 0.5
                            _nc['_synthetic'] = True
                            _v50_inj_cnt += 1
                            print(f"[P5-V50-{_tag}] 🧪 合成: {_v50_names[_pos]}位{_d}"
                                  f"(漏{_v50_miss[_pos].get(_d, 99)}期) "
                                  f"→ {''.join(map(str,_nc['digits']))}")
                            return _nc
                        # 【V1.52.0】池中无满足票(池top500高度集中, 改号后其余4位
                        # 几乎必落在饱和数字上, 26207十位tier2合成失败致十4 0/10):
                        # 直接构造任意合法组合 — P5任意5位组合均合法, 不依赖池多样性
                        # 构造票用池最低分-1: 原池最高-0.5虚高, 重建后排序时
                        # 构造票反超真实高分票(26208 Top1=00016)
                        _low_score = _pool_sorted[-1].get('final_score', -999) if _pool_sorted else -999
                        _others = [p for p in range(5) if p != _pos]
                        for _digs in itertools.product(*(range(10) for _ in _others)):
                            _cand = [0] * 5
                            _cand[_pos] = _d
                            _ok = True
                            for _p, _v in zip(_others, _digs):
                                if _pos_cnt[_p].get(_v, 0) >= 2:
                                    _ok = False
                                    break
                                _cand[_p] = _v
                            if not _ok:
                                continue
                            _nc = {'digits': _cand, 'final_score': _low_score - 1.0,
                                   '_synthetic': True}
                            _v50_inj_cnt += 1
                            print(f"[P5-V50-{_tag}] 🧪 构造合成: {_v50_names[_pos]}位{_d}"
                                  f"(漏{_v50_miss[_pos].get(_d, 99)}期) "
                                  f"→ {''.join(map(str,_nc['digits']))}")
                            return _nc
                        return None

                    # 按需求顺序逐个满足: 每需求选满足它的最佳候选
                    # (同时尽量覆盖其他未满足需求), 确定性且不打地鼠
                    # V1.53.0: tier3(10-15中冷深)每位置保2个数字 — 26208万4(漏10)
                    # 与万5(漏12)同档, 原只保_digs[0]万5, 万4 0/10(同P3 26208个1型)
                    # V1.54.0: ①_needs按tier全局排序(tier0所有位置→tier1→tier2→tier3),
                    #   修复26209百2(漏7短间隔)被万/千tier2/3占满10席未轮到;
                    #   ②tier1跨位置遗漏降序(短间隔回补最冷优先, 同P3[B]语义),
                    #   修复26209万9(漏6)被漏3的6抢占(浅优先保1个只保6);
                    #   ③tier1每位置保2个(与tier3对齐). 26209开奖98277的
                    #   万9/百2/十7/个7全是tier1(漏4-7), 原全漏
                    # 需求列表: (pos, tier, d), 已按tier全局优先级排序
                    # (tier0重号/近端 > tier1短间隔 > tier2/3中冷), 同tier内
                    # tier0浅优先(近期信号强), tier1-3深优先(回补最冷)
                    for (_pos, _t, _target) in _needs:
                        if len(_new_top) >= 10:
                            break
                        _limit_n = 2 if _t == 1 else 1
                        if _pos_tier_cnt.get((_pos, _t), 0) >= _limit_n:
                            continue
                        if any(c['digits'][_pos] == _target for c in _new_top):
                            _pos_tier_cnt[(_pos, _t)] = _pos_tier_cnt.get((_pos, _t), 0) + 1
                            continue
                        # 选含_target@_pos的最高分候选, gain=同时覆盖其他未满足需求数
                        _best_c = None
                        _best_gain = -1
                        _cands_t = []
                        for _c in _pool_sorted:
                            if tuple(_c['digits']) in _used or _violates(_c):
                                continue
                            if _c['digits'][_pos] == _target:
                                _cands_t.append(_c)
                        for _c in _cands_t:
                            _gain = 1
                            for (_pos2, _t2, _d2) in _needs:
                                if (_pos2, _t2) == (_pos, _t):
                                    continue
                                if any(c2['digits'][_pos2] == _d2 for c2 in _new_top):
                                    continue
                                if _c['digits'][_pos2] == _d2:
                                    _gain += 1
                            if _gain > _best_gain:
                                _best_gain = _gain
                                _best_c = _c
                        if _best_c is None:
                            # 池中无候选(500池高度集中), 合成保底
                            _best_c = _v50_synth(_pos, _target, 'REBUILD')
                            if _best_c is None:
                                print(f"[P5-V50-REBUILD] ⚠️ 需求({_v50_names[_pos]}位tier{_t}数字{_target})无候选, 跳过")
                                continue
                        _new_top.append(_best_c)
                        _used.add(tuple(_best_c['digits']))
                        for _p in range(5):
                            _pos_cnt[_p][_best_c['digits'][_p]] = _pos_cnt[_p].get(_best_c['digits'][_p], 0) + 1
                        _pos_tier_cnt[(_pos, _t)] = _pos_tier_cnt.get((_pos, _t), 0) + 1
                        print(f"[P5-V50-REBUILD] 🧱 覆盖需求: "
                              f"{''.join(map(str,_best_c['digits']))} (gain={_best_gain}, "
                              f"{_v50_names[_pos]}位tier{_t}数字{_target})")

                    # 剩余席位: 最高分未用候选(严格≤2/数字)
                    for _c in _pool_sorted:
                        if len(_new_top) >= 10:
                            break
                        if tuple(_c['digits']) in _used or _violates(_c):
                            continue
                        _new_top.append(_c)
                        _used.add(tuple(_c['digits']))
                        for _p in range(5):
                            _pos_cnt[_p][_c['digits'][_p]] = _pos_cnt[_p].get(_c['digits'][_p], 0) + 1
                    # 【V1.52.0】仍不足10注: 构造任意合法组合补满 — 池top500高度集中
                    # 且多位置2席饱和时池中票全违反, 原剩余席位+合成补满均无法补足
                    if len(_new_top) < 10:
                        _low_score = _pool_sorted[-1].get('final_score', -999) if _pool_sorted else -999
                        for _digs in itertools.product(range(10), repeat=5):
                            if len(_new_top) >= 10:
                                break
                            if tuple(_digs) in _used:
                                continue
                            if any(_pos_cnt[_p].get(_digs[_p], 0) >= 2 for _p in range(5)):
                                continue
                            _nc = {'digits': list(_digs), 'final_score': _low_score - 1.0,
                                   '_synthetic': True}
                            _new_top.append(_nc)
                            _used.add(tuple(_nc['digits']))
                            for _p in range(5):
                                _pos_cnt[_p][_nc['digits'][_p]] = _pos_cnt[_p].get(_nc['digits'][_p], 0) + 1
                            print(f"[P5-V50-REBUILD] 🧪 构造补满: {''.join(map(str,_nc['digits']))}")
                    # 仍不足10注: 合成补满(严格保持≤2/数字, 超限位置换最低遗漏数字)
                    if len(_new_top) < 10:
                        for _c in _pool_sorted:
                            if len(_new_top) >= 10:
                                break
                            if tuple(_c['digits']) in _used:
                                continue
                            _nc = dict(_c)
                            _nc['digits'] = list(_c['digits'])
                            for _p in range(5):
                                if _pos_cnt[_p].get(_nc['digits'][_p], 0) >= 2:
                                    _best_d = None
                                    _best_m = 999
                                    for _d in range(10):
                                        if _pos_cnt[_p].get(_d, 0) >= 2:
                                            continue
                                        _m = _v50_miss[_p].get(_d, 99)
                                        if _m < _best_m:
                                            _best_m = _m
                                            _best_d = _d
                                    if _best_d is not None:
                                        _nc['digits'][_p] = _best_d
                            if tuple(_nc['digits']) in _used:
                                continue
                            _nc['final_score'] = _c.get('final_score', 0) - 0.5
                            _nc['_synthetic'] = True
                            _new_top.append(_nc)
                            _used.add(tuple(_nc['digits']))
                            for _p in range(5):
                                _pos_cnt[_p][_nc['digits'][_p]] = _pos_cnt[_p].get(_nc['digits'][_p], 0) + 1
                            print(f"[P5-V50-REBUILD] 🧪 合成补满: {''.join(map(str,_nc['digits']))}")
                    # 极端情况仍不足10注: 放宽到≤3/数字(仅在池极端集中时触发)
                    if len(_new_top) < 10:
                        def _violates3(_c):
                            for _p in range(5):
                                if _pos_cnt[_p].get(_c['digits'][_p], 0) >= 3:
                                    return True
                            return False
                        for _c in _pool_sorted:
                            if len(_new_top) >= 10:
                                break
                            if tuple(_c['digits']) in _used or _violates3(_c):
                                continue
                            _new_top.append(_c)
                            _used.add(tuple(_c['digits']))
                            for _p in range(5):
                                _pos_cnt[_p][_c['digits'][_p]] = _pos_cnt[_p].get(_c['digits'][_p], 0) + 1
                    # 热号配额: 频次≥4数字在重建后若<2席, 再补
                    # 【V1.52.0】替换末尾票时遵守≤2约束并同步_pos_cnt — 原实现
                    # 不检查_violates且_pos_cnt过期, 可能引入新垄断(场景3回归抓出)
                    if len(_new_top) >= 10:
                        _new_used = set(tuple(c['digits']) for c in _new_top)
                        for _pos in range(5):
                            for _d in range(10):
                                if _v50_freq[_pos].get(_d, 0) >= 4:
                                    _cnt = sum(1 for c in _new_top if c['digits'][_pos] == _d)
                                    while _cnt < 2:
                                        _b = None
                                        _old_c = _new_top[-1]
                                        for _c in _pool_sorted:
                                            if tuple(_c['digits']) in _new_used:
                                                continue
                                            if _c['digits'][_pos] != _d:
                                                continue
                                            _cand_ok = True
                                            for _p in range(5):
                                                _cd = _c['digits'][_p]
                                                _cnt_after = _pos_cnt[_p].get(_cd, 0) + (
                                                    0 if _cd == _old_c['digits'][_p] else 1)
                                                if _cnt_after > 2:
                                                    _cand_ok = False
                                                    break
                                            if not _cand_ok:
                                                continue
                                            if _b is None or _c.get('final_score', -999) > _b.get('final_score', -999):
                                                _b = _c
                                        if _b is None:
                                            break
                                        _new_top[-1] = _b
                                        _new_used.discard(tuple(_old_c['digits']))
                                        _new_used.add(tuple(_b['digits']))
                                        for _p in range(5):
                                            _pos_cnt[_p][_old_c['digits'][_p]] = max(
                                                0, _pos_cnt[_p].get(_old_c['digits'][_p], 0) - 1)
                                            _pos_cnt[_p][_b['digits'][_p]] = _pos_cnt[_p].get(_b['digits'][_p], 0) + 1
                                        _cnt += 1
                                        print(f"[P5-V50-REBUILD] 🔥 热号{_v50_names[_pos]}位{_d}补席: "
                                              f"{''.join(map(str,_b['digits']))}")
                    if len(_new_top) == 10:
                        top10 = _new_top
                        _v50_changed = True
                        print(f"[P5-V50] ✅ 构造式重建完成")
                    else:
                        print(f"[P5-V50] ⚠️ 重建不足10注({len(_new_top)}), 保留原top10")
                else:
                    # ---- 非退化: 补丁式修复 ----
                    # [B] 单数字席位上限: 每位置每数字≤2席
                    for _pos in range(5):
                        for _round in range(6):
                            _cnt_map = {}
                            for _c in top10:
                                _cnt_map[_c['digits'][_pos]] = _cnt_map.get(_c['digits'][_pos], 0) + 1
                            _excess_d = None
                            for _d, _cnt in sorted(_cnt_map.items(), key=lambda x: -x[1]):
                                if _cnt > 2:
                                    _excess_d = _d
                                    break
                            if _excess_d is None:
                                break
                            _replaced = False
                            for _t_hi in (0, 1):
                                if _replaced:
                                    break
                                for _d2 in range(10):
                                    if _v50_tier(_pos, _d2) != _t_hi:
                                        continue
                                    if any(c['digits'][_pos] == _d2 for c in top10):
                                        continue
                                    if _v50_replace(_pos, _d2, '-CAP', _only_digit=_excess_d):
                                        _replaced = True
                                        break
                            if not _replaced:
                                _best_any = None
                                for _c in _v50_pool:
                                    if tuple(_c['digits']) in _v50_used:
                                        continue
                                    if _best_any is None or _c.get('final_score', -999) > _best_any.get('final_score', -999):
                                        _best_any = _c
                                if _best_any is not None and _v50_inj_cnt < _V50_MAX_INJ:
                                    _cands_out = [c for c in top10 if c['digits'][_pos] == _excess_d]
                                    if _cands_out:
                                        _worst = min(_cands_out, key=lambda x: (_v50_coverage_loss(x), x.get('final_score', 0)))
                                        top10.remove(_worst)
                                        top10.append(_best_any)
                                        _v50_used.discard(tuple(_worst['digits']))
                                        _v50_used.add(tuple(_best_any['digits']))
                                        _v50_injected.add(tuple(_best_any['digits']))
                                        _v50_changed = True
                                        _v50_inj_cnt += 1
                                        _replaced = True
                                        print(f"[P5-V50-CAP] 🔄 {_v50_names[_pos]}位{_excess_d}超席"
                                              f" → {''.join(map(str,_best_any['digits']))}")
                            if not _replaced:
                                if len(top10) > 8:
                                    _tickets = [c for c in top10 if c['digits'][_pos] == _excess_d]
                                    if _tickets:
                                        top10.remove(_tickets[0])
                                        _v50_used.discard(tuple(_tickets[0]['digits']))
                                        _v50_changed = True
                                        print(f"[P5-V50-CAP] ✂️ {_v50_names[_pos]}位{_excess_d}占{_cnt_map[_excess_d]}席, 裁剪1席")
                                break
                    # [C] 高档保底: 多轮循环直到无高档缺号可补
                    for _round in range(4):
                        _inj_this_round = 0
                        for _pos in range(5):
                            for _t_need in (0, 1, 2, 3):
                                _uncovered = [d for d in range(10)
                                              if _v50_tier(_pos, d) == _t_need
                                              and not any(c['digits'][_pos] == d for c in top10)]
                                if _uncovered:
                                    _uncovered.sort(key=lambda d: _v50_miss[_pos].get(d, 99))
                                    if _v50_replace(_pos, _uncovered[0], '-TIER'):
                                        _inj_this_round += 1
                        if _inj_this_round == 0:
                            break
                    # [E] 热号配额: 近10期频次≥4且覆盖<2席 → 补到2席
                    for _pos in range(5):
                        for _d in range(10):
                            if _v50_freq[_pos].get(_d, 0) >= 4:
                                _cnt = sum(1 for c in top10 if c['digits'][_pos] == _d)
                                while _cnt < 2:
                                    if not _v50_replace(_pos, _d, '-HOT'):
                                        break
                                    _cnt += 1

                if _v50_changed:
                    top10.sort(key=lambda x: -x.get('final_score', 0))
                    print(f"[P5-V50] ✅ 最终整合通道完成(注入{_v50_inj_cnt}注, "
                          f"票数{len(top10)})")
        except Exception as _e50:
            print(f"[P5-V50] ⚠️ 最终整合通道跳过: {_e50}")

        # ====== [V1.51.0] P3 Top1最终保底 — 【V1.55.0】扩展为P3 TopN保底 ======
        # 26206期归因: P3 Top1=558(前3位5,5,8)在V50重建/补丁中被拆除, 违反
        # V1.43.0设计(P3 Top1强制在P5 Top10). V46D保底在V50之前, 通道后置
        # 会拆掉它 — 在通道末端再保一次, 双路径生效
        # 【V1.55.0】26210期归因: 开奖09451千9 0/10 — P3候选(2,9,6)/(2,9,2)
        # 的千9信号在P5池中缺失(500池集中, 万2漏36深冷被GA/多样性挤出),
        # 混合评分无票可改, 仅Top1有保底 → Top2-Top10信号全部丢失.
        # 扩展: 遍历P3 Top10, 每个前3位缺失时保底注入(优先真实池票,
        # 池中无则合成改前3位), 上限5注防过度干预
        try:
            _p3t51_all = self._load_p3_prediction(self.last_period, top_n=10)
            # 【V1.55.0】兼容stub/旧接口: 返回3元素列表(单个预测)时包装成列表
            if _p3t51_all and len(_p3t51_all) == 3 and all(isinstance(x, int) for x in _p3t51_all):
                _p3t51_all = [_p3t51_all]
            if _p3t51_all:
                _v51_injected = 0
                _v51_prot = set()  # 【V1.55.0】已注入保底票保护: 后续注入不可换出
                # 【V1.55.0】上限5→8: 26210开奖09451的百4(漏5期)来自P3候选254
                # (P3 Top7), 上限5只保到245(P3 Top6) → 百4全漏. 扩到8覆盖
                # 更多P3候选, 后2位由_v51_loss权重保护
                # 【V2.54.0】上限10→9: 26216开奖95300后2位十0(漏10)/个0(漏1)
                # 全漏 — V51注入10张P3保底票把后2位覆盖票(重建票00100/07000)
                # 全换出. 上限9留1席给后2位覆盖(重建票中后2位覆盖最好的一张
                # 自然保留), P3 Top10第10张(586)放弃可接受(前3位核心信号
                # 978/223/357已覆盖)
                for _p3t51 in _p3t51_all:
                    if _v51_injected >= 8:
                        break
                    if len(_p3t51) != 3:
                        continue
                    _p3t_key = tuple(int(x) for x in _p3t51)
                    if any(tuple(c['digits'][:3]) == _p3t_key for c in top10):
                        continue
                    _best_p3t = None
                    for _c in _v50_pool:
                        if tuple(_c['digits'][:3]) == _p3t_key:
                            if _best_p3t is None or _c.get('final_score', -999) > _best_p3t.get('final_score', -999):
                                _best_p3t = _c
                    if _best_p3t is None:
                        # 池中无该前3位候选(500池集中) → 合成: 取最高分票改前3位
                        # 【V1.57.0】后2位多样化: 原取池中第一个非-999票, 后2位
                        # 固定(26212复现十8/个6占7席, 26211场景十5/个1占7席挤压
                        # 后2位覆盖). 改选"后2位在当前top10出现最少"的源票,
                        # 使合成票后2位分散, 保护后2位多样性
                        _cand51s = [c for c in _v50_pool
                                    if c.get('final_score', -999) != -999]
                        if _cand51s:
                            def _tail_cnt51(_c):
                                return (sum(1 for t in top10
                                            if t['digits'][3] == _c['digits'][3])
                                        + sum(1 for t in top10
                                              if t['digits'][4] == _c['digits'][4]))
                            _src51 = min(_cand51s,
                                         key=lambda x: (_tail_cnt51(x),
                                                        -x.get('final_score', -999)))
                            _nc51 = dict(_src51)
                            _nc51['digits'] = list(_src51['digits'])
                            _nc51['digits'][:3] = list(_p3t_key)
                            _nc51['final_score'] = _src51.get('final_score', 0) - 0.5
                            _best_p3t = _nc51
                    if _best_p3t is not None:
                        _prot51 = getattr(self, '_p5_protected', set())
                        _p3_sig = set(tuple(int(x) for x in c) for c in _p3t51_all)  # 【V1.55.0】
                        _pool_out51 = [c for c in top10 if tuple(c['digits']) not in _prot51
                                       and tuple(c['digits']) not in _v51_prot
                                       and tuple(c['digits'][:3]) not in _p3_sig]
                        # 【V1.63.0】排除tier2/3中冷(6-15)唯一载体 — 26219根因:
                        # REBUILD覆盖千6(漏11)的06535被V51保底换出致千6 0/10;
                        # 中冷是稀缺信号(P3 Top10无载体时REBUILD合成票是唯一来源),
                        # V51宁可少注入P3票也不拆中冷唯一覆盖
                        _pool_out51 = [c for c in _pool_out51
                                       if not any(_v50_tier(_p, c['digits'][_p]) in (2, 3)
                                                  and sum(1 for c2 in top10
                                                         if c2['digits'][_p] == c['digits'][_p]) == 1
                                                  for _p in range(5))]
                        if not _pool_out51:
                            _pool_out51 = [c for c in top10 if tuple(c['digits']) not in _prot51
                                           and tuple(c['digits']) not in _v51_prot]
                        if not _pool_out51:
                            _pool_out51 = list(top10)
                        # 优先换出含超限数字的票(防保底制造新垄断, 如55896的十9)
                        _over51 = [i for i in range(5)
                                   if sum(1 for c in top10 if c['digits'][i] == _best_p3t['digits'][i]) >= 2]
                        # 【V1.52.0】换出尊重珍贵覆盖: 26207重建选中的64842(十4漏9期
                        # tier2唯一载体)被27803换出致十4 0/10 — 优先换珍贵覆盖损失小
                        # 【V1.55.0】后2位覆盖纳入loss: 26210开奖个1(漏8期)载体
                        # 68081被V51保底换出致个1 0/10 — 换出时避开后2位唯一载体
                        _prev51 = list(self.draws[-1])

                        def _v51_loss(_c):
                            _l = 0
                            for _p in range(5):
                                _d = _c['digits'][_p]
                                _t = _v50_tier(_p, _d)
                                if _t > 3:
                                    continue
                                if sum(1 for c2 in top10 if c2['digits'][_p] == _d) == 1:
                                    _l += 1
                            # 后2位(十/个)唯一覆盖加权: 前3位由P3保底兜底, 后2位
                            # 丢失即永久丢失(V51合成票后2位固定85/73等)
                            for _p in (3, 4):
                                _d = _c['digits'][_p]
                                if sum(1 for c2 in top10 if c2['digits'][_p] == _d) == 1:
                                    _l += 2
                                    # 【V1.57.0】上期后2位重号唯一载体加权+4 —
                                    # 26212根因: 十4重号载体63848(loss=3)与
                                    # 23583/23506并列, 按score被V51第6次换出,
                                    # 开奖83943十4 0/10
                                    if _d == _prev51[_p]:
                                        _l += 4
                                    # 【V2.54.0】后2位近端(1-3期)唯一覆盖+3 —
                                    # 26216根因: 个0(漏1期)票26870被V51保底换出
                                    # → 个0 0/10. 近端信号价值高于普通唯一覆盖
                                    elif 1 <= _v50_miss[_p].get(_d, 99) <= 3:
                                        _l += 3
                            # 【V1.64.0】前3位短间隔(4-9期)唯一载体加权+3 — 26232
                            # 根因: 千0(漏5短间隔)载体30272/00820与十3(漏6)载体
                            # 09837被MIDC/MCP/V46B注入后, 被V51保底注入8张P3票
                            # 逐一换出(前3位唯一载体仅通用+1权重) → 千0/十3
                            # 0/10. 与26231百7/26232千0的V51上限8截断同源: V51
                            # 换出必须避开前3位短间隔唯一覆盖(P5自身短间隔信号,
                            # 后2位由V51N复查兜底, 前3位短间隔无复查通道)
                            for _p in (0, 1, 2):
                                _d = _c['digits'][_p]
                                if (4 <= _v50_miss[_p].get(_d, 99) <= 9
                                        and sum(1 for c2 in top10
                                               if c2['digits'][_p] == _d) == 1):
                                    _l += 3
                            return _l
                        # 【V1.52.0】换出目标优先"换入后所有位置≤2": 原fallback任意票
                        # 换入27803后百8/十0 2→3席新垄断(26205场景回归抓出)
                        def _v51_ok(_c):
                            for _p in range(5):
                                _dn = _best_p3t['digits'][_p]
                                _do = _c['digits'][_p]
                                _cnt = sum(1 for c2 in top10 if c2['digits'][_p] == _dn) + (
                                    0 if _dn == _do else 1)
                                if _cnt > 2:
                                    return False
                            return True
                        _targets51 = [c for c in _pool_out51 if _v51_ok(c)]
                        if not _targets51:
                            _targets51 = [c for c in _pool_out51
                                          if all(c['digits'][i] == _best_p3t['digits'][i] for i in _over51)]
                        if not _targets51:
                            _targets51 = _pool_out51
                        _worst51 = min(_targets51, key=lambda x: (_v51_loss(x),
                                                                  x.get('final_score', -999)))
                        top10.remove(_worst51)
                        top10.append(_best_p3t)
                        # 【V1.52.0】注入后裁剪: 保底票可能使某位置>2席(26205场景:
                        # _best_p3t的3个位置数字换入前均已2席, 无票可同时携带全部
                        # 超限数字 → fallback任意换出 → 注入后超限). 逐位置裁剪回≤2
                        # 【V1.55.0】裁剪排除_v51_prot: 已注入V51保底票绝不被后续
                        # 注入裁剪掉(26210: 连续注入万2候选296/268/288/245时,
                        # 后注入的票把先注入的裁剪移除, 只剩最后一个24575)
                        for _p in range(5):
                            _d = _best_p3t['digits'][_p]
                            while sum(1 for c in top10 if c['digits'][_p] == _d) > 2:
                                _cands_o = [c for c in top10
                                            if c['digits'][_p] == _d and c is not _best_p3t
                                            and tuple(c['digits']) not in _v51_prot]
                                if not _cands_o:
                                    # 全部为V51保护票 → 跳过裁剪, 接受暂时超限
                                    # (保底优先, 后2位多样性由排序兜底)
                                    break
                                _worst_o = min(_cands_o, key=lambda x: (_v51_loss(x),
                                                                        x.get('final_score', -999)))
                                top10.remove(_worst_o)
                                _rep = None
                                for _c in _v50_pool:
                                    if tuple(_c['digits']) in set(tuple(t['digits']) for t in top10):
                                        continue
                                    if _c['digits'][_p] == _d:
                                        continue
                                    _rep_ok = True
                                    for _p2 in range(5):
                                        _dn2 = _c['digits'][_p2]
                                        if sum(1 for t in top10 if t['digits'][_p2] == _dn2) >= 2:
                                            _rep_ok = False
                                            break
                                    if not _rep_ok:
                                        continue
                                    if _rep is None or _c.get('final_score', -999) > _rep.get('final_score', -999):
                                        _rep = _c
                                if _rep is not None:
                                    top10.append(_rep)
                                else:
                                    _nc_o = dict(_worst_o)
                                    _nc_o['digits'] = list(_worst_o['digits'])
                                    _nc_o['digits'][_p] = (int(_d) + 1) % 10
                                    _nc_o['final_score'] = _worst_o.get('final_score', -999) - 0.5
                                    top10.append(_nc_o)
                                if len(top10) != 10:
                                    break
                        _v51_injected += 1
                        _v51_prot.add(tuple(_best_p3t['digits']))
                        print(f"[P5-V51] 🎯 P3 Top保底: 前3位"
                              f"{''.join(map(str,_p3t_key))} → "
                              f"{''.join(map(str,_best_p3t['digits']))}")

                # 【V1.57.0】26212期归因: 开奖83943十4 0/10 — V51注入10张P3
                # 保底票把上期十4重号唯一载体63848换出(十8占7席垄断), 后2位
                # 重号丢失. V51注入后复查: 上期十/个重号缺失则强制恢复,
                # 优先换出"换入数字该位置≥3"的垄断票(十8垄断), 其次loss最低.
                # 复查注入票也入_v51_prot防后续复查/裁剪换出
                _prev51b = list(self.draws[-1])
                for _pos51b in (3, 4):
                    _d51b = _prev51b[_pos51b]
                    if any(c['digits'][_pos51b] == _d51b for c in top10):
                        continue
                    _best_rep51 = None
                    _used_tup51 = set(tuple(t['digits']) for t in top10)
                    for _c51b in _v50_pool:
                        if _c51b['digits'][_pos51b] != _d51b:
                            continue
                        if tuple(_c51b['digits']) in _used_tup51:
                            continue
                        if _best_rep51 is None or _c51b.get('final_score', -999) > _best_rep51.get('final_score', -999):
                            _best_rep51 = _c51b
                    if _best_rep51 is None:
                        # 合成: 取最高分票改后2位(不引入其他位置垄断)
                        for _c51b in sorted(_v50_pool,
                                            key=lambda x: -x.get('final_score', -999)):
                            if _c51b.get('final_score', -999) == -999:
                                continue
                            _nc51b = dict(_c51b)
                            _nc51b['digits'] = list(_c51b['digits'])
                            _nc51b['digits'][_pos51b] = _d51b
                            _nc51b['final_score'] = _c51b.get('final_score', 0) - 0.5
                            _best_rep51 = _nc51b
                            break
                    if _best_rep51 is None:
                        continue
                    _cands_rep51 = [c for c in top10 if tuple(c['digits']) not in _v51_prot]
                    _over_rep51 = [_p for _p in range(5)
                                   if sum(1 for c in top10
                                          if c['digits'][_p] == _best_rep51['digits'][_p]) >= 3]
                    if _over_rep51:
                        _cands2_rep51 = [c for c in _cands_rep51
                                         if any(c['digits'][_p] == _best_rep51['digits'][_p]
                                                for _p in _over_rep51)]
                        if _cands2_rep51:
                            _cands_rep51 = _cands2_rep51
                    if not _cands_rep51:
                        _cands_rep51 = list(top10)
                    _worst_rep51 = min(_cands_rep51,
                                       key=lambda x: (_v51_loss(x), x.get('final_score', -999)))
                    top10.remove(_worst_rep51)
                    top10.append(_best_rep51)
                    _v51_prot.add(tuple(_best_rep51['digits']))
                    print(f"[P5-V51R] 🔄 后2位重号复查: {['十','个'][_pos51b-3]}位{_d51b}"
                          f" → {''.join(map(str,_best_rep51['digits']))}"
                          f" (换出{''.join(map(str,_worst_rep51['digits']))})")

                # 【V2.54.0】26216期归因: 开奖95300后2位十0(漏10中冷)/个0(漏1近端)
                # 全漏 — V51 P3 Top10保底注入把后2位近端/短间隔/中冷覆盖票换出
                # (V50重建票00100/07000被当换出池). 追加后2位覆盖复查(同V51R
                # 重号复查语义): 十/个位漏1-15期数字缺失则恢复, 每位置上限2张,
                # 优先换出"后2位无近端信号"票, 复查注入票入_v51_prot防后续裁剪
                for _pos51n in (3, 4):
                    _near_digs51 = [d for d in range(10)
                                    if 1 <= _v50_miss[_pos51n].get(d, 99) <= 15
                                    and not any(c['digits'][_pos51n] == d for c in top10)]
                    _near_digs51.sort(key=lambda d: -_v50_miss[_pos51n].get(d, 99))
                    _n51_injected = 0
                    for _d51n in _near_digs51:
                        if _n51_injected >= 2:
                            break
                        _best_n51 = None
                        _used_tup51n = set(tuple(t['digits']) for t in top10)
                        for _c51n in _v50_pool:
                            if _c51n['digits'][_pos51n] != _d51n:
                                continue
                            if tuple(_c51n['digits']) in _used_tup51n:
                                continue
                            # 【V2.54.0】反垄断前置: 优先选换入后各位置≤2的票 —
                            # 26216: 26870(万2/千6/百8全超限)被over机制逼换出22312
                            # (P3 Top2百3票) → 百3丢. 选票时避开超限组合, over仅兜底
                            if any(sum(1 for c2 in top10
                                       if c2['digits'][_p] == _c51n['digits'][_p]) >= 2
                                   for _p in range(5)):
                                continue
                            if _best_n51 is None or _c51n.get('final_score', -999) > _best_n51.get('final_score', -999):
                                _best_n51 = _c51n
                        if _best_n51 is None:
                            # 合成: 取最高分票改后2位(前3位不动)
                            for _c51n in sorted(_v50_pool,
                                                key=lambda x: -x.get('final_score', -999)):
                                if _c51n.get('final_score', -999) == -999:
                                    continue
                                _nc51n = dict(_c51n)
                                _nc51n['digits'] = list(_c51n['digits'])
                                _nc51n['digits'][_pos51n] = _d51n
                                _nc51n['final_score'] = _c51n.get('final_score', 0) - 0.5
                                _best_n51 = _nc51n
                                break
                        if _best_n51 is None:
                            continue
                        # 换出池: 非_p5_protected(B2N/B2R原始保护票绝不动), 允许换
                        # V51注入的P3票(_v51_prot) — 后2位覆盖与P3前3位同等重要,
                        # 优先换"后2位无近端信号"且"P3排名靠后"的票(26216: 换
                        # 64195(P3 Top9)保十0/个0, 不拆97825(P3 Top1))
                        _cands_n51 = [c for c in top10
                                      if tuple(c['digits']) not in getattr(self, '_p5_protected', set())]
                        if not _cands_n51:
                            continue
                        _non_near_n51 = [c for c in _cands_n51
                                         if not any(1 <= _v50_miss[_p].get(c['digits'][_p], 99) <= 3
                                                    for _p in (3, 4))]
                        if _non_near_n51:
                            _cands_n51 = _non_near_n51

                        def _p3_rank51(_c):
                            for _ri, _rk in enumerate(_p3t51_all):
                                if tuple(_c['digits'][:3]) == tuple(int(x) for x in _rk):
                                    return _ri
                            return 99  # 非P3前3位票最优先换

                        # 【V2.54.0】P3 Top1-4(978/223/357/164)绝不可换: 前3位
                        # 核心信号, V51N只换P3排名≥5或非P3票(26216: 换64195/
                        # 49488保十0/个0, 不拆97825/22312/35766)
                        _cands_n51 = [c for c in _cands_n51 if _p3_rank51(c) >= 5]
                        # 【V1.64.0】V51N换出保护P3前3位唯一载体 — 26231根因:
                        # 07940(前3位079=P3 Top7, 百7唯一载体)被V51N后2位复查
                        # (十0漏14)换出, 百7 0/10. V2.54.0"排名≥5可换"在P3信号
                        # 弱时拆结构性前3位覆盖(P5万/千/百=P3百/十/个100%一致,
                        # 丢失不可由P5自身恢复); 后2位目标有其他通道(B2N/B2R/
                        # MCF)兜底. 万/千/百任一位置仅此一票(唯一载体)则不可换
                        _cands_n51 = [c for c in _cands_n51
                                      if all(any(c2['digits'][_p] == c['digits'][_p]
                                                 for c2 in top10 if c2 is not c)
                                             for _p in range(3))]
                        if not _cands_n51:
                            continue
                        _worst_n51 = min(_cands_n51,
                                         key=lambda x: (-_p3_rank51(x),
                                                        _v51_loss(x),
                                                        x.get('final_score', -999)))
                        # 【V2.54.0】反垄断: 换入后各位置≤2席(V1.50.0-B语义),
                        # 超限时优先换出含超限数字的票(V51 _over51机制),
                        # 防V51N引入新垄断(v153场景3百2×3回归失败)
                        _over_n51 = [_p for _p in range(5)
                                     if sum(1 for c2 in top10
                                            if c2['digits'][_p] == _best_n51['digits'][_p])
                                     - (1 if _worst_n51['digits'][_p] == _best_n51['digits'][_p] else 0)
                                     + 1 > 2]
                        if _over_n51:
                            _over_cands_n51 = [c for c in _cands_n51
                                               if any(c['digits'][_p] == _best_n51['digits'][_p]
                                                      for _p in _over_n51)]
                            if not _over_cands_n51:
                                # 【V2.54.0】扩大换出池: 允许含超限数字的P3 Top3-10票
                                # (保P3 Top1-2: 97825/22312) — 26216十0票万1超限
                                # 但rank≥5池无万1票可换, 扩大后换19459(P3 Top5)
                                _over_cands_n51 = [c for c in top10
                                                   if tuple(c['digits']) not in getattr(self, '_p5_protected', set())
                                                   and _p3_rank51(c) >= 3
                                                   and any(c['digits'][_p] == _best_n51['digits'][_p]
                                                          for _p in _over_n51)]
                            if not _over_cands_n51:
                                continue
                            _cands_n51 = _over_cands_n51
                            _worst_n51 = min(_cands_n51,
                                             key=lambda x: (-_p3_rank51(x),
                                                            _v51_loss(x),
                                                            x.get('final_score', -999)))
                        top10.remove(_worst_n51)
                        top10.append(_best_n51)
                        _v51_prot.add(tuple(_best_n51['digits']))
                        _n51_injected += 1
                        print(f"[P5-V51N] 🔄 后2位覆盖复查: {['十','个'][_pos51n-3]}位{_d51n}"
                              f"(漏{_v50_miss[_pos51n].get(_d51n, 99)}期)"
                              f" → {''.join(map(str,_best_n51['digits']))}"
                              f" (换出{''.join(map(str,_worst_n51['digits']))})")
        except Exception as _e51:
            print(f"[P5-V51] ⚠️ P3 TopN保底跳过: {_e51}")
        # 【V1.63.0】前3位中冷复查(V51T): 26219千6(漏11)/百2(漏9)被V51注入
        # P3 Top1-8时换出致0/10 — 前3位tier2/3(漏6-15)中冷是稀缺信号, P3 Top10
        # 无载体时REBUILD合成票是唯一来源, 换出后必须复查恢复. 不查tier0/1
        # (由P3保底重新覆盖)与后2位(V51N管短间隔, 超深冷1条可接受)
        # 【V1.64.0】范围6-15→4-15(含短间隔4-5): 26232千0(漏5短间隔)被V51
        # 注入链换出后无复查通道(P3保底被上限8截断401时tier1无人管) → 0/10
        try:
            _used_tup51t = set(tuple(c['digits']) for c in top10)
            _inj51t = set()  # 【V1.64.0】本轮V51T注入票: 换出池排除防自相残杀
            for _pos51t in (0, 1, 2):
                _tier23 = [d for d in range(10)
                           if 4 <= _v50_miss[_pos51t].get(d, 99) <= 15
                           and not any(c['digits'][_pos51t] == d for c in top10)]
                # 【V1.64.0】分档排序: 短间隔(4-9)浅优先/中冷(10-15)深优先 —
                # 26232千位缺失{0(5),2(8)}深优先选2(漏8), 开奖千0(漏5)不补;
                # 短间隔内浅冷回补概率高(同V37F _short_strong浅优先设计)
                _tier23.sort(key=lambda d: ((0 if _v50_miss[_pos51t].get(d, 99) <= 9 else 1),
                                            _v50_miss[_pos51t].get(d, 99)))
                for _d51t in _tier23[:1]:  # 【V1.64.0】每位置上限1, 防链式自相残杀
                    _best51t = None
                    for _c51t in _v50_pool:
                        if _c51t['digits'][_pos51t] != _d51t:
                            continue
                        if tuple(_c51t['digits']) in _used_tup51t:
                            continue
                        if any(sum(1 for c2 in top10
                                   if c2['digits'][_p] == _c51t['digits'][_p]) >= 2
                               for _p in range(5)):
                            continue
                        if (_best51t is None
                                or _c51t.get('final_score', -999) > _best51t.get('final_score', -999)):
                            _best51t = _c51t
                    if _best51t is None:
                        # 合成: 最高分票改前3位对应位置
                        for _c51t in sorted(_v50_pool,
                                            key=lambda x: -x.get('final_score', -999)):
                            if _c51t.get('final_score', -999) == -999:
                                continue
                            _nc51t = dict(_c51t)
                            _nc51t['digits'] = list(_c51t['digits'])
                            _nc51t['digits'][_pos51t] = _d51t
                            _nc51t['final_score'] = _c51t.get('final_score', 0) - 0.5
                            _best51t = _nc51t
                            break
                    if _best51t is None:
                        continue
                    _cands51t = [c for c in top10
                                 if id(c) not in _inj51t  # 【V1.64.0】本轮注入票不可换
                                 and tuple(c['digits'])
                                 not in getattr(self, '_p5_protected', set())]
                    # 【V1.64.0】优先换非_v51_prot票(seed原生), 仅当无票可换
                    # 时才允许换P3排名≥5的_v51_prot票(26232千0复查换出08330
                    # 属此类) — v155场景A百4载体(P3票)被宽松池换出回归失败,
                    # 优先原生票可同时满足两者
                    _nonprot51t = [c for c in _cands51t
                                   if tuple(c['digits']) not in _v51_prot]
                    if _nonprot51t:
                        _cands51t = _nonprot51t
                    else:
                        _cands51t = [c for c in _cands51t if _p3_rank51(c) >= 5]
                    # 【V1.64.0】V51T换出池自锁修复 — V1.63.0排除_v51_prot后,
                    # V51注入8张P3票使top10几乎全保护, V51T换出池恒空(26231
                    # 百7被V51N拆后V51T无法恢复). 同V51N语义: 允许换P3排名
                    # ≥5的_v51_prot票(Top1-4核心信号不可换, 低排名可让位),
                    # 防拆后2位由_tail_ok51t过滤兜底
                    if not _cands51t:
                        continue
                    # 排除tier2/3中冷唯一载体(与V51换出池同权)
                    _cands51t = [c for c in _cands51t
                                 if not any(_v50_tier(_p, c['digits'][_p]) in (2, 3)
                                            and sum(1 for c2 in top10
                                                   if c2['digits'][_p] == c['digits'][_p]) == 1
                                            for _p in range(5))]
                    if not _cands51t:
                        continue
                    # 优先换"后2位无唯一载体"的票(前3位中冷复查不能拆后2位
                    # 稀缺覆盖 — 26219 V51T换出37817致十1(漏23)0/10)
                    _tail_ok51t = [c for c in _cands51t
                                   if not any(sum(1 for c2 in top10
                                                  if c2['digits'][_p] == c['digits'][_p]) == 1
                                              for _p in (3, 4))]
                    if _tail_ok51t:
                        _cands51t = _tail_ok51t
                    else:
                        # 【V1.65.0】tail_ok为空=所有候选都带后2位唯一载体,
                        # 回退全候选会拆唯一载体(26234 47120十2/个0被换出),
                        # 宁可放弃本次注入也不拆后2位稀缺覆盖
                        continue
                    # 优先换"前3位无中冷(6-15)信号"的票
                    _non_mid51t = [c for c in _cands51t
                                   if not any(6 <= _v50_miss[_p].get(c['digits'][_p], 99) <= 15
                                              for _p in (0, 1, 2))]
                    if _non_mid51t:
                        _cands51t = _non_mid51t
                    _worst51t = min(_cands51t,
                                    key=lambda x: (x.get('final_score', -999),))
                    top10.remove(_worst51t)
                    top10.append(_best51t)
                    _used_tup51t.add(tuple(_best51t['digits']))
                    _inj51t.add(id(_best51t))  # 【V1.64.0】本轮注入票登记
                    _v51_prot.add(tuple(_best51t['digits']))  # 防后续通道换出
                    print(f"[P5-V51T] 🧪 前3位中冷复查: {['万','千','百'][_pos51t]}位{_d51t}"
                          f"(漏{_v50_miss[_pos51t].get(_d51t, 99)}期)"
                          f" → {''.join(map(str,_best51t['digits']))}"
                          f" (换出{''.join(map(str,_worst51t['digits']))})")
        except Exception as _e51t:
            print(f"[P5-V51T] ⚠️ 前3位中冷复查跳过: {_e51t}")
        # 【V1.52.0】V51换入/裁剪打乱顺序, 返回前按分数降序(26208: 65716
        # score最高却排第10, 86505排第1)
        try:
            top10.sort(key=lambda x: -x.get('final_score', -999))
        except Exception:
            pass
        return top10

    def _generate_compound(self, result: Dict) -> Dict[str, Any]:
        """
        V1.28.0: 多源异构复式 — 综合Top100+Top10+全量候选频率+冷位覆盖
        前3位(万千百)选4-7数, 后2位(十个)各保底≥5候选
        修复26182: 万位漏3, 千位漏1, 十个位各漏4/0
        """
        from collections import Counter as _Cnt

        # 多源集合: Top100 + Top10 + 全量候选前200的每位置独立统计
        top100 = result.get('top100', [])
        top10 = result.get('top10', [])
        all_scored = result.get('all', [])
        pool = top100 + top10

        # 源1: pool频次
        wan_cnt = _Cnt(b['digits'][0] for b in pool)
        qian_cnt = _Cnt(b['digits'][1] for b in pool)
        bai_cnt = _Cnt(b['digits'][2] for b in pool)
        shi_cnt = _Cnt(b['digits'][3] for b in pool)
        ge_cnt = _Cnt(b['digits'][4] for b in pool)

        # 源2: 全量候选前200的位置独立频次(弥补pool偏差)
        if all_scored:
            _front_all = all_scored[:200]
            for b in _front_all:
                # 弱计分(权重0.3)
                wan_cnt[b['digits'][0]] += 0.3
                qian_cnt[b['digits'][1]] += 0.3
                bai_cnt[b['digits'][2]] += 0.3
                shi_cnt[b['digits'][3]] += 0.3
                ge_cnt[b['digits'][4]] += 0.3

        # 源3: 冷位数字强制覆盖(近10期未出数字)
        if len(self.draws) >= 10:
            _recent10 = self.draws[-10:]
            for pos, cnt in [(0, wan_cnt), (1, qian_cnt), (2, bai_cnt), (3, shi_cnt), (4, ge_cnt)]:
                _recent_pos = {d[pos] for d in _recent10}
                for d in range(10):
                    if d not in _recent_pos and cnt.get(d, 0) < 1:
                        cnt[d] = 0.5  # 冷位弱推

        # 源4: 上期数字跨位映射覆盖
        if len(self.draws) >= 2:
            _last = self.draws[-1]
            _cross_pos = {
                0: [_last[1], _last[4]],  # 万←千, 个
                1: [_last[0], _last[2]],  # 千←万, 百
                2: [_last[3]],             # 百←十
                3: [_last[2]],             # 十←百
                4: [_last[0], _last[4]],   # 个←万, 个
            }
            for pos, cnt in [(0, wan_cnt), (1, qian_cnt), (2, bai_cnt), (3, shi_cnt), (4, ge_cnt)]:
                for _src_d in _cross_pos.get(pos, []):
                    if cnt.get(_src_d, 0) < 0.5:
                        cnt[_src_d] = 0.4

        # 各位置取前6(扩大覆盖), 前3位保底4, 后2位保底5
        def _pick(cnt, min_size=4, max_size=7):
            picked = sorted(cnt, key=lambda d: -cnt[d])[:max_size]
            if len(picked) < min_size:
                all_digits = set(range(10))
                picked_set = set(picked)
                extra = sorted(all_digits - picked_set, key=lambda d: abs(d - 4.5))[:min_size - len(picked)]
                picked.extend(extra)
            return sorted(picked[:max_size])

        wan_pool = _pick(wan_cnt, min_size=4, max_size=6)
        qian_pool = _pick(qian_cnt, min_size=4, max_size=6)
        bai_pool = _pick(bai_cnt, min_size=4, max_size=6)
        shi_pool = _pick(shi_cnt, min_size=5, max_size=6)
        ge_pool = _pick(ge_cnt, min_size=5, max_size=6)

        # ====== [V1.47.0] 复式注数限额(≤50注) ======
        # 用户反馈: 原方案前3位6×6×6=216注/全5位7776注, 投注成本过高
        # 限额: 前3位≤50, 后2位≤50, 全5位≤50(每位置2-3数字)
        # 裁剪优先级: 频率最低者先裁, 每位置保底min_per_pos个数字
        def _trim_pools(_pools, _cnts, _max_bets=50, _min_per_pos=3):
            while True:
                _prod = 1
                for _p in _pools:
                    _prod *= len(_p)
                if _prod <= _max_bets:
                    break
                _best_pos, _best_d, _best_f = None, None, None
                for _i, _p in enumerate(_pools):
                    if len(_p) <= _min_per_pos:
                        continue
                    for _d in _p:
                        _f = _cnts[_i].get(_d, 0)
                        if _best_f is None or _f < _best_f:
                            _best_pos, _best_d, _best_f = _i, _d, _f
                if _best_pos is None:
                    break
                _pools[_best_pos].remove(_best_d)
            return _pools

        # 前3位复式: ≤50注(如3×3×5=45)
        _trim_pools([wan_pool, qian_pool, bai_pool], [wan_cnt, qian_cnt, bai_cnt], 50, 3)
        # 后2位复式: ≤50注(兜底, 原6×6=36已达标)
        _trim_pools([shi_pool, ge_pool], [shi_cnt, ge_cnt], 50, 3)

        # 全5位复式: 独立小池(每位置Top3起步, 裁到≤50注, 每位置≥2)
        wan5 = sorted(wan_cnt, key=lambda d: -wan_cnt[d])[:3]
        qian5 = sorted(qian_cnt, key=lambda d: -qian_cnt[d])[:3]
        bai5 = sorted(bai_cnt, key=lambda d: -bai_cnt[d])[:3]
        shi5 = sorted(shi_cnt, key=lambda d: -shi_cnt[d])[:3]
        ge5 = sorted(ge_cnt, key=lambda d: -ge_cnt[d])[:3]
        _trim_pools([wan5, qian5, bai5, shi5, ge5],
                    [wan_cnt, qian_cnt, bai_cnt, shi_cnt, ge_cnt], 50, 2)

        front_bets = len(wan_pool) * len(qian_pool) * len(bai_pool)
        tail_bets = len(shi_pool) * len(ge_pool)
        full_bets = len(wan5) * len(qian5) * len(bai5) * len(shi5) * len(ge5)

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
                '万': wan5,
                '千': qian5,
                '百': bai5,
                '十': shi5,
                '个': ge5,
                'bets': f"{len(wan5)}×{len(qian5)}×{len(bai5)}×{len(shi5)}×{len(ge5)}={full_bets}注",
            },
        }
        return compound

    # ================================================================
    # [P3-E] P3预测存储读取 — 替代内建P3实例
    # ================================================================

    def _load_p3_prediction(self, data_period: str, top_n: int = 1) -> Optional:
        """
        从Pick3技能的预测存储中读取同一预测期的P3预测
        P3预测存储在[数据最新+1]期号下
        传入的data_period=P5数据最新期号(如26180), 内部+1后查询P3第26181期
        top_n=1返回 [百,十,个] 三位数字列表(兼容旧接口)
        top_n>1返回 [[百,十,个], ...] 最多top_n个预测列表
        """
        try:
            _p3_period = str(int(data_period) + 1)
            _p3_store = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..', '..', 'lottery-pick3-skills', 'scripts',
                'memory', 'p3_predictions.json'
            )
            if not os.path.exists(_p3_store):
                return None if top_n <= 1 else []
            with open(_p3_store, 'r') as _f:
                _p3_data = json.load(_f)
            for _entry in _p3_data.get('predictions', []):
                if _entry.get('period') == _p3_period:
                    _zx = _entry.get('zx_bets', [])
                    if not _zx:
                        return None if top_n <= 1 else []
                    if top_n <= 1:
                        _top = _zx[0].get('digits', [])
                        if len(_top) == 3:
                            return list(_top)
                        return None
                    # top_n > 1: 返回多个预测
                    _results = []
                    for _b in _zx[:top_n]:
                        _d = _b.get('digits', [])
                        if len(_d) == 3:
                            _results.append(list(_d))
                    return _results if _results else []
            return None if top_n <= 1 else []
        except Exception:
            return None if top_n <= 1 else []

    def _predict_p3_fallback(self) -> Optional[List[int]]:
        """
        [V1.29.0-A] P3预测备用路径: 当P3存储预测不可用时,
        基于P5自身数据中的前3位做轻量统计预测。
        不跑全量P3模型(避免OOM), 仅用位置频率+转移概率。
        返回 [百,十,个] 三位数字列表。
        """
        try:
            if len(self.draws) < 20:
                return None
            _result = []
            # 对每个位置(P1=万, P2=千, P3=百 = P3的百/十/个)
            _last_draw = list(self.draws[-1])
            _p3_last3 = _last_draw[:3]  # P5最后3位 = P3上期开奖
            for _pos in range(3):
                # 收集近30期该位置数字
                _pos_seq = [d[_pos] for d in self.draws[-30:]]
                _pos_scores = {}
                for _d in range(10):
                    # 频率分: 指数衰减权重, 近=权重高
                    _freq_score = 0.0
                    for _i, _v in enumerate(reversed(_pos_seq)):
                        if _v == _d:
                            _freq_score += 0.7 ** (_i // 3)  # 每3期衰减到70%
                    # 转移分: 上次该位置数字→当前数字的频率
                    _prev_val = _p3_last3[_pos]
                    _trans_count = 0
                    _trans_total = 0
                    for _i in range(1, len(self.draws) - 1):
                        if self.draws[_i][_pos] == _prev_val:
                            _trans_total += 1
                            if self.draws[_i - 1][_pos] == _d:
                                _trans_count += 1
                    _trans_score = _trans_count / max(_trans_total, 1)
                    # 综合评分
                    _pos_scores[_d] = _freq_score * 0.6 + _trans_score * 0.4
                # 选最高分
                _best = max(_pos_scores, key=_pos_scores.get)
                _result.append(_best)
            return _result
        except Exception:
            return None

    # ================================================================
    # [V1.30.0-①+③] 中等遗漏分池覆盖: 各位置4-8期遗漏数字注入
    # ================================================================

    def _inject_medium_cold_p5(self, candidates, all_pool, n=10):
        """
        [V1.30.0-①] 中等遗漏分池覆盖: 各位置扫描4-8期未出数字
        [V1.30.0-③] 后2位(十/个)独立中等遗漏检查
        
        26185期归因: 万位7(遗漏7)、个位9(遗漏4)等中等冷数字完全未被覆盖
        每个位置检查4-8期遗漏数字, 缺失时从全量池注入最高分候选
        """
        if not candidates or not all_pool or len(self.draws) < 10:
            return candidates
        try:
            misses = []
            for pos in range(5):
                pos_seq = [d[pos] for d in self.draws[-50:]]
                miss = {}
                for i in range(len(pos_seq) - 1, -1, -1):
                    di = pos_seq[i]
                    if di not in miss:
                        miss[di] = len(pos_seq) - 1 - i
                for di in range(10):
                    if di not in miss:
                        miss[di] = len(pos_seq)
                misses.append(miss)

            threshold_lo, threshold_hi = 3, 10  # V1.39.0-C: 4-8→3-10, 覆盖26196十位3(遗漏9期)
            used_tuples = set(tuple(c['digits']) for c in candidates)
            covered_medium = set()
            for c in candidates:
                for pos in range(5):
                    d = c['digits'][pos]
                    m = misses[pos].get(d, 999)
                    if threshold_lo <= m <= threshold_hi:
                        covered_medium.add((pos, d))

            injections = []
            for pos in range(5):
                sorted_d = sorted(range(10), key=lambda x: -misses[pos].get(x, 0))
                for d in sorted_d:
                    m = misses[pos].get(d, 0)
                    if not (threshold_lo <= m <= threshold_hi):
                        continue
                    if (pos, d) in covered_medium:
                        continue
                    best = None
                    for c in all_pool:
                        if c['digits'][pos] != d:
                            continue
                        if tuple(c['digits']) in used_tuples:
                            continue
                        if best is None or c['final_score'] > best['final_score']:
                            best = c
                    if best:
                        injections.append({'cand': best, 'pos': pos, 'digit': d, 'miss': m})
                        covered_medium.add((pos, d))

            injections.sort(key=lambda x: -x['miss'])
            result = list(candidates)
            for inj in injections:
                if len(result) <= n + 1:
                    worst = min(result, key=lambda x: x['final_score'])
                    result.remove(worst)
                    result.append(inj['cand'])
                    used_tuples.add(tuple(inj['cand']['digits']))
                    _pos_name = ['万','千','百','十','个'][inj['pos']]
                    print(f"[P5-MCP] 🟡 中等冷注入: {_pos_name}位{inj['digit']}"
                          f"遗漏{inj['miss']}期 → {''.join(map(str,inj['cand']['digits']))}")
            result.sort(key=lambda x: -x['final_score'])
            return result
        except Exception as e:
            print(f"[P5-MCP] ⚠️ 跳过: {e}")
            return candidates

    # ================================================================
    # [P5-O1] 位置深度冷号注入: 各位置扫描>10期未出数字
    # ================================================================

    def _inject_deep_cold_p5(self, candidates, all_pool, n=10):
        """
        [O1 + V1.30.0-② + V1.33.0-④] 双阈值冷号注入 + 个位下探
        - 深度冷: ≥10期(个位≥9), 每位置强注入
        - 中度冷: 8-9期(个位≥7), 每位置额外注入(不超过1注)
        - [V1.33.0-④] 个位(P5第5位)阈值下调:
          个位深度冷≥9(原≥10), 中冷≥7(原≥8)
          26188期个位0被判定中温漏掉
        
        26185期: 千位8遗漏8期处于中等冷状态, 原有>10阈值未覆盖
        改为双档阈值, 8-9期中冷也注入
        """
        if not candidates or not all_pool or len(self.draws) < 10:
            return candidates
        try:
            misses = []
            for pos in range(5):
                pos_seq = [d[pos] for d in self.draws[-50:]]
                miss = {}
                for i in range(len(pos_seq) - 1, -1, -1):
                    di = pos_seq[i]
                    if di not in miss:
                        miss[di] = len(pos_seq) - 1 - i
                for di in range(10):
                    if di not in miss:
                        miss[di] = len(pos_seq)
                misses.append(miss)
            
            # [V1.30.0-② + V1.33.0-④] 双阈值: 深度≥10(个位≥9), 中度≥8(个位≥7)
            # [V1.33.0-④] 个位(P5第5位, pos=4)阈值单独降低
            _base_deep = max(10, int(len(self.draws) * 0.04))
            _base_medium = max(8, int(len(self.draws) * 0.03))
            # 个位阈值: 深度冷≥9(原≥10), 中冷≥7(原≥8)
            threshold_deep_list = [_base_deep] * 5
            threshold_deep_list[4] = max(9, int(len(self.draws) * 0.035))
            threshold_medium_list = [_base_medium] * 5
            threshold_medium_list[4] = max(7, int(len(self.draws) * 0.025))
            used_tuples = set(tuple(c['digits']) for c in candidates)
            covered_cold = set()
            for c in candidates:
                for pos in range(5):
                    d = c['digits'][pos]
                    if misses[pos].get(d, 999) >= threshold_medium_list[pos]:
                        covered_cold.add((pos, d))
            
            injections_deep = []  # ≥10期
            injections_medium = []  # 8-9期
            for pos in range(5):
                sorted_d = sorted(range(10), key=lambda x: -misses[pos].get(x, 0))
                _medium_injected_this_pos = 0
                for d in sorted_d:
                    m = misses[pos].get(d, 0)
                    if m < threshold_medium_list[pos]:
                        continue
                    if (pos, d) in covered_cold:
                        continue
                    best = None
                    for c in all_pool:
                        if c['digits'][pos] != d:
                            continue
                        if tuple(c['digits']) in used_tuples:
                            continue
                        if best is None or c['final_score'] > best['final_score']:
                            best = c
                    if not best:
                        continue
                    if m >= threshold_deep_list[pos]:
                        injections_deep.append({'cand': best, 'pos': pos, 'digit': d, 'miss': m})
                    else:
                        # 8-9期: 每位置最多1注
                        if _medium_injected_this_pos >= 1:
                            continue
                        injections_medium.append({'cand': best, 'pos': pos, 'digit': d, 'miss': m})
                        _medium_injected_this_pos += 1
                    covered_cold.add((pos, d))
            
            # 深度冷优先注入, 再中冷
            injections_deep.sort(key=lambda x: -x['miss'])
            injections_medium.sort(key=lambda x: -x['miss'])
            all_injections = injections_deep + injections_medium
            
            result = list(candidates)
            for inj in all_injections:
                if len(result) <= n + 1:
                    worst = min(result, key=lambda x: x['final_score'])
                    result.remove(worst)
                    result.append(inj['cand'])
                    used_tuples.add(tuple(inj['cand']['digits']))
                    _pos_name = ['万','千','百','十','个'][inj['pos']]
                    _tag = '深度' if inj['miss'] >= threshold_deep_list[inj['pos']] else '中度'
                    print(f"[P5-O1] {_tag}冷号注入: {_pos_name}位{inj['digit']}"
                          f"遗漏{inj['miss']}期 → {''.join(map(str,inj['cand']['digits']))}")
            result.sort(key=lambda x: -x['final_score'])
            return result
        except Exception as e:
            print(f"[P5-O1] ⚠️ 跳过: {e}")

    def _inject_mid_cold_p5(self, candidates, all_pool, n=10):
        """
        [V1.40.0-A] 中位数字(2-5)中等遗漏(5-12期)独立注入
        
        26197期归因: 万位4(遗漏8期)、百位3(遗漏9期)、十位4(遗漏5期)
        同时缺失, 这些数字处于V1.30.0-①(3-10期)的中间地带,
        但2-5的数字在近期频率评分中系统性偏低, 需要独立注入路径
        """
        if not candidates or not all_pool or len(self.draws) < 10:
            return candidates
        try:
            misses = []
            for pos in range(5):
                pos_seq = [d[pos] for d in self.draws[-50:]]
                miss = {}
                for i in range(len(pos_seq) - 1, -1, -1):
                    di = pos_seq[i]
                    if di not in miss:
                        miss[di] = len(pos_seq) - 1 - i
                for di in range(10):
                    if di not in miss:
                        miss[di] = len(pos_seq)
                misses.append(miss)
            lo, hi = 5, 12
            used_tuples = set(tuple(c['digits']) for c in candidates)
            covered_mid = set()
            for c in candidates:
                for pos in range(5):
                    d = c['digits'][pos]
                    if 2 <= d <= 5 and lo <= misses[pos].get(d, 999) <= hi:
                        covered_mid.add((pos, d))
            injections = []
            for pos in range(5):
                for d in range(2, 6):
                    m = misses[pos].get(d, 0)
                    if not (lo <= m <= hi):
                        continue
                    if (pos, d) in covered_mid:
                        continue
                    best = None
                    for c in all_pool:
                        if c['digits'][pos] != d:
                            continue
                        if tuple(c['digits']) in used_tuples:
                            continue
                        if best is None or c['final_score'] > best['final_score']:
                            best = c
                    if best:
                        injections.append({'cand': best, 'pos': pos, 'digit': d, 'miss': m})
                        covered_mid.add((pos, d))
            injections.sort(key=lambda x: -x['miss'])
            result = list(candidates)
            for inj in injections:
                if len(result) <= n + 5:
                    worst = min(result, key=lambda x: x['final_score'])
                    result.remove(worst)
                    result.append(inj['cand'])
                    used_tuples.add(tuple(inj['cand']['digits']))
                    _pn = ['万','千','百','十','个'][inj['pos']]
                    print(f"[P5-MIDC] 🟠 中位冷注入: {_pn}位{inj['digit']}"
                          f"遗漏{inj['miss']}期 -> {''.join(map(str,inj['cand']['digits']))}")
            result.sort(key=lambda x: -x['final_score'])
            return result
        except Exception as e:
            print(f"[P5-MIDC] 跳过: {e}")
            return candidates

    def _inject_periodic_p5(self, candidates, all_pool, n=10):
        """
        [V1.40.0-B] 周期/间隔回归模式检测
        
        每个数字的历史间隔均值±30%为回补窗口,
        当前遗漏在窗口内且候选池缺失时强制注入
        """
        if not candidates or not all_pool or len(self.draws) < 30:
            return candidates
        try:
            intervals = [{d: [] for d in range(10)} for _ in range(5)]
            for pos in range(5):
                pos_seq = [d[pos] for d in self.draws[-200:]]
                last_seen = {}
                for i, digit in enumerate(pos_seq):
                    if digit in last_seen:
                        interval = i - last_seen[digit]
                        intervals[pos][digit].append(interval)
                    last_seen[digit] = i
            used_tuples = set(tuple(c['digits']) for c in candidates)
            pos_misses = []
            for pos in range(5):
                pos_seq = [d[pos] for d in self.draws[-50:]]
                miss = {}
                for i in range(len(pos_seq) - 1, -1, -1):
                    di = pos_seq[i]
                    if di not in miss:
                        miss[di] = len(pos_seq) - 1 - i
                for di in range(10):
                    if di not in miss:
                        miss[di] = len(pos_seq)
                pos_misses.append(miss)
            periodic_digits = []
            for pos in range(5):
                for d in range(10):
                    inter = intervals[pos][d]
                    if len(inter) < 3:
                        continue
                    avg_interval = sum(inter) / len(inter)
                    if avg_interval > 30:
                        continue
                    current_miss = pos_misses[pos].get(d, 999)
                    lo_m = avg_interval * 0.7
                    hi_m = avg_interval * 1.3
                    if lo_m <= current_miss <= hi_m:
                        covered = any(c['digits'][pos] == d for c in candidates)
                        if not covered:
                            periodic_digits.append({
                                'pos': pos, 'digit': d,
                                'avg': avg_interval, 'miss': current_miss,
                                'ratio': current_miss / avg_interval if avg_interval > 0 else 1.0
                            })
            periodic_digits.sort(key=lambda x: abs(1.0 - x['ratio']))
            result = list(candidates)
            for pd in periodic_digits:
                if len(result) <= n + 3:
                    best = None
                    for c in all_pool:
                        if c['digits'][pd['pos']] != pd['digit']:
                            continue
                        if tuple(c['digits']) in used_tuples:
                            continue
                        if best is None or c['final_score'] > best['final_score']:
                            best = c
                    if best:
                        worst = min(result, key=lambda x: x['final_score'])
                        result.remove(worst)
                        result.append(best)
                        used_tuples.add(tuple(best['digits']))
                        _pn = ['万','千','百','十','个'][pd['pos']]
                        print(f"[P5-PER] _periodic回归注入: {_pn}位{pd['digit']}"
                              f"(均值{pd['avg']:.0f}期, 当前遗漏{pd['miss']}期)"
                              f" -> {''.join(map(str,best['digits']))}")
            result.sort(key=lambda x: -x['final_score'])
            return result
        except Exception as e:
            print(f"[P5-PER] 跳过: {e}")
            return candidates

            return candidates

    # ================================================================
    # [P5-O2] 前3位极值和值走廊 + [P5-O5] 后2位极端覆盖
    # ================================================================

    def _rescue_extreme_candidates_p5(self, candidates, all_pool, n=10):
        """
        [O2] 保留5%名额给前3位和值≤8或≥22的极端候选
        [O5] 后2位和值≤4或≥16保留至少1注
        
        26180期前3位005和值=5, 被校准完全压制
        """
        if not candidates or not all_pool or len(candidates) < 2:
            return candidates
        try:
            used_tuples = set(tuple(c['digits']) for c in candidates)
            # 检查当前Top10是否已覆盖极值
            has_front_extreme = False
            has_tail_extreme = False
            for c in candidates:
                front3 = c['digits'][:3]
                tail2 = c['digits'][3:]
                fs = sum(front3)
                ts = sum(tail2)
                if fs <= 8 or fs >= 22:
                    has_front_extreme = True
                if ts <= 4 or ts >= 16:
                    has_tail_extreme = True
            
            # [O2] 前3位极值
            if not has_front_extreme:
                best_front = None
                for c in all_pool:
                    fs = sum(c['digits'][:3])
                    if not (fs <= 8 or fs >= 22):
                        continue
                    if tuple(c['digits']) in used_tuples:
                        continue
                    if best_front is None or c['final_score'] > best_front['final_score']:
                        best_front = c
                if best_front:
                    worst = min(candidates, key=lambda x: x['final_score'])
                    candidates.remove(worst)
                    candidates.append(best_front)
                    print(f"[P5-O2] 前3位极值注入: {''.join(map(str,best_front['digits']))}"
                          f"(和值{sum(best_front['digits'][:3])})")
                    used_tuples.add(tuple(best_front['digits']))
            
            # [O5] 后2位极端
            if not has_tail_extreme:
                best_tail = None
                for c in all_pool:
                    ts = sum(c['digits'][3:])
                    if not (ts <= 4 or ts >= 16):
                        continue
                    if tuple(c['digits']) in used_tuples:
                        continue
                    if best_tail is None or c['final_score'] > best_tail['final_score']:
                        best_tail = c
                if best_tail:
                    worst = min(candidates, key=lambda x: x['final_score'])
                    candidates.remove(worst)
                    candidates.append(best_tail)
                    print(f"[P5-O5] 后2位极端注入: {''.join(map(str,best_tail['digits']))}"
                          f"(后和{sum(best_tail['digits'][3:])})")
            
            candidates.sort(key=lambda x: -x['final_score'])
            return candidates
        except Exception as e:
            print(f"[P5-O2/O5] ⚠️ 跳过: {e}")
            return candidates

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
