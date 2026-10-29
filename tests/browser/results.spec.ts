import { test, expect } from './fixtures';
import type { Page, BrowserContext } from '@playwright/test';

// ---------------------------------------------------------------------------
// Coverage notes
// ---------------------------------------------------------------------------
// These tests exercise the Results page (MovementReport + SessionThumbnail +
// PoseReplay) under the fixture's per-page exact-route override policy.
// Every expected artifact read is fulfilled with a per-page exact path so
// the fixture's catch-all abort never blocks an expected read.  The
// intentionally-allowed 404s (pose, timestamps, proxy) are exercised by
// the fallback test only.
//
// Coverage:
// 1. Segment chip strip renders completed cycles with exact name selector
//    (page.getByRole(nav Completed cycles).getByRole(button exact name))
//    to avoid Play button duplicates.
// 2. Segment click dispatches mxr:seek-source with the correct source time.
// 3. SessionThumbnail fallback when the timestamp map is missing (no
//    fabricated image; aria-label is "Segment 1 preview" via custom label).
// 4. No horizontal overflow at 360 px viewport on the results page.
// 5. Reduced-motion navigation functional test (prefers-reduced-motion).
// 6. View-transition failure fallback: defineProperty(document, startViewTransition,
//    {value: () => { throw new Error('boom'); }, configurable: true}) and
//    verify Home -> Analyse navigation still produces exactly one history
//    entry and the correct route.
// 7. Synthetic frame extraction proof: generate a short colored canvas WebM
//    in the browser using captureStream/MediaRecorder, return the bytes to
//    the test, fulfill the proxy route with valid video/webm bytes and a
//    valid timestamps map (source_s can be 0 or 0.05 for a short clip).
//    Verify the rendered segment <img> naturalWidth > 0 (proves decode) and
//    compare the image aspect to the full frame.
// 8. Missing-map fallback test (timestamps 404) shows the fallback SVG.
// ---------------------------------------------------------------------------

const ORIGIN = 'http://127.0.0.1:3000';
const ANALYSIS_ID = 'a0000000-0000-0000-0000-000000000001';

// Minimal valid movement report fixture matching the PrototypeAnalysisResult
// schema (schema_version 0.3.0) with one completed rep and one excluded
// fragment.  Fields are derived from the MovementReport component usage.
const MOVEMENT_REPORT = {
  schema_version: '0.3.0',
  analysis_id: ANALYSIS_ID,
  exercise: 'lat_pulldown',
  detected_rep_count: 1,
  detected_rep_count_unavailable_reason: null,
  quality: {
    valid_observed_samples: 120,
    expected_supporting_samples: 150,
    per_metric_coverage: {
      'elbow_angle/estimated_3d/excursion': 0.8,
    },
  },
  reps: [
    {
      id: 'rep-1',
      ordinal: 1,
      start_s: 0.05,
      end_s: 0.45,
      completion_status: 'completed',
    },
    {
      id: 'rep-2',
      ordinal: 2,
      start_s: 0.5,
      end_s: 0.6,
      completion_status: 'excluded_partial',
    },
  ],
  metrics: [
    {
      id: 'elbow_angle/estimated_3d/excursion',
      rep_id: 'rep-1',
      value: 45.2,
      unit: 'deg',
      deviation: null,
      reference_interval: null,
      reason: null,
    },
  ],
  prototype_assessment: {
    status: 'unavailable',
    estimated_match: null,
    policy_version: null,
    omitted_components: [],
    missing_reasons: ['exercise_profile_unavailable'],
  },
  provenance: {
    reference_id: null,
    reference_name: null,
    reference_view_id: null,
    reference_review_status: null,
    reference_rep_count: null,
    matched_cycles: null,
    omitted_cycle_count: null,
    match_normalization_degrees: null,
    match_coverage_threshold: null,
    match_aggregation: null,
    calibration_status: null,
    experimental_policy_version: null,
  },
};

// Minimal analysis result fixture matching AnalysisResult.
// completion filter uses report.reps[].completion_status (actual field).
const ANALYSIS_RESULT = {
  analysis_id: ANALYSIS_ID,
  exercise: 'lat_pulldown',
  warnings: [],
  reps: [{ completion_status: 'completed' }],
};

