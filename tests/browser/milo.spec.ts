import { test, expect } from './fixtures';
import type { Page } from '@playwright/test';

test.describe('Milo preview', () => {
  test('renders ready asset status and idle head animation', async ({ freshPage }, testInfo) => {
    await freshPage.goto('/milo-preview');
    const root = freshPage.locator('[data-asset-status]').first();
    await expect(root).toHaveAttribute('data-asset-status', 'ready', { timeout: 10000 });
    await expect(root).toHaveAttribute('data-state', /idle|attentive|cheer|static/);
    await expect(root).toBeVisible();
    await freshPage.screenshot({ path: `/results/milo-preview-${testInfo.project.name}.png` });
  });

  test('attentive state applies attentive class', async ({ freshPage }) => {
    await freshPage.goto('/milo-preview');
    const root = freshPage.locator('[data-asset-status]').first();
    await expect(root).toHaveAttribute('data-asset-status', 'ready', { timeout: 10000 });

    await freshPage.getByRole('button', { name: 'Attentive' }).click();
    await expect(root).toHaveAttribute('data-state', 'attentive');
  });

  test('cheer eventually returns to idle and increments nonce once', async ({ freshPage }) => {
    await freshPage.goto('/milo-preview');
    const root = freshPage.locator('[data-asset-status]').first();
    await expect(root).toHaveAttribute('data-asset-status', 'ready', { timeout: 10000 });

    const before = Number(await root.getAttribute('data-cheer-nonce'));
    await freshPage.getByRole('button', { name: 'Cheer' }).click();
    await expect(root).toHaveAttribute('data-state', 'cheer');

    await freshPage.waitForTimeout(1800);
    await expect(root).toHaveAttribute('data-state', 'idle');

    const after = Number(await root.getAttribute('data-cheer-nonce'));
    expect(after - before).toBe(1);
  });

  test('retry with same key does not increment nonce', async ({ freshPage }) => {
    await freshPage.goto('/milo-preview');
    const root = freshPage.locator('[data-asset-status]').first();
    await expect(root).toHaveAttribute('data-asset-status', 'ready', { timeout: 10000 });

    await freshPage.getByRole('button', { name: 'Cheer' }).click();
    await expect(root).toHaveAttribute('data-state', 'cheer');
    await freshPage.waitForTimeout(1800);
    await expect(root).toHaveAttribute('data-state', 'idle');

    const before = Number(await root.getAttribute('data-cheer-nonce'));
    await freshPage.getByRole('button', { name: 'Retry (same key)' }).click();
    await freshPage.waitForTimeout(400);
    const after = Number(await root.getAttribute('data-cheer-nonce'));
    expect(after).toBe(before);
  });

  test('hidden unmounts the companion', async ({ freshPage }) => {
    await freshPage.goto('/milo-preview');
    const root = freshPage.locator('[data-asset-status]').first();
    await expect(root).toHaveAttribute('data-asset-status', 'ready', { timeout: 10000 });

    await freshPage.getByLabel('Hidden').check();
    await expect(freshPage.locator('[data-asset-status]')).toHaveCount(0);
  });

  test('reduced motion forces static state', async ({ freshPage }) => {
    await freshPage.goto('/milo-preview');
    const root = freshPage.locator('[data-asset-status]').first();
    await expect(root).toHaveAttribute('data-asset-status', 'ready', { timeout: 10000 });

    await freshPage.getByLabel('Reduced motion').check();
    await expect(root).toHaveAttribute('data-state', 'static');
  });

  test('OS reduced motion via emulateMedia forces static and no animation', async ({ freshPage }) => {
    await freshPage.emulateMedia({ reducedMotion: 'reduce' });
    await freshPage.goto('/milo-preview');
    const root = freshPage.locator('[data-asset-status]').first();
    await expect(root).toHaveAttribute('data-asset-status', 'ready', { timeout: 10000 });
    await expect(root).toHaveAttribute('data-state', 'static');
    const head = freshPage.locator('[data-asset-status] .head, [data-asset-status] [class*="head"]').first();
    if (await head.count()) {
      const animation = await head.evaluate((el) => getComputedStyle(el).animationName);
      expect(animation).toBe('none');
    }
  });

  test('failed asset shows fallback then neutral placeholder', async ({ freshPage }) => {
    await freshPage.goto('/milo-preview');
    const root = freshPage.locator('[data-asset-status]').first();
    await expect(root).toHaveAttribute('data-asset-status', 'ready', { timeout: 10000 });

    await freshPage.getByLabel('Failed asset (force fallback)').check();
    await expect(root).toHaveAttribute('data-asset-status', 'failed');

    // Clear fallback src to simulate missing fallback -> neutral placeholder.
    const fallbackInput = freshPage.locator('input[type="text"]').first();
    await fallbackInput.fill('');
    await expect(root).toBeVisible();
    await expect(freshPage.locator('[data-asset-status] img')).toHaveCount(0);
    await expect(freshPage.locator('[data-milo-fallback]')).toBeVisible();

    // Forced failed status must remain failed even after clearing fallback.
    await expect(root).toHaveAttribute('data-asset-status', 'failed');
  });
});
