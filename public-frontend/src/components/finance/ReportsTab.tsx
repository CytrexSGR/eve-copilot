/**
 * ReportsTab Component
 *
 * Financial reports view with income/expense breakdowns and P&L summary.
 * Uses CSS-only horizontal bar charts for visualization.
 */

import { useState, useEffect } from 'react';
import { reportsApi } from '../../services/api/finance';
import type { IncomeBreakdown, ExpenseSummary, PnlReport } from '../../types/finance';
import { formatIsk } from '../../types/finance';

const PERIOD_OPTIONS = [7, 14, 30, 60, 90];

function toISODate(date: Date): string {
  return date.toISOString().split('T')[0];
}

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return toISODate(d);
}

// ==================== Styles ====================

const cardStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: 8,
  padding: '1rem',
};

const headingStyle: React.CSSProperties = {
  margin: '0 0 0.75rem 0',
  fontSize: '0.95rem',
  fontWeight: 600,
  color: 'var(--text-primary)',
};

const rowStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '0.4rem 0',
  borderBottom: '1px solid var(--border-color)',
  fontSize: '0.85rem',
};

const iskGreen: React.CSSProperties = {
  fontFamily: 'monospace',
  color: '#3fb950',
  fontWeight: 600,
  fontSize: '0.85rem',
};

const iskRed: React.CSSProperties = {
  fontFamily: 'monospace',
  color: '#f85149',
  fontWeight: 600,
  fontSize: '0.85rem',
};

const labelDim: React.CSSProperties = {
  color: 'var(--text-secondary)',
  fontSize: '0.75rem',
};

const selectStyle: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-color)',
  borderRadius: 4,
  color: 'var(--text-primary)',
  padding: '0.3rem 0.5rem',
  fontSize: '0.85rem',
};

const inputStyle: React.CSSProperties = {
  ...selectStyle,
  width: 130,
};

// ==================== Sub-components ====================

function BarRow({
  label,
  amount,
  count,
  percent,
  barWidth,
  color,
}: {
  label: string;
  amount: number;
  count: number;
  percent: number;
  barWidth: number;
  color: string;
}) {
  return (
    <div style={rowStyle}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ marginBottom: 4, color: 'var(--text-primary)' }}>{label}</div>
        <div
          style={{
            height: 8,
            borderRadius: 4,
            background: 'var(--bg-primary, #161b22)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${Math.min(barWidth, 100)}%`,
              height: '100%',
              borderRadius: 4,
              background: color,
              transition: 'width 0.4s ease',
            }}
          />
        </div>
      </div>
      <div style={{ textAlign: 'right', marginLeft: '1rem', whiteSpace: 'nowrap' }}>
        <div style={{ fontFamily: 'monospace', fontWeight: 600, color, fontSize: '0.85rem' }}>
          {formatIsk(Math.abs(amount))}
        </div>
        <div style={labelDim}>{count} txn &middot; {percent.toFixed(1)}%</div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  color,
}: {
  title: string;
  value: number;
  color: string;
}) {
  return (
    <div
      style={{
        ...cardStyle,
        flex: 1,
        textAlign: 'center',
        minWidth: 160,
      }}
    >
      <div style={{ ...labelDim, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 1 }}>
        {title}
      </div>
      <div style={{ fontFamily: 'monospace', fontSize: '1.3rem', fontWeight: 700, color }}>
        {formatIsk(Math.abs(value))}
      </div>
    </div>
  );
}

function LoadingPlaceholder() {
  return (
    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
      Loading...
    </div>
  );
}

function EmptyPlaceholder({ message }: { message: string }) {
  return (
    <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
      {message}
    </div>
  );
}

// ==================== Main Component ====================

