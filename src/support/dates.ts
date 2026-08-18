/**
 * Dates are always offsets from today, never hardcoded - a fixed date would
 * pass today and fail tomorrow. Each function takes an optional reference
 * date so callers can pass a fixed one instead of `new Date()`.
 */

export function daysFromToday(days: number, referenceDate: Date = new Date()): Date {
  const date = new Date(referenceDate);
  date.setHours(12, 0, 0, 0);
  date.setDate(date.getDate() + days);
  return date;
}

/** Matches what the field actually shows, e.g. "8/19/2026" - not zero padded, despite the MM/DD/YYYY placeholder. */
export function toInputFormat(date: Date): string {
  return date.toLocaleDateString('en-US');
}

/** Matches the calendar's own day-cell label, e.g. "Wednesday, August 19, 2026", so a test can target one day directly. */
export function toCalendarLabel(date: Date): string {
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
}
