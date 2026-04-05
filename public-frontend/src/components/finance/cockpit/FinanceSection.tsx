import { useState, useEffect } from 'react';
import { fontSize, color, spacing } from '../../../styles/theme';
import { formatIsk } from '../../../types/finance';
import { DualSparkline } from './Sparkline';
import { walletApi, reportsApi, miningApi, buybackApi } from '../../../services/api/finance';
import { srpApi } from '../../../services/api/srp';
import { aggregateJournalByDay } from '../../../types/cockpit';
import type { WalletBalance, IncomeBreakdown, ExpenseSummary, MiningTaxSummary, BuybackRequest } from '../../../types/finance';
import type { SrpRequest } from '../../../types/srp';
import type { DailyCashflow } from '../../../types/cockpit';

interface FinanceSectionProps {
  corpId: number;
  days: number;
}

// ---------------------------------------------------------------------------
// State types
// ---------------------------------------------------------------------------

interface DataState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

function initialState<T>(): DataState<T> {
  return { data: null, loading: true, error: null };
}

// ---------------------------------------------------------------------------
// Panel wrapper
// ---------------------------------------------------------------------------

function Panel({ title, borderColor, gridColumn, children }: {
  title: string;
  borderColor: string;
  gridColumn?: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      padding: spacing.base,
      borderLeft: `2px solid ${borderColor}`,
      gridColumn,
    }}>
      <div style={{
        fontSize: fontSize.xxs,
        textTransform: 'uppercase' as const,
        color: color.textSecondary,
        marginBottom: spacing.sm,
      }}>
        &middot; {title}
      </div>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Horizontal bar helper (shared by Revenue + Expenses)
// ---------------------------------------------------------------------------

