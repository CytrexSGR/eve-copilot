/**
 * AlliancePowerPanel - Alliance statistics and trends
 *
 * Compact design showing system counts, member counts, and weekly deltas.
 */

import type { AlliancePowerData, AlliancePower } from '../../../types/geography-dotlan';

interface AlliancePowerPanelProps {
  data: AlliancePowerData;
}

export function AlliancePowerPanel({ data }: AlliancePowerPanelProps) {
  if (!data.alliances || data.alliances.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        color: '#8b949e',
        padding: '0.5rem',
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '4px',
        fontSize: '0.7rem',
      }}>
        No alliance data available
      </div>
    );
  }

  // Calculate growth stats
  const growingAlliances = data.alliances.filter(a => a.systems_delta > 0).length;
  const shrinkingAlliances = data.alliances.filter(a => a.systems_delta < 0).length;

  return (
    <div>
      {/* Summary Row */}
      <div style={{ background: 'rgba(88, 166, 255, 0.1)', borderRadius: '4px', padding: '0.3rem 0.5rem', marginBottom: '0.4rem', borderLeft: '2px solid #58a6ff' }}>
        <div style={{ display: 'flex', gap: '0.6rem', fontSize: '0.7rem', alignItems: 'baseline', flexWrap: 'wrap' }}>
          <StatItem label="🌐 Systems" value={data.total_systems} color="#58a6ff" />
          <StatItem label="👥 Members" value={data.total_members.toLocaleString()} color="#a855f7" />
          <StatItem label="🏛️ Alliances" value={data.alliances.length} />
          {growingAlliances > 0 && (
            <StatItem label="📈 Growing" value={growingAlliances} color="#3fb950" />
          )}
          {shrinkingAlliances > 0 && (
            <StatItem label="📉 Shrinking" value={shrinkingAlliances} color="#f85149" />
          )}
        </div>
      </div>

      {/* Compact Alliance Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.25rem', maxHeight: '300px', overflowY: 'auto' }}>
        {data.alliances.map((alliance) => (
          <AllianceRow key={alliance.alliance_id || alliance.alliance_name} alliance={alliance} />
        ))}
      </div>
    </div>
  );
}

function StatItem({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
      <span style={{ color: '#8b949e', fontSize: '0.6rem' }}>{label}</span>
      <span style={{ fontWeight: 600, color: color || '#c9d1d9', fontFamily: 'monospace' }}>{value}</span>
    </div>
  );
}

function AllianceRow({ alliance }: { alliance: AlliancePower }) {
  const isTop10 = alliance.rank_by_systems && alliance.rank_by_systems <= 10;
  const systemsColor = alliance.systems_delta > 0 ? '#3fb950' : alliance.systems_delta < 0 ? '#f85149' : '#8b949e';
  const membersColor = alliance.member_delta > 0 ? '#3fb950' : alliance.member_delta < 0 ? '#f85149' : '#8b949e';

  return (
    <div
      style={{
        background: isTop10 ? 'rgba(210,153,34,0.08)' : 'rgba(0,0,0,0.2)',
        borderRadius: '3px',
        padding: '0.3rem 0.4rem',
        borderLeft: `2px solid ${isTop10 ? '#d29922' : '#58a6ff'}`,
        fontSize: '0.65rem',
      }}
    >
      {/* Name + Rank */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', marginBottom: '0.15rem' }}>
        <span style={{
          fontWeight: 600,
          color: '#c9d1d9',
          fontSize: '0.7rem',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          flex: 1,
        }}>
          {alliance.alliance_name}
        </span>
        {alliance.rank_by_systems && (
          <span style={{
            padding: '0.05rem 0.2rem',
            borderRadius: '2px',
            fontSize: '0.5rem',
            fontWeight: 700,
            background: isTop10 ? '#d29922' : 'rgba(255,255,255,0.1)',
            color: isTop10 ? '#000' : '#8b949e',
          }}>
            #{alliance.rank_by_systems}
          </span>
        )}
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', gap: '0.5rem', color: '#8b949e', alignItems: 'baseline' }}>
        {/* Systems */}
        <span>
          <span style={{ opacity: 0.5 }}>Sys </span>
          <span style={{ color: '#c9d1d9', fontFamily: 'monospace' }}>{alliance.systems_count}</span>
          {alliance.systems_delta !== 0 && (
            <span style={{ color: systemsColor, fontSize: '0.55rem', marginLeft: '0.15rem' }}>
              {alliance.systems_delta > 0 ? '↑' : '↓'}{Math.abs(alliance.systems_delta)}
            </span>
          )}
        </span>

        {/* Members */}
        <span>
          <span style={{ opacity: 0.5 }}>Mem </span>
          <span style={{ color: '#c9d1d9', fontFamily: 'monospace' }}>{alliance.member_count.toLocaleString()}</span>
          {alliance.member_delta !== 0 && (
            <span style={{ color: membersColor, fontSize: '0.55rem', marginLeft: '0.15rem' }}>
              {alliance.member_delta > 0 ? '↑' : '↓'}{Math.abs(alliance.member_delta).toLocaleString()}
            </span>
          )}
        </span>

        {/* Corps */}
        <span>
          <span style={{ opacity: 0.5 }}>Corps </span>
          <span style={{ color: '#c9d1d9', fontFamily: 'monospace' }}>{alliance.corp_count}</span>
        </span>
      </div>
    </div>
  );
}

export default AlliancePowerPanel;
