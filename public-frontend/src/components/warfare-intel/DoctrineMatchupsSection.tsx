// src/components/warfare-intel/DoctrineMatchupsSection.tsx

interface DoctrineUsage {
  doctrine_name: string;
  losses: number;
  percentage: number;
}

interface Matchup {
  our_doctrine: string;
  enemy_doctrine: string;
  enemy_ticker: string;
  wins: number;
  losses: number;
  winrate: number;
}

interface DoctrineMatchupsSectionProps {
  doctrines: DoctrineUsage[];
  matchups: Matchup[];
  timeframeLabel: string;
  loading?: boolean;
}

export function DoctrineMatchupsSection({ doctrines, matchups, timeframeLabel, loading }: DoctrineMatchupsSectionProps) {
  const sectionStyle = {
    background: 'linear-gradient(135deg, rgba(15,20,30,0.95) 0%, rgba(20,25,35,0.9) 100%)',
    borderRadius: '12px',
    border: '1px solid rgba(100, 150, 255, 0.1)',
    padding: '1.5rem',
    marginBottom: '1.5rem'
  };

  if (loading) {
    return (
      <div style={sectionStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <span style={{ fontSize: '1.25rem' }}>📊</span>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#a855f7' }}>
            Doctrine Matchups
          </h3>
        </div>
        <div style={{ color: 'rgba(255,255,255,0.4)', padding: '2rem', textAlign: 'center' }}>
          Loading doctrines...
        </div>
      </div>
    );
  }

  return (
    <div style={sectionStyle}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.25rem' }}>📊</span>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#a855f7' }}>
            Doctrine Matchups
          </h3>
        </div>
        <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.4)' }}>
          {timeframeLabel}
        </span>
      </div>

      {/* What they're flying */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          What they're flying
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {doctrines.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', padding: '0.5rem' }}>
              No doctrine data available
            </div>
          ) : (
            doctrines.slice(0, 4).map(d => (
              <div key={d.doctrine_name} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{ flex: 1 }}>
                  <div style={{
                    height: '20px',
                    background: 'rgba(255,255,255,0.1)',
                    borderRadius: '4px',
                    overflow: 'hidden',
                    position: 'relative'
                  }}>
                    <div style={{
                      width: `${d.percentage}%`,
                      height: '100%',
                      background: 'linear-gradient(90deg, #a855f7, #6366f1)',
                      borderRadius: '4px'
                    }} />
                    <span style={{
                      position: 'absolute',
                      left: '0.5rem',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: '#fff',
                      textShadow: '0 1px 2px rgba(0,0,0,0.5)'
                    }}>
                      {d.doctrine_name}
                    </span>
                  </div>
                </div>
                <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.6)', minWidth: '60px', textAlign: 'right' }}>
                  {d.percentage.toFixed(0)}% ({d.losses})
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Matchup Results */}
      <div>
        <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Matchup Results
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {matchups.length === 0 ? (
            <div style={{ color: 'rgba(255,255,255,0.4)', padding: '0.5rem' }}>
              No matchup data available
            </div>
          ) : (
            matchups.slice(0, 5).map((m, i) => {
              const winrateColor = m.winrate >= 60 ? '#00ff88' : m.winrate >= 40 ? '#ffcc00' : '#ff4444';
              return (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.5rem 0.75rem',
                    background: 'rgba(0,0,0,0.2)',
                    borderRadius: '6px'
                  }}
                >
                  <span style={{ fontSize: '0.85rem', color: '#fff' }}>
                    {m.our_doctrine} vs {m.enemy_doctrine}
                    <span style={{ color: 'rgba(255,255,255,0.4)', marginLeft: '0.5rem' }}>
                      ({m.enemy_ticker})
                    </span>
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.5)' }}>
                      W:{m.wins} L:{m.losses}
                    </span>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: winrateColor }}>
                      {m.winrate.toFixed(0)}%
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
