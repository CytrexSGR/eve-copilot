/**
 * ActivityCard Component
 *
 * Displays activity intelligence summary for Overview tab.
 */

import { useState, useEffect } from 'react';
import { corpApi } from '../../../services/corporationApi';
import type { ActivitySummary } from '../../../types/corporation';
import { TrendIndicator, MiniChart, StatCard } from './index';

interface ActivityCardProps {
  corpId: number;
  days: number;
}

export function ActivityCard({ corpId, days }: ActivityCardProps) {
  const [data, setData] = useState<ActivitySummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    corpApi
      .getActivitySummary(corpId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [corpId, days]);

  if (loading) {
    return (
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.75rem', borderLeft: '2px solid #10b981' }}>
        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e' }}>• ACTIVITY</div>
        <div style={{ marginTop: '0.5rem', color: '#8b949e', fontSize: '0.75rem' }}>Loading...</div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: '0.75rem',
        borderLeft: '2px solid #10b981',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e', fontWeight: 600 }}>
          • ACTIVITY
        </div>
        <TrendIndicator trend={data.trend} size="small" />
      </div>

      {/* Stats Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '0.5rem',
        }}
      >
        <StatCard
          label="Active Days"
          value={data.active_days}
          color="#10b981"
          size="small"
        />
        <StatCard
          label="Avg/Day"
          value={data.avg_daily_activity.toFixed(1)}
          color="#10b981"
          size="small"
        />
      </div>

      {/* Chart */}
      <div style={{ marginTop: '0.25rem' }}>
        <MiniChart
          data={data.timeline.map((t) => t.activity)}
          height={35}
          color="#10b981"
        />
      </div>

      {/* Bottom Stats */}
      <div
        style={{
          fontSize: '0.65rem',
          color: '#8b949e',
          textAlign: 'center',
          marginTop: '0.25rem',
        }}
      >
        Peak Activity: <span style={{ color: '#fff' }}>{data.peak_hour.toString().padStart(2, '0')}:00 EVE</span>
      </div>
    </div>
  );
}
