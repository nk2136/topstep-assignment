import type { Locator, Page } from '@playwright/test';
import { toCalendarLabel } from '../support/dates';

/**
 * Dates are picked from the calendar, not typed. The wrapper around the
 * input is what gets clicked to open it - a label sits on top of the input
 * itself and blocks a direct click.
 */
export class DateField {
  private readonly input: Locator;

  constructor(
    private readonly page: Page,
    root: Locator,
    kind: 'departed' | 'return',
  ) {
    // Round-trip mode gives the departure input the return field's test ID
    // too (confirmed in the DOM), so both would match the same locator.
    // Picker class works instead - the only place in this suite that
    // doesn't use a test ID.
    this.input = root.locator(`input.${kind}-picker`).locator('visible=true').first();
  }

  private trigger(): Locator {
    return this.input.locator('xpath=..');
  }

  async open(): Promise<void> {
    await this.trigger().click();
    await this.dayCells().first().waitFor();
  }

  async choose(date: Date): Promise<void> {
    await this.open();
    await this.dayCell(date).click();
  }

  async value(): Promise<string> {
    return this.input.inputValue();
  }

  /**
   * A day at the month boundary is rendered twice - once as the real cell,
   * once as a hidden overflow cell in the adjacent month. Both share the
   * same label, so the hidden one is excluded explicitly instead of
   * trusting `.first()` to land on the right one.
   */
  dayCell(date: Date): Locator {
    return this.page
      .getByRole('gridcell', { name: toCalendarLabel(date) })
      .and(this.page.locator(':not(.hidden)'));
  }

  private dayCells(): Locator {
    return this.page.getByRole('gridcell');
  }

  /** Dates outside the bookable window stay in the grid but are unselectable. */
  async isSelectable(date: Date): Promise<boolean> {
    const classes = (await this.dayCell(date).getAttribute('class')) ?? '';
    return !classes.includes('disabled');
  }

  locator(): Locator {
    return this.input;
  }
}
