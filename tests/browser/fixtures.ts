import { test as base, expect, type Page, type BrowserContext } from '@playwright/test';

interface Fixtures {
  freshPage: Page;
}

const BASE_URL = 'http://127.0.0.1:3000';

export const test = base.extend<Fixtures>({
  freshPage: async ({ page, context }, use) => {
    const errors: Error[] = [];
    page.on('pageerror', (err) => errors.push(err));

    const calls: string[] = [];
    await context.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (url.origin !== BASE_URL) {
        calls.push(`external:${route.request().method()} ${url.pathname}`);
        return route.abort();
      }
      if (url.pathname === '/api/session' && route.request().method() === 'GET') {
        return route.fulfill({ json: { csrf_token: 'qc-csrf' } });
      }
      if (url.pathname.startsWith('/api/')) {
        calls.push(`api:${route.request().method()} ${url.pathname}`);
        return route.abort();
      }
      return route.continue();
    });

    await use(page);

    expect(errors).toEqual([]);
    expect(calls).toEqual([]);
  },
});

export { expect };
