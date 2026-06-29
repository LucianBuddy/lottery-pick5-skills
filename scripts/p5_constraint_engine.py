#!/usr/bin/env python3
"""
排列5 (Pick5) 约束引擎 v1.0
排列5: 万/千/百/十/个 五位，每位0-9
"""

from typing import List, Tuple, Optional


def validate_hard(digits: List[int]) -> Tuple[bool, str]:
    if len(digits) != 5:
        return False, f"位数错误({len(digits)})"
    for d in digits:
        if d < 0 or d > 9:
            return False, f"数字越界({d})"
    return True, "ok"


def validate_sum(digits: List[int], sum_range: Tuple[int, int] = (5, 40)) -> bool:
    return sum_range[0] <= sum(digits) <= sum_range[1]


def validate_parity(digits: List[int], odd_min: int = 1, odd_max: int = 4) -> bool:
    odd = sum(1 for d in digits if d % 2 == 1)
    return odd_min <= odd <= odd_max


def validate_span(digits: List[int], span_min: int = 2) -> bool:
    return max(digits) - min(digits) >= span_min


def validate_consecutive(digits: List[int], max_consec: int = 3) -> bool:
    consec = sum(1 for i in range(len(digits)-1) if digits[i+1] == digits[i])
    return consec <= max_consec


class P5ConstraintEngine:
    """排列5约束引擎 — 基于排列3约束引擎改编"""

    @staticmethod
    def validate_hard(digits: List[int]) -> Tuple[bool, str]:
        return validate_hard(digits)

    @staticmethod
    def validate_strategy(digits: List[int], strategy_type: int) -> Tuple[bool, str]:
        s = sum(digits)
        odd = sum(1 for d in digits if d % 2 == 1)
        sp = max(digits) - min(digits)

        if strategy_type == 1:  # 稳中求胜
            ok = (15 <= s <= 30) and (2 <= odd <= 3) and (sp >= 3)
        elif strategy_type == 2:  # 平衡配置
            ok = (10 <= s <= 35) and (1 <= odd <= 4) and (sp >= 2)
        elif strategy_type == 3:  # 高和值激进
            ok = (25 <= s <= 40) and (sp >= 5)
        elif strategy_type == 4:  # 低和值保守
            ok = (5 <= s <= 20) and (odd <= 2)
        elif strategy_type == 5:  # 重复偏好
            ok = len(set(digits)) <= 3
        else:
            ok = True
        return ok, "" if ok else "策略未通过"
