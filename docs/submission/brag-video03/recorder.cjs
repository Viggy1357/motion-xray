// Real UI recording CLI for motion-xray/browser-qc:local
// Records actual user flow against running Next.js app + backend API.
// No mocks, no route interception, no fake progress.

const { chromium } = require('/app/tests/browser/node_modules/@playwright/test');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = '/app/apps/web';
const NEXT_BIN = '/app/apps/web/node_modules/next/dist/bin/next';
const INPUT_VIDEO = '/input/lat_pulldown.mp4';
const OUTPUT_DIR = '/output';
const RAW_DIR = path.join(OUTPUT_DIR, 'raw');
const SCREENS_DIR = path.join(OUTPUT_DIR, 'screens');
const RECORDING_JSON = path.join(OUTPUT_DIR, 'recording.json');

const API_INTERNAL_URL = 'http://api:8000';
const APP_URL = 'http://localhost:3000';

const WINDOWS = {
  home: { duration: 12 },
  upload: { duration: 18 },
  processing: { duration: 15 },
  results: { duration: 25 },
  coaching: { duration: 20 },
  limits: { duration: 10 },
};

const TOTAL_BUDGET_MS = 7 * 60 * 1000;
const JOB_WAIT_MS = 300 * 1000;
const UI_WAIT_MS = 20 * 1000;
const COACHING_TIMEOUT_MS = 45 * 1000;

const ALLOW_COACHING = process.env.ALLOW_ONE_COACHING_CALL === '1';

function log(stage, msg) {
  process.stdout.write(`[${stage}] ${msg}\n`);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function waitForServer(url, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const r = await fetch(url, { method: 'GET' });
      if (r.status < 500) return true;
    } catch (_) {}
    await sleep(500);
  }
  return false;
}

