import type { AllianceWars } from '../../types/reports';
import { CoalitionCard } from './CoalitionCard';
import { ConflictCard } from './ConflictCard';

interface AlliancesTabProps {
  allianceWars: AllianceWars | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  livePowerBlocs?: any[] | null;
  powerBlocsTimeframe?: string;
  loading: boolean;
}

const sectionStyle = {
  background: 'rgba(0,0,0,0.3)',
  borderRadius: '8px',
  border: '1px solid rgba(255,255,255,0.08)',
  padding: '0.5rem',
  marginBottom: '0.75rem'
};

export function AlliancesTab({
  allianceWars,
  livePowerBlocs,
  powerBlocsTimeframe = '7d',
  loading
}: AlliancesTabProps) {
  if (loading) return <div className="skeleton" style={{ height: '400px' }} />;
  if (!allianceWars) return <p style={{ color: 'rgba(255,255,255,0.5)' }}>No alliance data available</p>;

  // Use live power blocs if available, otherwise fall back to pre-generated
  const coalitions = livePowerBlocs || allianceWars.coalitions;

  return (
    <>
      {/* POWER BLOCS */}
      {coalitions && coalitions.length > 0 && (
        <div style={sectionStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)', marginBottom: '0.4rem' }}>
            <span style={{ fontSize: '0.65rem' }}>🛡️</span>
            <h2 style={{ margin: 0, fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: '#a855f7' }}>Power Blocs</h2>
            <span style={{ marginLeft: 'auto', fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
              {coalitions.length} blocs ({powerBlocsTimeframe})
            </span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '0.4rem', padding: '0 0.25rem 0.25rem' }}>
            {coalitions.map((coalition) => (
              <CoalitionCard
                key={coalition.leader_alliance_id}
                coalition={coalition}
              />
            ))}
          </div>
        </div>
      )}

      {/* ACTIVE CONFLICTS */}
      <div style={sectionStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.5rem', borderBottom: '1px solid rgba(255,255,255,0.08)', marginBottom: '0.4rem' }}>
          <span style={{ fontSize: '0.65rem' }}>⚔️</span>
          <h2 style={{ margin: 0, fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase', color: '#ff8800' }}>Active Conflicts</h2>
          <span style={{ marginLeft: 'auto', fontSize: '0.55rem', color: 'rgba(255,255,255,0.4)' }}>
            {allianceWars.conflicts.length} wars
          </span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '0.4rem', padding: '0 0.25rem 0.25rem' }}>
          {allianceWars.conflicts.map((conflict) => (
            <ConflictCard
              key={`${conflict.alliance_1_id}-${conflict.alliance_2_id}`}
              conflict={conflict}
            />
          ))}
        </div>
      </div>
    </>
  );
}
