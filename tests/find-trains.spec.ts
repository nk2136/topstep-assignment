import { configuredTrip, aTrip, tripFromScenario } from '../src/data/trips';
import { STATIONS } from '../src/data/stations';
import { allScenarios } from '../src/support/scenarios';
import { daysFromToday, toInputFormat } from '../src/support/dates';
import { expect, test } from '../src/support/fixtures';

test.describe('Find trains - happy path', () => {
  test('shows the controls needed to search for a train', async ({ homePage }) => {
    const form = homePage.findTrains;

    await expect(form.from.summary()).toBeVisible();
    await expect(form.to.summary()).toBeVisible();
    await expect(form.departureDate.locator()).toBeVisible();
    await expect(form.travelers.trigger()).toBeVisible();
    await expect(form.findTrainsButton()).toBeVisible();
  });

  test('accepts the configured trip and starts a search', async ({ homePage }) => {
    // Route, dates and travelers come from config/scenarios.json, not literals here - see src/support/scenarios.ts.
    const trip = configuredTrip();
    const form = homePage.findTrains;

    await form.fill(trip);

    await expect(form.from.summary()).toContainText(trip.from.code);
    await expect(form.to.summary()).toContainText(trip.to.code);
    expect(await form.departureDate.value()).toBe(toInputFormat(daysFromToday(trip.departIn)));
    if (trip.returnIn !== undefined) {
      expect(await form.returnDate.value()).toBe(toInputFormat(daysFromToday(trip.returnIn)));
    }
    const travelerCount = trip.travelers.adults + trip.travelers.children;
    expect(await form.travelers.summary()).toContain(String(travelerCount));

    await form.expectSearchable();

    // Scope ends at the click - check the request it starts, not the results page.
    const request = await form.submitAndExpectSearchToStart();
    const body = request.postDataJSON() as {
      journeyRequest?: { journeyLegRequests?: Array<{ origin?: { code?: string } }> };
    };
    expect(body.journeyRequest?.journeyLegRequests?.[0]?.origin?.code).toBe(trip.from.code);
  });

  test('accepts a one way trip for a single traveller', async ({ homePage }) => {
    const trip = aTrip().from(STATIONS.DAL).to(STATIONS.NYP).departingIn(5).build();
    const form = homePage.findTrains;

    await form.fill(trip);

    expect(await form.departureDate.value()).toBe(toInputFormat(daysFromToday(5)));
    expect(await form.travelers.summary()).toContain('1');

    await form.expectSearchable();
    await form.submitAndExpectSearchToStart();
  });

  test('suggests matching stations as you type', async ({ homePage }) => {
    const form = homePage.findTrains;

    await form.from.enter('Dall');

    expect(await form.from.suggestionTexts()).toContain(STATIONS.DAL.suggestion);
  });

  test('swaps the departure and arrival stations', async ({ homePage }) => {
    const form = homePage.findTrains;

    await form.from.select(STATIONS.DAL);
    await form.to.select(STATIONS.NYP);

    await form.swapStationsButton().click();

    await expect(form.from.summary()).toContainText(STATIONS.NYP.code);
    await expect(form.to.summary()).toContainText(STATIONS.DAL.code);
  });

  // One test per extra route in config/scenarios.json - a new route is a new JSON entry, not a new test.
  for (const scenario of allScenarios()) {
    test(`searches a different route: ${scenario.name}`, async ({ homePage }) => {
      const trip = tripFromScenario(scenario);
      const form = homePage.findTrains;

      await form.fill(trip);

      await expect(form.from.summary()).toContainText(trip.from.code);
      await expect(form.to.summary()).toContainText(trip.to.code);
      expect(await form.departureDate.value()).toBe(toInputFormat(daysFromToday(trip.departIn)));

      await form.expectSearchable();
    });
  }
});
