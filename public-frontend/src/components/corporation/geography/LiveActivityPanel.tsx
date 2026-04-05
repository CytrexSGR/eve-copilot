/**
 * LiveActivityPanel - Real-time system activity from DOTLAN
 *
 * Compact design showing ship/pod/NPC kills, jumps, and heat index.
 */

import type { LiveActivityData } from '../../../types/geography-dotlan';
import { getHeatColor, getHeatLevel } from '../../../types/geography-dotlan';

interface LiveActivityPanelProps {
  data: LiveActivityData;
}

export function LiveActivityPanel({ data }: LiveActivityPanelProps) {
  if (!data.systems || data.systems.length === 0) {
    return (
      <div style={{ textAlign: 'center', color: '#8b949e', padding: '0.75rem', fontSize: '0.7rem' }}>
        No recent activity data available
      </div>
    );
  }

  // Calculate totals
  const totalShipKills = data.systems.reduce((sum, s) => sum + s.ship_kills, 0);
  const totalPodKills = data.systems.reduce((sum, s) => sum + s.pod_kills, 0);
  const totalNpcKills = data.systems.reduce((sum, s) => sum + s.npc_kills, 0);
  const totalJumps = data.systems.reduce((sum, s) => sum + s.jumps, 0);
  const hotSystems = data.systems.filter(s => s.heat_index >= 0.7).length;

  return (
    <div>
      {/* Summary Row */}
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '4px', padding: '0.3rem 0.5rem', marginBottom: '0.4rem', borderLeft: '2px solid #14b8a6' }}>
        <div style={{ display: 'flex', gap: '0.3rem', fontSize: '0.7rem', flexWrap: 'wrap' }}>
          <StatItem label="Systems" value={data.systems.length} />
          <StatItem label="🔥 Hot" value={hotSystems} color="#f85149" />
          <StatItem label="Ships" value={totalShipKills} color="#f85149" />
          <StatItem label="Pods" value={totalPodKills} color="#d29922" />
          <StatItem label="NPC" value={totalNpcKills.toLocaleString()} color="#8b949e" />
          <StatItem label="Jumps" value={totalJumps.toLocaleString()} color="#58a6ff" />
          {data.last_scraped && (
            <span style={{ marginLeft: 'auto', fontSize: '0.55rem', color: '#6e7681' }}>
              {new Date(data.last_scraped).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Compact System Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.25rem', maxHeight: '300px', overflowY: 'auto' }}>
        {data.systems.map((system) => {
          const heatLevel = getHeatLevel(system.heat_index);
          const heatColor = getHeatColor(system.heat_index);
          const secColor = getSecurityColor(system.security_status);

          return (
            <div
              key={system.solar_system_id}
              style={{
                background: system.heat_index >= 0.7 ? 'rgba(248,81,73,0.08)' : 'rgba(0,0,0,0.2)',
                padding: '0.25rem 0.4rem',
                borderRadius: '3px',
                borderLeft: `2px solid ${heatColor}`,
                fontSize: '0.65rem',
              }}
            >
              {/* System + Region + Heat inline */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', marginBottom: '0.15rem' }}>
                <span style={{ fontWeight: 600, color: '#c9d1d9', fontSize: '0.7rem' }}>{system.system_name}</span>
                <span style={{ color: secColor, fontSize: '0.55rem', fontFamily: 'monospace' }}>
                  {system.security_status.toFixed(1)}
                </span>
                <HeatBadge level={heatLevel} color={heatColor} />
              </div>

              {/* Stats row */}
              <div style={{ display: 'flex', gap: '0.5rem', color: '#8b949e' }}>
                <span style={{ color: '#6e7681', fontSize: '0.55rem' }}>{system.region_name}</span>
                <span style={{ marginLeft: 'auto' }}>
                  <span style={{ color: '#f85149' }}>{system.ship_kills}</span>
                  <span style={{ opacity: 0.5 }}>/</span>
                  <span style={{ color: '#d29922' }}>{system.pod_kills}</span>
                  <span style={{ opacity: 0.5 }}> K</span>
                </span>
                <span>
                  <span style={{ color: '#58a6ff' }}>{system.jumps}</span>
                  <span style={{ opacity: 0.5 }}> J</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatItem({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem', minWidth: '50px' }}>
      <span style={{ color: '#8b949e', fontSize: '0.6rem' }}>{label}</span>
      <span style={{ fontWeight: 600, color: color || '#c9d1d9', fontFamily: 'monospace' }}>{value}</span>
    </div>
  );
}

function HeatBadge({ level, color }: { level: string; color: string }) {
  const labels: Record<string, string> = {
    critical: 'HOT',
    high: 'ACT',
    medium: 'WRM',
    low: 'COL',
    safe: 'QT',
  };

  return (
    <span
      style={{
        padding: '0.05rem 0.2rem',
        borderRadius: '2px',
        fontSize: '0.5rem',
        fontWeight: 700,
        background: `${color}25`,
        color: color,
        marginLeft: 'auto',
      }}
    >
      {labels[level]}
    </span>
  );
}

function getSecurityColor(sec: number): string {
  if (sec >= 0.5) return '#3fb950';
  if (sec > 0) return '#d29922';
  return '#f85149';
}

export default LiveActivityPanel;
