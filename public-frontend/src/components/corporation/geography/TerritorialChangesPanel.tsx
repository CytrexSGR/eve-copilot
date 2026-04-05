/**
 * TerritorialChangesPanel - Recent sovereignty changes timeline
 *
 * Compact design showing systems gained and lost.
 */

import type { TerritorialChangesData, SovChange } from '../../../types/geography-dotlan';
import { getChangeColor } from '../../../types/geography-dotlan';

interface TerritorialChangesPanelProps {
  data: TerritorialChangesData;
}

export function TerritorialChangesPanel({ data }: TerritorialChangesPanelProps) {
  if (!data.changes || data.changes.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        color: '#8b949e',
        padding: '0.5rem',
        background: 'rgba(0,0,0,0.2)',
        borderRadius: '4px',
        fontSize: '0.7rem',
      }}>
        No sovereignty changes in {data.period_days} days
      </div>
    );
  }

  const netChange = data.net_gained - data.net_lost;

  return (
    <div>
      {/* Summary Row */}
      <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '4px', padding: '0.3rem 0.5rem', marginBottom: '0.4rem', borderLeft: '2px solid #a855f7' }}>
        <div style={{ display: 'flex', gap: '0.6rem', fontSize: '0.7rem', alignItems: 'baseline' }}>
          <StatItem label="Gained" value={`+${data.net_gained}`} color="#3fb950" />
          <StatItem label="Lost" value={`-${data.net_lost}`} color="#f85149" />
          <StatItem
            label="Net"
            value={netChange >= 0 ? `+${netChange}` : `${netChange}`}
            color={netChange >= 0 ? '#3fb950' : '#f85149'}
          />
          <span style={{ marginLeft: 'auto', fontSize: '0.55rem', color: '#6e7681' }}>
            {data.period_days}d period • {data.changes.length} changes
          </span>
        </div>
      </div>

      {/* Compact Changes List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem', maxHeight: '250px', overflowY: 'auto' }}>
        {data.changes.map((change) => (
          <ChangeRow key={change.id} change={change} />
        ))}
      </div>
    </div>
  );
}

function StatItem({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
      <span style={{ color: '#8b949e', fontSize: '0.6rem' }}>{label}</span>
      <span style={{ fontWeight: 700, color, fontFamily: 'monospace', fontSize: '0.85rem' }}>{value}</span>
    </div>
  );
}

function ChangeRow({ change }: { change: SovChange }) {
  const color = getChangeColor(change.change_direction);
  const icon = change.change_direction === 'gained' ? '↑' : change.change_direction === 'lost' ? '↓' : '→';

  // Format date compactly
  const date = change.changed_at ? new Date(change.changed_at) : null;
  const dateStr = date
    ? `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
    : '???';

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.4rem',
        padding: '0.2rem 0.4rem',
        background: 'rgba(0,0,0,0.15)',
        borderRadius: '2px',
        fontSize: '0.65rem',
        borderLeft: `2px solid ${color}`,
      }}
    >
      {/* Direction Icon */}
      <span style={{ fontSize: '0.8rem', fontWeight: 700, color, width: '14px', textAlign: 'center' }}>
        {icon}
      </span>

      {/* System + Region */}
      <span style={{ fontWeight: 600, color: '#c9d1d9' }}>
        {change.system_name || `#${change.solar_system_id}`}
      </span>
      <span style={{ color: '#6e7681', fontSize: '0.55rem' }}>{change.region_name}</span>

      {/* Alliance Change */}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.2rem', fontSize: '0.55rem', maxWidth: '150px' }}>
        {change.old_alliance_name && (
          <span style={{ color: '#f85149', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '60px' }}>
            {change.old_alliance_name}
          </span>
        )}
        {change.old_alliance_name && change.new_alliance_name && (
          <span style={{ color: '#6e7681' }}>→</span>
        )}
        {change.new_alliance_name && (
          <span style={{ color: '#3fb950', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '60px' }}>
            {change.new_alliance_name}
          </span>
        )}
      </div>

      {/* Date */}
      <span style={{ color: '#6e7681', fontSize: '0.5rem', fontFamily: 'monospace', minWidth: '55px', textAlign: 'right' }}>
        {dateStr}
      </span>
    </div>
  );
}

export default TerritorialChangesPanel;
