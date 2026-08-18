import scenariosFile from '../../config/scenarios.json';
import type { StationCode } from '../data/stations';

export interface ScenarioConfig {
  name: string;
  from: StationCode;
  to: StationCode;
  departIn: number;
  returnIn?: number;
  travelers: { adults: number; children: number };
}

/**
 * Route, dates and passenger count come from config/scenarios.json, not
 * literals in test files - override any of it per run:
 *
 *   TRIP_FROM=WAS TRIP_TO=PHL TRIP_ADULTS=1 TRIP_CHILDREN=0 npm test
 *
 * Env var wins over the file's `default` entry. An empty env var counts as
 * unset, not coerced to 0 - a return date of "today" would be earlier than
 * the departure date and quietly break the request.
 */
export function activeScenario(): ScenarioConfig {
  const defaults = scenariosFile.default;

  return {
    name: 'configured trip',
    from: (envValue('TRIP_FROM') as StationCode | undefined) ?? (defaults.from as StationCode),
    to: (envValue('TRIP_TO') as StationCode | undefined) ?? (defaults.to as StationCode),
    departIn: numberOrDefault('TRIP_DEPART_IN', defaults.departIn),
    returnIn: optionalNumberOrDefault('TRIP_RETURN_IN', defaults.returnIn),
    travelers: {
      adults: numberOrDefault('TRIP_ADULTS', defaults.travelers.adults),
      children: numberOrDefault('TRIP_CHILDREN', defaults.travelers.children),
    },
  };
}

/** An unset or empty-string environment variable is treated as not provided. */
function envValue(key: string): string | undefined {
  const value = process.env[key];
  return value === undefined || value === '' ? undefined : value;
}

function numberOrDefault(key: string, defaultValue: number): number {
  const value = envValue(key);
  return value === undefined ? defaultValue : Number(value);
}

function optionalNumberOrDefault(
  key: string,
  defaultValue: number | undefined,
): number | undefined {
  const value = envValue(key);
  return value === undefined ? defaultValue : Number(value);
}

export function allScenarios(): ScenarioConfig[] {
  return scenariosFile.scenarios as ScenarioConfig[];
}
