import { test, expect } from '@playwright/test';

test.describe('Deep Research Agent UI', () => {

  test('should render the landing page with the correct title and sidebar', async ({ page }) => {
    await page.goto('http://localhost:3000');

    await expect(page.locator('h1')).toContainText('Deep Research');
    await expect(page.locator('aside')).toBeVisible();
    await expect(page.locator('aside h2')).toContainText('Research Agent');
  });

  test('should mock a research query and verify UI transitions', async ({ page }) => {
    page.on('console', msg => console.log(`[Browser Console] ${msg.type()}: ${msg.text()}`));
    page.on('pageerror', err => console.error(`[Browser PageError] ${err.message}`));

    await page.route('**/api/v1/research', async route => {
      console.log('[Playwright Mock] Intercepted research request');
      const streamBody = [
        'data: {"node": "start", "session_id": "test-session"}\n\n',
        'data: {"track_id": 1, "track_text": "Mock track question", "track_status": "pending"}\n\n',
        'data: {"track_id": 1, "track_text": "Mock track question", "track_status": "searching"}\n\n',
        'data: {"node": "searcher", "source_urls": ["https://example.com/source"]}\n\n',
        'data: {"node": "filter"}\n\n',
        'data: {"track_id": 1, "track_text": "Mock track question", "track_status": "synthesizing"}\n\n',
        'data: {"track_id": 1, "track_text": "Mock track question", "track_status": "completed"}\n\n',
        'data: {"node": "end", "report": "## Mocked Research Report\\n\\nThis is a mocked success.", "metrics": {"breadth": {"sources_found": 1}}}\n\n'
      ].join('');
      
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: streamBody
      });
    });

    await page.goto('http://localhost:3000');

    const input = page.locator('textarea');
    const button = page.getByRole('button', { name: 'Start deep research' });

    await input.fill('Playwright Test Query');
    await button.click();

    const reportPanel = page.locator('.prose');
    await expect(reportPanel).toBeVisible();
    await expect(reportPanel).toContainText('Mocked Research Report');
    await expect(page.getByText('Report Ready')).toBeVisible();
  });
});
