/**
 * Alliance HuntingCard - Compact Summary Card
 */

import { useState, useEffect } from 'react';
import { getOffensiveStats } from '../../../services/allianceApi';
import type { AllianceOffensiveStats } from '../../../types/alliance';
import { MiniChart } from './MiniChart';

interface HuntingCardProps {
  allianceId: number;
  days: number;
}

export function HuntingCard({ allianceId, days }: HuntingCardProps) {
  const [data, setData] = useState<AllianceOffensiveStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getOffensiveStats(allianceId, days)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [allianceId, days]);

  if (loading) {
    return <div className="skeleton" style={{ height: '180px', borderRadius: '6px' }} />;
  }

  if (!data) return null;

  const { summary, kill_timeline, hunting_regions } = data;

  // Calculate threat level (based on kills intensity)
  const avgKillsPerDay = summary.total_kills / Math.max(days, 1);
  const threatLevel = avgKillsPerDay > 100 ? 'HIGH' : avgKillsPerDay > 50 ? 'MED' : 'LOW';
  const threatColor = threatLevel === 'HIGH' ? '#ff4444' : threatLevel === 'MED' ? '#ffcc00' : '#3fb950';

  // Calculate operational tempo (kills per active day)
  const activeDays = kill_timeline.filter(d => (d.kills || 0) > 0).length;
  const opTempo = summary.total_kills / Math.max(activeDays, 1);

  // Timeline data from kill timeline
  const timeline = kill_timeline.slice(-30);
  const timelineData = timeline.map(d => d.kills || 0);

  // Most hunted region
  const topRegion = hunting_regions.length > 0 ? hunting_regions[0] : null;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #ff8800',
      padding: '0.5rem',
      height: '180px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#ff8800', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          • HUNTING
        </span>
        <span style={{ fontSize: '0.5rem', color: '#58a6ff', cursor: 'pointer' }}>ℹ️</span>
      </div>

      {/* Top Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.4rem' }}>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>THREAT LEVEL</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: threatColor, fontFamily: 'monospace' }}>
            {threatLevel}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>OP TEMPO</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ff8800', fontFamily: 'monospace' }}>
            {opTempo.toFixed(0)}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#ff8800" />
      </div>

      {/* Bottom Stats */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.3rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Most Hunted: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{topRegion?.region_name || 'N/A'}</span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Active: </span>
          <span style={{ color: '#ff8800', fontWeight: 600 }}>{activeDays}d</span>
        </div>
      </div>
    </div>
  );
}
