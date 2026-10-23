#!/usr/bin/env python3
"""
build_site.py 的規則與邊界測試

執行：python3 -m unittest discover -s tests -v
"""

import json, os, random, sys, tempfile, unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import build_site as bs

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'marksix_all_draws.json')


def make_draw(draw_id, date, numbers, special):
    return {"draw_id": draw_id, "draw_date": date, "day_of_week": "Tuesday",
            "numbers": sorted(numbers, key=str) if any(type(n) is not int for n in numbers) else sorted(numbers),
            "special_number": special}


def random_draws(n, seed=0):
    """產生 n 期符合規則的假資料（7 個不重複號碼，1-49）"""
    rng = random.Random(seed)
    draws = []
    for i in range(n):
        balls = rng.sample(range(1, 50), 7)
        day = 1 + i % 28
        month = 1 + (i // 28) % 12
        draws.append(make_draw(f"24/{i + 1:03d}", f"2024-{month:02d}-{day:02d}", balls[:6], balls[6]))
    return draws


def fake_page(rows):
    """模擬 lottery.hk 的結果頁"""
    trs = []
    for draw_id, date, balls in rows:
        lis = ''.join(f'<li>{b}</li>' for b in balls)
        trs.append(f'<tr><td>{draw_id}</td><td>{date}</td><td><ul>{lis}</ul></td></tr>')
    return '<table><tr><th>Draw</th><th>Date</th><th>Numbers</th></tr>' + ''.join(trs) + '</table>'


class FakeResp:
    def __init__(self, text):
        self.text = text
    def raise_for_status(self):
        pass


# ============================================================
# 規則驗證
# ============================================================
class TestValidateDraw(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(bs.is_valid_draw(make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 49], 25)))

    def test_rejects_rule_violations(self):
        cases = {
            "只有5個號碼": make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5], 25),
            "7個主號碼": make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 6, 7], 25),
            "主號碼重複": make_draw("26/001", "2026-01-02", [1, 1, 3, 4, 5, 6], 25),
            "號碼0": make_draw("26/001", "2026-01-02", [0, 2, 3, 4, 5, 6], 25),
            "號碼50": make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 50], 25),
            "特別號與主號重複": make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 6], 6),
            "特別號超出範圍": make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 6], 50),
            "特別號缺失": make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 6], None),
            "期號格式錯誤": make_draw("<b>x</b>/1", "2026-01-02", [1, 2, 3, 4, 5, 6], 7),
            "期號年份與日期不符": make_draw("25/001", "2026-01-02", [1, 2, 3, 4, 5, 6], 7),
            "日期格式錯誤": make_draw("26/001", "2026/01/02", [1, 2, 3, 4, 5, 6], 7),
            "非整數號碼": make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, "6"], 7),
            "布林值號碼": make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, True], 7),
        }
        for name, d in cases.items():
            with self.subTest(name):
                self.assertFalse(bs.is_valid_draw(d))

    def test_existing_data_follows_rules(self):
        with open(DATA_FILE, encoding='utf-8') as f:
            draws = json.load(f)
        self.assertGreater(len(draws), 0)
        self.assertEqual([d for d in draws if not bs.is_valid_draw(d)], [])
        ids = [d['draw_id'] for d in draws]
        self.assertEqual(len(ids), len(set(ids)), "期號不可重複")


