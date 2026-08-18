import { test as base } from '@playwright/test';
import { HomePage } from '../pages/HomePage';

/**
 * Every test starts on the homepage with the form ready - one place for
 * navigation and overlay handling instead of a beforeEach per file.
 */
export const test = base.extend<{ homePage: HomePage }>({
  /**
   * The cookie banner can mount after navigation and blocks every click
   * until answered. addLocatorHandler watches for it independently and
   * accepts it the moment it appears, so no test needs to know it exists.
   */
  page: async ({ page }, use) => {
    await page.addLocatorHandler(page.locator('#onetrust-banner-sdk'), async () => {
      await page.locator('#onetrust-accept-btn-handler').click();
    });
    await use(page);
  },

  homePage: async ({ page }, use) => {
    const homePage = new HomePage(page);
    await homePage.open();
    await use(homePage);
  },
});

export { expect } from '@playwright/test';
