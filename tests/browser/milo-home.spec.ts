import { test, expect } from './fixtures';
import type { Page } from '@playwright/test';

const INTRO = 'How Motion X-Ray works';

async function gotoHome(page: Page) {
  await page.goto('/');
  const introHeading = page.getByRole('heading', { name: INTRO, level: 2 });
  if (await introHeading.isVisible().catch(() => false)) {
    await page.getByRole('button', { name: 'Skip intro', exact: true }).click();
  }
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Make your');
  await expect(introHeading).toBeHidden();
}

async function openSettings(page: Page) {
  await page.getByRole('button', { name: 'Settings and profile', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Settings', level: 1 })).toBeVisible();
}

test('home hero art renders with definite width and no horizontal overflow', async ({ freshPage: page }, testInfo) => {
  await gotoHome(page);

  const root = page.locator('[data-asset-status]').first();
  await expect(root).toBeVisible();

  const box = await root.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.width).toBeGreaterThanOrEqual(200);
  expect(box!.height).toBeGreaterThanOrEqual(200);

  const img = root.locator('img').first();
  if (await img.count()) {
    await expect(img).toBeVisible();
    const natural = await img.evaluate((el) => (el as HTMLImageElement).naturalWidth);
    expect(natural).toBeGreaterThan(0);
  }

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  );
  expect(overflow).toBe(true);

  await page.screenshot({ path: `/results/milo-home-${testInfo.project.name}.png`, fullPage: false });
});

test('hiding Milo companion removes the hero root and keeps the legacy fallback', async ({ freshPage: page }) => {
  await gotoHome(page);
  await expect(page.locator('[data-asset-status]').first()).toBeVisible();

  await openSettings(page);
  await page.getByLabel('Show Milo companion').uncheck();
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Settings saved.');

  await page.getByRole('button', { name: 'Home', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Make your');
  await expect(page.locator('[data-asset-status]')).toHaveCount(0);

  await page.reload();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Make your');
  await expect(page.locator('[data-asset-status]')).toHaveCount(0);
});

test('reduced motion on Home disables animations on the hero root', async ({ freshPage: page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await gotoHome(page);

  const root = page.locator('[data-asset-status]').first();
  await expect(root).toBeVisible();

  const anim = await root.evaluate((el) => {
    const cs = getComputedStyle(el);
    return {
      name: cs.animationName,
      duration: cs.animationDuration,
    };
  });
  expect(anim.name === 'none' || anim.duration === '0s').toBe(true);

  await page.screenshot({ path: `/results/milo-home-${testInfo.project.name}.png`, fullPage: false });
});
