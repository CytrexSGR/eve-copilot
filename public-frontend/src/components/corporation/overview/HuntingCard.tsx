/**
 * HuntingCard Component
 *
 * Displays hunting intelligence summary for Overview tab.
 */

import { useState, useEffect } from 'react';
import { corpApi } from '../../../services/corporationApi';
import type { HuntingSummary } from '../../../types/corporation';
import { TrendIndicator, MiniChart, StatCard, getThreatColor } from './index';

interface HuntingCardProps {
  corpId: number;
  days: number;
}

export function HuntingCard({ corpId, days }: HuntingCardProps) {
  const [data, setData] = useState<HuntingSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    corpApi
      .getHuntingSummary(corpId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [corpId, days]);

  if (loading) {
    return (
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.75rem', borderLeft: '2px solid #ff8800' }}>
        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e' }}>• HUNTING</div>
        <div style={{ marginTop: '0.5rem', color: '#8b949e', fontSize: '0.75rem' }}>Loading...</div>
      </div>
    );
  }

  if (!data) return null;

  const threatColor = getThreatColor(data.threat_level);

  return (
    <div
      style={{
        background: 'rgba(0,0,0,0.3)',
        borderRadius: '8px',
        padding: '0.75rem',
        borderLeft: `2px solid ${threatColor}`,
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
          • HUNTING
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
          label="Threat Level"
          value={data.threat_level.toUpperCase()}
          color={threatColor}
          size="small"
        />
        <StatCard
          label="Op Tempo"
          value={data.operational_tempo.toFixed(1)}
          suffix="/day"
          color="#ff8800"
          size="small"
        />
      </div>

      {/* Chart - Kill rate over time */}
      <div style={{ marginTop: '0.25rem' }}>
        <MiniChart
          data={data.timeline.map((t) => t.kills)}
          height={35}
          color="#ff8800"
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
        Most Hunted: <span style={{ color: '#fff' }}>{data.hunted_region}</span>
      </div>
    </div>
  );
}
