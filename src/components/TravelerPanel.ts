import type { Locator } from '@playwright/test';

export type TravelerType = 'adult' | 'senior' | 'youth' | 'child' | 'infant';

/**
 * One stepper per passenger type. Two rules apply that nothing else on the
 * form hints at: a booking caps at nine travelers total, and needs at least
 * one adult whenever a child is on it.
 */
export class TravelerPanel {
  constructor(private readonly root: Locator) {}

  trigger(): Locator {
    return this.root.getByTestId('traveler-dropdown-button').locator('visible=true');
  }

  private panel(): Locator {
    return this.root.locator('app-traveler');
  }

  async open(): Promise<void> {
    if (await this.addButton('adult').isVisible()) return;
    await this.trigger().click();
    await this.addButton('adult').waitFor();
  }

  async close(): Promise<void> {
    await this.panel().getByRole('button', { name: 'Close' }).click();
  }

  addButton(type: TravelerType): Locator {
    return this.panel().getByRole('button', { name: `+ Add ${type}`, exact: true });
  }

  removeButton(type: TravelerType): Locator {
    return this.panel().getByRole('button', { name: `- Remove ${type}`, exact: true });
  }

  async add(type: TravelerType, times = 1): Promise<void> {
    await this.open();
    for (let i = 0; i < times; i++) {
      await this.addButton(type).click();
    }
  }

  async remove(type: TravelerType, times = 1): Promise<void> {
    await this.open();
    for (let i = 0; i < times; i++) {
      await this.removeButton(type).click();
    }
  }

  async setCount(type: TravelerType, target: number): Promise<void> {
    await this.open();
    const current = await this.countOf(type);
    const difference = target - current;
    if (difference > 0) await this.add(type, difference);
    if (difference < 0) await this.remove(type, -difference);
  }

  async countOf(type: TravelerType): Promise<number> {
    await this.open();
    // Found by label, not position - a fixed index would assume the
    // steppers always render in the same order. Second input is a
    // screen-reader duplicate of the same value.
    const label = type.charAt(0).toUpperCase() + type.slice(1);
    const value = this.panel()
      .getByRole('group', { name: new RegExp(`^${label}\\b`) })
      .locator('input.value:not(.sr-only)');
    return Number(await value.inputValue());
  }

  /** The text on the closed dropdown, e.g. "4 Travelers". */
  async summary(): Promise<string> {
    return (await this.trigger().innerText()).replace(/\s+/g, ' ').trim();
  }

  /** Rendered twice (visible + screen-reader live region) - this asserts the visible copy. */
  message(text: string | RegExp): Locator {
    return this.panel().getByText(text).locator('visible=true').first();
  }
}
