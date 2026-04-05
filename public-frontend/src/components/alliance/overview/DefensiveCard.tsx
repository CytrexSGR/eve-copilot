/**
 * Alliance DefensiveCard - Compact Summary Card
 */

import { useState, useEffect } from 'react';
import { getDefensiveStats } from '../../../services/allianceApi';
import type { AllianceDefensiveStats } from '../../../types/alliance';
import { MiniChart } from './MiniChart';

interface DefensiveCardProps {
  allianceId: number;
  days: number;
}

export function DefensiveCard({ allianceId, days }: DefensiveCardProps) {
  const [data, setData] = useState<AllianceDefensiveStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getDefensiveStats(allianceId, days)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [allianceId, days]);

  if (loading) {
    return <div className="skeleton" style={{ height: '180px', borderRadius: '6px' }} />;
  }

  if (!data) return null;

  const { summary, death_timeline } = data;
  const timeline = death_timeline.slice(-30);
  const timelineData = timeline.map(d => d.deaths || 0);

  const kdRatio = summary.total_kills / Math.max(summary.total_deaths, 1);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #ff4444',
      padding: '0.5rem',
      height: '180px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#ff4444', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          • DEFENSIVE
        </span>
        <span style={{ fontSize: '0.5rem', color: '#58a6ff', cursor: 'pointer' }}>ℹ️</span>
      </div>

      {/* Top Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.4rem' }}>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>K/D RATIO</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: kdRatio >= 1 ? '#3fb950' : '#ff4444', fontFamily: 'monospace' }}>
            {kdRatio.toFixed(2)}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>EFFICIENCY</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: summary.efficiency >= 50 ? '#3fb950' : '#ffcc00', fontFamily: 'monospace' }}>
            {summary.efficiency.toFixed(1)} %
          </div>
        </div>
      </div>

      {/* Chart */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#ff4444" />
      </div>

      {/* Bottom Stats */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.3rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Top Threat: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{(data.top_threats?.[0] as any)?.alliance_name || (data.top_threats?.[0] as any)?.corporation_name || 'N/A'}</span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Deaths: </span>
          <span style={{ color: '#ff4444', fontWeight: 600 }}>{summary.total_deaths}</span>
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', marginTop: '0.15rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>ISK Lost: </span>
          <span style={{ color: '#ff4444', fontWeight: 600 }}>{(parseFloat(summary.isk_lost || '0') / 1e9).toFixed(1)}B</span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}> — </span>
          <span style={{ color: 'rgba(255,255,255,0.4)', fontWeight: 600 }}>stable</span>
        </div>
      </div>
    </div>
  );
}
