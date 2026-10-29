import { test, expect } from './fixtures';
import type { Locator, Page } from '@playwright/test';

declare global {
  interface Window {
    __qcTracks?: MediaStreamTrack[];
  }
}

const ORIGIN = 'http://127.0.0.1:3000';
const INTRO = 'How Motion X-Ray works';

const consentCheckbox = (page: Page) =>
  page.getByRole('checkbox', { name: /^I consent to uploading this video/ });

async function gotoIntro(page: Page) {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: INTRO, level: 2 })).toBeVisible();
}

async function skipIntro(page: Page) {
  await gotoIntro(page);
  await page.getByRole('button', { name: 'Skip intro', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Make your');
  await expect(page.getByRole('heading', { name: INTRO, level: 2 })).toBeHidden();
}

async function navTo(page: Page, name: 'Home' | 'Analyse' | 'Progress') {
  await page.getByRole('button', { name, exact: true }).click();
}

async function openAnalyse(page: Page) {
  await navTo(page, 'Analyse');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('clear view');
}

async function openSettings(page: Page) {
  await page.getByRole('button', { name: 'Settings and profile', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Settings', level: 1 })).toBeVisible();
}

async function openRecordDialog(page: Page): Promise<Locator> {
  await page.getByRole('button', { name: 'Record a set', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  return dialog;
}

async function beginCapture(dialog: Locator) {
  await dialog.getByRole('button', { name: 'Record a set', exact: true }).click();
  await dialog.getByRole('button', { name: 'Continue to camera', exact: true }).click();
  await dialog.getByRole('button', { name: 'Start recording', exact: true }).click();
}

async function recordShortTake(dialog: Locator) {
  await beginCapture(dialog);
  await expect(dialog.getByText(/REC\s*2\s*s/).first()).toBeVisible({ timeout: 20_000 });
  await dialog.getByRole('button', { name: 'Stop', exact: true }).click();
  await expect(dialog.getByRole('button', { name: 'Use this video', exact: true })).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Retake', exact: true })).toBeVisible();
}

test('intro Continue leads to Analyse with unchecked consent and disabled upload', async ({ freshPage: page }) => {
  await gotoIntro(page);
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('clear view');
  await expect(consentCheckbox(page)).not.toBeChecked();
  await expect(page.getByRole('button', { name: 'Upload & analyse', exact: true })).toBeDisabled();
});

test('skip intro keeps Home, persists marker and stays hidden after reload', async ({ freshPage: page }) => {
  await gotoIntro(page);
  await page.getByRole('button', { name: 'Skip intro', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Make your');
  const intro = page.getByRole('heading', { name: INTRO, level: 2 });
  await expect(intro).toBeHidden();
  const raw = await page.evaluate(() => window.localStorage.getItem('mxr.ux.v1'));
  expect(raw).toBeTruthy();
  expect(JSON.parse(raw as string)).toMatchObject({ introSeenVersion: 1 });
  await page.reload();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Make your');
  await expect(intro).toBeHidden();
});

test('progress shows empty state headings', async ({ freshPage: page }) => {
  await skipIntro(page);
  await navTo(page, 'Progress');
  await expect(page.getByRole('heading', { name: 'Small steps. Real consistency.', level: 1 })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Nothing logged yet', level: 2 })).toBeVisible();
});

test('settings cancel discards name edit and returns to Analyse', async ({ freshPage: page }) => {
  await skipIntro(page);
  await openAnalyse(page);
  await openSettings(page);
  await page.locator('#settings-display-name').fill('Scratch Name');
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toContainText('clear view');
  await openSettings(page);
  await expect(page.locator('#settings-display-name')).toHaveValue('');
});

test('settings save persists name and weekly target across reload', async ({ freshPage: page }) => {
  await skipIntro(page);
  await openSettings(page);
  await page.locator('#settings-display-name').fill('QC');
  await page.getByRole('checkbox', { name: 'Enable a weekly analysed-set target', exact: true }).check();
  await page.locator('#settings-goal-target').fill('3');
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Settings saved.');
  await expect(page.getByRole('heading', { name: 'Settings', level: 1 })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Settings', level: 1 })).toBeVisible();
  await expect(page.locator('#settings-display-name')).toHaveValue('QC');
  await expect(page.locator('#settings-goal-target')).toHaveValue('3');
  await expect(page.getByRole('checkbox', { name: 'Enable a weekly analysed-set target', exact: true })).toBeChecked();
});

test('without mediaDevices the Record entry is replaced by file choice', async ({ freshPage: page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(window.navigator, 'mediaDevices', { value: undefined, configurable: true });
  });
  await skipIntro(page);
  await openAnalyse(page);
  await expect(page.getByRole('button', { name: 'Record a set', exact: true })).toHaveCount(0);
  await expect(page.getByText('Choose video').first()).toBeVisible();
  await expect(page.locator('input[type="file"]').first()).toBeEnabled();
  await expect(page.getByText(/Camera recording is not available/).first()).toBeVisible();
});

test('camera denial surfaces fallback actions inside the dialog', async ({ freshPage: page }) => {
  await page.addInitScript(() => {
    const devices = navigator.mediaDevices;
    devices.getUserMedia = () => Promise.reject(new DOMException('denied', 'NotAllowedError'));
  });
  await skipIntro(page);
  await openAnalyse(page);
  const dialog = await openRecordDialog(page);
  await dialog.getByRole('button', { name: 'Record a set', exact: true }).click();
  await dialog.getByRole('button', { name: 'Continue to camera', exact: true }).click();
  await expect(dialog.getByText(/Camera access is not available/).first()).toBeVisible();
  await expect(dialog.getByRole('button', { name: 'Choose a video file instead', exact: true })).toBeVisible();
});

test('cancelling the countdown ends every captured track and clears the preview', async ({ freshPage: page, context }) => {
  await context.grantPermissions(['camera'], { origin: ORIGIN });
  await page.addInitScript(() => {
    window.__qcTracks = [];
    const original = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    navigator.mediaDevices.getUserMedia = async (constraints?: MediaStreamConstraints) => {
      const stream = await original(constraints);
      window.__qcTracks?.push(...stream.getTracks());
      return stream;
    };
  });
  await skipIntro(page);
  await openAnalyse(page);
  const dialog = await openRecordDialog(page);
  await beginCapture(dialog);
  await dialog.getByRole('button', { name: 'Cancel countdown', exact: true }).click();
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const tracks = window.__qcTracks ?? [];
          return tracks.length > 0 && tracks.every((t) => t.readyState === 'ended');
        }),
      { timeout: 10_000 },
    )
    .toBe(true);
  await expect
    .poll(
      () =>
        page.evaluate(() => {
          const videos = Array.from(document.querySelectorAll('video'));
          return videos.length > 0 && videos.every((v) => v.srcObject === null);
        }),
      { timeout: 10_000 },
    )
    .toBe(true);
  await expect(consentCheckbox(page)).not.toBeChecked();
});

test('record a real take, review, retake, then use the next take', async ({ freshPage: page, context }) => {
  test.setTimeout(45_000);
  await context.grantPermissions(['camera'], { origin: ORIGIN });
  await skipIntro(page);
  await openAnalyse(page);
  const dialog = await openRecordDialog(page);
  await recordShortTake(dialog);
  const review = dialog.getByLabel('Recorded clip preview');
  await expect(review).toBeVisible();
  await expect
    .poll(
      () =>
        review.evaluate((el) => {
          const v = el as HTMLVideoElement;
          return v.readyState >= 2 && v.videoWidth > 0 && v.duration > 0;
        }),
      { timeout: 15_000 },
    )
    .toBe(true);
  await dialog.getByRole('button', { name: 'Retake', exact: true }).click();
  await dialog.getByRole('button', { name: 'Confirm discard & retake', exact: true }).click();
  await expect(dialog.getByRole('button', { name: 'Record a set', exact: true })).toBeVisible();
  await recordShortTake(dialog);
  await dialog.getByRole('button', { name: 'Use this video', exact: true }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByLabel('Local preview — not uploaded yet')).toBeVisible();
  await expect(consentCheckbox(page)).not.toBeChecked();
  await expect(page.getByRole('button', { name: 'Upload & analyse', exact: true })).toBeDisabled();
});

async function assertLayout(page: Page, viewport: unknown) {
  expect(page.viewportSize()).toEqual(viewport);
  const fitsWidth = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  );
  expect(fitsWidth).toBe(true);
  const boxes = await page.locator('button, a, summary').evaluateAll((els) =>
    els
      .filter((el) => el.getClientRects().length > 0)
      .map((el) => {
        const rect = el.getBoundingClientRect();
        return { w: rect.width, h: rect.height };
      }),
  );
  expect(boxes.length).toBeGreaterThan(0);
  for (const box of boxes) {
    expect(box.w).toBeGreaterThanOrEqual(44);
    expect(box.h).toBeGreaterThanOrEqual(44);
  }
}

test('every screen fits the project viewport with 44px interactive targets', async ({ freshPage: page }, testInfo) => {
  const viewport = testInfo.project.use.viewport;
  await skipIntro(page);
  await navTo(page, 'Home');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Make your');
  await assertLayout(page, viewport);
  await openAnalyse(page);
  await assertLayout(page, viewport);
  await navTo(page, 'Progress');
  await expect(page.getByRole('heading', { name: 'Small steps. Real consistency.', level: 1 })).toBeVisible();
  await assertLayout(page, viewport);
  await openSettings(page);
  await assertLayout(page, viewport);
});