async function main() {
  const timings = {};
  const t0 = Date.now();
  const deadline = t0 + TOTAL_BUDGET_MS;

  fs.mkdirSync(RAW_DIR, { recursive: true });
  fs.mkdirSync(SCREENS_DIR, { recursive: true });

  // Start Next.js production server as child process
  const nextEnv = { ...process.env, API_INTERNAL_URL, APP_ORIGIN: 'http://localhost:3000', NODE_ENV: 'production', PORT: '3000' };
  const nextProc = spawn(process.execPath, [NEXT_BIN, 'start', '-H', '127.0.0.1', '-p', '3000'], {
    cwd: ROOT,
    env: nextEnv,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let nextKilled = false;
  const killNext = () => {
    if (!nextKilled) { try { nextProc.kill('SIGTERM'); } catch (_) {} nextKilled = true; }
  };
  process.on('exit', killNext);
  process.on('SIGINT', () => { killNext(); process.exit(130); });
  process.on('SIGTERM', () => { killNext(); process.exit(143); });

  const serverReady = await waitForServer("http://127.0.0.1:3000", 30000);
  if (!serverReady) {
    killNext();
    throw new Error('Next.js server failed to become ready within 30s');
  }
  log('server', 'Next.js ready on localhost:3000');

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });

  let context;
  let page;
  let videoPath;
  let coachingPostCount = 0;
  let coachingResponseMeta = null;
  let errorStage = null;
  let timedOut = false;
  let budgetTimer;

  const cleanup = async () => {
    if (budgetTimer) { clearTimeout(budgetTimer); budgetTimer = null; }
    try { if (context) await context.close(); } catch (_) {}
    context = null;
    try { await browser.close(); } catch (_) {}
    killNext();
  };

  budgetTimer = setTimeout(() => {
    timedOut = true;
    errorStage = errorStage || 'deadline';
    log('deadline', '7-minute budget exceeded; forcing cleanup');
    cleanup().catch(() => {});
  }, TOTAL_BUDGET_MS);

  try {
    context = await browser.newContext({
      viewport: { width: 1280, height: 720 },
      deviceScaleFactor: 1,
      recordVideo: { dir: RAW_DIR, size: { width: 1280, height: 720 } },
    });

    page = await context.newPage();
    const perfBaseline = await page.evaluate(() => performance.now());
    const wallBaseline = Date.now();

    // Capture coaching POST exactly once
    page.on('request', (req) => {
      try {
        const u = new URL(req.url());
        if (req.method() === 'POST' && u.pathname.endsWith('/coaching')) {
          coachingPostCount += 1;
          if (coachingPostCount > 1) {
            throw new Error('Multiple coaching POSTs detected; aborting');
          }
        }
      } catch (e) {
        if (e.message.startsWith('Multiple coaching')) throw e;
      }
    });

    const coachingRespPromise = new Promise((resolve) => {
      page.on('response', async (resp) => {
        try {
          const req = resp.request();
          if (req.method() === 'POST' && new URL(resp.url()).pathname.endsWith('/coaching')) {
            let body = null;
            try { body = await resp.json(); } catch (_) {}
            const safe = {};
            if (body && typeof body === 'object') {
              if ('status' in body) safe.status = body.status;
              if ('model' in body) safe.model = body.model;
              if ('cache' in body) safe.cache = body.cache;
              if ('usage' in body) safe.usage = body.usage;
            }
            coachingResponseMeta = { httpStatus: resp.status(), body: safe };
            resolve();
          }
        } catch (_) {}
      });
    });

    // HOME
    await page.goto(APP_URL, { waitUntil: 'domcontentloaded', timeout: UI_WAIT_MS });
    await page.waitForSelector('#home-h', { timeout: UI_WAIT_MS });
    // Skip intro button if present (fresh home, no localStorage seeding)
    const skipBtn = page.getByRole('button', { name: /Skip intro/i });
    if ((await skipBtn.count()) > 0) {
      await skipBtn.first().click({ timeout: 5000 }).catch(() => {});
    }
    timings.homeStart = Date.now() - wallBaseline;
    await page.screenshot({ path: path.join(SCREENS_DIR, '01-home.png') });
    await sleep(WINDOWS.home.duration * 1000);

    // Navigate to analyse (button, not link)
    await page.getByRole('button', { name: /Analyse a set/i }).first().click();
    await page.waitForLoadState('domcontentloaded', { timeout: UI_WAIT_MS });

    // UPLOAD
    await page.locator('input[type="file"]').first().setInputFiles(INPUT_VIDEO);
    await page.waitForSelector('text=lat_pulldown.mp4', { timeout: UI_WAIT_MS });
    await page.getByRole('checkbox', { name: /I consent to uploading/i }).check();
    await page.waitForSelector('button:has-text("Upload & analyse")', { timeout: UI_WAIT_MS });
    timings.uploadStart = Date.now() - wallBaseline;
    await page.screenshot({ path: path.join(SCREENS_DIR, '02-upload.png') });
    await sleep(WINDOWS.upload.duration * 1000);

    await page.getByRole('button', { name: /Upload & analyse/i }).first().click();

    // PROCESSING - wait for real status region containing "Processing"
    const processingStatus = page.getByRole('status').filter({ hasText: /Processing/ });
    await processingStatus.waitFor({ state: 'visible', timeout: JOB_WAIT_MS });
    timings.processingStart = Date.now() - wallBaseline;
    await page.screenshot({ path: path.join(SCREENS_DIR, '03-processing.png') });
    await sleep(WINDOWS.processing.duration * 1000);

    // RESULTS - wait for actual segment-ready button (accessible name)
    const segmentBtn = page.getByRole('button', { name: /^Play video from segment / }).first();
    await segmentBtn.waitFor({ state: 'visible', timeout: JOB_WAIT_MS });
    timings.resultsStart = Date.now() - wallBaseline;
    await page.screenshot({ path: path.join(SCREENS_DIR, '04-results.png') });
    // Hold 8s, then click chip, then 17s replay inside window
    await sleep(8 * 1000);
    await segmentBtn.click();
    await sleep(17 * 1000);

    // COACHING
    if (!ALLOW_COACHING) {
      throw new Error('ALLOW_ONE_COACHING_CALL not set; refusing to click coaching');
    }
    const coachingHeading = page.getByRole('heading', { name: 'Coaching highlight' });
    await coachingHeading.scrollIntoViewIfNeeded();
    timings.coachingStart = Date.now() - wallBaseline;
    await page.screenshot({ path: path.join(SCREENS_DIR, '05-coaching.png') });

    const coachingBtn = page.getByRole('button', { name: /Generate coaching/i }).first();
    const respPromise = coachingRespPromise;
    await coachingBtn.click();

    const coachingElapsed = await Promise.race([
      respPromise.then(() => 'done'),
      sleep(COACHING_TIMEOUT_MS).then(() => 'timeout'),
    ]);
    if (coachingElapsed === 'timeout') {
      throw new Error('Coaching response timeout');
    }
    // Screenshot after response received
    await page.screenshot({ path: path.join(SCREENS_DIR, '05b-coaching-after.png') });
    const elapsedMs = Date.now() - wallBaseline - timings.coachingStart;
    const remainingMs = (WINDOWS.coaching.duration * 1000) - elapsedMs;
    if (remainingMs > 0) await sleep(remainingMs);
    else await sleep(5 * 1000);

    // LIMITS - experimental disclosure
    await page.waitForSelector('text=/Reference comparison.*experimental/i', { timeout: UI_WAIT_MS });
    await page.locator('text=/Reference comparison.*experimental/i').first().scrollIntoViewIfNeeded();
    timings.limitsStart = Date.now() - wallBaseline;
    await page.screenshot({ path: path.join(SCREENS_DIR, '06-limits.png') });
    await sleep(WINDOWS.limits.duration * 1000);

    // Close context to finalize video
    await context.close();
    context = null;
    const video = page.video();
    if (video) videoPath = await video.path();

    const recording = {
      videoPath,
      timings: {
        home: { start_s: timings.homeStart / 1000, duration_s: WINDOWS.home.duration },
        upload: { start_s: timings.uploadStart / 1000, duration_s: WINDOWS.upload.duration },
        processing: { start_s: timings.processingStart / 1000, duration_s: WINDOWS.processing.duration },
        results: { start_s: timings.resultsStart / 1000, duration_s: WINDOWS.results.duration },
        coaching: { start_s: timings.coachingStart / 1000, duration_s: WINDOWS.coaching.duration },
        limits: { start_s: timings.limitsStart / 1000, duration_s: WINDOWS.limits.duration },
      },
      coaching_post_count: coachingPostCount,
      coaching_response: coachingResponseMeta,
      perf_baseline_ms: perfBaseline,
      wall_baseline_ms: wallBaseline,
      total_elapsed_ms: Date.now() - t0,
    };
    fs.writeFileSync(RECORDING_JSON, JSON.stringify(recording, null, 2));
    log('done', `recording.json written; video=${videoPath}`);
  } catch (err) {
    errorStage = err.stage || (timedOut ? 'deadline' : 'unknown');
    const sanitized = { name: err.name, message: String(err.message || '').slice(0, 200), stage: errorStage, coaching_post_count: coachingPostCount, timings };
    try { fs.writeFileSync(path.join(OUTPUT_DIR, 'error.json'), JSON.stringify(sanitized, null, 2)); } catch (_) {}
    throw err;
  } finally {
    await cleanup();
  }
}

main().catch((err) => {
  log('error', `${err.name}: ${String(err.message || '').slice(0, 200)}`);
  process.exit(1);
});
