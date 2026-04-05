import { usePilotIntel } from '../../hooks/usePilotIntel';
import { formatISK } from '../../utils/format';

export function QuickStatus() {
  const { profile } = usePilotIntel();

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
      gap: '0.5rem', marginBottom: '0.75rem',
    }}>
      {profile.characters.map(char => {
        const activeJobs = char.industry?.jobs?.filter(j => j.status === 'active').length ?? 0;
        return (
          <div key={char.character_id} style={{
            background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '6px', padding: '0.5rem 0.65rem',
            display: 'flex', alignItems: 'center', gap: '0.5rem',
          }}>
            <img
              src={`https://images.evetech.net/characters/${char.character_id}/portrait?size=64`}
              alt=""
              style={{ width: 36, height: 36, borderRadius: '50%', border: '1px solid rgba(255,255,255,0.1)', flexShrink: 0 }}
            />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 700 }}>{char.character_name}</div>
              <div style={{ fontSize: '0.65rem', color: 'rgba(255,255,255,0.4)', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {char.location && <span>{char.location.solar_system_name}</span>}
                {char.ship && <span style={{ color: '#a855f7' }}>{char.ship.ship_type_name}</span>}
              </div>
            </div>
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#3fb950', fontWeight: 600 }}>
                {formatISK(char.wallet?.balance ?? 0)}
              </div>
              {activeJobs > 0 && (
                <div style={{ fontSize: '0.6rem', color: '#00d4ff' }}>{activeJobs} jobs</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
