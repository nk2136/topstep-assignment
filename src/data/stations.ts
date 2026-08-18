export interface Station {
  /** Three letter code, e.g. "DAL". */
  code: string;
  /** Exact autocomplete text - needed because a code search also returns unrelated businesses. */
  suggestion: string;
}

/** Stations this suite knows about. Add one here to use it in a test. */
export const STATIONS = {
  DAL: { code: 'DAL', suggestion: 'Dallas, TX - Eddie Bernice Johnson Union Sta (DAL)' },
  NYP: { code: 'NYP', suggestion: 'New York, NY - Moynihan Train Hall at Penn Sta. (NYP)' },
  WAS: { code: 'WAS', suggestion: 'Washington, DC - Union Station (WAS)' },
  PHL: { code: 'PHL', suggestion: 'Philadelphia, PA - William H. Gray III 30th St. Station (PHL)' },
} as const satisfies Record<string, Station>;

export type StationCode = keyof typeof STATIONS;

/** Looks a station up by code. An unknown code fails to compile, not to run. */
export function station(code: StationCode): Station {
  return STATIONS[code];
}
