import { Link } from 'react-router-dom';
import { ConflictCard } from './ConflictCard';
import { MAX_CONFLICTS_DISPLAY, COLORS } from '../../constants';
import type { AllianceWars } from '../../types/reports';

interface ActiveConflictsSectionProps {
  allianceWars: AllianceWars | null;
}

export function ActiveConflictsSection({ allianceWars }: ActiveConflictsSectionProps) {
  const conflictCount = allianceWars?.conflicts?.length || 0;

  if (!allianceWars || conflictCount === 0) return null;

  return (
    <div style={{
      background: 'rgba(0,0,0,0.3)',
      borderRadius: '8px',
      border: '1px solid rgba(255,255,255,0.08)',
      overflow: 'hidden',
      marginBottom: '1rem',
    }}>
      {/* Header */}
      <div style={{
        padding: '0.5rem 0.75rem',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
      }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: COLORS.warning }} />
        <span style={{ fontSize: '0.7rem', fontWeight: 700, color: COLORS.warning, textTransform: 'uppercase' }}>
          Active Conflicts
        </span>
        <span style={{ fontSize: '0.6rem', color: 'rgba(255,255,255,0.4)' }}>
          {conflictCount} wars
        </span>
        <Link to="/battle-report" style={{
          marginLeft: 'auto', padding: '3px 8px',
          background: 'rgba(255,136,0,0.1)', color: '#ff8800',
          borderRadius: '3px', textDecoration: 'none',
          fontSize: '0.6rem', fontWeight: 600,
          border: '1px solid rgba(255,136,0,0.2)',
          textTransform: 'uppercase',
        }}>
          Full Intel
        </Link>
      </div>

      {/* Conflict grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: '0.3rem',
        padding: '0.4rem',
      }}>
        {allianceWars.conflicts.slice(0, MAX_CONFLICTS_DISPLAY).map((conflict) => (
          <ConflictCard
            key={`${conflict.alliance_1_id}-${conflict.alliance_2_id}`}
            conflict={conflict}
          />
        ))}
      </div>
    </div>
  );
}
