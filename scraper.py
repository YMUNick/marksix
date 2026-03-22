#!/usr/bin/env python3
"""
香港六合彩資料爬蟲 (Mark Six Scraper)
=====================================
爬取 lottery.hk 的歷史開獎資料 (2013年至今)

使用方式:
    python3 scraper.py              # 爬取所有歷史資料
    python3 scraper.py --year 2024  # 只爬取2024年
    python3 scraper.py --update     # 只更新最新資料

輸出: data/marksix_data.json
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
import argparse
from datetime import datetime

# ============================================================
# Configuration
# ============================================================
BASE_URL = "https://lottery.hk/en/mark-six/results"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
OUTPUT_FILE = os.path.join(DATA_DIR, 'marksix_raw.json')
DELAY = 1.5  # seconds between requests (be polite)


# ============================================================
# Scraper Functions
# ============================================================
def scrape_year(year: int) -> list:
    """Scrape all Mark Six results for a given year."""
    url = f"{BASE_URL}/{year}"
    print(f"  📡 Fetching {url}...")
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  ❌ Error fetching {year}: {e}")
        return []
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    draws = []
    
    # Parse the results table - adapt selectors to lottery.hk's structure
    # This is a template - you may need to adjust CSS selectors based on actual HTML
    rows = soup.select('table.results-table tbody tr, .draw-result, .result-row')
    
    for row in rows:
        try:
            # Try to extract date
            date_el = row.select_one('.date, td:first-child, .draw-date')
            if not date_el:
                continue
            
            date_text = date_el.get_text(strip=True)
            
            # Try to extract numbers
            number_els = row.select('.ball, .number, td.numbers span')
            if len(number_els) < 7:
                continue
            
            numbers = []
            for el in number_els[:6]:
                try:
                    numbers.append(int(el.get_text(strip=True)))
                except ValueError:
                    continue
            
            if len(numbers) != 6:
                continue
            
            # Special number is usually the 7th
            try:
                special = int(number_els[6].get_text(strip=True))
            except (IndexError, ValueError):
                special = None
            
            # Parse date
            try:
                draw_date = datetime.strptime(date_text, "%d/%m/%Y")
            except ValueError:
                try:
                    draw_date = datetime.strptime(date_text, "%Y-%m-%d")
                except ValueError:
                    continue
            
            draws.append({
                "draw_date": draw_date.strftime("%Y-%m-%d"),
                "day_of_week": draw_date.strftime("%A"),
                "numbers": sorted(numbers),
                "special_number": special
            })
            
        except Exception as e:
            print(f"  ⚠️ Error parsing row: {e}")
            continue
    
    print(f"  ✅ Found {len(draws)} draws for {year}")
    return draws


def scrape_all(start_year=2013, end_year=None):
    """Scrape all years from start_year to current year."""
    if end_year is None:
        end_year = datetime.now().year
    
    all_draws = []
    
    for year in range(start_year, end_year + 1):
        draws = scrape_year(year)
        all_draws.extend(draws)
        time.sleep(DELAY)
    
    # De-duplicate by date
    seen = set()
    unique_draws = []
    for d in all_draws:
        key = d['draw_date']
        if key not in seen:
            seen.add(key)
            unique_draws.append(d)
    
    # Sort by date
    unique_draws.sort(key=lambda x: x['draw_date'])
    
    # Assign draw IDs
    for i, d in enumerate(unique_draws):
        year = d['draw_date'][:4]
        year_short = d['draw_date'][2:4]
        year_draws = [dd for dd in unique_draws[:i+1] if dd['draw_date'].startswith(year)]
        d['draw_id'] = f"{year_short}/{len(year_draws):03d}"
    
    return unique_draws


def load_existing():
    """Load existing scraped data."""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_draws(draws):
    """Save draws to JSON file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(draws, f, ensure_ascii=False, indent=2)
    print(f"💾 Saved {len(draws)} draws to {OUTPUT_FILE}")


# ============================================================
# Alternative: Use HKJC API (if available)
# ============================================================
def scrape_hkjc_api(count=200):
    """
    Alternative scraper using the HKJC-style API endpoint.
    Some third-party APIs provide Mark Six data in JSON format.
    """
    # Example API endpoint (may change - check current availability)
    api_url = "https://bet.hkjc.com/marksix/getJSON.aspx"
    
    try:
        resp = requests.get(api_url, params={"sd": "20130101", "ed": "20260322"}, 
                          headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            draws = []
            for item in data:
                nums = [int(n.strip()) for n in item.get('no', '').split('+')[0].split(',')]
                special = int(item.get('sno', item.get('no', '').split('+')[-1]).strip())
                draws.append({
                    "draw_date": item.get('date', ''),
                    "numbers": sorted(nums[:6]),
                    "special_number": special
                })
            return draws
    except Exception as e:
        print(f"  ⚠️ HKJC API not available: {e}")
    
    return None


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='香港六合彩資料爬蟲')
    parser.add_argument('--year', type=int, help='只爬取特定年份')
    parser.add_argument('--update', action='store_true', help='只更新最新資料')
    parser.add_argument('--start', type=int, default=2013, help='起始年份 (預設: 2013)')
    args = parser.parse_args()
    
    print("🎲 香港六合彩資料爬蟲 (Mark Six Scraper)")
    print("=" * 50)
    
    if args.year:
        draws = scrape_year(args.year)
        save_draws(draws)
    elif args.update:
        existing = load_existing()
        current_year = datetime.now().year
        new_draws = scrape_year(current_year)
        
        existing_dates = {d['draw_date'] for d in existing}
        added = [d for d in new_draws if d['draw_date'] not in existing_dates]
        
        if added:
            all_draws = existing + added
            all_draws.sort(key=lambda x: x['draw_date'])
            save_draws(all_draws)
            print(f"🆕 Added {len(added)} new draws")
        else:
            print("ℹ️ No new draws found")
    else:
        draws = scrape_all(start_year=args.start)
        save_draws(draws)
    
    print("\n✅ Done! Run `python3 scripts/generate_data.py` to compute stats & predictions.")


if __name__ == "__main__":
    main()
