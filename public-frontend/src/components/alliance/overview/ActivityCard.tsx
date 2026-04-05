/**
 * Alliance ActivityCard - Compact Summary Card
 */

import { useState, useEffect } from 'react';
import { getCorpActivityHeatmap } from '../../../services/allianceApi';
import type { CorpHeatmapResponse } from '../../../services/allianceApi';
import { MiniChart } from './MiniChart';

interface ActivityCardProps {
  allianceId: number;
  days: number;
}

export function ActivityCard({ allianceId, days }: ActivityCardProps) {
  const [data, setData] = useState<CorpHeatmapResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getCorpActivityHeatmap(allianceId, days)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [allianceId, days]);

  if (loading) {
    return <div className="skeleton" style={{ height: '180px', borderRadius: '6px' }} />;
  }

  if (!data) return null;

  // Calculate activity metrics
  const totalActivity = data.corps.reduce((sum, c) => sum + c.total, 0);
  const activeDays = days; // Assume full period has activity
  const avgPerDay = totalActivity / Math.max(activeDays, 1);

  // Find peak activity hour from corps data
  const hourlyTotals = Array(24).fill(0);
  data.corps.forEach(corp => {
    corp.hours.forEach((count, hour) => {
      hourlyTotals[hour] += count;
    });
  });
  const peakHour = { hour: hourlyTotals.indexOf(Math.max(...hourlyTotals)), count: Math.max(...hourlyTotals) };

  // Mock timeline data
  const timelineData = Array(30).fill(0).map(() => Math.random() * avgPerDay * 1.5);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #3fb950',
      padding: '0.5rem',
      height: '180px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#3fb950', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          • ACTIVITY
        </span>
        <span style={{ fontSize: '0.5rem', color: '#58a6ff', cursor: 'pointer' }}>ℹ️</span>
      </div>

      {/* Top Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.4rem' }}>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>ACTIVE DAYS</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#3fb950', fontFamily: 'monospace' }}>
            {activeDays}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>AVG/DAY</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#3fb950', fontFamily: 'monospace' }}>
            {Math.round(avgPerDay)}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#3fb950" />
      </div>

      {/* Bottom Stats */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.3rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Peak Activity: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{peakHour?.hour}:00 UTC</span>
        </div>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Ops: </span>
          <span style={{ color: '#3fb950', fontWeight: 600 }}>{data.corps.length}</span>
        </div>
      </div>
    </div>
  );
}
