import { test, expect } from '@playwright/test';

// Kiosk viewport this terminal actually ships on.
const KIOSK_VIEWPORT = { width: 1024, height: 600 };

// Live LLM round trips observed around ~5.5s locally; give plenty of margin
// so the suite doesn't flake on a slower model/day.
const ASK_TIMEOUT = 20000;

// Console.error calls the app itself emits on purpose when a background
// (non-user-facing) fetch fails - e.g. the suggestion pool or session
// bootstrap. These are caught-and-logged, not bugs, so they're allow-listed
// rather than asserted against.
const ALLOWED_CONSOLE_ERROR_PATTERNS = [
  /Failed to load suggestion pool/,
  /Failed to start session/,
];

test.use({ viewport: KIOSK_VIEWPORT });

test.describe('Eli7 kid terminal', () => {
  // Several of these tests hit the live LLM backend. Running them in
  // parallel workers stacks concurrent /ask calls and starves the local API
  // process, pushing latency well past any reasonable timeout (observed
  // ~5.5s serial vs. 20s+ under 5-way concurrency). Serial keeps the suite
  // reliable without resorting to an arbitrarily huge timeout.
  test.describe.configure({ mode: 'serial' });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // App hydration signal: the textarea exists in every state (empty or mid-conversation).
    await expect(page.locator('textarea.input')).toBeVisible();
  });

  test('welcome state: title, subtitle, 3 chips, focused input, mascot, no reset button', async ({ page }) => {
    const title = page.locator('.empty-title');
    const subtitle = page.locator('.empty-subtitle');
    await expect(title).toBeVisible();
    await expect(title).not.toBeEmpty();
    await expect(subtitle).toBeVisible();
    await expect(subtitle).not.toBeEmpty();

    await expect(page.locator('.chip')).toHaveCount(3);

    const input = page.locator('textarea.input');
    await expect(input).toBeVisible();
    await expect(input).toBeFocused();

    await expect(page.locator('.mascot-welcome')).toBeVisible();

    await expect(page.locator('.reset-button')).toHaveCount(0);
  });

  test('ask by typing: question bubble, loading, then answer bubble', async ({ page }) => {
    const input = page.locator('textarea.input');
    const question = 'Porque é que o céu é azul?';
    await input.fill(question);

    const loading = page.locator('.loading');
    await input.press('Enter');

    await expect(page.locator('.question-text')).toHaveText(question);
    await expect(loading).toBeVisible();

    await expect(page.locator('.bubble').first()).toBeVisible({ timeout: ASK_TIMEOUT });
    await expect(loading).toHaveCount(0);
  });

  test('ask by tapping a chip submits that question (chip-tap fix guard)', async ({ page }) => {
    const firstChip = page.locator('.chip').first();
    const chipText = (await firstChip.textContent()).trim();

    await firstChip.click();

    await expect(page.locator('.question-text')).toHaveText(chipText);
    await expect(page.locator('.bubble').first()).toBeVisible({ timeout: ASK_TIMEOUT });
  });

  test('"Começar de novo": single reset button, returns to empty state, pings begin-new-topic', async ({ page }) => {
    const input = page.locator('textarea.input');
    await input.fill('O que são os sonhos?');
    await input.press('Enter');
    await expect(page.locator('.bubble').first()).toBeVisible({ timeout: ASK_TIMEOUT });

    // De-dupe guard: exactly one reset button ever renders, not one per message.
    await expect(page.locator('.reset-button')).toHaveCount(1);

    const beginNewTopicRequest = page.waitForRequest(
      (req) => req.url().includes('/begin-new-topic') && req.method() === 'POST'
    );

    await page.locator('.reset-button').click();
    await beginNewTopicRequest;

    await expect(page.locator('.empty-state')).toBeVisible();
    await expect(page.locator('.bubble')).toHaveCount(0);
    await expect(page.locator('.question-bubble')).toHaveCount(0);
    await expect(page.locator('.reset-button')).toHaveCount(0);
  });

  test('a 404 from begin-new-topic is suppressed, not surfaced as an error', async ({ page }) => {
    await page.route('**/begin-new-topic', (route) =>
      route.fulfill({ status: 404, body: 'Not Found' })
    );

    const pageErrors = [];
    page.on('pageerror', (err) => pageErrors.push(err.message));

    const input = page.locator('textarea.input');
    await input.fill('Como voam as borboletas?');
    await input.press('Enter');
    await expect(page.locator('.bubble').first()).toBeVisible({ timeout: ASK_TIMEOUT });

    await page.locator('.reset-button').click();

    // The reset flow completes normally even though the topic-boundary call 404s.
    await expect(page.locator('.empty-state')).toBeVisible();
    expect(pageErrors).toEqual([]);
  });

  test('long input: accepts 1500 chars (maxlength 2000) and keeps submit enabled', async ({ page }) => {
    const input = page.locator('textarea.input');
    await expect(input).toHaveAttribute('maxlength', '2000');

    const longText = 'a'.repeat(1500);
    await input.fill(longText);

    await expect(input).toHaveValue(longText);
    await expect(page.locator('.submit')).toBeEnabled();
  });

  test('touch targets: chip, submit, and reset-button are each >= 44px', async ({ page }) => {
    const chipBox = await page.locator('.chip').first().boundingBox();
    expect(chipBox.height).toBeGreaterThanOrEqual(44);
    expect(chipBox.width).toBeGreaterThanOrEqual(44);

    // .submit is opacity:0 (but still laid out) while disabled, so give it a
    // real value first to measure the interactable target, not the empty state.
    const input = page.locator('textarea.input');
    await input.fill('oi');
    const submitBox = await page.locator('.submit').boundingBox();
    expect(submitBox.height).toBeGreaterThanOrEqual(44);
    expect(submitBox.width).toBeGreaterThanOrEqual(44);

    // .reset-button only exists once a message is on screen.
    await input.press('Enter');
    await expect(page.locator('.bubble').first()).toBeVisible({ timeout: ASK_TIMEOUT });
    const resetBox = await page.locator('.reset-button').boundingBox();
    expect(resetBox.height).toBeGreaterThanOrEqual(44);
    expect(resetBox.width).toBeGreaterThanOrEqual(44);
  });

  test('no uncaught console errors during a normal ask flow', async ({ page }) => {
    const unexpectedErrors = [];
    page.on('console', (msg) => {
      if (msg.type() !== 'error') return;
      if (ALLOWED_CONSOLE_ERROR_PATTERNS.some((pattern) => pattern.test(msg.text()))) return;
      unexpectedErrors.push(msg.text());
    });

    const pageErrors = [];
    page.on('pageerror', (err) => pageErrors.push(err.message));

    const input = page.locator('textarea.input');
    await input.fill('O que faz as bolhas?');
    await input.press('Enter');
    await expect(page.locator('.bubble').first()).toBeVisible({ timeout: ASK_TIMEOUT });

    expect(unexpectedErrors).toEqual([]);
    expect(pageErrors).toEqual([]);
  });
});
