import { useState, useEffect } from 'react';
import { fontSize, color } from '../../../styles/theme';
import { contractsApi } from '../../../services/api/corptools';
import { SectionCard } from './SectionCard';
import type { ContractActiveResponse, ContractChange } from '../../../types/corptools';

interface LogisticsCardProps {
  corpId: number;
}

export function LogisticsCard({ corpId }: LogisticsCardProps) {
  const [activeData, setActiveData] = useState<ContractActiveResponse | null>(null);
  const [recentChanges, setRecentChanges] = useState<{ count: number; changes: ContractChange[] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    Promise.allSettled([
      contractsApi.getActive(corpId),
      contractsApi.getChanges(corpId, 24),
    ]).then(([activeResult, changesResult]) => {
      if (cancelled) return;

      if (activeResult.status === 'fulfilled') {
        setActiveData(activeResult.value);
      }
      if (changesResult.status === 'fulfilled') {
        setRecentChanges(changesResult.value);
      }

      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [corpId]);

  const totalContracts = activeData?.summary?.total ?? 0;
  const contracts = activeData?.contracts ?? [];

  // Group by type
  const byType: Record<string, number> = {};
  for (const c of contracts) {
    const t = c.type || 'unknown';
    byType[t] = (byType[t] || 0) + 1;
  }

  const changeCount = recentChanges?.count ?? 0;

  return (
    <SectionCard
      title="Logistics & Contracts"
      borderColor="#a855f7"
      linkTo="/corp/tools"
      loading={loading}
    >
      {/* Active contract count */}
      <div
        style={{
          fontSize: fontSize.base,
          fontWeight: 700,
          color: color.textPrimary,
        }}
      >
        {totalContracts} Active Contract{totalContracts !== 1 ? 's' : ''}
      </div>

      {/* Type breakdown */}
      {Object.keys(byType).length > 0 ? (
        <div
          style={{
            fontSize: fontSize.tiny,
            fontFamily: 'monospace',
            color: color.textSecondary,
            marginTop: '0.15rem',
          }}
        >
          {Object.entries(byType)
            .sort(([, a], [, b]) => b - a)
            .map(([type, count]) => `${type}: ${count}`)
            .join(', ')}
        </div>
      ) : (
        <div
          style={{
            fontSize: fontSize.tiny,
            color: color.textSecondary,
            marginTop: '0.15rem',
          }}
        >
          {'\u2014'}
        </div>
      )}

      {/* Recent changes */}
      <div
        style={{
          fontSize: fontSize.tiny,
          color: color.textSecondary,
          marginTop: '0.15rem',
        }}
      >
        {changeCount} change{changeCount !== 1 ? 's' : ''} in last 24h
      </div>
    </SectionCard>
  );
}