// Minimal analysis status fixture.
const ANALYSIS_STATUS = {
  id: ANALYSIS_ID,
  state: 'succeeded',
  stage: 'complete',
  created_at: new Date().toISOString(),
  error: null,
};

// Helper: navigate to the results page with the analysis id in the URL and
// override the API routes that the page fetches on mount.  Every expected
// artifact read is fulfilled with a per-page exact path so the fixture's
// catch-all abort never blocks an expected read.
async function goToResults(
  page: Page,
  opts: {
    fulfillTimestamps?: boolean;
    fulfillProxy?: boolean;
    fulfillPose?: boolean;
  } = {},
) {
  // Override the analysis status endpoint (exact path).
  await page.route(
    `**/api/analyses/${ANALYSIS_ID}`,
    (route) => route.fulfill({ json: ANALYSIS_STATUS }),
  );

  // Override the analysis result endpoint (exact path).
  await page.route(
    `**/api/analyses/${ANALYSIS_ID}/result`,
    (route) => route.fulfill({ json: ANALYSIS_RESULT }),
  );

  // Override the movement report endpoint (exact path).
  await page.route(
    `**/api/analyses/${ANALYSIS_ID}/movement-report`,
    (route) => route.fulfill({ json: MOVEMENT_REPORT }),
  );

  // Per-page exact paths for the artifact reads.  Each is fulfilled
  // independently so the fixture's catch-all abort never aborts an
  // expected read.  pose/timestamps/proxy 404s are intentionally allowed
  // when the corresponding fulfill flag is false.
  if (opts.fulfillPose !== false) {
    await page.route(
      `**/api/analyses/${ANALYSIS_ID}/artifacts/pose`,
      (route) => route.fulfill({ status: 404, body: 'not found' }),
    );
  }
  if (opts.fulfillTimestamps) {
    // Valid timestamps map: source_s can be 0 or 0.05 for a short clip.
    const tsMap = {
      transform_version: 'ffmpeg-proxy-v1',
      source_width: 64,
      source_height: 48,
      source_rotation: 0,
      proxy_width: 64,
      proxy_height: 48,
      padding_right: 0,
      padding_bottom: 0,
      frames: [
        { source_index: 0, source_s: 0, proxy_s: 0 },
        { source_index: 1, source_s: 0.05, proxy_s: 0.05 },
        { source_index: 2, source_s: 0.1, proxy_s: 0.1 },
        { source_index: 3, source_s: 0.2, proxy_s: 0.2 },
        { source_index: 4, source_s: 0.3, proxy_s: 0.3 },
        { source_index: 5, source_s: 0.4, proxy_s: 0.4 },
        { source_index: 6, source_s: 0.5, proxy_s: 0.5 },
        { source_index: 7, source_s: 0.6, proxy_s: 0.6 },
      ],
    };
    await page.route(
      `**/api/analyses/${ANALYSIS_ID}/artifacts/timestamps`,
      (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(tsMap),
        }),
    );
  } else {
    await page.route(
      `**/api/analyses/${ANALYSIS_ID}/artifacts/timestamps`,
      (route) => route.fulfill({ status: 404, body: 'not found' }),
    );
  }
  if (opts.fulfillProxy) {
    // Proxy bytes are fulfilled by the test using a synthetic WebM produced
    // in the browser.  See the synthetic-frame test below.
  } else {
    await page.route(
      `**/api/analyses/${ANALYSIS_ID}/artifacts/proxy`,
      (route) => route.fulfill({ status: 404, body: 'not found' }),
    );
  }

  // Navigate to the results page.
  await page.goto(
    `/analyse/results?analysis=${ANALYSIS_ID}&exercise=lat_pulldown`,
  );

  // Wait for the movement report to settle (the heading is visible).
  await expect(
    page.getByRole('heading', { name: 'Movement insights', level: 2 }),
  ).toBeVisible({ timeout: 10000 });
}

