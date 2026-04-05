import { useState, useEffect } from 'react';
import { fontSize, color } from '../../../styles/theme';
import { walletApi, reportsApi } from '../../../services/api/finance';
import { formatIsk } from '../../../types/finance';
import { SectionCard } from './SectionCard';

interface TreasuryCardProps {
  corpId: number;
  days: number;
}

export function TreasuryCard({ corpId, days }: TreasuryCardProps) {
  const [balance, setBalance] = useState<number | null>(null);
  const [income, setIncome] = useState<number | null>(null);
  const [expenses, setExpenses] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.allSettled([
      walletApi.getBalance(corpId),
      reportsApi.getIncome(corpId, days),
      reportsApi.getExpenses(corpId, days),
    ]).then(([balanceResult, incomeResult, expensesResult]) => {
      if (cancelled) return;

      if (balanceResult.status === 'fulfilled') {
        setBalance(balanceResult.value.balance);
      }
      if (incomeResult.status === 'fulfilled') {
        const totalIncome = incomeResult.value.reduce(
          (sum, entry) => sum + entry.total_amount,
          0,
        );
        setIncome(totalIncome);
      }
      if (expensesResult.status === 'fulfilled') {
        const totalExpenses = expensesResult.value.reduce(
          (sum, entry) => sum + entry.total_amount,
          0,
        );
        setExpenses(totalExpenses);
      }

      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [corpId, days]);

  const net =
    income !== null && expenses !== null ? income - expenses : null;

  return (
    <SectionCard
      title="Treasury"
      borderColor="#3fb950"
      linkTo="/corp/finance"
      loading={loading}
    >
      {/* Main balance */}
      <div
        style={{
          fontSize: fontSize.lg,
          fontFamily: 'monospace',
          fontWeight: 700,
          color: color.killGreen,
        }}
      >
        {balance !== null ? formatIsk(balance) : '--'}
      </div>

      {/* Income / Expenses */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem', marginTop: '0.25rem' }}>
        <div
          style={{
            fontSize: fontSize.xs,
            fontFamily: 'monospace',
            color: color.killGreen,
          }}
        >
          Income: +{income !== null ? formatIsk(income) : '--'}
        </div>
        <div
          style={{
            fontSize: fontSize.xs,
            fontFamily: 'monospace',
            color: color.lossRed,
          }}
        >
          Expenses: -{expenses !== null ? formatIsk(Math.abs(expenses)) : '--'}
        </div>
      </div>

      {/* Net line */}
      {net !== null && (
        <div
          style={{
            fontSize: fontSize.xs,
            fontFamily: 'monospace',
            fontWeight: 600,
            color: net >= 0 ? color.killGreen : color.lossRed,
            marginTop: '0.15rem',
          }}
        >
          Net: {net >= 0 ? '+' : ''}{formatIsk(net)}
        </div>
      )}
    </SectionCard>
  );
}
