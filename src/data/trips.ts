import type { Station } from './stations';
import { station, STATIONS } from './stations';
import type { ScenarioConfig } from '../support/scenarios';
import { activeScenario } from '../support/scenarios';

export interface Travelers {
  adults: number;
  children: number;
}

export interface Trip {
  from: Station;
  to: Station;
  /** Days from today, resolved to a real date when the form is filled. */
  departIn: number;
  returnIn?: number;
  travelers: Travelers;
}

/** Builder for search criteria - a test sets what it cares about, everything else defaults. */
export class TripBuilder {
  private trip: Trip = {
    from: STATIONS.DAL,
    to: STATIONS.NYP,
    departIn: 2,
    travelers: { adults: 1, children: 0 },
  };

  from(station: Station): this {
    this.trip.from = station;
    return this;
  }

  to(station: Station): this {
    this.trip.to = station;
    return this;
  }

  departingIn(days: number): this {
    this.trip.departIn = days;
    return this;
  }

  returningIn(days: number): this {
    this.trip.returnIn = days;
    return this;
  }

  withTravelers(travelers: Travelers): this {
    this.trip.travelers = travelers;
    return this;
  }

  /** A fresh, independent Trip. Mutating the result never affects the builder. */
  build(): Trip {
    return { ...this.trip, travelers: { ...this.trip.travelers } };
  }
}

export function aTrip(): TripBuilder {
  return new TripBuilder();
}

/** Turns a config/scenarios.json entry into a Trip the form can be filled from. */
export function tripFromScenario(config: ScenarioConfig): Trip {
  const builder = aTrip()
    .from(station(config.from))
    .to(station(config.to))
    .departingIn(config.departIn)
    .withTravelers(config.travelers);

  if (config.returnIn !== undefined) {
    builder.returningIn(config.returnIn);
  }

  return builder.build();
}

/** The trip a single-scenario test (happy path, validation, edge cases) runs against. */
export function configuredTrip(): Trip {
  return tripFromScenario(activeScenario());
}
