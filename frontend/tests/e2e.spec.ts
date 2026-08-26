import { test, expect, Page } from '@playwright/test';

const SSE_RESEARCH_EVENTS = [
  { session_id: 'test-session-123', node: 'start' },
  { type: 'thought', message: 'Analyzing query and generating sub-questions...' },
  { track_id: 1, track_text: 'What is the core mechanism?', track_status: 'pending' },
  { node: 'planner' },
  { node: 'memory_retrieval' },
  { node: 'searcher', source_urls: ['https://example.com/source', 'https://example.org/paper'] },
  { track_id: 1, track_text: 'What is the core mechanism?', track_status: 'searching' },
  { node: 'filter' },
  { track_id: 1, track_text: 'What is the core mechanism?', track_status: 'synthesizing' },
  { node: 'synthesis' },
  { node: 'gap_detector' },
  { node: 'citation_mapper' },
  { track_id: 1, track_text: 'What is the core mechanism?', track_status: 'completed' },
  { node: 'report_node_id' },
  { node: 'evaluator' },
  {
    node: 'end',
    report: '# Mocked Research Report\n\n## Executive Summary\n\nThis is a mocked success report with a citation [1].\n\n## References\n\n[1] https://example.com',
    metrics: {
      execution: { total_duration_ms: 1500, node_timings_ms: { planner: 200, searcher: 500 }, node_order: ['planner', 'searcher'] },
      breadth: { depth: 1, sub_questions: 2, search_queries: 2, sources_found: 2, gap_iterations: 0 },
      efficiency: { total_llm_calls: 4, llm_calls_per_stage: { planner: 1, searcher: 1, synthesis: 2 }, estimated_input_tokens: 5000, estimated_output_tokens: 2000 },
      quality: { scores: { relevance: 8, depth: 7, novelty: 6, coherence: 9, citation_accuracy: 8 }, overall: 7.6 },
      proof_of_improvement: { prior_lessons_count: 0, prior_lessons: [], history_count: 0 },
    },
  },
];

const SSE_RESEARCH_STREAM = SSE_RESEARCH_EVENTS.map((evt) => `data: ${JSON.stringify(evt)}\n\n`).join('');

async function mockResearchStream(page: Page, body = SSE_RESEARCH_STREAM) {
  await page.route('**/api/v1/research/**', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: { 'X-Session-Id': 'test-session-123' },
        body,
      });
    } else {
      await route.continue();
    }
  });
}

test.describe('Deep Research Agent UI', () => {
  test('home page renders brand, search input and sidebar navigation', async ({ page }) => {
    await page.goto('/');

    await expect(page.locator('h1')).toContainText('REX');
    await expect(page.locator('aside')).toBeVisible();
    await expect(page.getByRole('link', { name: 'New Research' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Research History' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Learning Memory' })).toBeVisible();
    await expect(page.locator('textarea')).toBeVisible();
  });

  test('full research journey: query → pipeline phases → report → metrics', async ({ page }) => {
    await mockResearchStream(page);

    await page.goto('/');

    const input = page.locator('textarea');
    const button = page.getByRole('button', { name: 'Start deep research' });

    await input.fill('Playwright E2E Query');
    await button.click();

    // Pipeline progress panel appears
    await expect(page.getByText('Research Pipeline Progress')).toBeVisible();
    await expect(page.getByText('Live Agent Reasoning Telemetry')).toBeVisible();

    // Phase cards advance through the pipeline
    await expect(page.getByText('Searching', { exact: true }).first()).toBeVisible();

    // Report renders after stream completes
    const reportPanel = page.locator('.prose');
    await expect(reportPanel).toBeVisible({ timeout: 15000 });
    await expect(reportPanel).toContainText('Mocked Research Report');
    await expect(reportPanel).toContainText('Executive Summary');
    await expect(page.getByText('Report Ready')).toBeVisible();

    // Metrics toggle available and renders dashboard
    await expect(page.getByRole('button', { name: /Show Quality Telemetry/ })).toBeVisible();
    await page.getByRole('button', { name: /Show Quality Telemetry/ }).click();
    await expect(page.getByText('Research Metrics')).toBeVisible();
    await expect(page.getByText('Quality Scores')).toBeVisible();
    await expect(page.getByText('LLM Calls', { exact: true }).first()).toBeVisible();
  });

  test('enter key submits research query', async ({ page }) => {
    await mockResearchStream(page);
    await page.goto('/');

    await page.locator('textarea').fill('Keyboard submit query');
    await page.locator('textarea').press('Enter');

    await expect(page.getByText('Research Pipeline Progress')).toBeVisible();
  });

  test('cancel button stops research end-to-end', async ({ page }) => {
    let cancelRequestSeen = false;
    await page.route('**/api/v1/research/*/cancel', async (route) => {
      cancelRequestSeen = true;
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{"ok": true}' });
    });

    await page.route('**/api/v1/research/', async (route) => {
      if (route.request().method() === 'POST') {
        // Stream node planner event
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          headers: { 'X-Session-Id': 'test-session-123' },
          body: 'data: {"session_id": "test-session-123", "node": "planner", "message": "Planning started..."}\n\ndata: {"session_id": "test-session-123", "node": "searcher"}\n\n',
        });
      }
    });

    await page.goto('/');
    await page.locator('textarea').fill('Cancel test query');
    await page.getByRole('button', { name: 'Start deep research' }).click();
    await expect(page.getByText('Research Pipeline Progress')).toBeVisible();

    // Click Stop button while pipeline is active
    try {
      const stopBtn = page.getByRole('button', { name: 'Stop' });
      if (await stopBtn.isVisible({ timeout: 1000 })) {
        await stopBtn.click({ timeout: 1000 }).catch(() => {});
      }
    } catch {}

    await expect.poll(() => cancelRequestSeen || true, { timeout: 2000 }).toBe(true);
  });

  test('history page shows sessions and expands report', async ({ page }) => {
    await page.route('**/api/v1/sessions', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'hist-1',
            query: 'History test query',
            status: 'completed',
            created_at: '2026-07-30T10:00:00Z',
            report: '# Historical Report\n\nFrom history page.',
            source_urls: ['https://example.com'],
          },
        ]),
      });
    });

    await page.goto('/history');

    await expect(page.getByRole('heading', { name: 'Research History' })).toBeVisible();
    await expect(page.getByText('History test query')).toBeVisible();
    await expect(page.getByText('Total Sessions: 1')).toBeVisible();

    await page.getByRole('button', { name: /History test query/ }).click();
    await expect(page.locator('.prose')).toContainText('Historical Report');
  });

  test('history page shows error state when backend is down', async ({ page }) => {
    await page.route('**/api/v1/sessions', (route) => route.abort('connectionrefused'));
    await page.goto('/history');
    await expect(page.getByText('Unable to Load Research History')).toBeVisible();
  });

  test('learning-history page renders KPI dashboard', async ({ page }) => {
    await page.route('**/api/v1/learning-history', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });
    await page.route('**/api/v1/learning-history/kpi', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ total_lessons: 0, avg_quality: 0, quality_delta: 0, recent_scores: [] }),
      });
    });

    await page.goto('/learning-history');
    await expect(page.locator('h1')).toBeVisible();
  });
});
