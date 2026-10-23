#!/usr/bin/env node
/*
 * index.html 前端測試（需要 playwright + chromium）
 *
 * 執行：node tests/test_frontend.js [index.html 路徑...]
 * 預設測試專案根目錄的 index.html。外部 CDN（Chart.js、字型）會被替換成空殼，可離線執行。
 */
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const { chromium } = require('playwright');

const ROOT = path.join(__dirname, '..');
let failures = 0;

async function test(name, fn) {
  try {
    await fn();
    console.log('  ✓ ' + name);
  } catch (e) {
    failures++;
    console.log('  ✗ ' + name + '\n      ' + e.message.split('\n').join('\n      '));
  }
}

function checkPick(nums, label) {
  assert.strictEqual(nums.length, 6, label + ' 應有 6 個號碼: ' + nums);
  assert.strictEqual(new Set(nums).size, 6, label + ' 號碼重複: ' + nums);
  assert.ok(nums.every(n => Number.isInteger(n) && n >= 1 && n <= 49), label + ' 超出 1-49: ' + nums);
  assert.deepStrictEqual(nums, nums.slice().sort((a, b) => a - b), label + ' 未排序: ' + nums);
}

/* ---------- pickWeighted 單元測試（直接從 index.html 抽出函式） ---------- */
function loadPickWeighted(html) {
  const m = html.match(/function pickWeighted\(w49\)\{[\s\S]*?\n\}/);
  assert.ok(m, '找不到 pickWeighted');
  return new Function(m[0] + '; return pickWeighted;')();
}

async function unitTests(html) {
  console.log('pickWeighted');
  const pick = loadPickWeighted(html);
  const ones = Array(49).fill(1);

  await test('一般權重：6 個不重複、排序、1-49', () => {
    for (let i = 0; i < 2000; i++) checkPick(pick(ones.map((_, j) => j + 1)), 'run ' + i);
  });
  await test('只有 3 個號碼有權重：仍要抽滿 6 個', () => {
    const w = Array(49).fill(0); w[0] = 5; w[10] = 5; w[48] = 5;
    for (let i = 0; i < 500; i++) {
      const r = pick(w);
      checkPick(r, 'run ' + i);
      [1, 11, 49].forEach(n => assert.ok(r.includes(n), '有權重的號碼 ' + n + ' 應被選中: ' + r));
    }
  });
  await test('全部權重為 0 / NaN / 負數 / Infinity：不卡死且合法', () => {
    [Array(49).fill(0), Array(49).fill(NaN), Array(49).fill(-3), Array(49).fill(Infinity)]
      .forEach(w => { for (let i = 0; i < 200; i++) checkPick(pick(w), String(w[0])); });
  });
  await test('極端偏重：權重大的號碼幾乎每次都中', () => {
    const w = Array(49).fill(1e-9); w[6] = 1;
    for (let i = 0; i < 200; i++) assert.ok(pick(w).includes(7));
  });
  await test('分布大致符合權重（號碼 1 權重是其他的 10 倍）', () => {
    const w = Array(49).fill(1); w[0] = 10;
    const cnt = Array(50).fill(0); const N = 20000;
    for (let i = 0; i < N; i++) pick(w).forEach(n => cnt[n]++);
    const others = cnt.slice(2).reduce((a, b) => a + b, 0) / 48;
    assert.ok(cnt[1] > others * 3, '號碼1=' + cnt[1] + ' 其他平均=' + others.toFixed(0));
    assert.ok(cnt.slice(2).every(c => c > 0), '每個號碼都應有機會被抽到');
  });
}

