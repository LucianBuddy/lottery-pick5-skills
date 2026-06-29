#!/usr/bin/env python3
"""
排列5 (Pick5) 历史数据自动更新器 v1.0
数据源: 体彩数据API (webapi.sporttery.cn) — gameNo=37 是排列5
"""

import os, sys, json, re, urllib.request, ssl
from pathlib import Path
from typing import List, Tuple, Optional
import pandas as pd

SKILL_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = SKILL_DIR / 'assets' / 'data' / '排列5历史数据.xlsx'

API_URL = 'https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry'


def _build_url(page_no: int = 1, page_size: int = 30) -> str:
    return (f'{API_URL}?gameNo=37&provinceId=0&pageSize={page_size}'
            f'&isPc=true&pageNo={page_no}')


def _http_get(url: str, timeout: int = 15) -> str:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.lottery.gov.cn/',
    })
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='replace')




def fetch_draws_500com() -> List[dict]:
    """500彩票网备用数据源 — 排列5历史页面"""
    url = 'https://datachart.500.com/plw/history/inc/history.php'
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=15) as resp:
            html = resp.read().decode('gb2312', errors='replace')
        results = []
        row_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL)
        for row in row_pattern.finditer(html):
            tds = re.findall(r'<td[^>]*>([^<]+)</td>', row.group(1))
            clean = [t.strip() for t in tds if t.strip()]
            if len(clean) >= 6 and clean[1].isdigit():
                nums = clean[2].split()
                if len(nums) == 5:
                    try:
                        results.append({
                            '期号': int(clean[1]),
                            '万位': int(nums[0]),
                            '千位': int(nums[1]),
                            '百位': int(nums[2]),
                            '十位': int(nums[3]),
                            '个位': int(nums[4]),
                        })
                    except (ValueError, IndexError):
                        continue
        results.sort(key=lambda x: x['期号'])
        print(f"[P5-Updater] 500彩票网获取到 {len(results)} 期 ({results[0]['期号']}~{results[-1]['期号']})")
        return results
    except Exception as e:
        print(f"[P5-Updater] 500彩票网失败: {e}")
        return []


# ——— 主要获取逻辑 ———

def fetch_draws(page_no: int = 1, page_size: int = 50) -> List[dict]:
    url = _build_url(page_no, page_size)
    try:
        raw = _http_get(url)
        data = json.loads(raw)
        if not data.get('success'):
            return []
        draw_list = data.get('value', {}).get('list', [])
        results = []
        for draw in draw_list:
            draw_num = draw.get('lotteryDrawNum', '')
            draw_result = draw.get('lotteryDrawResult', '')
            if not draw_num or not draw_result:
                continue
            nums = re.split(r'[\s,]+', draw_result.strip())
            if len(nums) != 5:
                continue
            try:
                results.append({
                    '期号': int(draw_num),
                    '万位': int(nums[0]),
                    '千位': int(nums[1]),
                    '百位': int(nums[2]),
                    '十位': int(nums[3]),
                    '个位': int(nums[4]),
                })
            except (ValueError, IndexError):
                continue
        return results
    except Exception as e:
        print(f"[P5-Updater] API失败: {e}")
        return []


def get_last_period() -> int:
    if not DATA_PATH.exists():
        return 0
    try:
        df = pd.read_excel(str(DATA_PATH), engine='openpyxl')
        return int(df['期号'].iloc[-1])
    except Exception:
        return 0


def get_total() -> int:
    if not DATA_PATH.exists():
        return 0
    try:
        df = pd.read_excel(str(DATA_PATH), engine='openpyxl')
        return len(df)
    except Exception:
        return 0


def append_draws(new_draws: List[dict]) -> int:
    if not new_draws:
        return 0
    cols = ['期号', '万位', '千位', '百位', '十位', '个位']
    new_df = pd.DataFrame(new_draws)
    for c in cols:
        if c not in new_df.columns:
            new_df[c] = 0
    new_df = new_df[cols]
    if DATA_PATH.exists():
        existing = pd.read_excel(str(DATA_PATH), engine='openpyxl')
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df
    combined = combined.drop_duplicates(subset=['期号'], keep='last')
    combined = combined.sort_values('期号').reset_index(drop=True)
    combined.to_excel(str(DATA_PATH), index=False)
    return len(new_draws)


def check_and_update() -> dict:
    last = get_last_period()
    all_draws = []
    page = 1
    while page <= 5:
        draws = fetch_draws(page_no=page, page_size=50)
        if not draws:
            break
        all_draws.extend(draws)
        if draws and draws[-1]['期号'] <= last:
            break
        page += 1
    new_draws = [d for d in all_draws if d['期号'] > last]
    new_draws.sort(key=lambda x: x['期号'])

    if not new_draws:
        print(f"[P5-Updater] ⚠️ 体彩API无数据，尝试500彩票网...")
        all_draws = fetch_draws_500com()
        new_draws = [d for d in all_draws if d["期号"] > last]
        new_draws.sort(key=lambda x: x["期号"])

    if new_draws:
        append_draws(new_draws)
        print(f"[P5-Updater] 同步: +{len(new_draws)}期 ({new_draws[0]['期号']}~{new_draws[-1]['期号']})")
        return {'updated': True, 'new_count': len(new_draws), 'last_period': new_draws[-1]['期号']}
    print(f"[P5-Updater] 已最新 (期号={last})")
    return {'updated': False, 'new_count': 0, 'last_period': last}


if __name__ == '__main__':
    result = check_and_update()
    print(json.dumps(result, ensure_ascii=False, indent=2))
