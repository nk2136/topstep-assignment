import type { Locator, Page } from '@playwright/test';
import { expect } from '@playwright/test';
import type { Station } from '../data/stations';

export type StationFieldLabel = 'From' | 'To';

/**
 * From and To are ARIA comboboxes with an async suggestion list - one class
 * serves both. Once a station is chosen, the input is replaced by a summary
 * (editing means reopening it first), and the suggestion list renders
 * outside the form, so options are looked up on the page, not the field.
 */
export class StationField {
  private readonly field: Locator;
  private readonly input: Locator;

  constructor(
    private readonly page: Page,
    root: Locator,
    private readonly label: StationFieldLabel,
    testId: string,
  ) {
    this.field = root.getByTestId(testId);
    this.input = this.field.locator('input[role="combobox"]').first();
  }

  /**
   * Types the code and confirms it stuck. A complete code usually resolves
   * on its own and collapses the input; the suggestion is only clicked if
   * the list is still open.
   */
  async select(station: Station): Promise<void> {
    await this.enter(station.code);

    const suggestion = this.suggestion(station);
    if (await suggestion.isVisible().catch(() => false)) {
      await suggestion.click();
    }

    await expect(this.field).toContainText(station.code);
  }

  /**
   * Types text without selecting a station. `fill()` sets the value but
   * never triggers the app's lookup, and real keystrokes race each other,
   * so this fills everything but the last character, then sends one real
   * keystroke for the rest - exactly one lookup, against the full text.
   */
  async enter(text: string): Promise<void> {
    await this.focus();

    if (text.length === 0) {
      await this.input.fill('');
      return;
    }

    await this.input.fill(text.slice(0, -1));
    await this.input.press(text.slice(-1));
  }

  private async focus(): Promise<void> {
    if (!(await this.input.isVisible().catch(() => false))) {
      await this.field.click();
    }
    await this.input.click();
  }

  suggestion(station: Station): Locator {
    return this.page.getByRole('option', { name: station.suggestion, exact: true });
  }

  async suggestionTexts(): Promise<string[]> {
    await this.page.getByRole('option').first().waitFor();
    return this.page.getByRole('option').allInnerTexts();
  }

  /** What a traveller sees once a station is chosen, e.g. "From DAL Dallas, TX ...". */
  summary(): Locator {
    return this.field;
  }

  locator(): Locator {
    return this.input;
  }

  /** The inline message shown once the field is left in an invalid state. */
  error(): Locator {
    return this.page.getByRole('alert').filter({ hasText: 'Enter a valid station' });
  }

  name(): StationFieldLabel {
    return this.label;
  }
}
