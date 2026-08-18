import { STATIONS } from '../src/data/stations';
import { daysFromToday } from '../src/support/dates';
import { expect, test } from '../src/support/fixtures';

test.describe('Find trains - edge cases', () => {
  test('will not take a booking beyond nine travellers, across categories', async ({
    homePage,
  }) => {
    const travelers = homePage.findTrains.travelers;

    // Mixed composition, not nine of one type - proves the cap is a total, not per category.
    await travelers.setCount('adult', 5);
    await travelers.setCount('child', 4);

    expect(await travelers.countOf('adult')).toBe(5);
    expect(await travelers.countOf('child')).toBe(4);

    for (const type of ['adult', 'senior', 'youth', 'child', 'infant'] as const) {
      await expect(travelers.addButton(type)).toBeDisabled();
    }
    await expect(
      travelers.message(/Call 1-800-USA-RAIL to make reservations for 9 to 14 travelers/),
    ).toBeVisible();
  });

  test('asks for an adult when only children are travelling', async ({ homePage }) => {
    const travelers = homePage.findTrains.travelers;

    await travelers.setCount('child', 2);
    await travelers.setCount('adult', 0);

    await expect(travelers.message(/Add at least one adult 18 years old or older/)).toBeVisible();
  });

  test('does not offer a departure date in the past', async ({ homePage }) => {
    const departureDate = homePage.findTrains.departureDate;

    await departureDate.open();

    expect(await departureDate.isSelectable(daysFromToday(-1))).toBe(false);
  });

  test('does not allow the same station for departure and arrival', async ({ homePage }) => {
    const form = homePage.findTrains;

    await form.from.select(STATIONS.DAL);
    await form.to.select(STATIONS.DAL);
    await form.departureDate.choose(daysFromToday(3));

    await form.expectNotSearchable();
    expect(await homePage.isCurrent()).toBe(true);
  });
});
