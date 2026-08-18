import { STATIONS } from '../src/data/stations';
import { daysFromToday } from '../src/support/dates';
import { expect, test } from '../src/support/fixtures';

/** The submit button is disabled until the form is complete - there's no error message to test, so these check the gate itself. */
test.describe('Find trains - validation', () => {
  test('cannot be searched before anything is entered', async ({ homePage }) => {
    await homePage.findTrains.expectNotSearchable();
  });

  test('stays unsearchable with only a departure station', async ({ homePage }) => {
    const form = homePage.findTrains;

    await form.from.select(STATIONS.DAL);

    await form.expectNotSearchable();
  });

  test('stays unsearchable with both stations but no departure date', async ({ homePage }) => {
    const form = homePage.findTrains;

    await form.from.select(STATIONS.DAL);
    await form.to.select(STATIONS.NYP);

    await form.expectNotSearchable();
  });

  test('becomes searchable once both stations and a departure date are set', async ({
    homePage,
  }) => {
    const form = homePage.findTrains;

    await form.from.select(STATIONS.DAL);
    await form.to.select(STATIONS.NYP);
    await form.departureDate.choose(daysFromToday(3));

    await form.expectSearchable();
  });

  test('reports text that does not match any station', async ({ homePage }) => {
    const form = homePage.findTrains;

    await form.from.enter('not a real station');
    await form.to.select(STATIONS.NYP);

    await expect(form.from.error().first()).toBeVisible();
    await form.expectNotSearchable();
    expect(await homePage.isCurrent()).toBe(true);
  });
});
