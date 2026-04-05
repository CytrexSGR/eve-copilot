/**
 * Alliance PilotCard - Compact Summary Card
 */

import { useState, useEffect } from 'react';
import { getCorpActivityHeatmap } from '../../../services/allianceApi';
import type { CorpHeatmapResponse } from '../../../services/allianceApi';
import { MiniChart } from './MiniChart';

interface PilotCardProps {
  allianceId: number;
  days: number;
}

export function PilotCard({ allianceId, days }: PilotCardProps) {
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

  // Aggregate pilot data from corps
  const totalCorps = data.corps.length;
  const totalActivity = data.corps.reduce((sum, c) => sum + c.total, 0);
  const avgActivity = totalActivity / Math.max(totalCorps, 1);

  // Mock morale (would need real endpoint)
  const morale = 67.0;

  // Mock timeline data
  const timelineData = Array(30).fill(0).map(() => Math.random() * avgActivity);

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '6px',
      border: '1px solid rgba(255,255,255,0.08)',
      borderLeft: '3px solid #a855f7',
      padding: '0.5rem',
      height: '180px',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: '#a855f7', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          • PILOTS
        </span>
        <span style={{ fontSize: '0.5rem', color: '#58a6ff', cursor: 'pointer' }}>ℹ️</span>
      </div>

      {/* Top Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.4rem' }}>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>TOTAL PILOTS</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#a855f7', fontFamily: 'monospace' }}>
            {totalCorps * 50}
          </div>
        </div>
        <div>
          <div style={{ fontSize: '0.5rem', color: 'rgba(255,255,255,0.4)', marginBottom: '0.1rem' }}>AVG MORALE</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: morale >= 60 ? '#3fb950' : '#ffcc00', fontFamily: 'monospace' }}>
            {morale.toFixed(1)}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', padding: '0 0.5rem' }}>
        <MiniChart data={timelineData} height={60} color="#a855f7" />
      </div>

      {/* Bottom Stats */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.55rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.3rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
          <span style={{ color: '#3fb950' }}>🟢</span>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Elite: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>22</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
          <span style={{ color: '#ff4444' }}>🔴</span>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Struggling: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>22</span>
        </div>
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', fontSize: '0.55rem', marginTop: '0.15rem' }}>
        <div>
          <span style={{ color: 'rgba(255,255,255,0.4)' }}>Top Pilot: </span>
          <span style={{ color: '#fff', fontWeight: 600 }}>Elomaris1</span>
        </div>
      </div>
    </div>
  );
}
