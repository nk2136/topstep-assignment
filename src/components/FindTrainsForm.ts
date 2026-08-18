import type { Locator, Page, Request } from '@playwright/test';
import { expect } from '@playwright/test';
import type { Trip } from '../data/trips';
import { daysFromToday } from '../support/dates';
import { DateField } from './DateField';
import { StationField } from './StationField';
import { TravelerPanel } from './TravelerPanel';

/** Composes the whole Find trains widget, scoped to its root element. */
export class FindTrainsForm {
  readonly from: StationField;
  readonly to: StationField;
  readonly departureDate: DateField;
  readonly returnDate: DateField;
  readonly travelers: TravelerPanel;

  private readonly root: Locator;

  constructor(private readonly page: Page) {
    this.root = page.getByTestId('fare-finder-cmp');
    this.from = new StationField(page, this.root, 'From', 'fare-finder-from-station-field-page');
    this.to = new StationField(page, this.root, 'To', 'fare-finder-to-station-field-page');
    this.departureDate = new DateField(page, this.root, 'departed');
    this.returnDate = new DateField(page, this.root, 'return');
    this.travelers = new TravelerPanel(this.root);
  }

  /** Two copies exist (desktop/mobile); matching on visibility picks whichever one is rendered. */
  findTrainsButton(): Locator {
    return this.root.getByTestId('fare-finder-findtrains-button').locator('visible=true');
  }

  swapStationsButton(): Locator {
    return this.root.locator('button.station-swap-button').locator('visible=true');
  }

  /** Turns a one way search into a round trip and reveals the return picker. */
  addReturnDateButton(): Locator {
    return this.root.getByRole('button', { name: 'Return Date', exact: true });
  }

  /** Waits until the button is genuinely clickable, using Playwright's own actionability check. */
  async expectSearchable(): Promise<void> {
    await expect(this.findTrainsButton()).toBeEnabled();
  }

  /** Waits until the form blocks a search - the button's real accessible state. */
  async expectNotSearchable(): Promise<void> {
    await expect(this.findTrainsButton()).toBeDisabled();
  }

  /** Fills the whole form from a Trip, skipping the parts it does not specify. */
  async fill(trip: Trip): Promise<void> {
    await this.from.select(trip.from);
    await this.to.select(trip.to);

    await this.departureDate.choose(daysFromToday(trip.departIn));

    if (trip.returnIn !== undefined) {
      await this.addReturnDateButton().click();
      await this.returnDate.choose(daysFromToday(trip.returnIn));
    }

    await this.setTravelers(trip);
  }

  private async setTravelers(trip: Trip): Promise<void> {
    const { adults, children } = trip.travelers;
    if (adults === 1 && children === 0) return; // already the default

    await this.travelers.setCount('adult', adults);
    await this.travelers.setCount('child', children);
    await this.travelers.close();
  }

  /** Clicks Find Trains and waits for the search request it starts, proving the click did something. */
  async submitAndExpectSearchToStart(): Promise<Request> {
    const searchRequest = this.page.waitForRequest(
      (request) =>
        request.method() === 'POST' &&
        new URL(request.url()).pathname === '/dotcom/journey-solution-option',
    );

    const [request] = await Promise.all([searchRequest, this.findTrainsButton().click()]);
    return request;
  }

  container(): Locator {
    return this.root;
  }
}
