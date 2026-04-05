// Types specific to the CEO Cockpit aggregation layer

export interface CockpitTimeOption {
  label: string;
  days: number;
}

export const TIME_OPTIONS: CockpitTimeOption[] = [
  { label: '24H', days: 1 },
  { label: '7D', days: 7 },
  { label: '14D', days: 14 },
  { label: '30D', days: 30 },
];

// Aggregated cashflow per day (derived from wallet journal)
export interface DailyCashflow {
  date: string;
  income: number;
  expenses: number;
  net: number;
}

// Helper: aggregate journal entries into daily cashflow
export function aggregateJournalByDay(
  entries: Array<{ date: string; amount: number }>
): DailyCashflow[] {
  const byDay: Record<string, { income: number; expenses: number }> = {};
  for (const e of entries) {
    const day = e.date.slice(0, 10);
    if (!byDay[day]) byDay[day] = { income: 0, expenses: 0 };
    if (e.amount > 0) byDay[day].income += e.amount;
    else byDay[day].expenses += Math.abs(e.amount);
  }
  return Object.entries(byDay)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, { income, expenses }]) => ({
      date,
      income,
      expenses,
      net: income - expenses,
    }));
}
