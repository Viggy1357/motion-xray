import { test, expect } from './fixtures';
import type { Page } from '@playwright/test';

const INTRO = 'How Motion X-Ray works';

const BUBBLE_TEXTS = [
  'One set at a time.',
  'You showed up. That counts.',
  'A little consistency goes a long way.',
];

async function gotoHome(page: Page) {
  await page.goto('/');
  const introHeading = page.getByRole('heading', { name: INTRO, level: 2 });
  await expect(introHeading).toBeVisible();
  await page.getByRole('button', { name: 'Skip intro', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Make your');
  await expect(introHeading).toBeHidden();
}

async function openSettings(page: Page) {
  await page.getByRole('button', { name: 'Settings and profile', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Settings', level: 1 })).toBeVisible();
}

test('home shows lady athlete and resting Pip without obscuring controls', async ({ freshPage: page }, testInfo) => {
  await gotoHome(page);

  const ladyImg = page.locator('.heroart img').first();
  await expect(ladyImg).toBeVisible();

  const rest = page.locator('[data-rest="true"]').first();
  await expect(rest).toBeVisible();
  await expect(rest).toHaveAttribute('aria-label', 'Milo resting');

  const front = page.getByRole('button', { name: 'Front', exact: true });
  const back = page.getByRole('button', { name: 'Back', exact: true });
  await back.click();
  await expect(ladyImg).toHaveAttribute('src', '/companion/athlete-back.png');
  await front.click();
  await expect(ladyImg).toHaveAttribute('src', '/companion/athlete.png');

  const cta = page.getByRole('button', { name: 'Analyse a set', exact: true });
  await expect(cta).toBeVisible();

  const restBox = await rest.boundingBox();
  const ctaBox = await cta.boundingBox();
  expect(restBox).not.toBeNull();
  expect(ctaBox).not.toBeNull();
  if (restBox && ctaBox) {
    const overlap =
      restBox.x < ctaBox.x + ctaBox.width &&
      restBox.x + restBox.width > ctaBox.x &&
      restBox.y < ctaBox.y + ctaBox.height &&
      restBox.y + restBox.height > ctaBox.y;
    expect(overlap).toBe(false);
  }

  await page.screenshot({
    path: `/results/milo02-home-${testInfo.project.name}.png`,
    fullPage: true,
  });
});

test('hiding Milo companion hides the resting pet but keeps the lady athlete', async ({ freshPage: page }) => {
  await gotoHome(page);
  await expect(page.locator('.heroart img').first()).toBeVisible();
  await expect(page.locator('[data-rest="true"]')).toHaveCount(1);

  await openSettings(page);
  await page.getByLabel('Show Milo companion').uncheck();
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Settings saved.');

  await page.getByRole('button', { name: 'Home', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Make your');
  await expect(page.locator('.heroart img').first()).toBeVisible();
  await expect(page.locator('[data-rest="true"]')).toHaveCount(0);
});

test('milo-moments preview rotates exactly three bubble texts sequentially', async ({ freshPage: page }) => {
  await page.goto('/milo-moments');
  await expect(page.getByRole('heading', { level: 1, name: 'Milo moments preview' })).toBeVisible();

  const bubble = page.locator('[data-bubble-index]').first();
  await expect(bubble).toBeVisible();

  const pip = page.locator('[data-asset-status="ready"]');
  await expect(pip).toBeVisible();
  await expect(pip).toHaveAttribute('data-state', 'attentive');

  const text0 = (await bubble.textContent())?.trim() ?? '';
  expect(BUBBLE_TEXTS).toContain(text0);

  await page.waitForTimeout(7000);
  const text1 = (await bubble.textContent())?.trim() ?? '';
  expect(BUBBLE_TEXTS).toContain(text1);
  expect(text1).not.toBe(text0);

  await page.waitForTimeout(7000);
  const text2 = (await bubble.textContent())?.trim() ?? '';
  expect(BUBBLE_TEXTS).toContain(text2);
  expect(text2).not.toBe(text1);
  expect(text2).not.toBe(text0);
});

test('milo-moments preview shows static first bubble text under reduced motion', async ({ freshPage: page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/milo-moments');
  await expect(page.getByRole('heading', { level: 1, name: 'Milo moments preview' })).toBeVisible();

  const bubble = page.locator('[data-bubble-index]').first();
  await expect(bubble).toBeVisible();

  const text0 = (await bubble.textContent())?.trim() ?? '';
  expect(BUBBLE_TEXTS).toContain(text0);

  await page.waitForTimeout(7000);
  const text1 = (await bubble.textContent())?.trim() ?? '';
  expect(text1).toBe(text0);
});

test('milo-moments pause hides the processing buddy', async ({ freshPage: page }) => {
  await page.goto('/milo-moments');
  await expect(page.locator('[data-bubble-index]').first()).toBeVisible();

  await page.getByRole('button', { name: 'Pause', exact: true }).click();
  await expect(page.locator('[data-bubble-index]')).toHaveCount(0);

  await page.getByRole('button', { name: 'Start', exact: true }).click();
  await expect(page.locator('[data-bubble-index]').first()).toBeVisible();
});

test('milo-moments preview does not show duplicate interval or cycle display', async ({ freshPage: page }) => {
  await page.goto('/milo-moments');
  await expect(page.getByRole('heading', { level: 1, name: 'Milo moments preview' })).toBeVisible();

  await expect(page.getByRole('button', { name: 'Start', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Pause', exact: true })).toBeVisible();

  const cycle = page.getByText(/Cycle index/i);
  await expect(cycle).toHaveCount(0);
});
