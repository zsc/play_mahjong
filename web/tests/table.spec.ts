import { test, expect } from '@playwright/test';

test('settled winner is exposed, winning tile is separate, table follows all four seats', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#engine-status')).toContainText('WASM');
  await page.locator('#watch-mode').click();
  await page.locator('#seed').fill('16000001');
  await page.locator('#start-seeded').click();
  await expect(page.locator('#decision-bar')).toContainText('西家和牌', { timeout: 60000 });
  await expect(page.locator('#board .settled-hand')).toHaveCount(4);
  await expect(page.locator('#board .concealed-hand')).toHaveCount(0);
  await expect(page.locator('#board .winner')).toHaveAttribute('data-seat', '2');
  await expect(page.locator('#board .winning-tile')).toHaveAttribute('data-tile', 'W6');
  await expect(page.locator('#board .winner .settled-hand > .tile')).toHaveCount(14);
  await expect(page.locator('.winning-summary .winning-tile')).toHaveAttribute('data-tile', 'W6');
  await expect(page.locator('#board .river')).toHaveCount(4);
  const columns = await page.locator('.river-tiles').evaluateAll(rows => rows.map(row => getComputedStyle(row).gridTemplateColumns.split(' ').length));
  expect(columns).toEqual([6, 6, 6, 6]);
  for (const [width, name] of [[1400, 'desktop'], [390, 'mobile']] as const) {
    await page.setViewportSize({ width, height: 1000 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
    await page.screenshot({ path: `test-results/settled-${name}.png`, fullPage: true });
  }
  // A new game must hide the other hands again, including after changing perspective.
  await page.locator('#human-mode').click();
  await page.locator('#seat').selectOption('2');
  await page.locator('#start-seeded').click();
  await expect(page.locator('#board .settled-hand')).toHaveCount(0);
  await expect(page.locator('#board .concealed-hand')).toHaveCount(3);
  await expect(page.locator('.seat-south')).toHaveAttribute('data-seat', '2');
  await expect(page.locator('.seat-east')).toHaveAttribute('data-seat', '3');
  await expect(page.locator('.seat-north')).toHaveAttribute('data-seat', '0');
  await expect(page.locator('.seat-west')).toHaveAttribute('data-seat', '1');
});

test('meld provenance and concealed kong display follow MCR 3.6.5 and 3.6.8', async ({ page }) => {
  await page.goto('/');
  const result = await page.evaluate(async () => {
    const { meldHtml } = await import('/src/table.ts');
    const holder = document.createElement('div');
    // These are presentation fixtures, not generated games or training evidence.
    const cases = [
      { kind: 'chow', tile: 'W2', claimed_tile: 'W3', claimed_from: 3, expected: ['W3', 'W1', 'W2'], slot: 0 },
      { kind: 'pung', tile: 'T2', claimed_tile: 'T2', claimed_from: 2, expected: ['T2', 'T2', 'T2'], slot: 1 },
      { kind: 'kong', tile: 'B4', claimed_tile: 'B4', claimed_from: 1, expected: ['B4', 'B4', 'B4', 'B4'], slot: 3 },
    ];
    for (const c of cases) {
      holder.innerHTML = meldHtml({ ended: false, table: [{ melds: [{ ...c, concealed: false }] }] } as any, 0);
      if (JSON.stringify([...holder.querySelectorAll('[data-tile]')].map(t => t.getAttribute('data-tile'))) !== JSON.stringify(c.expected)) throw new Error('meld tile order');
      if (Array.from(holder.querySelector('.meld')!.children).indexOf(holder.querySelector('.claimed-tile')!) !== c.slot) throw new Error('claimed tile direction');
    }
    const state = { ended: false, table: [{ melds: [{ kind: 'kong', tile: 'J3', concealed: true, claimed_from: null }] }] };
    holder.innerHTML = meldHtml(state as any, 0);
    if (holder.querySelectorAll('.tile-back').length !== 4 || holder.querySelector('[data-tile]')) throw new Error('concealed kong exposed live');
    state.ended = true;
    holder.innerHTML = meldHtml(state as any, 0);
    if (holder.querySelectorAll('[data-tile="J3"]').length !== 4) throw new Error('terminal kong not revealed');
    return true;
  });
  expect(result).toBe(true);
});
