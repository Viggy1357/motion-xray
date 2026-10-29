import { test, expect } from './fixtures';
import type { Page } from '@playwright/test';

const INTRO = 'How Motion X-Ray works';

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

test('home resting pet root has data-rest and a small size on mobile', async ({ freshPage: page }, testInfo) => {
  await page.setViewportSize({ width: 480, height: 800 });
  await gotoHome(page);

  const rest = page.locator('[data-rest="true"]').first();
  await expect(rest).toBeVisible();
  await expect(rest).toHaveAttribute('aria-label', 'Milo resting');

  const box = await rest.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.width).toBeGreaterThanOrEqual(90);
  expect(box!.width).toBeLessThanOrEqual(140);

  const ladyImg = page.locator('.heroart img').first();
  await expect(ladyImg).toBeVisible();

  await page.screenshot({ path: `/results/milo-home-${testInfo.project.name}.png`, fullPage: false });
});

test('hiding Milo companion removes the resting pet but keeps the lady athlete', async ({ freshPage: page }) => {
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

test('reduced motion on Home disables animations on the resting pet inner', async ({ freshPage: page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await gotoHome(page);

  const rest = page.locator('[data-rest="true"]').first();
  await expect(rest).toBeVisible();

  const inner = rest.locator('div').first();
  const anim = await inner.evaluate((el) => {
    const cs = getComputedStyle(el);
    return {
      name: cs.animationName,
      duration: cs.animationDuration,
    };
  });
  expect(anim.name === 'none' || anim.duration === '0s').toBe(true);

  await page.screenshot({ path: `/results/milo-home-${testInfo.project.name}.png`, fullPage: false });
});

test('home resting pet does not overlap the Analyse a set CTA', async ({ freshPage: page }) => {
  await gotoHome(page);

  const rest = page.locator('[data-rest="true"]').first();
  await expect(rest).toBeVisible();

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
});
