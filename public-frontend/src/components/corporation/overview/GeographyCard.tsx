/**
 * GeographyCard Component
 *
 * Displays geographic intelligence summary for Overview tab.
 */

import { useState, useEffect } from 'react';
import { corpApi } from '../../../services/corporationApi';
import type { GeographySummary } from '../../../types/corporation';
import { TrendIndicator, MiniChart, StatCard } from './index';

interface GeographyCardProps {
  corpId: number;
  days: number;
}

export function GeographyCard({ corpId, days }: GeographyCardProps) {
  const [data, setData] = useState<GeographySummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    corpApi
      .getGeographySummary(corpId, days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [corpId, days]);

  if (loading) {
    return (
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '0.75rem', borderLeft: '2px solid #00bcd4' }}>
        <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#8b949e' }}>• GEOGRAPHY</div>
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
        borderLeft: '2px solid #00bcd4',
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
          • GEOGRAPHY
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
          label="Systems"
          value={data.unique_systems}
          color="#00bcd4"
          size="small"
        />
        <StatCard
          label="Regions"
          value={data.unique_regions}
          color="#00bcd4"
          size="small"
        />
      </div>

      {/* Chart - Region diversity over time */}
      <div style={{ marginTop: '0.25rem' }}>
        <MiniChart
          data={data.timeline.map((t) => t.unique_regions)}
          height={35}
          color="#00bcd4"
        />
      </div>

      {/* Bottom Stats */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '0.3rem',
          fontSize: '0.65rem',
          color: '#8b949e',
          marginTop: '0.25rem',
        }}
      >
        <div>
          <span style={{ color: '#8b949e' }}>Primary Region:</span>{' '}
          <span style={{ color: '#fff' }}>{data.primary_region}</span>
        </div>
        <div>
          <span style={{ color: '#8b949e' }}>Primary System:</span>{' '}
          <span style={{ color: '#fff' }}>{data.primary_system}</span>
        </div>
      </div>
    </div>
  );
}
