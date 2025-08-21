import { test, expect } from '@playwright/test';

test.describe('Soft Terminal Curious Mode E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  // Visual & Layout Tests
  test('app fills viewport with no chrome', async ({ page }) => {
    const app = page.locator('.app');
    await expect(app).toBeVisible();
    
    // Check full-screen layout
    const box = await app.boundingBox();
    const viewport = page.viewportSize();
    expect(box.width).toBe(viewport.width);
    expect(box.height).toBe(viewport.height);
  });

  test('feed is centered and prompt is sticky at bottom', async ({ page }) => {
    const feed = page.locator('.feed');
    const promptSection = page.locator('.prompt-section');
    
    await expect(feed).toBeVisible();
    await expect(promptSection).toBeVisible();
    
    // Check prompt is at bottom
    const promptBox = await promptSection.boundingBox();
    const viewport = page.viewportSize();
    expect(promptBox.y + promptBox.height).toBeCloseTo(viewport.height, 50);
  });

  test('mobile viewport has proper hit targets', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    const chips = page.locator('.chip').first();
    if (await chips.isVisible()) {
      const chipBox = await chips.boundingBox();
      expect(chipBox.height).toBeGreaterThanOrEqual(44);
    }
    
    const inputBar = page.locator('.input-bar');
    const inputBox = await inputBar.boundingBox();
    expect(inputBox.height).toBeGreaterThanOrEqual(44);
  });

  // Interaction Tests
  test('two-second test: can type within 2s', async ({ page }) => {
    const startTime = Date.now();
    
    // Wait for input to be ready
    const input = page.locator('.input-field');
    await expect(input).toBeVisible();
    await expect(input).toBeEnabled();
    
    // Type into input
    await input.fill('Test');
    
    const elapsed = Date.now() - startTime;
    expect(elapsed).toBeLessThan(2000);
    
    // Check caret is visible when input is empty
    await input.clear();
    const caret = page.locator('.input-caret');
    await expect(caret).toBeVisible();
  });

  test('ask flow: complete question and answer cycle', async ({ page }) => {
    // Type question
    const input = page.locator('.input-field');
    await input.fill('How do rainbows form?');
    
    // Submit with Enter
    await input.press('Enter');
    
    // Wait for first bubble (within 3s)
    const answerBubble = page.locator('.answer-bubble').first();
    await expect(answerBubble).toBeVisible({ timeout: 3000 });
    
    // Check chunks are present and limited
    const chunks = page.locator('.answer-chunk');
    const chunkCount = await chunks.count();
    expect(chunkCount).toBeGreaterThan(0);
    expect(chunkCount).toBeLessThanOrEqual(3); // First response is 2-3 sentences
    
    // Check for More button
    const moreButton = page.locator('.more-button');
    const moreCount = await moreButton.count();
    
    if (moreCount > 0) {
      // More button should be attached to bubble
      await expect(moreButton).toBeVisible();
      await expect(moreButton).toContainText('More?');
      
      // Click More
      await moreButton.click();
      
      // Wait for additional chunks
      await page.waitForTimeout(1000);
      const newChunkCount = await chunks.count();
      expect(newChunkCount).toBeGreaterThan(chunkCount);
    }
  });

  test('starter seeds: visible and clickable', async ({ page }) => {
    // Check chips are visible on empty state
    const chips = page.locator('.chip');
    await expect(chips.first()).toBeVisible();
    
    const chipCount = await chips.count();
    expect(chipCount).toBeGreaterThanOrEqual(2);
    expect(chipCount).toBeLessThanOrEqual(4);
    
    // Click a chip
    const firstChip = chips.first();
    const chipText = await firstChip.textContent();
    await firstChip.click();
    
    // Should fill input and submit
    const input = page.locator('.input-field');
    await page.waitForTimeout(200); // Wait for auto-submit
    
    // Should see answer
    const answerBubble = page.locator('.answer-bubble');
    await expect(answerBubble).toBeVisible({ timeout: 5000 });
  });

  test('keyboard navigation', async ({ page }) => {
    const input = page.locator('.input-field');
    
    // Tab through chips to input
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    
    // Should reach input
    await expect(input).toBeFocused();
    
    // Type something
    await input.fill('Test question with\nmultiple lines');
    
    // Shift+Enter should add newline (already done above)
    const value = await input.inputValue();
    expect(value).toContain('\n');
    
    // Escape should clear
    await page.keyboard.press('Escape');
    const clearedValue = await input.inputValue();
    expect(clearedValue).toBe('');
    
    // Enter should submit
    await input.fill('Why is the sky blue?');
    await page.keyboard.press('Enter');
    
    const answerBubble = page.locator('.answer-bubble');
    await expect(answerBubble).toBeVisible({ timeout: 5000 });
  });

  test('reduced motion respects preference', async ({ page }) => {
    // Enable reduced motion
    await page.emulateMedia({ reducedMotion: 'reduce' });
    
    // Submit a question
    const input = page.locator('.input-field');
    await input.fill('Test question');
    await input.press('Enter');
    
    // Check animations are instant
    const bubble = page.locator('.bubble-group').first();
    await expect(bubble).toBeVisible();
    
    // More button should not have animation
    const moreButton = page.locator('.more-button');
    if (await moreButton.isVisible()) {
      const animationStyle = await moreButton.evaluate(el => 
        window.getComputedStyle(el).animation
      );
      expect(animationStyle).toContain('none');
    }
  });

  // Content Tests
  test('content sanity: no links, simple language', async ({ page }) => {
    // Submit a question
    const input = page.locator('.input-field');
    await input.fill('What is a volcano?');
    await input.press('Enter');
    
    // Wait for answer
    const answerBubble = page.locator('.answer-bubble').first();
    await expect(answerBubble).toBeVisible({ timeout: 5000 });
    
    const answerText = await answerBubble.textContent();
    
    // Check no links
    expect(answerText).not.toContain('http://');
    expect(answerText).not.toContain('https://');
    expect(answerText).not.toContain('www.');
    
    // Check for parenthetical definitions
    if (answerText.includes('volcano')) {
      expect(answerText).toMatch(/\(means:.*?\)/);
    }
    
    // Check simplified language (no complex terms without explanation)
    const complexTerms = ['approximately', 'degrees', 'intersect'];
    for (const term of complexTerms) {
      if (answerText.toLowerCase().includes(term)) {
        // Should be replaced or explained
        expect(answerText).toMatch(/about|halfway|meet/i);
      }
    }
  });

  // Performance Tests
  test('performance: first chunk within 3s', async ({ page }) => {
    const input = page.locator('.input-field');
    await input.fill('Why do cats purr?');
    
    const startTime = Date.now();
    await input.press('Enter');
    
    // Wait for first chunk
    const firstChunk = page.locator('.answer-chunk').first();
    await expect(firstChunk).toBeVisible({ timeout: 3000 });
    
    const elapsed = Date.now() - startTime;
    expect(elapsed).toBeLessThan(3000);
    
    // Log performance
    console.log(`First chunk latency: ${elapsed}ms`);
  });

  test('responsive rendering during text appearance', async ({ page }) => {
    const input = page.locator('.input-field');
    
    // Submit multiple questions quickly
    for (let i = 0; i < 3; i++) {
      await input.fill(`Question ${i + 1}: What is rain?`);
      await input.press('Enter');
      await page.waitForTimeout(500);
    }
    
    // Input should remain responsive
    await input.fill('Still responsive');
    await expect(input).toHaveValue('Still responsive');
    
    // Check no layout jank
    const feedContainer = page.locator('.feed-container');
    const scrollHeight = await feedContainer.evaluate(el => el.scrollHeight);
    expect(scrollHeight).toBeGreaterThan(0);
  });

  // Error States
  test('network error shows friendly message', async ({ page }) => {
    // Simulate network error by going offline
    await page.context().setOffline(true);
    
    const input = page.locator('.input-field');
    await input.fill('Test question');
    await input.press('Enter');
    
    // Should show error message
    const error = page.locator('.error-message');
    await expect(error).toBeVisible();
    await expect(error).toContainText("couldn't think");
    
    // Retry button should be present
    const retry = page.locator('.retry-button');
    await expect(retry).toBeVisible();
    
    // Go back online and retry
    await page.context().setOffline(false);
    await retry.click();
    
    // Error should disappear
    await expect(error).not.toBeVisible();
  });

  // Welcome State
  test('welcome state shows friendly message and chips', async ({ page }) => {
    // Check welcome message
    const welcome = page.locator('.welcome');
    await expect(welcome).toBeVisible();
    await expect(welcome).toContainText('wondering');
    
    // Check chips are present
    const chips = page.locator('.chip');
    const chipCount = await chips.count();
    expect(chipCount).toBeGreaterThanOrEqual(3);
    
    // Chips should have kid-friendly questions
    const firstChipText = await chips.first().textContent();
    expect(firstChipText).toMatch(/\?$/); // Should end with question mark
  });

  // Idle State
  test('idle state shows prompt after 20s', async ({ page, browserName }) => {
    // Skip this test in CI as it takes too long
    test.skip(browserName === 'webkit', 'Skipping long test in WebKit');
    
    // Submit a question first
    const input = page.locator('.input-field');
    await input.fill('Quick test');
    await input.press('Enter');
    
    // Wait for answer
    await page.locator('.answer-bubble').first().waitFor();
    
    // Wait for idle (20s)
    await page.waitForTimeout(21000);
    
    // Should show idle prompt chip
    const chips = page.locator('.chip');
    const chipVisible = await chips.first().isVisible();
    
    if (chipVisible) {
      const chipText = await chips.first().textContent();
      expect(chipText).toMatch(/Try:|Ask:|Wonder:|Curious/);
    }
  });
});