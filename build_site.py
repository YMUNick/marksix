#!/usr/bin/env python3
"""
========================================================
香港六合彩完整資料爬蟲 + 網站自動產生器
Mark Six Full Scraper & Site Builder
========================================================

功能：
1. 從 lottery.hk 爬取 2013-2026 所有開獎資料
2. 計算統計數據（頻率、奇偶、大小、熱冷、熱力圖）
3. 運行3種AI預測模型
4. 自動產生完整 index.html（嵌入所有資料）

使用方式：
  pip install requests beautifulsoup4
  python3 build_site.py

輸出：
  index.html（可直接部署到 GitHub Pages）
========================================================
"""

import requests
from bs4 import BeautifulSoup
import json, re, math, time, sys, os
from collections import Counter
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
BASE_URL = "https://lottery.hk/en/mark-six/results"

# ============================================================
# 1. SCRAPER
# ============================================================
def scrape_year(year):
    """Scrape all Mark Six results for a given year from lottery.hk"""
    url = f"{BASE_URL}/{year}"
    print(f"  📡 Fetching {year}...", end=" ", flush=True)
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Error: {e}")
        return []
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    draws = []
    
    # Find all table rows with draw data
    rows = soup.select('table tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue
        
        # Extract draw number
        draw_num_el = cells[0].get_text(strip=True)
        if '/' not in draw_num_el:
            continue
        
        # Extract date
        date_text = cells[1].get_text(strip=True)
        try:
            # Format: DD/MM/YYYY
            dt = datetime.strptime(date_text, "%d/%m/%Y")
            date_str = dt.strftime("%Y-%m-%d")
        except:
            continue
        
        # Extract numbers - find all list items or spans with numbers
        ball_els = cells[2].find_all('li') or cells[2].find_all('span')
        if not ball_els:
            # Try getting text directly
            nums_text = cells[2].get_text(strip=True)
            nums_match = re.findall(r'\d+', nums_text)
            if len(nums_match) >= 7:
                all_nums = [int(n) for n in nums_match[:7]]
            else:
                continue
        else:
            all_nums = []
            for el in ball_els:
                try:
                    all_nums.append(int(el.get_text(strip=True)))
                except:
                    continue
        
        if len(all_nums) < 7:
            continue
        
        # First 6 are main numbers, 7th is special
        main_nums = sorted(all_nums[:6])
        special = all_nums[6]
        
        draws.append({
            "draw_id": draw_num_el,
            "draw_date": date_str,
            "numbers": main_nums,
            "special_number": special
        })
    
    print(f"✅ {len(draws)} draws")
    return draws

def scrape_all(start_year=2013, end_year=2026):
    """Scrape all years"""
    print("🎲 開始爬取香港六合彩歷史資料...")
    print("=" * 50)
    
    all_draws = []
    for year in range(start_year, end_year + 1):
        draws = scrape_year(year)
        all_draws.extend(draws)
        time.sleep(1)  # Be polite
    
    # De-duplicate and sort
    seen = set()
    unique = []
    for d in all_draws:
        key = d['draw_date'] + str(d['numbers'])
        if key not in seen:
            seen.add(key)
            unique.append(d)
    
    unique.sort(key=lambda x: x['draw_date'])
    print(f"\n✅ 總共爬取 {len(unique)} 期資料")
    return unique

# ============================================================
# 2. STATISTICS
# ============================================================
def compute_stats(draws):
    """Compute all statistics"""
    total = len(draws)
    
    # Frequency
    freq = Counter()
    for d in draws:
        for n in d['numbers']:
            freq[n] += 1
    frequency = {str(n): freq.get(n, 0) for n in range(1, 50)}
    
    # Odd/Even
    odd = sum(1 for d in draws for n in d['numbers'] if n % 2 == 1)
    even = total * 6 - odd
    
    # High/Low
    low = sum(1 for d in draws for n in d['numbers'] if n <= 24)
    high = total * 6 - low
    
    # Hot/Cold (recent 20)
    r20 = draws[-20:]
    r20freq = Counter()
    for d in r20:
        for n in d['numbers']:
            r20freq[n] += 1
    hot_cold = sorted(
        [{"number": n, "count": r20freq.get(n, 0)} for n in range(1, 50)],
        key=lambda x: -x['count']
    )
    
    # Heatmap
    mx = max(freq.values()) if freq else 1
    heatmap = [{"number": n, "frequency": freq.get(n, 0), "intensity": round(freq.get(n, 0) / mx, 3)} for n in range(1, 50)]
    
    return {
        "frequency": frequency,
        "odd_even": {"odd": odd, "even": even},
        "high_low": {"low": low, "high": high},
        "hot_cold_20": hot_cold,
        "heatmap": heatmap
    }

# ============================================================
# 3. AI PREDICTIONS
# ============================================================
def predict_hot_cold(draws):
    total = len(draws)
    all_freq = Counter()
    r20_freq = Counter()
    for d in draws:
        for n in d['numbers']: all_freq[n] += 1
    for d in draws[-20:]:
        for n in d['numbers']: r20_freq[n] += 1
    
    ranked = sorted(range(1, 50), key=lambda x: all_freq.get(x, 0), reverse=True)
    hot, med, cold = ranked[:16], ranked[16:33], ranked[33:]
    
    def sc(n): return all_freq.get(n, 0) * 0.4 + r20_freq.get(n, 0) * 10 * 0.6
    picked = sorted(sorted(hot, key=sc, reverse=True)[:3] + sorted(med, key=sc, reverse=True)[:2] + sorted(cold, key=sc, reverse=True)[:1])
    
    conf, expl = {}, {}
    for n in picked:
        cat = "熱號 (Hot)" if n in hot else ("中間 (Medium)" if n in med else "冷號 (Cold)")
        rc = r20_freq.get(n, 0)
        c = min(0.85, 0.5 + rc * 0.05) if n in hot else (min(0.7, 0.4 + rc * 0.04) if n in med else min(0.55, 0.3 + rc * 0.03))
        conf[str(n)] = round(c, 2)
        expl[str(n)] = f"分類：{cat}｜歷史出現 {all_freq[n]} 次 ({round(all_freq[n]/total*100,1)}%)｜近20期出現 {rc} 次"
    
    return {"model": "頻率加權模型 (Hot/Cold Frequency)", "model_id": "frequency_weighted",
            "description": "基於歷史頻率分類，選取3個熱號 + 2個中間號 + 1個冷號",
            "numbers": picked, "confidence": conf, "explanations": expl,
            "avg_confidence": round(sum(conf.values()) / len(conf), 2)}

def predict_trend(draws):
    r20 = draws[-20:]
    weighted = {n: 0 for n in range(1, 50)}
    for i, d in enumerate(r20):
        w = math.exp(0.1 * (i - 19))
        for n in d['numbers']: weighted[n] += w
    
    first, second = draws[-20:-10], draws[-10:]
    trend = {}
    for n in range(1, 50):
        f1 = sum(1 for d in first for x in d['numbers'] if x == n)
        f2 = sum(1 for d in second for x in d['numbers'] if x == n)
        trend[n] = f2 - f1
    
    combined = {n: weighted[n] * 0.7 + max(0, trend[n]) * 0.5 for n in range(1, 50)}
    picked = sorted(sorted(range(1, 50), key=lambda x: combined[x], reverse=True)[:6])
    
    conf, expl = {}, {}
    for n in picked:
        td = "上升 ↑" if trend[n] > 0 else ("持平 →" if trend[n] == 0 else "下降 ↓")
        c = round(max(0.3, min(0.9, 0.4 + combined[n] * 0.05)), 2)
        f1 = sum(1 for d in first for x in d['numbers'] if x == n)
        f2 = sum(1 for d in second for x in d['numbers'] if x == n)
        conf[str(n)] = c
        expl[str(n)] = f"趨勢：{td}｜前10期出現 {f1} 次 → 後10期出現 {f2} 次｜加權分數 {round(combined[n],2)}"
    
    return {"model": "近期趨勢模型 (Recent Trend)", "model_id": "trend",
            "description": "分析最近20期趨勢，使用指數加權平均，偏好上升趨勢號碼",
            "numbers": picked, "confidence": conf, "explanations": expl,
            "avg_confidence": round(sum(conf.values()) / len(conf), 2)}

def predict_ml(draws):
    total = len(draws)
    all_freq = Counter()
    r50_freq = Counter()
    for d in draws:
        for n in d['numbers']: all_freq[n] += 1
    for d in draws[-50:]:
        for n in d['numbers']: r50_freq[n] += 1
    
    last_seen = {}
    for i, d in enumerate(draws):
        for n in d['numbers']: last_seen[n] = i
    gaps = {n: total - 1 - last_seen.get(n, 0) for n in range(1, 50)}
    
    scores = {}
    for n in range(1, 50):
        fh = all_freq.get(n, 0) / total
        fr = r50_freq.get(n, 0) / 50
        avg_gap = total / max(all_freq.get(n, 0), 1)
        fg = min(2.0, gaps[n] / max(avg_gap, 1))
        scores[n] = fh * 0.25 + fr * 0.35 + fg * 0.15 * 0.3 + 0.1
    
    ranked = sorted(range(1, 50), key=lambda x: scores[x], reverse=True)
    picked, oc, ec, lc, hc = [], 0, 0, 0, 0
    for n in ranked:
        if len(picked) >= 6: break
        io, ih = n % 2 == 1, n > 24
        if io and oc >= 4: continue
        if not io and ec >= 4: continue
        if ih and hc >= 4: continue
        if not ih and lc >= 4: continue
        picked.append(n)
        if io: oc += 1
        else: ec += 1
        if ih: hc += 1
        else: lc += 1
    picked.sort()
    
    conf, expl = {}, {}
    for n in picked:
        c = round(max(0.35, min(0.88, scores[n] * 3 + 0.3)), 2)
        conf[str(n)] = c
        expl[str(n)] = f"歷史頻率 {round(all_freq.get(n,0)/total*100,1)}%｜近50期出現 {r50_freq.get(n,0)} 次｜間隔 {gaps[n]} 期｜綜合分數 {round(scores[n],3)}"
    
    return {"model": "集成學習模型 (ML Ensemble)", "model_id": "ml_ensemble",
            "description": "結合歷史頻率、近期趨勢、間隔分析與奇偶平衡的多特徵集成模型",
            "numbers": picked, "confidence": conf, "explanations": expl,
            "avg_confidence": round(sum(conf.values()) / len(conf), 2)}

# ============================================================
# 4. BUILD SITE
# ============================================================
def build_site(draws):
    """Build the complete index.html with embedded data"""
    print("\n📊 計算統計數據...")
    stats = compute_stats(draws)
    
    print("🤖 運行AI預測模型...")
    p1 = predict_hot_cold(draws)
    p2 = predict_trend(draws)
    p3 = predict_ml(draws)
    
    data = {
        "meta": {
            "total_draws": len(draws),
            "date_range": f"{draws[0]['draw_date']} ~ {draws[-1]['draw_date']}",
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "data_source": "Hong Kong Mark Six (六合彩) via lottery.hk"
        },
        "recent_10": draws[-10:],
        "recent_20": draws[-20:],
        "stats": stats,
        "predictions": {
            "models": [p1, p2, p3],
            "disclaimer": "⚠️ 六合彩為隨機抽獎，任何統計預測均不保證中獎。本系統僅供娛樂參考。"
        }
    }
    
    # Save raw data
    with open('marksix_all_draws.json', 'w', encoding='utf-8') as f:
        json.dump(draws, f, ensure_ascii=False, indent=2)
    print(f"💾 完整資料已儲存至 marksix_all_draws.json ({len(draws)} 期)")
    
    # Read the template HTML and replace data
    data_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    
    # Check if index.html exists as template
    if os.path.exists('index.html'):
        with open('index.html', 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Replace the DATA variable
        html = re.sub(r'var DATA=\{.*?\};', f'var DATA={data_json};', html, count=1, flags=re.DOTALL)
        
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ index.html 已更新！({len(draws)} 期資料已嵌入)")
    else:
        # Save just the data
        with open('marksix_compact.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        print(f"💾 精簡資料已儲存至 marksix_compact.json")
        print("⚠️ 找不到 index.html 模板，請手動將 DATA 替換到 HTML 中")
        print(f"   DATA JSON 大小：{len(data_json)} bytes")
    
    # Print summary
    print("\n" + "=" * 50)
    print("📈 資料摘要：")
    print(f"   期數範圍：{data['meta']['date_range']}")
    print(f"   總期數：{data['meta']['total_draws']}")
    print(f"   最新一期：{draws[-1]['draw_id']} ({draws[-1]['draw_date']})")
    print(f"   號碼：{draws[-1]['numbers']} + {draws[-1]['special_number']}")
    print(f"\n🤖 AI預測：")
    print(f"   模型1（頻率加權）：{p1['numbers']}")
    print(f"   模型2（趨勢）：{p2['numbers']}")
    print(f"   模型3（集成）：{p3['numbers']}")
    print("=" * 50)

# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    draws = scrape_all(2013, 2026)
    
    if len(draws) == 0:
        print("❌ 沒有爬取到任何資料，請檢查網路連線。")
        sys.exit(1)
    
    build_site(draws)
    
    print("\n🚀 完成！")
    print("   1. 確認 index.html 已更新")
    print("   2. git add . && git commit -m 'update data' && git push")
    print("   3. 等待 1-2 分鐘，訪問你的 GitHub Pages 網站")
