import { useState, useEffect } from 'react';
import { fontSize, color, spacing } from '../../../styles/theme';
import { formatIsk } from '../../../types/finance';
import { contractsApi } from '../../../services/api/corptools';
import { buybackApi } from '../../../services/api/finance';
import type { ContractStatsResponse, CourierAnalysisResponse } from '../../../types/corptools';
import type { BuybackRequest } from '../../../types/finance';

interface ProductionSectionProps {
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
// Mini loading / error helpers
// ---------------------------------------------------------------------------

function MiniLoader() {
  return (
    <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>Loading...</div>
  );
}

// ---------------------------------------------------------------------------
// Stat row helper
// ---------------------------------------------------------------------------

function StatRow({ label, value, valueColor }: {
  label: string;
  value: string | number;
  valueColor?: string;
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: fontSize.xxs, marginBottom: spacing.xs }}>
      <span style={{ color: color.textSecondary }}>{label}</span>
      <span style={{ fontFamily: 'monospace', color: valueColor || color.textPrimary }}>{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ProductionSection({ corpId, days }: ProductionSectionProps) {
  const [contracts, setContracts] = useState<DataState<ContractStatsResponse>>(initialState());
  const [courier, setCourier] = useState<DataState<CourierAnalysisResponse>>(initialState());
  const [buyback, setBuyback] = useState<DataState<BuybackRequest[]>>(initialState());

  useEffect(() => {
    let cancelled = false;

    setContracts(initialState());
    setCourier(initialState());
    setBuyback(initialState());

    Promise.allSettled([
      contractsApi.getStats(corpId, days),
      contractsApi.getCourier(corpId, days),
      buybackApi.getRequests({ corporation_id: corpId }),
    ]).then(([contractsRes, courierRes, buybackRes]) => {
      if (cancelled) return;

      // Contract stats
      if (contractsRes.status === 'fulfilled') {
        setContracts({ data: contractsRes.value, loading: false, error: null });
      } else {
        setContracts({ data: null, loading: false, error: 'Contract data unavailable' });
      }

      // Courier analysis
      if (courierRes.status === 'fulfilled') {
        setCourier({ data: courierRes.value, loading: false, error: null });
      } else {
        setCourier({ data: null, loading: false, error: 'Courier data unavailable' });
      }

      // Buyback requests
      if (buybackRes.status === 'fulfilled') {
        const result = buybackRes.value;
        const requests = Array.isArray(result) ? result : (result as { requests: BuybackRequest[] }).requests || [];
        setBuyback({ data: requests, loading: false, error: null });
      } else {
        setBuyback({ data: null, loading: false, error: 'Buyback data unavailable' });
      }
    });

    return () => { cancelled = true; };
  }, [corpId, days]);

  return (
    <div>
      {/* Section header */}
      <div style={{
        fontSize: fontSize.xxs,
        textTransform: 'uppercase' as const,
        color: color.textSecondary,
        marginBottom: spacing.sm,
        letterSpacing: '0.05em',
      }}>
        &middot; PRODUCTION &amp; ECONOMY
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: spacing.base,
      }}>
        {/* 1. Contracts Overview */}
        <Panel title="Contracts Overview" borderColor="#00d4ff">
          <ContractsContent state={contracts} />
        </Panel>

        {/* 2. Courier & Logistics */}
        <Panel title="Courier & Logistics" borderColor="#ff8800">
          <CourierContent state={courier} />
        </Panel>

        {/* 3. Buyback Summary */}
        <Panel title="Buyback Summary" borderColor="#d29922">
          <BuybackContent state={buyback} />
        </Panel>

        {/* 4. Industry Overview */}
        <Panel title="Industry Overview" borderColor="#3fb950">
          <IndustryPlaceholder />
        </Panel>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 1. Contracts Overview Content
// ---------------------------------------------------------------------------

function ContractsContent({ state }: { state: DataState<ContractStatsResponse> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) {
    return (
      <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>
        Contract data unavailable
      </div>
    );
  }

  const stats = state.data;
  const byTypeStatus = stats.byTypeStatus || [];
  const completionRates = stats.completionRates || [];

  // Aggregate counts by status across all contract types
  const statusCounts: Record<string, number> = {};
  const statusIsk: Record<string, number> = {};
  for (const entry of byTypeStatus) {
    const status = entry.status || 'unknown';
    statusCounts[status] = (statusCounts[status] || 0) + (entry.count || 0);
    statusIsk[status] = (statusIsk[status] || 0) + (entry.totalValue || 0);
  }

  const outstanding = statusCounts['outstanding'] || 0;
  const inProgress = statusCounts['in_progress'] || 0;
  const completed = (statusCounts['finished'] || 0) +
    (statusCounts['finished_issuer'] || 0) +
    (statusCounts['finished_contractor'] || 0);
  const expired = (statusCounts['expired'] || 0) +
    (statusCounts['failed'] || 0) +
    (statusCounts['cancelled'] || 0);

  const totalIsk = Object.values(statusIsk).reduce((sum, v) => sum + (v > 0 ? v : 0), 0);

  // Overall completion rate
  const totalContracts = completionRates.reduce((s, r) => s + (r.total || 0), 0);
  const totalCompleted = completionRates.reduce((s, r) => s + (r.completed || 0), 0);
  const completionRate = totalContracts > 0 ? (totalCompleted / totalContracts) * 100 : 0;

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <StatRow label="Outstanding" value={outstanding} valueColor="#d29922" />
      <StatRow label="In Progress" value={inProgress} valueColor="#00d4ff" />
      <StatRow label="Completed" value={completed} valueColor="#3fb950" />
      <StatRow label="Expired/Failed" value={expired} valueColor="#8b949e" />

      <div style={{
        borderTop: '1px solid rgba(255,255,255,0.06)',
        paddingTop: spacing.xs,
        marginTop: spacing.xs,
      }}>
        <StatRow label="Total Volume" value={formatIsk(totalIsk)} valueColor="#00d4ff" />
        <StatRow
          label="Completion Rate"
          value={isFinite(completionRate) ? `${completionRate.toFixed(1)}%` : '--'}
          valueColor={completionRate >= 80 ? '#3fb950' : completionRate >= 50 ? '#d29922' : '#f85149'}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2. Courier & Logistics Content
// ---------------------------------------------------------------------------

function CourierContent({ state }: { state: DataState<CourierAnalysisResponse> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) {
    return (
      <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>
        Courier data unavailable
      </div>
    );
  }

  const data = state.data;
  const summary = data.summary || { total: 0, outstanding: 0, inProgress: 0, completed: 0, completionRate: 0 };
  const efficiency = data.efficiency || { averageCompletionHours: 0, totalRewardPaid: 0, totalVolumeMoved: 0, averageIskPerM3: 0 };

  if (summary.total === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No courier contracts</div>;
  }

  const avgHours = efficiency.averageCompletionHours || 0;

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <StatRow label="In Transit" value={summary.inProgress || 0} valueColor="#ff8800" />
      <StatRow label="Completed" value={summary.completed || 0} valueColor="#3fb950" />
      <StatRow label="Outstanding" value={summary.outstanding || 0} valueColor="#d29922" />

      <div style={{
        borderTop: '1px solid rgba(255,255,255,0.06)',
        paddingTop: spacing.xs,
        marginTop: spacing.xs,
      }}>
        {avgHours > 0 && (
          <StatRow
            label="Avg Delivery"
            value={avgHours < 1 ? `${Math.round(avgHours * 60)}min` : `${isFinite(avgHours) ? avgHours.toFixed(1) : '0.0'}h`}
            valueColor="#00d4ff"
          />
        )}
        <StatRow label="Total Rewards" value={formatIsk(efficiency.totalRewardPaid || 0)} valueColor="#ff8800" />
        {(efficiency.totalVolumeMoved || 0) > 0 && (
          <StatRow
            label="Volume Moved"
            value={`${((efficiency.totalVolumeMoved || 0) / 1000).toFixed(0)}K m3`}
            valueColor={color.textPrimary}
          />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 3. Buyback Summary Content
// ---------------------------------------------------------------------------

function BuybackContent({ state }: { state: DataState<BuybackRequest[]> }) {
  if (state.loading) return <MiniLoader />;
  if (state.error || !state.data) {
    return (
      <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>
        Buyback data unavailable
      </div>
    );
  }

  const requests = state.data;
  if (requests.length === 0) {
    return <div style={{ color: color.textSecondary, fontSize: fontSize.xxs }}>No buyback requests</div>;
  }

  const pending = requests.filter(r => r.status === 'pending');
  const approved = requests.filter(r => r.status === 'approved');
  const completed = requests.filter(r => r.status === 'completed');

  const pendingPayout = pending.reduce(
    (s, r) => s + (r.total_payout > 0 ? r.total_payout : 0), 0
  );

  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <div style={{ display: 'flex', gap: spacing.lg, marginBottom: spacing.sm }}>
        <div>
          <span style={{ color: '#d29922', fontWeight: 600 }}>{pending.length}</span>
          <span style={{ color: color.textSecondary }}> pending</span>
        </div>
        <div>
          <span style={{ color: '#3fb950', fontWeight: 600 }}>{approved.length}</span>
          <span style={{ color: color.textSecondary }}> approved</span>
        </div>
        <div>
          <span style={{ color: '#00d4ff', fontWeight: 600 }}>{completed.length}</span>
          <span style={{ color: color.textSecondary }}> completed</span>
        </div>
      </div>

      {pending.length > 0 && (
        <div style={{
          borderTop: '1px solid rgba(255,255,255,0.06)',
          paddingTop: spacing.xs,
        }}>
          <span style={{ color: color.textSecondary }}>Pending Payout: </span>
          <span style={{ fontFamily: 'monospace', color: '#d29922' }}>{formatIsk(pendingPayout)}</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 4. Industry Overview (Placeholder)
// ---------------------------------------------------------------------------

function IndustryPlaceholder() {
  return (
    <div style={{ fontSize: fontSize.xxs }}>
      <div style={{
        color: color.textSecondary,
        marginBottom: spacing.sm,
      }}>
        Industry data available per character
      </div>
      <div style={{
        color: color.textTertiary,
        fontStyle: 'italic',
      }}>
        See Character Dashboard for active jobs
      </div>
    </div>
  );
}
