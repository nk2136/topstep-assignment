# Amtrak Find Trains - Test Suite

Playwright + TypeScript tests for the "Find trains" search form on [amtrak.com/home](https://www.amtrak.com/home).

Scope is just the search form, up through clicking "Find trains." Nothing here touches the results page or the booking flow.

## Requirements

- Node.js 18+
- Internet access (tests run against amtrak.com)

## How to run this

1. Install dependencies:
   ```bash
   npm install
   ```
2. Install the browser Playwright needs:
   ```bash
   npx playwright install chromium
   ```
3. Run the tests:
   ```bash
   npm test
   ```

That's it. A full run takes under a minute. If something fails, an HTML report opens automatically with a screenshot, video, and trace for that test - run `npm run report` to see it again later.

Other commands:

| Command                           | What it does                                                   |
| --------------------------------- | -------------------------------------------------------------- |
| `npm run test:headed`             | Same tests, but you can watch the browser                      |
| `npm run test:ui`                 | Playwright's interactive test runner                           |
| `npm run lint` / `npm run format` | ESLint / Prettier                                              |
| `npm run typecheck`               | Type check only, no test run                                   |
| `npm run check`                   | Everything above plus the full test run - this is what CI runs |

To run against a different environment:

```bash
BASE_URL=https://www.amtrak.com npm test
```

## Changing what gets tested

The route, dates, and number of travelers aren't hardcoded in the test files. They come from [`config/scenarios.json`](config/scenarios.json), and you can override any of it from the command line:

```bash
TRIP_FROM=WAS TRIP_TO=PHL TRIP_ADULTS=1 TRIP_CHILDREN=0 npm test
```

| Variable                           | What it controls                                                 |
| ---------------------------------- | ---------------------------------------------------------------- |
| `TRIP_FROM`, `TRIP_TO`             | Station codes - see `src/data/stations.ts`                       |
| `TRIP_DEPART_IN`, `TRIP_RETURN_IN` | Days from today. Leave `TRIP_RETURN_IN` unset for a one-way trip |
| `TRIP_ADULTS`, `TRIP_CHILDREN`     | How many travelers                                               |

There's also a `scenarios` list in that same file, for extra routes to check beyond the default one - `find-trains.spec.ts` runs one test per entry, so adding coverage for a new route is just adding a line to the JSON, no new test code.

## Project layout

```
config/
  scenarios.json          The trip data tests run against (see above)
src/
  pages/HomePage.ts        Loads the page, deals with popups
  components/
    FindTrainsForm.ts      Fills out the whole form from a Trip object
    StationField.ts        The From / To boxes
    DateField.ts            The date pickers
    TravelerPanel.ts       Adult / child / senior counters
  data/
    stations.ts             Known station codes
    trips.ts                 Trip model + builder
  support/
    dates.ts                 Date math helpers
    scenarios.ts              Reads config/scenarios.json + env vars
    fixtures.ts               Test setup (cookie banner, opening the page)
tests/
  find-trains.spec.ts       Happy path, plus one test per extra route in config/scenarios.json
  validation.spec.ts        When the search button is and isn't clickable
  edge-cases.spec.ts         Traveler limits, past dates, same station twice
```

The form is really six separate widgets glued together (two station boxes, two date pickers, a traveler panel, a submit button), and the same station box shows up in three different places on the page. So instead of one giant page object, each widget is its own small class, and `FindTrainsForm` just wires them together. Adding a new widget later means adding a new class, not editing an existing one.

## What I tested and why

- **Happy path** - fill out the form, submit, confirm a real search request actually goes out. Also covers the autocomplete suggestions and the swap button.
- **Validation** - the submit button is `aria-disabled` with `pointer-events: none` while the form is incomplete, so a real user can't click it at all and there's no error message to test for. These tests just check the button's disabled/enabled state at each step instead of asserting error text that never appears.
- **Edge cases** - the 9-traveler cap (proved with a mixed 5 adults + 4 children, not just 9 of one type, since that's what shows it's a total and not a per-category limit), needing an adult if a child is booked, no past dates, can't pick the same station twice.
- **Scenarios** - the same flow run across a few different routes from `config/scenarios.json`, to show the approach scales past one hardcoded example.

Not tested, on purpose: results page, booking/payment, sign in, promo codes, the "Find schedule" and "Train status" tabs.

`DateField.ts` is the one place that locates by CSS class instead of test ID - see the comment there for why.

## Assumptions

- Testing against production is fine here - nothing books a real ticket or charges anything.
- DAL, NYP, WAS, and PHL are the station codes used as test data; more can be added in `stations.ts`.
- Dates are always relative ("2 days from now"), never hardcoded, so the suite doesn't rot.
- Chromium only for now - more browsers are one line in `playwright.config.ts`.
- Cookie consent is auto-accepted so it never blocks a test.

## What I'd do differently with more time

- **Assert against the results page too**, not just that the search request went out - a second page object, and past the scope of this exercise.
- **Cross-browser and mobile.** Firefox/WebKit are one entry each in `playwright.config.ts`; mobile is worth its own project since the page actually renders a different Find Trains button there, not just a resized layout.
- **Fetch station codes through a fixture instead of hardcoding them.** A fixture that calls an API for the current station list before a test runs would make that list available to every test dynamically - any new station that needs to be tested becomes available automatically, without anyone editing this file.
- **Add a thin API-level check alongside the UI test** - hit the search request's endpoint directly instead of only through the browser, for a faster, more stable layer under the UI tests.
- **Track flake over time.** A test that fails once and passes on retry is a real signal worth watching, not just something the retry quietly absorbs.
- **Run the suite on a schedule**, not just on push - a nightly run would catch Amtrak changing their markup before a real PR does.
- **Add accessibility checks** (axe) against the form.
- **Handle multiple environments (QA, dev, UAT) with their own URLs and credentials.** `BASE_URL` already lets a run target a different host; the rest would be a small per-environment config plus credentials read from environment variables or CI secrets, never committed - and `storageState` to authenticate once per environment instead of logging in on every test, once there's a login flow to test.