# ============================================================
# 爬蟲解析
# ============================================================
class TestScrapeYear(unittest.TestCase):
    def scrape(self, rows):
        with mock.patch.object(bs.requests, 'get', return_value=FakeResp(fake_page(rows))):
            return bs.scrape_year(2026)

    def test_parses_valid_row(self):
        draws = self.scrape([("26/001", "02/01/2026", [9, 3, 15, 22, 41, 48, 7])])
        self.assertEqual(len(draws), 1)
        self.assertEqual(draws[0]['numbers'], [3, 9, 15, 22, 41, 48])
        self.assertEqual(draws[0]['special_number'], 7)
        self.assertEqual(draws[0]['draw_date'], "2026-01-02")
        self.assertEqual(draws[0]['day_of_week'], "Friday")

    def test_skips_rows_that_break_rules(self):
        draws = self.scrape([
            ("26/001", "02/01/2026", [1, 2, 3, 4, 5, 6, 7]),     # OK
            ("26/002", "04/01/2026", [1, 1, 3, 4, 5, 6, 7]),     # 主號重複
            ("26/003", "06/01/2026", [1, 2, 3, 4, 5, 50, 7]),    # 超出範圍
            ("26/004", "08/01/2026", [1, 2, 3, 4, 5, 6, 6]),     # 特別號與主號重複
            ("26/005", "10/01/2026", [1, 2, 3, 4, 5, 6]),        # 只有6個
            ("25/150", "13/01/2026", [1, 2, 3, 4, 5, 6, 7]),     # 期號年份不符
            ("<i>1/2</i>", "15/01/2026", [1, 2, 3, 4, 5, 6, 7]),  # 期號格式錯
            ("26/008", "31/02/2026", [1, 2, 3, 4, 5, 6, 7]),     # 不存在的日期
        ])
        self.assertEqual([d['draw_id'] for d in draws], ["26/001"])

    def test_empty_page(self):
        self.assertEqual(self.scrape([]), [])

    def test_network_failure_returns_empty(self):
        with mock.patch.object(bs.requests, 'get', side_effect=bs.requests.exceptions.ConnectTimeout("x")), \
             mock.patch.object(bs.time, 'sleep'):
            self.assertEqual(bs.scrape_year(2026), [])


# ============================================================
# 合併 / 載入
# ============================================================
class TestMergeAndLoad(unittest.TestCase):
    def test_corrected_result_replaces_old_one(self):
        old = [make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 6], 7)]
        new = [make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 8], 7)]
        merged = bs.merge_draws(old, new)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['numbers'], [1, 2, 3, 4, 5, 8])

    def test_merge_sorted_and_new_added(self):
        old = [make_draw("26/002", "2026-01-04", [1, 2, 3, 4, 5, 6], 7)]
        new = [make_draw("26/003", "2026-01-06", [1, 2, 3, 4, 5, 6], 7),
               make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 6], 7)]
        self.assertEqual([d['draw_id'] for d in bs.merge_draws(old, new)], ["26/001", "26/002", "26/003"])

    def test_merge_across_year_boundary(self):
        old = [make_draw("25/150", "2025-12-30", [1, 2, 3, 4, 5, 6], 7)]
        new = [make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 6], 7)]
        self.assertEqual([d['draw_id'] for d in bs.merge_draws(old, new)], ["25/150", "26/001"])

    def load(self, content):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'x.json')
            if content is not None:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
            return bs.load_existing(path)

    def test_load_missing_file(self):
        self.assertEqual(self.load(None), [])

    def test_load_corrupted_file(self):
        self.assertEqual(self.load('{not json'), [])
        self.assertEqual(self.load('{"a": 1}'), [])

    def test_load_drops_invalid_rows(self):
        rows = [make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 6], 7),
                make_draw("26/002", "2026-01-04", [1, 2, 3, 4, 5, 6], 6), "垃圾"]
        self.assertEqual([d['draw_id'] for d in self.load(json.dumps(rows))], ["26/001"])


# ============================================================
# 統計
# ============================================================
class TestStats(unittest.TestCase):
    def test_low_high_boundary(self):
        # 小 = 1-24，大 = 25-49
        s = bs.compute_stats([make_draw("26/001", "2026-01-02", [1, 23, 24, 25, 26, 49], 2)])
        self.assertEqual(s['high_low'], {"low": 3, "high": 3})
        self.assertEqual(s['odd_even'], {"odd": 4, "even": 2})

    def test_special_number_not_counted(self):
        s = bs.compute_stats([make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 6], 49)])
        self.assertEqual(s['frequency']['49'], 0)
        self.assertEqual(sum(s['frequency'].values()), 6)

    def test_totals_consistent(self):
        draws = random_draws(137)
        s = bs.compute_stats(draws)
        self.assertEqual(sum(s['frequency'].values()), 137 * 6)
        self.assertEqual(sum(s['odd_even'].values()), 137 * 6)
        self.assertEqual(sum(s['high_low'].values()), 137 * 6)
        self.assertEqual(len(s['heatmap']), 49)
        self.assertEqual(len(s['hot_cold_20']), 49)