function HorizontalBar({ label, amount, maxAmount, barColor }: {
  label: string;
  amount: number;
  maxAmount: number;
  barColor: string;
}) {
  const pct = maxAmount > 0 ? (amount / maxAmount) * 100 : 0;
  return (
    <div style={{ marginBottom: spacing.sm }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: fontSize.xxs }}>
        <span style={{ color: color.textPrimary }}>{label}</span>
        <span style={{ fontFamily: 'monospace', color: barColor }}>{formatIsk(amount)}</span>
      </div>
      <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '2px', height: '6px', overflow: 'hidden', marginTop: '2px' }}>
        <div style={{ background: barColor, height: '100%', width: `${pct}%`, transition: 'width 0.3s' }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mini loading / error helpers
// ---------------------------------------------------------------------------

function MiniLoader() {
  return (
    <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>Loading...</div>
  );
}

function MiniError({ message }: { message: string }) {
  return (
    <div style={{ color: color.lossRed, fontSize: fontSize.xxs }}>{message}</div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function FinanceSection({ corpId, days }: FinanceSectionProps) {
  // Per-panel state
  const [balances, setBalances] = useState<DataState<WalletBalance[]>>(initialState());
  const [cashflow, setCashflow] = useState<DataState<DailyCashflow[]>>(initialState());
  const [srp, setSrp] = useState<DataState<SrpRequest[]>>(initialState());
  const [income, setIncome] = useState<DataState<IncomeBreakdown[]>>(initialState());
  const [expenses, setExpenses] = useState<DataState<ExpenseSummary[]>>(initialState());
  const [mining, setMining] = useState<DataState<MiningTaxSummary[]>>(initialState());
  const [buyback, setBuyback] = useState<DataState<BuybackRequest[]>>(initialState());

  useEffect(() => {
    let cancelled = false;

    // Reset all to loading
    setBalances(initialState());
    setCashflow(initialState());
    setSrp(initialState());
    setIncome(initialState());
    setExpenses(initialState());
    setMining(initialState());
    setBuyback(initialState());

    // Fetch all divisions (1-7) in parallel for wallet balance
    const balancePromises = [1, 2, 3, 4, 5, 6, 7].map(div =>
      walletApi.getBalance(corpId, div).catch(() => null)
    );

    Promise.allSettled([
      Promise.all(balancePromises),                       // 0: balances
      walletApi.getJournal(corpId, { limit: 1000 }),      // 1: journal
      srpApi.getRequests(corpId),                          // 2: SRP
      reportsApi.getIncome(corpId, days),                  // 3: income
      reportsApi.getExpenses(corpId, days),                // 4: expenses
      miningApi.getTaxSummary(corpId, days),               // 5: mining
      buybackApi.getRequests({ corporation_id: corpId }),  // 6: buyback
    ]).then(([balRes, journalRes, srpRes, incRes, expRes, minRes, bbRes]) => {
      if (cancelled) return;

      // Wallet balances
      if (balRes.status === 'fulfilled') {
        const validBalances = (balRes.value as (WalletBalance | null)[])
          .filter((b): b is WalletBalance => b !== null);
        setBalances({ data: validBalances, loading: false, error: null });
      } else {
        setBalances({ data: null, loading: false, error: 'Failed to load balances' });
      }

      // Cashflow from journal
      if (journalRes.status === 'fulfilled') {
        const entries = journalRes.value;
        const daily = aggregateJournalByDay(entries);
        setCashflow({ data: daily, loading: false, error: null });
      } else {
        setCashflow({ data: null, loading: false, error: 'Failed to load journal' });
      }

      // SRP
      if (srpRes.status === 'fulfilled') {
        setSrp({ data: srpRes.value, loading: false, error: null });
      } else {
        setSrp({ data: null, loading: false, error: 'SRP data unavailable' });
      }

      // Income
      if (incRes.status === 'fulfilled') {
        setIncome({ data: incRes.value, loading: false, error: null });
      } else {
        setIncome({ data: null, loading: false, error: 'Failed to load income' });
      }

      // Expenses
      if (expRes.status === 'fulfilled') {
        setExpenses({ data: expRes.value, loading: false, error: null });
      } else {
        setExpenses({ data: null, loading: false, error: 'Failed to load expenses' });
      }

      // Mining
      if (minRes.status === 'fulfilled') {
        setMining({ data: minRes.value, loading: false, error: null });
      } else {
        setMining({ data: null, loading: false, error: 'Failed to load mining data' });
      }

      // Buyback
      if (bbRes.status === 'fulfilled') {
        const result = bbRes.value;
        const requests = Array.isArray(result) ? result : (result as { requests: BuybackRequest[] }).requests || [];
        setBuyback({ data: requests, loading: false, error: null });
      } else {
        setBuyback({ data: null, loading: false, error: 'Failed to load buyback data' });
      }
    });

    return () => { cancelled = true; };
  }, [corpId, days]);

  return (
    <div>
      {/* Section header */}
      <div style={{
        fontSize: fontSize.xs,
        textTransform: 'uppercase' as const,
        color: color.textSecondary,
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        paddingBottom: spacing.sm,
        marginBottom: spacing.sm,
      }}>
        &middot; FINANZEN
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: spacing.base,
      }}>
      {/* 1. Wallet Balance - full width */}
      <Panel title="Wallet Balance" borderColor="#3fb950" gridColumn="1 / -1">
        <WalletBalanceContent state={balances} />
      </Panel>

      {/* 2. Cashflow - span 2 columns */}
      <Panel title="Cashflow" borderColor="#00d4ff" gridColumn="span 2">
        <CashflowContent state={cashflow} days={days} />
      </Panel>

      {/* 3. SRP Status */}
      <Panel title="SRP Status" borderColor="#a855f7">
        <SrpContent state={srp} />
      </Panel>

      {/* 4. Top Revenue */}
      <Panel title="Top Revenue" borderColor="#3fb950">
        <TopRevenueContent state={income} />
      </Panel>

      {/* 5. Top Expenses */}
      <Panel title="Top Expenses" borderColor="#f85149">
        <TopExpensesContent state={expenses} />
      </Panel>

      {/* 6. Mining Tax */}
      <Panel title="Mining Tax" borderColor="#d29922">
        <MiningTaxContent state={mining} />
      </Panel>

      {/* 7. Buyback Queue */}
      <Panel title="Buyback Queue" borderColor="#ff8800">
        <BuybackContent state={buyback} />
      </Panel>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 1. Wallet Balance Content
// ---------------------------------------------------------------------------

function WalletBalanceContent({ state }: { state: DataState<WalletBalance[]> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const balances = state.data;
  const div1 = balances.find(b => b.division_id === 1);
  const otherDivs = balances.filter(b => b.division_id !== 1 && (b.balance > 0 || b.balance < 0));
  const total = balances.reduce((sum, b) => sum + (b.balance > 0 ? b.balance : 0), 0);

  return (
    <div>
      {/* Primary division - large display */}
      <div style={{
        fontSize: fontSize.h2,
        fontFamily: 'monospace',
        fontWeight: 700,
        color: color.killGreen,
        marginBottom: spacing.sm,
      }}>
        {div1 ? formatIsk(div1.balance) : '--'}
      </div>

      {/* Other non-zero divisions */}
      {otherDivs.length > 0 && (
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: spacing.base,
          marginBottom: spacing.sm,
        }}>
          {otherDivs.map(d => (
            <div key={d.division_id} style={{ fontSize: fontSize.xxs }}>
              <span style={{ color: color.textSecondary }}>Div {d.division_id}: </span>
              <span style={{ fontFamily: 'monospace', color: color.textPrimary }}>{formatIsk(d.balance)}</span>
            </div>
          ))}
        </div>
      )}

      {/* Total */}
      <div style={{
        fontSize: fontSize.xxs,
        color: color.textSecondary,
        borderTop: '1px solid rgba(255,255,255,0.06)',
        paddingTop: spacing.xs,
      }}>
        Total: <span style={{ fontFamily: 'monospace', color: color.textPrimary }}>{formatIsk(total)}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2. Cashflow Content
// ---------------------------------------------------------------------------

function CashflowContent({ state, days }: { state: DataState<DailyCashflow[]>; days: number }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const daily = state.data;
  if (daily.length === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No journal entries</div>;
  }

  const totalIncome = daily.reduce((s, d) => s + d.income, 0);
  const totalExpenses = daily.reduce((s, d) => s + d.expenses, 0);
  const numDays = Math.max(daily.length, 1);
  const avgIn = totalIncome / numDays;
  const avgOut = totalExpenses / numDays;
  const net = avgIn - avgOut;

  const netColor = net >= 0 ? color.killGreen : color.lossRed;
  const netSign = net >= 0 ? '+' : '';

  return (
    <div>
      <div style={{ marginBottom: spacing.sm }}>
        <DualSparkline
          data1={daily.map(d => d.income)}
          data2={daily.map(d => d.expenses)}
          width={400}
          height={48}
          color1="#3fb950"
          color2="#f85149"
        />
      </div>
      <div style={{
        display: 'flex',
        gap: spacing.lg,
        flexWrap: 'wrap',
        fontSize: fontSize.xxs,
      }}>
        <div>
          <span style={{ color: color.textSecondary }}>Avg In: </span>
          <span style={{ fontFamily: 'monospace', color: color.killGreen }}>{formatIsk(avgIn)}</span>
          <span style={{ color: color.textSecondary }}>/day</span>
        </div>
        <div>
          <span style={{ color: color.textSecondary }}>Avg Out: </span>
          <span style={{ fontFamily: 'monospace', color: color.lossRed }}>{formatIsk(avgOut)}</span>
          <span style={{ color: color.textSecondary }}>/day</span>
        </div>
        <div>
          <span style={{ color: color.textSecondary }}>Net: </span>
          <span style={{ fontFamily: 'monospace', color: netColor }}>
            {netSign}{formatIsk(Math.abs(net))}
          </span>
          <span style={{ color: color.textSecondary }}>/day</span>
        </div>
      </div>
      <div style={{
        fontSize: fontSize.tiny,
        color: color.textTertiary,
        marginTop: spacing.xs,
      }}>
        Based on {daily.length} day{daily.length !== 1 ? 's' : ''} of journal data ({days}D window)
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 3. SRP Content
// ---------------------------------------------------------------------------

function SrpContent({ state }: { state: DataState<SrpRequest[]> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) {
    return (
      <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>
        SRP data unavailable
      </div>
    );
  }

  const requests = state.data;
  const pending = requests.filter(r => r.status === 'pending').length;
  const approved = requests.filter(r => r.status === 'approved').length;
  const paid = requests.filter(r => r.status === 'paid').length;
  const totalApprovedPayout = requests
    .filter(r => r.status === 'approved')
    .reduce((s, r) => s + (r.payout_amount > 0 ? r.payout_amount : 0), 0);

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <div style={{ display: 'flex', gap: spacing.lg, marginBottom: spacing.sm }}>
        <div>
          <span style={{ color: '#d29922' }}>{pending}</span>
          <span style={{ color: color.textSecondary }}> pending</span>
        </div>
        <div>
          <span style={{ color: '#3fb950' }}>{approved}</span>
          <span style={{ color: color.textSecondary }}> approved</span>
        </div>
        <div>
          <span style={{ color: '#00d4ff' }}>{paid}</span>
          <span style={{ color: color.textSecondary }}> paid</span>
        </div>
      </div>
      <div>
        <span style={{ color: color.textSecondary }}>Approved Payout: </span>
        <span style={{ fontFamily: 'monospace', color: color.accentPurple }}>
          {formatIsk(totalApprovedPayout)}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 4. Top Revenue Content
// ---------------------------------------------------------------------------

function TopRevenueContent({ state }: { state: DataState<IncomeBreakdown[]> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const sorted = [...state.data]
    .sort((a, b) => b.total_amount - a.total_amount)
    .slice(0, 5);

  if (sorted.length === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No revenue data</div>;
  }

  const maxAmount = Math.max(...sorted.map(i => i.total_amount), 0);

  return (
    <div>
      {sorted.map((item, idx) => (
        <HorizontalBar
          key={idx}
          label={item.category}
          amount={item.total_amount}
          maxAmount={maxAmount}
          barColor="#3fb950"
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 5. Top Expenses Content
// ---------------------------------------------------------------------------

function TopExpensesContent({ state }: { state: DataState<ExpenseSummary[]> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const sorted = [...state.data]
    .sort((a, b) => b.total_amount - a.total_amount)
    .slice(0, 5);

  if (sorted.length === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No expense data</div>;
  }

  const maxAmount = Math.max(...sorted.map(i => i.total_amount), 0);

  return (
    <div>
      {sorted.map((item, idx) => (
        <HorizontalBar
          key={idx}
          label={item.division_name}
          amount={item.total_amount}
          maxAmount={maxAmount}
          barColor="#f85149"
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 6. Mining Tax Content
// ---------------------------------------------------------------------------

function MiningTaxContent({ state }: { state: DataState<MiningTaxSummary[]> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const miners = state.data;
  if (miners.length === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No mining activity</div>;
  }

  const totalMined = miners.reduce((s, m) => s + (m.total_isk_value > 0 ? m.total_isk_value : 0), 0);
  const totalTax = miners.reduce((s, m) => s + (m.total_tax > 0 ? m.total_tax : 0), 0);
  const topMiner = [...miners].sort((a, b) => b.total_isk_value - a.total_isk_value)[0];

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <div style={{ marginBottom: spacing.xs }}>
        <span style={{ color: color.textSecondary }}>Total Mined: </span>
        <span style={{ fontFamily: 'monospace', color: '#d29922' }}>{formatIsk(totalMined)}</span>
      </div>
      <div style={{ marginBottom: spacing.xs }}>
        <span style={{ color: color.textSecondary }}>Total Tax Due: </span>
        <span style={{ fontFamily: 'monospace', color: color.textPrimary }}>{formatIsk(totalTax)}</span>
      </div>
      {topMiner && (
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: spacing.xs }}>
          <span style={{ color: color.textSecondary }}>Top Miner: </span>
          <span style={{ color: color.textPrimary }}>{topMiner.character_name}</span>
          <span style={{ color: color.textSecondary }}> ({formatIsk(topMiner.total_isk_value)})</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 7. Buyback Content
// ---------------------------------------------------------------------------

function BuybackContent({ state }: { state: DataState<BuybackRequest[]> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) return <MiniError message={state.error || 'No data'} />;

  const requests = state.data;
  const pendingRequests = requests.filter(r => r.status === 'pending');
  const pendingCount = pendingRequests.length;
  const pendingPayout = pendingRequests.reduce(
    (s, r) => s + (r.total_payout > 0 ? r.total_payout : 0), 0
  );

  if (pendingCount === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No pending requests</div>;
  }

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <span style={{ color: '#ff8800', fontWeight: 600 }}>{pendingCount}</span>
      <span style={{ color: color.textSecondary }}> pending request{pendingCount !== 1 ? 's' : ''}</span>
      <span style={{ color: color.textSecondary }}> | </span>
      <span style={{ fontFamily: 'monospace', color: '#ff8800' }}>{formatIsk(pendingPayout)}</span>
      <span style={{ color: color.textSecondary }}> total</span>
    </div>
  );
}
