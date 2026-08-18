import type { Page } from '@playwright/test';
import { FindTrainsForm } from '../components/FindTrainsForm';

export class HomePage {
  static readonly path = '/home';

  readonly findTrains: FindTrainsForm;

  constructor(private readonly page: Page) {
    this.findTrains = new FindTrainsForm(page);
  }

  async open(): Promise<void> {
    await this.page.goto(HomePage.path);
    await this.dismissPromotions();
    await this.findTrains.container().waitFor();
  }

  /** Promo/sign-in popups appear on some visits, not others - only closed if actually on screen. */
  private async dismissPromotions(): Promise<void> {
    const closeButtons = [
      '.agr-callout__container_inner_close-icon',
      '.agr-popup-close',
      '.signin-register__header_close-icon',
    ];

    for (const selector of closeButtons) {
      const button = this.page.locator(`${selector}:visible`).first();
      if (await button.isVisible().catch(() => false)) {
        await button.click().catch(() => undefined);
      }
    }
  }

  /** True while the browser is still on the homepage - nothing navigated it away. */
  async isCurrent(): Promise<boolean> {
    return new URL(this.page.url()).pathname.startsWith(HomePage.path);
  }
}