test.describe('Results page – segment navigation and thumbnails', () => {
  test('segment chip strip renders completed cycles with exact name selector', async ({
    freshPage: page,
  }) => {
    await goToResults(page);

    // Exact chip selector: page.getByRole(nav Completed cycles).getByRole(button exact name)
    // to avoid Play button duplicates.
    const chipNav = page.getByRole('navigation', { name: 'Completed cycles' });
    await expect(chipNav).toBeVisible();

    const segmentChip = chipNav.getByRole('button', {
      name: 'Play video from segment 1',
      exact: true,
    });
    await expect(segmentChip).toBeVisible();

    // The chip should display the segment label and time range.
    await expect(segmentChip).toContainText('Segment 1');
    await expect(segmentChip).toContainText('0.05s');
  });

  test('segment click dispatches seek-source with correct time', async ({
    freshPage: page,
  }) => {
    await goToResults(page);

    // Listen for the custom event.
    const seekPromise = page.evaluate(
      () =>
        new Promise<number>((resolve) => {
          const handler = (ev: Event) => {
            const detail = (ev as CustomEvent<{ seconds: number }>).detail;
            resolve(detail.seconds);
          };
          window.addEventListener('mxr:seek-source', handler, { once: true });
        }),
    );

    // Click the segment chip using the exact chip selector.
    const chipNav = page.getByRole('navigation', { name: 'Completed cycles' });
    await chipNav
      .getByRole('button', { name: 'Play video from segment 1', exact: true })
      .click();

    const seconds = await seekPromise;
    expect(seconds).toBe(0.05);
  });

  test('SessionThumbnail fallback when timestamp map is missing', async ({
    freshPage: page,
  }) => {
    await goToResults(page, { fulfillTimestamps: false });

    // The chip strip should show the completed segment.
    const chipNav = page.getByRole('navigation', { name: 'Completed cycles' });
    const segmentChip = chipNav.getByRole('button', {
      name: 'Play video from segment 1',
      exact: true,
    });
    await expect(segmentChip).toBeVisible();

    // The SessionThumbnail inside the chip strip should render the fallback
    // SVG because the timestamp map fetch fails.  The wrapper is
    // aria-hidden, so use a DOM locator (not getByRole) to find the
    // fallback span by its aria-label.
    const fallback = page.locator(
      'span[role="img"][aria-label="Segment 1 preview"]',
    );
    await expect(fallback.first()).toBeVisible({ timeout: 5000 });
  });

  test('no horizontal overflow at 360 px viewport', async ({
    freshPage: page,
  }) => {
    // This test must run in the mobile360 project.
    await page.setViewportSize({ width: 360, height: 820 });
    await goToResults(page);

    const overflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth,
    );
    expect(overflow).toBe(false);
  });
});

test.describe('Reduced-motion and view-transition fallback', () => {
  test('reduced-motion navigation does not break results page', async ({
    freshPage: page,
  }) => {
    // Emulate prefers-reduced-motion.
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await goToResults(page);

    // The page should still render the movement report heading.
    await expect(
      page.getByRole('heading', { name: 'Movement insights', level: 2 }),
    ).toBeVisible();

    // The segment chip should still be interactive.
    const chipNav = page.getByRole('navigation', { name: 'Completed cycles' });
    const chip = chipNav.getByRole('button', {
      name: 'Play video from segment 1',
      exact: true,
    });
    await expect(chip).toBeVisible();
    await chip.click();

    // No error should have been thrown (the fixture checks page errors).
  });

  test('view-transition throwing fallback still navigates Home -> Analyse', async ({
    freshPage: page,
  }) => {
    // Define startViewTransition as a throwing function via
    // Object.defineProperty(document, startViewTransition, {value: () => { throw ... }, configurable: true}).
    await page.addInitScript(() => {
      Object.defineProperty(document, 'startViewTransition', {
        value: () => {
          throw new Error('view transitions unavailable');
        },
        configurable: true,
      });
    });

    // Start at home.
    await page.goto('/');
    await expect(
      page.getByRole('heading', { name: /Make your/ }),
    ).toBeVisible();

    await page.getByRole('button', { name: 'Skip intro', exact: true }).click();
    const initialHistory = await page.evaluate(() => window.history.length);
    // Click the Analyse nav button.  The throwing startViewTransition must
    // not abort navigation.
    const analyseNav = page.getByRole('navigation', { name: 'Primary' });
    await analyseNav
      .getByRole('button', { name: 'Analyse', exact: true })
      .click();

    // The Analyse page heading should be visible.
    await expect(
      page.getByRole('heading', { name: /Let.s get a clear view/ }),
    ).toBeVisible({ timeout: 5000 });

    // Exactly one history entry beyond the initial /.
    const historyLength = await page.evaluate(() => window.history.length);
    expect(historyLength).toBe(initialHistory + 1);

    // The route should be /analyse.
    const pathname = await page.evaluate(() => window.location.pathname);
    expect(pathname).toBe('/analyse');
  });
});