# ============================================================
# 預測模型
# ============================================================
class TestPredictions(unittest.TestCase):
    MODELS = (bs.predict_hot_cold, bs.predict_trend, bs.predict_ml)

    def check_pick(self, p):
        nums = p['numbers']
        self.assertEqual(len(nums), 6)
        self.assertEqual(len(set(nums)), 6)
        self.assertEqual(nums, sorted(nums))
        self.assertTrue(all(isinstance(n, int) and 1 <= n <= 49 for n in nums))
        self.assertEqual(set(p['confidence']), {str(n) for n in nums})
        self.assertEqual(set(p['explanations']), {str(n) for n in nums})
        self.assertTrue(all(0 <= c <= 1 for c in p['confidence'].values()))

    def test_all_models_any_history_length(self):
        for n in (1, 2, 9, 10, 11, 19, 20, 21, 49, 50, 51, 300):
            draws = random_draws(n, seed=n)
            for model in self.MODELS:
                with self.subTest(draws=n, model=model.__name__):
                    self.check_pick(model(draws))

    def test_identical_draws(self):
        # 每期都開同樣號碼（極端情況）
        draws = [make_draw(f"24/{i + 1:03d}", f"2024-01-{i + 1:02d}", [1, 2, 3, 4, 5, 6], 7) for i in range(25)]
        for model in self.MODELS:
            with self.subTest(model=model.__name__):
                self.check_pick(model(draws))

    def test_ml_balance_constraint(self):
        for seed in range(20):
            nums = bs.predict_ml(random_draws(80, seed=seed))['numbers']
            odd = sum(n % 2 for n in nums)
            high = sum(n > 24 for n in nums)
            self.assertTrue(2 <= odd <= 4, nums)
            self.assertTrue(2 <= high <= 4, nums)

    def test_ml_gap_never_drawn_vs_just_drawn(self):
        # 只有一期：剛開出的號碼間隔 0，從沒開過的號碼間隔不能也是 0
        p = bs.predict_ml([make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 6], 7)])
        for n, text in p['explanations'].items():
            expected = 0 if int(n) <= 6 else 1
            self.assertIn(f"間隔 {expected} 期", text, f"號碼 {n}: {text}")

    def test_ml_recent_freq_uses_actual_window(self):
        # 少於 50 期時，近期頻率要除以實際期數
        draws = random_draws(10)
        p = bs.predict_ml(draws)
        for n, text in p['explanations'].items():
            cnt = sum(int(n) in d['numbers'] for d in draws)
            self.assertIn(f"近{len(draws)}期出現 {cnt} 次", text)

    def test_trend_latest_draw_weight_is_one(self):
        # 少於 20 期時，最新一期權重仍應為 1
        p = bs.predict_trend([make_draw("26/001", "2026-01-02", [1, 2, 3, 4, 5, 6], 7)])
        self.assertEqual(p['numbers'], [1, 2, 3, 4, 5, 6])
        for text in p['explanations'].values():
            self.assertIn("加權分數 1.2", text)  # 1*0.7 + 趨勢(+1)*0.5


# ============================================================
# 產生網站（端到端）
# ============================================================
class TestBuildSite(unittest.TestCase):
    def test_build_embeds_data(self):
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(root, 'index.html'), encoding='utf-8') as f:
                html = f.read()
            with open(os.path.join(tmp, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(html)
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                bs.build_site(random_draws(30))
                with open('index.html', encoding='utf-8') as f:
                    out = f.read()
            finally:
                os.chdir(cwd)
        self.assertIn('"total_draws":30', out)
        self.assertEqual(out.count('var DATA='), 1)


if __name__ == '__main__':
    unittest.main()
