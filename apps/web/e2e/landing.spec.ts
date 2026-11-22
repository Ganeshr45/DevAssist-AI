import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('landing page presents the product and primary destinations', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /make the hard parts clear/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /open assistant/i })).toHaveAttribute('href', '/dashboard');
  await expect(page.getByRole('link', { name: /explore knowledge base/i })).toHaveAttribute('href', '/knowledge');
});

test('landing page has no WCAG 2.2 AA axe violations', async ({ page }) => {
  await page.goto('/');
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  expect(results.violations).toEqual([]);
});