test.describe('Synthetic frame extraction proof', () => {
  test('renders decoded segment image from synthetic WebM proxy', async ({
    freshPage: page,
    context,
  }) => {
    // Generate a short colored canvas WebM in the browser using
    // captureStream/MediaRecorder.  Return the bytes to the test, then
    // fulfill the proxy route with valid video/webm bytes.
    const webmBytes = await page.evaluate(async () => {
      const canvas = document.createElement('canvas');
      canvas.width = 64;
      canvas.height = 48;
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error('no 2d context');
      // Fill with a solid color so the proxy has a valid first frame.
      ctx.fillStyle = '#3158e8';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // captureStream + MediaRecorder to produce a short WebM.
      const stream = (canvas as HTMLCanvasElement).captureStream(30);
      const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
      const chunks: Blob[] = [];
      recorder.ondataavailable = (ev) => {
        if (ev.data && ev.data.size > 0) chunks.push(ev.data);
      };
      const stopped = new Promise<void>((resolve) => {
        recorder.onstop = () => resolve();
      });
      recorder.start();
      // Record for ~200ms.
      await new Promise((r) => setTimeout(r, 200));
      recorder.stop();
      await stopped;
      stream.getTracks().forEach((track) => track.stop());
      const blob = new Blob(chunks, { type: 'video/webm' });
      const buf = await blob.arrayBuffer();
      return Array.from(new Uint8Array(buf));
    });

    expect(webmBytes.length).toBeGreaterThan(0);

    // Fulfill the proxy route with the synthetic WebM bytes.
    await page.route(
      `**/api/analyses/${ANALYSIS_ID}/artifacts/proxy`,
      (route) =>
        route.fulfill({
          status: 200,
          contentType: 'video/webm',
          body: Buffer.from(webmBytes),
        }),
    );

    // Navigate to results with timestamps + proxy fulfilled.
    await goToResults(page, { fulfillTimestamps: true, fulfillProxy: true });

    // The chip strip should show the completed segment.
    const chipNav = page.getByRole('navigation', { name: 'Completed cycles' });
    const segmentChip = chipNav.getByRole('button', {
      name: 'Play video from segment 1',
      exact: true,
    });
    await expect(segmentChip).toBeVisible();

    // The SessionThumbnail should render an <img> with naturalWidth > 0,
    // proving the synthetic WebM was decoded into a valid frame.
    const img = segmentChip.locator('img');
    await expect(img).toBeVisible({ timeout: 10000 });

    const naturalWidth = await img.evaluate(
      (el: HTMLImageElement) => el.naturalWidth,
    );
    const naturalHeight = await img.evaluate(
      (el: HTMLImageElement) => el.naturalHeight,
    );
    expect(naturalWidth).toBeGreaterThan(0);
    expect(naturalHeight).toBeGreaterThan(0);

    // Compare image aspect to the full frame (64:48 = 4:3).
    const aspect = naturalWidth / naturalHeight;
    expect(aspect).toBeCloseTo(64 / 48, 1);
    await page.screenshot({ path: `/results/ux9-segments-${page.viewportSize()?.width}.png`, fullPage: true });
  });
});

test.describe('Missing-map fallback', () => {
  test('timestamps 404 shows fallback SVG (no fabricated image)', async ({
    freshPage: page,
  }) => {
    await goToResults(page, { fulfillTimestamps: false });

    // The chip strip should show the completed segment.
    const chipNav = page.getByRole('navigation', { name: 'Completed cycles' });
    const segmentChip = chipNav.getByRole('button', {
      name: 'Play video from segment 1',
      exact: true,
    });
    await expect(segmentChip).toBeVisible();

    // No <img> should be rendered for the thumbnail (fallback only).
    const imgs = segmentChip.locator('img');
    const imgCount = await imgs.count();
    expect(imgCount).toBe(0);

    // The fallback SVG span should be visible.
    const fallback = page.locator(
      'span[role="img"][aria-label="Segment 1 preview"]',
    );
    await expect(fallback.first()).toBeVisible({ timeout: 5000 });
  });
});