/* ---------- 瀏覽器整合測試 ---------- */
async function pageTests(browser, file) {
  console.log('頁面：' + path.relative(ROOT, file));
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.route('**/*', route => {
    const url = route.request().url();
    if (url.startsWith('file:')) return route.continue();
    if (url.includes('chart')) {
      return route.fulfill({ contentType: 'text/javascript',
        body: 'window.Chart=function(){};Chart.defaults={font:{}};' });
    }
    return route.fulfill({ body: '' });
  });
  await page.goto('file://' + file);

  await test('載入無 JS 錯誤', () => assert.deepStrictEqual(errors, []));

  const data = await page.evaluate(() => DATA);

  await test('最新一期與近10期表格顯示正確', async () => {
    const latest = data.recent_10[data.recent_10.length - 1];
    const txt = await page.textContent('#latest-draw');
    assert.ok(txt.includes('#' + latest.draw_id), txt);
    const rows = await page.$$eval('#results-table tbody tr', trs => trs.length);
    assert.strictEqual(rows, data.recent_10.length);
  });

  await test('預測號碼符合規則', () => data.predictions.models.forEach((m, i) => checkPick(m.numbers, 'model ' + i)));

  await test('「查看分析」顯示的是模型自己的說明（不是前端另外算的）', async () => {
    const shown = await page.$$eval('.pred-model', cards => cards.map(c =>
      Array.from(c.querySelectorAll('.expl-item')).map(it => it.children[1].textContent)));
    data.predictions.models.forEach((m, i) => {
      assert.deepStrictEqual(shown[i], m.numbers.map(n => m.explanations[String(n)]), 'model ' + i);
    });
  });

  await test('「重新產生」連按 300 次：每次都是 6 個不重複號碼', async () => {
    const btns = await page.$$('.pred-model .toggle-btn:nth-child(2)');
    assert.strictEqual(btns.length, 3);
    for (let i = 0; i < btns.length; i++) {
      for (let k = 0; k < 300; k++) {
        await btns[i].click();
        const nums = await page.$$eval('.pred-model:nth-of-type(' + (i + 1) + ') .pred-ball',
          bs => bs.map(b => +b.textContent));
        checkPick(nums, 'model ' + i + ' click ' + k);
      }
    }
    // 重新產生後說明也要跟著換成新號碼
    const pairs = await page.$$eval('.pred-model', cards => cards.map(c => ({
      balls: Array.from(c.querySelectorAll('.pred-ball')).map(b => +b.textContent),
      expl: Array.from(c.querySelectorAll('.expl-num')).map(e => +e.textContent),
    })));
    pairs.forEach((p, i) => assert.deepStrictEqual(p.expl, p.balls, 'model ' + i));
  });

  await test('間隔分析：最新一期開出的號碼間隔為 0、不把特別號算進去', async () => {
    const r20 = data.recent_20, last = r20[r20.length - 1];
    const res = { n: last.numbers[0], sp: last.special_number };
    // 透過重新產生直到抽中目標號碼，讀取前端估算的說明
    const btn = (await page.$$('.pred-model .toggle-btn:nth-child(2)'))[2];
    const found = {};
    for (let k = 0; k < 3000 && Object.keys(found).length < 49; k++) {
      await btn.click();
      const items = await page.$$eval('.pred-model:nth-of-type(3) .expl-item',
        its => its.map(it => [+it.children[0].textContent, it.children[1].textContent]));
      items.forEach(([n, t]) => { found[n] = t; });
      if (found[res.n] && (found[res.sp] || last.numbers.includes(res.sp))) break;
    }
    assert.ok(found[res.n], '沒抽到號碼 ' + res.n);
    assert.ok(found[res.n].includes('距上次出現 0 期'), res.n + ': ' + found[res.n]);
    if (found[res.sp]) {
      const lastMain = [...r20].reverse().findIndex(d => d.numbers.includes(res.sp));
      const expected = lastMain < 0 ? '>' + (r20.length - 1) : String(lastMain);
      assert.ok(found[res.sp].includes('距上次出現 ' + expected + ' 期'), '特別號 ' + res.sp + ': ' + found[res.sp]);
    }
  });

  await page.close();
}

(async () => {
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  await unitTests(html);
  const files = process.argv.slice(2).map(f => path.resolve(f));
  if (!files.length) files.push(path.join(ROOT, 'index.html'));
  const browser = await chromium.launch();
  for (const f of files) await pageTests(browser, f);
  await browser.close();
  console.log(failures ? '\n❌ ' + failures + ' 個測試失敗' : '\n✅ 全部通過');
  process.exit(failures ? 1 : 0);
})();