export function ReportsTab({ corpId }: { corpId: number }) {
  const [days, setDays] = useState(30);
  const [income, setIncome] = useState<IncomeBreakdown[] | null>(null);
  const [expenses, setExpenses] = useState<ExpenseSummary[] | null>(null);
  const [pnl, setPnl] = useState<PnlReport | null>(null);
  const [loadingIncome, setLoadingIncome] = useState(true);
  const [loadingExpenses, setLoadingExpenses] = useState(true);
  const [loadingPnl, setLoadingPnl] = useState(true);

  // Date range for P&L (derived from days selector)
  const [startDate, setStartDate] = useState(daysAgo(30));
  const [endDate, setEndDate] = useState(toISODate(new Date()));

  // Sync date range when days selector changes
  useEffect(() => {
    setStartDate(daysAgo(days));
    setEndDate(toISODate(new Date()));
  }, [days]);

  // Fetch income
  useEffect(() => {
    setLoadingIncome(true);
    reportsApi
      .getIncome(corpId, days)
      .then((data) => {
        const sorted = [...data].sort((a, b) => Math.abs(b.total_amount) - Math.abs(a.total_amount));
        setIncome(sorted);
      })
      .catch(() => setIncome([]))
      .finally(() => setLoadingIncome(false));
  }, [corpId, days]);

  // Fetch expenses
  useEffect(() => {
    setLoadingExpenses(true);
    reportsApi
      .getExpenses(corpId, days)
      .then((data) => {
        const sorted = [...data].sort((a, b) => Math.abs(b.total_amount) - Math.abs(a.total_amount));
        setExpenses(sorted);
      })
      .catch(() => setExpenses([]))
      .finally(() => setLoadingExpenses(false));
  }, [corpId, days]);

  // Fetch P&L
  useEffect(() => {
    setLoadingPnl(true);
    reportsApi
      .getPnl(corpId, startDate, endDate)
      .then(setPnl)
      .catch(() => setPnl(null))
      .finally(() => setLoadingPnl(false));
  }, [corpId, startDate, endDate]);

  // Compute totals and percentages
  const totalIncome = income
    ? income.reduce((sum, i) => sum + Math.abs(i.total_amount), 0)
    : 0;
  const maxIncome = income && income.length > 0
    ? Math.abs(income[0].total_amount)
    : 1;

  const totalExpenses = expenses
    ? expenses.reduce((sum, e) => sum + Math.abs(e.total_amount), 0)
    : 0;
  const maxExpenses = expenses && expenses.length > 0
    ? Math.abs(expenses[0].total_amount)
    : 1;

  const netProfit = pnl ? pnl.net_profit : (totalIncome - totalExpenses);
  const netColor = netProfit >= 0 ? '#3fb950' : '#f85149';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: '0.75rem' }}>
      {/* PERIOD SELECTOR */}
      <div
        style={{
          ...cardStyle,
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Period:</span>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            style={selectStyle}
          >
            {PERIOD_OPTIONS.map((d) => (
              <option key={d} value={d}>
                {d} days
              </option>
            ))}
          </select>
        </div>
        <div
          style={{
            height: 20,
            width: 1,
            background: 'var(--border-color)',
          }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>P&L Range:</span>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={inputStyle}
          />
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>to</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            style={inputStyle}
          />
        </div>
      </div>

      {/* P&L SUMMARY — 3 stat cards in a row */}
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {loadingPnl ? (
          <div style={{ ...cardStyle, flex: 1 }}>
            <LoadingPlaceholder />
          </div>
        ) : (
          <>
            <StatCard
              title="Total Income"
              value={pnl ? pnl.total_income : totalIncome}
              color="#3fb950"
            />
            <StatCard
              title="Total Expenses"
              value={pnl ? pnl.total_expenses : totalExpenses}
              color="#f85149"
            />
            <StatCard
              title="Net Profit"
              value={pnl ? pnl.net_profit : netProfit}
              color={netColor}
            />
          </>
        )}
      </div>

      {/* INCOME + EXPENSES SIDE BY SIDE */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
        {/* INCOME BREAKDOWN */}
        <div style={cardStyle}>
          <h3 style={headingStyle}>Income Breakdown</h3>
          {loadingIncome ? (
            <LoadingPlaceholder />
          ) : !income || income.length === 0 ? (
            <EmptyPlaceholder message="No income data for this period" />
          ) : (
            <>
              {income.map((item) => {
                const absAmount = Math.abs(item.total_amount);
                const pct = totalIncome > 0 ? (absAmount / totalIncome) * 100 : 0;
                const bar = maxIncome > 0 ? (absAmount / maxIncome) * 100 : 0;
                return (
                  <BarRow
                    key={item.category}
                    label={item.category}
                    amount={item.total_amount}
                    count={item.transaction_count}
                    percent={pct}
                    barWidth={bar}
                    color="#3fb950"
                  />
                );
              })}
              {/* DIVIDER */}
              <div
                style={{
                  borderTop: '2px solid var(--border-color)',
                  marginTop: '0.5rem',
                  paddingTop: '0.5rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Total Income
                </span>
                <span style={iskGreen}>{formatIsk(totalIncome)}</span>
              </div>
            </>
          )}
        </div>

        {/* EXPENSE BREAKDOWN */}
        <div style={cardStyle}>
          <h3 style={headingStyle}>Expense Breakdown</h3>
          {loadingExpenses ? (
            <LoadingPlaceholder />
          ) : !expenses || expenses.length === 0 ? (
            <EmptyPlaceholder message="No expense data for this period" />
          ) : (
            <>
              {expenses.map((item) => {
                const absAmount = Math.abs(item.total_amount);
                const pct = totalExpenses > 0 ? (absAmount / totalExpenses) * 100 : 0;
                const bar = maxExpenses > 0 ? (absAmount / maxExpenses) * 100 : 0;
                return (
                  <BarRow
                    key={item.division_id}
                    label={item.division_name}
                    amount={item.total_amount}
                    count={item.transaction_count}
                    percent={pct}
                    barWidth={bar}
                    color="#f85149"
                  />
                );
              })}
              {/* DIVIDER */}
              <div
                style={{
                  borderTop: '2px solid var(--border-color)',
                  marginTop: '0.5rem',
                  paddingTop: '0.5rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Total Expenses
                </span>
                <span style={iskRed}>{formatIsk(totalExpenses)}</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
